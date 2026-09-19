"""Record one explicitly delivered #111 Codex application attempt."""

import argparse
import datetime
import hashlib
import json
import math
import subprocess
import time
from pathlib import Path

from .receipt_artifacts import verify_manifest


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_new(path, value):
    with path.open("x", encoding="utf-8", newline="") as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=True) + "\n")


def unique_event_fields(pairs):
    event = {}
    for key, value in pairs:
        if key in event:
            raise ValueError(f"duplicate JSON field: {key!r}")
        event[key] = value
    return event


def finite_event_number(text):
    value = float(text)
    if not math.isfinite(value):
        raise ValueError(f"non-finite JSON number: {text}")
    return value


def observe(
    run,
    code,
    elapsed,
    started_at,
    finished_at,
    coordinate,
    launch_error=None,
    timed_out=False,
):
    events = []
    unparsed = []
    protocol_errors = []
    decoded, encoding_errors = {}, []
    for stream, filename in (("stdout", "transcript.jsonl"), ("stderr", "stderr.log")):
        try:
            decoded[stream] = (run / filename).read_bytes().decode("utf-8")
        except UnicodeDecodeError as error:
            decoded[stream] = ""
            encoding_errors.append(
                {
                    "stream": stream,
                    "start": error.start,
                    "end": error.end,
                    "reason": error.reason,
                }
            )
    for index, line in enumerate(decoded["stdout"].split("\n"), 1):
        if not line.strip(" \t\r"):
            continue
        try:
            event = json.loads(
                line,
                object_pairs_hook=unique_event_fields,
                parse_constant=finite_event_number,
                parse_float=finite_event_number,
            )
            if not isinstance(event, dict) or (
                "item" in event and not isinstance(event["item"], dict)
            ):
                raise ValueError("event or item is not an object")
            events.append(event)
        except ValueError as error:
            unparsed.append({"line": index, "text": line})
            protocol_errors.append({"line": index, "error": str(error)})
    messages = []
    for event in events:
        if (
            event.get("type") == "item.completed"
            and event.get("item", {}).get("type") == "agent_message"
        ):
            message = event["item"].get("text")
            if isinstance(message, str):
                messages.append(message)
            else:
                protocol_errors.append({"error": "agent message is not text"})
    tool_items = [
        event.get("item")
        for event in events
        if event.get("item", {}).get("type")
        not in (None, "agent_message", "reasoning", "error")
    ]
    completed = any(event.get("type") == "turn.completed" for event in events)
    response = "\n".join(messages)
    try:
        response.encode("utf-8")
    except UnicodeEncodeError:
        protocol_errors.append({"error": "response contains an unpaired surrogate"})
        response = ""
    result = {
        "coordinate": coordinate,
        "launch_error": launch_error,
        "timed_out": timed_out,
        "encoding_errors": encoding_errors,
        "protocol_errors": protocol_errors,
        "returncode": code,
        "completed": completed,
        "started_at_utc": started_at,
        "finished_at_utc": finished_at,
        "duration_seconds": elapsed,
        "tool_items": tool_items,
        "response_sha256": sha(response.encode()),
        "transcript_sha256": sha((run / "transcript.jsonl").read_bytes()),
        "stderr_sha256": sha((run / "stderr.log").read_bytes()),
        "warnings": [
            event["item"].get("message")
            for event in events
            if event.get("item", {}).get("type") == "error"
        ],
        "thread_ids": [
            event.get("thread_id")
            for event in events
            if event.get("type") == "thread.started"
        ],
        "usage": [
            event.get("usage")
            for event in events
            if event.get("type") == "turn.completed"
        ],
        "unparsed_transcript_lines": unparsed,
        "valid_application": code == 0
        and completed
        and bool(response.strip())
        and not tool_items
        and not unparsed
        and not encoding_errors
        and not protocol_errors
        and launch_error is None
        and not timed_out,
    }
    return response, result


def inspect(
    run,
    code,
    elapsed,
    started_at,
    finished_at,
    coordinate,
    launch_error=None,
    timed_out=False,
):
    response, result = observe(
        run, code, elapsed, started_at, finished_at, coordinate, launch_error, timed_out
    )
    with (run / "response.txt").open("x", encoding="utf-8", newline="") as stream:
        stream.write(response)
    write_new(run / "result.json", result)
    return result


