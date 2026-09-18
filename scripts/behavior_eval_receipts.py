#!/usr/bin/env python3
"""Record and check ordinary behavior results; see docs/behavior-eval-receipts.md."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

POLICY_PATH = "release/behavior-eval-policy.json"
SCHEMA_PATH = "release/behavior-eval-receipt-v1.schema.json"
TOOL_PATH = "scripts/behavior_eval_receipts.py"


class ReceiptError(ValueError):
    """The supplied ordinary evidence cannot support the requested check."""


def require(condition, message):
    if not condition:
        raise ReceiptError(message)


def document_digest(value):
    """SHA-256 of UTF-8 JSON, sorted keys, compact separators, and no final newline."""
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode()
    ).hexdigest()


def read_json(content):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result

    def invalid_constant(_):
        raise ReceiptError("non-finite JSON number")

    try:
        return json.loads(
            content, object_pairs_hook=pairs, parse_constant=invalid_constant
        )
    except (ValueError, UnicodeError) as error:
        raise ReceiptError("invalid or duplicate-key JSON") from error


def validate(value, definition=None):
    """Validate the public receipt or a named input shape in its schema."""
    try:
        from jsonschema import Draft202012Validator
    except ImportError as error:
        raise ReceiptError(
            "jsonschema is required; use uv run --with jsonschema==4.26.0"
        ) from error
    schema = read_json((Path(__file__).resolve().parents[1] / SCHEMA_PATH).read_bytes())
    if definition:
        schema = {"$ref": "#/$defs/" + definition, "$defs": schema["$defs"]}
    require(
        not list(Draft202012Validator(schema).iter_errors(value)),
        f"{definition or 'receipt'} schema mismatch",
    )


def git(repository, *arguments):
    result = subprocess.run(
        ["git", *arguments], cwd=repository, capture_output=True, check=False
    )
    require(result.returncode == 0, "Git source observation failed")
    return result.stdout


def revision(repository, value):
    require(
        isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", value),
        "candidate must be a full commit identity",
    )
    require(
        git(repository, "rev-parse", "--verify", value + "^{commit}").decode().strip()
        == value,
        "candidate must name a commit",
    )
    return value


def relative_path(value):
    require(
        isinstance(value, str)
        and value
        and not any(ord(c) < 32 for c in value)
        and "\\" not in value,
        "expected a repository-relative path",
    )
    path = PurePosixPath(value)
    require(
        not path.is_absolute()
        and ".." not in path.parts
        and str(path) == value
        and value != ".",
        "expected a normalized repository-relative path",
    )
    return value


def source_bytes(repository, commit, path):
    return git(repository, "show", commit + ":" + relative_path(path))


def source_inventory(repository, commit):
    inventory = {}
    for record in git(repository, "ls-tree", "-rz", commit).split(b"\0"):
        if record:
            metadata, path = record.split(b"\t", 1)
            mode, kind, _ = metadata.decode().split()
            inventory[path.decode()] = (mode, kind)
    return inventory


def prepare(repository, candidate_revision, skill):
    """Freeze the caller's declared evaluation inputs at an existing source commit."""
    validate(skill, "skill")
    revision(repository, candidate_revision)
    validate(
        read_json(source_bytes(repository, candidate_revision, POLICY_PATH)), "policy"
    )
    prefix = f"plugins/{skill['plugin']}/skills/{skill['skill']}"
    inventory = source_inventory(repository, candidate_revision)
    paths = {path for path in inventory if path.startswith(prefix + "/")}
    require(prefix + "/SKILL.md" in paths, "skill source is absent")
    paths.update(
        [
            skill["content_lock"],
            skill["evals"],
            skill["trigger_evals"],
            POLICY_PATH,
            SCHEMA_PATH,
            TOOL_PATH,
        ]
    )
    paths.update(skill["dependencies"])
    paths.update(skill["shared_references"])
    parsed = corpus(
        repository, {"candidate_revision": candidate_revision, "skill": skill}
    )
    paths.update(parsed[2])
    inputs = {}
    for path in sorted(paths):
        relative_path(path)
        require(
            path in inventory
            and inventory[path] in (("100644", "blob"), ("100755", "blob")),
            "evaluation input must be a committed regular file",
        )
        inputs[path] = {
            "sha256": hashlib.sha256(
                source_bytes(repository, candidate_revision, path)
            ).hexdigest(),
            "mode": inventory[path][0],
        }
    return {
        "schema_version": 1,
        "candidate_revision": candidate_revision,
        "skill": skill,
        "inputs": inputs,
    }


