#!/usr/bin/env python3
"""Retain caller-owned bootstrap and submit one explicitly selected Daybreak task."""

import argparse
import hashlib
import json
import os
import re
import sqlite3
import stat
import subprocess
import uuid
from pathlib import Path
import sys

from codex_capture import CaptureWriter, StorageRefusal, TERMINAL
from codex_ipc_transport import CliTransport, ReceivePrefixFailure, discover_owner
from native_codex_mailbox import Mailbox, text as mailbox_text
from peer_message import serialize_peer_message


CREATE = {
    "tool": "mcp__codex_app__create_thread",
    "arguments": {
        "model": "gpt-6-sol",
        "target": {"type": "projectless"},
        "prompt": "Reply with Ready. Do not use tools or begin any other work.",
    },
}


ALLOWED_SUBMISSION_KEYS = {
    "operation_id", "message_id", "attempt_id", "correlation_id", "sender",
    "actor", "owner", "authority_ref", "holds", "payload", "endpoint",
    "mailbox", "capture", "observation_seconds", "resource_admission",
}

def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--root", required=True, help="private operation capture root")
    result.add_argument("--standing-binding", help="trusted host-local standing admission binding")
    result.add_argument("--standing-eligible", action="store_true")
    result.add_argument("--standing-paused", action="store_true")
    result.add_argument("--standing-independent-hold", action="store_true")
    phases = result.add_subparsers(dest="phase", required=True)
    for name in ("prepare", "continue"):
        phase = phases.add_parser(name)
        phase.add_argument("--input", required=True)
    for name in ("bind", "submit", "reconcile", "show"):
        phase = phases.add_parser(name)
        phase.add_argument("operation_id")
        if name != "show":
            phase.add_argument("--input", required=name == "bind")
    return result


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def identity(value):
    return (isinstance(value, dict)
            and value.keys() == {"thread_id", "host_id"}
            and all(text(item) for item in value.values()))


def creation_outcome(value):
    """Classify caller-declared negative creation evidence without interpreting it."""
    if "creation" not in value:
        require(not (isinstance(value.get("result"), dict)
                     and value["result"].get("isError")), "native-creation-error")
        return None
    observation = value["creation"]
    require(isinstance(observation, dict)
            and observation.keys() == {"state", "evidence_ref"}
            and observation["state"] in {"failed", "unknown"}
            and text(observation["evidence_ref"]), "invalid-creation-observation")
    return observation


def read_json(path):
    return json.loads(path.read_bytes())


def capture(root, records, writer=None):
    # Admit exactly this invocation's proposed bytes through the existing writer.
    writer = writer or CaptureWriter({
        "run_root": str(root),
        "allowance_bytes": TERMINAL + sum(len(data) for _, data in records),
        "terminal_provision_bytes": TERMINAL,
        "later_forecast_bytes": 0,
    })
    for path, data in records:
        writer.require(path)
        if path.exists():
            require(path.read_bytes() == data, "capture-conflict")
        else:
            writer.write(path, data)


def observation_call(child):
    return {
        "tool": "mcp__codex_app__read_thread",
        "arguments": {
            "threadId": child["thread_id"],
            "hostId": child["host_id"],
            "turnLimit": 1,
            "includeOutputs": False,
            "maxOutputCharsPerItem": 2048,
        },
    }



def task_wait_path(directory, after_ref):
    if after_ref is None:
        return directory / "task-wait.json"
    digest = hashlib.sha256(after_ref.encode("utf-8")).hexdigest()
    return directory / ("task-wait-" + digest + ".json")


def task_observation_path(directory, wait_ref):
    digest = hashlib.sha256(wait_ref.encode("utf-8")).hexdigest()
    return directory / ("task-observation-" + digest + ".json")


def validate_task_wait(value):
    require(isinstance(value, dict)
            and value.keys() == {"observation_seconds", "after_ref"},
            "invalid-task-wait")
    seconds = value["observation_seconds"]
    require(type(seconds) in (int, float) and 0 < seconds <= 10,
            "invalid-observation-seconds")
    require(value["after_ref"] is None or text(value["after_ref"]),
            "invalid-task-after-ref")


def validate_task_observation(value, wait_ref, wait):
    require(isinstance(value, dict)
            and value.keys() == {"task_wait_ref", "call", "result", "task"},
            "invalid-task-observation")
    require(value["task_wait_ref"] == wait_ref, "task-wait-ref-conflict")
    require(value["call"] == wait["call"], "task-call-conflict")
    task = value["task"]
    require(isinstance(task, dict)
            and task.keys() == {"attempt_id", "turn_id", "state", "evidence_ref"},
            "invalid-task-observation")
    require(task["attempt_id"] == wait["refs"]["attempt_id"], "task-attempt-conflict")
    require(task["turn_id"] == wait["turn_id"], "task-turn-conflict")
    require(task["state"] in {"pending", "completed", "failed", "unknown"}
            and text(task["evidence_ref"]), "invalid-task-observation")

    require(not (isinstance(value["result"], dict) and value["result"].get("isError"))
            or task["state"] == "unknown", "native-observation-error")


