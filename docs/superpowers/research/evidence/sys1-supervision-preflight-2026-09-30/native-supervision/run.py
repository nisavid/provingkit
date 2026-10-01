"""Run one separately accepted, source-bound passive qualification episode."""

import argparse
import contextlib
from datetime import datetime, timezone
import fcntl
import hashlib
import io
import json
from pathlib import Path
import sys
import time
import traceback
import uuid


def write_receipt(stream, receipt):
    stream.seek(0)
    json.dump(receipt, stream, indent=2)
    stream.write("\n")
    stream.truncate()
    stream.flush()


def launch(args, receipt, receipt_stream):
    data = args.manifest.read_bytes()
    if hashlib.sha256(data).hexdigest() != args.expected_sha256:
        raise ValueError("accepted manifest differs")
    manifest = json.loads(data)
    if manifest.get("purpose") != "passive-context-qualification":
        raise ValueError("only passive qualification is supported")
    for logical, resolved in manifest["dependency_roots"].items():
        if str(Path(logical).resolve(strict=True)) != resolved:
            raise ValueError("runtime dependency resolution differs")
    for name, expected in manifest["source_sha256"].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != expected:
            raise ValueError("runtime source differs: " + name)
    root = args.manifest.parent
    if root != Path(manifest["root"]) or root.resolve() != root:
        raise ValueError("attempt root differs")
    # This lock serializes this batch. It does not reserve provider capacity from other chats.
    with (root.parent / "execution.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with (root / "private/reservation.json").open("x") as record:
            json.dump({"manifest_sha256": args.expected_sha256, "started_monotonic_ns": time.monotonic_ns()}, record)
        outcome = {"status": "failed", "manifest_sha256": args.expected_sha256}
        try:
            from native_controller import run
            receipt["controller_started"] = True
            write_receipt(receipt_stream, receipt)
            outcome["observation"] = run(manifest, root)
            outcome["status"] = "observed"
        except Exception as error:
            outcome["error"] = str(error)
            receipt["error"] = str(error)
        outcome["ended_monotonic_ns"] = time.monotonic_ns()
        with (root / "private/outcome.json").open("x") as record:
            json.dump(outcome, record, indent=2)
            record.write("\n")
        print(json.dumps({"status": outcome["status"], "outcome": str(root / "private/outcome.json")}))
        return 0 if outcome["status"] == "observed" else 1


def main():
    started_wall = datetime.now(timezone.utc).isoformat()
    started_monotonic_ns = time.monotonic_ns()
    # Receipt storage must be usable before any episode record or native process is touched.
    bootstrap = argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument("--receipt-dir", type=Path, required=True)
    receipt_args, _ = bootstrap.parse_known_args()
    directory = receipt_args.receipt_dir
    if not directory.is_absolute() or directory.resolve() != directory or not directory.is_dir():
        raise ValueError("an existing, absolute coordinator receipt directory is required")
    invocation_id = uuid.uuid4().hex
    receipt = {"schema": "sys1-native-launch-receipt/v1", "invocation_id": invocation_id,
               "command": [sys.executable, *sys.argv], "expected_sha256": None,
               "started_wall": started_wall, "started_monotonic_ns": started_monotonic_ns,
               "controller_started": False, "status": "in-progress", "error": None}
    stdout, stderr = io.StringIO(), io.StringIO()
    exit_code = 1
    with (directory / (invocation_id + ".json")).open("x") as receipt_stream:
        write_receipt(receipt_stream, receipt)
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                parser = argparse.ArgumentParser(description=__doc__)
                parser.add_argument("--receipt-dir", type=Path, required=True)
                parser.add_argument("--manifest", type=Path, required=True)
                parser.add_argument("--expected-sha256", required=True)
                args = parser.parse_args()
                receipt.update(manifest_path=str(args.manifest), expected_sha256=args.expected_sha256)
                write_receipt(receipt_stream, receipt)
                exit_code = launch(args, receipt, receipt_stream)
            except SystemExit as error:
                exit_code = error.code if isinstance(error.code, int) else 1
                if exit_code:
                    receipt["error"] = "launcher argument parsing failed"
            except Exception as error:
                receipt["error"] = str(error)
                traceback.print_exc()
        receipt.update(ended_wall=datetime.now(timezone.utc).isoformat(),
                       ended_monotonic_ns=time.monotonic_ns(), exit_code=exit_code,
                       stdout=stdout.getvalue(), stderr=stderr.getvalue())
        receipt["status"] = ("observed" if exit_code == 0 else "native-episode-failed") if receipt["controller_started"] else ("no-controller" if exit_code == 0 else "rejected-before-controller")
        write_receipt(receipt_stream, receipt)
    sys.stdout.write(stdout.getvalue())
    sys.stderr.write(stderr.getvalue())
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
