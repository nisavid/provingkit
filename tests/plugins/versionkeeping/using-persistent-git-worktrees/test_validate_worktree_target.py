from __future__ import annotations

import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPOSITORY = Path(__file__).resolve().parents[4]
SKILL_ROOT = REPOSITORY / "plugins/versionkeeping/skills/using-persistent-git-worktrees"
VALIDATOR = SKILL_ROOT / "scripts" / "validate_worktree_target.py"


def load_validator_module():
    specification = importlib.util.spec_from_file_location("worktree_target", VALIDATOR)
    module = importlib.util.module_from_spec(specification)
    assert specification.loader is not None
    specification.loader.exec_module(module)
    return module


class ValidateWorktreeTargetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name).resolve()
        self.clone = self.root / "project"
        self.clone.mkdir()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_executable_git_configuration_classes_are_closed(self) -> None:
        module = load_validator_module()
        cases = {
            "core.alternateRefsCommand": "core.alternateRefsCommand",
            "core.askPass": "core.askPass",
            "core.fsmonitor": "core.fsmonitor",
            "core.gitProxy": "core.gitProxy",
            "core.hooksPath": "core.hooksPath",
            "core.sshCommand": "core.sshCommand",
            "include.path": "include*.path",
            "includeIf.onbranch:topic.path": "include*.path",
            "protocol.ext.allow": "protocol.*.allow",
            "filter.attack.clean": "filter.*.(clean|smudge|process)",
            "filter.attack.smudge": "filter.*.(clean|smudge|process)",
            "filter.attack.process": "filter.*.(clean|smudge|process)",
            "hook.attack.command": "hook.*.command",
            "gpg.program": "gpg.program",
            "gpg.openpgp.program": "gpg.*.program",
            "gpg.ssh.defaultKeyCommand": "gpg.ssh.defaultKeyCommand",
            "credential.helper": "credential.*.helper",
            "credential.example.com.helper": "credential.*.helper",
            "diff.external": "diff.external",
            "diff.attack.command": "diff.*.(command|textconv)",
            "diff.attack.textconv": "diff.*.(command|textconv)",
            "difftool.attack.cmd": "difftool.*.cmd",
            "merge.attack.driver": "merge.*.driver",
            "mergetool.attack.cmd": "mergetool.*.cmd",
            "remote.origin.vcs": "remote.*.(vcs|uploadpack|receivepack)",
            "remote.origin.uploadpack": "remote.*.(vcs|uploadpack|receivepack)",
            "remote.origin.receivepack": "remote.*.(vcs|uploadpack|receivepack)",
            "url.ext::.insteadOf": "url.*.(insteadOf|pushInsteadOf)",
            "submodule.attack.update": "submodule.*.update",
        }
        for key, config_class in cases.items():
            with self.subTest(key=key):
                self.assertEqual(
                    module.unsafe_git_config_class(key),
                    config_class,
                )
        self.assertIsNone(module.unsafe_git_config_class("remote.origin.url"))

    def test_closed_environment_disables_implicit_signing(self) -> None:
        module = load_validator_module()
        environment = module.git_environment(self.root / "empty-hooks")
        closed = {
            environment[f"GIT_CONFIG_KEY_{index}"]: environment[
                f"GIT_CONFIG_VALUE_{index}"
            ]
            for index in range(int(environment["GIT_CONFIG_COUNT"]))
        }
        self.assertEqual(closed["push.gpgSign"], "false")
        self.assertEqual(closed["commit.gpgSign"], "false")
        self.assertEqual(closed["tag.gpgSign"], "false")

    def test_policy_bootstrap_never_executes_candidate_path_git(self) -> None:
        module = load_validator_module()
        subprocess.run(["/usr/bin/git", "init", "-q"], cwd=self.clone, check=True)
        candidate_bin = self.root / "candidate-bin"
        candidate_bin.mkdir()
        marker = self.root / "candidate-git-ran"
        fake_git = candidate_bin / "git"
        fake_git.write_text(
            "#!/bin/sh\n"
            f"printf 'executed\\n' >> {shlex.quote(str(marker))}\n"
            "exit 0\n",
            encoding="utf-8",
        )
        fake_git.chmod(0o700)
        hooks = self.root / "empty-hooks"
        hooks.mkdir()

        with mock.patch.dict(os.environ, {"PATH": str(candidate_bin)}):
            module.establish_inert_git_policy(
                module.run_command,
                self.clone,
                hooks,
            )

        self.assertFalse(marker.exists())

    def run_validator(
        self,
        *,
        name: str = "feature",
        branch: str = "topic/feature",
        create: bool = False,
        existing_branch: bool = False,
    ):
        arguments = [
            sys.executable,
            str(VALIDATOR),
            "--main-clone",
            str(self.clone),
            "--name",
            name,
            "--branch",
            branch,
        ]
        if create:
            arguments.append("--create")
        if existing_branch:
            arguments.append("--existing-branch")
        return subprocess.run(
            arguments,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_public_creation_in_owned_workspace_verifies_exact_branch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="worktree-consumer-", dir=REPOSITORY) as scratch:
            clone = Path(scratch) / "project"
            clone.mkdir(mode=0o700)
            subprocess.run(["/usr/bin/git", "init", "-q", str(clone)], check=True)
            subprocess.run(
                ["/usr/bin/git", "-C", str(clone), "-c", "user.name=Fixture",
                 "-c", "user.email=fixture@example.invalid", "commit", "-q",
                 "--allow-empty", "-m", "fixture"], check=True,
            )
            result = subprocess.run(
                [sys.executable, str(VALIDATOR), "--main-clone", str(clone),
                 "--name", "feature", "--branch", "topic/feature", "--create"],
                text=True, capture_output=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            receipt = json.loads(result.stdout)
            self.assertEqual(receipt["status"], "created")
            target = Path(scratch) / "project.wt" / "feature"
            self.assertEqual(receipt["worktree_path"], str(target))
            actual_branch = subprocess.check_output(
                ["/usr/bin/git", "-C", str(target), "symbolic-ref", "--short", "HEAD"],
                text=True,
            ).strip()
            self.assertEqual(actual_branch, "topic/feature")
            self.assertNotEqual(actual_branch, "topic/wrong-branch")

    def test_installed_worktree_import_does_not_need_source_checkout(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPOSITORY, prefix="installed-worktree-") as scratch:
            installed = Path(scratch) / "scripts"
            installed.mkdir()
            for name in ("validate_worktree_target.py", "host_trust.py"):
                shutil.copyfile(VALIDATOR.with_name(name), installed / name)
            result = subprocess.run(
                [sys.executable, "-I", "-B", str(installed / VALIDATOR.name), "--help"],
                cwd=scratch, capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("--main-clone", result.stdout)

    def test_returns_exact_sibling_target(self) -> None:
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "valid")
        self.assertEqual(payload["worktree_root"], str(self.root / "project.wt"))
        self.assertEqual(
            payload["worktree_path"], str(self.root / "project.wt" / "feature")
        )
        self.assertEqual(payload["branch"], "topic/feature")

    def test_rejects_absolute_traversal_and_option_like_names(self) -> None:
        for name in ("/tmp/feature", "../feature", "nested/feature", "-feature"):
            with self.subTest(name=name):
                result = self.run_validator(name=name)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(json.loads(result.stdout)["status"], "blocked")

    def test_rejects_unsafe_branch_refs(self) -> None:
        for branch in (
            "/topic",
            "../topic",
            "-topic",
            "topic..other",
            "topic@{1}",
            "topic.lock",
            ".hidden/topic",
            "topic//other",
        ):
            with self.subTest(branch=branch):
                result = self.run_validator(branch=branch)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(json.loads(result.stdout)["status"], "blocked")

    def test_rejects_symlinked_clone_and_sibling_root(self) -> None:
        real_clone = self.root / "real-project"
        self.clone.rename(real_clone)
        self.clone.symlink_to(real_clone, target_is_directory=True)
        self.assertEqual(self.run_validator().returncode, 2)

        self.clone.unlink()
        real_clone.rename(self.clone)
        external = self.root / "external"
        external.mkdir()
        (self.root / "project.wt").symlink_to(external, target_is_directory=True)
        self.assertEqual(self.run_validator().returncode, 2)

    def test_rejects_symlinked_target_outside_sibling_root(self) -> None:
        sibling_root = self.root / "project.wt"
        sibling_root.mkdir()
        external = self.root / "external"
        external.mkdir()
        (sibling_root / "feature").symlink_to(external, target_is_directory=True)
        result = self.run_validator()
        self.assertEqual(result.returncode, 2)
        self.assertIn("symlink", json.loads(result.stdout)["reason"])

    def test_creation_rejects_root_replacement_after_receipt(self) -> None:
        module = load_validator_module()
        receipt = module.validated_target(self.clone, "feature", "topic/feature")
        sibling_root = self.root / "project.wt"
        sibling_root.mkdir(mode=0o700)
        external = self.root / "external"
        external.mkdir()
        sibling_root.rmdir()
        sibling_root.symlink_to(external, target_is_directory=True)
        calls = []

        def runner(*args, **kwargs):
            calls.append((args, kwargs))
            raise AssertionError("Git must not run for a replaced root")

        with self.assertRaises(module.InvalidTarget):
            module.create_worktree(receipt, runner=runner)
        self.assertEqual(calls, [])

    def test_creation_rejects_boolean_or_float_receipt_schema(self) -> None:
        module = load_validator_module()
        for malformed in (True, 1.0):
            with self.subTest(malformed=malformed):
                receipt = module.validated_target(
                    self.clone, f"feature-{malformed}", "topic/feature"
                )
                receipt["schema_version"] = malformed
                with self.assertRaisesRegex(
                    module.InvalidTarget, "receipt schema is invalid"
                ):
                    module.create_worktree(receipt)

    def test_creation_uses_one_guarded_git_flow_and_verifies_result(self) -> None:
        module = load_validator_module()
        receipt = module.validated_target(self.clone, "feature", "topic/feature")
        target = self.root / "project.wt" / "feature"
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            if "show-ref" in command:
                return subprocess.CompletedProcess(command, 1, "", "")
            if "worktree" in command and "add" in command:
                target.mkdir()
                return subprocess.CompletedProcess(command, 0, "created\n", "")
            if command[-2:] == ["list", "--porcelain"]:
                return subprocess.CompletedProcess(
                    command, 0, f"worktree {target}\nHEAD deadbeef\n", ""
                )
            if "symbolic-ref" in command:
                return subprocess.CompletedProcess(command, 0, "topic/feature\n", "")
            return subprocess.CompletedProcess(command, 0, "", "")

        with mock.patch.dict(os.environ, {"GH_TOKEN": "secret"}):
            result = module.create_worktree(receipt, runner=runner)
        self.assertEqual(result["status"], "created")
        commands = [command for command, _ in calls]
        add_command = next(command for command in commands if "add" in command)
        self.assertEqual(
            add_command[3:],
            [
                "-C",
                str(self.clone),
                "worktree",
                "add",
                "-b",
                "topic/feature",
                "--",
                str(target),
            ],
        )
        self.assertTrue(add_command[2].startswith("core.hooksPath="))
        self.assertEqual(len(commands), 7)
        self.assertTrue(
            all("config" in command and "--name-only" in command for command in commands[:2])
        )
        for _, options in calls:
            self.assertIs(options["stdin"], subprocess.DEVNULL)
            self.assertEqual(options["timeout"], module.GIT_TIMEOUT_SECONDS)
            self.assertEqual(options["env"]["GIT_TERMINAL_PROMPT"], "0")
            self.assertNotIn("GH_TOKEN", options["env"])

    def test_unrelated_runtime_sibling_preserves_completed_creation(self) -> None:
        module = load_validator_module()
        receipt = module.validated_target(self.clone, "feature", "topic/feature")
        # Git effects are inert; selection, binding, checks and result handling
        # execute normally. This does not prove a live Git worktree operation.
        with tempfile.TemporaryDirectory(dir=REPOSITORY.parent) as runtime_dir:
            runtime = Path(runtime_dir)
            selected_git = runtime / "git"
            selected_git.write_text("#!/bin/sh\nexit 0\n")
            selected_git.chmod(0o700)
            calls = []

            def runner(command, **kwargs):
                calls.append(command)
                self.assertEqual(command[0], str(selected_git))
                if "show-ref" in command:
                    return subprocess.CompletedProcess(command, 1, "", "")
                if "worktree" in command and "add" in command:
                    Path(receipt["worktree_path"]).mkdir()
                    (runtime / "unrelated-entry").mkdir()
                output = (f"worktree {receipt['worktree_path']}\n"
                          if "--porcelain" in command else
                          "topic/feature\n" if "symbolic-ref" in command else "")
                return subprocess.CompletedProcess(command, 0, output, "")

            with mock.patch.object(module, "TRUSTED_GIT_EXECUTABLE", selected_git):
                result = module.create_worktree(receipt, runner=runner)
        self.assertEqual(result["status"], "created", result)
        self.assertEqual(sum("add" in command for command in calls), 1)
        self.assertEqual(result["branch"], "topic/feature")
        with self.assertRaises(AssertionError):
            self.assertEqual(result["status"], "unknown")

    def test_runtime_drift_before_execution_blocks_without_running_git(self) -> None:
        module = load_validator_module()
        receipt = module.validated_target(self.clone, "feature", "topic/feature")
        runner = mock.Mock()
        with mock.patch.object(
            module, "recheck_host_executable", side_effect=module.HostTrustError("changed")
        ):
            with self.assertRaisesRegex(module.InvalidTarget, "changed before execution"):
                module.create_worktree(receipt, runner=runner)
        runner.assert_not_called()

    def test_runtime_drift_after_mutation_is_unknown(self) -> None:
        module = load_validator_module()
        receipt = module.validated_target(self.clone, "feature", "topic/feature")
        mutated = False
        original = module.recheck_host_executable

        def check(runtime):
            if mutated:
                raise module.HostTrustError("changed")
            original(runtime)

        def runner(command, **kwargs):
            nonlocal mutated
            if "show-ref" in command:
                return subprocess.CompletedProcess(command, 1, "", "")
            if "worktree" in command and "add" in command:
                mutated = True
                Path(receipt["worktree_path"]).mkdir()
            return subprocess.CompletedProcess(command, 0, "", "")

        with mock.patch.object(module, "recheck_host_executable", side_effect=check):
            result = module.create_worktree(receipt, runner=runner)
        self.assertEqual(result["status"], "unknown")
        self.assertIn("changed during execution", result["reason"])
        self.assertTrue(mutated)

    def test_failed_or_timed_out_mutation_is_unknown_without_a_target(self) -> None:
        module = load_validator_module()

        for outcome in ("failed", "timeout"):
            with self.subTest(outcome=outcome):
                receipt = module.validated_target(
                    self.clone, f"feature-{outcome}", f"topic/{outcome}"
                )

                def runner(command, **kwargs):
                    if "config" in command and "--name-only" in command:
                        return subprocess.CompletedProcess(command, 0, "", "")
                    if "show-ref" in command:
                        return subprocess.CompletedProcess(command, 1, "", "")
                    if outcome == "timeout":
                        raise subprocess.TimeoutExpired(
                            command, module.GIT_TIMEOUT_SECONDS
                        )
                    return subprocess.CompletedProcess(command, 1, "", "failed")

                result = module.create_worktree(receipt, runner=runner)
                self.assertEqual(result["status"], "unknown")
                self.assertFalse(Path(receipt["worktree_path"]).exists())

    def test_existing_branch_requires_and_verifies_exact_local_branch(self) -> None:
        module = load_validator_module()
        receipt = module.validated_target(self.clone, "feature", "topic/existing")
        target = Path(receipt["worktree_path"])
        commands = []

        def runner(command, **kwargs):
            commands.append(command)
            if "show-ref" in command:
                return subprocess.CompletedProcess(command, 0, "a" * 40 + "\n", "")
            if "worktree" in command and "add" in command:
                target.mkdir()
                return subprocess.CompletedProcess(command, 0, "created\n", "")
            if command[-2:] == ["list", "--porcelain"]:
                return subprocess.CompletedProcess(
                    command, 0, f"worktree {target}\nHEAD {'a' * 40}\n", ""
                )
            if "symbolic-ref" in command:
                return subprocess.CompletedProcess(command, 0, "topic/existing\n", "")
            return subprocess.CompletedProcess(command, 0, "", "")

        result = module.create_worktree(receipt, existing_branch=True, runner=runner)
        self.assertEqual(result["status"], "created")
        add_command = next(command for command in commands if "add" in command)
        self.assertNotIn("-b", add_command)

        absent_receipt = module.validated_target(self.clone, "other", "topic/tag-only")

        def absent_runner(command, **kwargs):
            return subprocess.CompletedProcess(command, 1, "", "")

        with self.assertRaises(module.InvalidTarget):
            module.create_worktree(
                absent_receipt, existing_branch=True, runner=absent_runner
            )

    def test_real_creation_suppresses_ambient_post_checkout_hook(self) -> None:
        subprocess.run(
            ["git", "init", str(self.clone)], check=True, capture_output=True
        )
        tracked = self.clone / "tracked.txt"
        tracked.write_text("tracked\n")
        subprocess.run(
            ["git", "-C", str(self.clone), "add", "tracked.txt"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(self.clone),
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.com",
                "commit",
                "-m",
                "test",
            ],
            check=True,
            capture_output=True,
        )
        marker = self.root / "hook-ran"
        hook = self.clone / ".git/hooks/post-checkout"
        hook.write_text(f"#!/bin/sh\ntouch '{marker}'\n")
        os.chmod(hook, 0o755)

        result = self.run_validator(create=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "created")
        self.assertFalse(marker.exists())
        self.assertTrue((self.root / "project.wt/feature").is_dir())

    def test_creation_blocks_smudge_filter_before_checkout(self) -> None:
        subprocess.run(
            ["git", "init", str(self.clone)], check=True, capture_output=True
        )
        marker = self.root / "smudge-ran"
        helper = self.root / "smudge-filter"
        helper.write_text(f"#!/bin/sh\ntouch '{marker}'\ncat\n")
        helper.chmod(0o700)
        (self.clone / ".gitattributes").write_text("tracked.txt filter=attack\n")
        (self.clone / "tracked.txt").write_text("tracked\n")
        subprocess.run(
            ["git", "-C", str(self.clone), "config", "filter.attack.smudge", str(helper)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(self.clone), "add", ".gitattributes", "tracked.txt"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(self.clone),
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.com",
                "commit",
                "-m",
                "test",
            ],
            check=True,
            capture_output=True,
        )

        result = self.run_validator(create=True)

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "blocked")
        self.assertFalse(marker.exists())
        self.assertFalse((self.root / "project.wt/feature").exists())

    def test_creation_blocks_named_post_checkout_hook_before_mutation(self) -> None:
        subprocess.run(
            ["git", "init", str(self.clone)], check=True, capture_output=True
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(self.clone),
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.com",
                "commit",
                "--allow-empty",
                "-m",
                "test",
            ],
            check=True,
            capture_output=True,
        )
        marker = self.root / "named-hook-ran"
        secret = "named-hook-config-secret-605a46"
        subprocess.run(
            [
                "git",
                "-C",
                str(self.clone),
                "config",
                "hook.attack.command",
                f"touch '{marker}' # {secret}",
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(self.clone),
                "config",
                "--add",
                "hook.attack.event",
                "post-checkout",
            ],
            check=True,
            capture_output=True,
        )

        result = self.run_validator(create=True)

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "blocked")
        self.assertFalse(marker.exists())
        self.assertFalse((self.root / "project.wt").exists())
        self.assertNotIn(secret, result.stdout + result.stderr)

    def test_mutation_failure_does_not_expose_config_value_from_git_stderr(
        self,
    ) -> None:
        subprocess.run(
            ["git", "init", str(self.clone)], check=True, capture_output=True
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(self.clone),
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.com",
                "commit",
                "--allow-empty",
                "-m",
                "test",
            ],
            check=True,
            capture_output=True,
        )
        secret = "inert-config-secret-c74dbd"
        subprocess.run(
            [
                "git",
                "-C",
                str(self.clone),
                "config",
                "checkout.workers",
                secret,
            ],
            check=True,
            capture_output=True,
        )

        result = self.run_validator(create=True)

        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "unknown")
        self.assertNotIn("stderr", payload)
        self.assertNotIn(secret, result.stdout + result.stderr)

    def test_creation_blocks_merge_tool_command_without_exposing_its_value(self) -> None:
        subprocess.run(
            ["git", "init", str(self.clone)], check=True, capture_output=True
        )
        marker = self.root / "merge-tool-ran"
        secret = "config-value-secret-7f70f8"
        command = f"touch '{marker}' # {secret}"
        subprocess.run(
            [
                "git",
                "-C",
                str(self.clone),
                "config",
                "mergetool.attack.cmd",
                command,
            ],
            check=True,
            capture_output=True,
        )

        result = self.run_validator(create=True)

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "blocked")
        self.assertNotIn(secret, result.stdout + result.stderr)
        self.assertFalse(marker.exists())
        self.assertFalse((self.root / "project.wt").exists())

    def test_creation_rejects_insecure_sibling_parent(self) -> None:
        module = load_validator_module()
        receipt = module.validated_target(self.clone, "feature", "topic/feature")
        self.root.chmod(0o777)
        try:
            with self.assertRaises(module.InvalidTarget):
                module.create_worktree(receipt)
        finally:
            self.root.chmod(0o700)


if __name__ == "__main__":
    unittest.main()
