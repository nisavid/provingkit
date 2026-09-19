#!/usr/bin/env python3
"""Prepare and package local feedback observations; never launch a model.

Procedure: docs/agents/mergecraft-feedback-evaluations.md.
The evidence validator owns canonical requests, history, and qualification.
"""

import argparse
from contextlib import contextmanager
import importlib.util
import os
from pathlib import Path
import re
import stat
import sys


VALIDATOR_PATH = Path(__file__).with_name("validate_feedback_response_evidence.py")
spec = importlib.util.spec_from_file_location("feedback_evidence_method", VALIDATOR_PATH)
evidence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evidence)
require = evidence.require


def encoded(value):
    return (evidence.canonical(value) + "\n").encode("utf-8")


def identity(path):
    path = Path(path)
    require(path.is_file(), f"method input missing: {path}")
    return {"path": str(path.resolve()), "sha256": evidence.digest(path.read_bytes()),
            "mode": stat.S_IMODE(path.stat().st_mode)}


def create(path, raw):
    with Path(path).open("xb") as stream:
        stream.write(raw)


LOCK_NAME = ".feedback-response-evals.lock"
SESSION_STATE_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


def regular_bytes(path, message):
    path = Path(path)
    try:
        status = path.lstat()
    except OSError:
        require(False, message)
    require(stat.S_ISREG(status.st_mode) and status.st_nlink == 1, message)
    return path.read_bytes()


@contextmanager
def admission_lock(output, operation):
    output = Path(output)
    require(output.is_dir() and not output.is_symlink(), "evaluation directory alias invalid")
    lock = output / LOCK_NAME
    marker = encoded({"schema_version": 1, "operation": operation, "pid": os.getpid()})
    try:
        create(lock, marker)
    except FileExistsError:
        require(False, "evaluation admission lock busy or recovery required")
    try:
        yield
    finally:
        require(not lock.is_symlink() and regular_bytes(lock, "admission lock ownership changed") == marker,
                "admission lock ownership changed")
        lock.unlink()


def source_snapshot(root):
    root = Path(root)
    manifest = evidence.strict_json(evidence.read_source(root, evidence.MANIFEST).decode("utf-8"))
    require(set(manifest) == {"skill_name", "evals"}
            and manifest["skill_name"] == "interacting-with-pr-review-feedback", "manifest schema drift")
    cases = manifest["evals"]
    require(isinstance(cases, list) and cases, "manifest cases missing")
    ids = [case["id"] for case in cases]
    require(all(type(value) is int for value in ids) and len(ids) == len(set(ids)), "case identities invalid")
    paths = evidence.source_paths(root, cases)
    return {"cases": cases,
            "source_sha256": {path: evidence.digest(evidence.read_source(root, path)) for path in paths},
            "source_modes": {path: stat.S_IMODE((root / path).stat().st_mode) for path in paths}}


def method_matches(root):
    for local in (Path(__file__), VALIDATOR_PATH):
        require(local.read_bytes() == evidence.read_source(Path(root), "scripts/" + local.name),
                "running method differs from candidate source")


def dispatch_contract(path):
    raw = Path(path).read_bytes().decode("utf-8")
    value = evidence.strict_json(raw)
    require(isinstance(value, dict) and set(value) == {
        "schema_version", "route", "model", "reasoning_effort",
        "executor_instructions", "grader_instructions", "method_files",
    } and type(value["schema_version"]) is int and value["schema_version"] == 1,
            "dispatch contract schema invalid")
    for key in ("route", "model", "reasoning_effort", "executor_instructions", "grader_instructions"):
        require(isinstance(value[key], str) and value[key].strip(), f"dispatch {key} missing")
    require(isinstance(value["method_files"], list) and value["method_files"], "dispatch method files missing")
    files = []
    for item in value["method_files"]:
        require(isinstance(item, dict) and set(item) == {"label", "path"}
                and isinstance(item["label"], str) and item["label"].strip()
                and isinstance(item["path"], str) and Path(item["path"]).is_absolute(),
                "dispatch method file invalid")
        files.append({"label": item["label"], **identity(item["path"])})
    require(len({item["label"] for item in files}) == len(files), "duplicate method label")
    return {"document": raw, "identity": identity(path), "files": files}


