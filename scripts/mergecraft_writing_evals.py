#!/usr/bin/env python3
"""Prepare and inspect the fixed Mergecraft Markdown and relation evaluations.

Procedure: docs/agents/mergecraft-writing-evaluations.md. This helper does not
grade responses, select historical evidence, or rewrite plugin evidence.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime
import hashlib
import json
import re
import subprocess
import uuid
from pathlib import Path

SKILLS = "plugins/mergecraft/skills"
MARKDOWN = f"{SKILLS}/writing-github-issue-and-pr-markdown"
RELATION = f"{SKILLS}/maintaining-issue-pr-relations"
PR_WRITER = f"{SKILLS}/writing-reviewable-pr-descriptions"
RELATION_EVALS = "evals/mergecraft/skills/maintaining-issue-pr-relations"
PROSE = "plugins/proseweaving/skills/writing-for-people"
SYSTEM = (
    "Carry out the supplied task. The request contains the unchanged task prompt, "
    "fixture contents, and a candidate_bundle of applicable skill instructions, "
    "if present. Referenced candidate files are supplied in full in that bundle. "
    "Apply those instructions to the task. No tools are available."
)
MODEL = "claude-opus-5"
EFFORT = "high"
MARKDOWN_BUNDLE = [
    f"{MARKDOWN}/SKILL.md",
    f"{MARKDOWN}/references/authoring-contract.md",
    f"{MARKDOWN}/references/review-voice.md",
    f"{PROSE}/SKILL.md",
    f"{PROSE}/references/edit-pass.md",
    f"{PROSE}/references/evidence-in-prose.md",
    f"{PROSE}/references/threaded-conversation.md",
]
RELATION_BUNDLE = MARKDOWN_BUNDLE + [
    f"{RELATION}/SKILL.md",
    f"{RELATION}/references/relation-contract.md",
    f"{RELATION}/references/command.md",
    f"{SKILLS}/publishing-reviewable-prs/SKILL.md",
    f"{PR_WRITER}/SKILL.md",
    f"{PR_WRITER}/references/body-contract.md",
    f"{PR_WRITER}/references/relation-ledger.md",
    f"{PR_WRITER}/references/github-markdown-authoring.md",
    f"{PR_WRITER}/references/change-navigation.md",
]
CALLER_REFERENCES = {
    "getting-prs-ready-for-review": [
        f"{SKILLS}/getting-prs-merged/references/caller-continuation.md"
    ],
    "resuming-reviewed-prs": [
        f"{SKILLS}/getting-prs-merged/references/caller-continuation.md"
    ],
    "getting-prs-merged": [
        f"{SKILLS}/getting-prs-merged/references/caller-continuation.md",
        f"{SKILLS}/getting-prs-merged/references/merge-actuator.md",
        f"{SKILLS}/getting-prs-merged/references/gh-fix-ci-adapter.md",
        f"{SKILLS}/getting-prs-merged/references/github-markdown-authoring.md",
    ],
}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encode(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def read_json(path: Path):
    return json.loads(path.read_bytes())


def require(condition, message: str) -> None:
    if not condition:
        raise ValueError(message)


def create(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)
    path.chmod(0o600)


def claude_code_version(executable: Path) -> str:
    """Read the semantic version from the executable selected for this run."""
    output = subprocess.check_output(
        [str(executable), "--version"],
        text=True,
        stderr=subprocess.STDOUT,
        timeout=5,
    )
    match = re.fullmatch(r"([0-9]+\.[0-9]+\.[0-9]+) \(Claude Code\)", output.strip())
    require(match is not None, "executable did not report a Claude Code version")
    return match.group(1)


def prepare(repo: Path, output: Path, claude: Path) -> dict:
    require(not output.exists(), "evaluation directory already exists")
    source = {}

    def read(relative: str) -> str:
        raw = (repo / relative).read_bytes()
        source[relative] = raw
        return raw.decode("utf-8")

    specs, grades = [], []
    for suite, corpus_path, expected_count in (
        ("markdown", f"{MARKDOWN}/evals/evals.json", 8),
        ("relations", f"{RELATION_EVALS}/evals.json", 17),
    ):
        cases = json.loads(read(corpus_path))["evals"]
        require(len(cases) == expected_count, f"{suite} case inventory changed")
        require(len({c["id"] for c in cases}) == len(cases), "duplicate case ID")
        directory = f"{MARKDOWN}/evals" if suite == "markdown" else RELATION_EVALS
        policy = json.loads(read(f"{directory}/policy.json"))
        require(policy["repetitions"] == 3, "repetition policy changed")
        read(f"{directory}/trigger-evals.json")
        if suite == "markdown":
            read(f"{directory}/delivery.json")
        for case in cases:
            if suite == "markdown":
                fixture = {p: read(f"{MARKDOWN}/{p}") for p in case["fixture_paths"]}
                paths = MARKDOWN_BUNDLE
            else:
                fixture = {
                    p: read(f"evals/mergecraft/skills/{p}") for p in case["files"]
                }
                paths = RELATION_BUNDLE + [f"{SKILLS}/{case['caller']}/SKILL.md"]
                paths += CALLER_REFERENCES.get(case["caller"], [])
            bundle = {p: read(p) for p in dict.fromkeys(paths)}
            request = json.dumps(
                {
                    "prompt": case["prompt"],
                    "fixture": fixture,
                    "candidate_bundle": bundle,
                },
                ensure_ascii=False,
                indent=2,
            )
            for repetition in range(1, 4):
                run_id = f"{suite}/case-{case['id']:02d}-with-skill-{repetition}"
                specs.append(
                    {
                        "id": run_id,
                        "kind": "behavior",
                        "suite": suite,
                        "case_id": case["id"],
                        "case_name": case["name"],
                        "repetition": repetition,
                        "request": request,
                        "request_sha256": digest(request.encode()),
                        "fixture_sha256": {
                            p: digest(v.encode()) for p, v in fixture.items()
                        },
                        "candidate_sha256": {
                            p: digest(v.encode()) for p, v in bundle.items()
                        },
                    }
                )
                grades.append(
                    {
                        "run_id": run_id,
                        "suite": suite,
                        "case_id": case["id"],
                        "expected_output": case["expected_output"],
                        "expectations": case["expectations"],
                    }
                )
    artifacts = {f"source/{p}": raw for p, raw in source.items()}
    artifacts.update(
        {
            "behavior-specs.json": encode(specs),
            "grader-cases.json": encode(grades),
        }
    )
    executable = claude.resolve(strict=True)
    client_version = claude_code_version(executable)
    manifest = {
        "schema_version": 2,
        "candidate_base_commit": subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
        ).strip(),
        "candidate_commit": None,
        "source_sha256": {p: digest(raw) for p, raw in sorted(source.items())},
        "artifact_sha256": {p: digest(raw) for p, raw in sorted(artifacts.items())},
        "helper_sha256": digest(Path(__file__).read_bytes()),
        "behavior_counts": {"markdown": 24, "relations": 51},
        "native_runs": 0,
        "executor": {
            "path": str(executable),
            "sha256": digest(executable.read_bytes()),
            "model_requested": MODEL,
            "effort_requested": EFFORT,
            "claude_code_version": client_version,
            "system_prompt": SYSTEM,
            "timeout_seconds": 240,
            "concurrency": 3,
        },
        "claim": "Prospective supplied-instruction observations only. Native discovery and historical controls require separate source/configuration retention review. No release or actuation claim.",
    }
    output.mkdir(mode=0o700)
    for name, raw in artifacts.items():
        create(output / name, raw)
    create(output / "manifest.json", encode(manifest))
    return manifest


def verify(evaluation: Path, repo: Path | None = None) -> dict:
    manifest = read_json(evaluation / "manifest.json")
    require(
        type(manifest.get("schema_version")) is int and manifest["schema_version"] == 2,
        "unsupported evaluation manifest schema; retain its original method",
    )
    require(
        isinstance(manifest.get("executor", {}).get("claude_code_version"), str)
        and re.fullmatch(r"\d+\.\d+\.\d+", manifest["executor"]["claude_code_version"]),
        "Claude Code version binding is missing or malformed",
    )
    require(
        manifest["helper_sha256"] == digest(Path(__file__).read_bytes()),
        "helper changed",
    )
    for path, expected in manifest["artifact_sha256"].items():
        require(
            digest((evaluation / path).read_bytes()) == expected,
            f"frozen artifact changed: {path}",
        )
    if repo is not None:
        for path, expected in manifest["source_sha256"].items():
            require(
                digest((repo / path).read_bytes()) == expected,
                f"current source changed: {path}",
            )
    return manifest


def execution_command(executable: str, session: str) -> list[str]:
    return [
        executable,
        "-p",
        "--verbose",
        "--output-format",
        "stream-json",
        "--no-session-persistence",
        "--session-id",
        session,
        "--model",
        MODEL,
        "--effort",
        EFFORT,
        "--permission-mode",
        "dontAsk",
        "--setting-sources",
        "",
        "--strict-mcp-config",
        "--mcp-config",
        '{"mcpServers":{}}',
        "--no-chrome",
        "--settings",
        '{"disableAllHooks":true,"autoMemoryEnabled":false,"enabledPlugins":{}}',
        "--safe-mode",
        "--tools",
        "",
        "--disable-slash-commands",
        "--system-prompt",
        SYSTEM,
    ]


def observe_stream(raw: bytes, session: str, expected_version: str) -> dict:
    events, errors = [], []
    decode_error = None
    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        decoded = ""
        decode_error = {"start": error.start, "end": error.end, "reason": error.reason}
    for line in decoded.split("\n"):
        if not line:
            continue
        try:
            event = json.loads(line)
            require(isinstance(event, dict), "stream event is not an object")
            events.append(event)
        except ValueError:
            errors.append(line)
    inits = [
        e for e in events if e.get("type") == "system" and e.get("subtype") == "init"
    ]
    results = [e for e in events if e.get("type") == "result"]
    init = inits[0] if len(inits) == 1 else {}
    result = results[0] if len(results) == 1 else {}
    assistants = [e for e in events if e.get("type") == "assistant"]
    blocks = [b for e in assistants for b in e.get("message", {}).get("content", [])]
    calls = [b for b in blocks if b.get("type") == "tool_use"]
    models = sorted(
        {e["message"]["model"] for e in assistants if e.get("message", {}).get("model")}
    )
    response = result.get("result")
    if not isinstance(response, str):
        response = "\n".join(b["text"] for b in blocks if b.get("type") == "text")
    valid = (
        decode_error is None
        and not errors
        and len(inits) == len(results) == 1
        and all(
            init.get(k) == []
            for k in ("tools", "mcp_servers", "skills", "plugins", "slash_commands")
        )
        and init.get("model") == MODEL
        and init.get("permissionMode") == "dontAsk"
        and init.get("claude_code_version") == expected_version
        and init.get("session_id") == result.get("session_id") == session
        and all(e.get("session_id") == session for e in assistants)
        and models == [MODEL]
        and not calls
        and result.get("subtype") == "success"
        and result.get("is_error") is False
        and not result.get("permission_denials")
        and isinstance(result.get("result"), str)
    )
    return {
        "response": response,
        "init": init,
        "assistant_models": models,
        "tool_calls": calls,
        "decode_error": decode_error,
        "parse_errors": errors,
        "stream_valid": valid,
        "result": result,
        "assistant_message_ids": [e.get("message", {}).get("id") for e in assistants],
        "assistant_session_ids": [e.get("session_id") for e in assistants],
        "provider_request_ids": [
            e.get("requestId") for e in assistants if e.get("requestId")
        ],
    }


def execute_one(evaluation: Path, spec: dict, executor: dict) -> dict:
    run = evaluation / "runs" / spec["id"]
    run.mkdir(parents=True, exist_ok=False)
    workspace = run / "workspace"
    workspace.mkdir()
    session = str(uuid.uuid4())
    command = execution_command(executor["path"], session)
    create(run / "request.txt", spec["request"].encode())
    create(run / "spec.json", encode({k: v for k, v in spec.items() if k != "request"}))
    create(run / "command.json", encode(command))
    now = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    started, timed_out, launch_error, returncode = now(), False, None, None
    with (
        (run / "stdout.jsonl").open("xb") as stdout,
        (run / "stderr.txt").open("xb") as stderr,
    ):
        try:
            process = subprocess.Popen(
                command,
                cwd=workspace,
                stdin=subprocess.PIPE,
                stdout=stdout,
                stderr=stderr,
            )
            try:
                process.communicate(
                    spec["request"].encode(), timeout=executor["timeout_seconds"]
                )
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                timed_out = True
            returncode = process.returncode
        except OSError as error:
            launch_error = str(error)
    raw = (run / "stdout.jsonl").read_bytes()
    observed = observe_stream(raw, session, executor["claude_code_version"])
    response = observed.pop("response")
    create(run / "response.txt", response.encode())
    record = {
        "id": spec["id"],
        "session_id": session,
        "started_at": started,
        "finished_at": now(),
        "model_requested": MODEL,
        "effort_requested": EFFORT,
        "request_sha256": digest(spec["request"].encode()),
        "response_sha256": digest(response.encode()),
        "stdout_sha256": digest(raw),
        "stderr_sha256": digest((run / "stderr.txt").read_bytes()),
        "command_sha256": digest((run / "command.json").read_bytes()),
        "exit_code": returncode,
        "timed_out": timed_out,
        "launch_error": launch_error,
        **observed,
        "technically_valid": returncode == 0
        and not timed_out
        and observed["stream_valid"],
    }
    observed_session = record["init"].get("session_id")
    record["reconciliation_execution"] = {
        "case_id": spec["case_id"],
        "repetition": spec["repetition"],
        "response_sha256": record["response_sha256"],
        "execution": {
            "completed": record["technically_valid"],
            "returncode": returncode,
            "thread_ids": [observed_session]
            if isinstance(observed_session, str) and observed_session.strip()
            else [],
            "response_sha256": record["response_sha256"],
        },
    }
    create(run / "record.json", encode(record))
    for path in run.iterdir():
        if path.is_file():
            path.chmod(0o600)
    return {
        k: record[k]
        for k in ("id", "session_id", "technically_valid", "exit_code", "timed_out")
    }


def run_batch(evaluation: Path, repo: Path, expected: str, selected: list[str]) -> bool:
    require(
        digest((evaluation / "manifest.json").read_bytes()) == expected,
        "manifest digest differs",
    )
    manifest = verify(evaluation, repo)
    executor = manifest["executor"]
    require(
        digest(Path(executor["path"]).read_bytes()) == executor["sha256"],
        "executor changed",
    )
    specs = {s["id"]: s for s in read_json(evaluation / "behavior-specs.json")}
    require(
        bool(selected) and len(set(selected)) == len(selected),
        "run selection is empty or duplicated",
    )
    require(set(selected) <= specs.keys(), "unknown run ID")
    require(
        all(not (evaluation / "runs" / name).exists() for name in selected),
        "run directory already exists; reconcile it before selecting new work",
    )
    pending, next_index, completed = set(), 0, []
    stop = evaluation / "STOP_LAUNCHES"
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=executor["concurrency"]
    ) as pool:
        while pending or next_index < len(selected):
            while (
                len(pending) < executor["concurrency"]
                and next_index < len(selected)
                and not stop.exists()
                and all(r["technically_valid"] for r in completed)
            ):
                pending.add(
                    pool.submit(
                        execute_one, evaluation, specs[selected[next_index]], executor
                    )
                )
                next_index += 1
            if not pending:
                break
            finished, pending = concurrent.futures.wait(
                pending, return_when=concurrent.futures.FIRST_COMPLETED
            )
            for future in finished:
                result = future.result()
                completed.append(result)
                print(json.dumps(result), flush=True)
    summary = {
        "completed": len(completed),
        "unlaunched": selected[next_index:],
        "stop_requested": stop.exists(),
    }
    print(json.dumps(summary), flush=True)
    return len(completed) == len(selected) and all(
        r["technically_valid"] for r in completed
    )


def collect_packet(evaluation: Path, repo: Path, suite: str, case: int) -> dict:
    verify(evaluation, repo)
    specs = [
        s
        for s in read_json(evaluation / "behavior-specs.json")
        if s["suite"] == suite and s["case_id"] == case
    ]
    require(
        len(specs) == 3 and {s["repetition"] for s in specs} == {1, 2, 3},
        "case does not have three coordinates",
    )
    grades = {g["run_id"]: g for g in read_json(evaluation / "grader-cases.json")}
    manifest = read_json(evaluation / "manifest.json")
    responses = []
    for spec in specs:
        run = evaluation / "runs" / spec["id"]
        record = read_json(run / "record.json")
        require(record["id"] == spec["id"], "run identity differs")
        require(
            read_json(run / "spec.json")
            == {k: v for k, v in spec.items() if k != "request"},
            "executed specification differs",
        )
        require(
            (run / "request.txt").read_bytes() == spec["request"].encode(),
            "executed request differs",
        )
        require(
            record["request_sha256"] == spec["request_sha256"],
            "recorded request digest differs",
        )
        for name, key in (
            ("response.txt", "response_sha256"),
            ("stdout.jsonl", "stdout_sha256"),
            ("stderr.txt", "stderr_sha256"),
            ("command.json", "command_sha256"),
        ):
            require(
                digest((run / name).read_bytes()) == record[key],
                f"recorded {name} digest differs",
            )
        require(
            read_json(run / "command.json")
            == execution_command(manifest["executor"]["path"], record["session_id"]),
            "execution command differs",
        )
        observed = observe_stream(
            (run / "stdout.jsonl").read_bytes(),
            record["session_id"],
            manifest["executor"]["claude_code_version"],
        )
        response = observed.pop("response")
        require(
            response.encode() == (run / "response.txt").read_bytes(),
            "stream response differs",
        )
        require(
            all(record[key] == value for key, value in observed.items()),
            "recorded stream observations differ",
        )
        require(
            record["technically_valid"]
            and record["exit_code"] == 0
            and not record["timed_out"]
            and not record["launch_error"]
            and observed["stream_valid"],
            "execution is technically invalid",
        )
        responses.append(
            {
                "run_id": spec["id"],
                "session_id": record["session_id"],
                "record_sha256": digest((run / "record.json").read_bytes()),
                "request_sha256": record["request_sha256"],
                "response_sha256": record["response_sha256"],
                "response": response,
            }
        )
    require(len({r["session_id"] for r in responses}) == 3, "sessions are not distinct")
    first = grades[specs[0]["id"]]
    require(
        all(grades[s["id"]]["expectations"] == first["expectations"] for s in specs),
        "rubrics differ across repetitions",
    )
    return {
        "manifest_sha256": digest((evaluation / "manifest.json").read_bytes()),
        "suite": suite,
        "case_id": case,
        "executor_request": json.loads(specs[0]["request"]),
        "expected_output": first["expected_output"],
        "expectations": first["expectations"],
        "responses": responses,
        "grading_contract": "Independently judge every exact expectation for each response with response-bound evidence. Preserve supplementary inaccuracies separately. Return coverage and missing-run accounting. Do not infer live effects or native discovery from these supplied-instruction decisions.",
    }


def collect(evaluation: Path, repo: Path, suite: str, case: int, output: Path) -> None:
    create(output, encode(collect_packet(evaluation, repo, suite, case)))


# Receipt capture is offline equipment. These constants preserve the existing
# private native method's delivery; they do not configure a new runner.
RELATION_RECEIPT_SKILL = "mergecraft/maintaining-issue-pr-relations"
RECEIPT_PROCEDURE = "docs/agents/mergecraft-writing-evaluations.md"
NATIVE_PATHS = [
    f"{RELATION}/{name}"
    for name in ("SKILL.md", "references/relation-contract.md", "references/command.md")
]
NATIVE_TARGET = "mergecraft-scope-eval:maintaining-issue-pr-relations"
NATIVE_PROMPT = (
    "Decide which available skill, if any, is needed for this user request. "
    "If a skill applies, invoke it using Skill, then stop without carrying out "
    "the task. If none applies, return NO_SKILL. Do not invoke any other tool "
    "or perform any task action.\n\nUser request: "
)
NATIVE_SETTINGS = {
    "disableAllHooks": True,
    "autoMemoryEnabled": False,
    "enabledPlugins": {},
    "claudeMdExcludes": ["**"],
}
NATIVE_PLUGIN = {
    "name": "mergecraft-scope-eval",
    "version": "0.0.0",
    "description": "Isolated candidate relation skill discovery evaluation",
}


def receipt_modules():
    import behavior_eval_inventory as inventory
    import behavior_eval_receipts as core

    return core, inventory


class ReceiptInputs:
    """Retain exact private input bytes/modes and recheck before adding outputs."""

    def __init__(self):
        self.files = {}

    def raw(self, path, expected=None):
        import stat

        path = Path(path).absolute()
        require(
            not path.is_symlink() and path.is_file(), f"input is not regular: {path}"
        )
        raw = path.read_bytes()
        identity = {
            "path": str(path),
            "sha256": digest(raw),
            "mode": stat.S_IMODE(path.stat().st_mode),
        }
        require(
            expected is None or identity["sha256"] == expected,
            f"input digest differs: {path}",
        )
        require(
            str(path) not in self.files or self.files[str(path)] == identity,
            f"input changed while reading: {path}",
        )
        self.files[str(path)] = identity
        return raw

    def json(self, path, expected=None):
        core, _ = receipt_modules()
        return core.read_json(self.raw(path, expected))

    def reference(self, reference):
        raw = self.raw(reference["path"], reference["sha256"])
        format = reference.get("format", "json")
        pointer = reference.get("pointer", "")
        require(format in ("json", "utf8"), "unsupported sidecar reference format")
        if format == "utf8":
            require(pointer == "", "text reference needs an empty pointer")
            return raw.decode("utf-8")
        core, _ = receipt_modules()
        value = core.read_json(raw)
        require(pointer == "" or pointer.startswith("/"), "invalid sidecar pointer")
        for part in pointer.split("/")[1:]:
            key = part.replace("~1", "/").replace("~0", "~")
            value = value[int(key)] if isinstance(value, list) else value[key]
        return value

    def recheck(self):
        for identity in list(self.files.values()):
            self.raw(identity["path"], identity["sha256"])


def receipt_source(inputs, repo, revision, descriptor_path, snapshot_path):
    core, inventory = receipt_modules()
    recorder_source = "scripts/mergecraft_writing_evals.py"
    require(
        inputs.raw(__file__) == core.source_bytes(repo, revision, recorder_source),
        "loaded recorder differs from committed S",
    )
    for module in (core, inventory, inventory.corpora):
        name = "scripts/" + Path(module.__file__).name
        require(
            inputs.raw(module.__file__) == core.source_bytes(repo, revision, name),
            "loaded processor differs from committed S",
        )
    schema = Path(core.__file__).resolve().parents[1] / core.SCHEMA_PATH
    require(
        inputs.raw(schema) == core.source_bytes(repo, revision, core.SCHEMA_PATH),
        "loaded schema differs from committed S",
    )
    descriptor = inputs.json(descriptor_path)
    snapshot = inputs.json(snapshot_path)
    actual = inventory.descriptor(repo, revision, RELATION_RECEIPT_SKILL)
    require(
        actual["status"] == "ready" and descriptor == actual,
        "ready source descriptor differs",
    )
    require(
        snapshot == inventory.prepare(repo, revision, RELATION_RECEIPT_SKILL),
        "prepared source snapshot differs",
    )
    require(
        snapshot["skill"] == descriptor["descriptor"], "snapshot descriptor differs"
    )
    require(
        len(descriptor["cases"]) == 17 and len(descriptor["triggers"]) == 13,
        "relation receipt requires the fixed 17 application and 13 Boolean cases",
    )
    expectations = [e for c in descriptor["cases"] for e in c["expectations"]]
    require(
        len(expectations) == 65
        and sum(e["severity"] == "safety" for e in expectations) == 56
        and sum(e["severity"] == "quality" for e in expectations) == 9,
        "relation expectation scope differs",
    )
    required = {"scripts/mergecraft_writing_evals.py", RECEIPT_PROCEDURE}
    require(
        required <= set(snapshot["inputs"]),
        "recorder/procedure freshness dependencies missing",
    )
    recorder_mode = inputs.files[str(Path(__file__).absolute())]["mode"]
    require(
        ("100755" if recorder_mode & 0o111 else "100644")
        == snapshot["inputs"][recorder_source]["mode"],
        "loaded recorder mode differs from committed S",
    )
    excluded = {f"{RELATION_EVALS}/experiment.json", f"{RELATION_EVALS}/grading.json"}
    require(
        not excluded.intersection(snapshot["inputs"]),
        "later relation evidence belongs to snapshot closure",
    )
    for name, identity in snapshot["inputs"].items():
        path = repo / name
        inputs.raw(path, identity["sha256"])
        mode = "100755" if path.stat().st_mode & 0o111 else "100644"
        require(mode == identity["mode"], f"source mode differs: {name}")
    return descriptor, snapshot


def receipt_native_preparation(inputs, preparations, snapshot, repo):
    import ast

    core, _ = receipt_modules()
    index_ref = preparations["native"]
    index = inputs.reference(index_ref)
    prepared = Path(index_ref["path"]).absolute().parent
    require(
        index["schema_version"] == 1
        and index["stage"] == "native-input-construction"
        and index["model_executed"] is False
        and index["native_runs_planned"] == 13,
        "native preparation shape differs",
    )
    inputs.raw(
        preparations["native_method"]["path"], preparations["native_method"]["sha256"]
    )
    require(
        index["adapter_sha256"] == preparations["native_method"]["sha256"],
        "native method identity differs",
    )
    inputs.raw(
        preparations["native_format"]["path"], preparations["native_format"]["sha256"]
    )
    require(preparations["native_format_evidence"], "native format evidence is absent")
    for reference in preparations["native_format_evidence"]:
        inputs.raw(reference["path"], reference["sha256"])
    provenance = preparations["native_provenance"]
    require(
        {key: ref["sha256"] for key, ref in provenance.items()}
        == index["producer_source_sha256"],
        "native method provenance differs",
    )
    for ref in provenance.values():
        inputs.raw(ref["path"], ref["sha256"])
    runner = inputs.raw(index["runner_path"], index["runner_sha256"])
    original = inputs.raw(
        provenance["claude_eval_runner_v3.py"]["path"],
        provenance["claude_eval_runner_v3.py"]["sha256"],
    )

    def runner_base(raw):
        assignments = [
            node.value
            for node in ast.parse(raw).body
            if isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "BASE" for t in node.targets)
        ]
        require(len(assignments) == 1, "native runner destination is ambiguous")
        value = assignments[0]
        require(
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == "Path"
            and len(value.args) == 1
            and isinstance(value.args[0], ast.Constant)
            and isinstance(value.args[0].value, str)
            and Path(value.args[0].value).is_absolute(),
            "native runner destination shape differs",
        )
        return value.args[0].value

    destination, original_destination = runner_base(runner), runner_base(original)
    require(
        destination == index["runner_base"]
        and runner.replace(
            f"BASE=Path({destination!r})".encode(),
            f"BASE=Path({original_destination!r})".encode(),
            1,
        )
        == original,
        "native runner changed beyond destination",
    )
    manifest = inputs.json(index["manifest_path"], index["manifest_sha256"])
    require(
        Path(index["source_root"]) == Path(index["manifest_path"]).parent / "source",
        "native source root differs",
    )
    require(
        manifest["schema_version"] == 1
        and manifest["model_requested"] == MODEL
        and manifest["effort_requested"] == EFFORT
        and manifest["trigger_runs"] == 13
        and manifest["runner_sha256"] == index["runner_sha256"]
        and manifest["source_sha256"] == index["source_sha256"],
        "native frozen manifest differs",
    )
    require(
        set(
            NATIVE_PATHS
            + [f"{RELATION_EVALS}/trigger-evals.json", f"{RELATION_EVALS}/policy.json"]
        )
        <= set(manifest["source_sha256"]),
        "native frozen dependencies missing",
    )
    for name, expected in manifest["source_sha256"].items():
        core.relative_path(name)
        raw = inputs.raw(Path(index["source_root"]) / name, expected)
        require(
            raw == core.source_bytes(repo, snapshot["candidate_revision"], name),
            "native source differs from committed S",
        )
        inputs.raw(repo / name, expected)
    inventory_paths = {
        str(path.relative_to(prepared))
        for path in prepared.rglob("*")
        if path.is_file()
    }
    require(
        inventory_paths == set(index["files_sha256"]) | {"index.json"},
        "native prepared artifact inventory differs",
    )
    for name, expected in index["files_sha256"].items():
        core.relative_path(name)
        inputs.raw(prepared / name, expected)
    plugin = prepared / "trigger-plugin"
    require(
        inputs.json(plugin / ".claude-plugin/plugin.json") == NATIVE_PLUGIN,
        "native plugin metadata differs",
    )
    native_sources = {name: snapshot["inputs"][name]["sha256"] for name in NATIVE_PATHS}
    require(
        index["native_source_sha256"] == native_sources,
        "native delivered source binding differs",
    )
    for name in NATIVE_PATHS:
        inputs.raw(
            plugin
            / "skills/maintaining-issue-pr-relations"
            / Path(name).relative_to(RELATION),
            native_sources[name],
        )
    cases = inputs.json(repo / RELATION_EVALS / "trigger-evals.json")
    specs = inputs.json(prepared / "trigger-specs.json")
    grades = inputs.json(prepared / "grader-cases.json")
    require(
        len(cases) == len(specs) == len(grades) == 13,
        "native preparation coverage differs",
    )
    for i, (case, spec, grade) in enumerate(zip(cases, specs, grades)):
        run_id = f"opus-relation-triggers-{index['version']}/case-{i:02d}"
        require(
            spec
            == {
                "id": run_id,
                "kind": "trigger",
                "suite": "relation-triggers",
                "case_id": i,
                "request": NATIVE_PROMPT + case["query"],
                "plugin_dir": str(plugin),
                "candidate_sha256": native_sources,
            },
            "native request or delivery differs",
        )
        require(
            grade
            == {
                "run_id": run_id,
                "case_id": i,
                "expected_should_trigger": case["should_trigger"],
                "query": case["query"],
                "required_skill": NATIVE_TARGET,
            },
            "native grader corpus differs",
        )
    require(
        inputs.json(prepared / "trigger-first.json") == specs[:1]
        and inputs.json(prepared / "trigger-rest.json") == specs[1:],
        "native dispatch partition differs",
    )
    return index, specs


def receipt_binding_data(
    repo, revision, descriptor_path, snapshot_path, preparations_path, *, before_run
):
    core, _ = receipt_modules()
    inputs = ReceiptInputs()
    descriptor, snapshot = receipt_source(
        inputs, repo, revision, descriptor_path, snapshot_path
    )
    preparations = inputs.json(preparations_path)
    require(preparations["schema_version"] == 1, "unsupported preparation sidecar")
    behavior_ref = preparations["behavior"]
    manifest = inputs.reference(behavior_ref)
    evaluation = Path(behavior_ref["path"]).absolute().parent
    require(manifest == verify(evaluation, repo), "behavior preparation differs")
    require(
        manifest["helper_sha256"] == digest(Path(__file__).read_bytes()),
        "behavior helper identity differs",
    )
    require(
        manifest["behavior_counts"] == {"markdown": 24, "relations": 51}
        and manifest["native_runs"] == 0,
        "behavior preparation coverage differs",
    )
    for name, expected in manifest["artifact_sha256"].items():
        core.relative_path(name)
        inputs.raw(evaluation / name, expected)
    for name, expected in manifest["source_sha256"].items():
        require(
            digest(core.source_bytes(repo, revision, name)) == expected,
            "behavior source differs from committed S",
        )
        inputs.raw(repo / name, expected)
    executor = manifest["executor"]
    require(
        executor["model_requested"] == MODEL
        and executor["effort_requested"] == EFFORT
        and executor["system_prompt"] == SYSTEM
        and executor["timeout_seconds"] == 240
        and executor["concurrency"] == 3,
        "behavior execution configuration differs",
    )
    inputs.raw(executor["path"], executor["sha256"])
    specs = [
        s
        for s in inputs.json(evaluation / "behavior-specs.json")
        if s["suite"] == "relations"
    ]
    original = inputs.json(repo / RELATION_EVALS / "evals.json")["evals"]
    rubrics = [
        r
        for r in inputs.json(evaluation / "grader-cases.json")
        if r["suite"] == "relations"
    ]
    require(
        len(rubrics) == 51 and len({r["run_id"] for r in rubrics}) == 51,
        "application rubric coverage differs",
    )
    expected_cases = {c["case_id"]["id"]: c for c in descriptor["cases"]}
    require(
        len(specs) == 51 and len({s["id"] for s in specs}) == 51,
        "application preparation coverage differs",
    )
    require(
        {r["run_id"] for r in rubrics} == {s["id"] for s in specs},
        "application rubric run IDs differ",
    )
    runs = []
    for i, case in enumerate(original):
        coordinate = {
            "source": f"{RELATION_EVALS}/evals.json",
            "pointer": f"/evals/{i}",
            "id": case["id"],
        }
        require(
            expected_cases[case["id"]]["case_id"] == coordinate,
            "application source coordinate differs",
        )
        fixtures = {
            name: (repo / "evals/mergecraft/skills" / name).read_bytes().decode("utf-8")
            for name in case["files"]
        }
        paths = list(
            dict.fromkeys(
                RELATION_BUNDLE
                + [f"{SKILLS}/{case['caller']}/SKILL.md"]
                + CALLER_REFERENCES.get(case["caller"], [])
            )
        )
        bundle = {name: (repo / name).read_bytes().decode() for name in paths}
        request = json.dumps(
            {"prompt": case["prompt"], "fixture": fixtures, "candidate_bundle": bundle},
            ensure_ascii=False,
            indent=2,
        )
        delivered = {name: digest(raw.encode()) for name, raw in bundle.items()}
        delivered.update(
            {
                f"evals/mergecraft/skills/{name}": digest(raw.encode())
                for name, raw in fixtures.items()
            }
        )
        require(
            set(delivered) <= set(snapshot["inputs"]),
            "delivered source missing from snapshot",
        )
        require(
            all(
                snapshot["inputs"][name]["sha256"] == h for name, h in delivered.items()
            ),
            "delivered source differs from snapshot",
        )
        for repetition in (1, 2, 3):
            run_id = f"relations/case-{case['id']:02d}-with-skill-{repetition}"
            matches = [spec for spec in specs if spec["id"] == run_id]
            require(len(matches) == 1, "missing original application run ID")
            spec = matches[0]
            require(
                spec
                == {
                    "id": run_id,
                    "kind": "behavior",
                    "suite": "relations",
                    "case_id": case["id"],
                    "case_name": case["name"],
                    "repetition": repetition,
                    "request": request,
                    "request_sha256": digest(request.encode()),
                    "fixture_sha256": {
                        k: digest(v.encode()) for k, v in fixtures.items()
                    },
                    "candidate_sha256": {
                        k: digest(v.encode()) for k, v in bundle.items()
                    },
                },
                "application request or delivery differs",
            )
            require(
                next(r for r in rubrics if r["run_id"] == run_id)
                == {
                    "run_id": run_id,
                    "suite": "relations",
                    "case_id": case["id"],
                    "expected_output": case["expected_output"],
                    "expectations": case["expectations"],
                },
                "application rubric differs from source",
            )
            destination = evaluation / "runs" / run_id
            require(
                not before_run or not destination.exists(),
                "application destination already contains an observation",
            )
            runs.append(
                {
                    "run_id": run_id,
                    "case_id": coordinate,
                    "repetition": repetition,
                    "directory": str(destination),
                    "request_sha256": spec["request_sha256"],
                    "delivered_source_sha256": delivered,
                }
            )
    native_index, native_specs = receipt_native_preparation(
        inputs, preparations, snapshot, repo
    )
    triggers = []
    for i, spec in enumerate(native_specs):
        coordinate = {
            "source": f"{RELATION_EVALS}/trigger-evals.json",
            "pointer": f"/{i}",
            "id": None,
        }
        require(
            any(
                t["case_id"] == coordinate and type(t["expected"]) is bool
                for t in descriptor["triggers"]
            ),
            "native coordinate or observation kind differs",
        )
        destination = Path(native_index["runner_base"]) / spec["id"]
        require(
            not before_run or not destination.exists(),
            "native destination already contains an observation",
        )
        triggers.append(
            {
                "run_id": spec["id"],
                "case_id": coordinate,
                "directory": str(destination),
                "request_sha256": digest(spec["request"].encode()),
                "delivered_source_sha256": spec["candidate_sha256"],
            }
        )
    grader = preparations["grader_model"]
    require(
        grader["basis"] in ("configured", "requested", "reported")
        and inputs.reference(grader["reference"]) == grader["id"],
        "grader model basis differs",
    )
    inputs.recheck()
    return {
        "schema_version": 1,
        "stage": "prepared-relation-binding",
        "rubrics": {
            str(case["case_id"]["id"]): [
                {key: expectation[key] for key in ("id", "severity", "text")}
                for expectation in case["expectations"]
            ]
            for case in descriptor["cases"]
        },
        "repository": str(repo.absolute()),
        "source_revision": revision,
        "snapshot_sha256": core.document_digest(snapshot),
        "snapshot": {
            "path": str(snapshot_path.absolute()),
            "sha256": digest(snapshot_path.read_bytes()),
        },
        "descriptor": {
            "path": str(descriptor_path.absolute()),
            "sha256": digest(descriptor_path.read_bytes()),
        },
        "preparations": {
            "path": str(preparations_path.absolute()),
            "sha256": digest(preparations_path.read_bytes()),
        },
        "executor_model_id": MODEL,
        "grader_model": grader,
        "runs": runs,
        "triggers": triggers,
        "inputs": sorted(inputs.files.values(), key=lambda row: row["path"]),
        "limits": "Prospective correspondence only; no authenticated execution, served model, complete provider input, or containment claim.",
    }


def receipt_bind(repo, revision, descriptor, snapshot, preparations, output):
    receipt_output(repo, output)
    binding = receipt_binding_data(
        repo, revision, descriptor, snapshot, preparations, before_run=True
    )
    create(output, encode(binding))
    return {"binding_sha256": digest(output.read_bytes()), "runs": 51, "triggers": 13}


def receipt_output(repo, output):
    require(
        not output.exists() and not output.is_symlink(), "receipt output already exists"
    )
    require(
        not output.resolve().is_relative_to(repo.resolve()),
        "receipt output must be outside source",
    )


def receipt_recheck_binding(path, expected):
    inputs = ReceiptInputs()
    binding = inputs.json(path, expected)
    require(
        binding["schema_version"] == 1
        and binding["stage"] == "prepared-relation-binding",
        "unsupported binding",
    )
    for item in binding["inputs"]:
        inputs.raw(item["path"], item["sha256"])
        require(
            inputs.files[str(Path(item["path"]).absolute())]["mode"] == item["mode"],
            "retained input mode differs",
        )
    current = receipt_binding_data(
        Path(binding["repository"]),
        binding["source_revision"],
        Path(binding["descriptor"]["path"]),
        Path(binding["snapshot"]["path"]),
        Path(binding["preparations"]["path"]),
        before_run=False,
    )
    require(
        current == binding,
        "prospective binding differs from current source/preparations",
    )
    return binding, inputs


def native_command(session, plugin, debug):
    return [
        "claude",
        "-p",
        "--verbose",
        "--output-format",
        "stream-json",
        "--no-session-persistence",
        "--session-id",
        session,
        "--model",
        MODEL,
        "--effort",
        EFFORT,
        "--permission-mode",
        "dontAsk",
        "--setting-sources",
        "",
        "--strict-mcp-config",
        "--mcp-config",
        '{"mcpServers":{}}',
        "--no-chrome",
        "--settings",
        json.dumps(NATIVE_SETTINGS, separators=(",", ":")),
        "--restricted",
        "--plugin-dir",
        str(plugin),
        "--tools",
        "Skill",
        "--allowedTools",
        "Skill",
        "--debug-file",
        str(debug),
    ]


def native_boolean(raw, session, plugin, body):
    """Derive only the two qualified old-format patterns from a complete stream."""
    core, _ = receipt_modules()
    rows = []
    for line_number, line in enumerate(raw.decode("utf-8").split("\n")):
        if line.strip():
            event = core.read_json(line.encode("utf-8"))
            require(isinstance(event, dict), "native event is not an object")
            rows.append((line_number, event))
    require(bool(rows), "native stream is missing or incomplete")
    inits = [
        (line, event)
        for line, event in rows
        if event.get("type") == "system" and event.get("subtype") == "init"
    ]
    terminals = [(line, event) for line, event in rows if event.get("type") == "result"]
    require(
        len(inits) == len(terminals) == 1
        and rows[0] == inits[0]
        and rows[-1] == terminals[0],
        "native initialization/completion ordering is incomplete",
    )
    init, terminal = inits[0][1], terminals[0][1]
    require(
        init.get("session_id") == terminal.get("session_id") == session
        and terminal.get("subtype") == "success"
        and terminal.get("is_error") is False
        and not terminal.get("permission_denials"),
        "native completion is invalid",
    )
    calls, results, injections, assistants, metadata = [], [], [], [], []
    for line, event in rows:
        kind = event.get("type")
        require(event.get("session_id", session) == session, "native session differs")
        if kind == "system":
            require(
                event.get("subtype") in ("init", "thinking_tokens"),
                "unsupported native system event",
            )
            continue
        if kind == "rate_limit_event":
            require("subtype" not in event, "unsupported native rate-limit event")
            continue
        if kind == "result":
            continue
        require(
            kind in ("assistant", "user") and "subtype" not in event,
            "unsupported native event type",
        )
        message = event.get("message")
        require(
            isinstance(message, dict)
            and isinstance(message.get("content"), list)
            and all(isinstance(b, dict) for b in message["content"]),
            "malformed native message blocks",
        )
        if kind == "assistant":
            require(
                event.get("session_id") == session and message.get("model") == MODEL,
                "native assistant identity differs",
            )
            assistants.append((line, event))
        if "tool_use_result" in event:
            metadata.append((line, event["tool_use_result"]))
        for block_number, block in enumerate(message["content"]):
            pointer = f"/{line}/message/content/{block_number}"
            if block.get("type") == "tool_use":
                require(
                    kind == "assistant", "native tool call has unsupported placement"
                )
                calls.append((line, pointer, block))
            elif block.get("type") == "tool_result":
                require(kind == "user", "native tool result has unsupported placement")
                results.append((line, pointer, block, event))
            elif (
                kind == "user"
                and block.get("type") == "text"
                and isinstance(block.get("text"), str)
                and block["text"].startswith("Base directory for this skill: ")
            ):
                injections.append((line, pointer + "/text", block["text"], event))
            elif kind == "user":
                raise ValueError("unsupported native user content")
            else:
                require(
                    block.get("type") in ("text", "thinking")
                    and isinstance(
                        block.get("text" if block["type"] == "text" else "thinking"),
                        str,
                    ),
                    "unsupported native assistant block",
                )
    require(assistants, "native assistant observation is absent")
    if not calls and not results and not injections and not metadata:
        return (
            False,
            {
                "init_pointer": f"/{inits[0][0]}",
                "terminal_pointer": f"/{terminals[0][0]}",
                "call_count": 0,
                "result_count": 0,
                "injection_count": 0,
            },
            rows,
        )
    require(
        len(calls) == len(results) == len(injections) == len(metadata) == 1,
        "unsupported repeated, parallel, unmatched, or incomplete native invocation",
    )
    call_line, call_pointer, call = calls[0]
    result_line, result_pointer, result, result_event = results[0]
    injection_line, injection_pointer, injection, injection_event = injections[0]
    require(
        call.get("name") == "Skill"
        and isinstance(call.get("id"), str)
        and bool(call["id"])
        and call.get("input") == {"skill": NATIVE_TARGET},
        "unsupported native target or arguments",
    )
    require(
        set(result) == {"type", "tool_use_id", "content"}
        and result["tool_use_id"] == call["id"]
        and result["content"] == "Launching skill: " + NATIVE_TARGET
        and isinstance(result_event.get("tool_use_result"), dict)
        and result_event["tool_use_result"].get("success") is True
        and result_event["tool_use_result"].get("commandName") == NATIVE_TARGET,
        "native call/result correspondence or success differs",
    )
    require(
        call_line < result_line
        and injection_line == result_line + 1
        and any(injection_line < line < terminals[0][0] for line, _ in assistants),
        "unsupported native call/result/injection ordering",
    )
    expected = f"Base directory for this skill: {plugin / 'skills/maintaining-issue-pr-relations'}\n\n{body}"
    require(
        injection_event.get("isSynthetic") is True and injection == expected,
        "native injected source correspondence differs",
    )
    require(
        len(result_event["message"]["content"])
        == len(injection_event["message"]["content"])
        == 1,
        "unsupported mixed native result/injection message",
    )
    return (
        True,
        {
            "init_pointer": f"/{inits[0][0]}",
            "terminal_pointer": f"/{terminals[0][0]}",
            "call_count": 1,
            "result_count": 1,
            "injection_count": 1,
            "call": {"pointer": call_pointer},
            "result": {"pointer": result_pointer},
            "result_metadata": {"pointer": f"/{result_line}/tool_use_result"},
            "injection": {"pointer": injection_pointer},
            "injection_association": "inferred-from-unique-call-adjacent-result-and-source-body",
            "explicit_injection_call_id": False,
        },
        rows,
    )


def receipt_native_observation(
    inputs, binding, preparations, collection, configuration, row, case_index
):
    import re

    native_index = inputs.reference(preparations["native"])
    prepared = Path(preparations["native"]["path"]).parent
    spec = inputs.json(prepared / "trigger-specs.json")[case_index]
    grade = inputs.json(prepared / "grader-cases.json")[case_index]
    directory = Path(row["directory"])
    record = inputs.json(directory / "record.json")
    require(
        record["id"] == spec["id"]
        and record["kind"] == "trigger"
        and inputs.json(directory / "spec.json")
        == {k: v for k, v in spec.items() if k != "request"}
        and inputs.raw(directory / "request.txt") == spec["request"].encode()
        and record["request_sha256"] == row["request_sha256"]
        and isinstance(record["response"], str)
        and record["response_sha256"] == digest(record["response"].encode()),
        "native original record/specification/request differs",
    )
    raw = inputs.raw(directory / "stdout.jsonl", record["stdout_sha256"])
    inputs.raw(directory / "stderr.txt", record["stderr_sha256"])
    command = inputs.json(directory / "command.json")
    plugin = Path(spec["plugin_dir"])
    require(
        command
        == native_command(record["session_id"], plugin, directory / "debug.log"),
        "native command configuration differs",
    )
    body = (
        inputs.raw(Path(native_index["source_root"]) / NATIVE_PATHS[0])
        .decode()
        .split("---\n", 2)[2]
        .lstrip("\n")
    )
    triggered, lineage, rows = native_boolean(raw, record["session_id"], plugin, body)
    events = [event for _, event in rows]
    init, terminal = events[0], events[-1]
    assistants = [e for e in events if e["type"] == "assistant"]
    calls = [
        b
        for e in assistants
        for b in e["message"]["content"]
        if b.get("type") == "tool_use"
    ]
    user_blocks = [
        b for e in events if e["type"] == "user" for b in e["message"]["content"]
    ]
    tool_results = [b for b in user_blocks if b.get("type") == "tool_result"]
    injections = [b["text"] for b in user_blocks if b.get("type") == "text"]
    models = sorted({e["message"]["model"] for e in assistants})
    require(
        record["init"] == init
        and record["exit_code"] == 0
        and record["timed_out"] is False
        and record["parse_errors"] == []
        and record["permission_denials"] == terminal.get("permission_denials", []) == []
        and record["result_subtype"] == terminal["subtype"] == "success"
        and record["result_is_error"] is terminal["is_error"] is False
        and terminal.get("result") == record["response"]
        and record["tool_calls"] == calls,
        "native terminal/technical collection admission differs",
    )
    require(
        record["model_requested"] == init["model"] == MODEL
        and record["effort_requested"] == EFFORT
        and record["assistant_models"] == models == [MODEL],
        "native model/effort observations differ",
    )
    require(
        init["tools"] == ["Skill"]
        and init["mcp_servers"] == []
        and init["permissionMode"] == "dontAsk"
        and init["claude_code_version"] == configuration["cli_version"]
        and init["plugins"]
        == [
            {
                "name": NATIVE_PLUGIN["name"],
                "path": str(plugin),
                "source": "mergecraft-scope-eval@inline",
                "version": "0.0.0",
            }
        ]
        and isinstance(init["skills"], list)
        and NATIVE_TARGET in init["skills"],
        "native initialized configuration differs",
    )
    debug = inputs.raw(directory / "debug.log")
    counts = re.findall(
        r"getSkills returning: (\d+) skill dir commands, (\d+) plugin skills, (\d+) bundled skills, (\d+) builtin plugin skills",
        debug.decode(),
    )
    require(
        counts
        and len(set(counts)) == 1
        and counts[0][:2] == ("0", "1")
        and counts[0][3] == "0",
        "native debug configuration differs",
    )
    injection_rows = [
        {
            "original_text_sha256": digest(text.encode()),
            "source_body_sha256": digest(body.encode()),
            "source_body_exact_match": True,
        }
        for text in injections
    ]
    configuration_sha = digest(inputs.raw(collection["configuration_path"]))
    packet = {
        "case_id": case_index,
        "request": spec["request"],
        "request_sha256": record["request_sha256"],
        "candidate_sha256": spec["candidate_sha256"],
        "expectation": grade,
        "response": {
            k: record[k]
            for k in (
                "id",
                "session_id",
                "response",
                "response_sha256",
                "assistant_models",
                "effort_requested",
                "exit_code",
                "timed_out",
                "result_is_error",
                "tool_calls",
            )
        },
        "init": {
            k: init.get(k)
            for k in (
                "tools",
                "skills",
                "plugins",
                "mcp_servers",
                "model",
                "claude_code_version",
            )
        },
        "skill_tool_results": tool_results,
        "skill_injections": injections,
        "raw_record_sha256": digest(inputs.raw(directory / "record.json")),
        "configuration_evidence_sha256": configuration_sha,
    }
    collection_root = Path(collection["root"])
    require(
        inputs.json(
            collection_root / f"grading-inputs/triggers/case-{case_index:02d}.json"
        )
        == packet,
        "native collected packet differs from original observations",
    )
    ambient = [name for name in init["skills"] if name != NATIVE_TARGET]
    isolation = {
        "run_id": spec["id"],
        "command_sha256": digest(inputs.raw(directory / "command.json")),
        "debug_sha256": digest(debug),
        "tools": init["tools"],
        "mcp_servers": init["mcp_servers"],
        "loaded_plugin_names": [p["name"] for p in init["plugins"]],
        "skill_directory_commands": 0,
        "candidate_plugin_skills": 1,
        "bundled_runtime_skill_descriptions_retained": bool(ambient),
        "bundled_runtime_skills_debug_count": int(counts[0][2]),
        "other_initialized_skill_descriptions": ambient,
        "claudeMdExcludes": ["**"],
        "skill_injections": injection_rows,
    }
    require(
        collection["isolation"]["runs"][case_index] == isolation,
        "native isolation collection differs",
    )
    reference = {
        "path": str(directory / "stdout.jsonl"),
        "sha256": digest(raw),
        "format": "jsonl",
    }
    for key in ("call", "result", "result_metadata", "injection"):
        if key in lineage:
            lineage[key] = {**reference, **lineage[key]}
    lineage.update(
        stream={**reference, "pointer": ""},
        original_record_sha256=packet["raw_record_sha256"],
        response_sha256=record["response_sha256"],
        source_body_sha256=digest(body.encode()),
        configuration_evidence_sha256=configuration_sha,
        isolation=isolation,
        limits=collection["isolation"].get("limitations", []),
    )
    return triggered, lineage, record["session_id"]


def receipt_observe(binding_path, binding_sha256, observations_path, output):
    import re

    core, _ = receipt_modules()
    require(not output.exists(), "observation output already exists")
    binding, inputs = receipt_recheck_binding(binding_path, binding_sha256)
    receipt_output(Path(binding["repository"]), output)
    observations = inputs.json(observations_path)
    require(observations["schema_version"] == 1, "unsupported observations sidecar")
    preparations = inputs.reference(binding["preparations"])
    evaluation = Path(preparations["behavior"]["path"]).parent
    repo = Path(binding["repository"])
    packets = {}
    for ref in observations["application_packets"]:
        packet = inputs.reference(ref)
        case = packet["case_id"]
        require(
            case not in packets and packet["suite"] == "relations",
            "application packet coordinate is duplicated or wrong",
        )
        require(
            packet == collect_packet(evaluation, repo, "relations", case),
            "application packet differs from original records",
        )
        packets[case] = (packet, ref)
    require(
        set(packets) == {row["case_id"]["id"] for row in binding["runs"]},
        "application packet coverage differs",
    )
    payloads, runs, triggers, sessions = {}, [], [], set()
    for number, row in enumerate(binding["runs"]):
        packet, packet_ref = packets[row["case_id"]["id"]]
        responses = [r for r in packet["responses"] if r["run_id"] == row["run_id"]]
        require(len(responses) == 1, "application response coordinate differs")
        response = responses[0]
        require(response["session_id"] not in sessions, "execution session reused")
        sessions.add(response["session_id"])
        directory = Path(row["directory"])
        for name in (
            "record.json",
            "spec.json",
            "request.txt",
            "command.json",
            "stdout.jsonl",
            "stderr.txt",
            "response.txt",
        ):
            inputs.raw(directory / name)
        execution = {
            "snapshot_sha256": binding["snapshot_sha256"],
            "case_id": row["case_id"],
            "repetition": row["repetition"],
            "model_id": binding["executor_model_id"],
            "response": response["response"],
        }
        core.validate(execution, "execution")
        name = f"execution/{number:02d}.json"
        payloads[name] = encode(execution)
        runs.append(
            {
                "case_id": row["case_id"],
                "repetition": row["repetition"],
                "run_id": row["run_id"],
                "executor_output": name,
                "execution_envelope_sha256": digest(payloads[name]),
                "response_sha256": response["response_sha256"],
                "runner_record_sha256": response["record_sha256"],
                "grader_packet": packet_ref,
                "grader_packet_sha256": packet_ref["sha256"],
                "session_id": response["session_id"],
            }
        )
    native = inputs.reference(preparations["native"])
    collection_ref = observations["native_collection"]
    collected = inputs.reference(collection_ref)
    configuration = inputs.reference(observations["configuration"])
    require(
        isinstance(configuration["cli_version"], str)
        and configuration["cli_version"]
        and isinstance(configuration["finding"], str)
        and configuration["finding"]
        and isinstance(configuration["source_excerpts"], list)
        and configuration["source_excerpts"]
        and all(isinstance(x, str) and x for x in configuration["source_excerpts"])
        and isinstance(configuration["executable_sha256"], str)
        and re.fullmatch("[0-9a-f]{64}", configuration["executable_sha256"]),
        "native configuration reader/schema evidence is incomplete",
    )
    require(
        collected["schema_version"] == 1
        and collected["stage"] == "native-record-collection"
        and collected["model_executed"] is False
        and collected["native_records_collected"] == 13
        and collected["semantic_grades_produced"] is False
        and collected["prepared_index_sha256"] == preparations["native"]["sha256"]
        and collected["candidate_manifest_sha256"] == native["manifest_sha256"]
        and collected["adapter_sha256"] == native["adapter_sha256"]
        and collected["producer_source_sha256"] == native["producer_source_sha256"]
        and collected["configuration_evidence_sha256"]
        == observations["configuration"]["sha256"],
        "native collection binding differs",
    )
    collection_root = Path(collection_ref["path"]).parent
    require(
        {
            str(p.relative_to(collection_root))
            for p in collection_root.rglob("*")
            if p.is_file()
        }
        == set(collected["files_sha256"]) | {"index.json"},
        "native collection inventory differs",
    )
    for name, expected in collected["files_sha256"].items():
        core.relative_path(name)
        inputs.raw(collection_root / name, expected)
    isolation = inputs.json(collection_root / "native-isolation-report.json")
    require(
        isolation["configuration_evidence_sha256"]
        == observations["configuration"]["sha256"]
        and isolation["configuration_evidence_cli_version"]
        == configuration["cli_version"]
        and isolation["configuration_evidence_executable_sha256"]
        == configuration["executable_sha256"]
        and isolation["managed_policy_contents_captured"] is False
        and len(isolation["runs"]) == 13,
        "native isolation report binding differs",
    )
    context = {
        "root": str(collection_root),
        "configuration_path": observations["configuration"]["path"],
        "isolation": isolation,
    }
    for number, row in enumerate(binding["triggers"]):
        observed, lineage, session = receipt_native_observation(
            inputs, binding, preparations, context, configuration, row, number
        )
        require(session not in sessions, "execution session reused")
        sessions.add(session)
        envelope = {
            "snapshot_sha256": binding["snapshot_sha256"],
            "case_id": row["case_id"],
            "model_id": binding["executor_model_id"],
            "observation_kind": "recorded-invocation",
            "triggered": observed,
        }
        core.validate(envelope, "triggerObservation")
        name = f"triggers/{number:02d}.json"
        payloads[name] = encode(envelope)
        triggers.append(
            {
                "case_id": row["case_id"],
                "observation": name,
                "lineage": lineage,
                "session_id": session,
            }
        )
    inputs.recheck()
    index = {
        "schema_version": 1,
        "stage": "observed-relation-receipts",
        "binding": {"path": str(binding_path.absolute()), "sha256": binding_sha256},
        "observations": {
            "path": str(observations_path.absolute()),
            "sha256": digest(observations_path.read_bytes()),
        },
        "runs": runs,
        "triggers": triggers,
        "inputs": sorted(inputs.files.values(), key=lambda row: row["path"]),
        "files_sha256": {name: digest(raw) for name, raw in payloads.items()},
        "limits": binding["limits"],
    }
    payloads["observation-index.json"] = encode(index)
    output.mkdir(mode=0o700)
    for name, raw in payloads.items():
        create(output / name, raw)
    require(
        all((output / name).read_bytes() == raw for name, raw in payloads.items()),
        "observation output reread differs",
    )
    return {
        "observation_index_sha256": digest(payloads["observation-index.json"]),
        "runs": 51,
        "triggers": 13,
    }


def receipt_results(
    binding_path,
    binding_sha256,
    observation_path,
    observation_sha256,
    grading_path,
    output,
):
    core, _ = receipt_modules()
    require(not output.exists(), "results output already exists")
    binding, inputs = receipt_recheck_binding(binding_path, binding_sha256)
    receipt_output(Path(binding["repository"]), output)
    index = inputs.json(observation_path, observation_sha256)
    require(
        index["schema_version"] == 1
        and index["stage"] == "observed-relation-receipts"
        and index["binding"]
        == {"path": str(binding_path.absolute()), "sha256": binding_sha256},
        "observation index belongs to another binding",
    )
    for item in index["inputs"]:
        inputs.raw(item["path"], item["sha256"])
        require(
            inputs.files[str(Path(item["path"]).absolute())]["mode"] == item["mode"],
            "observation input mode differs",
        )
    observed_root = observation_path.parent
    require(
        {
            str(p.relative_to(observed_root))
            for p in observed_root.rglob("*")
            if p.is_file()
        }
        == set(index["files_sha256"]) | {observation_path.name},
        "observation artifact inventory differs",
    )
    payloads = {}
    for name, expected in index["files_sha256"].items():
        core.relative_path(name)
        payloads[name] = inputs.raw(observed_root / name, expected)
    grading = inputs.json(grading_path)
    require(
        grading["schema_version"] == 1 and len(grading["runs"]) == 51,
        "grading coverage differs",
    )
    grades_by_run = {row["run_id"]: row for row in grading["runs"]}
    require(
        len(grades_by_run) == 51
        and set(grades_by_run) == {r["run_id"] for r in binding["runs"]},
        "grading coordinates are missing, duplicated, or extra",
    )
    descriptor = inputs.reference(binding["descriptor"])
    cases = {c["case_id"]["id"]: c for c in descriptor["cases"]}
    counts = {
        (c["case_id"]["id"], e["id"]): 0
        for c in descriptor["cases"]
        for e in c["expectations"]
    }
    results, lineage = [], []
    for number, (bound, observed) in enumerate(zip(binding["runs"], index["runs"])):
        require(
            all(observed[k] == bound[k] for k in ("run_id", "case_id", "repetition")),
            "observed coordinate differs",
        )
        row = grades_by_run[bound["run_id"]]
        record = inputs.reference(row["record"])
        require(
            record["run_id"] == bound["run_id"]
            and record["response_sha256"] == observed["response_sha256"]
            and record["grader_distinct_from_executor"] is True
            and isinstance(record["grader_task"], str)
            and record["grader_task"]
            and record["grader_task"]
            not in {r["session_id"] for r in index["runs"] + index["triggers"]},
            "original grading response/identity correspondence differs",
        )
        model = row["grader_model"]
        require(
            model["id"] == binding["grader_model"]["id"]
            and model["basis"] in ("configured", "requested", "reported")
            and inputs.reference(model["reference"]) == model["id"],
            "original grader model basis differs",
        )
        execution = core.read_json(payloads[observed["executor_output"]])
        require(
            digest(execution["response"].encode()) == observed["response_sha256"],
            "observed response digest differs",
        )
        packet = inputs.reference(observed["grader_packet"])
        case = cases[bound["case_id"]["id"]]
        expected = case["expectations"]
        require(
            packet["expectations"] == [e["original"] for e in expected],
            "original grader rubric differs",
        )
        require(
            len(record["expectations"]) == len(expected),
            "original grade expectation coverage differs",
        )
        judgments = []
        for actual, criterion in zip(record["expectations"], expected):
            require(
                actual["text"] == criterion["text"]
                and type(actual["passed"]) is bool
                and isinstance(actual.get("evidence"), str)
                and actual["evidence"],
                "original grade text, Boolean, or evidence differs",
            )
            require(
                actual.get("id", criterion["id"]) == criterion["id"]
                and actual.get("severity", criterion["severity"])
                == criterion["severity"],
                "original grade classification differs",
            )
            judgments.append({"id": criterion["id"], "passed": actual["passed"]})
            counts[case["case_id"]["id"], criterion["id"]] += actual["passed"]
        for previous in row["previous_grading"]:
            inputs.reference(previous)
        if row["adjudication"] is not None:
            inputs.reference(row["adjudication"])
        name = f"grading/{number:02d}.json"
        envelope = {
            "snapshot_sha256": binding["snapshot_sha256"],
            "case_id": bound["case_id"],
            "repetition": bound["repetition"],
            "model_id": model["id"],
            "executor_output_sha256": digest(payloads[observed["executor_output"]]),
            "expectations": judgments,
        }
        core.validate(envelope, "grading")
        payloads[name] = encode(envelope)
        results.append(
            {
                "case_id": bound["case_id"],
                "repetition": bound["repetition"],
                "executor_output": observed["executor_output"],
                "grading": name,
            }
        )
        lineage.append(
            {
                **observed,
                "original_grader": row["record"],
                "original_grader_sha256": row["record"]["sha256"],
                "grader_task": record["grader_task"],
                "grader_model": model,
                "grading_envelope_sha256": digest(payloads[name]),
                "previous_grading": row["previous_grading"],
                "adjudication": row["adjudication"],
            }
        )
    require(
        len(results) == 51 and len(index["triggers"]) == 13, "observed coverage differs"
    )
    result = {
        "schema_version": 1,
        "snapshot_sha256": binding["snapshot_sha256"],
        "executor_model_id": binding["executor_model_id"],
        "grader_model_id": binding["grader_model"]["id"],
        "runs": results,
        "triggers": [
            {k: row[k] for k in ("case_id", "observation")} for row in index["triggers"]
        ],
    }
    core.validate(result, "results")
    payloads["results.json"] = encode(result)
    inputs.recheck()
    output.mkdir(mode=0o700)
    for name, raw in payloads.items():
        create(output / name, raw)
    snapshot = inputs.reference(binding["snapshot"])
    receipt = core.produce(
        Path(binding["repository"]), snapshot, output / "results.json"
    )
    ordinary = core.evaluate(Path(binding["repository"]), receipt)
    thresholds = [
        {
            "case_id": c["case_id"],
            "id": e["id"],
            "severity": e["severity"],
            "passes": counts[c["case_id"]["id"], e["id"]],
            "required_passes": 3,
            "passed": counts[c["case_id"]["id"], e["id"]] == 3,
        }
        for c in descriptor["cases"]
        for e in c["expectations"]
    ]
    member_passed = (
        all(row["passed"] for row in thresholds)
        and ordinary["trigger_precision"]["correct"] == 13
    )
    inputs.recheck()
    create(output / "receipt.json", encode(receipt))
    create(
        output / "member-report.json",
        encode(
            {
                "schema_version": 1,
                "member_passed": member_passed,
                "ordinary": ordinary,
                "expectations": thresholds,
                "limits": binding["limits"],
            }
        ),
    )
    create(
        output / "lineage.json",
        encode(
            {
                "schema_version": 1,
                "binding": index["binding"],
                "observation_index": {
                    "path": str(observation_path.absolute()),
                    "sha256": observation_sha256,
                },
                "grading": {
                    "path": str(grading_path.absolute()),
                    "sha256": digest(grading_path.read_bytes()),
                },
                "runs": lineage,
                "triggers": index["triggers"],
                "inputs": sorted(inputs.files.values(), key=lambda r: r["path"]),
                "files_sha256": {
                    str(p.relative_to(output)): digest(p.read_bytes())
                    for p in output.rglob("*")
                    if p.is_file()
                },
                "limits": binding["limits"],
            }
        ),
    )
    return {
        "results_sha256": digest(payloads["results.json"]),
        "receipt_sha256": digest((output / "receipt.json").read_bytes()),
        "ordinary_status": ordinary["status"],
        "member_passed": member_passed,
        "judgments": 195,
    }


def member_inputs(inputs, identities):
    for identity in identities:
        inputs.raw(identity["path"], identity["sha256"])
        require(
            inputs.files[str(Path(identity["path"]).absolute())]["mode"]
            == identity["mode"],
            "retained input mode differs",
        )


def member_identity(reference):
    """Public artifact identity without the private storage coordinate."""
    return {k: reference[k] for k in ("sha256", "pointer", "format") if k in reference}


def member_public(value, location=""):
    """Report unknown local coordinates; never rewrite authored text."""
    if isinstance(value, str):
        import re

        require(
            not re.search(r"(?:^|[\s\"'=:])/(?:home|tmp|private/tmp|Users)/", value),
            f"public-coordinate conflict at {location}",
        )
    elif isinstance(value, list):
        for index, item in enumerate(value):
            member_public(item, f"{location}/{index}")
    elif isinstance(value, dict):
        for key, item in value.items():
            member_public(item, f"{location}/{key}")


def member_normalize(changes, run_id, pointer, original, retained):
    changes.append(
        {
            "projected_run_id": run_id,
            "pointer": pointer,
            "original_value_sha256": digest(encode(original)),
            "retained_value_sha256": digest(encode(retained)),
            "replacement": retained,
        }
    )
    return retained


def member_current(
    inputs, proposal, binding, lineage, index, finalized, native_by_id, report, ordinary
):
    import copy

    core, _ = receipt_modules()
    descriptor = inputs.reference(binding["descriptor"])
    preparations = inputs.reference(binding["preparations"])
    evaluation = Path(preparations["behavior"]["path"]).parent
    repo = Path(binding["repository"])
    observations = inputs.reference(index["observations"])
    collection_root = Path(observations["native_collection"]["path"]).parent
    context = {
        "root": str(collection_root),
        "configuration_path": observations["configuration"]["path"],
        "isolation": inputs.json(collection_root / "native-isolation-report.json"),
    }
    configuration = inputs.reference(observations["configuration"])
    original_grading = inputs.reference(lineage["grading"])
    grade_refs = {r["run_id"]: r for r in original_grading["runs"]}
    require(
        len(grade_refs) == len(original_grading["runs"]) == 51,
        "application grading coverage differs",
    )
    require(
        len(lineage["runs"]) == len(index["runs"]) == len(binding["runs"]) == 51,
        "application lineage coverage differs",
    )
    require(
        len(lineage["triggers"]) == len(binding["triggers"]) == 13,
        "native lineage coverage differs",
    )
    binding_sha = proposal["binding"]["sha256"]
    behavior_namespace = "relation-" + binding_sha
    native_namespace = "relation-native-" + binding_sha
    cases = {c["case_id"]["id"]: c for c in descriptor["cases"]}
    results = inputs.json(finalized / "results.json")
    behavior, native, grades, native_grades, requests, mapping, changes = (
        [],
        [],
        [],
        [],
        {},
        [],
        [],
    )
    sessions = {r["session_id"] for r in index["runs"] + index["triggers"]}
    counts = {
        (case, e["id"]): 0 for case, row in cases.items() for e in row["expectations"]
    }
    common_record_fields = (
        "session_id",
        "started_at",
        "finished_at",
        "model_requested",
        "effort_requested",
        "request_sha256",
        "stdout_sha256",
        "stderr_sha256",
        "exit_code",
        "timed_out",
        "assistant_models",
        "parse_errors",
    )
    init_fields = (
        "tools",
        "skills",
        "plugins",
        "mcp_servers",
        "slash_commands",
        "model",
        "permissionMode",
        "claude_code_version",
    )
    packets = {}
    for number, (bound, observed, retained) in enumerate(
        zip(binding["runs"], index["runs"], lineage["runs"])
    ):
        require(
            all(retained[k] == observed[k] for k in observed),
            "application observation lineage differs",
        )
        require(
            all(bound[k] == observed[k] for k in ("run_id", "case_id", "repetition")),
            "application bound coordinates differ",
        )
        case = bound["case_id"]["id"]
        if case not in packets:
            packets[case] = collect_packet(evaluation, repo, "relations", case)
        require(
            inputs.reference(observed["grader_packet"]) == packets[case],
            "application packet differs",
        )
        directory = Path(bound["directory"])
        spec = inputs.json(directory / "spec.json")
        record_raw = inputs.raw(
            directory / "record.json", observed["runner_record_sha256"]
        )
        record = core.read_json(record_raw)
        response = inputs.raw(directory / "response.txt").decode("utf-8")
        request = inputs.raw(directory / "request.txt", bound["request_sha256"]).decode(
            "utf-8"
        )
        execution = inputs.json(
            finalized / observed["executor_output"],
            observed["execution_envelope_sha256"],
        )
        require(
            execution["response"] == response
            and digest(response.encode()) == observed["response_sha256"],
            "application response correspondence differs",
        )
        require(
            spec["id"] == bound["run_id"]
            and spec["case_id"] == case
            and spec["repetition"] == bound["repetition"]
            and spec["kind"] == "behavior"
            and spec["suite"] == "relations"
            and record["id"] == bound["run_id"]
            and record["session_id"] == observed["session_id"],
            "application specification/record coordinates differ",
        )
        projected_id = (
            f"{behavior_namespace}/case-{case:02d}-with-skill-{bound['repetition']}"
        )
        projected = {key: record[key] for key in common_record_fields}
        projected.update(
            {
                key: record[key]
                for key in ("assistant_message_ids", "provider_request_ids")
                if key in record
            }
        )
        projected.update(
            {
                key: spec[key]
                for key in (
                    "case_id",
                    "case_name",
                    "repetition",
                    "fixture_sha256",
                    "candidate_sha256",
                )
            }
        )
        projected.update(
            id=projected_id,
            variant="with-skill",
            original_run_id=bound["run_id"],
            preparation_binding_sha256=binding_sha,
            original_record_sha256=digest(record_raw),
            response=response,
            response_sha256=observed["response_sha256"],
            tool_use=record["tool_calls"],
            command_sha256=digest(inputs.raw(directory / "command.json")),
            init={k: record["init"][k] for k in init_fields if k in record["init"]},
            result_subtype=record["result"]["subtype"],
            result_is_error=record["result"]["is_error"],
            permission_denials=record["result"].get("permission_denials", []),
        )
        for old, new in (
            ("uuid", "result_uuid"),
            ("usage", "usage"),
            ("modelUsage", "model_usage"),
        ):
            if old in record["result"]:
                projected[new] = record["result"][old]
        row = grade_refs[bound["run_id"]]
        require(
            retained["original_grader"] == row["record"]
            and retained["grader_model"] == row["grader_model"]
            and retained["previous_grading"] == row["previous_grading"]
            and retained["adjudication"] == row["adjudication"],
            "application grade lineage differs",
        )
        original = inputs.reference(row["record"])
        require(
            original["run_id"] == bound["run_id"]
            and original["response_sha256"] == projected["response_sha256"]
            and original["grader_distinct_from_executor"] is True
            and isinstance(original["grader_task"], str)
            and original["grader_task"]
            and original["grader_task"] not in sessions,
            "application independent grade binding differs",
        )
        require(
            row["grader_model"]["id"] == binding["grader_model"]["id"]
            and row["grader_model"]["basis"] in ("configured", "requested", "reported")
            and inputs.reference(row["grader_model"]["reference"])
            == row["grader_model"]["id"],
            "application grader model differs",
        )
        expected = cases[case]["expectations"]
        require(
            len(original["expectations"]) == len(expected),
            "application judgment coverage differs",
        )
        envelope = inputs.json(
            finalized / results["runs"][number]["grading"],
            retained["grading_envelope_sha256"],
        )
        judgments = []
        for actual, criterion in zip(original["expectations"], expected):
            require(
                actual["text"] == criterion["text"]
                and type(actual["passed"]) is bool
                and isinstance(actual["evidence"], str)
                and actual["evidence"],
                "application judgment differs",
            )
            judgments.append({"id": criterion["id"], "passed": actual["passed"]})
            counts[case, criterion["id"]] += actual["passed"]
        require(
            envelope["expectations"] == judgments
            and envelope["executor_output_sha256"]
            == observed["execution_envelope_sha256"],
            "original application grade/envelope differs",
        )
        grade = copy.deepcopy(original)
        grade.pop("supplementary_observations", None)
        grade.update(
            run_id=projected_id,
            original_run_id=bound["run_id"],
            original_grader=member_identity(row["record"]),
            grader_model={
                **row["grader_model"],
                "reference": member_identity(row["grader_model"]["reference"]),
            },
            previous_grading=[member_identity(r) for r in row["previous_grading"]],
            adjudication=None
            if row["adjudication"] is None
            else member_identity(row["adjudication"]),
        )
        behavior.append(projected)
        grades.append(grade)
        requests[bound["request_sha256"]] = request
        mapping.append(
            {
                "original_run_id": bound["run_id"],
                "projected_run_id": projected_id,
                "preparation_binding_sha256": binding_sha,
                "response_sha256": projected["response_sha256"],
                "runner_record_sha256": digest(record_raw),
                "projected_record_sha256": digest(encode(projected)),
                "packet": member_identity(observed["grader_packet"]),
                "execution_envelope_sha256": observed["execution_envelope_sha256"],
                "original_grade": member_identity(row["record"]),
                "grading_envelope_sha256": retained["grading_envelope_sha256"],
                "projected_grade_sha256": digest(encode(grade)),
            }
        )
    prepared_native = Path(preparations["native"]["path"]).parent
    specifications = inputs.json(prepared_native / "trigger-specs.json")
    for number, (bound, retained) in enumerate(
        zip(binding["triggers"], lineage["triggers"])
    ):
        triggered, actual_lineage, session = receipt_native_observation(
            inputs, binding, preparations, context, configuration, bound, number
        )
        require(
            actual_lineage == retained["lineage"] and session == retained["session_id"],
            "native lineage differs",
        )
        envelope = inputs.json(finalized / retained["observation"])
        require(
            envelope["case_id"] == bound["case_id"]
            and envelope["triggered"] is triggered,
            "native observation differs",
        )
        directory = Path(bound["directory"])
        spec = specifications[number]
        record = inputs.json(directory / "record.json")
        packet = inputs.json(
            collection_root / f"grading-inputs/triggers/case-{number:02d}.json"
        )
        projected_id = f"{native_namespace}/case-{number:02d}"
        projected = {key: record[key] for key in common_record_fields}
        projected.update(
            {
                key: record[key]
                for key in (
                    "result_subtype",
                    "result_is_error",
                    "permission_denials",
                    "response",
                    "response_sha256",
                )
            }
        )
        projected.update(
            id=projected_id,
            original_run_id=bound["run_id"],
            preparation_binding_sha256=binding_sha,
            candidate_sha256=spec["candidate_sha256"],
            case_id=number,
            original_record_sha256=actual_lineage["original_record_sha256"],
            tool_use=record["tool_calls"],
            tool_results=packet["skill_tool_results"],
            init={
                k: copy.deepcopy(record["init"][k])
                for k in init_fields
                if k in record["init"]
            },
        )
        projected["init"]["plugins"][0]["path"] = member_normalize(
            changes,
            projected_id,
            "/init/plugins/0/path",
            spec["plugin_dir"],
            "<CANDIDATE_PLUGIN>",
        )
        command = inputs.json(directory / "command.json")
        retained_argv = list(command)
        command_changes = []
        for flag, replacement in (
            ("--plugin-dir", "<CANDIDATE_PLUGIN>"),
            ("--debug-file", "<LOCAL_DEBUG_FILE>"),
        ):
            position = command.index(flag) + 1
            retained_argv[position] = member_normalize(
                changes,
                projected_id,
                f"/invocation/argv/{position}",
                command[position],
                replacement,
            )
            command_changes.append(changes[-1])
        projected["command_sha256"] = digest(inputs.raw(directory / "command.json"))
        projected["invocation"] = {
            "argv": retained_argv,
            "retained_argv_sha256": digest(
                json.dumps(retained_argv, separators=(",", ":")).encode()
            ),
            "redactions": command_changes,
        }
        projected["metadata_redactions"] = [
            c
            for c in changes
            if c["projected_run_id"] == projected_id
            and c["pointer"].startswith("/init/")
        ]
        injections = []
        for position, text in enumerate(packet["skill_injections"]):
            prefix = f"Base directory for this skill: {Path(spec['plugin_dir']) / 'skills/maintaining-issue-pr-relations'}\n\n"
            require(text.startswith(prefix), "native injection coordinate differs")
            normalized = (
                "Base directory for this skill: <CANDIDATE_SKILL_DIR>\n\n"
                + text[len(prefix) :]
            )
            member_normalize(
                changes,
                projected_id,
                f"/skill_injections/{position}/text",
                text,
                normalized,
            )
            injections.append(
                {
                    **actual_lineage["isolation"]["skill_injections"][position],
                    "text": normalized,
                    "retained_text_sha256": digest(normalized.encode()),
                    "redactions": [changes[-1]],
                }
            )
        projected["skill_injections"] = injections
        projected["isolation"] = {**actual_lineage["isolation"], "run_id": projected_id}
        original_ref = native_by_id[bound["run_id"]]["record"]
        original = inputs.reference(original_ref)
        calls = [call["input"]["skill"] for call in record["tool_calls"]]
        expected = descriptor["triggers"][number]["expected"]
        require(
            original["run_id"] == bound["run_id"]
            and original["response_sha256"] == record["response_sha256"]
            and original["grader_distinct_from_executor"] is True
            and isinstance(original["grader_task"], str)
            and original["grader_task"]
            and original["grader_task"] not in sessions
            and type(original["expected_should_trigger"]) is bool
            and original["expected_should_trigger"] is expected
            and original["actual_skill_calls"] == calls
            and type(original["passed"]) is bool
            and isinstance(original["evidence"], str)
            and original["evidence"],
            "native original grade correspondence differs",
        )
        require(
            not original["passed"] or triggered is expected,
            "native passing grade contradicts observation",
        )
        grade = copy.deepcopy(original)
        grade.pop("supplementary_observations", None)
        grade.update(
            run_id=projected_id,
            original_run_id=bound["run_id"],
            original_grader=member_identity(original_ref),
        )
        native.append(projected)
        native_grades.append(grade)
        requests[bound["request_sha256"]] = inputs.raw(
            directory / "request.txt", bound["request_sha256"]
        ).decode("utf-8")
        mapping.append(
            {
                "original_run_id": bound["run_id"],
                "projected_run_id": projected_id,
                "preparation_binding_sha256": binding_sha,
                "response_sha256": record["response_sha256"],
                "runner_record_sha256": actual_lineage["original_record_sha256"],
                "projected_record_sha256": digest(encode(projected)),
                "original_grade": member_identity(original_ref),
                "projected_grade_sha256": digest(encode(grade)),
                "observation_envelope_sha256": digest(
                    inputs.raw(finalized / retained["observation"])
                ),
            }
        )
    thresholds = [
        {
            "case_id": case,
            "expectation": e["text"],
            "passes": counts[case, e["id"]],
            "required": 3,
            "met": counts[case, e["id"]] == 3,
        }
        for case, row in cases.items()
        for e in row["expectations"]
    ]
    expected_report = {
        "schema_version": 1,
        "member_passed": (
            all(row["met"] for row in thresholds)
            and ordinary["trigger_precision"]["correct"] == 13
        ),
        "ordinary": ordinary,
        "expectations": [
            {
                "case_id": row["case_id"],
                "id": criterion["id"],
                "severity": criterion["severity"],
                "passes": counts[case, criterion["id"]],
                "required_passes": 3,
                "passed": counts[case, criterion["id"]] == 3,
            }
            for case, row in cases.items()
            for criterion in row["expectations"]
        ],
        "limits": binding["limits"],
    }
    require(
        member_canonical(report) == member_canonical(expected_report),
        "complete member report differs from bound source and original grades",
    )
    member_public(
        {
            "behavior": behavior,
            "native": native,
            "grades": grades,
            "native_grades": native_grades,
            "requests": requests,
        }
    )
    return (
        behavior,
        native,
        grades,
        native_grades,
        requests,
        mapping,
        changes,
        thresholds,
    )


def member_canonical(value):
    return digest(
        json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode()
    )


def member_history(inputs, history):
    """Verify retained originals; summarize later batches without publishing raw traces."""
    core, _ = receipt_modules()
    inventory = inputs.reference(history["inventory"])
    archive = inputs.reference(history["writer_archive"])
    copies = {row["original_path"]: row["copy"] for row in history["copies"]}
    require(len(copies) == len(history["copies"]), "duplicate history copy coordinate")
    used_copies = set()

    def raw(reference):
        original = reference["path"]
        actual = reference
        if original in copies:
            actual = copies[original]
            used_copies.add(original)
            require(
                actual["sha256"] == reference["sha256"],
                "history copy is not original bytes",
            )
        value = inputs.raw(actual["path"], reference["sha256"])
        require(
            "bytes" not in reference or len(value) == reference["bytes"],
            "history byte count differs",
        )
        if "mode" in reference and original not in copies:
            mode = reference["mode"]
            require(
                inputs.files[str(Path(actual["path"]).absolute())]["mode"]
                == (int(mode, 8) if isinstance(mode, str) else mode),
                "historical input mode differs",
            )
        return value

    def read(reference):
        return core.read_json(raw(reference))

    def original(path, expected=None):
        path = str(path)
        identity = inventory["inputs"].get(path)
        require(
            identity is not None or expected is not None,
            "historical original has no declared identity",
        )
        if identity is None:
            identity = {"sha256": expected}
        require(
            expected is None or identity["sha256"] == expected,
            "historical identity conflicts",
        )
        return {"path": path, **identity}

    for path, identity in inventory["inputs"].items():
        raw({"path": path, **identity})
    for name in ("experiment", "grading"):
        require(
            history[name]["sha256"]
            == inventory["current_owning_evidence"][name]["sha256"],
            "historical public pair differs from inventory",
        )
        raw(history[name])

    def embedded(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key.endswith("_utf8"):
                    require(
                        isinstance(child, str)
                        and digest(child.encode()) == value[key[:-5] + "_sha256"],
                        "embedded original grader bytes differ",
                    )
                else:
                    embedded(child)
        elif isinstance(value, list):
            for child in value:
                embedded(child)

    embedded(read(history["grading"]))
    embedded(read(history["experiment"]))
    batches = []

    def summarize_grades(artifacts, records):
        grades, supplements, sources = {}, {}, []
        for item in artifacts:
            ref = item["artifact"]
            value = read(ref)
            rows = value.get("runs", value.get("results"))
            require(isinstance(rows, list), "historical grade rows are absent")
            sources.append(member_identity(ref))
            for number, row in enumerate(rows):
                rid = row["run_id"]
                response = row.get(
                    "response_sha256", row.get("response", {}).get("sha256")
                )
                require(
                    rid in records and records[rid]["response_sha256"] == response,
                    "historical grade response differs",
                )
                judgments = row["expectations"]
                require(
                    judgments and all(type(j["passed"]) is bool for j in judgments),
                    "historical judgment is not Boolean",
                )
                require(
                    rid not in grades or grades[rid][0] == row,
                    "conflicting historical duplicate grade",
                )
                if rid not in grades:
                    grades[rid] = (row, [])
                grades[rid][1].append(
                    {
                        **member_identity(ref),
                        "pointer": f"/{'runs' if 'runs' in value else 'results'}/{number}",
                    }
                )
            findings = value.get(
                "supplementary_observations",
                value.get(
                    "supplementary_inaccuracies", value.get("supplemental_findings", [])
                ),
            )
            for finding in findings:
                sha = member_canonical(finding)
                require(
                    finding["run_id"] in records, "historical supplement run differs"
                )
                supplements[sha] = finding
        require(
            set(grades) == set(records), "historical independent grade coverage differs"
        )
        rows = []
        for rid, (grade, refs) in grades.items():
            judgments = grade["expectations"]
            rows.append(
                {
                    "original_run_id": rid,
                    "response_sha256": records[rid]["response_sha256"],
                    "record_sha256": records[rid]["record_sha256"],
                    "original_grade": refs,
                    "judgments": len(judgments),
                    "passed": sum(j["passed"] for j in judgments),
                    "original_judgment_sha256": [
                        member_canonical(j) for j in judgments
                    ],
                    "failed_judgments": [
                        i for i, j in enumerate(judgments) if not j["passed"]
                    ],
                }
            )
        return rows, supplements, sources, grades

    require(len(inventory["stopped_history"]) == 2, "stopped history coverage differs")
    for stopped, expected_counts in zip(
        inventory["stopped_history"], ((37, 14, 145, 143, 14), (3, 48, 18, 17, 3))
    ):
        manifest = read(stopped["manifest"])
        require(
            manifest == stopped["manifest_value"], "historical source manifest differs"
        )
        root = Path(stopped["manifest"]["path"]).parent
        for name, sha in manifest["source_sha256"].items():
            core.relative_path(name)
            raw(original(root / "source" / name, sha))
        specs = read(stopped["specifications"])
        read(stopped["grader_cases"])
        require(
            len(specs) == 51 and len({s["id"] for s in specs}) == 51,
            "stopped specification coverage differs",
        )
        specs_by_id = {s["id"]: s for s in specs}
        completed = {r["run_id"]: r for r in stopped["completed"]}
        unlaunched = {r["run_id"]: r for r in stopped["unlaunched"]}
        require(
            len(completed) == len(stopped["completed"])
            and len(unlaunched) == len(stopped["unlaunched"])
            and not set(completed) & set(unlaunched)
            and set(completed) | set(unlaunched) == set(specs_by_id),
            "stopped launched/unlaunched accounting differs",
        )
        records, absent = {}, []
        for rid, spec in specs_by_id.items():
            row = completed.get(rid, unlaunched.get(rid))
            require(
                row["spec_object_sha256"] == member_canonical(spec)
                and row["request_sha256"] == digest(spec["request"].encode())
                and row["case_id"] == spec["case_id"]
                and row["repetition"] == spec["repetition"]
                and row["fixture_sha256"] == spec["fixture_sha256"]
                and row["candidate_sha256"] == spec["candidate_sha256"],
                "historical specification differs",
            )
            if rid in unlaunched:
                require(
                    row["response_record_exists"] is False
                    and not (root.parent / rid).exists(),
                    "unlaunched historical run now has artifacts",
                )
                absent.append(
                    {
                        "original_run_id": rid,
                        "specification_sha256": row["spec_object_sha256"],
                        "request_sha256": row["request_sha256"],
                        "response_record_exists": False,
                    }
                )
                continue
            record = read(row["record"])
            directory = Path(row["record"]["path"]).parent
            require(
                record["id"] == rid
                and row["response_record_exists"] is True
                and digest(record["response"].encode())
                == row["response_sha256"]
                == record["response_sha256"]
                and record["request_sha256"] == row["request_sha256"],
                "historical record correspondence differs",
            )
            require(
                raw(original(directory / "request.txt")) == spec["request"].encode()
                and read(original(directory / "spec.json"))
                == {k: v for k, v in spec.items() if k != "request"},
                "historical request/specification bytes differ",
            )
            records[rid] = {
                "response_sha256": record["response_sha256"],
                "record_sha256": row["record"]["sha256"],
            }
        for grade in stopped["grades"]:
            source = read(grade["artifact"])["source_binding"]
            require(
                source["manifest_sha256"] == stopped["manifest"]["sha256"]
                and source["source_sha256"] == manifest["source_sha256"]
                and source["behavior_specs_sha256"]
                == stopped["specifications"]["sha256"]
                and source["grader_cases_sha256"] == stopped["grader_cases"]["sha256"],
                "historical grader source differs",
            )
        rows, findings, sources, _ = summarize_grades(stopped["grades"], records)
        require(
            read(stopped["adjudication"]) == stopped["adjudication_value"],
            "historical adjudication differs",
        )
        counts = (
            len(records),
            len(absent),
            sum(r["judgments"] for r in rows),
            sum(r["passed"] for r in rows),
            len(findings),
        )
        require(counts == expected_counts, "stopped historical counts differ")
        batches.append(
            {
                "name": stopped["name"],
                "source_manifest": member_identity(stopped["manifest"]),
                "source_sha256": manifest["source_sha256"],
                "original_grade_artifacts": sources,
                "completed": counts[0],
                "unlaunched": counts[1],
                "judgments": counts[2],
                "passed": counts[3],
                "runs": rows,
                "unlaunched_runs": absent,
                "adjudication": member_identity(stopped["adjudication"]),
                "supplements": [
                    {
                        "observation_sha256": sha,
                        "original_run_id": finding["run_id"],
                        "response_sha256": records[finding["run_id"]][
                            "response_sha256"
                        ],
                        "disposition": None,
                    }
                    for sha, finding in findings.items()
                ],
                "limitations": [
                    "Stopped diagnostic history; individual supplementary dispositions remain unresolved."
                ],
            }
        )
    writer = inventory["writer_composition_diagnostic"]
    manifest = read(writer["source_manifest"])
    require(
        manifest == writer["manifest_value"] and read(archive["manifest"]) == manifest,
        "writer archive source identity differs",
    )
    root = Path(archive["archive"])
    for name, sha in manifest["artifact_sha256"].items():
        core.relative_path(name)
        raw(original(root / name, sha))
    for name, sha in manifest["source_sha256"].items():
        core.relative_path(name)
        raw(original(root / "source" / name, sha))
    specifications = read(
        original(
            root / "behavior-specs.json",
            manifest["artifact_sha256"]["behavior-specs.json"],
        )
    )
    specifications_by_id = {row["id"]: row for row in specifications}
    require(
        len(specifications_by_id) == len(specifications),
        "writer historical specifications are duplicated",
    )
    require(
        len(archive["runs"]) == 51
        and len({r["original_run_id"] for r in archive["runs"]}) == 51,
        "complete writer archive requires 51 original records",
    )
    records = {}
    for row in archive["runs"]:
        record = read(row["original_record"])
        artifacts = {Path(ref["path"]).name: ref for ref in row["artifacts"]}
        require(
            len(artifacts) == len(row["artifacts"]) == 6
            and set(artifacts)
            == {
                "spec.json",
                "request.txt",
                "response.txt",
                "command.json",
                "stdout.jsonl",
                "stderr.txt",
            },
            "writer original artifact coverage differs",
        )
        contents = {name: raw(ref) for name, ref in artifacts.items()}
        spec = core.read_json(contents["spec.json"])
        require(
            record["id"] == spec["id"] == row["original_run_id"]
            and record["session_id"] == row["session_id"]
            and digest(contents["request.txt"])
            == record["request_sha256"]
            == row["request_sha256"]
            and digest(contents["response.txt"])
            == record["response_sha256"]
            == row["response_sha256"]
            and digest(contents["command.json"]) == record["command_sha256"]
            and digest(contents["stdout.jsonl"]) == record["stdout_sha256"]
            and digest(contents["stderr.txt"]) == record["stderr_sha256"],
            "writer original record/artifact differs",
        )
        prepared = specifications_by_id[record["id"]]
        require(
            spec == {key: value for key, value in prepared.items() if key != "request"}
            and contents["request.txt"] == prepared["request"].encode(),
            "writer historical prepared delivery differs",
        )
        if "response" in record:
            require(
                contents["response.txt"] == record["response"].encode(),
                "writer response bytes differ",
            )
        if "result" in record:
            require(
                contents["response.txt"] == record["result"]["result"].encode(),
                "writer terminal response differs",
            )
        records[record["id"]] = {
            "response_sha256": row["response_sha256"],
            "record_sha256": row["original_record"]["sha256"],
            "request_sha256": row["request_sha256"],
        }
    for artifact in writer["grades"]:
        value = read(artifact["artifact"])
        declared = value.get("input_manifest", {}).get(
            "sha256", value.get("inputs", {}).get("manifest_sha256")
        )
        require(
            declared == writer["source_manifest"]["sha256"],
            "writer original grader manifest differs",
        )
    rows, findings, sources, grades = summarize_grades(writer["grades"], records)
    for rid, (grade, _) in grades.items():
        require(
            grade.get("record_sha256", grade.get("record", {}).get("sha256"))
            == records[rid]["record_sha256"]
            and grade.get("request_sha256", grade.get("request", {}).get("sha256"))
            == records[rid]["request_sha256"],
            "writer grade original artifact differs",
        )
    adjudication = read(writer["accepted_supplementary_adjudication"])
    require(
        adjudication["source_map_sha256"] == writer["source_map"]["sha256"],
        "historical disposition source differs",
    )
    raw(writer["source_map"])
    dispositions = {
        row["observation_sha256"]: row for row in adjudication["observations"]
    }
    require(
        len(dispositions) == len(adjudication["observations"]) == len(findings) == 15
        and set(dispositions) == set(findings),
        "writer historical supplementary coverage differs",
    )
    supplements = []
    for sha, finding in findings.items():
        row = dispositions[sha]
        require(
            member_canonical(row["original_observation"]) == sha
            and row["run_id"] == finding["run_id"]
            and row["response"]["sha256"] == records[row["run_id"]]["response_sha256"],
            "historical supplementary observation differs",
        )
        raw(row["response"])
        raw(row["original_grade"])
        supplements.append(
            {
                "observation_sha256": sha,
                "original_run_id": row["run_id"],
                "response_sha256": row["response"]["sha256"],
                "disposition": row["determination"],
                "original_grade": member_identity(row["original_grade"]),
                "changes_original_grade": False,
            }
        )
    counts = (
        len(records),
        sum(r["judgments"] for r in rows),
        sum(r["passed"] for r in rows),
    )
    require(counts == (51, 195, 191), "writer historical counts differ")
    batches.append(
        {
            "name": writer["name"],
            "source_manifest": member_identity(writer["source_manifest"]),
            "source_sha256": manifest["source_sha256"],
            "original_grade_artifacts": sources,
            "completed": 51,
            "unlaunched": 0,
            "judgments": 195,
            "passed": 191,
            "runs": rows,
            "supplements": supplements,
            "adjudication": member_identity(
                writer["accepted_supplementary_adjudication"]
            ),
            "limitations": [
                "Diagnostic applications only; source assessments do not alter four false judgments."
            ],
        }
    )
    require(used_copies == set(copies), "unused history copy declaration")
    public = {
        "inventory": member_identity(history["inventory"]),
        "writer_archive": member_identity(history["writer_archive"]),
        "batches": batches,
        "limitations": [
            "Later originals retained privately; no historical row qualifies current source.",
            "Existing public history includes technical failures and incomplete wrapper observations.",
        ],
    }
    member_public(public)
    return public


def member_supplements(inputs, proposal, lineage, native_by_id, mapping):
    originals = [row["original_grader"] for row in lineage["runs"]]
    originals += [row["record"] for row in native_by_id.values()]
    files = {(r["path"], r["sha256"]) for r in originals}
    discovered = {}

    def visit(value, reference, pointer=""):
        if isinstance(value, dict):
            for key, child in value.items():
                here = pointer + "/" + key.replace("~", "~0").replace("/", "~1")
                if key == "supplementary_observations":
                    require(
                        isinstance(child, list),
                        "malformed current supplementary observations",
                    )
                    for number, observation in enumerate(child):
                        sha = member_canonical(observation)
                        require(
                            sha not in discovered,
                            "duplicate current supplementary observation",
                        )
                        discovered[sha] = (
                            observation,
                            {**reference, "pointer": f"{here}/{number}"},
                        )
                elif key in ("supplementary_inaccuracies", "supplemental_findings"):
                    raise ValueError("unsupported current supplementary container")
                else:
                    visit(child, reference, here)
        elif isinstance(value, list):
            for number, child in enumerate(value):
                visit(child, reference, f"{pointer}/{number}")

    for path, sha in sorted(files):
        visit(inputs.json(path, sha), {"path": path, "sha256": sha})
    rows = proposal["supplements"]
    require(
        isinstance(rows, list) and len(rows) == len(discovered),
        "supplementary disposition coverage differs",
    )
    runs = {row["original_run_id"]: row for row in mapping}
    require(len(runs) == 64, "current original run IDs conflict across methods")
    projected, seen = [], set()
    for row in rows:
        observation = inputs.reference(row["observation"])
        sha = member_canonical(observation)
        require(
            sha in discovered
            and sha not in seen
            and row["observation"] == discovered[sha][1],
            "supplementary disposition coverage or original pointer differs",
        )
        seen.add(sha)
        disposition = inputs.reference(row["disposition"])
        rid = observation["run_id"]
        require(
            rid in runs
            and observation["response_sha256"] == runs[rid]["response_sha256"]
            and disposition["observation_sha256"] == sha
            and disposition["run_id"] == rid
            and disposition["response_sha256"] == observation["response_sha256"]
            and isinstance(disposition["determination"], str)
            and disposition["determination"]
            and isinstance(disposition["source_revision"], str)
            and disposition["source_revision"],
            "supplementary original observation/disposition correspondence differs",
        )
        projected.append(
            {
                "run_id": runs[rid]["projected_run_id"],
                "original_run_id": rid,
                "observation_sha256": sha,
                "observation_source": member_identity(row["observation"]),
                "disposition_source": member_identity(row["disposition"]),
                "original_observation": observation,
                "original_disposition": disposition,
                "changes_original_grade": False,
            }
        )
    member_public(projected)
    return projected


def member_projection_payloads(projection_path, projection_sha256, output):
    core, _ = receipt_modules()
    inputs = ReceiptInputs()
    proposal = inputs.json(projection_path, projection_sha256)
    require(proposal["schema_version"] == 1, "unsupported member projection")
    reference = proposal["binding"]
    binding, bound_inputs = receipt_recheck_binding(
        Path(reference["path"]), reference["sha256"]
    )
    member_inputs(inputs, bound_inputs.files.values())
    repo = Path(binding["repository"])
    receipt_output(repo, output)
    require(not output.exists(), "member projection output already exists")
    lineage_ref = proposal["final_lineage"]
    lineage = inputs.reference(lineage_ref)
    require(
        lineage["schema_version"] == 1 and lineage["binding"] == reference,
        "final lineage binding differs",
    )
    member_inputs(inputs, lineage["inputs"])
    finalized = Path(lineage_ref["path"]).parent
    require(
        {str(p.relative_to(finalized)) for p in finalized.rglob("*") if p.is_file()}
        == set(lineage["files_sha256"]) | {Path(lineage_ref["path"]).name},
        "final artifact inventory differs",
    )
    for name, sha in lineage["files_sha256"].items():
        core.relative_path(name)
        inputs.raw(finalized / name, sha)
    snapshot = inputs.reference(binding["snapshot"])
    receipt = core.produce(repo, snapshot, finalized / "results.json")
    require(receipt == inputs.json(finalized / "receipt.json"), "final receipt differs")
    ordinary = core.evaluate(repo, receipt)
    report = inputs.json(finalized / "member-report.json")
    require(ordinary == report["ordinary"], "ordinary report differs")
    index = inputs.reference(lineage["observation_index"])
    require(
        index["binding"] == reference and index["triggers"] == lineage["triggers"],
        "final observation lineage differs",
    )
    member_inputs(inputs, index["inputs"])
    observed_root = Path(lineage["observation_index"]["path"]).parent
    require(
        {
            str(p.relative_to(observed_root))
            for p in observed_root.rglob("*")
            if p.is_file()
        }
        == set(index["files_sha256"])
        | {Path(lineage["observation_index"]["path"]).name},
        "observation artifact inventory differs",
    )
    for name, sha in index["files_sha256"].items():
        core.relative_path(name)
        require(
            inputs.raw(observed_root / name, sha) == inputs.raw(finalized / name),
            "final observed envelope differs",
        )
    native_grading = inputs.reference(proposal["native_grading"])
    require(
        native_grading["schema_version"] == 1 and len(native_grading["runs"]) == 13,
        "native grading coverage differs",
    )
    native_by_id = {row["run_id"]: row for row in native_grading["runs"]}
    require(
        len(native_by_id) == 13
        and set(native_by_id) == {r["run_id"] for r in binding["triggers"]},
        "native grading coverage is missing, duplicated, or extra",
    )
    behavior, native, grades, native_grades, requests, mapping, changes, thresholds = (
        member_current(
            inputs,
            proposal,
            binding,
            lineage,
            index,
            finalized,
            native_by_id,
            report,
            ordinary,
        )
    )
    supplementary = member_supplements(inputs, proposal, lineage, native_by_id, mapping)
    import copy

    history = proposal["history"]
    retained_history = member_history(inputs, history)
    old_experiment = inputs.reference(history["experiment"])
    old_grading = inputs.reference(history["grading"])
    require(
        len(old_experiment["behavior_runs"]) == 380
        and len(old_experiment["native_and_trigger_runs"]) == 78,
        "historical public record coverage differs",
    )
    prior = old_experiment["behavior_runs"] + old_experiment["native_and_trigger_runs"]
    all_runs = prior + behavior + native
    require(
        len({r["id"] for r in all_runs}) == len(all_runs), "projected run ID collision"
    )
    require(
        len({r["session_id"] for r in all_runs}) == len(all_runs),
        "projected session reused",
    )
    experiment = copy.deepcopy(old_experiment)
    experiment["behavior_runs"].extend(behavior)
    experiment["native_and_trigger_runs"].extend(native)
    for sha, text in requests.items():
        require(
            sha not in experiment["requests_by_sha256"]
            or experiment["requests_by_sha256"][sha] == text,
            "projected request digest conflict",
        )
        experiment["requests_by_sha256"][sha] = text
    experiment.setdefault("selection_history", []).append(
        {
            "selection": old_experiment["selection"],
            "experiment": member_identity(history["experiment"]),
            "grading": member_identity(history["grading"]),
        }
    )
    sha = proposal["binding"]["sha256"]
    experiment["selection"] = {
        "behavior_by_case": {str(n): "relation-" + sha for n in range(17)},
        "trigger_experiment": "relation-native-" + sha,
    }
    experiment["retained_private_history"] = retained_history
    experiment["selected_source_revision"] = binding["source_revision"]
    source_paths = set().union(*(r["delivered_source_sha256"] for r in binding["runs"]))
    folder = "evals/mergecraft/skills/maintaining-issue-pr-relations"
    source_paths.update(
        folder + "/" + name
        for name in ("evals.json", "policy.json", "trigger-evals.json")
    )
    experiment["current_source_sha256"] = {
        name: digest(core.source_bytes(repo, binding["source_revision"], name))
        for name in sorted(source_paths)
    }
    require(len(source_paths) == 45, "current member source coverage differs")
    candidate_passed = all(t["met"] for t in thresholds) and all(
        g["passed"] for g in native_grades
    )
    grading = {
        "schema_version": 1,
        "preparation_binding_sha256": sha,
        "selected_source_revision": binding["source_revision"],
        "runs": grades,
        "trigger_runs": native_grades,
        "thresholds": thresholds,
        "candidate_passed": candidate_passed,
        "supplementary_dispositions": supplementary,
        "previous_selected_grading": old_grading,
    }
    normalization = {
        "schema_version": 1,
        "preparation_binding_sha256": sha,
        "runs": mapping,
        "metadata": changes,
        "previous_experiment": member_identity(history["experiment"]),
        "previous_grading": member_identity(history["grading"]),
    }
    inverse = {
        "remove_keys": sorted(set(experiment) - set(old_experiment)),
        "replace_values": {
            key: value
            for key, value in old_experiment.items()
            if key
            not in ("behavior_runs", "native_and_trigger_runs", "requests_by_sha256")
            and experiment[key] != value
        },
        "list_lengths": {
            key: len(old_experiment[key])
            for key in ("behavior_runs", "native_and_trigger_runs")
        },
        "remove_request_keys": sorted(
            set(requests) - set(old_experiment["requests_by_sha256"])
        ),
    }
    recovered = copy.deepcopy(experiment)
    for key in inverse["remove_keys"]:
        del recovered[key]
    recovered.update(inverse["replace_values"])
    for key, length in inverse["list_lengths"].items():
        del recovered[key][length:]
    for key in inverse["remove_request_keys"]:
        del recovered["requests_by_sha256"][key]
    require(
        encode(recovered)
        == inputs.raw(history["experiment"]["path"], history["experiment"]["sha256"])
        and encode(old_grading)
        == inputs.raw(history["grading"]["path"], history["grading"]["sha256"]),
        "historical public byte reconstruction differs",
    )
    normalization["history_inverse"] = {
        "experiment": inverse,
        "grading": {"pointer": "/previous_selected_grading"},
        "encoding": "UTF-8 JSON, insertion order, indent=2, ensure_ascii=False, terminal LF",
    }
    payloads = {
        "experiment.json": encode(experiment),
        "grading.json": encode(grading),
        "normalization.json": encode(normalization),
    }
    inputs.recheck()
    verification = {
        "schema_version": 1,
        "projection": {
            "path": str(projection_path.absolute()),
            "sha256": projection_sha256,
        },
        "binding": proposal["binding"],
        "source_revision": binding["source_revision"],
        "candidate_passed": candidate_passed,
        "judgments": sum(len(g["expectations"]) for g in grades),
        "ordinary": ordinary,
        "inputs": sorted(inputs.files.values(), key=lambda r: r["path"]),
        "files_sha256": {name: digest(raw) for name, raw in payloads.items()},
        "limits": [
            "Offline correspondence only; no provider authenticity or semantic qualification."
        ],
    }
    payloads["verification-report.json"] = encode(verification)
    return payloads


def member_project(projection_path, projection_sha256, output):
    payloads = member_projection_payloads(projection_path, projection_sha256, output)
    verification = json.loads(payloads["verification-report.json"])
    output.mkdir(mode=0o700)
    for name, raw in payloads.items():
        create(output / name, raw)
    require(
        all((output / name).read_bytes() == raw for name, raw in payloads.items()),
        "member output reread differs",
    )
    return {
        "candidate_passed": verification["candidate_passed"],
        "applications": 51,
        "judgments": 195,
        "native_grades": 13,
        "files_sha256": {name: digest(raw) for name, raw in payloads.items()},
    }


def receipt_reconciliation(projection_path, projection_sha256, output):
    """Export original observations for separate current-source reconciliation."""
    core, _ = receipt_modules()
    member = member_projection_payloads(projection_path, projection_sha256, output)
    verification = core.read_json(member["verification-report.json"])
    inputs = ReceiptInputs()
    member_inputs(inputs, verification["inputs"])
    proposal = inputs.json(projection_path, projection_sha256)
    binding = inputs.reference(proposal["binding"])
    lineage = inputs.reference(proposal["final_lineage"])
    finalized = Path(proposal["final_lineage"]["path"]).parent
    results = inputs.json(finalized / "results.json")
    repo = Path(binding["repository"])
    require("rubrics" in binding, "original preparation lacks reconciliation rubrics")
    payloads = {"member/" + name: raw for name, raw in member.items()}
    copies = {}

    def reference(path, pointer="", format="json"):
        path = Path(path).absolute()
        raw = inputs.raw(path)
        name = "originals/" + digest(raw)
        payloads[name] = raw
        copies[str(path)] = {
            "original": inputs.files[str(path)],
            "copy": name,
        }
        return {
            "path": name,
            "sha256": digest(raw),
            "format": format,
            "pointer": pointer,
        }

    def retained(original):
        inputs.raw(original["path"], original["sha256"])
        return reference(
            original["path"],
            original.get("pointer", ""),
            original.get("format", "json"),
        )

    def pointer(value):
        return str(value).replace("~", "~0").replace("/", "~1")

    runs, runtime_cases = [], {}
    for bound, observed, result in zip(
        binding["runs"], lineage["runs"], results["runs"]
    ):
        directory = Path(bound["directory"])
        record = inputs.json(directory / "record.json")
        original = record.get("reconciliation_execution")
        require(
            isinstance(original, dict),
            "original execution lacks supported recording-time shape",
        )
        require(
            original
            == {
                "case_id": bound["case_id"]["id"],
                "repetition": bound["repetition"],
                "response_sha256": record["response_sha256"],
                "execution": {
                    "completed": True,
                    "returncode": 0,
                    "thread_ids": [record["session_id"]],
                    "response_sha256": record["response_sha256"],
                },
            }
            and record["technically_valid"] is True
            and record["session_id"]
            == record["init"]["session_id"]
            == record["result"]["session_id"],
            "original recorded execution differs from matched session, response, or coordinate",
        )
        request_path = directory / "request.txt"
        request = inputs.json(request_path)
        runtime = sorted(request["candidate_bundle"])
        runtime_cases[str(bound["case_id"]["id"])] = {
            "case_id": bound["case_id"],
            "runtime_inputs": runtime,
        }
        delivered = {
            path: {
                "representation": "utf8",
                "value": reference(request_path, "/candidate_bundle/" + pointer(path)),
            }
            for path in runtime
        }
        delivered.update(
            {
                "evals/mergecraft/skills/" + path: {
                    "representation": "utf8",
                    "value": reference(request_path, "/fixture/" + pointer(path)),
                }
                for path in request["fixture"]
            }
        )
        rubric = reference(
            proposal["binding"]["path"], "/rubrics/" + pointer(bound["case_id"]["id"])
        )
        grader = observed["grader_model"]
        runs.append(
            {
                "case_id": bound["case_id"],
                "repetition": bound["repetition"],
                "execution_record": reference(
                    directory / "record.json", "/reconciliation_execution"
                ),
                "original_revision": reference(
                    proposal["binding"]["path"], "/source_revision"
                ),
                "original_corpus_sha256": reference(
                    binding["snapshot"]["path"],
                    "/inputs/" + pointer(RELATION_EVALS + "/evals.json") + "/sha256",
                ),
                "prompt": reference(request_path, "/prompt"),
                "response": reference(directory / "response.txt", format="utf8"),
                "inputs": delivered,
                "executor_model": {
                    "basis": "requested",
                    "value": reference(directory / "record.json", "/model_requested"),
                },
                "grader_model": {
                    "basis": grader["basis"],
                    "value": retained(grader["reference"]),
                },
                "grading_record": retained(observed["original_grader"]),
                "graded_response": {
                    "representation": "sha256",
                    "value": reference(
                        observed["original_grader"]["path"], "/response_sha256"
                    ),
                },
                "original_expectations": rubric,
                "rubric": {"representation": "expectations", "value": rubric},
                "grades": reference(finalized / result["grading"], "/expectations"),
                "previous_grading": [
                    retained(item) for item in observed["previous_grading"]
                ],
                "adjudication": retained(observed["adjudication"])
                if observed["adjudication"] is not None
                else None,
            }
        )
    triggers = []
    for number, (bound, observed) in enumerate(
        zip(binding["triggers"], lineage["triggers"])
    ):
        directory = Path(bound["directory"])
        triggers.append(
            {
                "case_id": bound["case_id"],
                "observation_kind": "recorded-invocation",
                "record": reference(directory / "record.json"),
                "model": {
                    "basis": "requested",
                    "value": reference(directory / "record.json", "/model_requested"),
                },
                "query": reference(
                    repo / RELATION_EVALS / "trigger-evals.json", f"/{number}/query"
                ),
                "entrypoint": {
                    "representation": "utf8",
                    "value": reference(repo / RELATION / "SKILL.md", format="utf8"),
                },
                "triggered": reference(
                    finalized / observed["observation"], "/triggered"
                ),
                "limits": [
                    binding["limits"],
                    "Invocation Boolean is projected from retained original call/result/source correspondence; independent native grades remain in the strict member result.",
                ],
            }
        )
    declaration = {
        "schema_version": 1,
        "method": "reconciled-after-run",
        "executor_model_id": binding["executor_model_id"],
        "grader_model_id": binding["grader_model"]["id"],
        "runtime_inputs": sorted(
            {path for row in runtime_cases.values() for path in row["runtime_inputs"]}
        ),
        "runtime_inputs_complete": True,
        "case_runtime_inputs": list(runtime_cases.values()),
        "runs": runs,
        "triggers": triggers,
    }
    core.validate(declaration, "reconciliationResults")
    # Preserve the complete original provenance, including streams, envelopes,
    # independent native grades, history, and failed or adjudicated judgments.
    for identity in list(inputs.files.values()):
        reference(identity["path"], format="utf8")
    payloads["reconciliation.json"] = encode(declaration)
    payloads["provenance.json"] = encode(
        {
            "schema_version": 1,
            "original_source_revision": binding["source_revision"],
            "projection": {
                "path": str(projection_path.absolute()),
                "sha256": projection_sha256,
            },
            "binding": proposal["binding"],
            "lineage": proposal["final_lineage"],
            "copies": list(copies.values()),
            "candidate_passed": verification["candidate_passed"],
            "judgments": 195,
            "native_grades": 13,
            "reconciliation_sha256": digest(payloads["reconciliation.json"]),
            "limits": [
                binding["limits"],
                "This is a private export, not a new execution, Receipt, or landing authorization. Select Q and the supported P in the separate maintained reconciliation command.",
            ],
        }
    )
    inputs.recheck()
    output.mkdir(mode=0o700)
    for name, raw in payloads.items():
        create(output / name, raw)
    require(
        all((output / name).read_bytes() == raw for name, raw in payloads.items()),
        "reconciliation export reread differs",
    )
    return {
        "candidate_passed": verification["candidate_passed"],
        "applications": 51,
        "judgments": 195,
        "native_grades": 13,
        "reconciliation_sha256": digest(payloads["reconciliation.json"]),
        "original_source_revision": binding["source_revision"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    preparation = sub.add_parser("prepare")
    preparation.add_argument("--repo", type=Path, required=True)
    preparation.add_argument("--output", type=Path, required=True)
    preparation.add_argument("--claude", type=Path, required=True)
    checking = sub.add_parser("verify")
    checking.add_argument("--evaluation", type=Path, required=True)
    checking.add_argument("--repo", type=Path)
    running = sub.add_parser("run")
    running.add_argument("--evaluation", type=Path, required=True)
    running.add_argument("--repo", type=Path, required=True)
    running.add_argument("--manifest-sha256", required=True)
    running.add_argument("--run-id", action="append", required=True)
    collecting = sub.add_parser("collect")
    collecting.add_argument("--evaluation", type=Path, required=True)
    collecting.add_argument("--repo", type=Path, required=True)
    collecting.add_argument("--suite", choices=("markdown", "relations"), required=True)
    collecting.add_argument("--case", type=int, required=True)
    collecting.add_argument("--output", type=Path, required=True)
    binding = sub.add_parser("receipt-bind")
    for name in ("repo", "descriptor", "snapshot", "preparations", "output"):
        binding.add_argument("--" + name, type=Path, required=True)
    binding.add_argument("--revision", required=True)
    observation = sub.add_parser("receipt-observe")
    for name in ("binding", "observations", "output"):
        observation.add_argument("--" + name, type=Path, required=True)
    observation.add_argument("--binding-sha256", required=True)
    results = sub.add_parser("receipt-results")
    for name in ("binding", "observation-index", "grading", "output"):
        results.add_argument("--" + name, type=Path, required=True)
    for name in ("binding-sha256", "observation-index-sha256"):
        results.add_argument("--" + name, required=True)
    projection = sub.add_parser("member-project")
    projection.add_argument("--projection", type=Path, required=True)
    projection.add_argument("--projection-sha256", required=True)
    projection.add_argument("--output", type=Path, required=True)
    reconciliation = sub.add_parser("receipt-reconciliation")
    reconciliation.add_argument("--projection", type=Path, required=True)
    reconciliation.add_argument("--projection-sha256", required=True)
    reconciliation.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "receipt-reconciliation":
            print(
                json.dumps(
                    receipt_reconciliation(
                        args.projection, args.projection_sha256, args.output
                    )
                )
            )
            return 0
        if args.command == "member-project":
            print(
                json.dumps(
                    member_project(args.projection, args.projection_sha256, args.output)
                )
            )
            return 0
        if args.command == "receipt-results":
            print(
                json.dumps(
                    receipt_results(
                        args.binding,
                        args.binding_sha256,
                        args.observation_index,
                        args.observation_index_sha256,
                        args.grading,
                        args.output,
                    )
                )
            )
            return 0
        if args.command == "receipt-observe":
            print(
                json.dumps(
                    receipt_observe(
                        args.binding,
                        args.binding_sha256,
                        args.observations,
                        args.output,
                    )
                )
            )
            return 0
        if args.command == "receipt-bind":
            print(
                json.dumps(
                    receipt_bind(
                        args.repo,
                        args.revision,
                        args.descriptor,
                        args.snapshot,
                        args.preparations,
                        args.output,
                    )
                )
            )
            return 0
        if args.command == "prepare":
            manifest = prepare(args.repo, args.output, args.claude)
        elif args.command == "run":
            return (
                0
                if run_batch(
                    args.evaluation, args.repo, args.manifest_sha256, args.run_id
                )
                else 1
            )
        elif args.command == "collect":
            collect(args.evaluation, args.repo, args.suite, args.case, args.output)
            return 0
        else:
            manifest = verify(args.evaluation, args.repo)
        print(
            json.dumps(
                {
                    "behavior_counts": manifest["behavior_counts"],
                    "source_files": len(manifest["source_sha256"]),
                }
            )
        )
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        subprocess.SubprocessError,
    ) as error:
        parser.exit(1, f"{error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
