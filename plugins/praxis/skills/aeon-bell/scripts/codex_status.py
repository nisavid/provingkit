#!/usr/bin/env python3
"""Aeon Bell Codex status observation adapter.

Turns the engine's ``observation_requests`` into typed ``quota_recovery`` and
``daybreak_status`` observations by running one fixed, status-only Codex
app-server subprocess under an owner-approved private binding config. It
verifies the local account identity before and after observing and the
policy revision before (the binding is loaded and digested once at startup;
an edit during the run is detected only if it changes the local account id),
reads metadata only (no login, refresh, session, thread, turn, tool, or probe
requests), and never prints credentials, identifiers, paths, or server
output. A mismatch or unknown becomes ``held``; a transport failure becomes
``error``; neither can ever open a gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import queue
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ADAPTER = "praxis-aeon-bell-codex-status"
ADAPTER_VERSION = "1"
BINDING_FORMAT = "praxis-aeon-bell-codex-binding"
BINDING_VERSION = 1
BINDING_FIELDS = {
    "format",
    "version",
    "account",
    "route",
    "policy_revision",
    "codex_home",
    "expected_account_id",
    "quota",
    "models",
}
BINDING_OPTIONAL_FIELDS = {"expected_account_email"}
WINDOW_NAMES = {"primary", "secondary"}
GATE_FIELDS = {
    "quota_recovery": {"kind", "account", "route", "bucket", "policy_revision"},
    "daybreak_status": {"kind", "account", "route", "model", "policy_revision"},
}

CODEX_ARGV = [
    "codex",
    "app-server",
    "--stdio",
    "-c",
    "mcp_servers={}",
    "-c",
    "features.plugins=false",
    "-c",
    "features.apps=false",
]
ENVIRONMENT_ALLOWLIST = (
    "PATH",
    "HOME",
    "LANG",
    "LANGUAGE",
    "LC_ALL",
    "LC_CTYPE",
    "TERM",
    "TMPDIR",
    "USER",
    "LOGNAME",
)
DEFAULT_TIMEOUT_SECONDS = 30
MAX_TIMEOUT_SECONDS = 120
MAX_LINE_BYTES = 1024 * 1024
MAX_MESSAGES = 500
MAX_MODEL_PAGES = 10
MODEL_PAGE_LIMIT = 100
MAX_AUTH_BYTES = 1024 * 1024
MAX_INPUT_BYTES = 4 * 1024 * 1024
MAX_LABEL_LENGTH = 256
STOP_GRACE_SECONDS = 2

LIMITATIONS = [
    "status_only: the adapter reads account, model catalog, and rate-limit "
    "metadata; it runs no model, sends no task data, and is not the harmless "
    "runnability probe that Rolecasting policy separately requires",
    "identity_evidence: the account binding is verified from local Codex auth "
    "metadata under the exact configured home plus the app-server's account "
    "response; when the server exposes no identifier, the evidence level is "
    "local metadata plus server-authenticated, not server-confirmed",
    "snapshot: capacity and exposure may change immediately after this "
    "observation; the woken target must revalidate before doing work",
    "advertised_reset_is_not_trusted: observations expire on the engine's "
    "freshness window and are requeried then, whatever reset time was advertised",
]


class StatusError(ValueError):
    """A public-seam failure with a stable machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class Held(Exception):
    """Identity or binding evidence is missing or contradictory; hold the gate."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class TransportError(Exception):
    """The status transport failed; report a generic error observation."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


