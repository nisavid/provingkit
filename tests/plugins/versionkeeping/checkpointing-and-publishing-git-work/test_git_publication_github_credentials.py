"""GitHub credential compatibility with synthetic, nonpersisted credentials."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import unittest.mock as mock


REPOSITORY = Path(__file__).resolve().parents[4]
SCRIPTS = REPOSITORY / "plugins/versionkeeping/skills/checkpointing-and-publishing-git-work/scripts"
sys.path.insert(0, str(SCRIPTS))
from git_publication import adapter, deletion, execution  # noqa: E402


@unittest.skipUnless(sys.platform.startswith("linux"), "bounded Linux gh provider")
class GitHubCredentialTests(unittest.TestCase):
    endpoint = "https://github.com/owner/repository.git"
    token = "synthetic-github-token-do-not-use"

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="gh-credential-", dir=REPOSITORY.parent)
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.config = self.home / ".config/git/config"
        self.config.parent.mkdir(parents=True)
        self.repo_path = self.root / "repo"
        self.repo_path.mkdir()
        self.helper = self.root / "gh"
        self.helper.write_text(
            "#!/usr/bin/python3\nimport os,sys\n"
            "sys.stdin.read()\n"
            "token=os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')\n"
            "if not token: sys.exit(1)\n"
            "if sys.argv[-1]=='get': print('username=synthetic\\npassword='+token+'\\n')\n"
        )
        self.helper.chmod(0o700)
        self.helper_value = "!" + str(self.helper) + " auth git-credential"
        self.config.write_text('[credential "https://github.com"]\n\thelper = ' + self.helper_value + "\n")
        self.harmless_include = self.root / "harmless.gitconfig"
        self.harmless_include.write_text("[example]\n harmlessMarker = present\n")
        self.env_patch = mock.patch.dict(os.environ, {
            "HOME": str(self.home), "XDG_CONFIG_HOME": str(self.home / ".config"),
            "PATH": "/usr/bin:/bin", "GH_TOKEN": self.token,
            adapter.GIT_CONFIG_PROFILE_ENV: "host-compatible",
        }, clear=True)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.provider_patch = mock.patch.object(adapter, "GITHUB_GH_EXECUTABLE", self.helper, create=True)
        self.provider_patch.start()
        self.addCleanup(self.provider_patch.stop)
        subprocess.run(["/usr/bin/git", "init", "-q", str(self.repo_path)], check=True)

    def repository(self):
        return adapter.GitRepository(self.repo_path, config_profile="host-compatible",
                                     publication_credentials=True)

    def test_existing_session_token_reaches_real_git_credential_lookup_only(self):
        with self.repository() as repo:
            self.assertNotIn("GH_TOKEN", repo.env)
            repo.ensure_https_credentials(self.endpoint)
            self.assertNotIn("GH_TOKEN", repo.env)

    def test_unrelated_ancestor_entries_preserve_complete_credential_policy(self):
        askpass = self.root / "askpass"
        askpass.write_text("#!/bin/sh\nexit 1\n")
        askpass.chmod(0o700)
        with mock.patch.object(adapter, "GITHUB_ASKPASS_EXECUTABLE", askpass):
            with self.repository() as repo:
                first = repo.publication_credential_policy(self.endpoint)
                digest = adapter._config_digest({"credential_environment": first}, "sha256:example")
                for name, executable in (("provider_identity", self.helper), ("askpass_identity", askpass)):
                    self.assertEqual({Path(path) for path, _ in first[name]},
                                     {*executable.parents, executable})
                sibling = self.root / "unrelated"
                sibling.mkdir()
                (sibling / "entry").write_text("unrelated")
                self.assertEqual(repo.publication_credential_policy(self.endpoint), first)
                sibling.rename(self.root / "renamed")
                with self.repository() as fresh:
                    third = fresh.publication_credential_policy(self.endpoint)
                self.assertEqual(third, first)
                self.assertEqual(adapter._config_digest({"credential_environment": third}, "sha256:example"), digest)
                (self.root / "renamed/entry").unlink()
                (self.root / "renamed").rmdir()
                self.assertEqual(repo.publication_credential_policy(self.endpoint), first)
                with self.assertRaises(AssertionError):
                    self.assertEqual(third["source"], "not-the-selected-source")

    def test_provider_ancestor_mode_drift_blocks_before_credential_delivery(self):
        with self.repository() as repo:
            repo.publication_credential_policy(self.endpoint)
            original_mode = self.root.stat().st_mode & 0o777
            self.root.chmod(original_mode ^ 0o100)
            try:
                with mock.patch.object(adapter.subprocess, "run") as run:
                    with self.assertRaises(adapter.PolicyGate) as raised:
                        repo.ensure_https_credentials(self.endpoint)
                self.assertEqual(raised.exception.code, "TRUSTED_GIT_RUNTIME_CHANGED")
                run.assert_not_called()
            finally:
                self.root.chmod(original_mode)

    def test_precedence_and_rotation_bind_names_not_token_bytes(self):
        with self.repository() as repo:
            first = repo.publication_credential_policy(self.endpoint)
            digest = adapter._config_digest({"credential_environment": first}, "sha256:example")
            os.environ["GH_TOKEN"] = "rotated-synthetic-value"
            os.environ["GITHUB_TOKEN"] = "fallback-synthetic-value"
            second = repo.publication_credential_policy(self.endpoint)
            self.assertEqual(first["source"], "GH_TOKEN")
            self.assertEqual(digest, adapter._config_digest({"credential_environment": second}, "sha256:example"))
            self.assertNotIn(self.token, json.dumps(first))
            self.assertNotIn(hashlib.sha256(self.token.encode()).hexdigest(), json.dumps(first))
        del os.environ["GH_TOKEN"]
        with self.repository() as repo:
            fallback = repo.publication_credential_policy(self.endpoint)
            self.assertEqual(fallback["source"], "GITHUB_TOKEN")
            self.assertNotEqual(digest, adapter._config_digest({"credential_environment": fallback}, "sha256:example"))
            repo.ensure_https_credentials(self.endpoint)

    def test_transport_gets_only_selected_token_and_fixed_safety_options(self):
        os.environ.update({"GITHUB_TOKEN": "fallback-synthetic", "GH_DEBUG": "api",
                           "DEBUG": "all", "GH_HOST": "elsewhere.invalid",
                           "GH_CONFIG_DIR": "/untrusted", "GIT_TRACE": "1"})
        with self.repository() as repo:
            repo.publication_credential_policy(self.endpoint)
            calls = []
            real_run = subprocess.run
            def run(args, **kwargs):
                if "ls-remote" in args:
                    calls.append((args, kwargs["env"]))
                    return subprocess.CompletedProcess(args, 0, "", "")
                return real_run(args, **kwargs)
            with mock.patch.object(adapter.subprocess, "run", side_effect=run):
                adapter._run_endpoint(repo, self.endpoint, ["ls-remote", "--heads"])
            args, env = calls[0]
            self.assertEqual(env["GH_TOKEN"], self.token)
            for key in ("GITHUB_TOKEN", "GH_DEBUG", "DEBUG", "GH_HOST", "GH_CONFIG_DIR", "GIT_TRACE"):
                self.assertNotIn(key, env)
            self.assertEqual(env["GH_PROMPT_DISABLED"], "1")
            self.assertEqual(env["GIT_ASKPASS"], str(adapter.GITHUB_ASKPASS_EXECUTABLE))
            self.assertEqual(env["SSH_ASKPASS"], str(adapter.GITHUB_ASKPASS_EXECUTABLE))
            self.assertTrue(Path(env["GIT_ASKPASS"]).is_absolute())
            self.assertEqual(env["GIT_TERMINAL_PROMPT"], "0")
            self.assertEqual(env["SSH_ASKPASS_REQUIRE"], "never")
            self.assertIn("http.sslVerify=true", args)
            self.assertIn("http.followRedirects=false", args)
            self.assertIn("core.fsmonitor=false", args)
            self.assertIn(f"core.hooksPath={repo.hooks_path}", args)
            self.assertNotIn(self.token, " ".join(args))
            self.assertNotIn("GH_TOKEN", repo.env)

    def test_nontransport_hardened_and_other_authorities_receive_no_token(self):
        with self.repository() as repo:
            with self.assertRaises(adapter.PolicyGate) as raised:
                repo.run_transport(["rev-parse", "HEAD"], self.endpoint,
                    env_overrides={"VERSIONKEEPING_PUBLICATION_ENDPOINT": self.endpoint})
            self.assertEqual(raised.exception.code, "GIT_CREDENTIAL_TRANSPORT_REQUIRED")
            self.assertNotIn("GH_TOKEN", repo._credential_environment("https://other.invalid/repo")[0])
            self.assertNotIn("GH_TOKEN", repo._credential_environment("ssh://git@github.com/repo")[0])
            self.assertNotIn("GH_TOKEN", repo._credential_environment("https://github.com:444/repo")[0])
            repo.config_profile = "hardened"
            self.assertNotIn("GH_TOKEN", repo._credential_environment(self.endpoint)[0])

    def test_conflicting_global_path_and_malformed_helpers_are_refused(self):
        for extra in ('[credential]\n helper = !unsafe-command\n',
                      '[credential "https://github.com/other"]\n helper = unsafe\n',
                      '[credential "github.com"]\n helper = unsafe\n'):
            with self.subTest(extra=extra):
                self.config.write_text(extra + '[credential "https://github.com"]\n helper = ' + self.helper_value + '\n')
                with self.repository() as repo:
                    with self.assertRaises(adapter.PolicyGate) as raised:
                        repo.ensure_https_credentials(self.endpoint)
                    self.assertEqual(raised.exception.code, "GITHUB_CREDENTIAL_HELPER_CONFLICT")

    def test_unrelated_host_helper_and_explicit_reset_are_safe(self):
        self.config.write_text('[credential "https://gitlab.com"]\n helper = other\n'
                               '[credential "https://github.com"]\n helper =\n helper = ' + self.helper_value + '\n')
        with self.repository() as repo:
            repo.ensure_https_credentials(self.endpoint)

    def test_other_host_provider_retains_scrubbed_behavior_until_gh_is_selected(self):
        self.config.write_text('[credential]\n helper = other-provider\n'
                               '[http]\n extraHeader = ordinary-host-value\n'
                               '[includeIf "gitdir:/inactive-fixture/"]\n path = ' + str(self.harmless_include) + '\n')
        with self.repository() as repo:
            self.assertIsNone(repo.publication_credential_policy(self.endpoint))
            env, options = repo._credential_environment(self.endpoint)
            self.assertNotIn("GH_TOKEN", env)
            self.assertEqual(options, [])

    def test_conditional_includes_are_refused_before_credential_use(self):
        for condition, nested in (("gitdir:/inactive-fixture/", False),
                                  ("onbranch:unmatched-branch", False),
                                  ("gitdir:/inactive-fixture/", True)):
            with self.subTest(condition=condition, nested=nested):
                directive = f'[includeIf "{condition}"]\n path = {self.harmless_include}\n'
                if nested:
                    ordinary = self.root / "ordinary.gitconfig"
                    ordinary.write_text(directive)
                    directive = f'[include]\n path = {ordinary}\n'
                self.config.write_text('[credential "https://github.com"]\n helper = ' + self.helper_value + '\n' + directive)
                with self.repository() as repo:
                    real_run = subprocess.run
                    credential_calls = []
                    def run(args, **kwargs):
                        if "credential" in args and "fill" in args:
                            credential_calls.append(args)
                        return real_run(args, **kwargs)
                    with mock.patch.object(adapter.subprocess, "run", side_effect=run):
                        with self.assertRaises(adapter.PolicyGate) as raised:
                            repo.ensure_https_credentials(self.endpoint)
                    self.assertEqual(raised.exception.code, "UNSAFE_GIT_CONFIGURATION")
                    self.assertEqual(raised.exception.evidence, {"config_classes": ["includeIf.*"]})
                    self.assertEqual(credential_calls, [])

    def test_conditional_remote_context_is_refused_even_when_currently_inactive(self):
        subprocess.run(["/usr/bin/git", "-C", str(self.repo_path), "remote", "add", "origin",
                        "https://github.com/owner/fetch.git"], check=True)
        subprocess.run(["/usr/bin/git", "-C", str(self.repo_path), "remote", "set-url", "--push", "origin",
                        self.endpoint], check=True)
        self.config.write_text('[credential "https://github.com"]\n helper = ' + self.helper_value +
            f'\n[includeIf "hasconfig:remote.*.url:{self.endpoint}"]\n path = {self.harmless_include}\n')
        with self.repository() as repo:
            query = ["config", "--includes", "--name-only", "--list"]
            before = repo.run(query).stdout.lower()
            context = repo.run(["-c", "remote.versionkeeping-publication-fixture.url=" + self.endpoint, *query]).stdout.lower()
            self.assertNotIn("example.harmlessmarker", before)
            self.assertIn("example.harmlessmarker", context)
            with self.assertRaises(adapter.PolicyGate) as raised:
                repo._credential_environment(self.endpoint)
            self.assertEqual(raised.exception.code, "UNSAFE_GIT_CONFIGURATION")

    def test_ordinary_includes_work_but_later_condition_is_rechecked(self):
        self.config.write_text('[credential "https://github.com"]\n helper = ' + self.helper_value +
                               f'\n[include]\n path = {self.harmless_include}\n')
        with self.repository() as repo:
            repo.ensure_https_credentials(self.endpoint)
            with self.config.open("a") as stream:
                stream.write(f'[includeIf "gitdir:/inactive-fixture/"]\n path = {self.harmless_include}\n')
            with self.assertRaises(adapter.PolicyGate) as raised:
                repo._credential_environment(self.endpoint)
            self.assertEqual(raised.exception.code, "UNSAFE_GIT_CONFIGURATION")

    def test_http_and_credential_overrides_fail_without_disclosing_values(self):
        for section, key in (("http", "sslVerify"), ("http", "extraHeader"),
                             ("credential", "username"), ('url "https://other.invalid/"', "insteadOf")):
            with self.subTest(section=section, key=key):
                self.config.write_text('[credential "https://github.com"]\n helper = ' + self.helper_value +
                                       f'\n[{section}]\n {key} = secret-looking-override\n')
                with self.repository() as repo:
                    with self.assertRaises(adapter.PolicyGate) as raised:
                        repo.ensure_https_credentials(self.endpoint)
                    self.assertEqual(raised.exception.code, "UNSAFE_GIT_CONFIGURATION")
                    self.assertNotIn("secret-looking", str(raised.exception.evidence))

    def test_source_or_helper_change_is_refused_before_another_transport(self):
        with self.repository() as repo:
            repo.publication_credential_policy(self.endpoint)
            del os.environ["GH_TOKEN"]
            os.environ["GITHUB_TOKEN"] = "fallback-synthetic"
            with self.assertRaises(adapter.PolicyGate) as raised:
                repo.publication_credential_policy(self.endpoint)
            self.assertEqual(raised.exception.code, "GITHUB_CREDENTIAL_POLICY_CHANGED")

    def test_missing_token_keeps_existing_provider_failure(self):
        del os.environ["GH_TOKEN"]
        with self.config.open("a") as stream:
            stream.write(f'[includeIf "gitdir:/inactive-fixture/"]\n path = {self.harmless_include}\n')
        with self.repository() as repo:
            with self.assertRaises(adapter.PolicyGate) as raised:
                repo.ensure_https_credentials(self.endpoint)
            self.assertEqual(raised.exception.code, "HTTPS_CREDENTIALS_UNAVAILABLE")

    def test_provider_replacement_is_refused(self):
        with self.repository() as repo:
            repo.publication_credential_policy(self.endpoint)
            self.helper.write_text("#!/bin/sh\nexit 0\n")
            with self.assertRaises(adapter.PolicyGate) as raised:
                repo.ensure_https_credentials(self.endpoint)
            self.assertEqual(raised.exception.code, "TRUSTED_GIT_RUNTIME_CHANGED")

    def test_untrusted_provider_is_refused_before_credential_delivery(self):
        self.helper.chmod(0o722)
        with self.repository() as repo:
            with self.assertRaises(adapter.PolicyGate) as raised:
                repo.ensure_https_credentials(self.endpoint)
            self.assertEqual(raised.exception.code, "GITHUB_CREDENTIAL_PROVIDER_UNAVAILABLE")

    def test_credential_timeout_is_redacted(self):
        with self.repository() as repo:
            real_run = subprocess.run
            def run(args, **kwargs):
                if "credential" in args and "fill" in args:
                    raise subprocess.TimeoutExpired(args, 1)
                return real_run(args, **kwargs)
            with mock.patch.object(adapter.subprocess, "run", side_effect=run):
                with self.assertRaises(adapter.PolicyGate) as raised:
                    repo.ensure_https_credentials(self.endpoint)
            self.assertEqual(raised.exception.code, "HTTPS_CREDENTIALS_UNAVAILABLE")
            self.assertNotIn(self.token, str(raised.exception.evidence))

    def test_failed_selected_helper_uses_only_bound_nonprompting_fallback(self):
        self.helper.write_text("#!/bin/sh\nexit 1\n")
        os.environ["PATH"] = "/nonexistent-untrusted-prefix:/usr/bin:/bin"
        with self.repository() as repo:
            real_run = subprocess.run
            credential_environments = []
            def run(args, **kwargs):
                if "credential" in args and "fill" in args:
                    credential_environments.append(kwargs["env"])
                return real_run(args, **kwargs)
            with mock.patch.object(adapter.subprocess, "run", side_effect=run):
                with self.assertRaises(adapter.PolicyGate) as raised:
                    repo.ensure_https_credentials(self.endpoint)
            self.assertEqual(raised.exception.code, "HTTPS_CREDENTIALS_UNAVAILABLE")
            self.assertEqual(len(credential_environments), 1)
            env = credential_environments[0]
            self.assertEqual(env["GH_TOKEN"], self.token)
            self.assertEqual(env["GIT_ASKPASS"], str(adapter.GITHUB_ASKPASS_EXECUTABLE))
            self.assertTrue(Path(env["GIT_ASKPASS"]).is_absolute())
            self.assertEqual(env["GIT_TERMINAL_PROMPT"], "0")

    def test_missing_or_changed_askpass_binding_refuses_before_credential_call(self):
        real_bind = adapter.bind_host_executable
        def unavailable(path, **kwargs):
            if Path(path) == adapter.GITHUB_ASKPASS_EXECUTABLE:
                raise OSError("fixture unavailable")
            return real_bind(path, **kwargs)
        with self.repository() as repo:
            with mock.patch.object(adapter, "bind_host_executable", side_effect=unavailable):
                with self.assertRaises(adapter.PolicyGate) as raised:
                    repo.publication_credential_policy(self.endpoint)
            self.assertEqual(raised.exception.code, "GITHUB_CREDENTIAL_FALLBACK_UNAVAILABLE")
        with self.repository() as repo:
            repo.publication_credential_policy(self.endpoint)
            self.assertIsNotNone(repo._github_askpass)
            real_recheck = adapter.recheck_host_executable
            def changed(bound):
                if bound.path == str(adapter.GITHUB_ASKPASS_EXECUTABLE):
                    raise OSError("fixture identity changed")
                return real_recheck(bound)
            with mock.patch.object(adapter, "recheck_host_executable", side_effect=changed):
                with mock.patch.object(adapter.subprocess, "run") as run:
                    with self.assertRaises(adapter.PolicyGate) as raised:
                        repo.ensure_https_credentials(self.endpoint)
            self.assertEqual(raised.exception.code, "TRUSTED_GIT_RUNTIME_CHANGED")
            run.assert_not_called()

    def test_repository_capability_defaults_off(self):
        with adapter.GitRepository(self.repo_path, config_profile="host-compatible") as repo:
            self.assertIsNone(repo.publication_credential_policy(self.endpoint))
            env, options = repo._credential_environment(self.endpoint)
            self.assertNotIn("GH_TOKEN", env)
            self.assertEqual(options, [])

    def test_real_tls_git_transport_uses_synthetic_credentials(self):
        path = Path(__file__).with_name("test_git_publication_execution.py")
        spec = importlib.util.spec_from_file_location("credential_transport_fixture", path)
        fixture = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixture)
        tls_root = self.root / "tls"
        tls_root.mkdir()
        self.config.write_text("[credential]\n helper = " + self.helper_value + "\n")
        with fixture.authenticated_https_endpoint(tls_root, "synthetic", self.token, "a" * 40) as (endpoint, cert, authenticated):
            original_authority = adapter._github_credential_authority
            with mock.patch.object(adapter, "_github_credential_authority",
                                   side_effect=lambda value: value == endpoint or original_authority(value)):
                with self.repository() as repo:
                    repo.ensure_https_credentials(endpoint)
                    result = adapter._run_endpoint(repo, endpoint,
                        ["-c", f"http.sslCAInfo={cert}", "ls-remote", "--refs"], ["refs/heads/main"])
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertTrue(authenticated.is_set())
                    self.assertEqual(result.stdout.strip(), "a" * 40 + "\trefs/heads/main")
                    self.assertNotIn(self.token, result.stdout + result.stderr)
                    os.environ["GH_TOKEN"] = "rejected-synthetic-credential"
                    refused = adapter._run_endpoint(repo, endpoint,
                        ["-c", f"http.sslCAInfo={cert}", "ls-remote", "--refs"], ["refs/heads/main"])
                    self.assertNotEqual(refused.returncode, 0)
                    self.assertNotIn(os.environ["GH_TOKEN"], refused.stdout + refused.stderr)

    def test_public_planner_executor_bind_credential_policy_for_every_transport(self):
        remote = self.root / "remote.git"
        def git(path, *args):
            return subprocess.run(["/usr/bin/git", *args], cwd=path, check=True,
                                  text=True, capture_output=True).stdout.strip()
        git(self.root, "init", "--bare", "-q", str(remote))
        git(self.repo_path, "config", "user.name", "Test")
        git(self.repo_path, "config", "user.email", "test@example.com")
        (self.repo_path / "base").write_text("base")
        git(self.repo_path, "add", "base")
        git(self.repo_path, "commit", "-qm", "base")
        start = git(self.repo_path, "rev-parse", "HEAD")
        git(self.repo_path, "push", str(remote), f"{start}:refs/heads/main")
        git(remote, "symbolic-ref", "HEAD", "refs/heads/main")
        git(self.repo_path, "remote", "add", "publish", self.endpoint)
        (self.repo_path / "change").write_text("change")
        git(self.repo_path, "add", "change")
        git(self.repo_path, "commit", "-qm", "change")
        source = git(self.repo_path, "rev-parse", "HEAD")
        request = {"schema_version": 2, "start_head": start, "source_sha": source,
                   "task_owned_commits": [source], "adopted_commits": [],
                   "removal_authorized_commits": [], "default_branch_policy": None,
                   "explicit_destination": {"remote": "publish", "ref": "refs/heads/topic"},
                   "allow_create": True, "creation_base_ref": "refs/heads/main"}
        real_run = subprocess.run
        transports = []
        credential_calls = []
        change_source_after_push = [False]
        def substitute_transport(args, **kwargs):
            env = kwargs.get("env", {})
            if "credential" in args and "fill" in args:
                credential_calls.append("fill")
            if env.get("VERSIONKEEPING_PUBLICATION_ENDPOINT") == self.endpoint:
                # This seam replaces the wire with real local Git; credential
                # lookup and the separate TLS test execute their real paths.
                selected = "GH_TOKEN" if os.environ.get("GH_TOKEN") else "GITHUB_TOKEN"
                self.assertEqual(env.get(selected), os.environ[selected])
                self.assertNotIn("GITHUB_TOKEN" if selected == "GH_TOKEN" else "GH_TOKEN", env)
                transports.append(next(arg for arg in args if arg in ("ls-remote", "fetch", "push")))
                kwargs["env"] = dict(env, VERSIONKEEPING_PUBLICATION_ENDPOINT=str(remote))
            result = real_run(args, **kwargs)
            if change_source_after_push[0] and "push" in args:
                os.environ["GH_TOKEN"] = os.environ.pop("GITHUB_TOKEN")
                change_source_after_push[0] = False
            return result
        def execute(plan):
            raw = (json.dumps(plan, sort_keys=True, separators=(",", ":")) + "\n").encode()
            return execution.execute_repository(self.repo_path, raw, "sha256:" + hashlib.sha256(raw).hexdigest())
        with mock.patch.object(adapter.subprocess, "run", side_effect=substitute_transport):
            selections = []
            real_digest = adapter._config_digest

            def capture_digest(selection, fingerprint):
                selections.append((json.loads(json.dumps(selection)), fingerprint))
                return real_digest(selection, fingerprint)

            with mock.patch.object(adapter, "_config_digest", side_effect=capture_digest):
                plan = adapter.plan_repository(self.repo_path, request)
            self.assertEqual(plan["status"], "ready")
            # The old directory representation must require fresh planning and
            # review before either credential delivery or outbound transport.
            old_selection, fingerprint = selections[-1]
            for key in ("provider_identity", "askpass_identity"):
                for entry in old_selection["credential_environment"][key]:
                    path = Path(entry[0])
                    if path.is_dir():
                        value = path.lstat()
                        entry[1] = [value.st_dev, value.st_ino, value.st_mode,
                                    value.st_uid, value.st_gid, value.st_nlink,
                                    value.st_size, value.st_mtime_ns, value.st_ctime_ns]
            old_plan = json.loads(json.dumps(plan))
            old_plan["destination"]["config_digest"] = real_digest(old_selection, fingerprint)
            self.assertNotEqual(old_plan["destination"]["config_digest"], plan["destination"]["config_digest"])
            before_old = (list(transports), list(credential_calls))
            refused_old = execute(old_plan)
            self.assertEqual(refused_old["reasons"][0]["code"], "REVIEWED_CONFIG_CHANGED")
            self.assertFalse(refused_old["push_attempted"])
            self.assertEqual((transports, credential_calls), before_old)
            (self.root / "unrelated-plan-entry").write_text("unrelated")
            fresh_plan = adapter.plan_repository(self.repo_path, request)
            self.assertEqual(fresh_plan["status"], "ready", fresh_plan)
            self.assertEqual(fresh_plan["destination"]["config_digest"], plan["destination"]["config_digest"])
            os.environ["GITHUB_TOKEN"] = os.environ.pop("GH_TOKEN")
            before_refusal = list(transports)
            before_credentials = list(credential_calls)
            refused = execute(plan)
            self.assertEqual(refused["status"], "blocked")
            self.assertFalse(refused["push_attempted"])
            self.assertEqual(refused["reasons"][0]["code"], "REVIEWED_CONFIG_CHANGED")
            self.assertEqual(transports, before_refusal)
            self.assertEqual(credential_calls, before_credentials)
            # Removed source, helper selection, or admissible provider identity
            # must also refuse before transport, not only before the push.
            for change in ("source-removed", "helper-removed", "provider-changed", "conditional-added"):
                os.environ["GH_TOKEN"] = self.token
                os.environ.pop("GITHUB_TOKEN", None)
                current_plan = adapter.plan_repository(self.repo_path, request)
                before_refusal = list(transports)
                before_credentials = list(credential_calls)
                if change == "source-removed":
                    del os.environ["GH_TOKEN"]
                elif change == "helper-removed":
                    self.config.write_text("[credential]\n helper = other-provider\n")
                elif change == "conditional-added":
                    with self.config.open("a") as stream:
                        stream.write(f'[includeIf "gitdir:/inactive-fixture/"]\n path = {self.harmless_include}\n')
                else:
                    self.helper.write_bytes(self.helper.read_bytes())
                changed = execute(current_plan)
                self.assertEqual(changed["status"], "blocked", change)
                self.assertFalse(changed["push_attempted"], change)
                self.assertEqual(transports, before_refusal, change)
                self.assertEqual(credential_calls, before_credentials, change)
                self.config.write_text('[credential "https://github.com"]\n helper = ' + self.helper_value + '\n')
            os.environ["GITHUB_TOKEN"] = os.environ.pop("GH_TOKEN")
            plan = adapter.plan_repository(self.repo_path, request)
            result = execute(plan)
            self.assertEqual(result["status"], "verified")
            self.assertEqual(transports.count("push"), 1)
            (self.repo_path / "later").write_text("later")
            git(self.repo_path, "add", "later")
            git(self.repo_path, "commit", "-qm", "later")
            later = git(self.repo_path, "rev-parse", "HEAD")
            request.update(start_head=source, source_sha=later,
                           task_owned_commits=[later], allow_create=False)
            later_plan = adapter.plan_repository(self.repo_path, request)
            self.assertEqual(later_plan["status"], "ready")
            change_source_after_push[0] = True
            unknown = execute(later_plan)
            self.assertEqual(unknown["status"], "blocked")
            self.assertTrue(unknown["push_attempted"])
            self.assertEqual(unknown["reasons"][0]["code"], "POST_PUSH_STATE_UNKNOWN")
            self.assertEqual(git(remote, "rev-parse", "refs/heads/topic"), later)
        self.assertEqual(transports.count("push"), 2)
        self.assertGreater(transports.count("ls-remote"), 3)
        for document in (plan, result, refused, later_plan, unknown):
            self.assertNotIn(self.token, json.dumps(document))
            self.assertNotIn(hashlib.sha256(self.token.encode()).hexdigest(), json.dumps(document))
        self.assertNotIn(self.token, self.config.read_text())

    def test_deletion_public_entrypoints_keep_the_prior_scrubbed_environment(self):
        remote = self.root / "deletion-remote.git"
        def git(path, *args):
            return subprocess.run(["/usr/bin/git", *args], cwd=path, check=True,
                                  text=True, capture_output=True).stdout.strip()
        git(self.root, "init", "--bare", "-q", str(remote))
        git(self.repo_path, "config", "user.name", "Test")
        git(self.repo_path, "config", "user.email", "test@example.com")
        (self.repo_path / "fixture").write_text("fixture")
        git(self.repo_path, "add", "fixture")
        git(self.repo_path, "commit", "-qm", "fixture")
        target = git(self.repo_path, "rev-parse", "HEAD")
        git(self.repo_path, "push", str(remote), f"{target}:refs/heads/topic")
        git(self.repo_path, "remote", "add", "publish", self.endpoint)
        self.config.write_text('[credential "https://github.com"]\n helper = ' + self.helper_value +
                               '\n[http]\n userAgent = prior-host-setting\n'
                               f'[includeIf "hasconfig:remote.*.url:{self.endpoint}"]\n path = {self.harmless_include}\n')
        grant = {"authorized": True, "remote": "publish", "ref": "refs/heads/topic",
                 "expected_target_sha": target}
        request = {"schema_version": 1, "remote": "publish", "ref": "refs/heads/topic",
                   "expected_target_sha": target,
                   "verified_merge": {"status": "verified", "merged_source_sha": target,
                                      "merged_result_sha": "f" * 40},
                   "authorization": {"repository": dict(grant), "operator": dict(grant)}}
        real_run = subprocess.run
        calls = []
        def substitute_wire(args, **kwargs):
            env = kwargs.get("env", {})
            if env.get("VERSIONKEEPING_PUBLICATION_ENDPOINT") == self.endpoint:
                self.assertNotIn("GH_TOKEN", env)
                self.assertNotIn("GITHUB_TOKEN", env)
                self.assertNotIn("GH_PROMPT_DISABLED", env)
                calls.append(next(arg for arg in args if arg in ("ls-remote", "push")))
                kwargs["env"] = dict(env, VERSIONKEEPING_PUBLICATION_ENDPOINT=str(remote))
            return real_run(args, **kwargs)
        with mock.patch.object(adapter.subprocess, "run", side_effect=substitute_wire):
            plan = deletion.plan_remote_ref_deletion(self.repo_path, request)
            self.assertEqual(plan["status"], "ready")
            raw = (json.dumps(plan, sort_keys=True, separators=(",", ":")) + "\n").encode()
            result = deletion.execute_remote_ref_deletion(
                self.repo_path, raw, "sha256:" + hashlib.sha256(raw).hexdigest())
            self.assertEqual(result["status"], "verified")
            self.assertTrue(result["deletion_attempted"])
        self.assertEqual(calls.count("push"), 1)
        absent = subprocess.run(["/usr/bin/git", "show-ref", "--verify", "--quiet", "refs/heads/topic"], cwd=remote)
        self.assertEqual(absent.returncode, 1)
