"""Ordinary publication through the real planner, executor, and local Git.

Fixtures stay beneath the owned checkout parent: this does not qualify a
foreign-owned system temporary namespace or live authenticated publication.
"""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
import unittest.mock as mock


REPOSITORY = Path(__file__).resolve().parents[4]
SCRIPTS = REPOSITORY / (
    "plugins/versionkeeping/skills/checkpointing-and-publishing-git-work/scripts"
)
sys.path.insert(0, str(SCRIPTS))

from git_publication import adapter, execution  # noqa: E402


class OrdinaryPublicationTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(
            prefix="publication-host-runtime-", dir=REPOSITORY.parent
        )
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.repo = self.root / "repo"
        self.remote = self.root / "remote.git"
        home = self.root / "home"
        home.mkdir()
        self.environment = mock.patch.dict(
            os.environ,
            {
                adapter.GIT_CONFIG_PROFILE_ENV: "host-compatible",
                "HOME": str(home),
                "XDG_CONFIG_HOME": str(home / ".config"),
            },
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.git(self.root, "init", "--bare", str(self.remote))
        self.git(self.root, "init", "-b", "topic", str(self.repo))
        self.start = self.commit("base")
        self.git(self.repo, "remote", "add", "publish", str(self.remote))
        self.git(self.repo, "push", "publish", f"{self.start}:refs/heads/topic")
        self.git(self.repo, "push", "publish", f"{self.start}:refs/heads/main")
        self.git(self.remote, "symbolic-ref", "HEAD", "refs/heads/main")
        self.source = self.commit("change")
        self.request = {
            "schema_version": 2,
            "start_head": self.start,
            "source_sha": self.source,
            "task_owned_commits": [self.source],
            "adopted_commits": [],
            "removal_authorized_commits": [],
            "explicit_destination": {"remote": "publish", "ref": "refs/heads/topic"},
            "default_branch_policy": None,
            "allow_create": False,
            "creation_base_ref": None,
        }

    def git(self, repo, *args):
        env = os.environ.copy()
        env.update({
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        })
        return subprocess.run(
            ["/usr/bin/git", *args], cwd=repo, env=env, check=True,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ).stdout.strip()

    def commit(self, name):
        (self.repo / name).write_text(name, encoding="utf-8")
        self.git(self.repo, "add", "--", name)
        self.git(self.repo, "commit", "-m", name)
        return self.git(self.repo, "rev-parse", "HEAD")

    def execute(self, plan):
        plan_bytes = json.dumps(plan, sort_keys=True).encode("utf-8")
        return execution.execute_repository(
            self.repo, plan_bytes,
            "sha256:" + hashlib.sha256(plan_bytes).hexdigest(),
        )

    def test_ordinary_local_publication_verifies_exact_reviewed_destination(self):
        plan = adapter.plan_repository(self.repo, self.request)
        self.assertEqual(plan["status"], "ready", plan)
        self.assertEqual(plan["target"]["sha"], self.start)
        self.assertEqual(plan["destination"]["ref"], "refs/heads/topic")
        result = self.execute(plan)
        self.assertEqual(result["status"], "verified", result)
        self.assertEqual(result["source_sha"], self.source)
        self.assertEqual(self.git(self.remote, "rev-parse", "refs/heads/topic"), self.source)
        self.assertEqual(self.git(self.remote, "rev-parse", "refs/heads/main"), self.start)
        with self.assertRaises(AssertionError):
            self.assertEqual(self.git(self.remote, "rev-parse", "refs/heads/topic"), self.start)

    def test_unrelated_runtime_sibling_during_push_preserves_verified_result(self):
        runtime = self.root / "runtime"
        runtime.mkdir()
        selected_git = runtime / "git"
        selected_git.write_text('#!/bin/sh\nexec /usr/bin/git "$@"\n', encoding="utf-8")
        selected_git.chmod(0o755)
        original_run = subprocess.run
        pushed = []

        def run(command, **kwargs):
            completed = original_run(command, **kwargs)
            if "push" in command:
                self.assertEqual(command[0], str(selected_git))
                (runtime / "unrelated-entry").write_text("unrelated")
                pushed.append(command)
            return completed

        with mock.patch.dict(adapter.TRUSTED_SYSTEM_EXECUTABLES, {"git": selected_git}):
            plan = adapter.plan_repository(self.repo, self.request)
            self.assertEqual(plan["status"], "ready", plan)
            with mock.patch.object(adapter.subprocess, "run", side_effect=run):
                result = self.execute(plan)
        self.assertEqual(len(pushed), 1)
        self.assertEqual(result["status"], "verified", result)
        self.assertTrue(result["push_attempted"])
        self.assertEqual(self.git(self.remote, "rev-parse", "refs/heads/topic"), self.source)
        with self.assertRaises(AssertionError):
            self.assertEqual(result["status"], "blocked")

    def test_hardened_still_refuses_foreign_owned_system_root(self):
        original = Path.lstat

        def foreign_root(path, *args, **kwargs):
            observed = original(path, *args, **kwargs)
            if path != Path(path.anchor):
                return observed
            fields = {
                name: getattr(observed, name)
                for name in dir(observed) if name.startswith("st_")
            }
            fields["st_uid"] = 123456
            return SimpleNamespace(**fields)

        with mock.patch.object(Path, "lstat", foreign_root):
            with adapter.GitRepository(self.repo, config_profile="host-compatible") as repo:
                self.assertEqual(repo.output(["rev-parse", "HEAD"]), self.source)
            with self.assertRaises(adapter.PolicyGate) as raised:
                adapter.GitRepository(self.repo, config_profile="hardened")
        self.assertEqual(raised.exception.code, "TRUSTED_GIT_EXECUTABLE_UNAVAILABLE")

    def test_ordinary_never_selects_candidate_path_git(self):
        candidate_bin = self.repo / "bin"
        candidate_bin.mkdir()
        candidate_git = candidate_bin / "git"
        marker = self.root / "candidate-git-ran"
        candidate_git.write_text(f"#!/bin/sh\ntouch '{marker}'\nexit 1\n", encoding="utf-8")
        candidate_git.chmod(0o755)
        with mock.patch.dict(os.environ, {"PATH": str(candidate_bin)}):
            with adapter.GitRepository(self.repo, config_profile="host-compatible") as repo:
                self.assertEqual(repo.output(["rev-parse", "HEAD"]), self.source)
        self.assertFalse(marker.exists())

    def test_selected_executable_inside_candidate_is_refused(self):
        candidate_git = self.repo / "git"
        candidate_git.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        candidate_git.chmod(0o755)
        with mock.patch.dict(adapter.TRUSTED_SYSTEM_EXECUTABLES, {"git": candidate_git}):
            with self.assertRaises(adapter.PolicyGate) as raised:
                adapter.GitRepository(self.repo, config_profile="host-compatible")
        self.assertEqual(raised.exception.code, "TRUSTED_GIT_EXECUTABLE_UNAVAILABLE")

    def test_ordinary_keeps_repository_executable_config_refusal(self):
        self.git(self.repo, "config", "core.sshCommand", "/candidate/ssh")
        plan = adapter.plan_repository(self.repo, self.request)
        self.assertEqual(plan["status"], "blocked", plan)
        self.assertEqual(plan["reasons"][0]["code"], "UNSAFE_GIT_CONFIGURATION")

    def test_ordinary_refuses_foreign_intermediate_endpoint_ancestor(self):
        original = Path.lstat

        def foreign_parent(path, *args, **kwargs):
            observed = original(path, *args, **kwargs)
            if path != self.root:
                return observed
            fields = {
                name: getattr(observed, name)
                for name in dir(observed) if name.startswith("st_")
            }
            fields["st_uid"] = 123456
            return SimpleNamespace(**fields)

        with mock.patch.object(Path, "lstat", foreign_parent):
            plan = adapter.plan_repository(self.repo, self.request)
        self.assertEqual(plan["status"], "blocked", plan)
        self.assertEqual(plan["reasons"][0]["code"], "UNSAFE_GIT_REMOTE")

    def test_runtime_drift_before_git_call_is_refused(self):
        with adapter.GitRepository(self.repo, config_profile="host-compatible") as repo:
            with mock.patch.object(adapter, "recheck_host_executable", side_effect=OSError("drift")):
                with mock.patch.object(adapter.subprocess, "run") as run:
                    with self.assertRaises(adapter.PolicyGate) as raised:
                        repo.run(["rev-parse", "HEAD"])
        self.assertEqual(raised.exception.code, "TRUSTED_GIT_RUNTIME_CHANGED")
        run.assert_not_called()

    def test_observed_executable_replacement_is_not_rebound(self):
        runtime = self.root / "runtime"
        runtime.mkdir()
        selected_git = runtime / "git"
        selected_git.write_text('#!/bin/sh\nexec /usr/bin/git "$@"\n', encoding="utf-8")
        selected_git.chmod(0o755)
        marker = self.root / "replacement-ran"
        with mock.patch.dict(adapter.TRUSTED_SYSTEM_EXECUTABLES, {"git": selected_git}):
            with adapter.GitRepository(self.repo, config_profile="host-compatible") as repo:
                self.assertEqual(repo.output(["rev-parse", "HEAD"]), self.source)
                selected_git.unlink()
                selected_git.write_text(f"#!/bin/sh\ntouch '{marker}'\n", encoding="utf-8")
                selected_git.chmod(0o755)
                with self.assertRaises(adapter.PolicyGate) as raised:
                    repo.output(["rev-parse", "HEAD"])
        self.assertEqual(raised.exception.code, "TRUSTED_GIT_RUNTIME_CHANGED")
        self.assertFalse(marker.exists())

    def test_credential_preflight_refuses_runtime_drift_before_invocation(self):
        with adapter.GitRepository(self.repo, config_profile="host-compatible") as repo:
            with mock.patch.object(repo, "enable_https_credentials"):
                with mock.patch.object(adapter, "recheck_host_executable", side_effect=OSError("drift")):
                    with mock.patch.object(adapter.subprocess, "run") as run:
                        with self.assertRaises(adapter.PolicyGate) as raised:
                            repo.ensure_https_credentials("https://example.invalid/repo")
        self.assertEqual(raised.exception.code, "TRUSTED_GIT_RUNTIME_CHANGED")
        run.assert_not_called()

    def test_credential_preflight_rechecks_runtime_after_invocation(self):
        invoked = False
        original_recheck = adapter.recheck_host_executable

        def run(*args, **kwargs):
            nonlocal invoked
            invoked = True
            return subprocess.CompletedProcess([], 0)

        def recheck(bound):
            if invoked:
                raise OSError("drift after preflight")
            original_recheck(bound)

        with adapter.GitRepository(self.repo, config_profile="host-compatible") as repo:
            with mock.patch.object(repo, "enable_https_credentials"):
                with mock.patch.object(
                    adapter, "recheck_host_executable", side_effect=recheck,
                ):
                    with mock.patch.object(
                        adapter.subprocess, "run", side_effect=run,
                    ) as runner:
                        with self.assertRaises(adapter.PolicyGate) as raised:
                            repo.ensure_https_credentials("https://example.invalid/repo")
        self.assertEqual(raised.exception.code, "TRUSTED_GIT_RUNTIME_CHANGED")
        runner.assert_called_once()

    def test_runtime_drift_after_push_preserves_unknown_result(self):
        plan = adapter.plan_repository(self.repo, self.request)
        self.assertEqual(plan["status"], "ready", plan)
        original_run = subprocess.run
        original_recheck = adapter.recheck_host_executable
        pushed = False

        def run(command, **kwargs):
            nonlocal pushed
            completed = original_run(command, **kwargs)
            if "push" in command:
                pushed = True
            return completed

        def recheck(bound):
            if pushed:
                raise OSError("drift after started push")
            original_recheck(bound)

        with mock.patch.object(adapter.subprocess, "run", side_effect=run):
            with mock.patch.object(adapter, "recheck_host_executable", side_effect=recheck):
                result = self.execute(plan)
        self.assertTrue(pushed)
        self.assertTrue(result["push_attempted"])
        self.assertEqual(result["reasons"][0]["code"], "POST_PUSH_STATE_UNKNOWN", result)
        self.assertEqual(self.git(self.remote, "rev-parse", "refs/heads/topic"), self.source)


if __name__ == "__main__":
    unittest.main()
