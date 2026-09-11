#!/usr/bin/env python3
"""Validate retained feedback-response experiment bindings, not model judgments."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

SKILL = "plugins/mergecraft/skills/interacting-with-pr-review-feedback"
MANIFEST = "evals/mergecraft/skills/interacting-with-pr-review-feedback/evals.json"
EVIDENCE = f"{SKILL}/evals/response-evidence.json"
CANDIDATE_PATHS = (
    f"{SKILL}/SKILL.md",
    f"{SKILL}/references/interaction-authority.md",
    f"{SKILL}/references/github-markdown-authoring.md",
)
SOURCE_GLOBS = (
    f"{SKILL}/scripts/*.py",
    "tests/plugins/mergecraft/interacting-with-pr-review-feedback/**/*.py",
    "tests/plugins/mergecraft/interacting-with-pr-review-feedback/fixtures/**/*",
    "plugins/mergecraft/skills/addressing-pr-review-feedback/scripts/review_feedback_state.py",
    "tests/plugins/mergecraft/addressing-pr-review-feedback/**/*.py",
    "tests/plugins/mergecraft/addressing-pr-review-feedback/fixtures/**/*",
)

TOP_LEVEL_FIELDS = {
    "schema_version",
    "runs",
    "model",
    "reasoning_effort",
    "candidate_paths",
    "source_sha256",
    "expectation_policy",
    "authority",
    "history",
    "records",
}
RECORD_FIELDS = {
    "case_id",
    "variant",
    "repetition",
    "execution_session_id",
    "execution_model",
    "execution_reasoning_effort",
    "execution_turn_status",
    "request",
    "request_sha256",
    "response",
    "response_sha256",
    "tool_events",
    "grading_session_id",
    "grading_model",
    "grading_reasoning_effort",
    "grading_turn_status",
    "grading_request",
    "grading_request_sha256",
    "grading_response",
    "grading_response_sha256",
    "grading_tool_events",
    "grades",
}
LOCAL_AUTHORITY = {
    "kind": "locally_authored_development_observation",
    "session_identity": "unverified_label",
    "hash_scope": "recorded_bytes_only",
    "excluded_authority": [
        "provider_attestation",
        "release",
        "deployment",
        "installation",
        "live_response_write",
    ],
}
HISTORY_FIELDS = {
    "schema_version",
    "scope",
    "complete_model_activity_census",
    "prior_document",
    "prior_document_sha256",
    "additional_experiments",
    "entries",
}
RETAINED_EXPERIMENT_FIELDS = {
    "document",
    "document_sha256",
    "selected",
    "exclusion_reason",
    "availability",
    "completion",
}
EXPERIMENT_COMPLETION_FIELDS = {
    "planned_coordinates",
    "recorded_executions",
    "uncompleted_or_unrecorded_coordinates",
    "recorded_grades",
    "state",
}
EXPERIMENT_DOCUMENT_FIELDS = {
    "name",
    "selected",
    "reason",
    "stopped_at",
    "launcher_exit_code",
    "planned_coordinates",
    "completed_execution_count",
    "uncompleted_or_unrecorded_job_ids",
    "frozen_inputs",
    "raw_executions",
    "raw_grades",
}
HISTORICAL_LAUNCHER_FIELDS = {
    "job_id",
    "session_id",
    "model",
    "reasoning_effort",
    "request",
    "request_sha256",
    "response",
    "response_sha256",
    "tool_events",
    "turn_status",
}
HISTORY_ENTRY_FIELDS = {
    "id",
    "kind",
    "source_pointer",
    "selected",
    "exclusion_reason",
    "raw_json",
    "raw_sha256",
    "availability",
}
AVAILABILITY_FIELDS = {
    "exchange_records",
    "coordinate_identity",
    "session_identity",
    "request_response_digests",
    "completion_state",
    "tool_events",
    "grading_linkage",
}
LEGACY_TOP_LEVEL_FIELDS = {
    "schema_version",
    "runs",
    "model",
    "reasoning_effort",
    "candidate_paths",
    "source_sha256",
    "expectation_policy",
    "records",
    "method",
    "unqualified_path_labeled_handoff",
    "prior_experiments",
    "isolation_correction",
    "grading_contract_audit",
}


class EvidenceError(ValueError):
    """Retained evidence does not match its declared inputs."""


def require(condition, message):
    if not condition:
        raise EvidenceError(message)


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def digest(value):
    return hashlib.sha256(
        value if isinstance(value, bytes) else value.encode("utf-8")
    ).hexdigest()


def require_unique_additional_experiment_documents(documents):
    require(
        isinstance(documents, (list, tuple))
        and all(isinstance(document, str) and document for document in documents),
        "additional experiment documents invalid",
    )
    document_digests = [digest(document) for document in documents]
    require(
        len(document_digests) == len(set(document_digests)),
        "additional experiment document digest inventory invalid",
    )


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result

    def invalid(value):
        raise EvidenceError("non-finite JSON number")

    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid)
    except (ValueError, TypeError) as error:
        raise EvidenceError(str(error)) from error


def read_source(root, relative):
    require(isinstance(relative, str) and relative, "invalid source path")
    path = PurePosixPath(relative)
    require(
        not path.is_absolute()
        and ".." not in path.parts
        and str(path) == relative
        and "\\" not in relative,
        "source path must be strictly relative",
    )
    current = root
    for part in path.parts:
        current = current / part
        require(not current.is_symlink(), f"symlink source: {relative}")
    require(current.is_file(), f"missing source: {relative}")
    return current.read_bytes()


def source_paths(root, cases):
    paths = set(CANDIDATE_PATHS) | {MANIFEST}
    for case in cases:
        paths.update("evals/mergecraft/skills/" + name for name in case["files"])
    for pattern in SOURCE_GLOBS:
        matches = [
            path for path in root.glob(pattern) if path.is_file() or path.is_symlink()
        ]
        require(matches, f"empty mandatory source glob: {pattern}")
        paths.update(
            path.relative_to(root).as_posix()
            for path in matches
            if "__pycache__" not in path.parts and path.suffix != ".pyc"
        )
    return sorted(paths)


def executor_request(root, case, variant):
    return canonical(
        {
            "prompt": case["prompt"],
            "fixture": [
                read_source(root, "evals/mergecraft/skills/" + name).decode("utf-8")
                for name in case["files"]
            ],
            "candidate_bundle": [
                read_source(root, path).decode("utf-8") for path in CANDIDATE_PATHS
            ]
            if variant == "with_skill"
            else [],
        }
    )


def _validate_candidate_source_binding(
    request, variant, candidate_paths, source_sha256, boundary
):
    """Bind an executor request's candidate bytes to its applicable source map."""
    message = f"{boundary} source binding invalid"
    require(variant in ("with_skill", "without_skill"), message)
    require(
        isinstance(request, dict)
        and isinstance(request.get("candidate_bundle"), list)
        and all(isinstance(value, str) for value in request["candidate_bundle"]),
        message,
    )
    bundle = request["candidate_bundle"]
    if variant == "without_skill":
        require(bundle == [], message)
        return
    require(len(bundle) == len(candidate_paths), message)
    for path, value in zip(candidate_paths, bundle):
        require(
            path in source_sha256 and digest(value) == source_sha256[path],
            message,
        )


