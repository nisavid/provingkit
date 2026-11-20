#!/usr/bin/env python3
"""Prepare committed feedback-response inputs without starting model sessions."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import io
import json
import re
import stat
import tarfile
import tempfile
import uuid
from pathlib import Path, PurePosixPath

import evidence_transport as transport
import validate_feedback_response_evidence as evidence


ROOT = Path(__file__).resolve().parents[1]
PROCESSING_PATHS = (
    "scripts/run_feedback_response_eval.py",
    "scripts/validate_feedback_response_evidence.py",
    "scripts/evidence_transport.py",
    "docs/feedback-response-evaluation.md",
)
RECORD_PATH = "preparation.json"
OBJECT_ID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")


class PreparationError(ValueError):
    """Preparation cannot establish the declared byte correspondence."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PreparationError(message)


def safe_path(value: str) -> str:
    path = transport.safe_relative_path(
        value, label="committed input", error_factory=PreparationError
    )
    require("\\" not in value and not any(ord(c) < 32 for c in value),
            "unsafe committed input path")
    return path.as_posix()


def git(repository: Path, *arguments: str) -> bytes:
    return transport.run_candidate_git(
        repository, list(arguments), error_factory=PreparationError,
        operation="read committed evaluation inputs",
    )


def matches(path: str, pattern: str) -> bool:
    """Match path components with the same recursive ** rule as Path.glob."""
    def walk(parts: tuple[str, ...], patterns: tuple[str, ...]) -> bool:
        if not patterns:
            return not parts
        if patterns[0] == "**":
            return walk(parts, patterns[1:]) or bool(parts and walk(parts[1:], patterns))
        return bool(parts and fnmatch.fnmatchcase(parts[0], patterns[0])
                    and walk(parts[1:], patterns[1:]))

    return walk(PurePosixPath(path).parts, PurePosixPath(pattern).parts)


def tree_entries(repository: Path, revision: str) -> dict[str, dict[str, str]]:
    result = {}
    for record in git(repository, "ls-tree", "-r", "-z", "--full-tree", revision).split(b"\0"):
        if not record:
            continue
        metadata, separator, encoded = record.partition(b"\t")
        fields = metadata.decode("ascii").split()
        require(separator == b"\t" and len(fields) == 3, "malformed committed tree")
        mode, kind, object_id = fields
        path = safe_path(encoded.decode("utf-8"))
        require(path not in result and OBJECT_ID.fullmatch(object_id),
                "ambiguous committed input")
        result[path] = {"mode": mode, "kind": kind, "object_id": object_id}
    return result


def cases_from(content: bytes) -> list[dict]:
    document = transport.strict_json_bytes(
        content, label="committed evaluation corpus", error_factory=PreparationError
    )
    require(isinstance(document, dict) and set(document) == {"skill_name", "evals"}
            and document["skill_name"] == "interacting-with-pr-review-feedback",
            "unsupported evaluation corpus")
    cases = document["evals"]
    require(isinstance(cases, list) and len(cases) == 13,
            "preparation requires the maintained thirteen cases")
    require(all(isinstance(case, dict) and type(case.get("id")) is int for case in cases)
            and {case["id"] for case in cases} == set(range(13)),
            "evaluation case coordinates are invalid")
    for case in cases:
        require(all(isinstance(case.get(key), str) and case[key]
                    for key in ("prompt", "expected_output")), "invalid evaluation text")
        for key in ("files", "expectations"):
            require(isinstance(case.get(key), list) and case[key]
                    and all(isinstance(value, str) and value for value in case[key]),
                    "invalid evaluation dependencies")
    return sorted(cases, key=lambda case: case["id"])


