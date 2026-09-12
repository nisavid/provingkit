#!/usr/bin/env python3
"""Fetch and summarize thread-aware GitHub PR review state."""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class FeedbackAcquisitionError(ValueError):
    """GitHub feedback could not be acquired as a complete, consistent snapshot."""


class GraphQLQueryError(FeedbackAcquisitionError):
    """GitHub returned one or more GraphQL errors."""


class ResponseShapeError(FeedbackAcquisitionError):
    """A requested GraphQL structure or node was missing or malformed."""


class PaginationError(FeedbackAcquisitionError):
    """A paginated connection was incomplete or did not progress."""


class IdentityError(ResponseShapeError):
    """Repository or pull-request identity was missing or changed."""


CONNECTION_KEYS = ("threads", "comments", "reviews", "checks", "review_requests")
GITHUB_HOST = "github.com"
READ_TIMEOUT_SECONDS = 30
MAX_TOP_LEVEL_PAGES = 10_000
MAX_THREAD_COMMENT_PAGES = 10_000


class AcquiredPageSequence(list[dict[str, Any]]):
    """Retain the cursors used by the real acquisition requests."""

    def __init__(self) -> None:
        super().__init__()
        self.collection_pages = {key: [] for key in CONNECTION_KEYS}
        self.hydrated_threads: dict[str, dict[str, Any]] = {}

    def pagination_evidence(self) -> dict[str, Any]:
        return {
            "complete": True,
            "collections": {
                key: {
                    "complete": True,
                    "node_count": sum(page["node_count"] for page in pages),
                    "pages": copy.deepcopy(pages),
                }
                for key, pages in self.collection_pages.items()
            },
            "hydrated_threads": copy.deepcopy(list(self.hydrated_threads.values())),
        }


ACQUISITION_FIELD_CONTRACT = {
    "Actor": ("login",),
    "Node": ("id",),
    "IssueComment": (
        "id",
        "databaseId",
        "author",
        "authorAssociation",
        "body",
        "createdAt",
        "updatedAt",
        "url",
    ),
    "PullRequestReview": (
        "id",
        "databaseId",
        "author",
        "authorAssociation",
        "state",
        "body",
        "createdAt",
        "submittedAt",
        "updatedAt",
        "url",
        "commit",
    ),
    "PullRequestReviewComment": (
        "id",
        "databaseId",
        "author",
        "authorAssociation",
        "body",
        "createdAt",
        "updatedAt",
        "url",
        "path",
        "line",
        "originalLine",
        "originalPosition",
        "originalStartLine",
        "outdated",
        "startLine",
        "subjectType",
        "state",
        "replyTo",
        "commit",
        "originalCommit",
        "pullRequestReview",
    ),
    "PullRequestReviewThread": (
        "id",
        "isResolved",
        "isOutdated",
        "path",
        "line",
        "diffSide",
        "originalLine",
        "originalStartLine",
        "startDiffSide",
        "startLine",
        "subjectType",
        "comments",
    ),
}

ACTOR_IDENTITY_FRAGMENT = """
fragment ActorIdentity on Actor {
  __typename
  login
  ... on Node { id }
}
""".strip()

ISSUE_COMMENT_EVIDENCE_FRAGMENT = """
fragment IssueCommentEvidence on IssueComment {
  id
  databaseId
  author { ...ActorIdentity }
  authorAssociation
  body
  createdAt
  updatedAt
  url
}
""".strip()

REVIEW_COMMENT_EVIDENCE_FRAGMENT = """
fragment ReviewCommentEvidence on PullRequestReviewComment {
  id
  databaseId
  author { ...ActorIdentity }
  authorAssociation
  body
  createdAt
  updatedAt
  url
  path
  line
  originalLine
  originalPosition
  originalStartLine
  outdated
  startLine
  subjectType
  state
  replyTo { id databaseId }
  commit { oid }
  originalCommit { oid }
  pullRequestReview { id databaseId }
}
""".strip()

REVIEW_EVIDENCE_FRAGMENT = """
fragment ReviewEvidence on PullRequestReview {
  id
  databaseId
  author { ...ActorIdentity }
  authorAssociation
  state
  body
  createdAt
  submittedAt
  updatedAt
  url
  commit { oid }
}
""".strip()

SOURCE_EVIDENCE_FRAGMENTS = (
    f"{ACTOR_IDENTITY_FRAGMENT}\n\n"
    f"{ISSUE_COMMENT_EVIDENCE_FRAGMENT}\n\n"
    f"{REVIEW_COMMENT_EVIDENCE_FRAGMENT}\n\n"
    f"{REVIEW_EVIDENCE_FRAGMENT}"
)