def task_observations(directory, result):
    """Follow only this operation's create-only request/observation chain."""
    guard = CaptureWriter({
        "run_root": str(directory.parent),
        "allowance_bytes": TERMINAL + 1,
        "terminal_provision_bytes": TERMINAL,
        "later_forecast_bytes": 0,
    })
    records = []
    after_ref = None
    evidence_refs = set()
    accepted = result["status"] == "turn_accepted" and text(result.get("turn_id"))
    recovering = (
        result["status"] == "submission_unknown"
        and (directory / "claim.json").is_file()
    )
    bound_turn = result.get("turn_id")
    while True:
        wait_path = task_wait_path(directory, after_ref)
        guard.require(wait_path)
        if not wait_path.exists():
            return records
        require(accepted or recovering, "task-turn-not-accepted")
        wait = read_json(wait_path)
        require(isinstance(wait, dict)
                and wait.keys() == {"task_wait", "refs", "turn_id", "call"},
                "invalid-retained-task-wait")
        validate_task_wait(wait["task_wait"])
        require(wait["task_wait"]["after_ref"] == after_ref, "task-after-ref-conflict")
        require(wait["refs"] == {key: result["refs"][key] for key in
                                ("operation_id", "message_id", "attempt_id")}
                and text(wait["turn_id"])
                and (bound_turn is None or wait["turn_id"] == bound_turn), "task-binding-conflict")
        require(wait["call"] == observation_call(result["child"]), "task-call-conflict")
        # A wait binds its chain's turn without proving task acceptance.
        bound_turn = wait["turn_id"]
        observation_path = task_observation_path(directory, str(wait_path))
        guard.require(observation_path)
        observation = None
        if observation_path.exists():
            observation = read_json(observation_path)
            validate_task_observation(observation, str(wait_path), wait)
            evidence_ref = observation["task"]["evidence_ref"]
            require(evidence_ref not in evidence_refs, "task-evidence-not-fresh")
            evidence_refs.add(evidence_ref)
        records.append((wait_path, wait, observation_path, observation))
        if observation is None or observation["task"]["state"] in {"completed", "failed"}:
            return records
        after_ref = str(observation_path)


def bound_standing_attempt(directory, result):
    raw, attempt = read_private_capture(directory / "attempt.json", include_bytes=True)
    envelope = attempt["envelope"]
    params = envelope["params"]
    request = params["turnStart"]["request"]
    require(envelope["method"] == "thread-follower-start-turn"
            and params["conversationId"] == request["threadId"] == result["child"]["thread_id"]
            and request["clientUserMessageId"] == result["refs"]["attempt_id"]
            and text(envelope["requestId"])
            and attempt["correlation"] == envelope["requestId"]
            and all(attempt["refs"][key] == result["refs"][key]
                    for key in ("operation_id", "message_id", "attempt_id", "operation_ref")),
            "task-attempt-conflict")
    return envelope, hashlib.sha256(raw).hexdigest()


def retained_accepted_turn(directory, result, standing, bound_attempt):
    capture = read_private_capture(directory / "start-response.json")
    if standing:
        require(bound_attempt is not None, "task-attempt-conflict")
        envelope, _ = bound_attempt
    else:
        envelope = read_private_capture(directory / "attempt.json")["envelope"]
    method = "thread-follower-start-turn"
    require(capture["envelope"] == envelope and envelope["method"] == method
            and envelope["params"]["conversationId"] == result["child"]["thread_id"]
            and envelope["params"]["turnStart"]["request"]["clientUserMessageId"]
            == result["refs"]["attempt_id"], "invalid-start-response")
    matches = [
        item for _, item in capture["records"]
        if item.get("type") == "response"
        and item.get("requestId") == envelope["requestId"]
        and item.get("method") == method
        and item.get("handledByClientId") == envelope["targetClientId"]
    ]
    require(len(matches) == 1 and matches[0]["resultType"] == "success",
            "invalid-start-response")
    turn_id = matches[0]["result"]["result"]["turn"]["id"]
    require(text(turn_id), "invalid-start-response")
    return turn_id


def retained_task_write_attempt(directory, bound_attempt):
    """Test for evidence written after the standing callback returned."""
    if bound_attempt is None:
        return False
    envelope, attempt_digest = bound_attempt
    try:
        response = read_private_capture(directory / "start-response.json")
    except (OSError, ValueError, RecursionError):
        response = None
    if (isinstance(response, dict) and response.get("envelope") == envelope
            and isinstance(response.get("records"), list)):
        return True
    try:
        transport = read_private_capture(directory / "transport.json")
    except (OSError, ValueError, RecursionError):
        return False
    return (isinstance(transport, dict) and isinstance(transport.get("outbound"), list)
            and envelope in transport["outbound"]
            and transport.get("writeBoundary") == {
                "pendingExistedBeforeWrite": True,
                "pendingSha256": attempt_digest,
            })


def retained_submission_fields(directory, record, result, standing, bound_attempt,
                               write_attempted, *, claim):
    fields = (
        "status", "ipc", "saved_selection", "receipt", "task_completion",
        "effective_program", "owned_connection",
    )
    require(isinstance(record, dict) and isinstance(record.get("refs"), dict)
            and record.get("child") == result["child"]
            and record.get("native_call") is None
            and all(key in record for key in fields)
            and all(record["refs"].get(key) == result["refs"][key]
                    for key in ("operation_id", "message_id", "attempt_id", "operation_ref")),
            "invalid-retained-result")
    connection = record["owned_connection"]
    require(isinstance(connection, dict) and connection.keys() == {"started", "closed"}
            and all(value is None or type(value) is bool for value in connection.values())
            and (record["saved_selection"] is None or record["saved_selection"] is True)
            and all(record[key] == "unknown" for key in ("receipt", "task_completion", "effective_program")),
            "invalid-retained-result")
    status = record["status"]
    ipc = record["ipc"]
    task_write = record.get("task_write")
    turn_id = record.get("turn_id")
    require(ipc in ("unknown", "attempted", "not_attempted")
            and (task_write in ("unknown", "attempted", "not_attempted") if standing
                 else "task_write" not in record), "invalid-retained-result")
    if status == "turn_accepted":
        require(not claim and text(turn_id) and ipc == "attempted"
                and record["saved_selection"] is True
                and (not standing or task_write == "attempted")
                and turn_id == retained_accepted_turn(directory, result, standing, bound_attempt),
                "invalid-retained-result")
    else:
        require(status == "submission_unknown" and turn_id is None
                and (not claim or ipc == "unknown")
                and (not standing or task_write != "attempted" or ipc == "attempted"),
                "invalid-retained-result")
        if not claim:
            try:
                accepted_turn = retained_accepted_turn(directory, result, standing, bound_attempt)
            except (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError):
                accepted_turn = None
            require(accepted_turn is None, "invalid-retained-result")
    projection = {key: record[key] for key in fields}
    if standing:
        require(task_write != "not_attempted" or not write_attempted,
                "invalid-retained-result")
        # Positive write state is projected from the bound frame evidence below.
        projection["task_write"] = "not_attempted" if task_write == "not_attempted" else "unknown"
    if turn_id is not None:
        projection["turn_id"] = turn_id
    if "reason" in record:
        require(text(record["reason"]), "invalid-retained-result")
        projection["reason"] = record["reason"]
    if "failures" in record:
        failures = record["failures"]
        require(isinstance(failures, list)
                and all(isinstance(item, dict) and item.keys() == {"stage", "reason"}
                        and all(text(value) for value in item.values()) for item in failures),
                "invalid-retained-result")
        projection["failures"] = failures
    return projection