def prepare(root, output, dispatch, *, additional_experiments=(), historical_context=()):
    """Freeze exact inputs for a separately authorized, route-specific runner."""
    root, output = Path(root).resolve(), Path(output).resolve()
    require(not output.is_relative_to(root), "evaluation output must be outside source")
    require(not output.exists(), "evaluation output already exists")
    method_matches(root)
    snapshot = source_snapshot(root)
    policy = {str(case["id"]): [
        {"id": f"case-{case['id']}-expectation-{index}", "text": text, "severity": "safety"}
        for index, text in enumerate(case["expectations"], 1)
    ] for case in snapshot["cases"]}
    evidence.validate_expectation_policy(snapshot["cases"], policy)
    prior = evidence.read_source(root, evidence.EVIDENCE).decode("utf-8")
    additional = [Path(path).read_bytes().decode("utf-8") for path in additional_experiments]
    context = [{"identity": identity(path), "document": Path(path).read_bytes().decode("utf-8"),
                "selected": False} for path in historical_context]
    frozen = {"schema_version": 1, **snapshot, "candidate_paths": list(evidence.CANDIDATE_PATHS),
              "expectation_policy": policy, "history": evidence.history_envelope(prior, additional),
              "historical_context": context, "dispatch": dispatch_contract(dispatch)}
    output.mkdir(parents=True)
    create(output / "preparation.json", encoded(frozen))
    return {"preparation_sha256": evidence.digest(encoded(frozen)),
            "executions": len(snapshot["cases"]) * 6, "grading_exchanges": len(snapshot["cases"]) * 6}


def verify(root, output):
    """Check prepared input correspondence, without authenticating observations."""
    root, output = Path(root), Path(output)
    method_matches(root)
    frozen = evidence.strict_json((output / "preparation.json").read_bytes().decode("utf-8"))
    require(set(frozen) == {"schema_version", "cases", "source_sha256", "source_modes",
                           "candidate_paths", "expectation_policy", "history", "historical_context", "dispatch"}
            and type(frozen["schema_version"]) is int and frozen["schema_version"] == 1, "preparation schema drift")
    snapshot = source_snapshot(root)
    require(all(frozen[key] == value for key, value in snapshot.items()), "prepared source or method drift")
    require(frozen["candidate_paths"] == list(evidence.CANDIDATE_PATHS), "prepared delivery drift")
    evidence.validate_expectation_policy(frozen["cases"], frozen["expectation_policy"])
    evidence.validate_history(frozen["history"])
    require(evidence.read_source(root, evidence.EVIDENCE).decode("utf-8") == frozen["history"]["prior_document"],
            "predecessor changed after preparation")
    require(dispatch_contract(frozen["dispatch"]["identity"]["path"]) == frozen["dispatch"], "dispatch method drift")
    for item in frozen["historical_context"]:
        require(item["selected"] is False and identity(item["identity"]["path"]) == item["identity"]
                and Path(item["identity"]["path"]).read_bytes().decode("utf-8") == item["document"],
                "historical context drift")
    return frozen


def _packet_unlocked(root, output, case_id, variant, repetition, role="execution"):
    """Return the exact request and role instructions a runner must deliver."""
    frozen = verify(root, output)
    require(type(case_id) is int and variant in ("with_skill", "without_skill")
            and type(repetition) is int and repetition in (1, 2, 3), "unknown coordinate")
    case = next((row for row in frozen["cases"] if row["id"] == case_id), None)
    require(case is not None and role in ("execution", "grading"), "unknown coordinate or role")
    dispatch = evidence.strict_json(frozen["dispatch"]["document"])
    request = evidence.executor_request(Path(root), case, variant)
    if role == "grading":
        execution = _packet_unlocked(root, output, case_id, variant, repetition)
        observed, _ = _read_record_unlocked(output, execution)
        request = evidence.grading_request(
            case, request, observed["response"], evidence.digest(observed["response"]),
            frozen["expectation_policy"][str(case_id)],
        )
    value = {"preparation_sha256": evidence.digest(encoded(frozen)),
             "case_id": case_id, "variant": variant, "repetition": repetition, "role": role,
             "model": dispatch["model"], "reasoning_effort": dispatch["reasoning_effort"],
             "instructions": dispatch["executor_instructions" if role == "execution" else "grader_instructions"],
             "request": request}
    return {"packet": value, "sha256": evidence.digest(encoded(value))}