# -- small helpers -----------------------------------------------------------


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def parse_time(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise StatusError("invalid-time", f"{name} must be an ISO 8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise StatusError(
            "invalid-time", f"{name} must be an ISO 8601 timestamp"
        ) from error
    if parsed.tzinfo is None:
        raise StatusError("invalid-time", f"{name} must carry a UTC offset")
    return parsed.astimezone(timezone.utc)


def format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def _label(value: Any, name: str, code: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > MAX_LABEL_LENGTH
        or not value.isprintable()
        or value != value.strip()
    ):
        raise StatusError(code, f"{name} must be printable text")
    return value


def _read_json_file(path: Path, code: str, name: str) -> Any:
    try:
        if path.stat().st_size > MAX_INPUT_BYTES:
            raise StatusError(code, f"{name} is too large")
        return json.loads(path.read_bytes().decode("utf-8"))
    except OSError as error:
        raise StatusError(code, f"{name} is unreadable") from error
    except (UnicodeDecodeError, ValueError) as error:
        raise StatusError(code, f"{name} is not valid UTF-8 JSON") from error


# -- binding config ----------------------------------------------------------


def load_binding(path: Path) -> dict[str, Any]:
    """Load and validate the owner-approved private binding config."""
    try:
        info = path.lstat()
    except OSError as error:
        raise StatusError("invalid-binding", "binding config is unreadable") from error
    if not stat.S_ISREG(info.st_mode):
        raise StatusError("invalid-binding", "binding config must be a regular file")
    if info.st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise StatusError(
            "invalid-binding", "binding config must be private (mode 0600)"
        )
    value = _read_json_file(path, "invalid-binding", "binding config")
    if not isinstance(value, dict):
        raise StatusError("invalid-binding", "binding config must be a JSON object")
    keys = set(value)
    if not BINDING_FIELDS <= keys or not keys <= BINDING_FIELDS | BINDING_OPTIONAL_FIELDS:
        raise StatusError(
            "invalid-binding",
            f"binding config must have exactly the fields {sorted(BINDING_FIELDS)} "
            f"plus optional {sorted(BINDING_OPTIONAL_FIELDS)}",
        )
    if value["format"] != BINDING_FORMAT or value["version"] != BINDING_VERSION:
        raise StatusError("invalid-binding", "unsupported binding config format")
    for name in ("account", "route", "policy_revision", "expected_account_id"):
        _label(value[name], name, "invalid-binding")
    if "expected_account_email" in value:
        _label(value["expected_account_email"], "expected_account_email", "invalid-binding")
    home = value["codex_home"]
    if not isinstance(home, str) or not home or not Path(home).is_absolute():
        raise StatusError("invalid-binding", "codex_home must be an absolute path")
    quota = value["quota"]
    if not isinstance(quota, dict):
        raise StatusError("invalid-binding", "quota must be an object of buckets")
    for bucket, spec in quota.items():
        _label(bucket, "quota bucket label", "invalid-binding")
        if not isinstance(spec, dict) or set(spec) != {"limit_id", "windows"}:
            raise StatusError(
                "invalid-binding", "each quota bucket needs exactly limit_id and windows"
            )
        _label(spec["limit_id"], "limit_id", "invalid-binding")
        windows = spec["windows"]
        if not isinstance(windows, list) or not windows:
            raise StatusError("invalid-binding", "windows must be a nonempty list")
        seen: set[str] = set()
        for item in windows:
            if (
                not isinstance(item, dict)
                or not {"window"} <= set(item) <= {"window", "duration_minutes"}
                or item["window"] not in WINDOW_NAMES
                or item["window"] in seen
            ):
                raise StatusError(
                    "invalid-binding",
                    "each window needs a distinct primary or secondary name and "
                    "optional duration_minutes",
                )
            duration = item.get("duration_minutes")
            if duration is not None and (type(duration) is not int or duration <= 0):
                raise StatusError(
                    "invalid-binding", "duration_minutes must be a positive integer"
                )
            seen.add(item["window"])
    models = value["models"]
    if not isinstance(models, dict):
        raise StatusError("invalid-binding", "models must be an object of labels")
    for label, spec in models.items():
        _label(label, "model label", "invalid-binding")
        if (
            not isinstance(spec, dict)
            or set(spec) != {"model", "quota"}
            or spec["quota"] not in quota
        ):
            raise StatusError(
                "invalid-binding",
                "each model needs exactly model and a quota bucket bound in this config",
            )
        _label(spec["model"], "model", "invalid-binding")
    return value


def effective_policy_revision(binding: dict[str, Any]) -> str:
    """Fold an opaque digest of the whole private binding into the policy label.

    Any change to the bound home, account, limits, windows, or models changes
    this value, so gates registered under the old value stop matching and the
    engine drops their cached observations once the owner re-registers.
    """
    return f"{binding['policy_revision']}+{digest(binding)[:16]}"


def describe(binding: dict[str, Any]) -> dict[str, Any]:
    return {
        "adapter": ADAPTER,
        "account": binding["account"],
        "route": binding["route"],
        "policy_revision": effective_policy_revision(binding),
        "buckets": sorted(binding["quota"]),
        "models": sorted(binding["models"]),
        "limitations": LIMITATIONS,
    }


# -- requests ----------------------------------------------------------------


def load_requests(path: Path) -> list[dict[str, Any]]:
    value = _read_json_file(path, "invalid-requests", "requests file")
    if isinstance(value, dict):
        value = value.get("observation_requests", [])
    if not isinstance(value, list):
        raise StatusError(
            "invalid-requests",
            "requests must be a cycle output or a list of observation requests",
        )
    requests: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        label = f"observation_requests[{index}]"
        if not isinstance(item, dict) or not {"gate_key", "gate"} <= set(item):
            raise StatusError("invalid-requests", f"{label} needs gate_key and gate")
        key = item["gate_key"]
        if not isinstance(key, str) or len(key) != 64 or any(
            c not in "0123456789abcdef" for c in key
        ):
            raise StatusError("invalid-requests", f"{label}.gate_key must be a SHA-256")
        gate = item["gate"]
        if not isinstance(gate, dict) or gate.get("kind") not in GATE_FIELDS:
            raise StatusError("invalid-requests", f"{label}.gate has an unknown kind")
        if set(gate) != GATE_FIELDS[gate["kind"]]:
            raise StatusError("invalid-requests", f"{label}.gate has the wrong fields")
        for name, field in gate.items():
            _label(field, f"{label}.gate.{name}", "invalid-requests")
        requests.append({"gate_key": key, "gate": dict(gate)})
    return requests


def load_task_states(path: Path | None) -> list[Any]:
    if path is None:
        return []
    value = _read_json_file(path, "invalid-task-states", "task states file")
    if isinstance(value, dict):
        value = value.get("task_states", [])
    if not isinstance(value, list):
        raise StatusError("invalid-task-states", "task states must be a list")
    return value


# -- local auth metadata -----------------------------------------------------


def local_account_id(codex_home: Path) -> str:
    """Return only the account id from local auth metadata; nothing else is kept."""
    path = codex_home / "auth.json"
    try:
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_AUTH_BYTES:
            raise Held("held:credentials-unreadable")
        document = json.loads(path.read_bytes().decode("utf-8"))
    except FileNotFoundError as error:
        raise Held("held:credentials-missing") from error
    except OSError as error:
        raise Held("held:credentials-unreadable") from error
    except (UnicodeDecodeError, ValueError) as error:
        raise Held("held:credentials-unreadable") from error
    tokens = document.get("tokens") if isinstance(document, dict) else None
    account_id = tokens.get("account_id") if isinstance(tokens, dict) else None
    if not isinstance(account_id, str) or not account_id:
        raise Held("held:credentials-missing")
    return account_id


# -- transport ---------------------------------------------------------------


class _Transport:
    """One bounded newline-delimited JSON-RPC exchange with a child process."""

    def __init__(self, process: subprocess.Popen[bytes], deadline: float) -> None:
        self.process = process
        self.deadline = deadline
        self.lines: queue.Queue[bytes | None] = queue.Queue()
        self.next_id = 1
        self.messages_seen = 0
        self.reader = threading.Thread(target=self._pump, daemon=True)
        self.reader.start()

    def _pump(self) -> None:
        stream = self.process.stdout
        assert stream is not None
        try:
            while True:
                line = stream.readline(MAX_LINE_BYTES + 1)
                if not line:
                    break
                self.lines.put(line)
        except (OSError, ValueError):
            pass
        finally:
            self.lines.put(None)

    def _remaining(self) -> float:
        remaining = self.deadline - _monotonic()
        if remaining <= 0:
            raise TransportError("error:codex-timeout")
        return remaining

    def _write(self, message: dict[str, Any]) -> None:
        stream = self.process.stdin
        assert stream is not None
        try:
            stream.write(json.dumps(message, ensure_ascii=False).encode("utf-8") + b"\n")
            stream.flush()
        except (OSError, ValueError) as error:
            raise TransportError("error:codex-exit") from error

    def notify(self, method: str, params: dict[str, Any]) -> None:
        self._write({"method": method, "params": params})

    def request(self, method: str, params: dict[str, Any]) -> Any:
        identifier = self.next_id
        self.next_id += 1
        self._write({"id": identifier, "method": method, "params": params})
        while True:
            try:
                line = self.lines.get(timeout=self._remaining())
            except queue.Empty as error:
                raise TransportError("error:codex-timeout") from error
            if line is None:
                raise TransportError("error:codex-exit")
            self.messages_seen += 1
            if self.messages_seen > MAX_MESSAGES or len(line) > MAX_LINE_BYTES:
                raise TransportError("error:malformed-response")
            try:
                message = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, ValueError) as error:
                raise TransportError("error:malformed-response") from error
            if not isinstance(message, dict):
                raise TransportError("error:malformed-response")
            if message.get("id") != identifier or "method" in message:
                continue  # notification, server-initiated request, or foreign id
            if "error" in message:
                raise TransportError("error:rpc-error")
            if "result" not in message:
                raise TransportError("error:malformed-response")
            return message["result"]