def corpus(repository, snapshot):
    spec = snapshot["skill"]
    source = snapshot["candidate_revision"]
    document = read_json(source_bytes(repository, source, spec["evals"]))
    require(
        isinstance(document, dict)
        and document.get("skill_name") == spec["skill"]
        and isinstance(document.get("evals"), list)
        and document["evals"],
        "unsupported per-skill evaluation corpus",
    )
    cases, fixtures = {}, set()
    fixture_root = spec.get(
        "fixture_root", f"plugins/{spec['plugin']}/skills/{spec['skill']}"
    )
    relative_path(fixture_root)
    for case in document["evals"]:
        require(
            isinstance(case, dict) and type(case.get("id")) is int and case["id"] > 0,
            "corpus case must have a positive integer identity",
        )
        key = str(case["id"])
        require(key not in cases, "duplicate corpus case identity")
        expectations = case.get("expectations")
        require(
            isinstance(expectations, list) and expectations,
            "expectation coverage is absent",
        )
        seen = set()
        for expectation in expectations:
            require(
                isinstance(expectation, dict)
                and set(expectation) == {"id", "text", "severity"}
                and expectation["severity"] in ("safety", "quality"),
                "unsupported expectation: explicit safety/quality severity is required",
            )
            require(
                isinstance(expectation["id"], str)
                and re.fullmatch(
                    r"[a-zA-Z0-9][a-zA-Z0-9._:-]{0,159}", expectation["id"]
                )
                and expectation["id"] not in seen,
                "invalid or duplicate expectation identity",
            )
            require(
                isinstance(expectation["text"], str) and expectation["text"].strip(),
                "expectation text is absent",
            )
            seen.add(expectation["id"])
        require(
            isinstance(case.get("fixture_paths"), list), "unsupported fixture inventory"
        )
        for path in case["fixture_paths"]:
            fixtures.add(fixture_root + "/" + relative_path(path))
        cases[key] = expectations
    triggers = read_json(source_bytes(repository, source, spec["trigger_evals"]))
    require(
        isinstance(triggers, list) and triggers,
        "declared trigger corpus must contain cases",
    )
    queries = set()
    for item in triggers:
        require(
            isinstance(item, dict)
            and set(item) == {"query", "should_trigger"}
            and isinstance(item["query"], str)
            and item["query"].strip()
            and item["query"] not in queries
            and type(item["should_trigger"]) is bool,
            "unsupported or duplicate trigger case",
        )
        queries.add(item["query"])
    return (
        cases,
        {str(i): item["should_trigger"] for i, item in enumerate(triggers, 1)},
        fixtures,
    )


def local_bytes(path):
    try:
        return Path(path).read_bytes()
    except OSError as error:
        raise ReceiptError("local evidence artifact unavailable") from error


def artifact_bytes(directory, relative):
    path = Path(directory) / relative_path(relative)
    require(
        path.resolve().is_relative_to(Path(directory).resolve()),
        "artifact must remain inside the private result directory",
    )
    return local_bytes(path)


def check_coordinates(runs, triggers, cases, expected_triggers):
    required = {(case_id, repetition) for case_id in cases for repetition in (1, 2, 3)}
    coordinates = [(run["case_id"], run["repetition"]) for run in runs]
    require(
        len(coordinates) == len(required) and set(coordinates) == required,
        "run coverage must include each case at repetitions 1, 2, and 3 exactly once",
    )
    require(
        len(triggers) == len(expected_triggers)
        and {item["case_id"] for item in triggers} == set(expected_triggers),
        "trigger coverage differs from the corpus",
    )


