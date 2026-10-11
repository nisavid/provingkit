"""Construct a disposable seed commit and retain Git observation evidence.

This is cooperative local fixture accounting, not a permission boundary.
Baseline construction uses commit-tree; author commits keep their ordinary
workflow. Every Git command has a ten-second proposed collection timeout.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import time


BRANCH = "compatibility-observation"
COMMAND_TIMEOUT_SECONDS = 10
EXCLUDED = [".git", "__pycache__", "*.pyc", "*.pyo"]


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode() + b"\n"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def put(path, raw):
    with path.open("xb") as stream:
        stream.write(raw)
    return {"path": path.name, "sha256": digest(raw), "bytes": len(raw)}


def inventory(project):
    files = []

    def visit(directory):
        for path in sorted(directory.iterdir()):
            if path.name in (".git", "__pycache__") or path.suffix in (".pyc", ".pyo"):
                continue
            mode = path.lstat().st_mode
            name = path.relative_to(project).as_posix()
            name.encode("utf-8")
            if stat.S_ISDIR(mode):
                visit(path)
            elif stat.S_ISREG(mode):
                raw = path.read_bytes()
                files.append({"path": name, "sha256": digest(raw),
                              "bytes": len(raw), "mode": stat.S_IMODE(mode),
                              "executable": bool(mode & 0o111)})
            else:
                raise ValueError("unsupported source entry: " + name)

    visit(project)
    return sorted(files, key=lambda entry: entry["path"])


def executable():
    found = shutil.which("git")
    if found is None:
        raise ValueError("Git executable unavailable")
    path = Path(found).resolve()
    return {"path": str(path), "sha256": digest(path.read_bytes())}


class Recorder:
    def __init__(self, project, output, git):
        self.project = project
        self.output = output
        self.git = git
        self.commands = []
        output.mkdir(exist_ok=False)

    def command(self, name, arguments, stdin=None, required=False):
        directory = self.output / name
        directory.mkdir(exist_ok=False)
        argv = [self.git["path"], "-C", str(self.project),
                "--git-dir=" + str(self.project / ".git"),
                "--work-tree=" + str(self.project), *arguments]
        record = {"argv": argv, "cwd": str(self.project),
                  "started_at": datetime.now(timezone.utc).isoformat(),
                  "started_monotonic_ns": time.monotonic_ns(),
                  "timeout_seconds": COMMAND_TIMEOUT_SECONDS,
                  "exit_code": None, "status": "failed"}
        if stdin is not None:
            record["stdin"] = put(directory / "stdin.bin", stdin)
        stdout = stderr = b""
        try:
            result = subprocess.run(argv, input=stdin, capture_output=True,
                                    timeout=COMMAND_TIMEOUT_SECONDS)
            stdout, stderr = result.stdout, result.stderr
            record.update(exit_code=result.returncode,
                          status="completed" if result.returncode == 0 else "failed")
        except subprocess.TimeoutExpired as error:
            stdout, stderr = error.stdout or b"", error.stderr or b""
            record["error"] = "command timeout"
        except OSError as error:
            record["error"] = type(error).__name__ + ": " + str(error)
        record.update(finished_at=datetime.now(timezone.utc).isoformat(),
                      finished_monotonic_ns=time.monotonic_ns(),
                      stdout=put(directory / "stdout.bin", stdout),
                      stderr=put(directory / "stderr.bin", stderr))
        reference = put(directory / "record.json", encoded(record))
        self.commands.append({"name": name, "record": {**reference,
                              "path": name + "/record.json"}})
        if required and record["status"] != "completed":
            raise ValueError("Git preparation command failed: " + name)
        return record, stdout


def oid(raw):
    value = raw.strip().decode("ascii")
    if re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", value) is None:
        raise ValueError("Git returned an invalid object identity")
    return value


def prepare(project, output):
    git = executable()
    recorder = Recorder(project, output, git)
    result = {"schema": "compatibility-git-baseline/v1", "status": "preparing",
              "git": git, "branch": BRANCH, "excluded_source_entries": EXCLUDED,
              "construction": "Git plumbing seed commit; no author review inferred",
              "commands": recorder.commands}
    try:
        if (project / ".git").exists() or (project / ".git").is_symlink():
            raise ValueError("seed project already contains Git metadata")
        result["source_inventory"] = inventory(project)
        recorder.command("version", ["--version"], required=True)
        recorder.command("init", ["init", "--initial-branch=" + BRANCH], required=True)
        recorder.command("add", ["add", "--force", "--all", "--", "."], required=True)
        _, tree_raw = recorder.command("write-tree", ["write-tree"], required=True)
        tree = oid(tree_raw)
        recorder.command("author-identity", ["var", "GIT_AUTHOR_IDENT"], required=True)
        recorder.command("committer-identity", ["var", "GIT_COMMITTER_IDENT"], required=True)
        _, commit_raw = recorder.command(
            "commit-tree", ["commit-tree", tree],
            stdin=b"chore: prepare compatibility observation seed\n", required=True)
        head = oid(commit_raw)
        recorder.command("update-ref", ["update-ref", "refs/heads/" + BRANCH, head], required=True)
        recorder.command("seed-commit", ["show", "--no-patch", "--format=raw", head], required=True)
        _, root_raw = recorder.command("root", ["rev-parse", "--show-toplevel"], required=True)
        _, branch_raw = recorder.command("branch", ["symbolic-ref", "--short", "HEAD"], required=True)
        _, tracked_raw = recorder.command("tracked", ["ls-files", "-z"], required=True)
        _, status_raw = recorder.command("status", ["status", "--porcelain=v1", "-z", "--untracked-files=all"], required=True)
        _, remote_raw = recorder.command("remotes", ["remote", "-v"], required=True)
        expected = sorted(entry["path"] for entry in result["source_inventory"])
        tracked = sorted(os.fsdecode(name) for name in tracked_raw.split(b"\0") if name)
        if (Path(os.fsdecode(root_raw.strip())) != project or
                branch_raw.strip() != BRANCH.encode() or status_raw or remote_raw or
                tracked != expected or inventory(project) != result["source_inventory"]):
            raise ValueError("constructed Git baseline differs from prepared source")
        result.update(status="ready", head=head, tree=tree,
                      initial_status="clean", remotes="none-observed")
    except Exception as error:
        result.update(status="failed", error=type(error).__name__ + ": " + str(error))
        put(output / "baseline.json", encoded(result))
        raise
    reference = put(output / "baseline.json", encoded(result))
    return {**reference, "path": "baseline-git/baseline.json"}


def verify(project, baseline, output):
    if baseline.get("status") != "ready":
        raise ValueError("Git baseline is not ready")
    git = executable()
    if git != baseline["git"]:
        raise ValueError("Git executable differs from baseline")
    recorder = Recorder(project, output, git)
    result = {"schema": "compatibility-git-preflight/v1", "commands": recorder.commands,
              "status": "incomplete", "baseline_head": baseline["head"]}
    try:
        observed = {}
        for name, args in [
            ("root", ["rev-parse", "--show-toplevel"]),
            ("head", ["rev-parse", "--verify", "HEAD"]),
            ("branch", ["symbolic-ref", "--short", "HEAD"]),
            ("status", ["status", "--porcelain=v1", "-z", "--untracked-files=all"]),
            ("remotes", ["remote", "-v"]),
        ]:
            _, observed[name] = recorder.command(name, args, required=True)
        if (Path(os.fsdecode(observed["root"].strip())) != project or
                oid(observed["head"]) != baseline["head"] or
                observed["branch"].strip() != baseline["branch"].encode() or
                observed["status"] or observed["remotes"] or
                inventory(project) != baseline["source_inventory"]):
            raise ValueError("baseline Git state changed before task delivery")
        result["status"] = "matched"
    except Exception as error:
        result["error"] = type(error).__name__ + ": " + str(error)
        put(output / "preflight.json", encoded(result))
        raise
    return put(output / "preflight.json", encoded(result))


def capture(project, output, baseline, final_inventory):
    git = executable()
    recorder = Recorder(project, output, git)
    result = {"schema": "compatibility-final-git/v1", "status": "complete",
              "git": git, "baseline_head": baseline["head"],
              "commands": recorder.commands, "source_correspondence": "unverified",
              "errors": []}
    if git != baseline["git"]:
        result["errors"].append("Git executable differs from baseline")
    before = after = None
    try:
        before = inventory(project)
    except Exception as error:
        result["errors"].append("source-before: " + ascii(error))
    observed = {}
    head = baseline["head"]
    commands = [
        ("root", ["rev-parse", "--show-toplevel"]),
        ("head", ["rev-parse", "--verify", "HEAD"]),
        ("branch", ["symbolic-ref", "--quiet", "--short", "HEAD"]),
        ("baseline-reachable", ["merge-base", "--is-ancestor", head, "HEAD"]),
        ("commits", ["log", "--format=%H%x00%P%x00%an%x00%ae%x00%at%x00%cn%x00%ce%x00%ct%x00%B%x00", head + "..HEAD", "--"]),
        ("status", ["status", "--porcelain=v1", "-z", "--untracked-files=all"]),
        ("committed-paths", ["diff", "--no-ext-diff", "--no-textconv", "--raw", "-z", head, "HEAD", "--"]),
        ("committed-patch", ["diff", "--no-ext-diff", "--no-textconv", "--binary", head, "HEAD", "--"]),
        ("staged-patch", ["diff", "--no-ext-diff", "--no-textconv", "--binary", "--cached", "HEAD", "--"]),
        ("unstaged-patch", ["diff", "--no-ext-diff", "--no-textconv", "--binary", "--"]),
        ("untracked", ["ls-files", "--others", "--exclude-standard", "-z"]),
        ("remotes", ["remote", "-v"]),
    ]
    for name, args in commands:
        record, raw = recorder.command(name, args)
        observed[name] = (record, raw)
        if record["status"] != "completed" and not (name == "branch" and record["exit_code"] == 1):
            result["errors"].append("Git command failed: " + name)
    if observed["head"][0]["status"] == "completed":
        try:
            result["head"] = oid(observed["head"][1])
        except ValueError as error:
            result["errors"].append(str(error))
    result["branch_observation"] = ("detached" if observed["branch"][0]["exit_code"] == 1
                                     else "named" if observed["branch"][0]["status"] == "completed"
                                     else "unavailable")
    try:
        after = inventory(project)
    except Exception as error:
        result["errors"].append("source-after: " + ascii(error))
    result["source_before"] = before
    result["source_after"] = after
    if (final_inventory.get("status") == "complete" and before is not None and
            before == after == final_inventory["files"]):
        result["source_correspondence"] = "matched-at-recorded-boundaries"
    else:
        result["errors"].append("final source correspondence is unverified")
    if result["errors"]:
        result["status"] = "incomplete"
    reference = put(output / "final-git.json", encoded(result))
    return {"status": result["status"], "inventory": "final-git/final-git.json",
            "sha256": reference["sha256"],
            "source_correspondence": result["source_correspondence"]}
