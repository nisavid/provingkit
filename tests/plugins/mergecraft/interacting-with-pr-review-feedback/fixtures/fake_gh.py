#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

state_path = Path(sys.argv[1])
argv = sys.argv[2:]
request_text = sys.stdin.read()
request = json.loads(request_text) if request_text else None
state = json.loads(state_path.read_text(encoding="utf-8"))


def validate_acquisition_query(query):
    compact = " ".join(query.split())
    actor_fragment = (
        "fragment ActorIdentity on Actor { __typename login ... on Node { id } }"
    )
    review_comment_fragment = (
        "fragment ReviewCommentEvidence on PullRequestReviewComment { "
        "id databaseId author { ...ActorIdentity } authorAssociation body "
        "createdAt updatedAt url path line originalLine originalPosition "
        "originalStartLine outdated startLine subjectType state "
        "replyTo { id databaseId } commit { oid } "
        "originalCommit { oid } "
        "pullRequestReview { id databaseId } }"
    )
    required = [actor_fragment, review_comment_fragment]
    if "query PrReviewState(" in compact:
        required.extend(
            [
                (
                    "fragment IssueCommentEvidence on IssueComment { id databaseId "
                    "author { ...ActorIdentity } authorAssociation body createdAt "
                    "updatedAt url }"
                ),
                (
                    "fragment ReviewEvidence on PullRequestReview { id databaseId "
                    "author { ...ActorIdentity } authorAssociation state body "
                    "createdAt submittedAt updatedAt url commit { oid } }"
                ),
                (
                    "id isResolved isOutdated path line diffSide originalLine "
                    "originalStartLine startDiffSide startLine subjectType "
                    "comments(first: 100)"
                ),
                "comments(first: 100) { nodes { ...ReviewCommentEvidence }",
                (
                    "comments(first: 100, after: $commentsCursor) "
                    "@include(if: $includeComments) { "
                    "nodes { ...IssueCommentEvidence }"
                ),
                (
                    "reviews(first: 100, after: $reviewsCursor) "
                    "@include(if: $includeReviews) { nodes { ...ReviewEvidence }"
                ),
            ]
        )
    elif "query ThreadComments(" in compact:
        required.append(
            "comments(first: 100, after: $commentsCursor) { "
            "nodes { ...ReviewCommentEvidence }"
        )
    else:
        return "unsupported GraphQL acquisition query"
    if re.search(r"author\s*\{\s*__typename\s+id\b", query):
        return "acquisition query selected id directly on Actor"
    missing = [selection for selection in required if selection not in compact]
    if missing:
        return "acquisition query did not request exact fixture source fields"
    return None


method = "GET"
if "--method" in argv:
    method = argv[argv.index("--method") + 1]
endpoint = next(
    item for item in argv if item.startswith("/repos/") or item == "graphql"
)
if endpoint == "graphql":
    operation = "graphql_read_query"
elif method == "POST":
    operation = "response_write"
else:
    operation = "response_reread"
state.setdefault("calls", []).append(
    {"argv": argv, "request": request, "operation": operation}
)
key = f"{method} {endpoint}"
if endpoint == "graphql" and method != "POST":
    response = {
        "returncode": 2,
        "stderr": "GraphQL query bodies require explicit POST transport",
    }
else:
    queued = state.get("queued", {}).get(key, [])
    response = queued.pop(0) if queued else None

if response is None and endpoint == "graphql":
    if not isinstance(request, dict) or not isinstance(request.get("query"), str):
        response = {"returncode": 2, "stderr": "GraphQL POST lacked query document"}
    elif not isinstance(request.get("variables"), dict):
        response = {"returncode": 2, "stderr": "GraphQL POST lacked variables"}
    else:
        query_error = validate_acquisition_query(request["query"])
        response = (
            {"returncode": 2, "stderr": query_error}
            if query_error
            else {"returncode": 0, "json": state["graphql"]}
        )
elif response is None and method == "POST" and endpoint.startswith("/repos/"):
    response_id = state.setdefault("next_id", 900)
    state["next_id"] = response_id + 1
    object_kind = "inline" if "/replies" in endpoint else "conversation"
    created = {
        "id": response_id,
        "node_id": f"RESPONSE_node_{response_id}",
        "body": request["body"],
        "html_url": f"https://github.com/example/repo/pull/7#response-{response_id}",
        "user": {"login": state.get("actor", "ivan")},
        "kind": object_kind,
    }
    state.setdefault("objects", {})[str(response_id)] = created
    response = {"returncode": 0, "json": created}
elif response is None and method == "GET":
    response_id = endpoint.rsplit("/", 1)[-1]
    created = state.get("objects", {}).get(response_id)
    override = state.get("reread_overrides", {}).get(response_id)
    if created is not None and isinstance(override, dict):
        created = {**created, **override}
    response = (
        {"returncode": 0, "json": created}
        if created is not None
        else {"returncode": 1, "stderr": "HTTP 404"}
    )

state_path.write_text(
    json.dumps(state, ensure_ascii=False, sort_keys=True), encoding="utf-8"
)
if response.get("stdout") is not None:
    sys.stdout.write(response["stdout"])
elif "json" in response:
    sys.stdout.write(json.dumps(response["json"], ensure_ascii=False))
sys.stderr.write(response.get("stderr", ""))
raise SystemExit(response.get("returncode", 0))
