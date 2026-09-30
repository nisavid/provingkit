#!/usr/bin/env python3
"""Re-request one bound reviewer's review once and verify it by reread.

A review request made at or after the notice reply (``--notice-at``), whether
still pending or since removed, already counts as that request: no write.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PUBLISHER_SCRIPTS = (
    Path(__file__).resolve().parents[2] / "publishing-reviewable-prs" / "scripts"
)
sys.path.insert(0, str(PUBLISHER_SCRIPTS))

from reviewable_pr_state import (  # noqa: E402
    GITHUB_HOST,
    OID_RE,
    REPOSITORY_RE,
    MutationAmbiguousError,
    PublicationError,
    StateReadError,
    run_mutation as _run_mutation,
    run_read as _run_read,
    stored_pr as _stored_pr,
    strict_json,
)

OPERATION = "reviewer-rerequest"
SCHEMA_VERSION = 1
LOGIN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}")
REVIEW_ID_RE = re.compile(r"PRR_[A-Za-z0-9_-]+")
GRAPHQL = ["gh", "api", "--hostname", GITHUB_HOST, "graphql", "--input", "-"]
REVIEW_QUERY = (
    "query($owner:String!,$name:String!,$number:Int!,$reviewer:String!)"
    "{repository(owner:$owner,name:$name){pullRequest(number:$number)"
    "{url headRefOid author{login} "
    "reviewRequests(first:100){pageInfo{hasNextPage} "
    "nodes{requestedReviewer{__typename ... on User{login}}}} "
    "reviews(last:1,author:$reviewer)"
    "{nodes{id state submittedAt author{__typename login}}} "
    "timelineItems(last:100,itemTypes:[REVIEW_REQUESTED_EVENT])"
    "{nodes{... on ReviewRequestedEvent{createdAt "
    "requestedReviewer{__typename ... on User{login}}}}}}}}"
)


class _UsageError(Exception):
    """Invalid command-line arguments, reported as a blocked result."""


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        raise _UsageError(message)


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _path(value: Any, *keys: str) -> Any:
    for key in keys:
        value = value.get(key) if isinstance(value, dict) else None
    return value


def _active_login() -> str:
    result = _run_read(
        ["gh", "api", "--hostname", GITHUB_HOST, "--method", "GET", "user"]
    )
    value = strict_json(result.stdout, "authenticated login response")
    login = value.get("login") if isinstance(value, dict) else None
    if not isinstance(login, str) or not login:
        raise PublicationError("active authenticated login is unavailable")
    return login


def _pr_matches(stored: Any, url: str, pr_number: int, head_oid: str) -> bool:
    return (
        isinstance(stored, dict)
        and type(stored.get("number")) is int
        and stored.get("number") == pr_number
        and stored.get("url") == url
        and stored.get("state") == "OPEN"
        and stored.get("headRefOid") == head_oid
    )


def _lists_user(users: Any, login: str) -> bool:
    return isinstance(users, list) and any(
        _path(user, "login") == login for user in users
    )


def _instant(value: Any) -> datetime | None:
    """Parse an ISO 8601 timestamp that carries a UTC offset; None otherwise."""
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _requested_since(events: list[Any], reviewer: str, notice: datetime) -> bool | None:
    """True when a review_requested event names the reviewer at or after notice.

    None marks an event for the reviewer whose timestamp cannot be read.
    """
    found = False
    for event in events:
        requested = _path(event, "requestedReviewer")
        if not (
            _path(requested, "__typename") == "User"
            and _path(requested, "login") == reviewer
        ):
            continue
        created = _instant(_path(event, "createdAt"))
        if created is None:
            return None
        if created >= notice:
            found = True
    return found


def _read_review_state(repository: str, pr_number: int, reviewer: str) -> Any:
    owner, name = repository.split("/", 1)
    variables = {
        "owner": owner,
        "name": name,
        "number": pr_number,
        "reviewer": reviewer,
    }
    document = {"query": REVIEW_QUERY, "variables": variables}
    result = _run_read(GRAPHQL, input_text=canonical_json(document))
    value = strict_json(result.stdout, "review state read")
    if (
        not isinstance(value, dict)
        or value.get("errors")
        or not isinstance(value.get("data"), dict)
    ):
        raise StateReadError("review state read did not return complete data")
    return value["data"]


def _review_facts(
    data: Any, *, url: str, reviewer: str, notice_at: str | None = None
) -> dict[str, Any] | None:
    """Return the bound PR's live review facts, or None for any other PR."""
    pull_request = _path(data, "repository", "pullRequest")
    author = _path(pull_request, "author")
    requests = _path(pull_request, "reviewRequests", "nodes")
    more = _path(pull_request, "reviewRequests", "pageInfo", "hasNextPage")
    reviews = _path(pull_request, "reviews", "nodes")
    events = _path(pull_request, "timelineItems", "nodes")
    notice = _instant(notice_at) if notice_at is not None else None
    if not (
        _path(pull_request, "url") == url
        and isinstance(_path(pull_request, "headRefOid"), str)
        and (author is None or isinstance(_path(author, "login"), str))
        and isinstance(requests, list)
        and isinstance(more, bool)
        and isinstance(reviews, list)
        and len(reviews) <= 1
        and all(isinstance(review, dict) for review in reviews)
        and (
            (events is None and notice is None)
            or (isinstance(events, list) and all(isinstance(e, dict) for e in events))
        )
    ):
        return None
    since = None
    if notice is not None:
        since = _requested_since(events, reviewer, notice)
        if since is None:
            return None
    review = reviews[0] if reviews else {}
    return {
        "head_oid": pull_request["headRefOid"],
        "author": _path(author, "login"),
        "requested": any(
            _path(request, "requestedReviewer", "__typename") == "User"
            and _path(request, "requestedReviewer", "login") == reviewer
            for request in requests
        ),
        "requested_since_notice": since,
        "requests_complete": not more,
        "latest_review_id": review.get("id"),
        "latest_review_state": review.get("state"),
        "latest_review_submitted_at": review.get("submittedAt"),
        "latest_review_author": _path(review, "author", "login"),
        "latest_review_author_type": _path(review, "author", "__typename"),
    }