def _monotonic() -> float:
    return time.monotonic()


def _stop(process: subprocess.Popen[bytes], reader: threading.Thread | None) -> None:
    """Stop the child on every exit path, then release its pipes.

    The process is ended before its stdout is closed: the reader thread holds
    the buffered stream's lock while blocked in ``readline``, so closing first
    would wait for the child instead of ending it.
    """
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=STOP_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    try:
        if process.stdin is not None:
            process.stdin.close()
    except OSError:
        pass
    if reader is not None:
        reader.join(timeout=STOP_GRACE_SECONDS)
    if (reader is None or not reader.is_alive()) and process.stdout is not None:
        try:
            process.stdout.close()
        except OSError:
            pass


def _environment(codex_home: Path) -> dict[str, str]:
    env = {name: os.environ[name] for name in ENVIRONMENT_ALLOWLIST if name in os.environ}
    env["CODEX_HOME"] = str(codex_home)
    return env


def query_status(
    codex_home: Path, *, need_models: bool, timeout_seconds: int
) -> dict[str, Any]:
    """Run the fixed status-only protocol once and return raw result documents."""
    if shutil.which(CODEX_ARGV[0]) is None:
        raise TransportError("error:codex-unavailable")
    workdir = tempfile.mkdtemp(prefix="aeon-bell-status-")
    process: subprocess.Popen[bytes] | None = None
    transport: _Transport | None = None
    try:
        try:
            process = subprocess.Popen(
                CODEX_ARGV,
                cwd=workdir,
                env=_environment(codex_home),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
        except OSError as error:
            raise TransportError("error:codex-unavailable") from error
        transport = _Transport(process, _monotonic() + timeout_seconds)
        transport.request(
            "initialize",
            {
                "clientInfo": {"name": ADAPTER, "version": ADAPTER_VERSION},
                "capabilities": {"experimentalApi": True},
            },
        )
        transport.notify("initialized", {})
        account = transport.request("account/read", {"refreshToken": False})
        models: list[str] | None = None
        if need_models:
            models = []
            cursor: Any = None
            for _ in range(MAX_MODEL_PAGES):
                page = transport.request(
                    "model/list",
                    {"includeHidden": True, "limit": MODEL_PAGE_LIMIT, "cursor": cursor},
                )
                data = page.get("data") if isinstance(page, dict) else None
                if not isinstance(data, list):
                    raise TransportError("error:malformed-response")
                models.extend(
                    item["model"]
                    for item in data
                    if isinstance(item, dict) and isinstance(item.get("model"), str)
                )
                cursor = page.get("nextCursor")
                if cursor is None:
                    break
                if not isinstance(cursor, str) or not cursor:
                    raise TransportError("error:malformed-response")
            else:
                raise TransportError("error:model-list-unbounded")
        limits = transport.request("account/rateLimits/read", {})
        return {"account": account, "models": models, "limits": limits}
    finally:
        if process is not None:
            _stop(process, None if transport is None else transport.reader)
        shutil.rmtree(workdir, ignore_errors=True)


# -- evidence evaluation -----------------------------------------------------


def verify_server_account(account_result: Any, binding: dict[str, Any]) -> str:
    """Return ``confirmed`` or ``unavailable``; raise Held on contradiction."""
    if not isinstance(account_result, dict):
        raise TransportError("error:malformed-response")
    account = account_result.get("account")
    if not isinstance(account, dict):
        raise Held("held:not-authenticated")
    # Only an account whose type is exactly "chatgpt" is supported; a missing or
    # differently shaped type is held rather than assumed to be one.
    if account.get("type") != "chatgpt":
        raise Held("held:account-type-unsupported")
    confirmed = False
    for name in ("accountId", "account_id", "id"):
        value = account.get(name)
        if isinstance(value, str) and value:
            if value != binding["expected_account_id"]:
                raise Held("held:account-mismatch")
            confirmed = True
    expected_email = binding.get("expected_account_email")
    email = account.get("email")
    if expected_email is not None and isinstance(email, str) and email:
        if email != expected_email:
            raise Held("held:account-mismatch")
        confirmed = True
    return "confirmed" if confirmed else "unavailable"


def _window_remaining(limit: dict[str, Any], spec: dict[str, Any]) -> tuple[float, datetime | None] | None:
    window = limit.get(spec["window"])
    if not isinstance(window, dict):
        return None
    used = window.get("usedPercent")
    if isinstance(used, bool) or not isinstance(used, (int, float)):
        return None
    if math.isnan(used) or math.isinf(used) or used < 0 or used > 100:
        return None
    duration = spec.get("duration_minutes")
    if duration is not None and window.get("windowDurationMins") != duration:
        return None
    reset_at: datetime | None = None
    raw_reset = window.get("resetsAt")
    if isinstance(raw_reset, (int, float)) and not isinstance(raw_reset, bool):
        try:
            reset_at = datetime.fromtimestamp(raw_reset, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            reset_at = None
    elif isinstance(raw_reset, str):
        try:
            reset_at = parse_time(raw_reset, "resetsAt")
        except StatusError:
            reset_at = None
    return float(100 - used), reset_at


def bucket_capacity(
    limits_result: Any, spec: dict[str, Any]
) -> tuple[float, datetime | None] | None:
    """Composite remaining capacity across every required window, or None.

    The remaining capacity is the minimum across the required windows. The
    reset is the expected opening of the bucket, so it depends only on the
    windows that block it (remaining 0): the latest of their resets, because
    every blocking window must recover; None when no window blocks (there is
    nothing to open) or when any blocking window advertises no usable reset
    (a known opening is never manufactured from another window's reset). It
    is a scheduling hint only, never capacity.
    """
    if not isinstance(limits_result, dict):
        raise TransportError("error:rate-limits-shape")
    by_id = limits_result.get("rateLimitsByLimitId")
    if not isinstance(by_id, dict):
        raise TransportError("error:rate-limits-shape")
    limit = by_id.get(spec["limit_id"])
    if not isinstance(limit, dict):
        return None
    remaining = 100.0
    reset_at: datetime | None = None
    reset_unknown = False
    for window_spec in spec["windows"]:
        observed = _window_remaining(limit, window_spec)
        if observed is None:
            return None
        remaining = min(remaining, observed[0])
        if observed[0] > 0:
            continue  # not blocking: its reset says nothing about the opening
        if observed[1] is None:
            reset_unknown = True
        elif reset_at is None or observed[1] > reset_at:
            reset_at = observed[1]
    return remaining, None if reset_unknown else reset_at


def typed_observation(
    request: dict[str, Any], binding: dict[str, Any], status: dict[str, Any], now: datetime
) -> dict[str, Any]:
    """One typed ``ok`` observation, or ``Held`` for this gate alone.

    The binding names the limit id and the required windows a bucket depends
    on. When the server does not present that limit, one of those windows, a
    numeric used percentage, or the pinned duration, the binding and the
    server disagree and only the owner can fix it: the gate is
    ``held:limit-window-missing`` (an error observation that backs off and
    never opens) rather than a closed observation that would read like an
    exhausted bucket until the registration expired. A present window with no
    remaining capacity is an ordinary closed observation.
    """
    gate = request["gate"]
    base = {
        "gate_key": request["gate_key"],
        "status": "ok",
        "observed_at": format_time(now),
        "account": gate["account"],
        "route": gate["route"],
    }
    if gate["kind"] == "quota_recovery":
        capacity = bucket_capacity(status["limits"], binding["quota"][gate["bucket"]])
        if capacity is None:
            raise Held("held:limit-window-missing")
        bucket: dict[str, Any] = {
            "name": gate["bucket"],
            "remaining_percent": capacity[0],
        }
        if capacity[1] is not None:
            bucket["reset_at"] = format_time(capacity[1])
        return {**base, "buckets": [bucket]}
    spec = binding["models"][gate["model"]]
    exposed = spec["model"] in (status["models"] or [])
    capacity = bucket_capacity(status["limits"], binding["quota"][spec["quota"]])
    if capacity is None:
        raise Held("held:limit-window-missing")
    observation = {
        **base,
        "exposed_models": [gate["model"]] if exposed else [],
        "capacity": "available" if capacity[0] > 0 else "exhausted",
    }
    if capacity[1] is not None:
        # The bound bucket's expected opening, present only when the bucket is
        # exhausted with known resets. A scheduling hint for the engine; it says
        # nothing about the model's exposure and never opens the gate.
        observation["reset_at"] = format_time(capacity[1])
    return observation


def error_observation(gate_key: str, reason: str, now: datetime) -> dict[str, Any]:
    return {
        "gate_key": gate_key,
        "status": "error",
        "observed_at": format_time(now),
        "reason": reason,
    }


# -- observe -----------------------------------------------------------------


def classify_request(request: dict[str, Any], binding: dict[str, Any], revision: str) -> str | None:
    """Return None when observable, ``binding-labels-differ`` for another
    binding's gate, or a ``held:`` reason that must never open."""
    gate = request["gate"]
    if gate["account"] != binding["account"] or gate["route"] != binding["route"]:
        return "binding-labels-differ"
    if digest(gate) != request["gate_key"]:
        return "held:gate-key-mismatch"
    if gate["policy_revision"] != revision:
        return "held:policy-revision-mismatch"
    if gate["kind"] == "quota_recovery" and gate["bucket"] not in binding["quota"]:
        return "held:bucket-unbound"
    if gate["kind"] == "daybreak_status" and gate["model"] not in binding["models"]:
        return "held:model-unbound"
    return None


def observe_binding(
    binding: dict[str, Any],
    requests: list[dict[str, Any]],
    *,
    now: datetime,
    timeout_seconds: int,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Observe one binding's gates: returns (binding summary, gates, observations)."""
    revision = effective_policy_revision(binding)
    codex_home = Path(binding["codex_home"])
    gates: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    observable: list[dict[str, Any]] = []
    for request in requests:
        reason = classify_request(request, binding, revision)
        if reason is not None:
            gates.append(_gate_entry(request, "held", reason))
            observations.append(error_observation(request["gate_key"], reason, now))
        else:
            observable.append(request)

    identity: dict[str, Any] = {
        "status": "not-needed" if not observable else "unverified",
        "local_metadata_matches": None,
        "server_authenticated": None,
        "server_identity": None,
        "changed_during_observation": None,
    }
    if observable:
        outcome, reason = "observed", None
        status: dict[str, Any] | None = None
        try:
            before = local_account_id(codex_home)
            identity["local_metadata_matches"] = before == binding["expected_account_id"]
            if not identity["local_metadata_matches"]:
                raise Held("held:account-mismatch")
            status = query_status(
                codex_home,
                need_models=any(r["gate"]["kind"] == "daybreak_status" for r in observable),
                timeout_seconds=timeout_seconds,
            )
            identity["server_authenticated"] = isinstance(
                status["account"], dict
            ) and isinstance(status["account"].get("account"), dict)
            identity["server_identity"] = verify_server_account(status["account"], binding)
            after = local_account_id(codex_home)
            identity["changed_during_observation"] = after != before
            if identity["changed_during_observation"]:
                raise Held("held:identity-changed")
            identity["status"] = "verified"
            # Identity and transport are binding-wide; a limit or window the
            # server does not present is one gate's hold, so the other gates
            # on this binding are still observed.
            typed: list[tuple[dict[str, Any], str, str, dict[str, Any]]] = []
            for request in observable:
                try:
                    observation = typed_observation(request, binding, status, now)
                except Held as held:
                    typed.append(
                        (
                            request,
                            "held",
                            held.reason,
                            error_observation(request["gate_key"], held.reason, now),
                        )
                    )
                else:
                    typed.append((request, "observed", "typed-observation", observation))
        except Held as held:
            outcome, reason = "held", held.reason
            identity["status"] = "held"
        except TransportError as failure:
            outcome, reason = "error", failure.reason
            identity["status"] = "error"
        if outcome == "observed":
            for request, gate_outcome, gate_reason, observation in typed:
                observations.append(observation)
                gates.append(_gate_entry(request, gate_outcome, gate_reason))
        else:
            assert reason is not None
            observations.extend(
                error_observation(r["gate_key"], reason, now) for r in observable
            )
            gates.extend(_gate_entry(r, outcome, reason) for r in observable)

    summary = {
        "account": binding["account"],
        "route": binding["route"],
        "policy_revision": revision,
        "identity": identity,
    }
    return summary, gates, observations


def observe(
    bindings: list[dict[str, Any]],
    requests: list[dict[str, Any]],
    task_states: list[Any],
    *,
    now: datetime,
    timeout_seconds: int,
) -> dict[str, Any]:
    """Observe every request through the first binding whose labels match it."""
    summaries: list[dict[str, Any]] = []
    gates: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    remaining = list(requests)
    for binding in bindings:
        mine = [
            r
            for r in remaining
            if r["gate"]["account"] == binding["account"]
            and r["gate"]["route"] == binding["route"]
        ]
        remaining = [r for r in remaining if r not in mine]
        summary, bound_gates, bound_observations = observe_binding(
            binding, mine, now=now, timeout_seconds=timeout_seconds
        )
        summaries.append(summary)
        gates.extend(bound_gates)
        observations.extend(bound_observations)
    gates.extend(_gate_entry(r, "unhandled", "binding-labels-differ") for r in remaining)
    return {
        "adapter": ADAPTER,
        "observed_at": format_time(now),
        "bindings": summaries,
        "gates": gates,
        "cycle_input": {"observations": observations, "task_states": task_states},
        "limitations": LIMITATIONS,
    }


def load_bindings(paths: list[Path]) -> list[dict[str, Any]]:
    bindings = [load_binding(path) for path in paths]
    labels = [(b["account"], b["route"]) for b in bindings]
    if len(set(labels)) != len(labels):
        raise StatusError(
            "invalid-binding", "two binding configs share the same account and route labels"
        )
    return bindings


def _gate_entry(request: dict[str, Any], outcome: str, reason: str) -> dict[str, Any]:
    return {
        "gate_key": request["gate_key"],
        "kind": request["gate"]["kind"],
        "outcome": outcome,
        "reason": reason,
    }


# -- CLI ---------------------------------------------------------------------


def _write_private(path: Path, text: str) -> None:
    """Write a tick artifact readable by this user only.

    The cycle input carries task ids, host labels, and observation values, so
    it is created with mode 0600 and an existing wider file is tightened rather
    than inherited from the umask.
    """
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                fd = -1
                handle.write(text)
        finally:
            if fd != -1:
                os.close(fd)
    except OSError as error:
        raise StatusError("output-io", "output file is unwritable") from error


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    describe_parser = commands.add_parser(
        "describe", help="print the safe labels and effective policy revision"
    )
    describe_parser.add_argument("--binding", required=True, type=Path)

    observe_parser = commands.add_parser(
        "observe", help="observe requested gates and emit cycle-ready input"
    )
    observe_parser.add_argument(
        "--binding",
        required=True,
        type=Path,
        action="append",
        help="private binding config; repeat once per bound route",
    )
    observe_parser.add_argument(
        "--requests",
        required=True,
        type=Path,
        help="engine cycle output or a list of observation requests",
    )
    observe_parser.add_argument(
        "--task-states", type=Path, help="JSON list passed through into cycle_input"
    )
    observe_parser.add_argument(
        "--output", type=Path, help="also write cycle_input to this file"
    )
    observe_parser.add_argument(
        "--report", type=Path, help="also write the printed report to this file"
    )
    observe_parser.add_argument("--now", help="ISO 8601 timestamp with offset")
    observe_parser.add_argument(
        "--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if args.command == "describe":
            result = describe(load_binding(args.binding))
        else:
            bindings = load_bindings(args.binding)
            if not 1 <= args.timeout_seconds <= MAX_TIMEOUT_SECONDS:
                raise StatusError(
                    "invalid-timeout",
                    f"timeout-seconds must be from 1 to {MAX_TIMEOUT_SECONDS}",
                )
            now = (
                datetime.now(timezone.utc)
                if args.now is None
                else parse_time(args.now, "--now")
            )
            result = observe(
                bindings,
                load_requests(args.requests),
                load_task_states(args.task_states),
                now=now,
                timeout_seconds=args.timeout_seconds,
            )
            # Sequential private writes, output first, then the report, then
            # stdout; there is no transaction across them. A failure exits 2
            # with nothing printed, and a file written earlier in this run
            # may remain: the engine reads neither file unless the run
            # exited 0, and refuses any missing or partial file.
            if args.output is not None:
                _write_private(
                    args.output,
                    json.dumps(result["cycle_input"], ensure_ascii=False, indent=2)
                    + "\n",
                )
            if args.report is not None:
                _write_private(
                    args.report,
                    json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
                    + "\n",
                )
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except StatusError as error:
        print(f"codex status: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
