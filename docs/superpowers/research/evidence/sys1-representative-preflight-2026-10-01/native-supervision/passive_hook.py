"""Capture native supervision inputs without a model call or emitted instruction."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

from observer import capture, stamp


def exclusive(path, value):
    temporary = path.parent / ("." + path.name + "." + uuid.uuid4().hex)
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    root = args.config.resolve().parent
    records = root / "private" / "hooks"
    invocation = uuid.uuid4().hex
    observed = {"invocation_id": invocation, "started": stamp()}
    try:
        config = json.loads(args.config.read_text())
        if Path(config["root"]) != root:
            raise ValueError("hook configuration root differs")
        existing = list(records.glob("*.json"))
        if len(existing) >= config["max_hook_records"] or sum(path.stat().st_size for path in existing) >= config["max_record_bytes"]:
            raise ValueError("passive record bound reached")
        raw = sys.stdin.buffer.read(2_097_153)
        if len(raw) > 2_097_152:
            raise ValueError("hook input exceeds retained bound")
        hook = json.loads(raw)
        if hook.get("cwd") != str(root / "project"):
            raise ValueError("hook project differs")
        if hook.get("hook_event_name") not in {"PostToolUse", "Stop"}:
            raise ValueError("unexpected hook event")
        readiness = json.loads((root / "private/native-readiness.json").read_text())
        if readiness.get("verified") is not True or hook.get("session_id") != readiness.get("session_id"):
            raise ValueError("hook session not bound to native readiness")
        observer_config = {"harness": config["harness"], "session_id": readiness["session_id"],
                           "max_bytes": 2_097_152, "storage_root": config["storage_root"]}
        if readiness.get("transcript_path"):
            observer_config["transcript_path"] = readiness["transcript_path"]
        observed.update(raw_input_sha256=hashlib.sha256(raw).hexdigest(), raw_hook=hook)
        observed["context"] = capture(observer_config, hook)
        if observed["context"]["availability"] != "available":
            raise ValueError("hook-time transcript unavailable: " + str(observed["context"]["reason"]))
        environment = {key: value for key, value in os.environ.items() if not key.startswith("TYPESAFE_")}
        for kind in ("CONFIG", "STATE", "CACHE"):
            environment["XDG_" + kind + "_HOME"] = str(root / "integration-state" / kind.lower())
        completed = subprocess.run([config["node"], str(Path(__file__).with_name("bookkeeping.mjs"))],
                                   input=raw, capture_output=True, env=environment, timeout=15)
        observed["bookkeeping_process"] = {"exit_code": completed.returncode,
                                          "stderr": completed.stderr.decode("utf-8", errors="replace")}
        if completed.returncode != 0:
            raise ValueError("passive bookkeeping failed")
        observed["bookkeeping"] = json.loads(completed.stdout)
        observed["status"] = "captured"
        observed["ended"] = stamp()
        exclusive(records / (invocation + ".json"), observed)
    except Exception as error:
        observed.update(status="unavailable", error=str(error))
        try:
            exclusive(root / "private/observer-failure.json", {"invocation_id": invocation, "error": str(error)})
        except Exception:
            # A native nonzero completion remains observable if the marker cannot be published.
            pass
        observed["ended"] = stamp()
        try:
            exclusive(records / (invocation + ".json"), observed)
        except Exception:
            pass
        return 1
    # A passive capture never supplies an agent-facing instruction or permission.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
