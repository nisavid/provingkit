"""Tests for the ``gh`` stub's fidelity fixes: inline review comments, repository merge settings, required checks,
head placeholders, workflow-run listings, collaborator-only review requests, stable identities, the clock, the
``date`` shim that follows it, the ``sleep`` shim that moves it, responses delayed on it, and the Python startup
hook (``stub_clock``) that puts a child's ``time`` and ``datetime`` on it."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins/praxis/skills/constructing-agent-policies/scripts"


def load(name):
    specification = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


gh_stub = load("gh_stub")
stub_clock = load("stub_clock")

HEAD = "3f9c2e1b7a4d5e6f8091a2b3c4d5e6f708192a3b"
BASE = "9b1e4d27c3a8f0e5d6b7c8a9e0f1a2b3c4d5e6f7"
LATE_KEYS = ("on_write", "on_push")


def parse_time(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def github():
    """A pull request with a human thread, two reviews, a bot comment, mixed checks, and branch protection."""
    return {
        "login": "nisavid", "repo": "nisavid/quire",
        "pull_request": {"number": 84, "title": "Retry transient upload failures", "author": {"login": "nisavid"},
                         "headRefName": "nisavid/upload-retry", "baseRefName": "main",
                         "headRefOid": HEAD, "baseRefOid": BASE,
                         "headCommitMessage": "fix(upload): raise UploadError after the final attempt",
                         "reviewRequests": [{"__typename": "User", "login": "ben"}],
                         "milestone": {"title": "2026.09 release cut", "dueOn": "{{now+180m}}"}},
        "review_threads": [
            {"id": "PRRT_kwDOquire84ana", "isResolved": False, "isOutdated": False, "path": "src/quire/upload.py",
             "line": 16, "comments": [
                 {"author": {"login": "ana"}, "body": "Can we raise after the final attempt?",
                  "createdAt": "{{now-3h}}"},
                 {"author": {"login": "nisavid"}, "body": "Done in {{head}}.", "createdAt": "{{now-30m}}"}]}],
        "reviews": [
            {"author": {"login": "ana"}, "state": "COMMENTED", "body": "", "submittedAt": "{{now-3h}}",
             "commit": {"oid": "{{base}}"}},
            {"author": {"login": "ben"}, "state": "APPROVED", "body": "", "submittedAt": "{{now-2h}}",
             "commit": {"oid": "{{base}}"}}],
        "issue_comments": [{"author": {"login": "coderabbitai"}, "authorType": "Bot",
                            "body": "Walkthrough: retries uploads.", "createdAt": "{{now-2h}}"}],
        "checks": [
            {"__typename": "CheckRun", "name": "test", "status": "COMPLETED", "conclusion": "SUCCESS",
             "state": "SUCCESS", "bucket": "pass", "workflowName": "ci", "startedAt": "{{now-40m}}",
             "completedAt": "{{now-38m}}", "link": "https://github.com/nisavid/quire/actions/runs/7310000/job/1"},
            {"__typename": "CheckRun", "name": "lint", "state": "SUCCESS", "bucket": "pass", "conclusion": "SUCCESS",
             "workflowName": "ci"},
            {"__typename": "CheckRun", "name": "link-check", "state": "FAILURE", "bucket": "fail",
             "conclusion": "FAILURE", "workflowName": "docs"},
            {"__typename": "StatusContext", "context": "CodeRabbit", "name": "CodeRabbit", "state": "PENDING",
             "bucket": "pending"}],
        "branch_protection": {"required_status_checks": {"strict": False, "contexts": ["test", "lint"]},
                              "required_conversation_resolution": {"enabled": True}},
        "requested_reviewers": {"users": [{"login": "ben"}], "teams": []},
        "api": {},
    }


class StubCase(unittest.TestCase):
    """One initialized stub state per test, rendered the way the runner renders a case at run start."""

    def extra_state(self):
        return {}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state_dir = Path(self.tmp.name)
        self.now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
        state = github()
        state.update(self.extra_state())
        gh_stub.initialize(self.state_dir, self.render(state), head=HEAD, base=BASE)

    def render(self, state, now=None):
        late = {key: state[key] for key in LATE_KEYS if key in state}
        early = {key: value for key, value in state.items() if key not in LATE_KEYS}
        rendered = gh_stub.render_placeholders(early, now or self.now, head=HEAD, base=BASE)
        rendered.update(late)
        return rendered

    def gh(self, *argv, stdin=""):
        return gh_stub.invoke(list(argv), stdin, self.state_dir)

    def ok(self, *argv, stdin=""):
        out, code = self.gh(*argv, stdin=stdin)
        self.assertEqual(code, 0, out)
        return out

    def fails(self, *argv, stdin=""):
        out, code = self.gh(*argv, stdin=stdin)
        self.assertEqual(code, 1, out)
        return out

    def rest(self, endpoint, *argv, stdin=""):
        return json.loads(self.ok("api", endpoint, *argv, stdin=stdin))

    def graphql(self, query, variables=None):
        return json.loads(self.ok("api", "graphql", "--input", "-",
                                  stdin=json.dumps({"query": query, "variables": variables or {}})))["data"]

    def log(self):
        return [json.loads(line) for line in (self.state_dir / "gh-stub.log").read_text().splitlines()]

    def state(self):
        return json.loads((self.state_dir / "state.json").read_text())

    def pr_id(self):
        return self.state()["pull_request"]["id"]

    def threads(self):
        data = self.graphql('{ repository(owner: "nisavid", name: "quire") { pullRequest(number: 84) { reviewThreads'
                            '(first: 50) { nodes { id path line diffSide subjectType isResolved comments(first: 50) '
                            '{ nodes { id databaseId body createdAt author { login } replyTo { id } '
                            'pullRequestReview { id databaseId state } commit { oid } } } } } } } }')
        return data["repository"]["pullRequest"]["reviewThreads"]["nodes"]


# ----------------------------------------------------------------------------- H4 (1): inline review comments

INLINE = {"body": "`csv.writer` defaults to CRLF; set lineterminator.", "commit_id": HEAD,
          "path": "src/ledger/export.py", "line": 8, "side": "RIGHT"}


class InlineReviewCommentTest(StubCase):
    def test_rest_post_without_in_reply_to_creates_a_standalone_comment_that_rereads(self):
        created = self.rest("/repos/nisavid/quire/pulls/84/comments", "--method", "POST", "--input", "-",
                            stdin=json.dumps(INLINE))
        self.assertEqual((created["body"], created["path"], created["line"], created["side"], created["in_reply_to_id"],
                          created["user"]["login"], created["commit_id"]),
                         (INLINE["body"], "src/ledger/export.py", 8, "RIGHT", None, "nisavid", HEAD))
        self.assertIsInstance(created["id"], int)
        self.assertTrue(created["node_id"].startswith("PRRC_"))
        self.assertTrue(created["html_url"].endswith(f"#discussion_r{created['id']}"))
        write = self.log()[-1]["writes"][0]
        self.assertEqual({k: write[k] for k in ("kind", "number", "body", "file", "line", "method", "path")},
                         {"kind": "review-comment", "number": 84, "body": INLINE["body"], "file": "src/ledger/export.py",
                          "line": 8, "method": "POST", "path": "repos/nisavid/quire/pulls/84/comments"})
        self.assertTrue(gh_stub.write_matches(write, {"kind": "review-comment", "body_regex": "(?i)lineterminator"}))
        listing = self.rest("/repos/nisavid/quire/pulls/84/comments")
        mine = [c for c in listing if c["user"]["login"] == "nisavid" and c["path"] == "src/ledger/export.py"]
        self.assertEqual([c["id"] for c in mine], [created["id"]])
        self.assertEqual(self.rest(f"/repos/nisavid/quire/pulls/comments/{created['id']}")["body"], INLINE["body"])
        thread = next(t for t in self.threads() if t["path"] == "src/ledger/export.py")
        comment = thread["comments"]["nodes"][0]
        self.assertEqual((thread["line"], thread["diffSide"], thread["isResolved"], comment["id"], comment["databaseId"],
                          comment["replyTo"], comment["commit"]["oid"]),
                         (8, "RIGHT", False, created["node_id"], created["id"], None, HEAD))
        self.assertEqual(comment["pullRequestReview"]["databaseId"], created["pull_request_review_id"])
        self.assertEqual(comment["pullRequestReview"]["state"], "COMMENTED")
        reviews = self.rest("/repos/nisavid/quire/pulls/84/reviews")
        self.assertIn(created["pull_request_review_id"], [r["id"] for r in reviews])
        again = self.rest("/repos/nisavid/quire/pulls/84/comments")
        self.assertEqual([(c["id"], c["node_id"], c["created_at"]) for c in again],
                         [(c["id"], c["node_id"], c["created_at"]) for c in listing])

    def test_position_stands_in_for_line_and_a_comment_without_a_path_is_refused(self):
        created = self.rest("/repos/nisavid/quire/pulls/84/comments", "--method", "POST", "--input", "-",
                            stdin=json.dumps({"body": "Trailing whitespace.", "commit_id": HEAD,
                                              "path": "README.md", "position": 3}))
        self.assertEqual((created["path"], created["line"], created["position"]), ("README.md", 3, 3))
        before = len(self.rest("/repos/nisavid/quire/pulls/84/comments"))
        out = self.fails("api", "/repos/nisavid/quire/pulls/84/comments", "--method", "POST", "--input", "-",
                         stdin=json.dumps({"body": "No path.", "commit_id": HEAD, "line": 1}))
        self.assertIn("422", out)
        self.assertEqual(self.log()[-1]["writes"], [])
        self.assertEqual(len(self.rest("/repos/nisavid/quire/pulls/84/comments")), before)

    def test_a_reply_by_in_reply_to_still_joins_its_thread(self):
        root = self.rest("/repos/nisavid/quire/pulls/84/comments")[0]
        reply = self.rest("/repos/nisavid/quire/pulls/84/comments", "--method", "POST", "--input", "-",
                          stdin=json.dumps({"body": "Raised now.", "in_reply_to": root["id"]}))
        self.assertEqual(reply["in_reply_to_id"], root["id"])
        self.assertEqual(self.log()[-1]["writes"][0]["kind"], "review-comment-reply")

    def test_graphql_add_thread_and_add_comment_create_standalone_comments(self):
        data = self.graphql("mutation($pr: ID!) { addPullRequestReviewThread(input: {pullRequestId: $pr, "
                            'path: "tests/test_upload.py", line: 4, side: RIGHT, body: "Assert the cause."}) '
                            "{ thread { id path line comments(first: 5) { nodes { id body author { login } } } } } }",
                            {"pr": self.pr_id()})
        thread = data["addPullRequestReviewThread"]["thread"]
        self.assertEqual((thread["path"], thread["line"], thread["comments"]["nodes"][0]["body"],
                          thread["comments"]["nodes"][0]["author"]["login"]),
                         ("tests/test_upload.py", 4, "Assert the cause.", "nisavid"))
        write = self.log()[-1]["writes"][0]
        self.assertEqual((write["kind"], write["file"], write["line"], write["body"]),
                         ("review-comment", "tests/test_upload.py", 4, "Assert the cause."))
        self.assertIn(thread["id"], [t["id"] for t in self.threads()])
        pending = self.graphql("mutation($pr: ID!) { addPullRequestReview(input: {pullRequestId: $pr}) "
                               "{ pullRequestReview { id state } } }", {"pr": self.pr_id()})["addPullRequestReview"]
        review_id = pending["pullRequestReview"]["id"]
        self.assertEqual(pending["pullRequestReview"]["state"], "PENDING")
        data = self.graphql("mutation($review: ID!) { addPullRequestReviewComment(input: {pullRequestReviewId: $review, "
                            'path: "README.md", position: 2, body: "Typo."}) { comment { id path body '
                            "pullRequestReview { id } } } }", {"review": review_id})
        comment = data["addPullRequestReviewComment"]["comment"]
        self.assertEqual((comment["path"], comment["body"], comment["pullRequestReview"]["id"]),
                         ("README.md", "Typo.", review_id))
        self.assertEqual(self.log()[-1]["writes"][0]["review_id"], review_id)


REVIEW = {"event": "COMMENT", "body": "Two things.", "commit_id": HEAD, "comments": [
    {"path": "src/ledger/export.py", "line": 8, "side": "RIGHT", "body": "CRLF here: set lineterminator."},
    {"path": "src/ledger/export.py", "position": 3, "body": "The header repeats on append."}]}


class ReviewCommentsPersistTest(StubCase):
    def test_rest_review_submission_persists_its_inline_comments(self):
        review = self.rest("/repos/nisavid/quire/pulls/84/reviews", "--method", "POST", "--input", "-",
                           stdin=json.dumps(REVIEW))
        self.assertEqual((review["state"], review["body"], review["commit_id"]), ("COMMENTED", "Two things.", HEAD))
        write = self.log()[-1]["writes"][0]
        self.assertEqual((write["kind"], write["event"], write["body"]), ("review", "COMMENT", "Two things."))
        self.assertEqual([(c["path"], c["line"], c["body"]) for c in write["comments"]],
                         [("src/ledger/export.py", 8, "CRLF here: set lineterminator."),
                          ("src/ledger/export.py", 3, "The header repeats on append.")])
        self.assertTrue(gh_stub.write_matches(write, {"kind": "review", "body_regex": "(?i)lineterminator"}))
        self.assertTrue(gh_stub.write_matches(write, {"body_contains": "header repeats"}))
        self.assertFalse(gh_stub.write_matches(write, {"body_contains": "nothing of the sort"}))
        comments = self.rest(f"/repos/nisavid/quire/pulls/84/reviews/{review['id']}/comments")
        self.assertEqual([(c["path"], c["line"], c["body"], c["pull_request_review_id"], c["commit_id"])
                          for c in comments],
                         [("src/ledger/export.py", 8, "CRLF here: set lineterminator.", review["id"], HEAD),
                          ("src/ledger/export.py", 3, "The header repeats on append.", review["id"], HEAD)])
        listing = self.rest("/repos/nisavid/quire/pulls/84/comments")
        self.assertEqual({c["id"] for c in comments} <= {c["id"] for c in listing}, True)
        data = self.graphql('{ repository(owner: "nisavid", name: "quire") { pullRequest(number: 84) { reviews'
                            "(first: 20) { nodes { databaseId comments(first: 20) { nodes { path body } } } } } } }")
        found = next(r for r in data["repository"]["pullRequest"]["reviews"]["nodes"]
                     if r["databaseId"] == review["id"])
        self.assertEqual([c["body"] for c in found["comments"]["nodes"]],
                         ["CRLF here: set lineterminator.", "The header repeats on append."])
        self.assertEqual(len([t for t in self.threads() if t["path"] == "src/ledger/export.py"]), 2)

    def test_graphql_review_threads_and_comments_persist(self):
        data = self.graphql("mutation($pr: ID!) { addPullRequestReview(input: {pullRequestId: $pr, event: COMMENT, "
                            'body: "Notes.", threads: [{path: "README.md", line: 2, side: RIGHT, body: "Wrap this."}], '
                            'comments: [{path: "README.md", position: 5, body: "And this."}]}) '
                            "{ pullRequestReview { id databaseId comments(first: 10) { nodes { path line body } } } } }",
                            {"pr": self.pr_id()})
        review = data["addPullRequestReview"]["pullRequestReview"]
        self.assertEqual(sorted((c["path"], c["line"], c["body"]) for c in review["comments"]["nodes"]),
                         [("README.md", 2, "Wrap this."), ("README.md", 5, "And this.")])
        write = self.log()[-1]["writes"][0]
        self.assertEqual(sorted((c["path"], c["line"], c["body"]) for c in write["comments"]),
                         [("README.md", 2, "Wrap this."), ("README.md", 5, "And this.")])
        comments = self.rest(f"/repos/nisavid/quire/pulls/84/reviews/{review['databaseId']}/comments")
        self.assertEqual(len(comments), 2)


# ----------------------------------------------------------------------------- H4 (2): repository merge settings

class RepositorySettingsTest(StubCase):
    def test_repo_view_rest_and_graphql_report_merge_methods_by_default(self):
        view = json.loads(self.ok("repo", "view", "--json",
                                  "nameWithOwner,squashMergeAllowed,mergeCommitAllowed,rebaseMergeAllowed,"
                                  "deleteBranchOnMerge,isPrivate,visibility"))
        self.assertEqual(view, {"nameWithOwner": "nisavid/quire", "squashMergeAllowed": True, "mergeCommitAllowed": True,
                                "rebaseMergeAllowed": True, "deleteBranchOnMerge": False, "isPrivate": False,
                                "visibility": "PUBLIC"})
        repo = self.rest("repos/nisavid/quire")
        self.assertEqual({k: repo[k] for k in ("full_name", "allow_squash_merge", "allow_merge_commit",
                                                "allow_rebase_merge", "delete_branch_on_merge", "default_branch")},
                         {"full_name": "nisavid/quire", "allow_squash_merge": True, "allow_merge_commit": True,
                          "allow_rebase_merge": True, "delete_branch_on_merge": False, "default_branch": "main"})
        data = self.graphql('{ repository(owner: "nisavid", name: "quire") { squashMergeAllowed mergeCommitAllowed '
                            "rebaseMergeAllowed deleteBranchOnMerge } }")
        self.assertEqual(data["repository"], {"squashMergeAllowed": True, "mergeCommitAllowed": True,
                                              "rebaseMergeAllowed": True, "deleteBranchOnMerge": False})
        pr = self.rest("repos/nisavid/quire/pulls/84")
        self.assertTrue(pr["base"]["repo"]["allow_squash_merge"])


class RepositoryOverrideTest(StubCase):
    def extra_state(self):
        return {"api": {"GET repos/nisavid/quire": {"allow_squash_merge": False, "delete_branch_on_merge": True,
                                                    "description": "Upload client", "topics": ["uploads"]}}}

    def test_the_case_override_merges_over_the_repository_object(self):
        repo = self.rest("repos/nisavid/quire")
        self.assertEqual({k: repo[k] for k in ("full_name", "allow_squash_merge", "allow_merge_commit",
                                                "allow_rebase_merge", "delete_branch_on_merge", "description",
                                                "topics", "default_branch")},
                         {"full_name": "nisavid/quire", "allow_squash_merge": False, "allow_merge_commit": True,
                          "allow_rebase_merge": True, "delete_branch_on_merge": True, "description": "Upload client",
                          "topics": ["uploads"], "default_branch": "main"})
        view = json.loads(self.ok("repo", "view", "nisavid/quire", "--json",
                                  "squashMergeAllowed,mergeCommitAllowed,rebaseMergeAllowed,deleteBranchOnMerge,"
                                  "description"))
        self.assertEqual(view, {"squashMergeAllowed": False, "mergeCommitAllowed": True, "rebaseMergeAllowed": True,
                                "deleteBranchOnMerge": True, "description": "Upload client"})
        data = self.graphql('{ repository(owner: "nisavid", name: "quire") { squashMergeAllowed description } }')
        self.assertEqual(data["repository"], {"squashMergeAllowed": False, "description": "Upload client"})


# ----------------------------------------------------------------------------- H4 (3): required checks

class RequiredChecksTest(StubCase):
    def test_required_filters_by_the_protection_contexts(self):
        rows = [line.split("\t")[0] for line in self.ok("pr", "checks", "84", "--required").splitlines()]
        self.assertEqual(rows, ["test", "lint"])
        names = [c["name"] for c in json.loads(self.ok("pr", "checks", "84", "--required", "--json", "name,state"))]
        self.assertEqual(names, ["test", "lint"])
        every = [c["name"] for c in json.loads(self.ok("pr", "checks", "84", "--json", "name"))]
        self.assertEqual(every, ["test", "lint", "link-check", "CodeRabbit"])
        data = self.graphql('{ repository(owner: "nisavid", name: "quire") { pullRequest(number: 84) { statusCheckRollup '
                            "{ contexts(first: 10) { nodes { ... on CheckRun { name isRequired(pullRequestNumber: 84) } "
                            "... on StatusContext { context isRequired(pullRequestNumber: 84) } } } } } } }")
        nodes = data["repository"]["pullRequest"]["statusCheckRollup"]["contexts"]["nodes"]
        self.assertEqual([(n.get("name") or n.get("context"), n["isRequired"]) for n in nodes],
                         [("test", True), ("lint", True), ("link-check", False), ("CodeRabbit", False)])


class NoRequiredChecksTest(StubCase):
    def extra_state(self):
        return {"branch_protection": None}

    def test_required_with_no_protection_reports_none(self):
        out = self.ok("pr", "checks", "84", "--required")
        self.assertEqual(out, "no required checks reported on the 'nisavid/upload-retry' branch")
        self.assertEqual(json.loads(self.ok("pr", "checks", "84", "--required", "--json", "name")), [])
        self.assertEqual(len(self.ok("pr", "checks", "84").splitlines()), 4)


# ----------------------------------------------------------------------------- H4 (4): {{head}} renders as the current head

NEW_HEAD = "6c4e41f0a1b2c3d4e5f60718293a4b5c6d7e8f90"


class HeadPlaceholderTest(StubCase):
    def test_fixture_bodies_render_at_initialization_and_patches_at_the_current_head(self):
        bodies = [c["body"] for t in self.threads() for c in t["comments"]["nodes"]]
        self.assertIn(f"Done in {HEAD}.", bodies)
        unrendered = self.state_dir / "raw"
        gh_stub.initialize(unrendered, github(), head=HEAD, base=BASE)
        out, code = gh_stub.invoke(["api", "repos/nisavid/quire/pulls/84/comments"], "", unrendered)
        self.assertEqual(code, 0, out)
        self.assertIn(f"Done in {HEAD}.", [c["body"] for c in json.loads(out)])
        raw = json.loads((unrendered / "state.json").read_text())
        self.assertNotIn("{{", json.dumps({k: v for k, v in raw.items() if k not in LATE_KEYS}))
        gh_stub.apply_patch(self.state_dir, {"append": {"issue_comments": [
            {"author": {"login": "ana"}, "body": "Checked {{head}} against {{base}}."}]}})
        self.assertEqual(self.state()["issue_comments"][-1]["body"], f"Checked {HEAD} against {BASE}.")
        gh_stub.apply_patch(self.state_dir, {"set": {"pull_request": {"headRefOid": NEW_HEAD}}})
        gh_stub.apply_patch(self.state_dir, {"update_threads": {"PRRT_kwDOquire84ana": {"comments": [
            {"author": {"login": "ana"}, "body": "Can we raise after the final attempt?"},
            {"author": {"login": "nisavid"}, "body": f"Done in {HEAD}."},
            {"author": {"login": "nisavid"}, "body": "Now at {{head}}."}]}}})
        thread = next(t for t in self.threads() if t["id"] == "PRRT_kwDOquire84ana")
        self.assertEqual([c["body"] for c in thread["comments"]["nodes"]][-1], f"Now at {NEW_HEAD}.")


class OnWriteHeadTest(StubCase):
    def extra_state(self):
        return {"on_write": [{"match": {"kind": "issue-comment"}, "append": {"reviews": [
            {"author": {"login": "coderabbitai"}, "state": "COMMENTED", "body": "Reviewed {{head}}.",
             "commit": {"oid": "{{head}}"}}]}}]}

    def test_on_write_hooks_see_the_head_current_when_they_fire(self):
        gh_stub.apply_patch(self.state_dir, {"set": {"pull_request": {"headRefOid": NEW_HEAD}}})
        self.ok("pr", "comment", "84", "--body", "@coderabbitai review")
        review = self.state()["reviews"][-1]
        self.assertEqual((review["body"], review["commit"]), (f"Reviewed {NEW_HEAD}.", {"oid": NEW_HEAD}))


# ----------------------------------------------------------------------------- H4 (5): gh run list

MAIN_RUNS = {"total_count": 3, "check_runs": [
    {"name": "test", "head_sha": BASE, "status": "completed", "conclusion": "success", "app": {"slug": "github-actions"},
     "started_at": "{{now-5h}}", "completed_at": "{{now-4h}}"},
    {"name": "lint", "head_sha": BASE, "status": "completed", "conclusion": "success", "app": {"slug": "github-actions"}},
    {"name": "link-check", "head_sha": BASE, "status": "completed", "conclusion": "failure",
     "app": {"slug": "github-actions"}, "details_url": "https://github.com/nisavid/quire/actions/runs/7320000/job/2",
     "output": {"title": "docs/README.md: old-guide returned 404"}}]}


class RunListTest(StubCase):
    def extra_state(self):
        return {"api": {"GET repos/nisavid/quire/commits/main/check-runs": MAIN_RUNS}}

    def test_run_list_for_the_base_branch_answers_from_its_check_runs(self):
        rows = [line.split("\t") for line in self.ok("run", "list", "--branch", "main").splitlines()]
        self.assertEqual([(r[0], r[1], r[3], r[4], r[5]) for r in rows],
                         [("completed", "success", "ci", "main", "push"), ("completed", "success", "ci", "main", "push"),
                          ("completed", "failure", "docs", "main", "push")])
        runs = json.loads(self.ok("run", "list", "--branch", "main", "--json",
                                  "databaseId,name,workflowName,status,conclusion,headBranch,headSha,url,event"))
        self.assertEqual([(r["workflowName"], r["status"], r["conclusion"], r["headBranch"], r["headSha"]) for r in runs],
                         [("ci", "completed", "success", "main", BASE), ("ci", "completed", "success", "main", BASE),
                          ("docs", "completed", "failure", "main", BASE)])
        self.assertEqual(runs[2]["url"], "https://github.com/nisavid/quire/actions/runs/7320000/job/2")
        self.assertEqual(len({r["databaseId"] for r in runs}), 3)
        self.assertEqual(runs, json.loads(self.ok("run", "list", "-b", "main", "--json",
                                                  "databaseId,name,workflowName,status,conclusion,headBranch,headSha,"
                                                  "url,event")))
        docs = json.loads(self.ok("run", "list", "--branch", "main", "--workflow", "docs", "--json", "name,conclusion"))
        self.assertEqual(docs, [{"name": "docs", "conclusion": "failure"}])
        failed = json.loads(self.ok("run", "list", "--branch", "main", "--status", "failure", "--json", "workflowName"))
        self.assertEqual(failed, [{"workflowName": "docs"}])
        self.assertEqual(len(json.loads(self.ok("run", "list", "--branch", "main", "--limit", "2", "--json", "name"))), 2)
        self.assertEqual(self.log()[-1]["writes"], [])

    def test_run_list_covers_the_head_branch_and_other_branches_are_empty(self):
        head = json.loads(self.ok("run", "list", "--branch", "nisavid/upload-retry", "--json",
                                  "name,status,conclusion,headSha,displayTitle"))
        self.assertEqual(head, [
            {"name": "ci", "status": "completed", "conclusion": "success", "headSha": HEAD,
             "displayTitle": "fix(upload): raise UploadError after the final attempt"},
            {"name": "ci", "status": "completed", "conclusion": "success", "headSha": HEAD,
             "displayTitle": "fix(upload): raise UploadError after the final attempt"},
            {"name": "docs", "status": "completed", "conclusion": "failure", "headSha": HEAD,
             "displayTitle": "fix(upload): raise UploadError after the final attempt"}])
        everything = json.loads(self.ok("run", "list", "--json", "headBranch"))
        self.assertEqual([r["headBranch"] for r in everything], ["nisavid/upload-retry"] * 3 + ["main"] * 3)
        self.assertEqual(json.loads(self.ok("run", "list", "--branch", "release", "--json", "name")), [])
        self.assertEqual(self.ok("run", "list", "--branch", "release"), "")
        by_file = json.loads(self.ok("run", "list", "--workflow", "docs.yml", "--json", "headBranch"))
        self.assertEqual([r["headBranch"] for r in by_file], ["nisavid/upload-retry", "main"])


# ----------------------------------------------------------------------------- H4 (6): collaborator-only review requests

class ReviewRequestCollaboratorTest(StubCase):
    def extra_state(self):
        return {"api": {"GET repos/nisavid/quire/collaborators": [{"login": "nisavid", "role_name": "admin"},
                                                                  {"login": "ben", "role_name": "write"}],
                        "GET repos/nisavid/quire/collaborators/ana/permission": {"permission": "read", "role_name": "read"},
                        "GET repos/nisavid/quire/collaborators/mira/permission": {"permission": "maintain"}}}

    def requested(self):
        return [r.get("login") or r.get("slug") for r in json.loads(self.ok("pr", "view", "84", "--json",
                                                                            "reviewRequests"))["reviewRequests"]]

    def test_requests_for_non_collaborators_fail_with_422_and_change_nothing(self):
        gh_stub.set_turn(self.state_dir, 1)
        out = self.fails("pr", "edit", "84", "--add-reviewer", "ana")
        self.assertIn("Reviews may only be requested from collaborators", out)
        record = self.log()[-1]
        self.assertEqual(record["exit_code"], 1)
        self.assertEqual(record["writes"], [{"kind": "rejected-write", "rejected_kind": "request-reviewers",
                                             "reason": "not-a-collaborator", "reviewers": ["ana"], "action": "add",
                                             "number": 84, "turn": 1}])
        self.assertTrue(gh_stub.write_matches(record["writes"][0], {"kind": "rejected-write", "reviewer": "ana"}))
        self.assertEqual(self.requested(), ["ben"])
        out = self.fails("api", "--method", "POST", "repos/nisavid/quire/pulls/84/requested_reviewers",
                         "--input", "-", stdin='{"reviewers": ["ben", "ana"]}')
        self.assertIn("422", out)
        self.assertIn("Reviews may only be requested from collaborators", out)
        self.assertEqual(self.requested(), ["ben"])
        out = self.fails("api", "graphql", "-f", "query=mutation($pr: ID!) { requestReviews(input: {pullRequestId: $pr, "
                         'userLogins: ["ana"], union: true}) { pullRequest { id } } }', "-f", f"pr={self.pr_id()}")
        self.assertIn("Reviews may only be requested from collaborators", out)
        self.assertEqual(self.requested(), ["ben"])

    def test_collaborators_by_list_permission_or_association_and_teams_are_accepted(self):
        self.ok("pr", "edit", "84", "--add-reviewer", "mira", "--add-reviewer", "nisavid/core")
        self.assertEqual(self.requested(), ["ben", "mira", "core"])
        self.ok("pr", "edit", "84", "--remove-reviewer", "ana")
        self.assertEqual(self.log()[-1]["writes"][0]["kind"], "request-reviewers")
        gh_stub.apply_patch(self.state_dir, {"set": {"associations": {"kofi": "MEMBER"}}})
        self.ok("pr", "edit", "84", "--add-reviewer", "kofi")
        self.assertEqual(self.requested(), ["ben", "mira", "core", "kofi"])


class ReviewRequestWithoutEvidenceTest(StubCase):
    def extra_state(self):
        return {"api": {"GET repos/nisavid/quire/collaborators/lee/permission": {"permission": "read"},
                        "GET repos/nisavid/quire/collaborators/zed/permission": {"permission": "none"}}}

    def test_without_a_collaborator_list_only_an_explicit_none_permission_rejects(self):
        self.ok("pr", "edit", "84", "--add-reviewer", "dan", "--add-reviewer", "lee")
        logins = [r["login"] for r in json.loads(self.ok("pr", "view", "84", "--json",
                                                           "reviewRequests"))["reviewRequests"]]
        self.assertEqual(logins, ["ben", "dan", "lee"])
        out = self.fails("pr", "edit", "84", "--add-reviewer", "zed")
        self.assertIn("Reviews may only be requested from collaborators", out)


# ----------------------------------------------------------------------------- stable identities

class StableIdentityTest(StubCase):
    def identities(self):
        threads = [(t["id"], c["id"], c["databaseId"]) for t in self.threads() for c in t["comments"]["nodes"]]
        comments = [(c["id"], c["node_id"]) for c in self.rest("repos/nisavid/quire/issues/84/comments")]
        reviews = [(r["id"], r["node_id"], r["user"]["login"]) for r in self.rest("repos/nisavid/quire/pulls/84/reviews")]
        return threads, comments, reviews

    def test_identities_survive_restated_times_and_replaced_lists(self):
        before = self.identities()
        self.assertEqual(before, self.identities())
        state = self.render(github(), now=self.now - dt.timedelta(minutes=170))
        gh_stub.apply_patch(self.state_dir, {
            "set": {"reviews": state["reviews"], "issue_comments": state["issue_comments"]},
            "update_threads": {"PRRT_kwDOquire84ana": {"comments": state["review_threads"][0]["comments"]}}})
        after = self.identities()
        self.assertEqual(after, before)
        thread = next(t for t in self.threads() if t["id"] == "PRRT_kwDOquire84ana")
        self.assertEqual(parse_time(thread["comments"]["nodes"][1]["createdAt"]),
                         self.now - dt.timedelta(minutes=200))

    def test_identities_do_not_depend_on_when_the_run_started(self):
        other = self.state_dir / "other"
        gh_stub.initialize(other, self.render(github(), now=self.now - dt.timedelta(days=2)), head=HEAD, base=BASE)
        mine, theirs = self.state(), json.loads((other / "state.json").read_text())

        def pick(state):
            return ([(c["id"], c["databaseId"]) for t in state["review_threads"] for c in t["comments"]],
                    [(c["id"], c["databaseId"]) for c in state["issue_comments"]],
                    [(r["id"], r["databaseId"]) for r in state["reviews"]])

        self.assertEqual(pick(mine), pick(theirs))
        self.assertNotEqual(mine["issue_comments"][0]["createdAt"], theirs["issue_comments"][0]["createdAt"])

    def test_a_pending_review_keeps_its_creation_time_across_reads(self):
        self.graphql("mutation($pr: ID!) { addPullRequestReview(input: {pullRequestId: $pr, body: \"wip\"}) "
                     "{ pullRequestReview { id } } }", {"pr": self.pr_id()})
        query = ('{ repository(owner: "nisavid", name: "quire") { pullRequest(number: 84) { reviews(first: 10, '
                 "states: [PENDING]) { nodes { id createdAt updatedAt submittedAt } } } } }")
        first = self.graphql(query)["repository"]["pullRequest"]["reviews"]["nodes"]
        gh_stub.apply_patch(self.state_dir, {"advance": "90s"})
        second = self.graphql(query)["repository"]["pullRequest"]["reviews"]["nodes"]
        self.assertEqual(len(first), 1)
        self.assertEqual(first, second)
        self.assertIsNone(first[0]["submittedAt"])
        self.assertIsNotNone(first[0]["createdAt"])


# ----------------------------------------------------------------------------- H11: the clock advances

class ClockAdvanceTest(StubCase):
    def extra_state(self):
        return {"on_write": [{"match": {"kind": "review-thread-resolve"}, "append": {"issue_comments": [
            {"author": {"login": "ana"}, "body": "Resolved at {{now}}; I looked {{now-10m}}."}]}}]}

    def reads(self):
        comments = [(c["id"], c["created_at"]) for c in self.rest("repos/nisavid/quire/pulls/84/comments")]
        pr = json.loads(self.ok("pr", "view", "84", "--json", "milestone,createdAt"))
        reviews = [(r["id"], r["submitted_at"]) for r in self.rest("repos/nisavid/quire/pulls/84/reviews")]
        return comments, pr["milestone"]["dueOn"], reviews

    def assertNear(self, value, expected, seconds=5):
        moment = parse_time(value) if isinstance(value, str) else value
        self.assertLess(abs((moment - expected).total_seconds()), seconds, (value, expected))

    def test_advancing_between_turns_keeps_every_existing_time_and_moves_new_ones(self):
        gh_stub.set_turn(self.state_dir, 1)
        first = self.reads()
        self.assertEqual(first[1], gh_stub.render_placeholders("{{now+180m}}", self.now))
        self.assertNear(gh_stub.current_time(self.state_dir), self.now)
        gh_stub.set_turn(self.state_dir, 2)
        gh_stub.apply_patch(self.state_dir, {"advance": "170m"})
        shifted = self.now + dt.timedelta(minutes=170)
        self.assertEqual(self.reads(), first)
        self.assertNear(gh_stub.current_time(self.state_dir), shifted)
        self.ok("pr", "comment", "84", "--body", "Merging now.")
        record = self.log()[-1]
        self.assertEqual(record["turn"], 2)
        self.assertNear(record["clock"], shifted)
        self.assertNear(record["ts"], self.now)
        self.assertNear(self.rest("repos/nisavid/quire/issues/84/comments")[-1]["created_at"], shifted)
        self.graphql('mutation { resolveReviewThread(input: {threadId: "PRRT_kwDOquire84ana"}) { thread { id } } }')
        body = self.state()["issue_comments"][-1]["body"]
        at, looked = body.removeprefix("Resolved at ").removesuffix(".").split("; I looked ")
        self.assertNear(at, shifted)
        self.assertNear(looked, shifted - dt.timedelta(minutes=10))
        self.ok("pr", "merge", "84", "--squash")
        self.assertNear(json.loads(self.ok("pr", "view", "84", "--json", "mergedAt"))["mergedAt"], shifted)
        gh_stub.apply_patch(self.state_dir, {"advance": 600, "append": {"issue_comments": [
            {"author": {"login": "ben"}, "body": "Late."}]}})
        self.assertNear(self.state()["issue_comments"][-1]["createdAt"], shifted + dt.timedelta(minutes=10))
        self.assertNear(gh_stub.current_time(self.state_dir), shifted + dt.timedelta(minutes=10))
        gh_stub.set_turn(self.state_dir, 3)
        self.assertNear(gh_stub.current_time(self.state_dir), shifted + dt.timedelta(minutes=10))

    def test_advance_takes_seconds_or_units_and_refuses_anything_else(self):
        for value, seconds in (("45s", 45), ("3m", 180), ("2h", 7200), ("1d", 86400), (90, 90), ("+7m", 420)):
            state_dir = self.state_dir / value.replace("+", "p") if isinstance(value, str) else self.state_dir / "int"
            gh_stub.initialize(state_dir, self.render(github()), head=HEAD, base=BASE)
            gh_stub.apply_patch(state_dir, {"advance": value})
            self.assertNear(gh_stub.current_time(state_dir), self.now + dt.timedelta(seconds=seconds))
        for bad in ("soon", -5, "-5m", True, "1w", [10]):
            with self.assertRaises(ValueError, msg=repr(bad)):
                gh_stub.apply_patch(self.state_dir, {"advance": bad})
        gh_stub.apply_patch(self.state_dir, {"advance": None})
        self.assertNear(gh_stub.current_time(self.state_dir), self.now)
        self.assertNotIn("clock", self.log()[-1] if self.log() else {})


# ----------------------------------------------------------------------------- H11: the date shim

class DateShimTest(StubCase):
    def run_date(self, *argv, state=True):
        shim = gh_stub.install_date_shim(self.state_dir / "bin")
        env = {k: v for k, v in os.environ.items() if k != "GH_STUB_STATE_DIR"}
        if state:
            env["GH_STUB_STATE_DIR"] = str(self.state_dir)
        done = subprocess.run([str(shim), *argv], capture_output=True, text=True, env=env)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout.strip()

    def assertNear(self, epoch, expected, seconds=5):
        moment = dt.datetime.fromtimestamp(int(epoch), dt.timezone.utc)
        self.assertLess(abs((moment - expected).total_seconds()), seconds, (epoch, expected))

    def test_the_shim_follows_the_stub_clock_and_passes_own_times_through(self):
        marker = self.state_dir / "epoch0"
        marker.write_text("")
        os.utime(marker, (0, 0))
        self.assertNear(self.run_date("-u", "+%s"), self.now)
        gh_stub.apply_patch(self.state_dir, {"advance": "170m"})
        shifted = self.now + dt.timedelta(minutes=170)
        self.assertNear(self.run_date("-u", "+%s"), shifted)
        self.assertNear(parse_time(self.run_date("-u", "+%Y-%m-%dT%H:%M:%SZ")).timestamp(), shifted)
        self.assertEqual(self.run_date("-u", "-d", "@0", "+%Y"), "1970")
        self.assertEqual(self.run_date("-u", "--date=@0", "+%Y"), "1970")
        self.assertEqual(self.run_date("-ud", "@0", "+%Y"), "1970")
        self.assertEqual(self.run_date("-u", "-r", str(marker), "+%Y"), "1970")
        self.assertEqual(self.run_date("-u", f"--reference={marker}", "+%Y"), "1970")
        self.assertTrue(self.run_date("--version").startswith("date"))
        self.assertNear(self.run_date("-u", "+%s", state=False), self.now)
        self.assertNear(self.run_date("+%s"), shifted)
        self.assertEqual(self.state()["_clock_offset"], 170 * 60)
        for argument, expected in (("-d", True), ("-d@0", True), ("--date", True), ("--date=now", True),
                                   ("-r", True), ("--reference=x", True), ("-s", True), ("--set=now", True),
                                   ("-f", True), ("--file=-", True), ("-ud", True), ("-Rd", True),
                                   ("-u", False), ("-R", False), ("-I", False), ("-Iseconds", False),
                                   ("-Idate", False), ("+%s", False), ("--utc", False), ("--debug", False),
                                   ("-", False), ("now", False)):
            self.assertEqual(gh_stub.date_names_a_time(argument), expected, argument)

    def test_the_shim_is_plain_date_without_a_stub_state(self):
        (self.state_dir / "state.json").unlink()
        self.assertNear(self.run_date("-u", "+%s"), self.now)
        self.assertEqual(self.run_date("-u", "-d", "@0", "+%Y"), "1970")


# ----------------------------------------------------------------------------- virtual time: the sleep shim

def run_shim(install, state_dir, *argv, state=True):
    """Run one shim ``install`` puts in ``state_dir/bin``, with the stub state reachable unless ``state`` is false;
    return the completed process and its real duration in seconds."""
    shim = install(Path(state_dir) / "bin")
    env = {k: v for k, v in os.environ.items() if k != "GH_STUB_STATE_DIR"}
    if state:
        env["GH_STUB_STATE_DIR"] = str(state_dir)
    started = time.monotonic()
    done = subprocess.run([str(shim), *argv], capture_output=True, text=True, env=env)
    return done, time.monotonic() - started


class SleepShimTest(StubCase):
    def sleep(self, *argv, state=True):
        return run_shim(gh_stub.install_sleep_shim, self.state_dir, *argv, state=state)

    def assertNear(self, moment, expected, seconds=5):
        self.assertLess(abs((moment - expected).total_seconds()), seconds, (moment, expected))

    def test_sleep_moves_the_stub_clock_instead_of_waiting(self):
        done, elapsed = self.sleep("600")
        self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""))
        self.assertLess(elapsed, 3)
        self.assertEqual(self.state()["_clock_offset"], 600)
        done, elapsed = self.sleep("1.5", "2m", ".5h", "1d")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertLess(elapsed, 3)
        total = 600 + 1.5 + 120 + 1800 + 86400
        self.assertEqual(self.state()["_clock_offset"], total)
        self.assertNear(gh_stub.current_time(self.state_dir), self.now + dt.timedelta(seconds=total))
        self.ok("pr", "comment", "84", "--body", "Back after a day.")
        self.assertNear(parse_time(self.log()[-1]["clock"]), self.now + dt.timedelta(seconds=total))

    def test_infinity_is_refused_and_anything_else_runs_the_real_sleep(self):
        done, elapsed = self.sleep("infinity")
        self.assertEqual(done.returncode, 1)
        self.assertIn("infinity", done.stderr)
        self.assertLess(elapsed, 3)
        done, _ = self.sleep("--version")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue(done.stdout.startswith("sleep"), done.stdout)
        done, elapsed = self.sleep("1", state=False)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertGreaterEqual(elapsed, 1)
        self.assertEqual(self.state()["_clock_offset"], 0)

    def test_the_grammar_is_gnu_durations_summed(self):
        for argv, seconds in ((["90"], 90), (["1.5"], 1.5), ([".5"], 0.5), (["2."], 2), (["2m"], 120),
                              (["1h"], 3600), (["1d"], 86400), (["1m", "30s"], 90), (["0"], 0)):
            self.assertEqual(gh_stub.sleep_seconds(argv), seconds, argv)
        for argv in ([], ["-5"], ["soon"], ["1w"], ["--help"], ["1e3"], ["+5"], ["5", "x"], ["--", "5"],
                     ["infinity", "--help"]):
            self.assertIsNone(gh_stub.sleep_seconds(argv), argv)
        for argv in (["infinity"], ["INF"], ["infm"], ["5", "Infinity"]):
            with self.assertRaises(ValueError, msg=argv):
                gh_stub.sleep_seconds(argv)


# ----------------------------------------------------------------------------- virtual time: delayed responses

class DelayedResponseTest(StubCase):
    def extra_state(self):
        return {"on_write": [
            {"match": {"kind": "issue-comment", "body_contains": "@coderabbitai review"}, "delay": 90, "once": True,
             "append": {"reviews": [{"author": {"login": "coderabbitai"}, "state": "COMMENTED",
                                     "body": "Reviewed {{head}} at {{now}}."}]}},
            {"match": {"kind": "issue-comment", "body_contains": "ping"}, "delay": "1s",
             "append": {"issue_comments": [{"author": {"login": "ana"}, "body": "pong"}]}}]}

    def assertNear(self, moment, expected, seconds=5):
        self.assertLess(abs((moment - expected).total_seconds()), seconds, (moment, expected))

    def bot_reviews(self):
        reviews = json.loads(self.ok("pr", "view", "84", "--json", "reviews"))["reviews"]
        return [r for r in reviews if r["author"]["login"] == "coderabbitai"]

    def pongs(self):
        return [c for c in self.state()["issue_comments"] if c["body"] == "pong"]

    def test_a_delayed_review_lands_once_sleep_moves_the_clock_past_its_due_time(self):
        self.ok("pr", "comment", "84", "--body", "@coderabbitai review")
        self.assertEqual(self.bot_reviews(), [])
        self.ok("pr", "comment", "84", "--body", "@coderabbitai review")
        done, _ = run_shim(gh_stub.install_sleep_shim, self.state_dir, "120")
        self.assertEqual(done.returncode, 0, done.stderr)
        [review] = self.bot_reviews()
        self.assertNear(parse_time(review["submittedAt"]), self.now + dt.timedelta(seconds=90))
        self.assertEqual(review["body"], f"Reviewed {HEAD} at {review['submittedAt']}.")
        done, _ = run_shim(gh_stub.install_date_shim, self.state_dir, "-u", "+%s")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertNear(dt.datetime.fromtimestamp(int(done.stdout), dt.timezone.utc),
                        self.now + dt.timedelta(seconds=120))

    def test_a_delayed_review_lands_during_a_python_time_sleep(self):
        self.ok("pr", "comment", "84", "--body", "@coderabbitai review")
        done, _ = run_python(self.state_dir, "import time; time.sleep(120)")
        self.assertEqual(done.returncode, 0, done.stderr)
        state = self.state()  # read directly, so nothing but the sleep can have applied the review
        self.assertEqual((state["_clock_offset"], state["_pending"]), (120, []))
        [review] = [r for r in state["reviews"] if r["author"]["login"] == "coderabbitai"]
        self.assertNear(parse_time(review["submittedAt"]), self.now + dt.timedelta(seconds=90))

    def test_any_later_stub_call_or_date_applies_what_came_due_on_the_wall_clock(self):
        self.ok("pr", "comment", "84", "--body", "ping")
        time.sleep(1.2)
        self.assertEqual(self.pongs(), [])
        comments = json.loads(self.ok("pr", "view", "84", "--json", "comments"))["comments"]
        self.assertEqual([c["body"] for c in comments][-1], "pong")
        self.ok("pr", "comment", "84", "--body", "ping again")
        time.sleep(1.2)
        self.assertEqual(len(self.pongs()), 1)
        done, _ = run_shim(gh_stub.install_date_shim, self.state_dir, "-u", "+%s")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(len(self.pongs()), 2)

    def test_a_delay_is_seconds_or_units_and_initialization_refuses_anything_else(self):
        for bad in ("soon", -5, "1w", "90 seconds"):
            hooks = [{"match": {"kind": "issue-comment"}, "delay": bad, "append": {}}]
            with self.assertRaises(ValueError, msg=repr(bad)):
                gh_stub.initialize(self.state_dir / "bad", self.render(dict(github(), on_write=hooks)),
                                   head=HEAD, base=BASE)


# ----------------------------------------------------------------------------- virtual time: Python's clock

def run_python(state_dir, program, *, state=True, python_path=()):
    """Run ``program`` in a child Python whose ``PYTHONPATH`` is the directory holding the ``sitecustomize``
    :func:`stub_clock.install` writes in ``state_dir/python``, then ``python_path``, with the stub state reachable
    unless ``state`` is false; return the completed process and its real duration in seconds."""
    loader = stub_clock.install(Path(state_dir) / "python")
    env = {k: v for k, v in os.environ.items() if k not in ("GH_STUB_STATE_DIR", "PYTHONPATH")}
    env["PYTHONPATH"] = os.pathsep.join([str(loader.parent), *(str(p) for p in python_path)])
    if state:
        env["GH_STUB_STATE_DIR"] = str(state_dir)
    started = time.monotonic()
    done = subprocess.run([sys.executable, "-c", program], capture_output=True, text=True, env=env)
    return done, time.monotonic() - started


CLOCK_PROBE = """
import calendar, datetime, json, time
started, counter = time.monotonic(), time.perf_counter()
before = time.time()
time.sleep(600)
print(json.dumps({
    "before": before, "after": time.time(), "after_ns": time.time_ns(),
    "now_utc": datetime.datetime.now(datetime.timezone.utc).timestamp(),
    "now_local": datetime.datetime.now().timestamp(), "today": datetime.datetime.today().timestamp(),
    "utcnow": datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).timestamp(),
    "date": datetime.date.today().isoformat(),
    "gmtime": calendar.timegm(time.gmtime()), "localtime": time.mktime(time.localtime()),
    "ctime": time.ctime(), "strftime": time.strftime("%Y-%m-%d %H:%M"),
    "monotonic": time.monotonic() - started, "perf_counter": time.perf_counter() - counter}))