def packet(root, output, case_id, variant, repetition, role="execution"):
    if role == "grading":
        with admission_lock(output, "grading-packet"):
            _session_state_unlocked(root, output)
            return _packet_unlocked(root, output, case_id, variant, repetition, role)
    return _packet_unlocked(root, output, case_id, variant, repetition, role)


def record_directory(output, prepared):
    value = prepared["packet"]
    return Path(output) / "records" / (
        f"{value['case_id']}-{value['variant']}-{value['repetition']}-{value['role']}"
    )


def observation(raw, prepared):
    value = evidence.strict_json(raw.decode("utf-8"))
    require(isinstance(value, dict) and set(value) == {
        "packet_sha256", "session_id", "model", "reasoning_effort", "turn_status",
        "request", "response", "tool_events",
    }, "observation schema invalid")
    try:
        encoded(value)
    except UnicodeEncodeError:
        require(False, "observation cannot be encoded as canonical UTF-8")
    expected = prepared["packet"]
    require(value["packet_sha256"] == prepared["sha256"], "observation packet mismatch")
    for field in ("model", "reasoning_effort", "request"):
        require(value[field] == expected[field], f"observation {field} mismatch")
    require(isinstance(value["session_id"], str) and value["session_id"].strip(), "session label missing")
    require(value["turn_status"] == "completed", "observation did not complete")
    require(isinstance(value["response"], str) and value["response"].strip(), "response missing")
    require(value["tool_events"] == [], "observation tool events present")
    return value


def _read_record_unlocked(output, prepared):
    directory = record_directory(output, prepared)
    require(directory.is_dir() and not directory.is_symlink(), "record directory invalid")
    require({path.name for path in directory.iterdir()} == {
        "packet.json", "observation.json", "raw-record.bin", "record.json",
    }, "record file inventory drift")
    require(regular_bytes(directory / "packet.json", "recorded packet alias invalid") == encoded(prepared),
            "recorded packet drift")
    index_raw = regular_bytes(directory / "record.json", "record index alias invalid")
    index = evidence.strict_json(index_raw.decode("utf-8"))
    raw = regular_bytes(directory / "raw-record.bin", "raw record alias invalid")
    normalized = regular_bytes(directory / "observation.json", "observation alias invalid")
    require(index_raw == encoded(index), "record index encoding drift")
    require(index == {"packet_sha256": prepared["sha256"],
                      "raw_record_sha256": evidence.digest(raw),
                      "observation_sha256": evidence.digest(normalized)} and bool(raw), "record bytes drift")
    return observation(normalized, prepared), index


def historical_sessions(frozen):
    values = [evidence.strict_json(item["raw_json"]) for item in frozen["history"]["entries"]]
    values.extend(evidence.strict_json(item["document"])
                  for item in frozen["history"]["additional_experiments"])
    return {row[key] for value in values for row in evidence._walk_dicts(value)
            for key in ("session_id", "execution_session_id", "grading_session_id")
            if isinstance(row.get(key), str)}


def expected_coordinates(frozen):
    return {f"{case['id']}-{variant}-{repetition}-{role}": {
                "case_id": case["id"], "variant": variant,
                "repetition": repetition, "role": role,
            }
            for case in frozen["cases"] for variant in ("with_skill", "without_skill")
            for repetition in (1, 2, 3) for role in ("execution", "grading")}


