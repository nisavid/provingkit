from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPOSITORY = Path(__file__).resolve().parents[4]
SKILLS_ROOT = REPOSITORY / "plugins/mergecraft/skills"
SKILL_ROOT = SKILLS_ROOT / "getting-prs-merged"
PUBLISHER_SCRIPTS = SKILLS_ROOT / "publishing-reviewable-prs" / "scripts"
sys.path.insert(0, str(PUBLISHER_SCRIPTS))
import reviewable_pr_state as STATE


def load_comment_module(name: str):
    path = SKILL_ROOT / "scripts" / "post_coderabbit_comment.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


COMMENT = load_comment_module("post_coderabbit_comment")


class TopLevelCommentActuatorTests(unittest.TestCase):
    repository = "acme/app"
    pr_number = 42
    base = "main"
    base_oid = "a" * 40
    head = "fork-owner:widget"
    head_oid = "b" * 40
    head_owner = "fork-owner"
    head_repository = "fork-owner/app-fork"
    url = "https://github.com/acme/app/pull/42"
    login = "merge-operator"

    @property
    def expected(self):
        return COMMENT.ExpectedIdentity(
            repository=self.repository,
            pr_number=self.pr_number,
            base=self.base,
            base_oid=self.base_oid,
            head=self.head,
            head_oid=self.head_oid,
            head_owner=self.head_owner,
            head_repository=self.head_repository,
        )

    def stored(self) -> dict[str, object]:
        return {
            "number": self.pr_number,
            "url": self.url,
            "baseRefName": self.base,
            "baseRefOid": self.base_oid,
            "headRefName": "widget",
            "headRefOid": self.head_oid,
            "headRepositoryOwner": {"login": self.head_owner},
            "headRepository": {"nameWithOwner": self.head_repository},
            "title": "feat: widget",
            "body": "body",
            "isDraft": False,
            "state": "OPEN",
        }

    def test_posts_once_and_returns_exact_reread_receipt(self) -> None:
        body = "@coderabbitai review"
        created = {
            "id": 91,
            "html_url": f"{self.url}#issuecomment-91",
            "body": body,
            "user": {"login": self.login},
            "created_at": "2026-07-21T12:34:56Z",
        }
        with (
            mock.patch.object(COMMENT, "_active_login", return_value=self.login),
            mock.patch.object(
                COMMENT, "_stored_pr", return_value=self.stored()
            ) as stored,
            mock.patch.object(
                COMMENT,
                "_run_mutation",
                return_value=subprocess.CompletedProcess(
                    [], 0, json.dumps(created), ""
                ),
            ) as mutate,
            mock.patch.object(
                COMMENT,
                "_run_read",
                return_value=subprocess.CompletedProcess(
                    [], 0, json.dumps(created), ""
                ),
            ),
        ):
            receipt = COMMENT.post_comment(
                expected=self.expected,
                expected_authenticated_login=self.login,
                body=body,
                body_sha256=hashlib.sha256(body.encode()).hexdigest(),
            )
        self.assertEqual(
            receipt,
            {
                "id": 91,
                "html_url": f"{self.url}#issuecomment-91",
                "body_sha256": hashlib.sha256(body.encode()).hexdigest(),
                "user": {"login": self.login},
                "created_at": "2026-07-21T12:34:56Z",
            },
        )
        self.assertEqual(mutate.call_count, 1)
        self.assertEqual(stored.call_count, 2)

    def test_cli_acknowledgement_omits_body_and_unexpected_provider_fields(
        self,
    ) -> None:
        raw = b"Authorization: ghp_sensitive-looking-body\r\nsecret=opaque\n"
        body = raw.decode("utf-8")
        created = {
            "id": 91,
            "html_url": f"{self.url}#issuecomment-91",
            "body": body,
            "user": {"login": self.login},
            "created_at": "2026-07-21T12:34:56Z",
            "provider_debug": "Bearer provider-sensitive-value\x1b[31m",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "body.md"
            path.write_bytes(raw)
            arguments = [
                "post_coderabbit_comment.py",
                "--repository",
                self.repository,
                "--pr",
                str(self.pr_number),
                "--base",
                self.base,
                "--base-oid",
                self.base_oid,
                "--head",
                self.head,
                "--head-oid",
                self.head_oid,
                "--head-owner",
                self.head_owner,
                "--head-repository",
                self.head_repository,
                "--body-file",
                str(path),
                "--body-sha256",
                hashlib.sha256(raw).hexdigest(),
                "--expected-authenticated-login",
                self.login,
            ]
            with (
                mock.patch.object(sys, "argv", arguments),
                mock.patch.object(COMMENT, "_active_login", return_value=self.login),
                mock.patch.object(
                    COMMENT, "_stored_pr", return_value=self.stored()
                ),
                mock.patch.object(
                    COMMENT,
                    "_run_mutation",
                    return_value=subprocess.CompletedProcess(
                        [], 0, json.dumps(created), ""
                    ),
                ) as mutate,
                mock.patch.object(
                    COMMENT,
                    "_run_read",
                    return_value=subprocess.CompletedProcess(
                        [], 0, json.dumps(created), ""
                    ),
                ),
                mock.patch("builtins.print") as output,
            ):
                self.assertEqual(COMMENT.main(), 0)

        acknowledgement = json.loads(output.call_args.args[0])
        self.assertEqual(
            set(acknowledgement),
            {"id", "html_url", "body_sha256", "user", "created_at"},
        )
        self.assertEqual(acknowledgement["body_sha256"], hashlib.sha256(raw).hexdigest())
        rendered = output.call_args.args[0]
        self.assertNotIn(body, rendered)
        self.assertNotIn("provider_debug", rendered)
        self.assertNotIn("provider-sensitive-value", rendered)
        self.assertEqual(mutate.call_count, 1)

    def test_merge_procedure_captures_closed_comment_acknowledgement(self) -> None:
        procedure = " ".join(
            (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8").split()
        )
        self.assertIn("never returns body bytes or unexpected provider fields", procedure)
        self.assertIn("retains the comment stage, zero-exit fact", procedure)
        self.assertIn("returns no success acknowledgement", procedure)
        self.assertIn(
            "reject expected or observed actor logins that are not display-safe "
            "before mutation or output",
            procedure,
        )
        self.assertIn("nonzero POST also leaves the remote outcome unknown", procedure)
        self.assertIn("existing valid read authority without retry", procedure)
        self.assertIn(
            "local command preparation failure retains the comment stage and proves "
            "that no target mutation ran",
            procedure,
        )
        self.assertIn(
            "Local comment-body failures use fixed classifications", procedure
        )

    def test_cli_preserves_body_file_line_endings_and_terminal_newline(self) -> None:
        bodies = (
            b"first\r\nsecond",
            b"first\r\nsecond\r\n",
            b"first\nsecond",
            b"first\nsecond\n",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "body.md"
            for raw in bodies:
                with self.subTest(raw=raw):
                    path.write_bytes(raw)
                    arguments = [
                        "post_coderabbit_comment.py",
                        "--repository",
                        self.repository,
                        "--pr",
                        str(self.pr_number),
                        "--base",
                        self.base,
                        "--base-oid",
                        self.base_oid,
                        "--head",
                        self.head,
                        "--head-oid",
                        self.head_oid,
                        "--head-owner",
                        self.head_owner,
                        "--head-repository",
                        self.head_repository,
                        "--body-file",
                        str(path),
                        "--body-sha256",
                        hashlib.sha256(raw).hexdigest(),
                        "--expected-authenticated-login",
                        self.login,
                    ]
                    with (
                        mock.patch.object(sys, "argv", arguments),
                        mock.patch.object(
                            COMMENT, "post_comment", return_value={"id": 91}
                        ) as post,
                        mock.patch("builtins.print"),
                    ):
                        self.assertEqual(COMMENT.main(), 0)
                    self.assertEqual(
                        post.call_args.kwargs["body"].encode("utf-8"), raw
                    )

    def test_comment_body_read_failure_is_value_free_and_chained(self) -> None:
        hostile_path = Path("/synthetic/Authorization: arbitrary-secret-value/body.md")
        read_error = OSError("Authorization: arbitrary-secret-value")
        with (
            mock.patch.object(Path, "read_bytes", side_effect=read_error),
            self.assertRaises(COMMENT.PublicationError) as caught,
        ):
            COMMENT._read_body(hostile_path)

        diagnostic = str(caught.exception)
        self.assertEqual(
            diagnostic,
            "cannot read comment body; check the local path and read permissions",
        )
        self.assertIs(caught.exception.__cause__, read_error)
        self.assertNotIn(str(hostile_path), diagnostic)
        self.assertNotIn("arbitrary-secret-value", diagnostic)
        self.assertNotIn("authentication", diagnostic)

        with (
            mock.patch.object(
                Path,
                "read_bytes",
                return_value=b"\xffAuthorization: arbitrary-secret-value",
            ),
            self.assertRaises(COMMENT.PublicationError) as caught,
        ):
            COMMENT._read_body(hostile_path)
        self.assertEqual(str(caught.exception), "comment body must be valid UTF-8")
        self.assertIsInstance(caught.exception.__cause__, UnicodeDecodeError)

        arguments = [
            "post_coderabbit_comment.py",
            "--repository",
            self.repository,
            "--pr",
            str(self.pr_number),
            "--base",
            self.base,
            "--base-oid",
            self.base_oid,
            "--head",
            self.head,
            "--head-oid",
            self.head_oid,
            "--head-owner",
            self.head_owner,
            "--head-repository",
            self.head_repository,
            "--body-file",
            str(hostile_path),
            "--body-sha256",
            "0" * 64,
            "--expected-authenticated-login",
            self.login,
        ]
        with (
            mock.patch.object(sys, "argv", arguments),
            mock.patch.object(Path, "read_bytes", side_effect=read_error),
            mock.patch.object(COMMENT, "post_comment") as post,
            mock.patch("builtins.print") as output,
        ):
            self.assertEqual(COMMENT.main(), 1)

        rendered = output.call_args.args[0]
        self.assertIn("cannot read comment body", rendered)
        self.assertNotIn(str(hostile_path), rendered)
        self.assertNotIn("arbitrary-secret-value", rendered)
        self.assertNotIn("Traceback", rendered)
        post.assert_not_called()

    def test_comment_receipt_rejects_boolean_identifier(self) -> None:
        body = "@coderabbitai review"
        with self.assertRaisesRegex(COMMENT.PublicationError, "does not match"):
            COMMENT._comment_receipt(
                {
                    "id": True,
                    "html_url": f"{self.url}#issuecomment-1",
                    "body": body,
                    "user": {"login": self.login},
                    "created_at": "2026-07-21T12:34:56Z",
                },
                self.expected,
                body,
                self.login,
            )

    def test_comment_receipt_rejects_untrusted_url_suffix(self) -> None:
        body = "@coderabbitai review"
        with self.assertRaisesRegex(COMMENT.PublicationError, "does not match"):
            COMMENT._comment_receipt(
                {
                    "id": 91,
                    "html_url": (
                        f"{self.url}#issuecomment-91"
                        "?token=arbitrary-secret-value\x1b[31m"
                    ),
                    "body": body,
                    "user": {"login": self.login},
                    "created_at": "2026-07-21T12:34:56Z",
                },
                self.expected,
                body,
                self.login,
            )

    def test_comment_receipt_omits_untrusted_extra_fields(self) -> None:
        body = "@coderabbitai review"
        receipt = COMMENT._comment_receipt(
            {
                "id": 91,
                "html_url": f"{self.url}#issuecomment-91",
                "body": body,
                "user": {"login": self.login},
                "created_at": "2026-07-21T12:34:56Z",
                "untrusted": "Authorization: arbitrary-secret-value\x1b[31m",
            },
            self.expected,
            body,
            self.login,
        )

        rendered = json.dumps(receipt, sort_keys=True)
        self.assertNotIn("untrusted", receipt)
        self.assertNotIn("arbitrary-secret-value", rendered)
        self.assertNotIn("Authorization", rendered)
        self.assertNotIn("\u001b", rendered)

    def test_comment_timeout_is_ambiguous_and_never_retried(self) -> None:
        body = "@coderabbitai review"
        with (
            mock.patch.object(COMMENT, "_active_login", return_value=self.login),
            mock.patch.object(COMMENT, "_stored_pr", return_value=self.stored()),
            mock.patch.object(
                COMMENT,
                "_run_mutation",
                side_effect=COMMENT.MutationAmbiguousError("timeout"),
            ) as mutate,
        ):
            with self.assertRaisesRegex(COMMENT.MutationAmbiguousError, "timeout"):
                COMMENT.post_comment(
                    expected=self.expected,
                    expected_authenticated_login=self.login,
                    body=body,
                    body_sha256=hashlib.sha256(body.encode()).hexdigest(),
                )
        self.assertEqual(mutate.call_count, 1)

    def test_post_process_failures_keep_comment_stage_and_safe_mutation_facts(
        self,
    ) -> None:
        body = "@coderabbitai review\nAuthorization: synthetic-body-value"
        failures = (
            (
                "timeout",
                STATE.MutationAmbiguousError(
                    "Authorization: synthetic-provider-value",
                    timeout_seconds=STATE.MUTATION_TIMEOUT_SECONDS,
                ),
                STATE.MutationAmbiguousError,
                f"POST timed out after {STATE.MUTATION_TIMEOUT_SECONDS} seconds",
            ),
            (
                "zero-exit-malformed-output",
                STATE.MutationAmbiguousError(
                    "Authorization: synthetic-provider-value",
                    malformed_output=True,
                ),
                STATE.MutationAmbiguousError,
                "POST exited zero",
            ),
        )
        for name, failure, error_type, fact in failures:
            with self.subTest(name=name):
                with (
                    mock.patch.object(
                        COMMENT, "_active_login", return_value=self.login
                    ),
                    mock.patch.object(
                        COMMENT, "_stored_pr", return_value=self.stored()
                    ),
                    mock.patch.object(
                        COMMENT, "_run_mutation", side_effect=failure
                    ) as mutate,
                    mock.patch.object(COMMENT, "_run_read") as reread,
                    self.assertRaises(error_type) as caught,
                ):
                    COMMENT.post_comment(
                        expected=self.expected,
                        expected_authenticated_login=self.login,
                        body=body,
                        body_sha256=hashlib.sha256(body.encode()).hexdigest(),
                    )

                diagnostic = str(caught.exception)
                self.assertIn("comment stage", diagnostic)
                self.assertIn(fact, diagnostic)
                self.assertIn("canonical success was not acknowledged", diagnostic)
                self.assertIn("no automatic retry", diagnostic)
                self.assertNotIn("Authorization", diagnostic)
                self.assertNotIn("synthetic-provider-value", diagnostic)
                self.assertNotIn("synthetic-body-value", diagnostic)
                self.assertIs(caught.exception.__cause__, failure)
                self.assertIs(caught.exception.mutation_error, failure)
                self.assertEqual(mutate.call_count, 1)
                reread.assert_not_called()

    def test_comment_local_preparation_failure_proves_no_post_ran(self) -> None:
        body = "@coderabbitai review"
        with (
            mock.patch.object(COMMENT, "_active_login", return_value=self.login),
            mock.patch.object(COMMENT, "_stored_pr", return_value=self.stored()),
            mock.patch.object(COMMENT.json, "dumps", return_value="secret-\ud800"),
            mock.patch.object(STATE.subprocess, "run") as run,
            self.assertRaises(COMMENT.PublicationError) as raised,
        ):
            COMMENT.post_comment(
                expected=self.expected,
                expected_authenticated_login=self.login,
                body=body,
                body_sha256=hashlib.sha256(body.encode()).hexdigest(),
            )

        diagnostic = str(raised.exception)
        self.assertIn("comment stage", diagnostic)
        self.assertIn("POST could not be prepared locally", diagnostic)
        self.assertIn("no target mutation ran", diagnostic)
        self.assertIn("canonical success was not acknowledged", diagnostic)
        self.assertNotIn("secret", diagnostic)
        preparation_error = raised.exception.__cause__
        self.assertIsInstance(preparation_error, STATE.MutationPreparationError)
        self.assertIsInstance(preparation_error.__cause__, UnicodeEncodeError)
        self.assertIs(raised.exception.mutation_error, preparation_error)
        run.assert_not_called()

    def test_comment_post_start_io_failure_is_unknown_and_never_retried(self) -> None:
        body = "@coderabbitai review"
        events: list[str] = []
        io_error = OSError("Authorization: arbitrary-secret-value")

        class PostStartIoFailure:
            def __init__(self, arguments, **_kwargs):
                self.args = arguments
                self.returncode = None
                events.append("process-created")

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                events.append("process-waited")

            def communicate(self, input=None, timeout=None):
                events.append("communicate-entered")
                raise io_error

            def kill(self):
                events.append("process-killed")

            def wait(self, timeout=None):
                self.returncode = -9
                return self.returncode

        with (
            mock.patch.object(COMMENT, "_active_login", return_value=self.login),
            mock.patch.object(COMMENT, "_stored_pr", return_value=self.stored()),
            mock.patch.object(STATE.subprocess, "Popen", PostStartIoFailure),
            mock.patch.object(COMMENT, "_run_read") as reread,
            self.assertRaises(STATE.MutationAmbiguousError) as caught,
        ):
            COMMENT.post_comment(
                expected=self.expected,
                expected_authenticated_login=self.login,
                body=body,
                body_sha256=hashlib.sha256(body.encode()).hexdigest(),
            )

        diagnostic = str(caught.exception)
        self.assertIn("comment stage", diagnostic)
        self.assertIn("POST process started is unknown", diagnostic)
        self.assertIn("remote outcome unknown", diagnostic)
        self.assertIn("canonical success was not acknowledged", diagnostic)
        self.assertIn("no automatic retry was attempted", diagnostic)
        self.assertNotIn("POST could not start", diagnostic)
        self.assertNotIn("Authorization", diagnostic)
        self.assertIs(caught.exception.mutation_error.__cause__, io_error)
        self.assertEqual(
            events,
            [
                "process-created",
                "communicate-entered",
                "process-killed",
                "process-waited",
            ],
        )
        reread.assert_not_called()

    def test_nonzero_post_is_unknown_and_real_cli_never_retries(self) -> None:
        body = b"@coderabbitai review\nAuthorization: synthetic-body-value"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            post_count = root / "post-count"
            stored_path = root / "stored.json"
            stored_path.write_text(json.dumps(self.stored()), encoding="utf-8")
            fake_gh = fake_bin / "gh"
            fake_gh.write_text(
                """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

arguments = sys.argv[1:]
if "api" in arguments and arguments[-1] == "user":
    print(json.dumps({"login": "merge-operator"}))
elif "pr" in arguments and "view" in arguments:
    print(Path(os.environ["MERGECRAFT_STORED_PR"]).read_text())
elif "api" in arguments and "POST" in arguments:
    count = Path(os.environ["MERGECRAFT_POST_COUNT"])
    count.write_text(str((int(count.read_text()) if count.exists() else 0) + 1))
    sys.stderr.buffer.write(b"Authorization: synthetic-provider-value\\x1b[31m")
    raise SystemExit(37)
else:
    raise SystemExit(96)
""",
                encoding="utf-8",
            )
            fake_gh.chmod(0o700)
            body_path = root / "body.md"
            body_path.write_bytes(body)
            environment = dict(os.environ)
            environment.update(
                {
                    "PATH": str(fake_bin) + os.pathsep + environment.get("PATH", ""),
                    "MERGECRAFT_POST_COUNT": str(post_count),
                    "MERGECRAFT_STORED_PR": str(stored_path),
                }
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(COMMENT.__file__),
                    "--repository",
                    self.repository,
                    "--pr",
                    str(self.pr_number),
                    "--base",
                    self.base,
                    "--base-oid",
                    self.base_oid,
                    "--head",
                    self.head,
                    "--head-oid",
                    self.head_oid,
                    "--head-owner",
                    self.head_owner,
                    "--head-repository",
                    self.head_repository,
                    "--body-file",
                    str(body_path),
                    "--body-sha256",
                    hashlib.sha256(body).hexdigest(),
                    "--expected-authenticated-login",
                    self.login,
                ],
                capture_output=True,
                check=False,
                env=environment,
                text=True,
            )
            recorded_post_count = post_count.read_text()

        self.assertEqual(result.returncode, 1)
        self.assertEqual(recorded_post_count, "1")
        self.assertEqual(result.stdout, "")
        self.assertIn("comment stage", result.stderr)
        self.assertIn("POST exited nonzero (return code 37)", result.stderr)
        self.assertIn("remote outcome is unknown", result.stderr)
        self.assertIn("existing valid read authority", result.stderr)
        self.assertIn("independently inspect", result.stderr)
        self.assertIn("do not retry", result.stderr)
        self.assertNotIn("rejected", result.stderr)
        self.assertNotIn("synthetic-body-value", result.stderr)
        self.assertNotIn("synthetic-provider-value", result.stderr)
        self.assertNotIn("Authorization", result.stderr)
        self.assertNotIn("\x1b", result.stderr)

    def test_nonzero_post_preserves_original_cause_without_recovery(self) -> None:
        body = "@coderabbitai review"
        rejection = STATE.CommandRejectedError(37)
        with (
            mock.patch.object(COMMENT, "_active_login", return_value=self.login),
            mock.patch.object(COMMENT, "_stored_pr", return_value=self.stored()),
            mock.patch.object(
                COMMENT, "_run_mutation", side_effect=rejection
            ) as mutate,
            mock.patch.object(COMMENT, "_run_read") as reread,
            self.assertRaises(COMMENT.PublicationError) as caught,
        ):
            COMMENT.post_comment(
                expected=self.expected,
                expected_authenticated_login=self.login,
                body=body,
                body_sha256=hashlib.sha256(body.encode()).hexdigest(),
            )

        self.assertIs(caught.exception.__cause__, rejection)
        self.assertIs(caught.exception.mutation_error, rejection)
        self.assertEqual(mutate.call_count, 1)
        reread.assert_not_called()

    def test_actor_logins_are_display_safe_without_narrowing_supported_forms(
        self,
    ) -> None:
        supported = (
            "merge-operator",
            "mona-cat_octo",
            "octo_admin",
            "github-actions[bot]",
        )
        unsafe = (
            "Authorization: Bearer synthetic-secret",
            "two words",
            "line\nbreak",
            "ansi\x1b[31m",
            {"login": "nested"},
            ["nested"],
            "github-actions[bot][bot]",
        )
        for login in supported:
            with self.subTest(login=login):
                self.assertEqual(COMMENT._display_safe_login(login), login)
        for login in unsafe:
            with self.subTest(login=login):
                with self.assertRaisesRegex(
                    COMMENT.PublicationError, "display-safe GitHub.com actor login"
                ) as caught:
                    COMMENT._display_safe_login(login)
                self.assertNotIn("Authorization", str(caught.exception))
                self.assertNotIn("synthetic-secret", str(caught.exception))
                self.assertNotIn("\x1b", str(caught.exception))

    def test_actor_authority_rejects_deceptive_string_subclasses(self) -> None:
        class DeceptiveString(str):
            def __eq__(self, other: object) -> bool:
                return True

            __hash__ = str.__hash__

        body = "@coderabbitai review"
        deceptive = DeceptiveString("other-user")
        receipt = {
            "id": 91,
            "html_url": f"{self.url}#issuecomment-91",
            "body": body,
            "user": {"login": deceptive},
            "created_at": "2026-07-21T12:34:56Z",
        }

        for name, action in (
            ("authority", lambda: COMMENT._display_safe_login(deceptive)),
            (
                "receipt-author",
                lambda: COMMENT._comment_receipt(
                    receipt, self.expected, body, self.login
                ),
            ),
        ):
            with self.subTest(name=name), self.assertRaisesRegex(
                COMMENT.PublicationError, "display-safe GitHub.com actor login"
            ):
                action()

        with (
            mock.patch.object(COMMENT, "_active_login", return_value=deceptive),
            mock.patch.object(COMMENT, "_stored_pr") as stored,
            mock.patch.object(COMMENT, "_run_mutation") as mutate,
            self.assertRaisesRegex(
                COMMENT.PublicationError, "display-safe GitHub.com actor login"
            ),
        ):
            COMMENT.post_comment(
                expected=self.expected,
                expected_authenticated_login=self.login,
                body=body,
                body_sha256=hashlib.sha256(body.encode()).hexdigest(),
            )
        stored.assert_not_called()
        mutate.assert_not_called()

    def test_cli_accepts_supported_managed_and_bot_actor_logins(self) -> None:
        body = b"@coderabbitai review"
        supported = ("mona-cat_octo", "octo_admin", "github-actions[bot]")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "body.md"
            path.write_bytes(body)
            for login in supported:
                with self.subTest(login=login):
                    created = {
                        "id": 91,
                        "html_url": f"{self.url}#issuecomment-91",
                        "body": body.decode(),
                        "user": {"login": login},
                        "created_at": "2026-07-21T12:34:56Z",
                    }
                    arguments = [
                        "post_coderabbit_comment.py",
                        "--repository",
                        self.repository,
                        "--pr",
                        str(self.pr_number),
                        "--base",
                        self.base,
                        "--base-oid",
                        self.base_oid,
                        "--head",
                        self.head,
                        "--head-oid",
                        self.head_oid,
                        "--head-owner",
                        self.head_owner,
                        "--head-repository",
                        self.head_repository,
                        "--body-file",
                        str(path),
                        "--body-sha256",
                        hashlib.sha256(body).hexdigest(),
                        "--expected-authenticated-login",
                        login,
                    ]
                    completed = subprocess.CompletedProcess(
                        [], 0, json.dumps(created), ""
                    )
                    with (
                        mock.patch.object(sys, "argv", arguments),
                        mock.patch.object(
                            COMMENT, "_active_login", return_value=login
                        ),
                        mock.patch.object(
                            COMMENT, "_stored_pr", return_value=self.stored()
                        ),
                        mock.patch.object(
                            COMMENT, "_run_mutation", return_value=completed
                        ) as mutate,
                        mock.patch.object(
                            COMMENT, "_run_read", return_value=completed
                        ),
                        mock.patch("builtins.print") as output,
                    ):
                        self.assertEqual(COMMENT.main(), 0)

                    acknowledgement = json.loads(output.call_args.args[0])
                    self.assertEqual(acknowledgement["user"], {"login": login})
                    self.assertEqual(mutate.call_count, 1)

    def test_cli_rejects_unsafe_expected_login_before_read_or_mutation(self) -> None:
        unsafe_login = "Authorization: Bearer synthetic-secret\x1b[31m"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "body.md"
            body = b"@coderabbitai review"
            path.write_bytes(body)
            arguments = [
                "post_coderabbit_comment.py",
                "--repository",
                self.repository,
                "--pr",
                str(self.pr_number),
                "--base",
                self.base,
                "--base-oid",
                self.base_oid,
                "--head",
                self.head,
                "--head-oid",
                self.head_oid,
                "--head-owner",
                self.head_owner,
                "--head-repository",
                self.head_repository,
                "--body-file",
                str(path),
                "--body-sha256",
                hashlib.sha256(body).hexdigest(),
                "--expected-authenticated-login",
                unsafe_login,
            ]
            with (
                mock.patch.object(sys, "argv", arguments),
                mock.patch.object(COMMENT, "_run_read") as read,
                mock.patch.object(COMMENT, "_run_mutation") as mutate,
                mock.patch("builtins.print") as output,
            ):
                self.assertEqual(COMMENT.main(), 1)

        read.assert_not_called()
        mutate.assert_not_called()
        diagnostic = output.call_args.args[0]
        self.assertIn("display-safe GitHub.com actor login", diagnostic)
        self.assertNotIn("Authorization", diagnostic)
        self.assertNotIn("synthetic-secret", diagnostic)
        self.assertNotIn("\x1b", diagnostic)

    def test_cli_rejects_unsafe_nested_comment_author_without_acknowledgement(
        self,
    ) -> None:
        body = b"@coderabbitai review"
        created = {
            "id": 91,
            "html_url": f"{self.url}#issuecomment-91",
            "body": body.decode(),
            "user": {"login": {"Authorization": "synthetic-secret\x1b[31m"}},
            "created_at": "2026-07-21T12:34:56Z",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "body.md"
            path.write_bytes(body)
            arguments = [
                "post_coderabbit_comment.py",
                "--repository",
                self.repository,
                "--pr",
                str(self.pr_number),
                "--base",
                self.base,
                "--base-oid",
                self.base_oid,
                "--head",
                self.head,
                "--head-oid",
                self.head_oid,
                "--head-owner",
                self.head_owner,
                "--head-repository",
                self.head_repository,
                "--body-file",
                str(path),
                "--body-sha256",
                hashlib.sha256(body).hexdigest(),
                "--expected-authenticated-login",
                self.login,
            ]
            with (
                mock.patch.object(sys, "argv", arguments),
                mock.patch.object(COMMENT, "_active_login", return_value=self.login),
                mock.patch.object(COMMENT, "_stored_pr", return_value=self.stored()),
                mock.patch.object(
                    COMMENT,
                    "_run_mutation",
                    return_value=subprocess.CompletedProcess(
                        [], 0, json.dumps(created), ""
                    ),
                ) as mutate,
                mock.patch.object(COMMENT, "_run_read") as reread,
                mock.patch("builtins.print") as output,
            ):
                self.assertEqual(COMMENT.main(), 1)

        self.assertEqual(mutate.call_count, 1)
        reread.assert_not_called()
        diagnostic = output.call_args.args[0]
        self.assertIn("POST exited zero", diagnostic)
        self.assertIn("creation response validation failed", diagnostic)
        self.assertNotIn("Authorization", diagnostic)
        self.assertNotIn("synthetic-secret", diagnostic)
        self.assertNotIn("\x1b", diagnostic)

    def test_rejects_wrong_or_missing_author_and_timestamp(self) -> None:
        body = "@coderabbitai review"
        valid = {
            "id": 91,
            "html_url": f"{self.url}#issuecomment-91",
            "body": body,
            "user": {"login": self.login},
            "created_at": "2026-07-21T12:34:56Z",
        }
        cases = (
            ("wrong-author", {**valid, "user": {"login": "other"}}),
            (
                "missing-author",
                {key: value for key, value in valid.items() if key != "user"},
            ),
            (
                "missing-time",
                {key: value for key, value in valid.items() if key != "created_at"},
            ),
            ("malformed-time", {**valid, "created_at": "not-a-time"}),
        )
        for name, value in cases:
            with self.subTest(name=name):
                with self.assertRaises(COMMENT.PublicationError):
                    COMMENT._comment_receipt(value, self.expected, body, self.login)

    def test_active_login_mismatch_stops_before_pr_read_or_mutation(self) -> None:
        body = "@coderabbitai review"
        with (
            mock.patch.object(COMMENT, "_active_login", return_value="other"),
            mock.patch.object(COMMENT, "_stored_pr") as stored,
            mock.patch.object(COMMENT, "_run_mutation") as mutate,
        ):
            with self.assertRaisesRegex(
                COMMENT.PublicationError, "active authenticated"
            ):
                COMMENT.post_comment(
                    expected=self.expected,
                    expected_authenticated_login=self.login,
                    body=body,
                    body_sha256=hashlib.sha256(body.encode()).hexdigest(),
                )
        stored.assert_not_called()
        mutate.assert_not_called()

    def test_concurrent_head_drift_after_comment_is_ambiguous_without_retry(
        self,
    ) -> None:
        body = "@coderabbitai review"
        receipt = {
            "id": 91,
            "html_url": f"{self.url}#issuecomment-91",
            "body": body,
            "user": {"login": self.login},
            "created_at": "2026-07-21T12:34:56Z",
        }
        drifted = {**self.stored(), "headRefOid": "c" * 40}
        with (
            mock.patch.object(COMMENT, "_active_login", return_value=self.login),
            mock.patch.object(
                COMMENT, "_stored_pr", side_effect=[self.stored(), drifted]
            ),
            mock.patch.object(
                COMMENT,
                "_run_mutation",
                return_value=subprocess.CompletedProcess(
                    [], 0, json.dumps(receipt), ""
                ),
            ) as mutate,
            mock.patch.object(
                COMMENT,
                "_run_read",
                return_value=subprocess.CompletedProcess(
                    [], 0, json.dumps(receipt), ""
                ),
            ),
        ):
            with self.assertRaisesRegex(
                COMMENT.PublicationError, "PR identity verification failed"
            ):
                COMMENT.post_comment(
                    expected=self.expected,
                    expected_authenticated_login=self.login,
                    body=body,
                    body_sha256=hashlib.sha256(body.encode()).hexdigest(),
                )
        self.assertEqual(mutate.call_count, 1)

    def test_every_zero_exit_verification_failure_retains_comment_context(
        self,
    ) -> None:
        body = "@coderabbitai review"
        created = {
            "id": 91,
            "html_url": f"{self.url}#issuecomment-91",
            "body": body,
            "user": {"login": self.login},
            "created_at": "2026-07-21T12:34:56Z",
        }
        reread = subprocess.CompletedProcess([], 0, json.dumps(created), "")
        cases = (
            (
                "creation-response",
                {},
                {"_run_mutation": subprocess.CompletedProcess([], 0, "not-json", "")},
                "creation response validation failed",
            ),
            (
                "comment-reread-command",
                {},
                {"_run_read": STATE.CommandReadError(return_code=55)},
                "comment reread was rejected (return code 55)",
            ),
            (
                "comment-reread-response",
                {},
                {"_run_read": subprocess.CompletedProcess([], 0, "not-json", "")},
                "comment reread response validation failed",
            ),
            (
                "comment-identity",
                {},
                {
                    "_run_read": subprocess.CompletedProcess(
                        [],
                        0,
                        json.dumps(
                            {
                                **created,
                                "id": 92,
                                "html_url": f"{self.url}#issuecomment-92",
                            }
                        ),
                        "",
                    )
                },
                "comment identity verification failed",
            ),
            (
                "pr-reread-command",
                {"_stored_pr": [self.stored(), STATE.CommandReadError(return_code=56)]},
                {},
                "PR identity reread was rejected (return code 56)",
            ),
            (
                "pr-identity",
                {
                    "_stored_pr": [
                        self.stored(),
                        {**self.stored(), "headRefOid": "c" * 40},
                    ]
                },
                {},
                "PR identity verification failed",
            ),
        )
        for name, stored_overrides, command_overrides, classification in cases:
            with self.subTest(name=name):
                mutation = command_overrides.get(
                    "_run_mutation",
                    subprocess.CompletedProcess([], 0, json.dumps(created), ""),
                )
                comment_read = command_overrides.get("_run_read", reread)
                stored_values = stored_overrides.get(
                    "_stored_pr", [self.stored(), self.stored()]
                )
                with (
                    mock.patch.object(
                        COMMENT, "_active_login", return_value=self.login
                    ),
                    mock.patch.object(
                        COMMENT, "_stored_pr", side_effect=stored_values
                    ),
                    mock.patch.object(
                        COMMENT,
                        "_run_mutation",
                        side_effect=(mutation if isinstance(mutation, BaseException) else None),
                        return_value=(
                            None if isinstance(mutation, BaseException) else mutation
                        ),
                    ) as post,
                    mock.patch.object(
                        COMMENT,
                        "_run_read",
                        side_effect=(
                            comment_read
                            if isinstance(comment_read, BaseException)
                            else None
                        ),
                        return_value=(
                            None
                            if isinstance(comment_read, BaseException)
                            else comment_read
                        ),
                    ),
                ):
                    with self.assertRaises(COMMENT.PublicationError) as caught:
                        COMMENT.post_comment(
                            expected=self.expected,
                            expected_authenticated_login=self.login,
                            body=body,
                            body_sha256=hashlib.sha256(body.encode()).hexdigest(),
                        )
                diagnostic = str(caught.exception)
                self.assertIn("comment stage", diagnostic)
                self.assertIn("POST exited zero", diagnostic)
                self.assertIn(classification, diagnostic)
                self.assertIn("do not retry", diagnostic)
                self.assertIsInstance(
                    caught.exception.__cause__, COMMENT.PublicationError
                )
                if isinstance(comment_read, BaseException):
                    self.assertIs(caught.exception.__cause__, comment_read)
                elif len(stored_values) > 1 and isinstance(
                    stored_values[1], BaseException
                ):
                    self.assertIs(caught.exception.__cause__, stored_values[1])
                self.assertEqual(post.call_count, 1)

    def test_cli_emits_no_success_acknowledgement_after_zero_exit_failure(self) -> None:
        body = b"Authorization: sensitive-looking-comment"
        created = {
            "id": 91,
            "html_url": f"{self.url}#issuecomment-91",
            "body": body.decode(),
            "user": {"login": self.login},
            "created_at": "2026-07-21T12:34:56Z",
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "body.md"
            path.write_bytes(body)
            arguments = [
                "post_coderabbit_comment.py",
                "--repository",
                self.repository,
                "--pr",
                str(self.pr_number),
                "--base",
                self.base,
                "--base-oid",
                self.base_oid,
                "--head",
                self.head,
                "--head-oid",
                self.head_oid,
                "--head-owner",
                self.head_owner,
                "--head-repository",
                self.head_repository,
                "--body-file",
                str(path),
                "--body-sha256",
                hashlib.sha256(body).hexdigest(),
                "--expected-authenticated-login",
                self.login,
            ]
            with (
                mock.patch.object(sys, "argv", arguments),
                mock.patch.object(COMMENT, "_active_login", return_value=self.login),
                mock.patch.object(
                    COMMENT,
                    "_stored_pr",
                    side_effect=[self.stored(), STATE.CommandReadError(return_code=55)],
                ),
                mock.patch.object(
                    COMMENT,
                    "_run_mutation",
                    return_value=subprocess.CompletedProcess(
                        [], 0, json.dumps(created), ""
                    ),
                ) as post,
                mock.patch.object(
                    COMMENT,
                    "_run_read",
                    return_value=subprocess.CompletedProcess(
                        [], 0, json.dumps(created), ""
                    ),
                ),
                mock.patch("builtins.print") as output,
            ):
                self.assertEqual(COMMENT.main(), 1)

        self.assertEqual(post.call_count, 1)
        self.assertTrue(output.call_args.kwargs.get("file") is sys.stderr)
        diagnostic = output.call_args.args[0]
        self.assertIn("POST exited zero", diagnostic)
        self.assertIn("do not retry", diagnostic)
        self.assertNotIn(body.decode(), diagnostic)


if __name__ == "__main__":
    unittest.main()
