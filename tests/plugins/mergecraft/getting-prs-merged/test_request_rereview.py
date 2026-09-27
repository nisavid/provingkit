from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock


REPOSITORY = Path(__file__).resolve().parents[4]
SKILLS_ROOT = REPOSITORY / "plugins/mergecraft/skills"
SKILL_ROOT = SKILLS_ROOT / "getting-prs-merged"
PUBLISHER_SCRIPTS = SKILLS_ROOT / "publishing-reviewable-prs" / "scripts"
sys.path.insert(0, str(PUBLISHER_SCRIPTS))


def load_rerequest_module(name: str):
    path = SKILL_ROOT / "scripts" / "request_rereview.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


REREQUEST = load_rerequest_module("request_rereview")


def completed(value: object) -> subprocess.CompletedProcess[str]:
    text = value if isinstance(value, str) else json.dumps(value)
    return subprocess.CompletedProcess([], 0, text, "")


class ReviewerRerequestActuatorTests(unittest.TestCase):
    repository = "acme/app"
    pr_number = 42
    head_oid = "b" * 40
    url = "https://github.com/acme/app/pull/42"
    login = "merge-operator"
    author = "pr-author"
    reviewer = "ana"
    review_id = "PRR_kwDOreview1"

    def stored(self, **changes: object) -> dict[str, object]:
        return {
            "number": self.pr_number,
            "url": self.url,
            "headRefOid": self.head_oid,
            "state": "OPEN",
            **changes,
        }

    def review(self, **changes: object) -> dict[str, object]:
        return {
            "id": self.review_id,
            "state": "COMMENTED",
            "submittedAt": "2026-09-20T10:00:00Z",
            "author": {"__typename": "User", "login": self.reviewer},
            **changes,
        }

    def pull_request(
        self,
        *,
        requested: tuple[str, ...] = ("ben",),
        reviews: list[object] | None = None,
        more_requests: bool = False,
        **changes: object,
    ) -> dict[str, object]:
        pull_request = {
            "url": self.url,
            "headRefOid": self.head_oid,
            "author": {"login": self.author},
            "reviewRequests": {
                "pageInfo": {"hasNextPage": more_requests},
                "nodes": [
                    {"requestedReviewer": {"__typename": "User", "login": login}}
                    for login in requested
                ],
            },
            "reviews": {"nodes": [self.review()] if reviews is None else reviews},
            **changes,
        }
        return {"data": {"repository": {"pullRequest": pull_request}}}

    def requested_reviewers(self, *logins: str) -> dict[str, object]:
        return {
            "users": [{"login": login, "type": "User"} for login in logins],
            "teams": [],
        }

    def response(self, *logins: str, **changes: object) -> dict[str, object]:
        return {
            "number": self.pr_number,
            "html_url": self.url,
            "head": {"sha": self.head_oid},
            "requested_reviewers": [
                {"login": login, "type": "User"}
                for login in (logins or ("ben", self.reviewer))
            ],
            **changes,
        }

    def rerequest(self, **changes: object) -> dict[str, object]:
        arguments = {
            "repository": self.repository,
            "pr_number": self.pr_number,
            "head_oid": self.head_oid,
            "reviewer": self.reviewer,
            "expected_review_id": self.review_id,
            "expected_authenticated_login": self.login,
            **changes,
        }
        return REREQUEST.request_rereview(**arguments)

    @contextlib.contextmanager
    def live(
        self,
        *,
        reads: list[object] | None = None,
        mutation: object = None,
        stored: list[object] | None = None,
        login: str | None = None,
    ):
        read_effects = [
            item if isinstance(item, BaseException) else completed(item)
            for item in (reads or [])
        ]
        if isinstance(mutation, BaseException):
            mutation_effect = {"side_effect": mutation}
        else:
            mutation_effect = {
                "return_value": completed(
                    self.response() if mutation is None else mutation
                )
            }
        with (
            mock.patch.object(
                REREQUEST, "_active_login", return_value=login or self.login
            ) as active,
            mock.patch.object(
                REREQUEST,
                "_stored_pr",
                side_effect=stored or [self.stored(), self.stored()],
            ) as stored_pr,
            mock.patch.object(
                REREQUEST, "_run_read", side_effect=read_effects
            ) as read,
            mock.patch.object(REREQUEST, "_run_mutation", **mutation_effect) as mutate,
        ):
            yield {
                "active": active,
                "stored": stored_pr,
                "read": read,
                "mutate": mutate,
            }

    def test_requests_once_and_returns_verified_reread_receipt(self) -> None:
        with self.live(
            reads=[
                self.pull_request(),
                self.requested_reviewers("ben", self.reviewer),
            ]
        ) as calls:
            result = self.rerequest()
        self.assertEqual(result["status"], "verified", result["reason"])
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["operation"], "reviewer-rerequest")
        self.assertTrue(result["mutation_attempted"])
        self.assertTrue(result["live"]["requested"])
        self.assertEqual(result["live"]["latest_review_id"], self.review_id)
        self.assertEqual(calls["mutate"].call_count, 1)
        self.assertEqual(calls["stored"].call_count, 2)
        self.assertEqual(calls["read"].call_count, 2)
        query = json.loads(calls["read"].call_args_list[0].kwargs["input_text"])
        self.assertEqual(
            query["variables"],
            {"owner": "acme", "name": "app", "number": 42, "reviewer": "ana"},
        )
        self.assertEqual(
            calls["read"].call_args_list[1].args[0],
            [
                "gh",
                "api",
                "--hostname",
                "github.com",
                "--method",
                "GET",
                "repos/acme/app/pulls/42/requested_reviewers",
            ],
        )

    def test_already_requested_reviewer_is_verified_without_mutation(self) -> None:
        with self.live(
            reads=[self.pull_request(requested=("ben", self.reviewer))]
        ) as calls:
            result = self.rerequest()
        self.assertEqual(result["status"], "verified", result["reason"])
        self.assertFalse(result["mutation_attempted"])
        self.assertTrue(result["live"]["requested"])
        self.assertIn("already requested", result["reason"])
        calls["mutate"].assert_not_called()

    def test_reviewer_without_submitted_review_blocks(self) -> None:
        cases = (
            ("no-review", []),
            ("pending", [self.review(state="PENDING", submittedAt=None)]),
            ("unsubmitted", [self.review(submittedAt=None)]),
        )
        for name, reviews in cases:
            with self.subTest(name=name):
                with self.live(reads=[self.pull_request(reviews=reviews)]) as calls:
                    result = self.rerequest()
                self.assertEqual(result["status"], "blocked")
                self.assertIn("submitted review", result["reason"])
                calls["mutate"].assert_not_called()

    def test_newer_review_than_expected_blocks(self) -> None:
        newer = self.review(id="PRR_kwDOreview2", state="APPROVED")
        with self.live(reads=[self.pull_request(reviews=[newer])]) as calls:
            result = self.rerequest()
        self.assertEqual(result["status"], "blocked")
        self.assertIn("expected review", result["reason"])
        self.assertEqual(result["live"]["latest_review_id"], "PRR_kwDOreview2")
        self.assertEqual(result["live"]["latest_review_state"], "APPROVED")
        calls["mutate"].assert_not_called()

    def test_author_bot_or_active_login_as_reviewer_blocks(self) -> None:
        bot_review = self.review(
            author={"__typename": "Bot", "login": "coderabbitai"}
        )
        cases = (
            ("author", {"reviewer": self.author}, self.pull_request(), None),
            (
                "active-login",
                {"reviewer": self.login},
                self.pull_request(),
                None,
            ),
            (
                "bot",
                {"reviewer": "coderabbitai"},
                self.pull_request(reviews=[bot_review]),
                None,
            ),
            (
                "bot-login-form",
                {"reviewer": "coderabbitai[bot]"},
                self.pull_request(),
                "before-reads",
            ),
            (
                "team",
                {"reviewer": "acme/reviewers"},
                self.pull_request(),
                "before-reads",
            ),
        )
        for name, changes, state, stage in cases:
            with self.subTest(name=name):
                with self.live(reads=[state]) as calls:
                    result = self.rerequest(**changes)
                self.assertEqual(result["status"], "blocked")
                calls["mutate"].assert_not_called()
                if stage == "before-reads":
                    calls["active"].assert_not_called()
                    calls["read"].assert_not_called()

    def test_active_login_mismatch_stops_before_pr_read(self) -> None:
        with self.live(reads=[self.pull_request()], login="other") as calls:
            result = self.rerequest()
        self.assertEqual(result["status"], "blocked")
        self.assertIn("active authenticated login", result["reason"])
        calls["stored"].assert_not_called()
        calls["read"].assert_not_called()
        calls["mutate"].assert_not_called()

    def test_head_drift_before_request_blocks(self) -> None:
        with self.subTest(name="stored-pr"):
            with self.live(
                reads=[self.pull_request()],
                stored=[self.stored(headRefOid="c" * 40)],
            ) as calls:
                result = self.rerequest()
            self.assertEqual(result["status"], "blocked")
            self.assertIn("head", result["reason"])
            calls["read"].assert_not_called()
            calls["mutate"].assert_not_called()
        with self.subTest(name="graphql-pull-request"):
            with self.live(
                reads=[self.pull_request(headRefOid="c" * 40)]
            ) as calls:
                result = self.rerequest()
            self.assertEqual(result["status"], "blocked")
            self.assertIn("head", result["reason"])
            calls["mutate"].assert_not_called()
        with self.subTest(name="graphql-other-pull-request"):
            with self.live(
                reads=[self.pull_request(url="https://github.com/acme/app/pull/43")]
            ) as calls:
                result = self.rerequest()
            self.assertEqual(result["status"], "blocked")
            calls["mutate"].assert_not_called()

    def test_uses_additive_rest_endpoint_with_single_reviewer(self) -> None:
        with self.live(
            reads=[
                self.pull_request(),
                self.requested_reviewers("ben", self.reviewer),
            ]
        ) as calls:
            result = self.rerequest()
        self.assertEqual(result["status"], "verified", result["reason"])
        self.assertEqual(calls["mutate"].call_count, 1)
        self.assertEqual(
            calls["mutate"].call_args.args[0],
            [
                "gh",
                "api",
                "--hostname",
                "github.com",
                "--method",
                "POST",
                "repos/acme/app/pulls/42/requested_reviewers",
                "--input",
                "-",
            ],
        )
        self.assertEqual(
            calls["mutate"].call_args.kwargs["input_text"], '{"reviewers":["ana"]}'
        )

    def test_paginated_review_requests_block(self) -> None:
        with self.live(reads=[self.pull_request(more_requests=True)]) as calls:
            result = self.rerequest()
        self.assertEqual(result["status"], "blocked")
        self.assertIn("page", result["reason"])
        calls["mutate"].assert_not_called()

    def test_mutation_timeout_is_unknown_and_never_retried(self) -> None:
        with self.live(
            reads=[self.pull_request()],
            mutation=REREQUEST.MutationAmbiguousError("timeout"),
        ) as calls:
            result = self.rerequest()
        self.assertEqual(result["status"], "unknown")
        self.assertTrue(result["mutation_attempted"])
        self.assertEqual(calls["mutate"].call_count, 1)

    def test_response_or_reread_without_reviewer_is_unknown(self) -> None:
        cases = (
            ("response-without-reviewer", self.response("ben"), ("ben", "ana")),
            ("response-other-pr", self.response(number=43), ("ben", "ana")),
            (
                "response-other-head",
                self.response(head={"sha": "c" * 40}),
                ("ben", "ana"),
            ),
            ("response-invalid-json", "not json", ("ben", "ana")),
            ("reread-without-reviewer", self.response(), ("ben",)),
        )
        for name, response, reread in cases:
            with self.subTest(name=name):
                with self.live(
                    reads=[self.pull_request(), self.requested_reviewers(*reread)],
                    mutation=response,
                ) as calls:
                    result = self.rerequest()
                self.assertEqual(result["status"], "unknown")
                self.assertEqual(calls["mutate"].call_count, 1)
        with self.subTest(name="head-drift-after-request"):
            with self.live(
                reads=[
                    self.pull_request(),
                    self.requested_reviewers("ben", self.reviewer),
                ],
                stored=[self.stored(), self.stored(headRefOid="c" * 40)],
            ) as calls:
                result = self.rerequest()
            self.assertEqual(result["status"], "unknown")
            self.assertEqual(calls["mutate"].call_count, 1)

    def test_refused_request_is_blocked_with_live_state_reported(self) -> None:
        refusal = REREQUEST.PublicationError(
            "gh mutation failed: Reviews may only be requested from collaborators."
        )
        with self.live(
            reads=[self.pull_request(), self.requested_reviewers("ben")],
            mutation=refusal,
        ) as calls:
            result = self.rerequest()
        self.assertEqual(result["status"], "blocked")
        self.assertIn("collaborators", result["refusal"])
        self.assertFalse(result["live"]["requested"])
        self.assertEqual(calls["mutate"].call_count, 1)
        with self.subTest(name="requested-despite-refusal"):
            with self.live(
                reads=[
                    self.pull_request(),
                    self.requested_reviewers("ben", self.reviewer),
                ],
                mutation=refusal,
            ) as calls:
                result = self.rerequest()
            self.assertEqual(result["status"], "unknown")
            self.assertEqual(calls["mutate"].call_count, 1)

    def test_cli_exit_codes_and_canonical_json(self) -> None:
        arguments = [
            "--repository",
            self.repository,
            "--pr",
            str(self.pr_number),
            "--head-oid",
            self.head_oid,
            "--reviewer",
            self.reviewer,
            "--expected-review-id",
            self.review_id,
            "--expected-authenticated-login",
            self.login,
        ]
        for status, code in (("verified", 0), ("blocked", 1), ("unknown", 2)):
            with self.subTest(status=status):
                result = {
                    "schema_version": 1,
                    "operation": "reviewer-rerequest",
                    "status": status,
                    "reason": "ünïcode reason",
                }
                with (
                    mock.patch.object(
                        REREQUEST, "request_rereview", return_value=result
                    ) as rerequest,
                    contextlib.redirect_stdout(io.StringIO()) as printed,
                ):
                    self.assertEqual(REREQUEST.main(arguments), code)
                self.assertEqual(
                    printed.getvalue(),
                    json.dumps(
                        result,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n",
                )
                self.assertEqual(
                    rerequest.call_args.kwargs,
                    {
                        "repository": self.repository,
                        "pr_number": self.pr_number,
                        "head_oid": self.head_oid,
                        "reviewer": self.reviewer,
                        "expected_review_id": self.review_id,
                        "expected_authenticated_login": self.login,
                    },
                )
        invalid = {
            "head-oid": ["--head-oid", "b" * 39],
            "review-id": ["--expected-review-id", "PRRC_kwDOnotareview"],
            "repository": ["--repository", "acme/app/extra"],
        }
        for name, replacement in invalid.items():
            with self.subTest(invalid=name):
                changed = list(arguments)
                changed[changed.index(replacement[0]) + 1] = replacement[1]
                with (
                    mock.patch.object(REREQUEST, "_active_login") as active,
                    contextlib.redirect_stdout(io.StringIO()) as printed,
                ):
                    self.assertEqual(REREQUEST.main(changed), 1)
                active.assert_not_called()
                self.assertEqual(json.loads(printed.getvalue())["status"], "blocked")
        for name, changed in (
            ("missing-argument", arguments[2:]),
            ("non-integer-pr", [*arguments[:2], "--pr", "forty-two", *arguments[4:]]),
        ):
            with self.subTest(usage=name):
                with (
                    mock.patch.object(REREQUEST, "_active_login") as active,
                    contextlib.redirect_stdout(io.StringIO()) as printed,
                    contextlib.redirect_stderr(io.StringIO()),
                ):
                    self.assertEqual(REREQUEST.main(changed), 1)
                active.assert_not_called()
                output = json.loads(printed.getvalue())
                self.assertEqual(
                    (output["operation"], output["status"]),
                    ("reviewer-rerequest", "blocked"),
                )


if __name__ == "__main__":
    unittest.main()