def _requested(repository: str, pr_number: int, reviewer: str) -> bool:
    result = _run_read(
        [
            "gh",
            "api",
            "--hostname",
            GITHUB_HOST,
            "--method",
            "GET",
            f"repos/{repository}/pulls/{pr_number}/requested_reviewers",
        ]
    )
    users = _path(strict_json(result.stdout, "requested reviewers read"), "users")
    if not isinstance(users, list):
        raise StateReadError("requested reviewers read returned an unexpected value")
    return _lists_user(users, reviewer)


def _invalid_input(
    repository: Any,
    pr_number: Any,
    head_oid: Any,
    reviewer: Any,
    expected_review_id: Any,
    expected_authenticated_login: Any,
    notice_at: Any,
) -> str | None:
    if not isinstance(repository, str) or not REPOSITORY_RE.fullmatch(repository):
        return "repository must use OWNER/REPO"
    if type(pr_number) is not int or pr_number <= 0:
        return "PR number must be positive"
    if not isinstance(head_oid, str) or not OID_RE.fullmatch(head_oid):
        return "head OID must be a lowercase 40-digit hex OID"
    if not isinstance(reviewer, str) or not LOGIN_RE.fullmatch(reviewer):
        return "reviewer must be one user login, not a team or bot login"
    if not isinstance(expected_review_id, str) or not REVIEW_ID_RE.fullmatch(
        expected_review_id
    ):
        return "expected review ID must be a PRR_ review node ID"
    if not isinstance(expected_authenticated_login, str) or not (
        expected_authenticated_login
    ):
        return "expected authenticated login must be non-empty"
    if notice_at is not None and _instant(notice_at) is None:
        return (
            "notice time must be an ISO 8601 timestamp with a UTC offset, "
            "such as 2026-09-29T21:47:00Z"
        )
    return None


