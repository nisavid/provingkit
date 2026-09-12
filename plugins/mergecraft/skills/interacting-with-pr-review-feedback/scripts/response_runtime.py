#!/usr/bin/env python3
"""Admit, validate, execute, and reconcile one exact response intent."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from github_response_provider import (
    GhTransportError,
    InlineReplyAdapter,
    PullRequestConversationAdapter,
    TypedEpochAdapter,
)
from response_outcome_store import (
    OutcomeStoreError,
    ResponseOutcomeStore,
    digest,
    validate_epoch,
    validate_replacement_artifact_set,
)
from response_source_owner import source_owner_from_epoch, source_owner_from_record


class ResponseRuntimeError(RuntimeError):
    pass


class IntentConflict(ResponseRuntimeError):
    pass


class AdmissionError(ResponseRuntimeError):
    pass


class ReconciliationRequired(ResponseRuntimeError):
    pass


class SemanticPersistenceIncomplete(ResponseRuntimeError):
    pass


def _required_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise AdmissionError(f"{name} must be a nonempty string")
    return value


def _body_evidence(body: bytes) -> dict[str, Any]:
    try:
        body.decode("utf-8")
    except UnicodeDecodeError as error:
        raise AdmissionError("writer body is not exact UTF-8") from error
    return {
        "utf8_base64": base64.b64encode(body).decode("ascii"),
        "byte_length": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
    }


def _source_identity_digest(epoch: dict[str, Any], source: dict[str, Any]) -> str:
    return source_owner_from_epoch(epoch, source)["source_identity_digest"]


def _source_scope_digest(epoch: dict[str, Any], source: dict[str, Any]) -> str:
    return source_owner_from_epoch(epoch, source)["source_scope_digest"]


def _proposal(intent: dict[str, Any], exact_body: bytes) -> dict[str, Any]:
    required_fields = {
        "schema_version",
        "intent_key",
        "intent_kind",
        "admitted_epoch",
        "source",
        "operation",
        "placement",
        "writer",
        "authority",
        "classification",
        "adjudication",
        "independence_evidence",
    }
    optional_fields = {
        "predecessor_outcome_id",
        "carry_forward",
    }
    if (
        not isinstance(intent, dict)
        or not required_fields.issubset(intent)
        or not set(intent).issubset(required_fields | optional_fields)
    ):
        raise AdmissionError("intent field set is incomplete or unsupported")
    if intent.get("schema_version") != 1:
        raise AdmissionError("intent schema_version must be 1")
    key = _required_text(intent.get("intent_key"), "intent_key")
    intent_kind = intent.get("intent_kind")
    if intent_kind not in {"ordinary", "follow_up"}:
        raise AdmissionError("intent_kind must be ordinary or follow_up")
    epoch, source = intent.get("admitted_epoch"), intent.get("source")
    if not isinstance(epoch, dict) or not isinstance(source, dict):
        raise AdmissionError(
            "intent requires a complete admitted_epoch and exact source"
        )
    try:
        validate_epoch(epoch, "caller-intent")
    except OutcomeStoreError as error:
        raise AdmissionError(str(error)) from error
    if source not in epoch["sources"]:
        raise AdmissionError("source is not an exact member of the admitted epoch")
    operation, placement = intent.get("operation"), intent.get("placement")
    if not isinstance(placement, dict):
        raise AdmissionError("placement must be typed")
    if source["kind"] == "inline_review_comment":
        expected_placement = {
            "kind": "review_thread",
            "thread_node_id": source["thread"]["node_id"],
            "root_comment_database_id": source["thread"]["root_comment_database_id"],
        }
        expected_operation = "create_inline_reply"
        writer_field = "review_thread_reply"
        top_level_link = {
            "availability": "not_applicable",
            "reason": "inline_placement",
        }
    elif source["kind"] in {"pr_conversation_comment", "submitted_review_body"}:
        expected_placement = {
            "kind": "pull_request_conversation",
            "pr_number": epoch["pull_request"]["number"],
        }
        expected_operation = "create_pull_request_conversation_comment"
        writer_field = "pull_request_conversation_comment"
        try:
            body_text = exact_body.decode("utf-8")
        except UnicodeDecodeError as error:
            raise AdmissionError("writer body is not exact UTF-8") from error
        if source["permalink"] not in body_text:
            raise AdmissionError(
                "top-level writer body must contain the exact source permalink"
            )
        top_level_link = {"availability": "available", "permalink": source["permalink"]}
    else:
        raise AdmissionError("unsupported typed source kind")
    if operation != expected_operation or placement != expected_placement:
        raise AdmissionError(
            "source, operation, and placement violate the closed route matrix"
        )

    writer = intent.get("writer")
    classification = intent.get("classification")
    adjudication = intent.get("adjudication")
    authority = intent.get("authority")
    if not isinstance(writer, dict) or set(writer) != {
        "identity",
        "body_sha256",
        "contract",
        "contract_version",
        "field",
    }:
        raise AdmissionError("writer evidence is required")
    if writer.get("body_sha256") != hashlib.sha256(exact_body).hexdigest():
        raise AdmissionError("writer body binding does not match exact bytes")
    _required_text(writer.get("identity"), "writer.identity")
    if (
        writer.get("contract") != "portable-github-markdown-authoring"
        or writer.get("contract_version") != "1"
        or writer.get("field") != writer_field
    ):
        raise AdmissionError("writer contract identity, version, or field is invalid")
    if (
        not isinstance(classification, dict)
        or set(classification) != {"result", "evidence_id"}
        or classification.get("result") not in {"human_feedback", "automated_feedback"}
    ):
        raise AdmissionError("typed classification evidence is required")
    _required_text(classification.get("evidence_id"), "classification.evidence_id")
    if (
        not isinstance(adjudication, dict)
        or set(adjudication) != {"disposition", "evidence_id"}
        or adjudication.get("disposition") != "respond"
    ):
        raise AdmissionError("explicit respond adjudication is required")
    _required_text(adjudication.get("evidence_id"), "adjudication.evidence_id")
    if (
        not isinstance(authority, dict)
        or set(authority) != {"decision", "evidence_id", "actor_login"}
        or authority.get("decision") != "authorized"
    ):
        raise AdmissionError("explicit response authority is required")
    _required_text(authority.get("evidence_id"), "authority.evidence_id")
    actor_login = _required_text(authority.get("actor_login"), "authority.actor_login")
    predecessor = intent.get("predecessor_outcome_id")
    if intent_kind == "ordinary" and predecessor is not None:
        raise AdmissionError("ordinary intent cannot name a predecessor outcome")
    if intent_kind == "follow_up":
        _required_text(predecessor, "predecessor_outcome_id")
    independence = intent.get("independence_evidence")
    if (
        not isinstance(independence, dict)
        or (
            independence.get("availability") == "available"
            and set(independence) != {"availability", "evidence_id"}
        )
        or (
            independence.get("availability") == "not_applicable"
            and set(independence) != {"availability", "reason"}
        )
        or independence.get("availability") not in {"available", "not_applicable"}
    ):
        raise AdmissionError("independence evidence must use an explicit typed variant")
    _required_text(
        independence.get(
            "evidence_id" if independence["availability"] == "available" else "reason"
        ),
        "independence_evidence",
    )
    carry = intent.get("carry_forward")
    if carry is not None:
        if not isinstance(carry, dict) or set(carry) != {
            "from_epoch_id",
            "to_epoch",
            "independence_evidence",
        }:
            raise AdmissionError("carry_forward requires exact typed evidence")
        _required_text(carry["from_epoch_id"], "carry_forward.from_epoch_id")
        carry_independence = carry["independence_evidence"]
        if (
            not isinstance(carry_independence, dict)
            or set(carry_independence) != {"evidence_id", "assessment"}
            or carry_independence.get("assessment") != "unchanged"
        ):
            raise AdmissionError("carry_forward independence evidence is invalid")
        _required_text(
            carry_independence.get("evidence_id"),
            "carry_forward.independence_evidence.evidence_id",
        )
        try:
            validate_epoch(carry["to_epoch"], "caller-carry-forward")
        except OutcomeStoreError as error:
            raise AdmissionError(str(error)) from error
    return {
        "schema_version": 2,
        "intent_key": key,
        "intent_kind": intent_kind,
        "predecessor_outcome_id": predecessor,
        "admission_epoch": epoch,
        "source": source,
        "classification": classification,
        "adjudication": adjudication,
        "authority": authority,
        "operation": operation,
        "placement": placement,
        "target": {
            "host": "github.com",
            "repository": epoch["repository"],
            "pull_request": epoch["pull_request"],
        },
        "expected_actor_identity": {"availability": "available", "login": actor_login},
        "writer": writer,
        "body": _body_evidence(exact_body),
        "top_level_source_permalink": top_level_link,
        "independence_evidence": independence,
    }


def _replacement_proposal(
    intent: dict[str, Any], exact_body: bytes, history: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    required = {
        "schema_version",
        "intent_key",
        "intent_kind",
        "replacement_basis_id",
        "classification_artifact",
        "adjudication_artifact",
        "authority_artifact",
        "writer_result_artifact",
    }
    if not isinstance(intent, dict) or set(intent) != required:
        raise AdmissionError(
            "replacement intent field set is incomplete or unsupported"
        )
    if intent["schema_version"] != 2 or intent["intent_kind"] != "ordinary":
        raise AdmissionError("replacement intent must use closed schema 2 ordinary")
    _required_text(intent["intent_key"], "intent_key")
    basis_id = _required_text(intent["replacement_basis_id"], "replacement_basis_id")
    basis = history["replacement_bases"].get(basis_id)
    if (
        basis is None
        or basis["consumed_by"] is not None
        or basis["superseded_by"] is not None
        or basis["closed_by_replacement"] is not None
        or history["latest_basis_by_predecessor"].get(basis["predecessor_intent_id"])
        != basis_id
    ):
        raise AdmissionError(
            "replacement basis is absent, stale, superseded, or consumed"
        )
    artifacts = {
        name: intent[name]
        for name in (
            "classification_artifact",
            "adjudication_artifact",
            "authority_artifact",
            "writer_result_artifact",
        )
    }
    try:
        decoded, artifact_body = validate_replacement_artifact_set(
            artifacts, basis, "caller-replacement"
        )
    except OutcomeStoreError as error:
        raise AdmissionError(str(error)) from error
    if artifact_body != exact_body:
        raise AdmissionError("writer-result body differs from the exact body input")
    writer_result = decoded["writer_result"]
    ordinary = {
        "schema_version": 1,
        "intent_key": intent["intent_key"],
        "intent_kind": "ordinary",
        "admitted_epoch": basis["successor_epoch"],
        "source": basis["successor_source"],
        "operation": basis["operation"],
        "placement": basis["placement"],
        "writer": {
            "identity": writer_result["identity"],
            "body_sha256": hashlib.sha256(exact_body).hexdigest(),
            "contract": writer_result["contract"],
            "contract_version": writer_result["contract_version"],
            "field": writer_result["field"],
        },
        "authority": {
            "decision": decoded["authority"]["decision"],
            "evidence_id": decoded["authority"]["evidence_id"],
            "actor_login": decoded["authority"]["actor_login"],
        },
        "classification": {
            "result": decoded["classification"]["result"],
            "evidence_id": decoded["classification"]["evidence_id"],
        },
        "adjudication": {
            "disposition": decoded["adjudication"]["disposition"],
            "evidence_id": decoded["adjudication"]["evidence_id"],
        },
        "independence_evidence": {
            "availability": "not_applicable",
            "reason": "replacement_admission",
        },
    }
    return _proposal(ordinary, exact_body), basis


def _owner(
    epoch: dict[str, Any], source: dict[str, Any], predecessor: str | None
) -> dict[str, Any]:
    canonical_owner = source_owner_from_epoch(epoch, source)
    scope = canonical_owner["source_scope_digest"]
    owner_id = f"owner-{scope}"
    return {
        "owner_id": owner_id,
        "source_scope_digest": scope,
        "source_identity_digest": canonical_owner["source_identity_digest"],
        "qualified_pull_request": {
            "host": "github.com",
            "repository": epoch["repository"],
            "pull_request": {
                "number": epoch["pull_request"]["number"],
                "database_id": epoch["pull_request"]["database_id"],
                "node_id": epoch["pull_request"]["node_id"],
            },
        },
        "source_kind": source["kind"],
        "source_identity": source["provider_identity"],
        "source_revision_identity": source["source_revision_identity"],
        "source_revision_predecessor_owner_id": predecessor,
    }


def _intent_record(
    proposal: dict[str, Any],
    owner: dict[str, Any],
    *,
    replacement_of: str | None = None,
) -> dict[str, Any]:
    identity_material = {
        "owner_id": owner["owner_id"],
        "intent_key": proposal["intent_key"],
        "proposal": proposal,
        "replacement_of": replacement_of,
    }
    intent_id = f"intent-{digest(identity_material)}"
    binding = {
        **proposal,
        "intent_id": intent_id,
        "owner_id": owner["owner_id"],
        "source_scope_digest": owner["source_scope_digest"],
    }
    return {
        "intent_id": intent_id,
        "owner_id": owner["owner_id"],
        "intent_key": proposal["intent_key"],
        "intent_kind": proposal["intent_kind"],
        "binding": binding,
        "binding_digest": digest(binding),
        "replacement_of_intent_id": replacement_of,
    }


class ResponseRuntime:
    def __init__(
        self,
        *,
        state_directory: str | Path,
        epoch_adapter: TypedEpochAdapter | None = None,
        inline_adapter: InlineReplyAdapter | None = None,
        conversation_adapter: PullRequestConversationAdapter | None = None,
        outcome_store: ResponseOutcomeStore | None = None,
    ) -> None:
        self.store = outcome_store or ResponseOutcomeStore(state_directory)
        self.epoch_adapter = epoch_adapter or TypedEpochAdapter()
        self.inline_adapter = inline_adapter or InlineReplyAdapter()
        self.conversation_adapter = (
            conversation_adapter or PullRequestConversationAdapter()
        )

    def read_outcomes(self) -> list[dict[str, Any]]:
        return self.store.read_outcomes()

    @staticmethod
    def _typed_identity(value: Any) -> tuple[str, int, str] | None:
        if not isinstance(value, dict):
            return None
        kind = value.get("object_kind")
        database_id = value.get("database_id", value.get("id"))
        node_id = value.get("node_id")
        if (
            not isinstance(kind, str)
            or type(database_id) is not int
            or database_id <= 0
            or not isinstance(node_id, str)
            or not node_id
        ):
            return None
        return kind, database_id, node_id

    @staticmethod
    def _response_object_kind(operation: str) -> str:
        return {
            "create_inline_reply": "PullRequestReviewComment",
            "create_pull_request_conversation_comment": "IssueComment",
        }[operation]

    @staticmethod
    def _acquisition_object_kind(source_kind: str | None) -> str | None:
        return {
            "inline_review_comment": "PullRequestReviewComment",
            "pr_conversation_comment": "IssueComment",
            "submitted_review_body": "PullRequestReview",
        }.get(source_kind)

    def _source_identity(self, source: dict[str, Any]) -> tuple[str, int, str] | None:
        identity = dict(source.get("provider_identity") or {})
        identity["object_kind"] = self._acquisition_object_kind(source.get("kind"))
        return self._typed_identity(identity)

    def _receipt_identities(
        self, operation: str, receipt: dict[str, Any]
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        seen: set[tuple[str, int, str]] = set()
        for name in (
            "created_response_identity",
            "requested_reread_identity",
            "reread_response_identity",
        ):
            value = receipt.get(name)
            identity = self._typed_identity(value)
            if identity is not None and identity not in seen:
                result.append(dict(value))
                seen.add(identity)
        evidence = receipt.get("provider_evidence")
        if isinstance(evidence, dict):
            for name in (
                "created_response_identity",
                "requested_reread_identity",
                "reread_response_identity",
            ):
                value = evidence.get(name)
                identity = self._typed_identity(value)
                if identity is not None and identity not in seen:
                    result.append(dict(value))
                    seen.add(identity)
            created = evidence.get("create_response")
            if isinstance(created, dict):
                value = {
                    "object_kind": self._response_object_kind(operation),
                    "database_id": created.get("id"),
                    "node_id": created.get("node_id"),
                }
                identity = self._typed_identity(value)
                if identity is not None and identity not in seen:
                    result.append(value)
        return result

    def _known_response_identities(
        self, history: dict[str, Any], additional: list[dict[str, Any]] | None = None
    ) -> set[tuple[str, int, str]]:
        result = set(history["known_identities"])
        for value in additional or []:
            identity = self._typed_identity(value)
            if identity is not None:
                result.add(identity)
        return result

    def _comparable_source(
        self, source: dict[str, Any], known: set[tuple[str, int, str]]
    ) -> dict[str, Any]:
        value = json.loads(json.dumps(source))
        thread = value.get("thread")
        if isinstance(thread, dict):
            known_nodes = {
                node_id
                for kind, _, node_id in known
                if kind == "PullRequestReviewComment"
            }
            thread["comment_node_ids"] = [
                node_id
                for node_id in thread.get("comment_node_ids", [])
                if node_id not in known_nodes
            ]
        return value

    def _relevant_epoch_digest(
        self, epoch: dict[str, Any], known: set[tuple[str, int, str]]
    ) -> str:
        observations = [
            self._comparable_source(item, known)
            for item in epoch.get("observations", [])
            if self._source_identity(item) not in known
        ]
        registry = []
        for item in epoch.get("identity_registry", []):
            database = item.get("database_id") or {}
            identity = self._typed_identity(
                {
                    "object_kind": item.get("object_kind"),
                    "database_id": database.get("value"),
                    "node_id": item.get("node_id"),
                }
            )
            if identity not in known:
                registry.append(item)
        return digest({"observations": observations, "identity_registry": registry})

    def _revalidate(
        self,
        admitted_epoch: dict[str, Any],
        binding: dict[str, Any],
        history: dict[str, Any],
        *,
        additional_identities: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        known = self._known_response_identities(history, additional_identities)
        target = binding["target"]
        repo = target["repository"]["name_with_owner"]
        number = target["pull_request"]["number"]
        current = self.epoch_adapter.acquire(repo, number)
        if current["repository"] != target["repository"]:
            raise AdmissionError("repository identity drifted")
        current_pr = current["pull_request"]
        for name in ("node_id", "database_id", "head_oid", "number"):
            if current_pr.get(name) != target["pull_request"].get(name):
                raise AdmissionError(f"pull request {name} drifted")
        current_source = next(
            (
                item
                for item in current["sources"]
                if item.get("kind") == binding["source"].get("kind")
                and item.get("provider_identity")
                == binding["source"].get("provider_identity")
            ),
            None,
        )
        if current_source is None:
            raise AdmissionError("exact source was deleted or became inaccessible")
        if self._comparable_source(current_source, known) != self._comparable_source(
            binding["source"], known
        ):
            raise AdmissionError("exact source, thread, or placement changed")
        if self._relevant_epoch_digest(current, known) != self._relevant_epoch_digest(
            admitted_epoch, known
        ):
            raise AdmissionError("relevant feedback set changed")
        return current

    def _exact_replay(self, outcome: dict[str, Any]) -> dict[str, Any]:
        return {
            **outcome,
            "status": "confirmed_no_op",
            "exact_replay_of": outcome["outcome_id"],
        }

    def _admit_replacement(
        self,
        caller: dict[str, Any],
        proposal: dict[str, Any],
        history: dict[str, Any],
        basis: dict[str, Any],
    ) -> tuple[
        dict[str, Any], dict[str, Any], dict[str, Any] | None, dict[str, Any] | None
    ]:
        if proposal["intent_key"] in history["keys"]:
            raise IntentConflict("replacement intent key is not fresh")
        predecessor_id = basis["predecessor_intent_id"]
        predecessor = history["intents"][predecessor_id]
        predecessor_owner = history["owners"][predecessor["owner_id"]]
        canonical_owner = source_owner_from_epoch(
            basis["successor_epoch"], basis["successor_source"]
        )
        owner_id = history["owners_by_stable_scope"].get(
            canonical_owner["source_scope_key"]
        )
        owner = history["owners"].get(owner_id) if owner_id is not None else None
        if owner is not None and (
            source_owner_from_record(owner)["source_scope"]
            != canonical_owner["source_scope"]
        ):
            raise IntentConflict("stable source-owner digest collision")
        if owner is None:
            owner = _owner(
                basis["successor_epoch"],
                basis["successor_source"],
                predecessor_owner["owner_id"],
            )
            successor_owner = owner
        elif owner["owner_id"] == predecessor_owner["owner_id"]:
            successor_owner = None
        else:
            raise IntentConflict(
                "replacement source revision already has another owner"
            )
        admitted = _intent_record(proposal, owner, replacement_of=predecessor_id)
        self.store.append(
            "replacement_transition",
            {
                "schema_version": 2,
                "replacement_basis_id": basis["basis_id"],
                "predecessor_validation_id": basis["predecessor_validation_id"],
                "predecessor_intent_id": predecessor_id,
                "predecessor_owner_id": predecessor_owner["owner_id"],
                "terminal_state": basis["terminal_state"],
                "terminal_record_id": basis["terminal_record_id"],
                "terminal_record_sha256": basis["terminal_record_sha256"],
                "successor_owner": successor_owner,
                "successor_intent": admitted,
                "classification_artifact": caller["classification_artifact"],
                "adjudication_artifact": caller["adjudication_artifact"],
                "authority_artifact": caller["authority_artifact"],
                "writer_result_artifact": caller["writer_result_artifact"],
            },
            record_id=f"replacement-{admitted['intent_id']}",
        )
        return owner, admitted, None, None

    def _admit(
        self,
        caller: dict[str, Any],
        proposal: dict[str, Any],
        history: dict[str, Any],
        replacement_basis: dict[str, Any] | None = None,
    ) -> tuple[
        dict[str, Any], dict[str, Any], dict[str, Any] | None, dict[str, Any] | None
    ]:
        if replacement_basis is not None:
            return self._admit_replacement(caller, proposal, history, replacement_basis)
        canonical_owner = source_owner_from_epoch(
            proposal["admission_epoch"], proposal["source"]
        )
        stable_scope = canonical_owner["source_scope_key"]
        source_identity = canonical_owner["source_identity_key"]
        keyed_id = history["keys"].get(proposal["intent_key"])
        if keyed_id is not None:
            admitted = history["intents"][keyed_id]
            owner = history["owners"][admitted["owner_id"]]
            candidate = _intent_record(
                proposal, owner, replacement_of=admitted["replacement_of_intent_id"]
            )
            if candidate["binding_digest"] != admitted["binding_digest"]:
                raise IntentConflict(
                    "intent key is already bound to different exact inputs"
                )
        else:
            owner_id = history["owners_by_stable_scope"].get(stable_scope)
            owner = history["owners"].get(owner_id) if owner_id else None
            if owner is not None and (
                source_owner_from_record(owner)["source_scope"]
                != canonical_owner["source_scope"]
            ):
                raise IntentConflict("stable source-owner digest collision")
            if proposal["intent_kind"] == "follow_up":
                if owner is None:
                    raise AdmissionError("follow-up has no source-revision owner")
                admitted = _intent_record(proposal, owner)
                predecessor = history["outcomes"].get(
                    proposal["predecessor_outcome_id"]
                )
                if (
                    predecessor is None
                    or predecessor["status"] != "confirmed_success"
                    or predecessor["owner_id"] != owner["owner_id"]
                ):
                    raise AdmissionError(
                        "follow-up predecessor is not a confirmed same-scope outcome"
                    )
                self.store.append(
                    "follow_up_admission",
                    {
                        "schema_version": 2,
                        "intent": admitted,
                        "predecessor_outcome_id": predecessor["outcome_id"],
                    },
                    record_id=f"follow-up-{admitted['intent_id']}",
                )
            else:
                related = history["source_chains"].get(source_identity, [])
                if owner is None and not related:
                    owner = _owner(
                        proposal["admission_epoch"], proposal["source"], None
                    )
                    admitted = _intent_record(proposal, owner)
                    self.store.append(
                        "ordinary_admission",
                        {"schema_version": 2, "owner": owner, "intent": admitted},
                        record_id=f"ordinary-{admitted['intent_id']}",
                    )
                elif owner is None:
                    predecessor_owner = history["owners"][related[-1]]
                    predecessor_intents = [
                        item
                        for item in history["intents"].values()
                        if item["owner_id"] == predecessor_owner["owner_id"]
                        and item["intent_kind"] == "ordinary"
                    ]
                    successful = [
                        history["outcomes"][item]
                        for item in history["outcome_order"]
                        if predecessor_intents
                        and history["outcomes"][item]["intent_id"]
                        == predecessor_intents[-1]["intent_id"]
                        and history["outcomes"][item]["status"] == "confirmed_success"
                    ]
                    if not successful:
                        raise IntentConflict(
                            "changed source revision requires an atomic replacement transition"
                        )
                    owner = _owner(
                        proposal["admission_epoch"],
                        proposal["source"],
                        predecessor_owner["owner_id"],
                    )
                    admitted = _intent_record(proposal, owner)
                    self.store.append(
                        "ordinary_admission",
                        {"schema_version": 2, "owner": owner, "intent": admitted},
                        record_id=f"ordinary-{admitted['intent_id']}",
                    )
                else:
                    owner_intents = [
                        item
                        for item in history["intents"].values()
                        if item["owner_id"] == owner["owner_id"]
                        and item["intent_kind"] == "ordinary"
                    ]
                    if owner_intents and history["intent_state_by_intent"][
                        owner_intents[-1]["intent_id"]
                    ] in {"unknown", "confirmed_failure"}:
                        raise ReconciliationRequired(
                            "fresh key cannot bypass provider-attempted owner state"
                        )
                    raise IntentConflict(
                        "source revision already has an ordinary owner; prepare a replacement basis"
                    )
        history = self.store.semantic_history()
        carry = caller.get("carry_forward")
        current_state = history["intent_state_by_intent"][admitted["intent_id"]]
        if carry is not None:
            if not isinstance(carry, dict) or set(carry) != {
                "from_epoch_id",
                "to_epoch",
                "independence_evidence",
            }:
                raise AdmissionError("carry_forward requires exact typed evidence")
            independence = carry["independence_evidence"]
            if (
                not isinstance(independence, dict)
                or set(independence) != {"evidence_id", "assessment"}
                or independence.get("assessment") != "unchanged"
            ):
                raise AdmissionError("carry_forward independence evidence is invalid")
            _required_text(
                independence.get("evidence_id"),
                "carry_forward.independence_evidence.evidence_id",
            )
            if current_state != "pending":
                raise AdmissionError("carry-forward applies only to a pending intent")
            effective = admitted.get(
                "effective_epoch", admitted["binding"]["admission_epoch"]
            )
            if carry["from_epoch_id"] != effective["epoch_id"]:
                raise AdmissionError("carry-forward predecessor epoch is not current")
            self.store.append(
                "carry_forward",
                {
                    "schema_version": 2,
                    "owner_id": owner["owner_id"],
                    "intent_id": admitted["intent_id"],
                    "from_epoch_id": carry["from_epoch_id"],
                    "to_epoch": carry["to_epoch"],
                    "binding_digest": admitted["binding_digest"],
                    "independence_evidence": carry["independence_evidence"],
                },
                record_id=f"carry-forward-{digest(carry)}",
            )
            history = self.store.semantic_history()
            admitted = history["intents"][admitted["intent_id"]]
        state = history["intent_state_by_intent"][admitted["intent_id"]]
        effective_outcome_id = history["effective_outcome_by_intent"].get(
            admitted["intent_id"]
        )
        effective_outcome = (
            history["outcomes"].get(effective_outcome_id)
            if effective_outcome_id is not None
            else None
        )
        if state == "confirmed_success":
            return owner, admitted, self._exact_replay(effective_outcome), None
        if state in {"unknown", "replaced"}:
            raise ReconciliationRequired("intent state permits no provider write")
        if state in {"invalidated_unexecuted", "validation_indeterminate"}:
            raise AdmissionError(
                "pre-write invalidation or interrupted validation permanently closed this intent"
            )
        retry_predecessor = None
        if state == "confirmed_failure":
            prior = effective_outcome
            if (
                not prior["retryable"]
                or prior["leaf_receipt"].get("side_effect") != "none"
            ):
                raise ReconciliationRequired(
                    "prior provider result does not permit retry"
                )
            retry_predecessor = {
                "kind": "confirmed_failure_outcome",
                "outcome_id": prior["outcome_id"],
            }
        return owner, admitted, None, retry_predecessor

    def _execute_leaf(
        self, binding: dict[str, Any], exact_body: bytes, epoch: dict[str, Any]
    ) -> dict[str, Any]:
        target = binding["target"]
        repo = target["repository"]["name_with_owner"]
        number = target["pull_request"]["number"]
        actor = binding["expected_actor_identity"]["login"]
        if binding["operation"] == "create_inline_reply":
            return self.inline_adapter.create_and_reread(
                repo=repo,
                pr_number=number,
                root_comment_database_id=binding["placement"][
                    "root_comment_database_id"
                ],
                exact_body=exact_body,
                expected_actor_login=actor,
            )
        return self.conversation_adapter.create_and_reread(
            repo=repo,
            pr_number=number,
            pr_node_id=target["pull_request"]["node_id"],
            verification_epoch_id=epoch["epoch_id"],
            source_permalink=binding["source"]["permalink"],
            exact_body=exact_body,
            expected_actor_login=actor,
        )

    @staticmethod
    def _unknown_drift(reason: str) -> dict[str, Any]:
        return {"state": "unknown", "evidence": reason}

    def _outcome(
        self,
        owner: dict[str, Any],
        admitted: dict[str, Any],
        attempt: dict[str, Any],
        receipt: dict[str, Any],
        drift: dict[str, Any] | None,
        *,
        reconciles_attempt_id: str | None = None,
        reconciliation_id: str | None = None,
    ) -> dict[str, Any]:
        binding = admitted["binding"]
        identity = {
            "attempt_id": attempt["attempt_id"],
            "receipt": receipt,
            "reconciles": reconciles_attempt_id,
        }
        if reconciliation_id is not None:
            identity["reconciliation_id"] = reconciliation_id
        outcome_id = f"outcome-{digest(identity)}"
        retry_predecessor = attempt.get("retry_predecessor")
        retry_of_attempt_id = None
        if retry_predecessor is not None:
            retry_of_attempt_id = self.store.semantic_history()["outcomes"][
                retry_predecessor["outcome_id"]
            ]["attempt_id"]
        return {
            "schema_version": 2,
            "outcome_id": outcome_id,
            "owner_id": owner["owner_id"],
            "intent_id": admitted["intent_id"],
            "intent_key": admitted["intent_key"],
            "intent_kind": admitted["intent_kind"],
            "predecessor_outcome_id": binding["predecessor_outcome_id"],
            "status": receipt["status"],
            "binding_digest": admitted["binding_digest"],
            "source_scope_digest": owner["source_scope_digest"],
            "source": binding["source"],
            "source_revision": binding["source"]["source_revision"],
            "operation": binding["operation"],
            "placement": binding["placement"],
            "classification": binding["classification"],
            "authority": binding["authority"],
            "adjudication": binding["adjudication"],
            "writer": binding["writer"],
            "qualified_pull_request": binding["target"],
            "attempt_id": attempt["attempt_id"],
            "admitted_epoch_id": binding["admission_epoch"]["epoch_id"],
            "retry_of_attempt_id": retry_of_attempt_id,
            "reconciles_attempt_id": reconciles_attempt_id,
            "provider_call": True,
            "retryable": bool(receipt.get("retryable")),
            "reason": receipt.get("reason"),
            "leaf_receipt_digest": digest(receipt),
            "leaf_receipt": receipt,
            "post_write_drift_assessment": drift,
            "all_feedback_addressed": False,
        }

    def _resolution_payload(
        self,
        owner: dict[str, Any],
        admitted: dict[str, Any],
        attempt: dict[str, Any],
        receipt: dict[str, Any],
        drift: dict[str, Any] | None,
    ) -> dict[str, Any]:
        observations = self._receipt_identities(
            admitted["binding"]["operation"], receipt
        )
        claim = (
            receipt.get("reread_response_identity")
            if receipt.get("status") == "confirmed_success"
            and receipt.get("exact_reread")
            else None
        )
        outcome = self._outcome(owner, admitted, attempt, receipt, drift)
        return {
            "schema_version": 2,
            "attempt_id": attempt["attempt_id"],
            "owner_id": owner["owner_id"],
            "intent_id": admitted["intent_id"],
            "outcome": outcome,
            "identity_observations": observations,
            "identity_claim": claim,
        }

    def _prewrite_failure_result(
        self,
        owner: dict[str, Any],
        admitted: dict[str, Any],
        validation_id: str,
        reason: str,
        *,
        indeterminate: bool,
    ) -> dict[str, Any]:
        return {
            "schema_version": 2,
            "outcome_id": None,
            "owner_id": owner["owner_id"],
            "intent_id": admitted["intent_id"],
            "intent_key": admitted["intent_key"],
            "status": "confirmed_failure",
            "provider_call": False,
            "retryable": False,
            "reason": reason,
            "validation_id": validation_id,
            "pre_write_state": "validation_indeterminate"
            if indeterminate
            else "invalidated_unexecuted",
            "all_feedback_addressed": False,
        }

    def prepare_replacement(
        self, intent_key: str, current_repository: str | None = None
    ) -> dict[str, Any]:
        _required_text(intent_key, "intent_key")
        with self.store.locked(exclusive=True):
            history = self.store.semantic_history()
            predecessor_id = history["keys"].get(intent_key)
            if predecessor_id is None:
                raise AdmissionError("intent key has no durable binding")
            predecessor = history["intents"][predecessor_id]
            terminal_state = history["intent_state_by_intent"][predecessor_id]
            if (
                predecessor["intent_kind"] != "ordinary"
                or terminal_state
                not in {"invalidated_unexecuted", "validation_indeterminate"}
                or predecessor_id in history["replacement_by_predecessor"]
                or predecessor_id in history["current_attempt_by_intent"]
            ):
                raise AdmissionError(
                    "replacement predecessor is not durably unexecuted and terminal"
                )
            validations = [
                item
                for item in history["validations"].values()
                if item["intent_id"] == predecessor_id
            ]
            validation = validations[-1]
            binding = predecessor["binding"]
            target = binding["target"]
            repository_locator = current_repository or target["repository"]["name_with_owner"]
            if not isinstance(repository_locator, str) or not re.fullmatch(
                r"[^/\s]+/[^/\s]+", repository_locator
            ):
                raise AdmissionError(
                    "current repository locator is required and must be owner/name"
                )
            epoch = self.epoch_adapter.acquire(
                repository_locator, target["pull_request"]["number"]
            )
            source = next(
                (
                    item
                    for item in epoch["sources"]
                    if item["kind"] == binding["source"]["kind"]
                    and item["provider_identity"]
                    == binding["source"]["provider_identity"]
                ),
                None,
            )
            if source is None:
                raise AdmissionError(
                    "fresh replacement acquisition does not contain the exact source"
                )
            if source["kind"] == "inline_review_comment":
                operation = "create_inline_reply"
                placement = {
                    "kind": "review_thread",
                    "thread_node_id": source["thread"]["node_id"],
                    "root_comment_database_id": source["thread"][
                        "root_comment_database_id"
                    ],
                }
            else:
                operation = "create_pull_request_conversation_comment"
                placement = {
                    "kind": "pull_request_conversation",
                    "pr_number": epoch["pull_request"]["number"],
                }
            canonical_owner = source_owner_from_epoch(epoch, source)
            existing_owner_id = history["owners_by_stable_scope"].get(
                canonical_owner["source_scope_key"]
            )
            source_scope_digest = (
                history["owners"][existing_owner_id]["source_scope_digest"]
                if existing_owner_id is not None
                else canonical_owner["source_scope_digest"]
            )
            material = {
                "schema_version": 2,
                "predecessor_intent_id": predecessor_id,
                "predecessor_owner_id": predecessor["owner_id"],
                "predecessor_validation_id": validation["validation_id"],
                "terminal_state": terminal_state,
                "terminal_record_id": validation["terminal_record_id"],
                "terminal_record_sha256": validation["terminal_record_sha256"],
                "successor_epoch": epoch,
                "successor_epoch_id": epoch["epoch_id"],
                "successor_epoch_sha256": digest(epoch),
                "successor_source": source,
                "source_scope_digest": source_scope_digest,
                "operation": operation,
                "placement": placement,
                "supersedes_basis_id": history["latest_basis_by_predecessor"].get(
                    predecessor_id
                ),
            }
            basis = {"basis_id": digest(material), **material}
            record = self.store.append(
                "replacement_basis",
                basis,
                record_id=f"replacement-basis-{basis['basis_id']}",
            )
            return record["payload"]

    def invoke(self, intent: dict[str, Any], exact_body: bytes) -> dict[str, Any]:
        replacement = isinstance(intent, dict) and intent.get("schema_version") == 2
        proposal = None if replacement else _proposal(intent, exact_body)
        with self.store.locked(exclusive=True):
            history = self.store.semantic_history()
            replacement_basis = None
            if replacement:
                proposal, replacement_basis = _replacement_proposal(
                    intent, exact_body, history
                )
            owner, admitted, replay, retry_predecessor = self._admit(
                intent, proposal, history, replacement_basis
            )
            if replay is not None:
                return replay
            history = self.store.semantic_history()
            validation_id = f"validation-{digest({'intent_id': admitted['intent_id'], 'count': len(history['validations']) + 1})}"
            mode = "same_intent_retry" if retry_predecessor else "initial"
            effective_epoch = admitted.get(
                "effective_epoch", admitted["binding"]["admission_epoch"]
            )
            self.store.append(
                "prewrite_validation_started",
                {
                    "schema_version": 2,
                    "validation_id": validation_id,
                    "owner_id": owner["owner_id"],
                    "intent_id": admitted["intent_id"],
                    "epoch": effective_epoch,
                    "binding_digest": admitted["binding_digest"],
                    "invocation_mode": mode,
                },
                record_id=validation_id,
            )
            history = self.store.semantic_history()
            try:
                current = self._revalidate(
                    effective_epoch, admitted["binding"], history
                )
            except AdmissionError as error:
                reason = f"pre_write_revalidation: {error}"
                self.store.append(
                    "prewrite_invalidated",
                    {
                        "schema_version": 2,
                        "validation_id": validation_id,
                        "owner_id": owner["owner_id"],
                        "intent_id": admitted["intent_id"],
                        "drift": {"state": "observed", "evidence": str(error)},
                        "reason": reason,
                    },
                    record_id=f"invalidated-{validation_id}",
                )
                return self._prewrite_failure_result(
                    owner, admitted, validation_id, reason, indeterminate=False
                )
            except GhTransportError as error:
                return self._prewrite_failure_result(
                    owner,
                    admitted,
                    validation_id,
                    f"pre_write_validation_interrupted: {error}",
                    indeterminate=True,
                )

            prior_attempts = [
                item
                for item in history["attempts"].values()
                if item["intent_id"] == admitted["intent_id"]
            ]
            attempt_id = f"attempt-{digest({'validation_id': validation_id, 'ordinal': len(prior_attempts) + 1})}"
            attempt = {
                "attempt_id": attempt_id,
                "owner_id": owner["owner_id"],
                "intent_id": admitted["intent_id"],
                "binding_digest": admitted["binding_digest"],
                "ordinal": len(prior_attempts) + 1,
                "mode": mode,
                "retry_predecessor": retry_predecessor,
            }
            self.store.append(
                "write_started",
                {
                    "schema_version": 2,
                    "validation_id": validation_id,
                    "attempt": attempt,
                    "validation_epoch": current,
                    "revalidation_digest": digest(current),
                    "effect_assessment": "unknown",
                    "post_write_drift_assessment": self._unknown_drift(
                        "write boundary may be crossed"
                    ),
                },
                record_id=f"write-started-{attempt_id}",
            )
            try:
                receipt = self._execute_leaf(admitted["binding"], exact_body, current)
            except GhTransportError as error:
                receipt = {
                    "schema_version": 1,
                    "status": error.status,
                    "reason": str(error),
                    "retryable": error.retryable,
                    "side_effect": error.side_effect,
                    "provider_evidence": error.evidence,
                }
            drift: dict[str, Any] | None
            if (
                receipt["status"] == "confirmed_failure"
                and receipt.get("side_effect") == "none"
            ):
                drift = None
            else:
                drift = self._unknown_drift("provider result was not confirmed")
                if receipt["status"] == "confirmed_success":
                    identities = self._receipt_identities(
                        admitted["binding"]["operation"], receipt
                    )
                    try:
                        self._revalidate(
                            effective_epoch,
                            admitted["binding"],
                            self.store.semantic_history(),
                            additional_identities=identities,
                        )
                    except AdmissionError as error:
                        drift = {"state": "observed", "evidence": str(error)}
                    except GhTransportError as error:
                        drift = self._unknown_drift(str(error))
                    else:
                        drift = {
                            "state": "not_observed",
                            "evidence": "immediate bound post-write check completed",
                        }
            resolution = self._resolution_payload(
                owner, admitted, attempt, receipt, drift
            )
            try:
                self.store.append(
                    "attempt_resolution",
                    resolution,
                    record_id=f"resolution-{attempt_id}",
                )
            except OutcomeStoreError as error:
                raise SemanticPersistenceIncomplete(
                    f"attempt {attempt_id} retains durable write_started with unknown effect and drift"
                ) from error
            return resolution["outcome"]

    def _reconciliation_candidates(
        self,
        admitted: dict[str, Any],
        prior_epoch: dict[str, Any],
        current: dict[str, Any],
        history: dict[str, Any],
    ) -> list[dict[str, Any]]:
        binding = admitted["binding"]
        baseline = {self._source_identity(item) for item in prior_epoch["observations"]}
        result = []
        for item in current["sources"]:
            identity = self._source_identity(item)
            if (
                identity is None
                or identity in baseline
                or item["body"]["sha256"] != binding["body"]["sha256"]
                or item.get("author", {}).get("login")
                != binding["expected_actor_identity"]["login"]
            ):
                continue
            if identity in history["known_identities"]:
                continue
            if binding["operation"] == "create_inline_reply":
                if (
                    item["kind"] != "inline_review_comment"
                    or item.get("thread", {}).get("node_id")
                    != binding["placement"]["thread_node_id"]
                ):
                    continue
            elif item["kind"] != "pr_conversation_comment":
                continue
            result.append(item)
        return result

    def reconcile(self, intent_key: str) -> dict[str, Any]:
        _required_text(intent_key, "intent_key")
        with self.store.locked(exclusive=True):
            history = self.store.semantic_history()
            intent_id = history["keys"].get(intent_key)
            if intent_id is None:
                raise AdmissionError("intent key has no durable binding")
            admitted = history["intents"][intent_id]
            owner = history["owners"][admitted["owner_id"]]
            decision = history["reconciliation_decisions"][intent_id]
            if decision["kind"] == "already_confirmed":
                return history["outcomes"][decision["outcome_id"]]
            if decision["kind"] == "ineligible":
                raise AdmissionError(
                    "intent has no unknown provider-attempted evidence to reconcile"
                )
            prior_attempt = history["attempts"][
                history["current_attempt_by_intent"][intent_id]
            ]
            binding = admitted["binding"]
            open_rounds = [
                item
                for item in history["reconciliations"].values()
                if item["intent_id"] == intent_id and item.get("state") == "live"
            ]
            all_rounds = [
                item
                for item in history["reconciliations"].values()
                if item["intent_id"] == intent_id
            ]
            exact_body = base64.b64decode(binding["body"]["utf8_base64"])
            prior_outcome_id = history["effective_outcome_by_attempt"].get(
                prior_attempt["attempt_id"]
            )
            prior_outcome = history["outcomes"].get(prior_outcome_id)
            requested_identity = decision.get("identity")
            if open_rounds:
                active_round = open_rounds[0]
                reconciliation_id = active_round["reconciliation_id"]
                requested_identity = (
                    active_round["candidate_reservation"] or requested_identity
                )
            else:
                reconciliation_id = f"reconciliation-{digest({'attempt_id': prior_attempt['attempt_id'], 'round': len(all_rounds) + 1})}"
                started = {
                    "schema_version": 2,
                    "reconciliation_id": reconciliation_id,
                    "owner_id": owner["owner_id"],
                    "intent_id": intent_id,
                    "attempt_id": prior_attempt["attempt_id"],
                    "intent_key": intent_key,
                    "binding_digest": admitted["binding_digest"],
                    "prior_reconciliation_id": all_rounds[-1]["reconciliation_id"]
                    if all_rounds
                    else None,
                    "supersedes_incomplete_reconciliation_id": None,
                    "candidate_reservation": requested_identity,
                }
                self.store.append(
                    "reconciliation_started", started, record_id=reconciliation_id
                )
                history = self.store.semantic_history()
            receipt: dict[str, Any] | None = None
            if decision["kind"] == "ambiguous_effective_unknown":
                receipt = {
                    "schema_version": 1,
                    "status": "unknown",
                    "reason": "another effective unknown write has an indistinguishable provider result",
                    "retryable": False,
                    "side_effect": "unknown",
                    "provider_evidence": {
                        "competing_intent_ids": decision["intent_ids"]
                    },
                }
            elif requested_identity is None:
                if decision["kind"] != "collection_discovery_candidate":
                    raise AdmissionError(
                        "closed reconciliation decision is unsupported"
                    )
                else:
                    try:
                        current = self.epoch_adapter.acquire(
                            binding["target"]["repository"]["name_with_owner"],
                            binding["target"]["pull_request"]["number"],
                        )
                        candidates = self._reconciliation_candidates(
                            admitted, binding["admission_epoch"], current, history
                        )
                        if len(candidates) != 1:
                            raise GhTransportError(
                                "empty_eventually_consistent_list_does_not_prove_absence"
                                if not candidates
                                else "multiple_exact_results_are_ambiguous"
                            )
                        source = candidates[0]
                        requested_identity = {
                            "object_kind": self._acquisition_object_kind(
                                source["kind"]
                            ),
                            "database_id": source["provider_identity"]["database_id"],
                            "node_id": source["provider_identity"]["node_id"],
                        }
                        all_rounds = [
                            item
                            for item in history["reconciliations"].values()
                            if item["intent_id"] == intent_id
                        ]
                        reserved_id = f"reconciliation-{digest({'attempt_id': prior_attempt['attempt_id'], 'round': len(all_rounds) + 1})}"
                        self.store.append(
                            "reconciliation_started",
                            {
                                "schema_version": 2,
                                "reconciliation_id": reserved_id,
                                "owner_id": owner["owner_id"],
                                "intent_id": intent_id,
                                "attempt_id": prior_attempt["attempt_id"],
                                "intent_key": intent_key,
                                "binding_digest": admitted["binding_digest"],
                                "prior_reconciliation_id": reconciliation_id,
                                "supersedes_incomplete_reconciliation_id": reconciliation_id,
                                "candidate_reservation": requested_identity,
                            },
                            record_id=reserved_id,
                        )
                        reconciliation_id = reserved_id
                        history = self.store.semantic_history()
                    except GhTransportError as error:
                        receipt = {
                            "schema_version": 1,
                            "status": "unknown",
                            "reason": str(error),
                            "retryable": False,
                            "side_effect": "unknown",
                            "provider_evidence": error.evidence,
                        }
            if receipt is None:
                adapter = (
                    self.inline_adapter
                    if binding["operation"] == "create_inline_reply"
                    else self.conversation_adapter
                )
                try:
                    receipt = adapter.reread_known(
                        repo=binding["target"]["repository"]["name_with_owner"],
                        response_identity=requested_identity,
                        exact_body=exact_body,
                        expected_actor_login=binding["expected_actor_identity"][
                            "login"
                        ],
                    )
                except (GhTransportError, ValueError) as error:
                    receipt = {
                        "schema_version": 1,
                        "status": "unknown",
                        "reason": str(error),
                        "retryable": False,
                        "side_effect": "unknown",
                        "provider_evidence": getattr(error, "evidence", {}),
                    }
            retained_drift = (
                prior_outcome.get("post_write_drift_assessment")
                if prior_outcome
                else None
            )
            drift = (
                retained_drift
                if isinstance(retained_drift, dict)
                and retained_drift.get("state") in {"observed", "not_observed"}
                else self._unknown_drift(
                    "historical immediate post-write interval was not durably observed"
                )
            )
            pseudo_attempt = {
                **prior_attempt,
                "attempt_id": prior_attempt["attempt_id"],
            }
            outcome = self._outcome(
                owner,
                admitted,
                pseudo_attempt,
                receipt,
                drift,
                reconciles_attempt_id=prior_attempt["attempt_id"],
                reconciliation_id=reconciliation_id,
            )
            observations = self._receipt_identities(binding["operation"], receipt)
            claim = (
                receipt.get("reread_response_identity")
                if receipt.get("status") == "confirmed_success"
                and receipt.get("exact_reread")
                else None
            )
            result = (
                "confirmed_success"
                if receipt["status"] == "confirmed_success"
                else "still_unknown"
            )
            payload = {
                "schema_version": 2,
                "reconciliation_id": reconciliation_id,
                "attempt_id": prior_attempt["attempt_id"],
                "owner_id": owner["owner_id"],
                "intent_id": intent_id,
                "result": result,
                "outcome": outcome,
                "identity_observations": observations,
                "identity_claim": claim,
                "absence_evidence": None,
            }
            self.store.append(
                "reconciliation_resolution",
                payload,
                record_id=f"resolution-{reconciliation_id}",
            )
            return outcome
