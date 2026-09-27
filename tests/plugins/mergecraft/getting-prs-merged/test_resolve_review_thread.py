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


def load_resolution_module(name: str):
    path = SKILL_ROOT / "scripts" / "resolve_review_thread.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RESOLVE = load_resolution_module("resolve_review_thread")


def completed(value: object) -> subprocess.CompletedProcess[str]:
    text = value if isinstance(value, str) else json.dumps(value)
    return subprocess.CompletedProcess([], 0, text, "")


class ReviewThreadResolutionActuatorTests(unittest.TestCase):
    repository = "acme/app"
    pr_number = 42
    head_oid = "b" * 40
    url = "https://github.com/acme/app/pull/42"
    login = "merge-operator"
    thread_id = "PRRT_kwDOthread42"
    comment_id = "PRRC_kwDOcomment1"

    def stored(self, **changes: object) -> dict[str, object]:
        return {
            "number": self.pr_number,
            "url": self.url,
            "headRefOid": self.head_oid,
            "state": "OPEN",
            **changes,
        }

    def thread(
        self,
        *,
        resolved: bool = False,
        resolved_by: str | None = None,
        can_resolve: bool | None = None,
        last_comment: str | None = None,
        **changes: object,
    ) -> dict[str, object]:
        node = {
            "__typename": "PullRequestReviewThread",
            "id": self.thread_id,
            "isResolved": resolved,
            "viewerCanResolve": (not resolved) if can_resolve is None else can_resolve,
            "resolvedBy": {"login": resolved_by} if resolved_by else None,
            "repository": {"nameWithOwner": self.repository},
            "pullRequest": {
                "number": self.pr_number,
                "url": self.url,
                "headRefOid": self.head_oid,
            },
            "comments": {"nodes": [{"id": last_comment or self.comment_id}]},
        }
        node.update(changes)
        return {"data": {"node": node}}

    def resolution(self, **changes: object) -> dict[str, object]:
        thread = {
            "id": self.thread_id,
            "isResolved": True,
            "resolvedBy": {"login": self.login},
            **changes,
        }
        return {"data": {"resolveReviewThread": {"thread": thread}}}

    def resolve(self, **changes: object) -> dict[str, object]:
        arguments = {
            "repository": self.repository,
            "pr_number": self.pr_number,
            "head_oid": self.head_oid,
            "thread_id": self.thread_id,
            "expected_last_comment_id": self.comment_id,
            "expected_authenticated_login": self.login,
            **changes,
        }
        return RESOLVE.resolve_thread(**arguments)

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
                    self.resolution() if mutation is None else mutation
                )
            }
        with (
            mock.patch.object(
                RESOLVE, "_active_login", return_value=login or self.login
            ) as active,
            mock.patch.object(
                RESOLVE,
                "_stored_pr",
                side_effect=stored or [self.stored(), self.stored()],
            ) as stored_pr,
            mock.patch.object(RESOLVE, "_run_read", side_effect=read_effects) as read,
            mock.patch.object(RESOLVE, "_run_mutation", **mutation_effect) as mutate,
        ):
            yield {
                "active": active,
                "stored": stored_pr,
                "read": read,
                "mutate": mutate,
            }

    def test_resolves_once_and_returns_verified_reread_receipt(self) -> None:
        with self.live(
            reads=[self.thread(), self.thread(resolved=True, resolved_by=self.login)]
        ) as calls:
            result = self.resolve()
        self.assertEqual(result["status"], "verified", result["reason"])
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["operation"], "github:review-thread-resolution")
        self.assertTrue(result["mutation_attempted"])
        self.assertIsNone(result["reraised_comment_id"])
        self.assertEqual(result["live"]["resolved_by"], self.login)
        self.assertTrue(result["live"]["is_resolved"])
        self.assertEqual(calls["mutate"].call_count, 1)
        self.assertEqual(calls["stored"].call_count, 2)
        self.assertEqual(calls["read"].call_count, 2)
        arguments = calls["mutate"].call_args.args[0]
        self.assertEqual(
            arguments,
            ["gh", "api", "--hostname", "github.com", "graphql", "--input", "-"],
        )
        document = json.loads(calls["mutate"].call_args.kwargs["input_text"])
        self.assertIn("resolveReviewThread", document["query"])
        self.assertNotIn("resolutionReason", document["query"])
        self.assertEqual(document["variables"], {"thread": self.thread_id})
        read_document = json.loads(calls["read"].call_args_list[0].kwargs["input_text"])
        self.assertEqual(read_document["variables"], {"thread": self.thread_id})
        self.assertNotIn("mutation", read_document["query"])

    def test_already_resolved_thread_is_verified_without_mutation(self) -> None:
        with self.live(
            reads=[self.thread(resolved=True, resolved_by="reviewer")]
        ) as calls:
            result = self.resolve()
        self.assertEqual(result["status"], "verified", result["reason"])
        self.assertFalse(result["mutation_attempted"])
        self.assertEqual(result["live"]["resolved_by"], "reviewer")
        self.assertIn("already resolved", result["reason"])
        calls["mutate"].assert_not_called()

    def test_newer_comment_blocks_before_mutation_as_reraised(self) -> None:
        with self.live(reads=[self.thread(last_comment="PRRC_kwDOnewer")]) as calls:
            result = self.resolve()
        self.assertEqual(result["status"], "blocked")
        self.assertIn("reraised", result["reason"])
        self.assertEqual(result["reraised_comment_id"], "PRRC_kwDOnewer")
        self.assertFalse(result["mutation_attempted"])
        calls["mutate"].assert_not_called()

    def test_thread_on_other_repository_or_pull_request_blocks(self) -> None:
        cases = (
            ("repository", {"repository": {"nameWithOwner": "acme/other"}}),
            (
                "pull-request",
                {
                    "pullRequest": {
                        "number": 43,
                        "url": "https://github.com/acme/app/pull/43",
                        "headRefOid": self.head_oid,
                    }
                },
            ),
            ("thread-id", {"id": "PRRT_kwDOother"}),
            ("node-type", {"__typename": "PullRequestReviewComment"}),
        )
        for name, changes in cases:
            with self.subTest(name=name):
                with self.live(reads=[self.thread(**changes)]) as calls:
                    result = self.resolve()
                self.assertEqual(result["status"], "blocked")
                self.assertIn("bound", result["reason"])
                calls["mutate"].assert_not_called()
        with self.subTest(name="missing-node"):
            with self.live(reads=[{"data": {"node": None}}]) as calls:
                result = self.resolve()
            self.assertEqual(result["status"], "blocked")
            calls["mutate"].assert_not_called()

    def test_head_drift_before_resolution_blocks_without_mutation(self) -> None:
        with self.subTest(name="stored-pr"):
            with self.live(
                reads=[self.thread()], stored=[self.stored(headRefOid="c" * 40)]
            ) as calls:
                result = self.resolve()
            self.assertEqual(result["status"], "blocked")
            self.assertIn("head", result["reason"])
            calls["read"].assert_not_called()
            calls["mutate"].assert_not_called()
        with self.subTest(name="closed-pr"):
            with self.live(
                reads=[self.thread()], stored=[self.stored(state="MERGED")]
            ) as calls:
                result = self.resolve()
            self.assertEqual(result["status"], "blocked")
            calls["mutate"].assert_not_called()
        with self.subTest(name="thread-pull-request"):
            drifted = {
                "pullRequest": {
                    "number": self.pr_number,
                    "url": self.url,
                    "headRefOid": "c" * 40,
                }
            }
            with self.live(reads=[self.thread(**drifted)]) as calls:
                result = self.resolve()
            self.assertEqual(result["status"], "blocked")
            self.assertIn("head", result["reason"])
            calls["mutate"].assert_not_called()

    def test_active_login_mismatch_stops_before_any_read_or_mutation(self) -> None:
        with self.live(reads=[self.thread()], login="other") as calls:
            result = self.resolve()
        self.assertEqual(result["status"], "blocked")
        self.assertIn("active authenticated login", result["reason"])
        calls["stored"].assert_not_called()
        calls["read"].assert_not_called()
        calls["mutate"].assert_not_called()

    def test_viewer_cannot_resolve_blocks_without_mutation(self) -> None:
        with self.live(reads=[self.thread(can_resolve=False)]) as calls:
            result = self.resolve()
        self.assertEqual(result["status"], "blocked")
        self.assertIn("cannot resolve", result["reason"])
        self.assertFalse(result["live"]["viewer_can_resolve"])
        calls["mutate"].assert_not_called()

    def test_graphql_errors_in_read_block_without_mutation(self) -> None:
        cases = (
            ("errors", {"data": {"node": None}, "errors": [{"message": "denied"}]}),
            ("no-data", {"errors": [{"message": "denied"}]}),
            ("invalid-json", "not json"),
            ("failed-read", RESOLVE.StateReadError("gh read failed: HTTP 502")),
        )
        for name, response in cases:
            with self.subTest(name=name):
                with self.live(reads=[response]) as calls:
                    result = self.resolve()
                self.assertEqual(result["status"], "blocked")
                self.assertFalse(result["mutation_attempted"])
                calls["mutate"].assert_not_called()

    def test_mutation_timeout_is_unknown_and_never_retried(self) -> None:
        with self.live(
            reads=[self.thread()],
            mutation=RESOLVE.MutationAmbiguousError("timeout"),
        ) as calls:
            result = self.resolve()
        self.assertEqual(result["status"], "unknown")
        self.assertTrue(result["mutation_attempted"])
        self.assertEqual(calls["mutate"].call_count, 1)

    def test_untrustworthy_payload_or_null_resolved_by_is_unknown(self) -> None:
        cases = (
            ("null-resolved-by", self.resolution(resolvedBy=None)),
            ("other-resolver", self.resolution(resolvedBy={"login": "other"})),
            ("unresolved", self.resolution(isResolved=False)),
            ("other-thread", self.resolution(id="PRRT_kwDOother")),
            (
                "errors",
                {**self.resolution(), "errors": [{"message": "partial"}]},
            ),
            ("no-thread", {"data": {"resolveReviewThread": None}}),
            ("invalid-json", "not json"),
        )
        for name, payload in cases:
            with self.subTest(name=name):
                with self.live(
                    reads=[
                        self.thread(),
                        self.thread(resolved=True, resolved_by=self.login),
                    ],
                    mutation=payload,
                ) as calls:
                    result = self.resolve()
                self.assertEqual(result["status"], "unknown")
                self.assertEqual(calls["mutate"].call_count, 1)

    def test_refused_mutation_is_blocked_with_live_state_reported(self) -> None:
        refusal = RESOLVE.PublicationError(
            "gh mutation failed: Resource not accessible by integration"
        )
        with self.live(reads=[self.thread(), self.thread()], mutation=refusal) as calls:
            result = self.resolve()
        self.assertEqual(result["status"], "blocked")
        self.assertTrue(result["mutation_attempted"])
        self.assertIn("Resource not accessible", result["refusal"])
        self.assertFalse(result["live"]["is_resolved"])
        self.assertEqual(result["live"]["last_comment_id"], self.comment_id)
        self.assertEqual(calls["mutate"].call_count, 1)
        self.assertEqual(calls["read"].call_count, 2)
        with self.subTest(name="resolved-despite-refusal"):
            with self.live(
                reads=[
                    self.thread(),
                    self.thread(resolved=True, resolved_by=self.login),
                ],
                mutation=refusal,
            ) as calls:
                result = self.resolve()
            self.assertEqual(result["status"], "unknown")
            self.assertEqual(calls["mutate"].call_count, 1)
        with self.subTest(name="reread-fails-after-refusal"):
            with self.live(
                reads=[self.thread(), RESOLVE.StateReadError("gh read failed")],
                mutation=refusal,
            ) as calls:
                result = self.resolve()
            self.assertEqual(result["status"], "unknown")
            self.assertEqual(calls["mutate"].call_count, 1)

    def test_head_drift_after_resolution_is_unknown(self) -> None:
        with self.live(
            reads=[self.thread(), self.thread(resolved=True, resolved_by=self.login)],
            stored=[self.stored(), self.stored(headRefOid="c" * 40)],
        ) as calls:
            result = self.resolve()
        self.assertEqual(result["status"], "unknown")
        self.assertIn("head", result["reason"])
        self.assertEqual(calls["mutate"].call_count, 1)

    def test_reraised_after_resolution_is_reported(self) -> None:
        with self.live(
            reads=[
                self.thread(),
                self.thread(
                    resolved=True,
                    resolved_by=self.login,
                    last_comment="PRRC_kwDOnewer",
                ),
            ]
        ) as calls:
            result = self.resolve()
        self.assertEqual(result["status"], "verified", result["reason"])
        self.assertEqual(result["reraised_comment_id"], "PRRC_kwDOnewer")
        self.assertIn("reraised", result["reason"])
        self.assertEqual(calls["mutate"].call_count, 1)

    def test_cli_exit_codes_and_canonical_json(self) -> None:
        arguments = [
            "--repository",
            self.repository,
            "--pr",
            str(self.pr_number),
            "--head-oid",
            self.head_oid,
            "--thread-id",
            self.thread_id,
            "--expected-last-comment-id",
            self.comment_id,
            "--expected-authenticated-login",
            self.login,
        ]
        for status, code in (("verified", 0), ("blocked", 1), ("unknown", 2)):
            with self.subTest(status=status):
                result = {
                    "schema_version": 1,
                    "operation": "github:review-thread-resolution",
                    "status": status,
                    "reason": "ünïcode reason",
                }
                with (
                    mock.patch.object(
                        RESOLVE, "resolve_thread", return_value=result
                    ) as resolve,
                    contextlib.redirect_stdout(io.StringIO()) as printed,
                ):
                    self.assertEqual(RESOLVE.main(arguments), code)
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
                    resolve.call_args.kwargs,
                    {
                        "repository": self.repository,
                        "pr_number": self.pr_number,
                        "head_oid": self.head_oid,
                        "thread_id": self.thread_id,
                        "expected_last_comment_id": self.comment_id,
                        "expected_authenticated_login": self.login,
                    },
                )
        invalid = {
            "head-oid": ["--head-oid", "B" * 40],
            "thread-id": ["--thread-id", "PRRC_kwDOnotathread"],
            "comment-id": ["--expected-last-comment-id", "PRRT_kwDOnotacomment"],
            "repository": ["--repository", "acme"],
        }
        for name, replacement in invalid.items():
            with self.subTest(invalid=name):
                changed = list(arguments)
                changed[changed.index(replacement[0]) + 1] = replacement[1]
                with (
                    mock.patch.object(RESOLVE, "_active_login") as active,
                    contextlib.redirect_stdout(io.StringIO()) as printed,
                ):
                    self.assertEqual(RESOLVE.main(changed), 1)
                active.assert_not_called()
                self.assertEqual(json.loads(printed.getvalue())["status"], "blocked")
        for name, changed in (
            ("missing-argument", arguments[2:]),
            ("non-integer-pr", [*arguments[:2], "--pr", "forty-two", *arguments[4:]]),
        ):
            with self.subTest(usage=name):
                with (
                    mock.patch.object(RESOLVE, "_active_login") as active,
                    contextlib.redirect_stdout(io.StringIO()) as printed,
                    contextlib.redirect_stderr(io.StringIO()),
                ):
                    self.assertEqual(RESOLVE.main(changed), 1)
                active.assert_not_called()
                output = json.loads(printed.getvalue())
                self.assertEqual(
                    (output["operation"], output["status"]),
                    ("github:review-thread-resolution", "blocked"),
                )


if __name__ == "__main__":
    unittest.main()