"""

# The probe unpickles only what it pickled itself, to show the swapped classes and functions round-trip.
DATETIME_PROBE = """
import datetime, json, pickle, time
zone = datetime.timezone(datetime.timedelta(hours=-4), "EDT")
now = datetime.datetime.now(zone)
class Mine(datetime.datetime):
    pass
print(json.dumps({
    "zone": now.tzinfo is zone and now.utcoffset() == datetime.timedelta(hours=-4),
    "instant": abs(now.timestamp() - time.time()) < 2,
    "types": isinstance(now, datetime.datetime) and isinstance(now, datetime.date)
             and issubclass(datetime.datetime, datetime.date),
    "real values": isinstance(datetime.datetime.min, datetime.datetime)
                   and isinstance(datetime.date.min, datetime.date),
    "a date is no datetime": not isinstance(datetime.date.today(), datetime.datetime),
    "subclasses": isinstance(Mine(2020, 1, 2), datetime.datetime)
                  and not isinstance(datetime.datetime(2020, 1, 2), Mine),
    "pickles": pickle.loads(pickle.dumps(now)) == now and pickle.loads(pickle.dumps(time.sleep)) is time.sleep,
    "no instance dict": not hasattr(now, "__dict__"),
    "repr": [repr(datetime.datetime(2020, 1, 2, 3, 4)), repr(datetime.date(2020, 1, 2)), repr(datetime.datetime)],
    "patched": [type(time.time).__name__, datetime.datetime.__bases__[0].__name__]}))
