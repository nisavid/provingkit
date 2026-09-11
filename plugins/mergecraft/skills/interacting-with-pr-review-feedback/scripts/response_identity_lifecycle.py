"""Private response attribution and typed-identity lifecycle authority."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from typing import Any


class ResponseIdentityError(ValueError):
    """The validated record contradicts the retained identity lifecycle."""


Identity = tuple[str, int, str]

OPERATION_OBJECT_KINDS = {
    "create_inline_reply": "PullRequestReviewComment",
    "create_pull_request_conversation_comment": "IssueComment",
}


def _identity(value: Any, name: str) -> Identity:
    if not isinstance(value, dict) or set(value) != {
        "object_kind",
        "database_id",
        "node_id",
    }:
        raise ResponseIdentityError(f"invalid {name} field set")
    kind = value["object_kind"]
    database_id = value["database_id"]
    node_id = value["node_id"]
    if (
        not isinstance(kind, str)
        or not kind
        or type(database_id) is not int
        or database_id <= 0
        or not isinstance(node_id, str)
        or not node_id
    ):
        raise ResponseIdentityError(f"invalid {name}")
    return kind, database_id, node_id


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class ResponseIdentityAuthority:
    """Own response-result equivalence and the complete identity lifecycle."""

    def __init__(self, state: Callable[[], dict[str, Any]]) -> None:
        self._state = state

    @staticmethod
    def _correlation_key(binding: dict[str, Any]) -> dict[str, Any]:
        target = binding["target"]
        repository = target["repository"]
        pull_request = target["pull_request"]
        operation = binding["operation"]
        return {
            "schema_version": 1,
            "provider_target": {
                "host": target["host"],
                "repository_identity": copy.deepcopy(repository["provider_identity"]),
                "pull_request_identity": {
                    "database_id": pull_request["database_id"],
                    "node_id": pull_request["node_id"],
                    "number": pull_request["number"],
                },
            },
            "operation": operation,
            "response_object_kind": OPERATION_OBJECT_KINDS[operation],
            "placement": copy.deepcopy(binding["placement"]),
            "expected_actor_login": binding["expected_actor_identity"]["login"],
            "body": copy.deepcopy(binding["body"]),
        }

    def _roles(self, identity: Identity) -> set[str]:
        state = self._state()
        intents = set(state["identity_observers"].get(identity, set()))
        owner = state["identity_owners"].get(identity)
        reservation = state["identity_reservations"].get(identity)
        if owner is not None:
            intents.add(owner)
        if reservation is not None:
            intents.add(reservation["intent_id"])
        return intents

    def _validate_kind(self, identity: Identity, intent_id: str) -> None:
        operation = self._state()["intents"][intent_id]["binding"]["operation"]
        if identity[0] != OPERATION_OBJECT_KINDS[operation]:
            raise ResponseIdentityError(
                "response identity kind contradicts the operation"
            )

    def _require_same_intent(self, identity: Identity, intent_id: str) -> None:
        self._validate_kind(identity, intent_id)
        if self._roles(identity) - {intent_id}:
            raise ResponseIdentityError(
                "response identity belongs to another intent lifecycle"
            )

    def _observe_all(self, values: list[Any], intent_id: str) -> list[Identity]:
        identities = [_identity(value, "identity observation") for value in values]
        for identity in identities:
            self._require_same_intent(identity, intent_id)
        return identities

    def _attempt_resolution(self, payload: dict[str, Any]) -> None:
        state = self._state()
        intent_id = payload["intent_id"]
        observations = self._observe_all(payload["identity_observations"], intent_id)
        claim = payload["identity_claim"]
        claimed = _identity(claim, "identity claim") if claim is not None else None
        if claimed is not None:
            self._require_same_intent(claimed, intent_id)
            if claimed not in observations:
                raise ResponseIdentityError(
                    "identity claim lacks a matching observation"
                )
        for identity in observations:
            state["identity_observers"].setdefault(identity, set()).add(intent_id)
        if claimed is not None:
            state["identity_owners"][claimed] = intent_id

    def _reconciliation_started(self, payload: dict[str, Any]) -> None:
        state = self._state()
        intent_id = payload["intent_id"]
        reconciliation_id = payload["reconciliation_id"]
        supersedes = payload["supersedes_incomplete_reconciliation_id"]
        prior_identity = None
        if supersedes is not None:
            prior = state["reconciliations"][supersedes]["candidate_reservation"]
            if prior is not None:
                prior_identity = _identity(prior, "prior candidate reservation")
                self._require_same_intent(prior_identity, intent_id)
                retained = state["identity_reservations"].get(prior_identity)
                if retained is None or retained["reconciliation_id"] != supersedes:
                    raise ResponseIdentityError(
                        "reconciliation reservation owner is contradictory"
                    )
        reservation = payload["candidate_reservation"]
        new_identity = (
            _identity(reservation, "candidate reservation")
            if reservation is not None
            else None
        )
        if new_identity is not None:
            self._require_same_intent(new_identity, intent_id)
            retained = state["identity_reservations"].get(new_identity)
            if retained is not None and new_identity != prior_identity:
                raise ResponseIdentityError(
                    "response identity is already reserved by another reconciliation"
                )
        if prior_identity is not None:
            del state["identity_reservations"][prior_identity]
            if prior_identity != new_identity:
                state["identity_observers"].setdefault(prior_identity, set()).add(
                    intent_id
                )
        if new_identity is not None:
            state["identity_reservations"][new_identity] = {
                "reconciliation_id": reconciliation_id,
                "attempt_id": payload["attempt_id"],
                "intent_id": intent_id,
                "binding_digest": payload["binding_digest"],
            }

    def _reconciliation_resolution(self, payload: dict[str, Any]) -> None:
        state = self._state()
        intent_id = payload["intent_id"]
        reconciliation = state["reconciliations"][payload["reconciliation_id"]]
        reservation = reconciliation["candidate_reservation"]
        reserved = (
            _identity(reservation, "candidate reservation")
            if reservation is not None
            else None
        )
        values = list(payload["identity_observations"])
        if reserved is not None and reserved not in [
            _identity(value, "identity observation") for value in values
        ]:
            values.append(reservation)
        observations = self._observe_all(values, intent_id)
        if reserved is not None:
            retained = state["identity_reservations"].get(reserved)
            if (
                retained is None
                or retained["reconciliation_id"] != payload["reconciliation_id"]
                or retained["intent_id"] != intent_id
            ):
                raise ResponseIdentityError(
                    "reconciliation reservation owner is contradictory"
                )
        claim = payload["identity_claim"]
        claimed = _identity(claim, "identity claim") if claim is not None else None
        if claimed is not None:
            self._require_same_intent(claimed, intent_id)
            if claimed not in observations or (
                reserved is not None and claimed != reserved
            ):
                raise ResponseIdentityError(
                    "reconciliation identity claim is not exclusive"
                )
        for identity in observations:
            state["identity_observers"].setdefault(identity, set()).add(intent_id)
        if reserved is not None:
            del state["identity_reservations"][reserved]
        if claimed is not None:
            state["identity_owners"][claimed] = intent_id

    def apply_transition(
        self, record_kind: str, validated_payload: dict[str, Any]
    ) -> None:
        handlers = {
            "attempt_resolution": self._attempt_resolution,
            "reconciliation_started": self._reconciliation_started,
            "reconciliation_resolution": self._reconciliation_resolution,
        }
        handler = handlers.get(record_kind)
        if handler is not None:
            handler(validated_payload)

    def _groups(self) -> dict[str, dict[str, Any]]:
        state = self._state()
        groups: dict[str, dict[str, Any]] = {}
        for intent_id, attempt_id in state["current_attempt_by_intent"].items():
            if state["effective_disposition_by_attempt"].get(attempt_id) != "unknown":
                continue
            binding = state["intents"][intent_id]["binding"]
            value = self._correlation_key(binding)
            canonical = _canonical(value)
            group = groups.setdefault(
                canonical, {"correlation_key": value, "intent_ids": []}
            )
            group["intent_ids"].append(intent_id)
        for group in groups.values():
            group["intent_ids"].sort()
        return groups

    @staticmethod
    def _receipt_identity(receipt: Any, expected_kind: str) -> dict[str, Any] | None:
        if not isinstance(receipt, dict):
            return None
        for name in (
            "reread_response_identity",
            "requested_reread_identity",
            "created_response_identity",
        ):
            value = receipt.get(name)
            if isinstance(value, dict) and value.get("object_kind") == expected_kind:
                _identity(value, name)
                return copy.deepcopy(value)
        evidence = receipt.get("provider_evidence")
        if isinstance(evidence, dict):
            for name in (
                "reread_response_identity",
                "requested_reread_identity",
                "created_response_identity",
            ):
                value = evidence.get(name)
                if (
                    isinstance(value, dict)
                    and value.get("object_kind") == expected_kind
                ):
                    _identity(value, name)
                    return copy.deepcopy(value)
        return None

    def reconciliation_decision(self, intent_id: str) -> dict[str, Any]:
        state = self._state()
        attempt_id = state["current_attempt_by_intent"].get(intent_id)
        if attempt_id is None:
            return {"kind": "ineligible", "reason": "no_provider_attempt"}
        disposition = state["effective_disposition_by_attempt"].get(attempt_id)
        outcome_id = state["effective_outcome_by_attempt"].get(attempt_id)
        if disposition == "confirmed_success":
            return {"kind": "already_confirmed", "outcome_id": outcome_id}
        if disposition != "unknown":
            return {"kind": "ineligible", "reason": disposition}
        live = [
            value
            for value in state["reconciliations"].values()
            if value["intent_id"] == intent_id and value.get("state") == "live"
        ]
        if live and live[0]["candidate_reservation"] is not None:
            return {
                "kind": "known_identity_candidate",
                "identity": copy.deepcopy(live[0]["candidate_reservation"]),
            }
        outcome = state["outcomes"].get(outcome_id)
        if outcome is not None:
            operation = state["intents"][intent_id]["binding"]["operation"]
            identity = self._receipt_identity(
                outcome["leaf_receipt"], OPERATION_OBJECT_KINDS[operation]
            )
            if identity is not None:
                self._require_same_intent(
                    _identity(identity, "known identity"), intent_id
                )
                return {"kind": "known_identity_candidate", "identity": identity}
        binding = state["intents"][intent_id]["binding"]
        group = self._groups()[_canonical(self._correlation_key(binding))]
        if len(group["intent_ids"]) > 1:
            return {
                "kind": "ambiguous_effective_unknown",
                "correlation_key": copy.deepcopy(group["correlation_key"]),
                "intent_ids": list(group["intent_ids"]),
            }
        return {
            "kind": "collection_discovery_candidate",
            "correlation_key": copy.deepcopy(group["correlation_key"]),
        }

    def projection(self) -> dict[str, Any]:
        state = self._state()
        groups = self._groups()
        return {
            "identity_owners": copy.deepcopy(state["identity_owners"]),
            "identity_observers": copy.deepcopy(state["identity_observers"]),
            "identity_reservations": copy.deepcopy(state["identity_reservations"]),
            "known_identities": frozenset(
                set(state["identity_owners"])
                | set(state["identity_observers"])
                | set(state["identity_reservations"])
            ),
            "effective_unknown_groups": tuple(
                {
                    "correlation_key": copy.deepcopy(group["correlation_key"]),
                    "intent_ids": tuple(group["intent_ids"]),
                }
                for _, group in sorted(groups.items())
            ),
            "reconciliation_decisions": {
                intent_id: self.reconciliation_decision(intent_id)
                for intent_id in state["intents"]
            },
        }
