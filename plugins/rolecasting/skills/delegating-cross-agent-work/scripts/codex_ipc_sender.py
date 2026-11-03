#!/usr/bin/env python3
"""Forward one mailbox envelope to a nominated, loaded, busy Codex IPC peer.

Public output reports claimed, peer_input, reason, projection, and the actual
owned connection lifecycle. Only a correlated native receipt yields received;
RPC success alone remains possible_submission. This is cooperative source
behavior, with no current-app compatibility or live authority claim.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

from native_codex_mailbox import Mailbox, MailboxError
from peer_message import serialize_peer_message
from codex_capture import CaptureWriter
from codex_ipc_core import DEFAULTS, ArtifactFailure, Refusal, run_sender
from codex_ipc_transport import ReceiveFailure


def native_request(request, planned):
    if request.keys() != {"message_id", "attempt_id", "actor", "recipient", "evidence_ref", "native", "capture"}:
        raise Refusal("invalid_request")
    native = request["native"]
    required = {"route", "nominationRef", "purpose", "authorityRefs", "holdRefs", "scope"}
    if (not isinstance(native, dict) or not required <= native.keys()
            or native.keys() - required - {"profile", "observationSeconds"}):
        raise Refusal("invalid_native_request")
    route = native["route"]
    if (route["host"] != planned["recipient"]["host_id"]
            or route["target"] != planned["recipient"]["thread_id"]):
        raise Refusal("native_recipient_mismatch")
    if native["scope"].get("busyOnly") is not True:
        raise Refusal("busy-only-required")
    message = {k: v for k, v in planned.items() if k not in {"state", "attempts"}}
    return {
        **native, "payload": serialize_peer_message(message, request["actor"]),
        "actor": request["actor"], "declaredOrigin": planned["sender"],
        # A native receipt identifies this immutable attempt, not the exchange.
        "correlation": request["attempt_id"],
    }


def bounded_bytes(path, reason):
    ceiling = DEFAULTS["caseBytes"]
    with path.open("rb") as source:
        data = source.read(ceiling + 1)
    if len(data) > ceiling:
        raise Refusal(reason)
    return data


def compact_original(path):
    data = bounded_bytes(path, "original-source-profile-gap")
    return json.loads(data), hashlib.sha256(data).hexdigest()


def reconcile(request, planned, native, original_path, result):
    attempts = [a for a in planned["attempts"] if a["attempt_id"] == request["attempt_id"]]
    if len(attempts) == 1:
        result["peer_input"] = "unknown"
    original, attempt_hash = compact_original(original_path)
    try:
        rpc, rpc_hash = compact_original(original_path.with_name("rpc.json"))
    except FileNotFoundError as error:
        raise Refusal("original-rpc-unavailable") from error
    message = {k: v for k, v in planned.items() if k not in {"state", "attempts"}}
    if (len(attempts) != 1 or original["correlation"] != request["attempt_id"]
            or original["actor"] != attempts[0]["actor"]
            or original["binding"]["host"] != planned["recipient"]["host_id"]
            or original["binding"]["target"] != planned["recipient"]["thread_id"]
            or original["declaredOrigin"] != planned["sender"]
            or original["payload"] != serialize_peer_message(message, original["actor"])):
        raise Refusal("original-attempt-mismatch")
    if native["scope"].get("send") is not False or native["scope"].get("acquireLoaded") is not True:
        raise Refusal("read-only-reconciliation-scope-required")
    result["original"] = {"correlation": original["correlation"], "actor": original["actor"],
                          "attempt_sha256": attempt_hash, "rpc_sha256": rpc_hash,
                          "rpc_status": rpc["status"]}
    result["reader_actor"] = request["actor"]
    result["peer_input"] = "unknown"
    # The immutable attempt carries the original payload and authority records.
    # The current nomination and read-only scope belong to this invocation.
    native.update(payload=original["payload"], declaredOrigin=original["declaredOrigin"],
                  correlation=original["correlation"])
    saved_path = original_path.with_name("projection.json")
    if saved_path.exists():
        saved, _ = compact_original(saved_path)
        for item in saved.get("evidence", []):
            observation = item.get("observation", {})
            if (item.get("stage") == "receipt" and item.get("source") == "native-server-linked-message"
                    and item.get("serverUserMessageId")
                    and observation.get("source") == original["binding"]["owner"]
                    and observation.get("generation") == original["binding"]["generation"]
                    and observation.get("correlation") == original["correlation"]
                    and observation.get("host") == original["binding"]["host"]
                    and observation.get("target") == original["binding"]["target"]):
                project(result, {"projection": saved, "writeBoundary": False,
                                 "owned_connection": {"started": False, "closed": False}})
                return None
    writer = CaptureWriter(request["capture"])
    return run_sender(native, writer.root, writer=writer, mode="reconcile", attempt_path=original_path)


def project(result, native):
    result["projection"] = native["projection"]
    result["owned_connection"] = native["owned_connection"]
    result["reason"] = native["projection"]["reason"]
    evidence = native["projection"].get("evidence", [])
    if any(item["stage"] == "receipt" for item in evidence):
        result["peer_input"] = "received"
    elif native["writeBoundary"]:
        result["peer_input"] = "possible_submission"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", required=True)
    parser.add_argument("--request", required=True, help="explicit trusted local UTF-8 JSON request file path")
    parser.add_argument("--mode", choices=("submit", "reconcile"), default="submit")
    parser.add_argument("--original-attempt", type=Path)
    arguments = parser.parse_args()
    result = {
        "claimed": False, "peer_input": "not_attempted",
        "reason": "invalid_request",
        "owned_connection": {"started": False, "closed": False},
    }
    mailbox = None
    try:
        if (arguments.mode == "reconcile") != (arguments.original_attempt is not None):
            raise Refusal("original-attempt-mode-mismatch")
        request_bytes = bounded_bytes(Path(arguments.request), "request-byte-limit")
        request = json.loads(request_bytes.decode("utf-8"))
        mailbox = Mailbox(arguments.store)
        planned = mailbox.get(request["message_id"])
        if planned["recipient"] != request["recipient"]:
            result["reason"] = "recipient_mismatch"
        else:
            native = native_request(request, planned)
            if arguments.mode == "reconcile":
                try:
                    outcome = reconcile(request, planned, native, arguments.original_attempt, result)
                except ArtifactFailure as error:
                    project(result, error.result)
                    result["capture_failure"] = error.failure
                    raise
                if outcome is not None:
                    project(result, outcome)
                if result["peer_input"] == "received":
                    mailbox.observe(request["message_id"], request["attempt_id"], "received",
                                    request["evidence_ref"], json.dumps(result["projection"], sort_keys=True))
                return print_result(result)
            writer = CaptureWriter(request["capture"])
            claim = mailbox.claim(request["message_id"], request["attempt_id"], request["actor"])
            result["claimed"] = claim["claimed"] is True
            if not result["claimed"]:
                result["reason"] = "claim_not_acquired"
            else:
                # Bind uncertainty before acquisition or any native write.
                mailbox.observe(request["message_id"], request["attempt_id"], "unknown",
                                request["evidence_ref"], json.dumps(native, sort_keys=True))
                try:
                    outcome = run_sender(native, writer.root, writer=writer)
                except ArtifactFailure as error:
                    project(result, error.result)
                    result["capture_failure"] = error.failure
                    raise
                project(result, outcome)
                if result["peer_input"] == "received":
                    mailbox.observe(request["message_id"], request["attempt_id"], "received",
                                    request["evidence_ref"], json.dumps(outcome["projection"], sort_keys=True))
    except ArtifactFailure:
        pass  # Preserve the operation's original outcome and capture failures.
    except (Refusal, ReceiveFailure) as error:
        result["reason"] = str(error)
    except sqlite3.Error:
        result["reason"] = "mailbox_unavailable"
    except MailboxError:
        result["reason"] = "mailbox_error"
    except (OSError, UnicodeError, ValueError, KeyError, TypeError):
        result["reason"] = "invalid_request"
    finally:
        if mailbox is not None:
            mailbox.close()
    return print_result(result)


def print_result(result):
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