def strict_json(content: str, source: str) -> Any:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ResponseShapeError(
                    f"{source} contained duplicate JSON key: {key}"
                )
            value[key] = item
        return value

    def reject_constant(value: str) -> None:
        raise ResponseShapeError(f"{source} contained non-finite JSON value: {value}")

    try:
        return json.loads(
            content,
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
    except json.JSONDecodeError as error:
        raise ResponseShapeError(f"{source} was not valid JSON") from error


def build_pr_query(
    repo: str,
    pr_number: int,
    cursors: dict[str, str | None],
    include: dict[str, bool] | None = None,
) -> tuple[str, dict[str, Any]]:
    owner, name = split_repo(repo)
    include = include or {
        "threads": True,
        "comments": True,
        "reviews": True,
        "checks": True,
        "review_requests": True,
    }
    query = (
        """
query PrReviewState(
  $owner: String!
  $name: String!
  $prNumber: Int!
  $threadsCursor: String
  $commentsCursor: String
  $reviewsCursor: String
  $checksCursor: String
  $reviewRequestsCursor: String
  $includeThreads: Boolean!
  $includeComments: Boolean!
  $includeReviews: Boolean!
  $includeChecks: Boolean!
  $includeReviewRequests: Boolean!
) {
  repository(owner: $owner, name: $name) {
    id
    databaseId
    nameWithOwner
    owner { login }
    pullRequest(number: $prNumber) {
      id
      databaseId
      number
      url
      isDraft
      baseRefName
      headRefName
      baseRefOid
      headRefOid
      headRepository {
        nameWithOwner
        owner { login }
      }
      reviewDecision
      mergeStateStatus
      mergeable
      reviewThreads(first: 100, after: $threadsCursor) @include(if: $includeThreads) {
        nodes {
          id
          isResolved
          isOutdated
          path
          line
          diffSide
          originalLine
          originalStartLine
          startDiffSide
          startLine
          subjectType
          comments(first: 100) {
            nodes {
              ...ReviewCommentEvidence
            }
            pageInfo { hasNextPage endCursor }
          }
        }
        pageInfo { hasNextPage endCursor }
      }
      comments(first: 100, after: $commentsCursor) @include(if: $includeComments) {
        nodes {
          ...IssueCommentEvidence
        }
        pageInfo { hasNextPage endCursor }
      }
      reviews(first: 100, after: $reviewsCursor) @include(if: $includeReviews) {
        nodes {
          ...ReviewEvidence
        }
        pageInfo { hasNextPage endCursor }
      }
      reviewRequests(
        first: 100
        after: $reviewRequestsCursor
      ) @include(if: $includeReviewRequests) {
        nodes {
          requestedReviewer {
            __typename
            ... on User { login }
            ... on Team { slug }
          }
        }
        pageInfo { hasNextPage endCursor }
      }
      statusCheckRollup @include(if: $includeChecks) {
        contexts(first: 100, after: $checksCursor) {
          nodes {
            __typename
            ... on CheckRun {
              name
              status
              conclusion
            }
            ... on StatusContext {
              context
              state
            }
          }
          pageInfo { hasNextPage endCursor }
        }
      }
    }
  }
}
""".strip()
        + "\n\n"
        + SOURCE_EVIDENCE_FRAGMENTS
    )
    variables = {
        "owner": owner,
        "name": name,
        "prNumber": pr_number,
        "threadsCursor": cursors.get("threads"),
        "commentsCursor": cursors.get("comments"),
        "reviewsCursor": cursors.get("reviews"),
        "checksCursor": cursors.get("checks"),
        "reviewRequestsCursor": cursors.get("review_requests"),
        "includeThreads": bool(include.get("threads")),
        "includeComments": bool(include.get("comments")),
        "includeReviews": bool(include.get("reviews")),
        "includeChecks": bool(include.get("checks")),
        "includeReviewRequests": bool(include.get("review_requests")),
    }
    return query, variables


def split_repo(repo: str) -> tuple[str, str]:
    if re.fullmatch(r"[^/\s]+/[^/\s]+", repo) is None:
        raise ValueError("repo must be OWNER/REPO")
    owner, name = repo.split("/", 1)
    return owner, name


def validate_head_repository_identity(name_with_owner: str, owner: str) -> None:
    try:
        expected_owner, _ = split_repo(name_with_owner)
    except ValueError as error:
        raise IdentityError("head repository nameWithOwner was malformed") from error
    if owner != expected_owner:
        raise IdentityError("head repository owner does not match nameWithOwner")


def fetch_pages(repo: str, pr_number: int) -> list[dict[str, Any]]:
    pages = AcquiredPageSequence()
    cursors: dict[str, str | None] = {
        "threads": None,
        "comments": None,
        "reviews": None,
        "checks": None,
        "review_requests": None,
    }
    include = {key: True for key in cursors}
    expected_identity: dict[str, Any] | None = None
    seen_cursors = {key: set() for key in cursors}
    while True:
        if len(pages) >= MAX_TOP_LEVEL_PAGES:
            raise PaginationError(
                f"top-level pagination exceeded {MAX_TOP_LEVEL_PAGES} pages"
            )
        query, variables = build_pr_query(repo, pr_number, cursors, include=include)
        page = run_gh_graphql(query, variables)
        validate_pr_page(page, include, "paginated page")
        page_identity = pull_request_identity(page)
        if expected_identity is None:
            validate_requested_identity(repo, pr_number, page_identity)
            expected_identity = page_identity
        else:
            validate_matching_identity(
                expected_identity, page_identity, "paginated page"
            )
        pages.append(page)
        page_info = page_infos(page)
        pr = extract_pr(page)
        for key in CONNECTION_KEYS:
            if not include.get(key):
                continue
            connection = _pr_connection(pr, key, True, "retained pagination evidence")
            pages.collection_pages[key].append(
                {
                    "page_index": len(pages.collection_pages[key]),
                    "request_cursor": cursors[key],
                    "node_count": len(connection.get("nodes") or []),
                    "has_next_page": page_info[key].get("hasNextPage"),
                    "end_cursor": page_info[key].get("endCursor"),
                }
            )
        next_cursors = {
            key: next_cursor(key, page_info[key], cursors[key], seen_cursors[key])
            for key in cursors
        }
        if not any(next_cursors.values()):
            hydrate_thread_comments(pages, expected_identity)
            return pages
        include = {key: value is not None for key, value in next_cursors.items()}
        cursors = next_cursors


def hydrate_thread_comments(
    pages: list[dict[str, Any]], expected_identity: dict[str, Any]
) -> None:
    for page in pages:
        for thread in (extract_pr(page).get("reviewThreads") or {}).get("nodes") or []:
            comments = thread.get("comments") or {}
            page_info = comments.get("pageInfo") or {}
            seen_cursors: set[str] = set()
            cursor: str | None = None
            page_count = 0
            thread_pages = [
                {
                    "page_index": 0,
                    "request_cursor": None,
                    "node_count": len(comments.get("nodes") or []),
                    "has_next_page": page_info.get("hasNextPage"),
                    "end_cursor": page_info.get("endCursor"),
                }
            ]
            while page_info.get("hasNextPage"):
                if page_count >= MAX_THREAD_COMMENT_PAGES:
                    raise PaginationError(
                        "thread comments pagination exceeded "
                        f"{MAX_THREAD_COMMENT_PAGES} pages"
                    )
                cursor = next_cursor("thread comments", page_info, cursor, seen_cursors)
                next_page = fetch_thread_comments(
                    thread["id"], page_info.get("endCursor")
                )
                validate_thread_comments_page(
                    next_page, f"thread {thread['id']} comment page"
                )
                validate_matching_identity(
                    expected_identity,
                    thread_comments_identity(next_page),
                    f"thread {thread['id']} comment page",
                )
                next_comments = ((next_page.get("data") or {}).get("node") or {}).get(
                    "comments"
                ) or {}
                comments.setdefault("nodes", []).extend(
                    next_comments.get("nodes") or []
                )
                page_info = next_comments.get("pageInfo") or {}
                comments["pageInfo"] = page_info
                page_count += 1
                thread_pages.append(
                    {
                        "page_index": page_count,
                        "request_cursor": cursor,
                        "node_count": len(next_comments.get("nodes") or []),
                        "has_next_page": page_info.get("hasNextPage"),
                        "end_cursor": page_info.get("endCursor"),
                    }
                )
            if isinstance(pages, AcquiredPageSequence):
                hydration = {
                    "thread_node_id": thread["id"],
                    "complete": True,
                    "comment_count": sum(item["node_count"] for item in thread_pages),
                    "terminal_end_cursor": page_info.get("endCursor"),
                    "pages": thread_pages,
                }
                prior = pages.hydrated_threads.get(thread["id"])
                if prior is not None and prior != hydration:
                    raise IdentityError(
                        f"thread {thread['id']} had contradictory pagination evidence"
                    )
                pages.hydrated_threads[thread["id"]] = hydration


def fetch_thread_comments(thread_id: str, cursor: str | None) -> dict[str, Any]:
    query, variables = build_thread_comments_query(thread_id, cursor)
    page = run_gh_graphql(query, variables)
    validate_thread_comments_page(page, f"thread {thread_id} comment page")
    return page


def build_thread_comments_query(
    thread_id: str, cursor: str | None
) -> tuple[str, dict[str, Any]]:
    query = (
        """
query ThreadComments($threadId: ID!, $commentsCursor: String) {
  node(id: $threadId) {
    ... on PullRequestReviewThread {
      pullRequest {
        number
        baseRefName
        headRefName
        baseRefOid
        headRefOid
        headRepository {
          nameWithOwner
          owner { login }
        }
        repository {
          nameWithOwner
          owner { login }
        }
      }
      comments(first: 100, after: $commentsCursor) {
        nodes {
          ...ReviewCommentEvidence
        }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}
""".strip()
        + "\n\n"
        + ACTOR_IDENTITY_FRAGMENT
        + "\n\n"
        + REVIEW_COMMENT_EVIDENCE_FRAGMENT
    )
    return query, {"threadId": thread_id, "commentsCursor": cursor}


def run_gh_graphql(query: str, variables: dict[str, Any]) -> dict[str, Any]:
    command = [
        "gh",
        "api",
        "--hostname",
        GITHUB_HOST,
        "--method",
        "POST",
        "graphql",
        "--input",
        "-",
    ]
    request = json.dumps(
        {"query": query, "variables": variables},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    try:
        environment = dict(os.environ)
        environment.pop("GH_HOST", None)
        environment.pop("GH_REPO", None)
        environment.update({"GH_PROMPT_DISABLED": "1", "GIT_TERMINAL_PROMPT": "0"})
        completed = subprocess.run(
            command,
            check=False,
            input=request,
            text=True,
            capture_output=True,
            timeout=READ_TIMEOUT_SECONDS,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise FeedbackAcquisitionError(
            f"could not run gh GraphQL acquisition: {error}"
        ) from error
    if completed.returncode:
        detail = (
            completed.stderr.strip()
            or completed.stdout.strip()
            or "gh api graphql failed"
        )
        raise FeedbackAcquisitionError(detail)
    response = strict_json(completed.stdout, "GraphQL response")
    validate_graphql_envelope(response, "GraphQL response")
    return response


def validate_graphql_envelope(response: Any, source: str) -> None:
    if not isinstance(response, dict):
        raise ResponseShapeError(f"{source} was not an object")
    if "errors" in response:
        errors = response["errors"]
        if not isinstance(errors, list):
            raise ResponseShapeError(f"{source} had malformed GraphQL errors")
        if errors:
            messages = [
                error.get("message", "unknown GraphQL error")
                if isinstance(error, dict)
                else "malformed GraphQL error"
                for error in errors
            ]
            raise GraphQLQueryError(f"{source} reported errors: {'; '.join(messages)}")
    if not isinstance(response.get("data"), dict):
        raise ResponseShapeError(f"{source} was missing GraphQL data")


def validate_pr_page(page: Any, include: dict[str, bool], source: str) -> None:
    validate_graphql_envelope(page, source)
    try:
        repository = page["data"]["repository"]
    except (KeyError, TypeError) as error:
        raise ResponseShapeError(f"{source} was missing repository data") from error
    if not isinstance(repository, dict) or not repository:
        raise ResponseShapeError(f"{source} repository was null or malformed")
    owner = repository.get("owner")
    if (
        not isinstance(repository.get("nameWithOwner"), str)
        or not repository["nameWithOwner"]
        or not isinstance(owner, dict)
        or not isinstance(owner.get("login"), str)
        or not owner["login"]
    ):
        raise IdentityError(
            f"{source} was missing repository.owner.login or nameWithOwner"
        )

    pr = extract_pr(page)
    pull_request_identity(page)
    _validate_pr_scalars(pr, source)
    for connection_name in CONNECTION_KEYS:
        requested = bool(include.get(connection_name))
        connection = _pr_connection(pr, connection_name, requested, source)
        if connection is None:
            continue
        nodes, page_info = _validate_connection(connection, connection_name, source)
        if not requested and (nodes or page_info["hasNextPage"]):
            raise PaginationError(
                f"{source} returned unrequested {connection_name} data"
            )


def validate_thread_comments_page(page: Any, source: str) -> None:
    validate_graphql_envelope(page, source)
    try:
        node = page["data"]["node"]
    except (KeyError, TypeError) as error:
        raise ResponseShapeError(f"{source} was missing its thread node") from error
    if not isinstance(node, dict) or not node:
        raise ResponseShapeError(f"{source} thread node was null or malformed")
    thread_comments_identity(page)
    comments = node.get("comments")
    if not isinstance(comments, dict):
        raise ResponseShapeError(f"{source} was missing requested comments")
    _validate_connection(comments, "comments", source)


def _validate_pr_scalars(pr: dict[str, Any], source: str) -> None:
    required_strings = (
        "url",
        "baseRefName",
        "headRefName",
        "baseRefOid",
        "headRefOid",
        "mergeStateStatus",
        "mergeable",
    )
    if (
        type(pr.get("number")) is not int
        or pr["number"] <= 0
        or not isinstance(pr.get("isDraft"), bool)
        or any(
            not isinstance(pr.get(field), str) or not pr[field]
            for field in required_strings
        )
        or (
            pr.get("reviewDecision") is not None
            and not isinstance(pr["reviewDecision"], str)
        )
    ):
        raise ResponseShapeError(f"{source} had malformed pull request fields")


def _pr_connection(
    pr: dict[str, Any], connection_name: str, required: bool, source: str
) -> dict[str, Any] | None:
    field_names = {
        "threads": "reviewThreads",
        "comments": "comments",
        "reviews": "reviews",
        "review_requests": "reviewRequests",
    }
    if connection_name == "checks":
        if "statusCheckRollup" not in pr:
            if required:
                raise ResponseShapeError(f"{source} was missing requested checks")
            return None
        rollup = pr["statusCheckRollup"]
        if rollup is None:
            return {"nodes": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}
        if not isinstance(rollup, dict) or not isinstance(rollup.get("contexts"), dict):
            raise ResponseShapeError(f"{source} had malformed requested checks")
        return rollup["contexts"]

    field_name = field_names[connection_name]
    if field_name not in pr or pr[field_name] is None:
        if required:
            raise ResponseShapeError(
                f"{source} was missing requested {connection_name}"
            )
        return None
    if not isinstance(pr[field_name], dict):
        raise ResponseShapeError(f"{source} had malformed requested {connection_name}")
    return pr[field_name]


def _validate_connection(
    connection: dict[str, Any], connection_name: str, source: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    nodes = connection.get("nodes")
    page_info = connection.get("pageInfo")
    if not isinstance(nodes, list) or not isinstance(page_info, dict):
        raise ResponseShapeError(f"{source} had malformed {connection_name} connection")
    if (
        not isinstance(page_info.get("hasNextPage"), bool)
        or "endCursor" not in page_info
        or (
            page_info["endCursor"] is not None
            and not isinstance(page_info["endCursor"], str)
        )
    ):
        raise ResponseShapeError(f"{source} had malformed {connection_name} pageInfo")
    if page_info["hasNextPage"] and not page_info["endCursor"]:
        raise PaginationError(f"{connection_name} pagination has no end cursor")
    for index, node in enumerate(nodes):
        if not isinstance(node, dict) or not node:
            raise ResponseShapeError(
                f"{source} had null or malformed {connection_name} node {index}"
            )
        _validate_connection_node(node, connection_name, source, index)
    return nodes, page_info


def _validate_connection_node(
    node: dict[str, Any], connection_name: str, source: str, index: int
) -> None:
    if connection_name == "threads":
        if (
            not isinstance(node.get("id"), str)
            or not node["id"]
            or not isinstance(node.get("isResolved"), bool)
            or not isinstance(node.get("isOutdated"), bool)
            or not isinstance(node.get("comments"), dict)
        ):
            raise ResponseShapeError(f"{source} had malformed thread node {index}")
        _validate_connection(
            node["comments"], "comments", f"{source} thread {node['id']}"
        )
    elif connection_name == "comments":
        if (
            not isinstance(node.get("body"), str)
            or not isinstance(node.get("createdAt"), str)
            or not node["createdAt"]
            or not isinstance(node.get("url"), str)
            or not node["url"]
        ):
            raise ResponseShapeError(f"{source} had malformed comment node {index}")
    elif connection_name == "reviews":
        if not isinstance(node.get("state"), str) or not node["state"]:
            raise ResponseShapeError(f"{source} had malformed review node {index}")
    elif connection_name == "review_requests":
        requested = node.get("requestedReviewer")
        if not isinstance(requested, dict) or requested.get("__typename") not in {
            "User",
            "Team",
        }:
            raise ResponseShapeError(
                f"{source} had malformed review request node {index}"
            )
        identifier = (
            requested.get("login")
            if requested["__typename"] == "User"
            else requested.get("slug")
        )
        if not isinstance(identifier, str) or not identifier:
            raise ResponseShapeError(
                f"{source} had malformed review request node {index}"
            )
    elif connection_name == "checks":
        typename = node.get("__typename")
        if typename == "CheckRun":
            valid = (
                isinstance(node.get("name"), str)
                and bool(node["name"])
                and isinstance(node.get("status"), str)
            )
        elif typename == "StatusContext":
            valid = (
                isinstance(node.get("context"), str)
                and bool(node["context"])
                and isinstance(node.get("state"), str)
            )
        else:
            valid = False
        if not valid:
            raise ResponseShapeError(
                f"{source} had empty or malformed check node {index}"
            )


def validate_supplied_page_sequence(pages: list[dict[str, Any]]) -> None:
    include = {key: True for key in CONNECTION_KEYS}
    cursors: dict[str, str | None] = {key: None for key in CONNECTION_KEYS}
    seen_cursors = {key: set() for key in CONNECTION_KEYS}
    for index, page in enumerate(pages):
        source = f"supplied page {index + 1}"
        validate_pr_page(page, include, source)
        page_info = page_infos(page)
        next_cursors = {
            key: next_cursor(key, page_info[key], cursors[key], seen_cursors[key])
            for key in CONNECTION_KEYS
        }
        if not any(next_cursors.values()) and index != len(pages) - 1:
            raise PaginationError(
                f"{source} was terminal but additional pages followed"
            )
        include = {key: value is not None for key, value in next_cursors.items()}
        cursors = next_cursors
    if any(cursors.values()):
        raise PaginationError("supplied pages ended before pagination completed")
    merged_threads = collect_review_threads([extract_pr(page) for page in pages])
    if any(
        (thread["comments"]["pageInfo"] or {}).get("hasNextPage")
        for thread in merged_threads
    ):
        raise PaginationError(
            "supplied pages ended before thread comment hydration completed"
        )


def _canonical_digest(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _required_string(node: dict[str, Any], field: str, source: str) -> str:
    value = node.get(field)
    if not isinstance(value, str) or not value:
        raise ResponseShapeError(f"{source} lacked strict response evidence: {field}")
    return value


def _provider_identity(
    node: dict[str, Any], source: str, *, database_required: bool = True
) -> dict[str, Any]:
    node_id = _required_string(node, "id", source)
    if "databaseId" not in node:
        raise ResponseShapeError(
            f"{source} lacked strict response evidence: databaseId"
        )
    database_id = node["databaseId"]
    if database_id is None:
        if database_required:
            raise ResponseShapeError(
                f"{source} lacked strict response evidence: databaseId"
            )
    elif type(database_id) is not int or database_id <= 0:
        raise ResponseShapeError(
            f"{source} supplied invalid databaseId"
        )
    return {"node_id": node_id, "database_id": database_id}


class _IdentityRegistry:
    """Validate one acquisition-wide provider identity namespace."""

    def __init__(self) -> None:
        self._by_node: dict[str, tuple[str, int | None]] = {}
        self._by_database: dict[tuple[str, int], str] = {}
        self._fingerprints: dict[tuple[str, str, int | None], str] = {}
        self._observed: set[tuple[str, str, int | None]] = set()
        self._associations: list[tuple[tuple[str, str, int | None], str]] = []

    def register(
        self,
        object_kind: str,
        node: dict[str, Any],
        source: str,
        *,
        database_required: bool = True,
        observed: bool = True,
        fingerprint: Any | None = None,
    ) -> tuple[str, str, int | None]:
        node_id = _required_string(node, "id", source)
        database_id = node.get("databaseId")
        if database_required:
            if type(database_id) is not int or database_id <= 0:
                raise ResponseShapeError(
                    f"{source} lacked strict response evidence: databaseId"
                )
        elif database_id is not None:
            raise ResponseShapeError(
                f"{source} supplied databaseId not exposed by the public schema"
            )
        typed = (object_kind, node_id, database_id)
        prior_node = self._by_node.get(node_id)
        if prior_node is not None and prior_node != (object_kind, database_id):
            raise IdentityError(
                f"{source} had contradictory typed identity for node ID {node_id}"
            )
        self._by_node[node_id] = (object_kind, database_id)
        if database_id is not None:
            database_key = (object_kind, database_id)
            prior_database = self._by_database.get(database_key)
            if prior_database is not None and prior_database != node_id:
                raise IdentityError(
                    f"{source} had contradictory typed identity for database ID "
                    f"{database_id}"
                )
            self._by_database[database_key] = node_id
        if fingerprint is not None:
            digest = _canonical_digest(fingerprint)
            prior_fingerprint = self._fingerprints.get(typed)
            if prior_fingerprint is not None and prior_fingerprint != digest:
                label = (
                    "thread scalars"
                    if object_kind == "PullRequestReviewThread"
                    else "repeated provider object"
                )
                raise IdentityError(f"{source} changed {label} for one typed identity")
            self._fingerprints[typed] = digest
        if observed:
            self._observed.add(typed)
        else:
            self._associations.append((typed, source))
        return typed

    def validate_associations(self) -> None:
        for typed, source in self._associations:
            if typed not in self._observed:
                target = (
                    "its observed thread root"
                    if "replyTo" in source
                    else "an observed provider object"
                )
                raise IdentityError(f"{source} did not resolve to {target}")

    def entries(self) -> list[dict[str, Any]]:
        result = []
        for object_kind, node_id, database_id in sorted(self._observed):
            result.append(
                {
                    "object_kind": object_kind,
                    "node_id": node_id,
                    "database_id": (
                        {"availability": "available", "value": database_id}
                        if database_id is not None
                        else {
                            "availability": "unavailable",
                            "reason": "not_exposed_by_public_schema",
                        }
                    ),
                }
            )
        return result


def _identity_consistent_collections(
    pages: list[dict[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    registry = _IdentityRegistry()
    comments_by_identity: dict[tuple[str, str, int | None], dict[str, Any]] = {}
    reviews_by_identity: dict[tuple[str, str, int | None], dict[str, Any]] = {}
    threads_by_identity: dict[tuple[str, str, int | None], dict[str, Any]] = {}
    expected_repository_identity: dict[str, Any] | None = None

    for page_index, page in enumerate(pages, 1):
        expected_repository_identity = validate_repository_page_identity(
            expected_repository_identity, page, f"supplied page {page_index}"
        )
        pr = extract_pr(page)
        registry.register("PullRequest", pr, f"supplied page {page_index} pull request")
        for index, comment in enumerate((pr.get("comments") or {}).get("nodes") or []):
            source = f"supplied page {page_index} IssueComment {index}"
            typed = registry.register(
                "IssueComment", comment, source, fingerprint=comment
            )
            comments_by_identity.setdefault(typed, copy.deepcopy(comment))
        for index, review in enumerate((pr.get("reviews") or {}).get("nodes") or []):
            source = f"supplied page {page_index} PullRequestReview {index}"
            typed = registry.register(
                "PullRequestReview", review, source, fingerprint=review
            )
            reviews_by_identity.setdefault(typed, copy.deepcopy(review))
        for thread_index, thread in enumerate(
            (pr.get("reviewThreads") or {}).get("nodes") or []
        ):
            source = f"supplied page {page_index} review thread {thread_index}"
            scalar_evidence = {
                key: value for key, value in thread.items() if key != "comments"
            }
            typed_thread = registry.register(
                "PullRequestReviewThread",
                thread,
                source,
                database_required=False,
                fingerprint=scalar_evidence,
            )
            merged = threads_by_identity.setdefault(typed_thread, copy.deepcopy(thread))
            merged_comments = merged.setdefault("comments", {}).setdefault("nodes", [])
            if merged is not thread and typed_thread in threads_by_identity:
                existing = {
                    (item.get("id"), item.get("databaseId")) for item in merged_comments
                }
            else:  # pragma: no cover - defensive; setdefault always returns a value
                existing = set()
            for comment_index, comment in enumerate(
                (thread.get("comments") or {}).get("nodes") or []
            ):
                comment_source = f"{source} comment {comment_index}"
                typed_comment = registry.register(
                    "PullRequestReviewComment",
                    comment,
                    comment_source,
                    fingerprint=comment,
                )
                comment_pair = (typed_comment[1], typed_comment[2])
                if comment_pair not in existing:
                    merged_comments.append(copy.deepcopy(comment))
                    existing.add(comment_pair)
                reply_to = comment.get("replyTo")
                if isinstance(reply_to, dict):
                    registry.register(
                        "PullRequestReviewComment",
                        reply_to,
                        f"{comment_source} replyTo association",
                        observed=False,
                    )
                review = comment.get("pullRequestReview")
                if isinstance(review, dict):
                    registry.register(
                        "PullRequestReview",
                        review,
                        f"{comment_source} review association",
                        observed=False,
                    )

    registry.validate_associations()
    return (
        list(threads_by_identity.values()),
        list(comments_by_identity.values()),
        list(reviews_by_identity.values()),
        registry.entries(),
    )


def _required_bool(node: dict[str, Any], field: str, source: str) -> bool:
    value = node.get(field)
    if not isinstance(value, bool):
        raise ResponseShapeError(f"{source} lacked strict response evidence: {field}")
    return value


def _required_int(node: dict[str, Any], field: str, source: str) -> int:
    value = node.get(field)
    if type(value) is not int:
        raise ResponseShapeError(f"{source} lacked strict response evidence: {field}")
    return value


def _optional_int(node: dict[str, Any], field: str, source: str) -> int | None:
    if field not in node:
        raise ResponseShapeError(f"{source} lacked strict response evidence: {field}")
    value = node[field]
    if value is not None and type(value) is not int:
        raise ResponseShapeError(
            f"{source} had malformed strict response evidence: {field}"
        )
    return value


def _optional_string(node: dict[str, Any], field: str, source: str) -> str | None:
    if field not in node:
        raise ResponseShapeError(f"{source} lacked strict response evidence: {field}")
    value = node[field]
    if value is not None and (not isinstance(value, str) or not value):
        raise ResponseShapeError(
            f"{source} had malformed strict response evidence: {field}"
        )
    return value


def _selected_nullable(node: dict[str, Any], field: str, source: str) -> Any:
    if field not in node:
        raise ResponseShapeError(f"{source} lacked strict response evidence: {field}")
    return node[field]


def _optional_revision(node: Any, source: str) -> dict[str, Any]:
    if node is None:
        return {"availability": "unavailable", "reason": "provider_returned_null"}
    if not isinstance(node, dict):
        raise ResponseShapeError(f"{source} had malformed strict response evidence")
    return {
        "availability": "available",
        "oid": _required_string(node, "oid", source),
    }


def _author_evidence(node: dict[str, Any], source: str) -> dict[str, Any]:
    association = _required_string(node, "authorAssociation", source)
    author = _selected_nullable(node, "author", source)
    if author is None:
        return {
            "availability": "unavailable",
            "reason": "provider_returned_null",
            "association": association,
        }
    if not isinstance(author, dict):
        raise ResponseShapeError(f"{source} lacked strict response evidence: author")
    return {
        "availability": "available",
        "node_id": _required_string(author, "id", f"{source} author"),
        "login": _required_string(author, "login", f"{source} author"),
        "provider_type": _required_string(author, "__typename", f"{source} author"),
        "association": association,
    }


def _body_evidence(body: str) -> dict[str, Any]:
    body_bytes = body.encode("utf-8")
    return {
        "utf8_base64": base64.b64encode(body_bytes).decode("ascii"),
        "byte_length": len(body_bytes),
        "sha256": hashlib.sha256(body_bytes).hexdigest(),
    }


def _source_revision_identity(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "body": source["body"],
        "provider_revision": {
            "availability": "available",
            "kind": "updated_at",
            "value": source["updated_at"],
        },
        "associated_commit": source["associated_revision"],
    }


def _bind_source_revision(source: dict[str, Any]) -> None:
    source["source_revision_identity"] = _source_revision_identity(source)
    source["source_revision"] = _canonical_digest(source["source_revision_identity"])


def _strict_inline_source(
    comment: dict[str, Any],
    thread: dict[str, Any],
    root_identity: dict[str, Any],
) -> dict[str, Any]:
    identity = _provider_identity(comment, "inline review comment")
    root_nodes = (thread.get("comments") or {}).get("nodes") or []
    state = _required_string(comment, "state", "inline review comment")
    if "replyTo" not in comment:
        raise ResponseShapeError(
            "inline review comment lacked strict response evidence: replyTo"
        )
    reply_to = comment["replyTo"]
    if reply_to is None:
        if identity != root_identity:
            raise ResponseShapeError(
                "inline review comment replyTo contradicted the thread root"
            )
        reply_evidence = {"availability": "unavailable", "reason": "thread_root"}
    else:
        if not isinstance(reply_to, dict):
            raise ResponseShapeError(
                "inline review comment lacked strict response evidence: replyTo"
            )
        reply_identity = _provider_identity(reply_to, "inline comment replyTo")
        if reply_identity != root_identity:
            raise ResponseShapeError(
                "inline review comment replyTo did not identify the thread root"
            )
        reply_evidence = {"availability": "available", **reply_identity}
    review = _selected_nullable(comment, "pullRequestReview", "inline review comment")
    if review is None and state == "PENDING":
        review_evidence = {
            "availability": "unavailable",
            "reason": "provider_returned_null",
        }
    elif not isinstance(review, dict):
        raise ResponseShapeError(
            "inline review comment lacked strict response evidence: pullRequestReview"
        )
    else:
        review_evidence = _provider_identity(review, "inline comment review")
    commit = _selected_nullable(comment, "commit", "inline review comment")
    if commit is not None and not isinstance(commit, dict):
        raise ResponseShapeError(
            "inline review comment had malformed strict response evidence: commit"
        )
    original_commit = _selected_nullable(
        comment, "originalCommit", "inline review comment"
    )
    if original_commit is not None and not isinstance(original_commit, dict):
        raise ResponseShapeError(
            "inline review comment had malformed strict response evidence: "
            "originalCommit"
        )
    body = comment.get("body")
    if not isinstance(body, str):
        raise ResponseShapeError(
            "inline review comment lacked strict response evidence: body"
        )
    source = {
        "kind": "inline_review_comment",
        "provider_identity": identity,
        "permalink": _required_string(comment, "url", "inline review comment"),
        "body": _body_evidence(body),
        "author": _author_evidence(comment, "inline review comment"),
        "created_at": _required_string(comment, "createdAt", "inline review comment"),
        "updated_at": _required_string(comment, "updatedAt", "inline review comment"),
        "state": {
            "availability": "available",
            "value": state,
            "outdated": _required_bool(comment, "outdated", "inline review comment"),
        },
        "reply_to": reply_evidence,
        "location": {
            "path": _required_string(comment, "path", "inline review comment"),
            "line": _optional_int(comment, "line", "inline review comment"),
            "original_line": _optional_int(
                comment, "originalLine", "inline review comment"
            ),
            "original_position": _required_int(
                comment, "originalPosition", "inline review comment"
            ),
            "original_start_line": _optional_int(
                comment, "originalStartLine", "inline review comment"
            ),
            "start_line": _optional_int(comment, "startLine", "inline review comment"),
            "subject_type": _required_string(
                comment, "subjectType", "inline review comment"
            ),
        },
        "associated_revision": (
            {
                "availability": "available",
                "oid": _required_string(commit, "oid", "inline review comment commit"),
            }
            if commit is not None
            else {"availability": "unavailable", "reason": "provider_returned_null"}
        ),
        "original_revision": _optional_revision(
            original_commit, "inline review comment originalCommit"
        ),
        "thread": {
            "node_id": _required_string(thread, "id", "inline review thread"),
            "root_comment_node_id": root_identity["node_id"],
            "root_comment_database_id": root_identity["database_id"],
            "is_resolved": thread.get("isResolved"),
            "is_outdated": thread.get("isOutdated"),
            "path": _required_string(thread, "path", "inline review thread"),
            "line": _optional_int(thread, "line", "inline review thread"),
            "diff_side": _required_string(thread, "diffSide", "inline review thread"),
            "original_line": _optional_int(
                thread, "originalLine", "inline review thread"
            ),
            "original_start_line": _optional_int(
                thread, "originalStartLine", "inline review thread"
            ),
            "start_diff_side": _optional_string(
                thread, "startDiffSide", "inline review thread"
            ),
            "start_line": _optional_int(thread, "startLine", "inline review thread"),
            "subject_type": _required_string(
                thread, "subjectType", "inline review thread"
            ),
            "comment_node_ids": [
                _provider_identity(item, "inline thread comment")["node_id"]
                for item in root_nodes
            ],
        },
        "review": review_evidence,
    }
    if not isinstance(source["thread"]["is_resolved"], bool) or not isinstance(
        source["thread"]["is_outdated"], bool
    ):
        raise ResponseShapeError(
            "inline review thread lacked strict response evidence: state"
        )
    _bind_source_revision(source)
    return source


def _strict_conversation_source(comment: dict[str, Any]) -> dict[str, Any]:
    body = comment.get("body")
    if not isinstance(body, str):
        raise ResponseShapeError(
            "pull request conversation comment lacked strict response evidence: body"
        )
    source = {
        "kind": "pr_conversation_comment",
        "provider_identity": _provider_identity(
            comment, "pull request conversation comment"
        ),
        "permalink": _required_string(
            comment, "url", "pull request conversation comment"
        ),
        "body": _body_evidence(body),
        "author": _author_evidence(comment, "pull request conversation comment"),
        "created_at": _required_string(
            comment, "createdAt", "pull request conversation comment"
        ),
        "updated_at": _required_string(
            comment, "updatedAt", "pull request conversation comment"
        ),
        "state": {
            "availability": "unavailable",
            "reason": "not_exposed_for_issue_comment",
        },
        "location": {"placement": "pull_request_conversation"},
        "associated_revision": {
            "availability": "unavailable",
            "reason": "not_exposed_for_issue_comment",
        },
    }
    _bind_source_revision(source)
    return source


def _strict_review_source(review: dict[str, Any]) -> dict[str, Any]:
    body = review.get("body")
    if not isinstance(body, str):
        raise ResponseShapeError(
            "submitted review lacked strict response evidence: body"
        )
    commit = _selected_nullable(review, "commit", "review")
    if commit is not None and not isinstance(commit, dict):
        raise ResponseShapeError(
            "review had malformed strict response evidence: commit"
        )
    submitted_at = _selected_nullable(review, "submittedAt", "review")
    if submitted_at is not None and (
        not isinstance(submitted_at, str) or not submitted_at
    ):
        raise ResponseShapeError(
            "review had malformed strict response evidence: submittedAt"
        )
    state = _required_string(review, "state", "submitted review")
    if (state == "PENDING") != (submitted_at is None):
        raise ResponseShapeError(
            "review state contradicted strict response evidence: submittedAt"
        )
    source = {
        "kind": "submitted_review_body",
        "provider_identity": _provider_identity(review, "submitted review"),
        "permalink": _required_string(review, "url", "submitted review"),
        "body": _body_evidence(body),
        "author": _author_evidence(review, "submitted review"),
        "created_at": _required_string(review, "createdAt", "submitted review"),
        "submitted_at": (
            {"availability": "available", "value": submitted_at}
            if submitted_at is not None
            else {"availability": "unavailable", "reason": "review_not_submitted"}
        ),
        "updated_at": _required_string(review, "updatedAt", "submitted review"),
        "state": {
            "availability": "available",
            "value": state,
        },
        "location": {"placement": "submitted_review"},
        "associated_revision": (
            {
                "availability": "available",
                "oid": _required_string(commit, "oid", "submitted review commit"),
            }
            if commit is not None
            else {"availability": "unavailable", "reason": "provider_returned_null"}
        ),
    }
    _bind_source_revision(source)
    return source


def _validate_inline_associations(
    sources: list[dict[str, Any]], review_identities: list[dict[str, Any]]
) -> None:
    for source in sources:
        if (
            source["location"]["path"] != source["thread"]["path"]
            or source["location"]["subject_type"] != source["thread"]["subject_type"]
        ):
            raise ResponseShapeError(
                "inline review comment placement contradicted its containing thread"
            )
        if (
            source["state"]["value"] == "SUBMITTED"
            and source["review"] not in review_identities
        ):
            raise ResponseShapeError(
                "inline review comment review association was absent or contradictory"
            )


def typed_epoch_from_pages(
    repo: str,
    pages: list[dict[str, Any]],
    pr_number: int | None = None,
    *,
    acquisition_start_observation: dict[str, Any] | None = None,
    acquisition_end_observation: dict[str, Any] | None = None,
    pagination_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return strict response evidence without changing schema-v2 orientation."""
    if acquisition_start_observation is None:
        acquisition_start_observation = local_acquisition_observation("start")
    state_from_pages(repo, pages, pr_number=pr_number)
    first = extract_pr(pages[0])
    identity = pull_request_identity(pages[0])
    pr_identity = _provider_identity(first, "pull request")
    threads, comments, reviews, identity_registry = _identity_consistent_collections(
        pages
    )
    review_sources = [_strict_review_source(item) for item in reviews]
    review_identities = [item["provider_identity"] for item in review_sources]
    all_sources: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    for thread in threads:
        thread_comments = (thread.get("comments") or {}).get("nodes") or []
        root_comments = [
            item for item in thread_comments if item.get("replyTo") is None
        ]
        if len(root_comments) != 1 or any(
            "replyTo" not in item for item in thread_comments
        ):
            raise ResponseShapeError(
                "inline review thread lacked one unambiguous replyTo thread root"
            )
        root_identity = _provider_identity(
            root_comments[0], "inline thread root comment"
        )
        thread_sources = [
            _strict_inline_source(comment, thread, root_identity)
            for comment in thread_comments
        ]
        _validate_inline_associations(thread_sources, review_identities)
        observations.extend(thread_sources)
        all_sources.extend(
            source
            for source in thread_sources
            if source["state"]["value"] == "SUBMITTED"
            and base64.b64decode(source["body"]["utf8_base64"]).strip()
        )
    conversation_sources = [_strict_conversation_source(item) for item in comments]
    observations.extend(conversation_sources)
    observations.extend(review_sources)
    all_sources.extend(
        source
        for source in conversation_sources
        if base64.b64decode(source["body"]["utf8_base64"]).strip()
    )
    all_sources.extend(
        source
        for source in review_sources
        if source["state"]["value"] != "PENDING"
        and base64.b64decode(source["body"]["utf8_base64"]).strip()
    )
    if acquisition_end_observation is None:
        acquisition_end_observation = local_acquisition_observation("end")
    if pagination_evidence is None:
        pagination_evidence = pagination_evidence_from_pages(pages)
    repository = pages[0]["data"]["repository"]
    repository_identity = _provider_identity(
        repository, "repository", database_required=False
    )
    epoch = {
        "schema_version": 1,
        "complete": True,
        "snapshot_atomicity": "not_claimed",
        "repository": {
            "name_with_owner": identity["repo"],
            "owner_login": identity["owner"],
            "provider_identity": repository_identity,
        },
        "pull_request": {
            **pr_identity,
            "number": identity["number"],
            "permalink": _required_string(first, "url", "pull request"),
            "head_oid": identity["head_oid"],
            "base_oid": identity["base_oid"],
            "head_repository": identity["head_repo"],
        },
        "sources": all_sources,
        "observations": observations,
        "observation_digest": _canonical_digest(observations),
        "identity_registry": identity_registry,
        "identity_registry_digest": _canonical_digest(identity_registry),
        "acquisition_start_observation": acquisition_start_observation,
        "acquisition_end_observation": acquisition_end_observation,
        "pagination_evidence": pagination_evidence,
    }
    epoch["epoch_id"] = _canonical_digest(epoch)
    return epoch


def local_acquisition_observation(phase: str) -> dict[str, Any]:
    if phase not in {"start", "end"}:
        raise ValueError("acquisition observation phase must be start or end")
    return {
        "kind": "local_acquisition_observation",
        "phase": phase,
        "observed_at": datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z"),
        "monotonic_ns": time.monotonic_ns(),
    }


def pagination_evidence_from_pages(
    pages: list[dict[str, Any]],
) -> dict[str, Any]:
    if isinstance(pages, AcquiredPageSequence):
        return pages.pagination_evidence()
    collections: dict[str, Any] = {}
    for name in CONNECTION_KEYS:
        observations = []
        request_cursor = None
        for page in pages:
            pr = extract_pr(page)
            connection = _pr_connection(pr, name, False, "pagination evidence")
            if connection is None:
                continue
            page_info = connection.get("pageInfo") or {}
            observations.append(
                {
                    "page_index": len(observations),
                    "request_cursor": request_cursor,
                    "node_count": len(connection.get("nodes") or []),
                    "has_next_page": page_info.get("hasNextPage"),
                    "end_cursor": page_info.get("endCursor"),
                }
            )
            request_cursor = page_info.get("endCursor")
        if not observations or observations[-1]["has_next_page"] is not False:
            raise PaginationError(f"{name} pagination evidence was incomplete")
        collections[name] = {
            "complete": True,
            "node_count": sum(page["node_count"] for page in observations),
            "pages": observations,
        }
    hydrated_threads = []
    for thread in collect_review_threads([extract_pr(page) for page in pages]):
        comments = thread.get("comments") or {}
        page_info = comments.get("pageInfo") or {}
        if page_info.get("hasNextPage") is not False:
            raise PaginationError("hydrated thread pagination evidence was incomplete")
        hydrated_threads.append(
            {
                "thread_node_id": thread.get("id"),
                "complete": True,
                "comment_count": len(comments.get("nodes") or []),
                "terminal_end_cursor": page_info.get("endCursor"),
                "pages": [
                    {
                        "page_index": 0,
                        "request_cursor": None,
                        "node_count": len(comments.get("nodes") or []),
                        "has_next_page": page_info.get("hasNextPage"),
                        "end_cursor": page_info.get("endCursor"),
                    }
                ],
            }
        )
    return {
        "complete": True,
        "collections": collections,
        "hydrated_threads": hydrated_threads,
    }


def state_from_pages(
    repo: str, pages: list[dict[str, Any]], pr_number: int | None = None
) -> dict[str, Any]:
    owner, name = split_repo(repo)
    if not pages:
        raise ResponseShapeError("at least one page is required")

    validate_supplied_page_sequence(pages)
    first_identity = pull_request_identity(pages[0])
    validate_requested_identity(
        repo,
        first_identity["number"] if pr_number is None else pr_number,
        first_identity,
    )
    for page in pages[1:]:
        validate_matching_identity(
            first_identity, pull_request_identity(page), "supplied page"
        )

    pull_requests = [extract_pr(page) for page in pages]
    pr = pull_requests[0]
    review_threads = collect_review_threads(pull_requests)
    comments = collect_nodes(pull_requests, "comments")
    reviews = collect_nodes(pull_requests, "reviews")
    review_requests = collect_nodes(pull_requests, "reviewRequests")
    checks = collect_checks(pull_requests)
    unresolved_threads = [
        summarize_thread(thread, pr["headRefOid"])
        for thread in review_threads
        if not thread.get("isResolved")
    ]
    requested_reviewers, requested_teams = summarize_review_requests(review_requests)
    normalized_checks = [normalize_check(check) for check in checks]
    pagination_complete = is_pagination_complete(pull_requests)
    next_blocker = classify_blocker(
        pr,
        unresolved_threads,
        requested_reviewers,
        requested_teams,
        normalized_checks,
        pagination_complete,
    )

    return {
        "schema_version": 2,
        "repo": {
            "owner": owner,
            "name": name,
            "head_repository": first_identity["head_repo"],
            "head_owner": first_identity["head_owner"],
            "base_ref": pr.get("baseRefName"),
            "head_ref": pr.get("headRefName"),
        },
        "pr": {
            "number": pr.get("number"),
            "url": pr.get("url"),
            "draft": bool(pr.get("isDraft")),
        },
        "diff": {
            "head_sha": pr.get("headRefOid"),
            "base_sha": pr.get("baseRefOid"),
            "diff_id": pr.get("headRefOid"),
        },
        "github_state": {
            "merge_state": pr.get("mergeStateStatus"),
            "mergeable": pr.get("mergeable"),
            "review_decision": pr.get("reviewDecision"),
            "requested_reviewers": requested_reviewers,
            "requested_teams": requested_teams,
            "checks": normalized_checks,
            "unresolved_threads": unresolved_threads,
            "comments": summarize_comments(comments),
            "reviews": summarize_reviews(reviews),
            "pagination_complete": pagination_complete,
        },
        "next_blocker": next_blocker,
    }


def extract_pr(page: dict[str, Any]) -> dict[str, Any]:
    validate_graphql_envelope(page, "pull request page")
    try:
        pr = page["data"]["repository"]["pullRequest"]
    except (KeyError, TypeError) as error:
        raise ResponseShapeError(f"missing pullRequest in page: {error}") from error
    if not isinstance(pr, dict) or not pr:
        raise ResponseShapeError("pullRequest was null or malformed")
    return pr


def pull_request_identity(page: dict[str, Any]) -> dict[str, Any]:
    try:
        repository = page["data"]["repository"]
        pr = repository["pullRequest"]
        owner = (repository.get("owner") or {}).get("login")
        name_with_owner = repository.get("nameWithOwner")
        head_repository = pr.get("headRepository") or {}
        head_owner = (head_repository.get("owner") or {}).get("login")
        head_name_with_owner = head_repository.get("nameWithOwner")
    except (KeyError, TypeError) as error:
        raise IdentityError(f"missing repository identity in page: {error}") from error
    if not owner or not name_with_owner or not head_owner or not head_name_with_owner:
        raise IdentityError(
            "missing base or head repository owner or nameWithOwner in page"
        )
    validate_head_repository_identity(head_name_with_owner, head_owner)
    identity = {
        "repo": name_with_owner,
        "owner": owner,
        "head_repo": head_name_with_owner,
        "head_owner": head_owner,
        "number": pr.get("number"),
        "base_ref": pr.get("baseRefName"),
        "base_oid": pr.get("baseRefOid"),
        "head_ref": pr.get("headRefName"),
        "head_oid": pr.get("headRefOid"),
    }
    require_complete_identity(identity, "page")
    return identity


def validate_repository_page_identity(
    expected: dict[str, Any] | None,
    page: dict[str, Any],
    source: str,
) -> dict[str, Any]:
    repository = page["data"]["repository"]
    actual = _provider_identity(
        repository, f"{source} repository", database_required=False
    )
    if expected is not None:
        validate_matching_identity(expected, actual, f"{source} repository")
        return expected
    return actual


def thread_comments_identity(page: dict[str, Any]) -> dict[str, Any]:
    try:
        pr = page["data"]["node"]["pullRequest"]
        repository = pr["repository"]
        owner = (repository.get("owner") or {}).get("login")
        name_with_owner = repository.get("nameWithOwner")
        head_repository = pr.get("headRepository") or {}
        head_owner = (head_repository.get("owner") or {}).get("login")
        head_name_with_owner = head_repository.get("nameWithOwner")
    except (KeyError, TypeError) as error:
        raise IdentityError(
            f"missing pull request identity in thread comment page: {error}"
        ) from error
    if not owner or not name_with_owner or not head_owner or not head_name_with_owner:
        raise IdentityError(
            "missing base or head repository owner or nameWithOwner "
            "in thread comment page"
        )
    validate_head_repository_identity(head_name_with_owner, head_owner)
    identity = {
        "repo": name_with_owner,
        "owner": owner,
        "head_repo": head_name_with_owner,
        "head_owner": head_owner,
        "number": pr.get("number"),
        "base_ref": pr.get("baseRefName"),
        "base_oid": pr.get("baseRefOid"),
        "head_ref": pr.get("headRefName"),
        "head_oid": pr.get("headRefOid"),
    }
    require_complete_identity(identity, "thread comment page")
    return identity


def require_complete_identity(identity: dict[str, Any], source: str) -> None:
    required_fields = (
        "repo",
        "owner",
        "head_repo",
        "head_owner",
        "number",
        "base_ref",
        "base_oid",
        "head_ref",
        "head_oid",
    )
    malformed_fields = [
        field
        for field in required_fields
        if (
            type(identity.get(field)) is not int or identity[field] <= 0
            if field == "number"
            else not isinstance(identity.get(field), str) or not identity[field]
        )
    ]
    if malformed_fields:
        raise IdentityError(
            f"{source} has incomplete pull request identity: "
            f"{', '.join(malformed_fields)}"
        )


def validate_requested_identity(
    repo: str, pr_number: int, identity: dict[str, Any]
) -> None:
    expected_owner, _ = split_repo(repo)
    if (
        identity["repo"] != repo
        or identity["owner"] != expected_owner
        or identity["number"] != pr_number
    ):
        raise IdentityError(
            "first page does not match requested pull request: "
            f"expected {repo}#{pr_number} owned by {expected_owner}, "
            f"got {identity['repo']}#{identity['number']} owned by {identity['owner']}"
        )


def validate_matching_identity(
    expected: dict[str, Any], actual: dict[str, Any], source: str
) -> None:
    differing_fields = [
        key
        for key, value in expected.items()
        if type(actual.get(key)) is not type(value) or actual.get(key) != value
    ]
    if differing_fields:
        raise IdentityError(
            f"{source} drifted from first-page identity: {', '.join(differing_fields)}"
        )


def collect_nodes(
    pull_requests: list[dict[str, Any]], key: str
) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for pr in pull_requests:
        nodes.extend((pr.get(key) or {}).get("nodes") or [])
    return nodes


def collect_review_threads(pull_requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    threads_by_id: dict[str, dict[str, Any]] = {}
    anonymous_threads: list[dict[str, Any]] = []
    for pr in pull_requests:
        for thread in (pr.get("reviewThreads") or {}).get("nodes") or []:
            thread_id = thread.get("id")
            if not thread_id:
                anonymous_threads.append(thread)
                continue
            if thread_id not in threads_by_id:
                threads_by_id[thread_id] = copy.deepcopy(thread)
                continue
            existing = threads_by_id[thread_id]
            existing["isResolved"] = thread.get(
                "isResolved", existing.get("isResolved")
            )
            existing["isOutdated"] = thread.get(
                "isOutdated", existing.get("isOutdated")
            )
            existing["path"] = thread.get("path") or existing.get("path")
            existing["line"] = (
                thread.get("line")
                if thread.get("line") is not None
                else existing.get("line")
            )
            existing_comments = existing.setdefault("comments", {}).setdefault(
                "nodes", []
            )
            seen_urls = {comment.get("url") for comment in existing_comments}
            for comment in (thread.get("comments") or {}).get("nodes") or []:
                comment_url = comment.get("url")
                if comment_url not in seen_urls:
                    existing_comments.append(comment)
                    seen_urls.add(comment_url)
            existing["comments"]["pageInfo"] = (
                (thread.get("comments") or {}).get("pageInfo")
                or existing["comments"].get("pageInfo")
                or {}
            )
    return list(threads_by_id.values()) + anonymous_threads


def collect_checks(pull_requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for pr in pull_requests:
        rollup = pr.get("statusCheckRollup") or {}
        contexts = rollup.get("contexts") or {}
        nodes.extend(contexts.get("nodes") or [])
    return nodes


def summarize_thread(thread: dict[str, Any], diff_id: str | None) -> dict[str, Any]:
    comments = (thread.get("comments") or {}).get("nodes") or []
    latest = comments[-1] if comments else {}
    first = comments[0] if comments else {}
    latest_author = (latest.get("author") or {}).get("login")
    first_body = (first.get("body") or "").strip().splitlines()
    return {
        "id": thread.get("id"),
        "url": latest.get("url"),
        "path": thread.get("path"),
        "line": thread.get("line"),
        "author": ((first.get("author") or {}).get("login")),
        "latest_comment_author": latest_author,
        "latest_comment_created_at": latest.get("createdAt"),
        "summary": first_body[0] if first_body else "",
        "is_outdated": bool(thread.get("isOutdated")),
        "is_resolved": bool(thread.get("isResolved")),
        "associated_diff_id": diff_id,
    }


def summarize_review_requests(
    nodes: list[dict[str, Any]],
) -> tuple[list[str], list[str]]:
    reviewers: list[str] = []
    teams: list[str] = []
    for node in nodes:
        requested = node.get("requestedReviewer") or {}
        if requested.get("__typename") == "Team":
            if requested.get("slug"):
                teams.append(requested["slug"])
        elif requested.get("login"):
            reviewers.append(requested["login"])
    return reviewers, teams


def normalize_check(node: dict[str, Any]) -> dict[str, Any]:
    if node.get("__typename") == "StatusContext":
        state = node.get("state")
        conclusion = "SUCCESS" if state == "SUCCESS" else state
        return {
            "name": node.get("context"),
            "status": state,
            "conclusion": conclusion,
        }
    return {
        "name": node.get("name"),
        "status": node.get("status"),
        "conclusion": node.get("conclusion"),
    }


def summarize_reviews(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "author": (node.get("author") or {}).get("login"),
            "state": node.get("state"),
            "body": node.get("body") or "",
            "submitted_at": node.get("submittedAt"),
            "url": node.get("url"),
        }
        for node in nodes
    ]


def summarize_comments(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "author": (node.get("author") or {}).get("login"),
            "body": node.get("body") or "",
            "created_at": node.get("createdAt"),
            "url": node.get("url"),
        }
        for node in nodes
    ]


def classify_blocker(
    pr: dict[str, Any],
    unresolved_threads: list[dict[str, Any]],
    requested_reviewers: list[str],
    requested_teams: list[str],
    checks: list[dict[str, Any]],
    pagination_complete: bool,
) -> str | None:
    if not pagination_complete:
        return "pagination_incomplete"
    if pr.get("isDraft"):
        return "draft_pr"
    if requested_reviewers or requested_teams:
        return "requested_reviewers"
    active_threads = [
        thread for thread in unresolved_threads if not thread["is_outdated"]
    ]
    outdated_threads = [
        thread for thread in unresolved_threads if thread["is_outdated"]
    ]
    if active_threads:
        return "unresolved_review_threads"
    if outdated_threads:
        return "outdated_unresolved_review_threads"
    if any(not check_successful(check) for check in checks):
        return "checks_not_successful"
    review_decision = pr.get("reviewDecision")
    if review_decision not in (None, "", "APPROVED"):
        return "review_not_approved"
    merge_state = pr.get("mergeStateStatus")
    mergeable = pr.get("mergeable")
    if merge_state not in ("CLEAN", "HAS_HOOKS"):
        return "merge_state_not_clean"
    if mergeable not in (None, "MERGEABLE"):
        return "merge_state_not_clean"
    return None


def check_successful(check: dict[str, Any]) -> bool:
    status = check.get("status")
    conclusion = check.get("conclusion")
    return status in (None, "COMPLETED", "SUCCESS") and conclusion in (
        None,
        "SUCCESS",
        "NEUTRAL",
        "SKIPPED",
    )


def page_infos(page: dict[str, Any]) -> dict[str, dict[str, Any]]:
    pr = extract_pr(page)
    rollup = pr.get("statusCheckRollup") or {}
    contexts = rollup.get("contexts") or {}
    return {
        "threads": ((pr.get("reviewThreads") or {}).get("pageInfo") or {}),
        "comments": ((pr.get("comments") or {}).get("pageInfo") or {}),
        "reviews": ((pr.get("reviews") or {}).get("pageInfo") or {}),
        "checks": (contexts.get("pageInfo") or {}),
        "review_requests": ((pr.get("reviewRequests") or {}).get("pageInfo") or {}),
    }


def next_cursor(
    connection: str,
    info: dict[str, Any],
    current_cursor: str | None,
    seen_cursors: set[str],
) -> str | None:
    if not info.get("hasNextPage"):
        return None
    cursor = info.get("endCursor")
    if not isinstance(cursor, str) or not cursor:
        raise PaginationError(f"{connection} pagination has no end cursor")
    if cursor == current_cursor or cursor in seen_cursors:
        raise PaginationError(f"{connection} pagination cursor did not progress")
    seen_cursors.add(cursor)
    return cursor


def is_pagination_complete(pull_requests: list[dict[str, Any]]) -> bool:
    if not pull_requests:
        return False
    last_infos = page_infos(
        {"data": {"repository": {"pullRequest": pull_requests[-1]}}}
    )
    top_level_complete = not any(
        (info or {}).get("hasNextPage") for info in last_infos.values()
    )
    comments_complete = True
    for thread in collect_review_threads(pull_requests):
        comments_info = (thread.get("comments") or {}).get("pageInfo") or {}
        if comments_info.get("hasNextPage"):
            comments_complete = False
            break
    return top_level_complete and comments_complete


def summary_text(state: dict[str, Any]) -> str:
    requested_reviewers = (
        ", ".join(state["github_state"]["requested_reviewers"]) or "none"
    )
    requested_teams = ", ".join(state["github_state"]["requested_teams"]) or "none"
    lines = [
        f"PR: {state['pr']['url']}",
        f"head_repository: {state['repo']['head_repository']}",
        f"next_blocker: {state['next_blocker'] or 'none'}",
        f"review_decision: {state['github_state']['review_decision'] or 'none'}",
        f"merge_state: {state['github_state']['merge_state'] or 'unknown'}",
        f"requested_reviewers: {requested_reviewers}",
        f"requested_teams: {requested_teams}",
        f"unresolved_threads: {len(state['github_state']['unresolved_threads'])}",
        f"checks: {len(state['github_state']['checks'])}",
    ]
    for thread in state["github_state"]["unresolved_threads"]:
        status = "outdated" if thread["is_outdated"] else "active"
        location = thread.get("path") or "unknown-path"
        if thread.get("line") is not None:
            location = f"{location}:{thread['line']}"
        lines.append(
            "unresolved_thread: "
            f"{status} {location} "
            f"author={thread.get('author') or 'unknown'} "
            f"url={thread.get('url') or 'none'} "
            f"summary={thread.get('summary') or ''}"
        )
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="Base repository as OWNER/REPO")
    parser.add_argument(
        "--pr",
        required=True,
        type=int,
        help="Pull request number in the base repository",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON state")
    parser.add_argument(
        "--typed-epoch",
        action="store_true",
        help="Print strict typed response-source evidence",
    )
    parser.add_argument(
        "--summary", action="store_true", help="Print terse human summary"
    )
    parser.add_argument(
        "--fixture",
        action="append",
        type=Path,
        help="Read one or more fixture pages instead of calling gh",
    )
    return parser.parse_args(argv)


def load_fixture_page(path: Path) -> dict[str, Any]:
    try:
        page = strict_json(path.read_text(encoding="utf-8"), f"fixture page {path}")
    except (OSError, ResponseShapeError) as error:
        raise ResponseShapeError(
            f"could not load fixture page {path}: {error}"
        ) from error
    if not isinstance(page, dict):
        raise ResponseShapeError(f"fixture page {path} was not an object")
    return page


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.fixture:
        pages = [load_fixture_page(path) for path in args.fixture]
    else:
        pages = fetch_pages(args.repo, args.pr)
    if args.typed_epoch:
        epoch = typed_epoch_from_pages(args.repo, pages, pr_number=args.pr)
        print(json.dumps(epoch, indent=2, sort_keys=True))
        return 0
    state = state_from_pages(args.repo, pages, pr_number=args.pr)
    if args.json or not args.summary:
        print(json.dumps(state, indent=2, sort_keys=True))
    if args.summary:
        print(summary_text(state))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
