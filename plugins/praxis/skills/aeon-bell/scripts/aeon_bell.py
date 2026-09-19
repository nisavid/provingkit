#!/usr/bin/env python3
"""Aeon Bell: bounded local monitor, registry, and conditional-dispatch engine.

Owners register gated task continuations. A periodic monitor cycle reuses fresh
shared gate observations, requests each due gate once, and proposes wakes only
for registered, currently eligible targets. The engine never reads credentials,
never calls external services, and never executes native task tools; it emits
structured proposals and records attempts before the coordinator sends them.
"""

from __future__ import annotations

import argparse
import base64
import copy
import fcntl
import hashlib
import json
import math
import os
import re
import secrets
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

FORMAT = "praxis-aeon-bell-store"
FORMAT_VERSION = 1
STATE_NAME = "state.json"
LOCK_NAME = "lock"

ENTRY_REF_PREFIX = "ab1."
CONTINUATION_PREFIX = "ab1c."
REGISTRY_ID_LENGTH = 32
INVOCATION_ID_LENGTH = 24
INTERRUPTED_EFFECT_LIMIT = 64

GATE_KINDS = {"quota_recovery", "daybreak_status"}
GATE_FIELDS = {
    "quota_recovery": {"kind", "account", "route", "bucket", "policy_revision"},
    "daybreak_status": {"kind", "account", "route", "model", "policy_revision"},
}

# Freshness says how old an observation may be and still open a gate. It is a
# maximum usable age, not a polling interval: when a gate is next queried is
# the schedule's decision (see the adaptive polling constants below), and an
# explicit effective interval may query again while the prior observation is
# still fresh. Freshness itself is never shortened by the schedule.
OBSERVATION_FRESHNESS_MINUTES = 15
TASK_STATE_FRESHNESS_MINUTES = 15
BACKOFF_BASE_MINUTES = 15
BACKOFF_CEILING_MINUTES = 6 * 60

# Adaptive polling. A gate's next query is planned from the anchor (the
# observed_at of its latest successful observation) and the current owner
# metadata, never from a remembered tick: a closed gate is requeried after a
# quarter of the estimated remaining wait, bounded below and above; with no
# usable estimate after the anchor it waits the unknown default; an open gate
# whose registrations are still waiting is requeried when the observation can
# no longer admit. These bounds are separate from the provider-error backoff
# constants above, whose ceiling merely coincides today.
ADAPTIVE_OPEN_INTERVAL_MINUTES = 15
ADAPTIVE_MIN_INTERVAL_MINUTES = 15
ADAPTIVE_MAX_INTERVAL_MINUTES = 6 * 60
ADAPTIVE_UNKNOWN_INTERVAL_MINUTES = 60
ADAPTIVE_WAIT_DIVISOR = 4
# Registry-level bounds: a pending notice or an unrelayed reservation is
# recovered within the recovery bound; a registry with nothing waiting, or a
# gate no passed binding owns, is revisited within the liveness bound. Both are
# maximum waits from the read, not anchored deadlines.
RECOVERY_CHECK_MINUTES = 15
LIVENESS_CHECK_MINUTES = 6 * 60

TASK_STATUSES = {
    "idle",
    "running",
    "completed",
    "archived",
    "canceled",
    "human_waiting",
    "unavailable",
    "unknown",
}

MAX_ATTEMPTS_PER_EPISODE = 3
EVIDENCE_MAX_BYTES = 4096

IDENTITY_MAX_LENGTH = 256
CONTINUATION_MAX_LENGTH = 8000
DEFAULT_EXPIRY_MINUTES = 24 * 60
MAX_EXPIRY_MINUTES = 7 * 24 * 60

# Owner cadence metadata. An explicit effective interval is the cadence the
# authorized caller already resolved from operator or policy requirements; the
# engine applies it and never invents or reconciles policy. The sentinels clear
# a field on the command line.
EXPLICIT_INTERVAL_MAX_MINUTES = 7 * 24 * 60
FORECAST_UNKNOWN = "unknown"
INTERVAL_ADAPTIVE = "adaptive"


