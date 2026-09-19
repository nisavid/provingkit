"""Inspect evaluation source bytes without Git, execution, or grading.

JSON pointers are source coordinates, never invented semantic identifiers.
Owner observations come from declared source fields; selection belongs to the
inventory caller. All paths use repository-relative POSIX spelling.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import PurePosixPath
import re


def _load(content):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key!r}")
            result[key] = value
        return result

    def constant(value):
        raise ValueError(f"Nonfinite JSON number: {value}")

    value = json.loads(content.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    # JSON permits escapes that Python decodes to lone surrogates, and finite
    # number syntax can overflow a float. Admit only values UTF-8 JSON can retain.
    json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    return value


def _owner(value, plugin):
    if not isinstance(value, str) or not value:
        return []
    return [value if ":" in value or not plugin else f"{plugin}:{value}"]


def _escape(value):
    return str(value).replace("~", "~0").replace("/", "~1")


def _fixture(path, literal, pointer, rule):
    parent = PurePosixPath(path).parent
    base = parent.parent if rule == "source-parent-parent" else parent
    if rule == "dictionary-fixture-key":
        base /= "fixtures"
    resolved = None
    if isinstance(literal, str) and literal and not PurePosixPath(literal).is_absolute() and "\\" not in literal:
        parts = []
        for part in (base / literal).parts:
            if part == "..":
                if not parts:
                    break
                parts.pop()
            else:
                parts.append(part)
        else:
            if parts:
                resolved = "/".join(parts)
    return {"literal": literal, "path": resolved, "rule": rule, "pointer": pointer}


def _record(source, pointer, raw, role, owners=(), key=None):
    return {
        "source": source.copy(), "pointer": pointer, "role": role,
        "id": raw.get("id") if isinstance(raw, dict) else None,
        "key": key, "owners": list(owners), "fixtures": [],
        "expectations": [], "raw": raw,
    }


def _expectations(raw, pointer):
    result = []
    for field in ("expectations", "grader_expectations", "must_include", "must_not_include"):
        if not isinstance(raw.get(field, []), list):
            raise ValueError(f"{field} must be an array")
        for index, value in enumerate(raw.get(field, [])):
            structured = value if isinstance(value, dict) else {}
            result.append({
                "pointer": f"{pointer}/{field}/{index}", "field": field,
                "original": value, "id": structured.get("id"),
                "text": structured.get("text") if structured else value,
                "severity": structured.get("severity"),
            })
    return result


def _diagnostic(code, source, pointer, message):
    return {"code": code, "source": source, "pointer": pointer, "message": message}


def _trigger_problem(record):
    if not isinstance(record.get("query"), str) or not record["query"].strip():
        return "A trigger requires a nonblank query string."
    expected = record.get("expected")
    if record.get("expectation_kind") == "boolean":
        if type(expected) is not bool:
            return "A Boolean trigger requires an original Boolean expectation."
    elif record.get("expectation_kind") == "selection-sequence":
        if not isinstance(expected, list) or any(not isinstance(name, str) or not name.strip() for name in expected):
            return "A routing trigger requires the complete array of nonblank skill names."
    else:
        return "The trigger expectation kind is unsupported."
    return None


def _admit_source_links(result):
    """Admit nested values before inventory performs lookup or traversal."""
    def text(value, field):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a nonblank string")

    def strings(value, field):
        if not isinstance(value, list):
            raise ValueError(f"{field} must be an array of strings")
        for item in value:
            text(item, field)

    for reference in result["references"]:
        text(reference.get("path"), "reference path")
        strings(reference.get("owners", []), "reference owners")
    for record in result["records"]:
        if "scenario" not in record:
            continue
        scenario = record["scenario"]
        if not isinstance(scenario, dict):
            raise ValueError("scenario must be an object")
        text(scenario.get("source"), "scenario source")
        text(scenario.get("kind"), "scenario kind")
        if scenario["kind"] not in ("skill-evals", "simple-corpus", "tricritical-corpus"):
            raise ValueError("unsupported scenario selector kind")
        if "selector" not in scenario:
            raise ValueError("scenario requires its original selector")
    if result["format"] == "scenario-matrix":
        raw = result["raw"]
        runtime = raw.get("runtime_dependencies", {})
        if not isinstance(runtime, dict):
            raise ValueError("runtime_dependencies must be an object")
        for owner, paths in runtime.items():
            text(owner, "runtime dependency owner")
            strings(paths, "runtime dependency paths")
        for declaration in raw["skills"]:
            text(declaration.get("id"), "scenario declaration id")
            strings(declaration.get("companions", []), "scenario companions")


def mapping_digest(entry):
    """SHA-256 of sorted compact UTF-8 JSON for the five semantic fields.

    Unicode is emitted directly (ensure_ascii=False); nonfinite numbers are
    forbidden. Review metadata, status, and rationale are outside the digest.
    """
    fields = {key: entry[key] for key in ("source", "pointer", "original", "id", "severity")}
    return hashlib.sha256(json.dumps(fields, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def mapping_projection(entries, records):
    """Return selected accepted semantic fields for applicability comparison.

    Rationale, review metadata, proposals, and unresolved entries are excluded.
    This is a comparison projection, not validation: malformed accepted entries
    remain visible and normalize_records must check them before using a rubric.
    """
    coordinates = {(record["source"]["path"], expectation["pointer"])
                   for record in records for expectation in record["expectations"]}
    selected = [
        {key: entry.get(key) for key in ("source", "pointer", "original", "id", "severity")}
        for entry in entries
        if entry.get("status") == "accepted"
        and (entry.get("source", {}).get("path"), entry.get("pointer")) in coordinates
    ]
    return sorted(selected, key=lambda value: json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False))


def _at_pointer(document, pointer):
    if pointer == "":
        return document
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError("Invalid JSON pointer")
    current = document
    for token in pointer[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        current = current[int(token)] if isinstance(current, list) else current[token]
    return current


def _mapping_problem(entry, expectation, source, documents):
    if entry.get("status") != "accepted":
        return "expectation-mapping-required"
    if entry.get("source") != source:
        return "mapping-source-mismatch"
    content = documents.get(source["path"])
    if content is None or hashlib.sha256(content).hexdigest() != source["sha256"]:
        return "mapping-source-mismatch"
    try:
        original = _at_pointer(json.loads(content), entry["pointer"])
        if original != entry.get("original") or original != expectation["original"]:
            return "mapping-original-mismatch"
    except (ValueError, KeyError, IndexError, TypeError):
        return "mapping-original-mismatch"
    if not isinstance(entry.get("id"), str) or not entry["id"].strip() or entry.get("severity") not in ("safety", "quality"):
        return "mapping-incomplete"
    review = entry.get("review")
    if not isinstance(review, dict) or review.get("decision") != "accepted" or not isinstance(review.get("reference"), str) or not review["reference"].strip():
        return "mapping-review-required"
    if review.get("mapping_sha256") != mapping_digest(entry):
        return "mapping-review-digest-mismatch"
    for field in ("id", "severity"):
        if expectation[field] is not None and entry[field] != expectation[field]:
            return "mapping-source-conflict"
    return None


def normalize_records(records, expectation_map, documents):
    """Normalize selected records, retaining missing classifications explicitly.

    This checks source/data consistency only. It neither runs evaluations nor
    authenticates a review reference or an observation.
    """
    result = {"cases": [], "triggers": [], "diagnostics": []}
    map_invalid = False
    try:
        if isinstance(expectation_map, bytes):
            expectation_map = _load(expectation_map)
        if not isinstance(expectation_map, dict) or type(expectation_map.get("schema_version")) is not int or expectation_map["schema_version"] != 1 or not isinstance(expectation_map.get("entries"), list):
            raise ValueError("Expected schema_version 1 and an entries array")
        entries = expectation_map["entries"]
        if any(not isinstance(entry, dict) or not isinstance(entry.get("source"), dict) or not isinstance(entry["source"].get("path"), str) or not isinstance(entry.get("pointer"), str) for entry in entries):
            raise ValueError("Every map entry requires a source path and pointer")
    except (ValueError, UnicodeError, TypeError, RecursionError) as error:
        entries = []
        map_invalid = True
        result["diagnostics"].append(_diagnostic("invalid-expectation-map", None, "", str(error)))
    inspected = {}
    for record in records:
        if record["role"] not in ("application", "trigger"):
            continue
        original_id = record["id"] if record["id"] is not None else record["key"]
        case = {**record, "case_id": {"source": record["source"]["path"], "pointer": record["pointer"], "id": original_id}, "status": "unresolved" if map_invalid else "ready", "expectations": []}
        content = documents.get(record["source"]["path"])
        if content is None or hashlib.sha256(content).hexdigest() != record["source"]["sha256"]:
            case["status"] = "unresolved"
            result["diagnostics"].append(_diagnostic("source-bytes-mismatch", record["source"], record["pointer"], "Selected record source bytes are missing or differ from inspection."))
        else:
            path = record["source"]["path"]
            if path not in inspected:
                inspected[path] = {item["pointer"]: item for item in inspect_document(path, content)["records"]}
            observed = inspected[path].get(record["pointer"])
            fields = ("source", "pointer", "role", "id", "key", "fixtures", "expectations", "raw", "prompt", "name", "query", "expected", "expectation_kind", "raw_case")
            if observed is None or any(observed.get(field) != record.get(field) for field in fields):
                case["status"] = "unresolved"
                result["diagnostics"].append(_diagnostic("record-source-mismatch", record["source"], record["pointer"], "Selected record differs from the original source observation."))
        for fixture in record["fixtures"]:
            fixture_path = fixture["path"]
            if fixture_path not in documents:
                case["status"] = "unresolved"
                result["diagnostics"].append(_diagnostic("fixture-missing", record["source"], fixture["pointer"], f"Selected fixture bytes are missing: {fixture_path}"))
        if record["role"] == "trigger":
            problem = _trigger_problem(record)
            if problem:
                case["status"] = "unresolved"
                result["diagnostics"].append(_diagnostic("invalid-trigger", record["source"], record["pointer"], problem))
            if record["expectation_kind"] == "selection-sequence":
                case["expected_selection"] = record["expected"]
            else:
                case["should_trigger"] = record["expected"]
            result["triggers"].append(case)
            continue
        if not record["expectations"]:
            case["status"] = "unresolved"
            result["diagnostics"].append(_diagnostic("expectations-missing", record["source"], record["pointer"], "A current application case requires explicit expectation coverage."))
        seen = set()
        for expectation in record["expectations"]:
            item = {**expectation, "source": record["source"].copy()}
            matching = [entry for entry in entries if entry.get("status") == "accepted" and entry.get("source", {}).get("path") == record["source"]["path"] and entry.get("pointer") == item["pointer"]]
            problem = None
            if len(matching) > 1:
                problem = "mapping-duplicate"
            elif matching:
                problem = _mapping_problem(matching[0], expectation, record["source"], documents)
                if problem is None:
                    item.update(id=matching[0]["id"], severity=matching[0]["severity"])
            elif item["id"] is None or item["severity"] is None:
                problem = "expectation-mapping-required"
            if problem is None:
                if (not isinstance(item["id"], str)
                        or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._:-]{0,159}", item["id"])
                        or item["id"] in seen
                        or item["severity"] not in ("safety", "quality")
                        or not isinstance(item["text"], str) or not item["text"].strip()):
                    problem = "invalid-expectation"
                else:
                    seen.add(item["id"])
            if problem:
                case["status"] = "unresolved"
                result["diagnostics"].append(_diagnostic(problem, record["source"], item["pointer"], "Expectation mapping is missing or inconsistent with its source and reviewed semantic digest."))
            case["expectations"].append(item)
        result["cases"].append(case)
    return result


def apply_source_scope(path, result):
    """Classify source role even when committed bytes cannot be admitted."""
    # evals/README.md#phase-2-observable-routing owns this separate release tier.
    if path == "evals/skill-routing-matrix.json":
        result.update(role="scope", scope="production-release")
        for record in result["records"]:
            record["scope"] = "production-release"
        for diagnostic in result["diagnostics"]:
            diagnostic["scope"] = "production-release"
        result["diagnostics"].append({**_diagnostic("scope-only", result["source"], "",
            "Phase 2 production routing is retained separately from ordinary PR coverage."),
            "scope": "production-release"})
    return result


def inspect_document(path, content: bytes, *, plugin=None, skill=None):
    """Return source observations; caller context never invents an owner."""
    source = {"path": path, "sha256": hashlib.sha256(content).hexdigest()}
    failure = {"source": source, "format": "unsupported", "role": "unsupported", "records": [], "references": [], "diagnostics": [], "raw": None}
    try:
        raw = _load(content)
    except (ValueError, UnicodeError, RecursionError) as error:
        failure["diagnostics"].append(_diagnostic("invalid-json", source, "", str(error)))
        return apply_source_scope(path, failure)
    failure["raw"] = raw
    try:
        return apply_source_scope(path, _inspect_document(path, source, raw, plugin))
    except (ValueError, TypeError, AttributeError, KeyError, IndexError) as error:
        failure["diagnostics"].append(_diagnostic("malformed-source", source, "", f"Unsupported source shape: {error}"))
        return apply_source_scope(path, failure)


def _inspect_document(path, source, raw, plugin):
    result = {"source": source, "format": "unsupported", "role": "unsupported",
              "records": [], "references": [], "diagnostics": [], "raw": raw}
    name = PurePosixPath(path).name
    if isinstance(raw, dict) and all(field in raw for field in ("protocol", "corpus_path", "routing_cases", "source_files")):
        result.update(format="preview-panel", role="scope")
        for field in ("cases", "routing_cases"):
            for index, case in enumerate(raw.get(field, [])):
                record = _record(source, f"/{field}/{index}", case, "preview-scope")
                if "fixture_path" in case:
                    record["fixtures"].append({"literal": case["fixture_path"], "path": case["fixture_path"], "rule": "repository-root", "pointer": f"/{field}/{index}/fixture_path"})
                result["records"].append(record)
        for field in ("corpus_path", "routing_source_path"):
            if field in raw:
                result["references"].append({"path": raw[field], "pointer": "/" + field, "role": "scope-source", "owners": []})
        for index, item in enumerate(raw["source_files"]):
            result["references"].append({**item, "pointer": f"/source_files/{index}", "role": "scope-source", "owners": []})
    elif path == "evals/review-publication-handoffs/grading-criteria.json" and isinstance(raw, dict):
        result.update(format="handoff-criteria", role="scope")
        for key, expectations in raw.items():
            pointer = "/" + _escape(key)
            record = _record(source, pointer, expectations, "handoff-scope", key=key)
            record["expectations"] = [{"pointer": f"{pointer}/{index}", "field": "criteria", "original": value, "id": None, "text": value, "severity": None} for index, value in enumerate(expectations)]
            record["fixtures"] = [{"literal": f"cases/{key}.md", "path": str(PurePosixPath(path).parent / "cases" / (key + ".md")), "rule": "handoff-case-key", "pointer": pointer}]
            result["records"].append(record)
    elif isinstance(raw, dict) and ((name == "delivery.json" and "executor" in raw and "grader" in raw) or (name == "policy.json" and ("expectation_thresholds" in raw or {"behavior_acceptance", "trigger_acceptance"} <= set(raw))) or (name == "coverage.json" and "cases" in raw)):
        result.update(format=name.removesuffix(".json"), role="support")
        for index, case in enumerate(raw.get("cases", [])):
            result["records"].append(_record(source, f"/cases/{index}", case, "coverage-declaration"))
    elif name in ("experiment.json", "grading.json", "discovery-evidence.json", "response-evidence.json") or path.startswith(("evals/review-publication-handoffs/baseline/", "evals/review-publication-handoffs/candidate/", "evals/review-publication-handoffs/probe-")):
        result.update(format="retained-result", role="retained-evidence")
        result["records"].append(_record(source, "", raw, "retained-evidence"))
    elif isinstance(raw, dict) and (
            {"candidate_bundle", "runs", "input_format"} <= set(raw)
            or name.endswith(("grading.json", "grading-input.json")) and ("results" in raw or "outputs" in raw)
            or name == "discovery.json" and "results" in raw
            or name.endswith("adjudication.json") and ("adjudications" in raw or "decision" in raw)
            or "evidence_kind" in raw and ("bound_evidence_sha256" in raw or "retained_runs" in raw)):
        result.update(format="retained-result", role="retained-evidence")
        result["records"].append(_record(source, "", raw, "retained-evidence"))
    elif isinstance(raw, list) and all(isinstance(item, dict) and "should_trigger" in item and "query" in item for item in raw):
        result.update(format="trigger-array", role="trigger")
        for index, case in enumerate(raw):
            if type(case["should_trigger"]) is not bool or not isinstance(case["query"], str):
                raise ValueError("Trigger requires a query string and Boolean should_trigger")
            record = _record(source, f"/{index}", case, "trigger")
            record.update(query=case["query"], expected=case["should_trigger"], expectation_kind="boolean")
            result["records"].append(record)
    elif isinstance(raw, dict) and "semantic_definition" in raw and isinstance(raw.get("skills"), list):
        result.update(format="routing-matrix", role="trigger")
        semantic = raw["semantic_definition"]
        result["references"].append({**semantic, "pointer": "/semantic_definition", "role": "semantic-definition", "owners": []})
        for index, reference in enumerate(raw.get("existing_trigger_sources", [])):
            result["references"].append({**reference, "pointer": f"/existing_trigger_sources/{index}", "role": "trigger-source", "owners": _owner(reference.get("skill"), plugin)})
        for index, case in enumerate(raw["skills"]):
            owner = case.get("id")
            name = owner.split(":", 1)[-1] if isinstance(owner, str) else None
            expectations = {"cold_start": [name], "explicit": [name]}
            for field, expected in expectations.items():
                record = _record(source, f"/skills/{index}/{field}", case.get(field), "trigger", _owner(owner, plugin))
                record.update(query=case.get(field), expected=expected, expectation_kind="selection-sequence", raw_case=case)
                result["records"].append(record)
            supplemental = case.get("supplemental")
            if "supplemental" in case and not isinstance(supplemental, dict):
                record = _record(source, f"/skills/{index}/supplemental", supplemental, "trigger", _owner(owner, plugin))
                record.update(query=None, expected=None, expectation_kind="selection-sequence", raw_case=case)
                result["records"].append(record)
            elif supplemental is not None:
                for field in ("positive", "negative"):
                    record = _record(source, f"/skills/{index}/supplemental/{field}", supplemental.get(field), "trigger", _owner(owner, plugin))
                    record.update(query=supplemental.get(field), expected=supplemental.get(field + "_expected_skills"), expectation_kind="selection-sequence", raw_case=case)
                    result["records"].append(record)
    elif isinstance(raw, dict) and isinstance(raw.get("skills"), list) and all(isinstance(item, dict) and "scenario" in item for item in raw["skills"]):
        result.update(format="scenario-matrix", role="reference")
        for index, case in enumerate(raw["skills"]):
            pointer = f"/skills/{index}"
            owners = _owner(case.get("id"), plugin)
            record = _record(source, pointer, case, "scenario-reference", owners)
            record["scenario"] = case["scenario"]
            result["records"].append(record)
            scenario = case["scenario"]
            result["references"].append({"path": scenario["source"], "pointer": pointer + "/scenario", "role": "scenario-source", "owners": owners, "selector": scenario["selector"], "kind": scenario["kind"]})
    elif isinstance(raw, dict) and "control_plane_definition" in raw and isinstance(raw.get("fixtures"), list):
        result.update(format="retirement-associations", role="reference")
        for field in ("control_plane_definition", "corpus"):
            result["references"].append({"path": raw[field], "pointer": "/" + field, "role": "retirement-source", "owners": []})
        for index, case in enumerate(raw["fixtures"]):
            record = _record(source, f"/fixtures/{index}", case, "retirement-association", _owner(case.get("evaluation_skill_id"), plugin))
            record["scenario"] = {"source": raw["corpus"], "selector": case.get("scenario_selector"), "kind": "simple-corpus", "id": case.get("id")}
            result["records"].append(record)
    elif isinstance(raw, dict) and isinstance(raw.get("evals"), list):
        result.update(format="skill-evals", role="application")
        for index, case in enumerate(raw["evals"]):
            pointer = f"/evals/{index}"
            record = _record(source, pointer, case, "application", _owner(raw.get("skill_name"), plugin))
            record.update(name=case.get("name"), prompt=case.get("prompt"))
            record["expectations"] = _expectations(case, pointer)
            for field in ("fixture_paths", "files"):
                if not isinstance(case.get(field, []), list):
                    raise ValueError(f"{field} must be an array")
                for number, literal in enumerate(case.get(field, [])):
                    record["fixtures"].append(_fixture(path, literal, f"{pointer}/{field}/{number}", "source-parent-parent"))
            result["records"].append(record)
    elif isinstance(raw, dict) and isinstance(raw.get("scenarios"), (list, dict)):
        cases = raw["scenarios"]
        dictionary = isinstance(cases, dict)
        result.update(format="tricritical-corpus" if dictionary else "scenario-array", role="application")
        for key, case in (cases.items() if dictionary else enumerate(cases)):
            pointer = f"/scenarios/{_escape(key)}"
            declared = case.get("candidate_skill") if dictionary else case.get("skill")
            record = _record(source, pointer, case, "application", _owner(declared, plugin), key if dictionary else None)
            record.update(name=case.get("name"), prompt=case.get("prompt"))
            record["expectations"] = _expectations(case, pointer)
            if dictionary:
                record["fixtures"].append(_fixture(path, key, pointer, "dictionary-fixture-key"))
            if "fixture_path" in case:
                record["fixtures"].append(_fixture(path, case["fixture_path"], pointer + "/fixture_path", "source-parent"))
            for number, literal in enumerate(case.get("fixture_paths", [])):
                record["fixtures"].append(_fixture(path, literal, f"{pointer}/fixture_paths/{number}", "source-parent-parent"))
            result["records"].append(record)
    _admit_source_links(result)
    for record in result["records"]:
        if record["role"] == "trigger":
            problem = _trigger_problem(record)
            if problem:
                result["diagnostics"].append(_diagnostic("invalid-trigger", source, record["pointer"], problem))
        for fixture in record["fixtures"]:
            if fixture["path"] is None:
                result["diagnostics"].append(_diagnostic("fixture-path-unresolved", source, fixture["pointer"], "Fixture literal has no repository-relative resolution under its source rule."))
    if result["role"] in ("scope", "support", "retained-evidence"):
        result["diagnostics"].append(_diagnostic("scope-only", source, "", "This source describes a separate protocol, support input, or retained result; it supplies no current application or discovery grades."))
    elif result["role"] == "unsupported":
        result["diagnostics"].append(_diagnostic("unsupported-format", source, "", "No supported current source format matches this document."))
    return result
