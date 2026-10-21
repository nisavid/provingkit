"""Prepare preserved inputs for bounded startup collection."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time

from trace_adapter import TraceAdapter


INITIALIZE = {
    "id": 1, "method": "initialize",
    "params": {
        "clientInfo": {"name": "compatibility-native-preparation", "version": "2"},
        "capabilities": {"experimentalApi": True},
    },
}
LIMITS = {"pipe_bytes": 2 * 1024 * 1024, "message_bytes": 256 * 1024,
          "startup_seconds": 30, "term_seconds": 5, "kill_seconds": 5}
RECORD_BYTES = 64 * 1024
OUTCOME_BYTES = 96 * 1024


def bounded_record(path):
    with path.open("rb") as stream:
        raw = stream.read(RECORD_BYTES + 1)
    if len(raw) > RECORD_BYTES:
        raise ValueError("record limit")
    return raw


def encoded_record(value):
    raw = (json.dumps(value, indent=2) + "\n").encode()
    if len(raw) > RECORD_BYTES:
        raise ValueError("record limit")
    return raw


def bounded_limits(spec):
    result = LIMITS.copy()
    supplied = spec.get("limits", {})
    if not isinstance(supplied, dict):
        raise ValueError("invalid limits")
    for key, value in supplied.items():
        if (key not in LIMITS or type(value) not in (int, float)
                or not math.isfinite(value) or not 0 < value <= LIMITS[key]
                or (key.endswith("bytes") and type(value) is not int)):
            raise ValueError("invalid limits")
        result[key] = value
    return result


def file_identity(path):
    requested = str(path.absolute())
    path = path.resolve(strict=True)
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            size += len(chunk)
            digest.update(chunk)
    return {"path": str(path), "requested_path": requested,
            "bytes": size, "sha256": digest.hexdigest()}


def prepare(spec_path, output):
    raw = bounded_record(spec_path)
    spec = json.loads(raw)
    validate_spec(spec)
    inputs = [Path(__file__), Path(__file__).with_name("trace_adapter.py"),
              Path(spec["command"][0]), *map(Path, spec["sources"])]
    identities = [file_identity(p) for p in dict.fromkeys(inputs)]
    manifest = encoded_record({
        "schema": 1,
        "spec_sha256": hashlib.sha256(raw).hexdigest(),
        "inputs": identities,
    })
    output.mkdir()
    (output / "spec.json").write_bytes(raw)
    (output / "manifest.json").write_bytes(manifest)
    return {"prepared": str(output)}


def validate_spec(spec):
    required = {"schema", "command", "cwd", "sources", "expected_initialize"}
    if (not isinstance(spec, dict) or not required <= spec.keys()
            or set(spec) - required - {"limits", "trace"}):
        raise ValueError("invalid specification fields")
    if type(spec.get("schema")) is not int or spec["schema"] != 1:
        raise ValueError("unsupported specification revision")
    command = spec["command"]
    if (not isinstance(command, list) or not 1 <= len(command) <= 128
            or any(type(arg) is not str or "\0" in arg for arg in command)
            or not Path(command[0]).is_absolute()):
        raise ValueError("invalid command vector")
    if type(spec["cwd"]) is not str or not Path(spec["cwd"]).is_absolute():
        raise ValueError("invalid working directory")
    if (not isinstance(spec["sources"], list) or len(spec["sources"]) > 128
            or any(type(p) is not str or not Path(p).is_absolute() for p in spec["sources"])):
        raise ValueError("invalid source list")
    metadata = spec["expected_initialize"]
    if (not isinstance(metadata, dict)
            or set(metadata) != {"userAgent", "codexHome", "platformFamily", "platformOs"}
            or any(type(value) is not str for value in metadata.values())):
        raise ValueError("invalid initialize projection")
    bounded_limits(spec)
    trace = spec.get("trace")
    if trace is not None and trace != {"binding": "strace-source-subset/v1"}:
        raise ValueError("unsupported trace binding")
    has_trace_fd = any("{trace_fd}" in arg for arg in spec["command"])
    if has_trace_fd != (trace is not None):
        raise ValueError("trace command mismatch")


def run(package, output):
    output.mkdir()
    raw_spec = bounded_record(package / "spec.json")
    raw_manifest = bounded_record(package / "manifest.json")
    manifest = json.loads(raw_manifest)
    (output / "spec.json").write_bytes(raw_spec)
    (output / "manifest.json").write_bytes(raw_manifest)

    def finish(outcome):
        outcome["package_manifest_sha256"] = hashlib.sha256(raw_manifest).hexdigest()
        # Compact UTF-8 keeps the four matched strings within their original
        # specification budget. Escape lone surrogates as valid JSON bytes.
        raw = (json.dumps(outcome, ensure_ascii=False, separators=(",", ":"))
               + "\n").encode("utf-8", errors="backslashreplace")
        if len(raw) > OUTCOME_BYTES:
            outcome["initialize"] = None
            outcome["observed_reason"] = outcome["reason"]
            outcome["reason"] = "outcome_projection_limit"
            outcome["omitted_outcome_sha256"] = hashlib.sha256(raw).hexdigest()
            raw = encoded_record(outcome)
        (output / "outcome.json").write_bytes(raw)
        return outcome

    changed = hashlib.sha256(raw_spec).hexdigest() != manifest["spec_sha256"]
    try:
        changed |= any(file_identity(Path(item["requested_path"])) != item for item in manifest["inputs"])
    except OSError:
        changed = True
    if changed:
        return finish({"reason": "input_changed", "launched": False})
    spec = json.loads(raw_spec)
    validate_spec(spec)
    request = json.dumps(INITIALIZE).encode() + b"\n"
    trace_read = trace_write = None
    if spec.get("trace") is not None:
        trace_read, trace_write = os.pipe()
    command = [arg.replace("{trace_fd}", str(trace_write)) for arg in spec["command"]]
    started = time.monotonic()
    try:
        process = subprocess.Popen(
            command, cwd=spec["cwd"], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            start_new_session=True,
            pass_fds=() if trace_write is None else (trace_write,),
        )
    except OSError:
        if trace_read is not None:
            os.close(trace_read)
            os.close(trace_write)
        return finish({"reason": "launch_error", "launched": False,
                       "elapsed_seconds": time.monotonic() - started})
    if trace_write is not None:
        os.close(trace_write)
    trace_output = (output / "trace.jsonl").open("xb") if trace_read is not None else None
    trace = TraceAdapter(trace_output, process.pid) if trace_output is not None else None
    limits = bounded_limits(spec)
    counts = {"stdout": 0, "stderr": 0}
    eof = {"stdout": False, "stderr": False}
    buffered = bytearray()
    metadata = None
    reason = None
    try:
        process.stdin.write(request)
        process.stdin.flush()
        (output / "sent.jsonl").write_bytes(request)
    except OSError:
        reason = "request_delivery_unknown"

    def receive(selector, wait):
        nonlocal metadata, reason
        for key, _ in selector.select(wait):
            if key.data == "trace":
                chunk = os.read(trace_read, 4096)
                if chunk:
                    trace.feed(chunk)
                else:
                    trace.finish()
                if trace.terminal is not None:
                    selector.unregister(trace_read)
                continue
            remaining = limits["pipe_bytes"] - sum(counts.values())
            if remaining <= 0:
                reason = "pipe_limit"
                return
            chunk = os.read(key.fileobj.fileno(), min(4096, remaining))
            counts[key.data] += len(chunk)
            if not chunk:
                eof[key.data] = True
                selector.unregister(key.fileobj)
                continue
            if reason not in (None, "initialized"):
                continue
            if key.data == "stdout":
                buffered.extend(chunk)
                while b"\n" in buffered:
                    line, _, tail = buffered.partition(b"\n")
                    buffered[:] = tail
                    if len(line) > limits["message_bytes"]:
                        reason = "message_limit"
                        return
                    try:
                        response = json.loads(line)
                    except (ValueError, UnicodeError):
                        reason = "malformed_response"
                        return
                    if metadata is not None:
                        reason = "unsolicited_response"
                        return
                    if (not isinstance(response, dict)
                            or type(response.get("id")) is not int
                            or response != {"id": 1, "result": spec["expected_initialize"]}):
                        reason = "response_mismatch"
                        return
                    metadata = response["result"]
                    reason = "initialized"
                if len(buffered) > limits["message_bytes"]:
                    reason = "message_limit"
                    return
            if sum(counts.values()) >= limits["pipe_bytes"]:
                reason = "pipe_limit"
                return

    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ, "stdout")
        selector.register(process.stderr, selectors.EVENT_READ, "stderr")
        if trace_read is not None:
            selector.register(trace_read, selectors.EVENT_READ, "trace")
        deadline = started + limits["startup_seconds"]
        while reason is None and selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                reason = "startup_timeout"
                break
            receive(selector, min(remaining, 0.05))
        reason = reason or "premature_eof"
        try:
            process.stdin.close()
        except OSError:
            pass
        for sig, window in ((signal.SIGTERM, limits["term_seconds"]),
                            (signal.SIGKILL, limits["kill_seconds"])):
            if process.poll() is None or selector.get_map():
                try:
                    os.killpg(process.pid, sig)
                except ProcessLookupError:
                    pass
            stop = time.monotonic() + window
            while time.monotonic() < stop:
                if process.poll() is not None and not selector.get_map():
                    break
                if sum(counts.values()) >= limits["pipe_bytes"]:
                    for key in list(selector.get_map().values()):
                        if key.data != "trace":
                            selector.unregister(key.fileobj)
                    if process.poll() is not None:
                        break
                if selector.get_map():
                    receive(selector, min(0.05, max(0, stop - time.monotonic())))
                else:
                    time.sleep(0.01)
            if process.poll() is not None and not selector.get_map():
                break
        if buffered and reason == "initialized":
            reason = "incomplete_response"
    process.stdout.close()
    process.stderr.close()
    trace_result = None
    if trace is not None:
        terminal = trace.finish("collection_closed_before_trace_eof")
        trace_output.close()
        os.close(trace_read)
        trace_result = {"status": terminal["status"], "reason": terminal["reason"],
                        "sha256": hashlib.sha256((output / "trace.jsonl").read_bytes()).hexdigest(),
                        "bytes": trace.bytes, "records": trace.records,
                        "raw_bytes_consumed": trace.raw_bytes}
        if terminal["status"] != "complete" and reason == "initialized":
            reason = "trace_incomplete"
    if process.poll() is None:
        reason = "closure_unknown"
    elif reason == "initialized" and not all(eof.values()):
        reason = "closure_unknown"
    outcome = {
        "launched": True,
        "initialize": metadata, "reason": reason,
        "direct_child_returncode": process.returncode,
        "descendant_closure": "unknown",
        "diagnostic_qualification": "not_established",
        "trace": trace_result,
        "stdout_bytes": counts["stdout"], "stderr_bytes": counts["stderr"],
        "pipe_eof": eof,
        "elapsed_seconds": time.monotonic() - started,
    }
    return finish(outcome)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    command = sub.add_parser("prepare")
    command.add_argument("--spec", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command = sub.add_parser("run")
    command.add_argument("--package", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = prepare(args.spec, args.output) if args.action == "prepare" else run(args.package, args.output)
    except (OSError, ValueError, KeyError, TypeError):
        print(json.dumps({"reason": "invalid_or_unavailable_input"}), file=sys.stderr)
        return 2
    print(json.dumps(result))
    return 0 if args.action == "prepare" or result["reason"] == "initialized" else 2


if __name__ == "__main__":
    sys.exit(main())
