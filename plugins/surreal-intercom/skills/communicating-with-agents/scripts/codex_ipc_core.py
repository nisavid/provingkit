"""Finite IPC operation shared by explicit busy and observed-idle entries.

Source native_peer_client.py SHA-256:
abaf2dd6740c7b92abbd76ae8d05b51fc6a642e0ff88d8ec319816974ec09b6b.
The maintained entry supplies invocation-owned capture IO explicitly.
"""
import hashlib
import json
from pathlib import Path
import time
from codex_ipc_transport import ReceiveFailure, ReceivePrefixFailure, CliTransport, connect_unix

DEFAULTS = {"caseBytes": 1048576, "incomingBytes": 262144, "frameBytes": 65536,
            "events": 64, "projectionBytes": 8192, "maxAge": 10}

# Pinned native helper framing reference, not a measured processing allowance.
PROTOCOL_FRAME_MAX = 268435456
# At most DEFAULTS["events"] complete frames can pass the unchanged event guard.
# These structural maxima are independent of serialized fixture/resource limits.
ACQUISITION_MAX = {"incomingBytes": DEFAULTS["events"] * (PROTOCOL_FRAME_MAX + 4),
                   "frameBytes": PROTOCOL_FRAME_MAX}

class Refusal(Exception):
    pass

class ArtifactFailure(Exception):
    """Existing sender handback when required artifact finalization fails."""
    def __init__(self, result, original_failure, capture_failures, missing_evidence):
        self.result = result
        self.failure = {"originalFailure": original_failure,
                        "captureFailures": capture_failures, "missingEvidence": missing_evidence}
        super().__init__(original_failure["message"])


def failure_record(exc):
    return {"type": type(exc).__name__, "message": str(exc)}

def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()

def bounded_bytes(path, reason):
    ceiling = DEFAULTS["caseBytes"]
    with path.open("rb") as source:
        data = source.read(ceiling + 1)
    if len(data) > ceiling:
        raise Refusal(reason)
    return data


def print_result(result):
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