def committed_source(repository: Path, revision: str, export: Path):
    require(OBJECT_ID.fullmatch(revision), "source revision must be a full commit object ID")
    observed = git(repository, "rev-parse", "--verify", revision + "^{commit}").decode().strip()
    require(observed == revision, "source revision does not name that commit")
    tree = git(repository, "rev-parse", revision + "^{tree}").decode().strip()
    entries = tree_entries(repository, revision)
    manifest = entries.get(evidence.MANIFEST)
    require(manifest is not None and manifest["mode"] in {"100644", "100755"}
            and manifest["kind"] == "blob", "committed corpus is missing or unsafe")
    cases = cases_from(git(repository, "cat-file", "blob", manifest["object_id"]))
    selected = set(evidence.CANDIDATE_PATHS) | {evidence.MANIFEST}
    for case in cases:
        selected.update(safe_path("evals/mergecraft/skills/" + path) for path in case["files"])
    for pattern in evidence.SOURCE_GLOBS:
        matched = {path for path in entries if matches(path, pattern)
                   and "__pycache__" not in PurePosixPath(path).parts
                   and not path.endswith(".pyc")}
        require(matched, "empty mandatory committed source glob")
        selected.update(matched)
    for path in selected:
        safe_path(path)
        require(path in entries and entries[path]["mode"] in {"100644", "100755"}
                and entries[path]["kind"] == "blob", "committed input is missing or unsafe")
    archive = git(repository, "archive", "--format=tar", revision, "--", *sorted(selected))
    contents = {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as source:
        for member in source:
            path = safe_path(member.name.rstrip("/") if member.isdir() else member.name)
            if member.isdir():
                require(any(name.startswith(path + "/") for name in selected),
                        "unexpected exported directory")
                continue
            require(member.isfile() and path in selected and path not in contents,
                    "unexpected or unsafe exported input")
            require(bool(member.mode & 0o111) == (entries[path]["mode"] == "100755"),
                    "exported executable mode differs from committed mode")
            stream = source.extractfile(member)
            require(stream is not None, "exported input is unreadable")
            content = stream.read()
            header = f"blob {len(content)}\0".encode("ascii")
            algorithm = "sha1" if len(entries[path]["object_id"]) == 40 else "sha256"
            require(hashlib.new(algorithm, header + content).hexdigest() == entries[path]["object_id"],
                    "exported bytes differ from committed blob")
            contents[path] = content
            target = export / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            target.chmod(0o755 if entries[path]["mode"] == "100755" else 0o644)
    require(set(contents) == selected, "committed export inventory is incomplete")
    require(evidence.source_paths(export, cases) == sorted(selected),
            "constructor source inventory differs from committed export")
    require(cases_from(evidence.read_source(export, evidence.MANIFEST)) == cases,
            "exported corpus differs from selected corpus")
    return tree, cases, entries, contents


def preparation(repository: Path, revision: str):
    processing = {path: evidence.read_source(ROOT, path) for path in PROCESSING_PATHS}
    artifacts: dict[str, bytes] = {}

    def retain(content: bytes) -> dict:
        sha256 = evidence.digest(content)
        path = f"artifacts/{sha256}"
        artifacts[path] = content
        return {"path": path, "byte_count": len(content), "sha256": sha256}

    with tempfile.TemporaryDirectory(prefix="feedback-response-source-") as directory:
        export = Path(directory)
        tree, cases, entries, contents = committed_source(repository, revision, export)
        source_files = [
            {"path": path, "git_blob_id": entries[path]["object_id"],
             "git_mode": entries[path]["mode"], "artifact": retain(content)}
            for path, content in sorted(contents.items())
        ]
        slots = [
            {"case_id": case["id"], "variant": variant, "repetition": repetition,
             "state": "unstarted",
             "request": retain(evidence.executor_request(export, case, variant).encode("utf-8"))}
            for case in cases for variant in ("with_skill", "without_skill")
            for repetition in (1, 2, 3)
        ]
    processing_files = [{"path": path, "artifact": retain(content)}
                        for path, content in sorted(processing.items())]
    grading = {
        "constructor": "scripts/validate_feedback_response_evidence.py:grading_request",
        "cases": [{"case_id": case["id"], "expected_output": case["expected_output"],
                   "expectations": [
                       {"id": f"case-{case['id']}-expectation-{index}",
                        "text": text, "severity": "safety"}
                       for index, text in enumerate(case["expectations"], 1)]}
                  for case in cases],
    }
    record = {
        "schema_version": 1, "kind": "feedback-response-preparation",
        "source": {"commit": revision, "tree": tree, "files": source_files},
        "processing": {"files": processing_files},
        "candidate_paths": list(evidence.CANDIDATE_PATHS),
        "slots": slots, "grading_dependencies": retain(evidence.canonical(grading).encode("utf-8")),
    }
    record["preparation_id"] = evidence.digest(evidence.canonical(record))
    require(all(evidence.read_source(ROOT, path) == content for path, content in processing.items()),
            "processing inputs changed during preparation")
    return record, artifacts, processing


def reference(content: bytes, path: str) -> dict:
    return {"path": path, "byte_count": len(content), "sha256": evidence.digest(content)}


def verify_bytes(output: Path, path: str, content: bytes) -> None:
    target = transport.safe_regular_file(output, path, label="retained artifact",
                                         error_factory=PreparationError)
    require(stat.S_IMODE(target.stat().st_mode) == 0o600,
            "retained artifact permissions differ from private mode 0600")
    require(target.read_bytes() == content, "retained artifact bytes differ")


def check_invocations(output: Path) -> None:
    directory = output / "invocations"
    require(not directory.is_symlink(), "unsafe invocation history")
    if not directory.exists():
        return
    require(directory.is_dir(), "unsafe invocation history")
    for invocation in directory.iterdir():
        require(invocation.is_dir() and not invocation.is_symlink(), "unsafe invocation history")
        require({path.name for path in invocation.iterdir()} == {"started.json", "complete.json"},
                "an earlier invocation is incomplete or indeterminate; use a new output directory")
        for name in ("started.json", "complete.json"):
            target = transport.safe_regular_file(
                output, str((invocation / name).relative_to(output)),
                label="invocation history", error_factory=PreparationError,
            )
            require(stat.S_IMODE(target.stat().st_mode) == 0o600,
                    "invocation history permissions differ from private mode 0600")
        started = transport.read_strict_json(invocation / "started.json", label="invocation start",
                                              error_factory=PreparationError)
        complete = transport.read_strict_json(invocation / "complete.json", label="invocation result",
                                               error_factory=PreparationError)
        require(isinstance(started, dict) and isinstance(complete, dict)
                and started.get("status") == "started" and complete.get("status") == "complete"
                and {**started, "status": "complete"} == complete
                and started.get("invocation_id") == invocation.name,
                "retained invocation outcome is contradictory")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="retain 78 unstarted actor requests")
    prepare.add_argument("--repository", required=True, type=Path)
    prepare.add_argument("--source-revision", required=True)
    prepare.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    result = {
        "schema_version": 1, "kind": "feedback-response-preparation-invocation",
        "invocation_id": str(uuid.uuid4()), "status": "incomplete",
        "preparation_id": None, "record": None,
    }
    publishing_record = False
    output = None
    invocation_path = None
    try:
        record, artifacts, processing = preparation(args.repository, args.source_revision)
        content = (evidence.canonical(record) + "\n").encode("utf-8")
        result.update(preparation_id=record["preparation_id"], record=reference(content, RECORD_PATH))
        output = transport.lexical_absolute_path(args.output_dir)
        transport.prepare_private_directory(output, error_factory=PreparationError)
        check_invocations(output)
        invocation_path = output / "invocations" / result["invocation_id"]
        transport.frozen_no_replace_write(
            invocation_path / "started.json",
            evidence.canonical({**result, "status": "started"}).encode("utf-8"),
            error_factory=PreparationError,
        )
        for path, payload in sorted(artifacts.items()):
            transport.frozen_no_replace_write(output / path, payload, error_factory=PreparationError)
        for path, payload in artifacts.items():
            verify_bytes(output, path, payload)
        require(all(evidence.read_source(ROOT, path) == payload for path, payload in processing.items()),
                "processing inputs changed before publication")
        publishing_record = True
        transport.frozen_no_replace_write(output / RECORD_PATH, content, error_factory=PreparationError)
        verify_bytes(output, RECORD_PATH, content)
        for path, payload in artifacts.items():
            verify_bytes(output, path, payload)
        result["status"] = "complete"
        completion = evidence.canonical(result).encode("utf-8")
        transport.frozen_no_replace_write(invocation_path / "complete.json", completion,
                                           error_factory=PreparationError)
        verify_bytes(output, str((invocation_path / "complete.json").relative_to(output)), completion)
    except (PreparationError, evidence.EvidenceError, OSError, UnicodeError, tarfile.TarError) as error:
        result.update(status="indeterminate" if publishing_record else "incomplete", reason=str(error))
        if invocation_path is not None:
            try:
                transport.frozen_no_replace_write(
                    invocation_path / "failed.json", evidence.canonical(result).encode("utf-8"),
                    error_factory=PreparationError,
                )
            except (PreparationError, OSError):
                pass  # The caller's actual process result remains mandatory evidence.
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
