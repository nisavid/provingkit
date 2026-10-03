"""Consume an explicitly accepted manifest, preserving every launch attempt."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--receipt-dir", type=Path, required=True)
    args = parser.parse_args()
    receipt = {"schema": "passive-commit-launch/v1", "status": "rejected-before-native",
               "started_at": datetime.now(timezone.utc).isoformat(),
               "controller_started": False, "expected_sha256": args.expected_sha256,
               "command": [sys.executable, *sys.argv]}
    path = args.receipt_dir / (uuid.uuid4().hex + ".json")
    with path.open("x") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    code = 1
    try:
        raw = args.manifest.read_bytes()
        if hashlib.sha256(raw).hexdigest() != args.expected_sha256:
            raise ValueError("accepted manifest differs")
        manifest = json.loads(raw)
        for name, expected in manifest["source_sha256"].items():
            if hashlib.sha256(Path(name).read_bytes()).hexdigest() != expected:
                raise ValueError("source drift: " + name)
        root = args.manifest.parent
        if any(p.name in {"reservation.json", "outcome.json", "git-evidence.json"}
               or p.name.startswith("native-") for p in root.iterdir()):
            raise ValueError("episode already attempted")
        project = Path(manifest["project"])
        actual = {str(p.relative_to(project)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in project.rglob("*") if p.is_file()
                  and ".git" not in p.relative_to(project).parts}
        if actual != manifest["initial_files"]:
            raise ValueError("fixture drift")
        from git_state import snapshot
        if snapshot(project) != manifest["git_state"]:
            raise ValueError("Git state drift")
        with (root / "reservation.json").open("x") as stream:
            json.dump({"manifest_sha256": args.expected_sha256,
                       "receipt": str(path)}, stream)
        from native import run
        receipt["controller_started"] = True
        receipt["status"] = "native-incomplete"
        receipt["observation"] = run(manifest)
        receipt["status"] = "observed"
        code = 0
    except Exception as error:
        receipt["error"] = type(error).__name__ + ": " + str(error)
    receipt["ended_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": receipt["status"], "receipt": str(path)}))
    return code


if __name__ == "__main__":
    sys.exit(main())
