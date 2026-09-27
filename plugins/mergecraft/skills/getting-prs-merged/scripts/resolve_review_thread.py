#!/usr/bin/env python3
"""Resolve one bound review thread once and verify the resolution by reread."""

from __future__ import annotations

import argparse
import json
import re
import sys
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

OPERATION = "github:review-thread-resolution"
SCHEMA_VERSION = 1
THREAD_ID_RE = re.compile(r"PRRT_[A-Za-z0-9_-]+")
COMMENT_ID_RE = re.compile(r"PRRC_[A-Za-z0-9_-]+")
GRAPHQL = ["gh", "api", "--hostname", GITHUB_HOST, "graphql", "--input", "-"]
THREAD_QUERY = (
    "query($thread:ID!){node(id:$thread){__typename "
    "... on PullRequestReviewThread{id isResolved viewerCanResolve "
    "resolvedBy{login} repository{nameWithOwner} "
    "pullRequest{number url headRefOid} comments(last:1){nodes{id}}}}}"
)
RESOLVE_MUTATION = (
    "mutation($thread:ID!){resolveReviewThread(input:{threadId:$thread})"
    "{thread{id isResolved resolvedBy{login}}}}"
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


def _graphql_data(output: str, source: str) -> dict[str, Any]:
    value = strict_json(output, source)
    if (
        not isinstance(value, dict)
        or value.get("errors")
        or not isinstance(value.get("data"), dict)
    ):
        raise StateReadError(f"{source} did not return complete data")
    return value["data"]


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


def _read_thread(thread_id: str) -> Any:
    document = {"query": THREAD_QUERY, "variables": {"thread": thread_id}}
    result = _run_read(GRAPHQL, input_text=canonical_json(document))
    return _graphql_data(result.stdout, "review thread read").get("node")


def _thread_facts(
    node: Any, *, thread_id: str, repository: str, url: str, pr_number: int
) -> dict[str, Any] | None:
    """Return the live facts of the bound thread, or None for any other node."""
    number = _path(node, "pullRequest", "number")
    comments = _path(node, "comments", "nodes")
    resolved_by = _path(node, "resolvedBy")
    if not (
        _path(node, "__typename") == "PullRequestReviewThread"
        and _path(node, "id") == thread_id
        and _path(node, "repository", "nameWithOwner") == repository
        and type(number) is int
        and number == pr_number
        and _path(node, "pullRequest", "url") == url
        and isinstance(_path(node, "pullRequest", "headRefOid"), str)
        and isinstance(_path(node, "isResolved"), bool)
        and isinstance(_path(node, "viewerCanResolve"), bool)
        and (resolved_by is None or isinstance(_path(resolved_by, "login"), str))
        and isinstance(comments, list)
        and len(comments) == 1
        and isinstance(_path(comments[0], "id"), str)
    ):
        return None
    return {
        "head_oid": node["pullRequest"]["headRefOid"],
        "is_resolved": node["isResolved"],
        "resolved_by": _path(resolved_by, "login"),
        "viewer_can_resolve": node["viewerCanResolve"],
        "last_comment_id": comments[0]["id"],
    }


def _invalid_input(
    repository: Any,
    pr_number: Any,
    head_oid: Any,
    thread_id: Any,
    expected_last_comment_id: Any,
    expected_authenticated_login: Any,
) -> str | None:
    if not isinstance(repository, str) or not REPOSITORY_RE.fullmatch(repository):
        return "repository must use OWNER/REPO"
    if type(pr_number) is not int or pr_number <= 0:
        return "PR number must be positive"
    if not isinstance(head_oid, str) or not OID_RE.fullmatch(head_oid):
        return "head OID must be a lowercase 40-digit hex OID"
    if not isinstance(thread_id, str) or not THREAD_ID_RE.fullmatch(thread_id):
        return "thread ID must be a PRRT_ review-thread node ID"
    if not isinstance(expected_last_comment_id, str) or not COMMENT_ID_RE.fullmatch(
        expected_last_comment_id
    ):
        return "expected last comment ID must be a PRRC_ review-comment node ID"
    if not isinstance(expected_authenticated_login, str) or not (
        expected_authenticated_login
    ):
        return "expected authenticated login must be non-empty"
    return None


def resolve_thread(
    *,
    repository: str,
    pr_number: int,
    head_oid: str,
    thread_id: str,
    expected_last_comment_id: str,
    expected_authenticated_login: str,
) -> dict[str, Any]:
    """Check the binding, resolve at most once, and verify by reread; never retry."""
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "operation": OPERATION,
        "repository": repository,
        "pr_number": pr_number,
        "head_oid": head_oid,
        "thread_id": thread_id,
        "expected_last_comment_id": expected_last_comment_id,
        "expected_authenticated_login": expected_authenticated_login,
        "status": "blocked",
        "reason": "",
        "mutation_attempted": False,
        "live": None,
        "reraised_comment_id": None,
        "refusal": None,
    }

    def finish(status: str, reason: str) -> dict[str, Any]:
        result.update(status=status, reason=reason)
        return result

    invalid = _invalid_input(
        repository,
        pr_number,
        head_oid,
        thread_id,
        expected_last_comment_id,
        expected_authenticated_login,
    )
    if invalid is not None:
        return finish("blocked", invalid)
    url = f"https://github.com/{repository}/pull/{pr_number}"
    bound = {
        "thread_id": thread_id,
        "repository": repository,
        "url": url,
        "pr_number": pr_number,
    }
    try:
        if _active_login() != expected_authenticated_login:
            return finish(
                "blocked", "active authenticated login does not match authority"
            )
        if not _pr_matches(_stored_pr(repository, pr_number), url, pr_number, head_oid):
            return finish("blocked", "PR is not open at the bound URL and head")
        facts = _thread_facts(_read_thread(thread_id), **bound)
    except (PublicationError, OSError) as error:
        return finish("blocked", f"live state read failed before resolution: {error}")
    if facts is None:
        return finish("blocked", "thread is not the bound thread on the bound PR")
    result["live"] = facts
    if facts["head_oid"] != head_oid:
        return finish("blocked", "PR head changed before resolution")
    if facts["last_comment_id"] != expected_last_comment_id:
        result["reraised_comment_id"] = facts["last_comment_id"]
        return finish("blocked", "a newer comment reraised the thread")
    if facts["is_resolved"]:
        return finish("verified", "thread was already resolved; no write")
    if not facts["viewer_can_resolve"]:
        return finish("blocked", "active login cannot resolve this thread")

    result["mutation_attempted"] = True
    document = {"query": RESOLVE_MUTATION, "variables": {"thread": thread_id}}
    try:
        response = _run_mutation(GRAPHQL, input_text=canonical_json(document))
    except MutationAmbiguousError:
        return finish("unknown", "resolution timed out; reread live state first")
    except (PublicationError, OSError) as error:
        # A failed call may still have landed: only a reread can tell.
        result["refusal"] = str(error)
        try:
            facts = _thread_facts(_read_thread(thread_id), **bound)
        except (PublicationError, OSError):
            facts = None
        if facts is None:
            return finish("unknown", "resolution failed and the thread reread failed")
        result["live"] = facts
        if facts["is_resolved"]:
            return finish("unknown", "resolution failed yet the thread is resolved")
        return finish("blocked", "resolution was refused; the thread is unresolved")
    try:
        data = _graphql_data(response.stdout, "resolution response")
    except PublicationError:
        data = None
    thread = _path(data, "resolveReviewThread", "thread")
    if not (
        _path(thread, "id") == thread_id
        and _path(thread, "isResolved") is True
        and _path(thread, "resolvedBy", "login") == expected_authenticated_login
    ):
        return finish("unknown", "resolution returned no trustworthy receipt")
    try:
        facts = _thread_facts(_read_thread(thread_id), **bound)
    except (PublicationError, OSError):
        return finish("unknown", "thread reread failed after resolution")
    if facts is None:
        return finish("unknown", "thread reread no longer shows the bound thread")
    result["live"] = facts
    if facts["head_oid"] != head_oid:
        return finish("unknown", "PR head changed after resolution")
    if not facts["is_resolved"] or facts["resolved_by"] != expected_authenticated_login:
        return finish("unknown", "thread reread does not show this resolution")
    if facts["last_comment_id"] != expected_last_comment_id:
        result["reraised_comment_id"] = facts["last_comment_id"]
    try:
        after = _stored_pr(repository, pr_number)
    except (PublicationError, OSError):
        return finish("unknown", "PR reread failed after resolution")
    if not _pr_matches(after, url, pr_number, head_oid):
        return finish("unknown", "PR identity or head changed after resolution")
    if result["reraised_comment_id"] is not None:
        return finish("verified", "resolved and verified; a newer comment reraised it")
    return finish("verified", "resolved once and verified by reread")


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--head-oid", required=True)
    parser.add_argument("--thread-id", required=True)
    parser.add_argument("--expected-last-comment-id", required=True)
    parser.add_argument("--expected-authenticated-login", required=True)
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
        result = resolve_thread(
            repository=args.repository,
            pr_number=args.pr,
            head_oid=args.head_oid,
            thread_id=args.thread_id,
            expected_last_comment_id=args.expected_last_comment_id,
            expected_authenticated_login=args.expected_authenticated_login,
        )
    print(canonical_json(result))
    return {"verified": 0, "unknown": 2}.get(result["status"], 1)


if __name__ == "__main__":
    raise SystemExit(main())
