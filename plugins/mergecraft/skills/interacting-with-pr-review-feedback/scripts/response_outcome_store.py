#!/usr/bin/env python3
"""Crash-recoverable semantic transition storage for Mergecraft responses."""

from __future__ import annotations

import base64
import copy
import fcntl
import hashlib
import json
import os
import re
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from response_identity_lifecycle import ResponseIdentityAuthority, ResponseIdentityError
from response_source_owner import (
    SourceOwnerIdentityError,
    owner_uses_supported_digests,
    source_owner_from_epoch,
    source_owner_from_record,
)

LEGACY_NAMES = (
    "bindings.jsonl",
    "attempts.jsonl",
    "leaf_receipts.jsonl",
    "outcomes.jsonl",
)
FORMAT_MARKER_NAME = "response-outcome-bundle-v2.json"
FORMAT_MARKER = {
    "canonical_json": "utf8-sort-keys-compact",
    "format": "mergecraft-response-outcome-bundle",
    "record_schema": "atomic-semantic-transitions-v2",
    "version": 2,
}
RECORD_KINDS = {
    "ordinary_admission",
    "follow_up_admission",
    "carry_forward",
    "prewrite_validation_started",
    "prewrite_invalidated",
    "write_started",
    "attempt_resolution",
    "reconciliation_started",
    "reconciliation_resolution",
    "replacement_basis",
    "replacement_transition",
}
RECORD_NAME = re.compile(r"^(\d{20})-([0-9a-f]{64})\.json$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class OutcomeStoreError(RuntimeError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _invalid(message: str, record_id: str | None = None) -> OutcomeStoreError:
    suffix = f" in record {record_id}" if record_id else ""
    return OutcomeStoreError(f"invalid-response-outcome-bundle: {message}{suffix}")


def _exact(value: Any, keys: set[str], name: str, record_id: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise _invalid(f"invalid {name} field set", record_id)
    return value


def _text(value: Any, name: str, record_id: str) -> str:
    if not isinstance(value, str) or not value:
        raise _invalid(f"{name} must be nonempty text", record_id)
    return value


def _positive(value: Any, name: str, record_id: str) -> int:
    if type(value) is not int or value <= 0:
        raise _invalid(f"{name} must be a positive integer", record_id)
    return value


def _sha(value: Any, name: str, record_id: str) -> str:
    if not isinstance(value, str) or SHA256.fullmatch(value) is None:
        raise _invalid(f"{name} must be lowercase hexadecimal SHA-256", record_id)
    return value


def _optional_link(value: Any, name: str, record_id: str) -> str | None:
    if value is None:
        return None
    return _text(value, name, record_id)


def _identity(value: Any, name: str, record_id: str) -> tuple[str, int, str]:
    item = _exact(value, {"object_kind", "database_id", "node_id"}, name, record_id)
    return (
        _text(item["object_kind"], f"{name}.object_kind", record_id),
        _positive(item["database_id"], f"{name}.database_id", record_id),
        _text(item["node_id"], f"{name}.node_id", record_id),
    )


def _provider_identity(value: Any, name: str, record_id: str) -> tuple[int, str]:
    item = _exact(value, {"database_id", "node_id"}, name, record_id)
    return (
        _positive(item["database_id"], f"{name}.database_id", record_id),
        _text(item["node_id"], f"{name}.node_id", record_id),
    )


def _body(value: Any, name: str, record_id: str, *, allow_empty: bool = False) -> bytes:
    item = _exact(value, {"utf8_base64", "byte_length", "sha256"}, name, record_id)
    encoded = item["utf8_base64"]
    if not isinstance(encoded, str) or (not encoded and not allow_empty):
        raise _invalid(f"{name}.utf8_base64 must be nonempty text", record_id)
    try:
        raw = base64.b64decode(encoded, validate=True)
        raw.decode("utf-8")
    except (ValueError, UnicodeDecodeError) as error:
        raise _invalid(f"{name} is not canonical UTF-8 base64", record_id) from error
    if (
        item["byte_length"] != len(raw)
        or item["sha256"] != hashlib.sha256(raw).hexdigest()
    ):
        raise _invalid(f"{name} byte identity is contradictory", record_id)
    return raw


def _canonical_utf8_wrapper(
    value: Any, name: str, record_id: str, *, require_json: bool
) -> tuple[bytes, Any]:
    item = _exact(
        value,
        {"canonical_utf8_base64", "byte_length", "sha256"},
        name,
        record_id,
    )
    encoded = item["canonical_utf8_base64"]
    if not isinstance(encoded, str) or not encoded:
        raise _invalid(f"{name}.canonical_utf8_base64 must be nonempty text", record_id)
    try:
        raw = base64.b64decode(encoded, validate=True)
        text = raw.decode("utf-8")
    except (TypeError, ValueError, UnicodeDecodeError) as error:
        raise _invalid(f"{name} is not exact UTF-8 base64", record_id) from error
    if (
        item["byte_length"] != len(raw)
        or item["sha256"] != hashlib.sha256(raw).hexdigest()
    ):
        raise _invalid(f"{name} byte identity is contradictory", record_id)
    if not require_json:
        return raw, text
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError as error:
        raise _invalid(f"{name} is not canonical JSON", record_id) from error
    if not isinstance(decoded, dict) or canonical_bytes(decoded) != raw:
        raise _invalid(f"{name} is not canonical JSON", record_id)
    return raw, decoded


REPLACEMENT_ARTIFACT_COMMON_FIELDS = {
    "schema_version",
    "artifact_kind",
    "replacement_basis_id",
    "predecessor_intent_id",
    "predecessor_validation_id",
    "terminal_state",
    "terminal_record_id",
    "terminal_record_sha256",
    "successor_epoch_id",
    "successor_epoch_sha256",
    "source_scope_digest",
    "operation",
    "placement",
}

REPLACEMENT_ARTIFACT_VARIANT_FIELDS = {
    "classification": {"result", "evidence_id"},
    "adjudication": {
        "disposition",
        "evidence_id",
        "classification_artifact_sha256",
    },
    "authority": {
        "decision",
        "evidence_id",
        "actor_login",
        "classification_artifact_sha256",
        "adjudication_artifact_sha256",
    },
    "writer_result": {
        "identity",
        "contract",
        "contract_version",
        "field",
        "body",
        "classification_artifact_sha256",
        "adjudication_artifact_sha256",
        "authority_artifact_sha256",
    },
}


def _replacement_artifact(
    value: Any, kind: str, record_id: str
) -> tuple[dict[str, Any], str]:
    _, decoded = _canonical_utf8_wrapper(
        value, f"{kind}_artifact", record_id, require_json=True
    )
    _exact(
        decoded,
        REPLACEMENT_ARTIFACT_COMMON_FIELDS | REPLACEMENT_ARTIFACT_VARIANT_FIELDS[kind],
        f"decoded {kind} artifact",
        record_id,
    )
    if decoded["schema_version"] != 1 or decoded["artifact_kind"] != kind:
        raise _invalid(f"{kind} artifact variant is contradictory", record_id)
    for name in (
        "replacement_basis_id",
        "predecessor_intent_id",
        "predecessor_validation_id",
        "terminal_state",
        "terminal_record_id",
        "successor_epoch_id",
        "operation",
    ):
        _text(decoded[name], f"{kind}.{name}", record_id)
    for name in (
        "terminal_record_sha256",
        "successor_epoch_sha256",
        "source_scope_digest",
    ):
        _sha(decoded[name], f"{kind}.{name}", record_id)
    if not isinstance(decoded["placement"], dict):
        raise _invalid(f"{kind}.placement must be typed", record_id)
    if kind == "classification":
        if decoded["result"] not in {"human_feedback", "automated_feedback"}:
            raise _invalid("classification artifact result is unsupported", record_id)
        _text(decoded["evidence_id"], "classification.evidence_id", record_id)
    elif kind == "adjudication":
        if decoded["disposition"] != "respond":
            raise _invalid(
                "adjudication artifact does not authorize response", record_id
            )
        _text(decoded["evidence_id"], "adjudication.evidence_id", record_id)
        _sha(
            decoded["classification_artifact_sha256"],
            "adjudication.classification_artifact_sha256",
            record_id,
        )
    elif kind == "authority":
        if decoded["decision"] != "authorized":
            raise _invalid("authority artifact does not authorize response", record_id)
        for name in ("evidence_id", "actor_login"):
            _text(decoded[name], f"authority.{name}", record_id)
        for name in (
            "classification_artifact_sha256",
            "adjudication_artifact_sha256",
        ):
            _sha(decoded[name], f"authority.{name}", record_id)
    else:
        for name in ("identity", "contract", "contract_version", "field"):
            _text(decoded[name], f"writer_result.{name}", record_id)
        _canonical_utf8_wrapper(
            decoded["body"], "writer_result.body", record_id, require_json=False
        )
        for name in (
            "classification_artifact_sha256",
            "adjudication_artifact_sha256",
            "authority_artifact_sha256",
        ):
            _sha(decoded[name], f"writer_result.{name}", record_id)
    return decoded, value["sha256"]


def validate_replacement_artifact_set(
    artifacts: dict[str, Any], basis: dict[str, Any], record_id: str
) -> tuple[dict[str, dict[str, Any]], bytes]:
    decoded: dict[str, dict[str, Any]] = {}
    digests: dict[str, str] = {}
    for kind in (
        "classification",
        "adjudication",
        "authority",
        "writer_result",
    ):
        decoded[kind], digests[kind] = _replacement_artifact(
            artifacts[f"{kind}_artifact"], kind, record_id
        )
    common = {
        "schema_version": 1,
        "replacement_basis_id": basis["basis_id"],
        "predecessor_intent_id": basis["predecessor_intent_id"],
        "predecessor_validation_id": basis["predecessor_validation_id"],
        "terminal_state": basis["terminal_state"],
        "terminal_record_id": basis["terminal_record_id"],
        "terminal_record_sha256": basis["terminal_record_sha256"],
        "successor_epoch_id": basis["successor_epoch_id"],
        "successor_epoch_sha256": basis["successor_epoch_sha256"],
        "source_scope_digest": basis["source_scope_digest"],
        "operation": basis["operation"],
        "placement": basis["placement"],
    }
    for kind, artifact in decoded.items():
        actual = {name: artifact[name] for name in common}
        if actual != common:
            raise _invalid(
                f"{kind} artifact does not bind the retained basis", record_id
            )
    if (
        decoded["adjudication"]["classification_artifact_sha256"]
        != digests["classification"]
        or decoded["authority"]["classification_artifact_sha256"]
        != digests["classification"]
        or decoded["authority"]["adjudication_artifact_sha256"]
        != digests["adjudication"]
        or decoded["writer_result"]["classification_artifact_sha256"]
        != digests["classification"]
        or decoded["writer_result"]["adjudication_artifact_sha256"]
        != digests["adjudication"]
        or decoded["writer_result"]["authority_artifact_sha256"] != digests["authority"]
    ):
        raise _invalid(
            "replacement artifact cross-digests are contradictory", record_id
        )
    body, _ = _canonical_utf8_wrapper(
        decoded["writer_result"]["body"],
        "writer_result.body",
        record_id,
        require_json=False,
    )
    return decoded, body


def _reason_variant(
    value: Any, name: str, availability: str, record_id: str
) -> dict[str, Any]:
    item = _exact(value, {"availability", "reason"}, name, record_id)
    if item["availability"] != availability:
        raise _invalid(f"{name} has the wrong availability variant", record_id)
    _text(item["reason"], f"{name}.reason", record_id)
    return item


def _revision(value: Any, name: str, record_id: str) -> None:
    if isinstance(value, dict) and value.get("availability") == "available":
        item = _exact(value, {"availability", "oid"}, name, record_id)
        _text(item["oid"], f"{name}.oid", record_id)
        return
    _reason_variant(value, name, "unavailable", record_id)


def _author(value: Any, name: str, record_id: str) -> None:
    if isinstance(value, dict) and value.get("availability") == "available":
        item = _exact(
            value,
            {"availability", "node_id", "login", "provider_type", "association"},
            name,
            record_id,
        )
        for field in ("node_id", "login", "provider_type", "association"):
            _text(item[field], f"{name}.{field}", record_id)
        return
    item = _exact(value, {"availability", "reason", "association"}, name, record_id)
    if item["availability"] != "unavailable":
        raise _invalid(f"{name} has the wrong availability variant", record_id)
    _text(item["reason"], f"{name}.reason", record_id)
    _text(item["association"], f"{name}.association", record_id)


def _source_revision_identity(
    value: Any, record_id: str, *, allow_empty_body: bool = False
) -> None:
    item = _exact(
        value,
        {"body", "provider_revision", "associated_commit"},
        "source_revision_identity",
        record_id,
    )
    _body(
        item["body"],
        "source_revision_identity.body",
        record_id,
        allow_empty=allow_empty_body,
    )
    provider_revision = _exact(
        item["provider_revision"],
        {"availability", "kind", "value"},
        "provider_revision",
        record_id,
    )
    if provider_revision["availability"] != "available":
        raise _invalid("provider revision is unavailable", record_id)
    _text(provider_revision["kind"], "provider_revision.kind", record_id)
    _text(provider_revision["value"], "provider_revision.value", record_id)
    _revision(item["associated_commit"], "associated_commit", record_id)


def _source(
    value: Any, record_id: str, *, allow_empty_body: bool = False
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _invalid("source must be an object", record_id)
    kind = value.get("kind")
    common = {
        "kind",
        "provider_identity",
        "permalink",
        "body",
        "author",
        "created_at",
        "updated_at",
        "state",
        "location",
        "associated_revision",
        "source_revision_identity",
        "source_revision",
    }
    variant = {
        "inline_review_comment": {"reply_to", "original_revision", "thread", "review"},
        "pr_conversation_comment": set(),
        "submitted_review_body": {"submitted_at"},
    }
    if kind not in variant or set(value) != common | variant[kind]:
        raise _invalid("source kind or field set is unsupported", record_id)
    _provider_identity(
        value["provider_identity"], "source.provider_identity", record_id
    )
    _text(value["permalink"], "source.permalink", record_id)
    _body(
        value["body"],
        "source.body",
        record_id,
        allow_empty=allow_empty_body,
    )
    _text(value["created_at"], "source.created_at", record_id)
    _text(value["updated_at"], "source.updated_at", record_id)
    _author(value["author"], "source.author", record_id)
    _revision(value["associated_revision"], "source.associated_revision", record_id)
    _source_revision_identity(
        value["source_revision_identity"],
        record_id,
        allow_empty_body=allow_empty_body,
    )
    if (
        value["source_revision_identity"]["body"] != value["body"]
        or value["source_revision_identity"]["associated_commit"]
        != value["associated_revision"]
    ):
        raise _invalid(
            "source revision identity contradicts retained source", record_id
        )
    revision = _sha(value["source_revision"], "source.source_revision", record_id)
    if revision != digest(value["source_revision_identity"]):
        raise _invalid("source revision digest is contradictory", record_id)
    if kind == "inline_review_comment":
        state = _exact(
            value["state"],
            {"availability", "value", "outdated"},
            "source.state",
            record_id,
        )
        if state["availability"] != "available" or type(state["outdated"]) is not bool:
            raise _invalid("inline source state is malformed", record_id)
        _text(state["value"], "source.state.value", record_id)
        location = _exact(
            value["location"],
            {
                "path",
                "line",
                "original_line",
                "original_position",
                "original_start_line",
                "start_line",
                "subject_type",
            },
            "source.location",
            record_id,
        )
        _text(location["path"], "source.location.path", record_id)
        _positive(
            location["original_position"],
            "source.location.original_position",
            record_id,
        )
        _text(location["subject_type"], "source.location.subject_type", record_id)
        for field in ("line", "original_line", "original_start_line", "start_line"):
            if location[field] is not None:
                _positive(location[field], f"source.location.{field}", record_id)
        reply = value["reply_to"]
        if isinstance(reply, dict) and reply.get("availability") == "available":
            item = _exact(
                reply,
                {"availability", "database_id", "node_id"},
                "source.reply_to",
                record_id,
            )
            _positive(item["database_id"], "source.reply_to.database_id", record_id)
            _text(item["node_id"], "source.reply_to.node_id", record_id)
        else:
            _reason_variant(reply, "source.reply_to", "unavailable", record_id)
        _revision(value["original_revision"], "source.original_revision", record_id)
        review = value["review"]
        if isinstance(review, dict) and review.get("availability") == "unavailable":
            _reason_variant(review, "source.review", "unavailable", record_id)
        else:
            _provider_identity(review, "source.review", record_id)
        thread = _exact(
            value["thread"],
            {
                "node_id",
                "root_comment_node_id",
                "root_comment_database_id",
                "is_resolved",
                "is_outdated",
                "path",
                "line",
                "diff_side",
                "original_line",
                "original_start_line",
                "start_diff_side",
                "start_line",
                "subject_type",
                "comment_node_ids",
            },
            "source.thread",
            record_id,
        )
        _text(thread["node_id"], "source.thread.node_id", record_id)
        _text(
            thread["root_comment_node_id"],
            "source.thread.root_comment_node_id",
            record_id,
        )
        _positive(
            thread["root_comment_database_id"],
            "source.thread.root_comment_database_id",
            record_id,
        )
        if (
            type(thread["is_resolved"]) is not bool
            or type(thread["is_outdated"]) is not bool
        ):
            raise _invalid("inline thread state must be explicit booleans", record_id)
        for field in ("path", "diff_side", "subject_type"):
            _text(thread[field], f"source.thread.{field}", record_id)
        for field in ("line", "original_line", "original_start_line", "start_line"):
            if thread[field] is not None:
                _positive(thread[field], f"source.thread.{field}", record_id)
        if thread["start_diff_side"] is not None:
            _text(thread["start_diff_side"], "source.thread.start_diff_side", record_id)
        if (
            not isinstance(thread["comment_node_ids"], list)
            or not thread["comment_node_ids"]
        ):
            raise _invalid("inline thread comment identity list is absent", record_id)
        comment_ids = [
            _text(item, "source.thread.comment_node_id", record_id)
            for item in thread["comment_node_ids"]
        ]
        if (
            len(comment_ids) != len(set(comment_ids))
            or thread["root_comment_node_id"] not in comment_ids
        ):
            raise _invalid(
                "inline thread comment identity list is contradictory", record_id
            )
    elif kind == "pr_conversation_comment":
        _reason_variant(value["state"], "source.state", "unavailable", record_id)
        location = _exact(
            value["location"], {"placement"}, "source.location", record_id
        )
        if location["placement"] != "pull_request_conversation":
            raise _invalid("conversation source placement is contradictory", record_id)
    else:
        state = _exact(
            value["state"], {"availability", "value"}, "source.state", record_id
        )
        if state["availability"] != "available":
            raise _invalid("submitted review state is unavailable", record_id)
        state_value = _text(state["value"], "source.state.value", record_id)
        location = _exact(
            value["location"], {"placement"}, "source.location", record_id
        )
        if location["placement"] != "submitted_review":
            raise _invalid("submitted review placement is contradictory", record_id)
        submitted = value["submitted_at"]
        if isinstance(submitted, dict) and submitted.get("availability") == "available":
            item = _exact(
                submitted, {"availability", "value"}, "source.submitted_at", record_id
            )
            _text(item["value"], "source.submitted_at.value", record_id)
            if state_value == "PENDING":
                raise _invalid("pending review has a submitted timestamp", record_id)
        else:
            _reason_variant(submitted, "source.submitted_at", "unavailable", record_id)
            if state_value != "PENDING":
                raise _invalid(
                    "submitted review lacks a submitted timestamp", record_id
                )
    return value


def _observation(value: Any, phase: str, record_id: str) -> dict[str, Any]:
    item = _exact(
        value,
        {"kind", "phase", "observed_at", "monotonic_ns"},
        f"acquisition_{phase}_observation",
        record_id,
    )
    if item["kind"] != "local_acquisition_observation" or item["phase"] != phase:
        raise _invalid(f"acquisition {phase} observation is mistyped", record_id)
    _text(item["observed_at"], f"acquisition_{phase}.observed_at", record_id)
    _positive(item["monotonic_ns"], f"acquisition_{phase}.monotonic_ns", record_id)
    return item


def _pagination(value: Any, record_id: str) -> None:
    item = _exact(
        value,
        {"complete", "collections", "hydrated_threads"},
        "pagination_evidence",
        record_id,
    )
    if item["complete"] is not True or not isinstance(item["collections"], dict):
        raise _invalid("pagination evidence is incomplete", record_id)
    required = {"threads", "comments", "reviews", "checks", "review_requests"}
    if set(item["collections"]) != required:
        raise _invalid("pagination collection inventory is incomplete", record_id)

    def validate_pages(
        pages: Any, name: str, expected_count: Any, terminal_cursor: Any
    ) -> None:
        if not isinstance(pages, list) or not pages:
            raise _invalid(f"{name} page evidence is absent", record_id)
        continuation_cursors: set[str] = set()
        prior_end_cursor: str | None = None
        for index, page in enumerate(pages):
            page = _exact(
                page,
                {
                    "page_index",
                    "request_cursor",
                    "node_count",
                    "has_next_page",
                    "end_cursor",
                },
                f"{name}.page",
                record_id,
            )
            request_cursor = page["request_cursor"]
            end_cursor = page["end_cursor"]
            if page["page_index"] != index:
                raise _invalid("pagination page index is invalid", record_id)
            if type(page["node_count"]) is not int or page["node_count"] < 0:
                raise _invalid("pagination node count is invalid", record_id)
            if type(page["has_next_page"]) is not bool:
                raise _invalid("pagination continuation is not boolean", record_id)
            if request_cursor is not None and (
                not isinstance(request_cursor, str) or not request_cursor
            ):
                raise _invalid("pagination request cursor is malformed", record_id)
            if end_cursor is not None and (
                not isinstance(end_cursor, str) or not end_cursor
            ):
                raise _invalid("pagination cursor is malformed", record_id)
            if index == 0:
                if request_cursor is not None:
                    raise _invalid(
                        "first pagination request cursor is not null", record_id
                    )
            elif request_cursor != prior_end_cursor:
                raise _invalid("pagination request cursor is discontinuous", record_id)
            final = index == len(pages) - 1
            if not final:
                if page["has_next_page"] is not True or end_cursor is None:
                    raise _invalid(
                        "pagination terminated before the final page", record_id
                    )
                if end_cursor == request_cursor or end_cursor in continuation_cursors:
                    raise _invalid(
                        "pagination cursor did not progress uniquely", record_id
                    )
                continuation_cursors.add(end_cursor)
            elif page["has_next_page"] is not False:
                raise _invalid(f"{name} did not terminate", record_id)
            elif end_cursor is None and not (
                len(pages) == 1 and page["node_count"] == 0
            ):
                raise _invalid(
                    f"{name} terminal cursor is absent for a nonempty trace",
                    record_id,
                )
            prior_end_cursor = end_cursor
        if type(expected_count) is not int or expected_count < 0:
            raise _invalid(f"{name} total node count is invalid", record_id)
        if sum(page["node_count"] for page in pages) != expected_count:
            raise _invalid(f"{name} total node count is contradictory", record_id)
        if (
            terminal_cursor is not _NO_TERMINAL_CURSOR
            and prior_end_cursor != terminal_cursor
        ):
            raise _invalid(f"{name} terminal cursor is contradictory", record_id)

    _NO_TERMINAL_CURSOR = object()
    for name, collection in item["collections"].items():
        collection = _exact(
            collection,
            {"complete", "node_count", "pages"},
            f"pagination.{name}",
            record_id,
        )
        if collection["complete"] is not True:
            raise _invalid(
                f"pagination {name} has no complete page evidence", record_id
            )
        validate_pages(
            collection["pages"],
            f"pagination {name}",
            collection["node_count"],
            _NO_TERMINAL_CURSOR,
        )
    if not isinstance(item["hydrated_threads"], list):
        raise _invalid("hydrated thread evidence must be a list", record_id)
    seen: set[str] = set()
    for thread in item["hydrated_threads"]:
        thread = _exact(
            thread,
            {
                "thread_node_id",
                "complete",
                "comment_count",
                "terminal_end_cursor",
                "pages",
            },
            "hydrated_thread",
            record_id,
        )
        node_id = _text(
            thread["thread_node_id"], "hydrated_thread.thread_node_id", record_id
        )
        if node_id in seen or thread["complete"] is not True:
            raise _invalid(
                "hydrated thread evidence is duplicate or incomplete", record_id
            )
        seen.add(node_id)
        if type(thread["comment_count"]) is not int or thread["comment_count"] < 0:
            raise _invalid("hydrated thread comment count is invalid", record_id)
        validate_pages(
            thread["pages"],
            "hydrated thread",
            thread["comment_count"],
            thread["terminal_end_cursor"],
        )


EPOCH_KEYS = {
    "schema_version",
    "complete",
    "snapshot_atomicity",
    "repository",
    "pull_request",
    "sources",
    "observations",
    "observation_digest",
    "identity_registry",
    "identity_registry_digest",
    "acquisition_start_observation",
    "acquisition_end_observation",
    "pagination_evidence",
    "epoch_id",
}


def validate_epoch(value: Any, record_id: str) -> dict[str, Any]:
    epoch = _exact(value, EPOCH_KEYS, "acquisition epoch", record_id)
    if (
        epoch["schema_version"] != 1
        or epoch["complete"] is not True
        or epoch["snapshot_atomicity"] != "not_claimed"
    ):
        raise _invalid(
            "acquisition epoch is incomplete or overclaims atomicity", record_id
        )
    repository = _exact(
        epoch["repository"],
        {"name_with_owner", "owner_login", "provider_identity"},
        "repository coordinate",
        record_id,
    )
    _text(repository["name_with_owner"], "repository.name_with_owner", record_id)
    _text(repository["owner_login"], "repository.owner_login", record_id)
    _provider_identity(
        repository["provider_identity"], "repository.provider_identity", record_id
    )
    pr = _exact(
        epoch["pull_request"],
        {
            "node_id",
            "database_id",
            "number",
            "permalink",
            "head_oid",
            "base_oid",
            "head_repository",
        },
        "pull request coordinate",
        record_id,
    )
    _text(pr["node_id"], "pull_request.node_id", record_id)
    _positive(pr["database_id"], "pull_request.database_id", record_id)
    _positive(pr["number"], "pull_request.number", record_id)
    for name in ("permalink", "head_oid", "base_oid", "head_repository"):
        _text(pr[name], f"pull_request.{name}", record_id)
    if not isinstance(epoch["sources"], list) or not isinstance(
        epoch["observations"], list
    ):
        raise _invalid("epoch source collections must be lists", record_id)
    for source in epoch["observations"]:
        _source(source, record_id, allow_empty_body=True)
    for source in epoch["sources"]:
        _source(source, record_id)
    observation_keys = [
        (
            source["kind"],
            source["provider_identity"]["database_id"],
            source["provider_identity"]["node_id"],
        )
        for source in epoch["observations"]
    ]
    source_keys = [
        (
            source.get("kind"),
            (source.get("provider_identity") or {}).get("database_id"),
            (source.get("provider_identity") or {}).get("node_id"),
        )
        for source in epoch["sources"]
        if isinstance(source, dict)
    ]
    if (
        len(observation_keys) != len(set(observation_keys))
        or len(source_keys) != len(epoch["sources"])
        or len(source_keys) != len(set(source_keys))
    ):
        raise _invalid(
            "epoch contains duplicate or malformed source identities", record_id
        )
    if any(source not in epoch["observations"] for source in epoch["sources"]):
        raise _invalid("epoch source is not an exact retained observation", record_id)
    if epoch["observation_digest"] != digest(epoch["observations"]):
        raise _invalid("epoch observation digest is contradictory", record_id)
    if not isinstance(epoch["identity_registry"], list) or epoch[
        "identity_registry_digest"
    ] != digest(epoch["identity_registry"]):
        raise _invalid("epoch identity registry is absent or contradictory", record_id)
    identities: set[tuple[str, str, int | None]] = set()
    identities_by_node: dict[str, tuple[str, int | None]] = {}
    identities_by_database: dict[tuple[str, int], str] = {}
    for registry_item in epoch["identity_registry"]:
        item = _exact(
            registry_item,
            {"object_kind", "node_id", "database_id"},
            "identity_registry entry",
            record_id,
        )
        object_kind = _text(
            item["object_kind"], "identity_registry.object_kind", record_id
        )
        node_id = _text(item["node_id"], "identity_registry.node_id", record_id)
        database = item["database_id"]
        if isinstance(database, dict) and database.get("availability") == "available":
            database = _exact(
                database,
                {"availability", "value"},
                "identity_registry.database_id",
                record_id,
            )
            database_id: int | None = _positive(
                database["value"], "identity_registry.database_id.value", record_id
            )
        else:
            _reason_variant(
                database, "identity_registry.database_id", "unavailable", record_id
            )
            database_id = None
        typed = (object_kind, node_id, database_id)
        if typed in identities:
            raise _invalid("identity registry contains a duplicate", record_id)
        if node_id in identities_by_node and identities_by_node[node_id] != (
            object_kind,
            database_id,
        ):
            raise _invalid(
                "identity registry node identity is contradictory", record_id
            )
        if database_id is not None:
            database_key = (object_kind, database_id)
            if (
                database_key in identities_by_database
                and identities_by_database[database_key] != node_id
            ):
                raise _invalid(
                    "identity registry database identity is contradictory", record_id
                )
            identities_by_database[database_key] = node_id
        identities_by_node[node_id] = (object_kind, database_id)
        identities.add(typed)
    source_kinds = {
        "inline_review_comment": "PullRequestReviewComment",
        "pr_conversation_comment": "IssueComment",
        "submitted_review_body": "PullRequestReview",
    }
    for source in epoch["observations"]:
        identity = source["provider_identity"]
        if (
            source_kinds[source["kind"]],
            identity["node_id"],
            identity["database_id"],
        ) not in identities:
            raise _invalid(
                "retained source is absent from identity registry", record_id
            )
        if source["kind"] == "inline_review_comment":
            thread = source["thread"]
            required_associations = [
                ("PullRequestReviewThread", thread["node_id"], None),
                (
                    "PullRequestReviewComment",
                    thread["root_comment_node_id"],
                    thread["root_comment_database_id"],
                ),
            ]
            if source["review"].get("availability") != "unavailable":
                required_associations.append(
                    (
                        "PullRequestReview",
                        source["review"]["node_id"],
                        source["review"]["database_id"],
                    )
                )
            if any(
                association not in identities for association in required_associations
            ):
                raise _invalid(
                    "inline source association is absent from identity registry",
                    record_id,
                )
            for comment_node_id in thread["comment_node_ids"]:
                mapped = identities_by_node.get(comment_node_id)
                if mapped is None or mapped[0] != "PullRequestReviewComment":
                    raise _invalid(
                        "inline thread comment is absent from identity registry",
                        record_id,
                    )
    if (
        "PullRequest",
        epoch["pull_request"]["node_id"],
        epoch["pull_request"]["database_id"],
    ) not in identities:
        raise _invalid("pull request is absent from identity registry", record_id)
    start = _observation(epoch["acquisition_start_observation"], "start", record_id)
    end = _observation(epoch["acquisition_end_observation"], "end", record_id)
    if end["monotonic_ns"] <= start["monotonic_ns"]:
        raise _invalid("acquisition observations are not ordered", record_id)
    _pagination(epoch["pagination_evidence"], record_id)
    material = dict(epoch)
    epoch_id = material.pop("epoch_id")
    if _sha(epoch_id, "epoch_id", record_id) != digest(material):
        raise _invalid("epoch identity is contradictory", record_id)
    return epoch


def _epoch_semantics(epoch: dict[str, Any]) -> dict[str, Any]:
    return {
        "repository": epoch["repository"],
        "pull_request": epoch["pull_request"],
        "sources": epoch["sources"],
        "observations": epoch["observations"],
        "observation_digest": epoch["observation_digest"],
        "identity_registry": epoch["identity_registry"],
        "identity_registry_digest": epoch["identity_registry_digest"],
    }


BINDING_KEYS = {
    "schema_version",
    "intent_id",
    "intent_key",
    "intent_kind",
    "owner_id",
    "source_scope_digest",
    "predecessor_outcome_id",
    "admission_epoch",
    "source",
    "classification",
    "adjudication",
    "authority",
    "operation",
    "placement",
    "target",
    "expected_actor_identity",
    "writer",
    "body",
    "top_level_source_permalink",
    "independence_evidence",
}


def validate_binding(value: Any, record_id: str) -> dict[str, Any]:
    binding = _exact(value, BINDING_KEYS, "intent binding", record_id)
    if binding["schema_version"] != 2:
        raise _invalid("intent binding schema is unsupported", record_id)
    for name in ("intent_id", "intent_key", "owner_id"):
        _text(binding[name], f"binding.{name}", record_id)
    _sha(binding["source_scope_digest"], "binding.source_scope_digest", record_id)
    if binding["intent_kind"] not in {"ordinary", "follow_up"}:
        raise _invalid("intent kind is unsupported", record_id)
    predecessor = _optional_link(
        binding["predecessor_outcome_id"], "predecessor_outcome_id", record_id
    )
    if (binding["intent_kind"] == "follow_up") != (predecessor is not None):
        raise _invalid("follow-up predecessor shape is contradictory", record_id)
    epoch = validate_epoch(binding["admission_epoch"], record_id)
    source = _source(binding["source"], record_id)
    if source not in epoch["sources"]:
        raise _invalid("bound source is not in the admission epoch", record_id)
    classification = _exact(
        binding["classification"],
        {"result", "evidence_id"},
        "binding.classification",
        record_id,
    )
    if classification["result"] not in {"human_feedback", "automated_feedback"}:
        raise _invalid("classification result is unsupported", record_id)
    _text(classification["evidence_id"], "classification.evidence_id", record_id)
    adjudication = _exact(
        binding["adjudication"],
        {"disposition", "evidence_id"},
        "binding.adjudication",
        record_id,
    )
    if adjudication["disposition"] != "respond":
        raise _invalid("adjudication does not authorize a response", record_id)
    _text(adjudication["evidence_id"], "adjudication.evidence_id", record_id)
    authority = _exact(
        binding["authority"],
        {"decision", "evidence_id", "actor_login"},
        "binding.authority",
        record_id,
    )
    if authority["decision"] != "authorized":
        raise _invalid("response authority is absent", record_id)
    _text(authority["evidence_id"], "authority.evidence_id", record_id)
    _text(authority["actor_login"], "authority.actor_login", record_id)
    writer = _exact(
        binding["writer"],
        {"identity", "body_sha256", "contract", "contract_version", "field"},
        "binding.writer",
        record_id,
    )
    for field in ("identity", "contract", "contract_version", "field"):
        _text(writer[field], f"writer.{field}", record_id)
    raw = _body(binding["body"], "binding.body", record_id)
    if writer.get("body_sha256") != hashlib.sha256(raw).hexdigest():
        raise _invalid("writer body identity is contradictory", record_id)
    target = _exact(
        binding["target"], {"host", "repository", "pull_request"}, "target", record_id
    )
    if target["host"] != "github.com":
        raise _invalid("target host is unsupported", record_id)
    if (
        target["repository"] != epoch["repository"]
        or target["pull_request"] != epoch["pull_request"]
    ):
        raise _invalid("target and admission epoch disagree", record_id)
    actor = _exact(
        binding["expected_actor_identity"],
        {"availability", "login"},
        "expected_actor_identity",
        record_id,
    )
    if actor["availability"] != "available":
        raise _invalid("expected actor identity is unavailable", record_id)
    _text(actor["login"], "expected_actor_identity.login", record_id)
    kind = source["kind"]
    operation = binding["operation"]
    placement = binding["placement"]
    top_link = binding["top_level_source_permalink"]
    if kind == "inline_review_comment":
        expected = {
            "kind": "review_thread",
            "thread_node_id": source["thread"]["node_id"],
            "root_comment_database_id": source["thread"]["root_comment_database_id"],
        }
        if (
            operation != "create_inline_reply"
            or placement != expected
            or top_link
            != {"availability": "not_applicable", "reason": "inline_placement"}
        ):
            raise _invalid("inline route compatibility is contradictory", record_id)
        if writer["field"] != "review_thread_reply":
            raise _invalid("inline writer field is contradictory", record_id)
    else:
        expected = {
            "kind": "pull_request_conversation",
            "pr_number": epoch["pull_request"]["number"],
        }
        if (
            operation != "create_pull_request_conversation_comment"
            or placement != expected
        ):
            raise _invalid("top-level route compatibility is contradictory", record_id)
        if writer["field"] != "pull_request_conversation_comment":
            raise _invalid("top-level writer field is contradictory", record_id)
        if (
            top_link != {"availability": "available", "permalink": source["permalink"]}
            or source["permalink"].encode() not in raw
        ):
            raise _invalid("top-level source permalink is not satisfied", record_id)
    independence = binding["independence_evidence"]
    if (
        isinstance(independence, dict)
        and independence.get("availability") == "available"
    ):
        item = _exact(
            independence,
            {"availability", "evidence_id"},
            "independence_evidence",
            record_id,
        )
        _text(item["evidence_id"], "independence_evidence.evidence_id", record_id)
    else:
        _reason_variant(
            independence, "independence_evidence", "not_applicable", record_id
        )
    return binding


def validate_owner(value: Any, record_id: str) -> dict[str, Any]:
    owner = _exact(
        value,
        {
            "owner_id",
            "source_scope_digest",
            "source_identity_digest",
            "qualified_pull_request",
            "source_kind",
            "source_identity",
            "source_revision_identity",
            "source_revision_predecessor_owner_id",
        },
        "owner",
        record_id,
    )
    _text(owner["owner_id"], "owner.owner_id", record_id)
    _sha(owner["source_scope_digest"], "owner.source_scope_digest", record_id)
    _sha(owner["source_identity_digest"], "owner.source_identity_digest", record_id)
    _provider_identity(owner["source_identity"], "owner.source_identity", record_id)
    _source_revision_identity(owner["source_revision_identity"], record_id)
    _optional_link(
        owner["source_revision_predecessor_owner_id"],
        "source_revision_predecessor_owner_id",
        record_id,
    )
    if owner["source_kind"] not in {
        "inline_review_comment",
        "pr_conversation_comment",
        "submitted_review_body",
    }:
        raise _invalid("owner source kind is unsupported", record_id)
    if not isinstance(owner["qualified_pull_request"], dict):
        raise _invalid("owner qualified pull request is malformed", record_id)
    return owner


def validate_intent(value: Any, record_id: str) -> dict[str, Any]:
    intent = _exact(
        value,
        {
            "intent_id",
            "owner_id",
            "intent_key",
            "intent_kind",
            "binding",
            "binding_digest",
            "replacement_of_intent_id",
        },
        "intent",
        record_id,
    )
    binding = validate_binding(intent["binding"], record_id)
    for name in ("intent_id", "owner_id", "intent_key"):
        _text(intent[name], f"intent.{name}", record_id)
        if intent[name] != binding[name]:
            raise _invalid(f"intent {name} disagrees with binding", record_id)
    if intent["intent_kind"] != binding["intent_kind"]:
        raise _invalid("intent kind disagrees with binding", record_id)
    if _sha(intent["binding_digest"], "intent.binding_digest", record_id) != digest(
        binding
    ):
        raise _invalid("intent binding digest is contradictory", record_id)
    _optional_link(
        intent["replacement_of_intent_id"], "replacement_of_intent_id", record_id
    )
    return intent


def _drift(value: Any, record_id: str) -> dict[str, Any]:
    item = _exact(value, {"state", "evidence"}, "drift assessment", record_id)
    if item["state"] not in {"observed", "not_observed", "unknown"}:
        raise _invalid("drift state is unsupported", record_id)
    _text(item["evidence"], "drift.evidence", record_id)
    return item


def _json_evidence(value: Any, name: str, record_id: str) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _json_evidence(item, f"{name}[{index}]", record_id)
        return
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        for key, item in value.items():
            _json_evidence(item, f"{name}.{key}", record_id)
        return
    raise _invalid(f"{name} is not supported JSON evidence", record_id)


def _leaf_receipt(value: Any, record_id: str) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise _invalid("leaf receipt schema is unsupported", record_id)
    status = value.get("status")
    if status == "confirmed_success":
        item = _exact(
            value,
            {
                "schema_version",
                "status",
                "operation",
                "request_endpoint",
                "reread_endpoint",
                "request_body_utf8_base64",
                "request_body_sha256",
                "created_response_identity",
                "requested_reread_identity",
                "reread_response_identity",
                "response",
                "reread_body_utf8_base64",
                "reread_body_sha256",
                "exact_reread",
            },
            "successful leaf receipt",
            record_id,
        )
        if item["operation"] not in {
            "create_inline_reply",
            "create_pull_request_conversation_comment",
        }:
            raise _invalid("successful receipt operation is unsupported", record_id)
        for field in ("request_endpoint", "reread_endpoint"):
            _text(item[field], f"receipt.{field}", record_id)
        identities = [
            _identity(item[field], f"receipt.{field}", record_id)
            for field in (
                "created_response_identity",
                "requested_reread_identity",
                "reread_response_identity",
            )
        ]
        if identities[0] != identities[1] or identities[1] != identities[2]:
            raise _invalid("successful receipt identity equality is false", record_id)
        response = _exact(
            item["response"],
            {"node_id", "database_id", "object_kind", "permalink", "actor_login"},
            "receipt.response",
            record_id,
        )
        response_identity = (
            _text(response["object_kind"], "receipt.response.object_kind", record_id),
            _positive(
                response["database_id"], "receipt.response.database_id", record_id
            ),
            _text(response["node_id"], "receipt.response.node_id", record_id),
        )
        if response_identity != identities[2]:
            raise _invalid(
                "successful response object identity is contradictory", record_id
            )
        _text(response["permalink"], "receipt.response.permalink", record_id)
        _text(response["actor_login"], "receipt.response.actor_login", record_id)
        try:
            request = base64.b64decode(item["request_body_utf8_base64"], validate=True)
            reread = base64.b64decode(item["reread_body_utf8_base64"], validate=True)
            request.decode("utf-8")
            reread.decode("utf-8")
        except (TypeError, ValueError, UnicodeDecodeError) as error:
            raise _invalid(
                "successful receipt body encoding is invalid", record_id
            ) from error
        if (
            item["exact_reread"] is not True
            or request != reread
            or hashlib.sha256(request).hexdigest() != item["request_body_sha256"]
            or hashlib.sha256(reread).hexdigest() != item["reread_body_sha256"]
        ):
            raise _invalid(
                "successful receipt exact bytes are contradictory", record_id
            )
        return item
    item = _exact(
        value,
        {
            "schema_version",
            "status",
            "reason",
            "retryable",
            "side_effect",
            "provider_evidence",
        },
        "non-success leaf receipt",
        record_id,
    )
    if status not in {"confirmed_failure", "unknown"}:
        raise _invalid("leaf receipt status is unsupported", record_id)
    _text(item["reason"], "receipt.reason", record_id)
    if type(item["retryable"]) is not bool or not isinstance(
        item["provider_evidence"], dict
    ):
        raise _invalid("non-success receipt evidence is malformed", record_id)
    _json_evidence(item["provider_evidence"], "receipt.provider_evidence", record_id)
    expected_effect = "none" if status == "confirmed_failure" else "unknown"
    if item["side_effect"] != expected_effect:
        raise _invalid("non-success receipt side effect is contradictory", record_id)
    return item


def _outcome(value: Any, record_id: str) -> dict[str, Any]:
    required = {
        "schema_version",
        "outcome_id",
        "owner_id",
        "intent_id",
        "intent_key",
        "intent_kind",
        "predecessor_outcome_id",
        "status",
        "binding_digest",
        "source_scope_digest",
        "source",
        "source_revision",
        "operation",
        "placement",
        "classification",
        "authority",
        "adjudication",
        "writer",
        "qualified_pull_request",
        "attempt_id",
        "admitted_epoch_id",
        "retry_of_attempt_id",
        "reconciles_attempt_id",
        "provider_call",
        "retryable",
        "reason",
        "leaf_receipt_digest",
        "leaf_receipt",
        "post_write_drift_assessment",
        "all_feedback_addressed",
    }
    item = _exact(value, required, "semantic outcome", record_id)
    if item["schema_version"] != 2 or item["status"] not in {
        "confirmed_success",
        "confirmed_failure",
        "unknown",
    }:
        raise _invalid("semantic outcome status or schema is unsupported", record_id)
    for name in (
        "outcome_id",
        "owner_id",
        "intent_id",
        "intent_key",
        "binding_digest",
        "source_scope_digest",
        "attempt_id",
        "admitted_epoch_id",
    ):
        _text(item[name], f"outcome.{name}", record_id)
    for name in (
        "predecessor_outcome_id",
        "retry_of_attempt_id",
        "reconciles_attempt_id",
    ):
        _optional_link(item[name], f"outcome.{name}", record_id)
    if (
        item["all_feedback_addressed"] is not False
        or type(item["provider_call"]) is not bool
        or type(item["retryable"]) is not bool
    ):
        raise _invalid("outcome boolean claims are malformed", record_id)
    receipt = _leaf_receipt(item["leaf_receipt"], record_id)
    if item["leaf_receipt_digest"] != digest(receipt):
        raise _invalid("leaf receipt is absent or digest-invalid", record_id)
    if receipt.get("status") != item["status"]:
        raise _invalid("receipt and semantic outcome status disagree", record_id)
    if item["provider_call"] is not True or item["retryable"] is not bool(
        receipt.get("retryable")
    ):
        raise _invalid("outcome provider or retry claim is contradictory", record_id)
    if item["reason"] != receipt.get("reason"):
        raise _invalid("outcome reason differs from provider evidence", record_id)
    drift = item["post_write_drift_assessment"]
    if item["status"] == "confirmed_failure":
        if receipt.get("side_effect") != "none" or drift is not None:
            raise _invalid(
                "confirmed failure does not prove a provider no-write", record_id
            )
    else:
        _drift(drift, record_id)
    if item["status"] == "confirmed_success" and (
        item["retryable"] or item["reason"] is not None
    ):
        raise _invalid("successful outcome has failure fields", record_id)
    return item


def _attempt(value: Any, record_id: str) -> dict[str, Any]:
    item = _exact(
        value,
        {
            "attempt_id",
            "owner_id",
            "intent_id",
            "binding_digest",
            "ordinal",
            "mode",
            "retry_predecessor",
        },
        "attempt",
        record_id,
    )
    for name in ("attempt_id", "owner_id", "intent_id", "binding_digest"):
        _text(item[name], f"attempt.{name}", record_id)
    _positive(item["ordinal"], "attempt.ordinal", record_id)
    if item["mode"] not in {"initial", "same_intent_retry"}:
        raise _invalid("attempt mode is unsupported", record_id)
    predecessor = item["retry_predecessor"]
    if item["mode"] == "initial" and predecessor is not None:
        raise _invalid("retry attempt predecessor shape is contradictory", record_id)
    if item["mode"] == "same_intent_retry":
        if (
            not isinstance(predecessor, dict)
            or predecessor.get("kind") != "confirmed_failure_outcome"
        ):
            raise _invalid(
                "retry attempt predecessor shape is contradictory", record_id
            )
        item_ref = _exact(
            predecessor,
            {"kind", "outcome_id"},
            "retry_predecessor",
            record_id,
        )
        _text(item_ref["outcome_id"], "retry_predecessor.outcome_id", record_id)
    return item


PayloadValidator = Callable[[Any, str], dict[str, Any]]


def _record_payload(
    value: Any, keys: set[str], kind: str, record_id: str
) -> dict[str, Any]:
    payload = _exact(value, keys, kind, record_id)
    if payload["schema_version"] != 2:
        raise _invalid(f"invalid {kind} payload schema", record_id)
    return payload


def _validate_ordinary_admission(value: Any, record_id: str) -> dict[str, Any]:
    payload = _record_payload(
        value, {"schema_version", "owner", "intent"}, "ordinary_admission", record_id
    )
    validate_owner(payload["owner"], record_id)
    intent = validate_intent(payload["intent"], record_id)
    if (
        intent["intent_kind"] != "ordinary"
        or intent["replacement_of_intent_id"] is not None
    ):
        raise _invalid("ordinary admission intent is mistyped", record_id)
    return payload


def _validate_follow_up_admission(value: Any, record_id: str) -> dict[str, Any]:
    payload = _record_payload(
        value,
        {"schema_version", "intent", "predecessor_outcome_id"},
        "follow_up_admission",
        record_id,
    )
    intent = validate_intent(payload["intent"], record_id)
    _text(payload["predecessor_outcome_id"], "predecessor_outcome_id", record_id)
    if (
        intent["intent_kind"] != "follow_up"
        or intent["binding"]["predecessor_outcome_id"]
        != payload["predecessor_outcome_id"]
    ):
        raise _invalid("follow-up predecessor shape is contradictory", record_id)
    return payload


def _validate_carry_forward(value: Any, record_id: str) -> dict[str, Any]:
    payload = _record_payload(
        value,
        {
            "schema_version",
            "owner_id",
            "intent_id",
            "from_epoch_id",
            "to_epoch",
            "binding_digest",
            "independence_evidence",
        },
        "carry_forward",
        record_id,
    )
    for name in ("owner_id", "intent_id", "from_epoch_id"):
        _text(payload[name], f"carry_forward.{name}", record_id)
    _sha(payload["binding_digest"], "carry_forward.binding_digest", record_id)
    validate_epoch(payload["to_epoch"], record_id)
    evidence = _exact(
        payload["independence_evidence"],
        {"evidence_id", "assessment"},
        "carry-forward independence evidence",
        record_id,
    )
    _text(evidence["evidence_id"], "carry_forward.evidence_id", record_id)
    if evidence["assessment"] != "unchanged":
        raise _invalid("carry-forward independence was not established", record_id)
    return payload


def _validate_prewrite_validation_started(value: Any, record_id: str) -> dict[str, Any]:
    payload = _record_payload(
        value,
        {
            "schema_version",
            "validation_id",
            "owner_id",
            "intent_id",
            "epoch",
            "binding_digest",
            "invocation_mode",
        },
        "prewrite_validation_started",
        record_id,
    )
    for name in ("validation_id", "owner_id", "intent_id"):
        _text(payload[name], f"validation.{name}", record_id)
    _sha(payload["binding_digest"], "validation.binding_digest", record_id)
    validate_epoch(payload["epoch"], record_id)
    if payload["invocation_mode"] not in {"initial", "same_intent_retry"}:
        raise _invalid("validation invocation mode is unsupported", record_id)
    return payload


def _validate_prewrite_invalidated(value: Any, record_id: str) -> dict[str, Any]:
    payload = _record_payload(
        value,
        {"schema_version", "validation_id", "owner_id", "intent_id", "drift", "reason"},
        "prewrite_invalidated",
        record_id,
    )
    for name in ("validation_id", "owner_id", "intent_id", "reason"):
        _text(payload[name], f"invalidation.{name}", record_id)
    if _drift(payload["drift"], record_id)["state"] != "observed":
        raise _invalid("pre-write invalidation lacks observed drift", record_id)
    return payload


def _validate_write_started(value: Any, record_id: str) -> dict[str, Any]:
    payload = _record_payload(
        value,
        {
            "schema_version",
            "validation_id",
            "attempt",
            "validation_epoch",
            "revalidation_digest",
            "effect_assessment",
            "post_write_drift_assessment",
        },
        "write_started",
        record_id,
    )
    _text(payload["validation_id"], "write_started.validation_id", record_id)
    _attempt(payload["attempt"], record_id)
    epoch = validate_epoch(payload["validation_epoch"], record_id)
    _sha(payload["revalidation_digest"], "write_started.revalidation_digest", record_id)
    if (
        payload["revalidation_digest"] != digest(epoch)
        or payload["effect_assessment"] != "unknown"
        or _drift(payload["post_write_drift_assessment"], record_id)["state"]
        != "unknown"
    ):
        raise _invalid("write start evidence is contradictory", record_id)
    return payload


def _validate_attempt_resolution(value: Any, record_id: str) -> dict[str, Any]:
    payload = _record_payload(
        value,
        {
            "schema_version",
            "attempt_id",
            "owner_id",
            "intent_id",
            "outcome",
            "identity_observations",
            "identity_claim",
        },
        "attempt_resolution",
        record_id,
    )
    for name in ("attempt_id", "owner_id", "intent_id"):
        _text(payload[name], f"attempt_resolution.{name}", record_id)
    _outcome(payload["outcome"], record_id)
    if not isinstance(payload["identity_observations"], list):
        raise _invalid("identity observations must be a list", record_id)
    for identity in payload["identity_observations"]:
        _identity(identity, "identity_observation", record_id)
    if payload["identity_claim"] is not None:
        _identity(payload["identity_claim"], "identity_claim", record_id)
    return payload


def _validate_reconciliation_started(value: Any, record_id: str) -> dict[str, Any]:
    payload = _record_payload(
        value,
        {
            "schema_version",
            "reconciliation_id",
            "owner_id",
            "intent_id",
            "attempt_id",
            "intent_key",
            "binding_digest",
            "prior_reconciliation_id",
            "supersedes_incomplete_reconciliation_id",
            "candidate_reservation",
        },
        "reconciliation_started",
        record_id,
    )
    for name in (
        "reconciliation_id",
        "owner_id",
        "intent_id",
        "attempt_id",
        "intent_key",
    ):
        _text(payload[name], f"reconciliation.{name}", record_id)
    _sha(payload["binding_digest"], "reconciliation.binding_digest", record_id)
    for name in ("prior_reconciliation_id", "supersedes_incomplete_reconciliation_id"):
        _optional_link(payload[name], f"reconciliation.{name}", record_id)
    if payload["candidate_reservation"] is not None:
        _identity(payload["candidate_reservation"], "candidate_reservation", record_id)
    return payload


def _validate_reconciliation_resolution(value: Any, record_id: str) -> dict[str, Any]:
    payload = _record_payload(
        value,
        {
            "schema_version",
            "reconciliation_id",
            "attempt_id",
            "owner_id",
            "intent_id",
            "result",
            "outcome",
            "identity_observations",
            "identity_claim",
            "absence_evidence",
        },
        "reconciliation_resolution",
        record_id,
    )
    for name in ("reconciliation_id", "attempt_id", "owner_id", "intent_id"):
        _text(payload[name], f"reconciliation_resolution.{name}", record_id)
    if payload["result"] not in {"confirmed_success", "still_unknown"}:
        raise _invalid("reconciliation result is unsupported", record_id)
    if not isinstance(payload["identity_observations"], list):
        raise _invalid("identity observations must be a list", record_id)
    for identity in payload["identity_observations"]:
        _identity(identity, "identity_observation", record_id)
    if payload["identity_claim"] is not None:
        _identity(payload["identity_claim"], "identity_claim", record_id)
    if payload["absence_evidence"] is not None:
        raise _invalid("reconciliation contains absence evidence", record_id)
    _outcome(payload["outcome"], record_id)
    return payload


def _validate_replacement_basis(value: Any, record_id: str) -> dict[str, Any]:
    payload = _record_payload(
        value,
        {
            "schema_version",
            "basis_id",
            "predecessor_intent_id",
            "predecessor_owner_id",
            "predecessor_validation_id",
            "terminal_state",
            "terminal_record_id",
            "terminal_record_sha256",
            "successor_epoch",
            "successor_epoch_id",
            "successor_epoch_sha256",
            "successor_source",
            "source_scope_digest",
            "operation",
            "placement",
            "supersedes_basis_id",
        },
        "replacement_basis",
        record_id,
    )
    for name in (
        "basis_id",
        "predecessor_intent_id",
        "predecessor_owner_id",
        "predecessor_validation_id",
        "terminal_state",
        "terminal_record_id",
        "successor_epoch_id",
        "operation",
    ):
        _text(payload[name], f"replacement_basis.{name}", record_id)
    for name in (
        "basis_id",
        "terminal_record_sha256",
        "successor_epoch_sha256",
        "source_scope_digest",
    ):
        _sha(payload[name], f"replacement_basis.{name}", record_id)
    _optional_link(
        payload["supersedes_basis_id"],
        "replacement_basis.supersedes_basis_id",
        record_id,
    )
    if payload["terminal_state"] not in {
        "validation_indeterminate",
        "invalidated_unexecuted",
    }:
        raise _invalid("replacement basis terminal state is unsupported", record_id)
    epoch = validate_epoch(payload["successor_epoch"], record_id)
    if (
        payload["successor_epoch_id"] != epoch["epoch_id"]
        or payload["successor_epoch_sha256"] != digest(epoch)
        or payload["successor_source"] not in epoch["sources"]
    ):
        raise _invalid("replacement basis successor epoch is contradictory", record_id)
    material = dict(payload)
    material.pop("basis_id")
    if payload["basis_id"] != digest(material):
        raise _invalid("replacement basis identity is contradictory", record_id)
    if not isinstance(payload["placement"], dict):
        raise _invalid("replacement basis placement must be typed", record_id)
    return payload


def _validate_replacement_transition(value: Any, record_id: str) -> dict[str, Any]:
    payload = _record_payload(
        value,
        {
            "schema_version",
            "replacement_basis_id",
            "predecessor_validation_id",
            "predecessor_intent_id",
            "predecessor_owner_id",
            "terminal_state",
            "terminal_record_id",
            "terminal_record_sha256",
            "successor_owner",
            "successor_intent",
            "classification_artifact",
            "adjudication_artifact",
            "authority_artifact",
            "writer_result_artifact",
        },
        "replacement_transition",
        record_id,
    )
    for name in (
        "replacement_basis_id",
        "predecessor_validation_id",
        "predecessor_intent_id",
        "predecessor_owner_id",
        "terminal_state",
        "terminal_record_id",
    ):
        _text(payload[name], f"replacement.{name}", record_id)
    _sha(
        payload["terminal_record_sha256"],
        "replacement.terminal_record_sha256",
        record_id,
    )
    if payload["terminal_state"] not in {
        "validation_indeterminate",
        "invalidated_unexecuted",
    }:
        raise _invalid("replacement terminal state is unsupported", record_id)
    if payload["successor_owner"] is not None:
        validate_owner(payload["successor_owner"], record_id)
    validate_intent(payload["successor_intent"], record_id)
    for kind in (
        "classification",
        "adjudication",
        "authority",
        "writer_result",
    ):
        _replacement_artifact(payload[f"{kind}_artifact"], kind, record_id)
    return payload


RECORD_VALIDATORS: dict[str, PayloadValidator] = {
    "ordinary_admission": _validate_ordinary_admission,
    "follow_up_admission": _validate_follow_up_admission,
    "carry_forward": _validate_carry_forward,
    "prewrite_validation_started": _validate_prewrite_validation_started,
    "prewrite_invalidated": _validate_prewrite_invalidated,
    "write_started": _validate_write_started,
    "attempt_resolution": _validate_attempt_resolution,
    "reconciliation_started": _validate_reconciliation_started,
    "reconciliation_resolution": _validate_reconciliation_resolution,
    "replacement_basis": _validate_replacement_basis,
    "replacement_transition": _validate_replacement_transition,
}


class SemanticHistoryFold:
    """Own closed semantic-history validation, references, and transitions."""

    def __init__(self) -> None:
        self.state: dict[str, Any] = {
            "owners": {},
            "owners_by_scope": {},
            "owners_by_stable_scope": {},
            "source_chains": {},
            "intents": {},
            "keys": {},
            "validations": {},
            "attempts": {},
            "current_attempt_by_intent": {},
            "effective_disposition_by_attempt": {},
            "effective_outcome_by_attempt": {},
            "effective_outcome_by_intent": {},
            "outcomes": {},
            "outcome_order": [],
            "reconciliations": {},
            "identity_owners": {},
            "identity_reservations": {},
            "replacement_by_predecessor": {},
            "replacement_bases": {},
            "latest_basis_by_predecessor": {},
            "carry_forward": [],
            "identity_observers": {},
        }
        self._epochs: dict[str, dict[str, Any]] = {}
        self._current_record_digest: str | None = None
        self._identity_authority = ResponseIdentityAuthority(lambda: self.state)

    def _reference(
        self, index: str, reference: str, expected: str, record_id: str
    ) -> dict[str, Any]:
        item = self.state[index].get(reference)
        if item is None:
            raise _invalid(
                f"{expected} reference does not name one earlier {expected}",
                record_id,
            )
        return item

    def owner(self, owner_id: str, record_id: str) -> dict[str, Any]:
        return self._reference("owners", owner_id, "owner", record_id)

    def intent(self, intent_id: str, record_id: str) -> dict[str, Any]:
        return self._reference("intents", intent_id, "intent", record_id)

    def epoch(self, epoch_id: str, record_id: str) -> dict[str, Any]:
        item = self._epochs.get(epoch_id)
        if item is None:
            raise _invalid("epoch reference does not name one earlier epoch", record_id)
        return item

    def validation(self, validation_id: str, record_id: str) -> dict[str, Any]:
        return self._reference("validations", validation_id, "validation", record_id)

    def attempt(self, attempt_id: str, record_id: str) -> dict[str, Any]:
        return self._reference("attempts", attempt_id, "attempt", record_id)

    def reconciliation(self, reconciliation_id: str, record_id: str) -> dict[str, Any]:
        return self._reference(
            "reconciliations", reconciliation_id, "reconciliation", record_id
        )

    def outcome(self, outcome_id: str, record_id: str) -> dict[str, Any]:
        return self._reference("outcomes", outcome_id, "outcome", record_id)

    def response_identity(
        self, identity: tuple[str, int, str], record_id: str
    ) -> tuple[str, int, str]:
        if identity not in self._identity_authority.projection()["known_identities"]:
            raise _invalid(
                "response identity reference does not name earlier evidence", record_id
            )
        return identity

    def predecessor_successor(self, predecessor_intent_id: str, record_id: str) -> str:
        successor = self.state["replacement_by_predecessor"].get(predecessor_intent_id)
        if successor is None:
            raise _invalid("predecessor has no earlier successor link", record_id)
        return successor

    def remember_epoch(self, epoch: dict[str, Any], record_id: str) -> dict[str, Any]:
        prior = self._epochs.get(epoch["epoch_id"])
        if prior is not None and prior != epoch:
            raise _invalid("epoch identity maps to contradictory evidence", record_id)
        self._epochs[epoch["epoch_id"]] = epoch
        return epoch

    def add_owner(
        self, owner: dict[str, Any], record_id: str, *, replacement: bool = False
    ) -> None:
        owner = copy.deepcopy(validate_owner(owner, record_id))
        try:
            canonical_owner = source_owner_from_record(owner)
        except (KeyError, SourceOwnerIdentityError) as error:
            raise _invalid("owner stable typed identity is malformed", record_id) from error
        owner_id, scope = owner["owner_id"], owner["source_scope_digest"]
        stable_scope = canonical_owner["source_scope_key"]
        if (
            owner_id != f"owner-{scope}"
            or not owner_uses_supported_digests(owner, canonical_owner)
        ):
            raise _invalid("owner stable typed identity is contradictory", record_id)
        if (
            owner_id in self.state["owners"]
            or scope in self.state["owners_by_scope"]
            or stable_scope in self.state["owners_by_stable_scope"]
        ):
            raise _invalid("owner or source scope has multiple creators", record_id)
        chain = self.state["source_chains"].setdefault(
            canonical_owner["source_identity_key"], []
        )
        predecessor = owner["source_revision_predecessor_owner_id"]
        if chain:
            self.owner(predecessor, record_id)
            if predecessor != chain[-1]:
                raise _invalid(
                    "source revision predecessor does not name the latest owner",
                    record_id,
                )
            if not replacement:
                prior_intents = [
                    i
                    for i in self.state["intents"].values()
                    if i["owner_id"] == predecessor and i["intent_kind"] == "ordinary"
                ]
                prior_success = any(
                    self.state["outcomes"][outcome_id]["status"] == "confirmed_success"
                    for outcome_id in self.state["outcome_order"]
                    if prior_intents
                    and self.state["outcomes"][outcome_id]["intent_id"]
                    == prior_intents[-1]["intent_id"]
                )
                if not prior_success:
                    raise _invalid(
                        "ordinary source revision predecessor is not confirmed successful",
                        record_id,
                    )
        elif predecessor is not None:
            raise _invalid("first source revision has a predecessor", record_id)
        self.state["owners"][owner_id] = owner
        self.state["owners_by_scope"][scope] = owner_id
        self.state["owners_by_stable_scope"][stable_scope] = owner_id
        chain.append(owner_id)

    def add_intent(self, intent: dict[str, Any], record_id: str) -> None:
        intent = copy.deepcopy(validate_intent(intent, record_id))
        intent_id, key = intent["intent_id"], intent["intent_key"]
        if (
            intent["owner_id"] not in self.state["owners"]
            or intent_id in self.state["intents"]
        ):
            raise _invalid("intent has invalid or duplicate ownership", record_id)
        if key in self.state["keys"]:
            raise _invalid("intent key has multiple creators", record_id)
        owner = self.owner(intent["owner_id"], record_id)
        if intent["binding"]["source_scope_digest"] != owner["source_scope_digest"]:
            raise _invalid("intent and owner source scope disagree", record_id)
        binding = intent["binding"]
        epoch, source = binding["admission_epoch"], binding["source"]
        self.remember_epoch(epoch, record_id)
        expected_owner = source_owner_from_epoch(epoch, source)
        retained_owner = source_owner_from_record(owner)
        if (
            retained_owner["source_identity"] != expected_owner["source_identity"]
            or retained_owner["source_scope"] != expected_owner["source_scope"]
        ):
            raise _invalid(
                "owner stable source identity or revision is contradictory", record_id
            )
        if (
            owner["source_kind"] != source["kind"]
            or owner["source_identity"] != source["provider_identity"]
            or owner["source_revision_identity"] != source["source_revision_identity"]
        ):
            raise _invalid(
                "owner does not retain the exact typed source", record_id
            )
        self.state["intents"][intent_id] = intent
        self.state["keys"][key] = intent_id

    def intent_state(self, intent_id: str) -> str:
        attempt_id = self.state["current_attempt_by_intent"].get(intent_id)
        if attempt_id is not None:
            return self.state["effective_disposition_by_attempt"][attempt_id]
        validations = [
            v for v in self.state["validations"].values() if v["intent_id"] == intent_id
        ]
        if validations:
            last = validations[-1]
            return last.get("terminal") or "validation_indeterminate"
        if intent_id in self.state["replacement_by_predecessor"]:
            return "replaced"
        return "pending"

    def validate_outcome_binding(
        self, outcome: dict[str, Any], intent: dict[str, Any], record_id: str
    ) -> None:
        binding = intent["binding"]
        expected = {
            "owner_id": intent["owner_id"],
            "intent_id": intent["intent_id"],
            "intent_key": intent["intent_key"],
            "intent_kind": intent["intent_kind"],
            "predecessor_outcome_id": binding["predecessor_outcome_id"],
            "binding_digest": intent["binding_digest"],
            "source_scope_digest": binding["source_scope_digest"],
            "source": binding["source"],
            "source_revision": binding["source"]["source_revision"],
            "operation": binding["operation"],
            "placement": binding["placement"],
            "classification": binding["classification"],
            "authority": binding["authority"],
            "adjudication": binding["adjudication"],
            "writer": binding["writer"],
            "qualified_pull_request": binding["target"],
            "admitted_epoch_id": binding["admission_epoch"]["epoch_id"],
        }
        if any(outcome.get(name) != value for name, value in expected.items()):
            raise _invalid(
                "semantic outcome does not retain the exact intent binding", record_id
            )
        receipt = outcome["leaf_receipt"]
        if outcome["status"] == "confirmed_success":
            raw = base64.b64decode(receipt["request_body_utf8_base64"])
            if raw != base64.b64decode(binding["body"]["utf8_base64"]):
                raise _invalid(
                    "provider request bytes differ from the writer binding", record_id
                )
            expected_kind = {
                "create_inline_reply": "PullRequestReviewComment",
                "create_pull_request_conversation_comment": "IssueComment",
            }[binding["operation"]]
            if receipt["reread_response_identity"]["object_kind"] != expected_kind:
                raise _invalid(
                    "response identity kind contradicts the operation", record_id
                )
            if (
                receipt.get("response", {}).get("actor_login")
                != binding["expected_actor_identity"]["login"]
            ):
                raise _invalid("response actor differs from the bound actor", record_id)

    def _apply_ordinary_admission(
        self, payload: dict[str, Any], record_id: str
    ) -> None:
        _exact(
            payload,
            {"schema_version", "owner", "intent"},
            "ordinary_admission",
            record_id,
        )
        self.add_owner(payload["owner"], record_id)
        if (
            payload["intent"].get("intent_kind") != "ordinary"
            or payload["intent"].get("replacement_of_intent_id") is not None
            or payload["intent"].get("owner_id") != payload["owner"].get("owner_id")
        ):
            raise _invalid("ordinary admission intent is mistyped", record_id)
        self.add_intent(payload["intent"], record_id)

    def _apply_follow_up_admission(
        self, payload: dict[str, Any], record_id: str
    ) -> None:
        _exact(
            payload,
            {"schema_version", "intent", "predecessor_outcome_id"},
            "follow_up_admission",
            record_id,
        )
        intent = validate_intent(payload["intent"], record_id)
        predecessor = self.outcome(payload["predecessor_outcome_id"], record_id)
        if (
            intent["intent_kind"] != "follow_up"
            or intent["binding"]["predecessor_outcome_id"]
            != payload["predecessor_outcome_id"]
            or predecessor is None
            or predecessor["status"] != "confirmed_success"
            or predecessor["owner_id"] != intent["owner_id"]
        ):
            raise _invalid(
                "follow-up predecessor is not confirmed in the same scope",
                record_id,
            )
        self.add_intent(intent, record_id)

    def _apply_carry_forward(self, payload: dict[str, Any], record_id: str) -> None:
        _exact(
            payload,
            {
                "schema_version",
                "owner_id",
                "intent_id",
                "from_epoch_id",
                "to_epoch",
                "binding_digest",
                "independence_evidence",
            },
            "carry_forward",
            record_id,
        )
        intent = self.intent(payload["intent_id"], record_id)
        if (
            intent is None
            or intent["owner_id"] != payload["owner_id"]
            or intent["binding_digest"] != payload["binding_digest"]
            or self.intent_state(intent["intent_id"]) != "pending"
        ):
            raise _invalid(
                "carry-forward does not reference an unchanged pending intent",
                record_id,
            )
        prior_epoch = intent.get(
            "effective_epoch", intent["binding"]["admission_epoch"]
        )
        self.epoch(payload["from_epoch_id"], record_id)
        fresh = validate_epoch(payload["to_epoch"], record_id)
        if prior_epoch["epoch_id"] != payload["from_epoch_id"]:
            raise _invalid(
                "carry-forward epoch predecessor is contradictory", record_id
            )
        independence = _exact(
            payload["independence_evidence"],
            {"evidence_id", "assessment"},
            "carry-forward independence evidence",
            record_id,
        )
        _text(independence["evidence_id"], "carry_forward.evidence_id", record_id)
        if independence["assessment"] != "unchanged":
            raise _invalid("carry-forward independence was not established", record_id)
        if _epoch_semantics(prior_epoch) != _epoch_semantics(fresh):
            raise _invalid(
                "carry-forward changed the pending semantic binding", record_id
            )
        intent["effective_epoch"] = fresh
        self.remember_epoch(fresh, record_id)
        self.state["carry_forward"].append(payload)

    def _apply_prewrite_validation_started(
        self, payload: dict[str, Any], record_id: str
    ) -> None:
        _exact(
            payload,
            {
                "schema_version",
                "validation_id",
                "owner_id",
                "intent_id",
                "epoch",
                "binding_digest",
                "invocation_mode",
            },
            "prewrite_validation_started",
            record_id,
        )
        validation_id = _text(payload["validation_id"], "validation_id", record_id)
        intent = self.intent(payload["intent_id"], record_id)
        self.owner(payload["owner_id"], record_id)
        current_state = (
            self.intent_state(intent["intent_id"]) if intent is not None else None
        )
        retry_allowed = False
        if current_state == "confirmed_failure" and intent is not None:
            attempts = [
                a
                for a in self.state["attempts"].values()
                if a["intent_id"] == intent["intent_id"]
            ]
            prior_outcome_id = attempts[-1].get("outcome_id") if attempts else None
            prior = (
                self.outcome(prior_outcome_id, record_id)
                if prior_outcome_id is not None
                else None
            )
            retry_allowed = bool(
                prior
                and prior["retryable"]
                and prior["leaf_receipt"].get("side_effect") == "none"
            )
        if (
            validation_id in self.state["validations"]
            or intent is None
            or intent["owner_id"] != payload["owner_id"]
            or intent["binding_digest"] != payload["binding_digest"]
            or (current_state != "pending" and not retry_allowed)
        ):
            raise _invalid("validation start is not for one pending intent", record_id)
        validate_epoch(payload["epoch"], record_id)
        self.remember_epoch(payload["epoch"], record_id)
        effective_epoch = intent.get(
            "effective_epoch", intent["binding"]["admission_epoch"]
        )
        if payload["epoch"] != effective_epoch:
            raise _invalid(
                "validation does not reference the effective epoch", record_id
            )
        if payload["invocation_mode"] not in {"initial", "same_intent_retry"}:
            raise _invalid("validation invocation mode is unsupported", record_id)
        if (payload["invocation_mode"] == "same_intent_retry") != retry_allowed:
            raise _invalid(
                "validation invocation mode does not match effective state",
                record_id,
            )
        self.state["validations"][validation_id] = {
            **payload,
            "terminal": None,
            "terminal_record_id": record_id,
            "terminal_record_sha256": self._current_record_digest,
        }

    def _apply_prewrite_invalidated(
        self, payload: dict[str, Any], record_id: str
    ) -> None:
        _exact(
            payload,
            {
                "schema_version",
                "validation_id",
                "owner_id",
                "intent_id",
                "drift",
                "reason",
            },
            "prewrite_invalidated",
            record_id,
        )
        validation = self.validation(payload["validation_id"], record_id)
        self.owner(payload["owner_id"], record_id)
        self.intent(payload["intent_id"], record_id)
        if (
            validation is None
            or validation["intent_id"] != payload["intent_id"]
            or validation["owner_id"] != payload["owner_id"]
            or validation["terminal"] is not None
        ):
            raise _invalid("pre-write invalidation has no open validation", record_id)
        if _drift(payload["drift"], record_id)["state"] != "observed":
            raise _invalid("pre-write invalidation lacks observed drift", record_id)
        _text(payload["reason"], "prewrite_invalidated.reason", record_id)
        validation["terminal"] = "invalidated_unexecuted"
        validation["terminal_record_id"] = record_id
        validation["terminal_record_sha256"] = self._current_record_digest

    def _apply_write_started(self, payload: dict[str, Any], record_id: str) -> None:
        _exact(
            payload,
            {
                "schema_version",
                "validation_id",
                "attempt",
                "validation_epoch",
                "revalidation_digest",
                "effect_assessment",
                "post_write_drift_assessment",
            },
            "write_started",
            record_id,
        )
        validation = self.validation(payload["validation_id"], record_id)
        attempt = _attempt(payload["attempt"], record_id)
        intent = self.intent(attempt["intent_id"], record_id)
        self.owner(attempt["owner_id"], record_id)
        if (
            validation is None
            or validation["terminal"] is not None
            or intent is None
            or validation["intent_id"] != attempt["intent_id"]
            or validation["owner_id"] != intent["owner_id"]
            or attempt["owner_id"] != intent["owner_id"]
            or validation["binding_digest"] != intent["binding_digest"]
            or attempt["binding_digest"] != intent["binding_digest"]
            or validation["invocation_mode"] != attempt["mode"]
        ):
            raise _invalid("write start has no matching open validation", record_id)
        epoch = validate_epoch(payload["validation_epoch"], record_id)
        self.remember_epoch(epoch, record_id)
        if (
            payload["revalidation_digest"] != digest(epoch)
            or payload["effect_assessment"] != "unknown"
            or _drift(payload["post_write_drift_assessment"], record_id)["state"]
            != "unknown"
        ):
            raise _invalid("write start evidence is contradictory", record_id)
        binding = intent["binding"]
        effective_epoch = intent.get("effective_epoch", binding["admission_epoch"])
        current_source = next(
            (
                item
                for item in epoch["sources"]
                if item["kind"] == binding["source"]["kind"]
                and item["provider_identity"] == binding["source"]["provider_identity"]
            ),
            None,
        )
        known_identities = set(
            self._identity_authority.projection()["known_identities"]
        )
        known_response_nodes = {
            node_id
            for object_kind, _, node_id in known_identities
            if object_kind == "PullRequestReviewComment"
        }

        def comparable_source(
            source: dict[str, Any] | None,
            known_nodes: set[str] = known_response_nodes,
        ) -> Any:
            if source is None:
                return None
            value = json.loads(json.dumps(source))
            thread = value.get("thread")
            if isinstance(thread, dict):
                thread["comment_node_ids"] = [
                    node_id
                    for node_id in thread.get("comment_node_ids", [])
                    if node_id not in known_nodes
                ]
            return value

        object_kinds = {
            "inline_review_comment": "PullRequestReviewComment",
            "pr_conversation_comment": "IssueComment",
            "submitted_review_body": "PullRequestReview",
        }

        def source_identity(
            source: dict[str, Any], kinds: dict[str, str] = object_kinds
        ) -> tuple[str, int, str]:
            provider = source["provider_identity"]
            return (
                kinds[source["kind"]],
                provider["database_id"],
                provider["node_id"],
            )

        def relevant_epoch(
            epoch_value: dict[str, Any],
            known: set[tuple[str, int, str]] = known_identities,
        ) -> dict[str, Any]:
            observations = [
                comparable_source(source)
                for source in epoch_value["observations"]
                if source_identity(source) not in known
            ]
            registry = []
            for registry_item in epoch_value["identity_registry"]:
                database = registry_item["database_id"]
                typed = (
                    registry_item["object_kind"],
                    database.get("value")
                    if database.get("availability") == "available"
                    else None,
                    registry_item["node_id"],
                )
                if typed not in known:
                    registry.append(registry_item)
            return {"observations": observations, "identity_registry": registry}

        if (
            epoch["repository"] != binding["target"]["repository"]
            or epoch["pull_request"] != binding["target"]["pull_request"]
            or comparable_source(current_source) != comparable_source(binding["source"])
            or relevant_epoch(epoch) != relevant_epoch(effective_epoch)
        ):
            raise _invalid(
                "write validation does not match the complete intent binding",
                record_id,
            )
        prior_attempts = [
            a
            for a in self.state["attempts"].values()
            if a["intent_id"] == attempt["intent_id"]
        ]
        if (
            attempt["ordinal"] != len(prior_attempts) + 1
            or attempt["attempt_id"] in self.state["attempts"]
        ):
            raise _invalid("attempt ordinal or identity is invalid", record_id)
        if attempt["mode"] == "same_intent_retry":
            retry_ref = attempt["retry_predecessor"]
            prior = self.outcome(retry_ref["outcome_id"], record_id)
            eligible = bool(
                prior
                and prior_attempts
                and prior["attempt_id"] == prior_attempts[-1]["attempt_id"]
                and prior["intent_id"] == attempt["intent_id"]
                and prior["status"] == "confirmed_failure"
                and prior["retryable"]
                and prior["leaf_receipt"]["side_effect"] == "none"
            )
            if not eligible:
                raise _invalid("retry predecessor is not eligible", record_id)
        validation["terminal"] = "write_unknown"
        self.state["attempts"][attempt["attempt_id"]] = {**attempt, "outcome_id": None}
        self.state["current_attempt_by_intent"][attempt["intent_id"]] = attempt[
            "attempt_id"
        ]
        self.state["effective_disposition_by_attempt"][attempt["attempt_id"]] = (
            "unknown"
        )
        self.state["effective_outcome_by_attempt"][attempt["attempt_id"]] = None
        self.state["effective_outcome_by_intent"][attempt["intent_id"]] = None

    def _apply_attempt_resolution(
        self, payload: dict[str, Any], record_id: str
    ) -> None:
        _exact(
            payload,
            {
                "schema_version",
                "attempt_id",
                "owner_id",
                "intent_id",
                "outcome",
                "identity_observations",
                "identity_claim",
            },
            "attempt_resolution",
            record_id,
        )
        attempt = self.attempt(payload["attempt_id"], record_id)
        self.owner(payload["owner_id"], record_id)
        self.intent(payload["intent_id"], record_id)
        outcome = _outcome(payload["outcome"], record_id)
        if (
            attempt is None
            or attempt["outcome_id"] is not None
            or attempt["intent_id"] != payload["intent_id"]
            or attempt["owner_id"] != payload["owner_id"]
            or outcome["attempt_id"] != attempt["attempt_id"]
            or outcome["intent_id"] != attempt["intent_id"]
        ):
            raise _invalid("attempt resolution ownership is invalid", record_id)
        expected_retry_attempt = None
        retry_ref = attempt["retry_predecessor"]
        if retry_ref is not None:
            expected_retry_attempt = self.outcome(retry_ref["outcome_id"], record_id)[
                "attempt_id"
            ]
        if (
            outcome["retry_of_attempt_id"] != expected_retry_attempt
            or outcome["reconciles_attempt_id"] is not None
            or outcome["outcome_id"]
            != f"outcome-{digest({'attempt_id': attempt['attempt_id'], 'receipt': outcome['leaf_receipt'], 'reconciles': None})}"
        ):
            raise _invalid("attempt resolution links are contradictory", record_id)
        self.validate_outcome_binding(
            outcome, self.intent(attempt["intent_id"], record_id), record_id
        )
        if not isinstance(payload["identity_observations"], list):
            raise _invalid("identity observations must be a list", record_id)
        observations = [
            _identity(value, "identity_observation", record_id)
            for value in payload["identity_observations"]
        ]
        claim = payload["identity_claim"]
        if claim is not None:
            claimed = _identity(claim, "identity_claim", record_id)
            receipt_claim = None
            if outcome["status"] == "confirmed_success":
                receipt_claim = _identity(
                    outcome["leaf_receipt"]["reread_response_identity"],
                    "receipt.reread_response_identity",
                    record_id,
                )
            if (
                outcome["status"] != "confirmed_success"
                or claimed not in observations
                or claimed != receipt_claim
            ):
                raise _invalid(
                    "identity claim lacks conclusive matching evidence", record_id
                )
        elif outcome["status"] == "confirmed_success":
            raise _invalid(
                "successful result lacks an exclusive identity claim", record_id
            )
        outcome_id = outcome["outcome_id"]
        if outcome_id in self.state["outcomes"]:
            raise _invalid("semantic outcome has multiple creators", record_id)
        self.state["outcomes"][outcome_id] = outcome
        self.state["outcome_order"].append(outcome_id)
        attempt["outcome_id"] = outcome_id
        self.state["effective_disposition_by_attempt"][attempt["attempt_id"]] = outcome[
            "status"
        ]
        self.state["effective_outcome_by_attempt"][attempt["attempt_id"]] = outcome_id
        self.state["effective_outcome_by_intent"][attempt["intent_id"]] = outcome_id

    def _apply_reconciliation_started(
        self, payload: dict[str, Any], record_id: str
    ) -> None:
        _exact(
            payload,
            {
                "schema_version",
                "reconciliation_id",
                "owner_id",
                "intent_id",
                "attempt_id",
                "intent_key",
                "binding_digest",
                "prior_reconciliation_id",
                "supersedes_incomplete_reconciliation_id",
                "candidate_reservation",
            },
            "reconciliation_started",
            record_id,
        )
        reconciliation_id = _text(
            payload["reconciliation_id"], "reconciliation_id", record_id
        )
        intent = self.intent(payload["intent_id"], record_id)
        attempt = self.attempt(payload["attempt_id"], record_id)
        self.owner(payload["owner_id"], record_id)
        if (
            reconciliation_id in self.state["reconciliations"]
            or intent is None
            or attempt is None
            or attempt["intent_id"] != intent["intent_id"]
            or attempt["owner_id"] != payload["owner_id"]
            or intent["owner_id"] != payload["owner_id"]
            or self.state["current_attempt_by_intent"].get(intent["intent_id"])
            != attempt["attempt_id"]
            or self.state["effective_disposition_by_attempt"].get(attempt["attempt_id"])
            != "unknown"
            or self.intent_state(intent["intent_id"]) != "unknown"
            or payload["intent_key"] != intent["intent_key"]
            or payload["binding_digest"] != intent["binding_digest"]
        ):
            raise _invalid(
                "reconciliation does not reference one unknown intent", record_id
            )
        open_rounds = [
            r
            for r in self.state["reconciliations"].values()
            if r["intent_id"] == intent["intent_id"] and r.get("state") == "live"
        ]
        prior_rounds = [
            r
            for r in self.state["reconciliations"].values()
            if r["intent_id"] == intent["intent_id"]
        ]
        expected_prior = prior_rounds[-1]["reconciliation_id"] if prior_rounds else None
        if payload["prior_reconciliation_id"] is not None:
            self.reconciliation(payload["prior_reconciliation_id"], record_id)
        if payload["prior_reconciliation_id"] != expected_prior:
            raise _invalid(
                "reconciliation predecessor round is contradictory", record_id
            )
        supersedes = payload["supersedes_incomplete_reconciliation_id"]
        if supersedes is not None:
            self.reconciliation(supersedes, record_id)
        if open_rounds and (
            len(open_rounds) != 1 or supersedes != open_rounds[0]["reconciliation_id"]
        ):
            raise _invalid(
                "incomplete reconciliation was not explicitly superseded", record_id
            )
        if not open_rounds and supersedes is not None:
            raise _invalid("reconciliation supersedes a non-open round", record_id)
        if open_rounds:
            prior_round = open_rounds[0]
            prior_round["state"] = "superseded"
            prior_round["superseded_by"] = reconciliation_id
        self.state["reconciliations"][reconciliation_id] = {
            **payload,
            "resolution": None,
            "state": "live",
            "superseded_by": None,
        }

    def _apply_reconciliation_resolution(
        self, payload: dict[str, Any], record_id: str
    ) -> None:
        _exact(
            payload,
            {
                "schema_version",
                "reconciliation_id",
                "attempt_id",
                "owner_id",
                "intent_id",
                "result",
                "outcome",
                "identity_observations",
                "identity_claim",
                "absence_evidence",
            },
            "reconciliation_resolution",
            record_id,
        )
        reconciliation = self.reconciliation(payload["reconciliation_id"], record_id)
        self.attempt(payload["attempt_id"], record_id)
        self.owner(payload["owner_id"], record_id)
        self.intent(payload["intent_id"], record_id)
        if (
            reconciliation is None
            or reconciliation["state"] != "live"
            or reconciliation["attempt_id"] != payload["attempt_id"]
            or reconciliation["intent_id"] != payload["intent_id"]
            or reconciliation["owner_id"] != payload["owner_id"]
        ):
            raise _invalid("reconciliation resolution has no open round", record_id)
        if payload["result"] not in {"confirmed_success", "still_unknown"}:
            raise _invalid("reconciliation result is unsupported", record_id)
        outcome = payload["outcome"]
        if payload["absence_evidence"] is not None:
            raise _invalid("reconciliation contains absence evidence", record_id)
        outcome = _outcome(outcome, record_id)
        expected_status = (
            "confirmed_success"
            if payload["result"] == "confirmed_success"
            else "unknown"
        )
        if (
            outcome["status"] != expected_status
            or outcome["outcome_id"] in self.state["outcomes"]
        ):
            raise _invalid(
                "reconciliation result is contradictory or duplicate", record_id
            )
        if (
            outcome["attempt_id"] != payload["attempt_id"]
            or outcome["reconciles_attempt_id"] != payload["attempt_id"]
            or outcome["outcome_id"]
            != f"outcome-{digest({'attempt_id': payload['attempt_id'], 'receipt': outcome['leaf_receipt'], 'reconciles': payload['attempt_id'], 'reconciliation_id': payload['reconciliation_id']})}"
        ):
            raise _invalid("reconciliation outcome links are contradictory", record_id)
        self.validate_outcome_binding(
            outcome, self.intent(payload["intent_id"], record_id), record_id
        )
        if not isinstance(payload["identity_observations"], list):
            raise _invalid("identity observations must be a list", record_id)
        observations = [
            _identity(v, "identity_observation", record_id)
            for v in payload["identity_observations"]
        ]
        reservation = reconciliation["candidate_reservation"]
        reserved_identity = (
            _identity(reservation, "candidate_reservation", record_id)
            if reservation is not None
            else None
        )
        if reserved_identity is not None and reserved_identity not in observations:
            observations.append(reserved_identity)
        claim = payload["identity_claim"]
        if expected_status == "confirmed_success":
            claimed = _identity(claim, "identity_claim", record_id)
            receipt_claim = _identity(
                outcome["leaf_receipt"]["reread_response_identity"],
                "receipt.reread_response_identity",
                record_id,
            )
            if (
                claimed != receipt_claim
                or claimed not in observations
                or (reserved_identity is not None and claimed != reserved_identity)
            ):
                raise _invalid(
                    "reconciliation identity claim is not exclusive", record_id
                )
        elif claim is not None:
            raise _invalid("unknown reconciliation cannot claim an identity", record_id)
        self.state["outcomes"][outcome["outcome_id"]] = outcome
        self.state["outcome_order"].append(outcome["outcome_id"])
        self.state["effective_disposition_by_attempt"][payload["attempt_id"]] = (
            expected_status
        )
        self.state["effective_outcome_by_attempt"][payload["attempt_id"]] = outcome[
            "outcome_id"
        ]
        self.state["effective_outcome_by_intent"][payload["intent_id"]] = outcome[
            "outcome_id"
        ]
        reconciliation["resolution"] = payload["result"]
        reconciliation["state"] = "resolved"

    def _apply_replacement_basis(self, payload: dict[str, Any], record_id: str) -> None:
        basis = copy.deepcopy(_validate_replacement_basis(payload, record_id))
        basis_id = basis["basis_id"]
        predecessor_id = basis["predecessor_intent_id"]
        predecessor = self.intent(predecessor_id, record_id)
        validation = self.validation(basis["predecessor_validation_id"], record_id)
        self.owner(basis["predecessor_owner_id"], record_id)
        if (
            basis_id in self.state["replacement_bases"]
            or predecessor["intent_kind"] != "ordinary"
            or predecessor["owner_id"] != basis["predecessor_owner_id"]
            or validation["intent_id"] != predecessor_id
            or validation["owner_id"] != predecessor["owner_id"]
            or (validation["terminal"] or "validation_indeterminate")
            != basis["terminal_state"]
            or validation["terminal_record_id"] != basis["terminal_record_id"]
            or validation["terminal_record_sha256"] != basis["terminal_record_sha256"]
            or any(
                attempt["intent_id"] == predecessor_id
                for attempt in self.state["attempts"].values()
            )
            or predecessor_id in self.state["replacement_by_predecessor"]
        ):
            raise _invalid("replacement basis predecessor is not eligible", record_id)
        predecessor_validations = [
            item
            for item in self.state["validations"].values()
            if item["intent_id"] == predecessor_id
        ]
        if predecessor_validations[-1]["validation_id"] != validation["validation_id"]:
            raise _invalid(
                "replacement basis does not name current validation", record_id
            )
        prior_basis_id = self.state["latest_basis_by_predecessor"].get(predecessor_id)
        if basis["supersedes_basis_id"] != prior_basis_id:
            raise _invalid("replacement basis supersession is contradictory", record_id)
        if prior_basis_id is not None:
            prior_basis = self.state["replacement_bases"][prior_basis_id]
            if prior_basis["consumed_by"] is not None:
                raise _invalid(
                    "replacement basis cannot supersede consumed evidence", record_id
                )
            prior_basis["superseded_by"] = basis_id
        epoch = basis["successor_epoch"]
        source = basis["successor_source"]
        expected_owner = source_owner_from_epoch(epoch, source)
        predecessor_owner = self.state["owners"][predecessor["owner_id"]]
        retained_predecessor = source_owner_from_record(predecessor_owner)
        existing_owner_id = self.state["owners_by_stable_scope"].get(
            expected_owner["source_scope_key"]
        )
        expected_scope = (
            self.state["owners"][existing_owner_id]["source_scope_digest"]
            if existing_owner_id is not None
            else expected_owner["source_scope_digest"]
        )
        if source["kind"] == "inline_review_comment":
            expected_operation = "create_inline_reply"
            expected_placement = {
                "kind": "review_thread",
                "thread_node_id": source["thread"]["node_id"],
                "root_comment_database_id": source["thread"][
                    "root_comment_database_id"
                ],
            }
        else:
            expected_operation = "create_pull_request_conversation_comment"
            expected_placement = {
                "kind": "pull_request_conversation",
                "pr_number": epoch["pull_request"]["number"],
            }
        if (
            expected_owner["source_identity"]
            != retained_predecessor["source_identity"]
            or basis["source_scope_digest"] != expected_scope
            or basis["operation"] != expected_operation
            or basis["placement"] != expected_placement
        ):
            raise _invalid(
                "replacement basis source or route is contradictory", record_id
            )
        self.remember_epoch(epoch, record_id)
        self.state["replacement_bases"][basis_id] = {
            **basis,
            "consumed_by": None,
            "superseded_by": None,
            "closed_by_replacement": None,
        }
        self.state["latest_basis_by_predecessor"][predecessor_id] = basis_id

    def _apply_replacement_transition(
        self, payload: dict[str, Any], record_id: str
    ) -> None:
        _exact(
            payload,
            {
                "schema_version",
                "replacement_basis_id",
                "predecessor_validation_id",
                "predecessor_intent_id",
                "predecessor_owner_id",
                "terminal_state",
                "terminal_record_id",
                "terminal_record_sha256",
                "successor_owner",
                "successor_intent",
                "classification_artifact",
                "adjudication_artifact",
                "authority_artifact",
                "writer_result_artifact",
            },
            "replacement_transition",
            record_id,
        )
        predecessor_id = payload["predecessor_intent_id"]
        basis = self.state["replacement_bases"].get(payload["replacement_basis_id"])
        if basis is None:
            raise _invalid("replacement transition has no preceding basis", record_id)
        validation = self.validation(payload["predecessor_validation_id"], record_id)
        predecessor = self.intent(predecessor_id, record_id)
        self.owner(payload["predecessor_owner_id"], record_id)
        if (
            predecessor is None
            or validation is None
            or validation["intent_id"] != predecessor_id
            or predecessor["owner_id"] != payload["predecessor_owner_id"]
            or predecessor_id in self.state["replacement_by_predecessor"]
            or basis["predecessor_intent_id"] != predecessor_id
            or basis["consumed_by"] is not None
            or basis["superseded_by"] is not None
            or self.state["latest_basis_by_predecessor"].get(predecessor_id)
            != basis["basis_id"]
        ):
            raise _invalid(
                "replacement predecessor is invalid or already replaced", record_id
            )
        if validation["terminal"] not in {None, "invalidated_unexecuted"} or any(
            a["intent_id"] == predecessor_id for a in self.state["attempts"].values()
        ):
            raise _invalid(
                "replacement predecessor may have reached the provider", record_id
            )
        expected_terminal = (
            "validation_indeterminate"
            if validation["terminal"] is None
            else "invalidated_unexecuted"
        )
        if (
            payload["terminal_state"] != expected_terminal
            or payload["terminal_state"] != basis["terminal_state"]
            or payload["terminal_record_id"] != basis["terminal_record_id"]
            or payload["terminal_record_sha256"] != basis["terminal_record_sha256"]
        ):
            raise _invalid("replacement terminal evidence is contradictory", record_id)
        artifacts = {
            name: payload[name]
            for name in (
                "classification_artifact",
                "adjudication_artifact",
                "authority_artifact",
                "writer_result_artifact",
            )
        }
        decoded, body = validate_replacement_artifact_set(artifacts, basis, record_id)
        successor = validate_intent(payload["successor_intent"], record_id)
        if (
            successor["replacement_of_intent_id"] != predecessor_id
            or successor["intent_kind"] != "ordinary"
        ):
            raise _invalid("replacement successor link is absent", record_id)
        binding = successor["binding"]
        expected_writer = {
            "identity": decoded["writer_result"]["identity"],
            "body_sha256": hashlib.sha256(body).hexdigest(),
            "contract": decoded["writer_result"]["contract"],
            "contract_version": decoded["writer_result"]["contract_version"],
            "field": decoded["writer_result"]["field"],
        }
        if (
            binding["admission_epoch"] != basis["successor_epoch"]
            or binding["source"] != basis["successor_source"]
            or binding["source_scope_digest"] != basis["source_scope_digest"]
            or binding["operation"] != basis["operation"]
            or binding["placement"] != basis["placement"]
            or binding["classification"]
            != {
                "result": decoded["classification"]["result"],
                "evidence_id": decoded["classification"]["evidence_id"],
            }
            or binding["adjudication"]
            != {
                "disposition": decoded["adjudication"]["disposition"],
                "evidence_id": decoded["adjudication"]["evidence_id"],
            }
            or binding["authority"]
            != {
                "decision": decoded["authority"]["decision"],
                "evidence_id": decoded["authority"]["evidence_id"],
                "actor_login": decoded["authority"]["actor_login"],
            }
            or binding["writer"] != expected_writer
            or binding["body"]["sha256"] != hashlib.sha256(body).hexdigest()
        ):
            raise _invalid("replacement successor binding is contradictory", record_id)
        owner_payload = payload["successor_owner"]
        if successor["owner_id"] == predecessor["owner_id"]:
            if (
                owner_payload is not None
                or successor["binding"]["source_scope_digest"]
                != predecessor["binding"]["source_scope_digest"]
            ):
                raise _invalid(
                    "same-revision replacement owner shape is contradictory",
                    record_id,
                )
        else:
            if (
                owner_payload is None
                or owner_payload.get("source_revision_predecessor_owner_id")
                != predecessor["owner_id"]
            ):
                raise _invalid(
                    "changed-revision replacement owner link is absent", record_id
                )
            self.add_owner(owner_payload, record_id, replacement=True)
        self.add_intent(successor, record_id)
        validation["terminal"] = expected_terminal
        basis["consumed_by"] = record_id
        for item in self.state["replacement_bases"].values():
            if item["predecessor_intent_id"] == predecessor_id:
                item["closed_by_replacement"] = record_id
        self.state["replacement_by_predecessor"][predecessor_id] = successor[
            "intent_id"
        ]

    def fold(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        if set(RECORD_VALIDATORS) != RECORD_KINDS:
            raise _invalid("record validator registry is not closed")
        for record in records:
            kind = record["record_kind"]
            record_id = record["record_id"]
            self._current_record_digest = (
                record.get("record_digest")
                or hashlib.sha256(canonical_bytes(record)).hexdigest()
            )
            validator = RECORD_VALIDATORS.get(kind)
            handler = getattr(self, f"_apply_{kind}", None)
            if validator is None or handler is None:
                raise _invalid("unrecognized semantic record kind", record_id)
            payload = validator(record["payload"], record_id)
            prior_state = self.state
            prior_epochs = self._epochs
            self.state = copy.deepcopy(prior_state)
            self._epochs = copy.deepcopy(prior_epochs)
            try:
                handler(payload, record_id)
                self._identity_authority.apply_transition(kind, payload)
            except ResponseIdentityError as error:
                self.state = prior_state
                self._epochs = prior_epochs
                raise _invalid(str(error), record_id) from error
            except Exception:
                self.state = prior_state
                self._epochs = prior_epochs
                raise
        self.state["intent_state_by_intent"] = {
            intent_id: self.intent_state(intent_id)
            for intent_id in self.state["intents"]
        }
        self.state.update(self._identity_authority.projection())
        return self.state


def fold_semantic_history(records: list[dict[str, Any]]) -> dict[str, Any]:
    return SemanticHistoryFold().fold(records)


class ResponseOutcomeStore:
    """Publish canonical records with local POSIX no-replace primitives."""

    def __init__(
        self,
        directory: str | Path,
        *,
        fault_injector: Callable[[str, str], None] | None = None,
    ) -> None:
        self.directory = Path(directory)
        self.records_directory = self.directory / "records"
        self.staging_directory = self.directory / "staging"
        self.marker_path = self.directory / FORMAT_MARKER_NAME
        self.lock_path = self.directory / "response-runtime.lock"
        self._fault_injector = fault_injector

    def _inject(self, step: str, context: str) -> None:
        if self._fault_injector is not None:
            self._fault_injector(step, context)

    def _preflight_legacy(self) -> None:
        if not self.directory.exists():
            return
        legacy = [
            self.directory / name
            for name in LEGACY_NAMES
            if (self.directory / name).exists()
        ]
        if legacy:
            raise OutcomeStoreError(
                "unsupported-development-format: legacy response streams present: "
                + ", ".join(path.name for path in legacy)
            )

    @contextmanager
    def locked(self, *, exclusive: bool) -> Iterator[None]:
        self._preflight_legacy()
        try:
            self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        except OSError as error:
            raise OutcomeStoreError(
                f"storage-capability-failure: state directory: {error}"
            ) from error
        self._preflight_legacy()
        try:
            handle = self.lock_path.open("a+b")
        except OSError as error:
            raise OutcomeStoreError(
                f"storage-capability-failure: lock creation: {error}"
            ) from error
        try:
            try:
                self._inject("flock", "bundle_lock")
                fcntl.flock(
                    handle.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
                )
            except OSError as error:
                raise OutcomeStoreError(
                    f"storage-capability-failure: flock: {error}"
                ) from error
            try:
                self._preflight_legacy()
                if exclusive:
                    self._validate_initializable_layout()
                    self._initialize()
                else:
                    self._require_initialized()
                self.semantic_history()
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()

    def _require_initialized(self) -> None:
        if not self.marker_path.exists():
            raise _invalid("format marker is absent")
        self._validate_layout()

    def _initialize(self) -> None:
        try:
            self.records_directory.mkdir(mode=0o700, exist_ok=True)
            self.staging_directory.mkdir(mode=0o700, exist_ok=True)
        except OSError as error:
            raise OutcomeStoreError(
                f"storage-capability-failure: bundle directories: {error}"
            ) from error
        if not self.marker_path.exists():
            self._publish_bytes(
                canonical_bytes(FORMAT_MARKER),
                self.marker_path,
                context="format_marker",
                sync_directory=self.directory,
            )
        self._validate_layout()

    def _validate_initializable_layout(self) -> None:
        if self.marker_path.exists():
            return
        allowed = {"records", "staging", self.lock_path.name}
        try:
            unknown = sorted(
                item.name
                for item in self.directory.iterdir()
                if item.name not in allowed
            )
        except OSError as error:
            raise _invalid(f"could not inspect empty layout: {error}") from error
        if unknown:
            raise _invalid("unrecognized entries: " + ", ".join(unknown))

    def _validate_layout(self) -> None:
        try:
            marker = self.marker_path.read_bytes()
        except OSError as error:
            raise _invalid(f"could not read format marker: {error}") from error
        if marker != canonical_bytes(FORMAT_MARKER):
            raise _invalid("format marker is not the supported version 2 schema set")
        allowed = {FORMAT_MARKER_NAME, "records", "staging", self.lock_path.name}
        try:
            unknown = sorted(
                item.name
                for item in self.directory.iterdir()
                if item.name not in allowed
            )
        except OSError as error:
            raise _invalid(f"could not inspect layout: {error}") from error
        if unknown:
            raise _invalid("unrecognized entries: " + ", ".join(unknown))
        if not self.records_directory.is_dir() or not self.staging_directory.is_dir():
            raise _invalid("records or staging is not a directory")

    def _publish_bytes(
        self, data: bytes, final_path: Path, *, context: str, sync_directory: Path
    ) -> None:
        staging_path = (
            self.staging_directory
            / f"{context}-{os.getpid()}-{os.urandom(8).hex()}.tmp"
        )
        fd: int | None = None
        try:
            self._inject("staging_create", context)
            fd = os.open(staging_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            view = memoryview(data)
            while view:
                self._inject("staging_write_each_prefix", context)
                self._inject("staging_write", context)
                written = os.write(fd, view)
                if written <= 0:
                    raise OSError("staging write made no progress")
                view = view[written:]
            self._inject("fchmod", context)
            os.fchmod(fd, 0o400)
            self._inject("file_fsync", context)
            os.fsync(fd)
            os.close(fd)
            fd = None
            self._inject("staging_close", context)
            self._inject("hard_link_no_replace", context)
            self._inject("hard_link", context)
            os.link(staging_path, final_path)
            self._inject("sync_directory_open", context)
            directory_fd = os.open(sync_directory, os.O_RDONLY)
            try:
                self._inject("directory_fsync", context)
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
                self._inject("directory_close", context)
        except OSError as error:
            raise OutcomeStoreError(
                f"storage-capability-failure: {context}: {error}"
            ) from error
        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass

    def _envelope_records(self) -> list[dict[str, Any]]:
        self._validate_layout()
        result: list[dict[str, Any]] = []
        prior_digest: str | None = None
        prior_sequence = 0
        record_ids: set[str] = set()
        try:
            paths = sorted(self.records_directory.iterdir())
        except OSError as error:
            raise _invalid(f"could not list records: {error}") from error
        for path in paths:
            match = RECORD_NAME.fullmatch(path.name)
            if match is None or not path.is_file():
                raise _invalid(f"malformed record name {path.name}")
            sequence, filename_digest = int(match.group(1)), match.group(2)
            if sequence <= prior_sequence:
                raise _invalid("record sequence is not increasing")
            try:
                data = path.read_bytes()
                record = json.loads(data.decode("utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
                raise _invalid(f"unreadable record {path.name}: {error}") from error
            if not isinstance(record, dict) or canonical_bytes(record) != data:
                raise _invalid(f"noncanonical record {path.name}")
            record_digest = hashlib.sha256(data).hexdigest()
            required = {
                "schema_version",
                "sequence",
                "record_kind",
                "record_id",
                "prior_record_digest",
                "payload",
                "payload_digest",
            }
            if (
                set(record) != required
                or record.get("schema_version") != 2
                or record.get("sequence") != sequence
                or record_digest != filename_digest
                or record.get("prior_record_digest") != prior_digest
                or record.get("record_kind") not in RECORD_KINDS
                or not isinstance(record.get("record_id"), str)
                or not record["record_id"]
                or record["record_id"] in record_ids
                or not isinstance(record.get("payload"), dict)
                or record.get("payload_digest") != digest(record.get("payload"))
            ):
                raise _invalid(f"invalid record {path.name}")
            result.append({**record, "record_digest": record_digest, "path": path})
            prior_digest, prior_sequence = record_digest, sequence
            record_ids.add(record["record_id"])
        return result

    def records(self) -> list[dict[str, Any]]:
        records = self._envelope_records()
        fold_semantic_history(records)
        return records

    def semantic_history(self) -> dict[str, Any]:
        return fold_semantic_history(self._envelope_records())

    def append(
        self, record_kind: str, payload: dict[str, Any], *, record_id: str | None = None
    ) -> dict[str, Any]:
        if record_kind not in RECORD_KINDS:
            raise ValueError(f"unknown response record kind: {record_kind}")
        if not isinstance(payload, dict):
            raise TypeError("record payload must be an object")
        records = self._envelope_records()
        sequence = records[-1]["sequence"] + 1 if records else 1
        prior_digest = records[-1]["record_digest"] if records else None
        payload_digest = digest(payload)
        record_id = record_id or f"{record_kind}-{sequence}-{payload_digest[:16]}"
        _text(record_id, "record_id", record_id)
        record = {
            "schema_version": 2,
            "sequence": sequence,
            "record_kind": record_kind,
            "record_id": record_id,
            "prior_record_digest": prior_digest,
            "payload": payload,
            "payload_digest": payload_digest,
        }
        fold_semantic_history([*records, record])
        data = canonical_bytes(record)
        record_digest = hashlib.sha256(data).hexdigest()
        final_path = self.records_directory / f"{sequence:020d}-{record_digest}.json"
        self._publish_bytes(
            data, final_path, context=record_kind, sync_directory=self.records_directory
        )
        return {**record, "record_digest": record_digest, "path": final_path}

    def read(self, record_kind: str) -> list[dict[str, Any]]:
        if record_kind not in RECORD_KINDS:
            raise ValueError(f"unknown response record kind: {record_kind}")
        return [
            item["payload"]
            for item in self.records()
            if item["record_kind"] == record_kind
        ]

    def staging_remnants(self) -> list[str]:
        self._validate_layout()
        try:
            return sorted(item.name for item in self.staging_directory.iterdir())
        except OSError as error:
            raise _invalid(f"could not inspect staging: {error}") from error

    def read_outcomes(self) -> list[dict[str, Any]]:
        with self.locked(exclusive=True):
            history = self.semantic_history()
            return [history["outcomes"][item] for item in history["outcome_order"]]