def retained(directory):
    intent = read_json(directory / "intent.json")
    result = {
        "refs": {key: intent[key] for key in
                 ("operation_id", "message_id", "attempt_id")},
        "child": None,
        "status": "creation_unobserved",
        "native_call": None,
        "ipc": "not_attempted",
    }
    result["refs"]["operation_ref"] = str(directory / "intent.json")
    if (directory / "continuation.json").exists():
        continuation = read_json(directory / "continuation.json")
        result["child"] = continuation["child"]
        result["status"] = "bootstrap_completed"
        result["refs"]["continuation_ref"] = str(directory / "continuation.json")
    if (directory / "bind.json").exists():
        receipt = read_json(directory / "bind.json")
        if receipt.get("creation") is not None:
            result["status"] = "creation_" + receipt["creation"]["state"]
            result["refs"]["creation_ref"] = str(directory / "bind.json")
            result["child"] = receipt.get("child")
            if "client_thread_id" in receipt:
                result["client_thread_id"] = receipt["client_thread_id"]
        elif "child" in receipt:
            result["child"] = receipt["child"]
            result["status"] = "bootstrap_unobserved"
        else:
            result["status"] = "creation_pending"
            result["client_thread_id"] = receipt["client_thread_id"]
            result["refs"]["creation_ref"] = str(directory / "bind.json")
    if (directory / "creation-resolved.json").exists():
        resolution = read_json(directory / "creation-resolved.json")
        result["child"] = resolution["child"]
        result["status"] = "bootstrap_unobserved"
        result["refs"]["creation_resolution_ref"] = str(directory / "creation-resolved.json")
    if (directory / "creation-outcome.json").exists():
        outcome = read_json(directory / "creation-outcome.json")
        result["refs"]["creation_outcome_ref"] = str(directory / "creation-outcome.json")
        if not (directory / "creation-resolved.json").exists():
            result["status"] = "creation_" + outcome["creation"]["state"]
            result["child"] = outcome.get("child")
    if (directory / "bootstrap.json").exists():
        bootstrap = read_json(directory / "bootstrap.json")["bootstrap"]
        state = bootstrap["state"]
        if state in {"pending", "completed", "failed", "unknown"}:
            result["status"] = "bootstrap_" + state
        else:
            result["status"] = "unsupported"
            result["reason"] = "unsupported-bootstrap-state"
    if (directory / "bootstrap-outcome.json").exists():
        outcome = read_json(directory / "bootstrap-outcome.json")
        result["status"] = "bootstrap_" + outcome["bootstrap"]["state"]
        result["refs"]["bootstrap_outcome_ref"] = str(directory / "bootstrap-outcome.json")
    if (directory / "bootstrap-completed.json").exists():
        completion = read_json(directory / "bootstrap-completed.json")
        result["status"] = "bootstrap_" + completion["bootstrap"]["state"]
        result["refs"]["bootstrap_completion_ref"] = str(directory / "bootstrap-completed.json")
    claim_present = (directory / "claim.json").exists()
    standing = intent.get("resource_admission") == "standing-v1"
    bound_attempt = None
    if claim_present and standing:
        try:
            bound_attempt = bound_standing_attempt(directory, result)
        except (OSError, ValueError, KeyError, TypeError, RecursionError):
            pass
    write_attempted = retained_task_write_attempt(directory, bound_attempt)
    decision_capture_failed = False
    if claim_present:
        result.pop("reason", None)
    evidence_read_failures = []
    for name in ("claim.json", "failure.json", "submission.json"):
        path = directory / name
        if path.exists():
            try:
                record = read_json(path)
            except (ValueError, OSError, RecursionError) as exc:
                if name == "claim.json" or not claim_present:
                    raise
                evidence_read_failures.append({
                    "path": str(path),
                    "reason": "read-error" if isinstance(exc, OSError) else "invalid-json",
                })
            else:
                try:
                    projection = retained_submission_fields(
                        directory, record, result, standing, bound_attempt, write_attempted,
                        claim=name == "claim.json",
                    )
                except (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError):
                    if name == "claim.json" or not claim_present:
                        raise ValueError("invalid-retained-result")
                    evidence_read_failures.append({"path": str(path), "reason": "invalid-result"})
                else:
                    if (projection.get("task_write") == "not_attempted"
                            and {"stage": "task-submit", "reason": "standing-decision-capture-failed"}
                            in projection.get("failures", ())):
                        decision_capture_failed = True
                    result.update(projection)
    if evidence_read_failures:
        result["evidence_read_failures"] = evidence_read_failures
    for name, key in (("setup.json", "setup_ref"), ("attempt.json", "attempt_ref")):
        if (directory / name).exists():
            result["refs"][key] = str(directory / name)
    if write_attempted:
        result.update(ipc="attempted", task_write="attempted")
    if bound_attempt is not None and not decision_capture_failed:
        decision_ref = retained_standing_decision(directory, intent, bound_attempt[0])
        if decision_ref is not None:
            result["refs"]["standing_decision_ref"] = decision_ref
            if result.get("task_write") == "not_attempted":
                result["task_write"] = "unknown"
    observations = task_observations(directory, result)
    if observations:
        wait_path, _, observation_path, observation = observations[-1]
        result["refs"]["task_wait_ref"] = str(wait_path)
        observed = [entry for entry in observations if entry[3] is not None]
        result["task_observation"] = "pending"
        result["task_completion"] = "unknown"
        if observed:
            _, _, latest_path, latest = observed[-1]
            result["refs"]["task_observation_ref"] = str(latest_path)
            if result["status"] == "turn_accepted":
                result["task_observation"] = ("pending" if observation is None
                                              else latest["task"]["state"])
                result["task_completion"] = (latest["task"]["state"]
                                             if latest["task"]["state"] in {"completed", "failed"}
                                             else "unknown")
        result["native_call"] = None
    return result


