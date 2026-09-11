"""Private stable typed source-owner identity construction."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any


class SourceOwnerIdentityError(ValueError):
    """Source-owner input does not carry the supported typed identity contract."""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _provider_identity(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"database_id", "node_id"}:
        raise SourceOwnerIdentityError(f"{name} is not a typed provider identity")
    if (
        type(value["database_id"]) is not int
        or value["database_id"] <= 0
        or not isinstance(value["node_id"], str)
        or not value["node_id"]
    ):
        raise SourceOwnerIdentityError(f"{name} is not a typed provider identity")
    return copy.deepcopy(value)


def _construct(
    *,
    repository_identity: Any,
    pull_request_database_id: Any,
    pull_request_node_id: Any,
    pull_request_number: Any,
    source_kind: Any,
    source_identity: Any,
    source_revision_identity: Any,
    legacy_repository: Any,
) -> dict[str, Any]:
    repository = _provider_identity(repository_identity, "repository identity")
    source = _provider_identity(source_identity, "source identity")
    if (
        type(pull_request_database_id) is not int
        or pull_request_database_id <= 0
        or not isinstance(pull_request_node_id, str)
        or not pull_request_node_id
        or type(pull_request_number) is not int
        or pull_request_number <= 0
    ):
        raise SourceOwnerIdentityError("pull request identity is not fully typed")
    if source_kind not in {
        "inline_review_comment",
        "pr_conversation_comment",
        "submitted_review_body",
    }:
        raise SourceOwnerIdentityError("source kind is unsupported")
    if not isinstance(source_revision_identity, dict):
        raise SourceOwnerIdentityError("source revision identity is not typed")

    identity = {
        "provider_host": "github.com",
        "repository_identity": repository,
        "pull_request_identity": {
            "database_id": pull_request_database_id,
            "node_id": pull_request_node_id,
            "number": pull_request_number,
        },
        "source_kind": source_kind,
        "source_identity": source,
    }
    revision = copy.deepcopy(source_revision_identity)
    source_identity_digest = _digest(identity)
    scope_digest_material = {
        "source_identity_digest": source_identity_digest,
        "source_revision_identity": revision,
    }
    scope = {"source_identity": identity, "source_revision_identity": revision}

    legacy_identity = {
        "provider_host": "github.com",
        "repository": copy.deepcopy(legacy_repository),
        "pull_request": {
            "number": pull_request_number,
            "database_id": pull_request_database_id,
            "node_id": pull_request_node_id,
        },
        "source_kind": source_kind,
        "source_identity": source,
    }
    legacy_source_identity_digest = _digest(legacy_identity)
    legacy_source_scope_digest = _digest(
        {
            "source_identity_digest": legacy_source_identity_digest,
            "source_revision_identity": revision,
        }
    )
    return {
        "source_identity": identity,
        "source_scope": scope,
        "source_identity_key": _canonical(identity),
        "source_scope_key": _canonical(scope),
        "source_identity_digest": source_identity_digest,
        "source_scope_digest": _digest(scope_digest_material),
        "legacy_source_identity_digest": legacy_source_identity_digest,
        "legacy_source_scope_digest": legacy_source_scope_digest,
    }


def source_owner_from_epoch(
    epoch: dict[str, Any], source: dict[str, Any]
) -> dict[str, Any]:
    repository = epoch["repository"]
    pull_request = epoch["pull_request"]
    return _construct(
        repository_identity=repository["provider_identity"],
        pull_request_database_id=pull_request["database_id"],
        pull_request_node_id=pull_request["node_id"],
        pull_request_number=pull_request["number"],
        source_kind=source["kind"],
        source_identity=source["provider_identity"],
        source_revision_identity=source["source_revision_identity"],
        legacy_repository=repository,
    )


def source_owner_from_record(owner: dict[str, Any]) -> dict[str, Any]:
    qualified = owner["qualified_pull_request"]
    repository = qualified["repository"]
    pull_request = qualified["pull_request"]
    return _construct(
        repository_identity=repository["provider_identity"],
        pull_request_database_id=pull_request["database_id"],
        pull_request_node_id=pull_request["node_id"],
        pull_request_number=pull_request["number"],
        source_kind=owner["source_kind"],
        source_identity=owner["source_identity"],
        source_revision_identity=owner["source_revision_identity"],
        legacy_repository=repository,
    )


def owner_uses_supported_digests(
    owner: dict[str, Any], canonical: dict[str, Any]
) -> bool:
    actual = (owner["source_identity_digest"], owner["source_scope_digest"])
    return actual in {
        (
            canonical["source_identity_digest"],
            canonical["source_scope_digest"],
        ),
        (
            canonical["legacy_source_identity_digest"],
            canonical["legacy_source_scope_digest"],
        ),
    }
