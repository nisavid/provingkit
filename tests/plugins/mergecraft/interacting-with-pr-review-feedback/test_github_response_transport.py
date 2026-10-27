import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

REPOSITORY = Path(__file__).resolve().parents[4]
SCRIPTS = (
    REPOSITORY / "plugins/mergecraft/skills/interacting-with-pr-review-feedback/scripts"
)
sys.path.insert(0, str(SCRIPTS))

import github_response_provider

AUTH_COMMAND = ["gh", "auth", "token", "--hostname", "github.com"]


class GitHubResponseTransportTests(unittest.TestCase):
    def verify_actor(self, transport):
        transport.verify_actor(
            expected_actor_login="ivan", expected_actor_node_id="USER_ivan"
        )

    def test_actor_checks_and_write_keep_one_resolved_credential(self):
        calls = []

        def run(command, **kwargs):
            calls.append((command, {**kwargs, "env": dict(kwargs["env"])}))
            if command[1:3] == ["auth", "token"]:
                os.environ["GH_TOKEN"] = "ambient-switched-token"
                return subprocess.CompletedProcess(command, 0, b"pinned-token\n", b"")
            if command[-1] == "/user":
                output = {"login": "ivan", "node_id": "USER_ivan"}
            else:
                output = {"id": 900}
            return subprocess.CompletedProcess(
                command, 0, json.dumps(output).encode(), b""
            )

        with mock.patch.dict(
            os.environ,
            {"GH_HOST": "other.example", "GH_REPO": "other/repository"},
            clear=True,
        ):
            transport = github_response_provider.GhJsonTransport()
            with mock.patch.object(
                github_response_provider.subprocess, "run", side_effect=run
            ):
                self.verify_actor(transport)
                self.verify_actor(transport)
                transport.request(
                    "POST", "/repos/base-owner/base-repo/issues/7/comments", {"body": "Exact"}
                )
            self.assertEqual(os.environ["GH_TOKEN"], "ambient-switched-token")

        self.assertEqual(
            [command for command, _ in calls],
            [
                AUTH_COMMAND,
                ["gh", "api", "--hostname", "github.com", "/user"],
                ["gh", "api", "--hostname", "github.com", "/user"],
                [
                    "gh", "api", "--hostname", "github.com", "--method", "POST",
                    "/repos/base-owner/base-repo/issues/7/comments", "--input", "-",
                ],
            ],
        )
        for command, kwargs in calls[1:]:
            self.assertEqual(kwargs["env"]["GH_TOKEN"], "pinned-token")
            self.assertNotIn("GITHUB_TOKEN", kwargs["env"])
            self.assertNotIn("GH_HOST", kwargs["env"])
            self.assertNotIn("GH_REPO", kwargs["env"])
            self.assertNotIn("pinned-token", command)
        self.assertEqual(json.loads(calls[-1][1]["input"]), {"body": "Exact"})

    def test_environment_credentials_are_snapshotted_with_gh_token_precedence(self):
        for initial, expected in (
            ({"GH_TOKEN": "gh-token"}, "gh-token"),
            ({"GITHUB_TOKEN": "github-token"}, "github-token"),
            ({"GH_TOKEN": "gh-token", "GITHUB_TOKEN": "github-token"}, "gh-token"),
            ({"GH_TOKEN": "", "GITHUB_TOKEN": "github-token"}, "github-token"),
        ):
            with self.subTest(initial=initial):
                calls = []

                def run(command, **kwargs):
                    calls.append((command, dict(kwargs["env"])))
                    output = {"login": "ivan", "node_id": "USER_ivan"}
                    return subprocess.CompletedProcess(
                        command, 0, json.dumps(output).encode(), b""
                    )

                with mock.patch.dict(os.environ, initial, clear=True):
                    transport = github_response_provider.GhJsonTransport()
                    os.environ.update(
                        GH_TOKEN="new-gh-token", GITHUB_TOKEN="new-github-token"
                    )
                    with mock.patch.object(
                        github_response_provider.subprocess, "run", side_effect=run
                    ):
                        self.verify_actor(transport)
                        transport.request(
                            "POST", "/repos/base-owner/base-repo/issues/7/comments",
                            {"body": "Exact"},
                        )

                self.assertEqual(len(calls), 2)
                for command, environment in calls:
                    self.assertEqual(command[1], "api")
                    self.assertEqual(environment["GH_TOKEN"], expected)
                    self.assertNotIn("GITHUB_TOKEN", environment)

    def test_read_only_graphql_does_not_resolve_credentials_or_check_actor(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            transport = github_response_provider.GhJsonTransport()
            with mock.patch.object(
                github_response_provider.subprocess,
                "run",
                return_value=subprocess.CompletedProcess("gh", 0, b'{"data":{}}', b""),
            ) as run:
                result = transport.request(
                    "POST", "graphql",
                    {"query": "query { viewer { login } }", "variables": {}},
                )

        self.assertEqual(result, {"data": {}})
        self.assertEqual(run.call_count, 1)
        self.assertEqual(
            run.call_args.args[0],
            [
                "gh", "api", "--hostname", "github.com", "--method", "POST",
                "graphql", "--input", "-",
            ],
        )

    def test_failed_or_malformed_credential_resolution_has_no_api_effect(self):
        secret = "credential-output-must-remain-private"
        responses = (
            subprocess.CompletedProcess("gh", 1, secret.encode(), secret.encode()),
            subprocess.CompletedProcess("gh", 0, b"", b""),
            subprocess.CompletedProcess("gh", 0, b" \n\t", b""),
            subprocess.CompletedProcess("gh", 0, f"{secret} second-token".encode(), b""),
            subprocess.CompletedProcess("gh", 0, b"\xff", b""),
            OSError(secret),
            subprocess.TimeoutExpired(
                "gh", 30, output=secret.encode(), stderr=secret.encode()
            ),
        )
        for response in responses:
            with self.subTest(response=type(response).__name__):
                with mock.patch.dict(os.environ, {}, clear=True):
                    transport = github_response_provider.GhJsonTransport()
                    kwargs = (
                        {"side_effect": response}
                        if isinstance(response, Exception)
                        else {"return_value": response}
                    )
                    with mock.patch.object(
                        github_response_provider.subprocess, "run", **kwargs
                    ) as run:
                        with self.assertRaises(
                            github_response_provider.GhTransportError
                        ) as raised:
                            self.verify_actor(transport)

                self.assertEqual(run.call_count, 1)
                self.assertEqual(run.call_args.args[0], AUTH_COMMAND)
                self.assertEqual(raised.exception.status, "confirmed_failure")
                self.assertEqual(raised.exception.side_effect, "none")
                self.assertFalse(raised.exception.retryable)
                self.assertNotIn(secret, str(raised.exception))
                self.assertNotIn(secret, json.dumps(raised.exception.evidence))

    def test_malformed_environment_credential_has_no_subprocess_effect(self):
        with mock.patch.dict(
            os.environ, {"GH_TOKEN": "malformed credential"}, clear=True
        ):
            transport = github_response_provider.GhJsonTransport()
            with mock.patch.object(github_response_provider.subprocess, "run") as run:
                with self.assertRaises(
                    github_response_provider.GhTransportError
                ) as raised:
                    self.verify_actor(transport)

        run.assert_not_called()
        self.assertEqual(raised.exception.status, "confirmed_failure")
        self.assertEqual(raised.exception.side_effect, "none")
        self.assertNotIn("malformed credential", str(raised.exception))
        self.assertNotIn("malformed credential", json.dumps(raised.exception.evidence))


if __name__ == "__main__":
    unittest.main()