def _run_operation(case, directory, mode="submit", attempt_path=None, *, transport, clock, writer, request_input=None, idle_intent=False):
    writer.require(directory)
    save = writer.write_json
    now = clock
    binding = case["binding"]
    client = None
    followed = False
    reason = "missing-state"
    state = None
    observed_at = None
    revision = None
    possible = False
    dirty = None
    rpc = "unknown"
    original = None
    attempt_digest = None
    stage = None
    evidence = []
    evidence_overflow = False
    complete = False
    operation_records = []
    submit_observation = None
    terminal_reason = None
    outcome_finished = False
    primary_failure = None
    capture_failures = []
    missing_evidence = {}
    def capture(name, value):
        nonlocal primary_failure
        try:
            save(Path(directory) / name, value)
        except (OSError, Refusal, ValueError, TypeError) as exc:
            record = failure_record(exc)
            primary_failure = primary_failure or record
            capture_failures.append({"path": name, **record})
            missing_evidence[name] = "UNKNOWN"
    def exchange(envelope):
        # One operation owns every completed record, including cleanup's prefix.
        nonlocal terminal_reason, primary_failure
        statuses = getattr(transport, "receive_status", [])
        before = len(statuses)
        try:
            records = transport.send(envelope)
        except ReceivePrefixFailure as exc:
            primary_failure = primary_failure or failure_record(exc)
            if possible:
                operation_records.extend(exc.records)
            terminal_reason = str(exc)
            raise
        else:
            if possible:
                operation_records.extend(records)
            return records
        finally:
            if len(statuses) > before and not statuses[-1].startswith("receive-disabled:"):
                terminal_reason = statuses[-1]
    def original_responses(records):
        return [m for _, m in records if m.get("type") == "response"
                and m.get("requestId") == case.get("correlation")]
    def rpc_status(matching):
        if (len(matching) == 1 and isinstance(matching[0].get("resultType"), str)
                and matching[0]["resultType"] in {"success", "error"}):
            return matching[0]["resultType"]
        return "unknown"
    def observe(records):
        nonlocal state, observed_at, revision, dirty, evidence_overflow
        for record, message in records:
            if message.get("method") == "ipc-connection-reset":
                state = None
                raise Refusal("connection-reset-needs-new-binding")
            if (message.get("method") == "client-status-changed"
                    and message.get("params", {}).get("clientId") == binding["owner"]
                    and message.get("params", {}).get("status") == "disconnected"):
                state = None
                raise Refusal("owner-disconnected-needs-new-binding")
            if message.get("method") != "thread-stream-state-changed":
                continue
            params = message.get("params", {})
            if (message.get("type") != "broadcast" or message.get("version") != 11
                    or message.get("sourceClientId") != binding["owner"]
                    or client not in message.get("targetClientIds", [])
                    or params.get("hostId") != binding["host"] or params.get("conversationId") != binding["target"]
                    or record["generation"] != binding["generation"]):
                raise Refusal("unmatched-state-binding")
            change = params["change"]
            if change["type"] != "snapshot":
                dirty = "revision-gap" if change.get("baseRevision") != revision else "patch-needs-refresh"
                state = None
                patch_revision = change.get("revision")
                if type(patch_revision) is not int or patch_revision < 0:
                    raise Refusal("invalid-patch-revision")
                revision = max(revision, patch_revision) if revision is not None else patch_revision
                continue
            if not isinstance(change.get("revision"), int) or change["revision"] < 0:
                raise Refusal("invalid-revision")
            if revision is not None and change["revision"] < revision:
                raise Refusal("stale-revision")
            state = change["conversationState"]
            dirty = None
            observed_at = record["at"]
            revision = change["revision"]
            # Receipt observations belong to this snapshot, not the latest cache.
            # Keep selection invalidation and the finite receive lifecycle intact.
            if (possible or original is not None) and not idle_intent:
                if state.get("id") != binding["target"]:
                    raise Refusal("snapshot-target-mismatch")
                if not 0 <= now() - observed_at <= transport.limits["maxAge"]:
                    raise Refusal("stale-state")
                snapshot_turns, snapshot_complete = native_turns(state)
                correlation = original["correlation"] if original is not None else case["correlation"]
                observation = {"source": binding["owner"], "host": binding["host"], "target": binding["target"],
                               "client": client, "generation": record["generation"], "correlation": correlation,
                               "revision": revision, "at": observed_at, "historyComplete": snapshot_complete,
                               "limits": ["historical-snapshot-observation", "receipt-is-not-handling-or-result", "not-current-history"]}
                for item in correlated_evidence(snapshot_turns, correlation, case, binding, observed_at):
                    item["observation"] = dict(observation)
                    if not evidence_overflow and len(encode(evidence + [item])) <= transport.limits["projectionBytes"]:
                        evidence.append(item)
                    else:
                        evidence_overflow = True
    try:
        if len(encode(case)) > DEFAULTS["caseBytes"]:
            raise Refusal("case-byte-limit")
        for key, value in case.get("limits", {}).items():
            if key not in DEFAULTS or type(value) is not int or not 1 <= value <= ACQUISITION_MAX.get(key, DEFAULTS[key]):
                raise Refusal("unsupported-limit-profile")
            transport.limits[key] = value
        if transport.limits["projectionBytes"] < 256:
            raise Refusal("projection-limit-below-minimum")
        if len(encode(case)) > transport.limits["caseBytes"]:
            raise Refusal("case-byte-limit")
        if mode not in {"submit", "reconcile"}:
            raise Refusal("unsupported-command-mode")
        if mode == "submit" and attempt_path is not None:
            raise Refusal("existing-attempt-reconcile-only")
        if mode == "reconcile":
            original_path = Path(attempt_path)
            if original_path.stat().st_size > DEFAULTS["caseBytes"]:
                raise Refusal("attempt-input-byte-limit")
            original_bytes = original_path.read_bytes()
            original = json.loads(original_bytes)
            attempt_digest = hashlib.sha256(original_bytes).hexdigest()
            if (binding["host"] != original["binding"]["host"] or binding["target"] != original["binding"]["target"]
                    or not binding.get("nominationRef") or not case.get("consumerActor")):
                raise Refusal("successor-binding-unavailable")
            rpc_record = json.loads(original_path.with_name("rpc.json").read_bytes())
            rpc = rpc_record["status"]
            stage = "reconcile-unknown"
        if case.get("scope", {}).get("acquireLoaded") is not True:
            raise Refusal("acquisition-scope-unavailable")
        response = exchange({"type": "request", "requestId": "initialize", "version": 0,
                                   "method": "initialize", "params": {"clientType": "cli"}})
        matches = [m for _, m in response if m.get("type") == "response" and m.get("requestId") == "initialize"
                   and m.get("resultType") == "success" and m.get("method") == "initialize"]
        if (len(matches) != 1 or not isinstance(matches[0].get("result"), dict)
                or not matches[0]["result"].get("clientId")):
            raise Refusal("initialize-unavailable")
        client = matches[0]["result"]["clientId"]
        initial_records = response
        response = exchange({"type": "request", "requestId": "owner", "sourceClientId": client,
                                   "version": 1, "method": "thread-owner-discovery",
                                   "params": {"hostId": binding["host"], "conversationId": binding["target"]}})
        matches = [m for _, m in response if m.get("type") == "response" and m.get("requestId") == "owner"
                   and m.get("resultType") == "success" and m.get("method") == "thread-owner-discovery"]
        if len(matches) == 1 and matches[0].get("handledByClientId"):
            binding["owner"] = matches[0]["handledByClientId"]
        if len(matches) != 1 or matches[0].get("handledByClientId") != binding["owner"]:
            raise Refusal("owner-mismatch")
        observe(initial_records + response)
        followed = True
        observe(exchange(follow(client, binding, True)))
        if dirty is not None:
            observe(exchange(follow(client, binding, True)))
        if state is None or dirty is not None:
            raise Refusal(dirty or "missing-state")
        if transport.receiver.incomplete is not None:
            raise Refusal("connection-incomplete-before-write")
        if not 0 <= now() - observed_at <= transport.limits["maxAge"]:
            raise Refusal("stale-state")
        if state.get("id") != binding["target"]:
            raise Refusal("snapshot-target-mismatch")
        turns, complete = native_turns(state)
        if mode == "reconcile":
            stage = evidence[-1]["stage"] if evidence else "reconcile-unknown"
            raise Refusal("read-only-reconciliation")
        if state.get("turnHistory", {}).get("kind") == "canonical" and len(state["turnHistory"]["history"]["islands"]) != 1:
            raise Refusal("canonical-discontinuous-selection-unavailable")
        if turns and turns[-1]["status"] == "interrupted":
            raise Refusal("latest-turn-interrupted")
        current = [t for t in turns if t.get("status") == "inProgress"]
        runtime = state.get("threadRuntimeStatus", {}).get("type")
        if runtime == "active" and len(current) == 1 and turns[-1] == current[0]:
            selected = "steer"
        elif runtime == "idle" and not current:
            selected = "start"
        else:
            raise Refusal("state-conflict-or-unsupported")
        if idle_intent:
            if selected != "start":
                raise Refusal("idle-intent-observed-busy")
            if any(state.get(key) != expected for key, expected in (
                    ("threadStartKind", "default"), ("threadSource", "user"))):
                raise Refusal("idle-profile-unavailable")
        scope = case.get("scope", {})
        if not (scope.get("send") is True and scope.get("acquireLoaded") is True
                and scope.get("holdsSatisfied") is True and case.get("authorityRefs")
                and case.get("actor") and case.get("purpose") and case.get("correlation")):
            raise Refusal("scope-or-hold-unsatisfied")
        if "busyOnly" in scope and type(scope["busyOnly"]) is not bool:
            raise Refusal("invalid-busy-only")
        if scope.get("busyOnly") is True and selected == "start":
            raise Refusal("busy-only-start-forbidden")
        params = case["templates"][selected]
        if params.get("conversationId") != binding["target"]:
            raise Refusal("template-binding-mismatch")
        if selected == "steer":
            if params.get("clientUserMessageId") != case["correlation"]:
                raise Refusal("template-correlation-mismatch")
            message_input = params.get("input")
        else:
            request = params.get("turnStart", {}).get("request", {})
            inheritance = (params.get("turnStart", {}).get("context", {}).get("inheritThreadSettings")
                           if idle_intent else params.get("inheritThreadSettings"))
            if idle_intent and request.get("clientUserMessageId") != case["correlation"]:
                raise Refusal("template-correlation-mismatch")
            if request.get("threadId") != binding["target"] or inheritance is not True:
                raise Refusal("start-settings-not-inherited")
            message_input = request.get("input")
        if message_input != [{"type": "text", "text": case["payload"], "text_elements": []}]:
            raise Refusal("template-payload-mismatch")
        envelope = {"type": "request", "requestId": case["correlation"], "sourceClientId": client,
                    "targetClientId": binding["owner"], "version": 1 if selected == "steer" else 2,
                    "method": "thread-follower-" + selected + "-turn", "params": params}
        pending = {k: case[k] for k in ("payload", "correlation", "actor", "purpose", "authorityRefs", "holdRefs", "binding")}
        pending.update(pending=True, envelope=envelope, selection=selected, revision=revision, observedAt=observed_at,
                       payloadSha256=hashlib.sha256(case["payload"].encode()).hexdigest())
        pending.update(declaredOrigin=case["declaredOrigin"], nominationRef=case["nominationRef"],
                       route=case["route"], scope=case["scope"], profile=transport.limits,
                       configuration=configuration(case))
        if idle_intent:
            pending.update(observedProfile={key: state[key] for key in ("mode", "threadStartKind", "threadSource") if key in state},
                           observedRuntimeStatus=runtime, idle_observation_is_atomic=False)
        transport.pending_path = Path(directory) / "attempt.json"
        try:
            save(transport.pending_path, pending)
        except (OSError, Refusal) as exc:
            missing_evidence["attempt.json"] = "UNKNOWN"
            raise
        possible = True
        receive_failure = None
        try:
            records = exchange(envelope)
        except ReceivePrefixFailure as exc:
            records = exc.records
            receive_failure = str(exc)
        matching = original_responses(records)
        submit_observation = {"originalResult": matching, "status": rpc_status(matching),
                              "terminalReason": receive_failure or terminal_reason}
        observe(records)
        outcome_finished = True
    except (Refusal, ReceiveFailure, OSError, KeyError, ValueError, TypeError, AttributeError, FileExistsError) as exc:
        primary_failure = primary_failure or failure_record(exc)
        reason = primary_failure["message"]
        if possible and submit_observation is None:
            submit_observation = {"originalResult": [], "status": "unknown", "terminalReason": reason}
            terminal_reason = terminal_reason or reason
    finally:
        if followed:
            cleanup_records = []
            try:
                cleanup_records = exchange(follow(client, binding, False))
                closure = "unfollow-sent-ack-unknown"
            except ReceivePrefixFailure as exc:
                primary_failure = primary_failure or failure_record(exc)
                cleanup_records = exc.records
                closure = "unfollow-unknown:" + str(exc)
            except (Refusal, ReceiveFailure, OSError, KeyError, ValueError, TypeError) as exc:
                primary_failure = primary_failure or failure_record(exc)
                closure = "unfollow-unknown:" + str(exc)
            try:
                observe(cleanup_records)
            except (Refusal, KeyError, ValueError, TypeError, AttributeError) as exc:
                primary_failure = primary_failure or failure_record(exc)
                state = None
                outcome_finished = False
                reason = primary_failure["message"]
        else:
            closure = "no-subscription"
        try:
            transport.close()
            closure += ";owned-connection-closed"
        except OSError as exc:
            primary_failure = primary_failure or failure_record(exc)
            closure += ";owned-close-unknown:" + str(exc)
    # Finalize only after the finite operation has processed cleanup evidence.
    # Reconciliation reads the saved original RPC and never writes it again.
    if possible:
        matching = original_responses(operation_records)
        rpc = rpc_status(matching)
        if outcome_finished:
            reason = (terminal_reason if terminal_reason and terminal_reason != "observation-deadline-unknown"
                      else "rpc-" + rpc + "-effect-unconfirmed")
        rpc_record = {"originalResult": matching, "status": rpc, "effect": "possible-submission",
                      "submitObservation": submit_observation, "transportReason": terminal_reason}
        capture("rpc.json", rpc_record)
    if possible or original is not None:
        try:
            turns, complete = native_turns(state) if state is not None else ([], False)
            stage = evidence[-1]["stage"] if evidence else None
        except (Refusal, KeyError, ValueError, TypeError, AttributeError) as exc:
            primary_failure = primary_failure or failure_record(exc)
            complete = False
            stage = evidence[-1]["stage"] if evidence else None
            reason = primary_failure["message"]
    projection = {"stage": stage or ("reconcile-unknown" if original is not None else ("possible-submission" if possible else "refused-before-write")), "reason": reason, "closure": closure,
                  "acquisitionReason": terminal_reason,
                  "rpc": rpc, "historyComplete": complete, "evidence": evidence,
                  "limits": ["offline-injected-io-or-unqualified-live", "pending-is-not-receipt", "absence-is-not-nondelivery"],
                  "observation": {"source": binding["owner"], "at": observed_at, "revision": revision,
                                             "host": binding["host"], "target": binding["target"], "generation": binding["generation"]}}
    if idle_intent:
        projection.update(receipt="unknown", idle_observation_is_atomic=False)
        projection["limits"].append("idle-observation-not-atomic")
    if original is not None:
        projection.update(correlation=original["correlation"], originalAttemptSha256=attempt_digest,
                          originalActor=original["actor"], consumerActor=case["consumerActor"])
    if evidence_overflow or len(encode(projection)) > transport.limits["projectionBytes"]:
        projection = {"stage": "reconcile-unknown" if mode == "reconcile" else ("possible-submission" if possible else "refused-before-write"),
                      "reason": "projection-byte-limit", "incomplete": True, "rpc": rpc, "closure": closure}
        if len(encode(projection)) > transport.limits["projectionBytes"]:
            raise Refusal("projection-limit-cannot-represent-refusal")
    capture("received.json", transport.retained)
    result = {"outbound": transport.outbound, "projection": projection, "writeBoundary": transport.write_boundary,
              "firstDiagnostic": primary_failure,
              "owned_connection": {"started": transport.stream is not None,
                                   "closed": transport.stream is not None and transport.closed}}
    capture("outbound.json", transport.outbound)
    capture("projection.json", projection)
    capture("normalized-input.json", case)
    if request_input is not None:
        capture("request-input.json", request_input)
    capture("acquisition.json", {"incomingBytes": transport.acquired, "events": transport.events,
                                              "rejectedFrame": getattr(getattr(transport, "receiver", None), "rejected_frame", None),
                                              "rawInputLocation": None,
                                              "rawInputStatus": "caller-owned-location-unavailable",
                                              "normalizedInputBytes": len(encode(case)),
                                              "normalizedInputLocation": "normalized-input.json",
                                              "requestInputBytes": len(encode(request_input)) if request_input is not None else None,
                                              "requestInputLocation": "request-input.json" if request_input is not None else None,
                                              "requestInputStatus": "retained-serialized-request" if request_input is not None else "not-a-production-request",
                                              "incomingBytesMeaning": "acquired-wire-bytes-including-headers",
                                              "receivedRecordsLocation": "received.json",
                                              "projectionLocation": "projection.json",
                                              "effectiveLimits": transport.limits,
                                              "configuration": configuration(case),
                                              "receiveStatus": getattr(transport, "receive_status", []),
                                              "connectionGeneration": getattr(transport, "generation", None),
                                              "captureWrites": writer.observations})
    if capture_failures:
        raise ArtifactFailure(result, primary_failure, capture_failures, missing_evidence)
    return result