def grading_request(case, request, response, response_sha256, expectations):
    """Return the only grading request admitted for one selected execution."""
    return canonical(
        {
            "executor_request": strict_json(request),
            "response": response,
            "response_sha256": response_sha256,
            "expected_output": case["expected_output"],
            "expectations": expectations,
        }
    )


def _walk_dicts(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_dicts(child)


def _availability(present, total):
    if not present or not total:
        return "unavailable"
    return "recorded_for_all" if present == total else "partially_recorded"


def history_availability(value):
    """Validate recorded legacy exchanges and describe fields they actually retain."""
    exchanges = []
    coordinates = sessions = completion = tool_events = digests = grading_links = 0
    for item in _walk_dicts(value):
        has_exchange = "request" in item or "response" in item
        if has_exchange:
            require(
                isinstance(item.get("request"), str)
                and isinstance(item.get("response"), str),
                "historical request/response bytes missing",
            )
            exchanges.append(item)
            coordinate_present = any(
                field in item for field in ("job_id", "case_id", "variant", "repetition")
            )
            if coordinate_present:
                coordinate_valid = (
                    isinstance(item.get("job_id"), str) and item["job_id"].strip()
                ) or (
                    type(item.get("case_id")) is int
                    and item.get("variant") in ("with_skill", "without_skill")
                    and type(item.get("repetition")) is int
                    and item["repetition"] > 0
                )
                require(coordinate_valid, "historical coordinate identity invalid")
                coordinates += 1
            session_fields = [
                field
                for field in ("session_id", "execution_session_id", "grading_session_id")
                if field in item
            ]
            if session_fields:
                require(
                    all(
                        isinstance(item[field], str) and item[field].strip()
                        for field in session_fields
                    ),
                    "historical session identity invalid",
                )
                sessions += 1
            has_digests = "request_sha256" in item or "response_sha256" in item
            if has_digests:
                require(
                    item.get("request_sha256") == digest(item["request"])
                    and item.get("response_sha256") == digest(item["response"]),
                    "historical request/response digest mismatch",
                )
                digests += 1
            completion_fields = [
                field
                for field in (
                    "turn_status",
                    "execution_turn_status",
                    "grading_turn_status",
                )
                if field in item
            ]
            if completion_fields:
                require(
                    all(
                        isinstance(item[field], str)
                        and item[field] in ("completed", "failed", "interrupted")
                        for field in completion_fields
                    ),
                    "historical completion state invalid",
                )
                completion += 1
            event_fields = [
                field
                for field in ("tool_events", "grading_tool_events")
                if field in item
            ]
            if event_fields:
                require(
                    all(isinstance(item[field], list) for field in event_fields),
                    "historical tool events invalid",
                )
                tool_events += 1
            grading_present = any(
                field in item
                for field in (
                    "grading_request",
                    "grading_request_sha256",
                    "grading_response",
                    "grading_response_sha256",
                )
            )
            if grading_present:
                require(
                    isinstance(item.get("grading_request"), str)
                    and isinstance(item.get("grading_response"), str)
                    and item.get("grading_request_sha256")
                    == digest(item["grading_request"])
                    and item.get("grading_response_sha256")
                    == digest(item["grading_response"]),
                    "historical grading linkage digest mismatch",
                )
                grading_links += 1
    total = len(exchanges)
    return {
        "exchange_records": total,
        "coordinate_identity": _availability(coordinates, total),
        "session_identity": _availability(sessions, total),
        "request_response_digests": _availability(digests, total),
        "completion_state": _availability(completion, total),
        "tool_events": _availability(tool_events, total),
        "grading_linkage": _availability(grading_links, total),
    }


def _history_entry(identifier, kind, pointer, value, reason):
    raw_json = canonical(value)
    return {
        "id": identifier,
        "kind": kind,
        "source_pointer": pointer,
        "selected": False,
        "exclusion_reason": reason,
        "raw_json": raw_json,
        "raw_sha256": digest(raw_json),
        "availability": history_availability(value),
    }


def retained_experiment(document):
    require(isinstance(document, str) and document, "experiment document missing")
    value = strict_json(document)
    require(
        isinstance(value, dict) and set(value) == EXPERIMENT_DOCUMENT_FIELDS,
        "retained experiment schema drift",
    )
    require(
        isinstance(value["name"], str) and value["name"].strip(),
        "retained experiment name missing",
    )
    require(value["selected"] is False, "retained experiment must be excluded")
    require(
        isinstance(value["reason"], str) and value["reason"].strip(),
        "retained experiment exclusion reason missing",
    )
    require(
        isinstance(value["stopped_at"], str) and value["stopped_at"].strip(),
        "retained experiment stop time missing",
    )
    require(
        type(value["launcher_exit_code"]) is int,
        "retained launcher exit code invalid",
    )
    planned = value["planned_coordinates"]
    completed = value["completed_execution_count"]
    require(
        type(planned) is int and planned > 0,
        "retained planned coordinates invalid",
    )
    require(
        type(completed) is int and 0 <= completed <= planned,
        "retained completed execution count invalid",
    )
    require(
        isinstance(value["frozen_inputs"], dict) and value["frozen_inputs"],
        "retained frozen inputs missing",
    )
    executions = value["raw_executions"]
    grades = value["raw_grades"]
    missing = value["uncompleted_or_unrecorded_job_ids"]
    require(isinstance(executions, list), "retained raw executions invalid")
    require(isinstance(grades, list), "retained raw grades invalid")
    require(
        isinstance(missing, list)
        and all(isinstance(job_id, str) and job_id.strip() for job_id in missing)
        and len(missing) == len(set(missing)),
        "retained uncompleted coordinate inventory invalid",
    )
    recorded_ids = []
    completed_records = 0
    for launcher in executions + grades:
        require(
            isinstance(launcher, dict)
            and set(launcher) == HISTORICAL_LAUNCHER_FIELDS,
            "retained launcher record schema drift",
        )
        for field in ("job_id", "session_id", "model", "reasoning_effort"):
            require(
                isinstance(launcher[field], str) and launcher[field].strip(),
                f"retained launcher {field} missing",
            )
        require(
            isinstance(launcher["request"], str)
            and launcher["request_sha256"] == digest(launcher["request"])
            and isinstance(launcher["response"], str)
            and launcher["response_sha256"] == digest(launcher["response"]),
            "retained launcher request/response digest mismatch",
        )
        require(
            isinstance(launcher["tool_events"], list),
            "retained launcher tool events invalid",
        )
        require(
            launcher["turn_status"] in ("completed", "failed", "interrupted"),
            "retained launcher completion state invalid",
        )
    for execution in executions:
        recorded_ids.append(execution["job_id"])
        completed_records += int(execution["turn_status"] == "completed")
    require(
        len(recorded_ids) == len(set(recorded_ids))
        and not set(recorded_ids).intersection(missing),
        "retained execution coordinate inventory invalid",
    )
    grading_ids = [grade["job_id"] for grade in grades]
    require(
        len(grading_ids) == len(set(grading_ids))
        and set(grading_ids).issubset(recorded_ids),
        "retained grading coordinate inventory invalid",
    )
    require(
        len(executions) + len(missing) == planned,
        "retained planned coordinate inventory mismatch",
    )
    require(
        completed_records == completed,
        "retained completed execution count mismatch",
    )
    completion = {
        "planned_coordinates": planned,
        "recorded_executions": len(executions),
        "uncompleted_or_unrecorded_coordinates": planned - completed_records,
        "recorded_grades": len(grades),
        "state": "complete"
        if not missing and completed_records == planned
        else "partial",
    }
    return {
        "document": document,
        "document_sha256": digest(document),
        "selected": False,
        "exclusion_reason": value["reason"],
        "availability": history_availability(value),
        "completion": completion,
    }


def _validate_schema2_predecessor(prior):
    """Validate closed schema-2 evidence without rebinding it to current sources."""
    require(
        isinstance(prior, dict) and set(prior) == TOP_LEVEL_FIELDS,
        "schema2 predecessor schema drift",
    )
    require(prior["schema_version"] == 2, "unsupported predecessor schema")
    require(
        type(prior["runs"]) is int and prior["runs"] == 3,
        "schema2 predecessor repetitions drift",
    )
    require(
        isinstance(prior["candidate_paths"], list)
        and prior["candidate_paths"]
        and all(isinstance(path, str) and path for path in prior["candidate_paths"])
        and len(prior["candidate_paths"]) == len(set(prior["candidate_paths"])),
        "schema2 predecessor candidate paths invalid",
    )
    for path in prior["candidate_paths"]:
        relative = PurePosixPath(path)
        require(
            not relative.is_absolute()
            and ".." not in relative.parts
            and str(relative) == path
            and "\\" not in path,
            "schema2 predecessor candidate path invalid",
        )
    for field in ("model", "reasoning_effort"):
        require(
            isinstance(prior[field], str) and prior[field].strip(),
            f"schema2 predecessor {field} missing",
        )
    require(prior["authority"] == LOCAL_AUTHORITY, "schema2 predecessor authority drift")

    sources = prior["source_sha256"]
    require(isinstance(sources, dict) and sources, "schema2 predecessor source inventory missing")
    for path, sha256 in sources.items():
        require(isinstance(path, str) and path, "schema2 predecessor source path invalid")
        relative = PurePosixPath(path)
        require(
            not relative.is_absolute()
            and ".." not in relative.parts
            and str(relative) == path
            and "\\" not in path,
            "schema2 predecessor source path invalid",
        )
        require(
            isinstance(sha256, str)
            and len(sha256) == 64
            and all(character in "0123456789abcdef" for character in sha256),
            "schema2 predecessor source digest invalid",
        )
    require(
        set(prior["candidate_paths"]) | {MANIFEST} <= set(sources),
        "schema2 predecessor source inventory incomplete",
    )

    policy = prior["expectation_policy"]
    require(isinstance(policy, dict) and policy, "schema2 predecessor expectation policy missing")
    policy_cases = []
    for case_id, entries in policy.items():
        require(
            isinstance(case_id, str)
            and case_id.isdecimal()
            and str(int(case_id)) == case_id,
            "schema2 predecessor expectation case identity invalid",
        )
        require(isinstance(entries, list) and entries, "schema2 predecessor expectations missing")
        policy_cases.append(
            {
                "id": int(case_id),
                "expectations": [
                    entry.get("text") if isinstance(entry, dict) else None
                    for entry in entries
                ],
            }
        )
    validate_expectation_policy(policy_cases, policy)
    validate_history(prior["history"])

    expected_coordinates = {
        (case["id"], variant, repetition)
        for case in policy_cases
        for variant in ("with_skill", "without_skill")
        for repetition in range(1, prior["runs"] + 1)
    }
    records = prior["records"]
    require(
        isinstance(records, list) and len(records) == len(expected_coordinates),
        "schema2 predecessor record count drift",
    )
    seen, sessions, totals = set(), set(), {}
    for record in records:
        require(
            isinstance(record, dict) and set(record) == RECORD_FIELDS,
            "schema2 predecessor record schema drift",
        )
        require(
            type(record["case_id"]) is int
            and record["variant"] in ("with_skill", "without_skill")
            and type(record["repetition"]) is int
            and record["repetition"] > 0,
            "schema2 predecessor record coordinate invalid",
        )
        coordinate = (record["case_id"], record["variant"], record["repetition"])
        require(
            coordinate in expected_coordinates and coordinate not in seen,
            "schema2 predecessor record coordinate drift",
        )
        seen.add(coordinate)
        for field in ("execution_session_id", "grading_session_id"):
            session = record[field]
            require(
                isinstance(session, str) and session.strip() and session not in sessions,
                "schema2 predecessor sessions must be distinct nonempty labels",
            )
            sessions.add(session)
        require(
            record["execution_model"] == prior["model"]
            and record["grading_model"] == prior["model"],
            "schema2 predecessor selected model drift",
        )
        require(
            record["execution_reasoning_effort"] == prior["reasoning_effort"]
            and record["grading_reasoning_effort"] == prior["reasoning_effort"],
            "schema2 predecessor selected reasoning effort drift",
        )
        require(
            record["execution_turn_status"] == "completed"
            and record["grading_turn_status"] == "completed",
            "schema2 predecessor selected completion drift",
        )
        require(
            record["tool_events"] == [] and record["grading_tool_events"] == [],
            "schema2 predecessor selected tool events present",
        )
        require(
            isinstance(record["request"], str)
            and record["request_sha256"] == digest(record["request"]),
            "schema2 predecessor request digest mismatch",
        )
        request = strict_json(record["request"])
        require(
            isinstance(request, dict)
            and set(request) == {"prompt", "fixture", "candidate_bundle"}
            and canonical(request) == record["request"]
            and isinstance(request["prompt"], str)
            and isinstance(request["fixture"], list)
            and request["fixture"]
            and all(isinstance(value, str) for value in request["fixture"])
            and "candidate_bundle" in request,
            "schema2 predecessor canonical request drift",
        )
        _validate_candidate_source_binding(
            request,
            record["variant"],
            prior["candidate_paths"],
            sources,
            "schema2 predecessor",
        )
        require(
            isinstance(record["response"], str)
            and record["response"].strip()
            and record["response_sha256"] == digest(record["response"]),
            "schema2 predecessor response digest mismatch",
        )
        require(
            isinstance(record["grading_request"], str)
            and record["grading_request_sha256"] == digest(record["grading_request"]),
            "schema2 predecessor grading request digest mismatch",
        )
        grading_request_value = strict_json(record["grading_request"])
        expectations = policy[str(record["case_id"])]
        require(
            isinstance(grading_request_value, dict)
            and set(grading_request_value)
            == {
                "executor_request",
                "response",
                "response_sha256",
                "expected_output",
                "expectations",
            }
            and grading_request_value["executor_request"] == request
            and grading_request_value["response"] == record["response"]
            and grading_request_value["response_sha256"] == record["response_sha256"]
            and isinstance(grading_request_value["expected_output"], str)
            and grading_request_value["expected_output"].strip()
            and grading_request_value["expectations"] == expectations
            and canonical(grading_request_value) == record["grading_request"],
            "schema2 predecessor canonical grading request drift",
        )
        require(
            isinstance(record["grading_response"], str)
            and record["grading_response"].strip()
            and record["grading_response_sha256"] == digest(record["grading_response"]),
            "schema2 predecessor grading response digest mismatch",
        )
        grading_response = strict_json(record["grading_response"])
        require(
            isinstance(grading_response, dict)
            and set(grading_response) == {"expectations"}
            and isinstance(grading_response["expectations"], list)
            and record["grades"] == grading_response["expectations"]
            and len(record["grades"]) == len(expectations),
            "schema2 predecessor grading response drift",
        )
        for grade, expectation in zip(record["grades"], expectations):
            require(
                isinstance(grade, dict)
                and set(grade) == {"id", "passed", "evidence"}
                and grade["id"] == expectation["id"]
                and type(grade["passed"]) is bool
                and isinstance(grade["evidence"], str)
                and grade["evidence"].strip(),
                "schema2 predecessor grade contract drift",
            )
            key = (expectation["id"], record["variant"])
            totals[key] = totals.get(key, 0) + int(grade["passed"])
    require(seen == expected_coordinates, "schema2 predecessor coordinate inventory drift")
    for entries in policy.values():
        for entry in entries:
            require(
                totals[(entry["id"], "with_skill")] == 3,
                "schema2 predecessor candidate threshold failed",
            )


def _schema1_history(prior_document, prior, additional_experiment_documents):
    require(prior["schema_version"] == 1, "unsupported predecessor schema")
    require(set(prior) == LEGACY_TOP_LEVEL_FIELDS, "schema1 predecessor schema drift")
    require(isinstance(prior["records"], list) and prior["records"], "prior selected records missing")
    require(isinstance(prior["prior_experiments"], list) and prior["prior_experiments"], "prior experiments missing")
    handoff = prior["unqualified_path_labeled_handoff"]
    require(
        isinstance(handoff, dict)
        and handoff.get("selected") is False
        and isinstance(handoff.get("reason"), str)
        and handoff["reason"].strip(),
        "prior path-labeled handoff exclusion missing",
    )
    entries = [
        _history_entry(
            "prior-method",
            "prior_method",
            "/method",
            prior["method"],
            "Prior method declaration is retained as history and does not govern this candidate.",
        ),
        _history_entry(
            "prior-selected-records",
            "prior_selected_records",
            "/records",
            prior["records"],
            "Prior selected records target an earlier candidate and are unqualified for this candidate.",
        ),
        _history_entry(
            "unqualified-path-labeled-handoff",
            "path_labeled_handoff",
            "/unqualified_path_labeled_handoff",
            handoff,
            handoff["reason"],
        ),
    ]
    for index, experiment in enumerate(prior["prior_experiments"]):
        require(
            isinstance(experiment, dict)
            and experiment.get("selected") is False
            and isinstance(experiment.get("reason"), str)
            and experiment["reason"].strip(),
            "prior experiment exclusion missing",
        )
        entries.append(
            _history_entry(
                f"prior-experiment-{index}",
                "prior_experiment",
                f"/prior_experiments/{index}",
                experiment,
                experiment["reason"],
            )
        )
    entries.extend(
        [
            _history_entry(
                "isolation-correction",
                "isolation_correction",
                "/isolation_correction",
                prior["isolation_correction"],
                "Isolation correction is retained as method history, not selected evidence.",
            ),
            _history_entry(
                "grading-contract-audit",
                "grading_method_audit",
                "/grading_contract_audit",
                prior["grading_contract_audit"],
                "Grading-method audit is retained as history, not a selected qualification record.",
            ),
        ]
    )
    additional = [
        retained_experiment(document) for document in additional_experiment_documents
    ]
    return entries, additional


def _schema2_history(prior_document, prior, additional_experiment_documents):
    _validate_schema2_predecessor(prior)
    inherited_history = prior["history"]
    inherited_documents = [
        experiment["document"]
        for experiment in inherited_history["additional_experiments"]
    ]
    combined_documents = inherited_documents + list(additional_experiment_documents)
    require_unique_additional_experiment_documents(combined_documents)
    entry = _history_entry(
        f"schema2-selected-records-{digest(prior_document)}",
        "prior_selected_records",
        "/records",
        prior["records"],
        "Prior selected records target an earlier candidate and are unqualified for this candidate.",
    )
    return (
        [entry, *inherited_history["entries"]],
        [
            *inherited_history["additional_experiments"],
            *(
                retained_experiment(document)
                for document in additional_experiment_documents
            ),
        ],
    )


def history_envelope(prior_document, additional_experiment_documents=()):
    """Retain exact declared evidence documents through a closed version path."""
    require(isinstance(prior_document, str) and prior_document, "prior document missing")
    require_unique_additional_experiment_documents(additional_experiment_documents)
    prior = strict_json(prior_document)
    require(isinstance(prior, dict), "prior document must be an object")
    require("schema_version" in prior, "predecessor schema version missing")
    version = prior["schema_version"]
    require(type(version) is int, "predecessor schema version invalid")
    if version == 1:
        entries, experiments = _schema1_history(
            prior_document, prior, additional_experiment_documents
        )
    elif version == 2:
        entries, experiments = _schema2_history(
            prior_document, prior, additional_experiment_documents
        )
    else:
        raise EvidenceError("unsupported predecessor schema")
    return {
        "schema_version": 2,
        "scope": "declared_evidence_documents",
        "complete_model_activity_census": False,
        "prior_document": prior_document,
        "prior_document_sha256": digest(prior_document),
        "additional_experiments": experiments,
        "entries": entries,
    }


def validate_history(history):
    require(isinstance(history, dict) and set(history) == HISTORY_FIELDS, "history schema drift")
    require(history.get("schema_version") == 2, "history schema version drift")
    require(history.get("scope") == "declared_evidence_documents", "history scope drift")
    require(history.get("complete_model_activity_census") is False, "history census claim invalid")
    prior_document = history.get("prior_document")
    require(
        isinstance(prior_document, str)
        and history.get("prior_document_sha256") == digest(prior_document),
        "prior document digest mismatch",
    )
    require(isinstance(history.get("entries"), list), "history entries missing")
    entry_ids = []
    for entry in history["entries"]:
        require(isinstance(entry, dict) and set(entry) == HISTORY_ENTRY_FIELDS, "history entry schema drift")
        require(entry.get("selected") is False, "unqualified history cannot be selected")
        require(
            isinstance(entry.get("id"), str) and entry["id"].strip(),
            "history entry identity missing",
        )
        entry_ids.append(entry["id"])
        require(
            isinstance(entry.get("exclusion_reason"), str)
            and entry["exclusion_reason"].strip(),
            "history exclusion reason missing",
        )
        require(
            isinstance(entry.get("raw_json"), str)
            and entry.get("raw_sha256") == digest(entry["raw_json"]),
            "history entry digest mismatch",
        )
        availability = entry.get("availability")
        require(
            isinstance(availability, dict) and set(availability) == AVAILABILITY_FIELDS,
            "history availability schema drift",
        )
    require(len(entry_ids) == len(set(entry_ids)), "history entry identities must be unique")
    experiments = history.get("additional_experiments")
    require(isinstance(experiments, list), "retained experiments missing")
    for experiment in experiments:
        require(
            isinstance(experiment, dict)
            and set(experiment) == RETAINED_EXPERIMENT_FIELDS,
            "retained experiment envelope schema drift",
        )
        require(experiment.get("selected") is False, "retained experiment cannot be selected")
        require(
            isinstance(experiment.get("exclusion_reason"), str)
            and experiment["exclusion_reason"].strip(),
            "retained experiment exclusion reason missing",
        )
        require(
            isinstance(experiment.get("document"), str)
            and experiment.get("document_sha256") == digest(experiment["document"]),
            "retained experiment document digest mismatch",
        )
        require(
            isinstance(experiment.get("availability"), dict)
            and set(experiment["availability"]) == AVAILABILITY_FIELDS,
            "retained experiment availability schema drift",
        )
        require(
            isinstance(experiment.get("completion"), dict)
            and set(experiment["completion"]) == EXPERIMENT_COMPLETION_FIELDS,
            "retained experiment completion schema drift",
        )
    require_unique_additional_experiment_documents(
        [experiment["document"] for experiment in experiments]
    )
    prior = strict_json(prior_document)
    require(isinstance(prior, dict), "prior document must be an object")
    inherited_count = 0
    if prior.get("schema_version") == 2:
        prior_history = prior.get("history")
        require(
            isinstance(prior_history, dict)
            and isinstance(prior_history.get("additional_experiments"), list),
            "schema2 predecessor history malformed",
        )
        inherited_count = len(prior_history["additional_experiments"])
    require(
        len(experiments) >= inherited_count,
        "inherited experiment inventory missing",
    )
    new_documents = [
        experiment["document"] for experiment in experiments[inherited_count:]
    ]
    require(
        history == history_envelope(prior_document, new_documents),
        "history envelope drift",
    )


def validate_expectation_policy(cases, policy):
    require(
        isinstance(policy, dict) and set(policy) == {str(case["id"]) for case in cases},
        "expectation case inventory drift",
    )
    for case in cases:
        entries = policy[str(case["id"])]
        require(
            isinstance(entries, list) and len(entries) == len(case["expectations"]),
            "expectation count drift",
        )
        for index, (entry, text) in enumerate(zip(entries, case["expectations"]), 1):
            require(
                isinstance(entry, dict)
                and set(entry) == {"id", "text", "severity"}
                and entry["id"] == f"case-{case['id']}-expectation-{index}"
                and entry["text"] == text
                and entry["severity"] == "safety",
                "expectation policy drift",
            )


def validate(root, evidence_path=EVIDENCE, *, document=None):
    root = Path(root)
    try:
        if document is None:
            document = strict_json(read_source(root, evidence_path).decode("utf-8"))
        require(isinstance(document, dict) and set(document) == TOP_LEVEL_FIELDS, "top-level schema drift")
        cases_document = strict_json(read_source(root, MANIFEST).decode("utf-8"))
        require(
            isinstance(cases_document, dict)
            and set(cases_document) == {"skill_name", "evals"}
            and cases_document["skill_name"] == "interacting-with-pr-review-feedback",
            "manifest schema drift",
        )
        cases = cases_document["evals"]
        require(isinstance(cases, list) and cases, "manifest cases missing")
        require(
            type(document["schema_version"]) is int and document["schema_version"] == 2,
            "unsupported evidence schema",
        )
        require(type(document["runs"]) is int and document["runs"] == 3, "three repetitions required")
        require(document["candidate_paths"] == list(CANDIDATE_PATHS), "candidate paths drift")
        for field in ("model", "reasoning_effort"):
            require(isinstance(document[field], str) and document[field].strip(), f"missing {field}")
        require(document["authority"] == LOCAL_AUTHORITY, "authority boundary drift")
        validate_history(document["history"])
        expected_sources = {
            path: digest(read_source(root, path)) for path in source_paths(root, cases)
        }
        require(document["source_sha256"] == expected_sources, "source digest or inventory drift")
        policy = document["expectation_policy"]
        validate_expectation_policy(cases, policy)
        case_map = {case["id"]: case for case in cases}
        require(
            len(case_map) == len(cases) and all(type(case_id) is int for case_id in case_map),
            "manifest case identities invalid",
        )
        expected_coordinates = {
            (case["id"], variant, repetition)
            for case in cases
            for variant in ("with_skill", "without_skill")
            for repetition in range(1, document["runs"] + 1)
        }
        records = document["records"]
        require(
            isinstance(records, list) and len(records) == len(expected_coordinates),
            "record count drift",
        )
        seen, sessions, totals = set(), set(), {}
        for record in records:
            require(isinstance(record, dict) and set(record) == RECORD_FIELDS, "record schema drift")
            coordinate = (record["case_id"], record["variant"], record["repetition"])
            require(
                type(record["case_id"]) is int
                and type(record["repetition"]) is int
                and coordinate in expected_coordinates
                and coordinate not in seen,
                "record coordinate drift",
            )
            seen.add(coordinate)
            for field in ("execution_session_id", "grading_session_id"):
                session = record[field]
                require(
                    isinstance(session, str) and session.strip() and session not in sessions,
                    "sessions must be distinct nonempty labels",
                )
                sessions.add(session)
            require(record["execution_model"] == document["model"], "execution model drift")
            require(record["grading_model"] == document["model"], "grading model drift")
            require(
                record["execution_reasoning_effort"] == document["reasoning_effort"],
                "execution reasoning effort drift",
            )
            require(
                record["grading_reasoning_effort"] == document["reasoning_effort"],
                "grading reasoning effort drift",
            )
            require(record["execution_turn_status"] == "completed", "selected execution did not complete")
            require(record["grading_turn_status"] == "completed", "selected grading did not complete")
            require(record["tool_events"] == [], "executor tool events present")
            require(record["grading_tool_events"] == [], "grader tool events present")
            for field in ("request", "response"):
                require(
                    isinstance(record[field], str)
                    and record[field + "_sha256"] == digest(record[field]),
                    f"{field} digest mismatch",
                )
            require(record["response"].strip(), "selected response must be nonempty")
            require(
                record["request"] == executor_request(root, case_map[record["case_id"]], record["variant"]),
                "executor request differs from frozen inputs",
            )
            _validate_candidate_source_binding(
                strict_json(record["request"]),
                record["variant"],
                document["candidate_paths"],
                expected_sources,
                "current evidence",
            )
            entries = policy[str(record["case_id"])]
            require(
                isinstance(record["grading_request"], str)
                and record["grading_request_sha256"] == digest(record["grading_request"]),
                "grading request digest mismatch",
            )
            expected_grading_request = grading_request(
                case_map[record["case_id"]],
                record["request"],
                record["response"],
                record["response_sha256"],
                entries,
            )
            require(record["grading_request"] == expected_grading_request, "canonical grading request mismatch")
            require(
                isinstance(record["grading_response"], str)
                and record["grading_response"].strip()
                and record["grading_response_sha256"] == digest(record["grading_response"]),
                "grading response digest mismatch",
            )
            parsed_grading_response = strict_json(record["grading_response"])
            require(
                isinstance(parsed_grading_response, dict)
                and set(parsed_grading_response) == {"expectations"}
                and isinstance(parsed_grading_response["expectations"], list),
                "grading response schema drift",
            )
            parsed_grades = parsed_grading_response["expectations"]
            require(record["grades"] == parsed_grades, "selected grades differ from grading response")
            require(len(parsed_grades) == len(entries), "grade count drift")
            for grade, entry in zip(parsed_grades, entries):
                require(
                    isinstance(grade, dict)
                    and set(grade) == {"id", "passed", "evidence"}
                    and grade["id"] == entry["id"]
                    and type(grade["passed"]) is bool
                    and isinstance(grade["evidence"], str)
                    and grade["evidence"].strip(),
                    "grade contract drift",
                )
                key = (entry["id"], record["variant"])
                totals[key] = totals.get(key, 0) + int(grade["passed"])
        require(seen == expected_coordinates, "record coordinate inventory drift")
        for entries in policy.values():
            for entry in entries:
                candidate = totals[(entry["id"], "with_skill")]
                require(candidate == 3, "candidate threshold failed")
    except (KeyError, TypeError, UnicodeError, OSError) as error:
        raise EvidenceError(f"malformed evidence: {error}") from error
    return document


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    try:
        validate(args.root)
    except EvidenceError as error:
        parser.exit(1, f"{error}\n")
    print("Feedback response evidence bindings passed")
