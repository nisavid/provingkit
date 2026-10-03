"""Prepare a passive Codex observation; never launch a native task or Jev call."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import uuid

from git_state import snapshot


SOURCE = Path(__file__).resolve().parent
SEED = SOURCE.parent / "sys1-representative-preflight-2026-10-01/representative-workload/project"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--discover-profile", action="store_true",
                        help="query native metadata only; create no task and send no prompt")
    args = parser.parse_args()
    parent = args.parent
    if not parent.is_absolute() or parent.resolve() != parent or not parent.is_dir():
        raise ValueError("existing absolute scratch parent required")
    receipt_path = parent / ("preparation-" + uuid.uuid4().hex + ".json")
    receipt = {"status": "preparing", "started_at": datetime.now(timezone.utc).isoformat(),
               "native_sessions_started": 0, "root": None}
    with receipt_path.open("x") as stream:
        json.dump(receipt, stream, indent=2)
    try:
        summary = prepare(parent, args.discover_profile, receipt, receipt_path)
        receipt.update(status="prepared", **summary)
    except Exception as error:
        receipt.update(status="failed", error=type(error).__name__ + ": " + str(error))
        raise
    finally:
        receipt["ended_at"] = datetime.now(timezone.utc).isoformat()
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({**summary, "receipt": str(receipt_path)}))


def prepare(parent, discover_profile, receipt, receipt_path):
    root = Path(tempfile.mkdtemp(prefix="commit-observation-", dir=parent))
    receipt["root"] = str(root)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    project = root / "project"
    shutil.copytree(SEED, project, ignore=shutil.ignore_patterns("__pycache__"))
    (project / ".runner-tmp").mkdir()
    (project / ".observation").mkdir()
    (project / ".observation/records").mkdir()
    (project / ".observation/hooks").mkdir()
    with (project / ".gitignore").open("a") as stream:
        stream.write("\n/.runner-tmp/\n/.observation/\n")
    (project / "CONTRIBUTING.md").write_text(
        "# Contributing\n\nUse Conventional Commits. No DCO or sign-off is required.\n"
        "Run `make test` and `git diff --check` for changes. Keep this disposable\n"
        "repository local; it has no publication destination.\n")
    git = ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false"]
    def run(*command):
        return subprocess.run([*git, *command], cwd=project, check=True,
                              capture_output=True).stdout.decode().strip()
    run("init", "--quiet", "--initial-branch=observation")
    run("add", "--all")
    run("commit", "--quiet", "-m", "test: seed disposable report task")
    baseline = run("rev-parse", "HEAD")
    hooks = project / ".observation/hooks"
    observer = project / ".observation/observe_commit.py"
    shutil.copyfile(SOURCE / "observe_commit.py", observer)
    hook = hooks / "commit-msg"
    hook.write_text("#!/bin/sh\nexec " + shlex.join([sys.executable, str(observer),
                    "--repository", str(project), "--records",
                    str(project / ".observation/records")]) + ' --message "$1"\n')
    hook.chmod(0o755)
    run("config", "core.hooksPath", str(hooks))
    run("config", "commit.gpgsign", "false")
    profile = None
    if discover_profile:
        from profile import discover
        profile = discover(project, root)
        (root / "profile.json").write_text(json.dumps(profile, indent=2) + "\n")
    sources = [p for p in SOURCE.iterdir() if p.suffix in {".py", ".md"}]
    sources += [p for p in SEED.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    manifest = {
        "schema": "passive-commit-observation/v1", "purpose": "passive-commit-observation",
        "execution_authorized": False, "profile": "installed-codex-authoring",
        "root": str(root), "project": str(project), "baseline": baseline,
        "git_state": snapshot(project),
        "native_deadline_seconds": 480, "maximum_tool_calls": 40,
        "prompt": (SOURCE / "prompt.md").read_text(),
        "profile_sha256": digest(root / "profile.json") if profile else None,
        "source_sha256": {str(p): digest(p) for p in sources},
        "initial_files": {str(p.relative_to(project)): digest(p)
                          for p in project.rglob("*") if p.is_file()
                          and ".git" not in p.relative_to(project).parts},
    }
    path = root / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    return {"manifest": str(path), "sha256": digest(path), "native_sessions_started": 0}


if __name__ == "__main__":
    main()