def correlated_evidence(turns, correlation, case, binding, observed_at):
    found = []
    for turn in turns:
        for item in turn.get("items", []):
            if (item.get("type") == "steeringUserMessage" and item.get("clientUserMessageId") == correlation
                    and item.get("serverUserMessageId") and item.get("status") in {"accepted", "refused"}):
                found.append({"stage": "receipt", "source": "native-server-linked-message", "at": observed_at,
                              "turnId": turn.get("turnId"), "serverUserMessageId": item["serverUserMessageId"]})
                if item["status"] == "refused":
                    found.append({"stage": "receiver-refusal", "source": "native-server-linked-message", "at": observed_at})
    return found

def native_turns(state):
    history = state.get("turnHistory")
    if history is not None:
        if history.get("kind") != "canonical":
            raise Refusal("unsupported-turn-history-kind")
        value = history.get("history")
        if (not isinstance(value, dict) or not isinstance(value.get("islands"), list)
                or not isinstance(value.get("entitiesByKey"), dict)):
            raise Refusal("unsupported-turn-history")
        islands = value["islands"]
        entities = value["entitiesByKey"]
        turns = []
        for island in islands:
            if not isinstance(island, dict) or not isinstance(island.get("entries"), list):
                raise Refusal("unsupported-turn-history")
            for entry in island["entries"]:
                if (not isinstance(entry, dict) or not isinstance(entry.get("value"), str)
                        or entry["value"] not in entities):
                    raise Refusal("unsupported-turn-history")
                turns.append(entities[entry["value"]])
        complete = value.get("isComplete") is True and len(islands) == 1
    else:
        turns = state.get("turns")
        complete = state.get("resumeState") == "resumed" and state.get("turnsPagination", {}).get("hasLoadedOldest", True) is True
    if not isinstance(turns, list) or any(not isinstance(t, dict) or "status" not in t for t in turns):
        raise Refusal("unsupported-turn-history")
    if any(t["status"] not in {"inProgress", "completed", "failed", "interrupted"} for t in turns):
        raise Refusal("unsupported-turn-status")
    complete = complete and all(t.get("itemsPagination", {}).get("hasLoadedOldest", True) is True for t in turns)
    return turns, complete