def _session_state_unlocked(root, output):
    frozen = verify(root, output)
    historical = sorted(historical_sessions(frozen))
    state = {"schema_version": 1, "preparation_sha256": evidence.digest(encoded(frozen)),
             "historical_session_ids": historical, "accepted_records": []}
    records_root = Path(output) / "records"
    require(not records_root.is_symlink(), "record inventory alias invalid")
    if not records_root.exists():
        return {"state": state, "sha256": evidence.digest(encoded(state))}
    require(records_root.is_dir(), "record inventory invalid")
    coordinates = expected_coordinates(frozen)
    accepted, labels = [], set()
    for directory in sorted(records_root.iterdir(), key=lambda item: item.name):
        require(directory.name in coordinates, "record inventory contains an unknown coordinate")
        require(directory.is_dir() and not directory.is_symlink(), "record directory invalid")
        coordinate = coordinates[directory.name]
        prepared = _packet_unlocked(root, output, **coordinate)
        observed, index = _read_record_unlocked(output, prepared)
        label = observed["session_id"]
        require(label not in historical, "historical session cannot supply a selected observation")
        require(label not in labels, "current session cannot supply more than one selected observation")
        labels.add(label)
        accepted.append({**coordinate, "session_id": label, "packet_sha256": index["packet_sha256"],
                         "observation_sha256": index["observation_sha256"],
                         "raw_record_sha256": index["raw_record_sha256"]})
    accepted.sort(key=lambda item: (item["case_id"], item["variant"], item["repetition"], item["role"]))
    state["accepted_records"] = accepted
    return {"state": state, "sha256": evidence.digest(encoded(state))}


def session_state(root, output):
    with admission_lock(output, "session-state"):
        return _session_state_unlocked(root, output)


def record(root, output, case_id, variant, repetition, role, observation_path, raw_record, *,
           expected_session_state_sha256):
    """Retain supplied bytes once, then atomically admit their declared correspondence."""
    normalized, raw = Path(observation_path).read_bytes(), Path(raw_record).read_bytes()
    with admission_lock(output, "record"):
        before = _session_state_unlocked(root, output)
        prepared = _packet_unlocked(root, output, case_id, variant, repetition, role)
        directory = record_directory(output, prepared)
        directory.parent.mkdir(exist_ok=True)
        require(directory.parent.is_dir() and not directory.parent.is_symlink(), "record inventory alias invalid")
        directory.mkdir()
        create(directory / "observation.json", normalized)
        create(directory / "raw-record.bin", raw)
        create(directory / "packet.json", encoded(prepared))
        try:
            require(isinstance(expected_session_state_sha256, str)
                    and SESSION_STATE_PATTERN.fullmatch(expected_session_state_sha256),
                    "session state SHA-256 must be 64 lowercase hexadecimal characters")
            require(expected_session_state_sha256 == before["sha256"], "stale session state")
            value = observation(normalized, prepared)
            require(bool(raw), "raw record missing")
            require(value["session_id"] not in before["state"]["historical_session_ids"],
                    "historical session cannot supply a selected observation")
            require(value["session_id"] not in {
                item["session_id"] for item in before["state"]["accepted_records"]
            }, "current session cannot supply more than one selected observation")
        except (evidence.EvidenceError, UnicodeError, ValueError) as error:
            create(directory / "rejection.json", encoded({"selected": False, "reason": str(error)}))
            raise
        index = {"packet_sha256": prepared["sha256"], "raw_record_sha256": evidence.digest(raw),
                 "observation_sha256": evidence.digest(normalized)}
        create(directory / "record.json", encoded(index))
        after = _session_state_unlocked(root, output)
        return {"recorded": True, "session_id": value["session_id"],
                "packet_sha256": prepared["sha256"],
                "record_sha256": evidence.digest(encoded(index)),
                "session_state_sha256_before": before["sha256"],
                "session_state_sha256_after": after["sha256"]}


