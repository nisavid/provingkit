#!/usr/bin/env python3
"""Operation-specific GitHub adapters for one Mergecraft response."""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

GITHUB_HOST = "github.com"
WRITE_TIMEOUT_SECONDS = 30


class GhTransportError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status: str = "unknown",
        retryable: bool = False,
        side_effect: str = "unknown",
        evidence: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.retryable = retryable
        self.side_effect = side_effect
        self.evidence = evidence or {}


def _split_repo(repo: str) -> tuple[str, str]:
    if re.fullmatch(r"[^/\s]+/[^/\s]+", repo) is None:
        raise ValueError("repo must be OWNER/REPO")
    return tuple(repo.split("/", 1))  # type: ignore[return-value]


def _json_object(content: bytes, source: str) -> dict[str, Any]:
    try:
        value = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GhTransportError(f"{source} returned invalid UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise GhTransportError(f"{source} returned a non-object JSON value")
    return value


class GhJsonTransport:
    """Execute gh with argv-only routing and one typed JSON stdin value."""

    def __init__(self, program_argv: list[str] | None = None) -> None:
        self.program_argv = list(program_argv or ["gh"])
        if not self.program_argv or any(not item for item in self.program_argv):
            raise ValueError("program_argv must contain nonempty argv values")

    def request(
        self, method: str, endpoint: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        command = [
            *self.program_argv,
            "api",
            "--hostname",
            GITHUB_HOST,
        ]
        if method != "GET":
            command.extend(["--method", method])
        command.append(endpoint)
        if payload is not None:
            command.extend(["--input", "-"])
        request_bytes = (
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
                "utf-8"
            )
            if payload is not None
            else None
        )
        environment = dict(os.environ)
        environment.pop("GH_HOST", None)
        environment.pop("GH_REPO", None)
        environment.update({"GH_PROMPT_DISABLED": "1", "GIT_TERMINAL_PROMPT": "0"})
        try:
            completed = subprocess.run(
                command,
                input=request_bytes,
                capture_output=True,
                check=False,
                timeout=WRITE_TIMEOUT_SECONDS,
                env=environment,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise GhTransportError(f"gh transport did not complete: {error}") from error
        if completed.returncode:
            detail_bytes = completed.stderr or completed.stdout
            detail = detail_bytes.decode("utf-8", errors="replace").strip()
            status_match = re.search(r"(?:HTTP\s+|status[=: ]+)(\d{3})", detail)
            http_status = int(status_match.group(1)) if status_match else None
            graphql_read_query = method == "POST" and endpoint == "graphql"
            proven_no_write = (
                method == "POST"
                and endpoint != "graphql"
                and http_status in {400, 401, 404, 409, 422}
            )
            confirmed_failure = graphql_read_query or proven_no_write
            transport_operation = (
                "graphql_read_query"
                if graphql_read_query
                else "response_write"
                if method == "POST"
                else "response_reread"
            )
            raise GhTransportError(
                detail or "gh api failed",
                status="confirmed_failure" if confirmed_failure else "unknown",
                retryable=bool(proven_no_write and http_status == 409),
                side_effect="none" if confirmed_failure else "unknown",
                evidence={"transport_operation": transport_operation},
            )
        return _json_object(completed.stdout, f"{method} {endpoint}")


def _load_acquisition_module() -> Any:
    path = (
        Path(__file__).resolve().parents[2]
        / "addressing-pr-review-feedback/scripts/review_feedback_state.py"
    )
    spec = importlib.util.spec_from_file_location(
        "mergecraft_feedback_acquisition", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load Mergecraft feedback acquisition")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TypedEpochAdapter:
    """Acquire a complete strict feedback epoch through the real GraphQL shape."""

    def __init__(self, transport: GhJsonTransport | None = None) -> None:
        self.transport = transport or GhJsonTransport()
        self.acquisition = _load_acquisition_module()

    def _graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        return self.transport.request(
            "POST", "graphql", {"query": query, "variables": variables}
        )

    def acquire(self, repo: str, pr_number: int) -> dict[str, Any]:
        try:
            return self._acquire(repo, pr_number)
        except self.acquisition.FeedbackAcquisitionError as error:
            raise GhTransportError(
                f"feedback acquisition failed closed: {error}",
                status="confirmed_failure",
                retryable=True,
                side_effect="none",
                evidence={"transport_operation": "graphql_read_query"},
            ) from error

    def _acquire(self, repo: str, pr_number: int) -> dict[str, Any]:
        module = self.acquisition
        acquisition_start = module.local_acquisition_observation("start")
        pages: list[dict[str, Any]] = []
        pagination_collections = {key: [] for key in module.CONNECTION_KEYS}
        cursors = {key: None for key in module.CONNECTION_KEYS}
        include = {key: True for key in module.CONNECTION_KEYS}
        expected_identity = None
        seen_cursors = {key: set() for key in module.CONNECTION_KEYS}
        while True:
            if len(pages) >= module.MAX_TOP_LEVEL_PAGES:
                raise module.PaginationError("top-level pagination exceeded limit")
            query, variables = module.build_pr_query(
                repo, pr_number, cursors, include=include
            )
            page = self._graphql(query, variables)
            module.validate_pr_page(page, include, "paginated page")
            page_identity = module.pull_request_identity(page)
            if expected_identity is None:
                module.validate_requested_identity(repo, pr_number, page_identity)
                expected_identity = page_identity
            else:
                module.validate_matching_identity(
                    expected_identity, page_identity, "paginated page"
                )
            pages.append(page)
            page_info = module.page_infos(page)
            pr = module.extract_pr(page)
            for key in module.CONNECTION_KEYS:
                if not include.get(key):
                    continue
                connection = module._pr_connection(
                    pr, key, True, "retained pagination evidence"
                )
                pagination_collections[key].append(
                    {
                        "page_index": len(pagination_collections[key]),
                        "request_cursor": cursors[key],
                        "node_count": len(connection.get("nodes") or []),
                        "has_next_page": page_info[key].get("hasNextPage"),
                        "end_cursor": page_info[key].get("endCursor"),
                    }
                )
            next_cursors = {
                key: module.next_cursor(
                    key, page_info[key], cursors[key], seen_cursors[key]
                )
                for key in module.CONNECTION_KEYS
            }
            if not any(next_cursors.values()):
                break
            include = {key: value is not None for key, value in next_cursors.items()}
            cursors = next_cursors

        assert expected_identity is not None
        hydrated_threads_by_id: dict[str, dict[str, Any]] = {}
        for page in pages:
            for thread in (module.extract_pr(page).get("reviewThreads") or {}).get(
                "nodes"
            ) or []:
                comments = thread.get("comments") or {}
                page_info = comments.get("pageInfo") or {}
                cursor = None
                seen: set[str] = set()
                count = 0
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
                    if count >= module.MAX_THREAD_COMMENT_PAGES:
                        raise module.PaginationError(
                            "thread comments pagination exceeded limit"
                        )
                    cursor = module.next_cursor(
                        "thread comments", page_info, cursor, seen
                    )
                    query, variables = module.build_thread_comments_query(
                        thread["id"], cursor
                    )
                    next_page = self._graphql(query, variables)
                    module.validate_thread_comments_page(
                        next_page, f"thread {thread['id']} comment page"
                    )
                    module.validate_matching_identity(
                        expected_identity,
                        module.thread_comments_identity(next_page),
                        f"thread {thread['id']} comment page",
                    )
                    next_comments = (
                        (next_page.get("data") or {}).get("node") or {}
                    ).get("comments") or {}
                    comments.setdefault("nodes", []).extend(
                        next_comments.get("nodes") or []
                    )
                    page_info = next_comments.get("pageInfo") or {}
                    comments["pageInfo"] = page_info
                    count += 1
                    thread_pages.append(
                        {
                            "page_index": count,
                            "request_cursor": cursor,
                            "node_count": len(next_comments.get("nodes") or []),
                            "has_next_page": page_info.get("hasNextPage"),
                            "end_cursor": page_info.get("endCursor"),
                        }
                    )
                hydration = {
                    "thread_node_id": thread["id"],
                    "complete": True,
                    "comment_count": len(comments.get("nodes") or []),
                    "terminal_end_cursor": page_info.get("endCursor"),
                    "pages": thread_pages,
                }
                prior_hydration = hydrated_threads_by_id.get(thread["id"])
                if prior_hydration is not None and prior_hydration != hydration:
                    raise module.IdentityError(
                        f"thread {thread['id']} had contradictory pagination evidence"
                    )
                hydrated_threads_by_id[thread["id"]] = hydration
        acquisition_end = module.local_acquisition_observation("end")
        pagination_evidence = {
            "complete": True,
            "collections": {
                key: {
                    "complete": True,
                    "node_count": sum(page["node_count"] for page in value),
                    "pages": value,
                }
                for key, value in pagination_collections.items()
            },
            "hydrated_threads": list(hydrated_threads_by_id.values()),
        }
        return module.typed_epoch_from_pages(
            repo,
            pages,
            pr_number=pr_number,
            acquisition_start_observation=acquisition_start,
            acquisition_end_observation=acquisition_end,
            pagination_evidence=pagination_evidence,
        )


def _body_text(exact_body: bytes) -> str:
    try:
        value = exact_body.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("writer body must be exact UTF-8 bytes") from error
    if value.encode("utf-8") != exact_body:
        raise ValueError("writer body did not round-trip as UTF-8")
    return value


def _response_object_kind(operation: str) -> str:
    return {
        "create_inline_reply": "PullRequestReviewComment",
        "create_pull_request_conversation_comment": "IssueComment",
    }[operation]


def _identity_evidence(operation: str, value: dict[str, Any]) -> dict[str, Any]:
    return {
        "object_kind": _response_object_kind(operation),
        "database_id": value.get("id", value.get("database_id")),
        "node_id": value.get("node_id"),
    }


def _validated_response_identity(
    operation: str, value: dict[str, Any], source: str
) -> dict[str, Any]:
    identity = _identity_evidence(operation, value)
    if (
        type(identity["database_id"]) is not int
        or identity["database_id"] <= 0
        or not isinstance(identity["node_id"], str)
        or not identity["node_id"]
    ):
        raise ValueError(f"{source} lacked complete typed response identity")
    return identity


def _validated_requested_identity(
    operation: str, identity: dict[str, Any]
) -> dict[str, Any]:
    if identity.get("object_kind") != _response_object_kind(operation):
        raise ValueError("reread identity is not operation-specific")
    return _validated_response_identity(operation, identity, "requested reread")


def _receipt(
    *,
    operation: str,
    endpoint: str,
    reread_endpoint: str,
    exact_body: bytes,
    created: dict[str, Any],
    requested_identity: dict[str, Any],
    reread: dict[str, Any],
    expected_actor_login: str,
) -> dict[str, Any]:
    created_identity = _identity_evidence(operation, created)
    reread_identity = _identity_evidence(operation, reread)
    identity_evidence = {
        "created_response_identity": created_identity,
        "requested_reread_identity": requested_identity,
        "reread_response_identity": reread_identity,
    }
    reread_body = reread.get("body")
    user = reread.get("user")
    actor = user.get("login") if isinstance(user, dict) else None
    try:
        created_identity = _validated_response_identity(
            operation, created, "create response"
        )
        requested_identity = _validated_requested_identity(
            operation, requested_identity
        )
        reread_identity = _validated_response_identity(
            operation, reread, "stable reread"
        )
    except ValueError as error:
        raise GhTransportError(
            str(error),
            status="unknown",
            side_effect="unknown",
            evidence=identity_evidence,
        ) from error
    if not (created_identity == requested_identity == reread_identity):
        raise GhTransportError(
            "created, requested, and reread response identities did not match",
            status="unknown",
            side_effect="unknown",
            evidence=identity_evidence,
        )
    if not isinstance(reread_body, str) or not isinstance(actor, str):
        raise GhTransportError(
            "stable reread lacked body or actor",
            status="unknown",
            side_effect="unknown",
            evidence=identity_evidence,
        )
    reread_bytes = reread_body.encode("utf-8")
    if reread_bytes != exact_body or actor != expected_actor_login:
        raise GhTransportError(
            "stable reread did not match exact body and writer identity",
            status="unknown",
            side_effect="unknown",
            evidence=identity_evidence,
        )
    return {
        "schema_version": 1,
        "status": "confirmed_success",
        "operation": operation,
        "request_endpoint": endpoint,
        "reread_endpoint": reread_endpoint,
        "request_body_utf8_base64": base64.b64encode(exact_body).decode("ascii"),
        "request_body_sha256": hashlib.sha256(exact_body).hexdigest(),
        "created_response_identity": created_identity,
        "requested_reread_identity": requested_identity,
        "reread_response_identity": reread_identity,
        "response": {
            "node_id": reread_identity["node_id"],
            "database_id": reread_identity["database_id"],
            "object_kind": reread_identity["object_kind"],
            "permalink": reread.get("html_url"),
            "actor_login": actor,
        },
        "reread_body_utf8_base64": base64.b64encode(reread_bytes).decode("ascii"),
        "reread_body_sha256": hashlib.sha256(reread_bytes).hexdigest(),
        "exact_reread": True,
    }


class InlineReplyAdapter:
    """Create exactly one reply in an existing pull-request review thread."""

    def __init__(self, transport: GhJsonTransport | None = None) -> None:
        self.transport = transport or GhJsonTransport()

    def create_and_reread(
        self,
        *,
        repo: str,
        pr_number: int,
        root_comment_database_id: int,
        exact_body: bytes,
        expected_actor_login: str,
    ) -> dict[str, Any]:
        _split_repo(repo)
        if type(pr_number) is not int or pr_number <= 0:
            raise ValueError("pr_number must be a positive integer")
        if type(root_comment_database_id) is not int or root_comment_database_id <= 0:
            raise ValueError("root_comment_database_id must be a positive integer")
        body = _body_text(exact_body)
        endpoint = (
            f"/repos/{repo}/pulls/{pr_number}/comments/"
            f"{root_comment_database_id}/replies"
        )
        created = self.transport.request("POST", endpoint, {"body": body})
        try:
            requested_identity = _validated_response_identity(
                "create_inline_reply", created, "create response"
            )
        except ValueError as error:
            raise GhTransportError(
                str(error),
                status="unknown",
                side_effect="unknown",
                evidence={
                    "created_response_identity": _identity_evidence(
                        "create_inline_reply", created
                    )
                },
            ) from error
        response_id = requested_identity["database_id"]
        reread_endpoint = f"/repos/{repo}/pulls/comments/{response_id}"
        try:
            reread = self.transport.request("GET", reread_endpoint)
            return _receipt(
                operation="create_inline_reply",
                endpoint=endpoint,
                reread_endpoint=reread_endpoint,
                exact_body=exact_body,
                created=created,
                requested_identity=requested_identity,
                reread=reread,
                expected_actor_login=expected_actor_login,
            )
        except GhTransportError as error:
            error.evidence.update(
                {"create_response": created, "request_endpoint": endpoint}
            )
            raise

    def reread_known(
        self,
        *,
        repo: str,
        response_identity: dict[str, Any],
        exact_body: bytes,
        expected_actor_login: str,
    ) -> dict[str, Any]:
        _split_repo(repo)
        requested_identity = _validated_requested_identity(
            "create_inline_reply", response_identity
        )
        endpoint = f"/repos/{repo}/pulls/comments/{requested_identity['database_id']}"
        reread = self.transport.request("GET", endpoint)
        return _receipt(
            operation="create_inline_reply",
            endpoint="reconciled_same_intent_request",
            reread_endpoint=endpoint,
            exact_body=exact_body,
            created=response_identity,
            requested_identity=requested_identity,
            reread=reread,
            expected_actor_login=expected_actor_login,
        )


class PullRequestConversationAdapter:
    """Create one top-level conversation response on a verified pull request."""

    def __init__(self, transport: GhJsonTransport | None = None) -> None:
        self.transport = transport or GhJsonTransport()

    def create_and_reread(
        self,
        *,
        repo: str,
        pr_number: int,
        pr_node_id: str,
        verification_epoch_id: str,
        source_permalink: str,
        exact_body: bytes,
        expected_actor_login: str,
    ) -> dict[str, Any]:
        _split_repo(repo)
        if (
            type(pr_number) is not int
            or pr_number <= 0
            or not pr_node_id
            or not verification_epoch_id
        ):
            raise ValueError(
                "top-level response requires typed pull request verification"
            )
        body = _body_text(exact_body)
        if not source_permalink or source_permalink not in body:
            raise ValueError(
                "top-level writer body must already contain the natural source permalink"
            )
        endpoint = f"/repos/{repo}/issues/{pr_number}/comments"
        created = self.transport.request("POST", endpoint, {"body": body})
        try:
            requested_identity = _validated_response_identity(
                "create_pull_request_conversation_comment", created, "create response"
            )
        except ValueError as error:
            raise GhTransportError(
                str(error),
                status="unknown",
                side_effect="unknown",
                evidence={
                    "created_response_identity": _identity_evidence(
                        "create_pull_request_conversation_comment", created
                    )
                },
            ) from error
        response_id = requested_identity["database_id"]
        reread_endpoint = f"/repos/{repo}/issues/comments/{response_id}"
        try:
            reread = self.transport.request("GET", reread_endpoint)
            return _receipt(
                operation="create_pull_request_conversation_comment",
                endpoint=endpoint,
                reread_endpoint=reread_endpoint,
                exact_body=exact_body,
                created=created,
                requested_identity=requested_identity,
                reread=reread,
                expected_actor_login=expected_actor_login,
            )
        except GhTransportError as error:
            error.evidence.update(
                {"create_response": created, "request_endpoint": endpoint}
            )
            raise

    def reread_known(
        self,
        *,
        repo: str,
        response_identity: dict[str, Any],
        exact_body: bytes,
        expected_actor_login: str,
    ) -> dict[str, Any]:
        _split_repo(repo)
        requested_identity = _validated_requested_identity(
            "create_pull_request_conversation_comment", response_identity
        )
        endpoint = f"/repos/{repo}/issues/comments/{requested_identity['database_id']}"
        reread = self.transport.request("GET", endpoint)
        return _receipt(
            operation="create_pull_request_conversation_comment",
            endpoint="reconciled_same_intent_request",
            reread_endpoint=endpoint,
            exact_body=exact_body,
            created=response_identity,
            requested_identity=requested_identity,
            reread=reread,
            expected_actor_login=expected_actor_login,
        )