class AeonBellError(ValueError):
    """A public-seam failure with a stable machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _reference(prefix: str, value: dict[str, Any]) -> str:
    encoded = base64.urlsafe_b64encode(canonical_bytes(value)).decode("ascii")
    return prefix + encoded.rstrip("=")


def _reference_value(value: Any, prefix: str, fields: set[str]) -> dict[str, Any]:
    if not isinstance(value, str) or not value.startswith(prefix) or len(value) > 4096:
        raise AeonBellError("invalid-reference", "monitor reference is malformed")
    encoded = value[len(prefix) :]
    try:
        raw = base64.b64decode(
            encoded + "=" * (-len(encoded) % 4), altchars=b"-_", validate=True
        )
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as error:
        raise AeonBellError("invalid-reference", "monitor reference is malformed") from error
    if not isinstance(payload, dict) or set(payload) != fields:
        raise AeonBellError("invalid-reference", "monitor reference is malformed")
    return payload


def _entry_reference(value: Any) -> dict[str, Any]:
    payload = _reference_value(
        value, ENTRY_REF_PREFIX, {"store", "registry_id", "config_revision"}
    )
    if not (
        isinstance(payload["store"], str)
        and os.path.isabs(payload["store"])
        and AeonBell._is_hex_id(payload["registry_id"], REGISTRY_ID_LENGTH)
        and type(payload["config_revision"]) is int
        and payload["config_revision"] >= 1
    ):
        raise AeonBellError("invalid-reference", "monitor reference is malformed")
    return payload


def _continuation_reference(value: Any) -> dict[str, Any]:
    fields = {
        "store",
        "registry_id",
        "config_revision",
        "invocation_id",
        "generation",
        "tick_id",
        "action_id",
    }
    payload = _reference_value(value, CONTINUATION_PREFIX, fields)
    if not (
        isinstance(payload["store"], str)
        and os.path.isabs(payload["store"])
        and AeonBell._is_hex_id(payload["registry_id"], REGISTRY_ID_LENGTH)
        and type(payload["config_revision"]) is int
        and payload["config_revision"] >= 1
        and AeonBell._is_hex_id(payload["invocation_id"], INVOCATION_ID_LENGTH)
        and type(payload["generation"]) is int
        and payload["generation"] >= 1
        and AeonBell._is_hex_id(payload["tick_id"], TICK_ID_LENGTH)
        and AeonBell._is_hex_id(payload["action_id"], ACTION_ID_LENGTH)
    ):
        raise AeonBellError("invalid-reference", "monitor reference is malformed")
    return payload


def parse_time(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise AeonBellError("invalid-time", f"{name} must be an ISO 8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise AeonBellError(
            "invalid-time", f"{name} must be an ISO 8601 timestamp"
        ) from error
    if parsed.tzinfo is None:
        raise AeonBellError("invalid-time", f"{name} must carry a UTC offset")
    return parsed.astimezone(timezone.utc)


def format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def _identity(value: Any, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > IDENTITY_MAX_LENGTH
        or not value.isprintable()
        or value != value.strip()
    ):
        raise AeonBellError(
            "invalid-identity",
            f"{name} must be printable text of at most {IDENTITY_MAX_LENGTH} characters",
        )
    return value


def _continuation(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AeonBellError(
            "invalid-continuation", "continuation must be nonempty text"
        )
    if len(value) > CONTINUATION_MAX_LENGTH:
        raise AeonBellError(
            "invalid-continuation",
            f"continuation must be at most {CONTINUATION_MAX_LENGTH} characters",
        )
    if any(ch.isprintable() is False and ch not in "\n\t" for ch in value):
        raise AeonBellError(
            "invalid-continuation", "continuation must not contain control characters"
        )
    return value


def validate_gate(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise AeonBellError("invalid-gate", "gate must be a JSON object")
    kind = value.get("kind")
    if kind not in GATE_KINDS:
        raise AeonBellError(
            "invalid-gate", f"gate kind must be one of {sorted(GATE_KINDS)}"
        )
    if set(value) != GATE_FIELDS[kind]:
        raise AeonBellError(
            "invalid-gate",
            f"{kind} gate must have exactly the fields {sorted(GATE_FIELDS[kind])}",
        )
    return {name: _identity(value[name], f"gate.{name}") for name in sorted(value)}


def gate_key(gate: dict[str, str]) -> str:
    return digest(gate)


def _is_gate_key(value: Any) -> bool:
    """True for a well-formed gate key, the only input value safe to echo."""
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    )


def _expiry_minutes(value: Any) -> int:
    if value is None:
        return DEFAULT_EXPIRY_MINUTES
    if type(value) is not int or value <= 0 or value > MAX_EXPIRY_MINUTES:
        raise AeonBellError(
            "invalid-expiry",
            f"expires-in-minutes must be an integer from 1 to {MAX_EXPIRY_MINUTES}",
        )
    return value


def _forecast(value: Any, now: datetime, expires_at: datetime) -> str | None:
    """Validate a new owner forecast: ``unknown`` clears; a time must lie after
    now and before the registration's resulting expiry, which is never
    extended to fit it."""
    if value == FORECAST_UNKNOWN:
        return None
    if not isinstance(value, str) or not value:
        raise AeonBellError(
            "invalid-forecast",
            f"expected-open-at must be an ISO 8601 timestamp with offset or {FORECAST_UNKNOWN}",
        )
    try:
        forecast = parse_time(value, "expected-open-at")
    except AeonBellError as error:
        raise AeonBellError(
            "invalid-forecast",
            f"expected-open-at must be an ISO 8601 timestamp with offset or {FORECAST_UNKNOWN}",
        ) from error
    if forecast <= now:
        raise AeonBellError("invalid-forecast", "expected-open-at must be in the future")
    if forecast >= expires_at:
        raise AeonBellError(
            "invalid-forecast",
            "expected-open-at must be before the registration expires; renew the "
            "expiry in the same command to forecast later",
        )
    return format_time(forecast)


def _interval(value: Any) -> int | None:
    """Validate an explicit effective interval: ``adaptive`` clears; otherwise
    a whole number of minutes from 1 to the explicit maximum."""
    if value == INTERVAL_ADAPTIVE:
        return None
    if (
        not isinstance(value, str)
        or not value.isascii()
        or not value.isdigit()
        or int(value) < 1
        or int(value) > EXPLICIT_INTERVAL_MAX_MINUTES
    ):
        raise AeonBellError(
            "invalid-interval",
            f"poll-interval-minutes must be an integer from 1 to "
            f"{EXPLICIT_INTERVAL_MAX_MINUTES} or {INTERVAL_ADAPTIVE}",
        )
    return int(value)


OBSERVATION_COMMON_FIELDS = {"gate_key", "status", "observed_at", "expires_at"}
OBSERVATION_FIELDS = {
    "quota_recovery": OBSERVATION_COMMON_FIELDS
    | {"account", "route", "buckets", "credits"},
    "daybreak_status": OBSERVATION_COMMON_FIELDS
    | {"account", "route", "exposed_models", "capacity", "reset_at"},
}
# Fields an observation may omit. ``reset_at`` is the daybreak_status reset
# hint (a quota_recovery observation carries its hint inside the bucket and
# never at the top level, which the per-kind allowed set still enforces).
OBSERVATION_OPTIONAL_FIELDS = {"expires_at", "credits", "reset_at"}
ERROR_OBSERVATION_FIELDS = {"gate_key", "status", "observed_at", "reason"}
CAPACITY_STATES = {"available", "exhausted", "unknown"}
# A closed observation's reset hint feeds the adaptive plan only when exhausted
# capacity is what closed it: a reset says nothing about a missing model, an
# unknown capacity, or a binding mismatch.
RESET_HINT_REASONS = {"bucket-exhausted", "capacity-exhausted"}

NATIVE_LIMITATIONS = [
    (
        "no_atomic_idle_only_send: the native read and send-follow-up tools are "
        "separate; a target may start running between the read and the send, so "
        "send may steer an already-running task"
    ),
    (
        "no_idempotency_token: the native send tool offers no caller idempotency "
        "token; an unknown send outcome requires reconciliation and is never "
        "retried automatically"
    ),
    (
        "registry_recheck_is_not_atomic: the pre-send inspect and the send are "
        "separate steps; an owner remove, rearm, or expiry landing between them "
        "is not prevented (gate and continuation are frozen while reserved, so no "
        "other owner change can land), the engine records the outcome without "
        "overriding the owner's later state, and the woken target's own episode "
        "check is the last guard"
    ),
    (
        "observation_is_a_snapshot: a gate observed open may close before the "
        "continuation runs; the woken target must revalidate its own eligibility, "
        "quota, and policy before work"
    ),
    (
        "acceptance_is_not_delivery: a send accepted by the native tool is not "
        "proof that the target received, read, or acted on the continuation"
    ),
    (
        "schedule_is_advisory: the schedule and its registry fingerprint recommend "
        "the next check from durable state at computation time; they authorize no "
        "work and are not an atomic lease on the native heartbeat, whose read and "
        "update are separate steps that a fresh inspect must recheck"
    ),
]


# Notification state: the engine, not the monitor's context, owns which standing
# conditions and attempt resolutions were already relayed. ``notice`` freezes a
# pending snapshot; ``acknowledge`` promotes exactly that snapshot to the
# baseline. Acknowledgement records the caller's assertion that the text was
# relayed; it is not receipt by anyone. Beside those two sits the durable
# per-gate query knowledge (``knowledge``: gate key to the latest adapter
# outcome), which every valid adapter report updates whether or not a notice
# is pending, and which acknowledgement never reads or rewrites.
NOTICE_ID_LENGTH = 24
EVENT_STATUSES = {
    "accepted",
    "not_sent",
    "unknown",
    "reconciled_accepted",
    "reconciled_not_sent",
}
DELIVERY_CLAIMS = {
    "accepted": "accepted_by_native_send_tool",
    "reconciled_accepted": "accepted_by_native_send_tool",
    "not_sent": "not_sent",
    "reconciled_not_sent": "not_sent",
    "unknown": "unknown_requires_reconciliation",
}
ADAPTER_OUTCOMES = {"observed", "held", "error", "unhandled"}
# Configuration knowledge the directed tick learns from its own inputs, never
# from an adapter: ``no-binding`` records that a due gate was requested while
# no binding path was passed at all, so no query was issued. It sits beside
# the adapter outcomes in the per-gate knowledge and is a configuration gap
# like ``unhandled``, but it is not query evidence and never comes from a
# report.
CONFIGURATION_OUTCOMES = {"no-binding"}
KNOWLEDGE_OUTCOMES = ADAPTER_OUTCOMES | CONFIGURATION_OUTCOMES
CONFIGURATION_GAP_OUTCOMES = {"unhandled", "no-binding"}
ADAPTER_GATE_FIELDS = {"gate_key", "kind", "outcome", "reason"}
NOTIFICATION_LIMITATION = (
    "acknowledgement_is_not_receipt: acknowledge records the caller's assertion "
    "that the notice text was relayed; a notice pending across a crash is relayed "
    "again (at least once), and nothing here proves a person received or read it"
)

# The directed tick: the engine issues one fully bound action at a time
# (task_read, observe, send, emit, heartbeat_set) and the monitor submits the
# typed result of exactly that action. The engine binds and orders those
# results and applies their consequences; it never verifies that the named
# tool was invoked or that a result is true. Durable tick state lives under
# one additive private store key beside the notification state.
TICK_ID_LENGTH = 24
ACTION_ID_LENGTH = 12
TICK_PHASES = (
    "task_states",
    "observe",
    "dispatch",
    "notice",
    "schedule",
    "diagnostics",
    "done",
)
TICK_TIME_MODES = {"supplied", "clock"}
ACTION_KINDS = {"task_read", "observe", "send", "emit", "heartbeat_set"}
ACTION_PURPOSES = {
    "task_read": {"task-state", "pre-send"},
    "observe": {"query"},
    "send": {"wake"},
    "emit": {"notice", "diagnostics"},
    "heartbeat_set": {"schedule"},
}
FAILURE_DISPOSITIONS = {"not_performed", "failed", "unavailable"}
ACTION_DISPOSITIONS = {"pending", "performed"} | FAILURE_DISPOSITIONS
RESUMABLE_KINDS = {"task_read", "observe"}
CONSEQUENCE_CODES = {
    "task-state-recorded",
    "no-task-state",
    "observation-ingested",
    "query-failed",
    "attempt-accepted",
    "attempt-not-sent",
    "attempt-unknown",
    "attempt-superseded",
    "notice-acknowledged",
    "notice-still-pending",
    "notice-acknowledged-elsewhere",
    "diagnostics-emitted",
    "diagnostics-unemitted",
    "heartbeat-applied",
    "heartbeat-applied-off-target",
    "heartbeat-control-failed",
}
OBSERVE_NOT_ISSUED_REASONS = {"no-request", "no-binding", "artifact-io"}
ARTIFACT_CODES = {
    "invalid-adapter-report",
    "invalid-observation",
    "invalid-input",
    "artifact-io",
}
HEARTBEAT_RULES = {
    "schedule-as-printed",
    "failed-observation-recovery",
    "fresh-owner-work",
}
HEARTBEAT_RESULTS = {"applied", "applied-off-target"} | FAILURE_DISPOSITIONS
DISPATCH_STAGES = {"recheck", "pre-send", "send"}
DISPATCH_RESULTS = {"accepted", "not_sent", "unknown", "superseded", "pending"}
NOTICE_CONSEQUENCES = {
    "notice-acknowledged",
    "notice-still-pending",
    "notice-acknowledged-elsewhere",
}
RESULT_WINDOW_SECONDS = 60
HEARTBEAT_OFF_TARGET_SECONDS = 60
TICK_DIAGNOSTICS_MAX_LINES = 32
TICK_DIAGNOSTIC_MAX_CHARS = 512
TICK_MAX_HEARTBEAT_WRITES = 2
ARTIFACT_DIRECTORY = "ticks"
ARTIFACT_NAMES = ("plan.json", "report.json", "input.json")
# The adapter's exit-2 line is fixed, value-free text that the tick relays
# verbatim inside one diagnostics line as ``step observe: <line>``; its bound
# is that line's bound less the relay prefix, so an accepted line is never
# truncated on relay. The adapter's longest line today (the invalid-binding
# field-set error) is 232 characters.
OBSERVE_STEP_PREFIX = "step observe: "
STDERR_LINE_MAX_CHARS = TICK_DIAGNOSTIC_MAX_CHARS - len(OBSERVE_STEP_PREFIX)
STDERR_LINE_PATTERN = re.compile(r"^codex status: [a-z-]+: .+$")
TICK_LIMITATION = (
    "results_are_caller_assertions: every submitted result is the monitor's "
    "assertion about a native effect (a read, a send, printed text, a heartbeat "
    "write) inside the trusted single-user store; the engine binds and orders "
    "those assertions and never verifies them"
)
TICK_RECORD_FIELDS = {
    "tick_id",
    "status",
    "started_at",
    "finished_at",
    "time_mode",
    "last_now",
    "binding_paths",
    "heartbeat",
    "phase",
    "registration_order",
    "task_states",
    "requested_gate_keys",
    "observe",
    "proposals",
    "dispatch",
    "notice",
    "heartbeat_writes",
    "registry_changed_after_last_write",
    "diagnostics",
    "actions",
}
TICK_SUMMARY_FIELDS = {
    "tick_id",
    "status",
    "started_at",
    "finished_at",
    "abandoned_pending",
    "actions",
    "diagnostics_unemitted",
}
TICK_OBSERVE_FIELDS = {
    "issued",
    "not_issued_reason",
    "exit_code",
    "failure_line",
    "artifacts_code",
    "answered_gate_keys",
    "unanswered_gate_keys",
    "adapter_report_learned",
    "adapter_report",
}
TICK_ACTION_FIELDS = {
    "action_id",
    "kind",
    "purpose",
    "issued_at",
    "submitted_at",
    "disposition",
    "reason",
    "consequence",
    "recorded",
    "arguments",
    "require",
    "restart",
}
TICK_NOTICE_FIELDS = {"notice_id", "replayed", "emitted", "acknowledged", "consequence"}
TICK_PROPOSAL_FIELDS = {
    "attempt_id",
    "registration_id",
    "episode",
    "message",
    "message_sha256",
}
TICK_WRITE_FIELDS = {
    "write_number",
    "target_at",
    "delay_minutes",
    "rule",
    "fingerprint",
    "result",
    "next_run_at",
    "reason",
    "basis",
}
RESULT_SHAPES = {
    "task_read": {
        "status": "|".join(sorted(TASK_STATUSES)),
        "observed_at": "ISO 8601 with offset, within 60 seconds before issued_at and 60 seconds after now",
    },
    "observe": {
        "exit_code": "0|2",
        "stderr_line": "required exactly when exit_code is 2: the verbatim `codex status: <code>: <message>` line",
    },
    "send": {
        "outcome": "accepted|not_sent|unknown",
        "evidence": "optional flat JSON object of scalar values, at most 4096 bytes",
    },
    "emit": {"emitted": True},
    "heartbeat_set": {
        "applied": True,
        "next_run_at": "ISO 8601 with offset: the run the control left applied",
        "previous_next_run_at": "optional ISO 8601 with offset or null",
    },
}
FAILURE_FORM = {
    "disposition": "not_performed|failed|unavailable",
    "reason": f"printable text of at most {IDENTITY_MAX_LENGTH} characters",
}
ACTION_NOTES = {
    "task_read": (
        "read the target with the native task read tool and map its state "
        "truthfully, judging the episode named in the arguments; submit the "
        "failure form when the read could not be performed"
    ),
    "observe": "run argv exactly as printed, with no other arguments, and submit its exit code",
    "send": (
        "send message verbatim with the native send-follow-up tool, with no model "
        "or effort override; submit exactly what the tool did"
    ),
    "emit": "print text verbatim and submit that it was printed",
    "heartbeat_set": (
        "set the next run of the one existing heartbeat named by heartbeat to "
        "target_at with the harness's own control; submit the run it left applied"
    ),
}


def _bounded_text(value: Any, name: str, limit: int = IDENTITY_MAX_LENGTH) -> str:
    if not isinstance(value, str) or len(value) > limit or not value.isprintable():
        raise AeonBellError(
            "invalid-observation",
            f"{name} must be printable text of at most {limit} characters",
        )
    return value


def _evidence(value: Any) -> dict[str, Any]:
    """Accept a small flat JSON object of scalars as dispatch evidence."""
    if value is None:
        return {}
    if not isinstance(value, dict) or not all(
        isinstance(key, str)
        and (item is None or isinstance(item, (str, bool, int, float)))
        for key, item in value.items()
    ):
        raise AeonBellError(
            "invalid-evidence", "evidence must be a flat JSON object of scalar values"
        )
    if len(canonical_bytes(value)) > EVIDENCE_MAX_BYTES:
        raise AeonBellError(
            "invalid-evidence", f"evidence must be at most {EVIDENCE_MAX_BYTES} bytes"
        )
    return value


def _percent(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AeonBellError("invalid-observation", f"{name} must be a number")
    if math.isnan(value) or value < 0 or value > 100:
        raise AeonBellError("invalid-observation", f"{name} must be within 0 and 100")
    return float(value)


def evaluate_observation(
    gate: dict[str, str], observation: dict[str, Any]
) -> tuple[str, str, dict[str, Any]]:
    """Return (result, reason, evidence) for one typed status-adapter observation.

    Only explicit, matching, positive evidence yields ``open``. Reset timestamps,
    credits, nonmatching buckets or accounts, and missing or unknown values close.
    """
    kind = gate["kind"]
    if (
        observation["account"] != gate["account"]
        or observation["route"] != gate["route"]
    ):
        return "closed", "binding-mismatch", {"account_matches": False}
    if kind == "quota_recovery":
        buckets = observation["buckets"]
        if not isinstance(buckets, list):
            raise AeonBellError("invalid-observation", "buckets must be a list")
        matched: dict[str, Any] | None = None
        for bucket in buckets:
            if (
                not isinstance(bucket, dict)
                or not {"name", "remaining_percent"} <= set(bucket)
                or not set(bucket) <= {"name", "remaining_percent", "reset_at"}
            ):
                raise AeonBellError(
                    "invalid-observation",
                    "each bucket must carry name, remaining_percent, and optional reset_at",
                )
            if _bounded_text(bucket["name"], "bucket.name") == gate["bucket"]:
                matched = bucket
        if matched is None:
            return "closed", "bucket-missing", {"account_matches": True, "bucket": None}
        remaining = _percent(matched["remaining_percent"], "bucket.remaining_percent")
        evidence = {
            "account_matches": True,
            "bucket": gate["bucket"],
            "remaining_percent": remaining,
            "reset_at": (
                None
                if matched.get("reset_at") is None
                else format_time(parse_time(matched["reset_at"], "bucket.reset_at"))
            ),
        }
        if remaining > 0:
            return "open", "bucket-has-remaining-capacity", evidence
        return "closed", "bucket-exhausted", evidence
    models = observation["exposed_models"]
    if not isinstance(models, list) or not all(isinstance(m, str) for m in models):
        raise AeonBellError(
            "invalid-observation", "exposed_models must be a string list"
        )
    capacity = observation["capacity"]
    if capacity not in CAPACITY_STATES:
        raise AeonBellError(
            "invalid-observation", f"capacity must be one of {sorted(CAPACITY_STATES)}"
        )
    evidence = {
        "account_matches": True,
        "model_exposed": gate["model"] in models,
        "capacity": capacity,
        # The bound bucket's reset, when the adapter observed one. Recorded as
        # observed; the plan decides whether it applies (see RESET_HINT_REASONS).
        "reset_at": (
            None
            if observation.get("reset_at") is None
            else format_time(parse_time(observation["reset_at"], "reset_at"))
        ),
    }
    if gate["model"] not in models:
        return "closed", "model-not-exposed", evidence
    if capacity != "available":
        return "closed", f"capacity-{capacity}", evidence
    return "open", "model-exposed-with-capacity", evidence


def empty_state() -> dict[str, Any]:
    return {
        "format": FORMAT,
        "version": FORMAT_VERSION,
        "registrations": {},
        "observations": {},
        "retry_schedule": {},
        "attempts": {},
    }


REGISTRATION_STATUSES = {
    "waiting",
    "paused",
    "reserved",
    "completed",
    "unresolved",
    "expired",
    "removed",
}
ATTEMPT_STATUSES = {
    "reserved",
    "accepted",
    "not_sent",
    "unknown",
    "reconciled_accepted",
    "reconciled_not_sent",
    "superseded_reserved",
    "superseded_unknown",
}
UNRESOLVED_REASONS = {"delivery-unknown", "attempt-limit"}
OBSERVATION_RESULTS = {"open", "closed"}


def _validate_records(state: dict[str, Any]) -> None:
    """Refuse a store whose records lack a field the engine indexes directly.

    The four registry containers are read here, once per command, before any
    transaction can write: a record missing a required field, carrying a value
    outside its enumeration, or naming an attempt or registration the store
    does not hold is ``corrupt-store`` with a fixed message that names the
    container and never a key or value. Additive fields are ignored, and the
    supported legacy shapes still read: registrations without ``episodes``,
    ``attempt_count``, ``unresolved_reason``, ``attempt_id``,
    ``expected_open_at``, or ``poll_interval_minutes`` (the last two read as
    null and adaptive); attempts without ``gate``, ``evidence``, or
    ``reconciliation_evidence``. A
    registration written before ``unresolved_reason`` was owned by the
    unresolved status may still carry it on another status; it is read as
    carrying none. Notification state and attempt gate snapshots keep their
    own read boundaries (``notice`` and ``acknowledge``), so a malformed
    notice-only structure leaves the registry inspectable.
    """

    def text(item: Any) -> bool:
        return isinstance(item, str)

    def optional_text(item: Any) -> bool:
        return item is None or isinstance(item, str)

    def natural(item: Any) -> bool:
        return type(item) is int and item >= 0

    def strings(item: Any) -> bool:
        return isinstance(item, list) and all(isinstance(s, str) for s in item)

    def refuse(container: str) -> None:
        raise AeonBellError(
            "corrupt-store", f"a {container} record has an unsupported shape"
        )

    registrations = state["registrations"]
    attempts = state["attempts"]
    for record in registrations.values():
        if not (
            isinstance(record, dict)
            and all(
                text(record.get(name))
                for name in (
                    "registration_id",
                    "owner",
                    "host",
                    "task_id",
                    "episode",
                    "gate_key",
                    "continuation",
                    "registered_at",
                    "updated_at",
                    "expires_at",
                )
            )
            and natural(record.get("sequence"))
            and record.get("status") in REGISTRATION_STATUSES
            and strings(record.get("completed_episodes"))
            and ("episodes" not in record or strings(record["episodes"]))
            and optional_text(record.get("attempt_id"))
            and natural(record.get("attempt_count", 0))
            and record.get("unresolved_reason") in (None, *UNRESOLVED_REASONS)
            and (record.get("attempt_id") is None or record["attempt_id"] in attempts)
            and optional_text(record.get("expected_open_at"))
            and (
                record.get("poll_interval_minutes") is None
                or (
                    type(record["poll_interval_minutes"]) is int
                    and 1 <= record["poll_interval_minutes"] <= EXPLICIT_INTERVAL_MAX_MINUTES
                )
            )
        ):
            refuse("registration")
        try:
            validate_gate(record.get("gate"))
            if record.get("expected_open_at") is not None:
                parse_time(record["expected_open_at"], "expected_open_at")
        except AeonBellError:
            refuse("registration")
        if record["status"] != "unresolved":
            record.pop("unresolved_reason", None)
    for observation in state["observations"].values():
        if not (
            isinstance(observation, dict)
            and all(
                text(observation.get(name))
                for name in (
                    "gate_key",
                    "binding_digest",
                    "reason",
                    "observed_at",
                    "expires_at",
                )
            )
            and observation.get("result") in OBSERVATION_RESULTS
        ):
            refuse("observation")
    for schedule in state["retry_schedule"].values():
        if not (
            isinstance(schedule, dict)
            and natural(schedule.get("failures"))
            and text(schedule.get("last_reason"))
            and text(schedule.get("next_due_at"))
        ):
            refuse("retry schedule")
    for attempt in attempts.values():
        if not (
            isinstance(attempt, dict)
            and all(
                text(attempt.get(name))
                for name in (
                    "attempt_id",
                    "registration_id",
                    "host",
                    "task_id",
                    "episode",
                    "gate_key",
                    "gate_observed_at",
                    "planned_at",
                    "message_sha256",
                )
            )
            and attempt.get("status") in ATTEMPT_STATUSES
            and optional_text(attempt.get("resolved_at"))
            and attempt["registration_id"] in registrations
        ):
            refuse("attempt")


class Store:
    """One private local directory holding a single JSON state document."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def _prepare(self) -> None:
        if self.directory.exists() and not self.directory.is_dir():
            raise AeonBellError("invalid-store", "store path is not a directory")
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            os.chmod(self.directory, 0o700)
        except OSError:
            pass

    def _load(self) -> dict[str, Any]:
        path = self.directory / STATE_NAME
        if not path.exists():
            return empty_state()
        try:
            value = json.loads(path.read_bytes().decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as error:
            raise AeonBellError(
                "corrupt-store", "store state is not valid UTF-8 JSON"
            ) from error
        if (
            not isinstance(value, dict)
            or value.get("format") != FORMAT
            or value.get("version") != FORMAT_VERSION
            or any(
                not isinstance(value.get(name), dict)
                for name in (
                    "registrations",
                    "observations",
                    "retry_schedule",
                    "attempts",
                )
            )
        ):
            raise AeonBellError(
                "corrupt-store", "store state has an unsupported shape or version"
            )
        _validate_records(value)
        return value

    def save(self, state: dict[str, Any]) -> None:
        """Atomically replace the state document; call only inside a transaction."""
        path = self.directory / STATE_NAME
        staging = self.directory / f".{STATE_NAME}.{secrets.token_hex(8)}.tmp"
        fd = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(canonical_bytes(state) + b"\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(staging, path)
        except BaseException:
            staging.unlink(missing_ok=True)
            raise
        directory_fd = os.open(self.directory, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)

    @contextmanager
    def transaction(self, *, write: bool) -> Iterator[dict[str, Any]]:
        self._prepare()
        lock_fd = os.open(self.directory / LOCK_NAME, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            state = self._load()
            yield state
            if write:
                self.save(state)
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)

    @contextmanager
    def existing_transaction(self, *, write: bool) -> Iterator[dict[str, Any]]:
        """Open an existing registry without creating a path, lock, or state."""
        state_path = self.directory / STATE_NAME
        lock_path = self.directory / LOCK_NAME
        if not self.directory.is_dir() or not state_path.is_file():
            raise AeonBellError("registry-not-found", "configured registry does not exist")
        try:
            lock_fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        except FileNotFoundError as error:
            raise AeonBellError(
                "registry-not-found", "configured registry does not exist"
            ) from error
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            if not state_path.is_file():
                raise AeonBellError(
                    "registry-not-found", "configured registry does not exist"
                )
            state = self._load()
            yield state
            if write:
                self.save(state)
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)


class AeonBell:
    """Public engine API. Every method is one locked, atomic state transition."""

    def __init__(self, store: Path) -> None:
        self.store = Store(store)

    def _canonical_store(self) -> str:
        return os.path.realpath(os.path.abspath(self.store.directory))

    @staticmethod
    def _monitor_state(state: dict[str, Any]) -> dict[str, Any] | None:
        monitor = state.get("monitor")
        if monitor is None:
            return None
        required = {
            "registry_id",
            "canonical_store",
            "config_revision",
            "binding_paths",
            "heartbeat",
            "next_generation",
            "active_invocation",
            "interrupted_effects",
        }
        def time_ok(value: Any) -> bool:
            try:
                parse_time(value, "monitor time")
            except AeonBellError:
                return False
            return True

        active = monitor.get("active_invocation") if isinstance(monitor, dict) else None
        active_ok = active is None or (
            isinstance(active, dict)
            and set(active)
            == {
                "invocation_id",
                "generation",
                "started_at",
                "last_transition_at",
                "tick_id",
            }
            and AeonBell._is_hex_id(active["invocation_id"], INVOCATION_ID_LENGTH)
            and type(active["generation"]) is int
            and active["generation"] >= 1
            and AeonBell._is_hex_id(active["tick_id"], TICK_ID_LENGTH)
            and time_ok(active["started_at"])
            and time_ok(active["last_transition_at"])
        )
        effects = monitor.get("interrupted_effects") if isinstance(monitor, dict) else None
        effects_ok = isinstance(effects, list) and len(effects) <= INTERRUPTED_EFFECT_LIMIT
        if effects_ok:
            for effect in effects:
                if not (
                    isinstance(effect, dict)
                    and set(effect)
                    == {
                        "invocation_id",
                        "generation",
                        "tick_id",
                        "action_id",
                        "kind",
                        "purpose",
                        "action",
                        "settled_at",
                    }
                    and AeonBell._is_hex_id(effect["invocation_id"], INVOCATION_ID_LENGTH)
                    and type(effect["generation"]) is int
                    and effect["generation"] >= 1
                    and AeonBell._is_hex_id(effect["tick_id"], TICK_ID_LENGTH)
                    and AeonBell._is_hex_id(effect["action_id"], ACTION_ID_LENGTH)
                    and effect["kind"] in ACTION_KINDS - RESUMABLE_KINDS
                    and effect["purpose"] in ACTION_PURPOSES[effect["kind"]]
                    and isinstance(effect["action"], dict)
                    and set(effect["action"]) == TICK_ACTION_FIELDS
                    and effect["action"].get("action_id") == effect["action_id"]
                    and effect["action"].get("kind") == effect["kind"]
                    and effect["action"].get("purpose") == effect["purpose"]
                    and effect["action"].get("disposition") == "pending"
                    and isinstance(effect["action"].get("arguments"), dict)
                    and (
                        effect["action"].get("require") is None
                        or isinstance(effect["action"]["require"], dict)
                    )
                    and time_ok(effect["action"].get("issued_at"))
                    and (
                        effect["settled_at"] is None
                        or time_ok(effect["settled_at"])
                    )
                ):
                    effects_ok = False
                    break
        if not (
            isinstance(monitor, dict)
            and set(monitor) == required
            and AeonBell._is_hex_id(monitor["registry_id"], REGISTRY_ID_LENGTH)
            and isinstance(monitor["canonical_store"], str)
            and os.path.isabs(monitor["canonical_store"])
            and type(monitor["config_revision"]) is int
            and monitor["config_revision"] >= 1
            and isinstance(monitor["binding_paths"], list)
            and all(isinstance(path, str) and os.path.isabs(path) for path in monitor["binding_paths"])
            and isinstance(monitor["heartbeat"], str)
            and type(monitor["next_generation"]) is int
            and monitor["next_generation"] >= 1
            and active_ok
            and effects_ok
        ):
            raise AeonBellError(
                "corrupt-store", "monitor state has an unsupported shape"
            )
        return monitor

    def monitor_bind(
        self,
        *,
        binding_paths: list[str],
        heartbeat: str,
        initialize_registry: bool,
        registry_id: str | None,
    ) -> dict[str, Any]:
        """Bind an existing registry, or explicitly initialize one, for monitor entry."""
        canonical_store = self._canonical_store()
        bindings = [os.path.realpath(os.path.abspath(path)) for path in binding_paths]
        heartbeat = _identity(heartbeat, "heartbeat")
        existed = (self.store.directory / STATE_NAME).is_file()
        if not existed and not initialize_registry:
            raise AeonBellError("registry-not-found", "configured registry does not exist")
        transaction = self.store.transaction if initialize_registry else self.store.existing_transaction
        with transaction(write=True) as state:
            monitor = self._monitor_state(state)
            if monitor is None:
                monitor = {
                    "registry_id": secrets.token_hex(REGISTRY_ID_LENGTH // 2),
                    "canonical_store": canonical_store,
                    "config_revision": 1,
                    "binding_paths": bindings,
                    "heartbeat": heartbeat,
                    "next_generation": 1,
                    "active_invocation": None,
                    "interrupted_effects": [],
                }
                state["monitor"] = monitor
            else:
                if registry_id != monitor["registry_id"]:
                    raise AeonBellError(
                        "registry-mismatch",
                        "reconfiguration requires the current registry id",
                    )
                if monitor["active_invocation"] is not None:
                    raise AeonBellError(
                        "monitor-active", "the active invocation must finish before reconfiguration"
                    )
                if self._tick_state(state)["current"] is not None:
                    raise AeonBellError(
                        "monitor-active", "the running tick must finish before reconfiguration"
                    )
                if monitor["canonical_store"] != canonical_store:
                    raise AeonBellError(
                        "registry-mismatch", "the registry is bound to another canonical path"
                    )
                if bindings != monitor["binding_paths"] or heartbeat != monitor["heartbeat"]:
                    monitor["binding_paths"] = bindings
                    monitor["heartbeat"] = heartbeat
                    monitor["config_revision"] += 1
            entry_ref = _reference(
                ENTRY_REF_PREFIX,
                {
                    "store": monitor["canonical_store"],
                    "registry_id": monitor["registry_id"],
                    "config_revision": monitor["config_revision"],
                },
            )
            return {
                "status": "bound",
                "registry_id": monitor["registry_id"],
                "config_revision": monitor["config_revision"],
                "entry_ref": entry_ref,
                "store_created": not existed,
            }

    @staticmethod
    def _verify_entry(monitor: dict[str, Any] | None, entry: dict[str, Any], store: str) -> dict[str, Any]:
        if monitor is None or (
            monitor["canonical_store"] != store
            or monitor["registry_id"] != entry["registry_id"]
            or monitor["config_revision"] != entry["config_revision"]
        ):
            raise AeonBellError("registry-mismatch", "monitor entry does not match this registry")
        return monitor

    @staticmethod
    def _monitor_continuation(
        monitor: dict[str, Any], invocation: dict[str, Any], action_id: str
    ) -> str:
        return _reference(
            CONTINUATION_PREFIX,
            {
                "store": monitor["canonical_store"],
                "registry_id": monitor["registry_id"],
                "config_revision": monitor["config_revision"],
                "invocation_id": invocation["invocation_id"],
                "generation": invocation["generation"],
                "tick_id": invocation["tick_id"],
                "action_id": action_id,
            },
        )

    def _monitor_response(
        self,
        state: dict[str, Any],
        monitor: dict[str, Any],
        invocation: dict[str, Any],
        tick: dict[str, Any],
    ) -> dict[str, Any]:
        pending = self._pending_action(tick)
        if pending is None:
            return {
                "status": "complete",
                "invocation_id": invocation["invocation_id"],
                "outcome": self._tick_outcome(tick),
                "printed_anything": self._tick_outcome(tick)["printed_anything"],
            }
        action = {
            "kind": pending["kind"],
            "purpose": pending["purpose"],
            "arguments": copy.deepcopy(pending["arguments"]),
            "require": copy.deepcopy(pending["require"]),
            "result_shape": RESULT_SHAPES[pending["kind"]],
            "failure_form": FAILURE_FORM,
        }
        return {
            "status": "action_required",
            "registry_id": monitor["registry_id"],
            "invocation_id": invocation["invocation_id"],
            "generation": invocation["generation"],
            "continuation": self._monitor_continuation(
                monitor, invocation, pending["action_id"]
            ),
            "action": action,
            "limitations": [
                "results_are_caller_assertions",
                "entry_ref_and_continuation_are_not_authentication",
            ],
        }

    def monitor_enter(
        self, *, entry_ref: str, now: datetime, supplied: bool
    ) -> dict[str, Any]:
        """Claim the newest invocation generation and return one bound action."""
        entry = _entry_reference(entry_ref)
        canonical_store = self._canonical_store()
        if entry["store"] != canonical_store:
            raise AeonBellError("registry-mismatch", "monitor entry names another registry")
        with self.store.existing_transaction(write=True) as state:
            monitor = self._verify_entry(
                self._monitor_state(state), entry, canonical_store
            )
            ticks = self._tick_state(state)
            current, last = ticks["current"], ticks["last"]
            retained = False
            if current is not None:
                pending = self._pending_action(current)
                previous = monitor["active_invocation"]
                if (
                    pending is not None
                    and pending["kind"] in RESUMABLE_KINDS
                    and previous is not None
                    and previous.get("tick_id") == current["tick_id"]
                ):
                    now = self._tick_now(current, now, supplied)
                    current["last_now"] = format_time(now)
                    pending["issued_at"] = format_time(now)
                    retained = True
                else:
                    if (
                        pending is not None
                        and pending["kind"] not in RESUMABLE_KINDS
                        and previous is not None
                        and previous.get("tick_id") == current["tick_id"]
                    ):
                        monitor["interrupted_effects"].append(
                            {
                                "invocation_id": previous["invocation_id"],
                                "generation": previous["generation"],
                                "tick_id": current["tick_id"],
                                "action_id": pending["action_id"],
                                "kind": pending["kind"],
                                "purpose": pending["purpose"],
                                "action": copy.deepcopy(pending),
                                "settled_at": None,
                            }
                        )
                        monitor["interrupted_effects"][:] = monitor[
                            "interrupted_effects"
                        ][-INTERRUPTED_EFFECT_LIMIT:]
                    last = self._tick_summary(current, "abandoned", now)
            generation = monitor["next_generation"]
            monitor["next_generation"] += 1
            invocation = {
                "invocation_id": secrets.token_hex(INVOCATION_ID_LENGTH // 2),
                "generation": generation,
                "started_at": format_time(now),
                "last_transition_at": format_time(now),
                "tick_id": None,
            }
            if retained:
                tick = current
                assert tick is not None
            else:
                tick = self._new_tick_locked(
                    state,
                    now=now,
                    supplied=supplied,
                    binding_paths=list(monitor["binding_paths"]),
                    heartbeat=monitor["heartbeat"],
                    last=last,
                )
                if last is not None and last["status"] == "abandoned":
                    for line in last["diagnostics_unemitted"]:
                        self._tick_diagnostic(tick, line)
            invocation["tick_id"] = tick["tick_id"]
            monitor["active_invocation"] = invocation
            return self._monitor_response(state, monitor, invocation, tick)

    def monitor_continue(
        self,
        *,
        continuation: str,
        result: Any,
        now: datetime,
        supplied: bool,
    ) -> dict[str, Any]:
        """Advance exactly the action bound by one active continuation."""
        ref = _continuation_reference(continuation)
        canonical_store = self._canonical_store()
        if ref["store"] != canonical_store:
            raise AeonBellError("registry-mismatch", "continuation names another registry")
        cleanup: str | None = None
        with self.store.existing_transaction(write=True) as state:
            entry = {
                name: ref[name]
                for name in ("store", "registry_id", "config_revision")
            }
            monitor = self._verify_entry(
                self._monitor_state(state), entry, canonical_store
            )
            invocation = monitor["active_invocation"]
            if invocation is None or any(
                invocation.get(name) != ref[name]
                for name in ("invocation_id", "generation", "tick_id")
            ):
                return self._monitor_late_result(state, monitor, ref, result, now)
            ticks = self._tick_state(state)
            tick = ticks["current"]
            if tick is None or tick["tick_id"] != ref["tick_id"]:
                raise AeonBellError(
                    "stale-invocation", "this invocation was superseded; stop"
                )
            pending = self._pending_action(tick)
            if pending is None or pending["action_id"] != ref["action_id"]:
                raise AeonBellError(
                    "stale-result", "continuation is not the active pending action"
                )
            now = self._tick_now(tick, now, supplied)
            parsed = self._tick_result(pending, result, now)
            tick["last_now"] = format_time(now)
            self._tick_apply(state, tick, pending, parsed, now)
            invocation["last_transition_at"] = format_time(now)
            response = self._monitor_response(state, monitor, invocation, tick)
            if tick["status"] == "complete":
                _, cleanup = self._tick_finish_transition(
                    state,
                    tick,
                    now,
                    {
                        "action_id": pending["action_id"],
                        "disposition": pending["disposition"],
                        "consequence": pending["consequence"],
                    },
                )
                monitor["active_invocation"] = None
        if cleanup is not None:
            self._remove_artifacts(cleanup)
        return response

    def _monitor_late_result(
        self,
        state: dict[str, Any],
        monitor: dict[str, Any],
        ref: dict[str, Any],
        result: Any,
        now: datetime,
    ) -> dict[str, Any]:
        """Record one still-applicable exact effect result from a fenced actor."""
        matches = [
            effect
            for effect in monitor["interrupted_effects"]
            if all(
                effect.get(name) == ref[name]
                for name in (
                    "invocation_id",
                    "generation",
                    "tick_id",
                    "action_id",
                )
            )
        ]
        if not matches:
            raise AeonBellError(
                "stale-invocation", "this invocation was superseded; stop"
            )
        effect = matches[-1]
        action = effect["action"]
        parsed = self._tick_result(action, result, now)
        if effect["settled_at"] is not None:
            late = "already-settled"
        else:
            applicable = True
            if action["kind"] == "send":
                if parsed["failure"]:
                    outcome = (
                        "unknown" if parsed["disposition"] == "failed" else "not_sent"
                    )
                    evidence = {
                        "disposition": parsed["disposition"],
                        "reason": parsed["reason"],
                    }
                else:
                    outcome, evidence = parsed["outcome"], parsed["evidence"]
                try:
                    self._report_locked(
                        state, action["arguments"]["attempt_id"], outcome, evidence, now
                    )
                except AeonBellError as error:
                    if error.code != "attempt-not-reserved":
                        raise
                    applicable = False
            elif action["kind"] == "emit" and action["purpose"] == "notice":
                if not parsed["failure"]:
                    try:
                        self._acknowledge_locked(
                            state, action["arguments"]["notice_id"], now
                        )
                    except AeonBellError as error:
                        if error.code != "unknown-notice":
                            raise
                        applicable = False
            effect["settled_at"] = format_time(now)
            late = "recorded" if applicable else "already-settled"
        return {
            "status": "stopped",
            "reason": "superseded-invocation",
            "late_result": late,
        }

    def monitor_status(self, *, entry_ref: str, now: datetime) -> dict[str, Any]:
        """Return coordination state without any resumable or effect-bearing value."""
        entry = _entry_reference(entry_ref)
        canonical_store = self._canonical_store()
        if entry["store"] != canonical_store:
            raise AeonBellError("registry-mismatch", "monitor entry names another registry")
        with self.store.existing_transaction(write=False) as state:
            monitor = self._verify_entry(
                self._monitor_state(state), entry, canonical_store
            )
            ticks = self._tick_state(state)
            tick = ticks["current"]
            active = monitor["active_invocation"]
            active_view = None
            if active is not None:
                pending = self._pending_action(tick)
                active_view = {
                    "invocation_id": active["invocation_id"],
                    "generation": active["generation"],
                    "started_at": active["started_at"],
                    "last_transition_at": active["last_transition_at"],
                    "tick_id": active["tick_id"],
                    "phase": None if tick is None else tick["phase"],
                    "pending": (
                        None
                        if pending is None
                        else {
                            "kind": pending["kind"],
                            "purpose": pending["purpose"],
                            "issued_at": pending["issued_at"],
                            "interruption_class": (
                                "safe_to_reissue"
                                if pending["kind"] in RESUMABLE_KINDS
                                else "effect_may_have_happened"
                            ),
                        }
                    ),
                }
            unsettled = [
                effect
                for effect in monitor["interrupted_effects"]
                if effect["settled_at"] is None
            ]
            last = ticks["last"]
            last_view = None
            if last is not None:
                pending = last["abandoned_pending"]
                last_view = {
                    "status": last["status"],
                    "started_at": last["started_at"],
                    "finished_at": last["finished_at"],
                    "pending": (
                        None
                        if pending is None
                        else {
                            "kind": pending["kind"],
                            "purpose": pending["purpose"],
                        }
                    ),
                }
            schedule = self._schedule(state, now)
            schedule["gates"] = [
                {
                    name: copy.deepcopy(value)
                    for name, value in plan.items()
                    if name
                    not in {"gate", "gate_key", "registration_ids", "task_ids"}
                }
                for plan in schedule["gates"]
            ]
            return {
                "registry_id": monitor["registry_id"],
                "config_revision": monitor["config_revision"],
                "active_invocation": active_view,
                "interrupted_effects": {
                    "count": len(unsettled),
                    "reserved_send_attempts": sum(
                        effect["kind"] == "send" for effect in unsettled
                    ),
                },
                "last": last_view,
                "schedule": schedule,
            }

    def register(
        self,
        *,
        owner: str,
        host: str,
        task_id: str,
        episode: str,
        gate: dict[str, Any],
        continuation: str,
        now: datetime,
        expires_in_minutes: int | None = None,
        expected_open_at: str | None = None,
        poll_interval_minutes: str | None = None,
    ) -> dict[str, Any]:
        owner = _identity(owner, "owner")
        host = _identity(host, "host")
        task_id = _identity(task_id, "task_id")
        episode = _identity(episode, "episode")
        gate = validate_gate(gate)
        continuation = _continuation(continuation)
        minutes = _expiry_minutes(expires_in_minutes)
        expires_at = now + timedelta(minutes=minutes)
        forecast = (
            None
            if expected_open_at is None
            else _forecast(expected_open_at, now, expires_at)
        )
        interval = None if poll_interval_minutes is None else _interval(poll_interval_minutes)
        with self.store.transaction(write=True) as state:
            for existing in state["registrations"].values():
                if (
                    existing["host"] == host
                    and existing["task_id"] == task_id
                    and existing["status"] != "removed"
                ):
                    raise AeonBellError(
                        "duplicate-target",
                        "target task already has a registration; update, rearm, or remove it",
                    )
            registration_id = secrets.token_hex(12)
            sequence = 1 + max(
                (r["sequence"] for r in state["registrations"].values()), default=0
            )
            record = {
                "registration_id": registration_id,
                "sequence": sequence,
                "owner": owner,
                "host": host,
                "task_id": task_id,
                "episode": episode,
                "gate": gate,
                "gate_key": gate_key(gate),
                "continuation": continuation,
                "status": "waiting",
                "registered_at": format_time(now),
                "updated_at": format_time(now),
                "expires_at": format_time(expires_at),
                "completed_episodes": [],
                "episodes": [episode],
                "expected_open_at": forecast,
                "poll_interval_minutes": interval,
            }
            state["registrations"][registration_id] = record
            return self._owner_result(state, record, now)

    def _owner_result(
        self, state: dict[str, Any], record: dict[str, Any], now: datetime
    ) -> dict[str, Any]:
        """An owner command's output: the registration plus the registry's
        schedule after the change, so the caller can bring the monitor's
        heartbeat forward under its own native authority."""
        return {
            **self._public_registration(record, now),
            "schedule": self._schedule(state, now),
        }

    @staticmethod
    def _owned(
        state: dict[str, Any], registration_id: str, owner: str
    ) -> dict[str, Any]:
        record = state["registrations"].get(registration_id)
        if record is None or record["status"] == "removed":
            raise AeonBellError("unknown-registration", "no such active registration")
        if record["owner"] != _identity(owner, "owner"):
            raise AeonBellError(
                "owner-mismatch", "registration belongs to a different owner"
            )
        return record

    def update(
        self,
        *,
        registration_id: str,
        owner: str,
        now: datetime,
        gate: dict[str, Any] | None = None,
        continuation: str | None = None,
        expires_in_minutes: int | None = None,
        expected_open_at: str | None = None,
        poll_interval_minutes: str | None = None,
    ) -> dict[str, Any]:
        if (
            gate is None
            and continuation is None
            and expires_in_minutes is None
            and expected_open_at is None
            and poll_interval_minutes is None
        ):
            raise AeonBellError("nothing-to-update", "update needs at least one change")
        if gate is not None:
            gate = validate_gate(gate)
        if continuation is not None:
            continuation = _continuation(continuation)
        if expires_in_minutes is not None:
            expires_in_minutes = _expiry_minutes(expires_in_minutes)
        interval = None if poll_interval_minutes is None else _interval(poll_interval_minutes)
        with self.store.transaction(write=True) as state:
            record = self._owned(state, registration_id, owner)
            if record["status"] == "reserved" and (
                gate is not None or continuation is not None
            ):
                # Reservation froze the gate and continuation into the attempt's
                # message; they belong to that attempt until it is reported,
                # reconciled, or superseded. Expiry and cadence metadata are
                # still owner state: neither reaches the attempt or its message.
                raise AeonBellError(
                    "invalid-transition",
                    "registration is reserved: its gate and continuation are frozen "
                    "until the attempt is reported, reconciled, or rearmed",
                )
            expires_at = (
                parse_time(record["expires_at"], "expires_at")
                if expires_in_minutes is None
                else now + timedelta(minutes=expires_in_minutes)
            )
            # A new forecast is checked against the expiry this command leaves
            # behind, before anything is written; a stored one is left alone.
            forecast = (
                record.get("expected_open_at")
                if expected_open_at is None
                else _forecast(expected_open_at, now, expires_at)
            )
            if gate is not None:
                record["gate"] = gate
                record["gate_key"] = gate_key(gate)
            if continuation is not None:
                record["continuation"] = continuation
            if expires_in_minutes is not None:
                record["expires_at"] = format_time(expires_at)
                if record["status"] == "expired":
                    record["status"] = "waiting"
            record["expected_open_at"] = forecast
            if poll_interval_minutes is not None:
                record["poll_interval_minutes"] = interval
            record["updated_at"] = format_time(now)
            return self._owner_result(state, record, now)

    def _transition(
        self,
        registration_id: str,
        owner: str,
        now: datetime,
        *,
        allowed_from: set[str],
        to: str,
    ) -> dict[str, Any]:
        with self.store.transaction(write=True) as state:
            record = self._owned(state, registration_id, owner)
            if record["status"] not in allowed_from:
                raise AeonBellError(
                    "invalid-transition",
                    f"registration is {record['status']}, not one of {sorted(allowed_from)}",
                )
            record["status"] = to
            record["updated_at"] = format_time(now)
            return self._owner_result(state, record, now)

    def pause(
        self, *, registration_id: str, owner: str, now: datetime
    ) -> dict[str, Any]:
        return self._transition(
            registration_id, owner, now, allowed_from={"waiting"}, to="paused"
        )

    def resume(
        self, *, registration_id: str, owner: str, now: datetime
    ) -> dict[str, Any]:
        return self._transition(
            registration_id, owner, now, allowed_from={"paused"}, to="waiting"
        )

    def remove(
        self, *, registration_id: str, owner: str, now: datetime
    ) -> dict[str, Any]:
        with self.store.transaction(write=True) as state:
            record = self._owned(state, registration_id, owner)
            record["status"] = "removed"
            record.pop("unresolved_reason", None)
            record["updated_at"] = format_time(now)
            return self._owner_result(state, record, now)

    @staticmethod
    def _episode_history(state: dict[str, Any], record: dict[str, Any]) -> list[str]:
        """Every episode identity this registration has ever used, in order.

        Stores written before ``episodes`` was recorded are reconstructed from
        the current episode, completed episodes, and the registration's attempts.
        """
        history: list[str] = list(record.get("episodes", []))
        for episode in [
            *record["completed_episodes"],
            *(
                attempt["episode"]
                for attempt in sorted(
                    state["attempts"].values(), key=lambda a: a["planned_at"]
                )
                if attempt["registration_id"] == record["registration_id"]
            ),
            record["episode"],
        ]:
            if episode not in history:
                history.append(episode)
        return history

    def rearm(
        self,
        *,
        registration_id: str,
        owner: str,
        episode: str,
        now: datetime,
        expires_in_minutes: int | None = None,
        expected_open_at: str | None = None,
        poll_interval_minutes: str | None = None,
    ) -> dict[str, Any]:
        """Start an explicit new waiting episode, superseding any prior attempt.

        The episode identity must never have been used by this registration,
        including identities that were superseded without ever dispatching, so a
        woken target can bind its revalidation to one unambiguous wait. An
        expired registration is rearmed only with an explicit new expiry.

        A fresh episode is a fresh wait: the stored forecast belonged to the
        old wait and is cleared unless this command supplies one; the explicit
        effective interval is a standing requirement and is retained unless
        this command changes it.
        """
        episode = _identity(episode, "episode")
        if expires_in_minutes is not None:
            expires_in_minutes = _expiry_minutes(expires_in_minutes)
        interval = None if poll_interval_minutes is None else _interval(poll_interval_minutes)
        with self.store.transaction(write=True) as state:
            record = self._owned(state, registration_id, owner)
            history = self._episode_history(state, record)
            if episode in history:
                raise AeonBellError(
                    "episode-reused",
                    "a new wait episode must use an episode identity this registration "
                    "has never used",
                )
            if expires_in_minutes is None and now >= parse_time(
                record["expires_at"], "expires_at"
            ):
                raise AeonBellError(
                    "invalid-transition",
                    "registration has expired; rearm with --expires-in-minutes to start "
                    "a new wait, or update its expiry first",
                )
            expires_at = (
                parse_time(record["expires_at"], "expires_at")
                if expires_in_minutes is None
                else now + timedelta(minutes=expires_in_minutes)
            )
            forecast = (
                None
                if expected_open_at is None
                else _forecast(expected_open_at, now, expires_at)
            )
            previous = record.get("attempt_id")
            if previous is not None:
                attempt = state["attempts"][previous]
                if attempt["status"] in {"reserved", "unknown"}:
                    attempt["status"] = f"superseded_{attempt['status']}"
                    attempt["resolved_at"] = format_time(now)
                    attempt["superseded_by_episode"] = episode
            record["episodes"] = [*history, episode]
            record["episode"] = episode
            record["status"] = "waiting"
            record["attempt_id"] = None
            record["attempt_count"] = 0
            record.pop("unresolved_reason", None)
            if expires_in_minutes is not None:
                record["expires_at"] = format_time(expires_at)
            record["expected_open_at"] = forecast
            if poll_interval_minutes is not None:
                record["poll_interval_minutes"] = interval
            record["updated_at"] = format_time(now)
            return self._owner_result(state, record, now)

    # -- dispatch results --------------------------------------------------

    def report(
        self, *, attempt_id: str, outcome: str, evidence: Any, now: datetime
    ) -> dict[str, Any]:
        if outcome not in {"accepted", "not_sent", "unknown"}:
            raise AeonBellError(
                "invalid-outcome", "outcome must be accepted, not_sent, or unknown"
            )
        evidence = _evidence(evidence)
        with self.store.transaction(write=True) as state:
            return self._report_locked(state, attempt_id, outcome, evidence, now)

    def _report_locked(
        self,
        state: dict[str, Any],
        attempt_id: str,
        outcome: str,
        evidence: dict[str, Any],
        now: datetime,
    ) -> dict[str, Any]:
        """Record a validated send outcome on a reserved attempt under the
        caller's lock; the directed tick applies its send results here."""
        attempt = state["attempts"].get(attempt_id)
        if attempt is None:
            raise AeonBellError("unknown-attempt", "no such attempt")
        if attempt["status"] != "reserved":
            raise AeonBellError(
                "attempt-not-reserved",
                f"attempt is {attempt['status']}; only a reserved attempt takes a report",
            )
        record = state["registrations"][attempt["registration_id"]]
        attempt["status"] = outcome
        attempt["resolved_at"] = format_time(now)
        attempt["evidence"] = evidence
        self._settle(record, attempt, now)
        return self._dispatch_result(record, attempt, now)

    def reconcile(
        self, *, attempt_id: str, resolution: str, evidence: Any, now: datetime
    ) -> dict[str, Any]:
        if resolution not in {"accepted", "not_sent"}:
            raise AeonBellError(
                "invalid-resolution", "resolution must be accepted or not_sent"
            )
        evidence = _evidence(evidence)
        if not evidence:
            raise AeonBellError(
                "missing-evidence", "reconciliation needs explicit evidence"
            )
        with self.store.transaction(write=True) as state:
            attempt = state["attempts"].get(attempt_id)
            if attempt is None:
                raise AeonBellError("unknown-attempt", "no such attempt")
            if attempt["status"] not in {"unknown", "reserved"}:
                raise AeonBellError(
                    "attempt-not-unresolved",
                    f"attempt is {attempt['status']}; only an unresolved attempt reconciles",
                )
            record = state["registrations"][attempt["registration_id"]]
            attempt["status"] = f"reconciled_{resolution}"
            attempt["resolved_at"] = format_time(now)
            attempt["reconciliation_evidence"] = evidence
            self._settle(record, attempt, now)
            return self._dispatch_result(record, attempt, now)

    @staticmethod
    def _settle(record: dict[str, Any], attempt: dict[str, Any], now: datetime) -> None:
        if (
            record["status"] == "removed"
            or record.get("attempt_id") != attempt["attempt_id"]
        ):
            return  # owner removal or explicit rearm wins; registration state stands
        outcome = attempt["status"].removeprefix("reconciled_")
        record["updated_at"] = format_time(now)
        # unresolved_reason belongs to the unresolved state this settlement may
        # be leaving; the branches that enter it again set their own reason.
        record.pop("unresolved_reason", None)
        if outcome == "accepted":
            record["status"] = "completed"
            record["completed_episodes"].append(attempt["episode"])
            return
        if outcome == "unknown":
            record["status"] = "unresolved"
            record["unresolved_reason"] = "delivery-unknown"
            return
        record["attempt_id"] = None
        if record.get("attempt_count", 0) >= MAX_ATTEMPTS_PER_EPISODE:
            record["status"] = "unresolved"
            record["unresolved_reason"] = "attempt-limit"
        else:
            record["status"] = "waiting"

    def _dispatch_result(
        self, record: dict[str, Any], attempt: dict[str, Any], now: datetime
    ) -> dict[str, Any]:
        claim = {
            "accepted": "accepted_by_native_send_tool",
            "reconciled_accepted": "accepted_by_native_send_tool",
            "not_sent": "not_sent",
            "reconciled_not_sent": "not_sent",
            "unknown": "unknown_requires_reconciliation",
        }[attempt["status"]]
        return {
            "attempt": self._public_attempt(attempt, now),
            "registration": self._public_registration(record, now),
            "delivery_claim": claim,
            "limitations": NATIVE_LIMITATIONS,
        }

    @staticmethod
    def _public_attempt(attempt: dict[str, Any], now: datetime) -> dict[str, Any]:
        return {
            name: attempt[name]
            for name in (
                "attempt_id",
                "registration_id",
                "host",
                "task_id",
                "episode",
                "gate_key",
                "gate_observed_at",
                "status",
                "planned_at",
                "resolved_at",
                "message_sha256",
            )
        }

    # -- monitor cycle -----------------------------------------------------

    def cycle(self, *, cycle_input: Any, now: datetime) -> dict[str, Any]:
        observations, task_states = self._validated_cycle_input(cycle_input)
        with self.store.transaction(write=True) as state:
            return self._cycle_locked(state, observations, task_states, now)

    def _cycle_locked(
        self,
        state: dict[str, Any],
        observations: list[Any],
        task_states: dict[tuple[str, str], dict[str, Any]],
        now: datetime,
    ) -> dict[str, Any]:
        """One legacy monitor tick on a loaded state: ingest, expire, request,
        plan. The directed tick runs the same pieces in separate transitions."""
        ingested = self._ingest_observations(state, observations, now)
        self._expire_registrations(state, now)
        requests = self._observation_requests(state, now)
        skipped, proposals = self._plan_wakes(state, task_states, now)
        return {
            "cycle_at": format_time(now),
            "ingested_observations": ingested,
            "observation_requests": requests,
            "wake_proposals": proposals,
            "skipped": skipped,
            "unresolved_attempts": self._unresolved_attempts(state, now),
            "attention": self._attention(state, now),
            "schedule": self._schedule(state, now),
            "limitations": NATIVE_LIMITATIONS,
        }

    @staticmethod
    def _attention(state: dict[str, Any], now: datetime) -> list[dict[str, Any]]:
        """Everything no tick will move on its own: the one list a monitor checks.

        Registrations that are reserved, unresolved, or expired, plus every
        unresolved attempt whose registration the owner removed (``detached``):
        removal cancels the wait but not the closeout the attempt still owes.
        ``since`` is when the entry entered its current state, read from the
        lifecycle record of that transition, so a monitor can tell an unchanged
        entry from a new one across ticks and across owner edits.
        """
        entries: list[dict[str, Any]] = []
        for record in sorted(
            state["registrations"].values(), key=lambda r: r["sequence"]
        ):
            expired = now >= parse_time(record["expires_at"], "expires_at")
            status = record["status"]
            if status == "removed":
                attempt = state["attempts"].get(record.get("attempt_id") or "")
                if attempt is None or attempt["status"] not in {"reserved", "unknown"}:
                    continue
                entries.append(AeonBell._detached_entry(record, attempt))
                continue
            if status not in {"reserved", "unresolved", "expired"} and not (
                status == "waiting" and expired
            ):
                continue
            shown = "expired" if status == "waiting" else status
            entries.append(
                {
                    "registration_id": record["registration_id"],
                    "host": record["host"],
                    "task_id": record["task_id"],
                    "episode": record["episode"],
                    "status": shown,
                    "unresolved_reason": record.get("unresolved_reason"),
                    "attempt_id": record.get("attempt_id"),
                    "since": AeonBell._state_since(state, record, shown),
                    "next_action": AeonBell._next_action(record, expired),
                }
            )
        return entries

    @staticmethod
    def _defining_attempt(
        state: dict[str, Any], record: dict[str, Any], shown: str
    ) -> dict[str, Any] | None:
        """The attempt whose transition put the registration into ``shown``.

        ``updated_at`` is owner metadata: every allowed ``update`` (an expiry
        renewal while reserved; a gate, continuation, or expiry edit while
        unresolved) and the cycle's own persistence of a status move it, and a
        moved ``since`` or a relabelled entry would read as news. State age and
        gate identity therefore come only from the record the transition itself
        wrote: the reservation for ``reserved``, the resolution that left the
        attempt unknown or exhausted the episode's attempts for ``unresolved``.
        ``expired`` is a registration fact with no attempt (None). Those records
        exist in every store this engine wrote; a registration whose state
        names none is malformed.
        """
        if shown == "expired":
            return None
        attempts = state["attempts"]
        if shown == "reserved":
            attempt = attempts.get(record.get("attempt_id") or "")
            if attempt is None:
                raise AeonBellError(
                    "corrupt-store", "reserved registration names no attempt record"
                )
            return attempt
        if record.get("unresolved_reason") == "delivery-unknown":
            attempt = attempts.get(record.get("attempt_id") or "")
            if attempt is None or attempt["resolved_at"] is None:
                raise AeonBellError(
                    "corrupt-store", "unresolved registration names no resolved attempt"
                )
            return attempt
        # attempt-limit: the third not_sent resolution of this episode.
        resolutions = [
            attempt
            for attempt in attempts.values()
            if attempt["registration_id"] == record["registration_id"]
            and attempt["episode"] == record["episode"]
            and attempt["status"] in {"not_sent", "reconciled_not_sent"}
            and attempt["resolved_at"] is not None
        ]
        if not resolutions:
            raise AeonBellError(
                "corrupt-store", "unresolved registration has no resolved attempt"
            )
        return max(
            resolutions,
            key=lambda a: (
                parse_time(a["resolved_at"], "resolved_at"),
                a["planned_at"],
                a["attempt_id"],
            ),
        )

    @staticmethod
    def _state_since(state: dict[str, Any], record: dict[str, Any], shown: str) -> str:
        """When the registration entered ``shown``, from the record of that transition."""
        if shown == "expired":
            # Expiry entered its state at expires_at, whether or not a cycle
            # has persisted the status yet.
            return record["expires_at"]
        attempt = AeonBell._defining_attempt(state, record, shown)
        assert attempt is not None
        return attempt["planned_at"] if shown == "reserved" else attempt["resolved_at"]

    @staticmethod
    def _reserved_guidance(attempt_id: Any) -> str:
        """Who may close a reserved attempt, and how, by what they know.

        Only the monitor that holds the reservation observed the send outcome.
        Anyone else (a restarted monitor, an owner) must settle it from the
        target transcript: an evidence-free not_sent would rearm a blind retry
        of a send that may already have reached the target.
        """
        return (
            f"only the monitor holding this reservation may report attempt {attempt_id} "
            "as accepted, not_sent, or unknown, from its own send outcome; a restarted "
            "monitor or an owner without send knowledge never guesses not_sent and "
            "instead reconciles it with target-transcript evidence "
            f"(reconcile --attempt-id {attempt_id} --resolution accepted|not_sent "
            "--evidence-json)"
        )

    @staticmethod
    def _detached_entry(record: dict[str, Any], attempt: dict[str, Any]) -> dict[str, Any]:
        """An attention entry for an attempt whose registration was removed."""
        transition = attempt["resolved_at"] or attempt["planned_at"]
        since = max(record["updated_at"], transition, key=lambda t: parse_time(t, "since"))
        if attempt["status"] == "reserved":
            next_action = (
                f"the owner removed this registration while attempt {attempt['attempt_id']} "
                "was reserved; " + AeonBell._reserved_guidance(attempt["attempt_id"])
            )
        else:
            next_action = (
                f"the owner removed this registration while attempt {attempt['attempt_id']} "
                "was unknown: reconcile it with evidence from the target transcript"
            )
        return {
            "registration_id": record["registration_id"],
            "host": record["host"],
            "task_id": record["task_id"],
            "episode": attempt["episode"],
            "status": "detached",
            "unresolved_reason": None,
            "attempt_id": attempt["attempt_id"],
            "since": since,
            "next_action": next_action,
        }

    @staticmethod
    def _validated_cycle_input(
        value: Any,
    ) -> tuple[list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
        if not isinstance(value, dict) or not set(value) <= {
            "observations",
            "task_states",
        }:
            raise AeonBellError(
                "invalid-input",
                "cycle input must be an object with only observations and task_states",
            )
        observations = value.get("observations", [])
        task_states = value.get("task_states", [])
        if not isinstance(observations, list) or not isinstance(task_states, list):
            raise AeonBellError(
                "invalid-input", "observations and task_states must be lists"
            )
        states: dict[tuple[str, str], dict[str, Any]] = {}
        for item in task_states:
            if not isinstance(item, dict) or set(item) != {
                "host",
                "task_id",
                "status",
                "observed_at",
            }:
                raise AeonBellError(
                    "invalid-input",
                    "each task state needs exactly host, task_id, status, observed_at",
                )
            host = _identity(item["host"], "task_state.host")
            task_id = _identity(item["task_id"], "task_state.task_id")
            if item["status"] not in TASK_STATUSES:
                raise AeonBellError(
                    "invalid-input",
                    f"task state status must be one of {sorted(TASK_STATUSES)}",
                )
            states[(host, task_id)] = {
                "status": item["status"],
                "observed_at": parse_time(
                    item["observed_at"], "task_state.observed_at"
                ),
            }
        return observations, states

    @staticmethod
    def _expire_registrations(state: dict[str, Any], now: datetime) -> None:
        for record in state["registrations"].values():
            if record["status"] == "waiting" and now >= parse_time(
                record["expires_at"], "expires_at"
            ):
                record["status"] = "expired"
                record["updated_at"] = format_time(now)

    @staticmethod
    def _latest_evidence_at(
        state: dict[str, Any], key: str, binding_digest: str
    ) -> datetime | None:
        """The key's latest evidence time under the current binding.

        The later of the stored successful observation's ``observed_at`` (only
        when it was made against the same binding digest; a stored observation
        under another binding is a distinct comparison domain that the
        existing invalidation rules already make unusable) and the retry
        schedule's last failure. None when the key holds no such evidence.
        """
        latest: datetime | None = None
        stored = state["observations"].get(key)
        if stored is not None and stored["binding_digest"] == binding_digest:
            latest = parse_time(stored["observed_at"], "observed_at")
        schedule = state["retry_schedule"].get(key)
        failed_at = None if schedule is None else schedule.get("last_failure_at")
        if isinstance(failed_at, str):
            failed = parse_time(failed_at, "last_failure_at")
            latest = failed if latest is None else max(latest, failed)
        return latest

    @staticmethod
    def _ordering_skip(observed_at: datetime, latest: datetime | None) -> str | None:
        """Why an observation is not newer than the key's evidence, or None.

        The successful-observation anchor is monotonic: input older than the
        latest evidence is superseded, and input stamped at the same second
        carries no ordering, so the stored state is preserved either way (an
        identical replay is therefore a no-op). Only newer input is applied.
        """
        if latest is None or observed_at > latest:
            return None
        return "observation-superseded" if observed_at < latest else "observation-not-newer"

    def _ingest_observations(
        self, state: dict[str, Any], observations: list[Any], now: datetime
    ) -> list[dict[str, Any]]:
        gates_by_key = {
            record["gate_key"]: record["gate"]
            for record in state["registrations"].values()
            if record["status"] != "removed"
        }
        ingested: list[dict[str, Any]] = []
        for index, item in enumerate(observations):
            label = f"observations[{index}]"
            if not isinstance(item, dict):
                raise AeonBellError("invalid-observation", f"{label} must be an object")
            key = item.get("gate_key")
            gate = gates_by_key.get(key) if isinstance(key, str) else None
            if gate is None:
                # An owner remove or gate change can land between the plan cycle
                # and this result cycle, so an observation nobody registered any
                # more is ordinary: skip it, store nothing, keep the rest.
                ingested.append(
                    {
                        "gate_key": key if _is_gate_key(key) else None,
                        "accepted": False,
                        "result": None,
                        "reason": "gate-not-registered",
                    }
                )
                continue
            status = item.get("status")
            observed_at = parse_time(item.get("observed_at"), f"{label}.observed_at")
            if observed_at > now + timedelta(minutes=1):
                raise AeonBellError(
                    "invalid-observation", f"{label}.observed_at is in the future"
                )
            if status == "error":
                if set(item) != ERROR_OBSERVATION_FIELDS:
                    raise AeonBellError(
                        "invalid-observation",
                        f"{label} error observation must have exactly gate_key, status, "
                        "observed_at, reason",
                    )
                reason = _bounded_text(item["reason"], f"{label}.reason")
                skip = self._ordering_skip(
                    observed_at, self._latest_evidence_at(state, key, digest(gate))
                )
                if skip is not None:
                    # Superseded or unordered failure evidence advances nothing:
                    # it cannot create or extend a failing marker past newer state.
                    ingested.append(
                        {"gate_key": key, "accepted": False, "result": None, "reason": skip}
                    )
                    continue
                schedule = state["retry_schedule"].get(key, {"failures": 0})
                failures = schedule["failures"] + 1
                delay = min(
                    BACKOFF_BASE_MINUTES * (2 ** (failures - 1)),
                    BACKOFF_CEILING_MINUTES,
                )
                state["retry_schedule"][key] = {
                    "failures": failures,
                    "last_failure_at": format_time(observed_at),
                    "last_reason": reason,
                    "next_due_at": format_time(now + timedelta(minutes=delay)),
                    "backoff_minutes": delay,
                }
                ingested.append(
                    {
                        "gate_key": key,
                        "accepted": True,
                        "result": "error",
                        "reason": reason,
                    }
                )
                continue
            if status != "ok":
                raise AeonBellError(
                    "invalid-observation", f"{label}.status must be ok or error"
                )
            allowed = OBSERVATION_FIELDS[gate["kind"]]
            if not set(item) <= allowed or not (
                allowed - OBSERVATION_OPTIONAL_FIELDS
            ) <= set(item):
                raise AeonBellError(
                    "invalid-observation",
                    f"{label} has an unsupported field set for a {gate['kind']} gate",
                )
            _bounded_text(item["account"], f"{label}.account")
            _bounded_text(item["route"], f"{label}.route")
            result, reason, evidence = evaluate_observation(gate, item)
            binding_digest = digest(gate)
            skip = self._ordering_skip(
                observed_at, self._latest_evidence_at(state, key, binding_digest)
            )
            if skip is not None:
                # Older or equal-time input never replaces the stored observation:
                # the anchor, the planned query, and any newer failure state stand,
                # and a superseded open observation admits nothing.
                ingested.append(
                    {"gate_key": key, "accepted": False, "result": None, "reason": skip}
                )
                continue
            window_end = observed_at + timedelta(minutes=OBSERVATION_FRESHNESS_MINUTES)
            if item.get("expires_at") is None:
                expires_at = window_end
                source = "cycle"
            else:
                # An import may shorten freshness but never extend it: an advertised
                # reset far ahead must not suppress the early-recovery requery.
                expires_at = min(
                    parse_time(item["expires_at"], f"{label}.expires_at"), window_end
                )
                source = "import"
            fresh = expires_at > now
            state["observations"][key] = {
                "gate_key": key,
                "kind": gate["kind"],
                "binding_digest": binding_digest,
                "result": result,
                "reason": reason,
                "evidence": evidence,
                "observed_at": format_time(observed_at),
                "expires_at": format_time(expires_at),
                "source": source,
            }
            state["retry_schedule"].pop(key, None)
            ingested.append(
                {
                    "gate_key": key,
                    "accepted": True,
                    "result": result,
                    "reason": reason,
                    "fresh": fresh,
                    "expires_at": format_time(expires_at),
                }
            )
        return ingested

    @staticmethod
    def _current_observation(
        state: dict[str, Any], record: dict[str, Any], now: datetime
    ) -> tuple[str, str, dict[str, Any] | None]:
        observation = state["observations"].get(record["gate_key"])
        if observation is None:
            return "unobserved", "gate-unobserved", None
        if observation["binding_digest"] != digest(record["gate"]):
            return "unobserved", "gate-binding-changed", None
        if parse_time(observation["expires_at"], "expires_at") <= now:
            return "stale", "gate-observation-stale", observation
        return observation["result"], f"gate-{observation['result']}", observation

    # -- scheduling --------------------------------------------------------

    @staticmethod
    def _waiting_by_gate(
        state: dict[str, Any], now: datetime
    ) -> dict[str, dict[str, Any]]:
        """Gate key to its gate and the waiting, unexpired registrations carrying it."""
        gates: dict[str, dict[str, Any]] = {}
        for record in sorted(
            state["registrations"].values(), key=lambda r: r["sequence"]
        ):
            if record["status"] != "waiting" or now >= parse_time(
                record["expires_at"], "expires_at"
            ):
                continue
            entry = gates.setdefault(
                record["gate_key"], {"gate": record["gate"], "registrations": []}
            )
            entry["registrations"].append(record)
        return gates

    def _gate_plans(
        self, state: dict[str, Any], now: datetime, knowledge: dict[str, str]
    ) -> list[dict[str, Any]]:
        """One plan per gate key in use: when its next query is due and why.

        The anchor is the observed_at of the latest successful observation
        under the key. A closed gate's estimate is the earliest owner forecast
        or observed reset hint (a quota bucket's reset, or a daybreak_status
        reset when exhausted capacity closed it) that lies after the anchor, judged at the anchor
        so an estimate passing in wall time never postpones a check already
        due; the unknown default applies only once a later observation's anchor
        lies past every estimate. Each registration demands either its explicit
        effective interval from the anchor or the gate's adaptive default, and
        the earliest demand wins the shared query. Provider-error backoff bounds
        the query from below; the later applicable bound holds.
        """
        plans: list[dict[str, Any]] = []
        for key, entry in self._waiting_by_gate(state, now).items():
            registrations = entry["registrations"]
            probe = {"gate_key": key, "gate": entry["gate"]}
            _, reason, observation = self._current_observation(state, probe, now)
            plan: dict[str, Any] = {
                "gate_key": key,
                "gate": entry["gate"],
                "kind": entry["gate"]["kind"],
                "registration_ids": [r["registration_id"] for r in registrations],
                "task_ids": sorted(r["task_id"] for r in registrations),
                "observation": None,
                "anchor": None,
                "fresh": None,
                "basis": None,
                "estimate_at": None,
                "cadence": "adaptive",
                "interval_minutes": None,
                "query_due_at": None,
                "backoff_until": None,
                "configuration_gap": knowledge.get(key) in CONFIGURATION_GAP_OUTCOMES,
                "check_at": None,
                "due": False,
            }
            query_due_at: datetime | None = None
            if observation is None:
                plan["basis"] = (
                    "unobserved" if reason == "gate-unobserved" else "binding-changed"
                )
            else:
                anchor = parse_time(observation["observed_at"], "observed_at")
                expires_at = parse_time(observation["expires_at"], "expires_at")
                plan["observation"] = observation["result"]
                plan["anchor"] = observation["observed_at"]
                plan["fresh"] = expires_at > now
                if observation["result"] == "open":
                    # Still waiting on an open gate (targets not idle): the next
                    # query is when this observation can no longer admit.
                    plan["basis"] = "open"
                    default_interval = ADAPTIVE_OPEN_INTERVAL_MINUTES
                    default_due = min(
                        anchor + timedelta(minutes=default_interval), expires_at
                    )
                else:
                    estimates: list[tuple[datetime, str]] = []
                    for record in registrations:
                        forecast = record.get("expected_open_at")
                        if forecast is not None:
                            estimates.append(
                                (parse_time(forecast, "expected_open_at"), "forecast")
                            )
                    reset_at = (observation.get("evidence") or {}).get("reset_at")
                    if reset_at is not None and observation["reason"] in RESET_HINT_REASONS:
                        estimates.append((parse_time(reset_at, "reset_at"), "reset-hint"))
                    applicable = [e for e in estimates if e[0] > anchor]
                    if applicable:
                        estimate, source = min(applicable)
                        remaining = int((estimate - anchor).total_seconds() // 60)
                        default_interval = min(
                            max(
                                remaining // ADAPTIVE_WAIT_DIVISOR,
                                ADAPTIVE_MIN_INTERVAL_MINUTES,
                            ),
                            ADAPTIVE_MAX_INTERVAL_MINUTES,
                        )
                        plan["basis"] = source
                        plan["estimate_at"] = format_time(estimate)
                    else:
                        default_interval = ADAPTIVE_UNKNOWN_INTERVAL_MINUTES
                        plan["basis"] = "no-estimate"
                    default_due = anchor + timedelta(minutes=default_interval)
                demands: list[tuple[datetime, int, str, int]] = []
                for record in registrations:
                    interval = record.get("poll_interval_minutes")
                    if interval is None:
                        demands.append((default_due, 1, "adaptive", default_interval))
                    else:
                        demands.append(
                            (anchor + timedelta(minutes=interval), 0, "explicit", interval)
                        )
                query_due_at, _, plan["cadence"], plan["interval_minutes"] = min(demands)
                plan["query_due_at"] = format_time(query_due_at)
            bound = query_due_at
            schedule = state["retry_schedule"].get(key)
            if schedule is not None:
                next_due = parse_time(schedule["next_due_at"], "next_due_at")
                if next_due > now:
                    plan["backoff_until"] = schedule["next_due_at"]
                    if bound is None or next_due > bound:
                        bound = next_due
            plan["check_at"] = None if bound is None else format_time(bound)
            plan["due"] = bound is None or bound <= now
            plans.append(plan)
        return plans

    def _schedule(
        self,
        state: dict[str, Any],
        now: datetime,
        notification: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """The common schedule object: the next check this registry needs.

        Reconstructed from durable state alone, so a restarted actor reads the
        same recommendation. A due gate is an immediate recommendation; a
        planned query, a backoff retry, or a waiting registration's expiry is
        an absolute time; a pending notice or an unrelayed reservation is
        recovered within the recovery bound; a configuration gap or a registry
        with nothing waiting is revisited within the liveness bound. Malformed
        notification state leaves the registry readable and is treated as
        nothing acknowledged, which is the conservative side.
        """
        if notification is None:
            try:
                notification = self._notification(state)
            except AeonBellError:
                notification = None
        knowledge = {} if notification is None else notification["knowledge"]
        pending = None if notification is None else notification["pending"]
        acknowledged = (
            set() if notification is None else set(notification["baseline"]["markers"])
        )
        plans = self._gate_plans(state, now, knowledge)
        liveness = now + timedelta(minutes=LIVENESS_CHECK_MINUTES)
        recovery = now + timedelta(minutes=RECOVERY_CHECK_MINUTES)
        candidates: list[tuple[datetime, int, str]] = []
        for plan in plans:
            if plan["due"] and plan["configuration_gap"]:
                candidates.append((liveness, 6, "configuration-gap"))
            elif plan["due"]:
                candidates.append((now, 0, "gate-due"))
            else:
                check_at = parse_time(plan["check_at"], "check_at")
                if plan["backoff_until"] is not None and check_at != (
                    None
                    if plan["query_due_at"] is None
                    else parse_time(plan["query_due_at"], "query_due_at")
                ):
                    candidates.append((check_at, 5, "backoff"))
                else:
                    candidates.append((check_at, 4, "gate-query"))
        waiting = 0
        for record in state["registrations"].values():
            if record["status"] == "waiting" and now < parse_time(
                record["expires_at"], "expires_at"
            ):
                waiting += 1
                candidates.append(
                    (parse_time(record["expires_at"], "expires_at"), 3, "registration-expiry")
                )
        if pending is not None:
            candidates.append((recovery, 1, "notice-pending"))
        attention = self._attention(state, now)
        for entry in attention:
            attempt = state["attempts"].get(entry["attempt_id"] or "")
            marker = f"attention:{entry['registration_id']}:{entry['status']}:{entry['since']}"
            if (
                attempt is not None
                and attempt["status"] == "reserved"
                and marker not in acknowledged
            ):
                candidates.append((recovery, 2, "reservation-unrelayed"))
        if waiting == 0:
            candidates.append((liveness, 7, "liveness"))
        next_at, _, reason = min(candidates)
        if next_at <= now:
            next_at = now
        delay = math.ceil(max((next_at - now).total_seconds(), 0) / 60)
        counts = {
            name: 0
            for name in ("waiting", "paused", "reserved", "completed", "unresolved", "expired")
        }
        for record in state["registrations"].values():
            status = record["status"]
            if status == "removed":
                continue
            if status == "waiting" and now >= parse_time(record["expires_at"], "expires_at"):
                status = "expired"
            counts[status] += 1
        fingerprint = digest(
            {
                "registrations": [
                    {
                        name: record.get(name)
                        for name in (
                            "registration_id",
                            "status",
                            "episode",
                            "gate_key",
                            "expires_at",
                            "expected_open_at",
                            "poll_interval_minutes",
                            "attempt_id",
                        )
                    }
                    for record in sorted(
                        state["registrations"].values(), key=lambda r: r["sequence"]
                    )
                ],
                "attempts": {
                    attempt_id: attempt["status"]
                    for attempt_id, attempt in sorted(state["attempts"].items())
                },
                "observations": {
                    key: {
                        name: observation[name]
                        for name in ("observed_at", "expires_at", "result", "binding_digest")
                    }
                    for key, observation in sorted(state["observations"].items())
                },
                "retry_schedule": state["retry_schedule"],
                "gate_knowledge": {
                    plan["gate_key"]: knowledge.get(plan["gate_key"])
                    for plan in sorted(plans, key=lambda item: item["gate_key"])
                },
                "pending_notice_id": None if pending is None else pending["notice_id"],
                "baseline_sequence": (
                    None if notification is None else notification["baseline"]["sequence"]
                ),
            }
        )
        # Tick state is read leniently here: legacy commands never fail on a
        # malformed tick key, they report it unreadable. It is not a
        # fingerprint input, so a running tick does not move the fingerprint.
        tick_value = state.get("tick")
        current = tick_value.get("current") if isinstance(tick_value, dict) else None
        tick_in_progress = isinstance(current, dict) and current.get("status") == "running"
        try:
            self._tick_state(state)
        except AeonBellError:
            tick_readable = False
        else:
            tick_readable = True
        return {
            "computed_at": format_time(now),
            "next_check_at": format_time(next_at),
            "delay_minutes": delay,
            "reason": reason,
            "gates": plans,
            "registry": {
                "counts": counts,
                "attention": len(attention),
                "pending_notice": pending is not None,
                "notification_readable": notification is not None,
                "fingerprint": fingerprint,
                "tick_in_progress": tick_in_progress,
                "tick_readable": tick_readable,
            },
            "bounds": {
                "adaptive_min_minutes": ADAPTIVE_MIN_INTERVAL_MINUTES,
                "adaptive_max_minutes": ADAPTIVE_MAX_INTERVAL_MINUTES,
                "adaptive_unknown_minutes": ADAPTIVE_UNKNOWN_INTERVAL_MINUTES,
                "adaptive_open_minutes": ADAPTIVE_OPEN_INTERVAL_MINUTES,
                "recovery_minutes": RECOVERY_CHECK_MINUTES,
                "liveness_minutes": LIVENESS_CHECK_MINUTES,
            },
        }

    def _observation_requests(
        self, state: dict[str, Any], now: datetime
    ) -> list[dict[str, Any]]:
        """One request per gate key whose planned query is due.

        ``unobserved`` has no usable observation (none stored, or the binding
        changed); ``stale`` has one past its freshness; ``due`` still has a
        fresh one, but an explicit effective interval asks again anyway. A key
        inside its backoff window is not due whatever its plan.
        """
        requests: list[dict[str, Any]] = []
        for plan in self._gate_plans(state, now, {}):
            if not plan["due"]:
                continue
            if plan["observation"] is None:
                reason = "unobserved"
            elif not plan["fresh"]:
                reason = "stale"
            else:
                reason = "due"
            requests.append(
                {
                    "gate_key": plan["gate_key"],
                    "gate": plan["gate"],
                    "kind": plan["kind"],
                    "task_ids": plan["task_ids"],
                    "reason": reason,
                    "freshness_minutes": OBSERVATION_FRESHNESS_MINUTES,
                    "cadence": plan["cadence"],
                    "interval_minutes": plan["interval_minutes"],
                    "query_due_at": plan["query_due_at"],
                }
            )
        return requests

    def _plan_wakes(
        self,
        state: dict[str, Any],
        task_states: dict[tuple[str, str], dict[str, Any]],
        now: datetime,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        skipped: list[dict[str, Any]] = []
        proposals: list[dict[str, Any]] = []
        for record in sorted(
            state["registrations"].values(), key=lambda r: r["sequence"]
        ):
            if record["status"] == "removed":
                continue
            reason = self._ineligibility(state, record, task_states, now)
            if reason is not None:
                skipped.append(
                    {
                        "registration_id": record["registration_id"],
                        "host": record["host"],
                        "task_id": record["task_id"],
                        "episode": record["episode"],
                        "reason": reason,
                    }
                )
                continue
            proposals.append(self._reserve(state, record, now))
        return skipped, proposals

    def _ineligibility(
        self,
        state: dict[str, Any],
        record: dict[str, Any],
        task_states: dict[tuple[str, str], dict[str, Any]],
        now: datetime,
    ) -> str | None:
        status = record["status"]
        if status != "waiting":
            return f"registration-{status}"
        if now >= parse_time(record["expires_at"], "expires_at"):
            return "registration-expired"
        gate_status, gate_reason, _ = self._current_observation(state, record, now)
        if gate_status != "open":
            return gate_reason
        task = task_states.get((record["host"], record["task_id"]))
        if task is None:
            return "task-unknown"
        if task["observed_at"] + timedelta(minutes=TASK_STATE_FRESHNESS_MINUTES) <= now:
            return "task-state-stale"
        if task["status"] != "idle":
            return f"task-{task['status']}"
        return None

    def _reserve(
        self, state: dict[str, Any], record: dict[str, Any], now: datetime
    ) -> dict[str, Any]:
        _, _, observation = self._current_observation(state, record, now)
        assert observation is not None
        attempt_id = secrets.token_hex(12)
        message = self._message(record, observation)
        attempt = {
            "attempt_id": attempt_id,
            "registration_id": record["registration_id"],
            "owner": record["owner"],
            "host": record["host"],
            "task_id": record["task_id"],
            "episode": record["episode"],
            "gate_key": record["gate_key"],
            # The attempt owns the gate it was made against. The registration's
            # gate is the owner's current intent and may be edited later; every
            # label derived from this attempt reads this snapshot instead.
            "gate": dict(record["gate"]),
            "gate_observed_at": observation["observed_at"],
            "status": "reserved",
            "planned_at": format_time(now),
            "resolved_at": None,
            "message_sha256": hashlib.sha256(message.encode("utf-8")).hexdigest(),
        }
        state["attempts"][attempt_id] = attempt
        record["status"] = "reserved"
        record["attempt_id"] = attempt_id
        record["attempt_count"] = record.get("attempt_count", 0) + 1
        record["updated_at"] = format_time(now)
        return {
            "attempt_id": attempt_id,
            "registration_id": record["registration_id"],
            "owner": record["owner"],
            "host": record["host"],
            "task_id": record["task_id"],
            "episode": record["episode"],
            "gate_key": record["gate_key"],
            "gate": record["gate"],
            "gate_observation": {
                "result": observation["result"],
                "reason": observation["reason"],
                "observed_at": observation["observed_at"],
                "expires_at": observation["expires_at"],
            },
            "attempt_status": "reserved",
            "native_steps": [
                {
                    "step": "recheck",
                    "command": ["inspect"],
                    "require": {
                        "registration_id": record["registration_id"],
                        "status": "reserved",
                        "attempt_id": attempt_id,
                        "episode": record["episode"],
                        "expired": False,
                    },
                    "on_mismatch": (
                        "the owner removed or rearmed this registration, or let it "
                        "expire, since planning: do not send; report the attempt as "
                        "not_sent if it is still reserved, otherwise nothing remains to report"
                    ),
                },
                {
                    "step": "read",
                    "tool": "task_read",
                    "arguments": {"host": record["host"], "task_id": record["task_id"]},
                    "require": {"status": "idle", "episode": record["episode"]},
                    "on_mismatch": "do not send; report the attempt as not_sent",
                },
                {
                    "step": "send",
                    "tool": "send_follow_up",
                    "arguments": {
                        "host": record["host"],
                        "task_id": record["task_id"],
                        "message": message,
                    },
                    "model_override": None,
                    "effort_override": None,
                },
                {
                    "step": "report",
                    "command": [
                        "report",
                        "--attempt-id",
                        attempt_id,
                        "--outcome",
                        "accepted|not_sent|unknown",
                    ],
                },
            ],
            "target_revalidation_required": True,
            "next_action": (
                "inspect the registry and read the target immediately before sending; "
                "send only if this attempt is still reserved and the target is still "
                "idle in this episode, then report this attempt"
            ),
            "limitations": NATIVE_LIMITATIONS,
        }

    @staticmethod
    def _message(record: dict[str, Any], observation: dict[str, Any]) -> str:
        gate = record["gate"]
        policy = (
            "recheck the current Rolecasting policy, including any separately required "
            "harmless probe, and confirm the exact exposed model and matching account"
            if gate["kind"] == "daybreak_status"
            else "recheck that the quota bucket still has remaining capacity"
        )
        return (
            f"[Aeon Bell wake] host {record['host']}, task {record['task_id']}, "
            f"episode {record['episode']}. Gate {gate['kind']} was observed "
            f"{observation['result']} at {observation['observed_at']} "
            f"({observation['reason']}). This wake authorizes no work by itself. "
            f"Before continuing, revalidate your own current eligibility: {policy}; "
            "confirm you are still the intended continuation for this episode; stop if "
            "anything changed. Continuation follows.\n\n"
            f"{record['continuation']}"
        )

    @staticmethod
    def _unresolved_attempts(
        state: dict[str, Any], now: datetime
    ) -> list[dict[str, Any]]:
        unresolved: list[dict[str, Any]] = []
        for attempt in sorted(
            state["attempts"].values(), key=lambda a: a["planned_at"]
        ):
            if attempt["status"] not in {"reserved", "unknown"}:
                continue
            age = int(
                (now - parse_time(attempt["planned_at"], "planned_at")).total_seconds()
                // 60
            )
            if attempt["status"] == "reserved":
                next_action = (
                    AeonBell._reserved_guidance(attempt["attempt_id"])
                    + "; a lost process leaves it reserved until it is reported, "
                    "reconciled, or superseded by rearm"
                )
            else:
                next_action = (
                    "reconcile with evidence: check the target task for the continuation "
                    "message, then reconcile as accepted or not_sent"
                )
            unresolved.append(
                {
                    "attempt_id": attempt["attempt_id"],
                    "registration_id": attempt["registration_id"],
                    "host": attempt["host"],
                    "task_id": attempt["task_id"],
                    "episode": attempt["episode"],
                    "status": attempt["status"],
                    "planned_at": attempt["planned_at"],
                    "age_minutes": age,
                    "next_action": next_action,
                }
            )
        return unresolved

    def inspect(self, *, now: datetime) -> dict[str, Any]:
        with self.store.transaction(write=False) as state:
            registrations = [
                self._public_registration(record, now)
                for record in sorted(
                    state["registrations"].values(), key=lambda r: r["sequence"]
                )
                if record["status"] != "removed"
            ]
            observations = [
                {
                    **observation,
                    "fresh": parse_time(observation["expires_at"], "expires_at") > now,
                }
                for observation in sorted(
                    state["observations"].values(), key=lambda o: o["gate_key"]
                )
            ]
            return {
                "registrations": registrations,
                "observations": observations,
                "retry_schedule": state["retry_schedule"],
                "unresolved_attempts": self._unresolved_attempts(state, now),
                "attention": self._attention(state, now),
                "schedule": self._schedule(state, now),
                "limitations": NATIVE_LIMITATIONS,
            }

    @staticmethod
    def _public_registration(record: dict[str, Any], now: datetime) -> dict[str, Any]:
        public = {
            name: record[name]
            for name in (
                "registration_id",
                "owner",
                "host",
                "task_id",
                "episode",
                "gate",
                "gate_key",
                "continuation",
                "status",
                "registered_at",
                "updated_at",
                "expires_at",
                "completed_episodes",
            )
        }
        public["expired"] = now >= parse_time(record["expires_at"], "expires_at")
        public["episodes"] = record.get(
            "episodes",
            list(dict.fromkeys([*record["completed_episodes"], record["episode"]])),
        )
        public["attempt_id"] = record.get("attempt_id")
        public["attempt_count"] = record.get("attempt_count", 0)
        public["unresolved_reason"] = record.get("unresolved_reason")
        # Legacy records carry neither field: null forecast, adaptive cadence.
        public["expected_open_at"] = record.get("expected_open_at")
        public["poll_interval_minutes"] = record.get("poll_interval_minutes")
        public["next_action"] = AeonBell._next_action(record, public["expired"])
        return public

    @staticmethod
    def _next_action(record: dict[str, Any], expired: bool) -> str:
        status = record["status"]
        if status == "waiting" and expired:
            return "registration expired: update expiry or remove it"
        return {
            "waiting": "none: the monitor checks the gate each tick and wakes when eligible",
            "paused": "resume to wait again, or remove",
            "reserved": (
                AeonBell._reserved_guidance(record.get("attempt_id"))
                + "; rearm with a new episode only if that attempt is abandoned"
            ),
            "completed": (
                f"episode {record['episode']} was woken; rearm with a new episode to wait "
                "again"
            ),
            "unresolved": (
                f"reconcile attempt {record.get('attempt_id')} with evidence"
                if record.get("unresolved_reason") == "delivery-unknown"
                else "attempt limit reached for this episode: rearm with a new episode "
                "or remove"
            ),
            "expired": "registration expired: update expiry or remove it",
            "removed": "none",
        }[status]

    @staticmethod
    def _not_sent_next_action(
        record: dict[str, Any], attempt: dict[str, Any], now: datetime
    ) -> str:
        """What a ``not_sent`` resolution asks for, from the registration now.

        The lifecycle table says a not_sent attempt returns the registration to
        waiting or exhausts the episode; by the time the event is relayed the
        owner may have removed, rearmed, or paused it, or a later attempt may
        have moved it on. The next action follows the current state, not the
        table row, and names no episode identity (the notice text carries none).
        """
        status = record["status"]
        if status == "removed":
            return (
                "none: the owner removed this registration; nothing waits on it and "
                "this attempt is closed"
            )
        expired = now >= parse_time(record["expires_at"], "expires_at")
        if status == "expired" or (status == "waiting" and expired):
            return "registration expired: update expiry or remove it"
        rearmed = attempt["episode"] != record["episode"]
        if status == "waiting":
            if rearmed:
                return (
                    "none: the owner rearmed this registration on a new episode, "
                    "which now waits"
                )
            return (
                "none: the registration waits again; the monitor checks the gate "
                "each tick and wakes when eligible"
            )
        if status == "paused":
            return "none: the owner paused this registration; resume to wait again, or remove"
        if status == "reserved":
            return (
                f"none: a later attempt {record.get('attempt_id')} is reserved for this "
                "registration; only the monitor holding that reservation reports it"
            )
        if status == "completed":
            return (
                "none: a later attempt for this registration was accepted; rearm with "
                "a new episode to wait again"
            )
        if record.get("unresolved_reason") == "delivery-unknown":
            return (
                f"reconcile the later attempt {record.get('attempt_id')} with "
                "target-transcript evidence"
            )
        return "attempt limit reached for this episode: rearm with a new episode or remove"

    # -- notification ------------------------------------------------------

    @staticmethod
    def _empty_notification() -> dict[str, Any]:
        return {
            "baseline": {
                "sequence": 0,
                "acknowledged_at": None,
                "notice_id": None,
                "markers": [],
                "reported_events": [],
            },
            "pending": None,
            "knowledge": {},
        }

    @staticmethod
    def _notification(state: dict[str, Any]) -> dict[str, Any]:
        """The private notification state, or an empty one for a store without it.

        A store written before notification state existed has no baseline: its
        first notice reports every standing condition and every terminal attempt
        once (the bootstrap), and nothing is seeded away. A store written before
        per-gate query knowledge existed reads its knowledge from the unhandled
        markers it already holds (the pending snapshot's if one is pending, else
        the baseline's), which is exactly what it retained before. Malformed
        state is refused without touching the registry.
        """
        value = state.get("notification")
        if value is None:
            return AeonBell._empty_notification()

        def strings(item: Any) -> bool:
            return isinstance(item, list) and all(isinstance(s, str) for s in item)

        def natural(item: Any) -> bool:
            return type(item) is int and item >= 0

        def optional_text(item: Any) -> bool:
            return item is None or isinstance(item, str)

        def outcomes(item: Any) -> bool:
            return isinstance(item, dict) and all(
                _is_gate_key(key) and outcome in KNOWLEDGE_OUTCOMES
                for key, outcome in item.items()
            )

        baseline = value.get("baseline") if isinstance(value, dict) else None
        pending = value.get("pending") if isinstance(value, dict) else None
        valid = (
            isinstance(value, dict)
            and set(value) in ({"baseline", "pending"}, {"baseline", "pending", "knowledge"})
            and ("knowledge" not in value or outcomes(value["knowledge"]))
            and isinstance(baseline, dict)
            and set(baseline)
            == {"sequence", "acknowledged_at", "notice_id", "markers", "reported_events"}
            and natural(baseline["sequence"])
            and optional_text(baseline["acknowledged_at"])
            and optional_text(baseline["notice_id"])
            and strings(baseline["markers"])
            and strings(baseline["reported_events"])
            and (
                pending is None
                or (
                    isinstance(pending, dict)
                    and set(pending)
                    == {
                        "notice_id",
                        "computed_at",
                        "sequence",
                        "markers",
                        "new",
                        "cleared",
                        "events",
                        "event_ids",
                        "coverage",
                        "text",
                    }
                    and isinstance(pending["notice_id"], str)
                    and isinstance(pending["computed_at"], str)
                    and natural(pending["sequence"])
                    and strings(pending["markers"])
                    and all(isinstance(pending[n], list) for n in ("new", "cleared", "events"))
                    and strings(pending["event_ids"])
                    and isinstance(pending["coverage"], dict)
                    and isinstance(pending["text"], str)
                )
            )
        )
        if not valid:
            raise AeonBellError(
                "corrupt-store", "notification state has an unsupported shape"
            )
        knowledge = value.get("knowledge")
        if knowledge is None:
            source = baseline["markers"] if pending is None else pending["markers"]
            knowledge = {
                marker.split(":", 1)[1]: "unhandled"
                for marker in source
                if marker.startswith("unhandled:")
            }
        return {"baseline": baseline, "pending": pending, "knowledge": knowledge}

    @staticmethod
    def _validated_adapter_report(value: Any) -> dict[str, str] | None:
        """Map gate key to outcome from one ``codex_status.py observe`` report.

        Only ``gates`` is read: exactly ``gate_key, kind, outcome, reason`` per
        entry. That list is the tick's actual query set, so it says which gates
        were covered this tick; anything else is rejected without echo.
        """
        if value is None:
            return None
        if not isinstance(value, dict) or not isinstance(value.get("gates"), list):
            raise AeonBellError(
                "invalid-adapter-report",
                "adapter report must be an observe report object with a gates list",
            )
        queried: dict[str, str] = {}
        for index, entry in enumerate(value["gates"]):
            if (
                not isinstance(entry, dict)
                or set(entry) != ADAPTER_GATE_FIELDS
                or not _is_gate_key(entry["gate_key"])
                or entry["kind"] not in GATE_KINDS
                or entry["outcome"] not in ADAPTER_OUTCOMES
                or entry["gate_key"] in queried
            ):
                raise AeonBellError(
                    "invalid-adapter-report",
                    f"gates[{index}] must carry exactly gate_key, kind, outcome, reason "
                    "for a distinct registered gate key",
                )
            _bounded_text(entry["reason"], f"gates[{index}].reason")
            queried[entry["gate_key"]] = entry["outcome"]
        return queried

    @staticmethod
    def _labels(gate: dict[str, str] | None) -> dict[str, Any]:
        if gate is None:
            return {"kind": None, "account": None, "route": None}
        return {"kind": gate["kind"], "account": gate["account"], "route": gate["route"]}

    @staticmethod
    def _attempt_gate(state: dict[str, Any], attempt: dict[str, Any]) -> dict[str, str] | None:
        """The gate this attempt was reserved against, or None when unavailable.

        Reservation snapshots the gate onto the attempt; that copy is validated
        against the attempt's gate key before use, and a malformed or
        mismatched copy is refused as a corrupt store rather than read. A
        supported legacy attempt carries only its key: any registration record
        with that exact key holds an identical gate (the key digests the whole
        gate object), and nothing else is evidence. Labels are never
        reconstructed from a registration whose key no longer matches.
        """
        if "gate" in attempt:
            try:
                gate = validate_gate(attempt["gate"])
            except AeonBellError as error:
                raise AeonBellError(
                    "corrupt-store", "attempt names a malformed gate snapshot"
                ) from error
            if gate_key(gate) != attempt["gate_key"]:
                raise AeonBellError(
                    "corrupt-store", "attempt gate snapshot does not match its gate key"
                )
            return gate
        for record in state["registrations"].values():
            if record["gate_key"] == attempt["gate_key"]:
                return record["gate"]
        return None

    @staticmethod
    def _gate_labels(state: dict[str, Any], key: str) -> dict[str, Any]:
        for record in state["registrations"].values():
            if record["gate_key"] == key:
                return AeonBell._labels(record["gate"])
        for attempt in state["attempts"].values():
            if attempt["gate_key"] == key:
                gate = AeonBell._attempt_gate(state, attempt)
                if gate is not None:
                    return AeonBell._labels(gate)
        return AeonBell._labels(None)

    @staticmethod
    def _awaited_gates(state: dict[str, Any], now: datetime) -> dict[str, list[str]]:
        """Gate key to the ids of the waiting, unexpired registrations using it."""
        in_use: dict[str, list[str]] = {}
        for record in sorted(
            state["registrations"].values(), key=lambda r: r["sequence"]
        ):
            if record["status"] == "waiting" and now < parse_time(
                record["expires_at"], "expires_at"
            ):
                in_use.setdefault(record["gate_key"], []).append(
                    record["registration_id"]
                )
        return in_use

    def _notice_snapshot(
        self,
        state: dict[str, Any],
        baseline: dict[str, Any],
        in_use: dict[str, list[str]],
        queried: dict[str, str] | None,
        knowledge: dict[str, str],
        now: datetime,
        configured: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Compare the store and the current query knowledge with the baseline.

        ``knowledge`` already carries this tick's query set; ``queried`` only
        says which of it is fresh this tick and which is retained.
        ``configured`` names the gates whose knowledge this tick learned from
        its own configuration (a query not issued for ``no-binding``): fresh,
        so not retained, yet never part of the queried set or the coverage
        claim, because nothing was asked.
        """
        prior = set(baseline["markers"])
        bodies: dict[str, dict[str, Any]] = {}
        retained: list[str] = []
        for entry in self._attention(state, now):
            marker = f"attention:{entry['registration_id']}:{entry['status']}:{entry['since']}"
            record = state["registrations"][entry["registration_id"]]
            attempt = state["attempts"].get(entry["attempt_id"] or "")
            if attempt is None and entry["status"] == "unresolved":
                # attempt-limit names no open attempt; the episode's last
                # not_sent resolution is the record that defines this entry.
                attempt = self._defining_attempt(state, record, "unresolved")
            # An entry defined by an attempt is that attempt's stuck work and
            # identifies the gate it was reserved against; an expired entry
            # describes the registration's current intent.
            gate = record["gate"] if attempt is None else self._attempt_gate(state, attempt)
            bodies[marker] = {
                "marker": marker,
                "family": "attention",
                "registration_id": entry["registration_id"],
                "status": entry["status"],
                "since": entry["since"],
                "attempt_id": entry["attempt_id"],
                "unresolved_reason": entry["unresolved_reason"],
                **self._labels(gate),
                "next_action": entry["next_action"],
            }
        for key, ids in in_use.items():
            # A gap is known only from an actual query. An unqueried gate (backoff,
            # fresh cache, no adapter run) keeps its latest known result; absence
            # of observation alone never clears it, and a gate never queried is
            # neither a gap nor a clear.
            outcome = knowledge.get(key)
            gap = outcome in CONFIGURATION_GAP_OUTCOMES
            covered = (queried is not None and key in queried) or (
                configured is not None and key in configured
            )
            if gap and not covered:
                retained.append(key)
            if outcome == "unhandled":
                marker = f"unhandled:{key}"
                bodies[marker] = {
                    "marker": marker,
                    "family": "unhandled",
                    "gate_key": key,
                    **self._gate_labels(state, key),
                    "registration_ids": ids,
                    "next_action": (
                        "no binding passed to observe carries this gate's account and "
                        "route labels: pass one, or update or remove the registration"
                    ),
                }
            elif outcome == "no-binding":
                marker = f"no-binding:{key}"
                bodies[marker] = {
                    "marker": marker,
                    "family": "no-binding",
                    "gate_key": key,
                    **self._gate_labels(state, key),
                    "registration_ids": ids,
                    "next_action": (
                        "no --binding was passed to the tick, so this gate was not "
                        "queried: configure the binding that carries its account and "
                        "route labels and bring the existing heartbeat forward, or "
                        "update or remove the registration"
                    ),
                }
            schedule = state["retry_schedule"].get(key)
            if schedule is not None:
                reason = schedule["last_reason"]
                marker = f"failing:{key}:{reason}"
                bodies[marker] = {
                    "marker": marker,
                    "family": "failing",
                    "gate_key": key,
                    **self._gate_labels(state, key),
                    "reason": reason,
                    "failures": schedule["failures"],
                    "next_due_at": schedule["next_due_at"],
                    "registration_ids": ids,
                    "next_action": (
                        "owner: fix the binding, re-register with the current describe "
                        "revision, or remove the registration"
                        if reason.startswith("held:")
                        else f"none: the shared backoff requeries at {schedule['next_due_at']}"
                    ),
                }
        markers_now = sorted(bodies)
        new = [bodies[m] for m in markers_now if m not in prior]
        cleared: list[dict[str, Any]] = []
        for marker in sorted(prior - set(markers_now)):
            family, _, rest = marker.partition(":")
            if family in ("unhandled", "no-binding"):
                cleared.append(
                    {
                        "marker": marker,
                        "family": family,
                        "gate_key": rest,
                        **self._gate_labels(state, rest),
                        "registration_ids": in_use.get(rest, []),
                    }
                )
            elif family == "failing":
                key, _, reason = rest.partition(":")
                cleared.append(
                    {
                        "marker": marker,
                        "family": family,
                        "gate_key": key,
                        **self._gate_labels(state, key),
                        "reason": reason,
                        "registration_ids": in_use.get(key, []),
                    }
                )
        reported = set(baseline["reported_events"])
        events: list[dict[str, Any]] = []
        for attempt in sorted(
            state["attempts"].values(),
            key=lambda a: (a["resolved_at"] or "", a["attempt_id"]),
        ):
            status = attempt["status"]
            event_id = f"{attempt['attempt_id']}:{status}"
            if status not in EVENT_STATUSES or event_id in reported:
                continue
            labels = self._labels(self._attempt_gate(state, attempt))
            if status == "unknown":
                next_action = (
                    f"reconcile attempt {attempt['attempt_id']} with target-transcript "
                    "evidence"
                )
            elif status.endswith("accepted"):
                next_action = (
                    "none: the send tool accepted the wake, which is not delivery; the "
                    "target revalidates before any work"
                )
            else:
                next_action = self._not_sent_next_action(
                    state["registrations"][attempt["registration_id"]], attempt, now
                )
            events.append(
                {
                    "event_id": event_id,
                    "attempt_id": attempt["attempt_id"],
                    "registration_id": attempt["registration_id"],
                    **labels,
                    "status": status,
                    "resolved_at": attempt["resolved_at"],
                    "delivery_claim": DELIVERY_CLAIMS[status],
                    "next_action": next_action,
                }
            )
        return {
            "markers": markers_now,
            "new": new,
            "cleared": cleared,
            "events": events,
            "coverage": {
                "adapter_report": queried is not None,
                "queried": sorted(queried) if queried is not None else [],
                "retained": sorted(retained),
            },
        }

    @staticmethod
    def _notice_text(pending: dict[str, Any]) -> str:
        """The literal lines the monitor relays. Labels, ids, codes, and next
        actions only: never host or task ids, episodes, continuation text,
        observation values, or binding values."""

        def labels(body: dict[str, Any]) -> str:
            return (
                f"{body['kind'] or 'unknown'} {body['account'] or 'unknown'}/"
                f"{body['route'] or 'unknown'}"
            )

        def ids(body: dict[str, Any]) -> str:
            return ", ".join(body["registration_ids"]) or "none"

        lines = [
            f"Aeon Bell notice {pending['notice_id']}: registry state as of "
            f"{pending['computed_at']} (report {pending['sequence'] + 1})"
        ]
        for event in pending["events"]:
            lines.append(
                f"event: attempt {event['attempt_id']} for registration "
                f"{event['registration_id']} ({labels(event)}) {event['status']} at "
                f"{event['resolved_at']}; delivery claim {event['delivery_claim']}; "
                f"next: {event['next_action']}"
            )
        for prefix, entries in (("new", pending["new"]), ("cleared", pending["cleared"])):
            for body in entries:
                if body["family"] == "attention":
                    lines.append(
                        f"{prefix}: registration {body['registration_id']} {body['status']} "
                        f"since {body['since']} ({labels(body)}); attempt "
                        f"{body['attempt_id'] or 'none'}; reason "
                        f"{body['unresolved_reason'] or 'none'}; next: {body['next_action']}"
                    )
                elif body["family"] in ("unhandled", "no-binding"):
                    line = (
                        f"{prefix}: {body['family']} gate {labels(body)} key "
                        f"{body['gate_key']}; registrations {ids(body)}"
                    )
                    if prefix == "new":
                        line += f"; next: {body['next_action']}"
                    lines.append(line)
                else:
                    line = (
                        f"{prefix}: failing gate {labels(body)} key {body['gate_key']} "
                        f"reason {body['reason']}"
                    )
                    if prefix == "new":
                        line += (
                            f" (failures {body['failures']}, next query "
                            f"{body['next_due_at']}); registrations {ids(body)}; "
                            f"next: {body['next_action']}"
                        )
                    else:
                        line += f"; registrations {ids(body)}"
                    lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def _public_baseline(baseline: dict[str, Any]) -> dict[str, Any]:
        return dict(baseline)

    def notice(self, *, adapter_report: Any, now: datetime) -> dict[str, Any]:
        """Select what a tick must relay, freezing it until acknowledged.

        A pending notice is returned verbatim, whatever changed since, so a
        relay that crashed before acknowledging repeats the same text (at least
        once). A quiet tick presents nothing and needs no acknowledgement.

        Whatever is presented, a valid adapter report is learned: the durable
        per-gate query knowledge takes this tick's outcomes under the same lock,
        so a result seen during a replay tick, or during a quiet one, is still
        the latest known result when a later tick does not query the gate.
        Knowledge is pruned to the gates that waiting registrations use when a
        fresh notice is computed, where an owner change already reads as
        cleared; it is never pruned on a replay, so an owner pause and resume
        under a pending notice cannot manufacture a clear.
        """
        queried = self._validated_adapter_report(adapter_report)
        with self.store.transaction(write=False) as state:
            result, changed = self._notice_locked(state, queried, now)
            if changed:
                self.store.save(state)
            return result

    def _notice_locked(
        self,
        state: dict[str, Any],
        queried: dict[str, str] | None,
        now: datetime,
        configured: dict[str, str] | None = None,
    ) -> tuple[dict[str, Any], bool]:
        """The notice selection on a loaded state; returns the result and
        whether the caller must save the state it mutated. ``configured`` is
        the directed tick's own configuration knowledge for gates it requested
        but could not query (``no-binding``); it is learned like a query
        outcome and never counted as one."""
        notification = self._notification(state)
        baseline = notification["baseline"]
        pending = notification["pending"]
        knowledge = dict(notification["knowledge"])
        if queried is not None:
            knowledge.update(queried)
        if configured is not None:
            knowledge.update(configured)
        if pending is None:
            in_use = self._awaited_gates(state, now)
            knowledge = {k: v for k, v in knowledge.items() if k in in_use}
            snapshot = self._notice_snapshot(
                state, baseline, in_use, queried, knowledge, now, configured
            )
            if not (snapshot["new"] or snapshot["cleared"] or snapshot["events"]):
                current = {
                    "baseline": baseline,
                    "pending": None,
                    "knowledge": knowledge,
                }
                changed = knowledge != notification["knowledge"]
                if changed:
                    state["notification"] = current
                return {
                    "notice_id": None,
                    "computed_at": format_time(now),
                    "report": False,
                    "replayed": False,
                    "sequence": baseline["sequence"],
                    "acknowledged_at": baseline["acknowledged_at"],
                    "markers_now": snapshot["markers"],
                    "new": [],
                    "cleared": [],
                    "events": [],
                    "coverage": snapshot["coverage"],
                    "text": None,
                    "schedule": self._schedule(state, now, current),
                    "limitations": [*NATIVE_LIMITATIONS, NOTIFICATION_LIMITATION],
                }, changed
            pending = {
                "notice_id": digest(
                    {
                        "sequence": baseline["sequence"],
                        "computed_at": format_time(now),
                        "markers": snapshot["markers"],
                        "new": [b["marker"] for b in snapshot["new"]],
                        "cleared": [b["marker"] for b in snapshot["cleared"]],
                        "events": [e["event_id"] for e in snapshot["events"]],
                    }
                )[:NOTICE_ID_LENGTH],
                "computed_at": format_time(now),
                "sequence": baseline["sequence"],
                "markers": snapshot["markers"],
                "new": snapshot["new"],
                "cleared": snapshot["cleared"],
                "events": snapshot["events"],
                "event_ids": [e["event_id"] for e in snapshot["events"]],
                "coverage": snapshot["coverage"],
                "text": "",
            }
            pending["text"] = self._notice_text(pending)
            current = {
                "baseline": baseline,
                "pending": pending,
                "knowledge": knowledge,
            }
            state["notification"] = current
            changed = True
            replayed = False
        else:
            current = {
                "baseline": baseline,
                "pending": pending,
                "knowledge": knowledge,
            }
            changed = knowledge != notification["knowledge"]
            if changed:
                state["notification"] = current
            replayed = True
        return {
            "notice_id": pending["notice_id"],
            "computed_at": pending["computed_at"],
            "report": True,
            "replayed": replayed,
            "sequence": pending["sequence"],
            "acknowledged_at": baseline["acknowledged_at"],
            "markers_now": pending["markers"],
            "new": pending["new"],
            "cleared": pending["cleared"],
            "events": pending["events"],
            "coverage": pending["coverage"],
            "text": pending["text"],
            "schedule": self._schedule(state, now, current),
            "limitations": [*NATIVE_LIMITATIONS, NOTIFICATION_LIMITATION],
        }, changed

    def acknowledge(self, *, notice_id: str, now: datetime) -> dict[str, Any]:
        """Promote exactly the pending snapshot to the baseline.

        Binds to the pending notice id only: a stale id never advances past a
        newer pending notice, and the id last acknowledged is answered as
        already acknowledged with the store unchanged. The per-gate query
        knowledge is carried over as it is: acknowledgement consumes the frozen
        snapshot, never anything learned since.
        """
        notice_id = _identity(notice_id, "notice_id")
        with self.store.transaction(write=False) as state:
            result, changed = self._acknowledge_locked(state, notice_id, now)
            if changed:
                self.store.save(state)
            return result

    def _acknowledge_locked(
        self, state: dict[str, Any], notice_id: str, now: datetime
    ) -> tuple[dict[str, Any], bool]:
        """Acknowledgement on a loaded state; returns the result and whether
        the caller must save."""
        notification = self._notification(state)
        baseline = notification["baseline"]
        pending = notification["pending"]
        if pending is None or pending["notice_id"] != notice_id:
            if notice_id == baseline["notice_id"]:
                return {
                    "acknowledged": False,
                    "result": "already-acknowledged",
                    "notice_id": notice_id,
                    "pending_notice_id": None if pending is None else pending["notice_id"],
                    "baseline": self._public_baseline(baseline),
                    "schedule": self._schedule(state, now, notification),
                }, False
            raise AeonBellError(
                "unknown-notice",
                "no pending notice has that id; rerun notice and acknowledge its id",
            )
        existing = set(state["attempts"])
        reported = sorted(
            {
                event_id
                for event_id in [*baseline["reported_events"], *pending["event_ids"]]
                if event_id.split(":", 1)[0] in existing
            }
        )
        notification = {
            "baseline": {
                "sequence": baseline["sequence"] + 1,
                "acknowledged_at": format_time(now),
                "notice_id": notice_id,
                "markers": pending["markers"],
                "reported_events": reported,
            },
            "pending": None,
            "knowledge": notification["knowledge"],
        }
        state["notification"] = notification
        return {
            "acknowledged": True,
            "result": "acknowledged",
            "notice_id": notice_id,
            "pending_notice_id": None,
            "baseline": self._public_baseline(notification["baseline"]),
            "schedule": self._schedule(state, now, notification),
        }, True

    # -- directed tick -----------------------------------------------------
    #
    # One tick is a sequence of locked transitions on the store. Each
    # transition validates the durable tick record, applies exactly one
    # submitted result, runs the internal phases that need no native effect,
    # and issues at most one next action with fully bound arguments. The
    # monitor performs that action with its own native tool and submits the
    # typed result; the engine never verifies the result, only its shape,
    # its binding to the pending action, and its consequences.

    @staticmethod
    def _is_hex_id(value: Any, length: int) -> bool:
        return (
            isinstance(value, str)
            and len(value) == length
            and all(ch in "0123456789abcdef" for ch in value)
        )

    @staticmethod
    def _tick_state(state: dict[str, Any]) -> dict[str, Any]:
        """The durable tick state, validated strictly, or empty for a store
        without it. Tick commands fail closed on a malformed key; the repair
        is the operator deleting the key under the store's lock discipline,
        as for malformed notification state. Reservations and notices live
        outside the key and are never affected."""
        value = state.get("tick")
        if value is None:
            return {"current": None, "last": None}

        def refuse() -> None:
            raise AeonBellError("corrupt-store", "tick state has an unsupported shape")

        def time_ok(item: Any) -> bool:
            try:
                parse_time(item, "tick time")
            except AeonBellError:
                return False
            return True

        def optional_time(item: Any) -> bool:
            return item is None or time_ok(item)

        def text(item: Any) -> bool:
            return isinstance(item, str)

        def optional_text(item: Any) -> bool:
            return item is None or isinstance(item, str)

        def strings(item: Any) -> bool:
            return isinstance(item, list) and all(isinstance(s, str) for s in item)

        def keys(item: Any, fields: set[str]) -> bool:
            return isinstance(item, dict) and set(item) == fields

        def bounded_lines(item: Any) -> bool:
            return (
                strings(item)
                and len(item) <= TICK_DIAGNOSTICS_MAX_LINES + 1
                and all(len(line) <= TICK_DIAGNOSTIC_MAX_CHARS for line in item)
            )

        if not keys(value, {"current", "last"}):
            refuse()
        current, last = value["current"], value["last"]
        if current is not None:
            if not keys(current, TICK_RECORD_FIELDS):
                refuse()
            if not (
                AeonBell._is_hex_id(current["tick_id"], TICK_ID_LENGTH)
                and current["status"] == "running"
                and time_ok(current["started_at"])
                and current["finished_at"] is None
                and current["time_mode"] in TICK_TIME_MODES
                and time_ok(current["last_now"])
                and strings(current["binding_paths"])
                and optional_text(current["heartbeat"])
                and current["phase"] in TICK_PHASES
                and strings(current["registration_order"])
                and all(r in state["registrations"] for r in current["registration_order"])
                and isinstance(current["task_states"], dict)
                and all(
                    keys(item, {"status", "observed_at"})
                    and item["status"] in TASK_STATUSES
                    and time_ok(item["observed_at"])
                    for item in current["task_states"].values()
                )
                and strings(current["requested_gate_keys"])
                and isinstance(current["registry_changed_after_last_write"], bool)
                and bounded_lines(current["diagnostics"])
            ):
                refuse()
            observe = current["observe"]
            if not (
                keys(observe, TICK_OBSERVE_FIELDS)
                and isinstance(observe["issued"], bool)
                and observe["not_issued_reason"] in (None, *OBSERVE_NOT_ISSUED_REASONS)
                and not isinstance(observe["exit_code"], bool)
                and observe["exit_code"] in (None, 0, 2)
                and optional_text(observe["failure_line"])
                and observe["artifacts_code"] in (None, *ARTIFACT_CODES)
                and strings(observe["answered_gate_keys"])
                and strings(observe["unanswered_gate_keys"])
                and isinstance(observe["adapter_report_learned"], bool)
                and (
                    observe["adapter_report"] is None
                    or (
                        isinstance(observe["adapter_report"], dict)
                        and all(
                            _is_gate_key(key) and outcome in ADAPTER_OUTCOMES
                            for key, outcome in observe["adapter_report"].items()
                        )
                    )
                )
            ):
                refuse()
            if not isinstance(current["proposals"], list):
                refuse()
            for proposal in current["proposals"]:
                if not (
                    keys(proposal, TICK_PROPOSAL_FIELDS)
                    and all(text(proposal[name]) for name in TICK_PROPOSAL_FIELDS)
                ):
                    refuse()
                attempt = state["attempts"].get(proposal["attempt_id"])
                stored = hashlib.sha256(proposal["message"].encode("utf-8")).hexdigest()
                if (
                    attempt is None
                    or stored != proposal["message_sha256"]
                    or attempt["message_sha256"] != proposal["message_sha256"]
                ):
                    refuse()
            dispatch = current["dispatch"]
            if not (
                keys(dispatch, {"skipped", "attempts", "cursor"})
                and isinstance(dispatch["skipped"], list)
                and isinstance(dispatch["attempts"], list)
                and (
                    dispatch["cursor"] is None
                    or (type(dispatch["cursor"]) is int and dispatch["cursor"] >= 0)
                )
                and all(
                    keys(entry, {"attempt_id", "registration_id", "stage", "result"})
                    and entry["stage"] in DISPATCH_STAGES
                    and entry["result"] in DISPATCH_RESULTS
                    for entry in dispatch["attempts"]
                )
            ):
                refuse()
            notice = current["notice"]
            if not (
                keys(notice, TICK_NOTICE_FIELDS)
                and optional_text(notice["notice_id"])
                and isinstance(notice["replayed"], bool)
                and isinstance(notice["emitted"], bool)
                and isinstance(notice["acknowledged"], bool)
                and notice["consequence"] in (None, *NOTICE_CONSEQUENCES)
            ):
                refuse()
            writes = current["heartbeat_writes"]
            if not (
                isinstance(writes, list)
                and len(writes) <= TICK_MAX_HEARTBEAT_WRITES
                and all(
                    keys(write, TICK_WRITE_FIELDS)
                    and write["write_number"] in (1, 2)
                    and time_ok(write["target_at"])
                    and type(write["delay_minutes"]) is int
                    and write["rule"] in HEARTBEAT_RULES
                    and text(write["fingerprint"])
                    and write["result"] in (None, *HEARTBEAT_RESULTS)
                    and optional_time(write["next_run_at"])
                    and optional_text(write["reason"])
                    and isinstance(write["basis"], dict)
                    for write in writes
                )
            ):
                refuse()
            actions = current["actions"]
            if not isinstance(actions, list):
                refuse()
            for index, action in enumerate(actions):
                if not (
                    keys(action, TICK_ACTION_FIELDS)
                    and AeonBell._is_hex_id(action["action_id"], ACTION_ID_LENGTH)
                    and action["kind"] in ACTION_KINDS
                    and action["purpose"] in ACTION_PURPOSES[action["kind"]]
                    and time_ok(action["issued_at"])
                    and optional_time(action["submitted_at"])
                    and action["disposition"] in ACTION_DISPOSITIONS
                    and optional_text(action["reason"])
                    and action["consequence"] in (None, *CONSEQUENCE_CODES)
                    and (action["recorded"] is None or isinstance(action["recorded"], dict))
                    and isinstance(action["arguments"], dict)
                    and (action["require"] is None or isinstance(action["require"], dict))
                    and action["restart"] in ("resumable", "abandon-only")
                ):
                    refuse()
                if action["disposition"] == "pending" and index != len(actions) - 1:
                    refuse()
        if last is not None:
            if not (
                keys(last, TICK_SUMMARY_FIELDS)
                and AeonBell._is_hex_id(last["tick_id"], TICK_ID_LENGTH)
                and last["status"] in ("complete", "abandoned")
                and time_ok(last["started_at"])
                and time_ok(last["finished_at"])
                and isinstance(last["actions"], list)
                and all(
                    keys(entry, {"kind", "purpose", "disposition"})
                    for entry in last["actions"]
                )
                and bounded_lines(last["diagnostics_unemitted"])
            ):
                refuse()
            pending = last["abandoned_pending"]
            if pending is not None and not (
                keys(pending, {"action_id", "kind", "purpose", "attempt_id", "notice_id"})
                and optional_text(pending["attempt_id"])
                and optional_text(pending["notice_id"])
            ):
                refuse()
        return {"current": current, "last": last}

    # Artifacts: the observe step's plan, report, and input files live under
    # the store, outside the atomicity of the JSON document. They are written
    # only when observe is issued, kept until the tick ends so a lost observe
    # submit can be re-performed, removed best-effort afterwards, and swept
    # on every start. Nothing outside <store>/ticks/ is ever removed.

    def _artifact_root(self) -> Path:
        return self.store.directory / ARTIFACT_DIRECTORY

    def _artifact_directory(self, tick_id: str) -> Path:
        return self._artifact_root() / tick_id

    @staticmethod
    def _write_private_artifact(path: Path, text: str) -> None:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                fd = -1
                handle.write(text)
        finally:
            if fd != -1:
                os.close(fd)

    def _remove_artifacts(self, tick_id: str) -> bool:
        """Remove one tick's artifact directory by the bounded rule: refuse a
        symlink or a non-directory, unlink only regular files with the three
        known names, then rmdir. False leaves everything in place."""
        directory = self._artifact_directory(tick_id)
        try:
            if os.path.islink(directory):
                return False
            if not os.path.lexists(directory):
                return True
            if not os.path.isdir(directory):
                return False
            for name in os.listdir(directory):
                path = directory / name
                if (
                    name not in ARTIFACT_NAMES
                    or os.path.islink(path)
                    or not os.path.isfile(path)
                ):
                    return False
            for name in os.listdir(directory):
                os.unlink(directory / name)
            os.rmdir(directory)
        except OSError:
            return False
        return True

    def _sweep_artifacts(self, keep: str) -> list[str]:
        """Remove every stale tick directory but the running tick's; each
        failure is one diagnostics line naming the directory, never hidden."""
        root = self._artifact_root()
        lines: list[str] = []
        try:
            names = os.listdir(root)
        except FileNotFoundError:
            return lines
        except OSError:
            return [f"aeon bell: artifact-io: {ARTIFACT_DIRECTORY} could not be listed"]
        for name in sorted(names):
            if name == keep or not self._is_hex_id(name, TICK_ID_LENGTH):
                continue
            if not self._remove_artifacts(name):
                lines.append(
                    f"aeon bell: artifact-io: {ARTIFACT_DIRECTORY}/{name} could not be removed"
                )
        return lines

    def _write_plan(self, tick: dict[str, Any], requests: list[dict[str, Any]]) -> bool:
        root = self._artifact_root()
        directory = self._artifact_directory(tick["tick_id"])
        try:
            root.mkdir(mode=0o700, exist_ok=True)
            if os.path.islink(root) or not os.path.isdir(root):
                return False
            directory.mkdir(mode=0o700, exist_ok=True)
            if os.path.islink(directory) or not os.path.isdir(directory):
                return False
            os.chmod(directory, 0o700)
            self._write_private_artifact(
                directory / "plan.json",
                json.dumps({"observation_requests": requests}, ensure_ascii=False, indent=2)
                + "\n",
            )
        except OSError:
            return False
        return True

    @staticmethod
    def _tick_diagnostic(tick: dict[str, Any], line: str) -> None:
        """Append one prose line for the end-of-tick diagnostics emit, bounded:
        the 33rd and later lines collapse into one counting line."""
        lines = tick["diagnostics"]
        line = line[:TICK_DIAGNOSTIC_MAX_CHARS]
        if len(lines) < TICK_DIAGNOSTICS_MAX_LINES:
            lines.append(line)
            return
        pattern = r"aeon bell: diagnostics-truncated: (\d+) further line\(s\) omitted"
        omitted = 0
        if len(lines) > TICK_DIAGNOSTICS_MAX_LINES:
            match = re.fullmatch(pattern, lines[-1])
            omitted = int(match.group(1)) if match else 0
            lines.pop()
        lines.append(
            f"aeon bell: diagnostics-truncated: {omitted + 1} further line(s) omitted"
        )

    @staticmethod
    def _tick_issue(
        tick: dict[str, Any],
        now: datetime,
        kind: str,
        purpose: str,
        arguments: dict[str, Any],
        require: dict[str, Any] | None,
    ) -> dict[str, Any]:
        action = {
            "action_id": secrets.token_hex(ACTION_ID_LENGTH // 2),
            "kind": kind,
            "purpose": purpose,
            "issued_at": format_time(now),
            "submitted_at": None,
            "disposition": "pending",
            "reason": None,
            "consequence": None,
            "recorded": None,
            "arguments": arguments,
            "require": require,
            "restart": "resumable" if kind in RESUMABLE_KINDS else "abandon-only",
        }
        tick["actions"].append(action)
        return action

    @staticmethod
    def _pending_action(tick: dict[str, Any] | None) -> dict[str, Any] | None:
        if tick is None or not tick["actions"]:
            return None
        action = tick["actions"][-1]
        return action if action["disposition"] == "pending" else None

    def _tick_now(self, tick: dict[str, Any], now: datetime, supplied: bool) -> datetime:
        """The transition time under the tick's fixed time mode: supplied time
        must not run backwards; clock time is clamped forward with one
        diagnostic per tick."""
        if supplied != (tick["time_mode"] == "supplied"):
            raise AeonBellError(
                "tick-clock",
                f"this tick runs in {tick['time_mode']} time mode; "
                + ("omit --now" if supplied else "pass --now on every submit"),
            )
        last = parse_time(tick["last_now"], "last_now")
        if now >= last:
            return now
        if supplied:
            raise AeonBellError("tick-clock", "--now precedes the tick's last transition time")
        line = "aeon bell: clock-regressed: transition time clamped to the tick's last time"
        if line not in tick["diagnostics"]:
            self._tick_diagnostic(tick, line)
        return last

    @staticmethod
    def _tick_result(action: dict[str, Any], value: Any, now: datetime) -> dict[str, Any]:
        """Validate a submitted result against the pending action's exact
        shape, or the failure form; nothing else is accepted."""

        def invalid(message: str) -> None:
            raise AeonBellError("invalid-result", message)

        def time_field(item: Any, name: str) -> datetime:
            try:
                return parse_time(item, name)
            except AeonBellError:
                invalid(f"{name} must be an ISO 8601 timestamp with offset")
            raise AssertionError("unreachable")

        if not isinstance(value, dict):
            invalid("result must be a JSON object")
        kind = action["kind"]
        if set(value) == {"disposition", "reason"} and value["disposition"] in FAILURE_DISPOSITIONS:
            reason = value["reason"]
            if not (
                isinstance(reason, str)
                and reason
                and len(reason) <= IDENTITY_MAX_LENGTH
                and reason.isprintable()
            ):
                invalid(
                    f"reason must be printable text of at most {IDENTITY_MAX_LENGTH} characters"
                )
            return {"failure": True, "disposition": value["disposition"], "reason": reason}
        if kind == "task_read":
            if set(value) != {"status", "observed_at"}:
                invalid("task_read result must carry exactly status and observed_at, or the failure form")
            if value["status"] not in TASK_STATUSES:
                invalid(f"status must be one of {sorted(TASK_STATUSES)}")
            observed_at = time_field(value["observed_at"], "observed_at")
            issued_at = parse_time(action["issued_at"], "issued_at")
            window = timedelta(seconds=RESULT_WINDOW_SECONDS)
            if observed_at < issued_at - window or observed_at > now + window:
                raise AeonBellError(
                    "stale-result",
                    "observed_at must lie between 60 seconds before the action was "
                    "issued and 60 seconds after now",
                )
            return {"failure": False, "status": value["status"], "observed_at": observed_at}
        if kind == "observe":
            exit_code = value.get("exit_code")
            if isinstance(exit_code, bool) or exit_code not in (0, 2):
                invalid("observe result must carry exit_code 0 or 2, or the failure form")
            if exit_code == 0:
                if set(value) != {"exit_code"}:
                    invalid("an exit 0 observe result carries exactly exit_code")
                return {"failure": False, "exit_code": 0, "stderr_line": None}
            if set(value) != {"exit_code", "stderr_line"}:
                invalid("an exit 2 observe result carries exactly exit_code and stderr_line")
            line = value["stderr_line"]
            if not (
                isinstance(line, str)
                and line.isprintable()
                and len(line) <= STDERR_LINE_MAX_CHARS
                and STDERR_LINE_PATTERN.fullmatch(line)
            ):
                invalid(
                    "stderr_line must be the adapter's `codex status: <code>: <message>` "
                    f"line of at most {STDERR_LINE_MAX_CHARS} characters"
                )
            return {"failure": False, "exit_code": 2, "stderr_line": line}
        if kind == "send":
            if not {"outcome"} <= set(value) <= {"outcome", "evidence"}:
                invalid("send result must carry outcome and optional evidence, or the failure form")
            if value["outcome"] not in {"accepted", "not_sent", "unknown"}:
                invalid("outcome must be accepted, not_sent, or unknown")
            try:
                evidence = _evidence(value.get("evidence"))
            except AeonBellError as error:
                invalid(error.message)
                raise AssertionError("unreachable") from error
            return {"failure": False, "outcome": value["outcome"], "evidence": evidence}
        if kind == "emit":
            if set(value) != {"emitted"} or value["emitted"] is not True:
                invalid("emit result must be exactly {\"emitted\": true}, or the failure form")
            return {"failure": False}
        if not {"applied", "next_run_at"} <= set(value) <= {
            "applied",
            "next_run_at",
            "previous_next_run_at",
        }:
            invalid(
                "heartbeat_set result must carry applied, next_run_at, and optional "
                "previous_next_run_at, or the failure form"
            )
        if value["applied"] is not True:
            invalid("applied must be true; report a control that did not apply with the failure form")
        next_run_at = time_field(value["next_run_at"], "next_run_at")
        previous = value.get("previous_next_run_at")
        if previous is not None:
            previous = format_time(time_field(previous, "previous_next_run_at"))
        return {"failure": False, "next_run_at": next_run_at, "previous_next_run_at": previous}

    # -- tick phases --------------------------------------------------------

    def _tick_advance(self, state: dict[str, Any], tick: dict[str, Any], now: datetime) -> None:
        """Run the phases that need no native effect until an action is
        pending or the tick is complete."""
        while True:
            phase = tick["phase"]
            if phase == "task_states":
                done = sum(
                    1
                    for action in tick["actions"]
                    if action["kind"] == "task_read" and action["purpose"] == "task-state"
                )
                if done < len(tick["registration_order"]):
                    registration_id = tick["registration_order"][done]
                    record = state["registrations"][registration_id]
                    self._tick_issue(
                        tick,
                        now,
                        "task_read",
                        "task-state",
                        {
                            "host": record["host"],
                            "task_id": record["task_id"],
                            "registration_id": registration_id,
                            "episode": record["episode"],
                            "attempt_id": None,
                            "require": None,
                        },
                        None,
                    )
                    return
                tick["phase"] = "observe"
            elif phase == "observe":
                if self._tick_enter_observe(state, tick, now):
                    return
                tick["phase"] = "dispatch"
            elif phase == "dispatch":
                if self._tick_enter_dispatch(state, tick, now):
                    return
                tick["phase"] = "notice"
            elif phase == "notice":
                if self._tick_enter_notice(state, tick, now):
                    return
                tick["phase"] = "schedule"
            elif phase == "schedule":
                if self._tick_enter_schedule(state, tick, now):
                    return
                tick["phase"] = "diagnostics"
            elif phase == "diagnostics":
                issued = any(
                    action["kind"] == "emit" and action["purpose"] == "diagnostics"
                    for action in tick["actions"]
                )
                if tick["diagnostics"] and not issued:
                    self._tick_issue(
                        tick,
                        now,
                        "emit",
                        "diagnostics",
                        {
                            "channel": "diagnostics",
                            "text": "\n".join(tick["diagnostics"]),
                            "notice_id": None,
                            "replayed": None,
                        },
                        None,
                    )
                    return
                tick["phase"] = "done"
            else:
                tick["status"] = "complete"
                tick["finished_at"] = format_time(now)
                return

    def _tick_enter_observe(
        self, state: dict[str, Any], tick: dict[str, Any], now: datetime
    ) -> bool:
        """The plan cycle: list the due gates and issue one observe with
        engine-owned paths, or record why none is issued."""
        self._expire_registrations(state, now)
        requests = self._observation_requests(state, now)
        keys = [request["gate_key"] for request in requests]
        tick["requested_gate_keys"] = keys
        observe = tick["observe"]
        observe["unanswered_gate_keys"] = list(keys)
        if not requests:
            observe["not_issued_reason"] = "no-request"
            return False
        if not tick["binding_paths"]:
            # A configuration gap, not a failed query: the notice step learns
            # it as durable knowledge (reported once, quiet while unchanged)
            # and the schedule defers the gate to the liveness bound.
            observe["not_issued_reason"] = "no-binding"
            return False
        if not self._write_plan(tick, requests):
            observe["not_issued_reason"] = "artifact-io"
            self._tick_diagnostic(tick, "aeon bell: artifact-io: plan.json could not be written")
            return False
        directory = self._artifact_directory(tick["tick_id"])
        adapter = Path(__file__).resolve().parent / "codex_status.py"
        argv = ["python3", str(adapter), "observe"]
        for path in tick["binding_paths"]:
            argv += ["--binding", path]
        argv += [
            "--requests",
            str(directory / "plan.json"),
            "--output",
            str(directory / "input.json"),
            "--report",
            str(directory / "report.json"),
        ]
        if tick["time_mode"] == "supplied":
            argv += ["--now", format_time(now)]
        observe["issued"] = True
        self._tick_issue(tick, now, "observe", "query", {"argv": argv, "cwd": None}, None)
        return True

    def _tick_enter_dispatch(
        self, state: dict[str, Any], tick: dict[str, Any], now: datetime
    ) -> bool:
        """The result cycle, then one pre-send read per still-valid reservation."""
        dispatch = tick["dispatch"]
        if dispatch["cursor"] is None:
            self._expire_registrations(state, now)
            task_states: dict[tuple[str, str], dict[str, Any]] = {}
            for key, item in tick["task_states"].items():
                host, _, task_id = key.partition("\0")
                task_states[(host, task_id)] = {
                    "status": item["status"],
                    "observed_at": parse_time(item["observed_at"], "observed_at"),
                }
            skipped, proposals = self._plan_wakes(state, task_states, now)
            dispatch["skipped"] = [
                {"registration_id": entry["registration_id"], "reason": entry["reason"]}
                for entry in skipped
            ]
            for proposal in proposals:
                [send] = [s for s in proposal["native_steps"] if s["step"] == "send"]
                message = send["arguments"]["message"]
                tick["proposals"].append(
                    {
                        "attempt_id": proposal["attempt_id"],
                        "registration_id": proposal["registration_id"],
                        "episode": proposal["episode"],
                        "message": message,
                        "message_sha256": hashlib.sha256(message.encode("utf-8")).hexdigest(),
                    }
                )
            dispatch["cursor"] = 0
        while dispatch["cursor"] < len(tick["proposals"]):
            proposal = tick["proposals"][dispatch["cursor"]]
            mismatch = self._recheck(state, proposal, now)
            if mismatch is not None:
                self._dispatch_mismatch(state, tick, proposal, "recheck", mismatch, now)
                dispatch["cursor"] += 1
                continue
            record = state["registrations"][proposal["registration_id"]]
            require = {"status": "idle", "episode": proposal["episode"]}
            self._tick_issue(
                tick,
                now,
                "task_read",
                "pre-send",
                {
                    "host": record["host"],
                    "task_id": record["task_id"],
                    "registration_id": proposal["registration_id"],
                    "episode": proposal["episode"],
                    "attempt_id": proposal["attempt_id"],
                    "require": require,
                },
                require,
            )
            return True
        return False

    @staticmethod
    def _recheck(state: dict[str, Any], proposal: dict[str, Any], now: datetime) -> str | None:
        """Why this proposal's reservation no longer holds, or None."""
        attempt = state["attempts"][proposal["attempt_id"]]
        if attempt["status"] != "reserved":
            return f"attempt-{attempt['status']}"
        record = state["registrations"][proposal["registration_id"]]
        if record["status"] != "reserved":
            return f"registration-{record['status']}"
        if (
            record.get("attempt_id") != proposal["attempt_id"]
            or record["episode"] != proposal["episode"]
        ):
            return "registration-rearmed"
        if now >= parse_time(record["expires_at"], "expires_at"):
            return "registration-expired"
        return None

    def _dispatch_mismatch(
        self,
        state: dict[str, Any],
        tick: dict[str, Any],
        proposal: dict[str, Any],
        stage: str,
        mismatch: str,
        now: datetime,
    ) -> str:
        attempt = state["attempts"][proposal["attempt_id"]]
        if attempt["status"] == "reserved":
            self._report_locked(
                state, proposal["attempt_id"], "not_sent", {"recheck": mismatch}, now
            )
            result = "not_sent"
        else:
            result = "superseded"
        tick["dispatch"]["attempts"].append(
            {
                "attempt_id": proposal["attempt_id"],
                "registration_id": proposal["registration_id"],
                "stage": stage,
                "result": result,
            }
        )
        return result

    def _dispatch_report(
        self,
        state: dict[str, Any],
        tick: dict[str, Any],
        proposal: dict[str, Any],
        stage: str,
        outcome: str,
        evidence: dict[str, Any],
        now: datetime,
    ) -> str:
        """Report a tick attempt; an attempt an owner or legacy actor settled
        meanwhile is superseded, never a tick failure."""
        try:
            self._report_locked(state, proposal["attempt_id"], outcome, evidence, now)
            result = outcome
        except AeonBellError as error:
            if error.code != "attempt-not-reserved":
                raise
            result = "superseded"
        tick["dispatch"]["attempts"].append(
            {
                "attempt_id": proposal["attempt_id"],
                "registration_id": proposal["registration_id"],
                "stage": stage,
                "result": result,
            }
        )
        return result

    @staticmethod
    def _gate_evidence_fresh(state: dict[str, Any], attempt: dict[str, Any], now: datetime) -> bool:
        """Whether the observation the attempt was reserved against can still
        admit: its stored expiry when the store still holds that observation,
        never later than the freshness window from its timestamp."""
        observed_at = parse_time(attempt["gate_observed_at"], "gate_observed_at")
        deadline = observed_at + timedelta(minutes=OBSERVATION_FRESHNESS_MINUTES)
        stored = state["observations"].get(attempt["gate_key"])
        if stored is not None and stored["observed_at"] == attempt["gate_observed_at"]:
            deadline = min(deadline, parse_time(stored["expires_at"], "expires_at"))
        return deadline > now

    def _tick_pre_send_result(
        self,
        state: dict[str, Any],
        tick: dict[str, Any],
        action: dict[str, Any],
        parsed: dict[str, Any],
        now: datetime,
    ) -> bool:
        """Apply a pre-send read: issue the send only from a fresh idle read
        against still-fresh gate evidence and a reservation that still holds;
        every other result is a not_sent report. Returns True when a send was
        issued."""
        dispatch = tick["dispatch"]
        proposal = tick["proposals"][dispatch["cursor"]]
        attempt = state["attempts"][proposal["attempt_id"]]
        if parsed["failure"]:
            evidence = {"read": parsed["disposition"], "reason": parsed["reason"]}
        else:
            action["recorded"] = {"status": parsed["status"]}
            status = parsed["status"]
            reason: str | None = None
            if status == "idle":
                fresh_until = parsed["observed_at"] + timedelta(
                    minutes=TASK_STATE_FRESHNESS_MINUTES
                )
                if fresh_until <= now:
                    reason = "task-state-stale"
                elif not self._gate_evidence_fresh(state, attempt, now):
                    reason = "gate-observation-stale"
                else:
                    mismatch = self._recheck(state, proposal, now)
                    if mismatch is None:
                        if attempt["message_sha256"] != proposal["message_sha256"]:
                            raise AeonBellError(
                                "corrupt-store",
                                "the stored wake message no longer matches its attempt",
                            )
                        action["consequence"] = "task-state-recorded"
                        record = state["registrations"][proposal["registration_id"]]
                        self._tick_issue(
                            tick,
                            now,
                            "send",
                            "wake",
                            {
                                "tool": "send_follow_up",
                                "host": record["host"],
                                "task_id": record["task_id"],
                                "message": proposal["message"],
                                "message_sha256": proposal["message_sha256"],
                                "model_override": None,
                                "effort_override": None,
                                "attempt_id": proposal["attempt_id"],
                                "registration_id": proposal["registration_id"],
                                "episode": proposal["episode"],
                            },
                            None,
                        )
                        return True
                    result = self._dispatch_mismatch(
                        state, tick, proposal, "pre-send", mismatch, now
                    )
                    action["consequence"] = (
                        "attempt-not-sent" if result == "not_sent" else "attempt-superseded"
                    )
                    dispatch["cursor"] += 1
                    return False
            evidence = {"read": status, "reason": reason}
        result = self._dispatch_report(
            state, tick, proposal, "pre-send", "not_sent", evidence, now
        )
        action["consequence"] = (
            "attempt-not-sent" if result == "not_sent" else "attempt-superseded"
        )
        dispatch["cursor"] += 1
        return False

    def _tick_send_result(
        self,
        state: dict[str, Any],
        tick: dict[str, Any],
        action: dict[str, Any],
        parsed: dict[str, Any],
        now: datetime,
    ) -> None:
        dispatch = tick["dispatch"]
        proposal = tick["proposals"][dispatch["cursor"]]
        if parsed["failure"]:
            outcome = "unknown" if parsed["disposition"] == "failed" else "not_sent"
            evidence: dict[str, Any] = {
                "disposition": parsed["disposition"],
                "reason": parsed["reason"],
            }
        else:
            outcome, evidence = parsed["outcome"], parsed["evidence"]
        result = self._dispatch_report(state, tick, proposal, "send", outcome, evidence, now)
        action["consequence"] = {
            "accepted": "attempt-accepted",
            "not_sent": "attempt-not-sent",
            "unknown": "attempt-unknown",
            "superseded": "attempt-superseded",
        }[result]
        action["recorded"] = {"outcome": outcome, "attempt_id": proposal["attempt_id"]}
        dispatch["cursor"] += 1

    def _ingest_artifacts(
        self, state: dict[str, Any], tick: dict[str, Any], now: datetime
    ) -> tuple[str | None, dict[str, str] | None, list[str]]:
        """Read the adapter's report.json and input.json from the engine's own
        directory. Any unreadable, invalid, or partial file is one artifacts
        code with nothing applied: ingestion runs against copies and is rolled
        back, so a failed observe never leaves half-applied state."""
        directory = self._artifact_directory(tick["tick_id"])

        def load(name: str, code: str) -> Any:
            try:
                raw = (directory / name).read_bytes()
            except OSError:
                return "artifact-io", None
            try:
                return None, json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                return code, None

        code, report = load("report.json", "invalid-adapter-report")
        if code is not None:
            return code, None, []
        try:
            queried = self._validated_adapter_report(report)
        except AeonBellError:
            return "invalid-adapter-report", None, []
        if queried is None:
            return "invalid-adapter-report", None, []
        code, cycle_input = load("input.json", "invalid-input")
        if code is not None:
            return code, None, []
        if not isinstance(cycle_input, dict) or not isinstance(
            cycle_input.get("observations"), list
        ):
            return "invalid-input", None, []
        saved_observations = copy.deepcopy(state["observations"])
        saved_retry = copy.deepcopy(state["retry_schedule"])
        try:
            ingested = self._ingest_observations(state, cycle_input["observations"], now)
        except AeonBellError:
            state["observations"] = saved_observations
            state["retry_schedule"] = saved_retry
            return "invalid-observation", None, []
        answered = [
            key
            for key in tick["requested_gate_keys"]
            if any(entry["gate_key"] == key and entry["accepted"] for entry in ingested)
        ]
        return None, queried, answered

    def _tick_observe_result(
        self,
        state: dict[str, Any],
        tick: dict[str, Any],
        action: dict[str, Any],
        parsed: dict[str, Any],
        now: datetime,
    ) -> None:
        observe = tick["observe"]
        answered: list[str] = []
        if parsed["failure"]:
            observe["failure_line"] = parsed["reason"]
            self._tick_diagnostic(
                tick,
                f"aeon bell: observe-failed: {parsed['disposition']}: {parsed['reason']}",
            )
            action["consequence"] = "query-failed"
            action["recorded"] = {"exit_code": None, "answered_gate_keys": []}
        elif parsed["exit_code"] == 2:
            observe["exit_code"] = 2
            observe["failure_line"] = parsed["stderr_line"]
            self._tick_diagnostic(tick, f"{OBSERVE_STEP_PREFIX}{parsed['stderr_line']}")
            action["consequence"] = "query-failed"
            action["recorded"] = {"exit_code": 2, "answered_gate_keys": []}
        else:
            observe["exit_code"] = 0
            code, queried, answered = self._ingest_artifacts(state, tick, now)
            if code is not None:
                observe["artifacts_code"] = code
                self._tick_diagnostic(
                    tick,
                    f"aeon bell: observe-artifacts: {code}: report.json or input.json unusable",
                )
                action["consequence"] = "query-failed"
            else:
                observe["answered_gate_keys"] = answered
                observe["adapter_report_learned"] = True
                observe["adapter_report"] = queried
                action["consequence"] = "observation-ingested"
            action["recorded"] = {"exit_code": 0, "answered_gate_keys": answered}
        observe["unanswered_gate_keys"] = [
            key for key in tick["requested_gate_keys"] if key not in answered
        ]

    def _tick_enter_notice(
        self, state: dict[str, Any], tick: dict[str, Any], now: datetime
    ) -> bool:
        observe = tick["observe"]
        # A query not issued because no binding was passed is configuration
        # knowledge for every gate this tick requested: the gap is learned
        # from the tick's own inputs, and no adapter report is fabricated.
        configured = (
            {key: "no-binding" for key in tick["requested_gate_keys"]}
            if observe["not_issued_reason"] == "no-binding"
            else None
        )
        result, _ = self._notice_locked(state, observe["adapter_report"], now, configured)
        notice = tick["notice"]
        if not result["report"]:
            return False
        notice["notice_id"] = result["notice_id"]
        notice["replayed"] = result["replayed"]
        pending = self._notification(state)["pending"]
        if pending is None or pending["notice_id"] != result["notice_id"]:
            raise AeonBellError("corrupt-store", "the pending notice does not match the tick's")
        self._tick_issue(
            tick,
            now,
            "emit",
            "notice",
            {
                "channel": "notice",
                "text": result["text"],
                "notice_id": result["notice_id"],
                "replayed": result["replayed"],
            },
            None,
        )
        return True

    def _tick_notice_result(
        self,
        state: dict[str, Any],
        tick: dict[str, Any],
        action: dict[str, Any],
        parsed: dict[str, Any],
        now: datetime,
    ) -> None:
        notice = tick["notice"]
        if parsed["failure"]:
            notice["consequence"] = "notice-still-pending"
            self._tick_diagnostic(
                tick, f"aeon bell: notice-unrelayed: {notice['notice_id']} stays pending"
            )
        else:
            notice["emitted"] = True
            try:
                result, _ = self._acknowledge_locked(state, notice["notice_id"], now)
                consequence = (
                    "notice-acknowledged"
                    if result["acknowledged"]
                    else "notice-acknowledged-elsewhere"
                )
            except AeonBellError as error:
                if error.code != "unknown-notice":
                    raise
                consequence = "notice-acknowledged-elsewhere"
            notice["acknowledged"] = True
            notice["consequence"] = consequence
        action["consequence"] = notice["consequence"]
        action["recorded"] = {"channel": "notice", "notice_id": notice["notice_id"]}
        tick["phase"] = "schedule"

    def _scheduling_decision(
        self, state: dict[str, Any], tick: dict[str, Any], now: datetime
    ) -> dict[str, Any]:
        """Choose the heartbeat target from the schedule recomputed now.

        Per due gate (a gate in a configuration gap is already deferred by the
        schedule and counts as none of these): fresh owner work (not requested
        this tick), answered-still-due (requested and answered, due again on
        its own cadence or stale evidence), or unanswered (requested, no
        accepted ingestion). Fresh owner work runs now. An answered-still-due
        gate keeps the schedule as printed: its deadline is independent of any
        failed observation, which is then retried at that same run rather
        than pushed out. Otherwise an unanswered gate is bounded by the
        recovery bound, never later than a nearer non-due query or waiting
        expiry. Otherwise the schedule applies as printed.
        """
        schedule = self._schedule(state, now)
        requested = set(tick["requested_gate_keys"])
        answered = set(tick["observe"]["answered_gate_keys"])
        unrequested: list[str] = []
        answered_due: list[str] = []
        unanswered: list[str] = []
        non_due: list[datetime] = []
        for plan in schedule["gates"]:
            key = plan["gate_key"]
            if plan["due"]:
                if plan["configuration_gap"]:
                    continue
                if key not in requested:
                    unrequested.append(key)
                elif key in answered:
                    answered_due.append(key)
                else:
                    unanswered.append(key)
            elif plan["check_at"] is not None:
                non_due.append(parse_time(plan["check_at"], "check_at"))
        expiries = [
            parse_time(record["expires_at"], "expires_at")
            for record in state["registrations"].values()
            if record["status"] == "waiting"
            and now < parse_time(record["expires_at"], "expires_at")
        ]
        recovery = now + timedelta(minutes=RECOVERY_CHECK_MINUTES)
        basis = {
            "schedule_reason": schedule["reason"],
            "recovery_bound_at": None,
            "earliest_non_due_check_at": format_time(min(non_due)) if non_due else None,
            "earliest_waiting_expiry_at": format_time(min(expiries)) if expiries else None,
            "unrequested_due_gate_keys": unrequested,
            "answered_due_gate_keys": answered_due,
            "unanswered_due_gate_keys": unanswered,
        }
        if unrequested:
            rule, target = "fresh-owner-work", now
        elif answered_due:
            rule = "schedule-as-printed"
            target = parse_time(schedule["next_check_at"], "next_check_at")
        elif unanswered:
            rule = "failed-observation-recovery"
            target = min([recovery, *non_due, *expiries])
            basis["recovery_bound_at"] = format_time(recovery)
        else:
            rule = "schedule-as-printed"
            target = parse_time(schedule["next_check_at"], "next_check_at")
        if target < now:
            target = now
        delay = math.ceil((target - now).total_seconds() / 60)
        return {
            "target_at": format_time(target),
            "delay_minutes": delay,
            "rule": rule,
            "fingerprint": schedule["registry"]["fingerprint"],
            "basis": basis,
        }

    def _tick_enter_schedule(
        self, state: dict[str, Any], tick: dict[str, Any], now: datetime
    ) -> bool:
        writes = tick["heartbeat_writes"]
        if tick["heartbeat"] is None:
            schedule = self._schedule(state, now)
            self._tick_diagnostic(
                tick,
                "aeon bell: heartbeat-unconfigured: no $HEARTBEAT is configured; next "
                f"check {schedule['next_check_at']} not applied",
            )
            return False
        if writes:
            last = writes[-1]
            if last["result"] in FAILURE_DISPOSITIONS:
                return False
            fingerprint = self._schedule(state, now)["registry"]["fingerprint"]
            if fingerprint == last["fingerprint"]:
                return False
            if len(writes) >= TICK_MAX_HEARTBEAT_WRITES:
                tick["registry_changed_after_last_write"] = True
                self._tick_diagnostic(
                    tick,
                    "aeon bell: schedule-raced: the registry changed during scheduling; "
                    f"the run left applied is from fingerprint {last['fingerprint'][:12]}",
                )
                return False
        decision = self._scheduling_decision(state, tick, now)
        write = {
            "write_number": len(writes) + 1,
            "target_at": decision["target_at"],
            "delay_minutes": decision["delay_minutes"],
            "rule": decision["rule"],
            "fingerprint": decision["fingerprint"],
            "result": None,
            "next_run_at": None,
            "reason": None,
            "basis": decision["basis"],
        }
        writes.append(write)
        self._tick_issue(
            tick,
            now,
            "heartbeat_set",
            "schedule",
            {
                "heartbeat": tick["heartbeat"],
                "target_at": write["target_at"],
                "delay_minutes": write["delay_minutes"],
                "rule": write["rule"],
                "write_number": write["write_number"],
                "fingerprint": write["fingerprint"],
                "basis": write["basis"],
            },
            None,
        )
        return True

    def _tick_heartbeat_result(
        self,
        tick: dict[str, Any],
        action: dict[str, Any],
        parsed: dict[str, Any],
    ) -> None:
        write = tick["heartbeat_writes"][-1]
        if parsed["failure"]:
            write["result"] = parsed["disposition"]
            write["reason"] = parsed["reason"]
            self._tick_diagnostic(
                tick,
                f"aeon bell: heartbeat-control: {parsed['disposition']}: {parsed['reason']}",
            )
            action["consequence"] = "heartbeat-control-failed"
            action["recorded"] = {"next_run_at": None, "write_number": write["write_number"]}
            return
        write["next_run_at"] = format_time(parsed["next_run_at"])
        target = parse_time(write["target_at"], "target_at")
        difference = abs((parsed["next_run_at"] - target).total_seconds())
        if difference > HEARTBEAT_OFF_TARGET_SECONDS:
            write["result"] = "applied-off-target"
            self._tick_diagnostic(
                tick,
                "aeon bell: heartbeat-off-target: applied run differs from the chosen "
                f"target by {round(difference / 60)} minute(s)",
            )
            action["consequence"] = "heartbeat-applied-off-target"
        else:
            write["result"] = "applied"
            action["consequence"] = "heartbeat-applied"
        action["recorded"] = {
            "next_run_at": write["next_run_at"],
            "write_number": write["write_number"],
        }

    def _tick_apply(
        self,
        state: dict[str, Any],
        tick: dict[str, Any],
        action: dict[str, Any],
        parsed: dict[str, Any],
        now: datetime,
    ) -> None:
        """Record one submitted result on its action and apply its consequence."""
        action["submitted_at"] = format_time(now)
        if parsed["failure"]:
            action["disposition"] = parsed["disposition"]
            action["reason"] = parsed["reason"]
        else:
            action["disposition"] = "performed"
        kind, purpose = action["kind"], action["purpose"]
        arguments = action["arguments"]
        if kind == "task_read" and purpose == "task-state":
            if parsed["failure"]:
                action["consequence"] = "no-task-state"
                self._tick_diagnostic(
                    tick,
                    f"aeon bell: task-read-failed: registration "
                    f"{arguments['registration_id']}: {parsed['disposition']}: {parsed['reason']}",
                )
            else:
                key = f"{arguments['host']}\0{arguments['task_id']}"
                tick["task_states"][key] = {
                    "status": parsed["status"],
                    "observed_at": format_time(parsed["observed_at"]),
                }
                action["consequence"] = "task-state-recorded"
                action["recorded"] = {"status": parsed["status"]}
        elif kind == "task_read":
            if self._tick_pre_send_result(state, tick, action, parsed, now):
                return
        elif kind == "observe":
            self._tick_observe_result(state, tick, action, parsed, now)
            tick["phase"] = "dispatch"
        elif kind == "send":
            self._tick_send_result(state, tick, action, parsed, now)
        elif kind == "emit" and purpose == "notice":
            self._tick_notice_result(state, tick, action, parsed, now)
        elif kind == "emit":
            action["consequence"] = (
                "diagnostics-unemitted" if parsed["failure"] else "diagnostics-emitted"
            )
            action["recorded"] = {"channel": "diagnostics", "notice_id": None}
            tick["phase"] = "done"
        else:
            self._tick_heartbeat_result(tick, action, parsed)
        self._tick_advance(state, tick, now)

    # -- tick views ---------------------------------------------------------

    @staticmethod
    def _tick_public_record(tick: dict[str, Any]) -> dict[str, Any]:
        """The tick record for printing: no wake message text (only its
        digest) and no action arguments outside the pending action."""
        public = {name: copy.deepcopy(tick[name]) for name in tick if name not in ("proposals", "actions")}
        public["proposals"] = [
            {name: proposal[name] for name in ("attempt_id", "registration_id", "episode", "message_sha256")}
            for proposal in tick["proposals"]
        ]
        public["actions"] = [
            {name: action[name] for name in action if name not in ("arguments", "require")}
            for action in tick["actions"]
        ]
        return public

    @staticmethod
    def _tick_outcome(tick: dict[str, Any]) -> dict[str, Any]:
        writes = tick["heartbeat_writes"]
        last = writes[-1] if writes else None
        applied = [w for w in writes if w["result"] in ("applied", "applied-off-target")]
        notice = tick["notice"]
        return {
            "wakes": [
                {name: entry[name] for name in ("attempt_id", "registration_id", "result")}
                for entry in tick["dispatch"]["attempts"]
            ],
            "notice": {
                "notice_id": notice["notice_id"],
                "acknowledged": notice["acknowledged"],
                "replayed": notice["replayed"],
            },
            "heartbeat": {
                "issued": last is not None,
                "rule": None if last is None else last["rule"],
                "target_at": None if last is None else last["target_at"],
                "delay_minutes": None if last is None else last["delay_minutes"],
                "writes": len(writes),
                "result": "not-issued" if last is None else last["result"],
                "reason": None if last is None else last["reason"],
                "fingerprint_applied_from": applied[-1]["fingerprint"] if applied else None,
                "registry_changed_after_last_write": tick["registry_changed_after_last_write"],
            },
            "printed_anything": any(
                action["kind"] == "emit" and action["disposition"] == "performed"
                for action in tick["actions"]
            ),
        }

    @staticmethod
    def _tick_summary(tick: dict[str, Any], status: str, now: datetime) -> dict[str, Any]:
        pending = AeonBell._pending_action(tick)
        abandoned = None
        if status == "abandoned" and pending is not None:
            abandoned = {
                "action_id": pending["action_id"],
                "kind": pending["kind"],
                "purpose": pending["purpose"],
                "attempt_id": pending["arguments"].get("attempt_id"),
                "notice_id": pending["arguments"].get("notice_id"),
            }
        emitted = any(
            action["kind"] == "emit"
            and action["purpose"] == "diagnostics"
            and action["disposition"] == "performed"
            for action in tick["actions"]
        )
        return {
            "tick_id": tick["tick_id"],
            "status": status,
            "started_at": tick["started_at"],
            "finished_at": format_time(now),
            "abandoned_pending": abandoned,
            "actions": [
                {name: action[name] for name in ("kind", "purpose", "disposition")}
                for action in tick["actions"]
            ],
            "diagnostics_unemitted": [] if emitted else list(tick["diagnostics"]),
        }

    def _tick_view(
        self,
        state: dict[str, Any],
        tick: dict[str, Any] | None,
        now: datetime,
        last: dict[str, Any] | None,
        last_result: dict[str, Any] | None,
        outcome: dict[str, Any] | None,
    ) -> dict[str, Any]:
        pending = self._pending_action(tick)
        pending_view = None
        if pending is not None:
            pending_view = {
                "action_id": pending["action_id"],
                "kind": pending["kind"],
                "purpose": pending["purpose"],
                "arguments": pending["arguments"],
                "require": pending["require"],
                "result_shape": RESULT_SHAPES[pending["kind"]],
                "failure_form": FAILURE_FORM,
                "restart": pending["restart"],
                "note": ACTION_NOTES[pending["kind"]],
            }
        return {
            "tick": None if tick is None else self._tick_public_record(tick),
            "pending_action": pending_view,
            "last_result": last_result,
            "outcome_when_complete": outcome,
            "last": last,
            "schedule": self._schedule(state, now),
            "limitations": [*NATIVE_LIMITATIONS, NOTIFICATION_LIMITATION, TICK_LIMITATION],
        }

    def _tick_finish_transition(
        self,
        state: dict[str, Any],
        tick: dict[str, Any],
        now: datetime,
        last_result: dict[str, Any] | None,
    ) -> tuple[dict[str, Any], str | None]:
        """Build the view of this transition; a completed tick is moved to
        `last` and its id returned for artifact removal after the save."""
        if tick["status"] == "complete":
            summary = self._tick_summary(tick, "complete", now)
            state["tick"] = {"current": None, "last": summary}
            view = self._tick_view(
                state, tick, now, summary, last_result, self._tick_outcome(tick)
            )
            return view, tick["tick_id"]
        view = self._tick_view(state, tick, now, state["tick"]["last"], last_result, None)
        return view, None

    def _tick_cleanup(self, view: dict[str, Any], tick_id: str | None) -> dict[str, Any]:
        """Best-effort artifact removal after the save; a failure is reported
        on the printed summary and never hidden."""
        if tick_id is not None and not self._remove_artifacts(tick_id):
            line = f"aeon bell: artifact-io: {ARTIFACT_DIRECTORY}/{tick_id} could not be removed"
            if view["last"] is not None:
                view["last"]["diagnostics_unemitted"] = [
                    *view["last"]["diagnostics_unemitted"],
                    line,
                ]
        return view

    # -- tick commands ------------------------------------------------------

    def _new_tick_locked(
        self,
        state: dict[str, Any],
        *,
        now: datetime,
        supplied: bool,
        binding_paths: list[str],
        heartbeat: str | None,
        last: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Create and advance one tick while the caller holds the store lock."""
        tick_id = secrets.token_hex(TICK_ID_LENGTH // 2)
        self._expire_registrations(state, now)
        order = [
            record["registration_id"]
            for record in sorted(
                state["registrations"].values(), key=lambda r: r["sequence"]
            )
            if record["status"] == "waiting"
            and now < parse_time(record["expires_at"], "expires_at")
        ]
        tick: dict[str, Any] = {
            "tick_id": tick_id,
            "status": "running",
            "started_at": format_time(now),
            "finished_at": None,
            "time_mode": "supplied" if supplied else "clock",
            "last_now": format_time(now),
            "binding_paths": binding_paths,
            "heartbeat": heartbeat,
            "phase": "task_states",
            "registration_order": order,
            "task_states": {},
            "requested_gate_keys": [],
            "observe": {
                "issued": False,
                "not_issued_reason": None,
                "exit_code": None,
                "failure_line": None,
                "artifacts_code": None,
                "answered_gate_keys": [],
                "unanswered_gate_keys": [],
                "adapter_report_learned": False,
                "adapter_report": None,
            },
            "proposals": [],
            "dispatch": {"skipped": [], "attempts": [], "cursor": None},
            "notice": {
                "notice_id": None,
                "replayed": False,
                "emitted": False,
                "acknowledged": False,
                "consequence": None,
            },
            "heartbeat_writes": [],
            "registry_changed_after_last_write": False,
            "diagnostics": [],
            "actions": [],
        }
        for line in self._sweep_artifacts(tick_id):
            self._tick_diagnostic(tick, line)
        state["tick"] = {"current": tick, "last": last}
        self._tick_advance(state, tick, now)
        return tick

    def tick_start(
        self,
        *,
        now: datetime,
        supplied: bool,
        binding_paths: list[str],
        heartbeat: str | None,
        abandon: str | None,
    ) -> dict[str, Any]:
        """Start one directed tick: refuse while another runs unless it is
        explicitly abandoned, snapshot the waiting registrations, sweep stale
        artifacts, and issue the first action."""
        if heartbeat is not None:
            heartbeat = _identity(heartbeat, "heartbeat")
        bindings = [os.path.abspath(path) for path in binding_paths]
        with self.store.transaction(write=True) as state:
            ticks = self._tick_state(state)
            current, last = ticks["current"], ticks["last"]
            if current is not None:
                if abandon != current["tick_id"]:
                    raise AeonBellError(
                        "tick-in-progress",
                        f"tick {current['tick_id']} is running: submit its pending action, "
                        f"or start again with --abandon {current['tick_id']}",
                    )
                last = self._tick_summary(current, "abandoned", now)
            elif abandon is not None:
                raise AeonBellError("tick-not-running", "no running tick has that id")
            tick = self._new_tick_locked(
                state,
                now=now,
                supplied=supplied,
                binding_paths=bindings,
                heartbeat=heartbeat,
                last=last,
            )
            view, cleanup = self._tick_finish_transition(state, tick, now, None)
        return self._tick_cleanup(view, cleanup)

    def tick_submit(
        self,
        *,
        tick_id: str,
        action_id: str,
        result: Any,
        now: datetime,
        supplied: bool,
    ) -> dict[str, Any]:
        """Apply the typed result of exactly the pending action and issue the
        next one. Every refusal leaves the store unchanged with the same
        action pending."""
        with self.store.transaction(write=True) as state:
            ticks = self._tick_state(state)
            current, last = ticks["current"], ticks["last"]
            known = {record["tick_id"] for record in (current, last) if record is not None}
            if tick_id not in known:
                raise AeonBellError(
                    "unknown-tick",
                    "no current or last tick has that id; stop this run and start nothing",
                )
            if current is None or current["tick_id"] != tick_id:
                raise AeonBellError(
                    "tick-not-running",
                    "another run ended this tick; stop this run and start nothing",
                )
            now = self._tick_now(current, now, supplied)
            pending = self._pending_action(current)
            if pending is None or pending["action_id"] != action_id:
                raise AeonBellError(
                    "action-not-pending",
                    "that action is not the pending action; run tick status and submit "
                    "for the action it shows",
                )
            parsed = self._tick_result(pending, result, now)
            current["last_now"] = format_time(now)
            self._tick_apply(state, current, pending, parsed, now)
            last_result = {
                "action_id": pending["action_id"],
                "disposition": pending["disposition"],
                "consequence": pending["consequence"],
            }
            view, cleanup = self._tick_finish_transition(state, current, now, last_result)
        return self._tick_cleanup(view, cleanup)

    def tick_status(self, *, now: datetime) -> dict[str, Any]:
        """Read-only view of the running tick, its pending action, and the
        last tick summary; corrupt-store when the tick key is malformed."""
        with self.store.transaction(write=False) as state:
            ticks = self._tick_state(state)
            current = ticks["current"]
            last_result = None
            if current is not None:
                done = [a for a in current["actions"] if a["disposition"] != "pending"]
                if done:
                    last_result = {
                        "action_id": done[-1]["action_id"],
                        "disposition": done[-1]["disposition"],
                        "consequence": done[-1]["consequence"],
                    }
            return self._tick_view(state, current, now, ticks["last"], last_result, None)


def _json_argument(value: str, name: str) -> Any:
    try:
        return json.loads(value)
    except ValueError as error:
        raise AeonBellError("invalid-json", f"{name} is not valid JSON") from error


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    def common(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("--store", required=True, type=Path)
        sub.add_argument(
            "--now", help="ISO 8601 timestamp with offset; defaults to now"
        )

    register = commands.add_parser("register")
    common(register)
    register.add_argument("--owner", required=True)
    register.add_argument("--host", required=True)
    register.add_argument("--task-id", required=True)
    register.add_argument("--episode", required=True)
    register.add_argument("--gate-json", required=True)
    continuation = register.add_mutually_exclusive_group(required=True)
    continuation.add_argument("--continuation")
    continuation.add_argument("--continuation-file", type=Path)
    register.add_argument("--expires-in-minutes", type=int)

    def cadence(sub: argparse.ArgumentParser) -> None:
        sub.add_argument(
            "--expected-open-at",
            help=(
                "owner forecast of when the gate opens: ISO 8601 with offset, "
                f"or {FORECAST_UNKNOWN}"
            ),
        )
        sub.add_argument(
            "--poll-interval-minutes",
            help=(
                "effective cadence already resolved from operator or policy "
                f"requirements: 1 to {EXPLICIT_INTERVAL_MAX_MINUTES}, or {INTERVAL_ADAPTIVE}"
            ),
        )

    cadence(register)

    inspect = commands.add_parser("inspect")
    common(inspect)

    def owned(name: str) -> argparse.ArgumentParser:
        sub = commands.add_parser(name)
        common(sub)
        sub.add_argument("--registration-id", required=True)
        sub.add_argument("--owner", required=True)
        return sub

    update = owned("update")
    update.add_argument("--gate-json")
    revised = update.add_mutually_exclusive_group()
    revised.add_argument("--continuation")
    revised.add_argument("--continuation-file", type=Path)
    update.add_argument("--expires-in-minutes", type=int)
    cadence(update)
    owned("pause")
    owned("resume")
    owned("remove")

    rearm = owned("rearm")
    rearm.add_argument("--episode", required=True)
    rearm.add_argument(
        "--expires-in-minutes",
        type=int,
        help="new expiry from now; required when the registration has expired",
    )
    cadence(rearm)

    cycle = commands.add_parser("cycle")
    common(cycle)
    cycle.add_argument("--input", type=Path, help="JSON object; defaults to empty")

    report = commands.add_parser("report")
    common(report)
    report.add_argument("--attempt-id", required=True)
    report.add_argument(
        "--outcome", required=True, choices=["accepted", "not_sent", "unknown"]
    )
    report.add_argument("--evidence-json")

    reconcile = commands.add_parser("reconcile")
    common(reconcile)
    reconcile.add_argument("--attempt-id", required=True)
    reconcile.add_argument(
        "--resolution", required=True, choices=["accepted", "not_sent"]
    )
    reconcile.add_argument("--evidence-json", required=True)

    notice = commands.add_parser("notice")
    common(notice)
    notice.add_argument(
        "--adapter-report",
        type=Path,
        help="this tick's codex_status.py observe report; omit when observe did not run",
    )

    acknowledge = commands.add_parser("acknowledge")
    common(acknowledge)
    acknowledge.add_argument("--notice-id", required=True)

    tick = commands.add_parser("tick", help="the engine-directed monitor tick")
    tick_commands = tick.add_subparsers(dest="tick_command", required=True)
    tick_start = tick_commands.add_parser("start")
    common(tick_start)
    tick_start.add_argument(
        "--binding",
        type=Path,
        action="append",
        default=[],
        help="private binding config path passed to observe; repeat once per bound route",
    )
    tick_start.add_argument(
        "--heartbeat",
        help="opaque reference of the one existing heartbeat as the harness names it",
    )
    tick_start.add_argument(
        "--abandon", metavar="TICK_ID", help="abandon the running tick with this id first"
    )
    tick_submit = tick_commands.add_parser("submit")
    common(tick_submit)
    tick_submit.add_argument("--tick-id", required=True)
    tick_submit.add_argument("--action-id", required=True)
    result = tick_submit.add_mutually_exclusive_group(required=True)
    result.add_argument("--result-json")
    result.add_argument("--result-file", type=Path)
    tick_status = tick_commands.add_parser("status")
    common(tick_status)

    monitor = commands.add_parser("monitor", help="the registry-bound monitor entry")
    monitor_commands = monitor.add_subparsers(dest="monitor_command", required=True)
    monitor_bind = monitor_commands.add_parser("bind")
    monitor_bind.add_argument("--store", required=True, type=Path)
    monitor_bind.set_defaults(now=None)
    monitor_bind.add_argument("--initialize-registry", action="store_true")
    monitor_bind.add_argument("--registry-id")
    monitor_bind.add_argument("--binding", type=Path, action="append", default=[])
    monitor_bind.add_argument("--heartbeat", required=True)
    monitor_enter = monitor_commands.add_parser("enter")
    monitor_enter.add_argument("--entry-ref", required=True)
    monitor_enter.add_argument("--now")
    monitor_continue = monitor_commands.add_parser("continue")
    monitor_continue.add_argument("--continuation", required=True)
    monitor_continue.add_argument("--result-json", required=True)
    monitor_continue.add_argument("--now")
    monitor_status = monitor_commands.add_parser("status")
    monitor_status.add_argument("--entry-ref", required=True)
    monitor_status.add_argument("--now")
    return parser.parse_args(argv)


def _json_file(path: Path | None, name: str, code: str = "invalid-input") -> Any:
    if path is None:
        return {}
    try:
        return json.loads(path.read_bytes().decode("utf-8"))
    except OSError as error:
        raise AeonBellError(code, f"{name} is unreadable") from error
    except (UnicodeDecodeError, ValueError) as error:
        raise AeonBellError(code, f"{name} is not valid UTF-8 JSON") from error


def _now(value: str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    return parse_time(value, "--now")


def _result_argument(args: argparse.Namespace) -> Any:
    """The submitted result as JSON; any read or parse failure is invalid-result."""
    if args.result_json is not None:
        try:
            return json.loads(args.result_json)
        except ValueError as error:
            raise AeonBellError("invalid-result", "--result-json is not valid JSON") from error
    try:
        return json.loads(args.result_file.read_bytes().decode("utf-8"))
    except OSError as error:
        raise AeonBellError("invalid-result", "--result-file is unreadable") from error
    except (UnicodeDecodeError, ValueError) as error:
        raise AeonBellError(
            "invalid-result", "--result-file is not valid UTF-8 JSON"
        ) from error


def _monitor_result_argument(value: str) -> Any:
    try:
        return json.loads(value)
    except ValueError as error:
        raise AeonBellError(
            "invalid-result", "--result-json is not valid JSON"
        ) from error


def _continuation_argument(args: argparse.Namespace) -> str | None:
    if args.continuation is not None:
        return args.continuation
    if args.continuation_file is None:
        return None
    try:
        return args.continuation_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise AeonBellError(
            "invalid-continuation", "continuation file is unreadable or not UTF-8"
        ) from error


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if args.command == "monitor" and args.monitor_command in {
            "enter",
            "continue",
            "status",
        }:
            ref = (
                args.continuation
                if args.monitor_command == "continue"
                else args.entry_ref
            )
            if args.monitor_command == "continue":
                payload = _continuation_reference(ref)
            else:
                payload = _entry_reference(ref)
            engine = AeonBell(Path(payload["store"]))
        else:
            engine = AeonBell(args.store)
        now = _now(args.now)
        if args.command == "monitor" and args.monitor_command == "bind":
            result = engine.monitor_bind(
                binding_paths=[str(path) for path in args.binding],
                heartbeat=args.heartbeat,
                initialize_registry=args.initialize_registry,
                registry_id=args.registry_id,
            )
        elif args.command == "monitor" and args.monitor_command == "enter":
            result = engine.monitor_enter(
                entry_ref=args.entry_ref,
                now=now,
                supplied=args.now is not None,
            )
        elif args.command == "monitor" and args.monitor_command == "continue":
            result = engine.monitor_continue(
                continuation=args.continuation,
                result=_monitor_result_argument(args.result_json),
                now=now,
                supplied=args.now is not None,
            )
        elif args.command == "monitor" and args.monitor_command == "status":
            result = engine.monitor_status(entry_ref=args.entry_ref, now=now)
        elif args.command == "monitor":
            raise AeonBellError("unsupported-command", "monitor command is not implemented")
        elif args.command == "register":
            result = engine.register(
                owner=args.owner,
                host=args.host,
                task_id=args.task_id,
                episode=args.episode,
                gate=_json_argument(args.gate_json, "--gate-json"),
                continuation=_continuation_argument(args),
                now=now,
                expires_in_minutes=args.expires_in_minutes,
                expected_open_at=args.expected_open_at,
                poll_interval_minutes=args.poll_interval_minutes,
            )
        elif args.command == "update":
            result = engine.update(
                registration_id=args.registration_id,
                owner=args.owner,
                now=now,
                gate=(
                    None
                    if args.gate_json is None
                    else _json_argument(args.gate_json, "--gate-json")
                ),
                continuation=_continuation_argument(args),
                expires_in_minutes=args.expires_in_minutes,
                expected_open_at=args.expected_open_at,
                poll_interval_minutes=args.poll_interval_minutes,
            )
        elif args.command in {"pause", "resume", "remove"}:
            result = getattr(engine, args.command)(
                registration_id=args.registration_id, owner=args.owner, now=now
            )
        elif args.command == "rearm":
            result = engine.rearm(
                registration_id=args.registration_id,
                owner=args.owner,
                episode=args.episode,
                now=now,
                expires_in_minutes=args.expires_in_minutes,
                expected_open_at=args.expected_open_at,
                poll_interval_minutes=args.poll_interval_minutes,
            )
        elif args.command == "cycle":
            result = engine.cycle(
                cycle_input=_json_file(args.input, "--input"), now=now
            )
        elif args.command == "report":
            result = engine.report(
                attempt_id=args.attempt_id,
                outcome=args.outcome,
                evidence=(
                    None
                    if args.evidence_json is None
                    else _json_argument(args.evidence_json, "--evidence-json")
                ),
                now=now,
            )
        elif args.command == "reconcile":
            result = engine.reconcile(
                attempt_id=args.attempt_id,
                resolution=args.resolution,
                evidence=_json_argument(args.evidence_json, "--evidence-json"),
                now=now,
            )
        elif args.command == "notice":
            result = engine.notice(
                adapter_report=(
                    None
                    if args.adapter_report is None
                    else _json_file(
                        args.adapter_report, "--adapter-report", "invalid-adapter-report"
                    )
                ),
                now=now,
            )
        elif args.command == "acknowledge":
            result = engine.acknowledge(notice_id=args.notice_id, now=now)
        elif args.command == "tick" and args.tick_command == "start":
            result = engine.tick_start(
                now=now,
                supplied=args.now is not None,
                binding_paths=[str(path) for path in args.binding],
                heartbeat=args.heartbeat,
                abandon=args.abandon,
            )
        elif args.command == "tick" and args.tick_command == "submit":
            result = engine.tick_submit(
                tick_id=args.tick_id,
                action_id=args.action_id,
                result=_result_argument(args),
                now=now,
                supplied=args.now is not None,
            )
        elif args.command == "tick":
            result = engine.tick_status(now=now)
        else:
            result = engine.inspect(now=now)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except AeonBellError as error:
        print(f"aeon bell: {error}", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"aeon bell: store-io: {error.strerror}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