def _assemble_unlocked(root, output, destination):
    """Require the whole prepared batch and export the existing closed schema."""
    root, destination = Path(root).resolve(), Path(destination).resolve()
    require(not destination.is_relative_to(root), "assembled output must be outside source")
    provenance_path = destination.with_name(destination.name + ".provenance.json")
    require(not destination.exists() and not provenance_path.exists(), "assembly output already exists")
    _session_state_unlocked(root, output)
    frozen = verify(root, output)
    dispatch = evidence.strict_json(frozen["dispatch"]["document"])
    excluded_sessions = historical_sessions(frozen)
    expected = {f"{case['id']}-{variant}-{repetition}-{role}"
                for case in frozen["cases"] for variant in ("with_skill", "without_skill")
                for repetition in (1, 2, 3) for role in ("execution", "grading")}
    records_root = Path(output) / "records"
    require(records_root.is_dir() and {path.name for path in records_root.iterdir()} == expected,
            "record inventory differs from prepared coordinates")
    records, record_identities = [], []
    for case in frozen["cases"]:
        for variant in ("with_skill", "without_skill"):
            for repetition in (1, 2, 3):
                row = {"case_id": case["id"], "variant": variant, "repetition": repetition}
                for role in ("execution", "grading"):
                    prepared = _packet_unlocked(root, output, case["id"], variant, repetition, role)
                    observed, recorded_identity = _read_record_unlocked(output, prepared)
                    record_identities.append({"case_id": case["id"], "variant": variant,
                                              "repetition": repetition, "role": role, **recorded_identity})
                    require(observed["session_id"] not in excluded_sessions,
                            "historical session cannot supply a selected observation")
                    for field in ("session_id", "model", "reasoning_effort", "turn_status"):
                        row[f"{role}_{field}"] = observed[field]
                    prefix = "" if role == "execution" else "grading_"
                    for field in ("request", "response"):
                        row[prefix + field] = observed[field]
                        row[prefix + field + "_sha256"] = evidence.digest(observed[field])
                    row[prefix + "tool_events"] = observed["tool_events"]
                    if role == "grading":
                        row["grades"] = evidence.strict_json(observed["response"])["expectations"]
                records.append(row)
    document = {"schema_version": 2, "runs": 3,
                "model": dispatch["model"], "reasoning_effort": dispatch["reasoning_effort"],
                "candidate_paths": frozen["candidate_paths"], "source_sha256": frozen["source_sha256"],
                "expectation_policy": frozen["expectation_policy"], "authority": evidence.LOCAL_AUTHORITY,
                "history": frozen["history"], "records": records}
    evidence.validate(root, document=document)
    verify(root, output)
    raw = encoded(document)
    provenance = {"preparation_sha256": evidence.digest(encoded(frozen)),
                  "evidence_sha256": evidence.digest(raw), "historical_context": frozen["historical_context"],
                  "records": record_identities,
                  "authority": "Local byte correspondence; no provider authentication or execution assurance."}
    create(provenance_path, encoded(provenance))
    create(destination, raw)
    return {"evidence_sha256": evidence.digest(raw), "records": len(records),
            "provenance_sha256": evidence.digest(encoded(provenance))}


def assemble(root, output, destination):
    with admission_lock(output, "assemble"):
        return _assemble_unlocked(root, output, destination)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for action in ("prepare", "verify", "session-state", "packet", "record", "assemble"):
        command = commands.add_parser(action)
        command.add_argument("--repo", type=Path, required=True)
        if action == "prepare":
            command.add_argument("--output", type=Path, required=True)
            command.add_argument("--dispatch", type=Path, required=True)
            command.add_argument("--additional-experiment", type=Path, action="append", default=[])
            command.add_argument("--historical-context", type=Path, action="append", default=[])
        else:
            command.add_argument("--evaluation", type=Path, required=True)
        if action in ("packet", "record"):
            command.add_argument("--case", type=int, required=True)
            command.add_argument("--variant", choices=("with_skill", "without_skill"), required=True)
            command.add_argument("--repetition", type=int, choices=(1, 2, 3), required=True)
            command.add_argument("--role", choices=("execution", "grading"), required=True)
        if action == "record":
            command.add_argument("--observation", type=Path, required=True)
            command.add_argument("--raw-record", type=Path, required=True)
            command.add_argument("--session-state-sha256", required=True)
        if action == "assemble":
            command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(args.repo, args.output, args.dispatch,
                             additional_experiments=args.additional_experiment,
                             historical_context=args.historical_context)
        elif args.command == "verify":
            frozen = verify(args.repo, args.evaluation)
            result = {"status": "inputs-match", "preparation_sha256": evidence.digest(encoded(frozen)),
                      "source_files": len(frozen["source_sha256"])}
        elif args.command == "session-state":
            result = session_state(args.repo, args.evaluation)
        elif args.command == "assemble":
            result = assemble(args.repo, args.evaluation, args.output)
        else:
            coordinate = (args.repo, args.evaluation, args.case, args.variant, args.repetition, args.role)
            result = (packet(*coordinate) if args.command == "packet" else
                      record(*coordinate, args.observation, args.raw_record,
                             expected_session_state_sha256=args.session_state_sha256))
        print(evidence.canonical(result))
        return 0
    except (evidence.EvidenceError, OSError, ValueError, TypeError, KeyError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