def follow(client, binding, value):
    return {"type": "broadcast", "sourceClientId": client, "targetClientIds": [binding["owner"]],
            "version": 1, "method": "thread-stream-following-changed",
            "params": {"hostId": binding["host"], "conversationId": binding["target"], "following": value}}


def configuration(request):
    supplied = request.get("profile", {})
    return {"source": "caller-explicit" if supplied else "small-defaults", "supplied": supplied,
            "authority": "caller-declaration-only;separate-live-grant-required"}


def _run_sender(request, directory, *, connector, clock, mode, attempt_path, writer, idle_intent):
    """Production operation seam. Connector and clock are injectable system IO.

    Request contains nomination/route and original scope records, never native
    state, assigned identity, timestamps or later receiver-evidence fixtures.
    This validates cooperative caller records; it grants no operator authority.
    """
    writer.require(directory)
    if len(encode(request)) > DEFAULTS["caseBytes"]:
        raise Refusal("case-byte-limit")
    if any(k in request for k in ("script", "now", "receiverEvidence", "binding", "templates")):
        raise Refusal("production-fixture-input-forbidden")
    scope = request.get("scope", {})
    if idle_intent:
        if scope.get("idleStartIntent") is not True or "busyOnly" in scope or mode != "submit":
            raise Refusal("explicit-idle-intent-required")
    elif scope.get("busyOnly") is not True:
        raise Refusal("busy-only-required")
    route = request["route"]
    if not all(isinstance(route.get(k), str) and route[k] for k in ("endpoint", "host", "target")):
        raise Refusal("explicit-route-required")
    if not request.get("nominationRef") or not request.get("actor") or not request.get("declaredOrigin"):
        raise Refusal("sender-origin-and-nomination-required")
    limits = dict(DEFAULTS)
    if not isinstance(request.get("profile", {}), dict):
        raise Refusal("unsupported-limit-profile")
    for key, value in request.get("profile", {}).items():
        if key not in DEFAULTS or type(value) is not int or not 1 <= value <= ACQUISITION_MAX.get(key, DEFAULTS[key]):
            raise Refusal("unsupported-limit-profile")
        limits[key] = value
    # Tightened tiny receive budgets remain useful intentional refusal probes.
    # An expanded profile must admit at least one full maximum-size frame.
    if (any(limits[k] > DEFAULTS[k] for k in ACQUISITION_MAX)
            and limits["frameBytes"] + 4 > limits["incomingBytes"]):
        raise Refusal("incoherent-acquisition-profile")
    wait = request.get("observationSeconds", 1)
    if type(wait) not in (int, float) or not 0 < wait <= 10:
        raise Refusal("unsupported-observation-wait")
    transport = CliTransport(route["endpoint"], limits, wait, connector, clock)
    case = dict(request)
    case.update(binding={"host": route["host"], "target": route["target"], "owner": None,
                         "generation": transport.generation, "nominationRef": request["nominationRef"]},
                limits=request.get("profile", {}))
    if mode == "submit":
        payload, correlation = request["payload"], request["correlation"]
        inp = [{"type": "text", "text": payload, "text_elements": []}]
        if idle_intent:
            case["templates"] = {"start": {"conversationId": route["target"], "turnStart": {
                "request": {"threadId": route["target"], "clientUserMessageId": correlation, "input": inp},
                "context": {"inheritThreadSettings": True}}}}
        else:
            case["templates"] = {
                "steer": {"conversationId": route["target"], "input": inp, "attachments": [],
                          "clientUserMessageId": correlation,
                          "restoreMessage": {"id": correlation, "context": {"prompt": payload,
                              "fileAttachments": [], "addedFiles": [], "imageAttachments": [],
                              "pastedTextAttachments": [], "commentAttachments": [], "turnTrigger": "steer"}}},
                "start": {"conversationId": route["target"], "inheritThreadSettings": True,
                          "turnStart": {"request": {"threadId": route["target"], "input": inp}, "context": {}}}}
    else:
        case["consumerActor"] = request["actor"]
    return _run_operation(case, directory, mode, attempt_path, transport=transport, clock=clock, writer=writer, request_input=request, idle_intent=idle_intent)


def run_sender(request, directory, *, connector=connect_unix, clock=time.monotonic,
               mode="submit", attempt_path=None, writer):
    """Send through the existing busy-only gate; never fall back to idle start."""
    return _run_sender(request, directory, connector=connector, clock=clock,
                       mode=mode, attempt_path=attempt_path, writer=writer, idle_intent=False)


def run_idle_sender(request, directory, *, writer):
    """Explicit cooperative idle intent; observed idle is not an atomic precondition.

    This source prototype makes no opening-receipt or live compatibility claim.
    """
    return _run_sender(request, directory, connector=connect_unix, clock=time.monotonic,
                       mode="submit", attempt_path=None, writer=writer, idle_intent=True)