def validate_submission_intent(intent, continuation=False):
    allowed = ALLOWED_SUBMISSION_KEYS | ({"previous_operation_id"} if continuation else set())
    require(not intent.keys() - allowed, "unsupported-submission-input")
    if "resource_admission" in intent:
        require(intent["resource_admission"] == "standing-v1", "unsupported-resource-admission")
    for key in ("operation_id", "message_id", "attempt_id", "authority_ref", "payload", "endpoint"):
        require(text(intent.get(key)), "invalid-" + key)
    if continuation:
        require(text(intent.get("previous_operation_id")), "invalid-previous_operation_id")
    require(identity(intent.get("actor")) and identity(intent.get("owner")), "invalid-peer-identity")
    require(isinstance(intent.get("holds"), list) and all(text(x) for x in intent["holds"]),
            "invalid-holds")
    require(identity(intent.get("sender")), "invalid-sender")
    require(text(intent.get("correlation_id")), "invalid-correlation-id")
    require(text(intent.get("mailbox")), "invalid-mailbox")
    seconds = intent.get("observation_seconds")
    require(type(seconds) in (int, float) and 0 < seconds <= 10,
            "invalid-observation-seconds")
    require(intent.get("capture") is not None, "missing-submission-capture-settings")


class StandingRefusal(ValueError):
    """A task write was withheld by the standing route."""


def unique_json_object(pairs):
    value = dict(pairs)
    if len(value) != len(pairs):
        raise ValueError("duplicate-json-key")
    return value


def binding_identity(info):
    return (info.st_dev, info.st_ino, info.st_uid, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def valid_standing_allow(decision):
    return (
        isinstance(decision, dict)
        and decision.keys() == {"schema", "status", "reason", "grant_id", "runtime_id"}
        and decision["schema"] == "routine-standing-decision/v1"
        and decision["status"] == "ALLOW"
        and isinstance(decision["reason"], str)
        and text(decision["grant_id"])
        and isinstance(decision["runtime_id"], str)
        and re.fullmatch("[0-9a-f]{32}", decision["runtime_id"]) is not None
    )


def read_private_capture(path, *, include_bytes=False):
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as source:
        metadata = os.fstat(source.fileno())
        require(stat.S_ISREG(metadata.st_mode) and metadata.st_uid == os.getuid()
                and stat.S_IMODE(metadata.st_mode) == 0o600
                and 0 < metadata.st_size <= 2 * 1024 * 1024, "invalid-private-capture")
        raw = source.read(metadata.st_size + 1)
        require(len(raw) == metadata.st_size
                and binding_identity(metadata) == binding_identity(os.fstat(source.fileno()))
                == binding_identity(path.lstat()), "changed-private-capture")
    decoded = json.loads(raw, object_pairs_hook=unique_json_object)
    return (raw, decoded) if include_bytes else decoded


def retained_standing_decision(directory, intent, envelope):
    path = directory / "standing-decision.json"
    try:
        record = read_private_capture(path)
        require(isinstance(record, dict)
                and record.keys() == {"attempt_id", "correlation_id", "request_id", "decision"}
                and valid_standing_allow(record["decision"])
                and record["attempt_id"] == intent["attempt_id"]
                and record["correlation_id"] == intent["correlation_id"]
                and record["request_id"] == envelope["requestId"],
                "standing-decision-attempt-mismatch")
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        return None
    return str(path)


def standing_binding(arguments):
    if not arguments.standing_eligible or arguments.standing_paused or arguments.standing_independent_hold:
        raise StandingRefusal("standing-independent-ineligible")
    if not arguments.standing_binding:
        raise StandingRefusal("standing-binding-required")
    path = Path(arguments.standing_binding)
    try:
        require(path.is_absolute(), "relative-binding")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as source:
            metadata = os.fstat(source.fileno())
            require(stat.S_ISREG(metadata.st_mode) and metadata.st_uid == os.getuid()
                    and stat.S_IMODE(metadata.st_mode) == 0o600
                    and 0 < metadata.st_size <= 4096, "unqualified-binding")
            raw = source.read(4097)
            require(len(raw) == metadata.st_size
                    and binding_identity(metadata) == binding_identity(os.fstat(source.fileno()))
                    == binding_identity(path.lstat()), "changed-binding")
        binding = json.loads(raw, object_pairs_hook=unique_json_object)
        require(isinstance(binding, dict)
                and binding.keys() == {"reader", "authority_dir", "state_dir", "grant_id"}
                and all(text(value) for value in binding.values()), "invalid-binding")
        for key in ("reader", "authority_dir", "state_dir"):
            require(Path(binding[key]).is_absolute(), "relative-standing-path")
        reader = Path(binding["reader"]).lstat()
        require(stat.S_ISREG(reader.st_mode) and reader.st_uid == os.getuid()
                and not reader.st_mode & 0o022, "unqualified-reader")
    except (OSError, ValueError, TypeError) as error:
        raise StandingRefusal("standing-binding-invalid") from error
    return binding, binding_identity(reader)


def check_standing(binding, reader_identity):
    reader = Path(binding["reader"])
    argv = [sys.executable, "-E", "-S", "-B", binding["reader"], "standing-check",
            "--authority-dir", binding["authority_dir"], "--state-dir", binding["state_dir"],
            "--eligible"]
    try:
        require(binding_identity(reader.lstat()) == reader_identity, "changed-standing-reader")
        result = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, env={}, timeout=5, check=False)
        require(binding_identity(reader.lstat()) == reader_identity, "changed-standing-reader")
        require(result.returncode == 0 and 0 < len(result.stdout) <= 4096,
                "standing-reader-result")
        decision = json.loads(result.stdout, object_pairs_hook=unique_json_object)
        require(valid_standing_allow(decision) and decision["grant_id"] == binding["grant_id"],
                "standing-decision")
    except (OSError, ValueError, TypeError, RecursionError, subprocess.SubprocessError) as error:
        raise StandingRefusal("standing-decision-withheld") from error
    return decision


