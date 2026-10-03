"""Passively retain Git's commit-msg input; never judge or rewrite a message."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--message", type=Path, required=True)
    args = parser.parse_args()
    record = Path(tempfile.mkdtemp(prefix="commit-", dir=args.records))
    metadata = {"schema": "passive-commit-observation/v1", "status": "incomplete",
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "assessment_performed": False, "artifacts": {}}
    try:
        def git(*command):
            return subprocess.run(["git", *command], cwd=args.repository,
                                  capture_output=True, check=True, timeout=5).stdout

        def retain(name, data):
            (record / name).write_bytes(data)
            metadata["artifacts"][name] = {"bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest()}

        retain("message.bin", args.message.read_bytes())
        retain("staged.patch", git("--no-pager", "diff", "--cached", "--no-color",
                                   "--no-ext-diff", "--no-textconv", "--binary"))
        metadata["index_tree"] = git("write-tree").decode().strip()
        metadata["parent"] = git("rev-parse", "--verify", "HEAD").decode().strip()
        metadata["status"] = "captured"
    except Exception as error:
        metadata["error"] = type(error).__name__ + ": " + str(error)
    (record / "record.json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # An observation failure invalidates evidence, not the developer's commit.
        # The controller must reconcile every commit against complete records.
        pass
