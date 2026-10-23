"""Check prepared preservation-record consistency without admitting a delivery."""

from __future__ import annotations

import hashlib
import calendar
import re
from decimal import Decimal, DecimalException
from pathlib import Path, PurePosixPath
from typing import Callable


PREPARED_SCHEMA_SHA256 = "42a5e0213de0a877b88edeb686be3905313349898b7d1168ebe86cf2f16480c6"
REQUEST_VERSION = "provingkit-member-delivery-request-v1"


class Contradiction(ValueError):
    """Supplied records contradict the supported request or each other."""


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise Contradiction(reason)


def result(outcome: str, check_outcome: str, reason: str) -> dict:
    return {"outcome": outcome, "established_claims": [], "checks": [{
        "id": "preservation_response", "outcome": check_outcome, "reason": reason,
    }]}


def timestamp_valid(value: str) -> bool:
    match = re.fullmatch(
        r"([0-9]{4})-([0-9]{2})-([0-9]{2})[Tt]"
        r"([01][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9]|60)"
        r"(?:\.[0-9]+)?(?:[Zz]|([+-])([01][0-9]|2[0-3]):([0-5][0-9]))", value)
    if match is None:
        return False
    year, month, day, hour, minute, second = map(int, match.groups()[:6])
    if not 1 <= month <= 12 or not 1 <= day <= calendar.monthrange(year, month)[1]:
        return False
    if second == 60:
        # A leap-second label must fall at the end of a UTC day. This parser
        # does not consult an external announcement table.
        sign, offset_hour, offset_minute = match.groups()[6:]
        offset = (int(offset_hour) * 60 + int(offset_minute)) if sign else 0
        if sign == "-":
            offset = -offset
        if (hour * 60 + minute - offset) % 1440 != 1439:
            return False
    return True


def json_values_equal(left: object, right: object) -> bool:
    pending = [(left, right)]
    while pending:
        left, right = pending.pop()
        if type(left) is not type(right) and not (
            type(left) in (int, float, Decimal) and type(right) in (int, float, Decimal)
        ):
            return False
        if isinstance(left, dict):
            if left.keys() != right.keys():
                return False
            pending.extend((left[key], right[key]) for key in left)
        elif isinstance(left, list):
            if len(left) != len(right):
                return False
            pending.extend(zip(left, right))
        elif left != right:
            return False
    return True


def validate_nonpassing(request: object, root: Path, decode: Callable[[bytes], object]) -> dict | None:
    if not isinstance(request, dict) or request.get("schema_version") != REQUEST_VERSION:
        return None
    try:
        return consume(request, root, decode)
    except DecimalException:
        return result("rejected", "invalid", "A JSON number exceeds the supported numeric range.")
    except (Contradiction, ValueError, UnicodeDecodeError, RecursionError) as error:
        return result("rejected", "invalid", str(error) or "Invalid preservation input.")