def produce(repository, snapshot, results_path):
    """Project local result artifacts into a public receipt without their private paths."""
    validate(snapshot, "snapshot")
    require(
        snapshot
        == prepare(repository, snapshot["candidate_revision"], snapshot["skill"]),
        "evaluation input snapshot differs from source",
    )
    results_path = Path(results_path)
    raw = local_bytes(results_path)
    results = read_json(raw)
    validate(results, "results")
    require(
        results["snapshot_sha256"] == document_digest(snapshot),
        "results name another snapshot",
    )
    cases, expected_triggers, _ = corpus(repository, snapshot)
    check_coordinates(results["runs"], results["triggers"], cases, expected_triggers)
    runs = []
    for run in results["runs"]:
        output = artifact_bytes(results_path.parent, run["executor_output"])
        grading = artifact_bytes(results_path.parent, run["grading"])
        execution = read_json(output)
        validate(execution, "execution")
        require(
            execution["snapshot_sha256"] == results["snapshot_sha256"]
            and execution["case_id"] == run["case_id"]
            and execution["repetition"] == run["repetition"]
            and execution["model_id"] == results["executor_model_id"],
            "executor artifact belongs to another evaluation coordinate",
        )
        grading_document = read_json(grading)
        validate(grading_document, "grading")
        require(
            grading_document["snapshot_sha256"] == results["snapshot_sha256"]
            and grading_document["case_id"] == run["case_id"]
            and grading_document["repetition"] == run["repetition"]
            and grading_document["model_id"] == results["grader_model_id"]
            and grading_document["executor_output_sha256"]
            == hashlib.sha256(output).hexdigest(),
            "grading artifact belongs to another executor output",
        )
        observed_grades = grading_document["expectations"]
        expected_ids = {item["id"] for item in cases[run["case_id"]]}
        require(
            len(observed_grades) == len(expected_ids)
            and {item["id"] for item in observed_grades} == expected_ids,
            "grading expectation coverage differs from the corpus",
        )
        grades = {item["id"]: item["passed"] for item in observed_grades}
        expectations = [
            {
                "id": item["id"],
                "severity": item["severity"],
                "passed": grades[item["id"]],
            }
            for item in cases[run["case_id"]]
        ]
        runs.append(
            {
                "case_id": run["case_id"],
                "repetition": run["repetition"],
                "expectations": expectations,
                "executor_output_sha256": hashlib.sha256(output).hexdigest(),
                "grading_sha256": hashlib.sha256(grading).hexdigest(),
            }
        )
    triggers = []
    for item in results["triggers"]:
        observed = artifact_bytes(results_path.parent, item["observation"])
        observation = read_json(observed)
        validate(observation, "triggerObservation")
        require(
            observation["snapshot_sha256"] == results["snapshot_sha256"]
            and observation["case_id"] == item["case_id"]
            and observation["model_id"] == results["executor_model_id"],
            "trigger artifact belongs to another evaluation coordinate",
        )
        triggers.append(
            {
                "case_id": item["case_id"],
                "expected": expected_triggers[item["case_id"]],
                "triggered": observation["triggered"],
                "observation_kind": observation["observation_kind"],
                "observation_sha256": hashlib.sha256(observed).hexdigest(),
            }
        )
    receipt = {
        "schema_version": 1,
        "kind": "evaluation",
        "candidate_revision": snapshot["candidate_revision"],
        "snapshot": snapshot,
        "executor_model_id": results["executor_model_id"],
        "grader_model_id": results["grader_model_id"],
        "runs_per_case": 3,
        "runs": runs,
        "triggers": triggers,
        "private_evidence": {"manifest_sha256": hashlib.sha256(raw).hexdigest()},
        "attestation": None,
    }
    validate(receipt)
    evaluate(repository, receipt)
    return receipt


def evaluate(repository, receipt):
    """Recompute coverage and thresholds without trusting a stored overall verdict."""
    cases, expected_triggers, _ = corpus(repository, receipt["snapshot"])
    policy = read_json(
        source_bytes(repository, receipt["candidate_revision"], POLICY_PATH)
    )
    check_coordinates(receipt["runs"], receipt["triggers"], cases, expected_triggers)
    counts = {
        (case_id, item["id"]): 0 for case_id, items in cases.items() for item in items
    }
    for run in receipt["runs"]:
        expected = {item["id"]: item["severity"] for item in cases[run["case_id"]]}
        grades = run["expectations"]
        require(
            len(grades) == len(expected)
            and {item["id"] for item in grades} == set(expected),
            "expectation coverage differs from the corpus",
        )
        for grade in grades:
            require(
                grade["severity"] == expected[grade["id"]]
                and type(grade["passed"]) is bool,
                "grade severity or Boolean result differs from the corpus contract",
            )
            counts[run["case_id"], grade["id"]] += grade["passed"]
    threshold_passed = all(
        counts[case_id, item["id"]] >= policy[item["severity"]]["required_passes"]
        for case_id, items in cases.items()
        for item in items
    )
    triggers = receipt["triggers"]
    for item in triggers:
        require(
            type(item["expected"]) is bool
            and type(item["triggered"]) is bool
            and item["expected"] == expected_triggers[item["case_id"]],
            "trigger expectation differs from corpus",
        )
    correct = sum(item["expected"] == item["triggered"] for item in triggers)
    passed = threshold_passed and correct == len(triggers)
    return {
        "status": "pass" if passed else "fail",
        "reason": "threshold satisfied" if passed else "threshold failed",
        "trigger_precision": {"correct": correct, "total": len(triggers)},
    }


