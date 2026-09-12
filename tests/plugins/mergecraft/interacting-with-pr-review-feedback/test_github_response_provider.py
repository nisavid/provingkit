import base64
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
REPOSITORY = Path(__file__).resolve().parents[4]
SCRIPTS = (
    REPOSITORY / "plugins/mergecraft/skills/interacting-with-pr-review-feedback/scripts"
)
sys.path.insert(0, str(SCRIPTS))

import github_response_provider

TYPED_FIXTURE = (
    REPOSITORY
    / "tests/plugins/mergecraft/addressing-pr-review-feedback/fixtures/typed_feedback_epoch.json"
)


class GitHubResponseProviderTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.state_path = Path(self.temporary.name) / "state.json"
        self.state_path.write_text(
            json.dumps({"actor": "ivan", "next_id": 900}), encoding="utf-8"
        )
        fake = TEST_DIR / "fixtures" / "fake_gh.py"
        self.transport = github_response_provider.GhJsonTransport(
            program_argv=[sys.executable, str(fake), str(self.state_path)]
        )
        self.inline = github_response_provider.InlineReplyAdapter(self.transport)
        self.top_level = github_response_provider.PullRequestConversationAdapter(
            self.transport
        )

    def tearDown(self):
        self.temporary.cleanup()

    def state(self):
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def test_typed_epoch_uses_explicit_post_for_graphql_read_query(self):
        state = self.state()
        state["graphql"] = json.loads(TYPED_FIXTURE.read_text(encoding="utf-8"))
        self.state_path.write_text(json.dumps(state), encoding="utf-8")

        epoch = github_response_provider.TypedEpochAdapter(self.transport).acquire(
            "base-owner/base-repo", 7
        )

        self.assertEqual(epoch["pull_request"]["node_id"], "PR_node_7")
        self.assertEqual(
            epoch["repository"]["provider_identity"],
            {"database_id": 77, "node_id": "REPO_node_77"},
        )
        self.assertTrue(epoch["pagination_evidence"]["complete"])
        self.assertLess(
            epoch["acquisition_start_observation"]["monotonic_ns"],
            epoch["acquisition_end_observation"]["monotonic_ns"],
        )
        calls = self.state()["calls"]
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["operation"], "graphql_read_query")
        self.assertEqual(
            calls[0]["argv"],
            [
                "api",
                "--hostname",
                "github.com",
                "--method",
                "POST",
                "graphql",
                "--input",
                "-",
            ],
        )
        self.assertIn("query", calls[0]["request"])
        self.assertIsInstance(calls[0]["request"]["variables"], dict)
        self.assertEqual(epoch["sources"][0]["state"]["value"], "SUBMITTED")
        self.assertEqual(epoch["sources"][-1]["created_at"], "2026-09-01T08:58:00Z")

    def test_typed_epoch_retains_each_actual_top_level_page_observation(self):
        first = json.loads(TYPED_FIXTURE.read_text(encoding="utf-8"))
        second = copy.deepcopy(first)
        first_pr = first["data"]["repository"]["pullRequest"]
        second_pr = second["data"]["repository"]["pullRequest"]
        connections = ("reviewThreads", "comments", "reviews", "reviewRequests")
        for index, name in enumerate(connections):
            first_pr[name]["pageInfo"] = {
                "hasNextPage": True,
                "endCursor": f"cursor-{index}",
            }
            second_pr[name]["pageInfo"] = {
                "hasNextPage": False,
                "endCursor": f"terminal-{index}",
            }
        first_pr["statusCheckRollup"]["contexts"]["pageInfo"] = {
            "hasNextPage": True,
            "endCursor": "cursor-checks",
        }
        second_pr["statusCheckRollup"]["contexts"]["pageInfo"] = {
            "hasNextPage": False,
            "endCursor": "terminal-checks",
        }
        state = self.state()
        state["graphql"] = second
        state["queued"] = {
            "POST graphql": [
                {"returncode": 0, "json": first},
                {"returncode": 0, "json": second},
            ]
        }
        self.state_path.write_text(json.dumps(state), encoding="utf-8")

        epoch = github_response_provider.TypedEpochAdapter(self.transport).acquire(
            "base-owner/base-repo", 7
        )

        for collection in epoch["pagination_evidence"]["collections"].values():
            self.assertEqual(
                [page["page_index"] for page in collection["pages"]], [0, 1]
            )
            self.assertEqual(
                [page["request_cursor"] for page in collection["pages"]],
                [None, collection["pages"][0]["end_cursor"]],
            )
            self.assertEqual(
                collection["node_count"],
                sum(page["node_count"] for page in collection["pages"]),
            )
            self.assertTrue(collection["pages"][0]["has_next_page"])
            self.assertFalse(collection["pages"][1]["has_next_page"])
        self.assertEqual(
            sum(
                call["operation"] == "graphql_read_query"
                for call in self.state()["calls"]
            ),
            2,
        )

    def test_external_fixture_rejects_impossible_or_incomplete_source_selections(self):
        state = self.state()
        state["graphql"] = json.loads(TYPED_FIXTURE.read_text(encoding="utf-8"))
        self.state_path.write_text(json.dumps(state), encoding="utf-8")
        acquisition = github_response_provider.TypedEpochAdapter(self.transport)
        query, variables = acquisition.acquisition.build_pr_query(
            "base-owner/base-repo", 7, cursors={}
        )
        thread_query, thread_variables = (
            acquisition.acquisition.build_thread_comments_query(
                "THREAD_node_21", "cursor-1"
            )
        )

        self.transport.request(
            "POST",
            "graphql",
            {"query": thread_query, "variables": thread_variables},
        )

        invalid_queries = (
            query.replace(
                "author { ...ActorIdentity }", "author { __typename id login }", 1
            ),
            query.replace("\n  state\n  replyTo", "\n  replyTo", 1),
        )
        for invalid_query in invalid_queries:
            with (
                self.subTest(query=invalid_query),
                self.assertRaisesRegex(
                    github_response_provider.GhTransportError,
                    "acquisition query",
                ),
            ):
                self.transport.request(
                    "POST",
                    "graphql",
                    {"query": invalid_query, "variables": variables},
                )

        self.assertNotIn("objects", self.state())

    def test_external_fixture_rejects_get_with_graphql_query_body(self):
        with self.assertRaisesRegex(
            github_response_provider.GhTransportError,
            "GraphQL query bodies require explicit POST transport",
        ):
            self.transport.request(
                "GET",
                "graphql",
                {"query": "query { viewer { login } }", "variables": {}},
            )

        call = self.state()["calls"][0]
        self.assertEqual(call["operation"], "graphql_read_query")
        self.assertNotIn("--method", call["argv"])
        self.assertNotIn("objects", self.state())

    def test_graphql_post_failure_remains_a_side_effect_free_read(self):
        state = self.state()
        state["queued"] = {"POST graphql": [{"returncode": 1, "stderr": "HTTP 500"}]}
        self.state_path.write_text(json.dumps(state), encoding="utf-8")

        with self.assertRaises(github_response_provider.GhTransportError) as raised:
            github_response_provider.TypedEpochAdapter(self.transport).acquire(
                "base-owner/base-repo", 7
            )

        self.assertEqual(raised.exception.status, "confirmed_failure")
        self.assertEqual(raised.exception.side_effect, "none")
        self.assertFalse(raised.exception.retryable)
        self.assertEqual(
            raised.exception.evidence["transport_operation"],
            "graphql_read_query",
        )
        self.assertNotIn("objects", self.state())

    def test_inline_reply_uses_thread_root_database_id_and_stable_reread(self):
        body = b"First line\r\nSecond line\r\n"
        result = self.inline.create_and_reread(
            repo="base-owner/base-repo",
            pr_number=7,
            root_comment_database_id=301,
            exact_body=body,
            expected_actor_login="ivan",
        )

        self.assertEqual(result["status"], "confirmed_success")
        self.assertEqual(base64.b64decode(result["request_body_utf8_base64"]), body)
        self.assertEqual(base64.b64decode(result["reread_body_utf8_base64"]), body)
        calls = self.state()["calls"]
        self.assertEqual(
            [call["operation"] for call in calls],
            ["response_write", "response_reread"],
        )
        self.assertEqual(
            calls[0]["argv"],
            [
                "api",
                "--hostname",
                "github.com",
                "--method",
                "POST",
                "/repos/base-owner/base-repo/pulls/7/comments/301/replies",
                "--input",
                "-",
            ],
        )
        self.assertEqual(calls[0]["request"], {"body": body.decode("utf-8")})
        self.assertEqual(
            calls[1]["argv"][-1],
            "/repos/base-owner/base-repo/pulls/comments/900",
        )

    def test_post_write_malformed_actor_evidence_is_unknown_with_created_identity(self):
        state = self.state()
        state["reread_overrides"] = {"900": {"user": ["malformed"]}}
        self.state_path.write_text(json.dumps(state), encoding="utf-8")

        with self.assertRaises(github_response_provider.GhTransportError) as raised:
            self.inline.create_and_reread(
                repo="base-owner/base-repo",
                pr_number=7,
                root_comment_database_id=301,
                exact_body=b"Exact body",
                expected_actor_login="ivan",
            )

        self.assertEqual(raised.exception.status, "unknown")
        self.assertEqual(raised.exception.side_effect, "unknown")
        self.assertEqual(raised.exception.evidence["create_response"]["id"], 900)
        self.assertEqual(
            [call["operation"] for call in self.state()["calls"]],
            ["response_write", "response_reread"],
        )

    def test_create_and_reread_require_full_typed_identity_equality(self):
        for override in ({"id": 901}, {"node_id": "RESPONSE_node_other"}):
            with self.subTest(override=override):
                state = self.state()
                state["reread_overrides"] = {"900": override}
                self.state_path.write_text(json.dumps(state), encoding="utf-8")
                with self.assertRaises(
                    github_response_provider.GhTransportError
                ) as raised:
                    self.inline.create_and_reread(
                        repo="base-owner/base-repo",
                        pr_number=7,
                        root_comment_database_id=301,
                        exact_body=b"Exact body",
                        expected_actor_login="ivan",
                    )
                self.assertEqual(raised.exception.status, "unknown")
                self.assertEqual(raised.exception.side_effect, "unknown")
                evidence = raised.exception.evidence
                self.assertIn("created_response_identity", evidence)
                self.assertIn("requested_reread_identity", evidence)
                self.assertIn("reread_response_identity", evidence)
                state = self.state()
                state["next_id"] = 900
                state.pop("objects", None)
                state.pop("reread_overrides", None)
                state.pop("calls", None)
                self.state_path.write_text(json.dumps(state), encoding="utf-8")

    def test_reread_known_requires_complete_operation_specific_identity(self):
        state = self.state()
        state["objects"] = {
            "900": {
                "id": 900,
                "node_id": "RESPONSE_node_900",
                "body": "Exact body",
                "html_url": "https://github.com/example/repo/pull/7#response-900",
                "user": {"login": "ivan"},
            }
        }
        self.state_path.write_text(json.dumps(state), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "operation-specific"):
            self.inline.reread_known(
                repo="base-owner/base-repo",
                response_identity={
                    "object_kind": "IssueComment",
                    "database_id": 900,
                    "node_id": "RESPONSE_node_900",
                },
                exact_body=b"Exact body",
                expected_actor_login="ivan",
            )

        receipt = self.inline.reread_known(
            repo="base-owner/base-repo",
            response_identity={
                "object_kind": "PullRequestReviewComment",
                "database_id": 900,
                "node_id": "RESPONSE_node_900",
            },
            exact_body=b"Exact body",
            expected_actor_login="ivan",
        )
        self.assertEqual(
            receipt["created_response_identity"],
            receipt["requested_reread_identity"],
        )
        self.assertEqual(
            receipt["requested_reread_identity"],
            receipt["reread_response_identity"],
        )

    def test_top_level_route_requires_typed_pr_verification_and_has_no_issue_api(self):
        body = (
            b"Handled the concern from "
            b"https://github.com/base-owner/base-repo/pull/7#issuecomment-401"
        )
        with self.assertRaisesRegex(ValueError, "typed pull request verification"):
            self.top_level.create_and_reread(
                repo="base-owner/base-repo",
                pr_number=7,
                pr_node_id="",
                verification_epoch_id="epoch",
                source_permalink="https://github.com/base-owner/base-repo/pull/7#issuecomment-401",
                exact_body=body,
                expected_actor_login="ivan",
            )

        result = self.top_level.create_and_reread(
            repo="base-owner/base-repo",
            pr_number=7,
            pr_node_id="PR_node_7",
            verification_epoch_id="epoch",
            source_permalink="https://github.com/base-owner/base-repo/pull/7#issuecomment-401",
            exact_body=body,
            expected_actor_login="ivan",
        )

        self.assertEqual(result["status"], "confirmed_success")
        calls = self.state()["calls"]
        self.assertEqual(
            [call["operation"] for call in calls],
            ["response_write", "response_reread"],
        )
        self.assertEqual(
            calls[0]["argv"][-3:],
            [
                "/repos/base-owner/base-repo/issues/7/comments",
                "--input",
                "-",
            ],
        )
        self.assertEqual(
            calls[1]["argv"][-1],
            "/repos/base-owner/base-repo/issues/comments/900",
        )
        self.assertFalse(hasattr(self.top_level, "create_issue_comment"))


if __name__ == "__main__":
    unittest.main()
