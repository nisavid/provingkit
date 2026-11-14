#!/usr/bin/env python3
"""Submit one local owner-admission prototype request from a planned mailbox.

Trusted caller records are cooperative declarations, not permission enforcement.
The owner may use native admission or ordinary turn/start fallback. Neither RPC
success nor this requested flag proves the branch, receipt, or processing.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import sys
import time

from codex_capture import CaptureWriter
from codex_ipc_core import DEFAULTS, Refusal, bounded_bytes, encode, failure_record, print_result
from codex_ipc_transport import CliTransport, ReceiveFailure, discover_owner
from native_codex_mailbox import Mailbox, MailboxError, text
from peer_message import serialize_peer_message


def _validate_v2_nomination(record, specification, request, planned, consumed_milliseconds):
    required = {
        "schema", "status", "route", "recipient", "producer", "submitter", "operationId",
        "acceptor", "expectedInvocation", "permissions", "acquisitionHolds", "freshness",
        "acquisition", "privacy", "retirement",
    }
    if not isinstance(record, dict) or record.keys() != required:
        raise Refusal("invalid-nomination-record")
    route = record["route"]
    if (record["schema"] != "codex-route-nomination-v2"
            or record["status"] != "provisional"
            or not isinstance(route, dict)
            or route.keys() != {"endpoint", "host", "target"}
            or route["host"] != "local"
            or record["recipient"] != planned["recipient"]
            or record["producer"] != record["recipient"]
            or record["submitter"] != request["actor"]
            or route["host"] != planned["recipient"]["host_id"]
            or route["target"] != planned["recipient"]["thread_id"]
            or not isinstance(record["operationId"], str)
            or not record["operationId"]
            or not isinstance(record["acquisitionHolds"], list)
            or any(not isinstance(item, str) or not item
                   for item in record["acquisitionHolds"])
            or len(set(record["acquisitionHolds"])) != len(record["acquisitionHolds"])):
        raise Refusal("nomination-binding-mismatch")
    text(route["endpoint"], "endpoint")
    permission_keys = {
        "evidenceRef", "issuer", "actor", "act", "chat", "operationId",
        "validityRef", "revocationRef", "consumer",
    }
    permission_shapes = {
        "metadata": (record["producer"], "acquire-route-metadata", "nomination-controller"),
        "nomination": (record["producer"], "publish-route-nomination", "codex-route-nomination"),
        "routeUse": (record["submitter"], "consume-route-nomination", "owner-admission-sender"),
    }
    permissions = record["permissions"]
    if (not isinstance(permissions, dict)
            or permissions.keys() != {"metadata", "nomination", "routeUse"}):
        raise Refusal("nomination-authority-binding-mismatch")
    for name, value in permissions.items():
        actor, act, consumer = permission_shapes[name]
        if (not isinstance(value, dict) or value.keys() != permission_keys
                or value["actor"] != actor or value["chat"] != planned["recipient"]
                or value["operationId"] != record["operationId"]
                or (value["act"], value["consumer"]) != (act, consumer)
                or not isinstance(value["issuer"], dict)
                or value["issuer"].keys() != {"thread_id", "host_id"}
                or any(not isinstance(item, str) or not item for item in value["issuer"].values())
                or any(not isinstance(value[key], str) or not value[key]
                       for key in ("evidenceRef", "validityRef", "revocationRef"))):
            raise Refusal("nomination-authority-binding-mismatch")
    freshness = record["freshness"]
    if (not isinstance(freshness, dict)
            or freshness.keys() != {"observedAtMilliseconds"}
            or type(freshness["observedAtMilliseconds"]) is not int
            or freshness["observedAtMilliseconds"] < 0
            or type(consumed_milliseconds) is not int
            or consumed_milliseconds < freshness["observedAtMilliseconds"]):
        raise Refusal("invalid-nomination-observation-time")
    acquisition = record["acquisition"]
    acquisition_keys = {
        "startedMilliseconds", "finishedMilliseconds", "descriptorEntries", "unixRows",
        "unixBytes", "descriptorLinkBytes", "selectedDescriptor", "socketInode",
        "launchSourceRef", "listenerSourceRef",
    }
    if (not isinstance(acquisition, dict) or acquisition.keys() != acquisition_keys
            or acquisition["finishedMilliseconds"] != freshness["observedAtMilliseconds"]
            or any(type(acquisition[key]) is not int or acquisition[key] < 0 for key in (
                "startedMilliseconds", "finishedMilliseconds", "descriptorEntries", "unixRows",
                "unixBytes", "descriptorLinkBytes", "selectedDescriptor", "socketInode",
            ))
            or acquisition["finishedMilliseconds"] - acquisition["startedMilliseconds"] > 5000
            or acquisition["descriptorEntries"] > 1024
            or acquisition["unixRows"] > 4096
            or acquisition["unixBytes"] > 524288
            or acquisition["descriptorLinkBytes"] > 262144
            or not all(isinstance(acquisition[key], str) and acquisition[key]
                       for key in ("launchSourceRef", "listenerSourceRef"))):
        raise Refusal("invalid-nomination-acquisition")
    expected = record["expectedInvocation"]
    actual = specification["invocation"]
    expected_keys = {
        "control", "taskRef", "attemptId", "chat", "command", "workingDirectory", "helper",
    }
    actual_keys = expected_keys | {"evidenceRef", "nativeItemId", "status", "exitCode"}
    if (not isinstance(expected, dict) or expected.keys() != expected_keys
            or not isinstance(actual, dict) or actual.keys() != actual_keys
            or any(actual[key] != expected[key] for key in expected_keys)
            or actual["control"] != "native-read-thread-command-execution"
            or actual["chat"] != planned["recipient"]
            or actual["status"] != "completed" or actual["exitCode"] != 0
            or any(not isinstance(actual[key], str) or not actual[key]
                   for key in ("evidenceRef", "nativeItemId"))):
        raise Refusal("native-invocation-binding-mismatch")
    if record["privacy"] != {"boundary": "unix-account-private", "sameUidIsolation": False,
                             "pathIsAuthority": False}:
        raise Refusal("unsupported-nomination-privacy-boundary")
    if record["retirement"] != {"scope": "original-invocation-staging-only"}:
        raise Refusal("unsupported-nomination-retirement")
    return route, actual


def _load_guarded_nomination(specification, request, planned, effective_uid, clock):
    if (not isinstance(specification, dict)
            or specification.keys() != {"path", "sha256", "size", "invocation"}):
        raise Refusal("invalid-nomination-reference")
    path = Path(specification["path"])
    digest = specification["sha256"]
    size = specification["size"]
    if (not path.is_absolute() or type(size) is not int or not 0 < size <= 4096
            or not isinstance(digest, str) or len(digest) != 64
            or digest != digest.lower() or any(c not in "0123456789abcdef" for c in digest)):
        raise Refusal("invalid-nomination-reference")
    try:
        before = path.lstat()
        parent = path.parent.lstat()
        if (stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode)
                or stat.S_IMODE(before.st_mode) != 0o600 or before.st_uid != effective_uid
                or stat.S_ISLNK(parent.st_mode) or not stat.S_ISDIR(parent.st_mode)
                or stat.S_IMODE(parent.st_mode) != 0o700 or parent.st_uid != effective_uid):
            raise Refusal("unsafe-nomination-custody")
        with path.open("rb") as source:
            data = source.read(4097)
        after = path.lstat()
    except OSError as error:
        raise Refusal("nomination-unavailable") from error
    stable = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    if stable != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise Refusal("nomination-changed-during-read")
    if (len(data) != size or before.st_size != size
            or hashlib.sha256(data).hexdigest() != digest):
        raise Refusal("nomination-identity-mismatch")
    try:
        record = json.loads(data)
    except (UnicodeError, ValueError, RecursionError) as error:
        raise Refusal("invalid-nomination-record") from error
    consumed_milliseconds = clock()
    route, invocation = _validate_v2_nomination(
        record, specification, request, planned, consumed_milliseconds,
    )
    acceptor = record["acceptor"]
    expected_peer_keys = {
        "pid", "uid", "gid", "startTicks", "bootId", "networkNamespace", "executable",
    }
    if (not isinstance(acceptor, dict) or acceptor.keys() != expected_peer_keys
            or type(acceptor["pid"]) is not int or acceptor["pid"] <= 0
            or any(type(acceptor[key]) is not int or acceptor[key] < 0
                   for key in ("uid", "gid", "startTicks"))
            or not isinstance(acceptor["bootId"], str) or not acceptor["bootId"]
            or not isinstance(acceptor["networkNamespace"], str)
            or not acceptor["networkNamespace"]
            or not isinstance(acceptor["executable"], dict)
            or acceptor["executable"].keys() != {"path", "device", "inode"}
            or not isinstance(acceptor["executable"]["path"], str)
            or not Path(acceptor["executable"]["path"]).is_absolute()
            or any(type(acceptor["executable"][key]) is not int
                   or acceptor["executable"][key] < 0 for key in ("device", "inode"))):
        raise Refusal("invalid-nominated-acceptor")
    return record, {
        "path": str(path), "sha256": digest, "size": size,
        "invocationEvidenceRef": invocation["evidenceRef"],
        "nativeItemId": invocation["nativeItemId"],
        "consumedAtMilliseconds": consumed_milliseconds,
    }
def prepare(request, planned, effective_uid=None, clock=None):
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
    common = {"purpose", "authorityRefs", "holdRefs", "scope"}
    if not isinstance(native, dict) or not common <= native.keys():
        raise Refusal("invalid_native_request")
    optional = {"profile", "observationSeconds"}
    legacy = {"route", "nominationRef"}
    guarded = {"nomination"}
    branch = native.keys() - common - optional
    if branch == legacy:
        route = native["route"]
        nomination_ref = native["nominationRef"]
        guard = None
    elif branch == guarded:
        record, nomination_identity = _load_guarded_nomination(
            native["nomination"], request, planned,
            os.geteuid() if effective_uid is None else effective_uid,
            (lambda: time.monotonic_ns() // 1_000_000) if clock is None else clock,
        )
        route = record["route"]
        nomination_ref = "sha256:" + nomination_identity["sha256"]
        guard = {"expectedPeer": record["acceptor"], "nomination": nomination_identity}
    else:
        raise Refusal("invalid_native_request")
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
    text(nomination_ref, "nominationRef")
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
        **{key: value for key, value in native.items() if key != "nomination"},
        "route": route, "nominationRef": nomination_ref,
        "payload": payload, "actor": request["actor"],
        "declaredOrigin": planned["sender"], "correlation": request["attempt_id"],
    }
    if guard is not None:
        normalized["guardedNomination"] = guard["nomination"]
    if len(encode(normalized)) > limits["caseBytes"]:
        raise Refusal("case-byte-limit")
    return normalized, limits, wait, guard


def submit(native, limits, wait, writer, result, guard=None):
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
        if guard is not None:
            if transport.connected_peer_identity() != guard["expectedPeer"]:
                raise Refusal("connected-peer-mismatch")
            binding["peerIdentity"] = guard["expectedPeer"]
        client = discover_owner(transport, binding, text=text, refusal=Refusal)
        if (guard is not None
                and transport.connected_peer_identity() != guard["expectedPeer"]):
            raise Refusal("connected-peer-changed-before-message")
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

    nondelivery = None
    if (not transport.write_boundary
            and (transport.stream is None or transport.closed)):
        nondelivery = {
            "claim": "message-frame-write-boundary-not-entered",
            "reason": result["reason"],
            "writeBoundary": dict(transport.write_boundary),
            "ownedConnection": dict(result["owned_connection"]),
        }

    submitted_records = transport.retained[submission_start:] if submission_start is not None else []
    original = [message for _, message in submitted_records
                if message.get("type") == "response"
                and message.get("requestId") == native["correlation"]]
    status = "unknown"
    if (len(original) == 1 and original[0].get("method") == "thread-follower-start-turn"
            and isinstance(original[0].get("resultType"), str)
            and original[0]["resultType"] in {"success", "error"}):
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
    return nondelivery


def main(argv=None, *, effective_uid=None, clock=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", required=True)
    parser.add_argument("--request", required=True)
    arguments = parser.parse_args(argv)
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
        native, limits, wait, guard = prepare(request, planned, effective_uid, clock)
        writer = CaptureWriter(request["capture"])
        claim = mailbox.claim(request["message_id"], request["attempt_id"], request["actor"])
        result["claimed"] = claim["claimed"] is True
        if not result["claimed"]:
            result["reason"] = "claim_not_acquired"
        else:
            # Durable uncertainty precedes acquisition and any native input write.
            mailbox.observe(request["message_id"], request["attempt_id"], "unknown",
                            request["evidence_ref"], json.dumps(native, sort_keys=True))
            nondelivery = submit(native, limits, wait, writer, result, guard)
            if nondelivery is not None:
                bookkeeping = {
                    "kind": "not_delivered", "evidence_ref": request["evidence_ref"],
                    "observation": nondelivery,
                }
                try:
                    mailbox.observe(
                        request["message_id"], request["attempt_id"], "not_delivered",
                        request["evidence_ref"],
                        json.dumps(nondelivery, ensure_ascii=True, sort_keys=True,
                                   separators=(",", ":")),
                    )
                    bookkeeping["status"] = "retained"
                except (MailboxError, OSError, sqlite3.Error, ValueError, TypeError) as error:
                    bookkeeping["status"] = "failed"
                    bookkeeping["failure"] = failure_record(error)
                result["conclusive_bookkeeping"] = bookkeeping
    except (Refusal, ReceiveFailure, MailboxError, OSError, sqlite3.Error,
            UnicodeError, ValueError, KeyError, TypeError) as error:
        result["reason"] = str(error)
    finally:
        if mailbox is not None:
            mailbox.close()
    return print_result(result)


if __name__ == "__main__":
    sys.exit(main())