def record_attempt(run, command, prompt, coordinate, metadata, timeout=180):
    run.mkdir(parents=True, exist_ok=False)
    write_new(run / "command.json", command)
    write_new(run / "launch-metadata.json", metadata)
    started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    started = time.monotonic()
    code, launch_error, timed_out = None, None, False
    with (
        (run / "transcript.jsonl").open("xb") as out,
        (run / "stderr.log").open("xb") as err,
    ):
        try:
            code = subprocess.run(
                command,
                input=prompt,
                stdout=out,
                stderr=err,
                timeout=timeout,
                check=False,
            ).returncode
        except subprocess.TimeoutExpired:
            code = 124
            timed_out = True
        except OSError as error:
            launch_error = str(error)
    finished_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return inspect(
        run,
        code,
        round(time.monotonic() - started, 3),
        started_at,
        finished_at,
        coordinate,
        launch_error,
        timed_out,
    )


def execute(root, expected_manifest, number, repetition):
    manifest = verify_manifest(root, expected_manifest)
    if (
        manifest.get("status") != "prepared-final-source-awaiting-launch-review"
        or (root / "STOP_LAUNCHES").exists()
    ):
        raise ValueError("final source or launch review is pending")
    client = manifest["client_binding"]
    if sha(Path(client["path"]).read_bytes()) != client["sha256"]:
        raise ValueError("Codex client differs")
    if list((root / "cwd").iterdir()):
        raise ValueError("application working directory is not empty")
    coordinate = next(
        c
        for c in manifest["run_coordinates"]
        if c["case"] == number and c["repetition"] == repetition
    )
    metadata = next(c for c in manifest["coordinates"] if c["id"] == number)
    case = root / f"eval-{number}/with_skill"
    prompt = (case / "prompt.txt").read_bytes()
    if (
        sha(prompt) != metadata["submitted_prompt_sha256"]
        or sha((case / "request.json").read_bytes()) != metadata["request_sha256"]
    ):
        raise ValueError("request or prompt differs")
    result = record_attempt(
        root / coordinate["output_directory"],
        command_for(root, manifest),
        prompt,
        coordinate,
        launch_metadata(manifest, expected_manifest, metadata, coordinate),
        timeout=manifest["timeout_seconds"],
    )
    verify_manifest(root, expected_manifest)
    write_new(
        root / coordinate["output_directory"] / "execution-record.json",
        execution_record(manifest, expected_manifest, metadata, coordinate, result),
    )
    return result


def command_for(root, manifest):
    return [
        manifest["client_binding"]["path"],
        "exec",
        "--json",
        "--ephemeral",
        "--ignore-user-config",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "-C",
        str(root / "cwd"),
        "-m",
        "gpt-6-astra",
        "-c",
        "model_reasoning_effort=xhigh",
        "-",
    ]


def launch_metadata(manifest, expected_manifest, metadata, coordinate):
    return {
        "manifest_sha256": expected_manifest,
        "request_sha256": metadata["request_sha256"],
        "submitted_prompt_sha256": metadata["submitted_prompt_sha256"],
        "harness_version": "codex-cli " + manifest["client_binding"]["version"],
        "requested_model": manifest["requested_model"],
        "requested_effort": manifest["requested_effort"],
        "client_sha256": manifest["client_binding"]["sha256"],
        "coordinate": coordinate,
        "receipt_case_id": metadata["receipt_case_id"],
        "receipt_snapshot_sha256": manifest["receipt"]["snapshot_sha256"],
        "receipt_snapshot_file_sha256": manifest["receipt"]["snapshot_file_sha256"],
        "source_revision": manifest["receipt"]["source_revision"],
        "runtime_inputs": metadata["input_paths"],
        "input_evidence": metadata["input_evidence"],
    }


def execution_record(manifest, manifest_hash, metadata, coordinate, result):
    """Written by the recorder at completion, including failed ordinary attempts."""
    return {
        "kind": "pr-writing-original-execution",
        "case": coordinate["case"],
        "repetition": coordinate["repetition"],
        "source_revision": manifest["receipt"]["source_revision"],
        "original_corpus_sha256": manifest["corpus_sha256"],
        "runner_manifest_sha256": manifest_hash,
        "request_sha256": metadata["request_sha256"],
        "submitted_prompt_sha256": metadata["submitted_prompt_sha256"],
        "runtime_inputs": metadata["input_paths"],
        "inputs": metadata["input_evidence"],
        "requested_model": manifest["requested_model"],
        "requested_effort": manifest["requested_effort"],
        "execution": result,
        "response_sha256": result["response_sha256"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--case", type=int, choices=range(11), required=True)
    parser.add_argument("--repetition", type=int, choices=range(1, 4), required=True)
    args = parser.parse_args()
    result = execute(
        args.root.resolve(), args.manifest_sha256, args.case, args.repetition
    )
    print(
        json.dumps(
            {
                "case": args.case,
                "repetition": args.repetition,
                "valid_application": result["valid_application"],
                "returncode": result["returncode"],
            }
        )
    )
    raise SystemExit(0 if result["valid_application"] else 1)