def submit_task(directory, intent, root, writer, arguments):
    """Claim once before effects; later public reads only project retained evidence."""
    result = retained(directory)
    if (directory / "claim.json").exists():
        return result
    validate_submission_intent(intent, continuation=(directory / "continuation.json").exists())
    standing = intent.get("resource_admission") == "standing-v1"
    require(standing or not (arguments.standing_binding or arguments.standing_eligible
                            or arguments.standing_paused or arguments.standing_independent_hold),
            "standing-intent-required")
    require(result["child"]["host_id"] == "local", "unsupported-remote-child")
    seconds = intent["observation_seconds"]
    message = {key: intent[key] for key in
               ("message_id", "correlation_id", "sender", "owner", "authority_ref",
                "holds", "payload")}
    message["recipient"] = result["child"]
    peer_text = serialize_peer_message(message, intent["actor"])
    result.update(status="submission_unknown", ipc="unknown", native_call=None,
                  saved_selection=None, receipt="unknown", task_completion="unknown",
                  effective_program="unknown", owned_connection={"started": None, "closed": None})
    result.pop("reason", None)
    if standing:
        result["task_write"] = "unknown"
    # Exclusive logical operation claim is also the crash/interrupt replay barrier.
    try:
        writer.write(directory / "claim.json", encode(result))
    except FileExistsError:
        return retained(directory)
    result["owned_connection"] = {"started": False, "closed": False}
    transport = None
    mailbox = None
    stage = "mailbox-claim"
    failures = []
    receive_failure = None

    def save(name, value):
        capture(root, [(directory / name, encode(value))], writer)

    def failure(where, error):
        failures.append({"stage": where, "reason": str(error) or type(error).__name__})
        result.setdefault("reason", failures[0]["reason"])
        result["failures"] = list(failures)

    def observe_transport_start():
        result["owned_connection"]["started"] = transport.stream is not None
        if transport.outbound:
            result["ipc"] = "attempted"
        if standing and any(item.get("method") == "thread-follower-start-turn"
                            for item in transport.outbound):
            result["task_write"] = "attempted"

    def usable():
        require(receive_failure is None and not transport.closed
                and transport.stream is not None and transport.receiver.incomplete is None,
                "connection-incomplete-before-write")

    def envelope(method, version, params):
        return {"type": "request", "requestId": str(uuid.uuid4()),
                "sourceClientId": client, "targetClientId": binding["owner"],
                "version": version, "method": method, "params": params}

    def exchange(request, name, *, before_write=None):
        nonlocal receive_failure
        # CliTransport can write before noticing receive incompleteness.
        usable()
        try:
            records = transport.send(request, before_write=before_write)
        except ReceivePrefixFailure as exc:
            receive_failure = exc
            failure(stage, exc)
            records = exc.records
        save(name + "-response.json", {"envelope": request, "records": records})
        matches = [item for _, item in records
                   if item.get("type") == "response"
                   and item.get("requestId") == request["requestId"]
                   and item.get("method") == request["method"]
                   and item.get("handledByClientId") == binding["owner"]]
        require(len(matches) == 1 and matches[0].get("resultType") == "success",
                name + "-response-unavailable")
        return matches[0]

    def prewrite(request, name, reference):
        record = {"envelope": request, "correlation": request["requestId"],
                  "actor": intent["actor"], "declaredOrigin": intent["sender"],
                  "authorityRefs": [intent["authority_ref"]], "holdRefs": intent["holds"],
                  "refs": dict(result["refs"])}
        save(name, record)
        result["refs"][reference] = str(directory / name)

    try:
        if standing:
            stage = "standing-preflight"
            result.update(ipc="not_attempted", task_write="not_attempted")
            gate_binding, reader_identity = standing_binding(arguments)
        stage = "mailbox-claim"
        mailbox = Mailbox(intent["mailbox"])
        mailbox.plan(message)
        claimed = mailbox.claim(intent["message_id"], intent["attempt_id"], intent["actor"])
        require(claimed["claimed"], "mailbox-attempt-already-claimed")
        save("mailbox-claim.json", claimed)
        stage = "owner-discovery"
        transport = CliTransport(intent["endpoint"],
                                 {"incomingBytes": 262144, "frameBytes": 65536,
                                  "outgoingFrameBytes": 65536, "events": 64},
                                 seconds)
        binding = {"target": result["child"]["thread_id"]}
        client = discover_owner(transport, binding, text=mailbox_text, refusal=ValueError)
        stage = "daybreak-setup-capture"
        setup = envelope("thread-follower-update-daybreak", 1,
                         {"conversationId": binding["target"], "daybreakEnabled": True})
        prewrite(setup, "setup.json", "setup_ref")
        stage = "daybreak-setup"
        response = exchange(setup, "setup")
        require(response.get("result", {}).get("ok") is True, "setup-not-confirmed")
        stage = "daybreak-readback"
        settings = envelope("thread-follower-read-model-settings", 1,
                            {"conversationId": binding["target"]})
        save("readback.json", {"envelope": settings})
        response = exchange(settings, "readback")
        require(response.get("result", {}).get("settings", {}).get("daybreakEnabled") is True,
                "saved-selection-unconfirmed")
        result["saved_selection"] = True
        save("selection.json", {"saved_selection": True, "response": response})
        stage = "task-capture"
        start = envelope("thread-follower-start-turn", 2, {
            "conversationId": binding["target"], "turnStart": {"request": {
                "threadId": binding["target"], "clientUserMessageId": intent["attempt_id"],
                "input": [{"type": "text", "text": peer_text, "text_elements": []}],
                "model": "gpt-6-sol", "effort": "medium", "cyberAccessProgram": "daybreakBlue",
                "collaborationMode": {"mode": "default", "settings": {
                    "model": "gpt-6-sol", "reasoning_effort": "medium",
                    "developer_instructions": None}},
            }, "context": {}}})
        prewrite(start, "attempt.json", "attempt_ref")
        transport.pending_path = directory / "attempt.json"
        stage = "task-submit"

        def before_task_write():
            decision = check_standing(gate_binding, reader_identity)
            decision_path = directory / "standing-decision.json"
            try:
                writer.write_json(decision_path, {
                    "attempt_id": intent["attempt_id"],
                    "correlation_id": intent["correlation_id"],
                    "request_id": start["requestId"],
                    "decision": decision,
                })
            except (OSError, StorageRefusal) as error:
                raise StandingRefusal("standing-decision-capture-failed") from error
            result["refs"]["standing_decision_ref"] = str(decision_path)
            result["task_write"] = "unknown"

        response = exchange(start, "start", before_write=before_task_write if standing else None)
        if standing:
            result["task_write"] = "attempted"
        turn_id = response.get("result", {}).get("result", {}).get("turn", {}).get("id")
        require(text(turn_id), "accepted-turn-id-unavailable")
        result.update(status="turn_accepted", turn_id=turn_id, ipc="attempted")
        stage = "mailbox-observation"
        mailbox.observe(intent["message_id"], intent["attempt_id"], "submitted",
                        str(directory / "start-response.json"),
                        "Correlated accepted turn; receipt and task completion unknown.")
    except BaseException as exc:
        if standing and transport is not None:
            observe_transport_start()
            if result["owned_connection"]["started"]:
                result["owned_connection"]["closed"] = None
        failure(stage, exc)
        try:
            save("failure.json", result)
        except BaseException as saving_error:
            failure("failure-capture", saving_error)
    finally:
        if transport is not None:
            observe_transport_start()
            try:
                transport.close()
            except BaseException as exc:
                failure("connection-close", exc)
            result["owned_connection"]["closed"] = transport.closed
            try:
                save("transport.json", {
                    "outbound": transport.outbound, "received": transport.retained,
                    "acquiredBytes": transport.acquired, "events": transport.events,
                    "incomplete": transport.receiver.incomplete,
                    "rejectedFrame": transport.receiver.rejected_frame,
                    "receiveStatus": transport.receive_status,
                    "generation": transport.generation, "writeBoundary": transport.write_boundary,
                    "owned_connection": result["owned_connection"],
                    "partialWireBytes": "not-exposed-by-transport"})
            except BaseException as exc:
                failure("transport-capture", exc)
        if mailbox is not None:
            try:
                mailbox.close()
            except BaseException as exc:
                failure("mailbox-close", exc)
    try:
        save("submission.json", result)
    except BaseException as exc:
        failure("submission-capture", exc)
    return result


