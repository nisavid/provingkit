"""Semantic identity of the disposable repository before an episode."""

import hashlib
from pathlib import Path
import stat
import subprocess


def snapshot(project):
    def git(*args):
        return subprocess.run(["git", "-c", "core.fsmonitor=false", *args],
                              cwd=project, check=True, capture_output=True,
                              timeout=5).stdout.decode().strip()
    hooks = git("config", "--get", "core.hooksPath")
    hook = Path(hooks) / "commit-msg"
    return {"head": git("rev-parse", "HEAD"), "branch": git("symbolic-ref", "HEAD"),
            "index_tree": git("write-tree"), "status": git("status", "--porcelain=v1"),
            "remotes": git("remote", "-v"), "hooks": hooks,
            "hook_identity": {"mode": stat.S_IMODE(hook.stat().st_mode),
                              "sha256": hashlib.sha256(hook.read_bytes()).hexdigest()}
                             if hook.is_file() else None,
            "signing": git("config", "--get", "commit.gpgsign"),
            "author_name": git("config", "--get", "user.name"),
            "author_email": git("config", "--get", "user.email")}