def check(repository, request, receipts):
    """Check declared changed skills at the receipt-containing candidate revision."""
    validate(request, "request")
    revision(repository, request["base_revision"])
    revision(repository, request["candidate_revision"])
    require(
        request.get("inventory_complete") is True,
        "complete caller-owned skill inventory is required",
    )
    keys = [spec["plugin"] + "/" + spec["skill"] for spec in request["skills"]]
    require(len(keys) == len(set(keys)), "duplicate skill inventory entry")
    require(
        set(request["changed_skills"]) <= set(keys),
        "changed skill is absent from the declared inventory",
    )
    changed = set(
        git(
            repository,
            "diff",
            "--name-only",
            "-z",
            "--no-renames",
            request["base_revision"],
            request["candidate_revision"],
            "--",
        )
        .decode()
        .split("\0")
    ) - {""}
    results = []
    for spec in request["skills"]:
        key = spec["plugin"] + "/" + spec["skill"]
        prefix = f"plugins/{spec['plugin']}/skills/{spec['skill']}/"
        required_paths = {
            spec["content_lock"],
            spec["evals"],
            spec["trigger_evals"],
            POLICY_PATH,
            SCHEMA_PATH,
            TOOL_PATH,
            *spec["dependencies"],
            *spec["shared_references"],
        }
        require(
            spec.get("closure_complete") is True,
            "complete caller-owned dependency closure is required",
        )
        source_error = None
        try:
            _, _, fixtures = corpus(
                repository,
                {"candidate_revision": request["candidate_revision"], "skill": spec},
            )
            required_paths.update(fixtures)
        except ReceiptError as error:
            source_error = str(error)
        if (
            source_error is None
            and key not in request["changed_skills"]
            and not any(
                path.startswith(prefix) or path in required_paths for path in changed
            )
        ):
            continue
        try:
            require(source_error is None, source_error)
            require(key in receipts, "receipt missing")
            receipt = receipts[key]
            validate(receipt)
            require(
                receipt["snapshot"]["skill"] == spec,
                "stale or wrong-skill receipt descriptor",
            )
            require(
                receipt["candidate_revision"]
                == receipt["snapshot"]["candidate_revision"],
                "receipt revision differs from its evaluated snapshot",
            )
            source = receipt["candidate_revision"]
            git(
                repository,
                "merge-base",
                "--is-ancestor",
                source,
                request["candidate_revision"],
            )
            observed = prepare(repository, source, spec)
            current = prepare(repository, request["candidate_revision"], spec)
            require(
                receipt["snapshot"] == observed,
                "receipt snapshot differs from evaluated source",
            )
            require(
                observed["inputs"] == current["inputs"], "stale evaluated input closure"
            )
            if receipt["kind"] == "waiver":
                result = {
                    "status": "waiver-pending",
                    "operator_authority_verified": False,
                    "expiry_verified": False,
                    "reason": "separate operator decision and next-release expiry verification required",
                    "waiver_receipt_sha256": document_digest(receipt),
                }
            else:
                result = evaluate(repository, receipt)
            result["evaluated_revision"] = source
            result["receipt_sha256"] = document_digest(receipt)
        except ReceiptError as error:
            result = {"status": "fail", "reason": str(error)}
        results.append({"skill": key, **result})
    return {
        "status": (
            "not-required"
            if not results
            else "pass"
            if all(item["status"] == "pass" for item in results)
            else "fail"
        ),
        "coverage_basis": "caller-declared-complete",
        "candidate_revision": request["candidate_revision"],
        "skills": results,
    }


class _ReceiptFiles(dict):
    """Load only receipts selected by the check; unrelated evidence is a no-op."""

    def __getitem__(self, key):
        return read_json(local_bytes(super().__getitem__(key)))


def main(argv=None):
    """Run the local JSON adapter; no subcommand executes evaluations."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    commands = parser.add_subparsers(dest="command", required=True)
    preparation = commands.add_parser(
        "prepare", help="freeze declared committed evaluation inputs"
    )
    preparation.add_argument("--revision", required=True)
    preparation.add_argument("--skill-spec", type=Path, required=True)
    production = commands.add_parser(
        "produce", help="project actual local result artifacts"
    )
    production.add_argument("--snapshot", type=Path, required=True)
    production.add_argument("--results", type=Path, required=True)
    checking = commands.add_parser(
        "check", help="check supplied receipts against a candidate"
    )
    checking.add_argument("--request", type=Path, required=True)
    checking.add_argument("--receipts", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(
                args.repository, args.revision, read_json(args.skill_spec.read_bytes())
            )
        elif args.command == "produce":
            result = produce(
                args.repository, read_json(args.snapshot.read_bytes()), args.results
            )
        else:
            request = read_json(args.request.read_bytes())
            validate(request, "request")
            supplied = _ReceiptFiles()
            for spec in request["skills"]:
                path = args.receipts / spec["plugin"] / (spec["skill"] + ".json")
                if path.exists():
                    supplied[spec["plugin"] + "/" + spec["skill"]] = path
            result = check(args.repository, request, supplied)
        print(
            json.dumps(
                result, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False
            )
        )
        return 1 if args.command == "check" and result["status"] == "fail" else 0
    except ReceiptError as error:
        print(json.dumps({"status": "error", "reason": str(error)}))
        return 2
    except OSError:
        print(
            json.dumps(
                {
                    "status": "error",
                    "reason": "local input or Git executable unavailable",
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