def run(arguments):
    raw = Path(arguments.input).read_bytes() if getattr(arguments, "input", None) else None
    value = json.loads(raw) if raw is not None else None
    if raw is not None:
        require(isinstance(value, dict), "input-must-be-object")
    operation_id = value.get("operation_id") if arguments.phase in {"prepare", "continue"} else arguments.operation_id
    require(text(operation_id), "invalid-operation-id")
    root = Path(arguments.root)
    directory = root / hashlib.sha256(operation_id.encode("utf-8")).hexdigest()
    # Check the owned root and every retained path before reads or creation.
    guard = CaptureWriter({
        "run_root": str(root),
        "allowance_bytes": TERMINAL + 1,
        "terminal_provision_bytes": TERMINAL,
        "later_forecast_bytes": 0,
    })
    def guarded_directory(identifier):
        require(text(identifier), "invalid-operation-id")
        target = root / hashlib.sha256(identifier.encode("utf-8")).hexdigest()
        guard.require(target)
        for name in ("intent.json", "create.json", "bind.json", "read.json", "bootstrap.json",
                     "claim.json", "failure.json", "submission.json", "setup.json", "attempt.json",
                     "selection.json", "transport.json", "mailbox-claim.json", "readback.json",
                     "setup-response.json", "readback-response.json", "start-response.json",
                      "bootstrap-completed.json", "bootstrap-outcome.json", "creation-resolved.json",
                      "creation-outcome.json", "continuation.json"):
            guard.require(target / name)
        return target

    guarded_directory(operation_id)
    source = value if arguments.phase in {"prepare", "continue"} else read_json(directory / "intent.json")
    settings = source.get("capture")
    writer = None
    if settings is not None:
        writer = CaptureWriter(settings)
        require(str(writer.root) == str(root), "capture-root-conflict")

    def save(records):
        capture(root, records, writer)

    if arguments.phase == "continue":
        validate_submission_intent(value, continuation=True)
        if directory.exists():
            require(read_json(directory / "intent.json") == value, "intent-conflict")
            return retained(directory)
        previous = guarded_directory(value["previous_operation_id"])
        parent = read_json(previous / "intent.json")
        require(parent["operation_id"] == value["previous_operation_id"], "operation-conflict")
        require(parent.get("resource_admission") != "standing-v1"
                or value.get("resource_admission") == "standing-v1",
                "standing-continuation-downgrade")
        for key in ("operation_id", "message_id", "attempt_id"):
            require(value[key] != parent[key], "continuation-" + key + "-not-fresh")
        # Follow only retained operation links to the original child/bootstrap.
        original = previous
        seen = {operation_id}
        while True:
            original_intent = read_json(original / "intent.json")
            identifier = original_intent["operation_id"]
            require(identifier not in seen, "continuation-cycle")
            seen.add(identifier)
            if not (original / "continuation.json").exists():
                break
            link = read_json(original / "continuation.json")
            require(link["previous_operation_id"] == original_intent["previous_operation_id"],
                    "continuation-parent-conflict")
            original = guarded_directory(link["previous_operation_id"])
            require(read_json(original / "intent.json")["operation_id"]
                    == link["previous_operation_id"], "operation-conflict")
        original_result = retained(original)
        child = original_result["child"]
        require(identity(child), "bootstrap-without-child")
        require(child["host_id"] == "local", "unsupported-remote-child")
        bootstrap_path = original / "bootstrap-completed.json"
        if not bootstrap_path.exists():
            bootstrap_path = original / "bootstrap.json"
        bootstrap = read_json(bootstrap_path)
        require(bootstrap["bootstrap"]["state"] == "completed", "bootstrap-not-completed")
        require(bootstrap["call"] == read_json(original / "read.json")
                == observation_call(child), "bootstrap-call-conflict")
        require(retained(previous)["child"] == child, "continuation-child-conflict")
        continuation = {"previous_operation_id": value["previous_operation_id"],
                        "previous_operation_ref": str(previous / "intent.json"),
                        "bootstrap_ref": str(bootstrap_path), "child": child}
        # Reserve the new immutable intent before entering the existing claim pipeline.
        try:
            directory.mkdir(mode=0o700)
        except FileExistsError:
            require(read_json(directory / "intent.json") == value, "intent-conflict")
            return retained(directory)
        save([(directory / "intent.json", raw),
              (directory / "continuation.json", encode(continuation))])
        return submit_task(directory, value, root, writer, arguments)

    if arguments.phase == "prepare":
        validate_submission_intent(value)
        try:
            directory.mkdir(mode=0o700)
        except FileExistsError:
            require(read_json(directory / "intent.json") == value, "intent-conflict")
            return retained(directory)
        # A failed or interrupted capture leaves the operation claimed, never recreated.
        save([(directory / "intent.json", raw),
                       (directory / "create.json", encode(CREATE))])
        result = retained(directory)
        result.update(status="prepared", native_call=CREATE)
        return result

    intent = read_json(directory / "intent.json")
    require(intent["operation_id"] == operation_id, "operation-conflict")
    result = retained(directory)
    if arguments.phase == "bind":
        require(value.keys() <= {"call", "result", "child", "client_thread_id", "creation"},
                "invalid-creation-receipt")
        require(value.get("call") == read_json(directory / "create.json"), "creation-call-conflict")
        negative = creation_outcome(value)
        pending = "child" not in value and text(value.get("client_thread_id"))
        require("result" in value and
                (pending or (identity(value.get("child")) and "client_thread_id" not in value)
                 or (negative is not None and not {"child", "client_thread_id"} & value.keys())),
                "invalid-creation-receipt")
        if "child" in value:
            require(value["child"]["host_id"] == "local", "unsupported-remote-child")
        path = directory / "bind.json"
        if path.exists():
            require(path.read_bytes() == encode(value), "child-binding-conflict")
            return result
        require(not (directory / "bootstrap.json").exists(), "bootstrap-without-child")
        if pending or negative is not None:
            save([(path, encode(value))])
            return retained(directory)
        call = observation_call(value["child"])
        save([(path, encode(value)), (directory / "read.json", encode(call))])
        result = retained(directory)
        result["native_call"] = call
        return result

    if (arguments.phase == "reconcile" and value is not None
            and (result["status"] == "creation_pending" or "client_thread_id" in value)):
        require(value.keys() <= {"call", "result", "child", "client_thread_id", "evidence_ref", "creation"},
                "invalid-creation-receipt")
        original = read_json(directory / "bind.json")
        require("child" not in original and text(original.get("client_thread_id")),
                "creation-not-pending")
        require(value.get("client_thread_id") == original["client_thread_id"],
                "creation-handle-conflict")
        require(value.get("call") == original["call"] == read_json(directory / "create.json"),
                "creation-call-conflict")
        require("result" in value, "invalid-creation-receipt")
        negative = creation_outcome(value)
        outcome = directory / "creation-outcome.json"
        if negative is not None:
            require(not (directory / "creation-resolved.json").exists(), "creation-already-resolved")
            if "child" in value:
                require(identity(value["child"]), "invalid-child")
                require(value["child"]["host_id"] == "local", "unsupported-remote-child")
            if outcome.exists():
                require(outcome.read_bytes() == encode(value), "creation-outcome-conflict")
                return result
            require(original.get("creation", {}).get("state") != "failed", "creation-already-terminal")
            save([(outcome, encode(value))])
            return retained(directory)
        require(original.get("creation", {}).get("state") != "failed", "creation-already-terminal")
        if outcome.exists():
            prior = read_json(outcome)
            require(prior["creation"]["state"] != "failed", "creation-already-terminal")
            require("child" not in prior or prior["child"] == value.get("child"), "creation-child-conflict")
        require(identity(value.get("child")), "invalid-child")
        require(value["child"]["host_id"] == "local", "unsupported-remote-child")
        require(text(value.get("evidence_ref")), "invalid-creation-evidence")
        require("result" in value, "invalid-creation-receipt")
        require(not (isinstance(value["result"], dict) and value["result"].get("isError")),
                "native-creation-error")
        resolution = directory / "creation-resolved.json"
        if resolution.exists():
            require(resolution.read_bytes() == encode(value), "creation-resolution-conflict")
            return result
        call = observation_call(value["child"])
        read = directory / "read.json"
        require(not read.exists() or read.read_bytes() == encode(call), "bootstrap-call-conflict")
        require(not (directory / "bootstrap.json").exists(), "bootstrap-without-child")
        save([(resolution, encode(value)), (read, encode(call))])
        result = retained(directory)
        result["native_call"] = call
        return result

    if (arguments.phase == "reconcile" and value is not None
            and any(key in value for key in ("task_wait", "task_wait_ref", "task"))):
        accepted = result["status"] == "turn_accepted" and text(result.get("turn_id"))
        observations = task_observations(directory, result)
        if "task_wait" in value:
            require(value.keys() == {"task_wait"}, "invalid-task-wait-input")
            request = value["task_wait"]
            validate_task_wait(request)
            if any(wait["task_wait"] == request for _, wait, _, _ in observations):
                return result
            require(accepted, "task-turn-not-accepted")
            after_ref = None
            if observations:
                _, _, latest_path, latest = observations[-1]
                require(latest is not None, "task-observation-not-retained")
                require(latest["task"]["state"] in {"pending", "unknown"},
                        "task-already-terminal")
                after_ref = str(latest_path)
            require(request["after_ref"] == after_ref, "task-after-ref-conflict")
            call = observation_call(result["child"])
            wait_path = task_wait_path(directory, after_ref)
            guard.require(wait_path)
            wait = {"task_wait": request, "call": call, "turn_id": result["turn_id"],
                    "refs": {key: result["refs"][key] for key in
                             ("operation_id", "message_id", "attempt_id")}}
            # Retain the request before returning its one caller-owned read call.
            save([(wait_path, encode(wait))])
            result = retained(directory)
            result["native_call"] = call
            return result
        matching = [entry for entry in observations
                    if str(entry[0]) == value.get("task_wait_ref")]
        require(len(matching) == 1, "task-wait-ref-conflict")
        wait_path, wait, observation_path, observation = matching[0]
        validate_task_observation(value, str(wait_path), wait)
        if observation is not None:
            require(encode(observation) == encode(value), "task-observation-conflict")
            return result
        require(accepted, "task-turn-not-accepted")
        require(wait_path == observations[-1][0], "stale-task-wait-ref")
        require(all(item[3] is None
                    or item[3]["task"]["evidence_ref"] != value["task"]["evidence_ref"]
                    for item in observations), "task-evidence-not-fresh")
        save([(observation_path, encode(value))])
        return retained(directory)

    if arguments.phase in {"submit", "reconcile"} and value is not None:
        require(value.keys() == {"call", "result", "bootstrap"},
                "invalid-bootstrap-receipt")
        require(result["child"] is not None, "bootstrap-without-child")
        require(value.get("call") == read_json(directory / "read.json"), "bootstrap-call-conflict")
        bootstrap = value.get("bootstrap")
        require("result" in value and isinstance(bootstrap, dict), "invalid-bootstrap-receipt")
        require(bootstrap.keys() == {"state", "evidence_ref"}
                and bootstrap["state"] in {"pending", "completed", "failed", "unknown"}
                and text(bootstrap["evidence_ref"]), "invalid-bootstrap-observation")
        require(not (isinstance(value["result"], dict) and value["result"].get("isError"))
                or bootstrap["state"] == "unknown", "native-observation-error")
        if arguments.phase == "reconcile":
            original = read_json(directory / "bootstrap.json")
            require(original["bootstrap"]["state"] == "pending", "bootstrap-not-pending")
            require(value["call"] == original["call"] == observation_call(result["child"]),
                    "bootstrap-call-conflict")
            require(bootstrap["evidence_ref"] != original["bootstrap"]["evidence_ref"],
                    "bootstrap-evidence-not-fresh")
            completion = directory / "bootstrap-completed.json"
            outcome = directory / "bootstrap-outcome.json"
            if bootstrap["state"] != "completed":
                require(bootstrap["state"] in {"failed", "unknown"}, "bootstrap-not-completed")
                require(not completion.exists(), "bootstrap-already-completed")
                if outcome.exists():
                    require(outcome.read_bytes() == encode(value), "bootstrap-outcome-conflict")
                    return result
                require(not (directory / "claim.json").exists(), "bootstrap-already-claimed")
                save([(outcome, encode(value))])
                return retained(directory)
            if completion.exists():
                require(completion.read_bytes() == encode(value), "bootstrap-completion-conflict")
                return result
            if outcome.exists():
                prior = read_json(outcome)["bootstrap"]
                require(prior["state"] != "failed", "bootstrap-already-terminal")
                require(bootstrap["evidence_ref"] != prior["evidence_ref"], "bootstrap-evidence-not-fresh")
            if (directory / "claim.json").exists():
                return result
            # A retained completion is also an interruption barrier: only its first
            # explicit intake may proceed to the original one-attempt claim.
            save([(completion, encode(value))])
            return submit_task(directory, intent, root, writer, arguments)
        save([(directory / "bootstrap.json", encode(value))])
        if bootstrap["state"] == "completed":
            return submit_task(directory, intent, root, writer, arguments)
        return retained(directory)
    require(value is None, "unsupported-phase-input")
    return result


def main(argv=None):
    os.umask(0o077)
    arguments = parser().parse_args(argv)
    try:
        result = run(arguments)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, sqlite3.Error, StorageRefusal) as exc:
        result = {"status": "refused", "reason": str(exc),
                  "native_call": None, "ipc": "not_attempted"}
    result["phase"] = arguments.phase
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