def consume(request: dict, root: Path, decode: Callable[[bytes], object]) -> dict:
    require(set(request) == {"schema_version", "preservation"}, "Unsupported request fields.")
    spec = request["preservation"]
    fields = {"response", "admission_request", "reviewed_contract", "schema", "inputs", "expected_dependencies"}
    require(isinstance(spec, dict) and set(spec) == fields, "Invalid preservation request fields.")
    roles = [spec[key] for key in ("response", "admission_request", "reviewed_contract", "schema")]
    require(all(isinstance(name, str) and name for name in roles), "Input roles need logical names.")
    require(len(set(roles)) == 4, "Input roles must identify distinct records.")
    inputs = spec["inputs"]
    require(isinstance(inputs, dict) and all(isinstance(name, str) and name for name in inputs),
            "Invalid logical input map.")
    require(all(name in inputs for name in roles), "The input map omits a required role.")
    expected = spec["expected_dependencies"]
    require(isinstance(expected, dict) and bool(expected)
            and all(isinstance(name, str) and name for name in expected)
            and all(state in ("missing", "unavailable") for state in expected.values()),
            "Invalid expected dependency states.")
    raw_inputs = {}
    missing = []
    for name, identity in inputs.items():
        require(isinstance(identity, dict) and set(identity) == {"path", "bytes", "sha256"},
                "Invalid input identity: " + name)
        path = identity["path"]
        require(isinstance(path, str) and bool(path), "Invalid input path: " + name)
        relative = PurePosixPath(path)
        require(not relative.is_absolute() and ".." not in relative.parts,
                "Input paths must be relative to --inputs: " + name)
        require(type(identity["bytes"]) is int and identity["bytes"] >= 0
                and isinstance(identity["sha256"], str)
                and re.fullmatch(r"[a-f0-9]{64}", identity["sha256"]) is not None,
                "Invalid byte identity: " + name)
        selected = root / relative
        require(selected.resolve().is_relative_to(root.resolve()), "Input path leaves --inputs: " + name)
        try:
            raw = selected.read_bytes()
        except OSError:
            missing.append(name)
            continue
        require(len(raw) == identity["bytes"] and hashlib.sha256(raw).hexdigest() == identity["sha256"],
                "Input bytes differ from the supplied identity: " + name)
        raw_inputs[name] = raw
    require(inputs[spec["schema"]]["sha256"] == PREPARED_SCHEMA_SHA256
            and inputs[spec["schema"]]["bytes"] == 56612,
            "The supplied schema is not the supported prepared schema.")
    response = decode(raw_inputs[spec["response"]]) if spec["response"] in raw_inputs else None
    try:
        # This unchanged public-schema copy is a validator resource, independent
        # of the caller's available files, so missing evidence cannot hide a
        # detectable response contradiction.
        schema_raw = Path(__file__).with_name("member_delivery_prepared.schema.json").read_bytes()
    except OSError:
        return result("incomplete", "unavailable", "The validator's prepared schema resource is unavailable.")
    if hashlib.sha256(schema_raw).hexdigest() != PREPARED_SCHEMA_SHA256:
        return result("incomplete", "unavailable", "The validator's prepared schema resource has changed.")
    schema = decode(schema_raw)
    allowed_dependencies = schema["oneOf"][1]["properties"]["dependencies"]["items"]["properties"]["dependency"]["enum"]
    require(set(expected).issubset(allowed_dependencies), "Unknown expected dependency names.")
    if spec["response"] in missing:
        return result("incomplete", "missing", "Required input files are unavailable: " + ", ".join(missing))
    try:
        from jsonschema import Draft202012Validator, validators
    except ImportError:
        return result("incomplete", "unavailable", "The jsonschema dependency is unavailable.")
    def integer_type(checker, value):
        return Draft202012Validator.TYPE_CHECKER.is_type(value, "integer") or (
            isinstance(value, Decimal) and value.is_finite()
            and value == value.to_integral_value()
        )

    type_checker = Draft202012Validator.TYPE_CHECKER.redefine("integer", integer_type)
    validator_type = validators.extend(Draft202012Validator, type_checker=type_checker)
    invalid = next(validator_type(schema).iter_errors(response), None)
    require(invalid is None, "The response does not match either prepared response shape.")

    def reference(name: str) -> dict:
        return {"logical_name": name, "bytes": inputs[name]["bytes"], "sha256": inputs[name]["sha256"]}

    if response["claim"] == "correspondence-to-owner-admitted-observation-at-capture":
        require(response["producer_contract"] == reference(spec["reviewed_contract"]),
                "The response is bound to a different reviewed contract.")
        require(response["currentness"]["admission_request"] == reference(spec["admission_request"]),
                "The response is bound to a different admission request.")
        for field in ("subject", "baseline"):
            record = response[field]["record"]
            name = record["logical_name"]
            require(name in inputs, "The " + field + " statement is absent from the input map.")
            require(record == reference(name), "The " + field + " statement has a different byte identity.")
            if name in raw_inputs:
                try:
                    statement = decode(raw_inputs[name])
                except DecimalException:
                    raise Contradiction("The raw " + field + " statement exceeds the supported numeric range.") from None
                except (ValueError, UnicodeDecodeError, RecursionError):
                    raise Contradiction("The raw " + field + " statement must contain valid JSON.") from None
                require(json_values_equal(statement, response[field]["statement"]),
                        "The raw " + field + " statement differs from the response statement.")
        require(response["owner_decision"]["baseline_record_sha256"] == response["baseline"]["record"]["sha256"],
                "The decision baseline differs from the supplied baseline record.")
        require(response["owner_decision"]["subject_sha256"] == response["subject"]["record"]["sha256"],
                "The decision subject differs from the supplied subject record.")
        export_hashes = [export["record"]["sha256"] for export in response["exports"]]
        require(len(export_hashes) == len(set(export_hashes)), "Export records repeat a digest.")
        require(set(response["owner_decision"]["export_record_sha256s"]) == set(export_hashes),
                "The decision export digests differ from the supplied export records.")
        baseline = response["baseline"]["statement"]
        timestamps = [baseline["observed_at"], response["owner_decision"]["decided_at"],
                      response["currentness"]["observed_at"]]
        timestamps.extend(client["evidence"]["observed_at"] for client in baseline["clients"].values()
                          if client["evidence"]["state"] == "measured")
        require(all(timestamp_valid(value) for value in timestamps),
                "Decision and observation timestamps must be timezone-aware RFC 3339.")
        if missing:
            return result("incomplete", "missing", "Required input files are unavailable: " + ", ".join(missing))
        return result("incomplete", "missing", "Complete preservation admission is not implemented.")
    require(timestamp_valid(response["observed_at"]), "The observation timestamp must be timezone-aware RFC 3339.")

    require(response["admission_request"] == reference(spec["admission_request"]),
            "The response is bound to a different admission request.")
    require(response["reviewed_contract"] == reference(spec["reviewed_contract"]),
            "The response is bound to a different reviewed contract.")
    known = response["known_records"]
    known_names = [record["logical_name"] for record in known]
    require(len(set(known_names)) == len(known_names), "Known records repeat a logical name.")
    expected_names = set(inputs) - {spec["response"]}
    require(set(known_names) == expected_names, "Known records differ from the supplied input map.")
    require(all(record == reference(record["logical_name"]) for record in known),
            "Known-record byte identities differ from the supplied input map.")
    dependencies = response["dependencies"]
    names = [entry["dependency"] for entry in dependencies]
    require(len(set(names)) == len(names), "Dependencies repeat a name.")
    actual_states = {entry["dependency"]: entry["state"] for entry in dependencies}
    require(actual_states == spec["expected_dependencies"], "Dependency states differ from the caller's expectations.")
    matching_state = "missing" if response["outcome"] == "missing-evidence" else "unavailable"
    require(matching_state in actual_states.values(), "The declared outcome has no matching dependency state.")
    for name, raw in raw_inputs.items():
        try:
            unchanged = (root / inputs[name]["path"]).read_bytes() == raw
        except OSError:
            unchanged = False
        require(unchanged, "Input changed during consumption: " + name)
    report = result("incomplete", "consistent", "The nonpassing response agrees with the supplied identities and dependency states.")
    report["preservation_response"] = {key: response[key] for key in (
        "record_origin", "outcome", "claim", "observed_at", "dependencies", "reason",
    )}
    if missing:
        report["checks"].append({"id": "input_files", "outcome": "missing", "reason":
                                 "Known input files are unavailable: " + ", ".join(missing)})
    return report
