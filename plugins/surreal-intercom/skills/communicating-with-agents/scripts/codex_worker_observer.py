#!/usr/bin/env python3
"""Observe one nominated Codex Worker without submitting work."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time

from codex_ipc_core import Refusal, consume_thread_state_record, follow, native_turns
from codex_ipc_transport import CliTransport, ReceiveFailure, ReceivePrefixFailure, discover_owner


INPUT_MAX = 1048576
PROFILE_MAX = {
    "inputBytes": INPUT_MAX,
    "routeBytes": 65536,
    "frameBytes": 65536,
    "incomingBytes": 262144,
    "events": 64,
    "resultBytes": 8192,
    "stdoutBytes": 8192,
    "stderrBytes": 8192,
    "outgoingFrameBytes": 4096,
    "writes": 70,
    "networkSeconds": 10,
    "ioSeconds": 1,
    "cleanupReserveSeconds": 1,
    "observationSeconds": 9,
    "maxReceiptAgeSeconds": 10,
}
PROFILE_KEYS = set(PROFILE_MAX)
ALLOWED_METHODS = {
    "initialize", "thread-owner-discovery", "thread-stream-following-changed",
}


class OutputFailure(Exception):
    pass


def encoded(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()


def bounded_input(path):
    with path.open("rb") as source:
        data = source.read(INPUT_MAX + 1)
    if len(data) > INPUT_MAX:
        raise Refusal("input-byte-limit")
    return data


def require_text(value, reason):
    if not isinstance(value, str) or not value.strip():
        raise Refusal(reason)
    return value


def validated_input(document, input_size):
    if set(document) != {"schema", "observationId", "actor", "route", "scope", "profile"}:
        raise Refusal("invalid-input-shape")
    if document["schema"] != "provingkit-codex-worker-observation-diagnostic-v1":
        raise Refusal("unsupported-input-schema")
    require_text(document["observationId"], "invalid-observation-id")
    actor = document["actor"]
    if (not isinstance(actor, dict) or set(actor) != {"threadId", "hostId"}
            or any(not isinstance(value, str) or not value.strip() for value in actor.values())):
        raise Refusal("invalid-actor")
    route = document["route"]
    if (not isinstance(route, dict)
            or set(route) != {"endpoint", "host", "target", "routeRef", "permissionRef"}):
        raise Refusal("invalid-route")
    for key in route:
        require_text(route[key], "invalid-route")
    if route["host"] != "local":
        raise Refusal("local-route-required")
    scope = document["scope"]
    if scope != {"diagnosticObservation": True, "send": False}:
        raise Refusal("diagnostic-read-only-scope-required")
    profile = document["profile"]
    if not isinstance(profile, dict) or set(profile) != PROFILE_KEYS:
        raise Refusal("explicit-diagnostic-profile-required")
    for key, maximum in PROFILE_MAX.items():
        value = profile[key]
        numeric = type(value) in (int, float) if key.endswith("Seconds") else type(value) is int
        if not numeric or not 0 < value <= maximum:
            raise Refusal("unsupported-diagnostic-profile")
    if profile["resultBytes"] < 1024 or profile["stdoutBytes"] < 128 or profile["stderrBytes"] < 128:
        raise Refusal("diagnostic-output-limit-too-small")
    if profile["cleanupReserveSeconds"] != 1:
        raise Refusal("one-second-cleanup-reserve-required")
    if profile["cleanupReserveSeconds"] >= profile["networkSeconds"]:
        raise Refusal("cleanup-reserve-exhausts-network-budget")
    if profile["observationSeconds"] > profile["networkSeconds"] - profile["cleanupReserveSeconds"]:
        raise Refusal("observation-exceeds-cleanup-reserve")
    if input_size > profile["inputBytes"]:
        raise Refusal("input-byte-limit")
    if len(encoded(route)) > profile["routeBytes"]:
        raise Refusal("route-byte-limit")
    return profile


def iso_time(unix_ns):
    if unix_ns is None:
        return None
    return datetime.fromtimestamp(unix_ns / 1_000_000_000, timezone.utc).isoformat().replace("+00:00", "Z")


def project_snapshot(update):
    state = update["state"]
    runtime_status = state.get("threadRuntimeStatus", {})
    if not isinstance(runtime_status, dict):
        raise Refusal("invalid-thread-runtime-status")
    runtime = runtime_status.get("type")
    if "type" in runtime_status and not isinstance(runtime, str):
        raise Refusal("invalid-thread-runtime-status-type")
    activity = runtime if runtime in {"active", "idle"} else "unknown"
    try:
        turns, complete = native_turns(state)
        if any(not isinstance(turn.get("turnId"), str) or not turn["turnId"].strip()
               for turn in turns):
            raise Refusal("unsupported-turn-id")
        history = {"support": "supported", "complete": complete}
        view = {
            "activity": activity,
            "threadRuntimeStatusType": runtime,
            "turns": [{"turnId": turn.get("turnId"), "status": turn["status"]} for turn in turns],
        }
    except (Refusal, AttributeError, KeyError, TypeError, ValueError) as error:
        history = {"support": "unsupported", "complete": False, "reason": str(error)}
        view = {"activity": activity, "threadRuntimeStatusType": runtime, "turns": None}
    return {
        "revision": update["revision"],
        "receivedAt": iso_time(update.get("receivedAtUnixNs")),
        "receivedAtMonotonic": update["observedAt"],
        "activity": activity,
        "history": history,
        "view": view,
    }


def observe(document, profile):
    route = document["route"]
    limits = {
        "incomingBytes": profile["incomingBytes"],
        "frameBytes": profile["frameBytes"],
        "events": profile["events"],
        "outgoingFrameBytes": profile["outgoingFrameBytes"],
        "maxAge": profile["maxReceiptAgeSeconds"],
    }
    transport = CliTransport(
        route["endpoint"], limits, profile["observationSeconds"],
        network_seconds=profile["networkSeconds"], io_seconds=profile["ioSeconds"],
        cleanup_reserve_seconds=profile["cleanupReserveSeconds"],
        max_writes=profile["writes"], allowed_methods=ALLOWED_METHODS,
        receipt_clock=time.time_ns,
    )
    binding = {
        "host": route["host"], "target": route["target"], "owner": None,
        "generation": transport.generation,
    }
    followed = False
    client = None
    snapshots = []
    snapshot_states = {}
    evidence_reason = None
    revision = None
    dirty = None
    operation_error = None
    acquisition_failure = None
    follow_reason = None
    closure = {"subscription": "not-followed", "connection": "not-opened"}
    binding_invalidations = {
        "connection-reset-needs-new-binding", "owner-disconnected-needs-new-binding",
    }
    def preferred_error(current, candidate):
        if current is None or (candidate in binding_invalidations
                               and current not in binding_invalidations):
            return candidate
        return current
    def record_operation_error(reason, state="unknown"):
        nonlocal operation_error
        current = operation_error["reason"] if operation_error is not None else None
        selected = preferred_error(current, reason)
        if operation_error is None or selected != current:
            operation_error = {
                "state": "unknown" if selected in binding_invalidations else state,
                "reason": selected,
            }
    def mark_acquisition_failure(reason):
        nonlocal acquisition_failure
        if acquisition_failure is None:
            acquisition_failure = reason
    def acquire(envelope, **options):
        before = len(transport.receive_status)
        try:
            records = transport.send(envelope, **options)
        except ReceivePrefixFailure as error:
            mark_acquisition_failure(str(error))
            records = error.records
        except ReceiveFailure as error:
            mark_acquisition_failure(str(error))
            raise
        for reason in transport.receive_status[before:]:
            if reason in {"event-limit", "incoming-byte-limit"}:
                mark_acquisition_failure(reason)
            elif (transport.receiver.incomplete == reason
                  and not (reason == "stream-eof-unknown"
                           and transport.receiver.frame_boundary_eof)):
                mark_acquisition_failure(reason)
        return records
    def process_records(records):
        nonlocal revision, dirty, evidence_reason
        batch_error = None
        for record, message in records:
            try:
                update = consume_thread_state_record(
                    record, message, binding=binding,
                    client=binding.get("client", client), revision=revision,
                )
                if update is None:
                    continue
                snapshot = None
                state_bytes = None
                previous = None
                if update["state"] is not None:
                    state_bytes = encoded(update["state"])
                    snapshot = project_snapshot(update)
                    previous = snapshot_states.get(update["revision"])
                revision = update["revision"]
                dirty = update["dirty"]
                if snapshot is not None:
                    if previous is not None and previous != state_bytes:
                        evidence_reason = "conflicting-same-revision"
                    else:
                        snapshot_states[update["revision"]] = state_bytes
                    snapshots.append(snapshot)
            except Refusal as error:
                batch_error = preferred_error(batch_error, str(error))
        if batch_error is not None:
            raise Refusal(batch_error)
    try:
        client = discover_owner(
            transport, binding, text=require_text, refusal=Refusal,
            record_consumer=process_records, exchange=acquire,
        )
        followed = True
        before = len(transport.receive_status)
        process_records(acquire(follow(client, binding, True), reserve_cleanup=True))
        follow_reason = next(
            (reason for reason in reversed(transport.receive_status[before:])
             if not reason.startswith("receive-disabled:")),
            None,
        )
    except (Refusal, ReceiveFailure, OSError, KeyError, TypeError, ValueError) as error:
        unknown_before_follow = str(error) in {
            "connection-reset-needs-new-binding", "owner-disconnected-needs-new-binding",
        }
        if not (acquisition_failure is not None and str(error) in {
                "initialize-unavailable", "owner-unavailable", "connection-incomplete-before-write",
        }):
            record_operation_error(
                str(error), "unknown" if followed or unknown_before_follow else "refused")
    finally:
        if followed:
            try:
                cleanup_records = acquire(follow(client, binding, False))
                closure["subscription"] = "unfollow-sent-ack-unknown"
                process_records(cleanup_records)
            except (Refusal, AttributeError, KeyError, RecursionError, TypeError, ValueError) as error:
                closure["cleanupFailure"] = str(error)
                record_operation_error(str(error))
            except (ReceiveFailure, OSError) as error:
                closure["subscription"] = "unfollow-unknown:" + str(error)
        try:
            transport.close()
            closure["connection"] = "closed" if transport.stream is not None else "not-opened"
        except OSError as error:
            closure["connection"] = "unknown:" + str(error)
    if operation_error is not None:
        terminal = operation_error
    elif evidence_reason is not None:
        terminal = {"state": "unknown", "reason": evidence_reason}
    elif dirty is not None:
        terminal = {"state": "unknown", "reason": dirty}
    elif acquisition_failure is not None:
        terminal = {"state": "unknown", "reason": acquisition_failure}
    elif not snapshots:
        receive_reason = follow_reason or next(
            (reason for reason in reversed(transport.receive_status)
             if not reason.startswith("receive-disabled:")),
            None,
        )
        terminal = {"state": "unknown", "reason": receive_reason or "missing-snapshot"}
    else:
        final_age = transport.clock() - snapshots[-1]["receivedAtMonotonic"]
        if not 0 <= final_age <= profile["maxReceiptAgeSeconds"]:
            terminal = {"state": "unknown", "reason": "stale-snapshot-receipt"}
        else:
            terminal = {"state": "complete", "reason": "bounded-snapshot-observed"}
    selected = {
        "fields": ["threadRuntimeStatus.type", "turns[].turnId", "turns[].status"],
        "first": snapshots[0]["view"] if snapshots else None,
        "last": snapshots[-1]["view"] if snapshots else None,
        "equal": (snapshots[0]["view"] == snapshots[-1]["view"]
                  if len(snapshots) >= 2
                  and snapshots[0]["history"]["support"] == "supported"
                  and snapshots[-1]["history"]["support"] == "supported" else None),
        "meaning": "equality-does-not-establish-unchanged-work-or-a-legitimate-wait",
    }
    latest = snapshots[-1] if snapshots else None
    return {
        "schema": "provingkit-codex-worker-observation-diagnostic-result-v1",
        "observationId": document["observationId"],
        "status": "observed" if terminal["state"] == "complete" else terminal["state"],
        "terminal": terminal,
        "activity": latest["activity"] if latest else "unknown",
        "localReceipt": {
            "first": snapshots[0]["receivedAt"] if snapshots else None,
            "last": latest["receivedAt"] if latest else None,
            "lastAgeSeconds": (transport.clock() - latest["receivedAtMonotonic"] if latest else None),
            "maximumAgeSeconds": profile["maxReceiptAgeSeconds"],
        },
        "selectedViewComparison": selected,
        "history": {
            "first": snapshots[0]["history"] if snapshots else None,
            "last": latest["history"] if latest else None,
        },
        "binding": {
            "host": route["host"], "target": route["target"], "owner": binding["owner"],
            "routeRef": route["routeRef"], "permissionRef": route["permissionRef"],
            "ownerDiscovery": "cooperative-not-authentication",
            "serverAuthentication": "unknown", "upstreamFreshness": "unknown",
        },
        "acquisition": {
            "incomingBytes": transport.acquired, "events": transport.events,
            "outgoingWrites": transport.write_count, "completedSnapshots": len(snapshots),
            "elapsedSeconds": transport.clock() - transport.started_at,
            "receiveStatus": transport.receive_status,
            "rejectedFrame": transport.receiver.rejected_frame,
            "incomingBytesMeaning": "all-frame-wire-bytes-including-headers",
            "profile": profile,
        },
        "closure": closure,
        "limits": [
            "diagnostic-source-and-synthetic-evidence-only",
            "whole-snapshots-can-contain-history-outside-the-selected-view",
            "no-raw-history-retained-in-result",
            "revision-is-not-a-proved-cross-connection-cursor",
            "positive-comparison-does-not-authenticate-server-or-freshness",
            "activity-arrives-after-history-acquisition",
            "not-a-metadata-only-or-cheap-quiet-polling-claim",
            "no-recovery-decision-or-continuation-authority",
        ],
    }


def write_create_only(path, result, maximum):
    body = encoded(result) + b"\n"
    if len(body) > maximum:
        result = {
            "schema": "provingkit-codex-worker-observation-diagnostic-result-v1",
            "status": "refused", "terminal": {"state": "refused", "reason": "result-byte-limit"},
        }
        body = encoded(result) + b"\n"
    if len(body) > maximum:
        raise OutputFailure("result-limit-cannot-represent-refusal")
    try:
        output_exists = path.exists() or path.is_symlink()
    except OSError as error:
        raise OutputFailure("output-finalization-failed") from error
    if output_exists:
        raise OutputFailure("output-collision")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = None
    temporary_created = False
    finalization_error = None
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        temporary_created = True
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            descriptor = None
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    except OSError as error:
        finalization_error = error
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError as error:
                if finalization_error is None:
                    finalization_error = error
        if temporary_created:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
            except OSError as error:
                if finalization_error is None:
                    finalization_error = error
    if finalization_error is not None:
        raise OutputFailure("output-finalization-failed") from finalization_error
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    profile = {"resultBytes": 8192, "stdoutBytes": 8192, "stderrBytes": 8192}
    try:
        output_exists = arguments.output.exists() or arguments.output.is_symlink()
    except OSError:
        print('{"reason":"output-path-unavailable","status":"refused"}')
        return 3
    if output_exists:
        print('{"reason":"output-collision","status":"refused"}')
        return 3
    try:
        data = bounded_input(arguments.input)
        try:
            document = json.loads(data.decode("utf-8"))
        except RecursionError as error:
            raise Refusal("input-decode-error") from error
        profile = validated_input(document, len(data))
        result = observe(document, profile)
    except (Refusal, OSError, UnicodeError, ValueError, KeyError, TypeError) as error:
        result = {
            "schema": "provingkit-codex-worker-observation-diagnostic-result-v1",
            "status": "refused", "terminal": {"state": "refused", "reason": str(error)},
            "activity": "unknown", "closure": {"subscription": "not-followed", "connection": "not-opened"},
        }
    try:
        result = write_create_only(arguments.output, result, profile["resultBytes"])
    except OutputFailure as error:
        print(encoded({"status": "refused", "reason": str(error)}).decode())
        return 3
    print(encoded({"status": result["status"]}).decode())
    return 0 if result["status"] == "observed" else 2


if __name__ == "__main__":
    sys.exit(main())