"""

INERT_PROBE = """
import datetime, json, time
started = time.monotonic()
time.sleep(0.3)
print(json.dumps({"time": time.time(), "slept": time.monotonic() - started,
                  "patched": [type(time.time).__name__, datetime.datetime.__bases__[0].__name__]}))
"""


class PythonClockTest(StubCase):
    """A child's Python tells time by the stub's clock through the ``sitecustomize`` hook; the stub never does."""

    def assertNear(self, value, expected, seconds=5):
        self.assertLess(abs(value - expected), seconds, (value, expected))

    def probe(self, program, **options):
        done, elapsed = run_python(self.state_dir, program, **options)
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout), elapsed

    def test_time_sleep_moves_the_stub_clock_and_every_reading_follows_it(self):
        result, elapsed = self.probe(CLOCK_PROBE)
        wall = time.time()
        self.assertLess(elapsed, 3)
        self.assertLess(result["monotonic"], 1)
        self.assertLess(result["perf_counter"], 1)
        self.assertEqual(json.loads((self.state_dir / "state.json").read_text())["_clock_offset"], 600)
        after = result["after"]
        self.assertNear(after - result["before"], 600)
        self.assertNear(after, wall + 600)
        for key in ("now_utc", "now_local", "today", "utcnow", "gmtime", "localtime"):
            self.assertNear(result[key], after, 2)
        self.assertNear(result["after_ns"] / 1e9, after, 1)
        moments = (after, after + 1)
        self.assertIn(result["date"], {dt.date.fromtimestamp(t).isoformat() for t in moments})
        self.assertIn(result["ctime"], {time.ctime(t) for t in moments})
        self.assertIn(result["strftime"], {time.strftime("%Y-%m-%d %H:%M", time.localtime(t)) for t in moments})

    def test_the_swapped_datetime_classes_keep_zones_types_pickling_and_repr(self):
        result, _ = self.probe(DATETIME_PROBE)
        self.assertEqual(result.pop("repr"), ["datetime.datetime(2020, 1, 2, 3, 4)", "datetime.date(2020, 1, 2)",
                                              "<class 'datetime.datetime'>"])
        self.assertEqual(result.pop("patched"), ["function", "datetime"])
        self.assertEqual(result, dict.fromkeys(result, True))

    def test_the_hook_is_inert_where_no_stub_state_is_reachable(self):
        result, _ = self.probe(INERT_PROBE, state=False)
        self.assertEqual(result["patched"], ["builtin_function_or_method", "date"])
        self.assertGreaterEqual(result["slept"], 0.3)
        self.assertNear(result["time"], time.time())
        self.assertEqual(self.state()["_clock_offset"], 0)
        (self.state_dir / "state.json").unlink()
        result, _ = self.probe(INERT_PROBE)
        self.assertEqual(result["patched"], ["builtin_function_or_method", "date"])
        self.assertGreaterEqual(result["slept"], 0.3)

    def test_a_sitecustomize_later_on_the_path_still_runs(self):
        other = self.state_dir / "other"
        other.mkdir()
        (other / "sitecustomize.py").write_text("import builtins\nbuiltins.shadowed_ran = True\n")
        program = "import builtins, time; print(getattr(builtins, 'shadowed_ran', False), type(time.time).__name__)"
        for state, patched in ((True, "function"), (False, "builtin_function_or_method")):
            done, _ = run_python(self.state_dir, program, state=state, python_path=[other])
            self.assertEqual((done.returncode, done.stdout.split()), (0, ["True", patched]), done.stderr)

    def test_the_stub_and_its_shims_never_load_the_hook(self):
        loader = stub_clock.install(self.state_dir / "python")
        bin_dir = self.state_dir / "bin"
        programs = [gh_stub.install(bin_dir), *gh_stub.install_model_shims(bin_dir),
                    gh_stub.install_date_shim(bin_dir), gh_stub.install_sleep_shim(bin_dir),
                    gh_stub.install_post_receive(self.state_dir / "origin.git", self.state_dir)]
        for program in programs:
            command = shlex.split(program.read_text().splitlines()[1])
            self.assertEqual(command[:3], ["exec", sys.executable, "-S"], program)
        gh_stub.advance_clock(self.state_dir, 600)
        env = dict(os.environ, GH_STUB_STATE_DIR=str(self.state_dir), PYTHONPATH=str(loader.parent))
        started = time.time()
        for argv in (["gh", "pr", "comment", "84", "--body", "Checked."], ["claude", "-p", "hello"]):
            subprocess.run([str(bin_dir / argv[0]), *argv[1:]], stdin=subprocess.DEVNULL, capture_output=True,
                           env=env)
        date = subprocess.run([str(bin_dir / "date"), "-u", "+%s"], capture_output=True, text=True, env=env)
        finished = time.time()
        self.assertEqual(subprocess.run([str(bin_dir / "sleep"), "30"], env=env).returncode, 0)
        comment, refused = self.log()
        for record in (comment, refused):
            logged = parse_time(record["ts"]).timestamp()
            self.assertTrue(started - 2 <= logged <= finished + 2, (record["ts"], started, finished))
            self.assertNear(parse_time(record["clock"]).timestamp(), logged + 600, 3)
        self.assertEqual(refused["writes"][0]["kind"], gh_stub.NESTED_RUN_KIND)
        self.assertNear(int(date.stdout), started + 600)
        self.assertEqual(self.state()["_clock_offset"], 630)


if __name__ == "__main__":
    unittest.main()