def request_rereview(
    *,
    repository: str,
    pr_number: int,
    head_oid: str,
    reviewer: str,
    expected_review_id: str,
    expected_authenticated_login: str,
    notice_at: str | None = None,
) -> dict[str, Any]:
    """Check the binding, request at most once, and verify by reread; never retry."""
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "operation": OPERATION,
        "repository": repository,
        "pr_number": pr_number,
        "head_oid": head_oid,
        "reviewer": reviewer,
        "expected_review_id": expected_review_id,
        "expected_authenticated_login": expected_authenticated_login,
        "notice_at": notice_at,
        "status": "blocked",
        "reason": "",
        "mutation_attempted": False,
        "live": None,
        "refusal": None,
    }

    def finish(status: str, reason: str) -> dict[str, Any]:
        result.update(status=status, reason=reason)
        return result

    invalid = _invalid_input(
        repository,
        pr_number,
        head_oid,
        reviewer,
        expected_review_id,
        expected_authenticated_login,
        notice_at,
    )
    if invalid is not None:
        return finish("blocked", invalid)
    url = f"https://github.com/{repository}/pull/{pr_number}"
    try:
        if _active_login() != expected_authenticated_login:
            return finish(
                "blocked", "active authenticated login does not match authority"
            )
        if not _pr_matches(_stored_pr(repository, pr_number), url, pr_number, head_oid):
            return finish("blocked", "PR is not open at the bound URL and head")
        facts = _review_facts(
            _read_review_state(repository, pr_number, reviewer),
            url=url,
            reviewer=reviewer,
            notice_at=notice_at,
        )
    except (PublicationError, OSError) as error:
        return finish("blocked", f"live state read failed before the request: {error}")
    if facts is None:
        return finish("blocked", "review state does not belong to the bound PR")
    result["live"] = facts
    if facts["head_oid"] != head_oid:
        return finish("blocked", "PR head changed before the request")
    if reviewer in (facts["author"], expected_authenticated_login):
        return finish("blocked", "reviewer is the PR author or the active login")
    if facts["latest_review_id"] is not None and (
        facts["latest_review_author_type"] != "User"
        or facts["latest_review_author"] != reviewer
    ):
        return finish("blocked", "reviewer is not a user who reviewed this PR")
    if (
        facts["latest_review_id"] is None
        or facts["latest_review_state"] == "PENDING"
        or not isinstance(facts["latest_review_submitted_at"], str)
    ):
        return finish("blocked", "reviewer has no submitted review on this PR")
    if facts["latest_review_id"] != expected_review_id:
        return finish("blocked", "reviewer's latest review is not the expected review")
    if not facts["requests_complete"]:
        return finish("blocked", "review requests span more than one page")
    if facts["requested"]:
        return finish("verified", "reviewer is already requested; no write")
    if facts["requested_since_notice"]:
        return finish(
            "verified", "reviewer was requested at or after the notice; no write"
        )

    result["mutation_attempted"] = True
    try:
        # REST adds to the pending requests; GraphQL requestReviews replaces them
        # unless union is set.
        response = _run_mutation(
            [
                "gh",
                "api",
                "--hostname",
                GITHUB_HOST,
                "--method",
                "POST",
                f"repos/{repository}/pulls/{pr_number}/requested_reviewers",
                "--input",
                "-",
            ],
            input_text=canonical_json({"reviewers": [reviewer]}),
        )
    except MutationAmbiguousError:
        return finish("unknown", "request timed out; reread live state first")
    except (PublicationError, OSError) as error:
        # A failed call may still have landed: only a reread can tell.
        result["refusal"] = str(error)
        try:
            requested = _requested(repository, pr_number, reviewer)
        except (PublicationError, OSError):
            return finish("unknown", "request failed and the reviewers reread failed")
        facts["requested"] = requested
        if requested:
            return finish("unknown", "request failed yet the reviewer is requested")
        return finish("blocked", "request was refused; the reviewer is not requested")
    try:
        receipt = strict_json(response.stdout, "review request response")
    except PublicationError:
        receipt = None
    number = _path(receipt, "number")
    if not (
        type(number) is int
        and number == pr_number
        and _path(receipt, "html_url") == url
        and _path(receipt, "head", "sha") == head_oid
        and _lists_user(_path(receipt, "requested_reviewers"), reviewer)
    ):
        return finish("unknown", "request returned no trustworthy receipt")
    try:
        requested = _requested(repository, pr_number, reviewer)
    except (PublicationError, OSError):
        return finish("unknown", "requested reviewers reread failed after the request")
    facts["requested"] = requested
    if not requested:
        return finish("unknown", "reviewers reread does not list the reviewer")
    try:
        after = _stored_pr(repository, pr_number)
    except (PublicationError, OSError):
        return finish("unknown", "PR reread failed after the request")
    if not _pr_matches(after, url, pr_number, head_oid):
        return finish("unknown", "PR identity or head changed after the request")
    return finish("verified", "requested once and verified by reread")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--head-oid", required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--expected-review-id", required=True)
    parser.add_argument("--expected-authenticated-login", required=True)
    parser.add_argument(
        "--notice-at",
        help="notice reply timestamp; a review request at or after it counts",
    )
    try:
        args = parser.parse_args(argv)
    except _UsageError as error:
        result = {
            "schema_version": SCHEMA_VERSION,
            "operation": OPERATION,
            "status": "blocked",
            "reason": f"invalid arguments: {error}",
        }
    else:
        result = request_rereview(
            repository=args.repository,
            pr_number=args.pr,
            head_oid=args.head_oid,
            reviewer=args.reviewer,
            expected_review_id=args.expected_review_id,
            expected_authenticated_login=args.expected_authenticated_login,
            notice_at=args.notice_at,
        )
    print(canonical_json(result))
    return {"verified": 0, "unknown": 2}.get(result["status"], 1)


if __name__ == "__main__":
    raise SystemExit(main())
