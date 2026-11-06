#!/usr/bin/env python3
"""Submit one local owner-admission prototype request from a planned mailbox.

Trusted caller records are cooperative declarations, not permission enforcement.
The owner may use native admission or ordinary turn/start fallback. Neither RPC
success nor this requested flag proves the branch, receipt, or processing.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

SCRIPTS = (
    Path(__file__).resolve().parents[4] / "plugins" / "rolecasting" / "skills"
    / "delegating-cross-agent-work" / "scripts"
)
sys.path.insert(0, str(SCRIPTS))

from codex_capture import CaptureWriter
from codex_ipc_core import DEFAULTS, Refusal, bounded_bytes, encode, failure_record, print_result
from codex_ipc_transport import CliTransport, ReceiveFailure
from native_codex_mailbox import Mailbox, MailboxError, text
from peer_message import serialize_peer_message


def prepare(request, planned):
    required = {"message_id", "attempt_id", "actor", "recipient", "evidence_ref", "native", "capture"}
    if not isinstance(request, dict) or request.keys() != required:
        raise Refusal("invalid_request")
    for key in ("message_id", "attempt_id", "evidence_ref"):
        text(request[key], key)
    if request["attempt_id"] in {"initialize", "owner"}:
        raise Refusal("reserved-attempt-identity")
    if request["recipient"] != planned["recipient"]:
        raise Refusal("recipient_mismatch")
    native = request["native"]
    required = {"route", "nominationRef", "purpose", "authorityRefs", "holdRefs", "scope"}
    if (not isinstance(native, dict) or not required <= native.keys()
            or native.keys() - required - {"profile", "observationSeconds"}):
        raise Refusal("invalid_native_request")
    route = native["route"]
    if (not isinstance(route, dict) or route.keys() != {"endpoint", "host", "target"}
            or route["host"] != "local"):
        raise Refusal("explicit-local-route-required")
    text(route["endpoint"], "endpoint")
    text(route["target"], "target")
    if (route["host"] != planned["recipient"]["host_id"]
            or route["target"] != planned["recipient"]["thread_id"]):
        raise Refusal("native_recipient_mismatch")
    scope = native["scope"]
    if (not isinstance(scope, dict)
            or scope.keys() != {"send", "ownerAdmissionIntent", "holdsSatisfied"}
            or any(value is not True for value in scope.values())):
        raise Refusal("explicit-owner-admission-scope-required")
    text(native["nominationRef"], "nominationRef")
    text(native["purpose"], "purpose")
    if (native["authorityRefs"] != [planned["authority_ref"]]
            or native["holdRefs"] != planned["holds"]):
        raise Refusal("original-authority-or-holds-mismatch")
    message = {key: value for key, value in planned.items() if key not in {"state", "attempts"}}
    payload = serialize_peer_message(message, request["actor"])
    profile = native.get("profile", {})
    if not isinstance(profile, dict):
        raise Refusal("unsupported-limit-profile")
    limits = dict(DEFAULTS)
    for key, value in profile.items():
        if key not in DEFAULTS or type(value) is not int or not 1 <= value <= DEFAULTS[key]:
            raise Refusal("unsupported-limit-profile")
        limits[key] = value
    if limits["projectionBytes"] < 256:
        raise Refusal("projection-limit-below-minimum")
    wait = native.get("observationSeconds", 1)
    if type(wait) not in (int, float) or not 0 < wait <= 10:
        raise Refusal("unsupported-observation-wait")
    normalized = {
        **native, "payload": payload, "actor": request["actor"],
        "declaredOrigin": planned["sender"], "correlation": request["attempt_id"],
    }
    if len(encode(normalized)) > limits["caseBytes"]:
        raise Refusal("case-byte-limit")
    return normalized, limits, wait


def submit(native, limits, wait, writer, result):
    transport = CliTransport(native["route"]["endpoint"], limits, wait)
    binding = {
        "host": "local", "target": native["route"]["target"], "owner": None,
        "generation": transport.generation, "nominationRef": native["nominationRef"],
    }
    first_error = None
    capture_failures = []
    missing = {}
    submission_start = None

    def diagnose(error):
        nonlocal first_error
        first_error = first_error or failure_record(error)

    def capture(name, value):
        try:
            writer.write_json(writer.root / name, value)
        except (OSError, Refusal, ValueError, TypeError) as error:
            diagnose(error)
            capture_failures.append({"path": name, **failure_record(error)})
            missing[name] = "UNKNOWN"

    try:
        records = transport.send({
            "type": "request", "requestId": "initialize", "version": 0,
            "method": "initialize", "params": {"clientType": "cli"},
        })
        matches = [message for _, message in records
                   if message.get("type") == "response"
                   and message.get("requestId") == "initialize"
                   and message.get("method") == "initialize"
                   and message.get("resultType") == "success"]
        if len(matches) != 1:
            raise Refusal("initialize-unavailable")
        client = text(matches[0].get("result", {}).get("clientId"), "native-client")
        records = transport.send({
            "type": "request", "requestId": "owner", "sourceClientId": client,
            "version": 1, "method": "thread-owner-discovery",
            "params": {"hostId": "local", "conversationId": binding["target"]},
        })
        matches = [message for _, message in records
                   if message.get("type") == "response"
                   and message.get("requestId") == "owner"
                   and message.get("method") == "thread-owner-discovery"
                   and message.get("resultType") == "success"]
        if len(matches) != 1:
            raise Refusal("owner-unavailable")
        binding["owner"] = text(matches[0].get("handledByClientId"), "native-owner")
        if transport.receiver.incomplete is not None:
            raise Refusal("connection-incomplete-before-write")
        correlation = native["correlation"]
        envelope = {
            "type": "request", "requestId": correlation, "sourceClientId": client,
            "targetClientId": binding["owner"], "version": 2,
            "method": "thread-follower-start-turn",
            "params": {"conversationId": binding["target"], "turnStart": {
                "request": {"threadId": binding["target"], "clientUserMessageId": correlation,
                    "input": [{"type": "text", "text": native["payload"], "text_elements": []}]},
                "context": {"inheritThreadSettings": True, "useUserMessageAdmission": True}}},
        }
        if len(encode(envelope)) > limits["frameBytes"]:
            raise Refusal("outbound-frame-byte-limit")
        pending = {
            key: native[key] for key in (
                "payload", "correlation", "actor", "purpose", "authorityRefs", "holdRefs",
                "declaredOrigin", "nominationRef", "route", "scope",
            )
        }
        pending.update(
            pending=True, envelope=envelope, binding=binding,
            payloadSha256=hashlib.sha256(native["payload"].encode()).hexdigest(),
            profile=limits, native_branch="unknown", ordinary_start_fallback_possible=True,
        )
        transport.pending_path = writer.root / "attempt.json"
        # A failed create-only pending capture must prevent the input write.
        try:
            writer.write_json(transport.pending_path, pending)
        except (OSError, Refusal, ValueError, TypeError) as error:
            diagnose(error)
            capture_failures.append({"path": "attempt.json", **failure_record(error)})
            missing["attempt.json"] = "UNKNOWN"
            raise
        # Mark uncertainty before entering IO, including partial or failed writes.
        result["peer_input"] = "possible_submission"
        submission_start = len(transport.retained)
        transport.send(envelope)
        result["reason"] = "rpc-outcome-unknown"
    except (Refusal, ReceiveFailure, MailboxError, OSError, ValueError, KeyError, TypeError) as error:
        diagnose(error)
        result["reason"] = str(error)
    finally:
        try:
            transport.close()
        except OSError as error:
            diagnose(error)
        result["owned_connection"] = {
            "started": transport.stream is not None,
            "closed": transport.stream is not None and transport.closed,
        }

    submitted_records = transport.retained[submission_start:] if submission_start is not None else []
    original = [message for _, message in submitted_records
                if message.get("type") == "response"
                and message.get("requestId") == native["correlation"]]
    status = "unknown"
    if (len(original) == 1 and original[0].get("method") == "thread-follower-start-turn"
            and original[0].get("resultType") in {"success", "error"}):
        status = original[0]["resultType"]
    if result["reason"] == "rpc-outcome-unknown":
        result["reason"] = {
            "success": "rpc-success-effect-unconfirmed",
            "error": "rpc-error-effect-unknown",
        }.get(status, "rpc-outcome-unknown")
    projection = {
        "stage": "possible-submission" if result["peer_input"] == "possible_submission" else "refused-before-write",
        "reason": result["reason"], "receipt": "unknown", "native_branch": "unknown",
        "ordinary_start_fallback_possible": True, "evidence": [],
        "limits": ["cooperative-source-prototype", "rpc-is-not-admission-or-receipt",
                   "native-branch-unobserved", "processing-unobserved"],
    }
    if len(encode(projection)) > limits["projectionBytes"]:
        projection = {
            "stage": projection["stage"], "reason": "projection-limit",
            "receipt": "unknown", "native_branch": "unknown",
            "ordinary_start_fallback_possible": True, "evidence": [],
        }
    result["projection"] = projection
    capture("rpc.json", {
        "originalResult": original, "status": status,
        "terminalReason": transport.receive_status[-1] if transport.receive_status else None,
    })
    capture("received.json", transport.retained)
    capture("outbound.json", transport.outbound)
    capture("projection.json", projection)
    capture("normalized-input.json", native)
    capture("acquisition.json", {
        "incomingBytes": transport.acquired, "events": transport.events,
        "effectiveLimits": limits, "receiveStatus": transport.receive_status,
        "connectionGeneration": transport.generation,
        "rejectedFrame": transport.receiver.rejected_frame,
        "rawInputLocation": None, "rawInputStatus": "caller-owned-location-unavailable",
        "captureWrites": list(writer.observations),
    })
    result["firstDiagnostic"] = first_error
    if capture_failures:
        result["capture_failure"] = {
            "originalFailure": first_error, "captureFailures": capture_failures,
            "missingEvidence": missing,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", required=True)
    parser.add_argument("--request", required=True)
    arguments = parser.parse_args()
    result = {
        "claimed": False, "peer_input": "not_attempted", "reason": "invalid_request",
        "receipt": "unknown", "native_branch": "unknown",
        "ordinary_start_fallback_possible": True,
        "owned_connection": {"started": False, "closed": False},
    }
    mailbox = None
    try:
        request = json.loads(bounded_bytes(Path(arguments.request), "request-byte-limit").decode("utf-8"))
        if not isinstance(request, dict):
            raise Refusal("invalid_request")
        mailbox = Mailbox(arguments.store)
        planned = mailbox.get(request["message_id"])
        native, limits, wait = prepare(request, planned)
        writer = CaptureWriter(request["capture"])
        claim = mailbox.claim(request["message_id"], request["attempt_id"], request["actor"])
        result["claimed"] = claim["claimed"] is True
        if not result["claimed"]:
            result["reason"] = "claim_not_acquired"
        else:
            # Durable uncertainty precedes acquisition and any native input write.
            mailbox.observe(request["message_id"], request["attempt_id"], "unknown",
                            request["evidence_ref"], json.dumps(native, sort_keys=True))
            submit(native, limits, wait, writer, result)
    except (Refusal, ReceiveFailure, MailboxError, OSError, sqlite3.Error,
            UnicodeError, ValueError, KeyError, TypeError) as error:
        result["reason"] = str(error)
    finally:
        if mailbox is not None:
            mailbox.close()
    return print_result(result)


if __name__ == "__main__":
    sys.exit(main())
