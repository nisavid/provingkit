"""Local owner-admission encoding through a disposable Unix peer."""

import contextlib
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = (
    ROOT / "plugins" / "surreal-intercom" / "skills"
    / "communicating-with-agents" / "scripts"
)
PROTOTYPE = SCRIPTS / "owner_admission_sender.py"
NO_RESPONSE = object()


class InjectedPeerStream:
    """One deterministic connection with source-backed peer observations."""

    def __init__(self, peer=None, *, early_response=False, response_kind="success",
                 null_initialize=False, deep_initialize=None,
                 response_request_id="owner-attempt", owner_response_kind="success",
                 message_write_error=False, message_write_interrupt=False):
        self.peer = peer
        self.peer_identity_calls = 0
        self.early_response = early_response
        self.response_kind = response_kind
        self.null_initialize = null_initialize
        self.deep_initialize = deep_initialize
        self.response_request_id = response_request_id
        self.owner_response_kind = owner_response_kind
        self.message_write_error = message_write_error
        self.message_write_interrupt = message_write_interrupt
        self.writes = []
        self.responses = bytearray()
        self.closed = False

    def peer_identity(self):
        index = self.peer_identity_calls
        self.peer_identity_calls += 1
        if isinstance(self.peer, list):
            return self.peer[min(index, len(self.peer) - 1)]
        return self.peer

    def read(self, maximum, timeout):
        if not self.responses:
            raise TimeoutError
        data = bytes(self.responses[:maximum])
        del self.responses[:maximum]
        return data

    def write(self, data, timeout):
        length = struct.unpack("<I", data[:4])[0]
        value = json.loads(data[4:4 + length])
        self.writes.append(value)
        if value["method"] == "initialize":
            response = {
                "type": "response", "requestId": self.response_request_id,
                "resultType": self.response_kind, "method": "thread-follower-start-turn",
                "result": {},
            }
            if self.early_response:
                self._queue(response)
            if self.deep_initialize is not None:
                self._queue(self.deep_initialize)
                return
            response = {
                "type": "response", "requestId": "initialize",
                "resultType": "success", "method": "initialize",
                "result": None if self.null_initialize else {"clientId": "native-client"},
            }
        elif value["method"] == "thread-owner-discovery":
            response = {
                "type": "response", "requestId": "owner",
                "resultType": self.owner_response_kind, "method": "thread-owner-discovery",
                "handledByClientId": "native-owner",
            }
        else:
            if self.message_write_interrupt:
                raise KeyboardInterrupt("synthetic-abrupt-message-write-interruption")
            if self.message_write_error:
                raise OSError("partial-message-write")
            if self.early_response or self.response_kind is NO_RESPONSE:
                return
            response = {
                "type": "response", "requestId": self.response_request_id,
                "resultType": self.response_kind, "method": "thread-follower-start-turn",
                "result": {},
            }
        self._queue(response)

    def _queue(self, value):
        if isinstance(value, bytes):
            body = value
        else:
            body = json.dumps(value).encode()
        self.responses.extend(struct.pack("<I", len(body)) + body)

    def close(self):
        self.closed = True


class CodexOwnerAdmissionTests(unittest.TestCase):
    def test_guarded_nomination_refuses_mismatched_connected_peer_before_protocol_write(self):
        self._assert_guarded_peer_mismatch()

    def test_guarded_nomination_refuses_peer_changed_before_message_write(self):
        self._assert_guarded_peer_mismatch(changed_after_owner=True)

    def _assert_guarded_peer_mismatch(self, *, changed_after_owner=False):
        with tempfile.TemporaryDirectory(prefix="codex-owner-guard-") as temporary:
            root = Path(temporary).resolve()
            store = root / "mailbox.sqlite3"
            capture = root / "capture"
            capture.mkdir(mode=0o700)
            original = {
                "message_id": "owner-message", "correlation_id": "shared-exchange",
                "sender": {"thread_id": "origin", "host_id": "origin-host"},
                "recipient": {"thread_id": "owner-peer", "host_id": "local"},
                "owner": {"thread_id": "task-owner", "host_id": "owner-host"},
                "payload": "Guard this payload.",
                "authority_ref": "synthetic://original-authority",
                "holds": ["synthetic://original-hold"],
            }
            actor = {"thread_id": "forwarder", "host_id": "forwarder-host"}
            environment = {
                **os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
            }

            def mailbox(*arguments):
                completed = subprocess.run([
                    sys.executable, "-B", str(SCRIPTS / "native_codex_mailbox.py"),
                    "--store", str(store), *arguments,
                ], capture_output=True, text=True, timeout=10, env=environment)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                return json.loads(completed.stdout)

            message_file = root / "message.json"
            message_file.write_text(json.dumps(original), encoding="utf-8")
            mailbox("init")
            mailbox("plan", "--input", str(message_file))

            executable = {"path": "/opt/codex/Codex", "device": 41, "inode": 73}
            expected_peer = {
                "pid": 4100, "uid": 1000, "gid": 1000, "startTicks": 9001,
                "bootId": "synthetic-boot", "networkNamespace": "net:[701]",
                "executable": executable,
            }
            expected_invocation = {
                "control": "native-read-thread-command-execution",
                "taskRef": "synthetic://task", "attemptId": "shared-exchange",
                "chat": original["recipient"],
                "command": ["/usr/bin/python3", "-B", "/opt/helpers/codex_route_nomination.py",
                            "--request", "/private/request.json"],
                "workingDirectory": "/synthetic/worktree",
                "helper": {"path": "/opt/helpers/codex_route_nomination.py",
                           "sha256": "a" * 64},
            }
            nomination = {
                "schema": "codex-route-nomination-v2", "status": "provisional",
                "route": {"endpoint": str(root / "peer.sock"), "host": "local",
                          "target": "owner-peer"},
                "recipient": original["recipient"], "producer": original["recipient"],
                "submitter": actor,
                "operationId": "shared-exchange", "acceptor": expected_peer,
                "expectedInvocation": expected_invocation,
                "acquisition": {
                    "startedMilliseconds": 1000, "finishedMilliseconds": 1004,
                    "descriptorEntries": 12, "unixRows": 30, "unixBytes": 4096,
                    "descriptorLinkBytes": 512, "selectedDescriptor": 11,
                    "socketInode": 501,
                    "launchSourceRef": "synthetic://installed-launch-source",
                    "listenerSourceRef": "synthetic://installed-listener-source",
                },
                "permissions": {},
                "acquisitionHolds": ["synthetic://original-hold"],
                "freshness": {"observedAtMilliseconds": 1004},
                "privacy": {"boundary": "unix-account-private",
                            "sameUidIsolation": False, "pathIsAuthority": False},
                "retirement": {"scope": "original-invocation-staging-only"},
            }
            for name, evidence, act, consumer in (
                ("metadata", "synthetic://metadata-authority",
                 "acquire-route-metadata", "nomination-controller"),
                ("nomination", "synthetic://nomination-authority",
                 "publish-route-nomination", "codex-route-nomination"),
                ("routeUse", "synthetic://route-use-authority",
                 "consume-route-nomination", "owner-admission-sender"),
            ):
                nomination["permissions"][name] = {
                    "evidenceRef": evidence,
                    "issuer": {"thread_id": "operator", "host_id": "native"},
                    "actor": (original["recipient"] if name in {"metadata", "nomination"}
                              else actor),
                    "act": act, "chat": original["recipient"],
                    "operationId": "shared-exchange",
                    "validityRef": "synthetic://validity/" + name,
                    "revocationRef": "synthetic://revocation/" + name,
                    "consumer": consumer,
                }
            nomination_bytes = json.dumps(
                nomination, sort_keys=True, separators=(",", ":")
            ).encode()
            nomination_path = root / "nomination.json"
            nomination_path.write_bytes(nomination_bytes)
            nomination_path.chmod(0o600)
            request = {
                "message_id": "owner-message", "attempt_id": "owner-attempt",
                "actor": actor, "recipient": original["recipient"],
                "evidence_ref": "synthetic://owner-evidence",
                "native": {
                    "nomination": {
                        "path": str(nomination_path),
                        "sha256": hashlib.sha256(nomination_bytes).hexdigest(),
                        "size": len(nomination_bytes),
                        "invocation": {
                            **expected_invocation,
                            "evidenceRef": "synthetic://native-command/completed",
                            "nativeItemId": "item-1", "status": "completed", "exitCode": 0,
                        },
                    },
                    "purpose": "Forward the original peer message",
                    "authorityRefs": ["synthetic://original-authority"],
                    "holdRefs": ["synthetic://original-hold"],
                    "scope": {"send": True, "ownerAdmissionIntent": True,
                              "holdsSatisfied": True},
                    "profile": {}, "observationSeconds": 0.1,
                },
                "capture": {"run_root": str(capture), "allowance_bytes": 8388608,
                            "terminal_provision_bytes": 524288,
                            "later_forecast_bytes": 0},
            }
            request_file = root / "request.json"
            request_file.write_text(json.dumps(request), encoding="utf-8")

            mismatched_peer = dict(expected_peer, pid=4101)
            peer = [expected_peer, mismatched_peer] if changed_after_owner else mismatched_peer
            stream = InjectedPeerStream(peer)
            sys.path.insert(0, str(SCRIPTS))
            try:
                sender = importlib.import_module("owner_admission_sender")
                transport_module = importlib.import_module("codex_ipc_transport")

                def transport(endpoint, limits, wait):
                    return transport_module.CliTransport(
                        endpoint, limits, wait, connector=lambda _endpoint, _wait: stream,
                    )

                output = io.StringIO()
                repeated_output = io.StringIO()
                with mock.patch.object(sender, "CliTransport", transport), mock.patch.object(
                    sys, "argv", [str(PROTOTYPE), "--store", str(store),
                                  "--request", str(request_file)]
                ):
                    with contextlib.redirect_stdout(output):
                        exit_code = sender.main(
                            effective_uid=nomination_path.stat().st_uid,
                            clock=lambda: 7005,
                        )
                    with contextlib.redirect_stdout(repeated_output):
                        repeated_exit_code = sender.main(
                            effective_uid=nomination_path.stat().st_uid,
                            clock=lambda: 7005,
                        )
            finally:
                sys.path.remove(str(SCRIPTS))

            self.assertEqual(exit_code, 0)
            result = json.loads(output.getvalue())
            self.assertEqual(
                result["reason"],
                "connected-peer-changed-before-message" if changed_after_owner
                else "connected-peer-mismatch",
            )
            self.assertEqual(result["peer_input"], "not_attempted")
            expected_methods = ([] if not changed_after_owner else
                                ["initialize", "thread-owner-discovery"])
            self.assertEqual([frame["method"] for frame in stream.writes], expected_methods)
            self.assertTrue(stream.closed)
            self.assertEqual(result["conclusive_bookkeeping"]["status"], "retained")
            self.assertEqual(repeated_exit_code, 0)
            repeated = json.loads(repeated_output.getvalue())
            self.assertFalse(repeated["claimed"])
            self.assertEqual(repeated["reason"], "claim_not_acquired")
            self.assertEqual(repeated["peer_input"], "not_attempted")
            recorded = mailbox("show", "owner-message")
            self.assertEqual(len(recorded["attempts"]), 1)
            attempt = recorded["attempts"][0]
            self.assertEqual(attempt["attempt_id"], "owner-attempt")
            self.assertEqual([item["kind"] for item in attempt["observations"]],
                             ["unknown", "not_delivered"])
            self.assertIsNone(attempt["reconciliation"])
            later = mailbox(
                "claim", "owner-message", "later-attempt",
                "--actor-thread-id", actor["thread_id"],
                "--actor-host-id", actor["host_id"],
            )
            self.assertFalse(later["claimed"])

    def exchange(self, *, early_response=False, response_kind="success", repeat=False,
                 capture_collision=False, route_change=None, null_initialize=False,
                 deep_initialize=None, owner_response_kind="success",
                 message_write_error=False, message_write_interrupt=False):
        with tempfile.TemporaryDirectory(prefix="codex-owner-") as temporary:
            root = Path(temporary).resolve()
            store = root / "mailbox.sqlite3"
            capture = root / "capture"
            capture.mkdir()
            endpoint = root / "peer.sock"
            original = {
                "message_id": "owner-message", "correlation_id": "shared-exchange",
                "sender": {"thread_id": "origin", "host_id": "origin-host"},
                "recipient": {"thread_id": "owner-peer", "host_id": "local"},
                "owner": {"thread_id": "task-owner", "host_id": "owner-host"},
                "payload": "Keep café and 雪.\nSecond line: 👋",
                "authority_ref": "synthetic://original-authority",
                "holds": ["synthetic://original-hold"],
            }
            actor = {"thread_id": "forwarder", "host_id": "forwarder-host"}
            expected_payload = "Peer message (no new operator authority).\n" + json.dumps({
                "schema": "provingkit-peer-message-v1",
                "message_id": "owner-message", "correlation_id": "shared-exchange",
                "sender": {"thread_id": "origin", "host_id": "origin-host"},
                "actor": {"thread_id": "forwarder", "host_id": "forwarder-host"},
                "recipient": {"thread_id": "owner-peer", "host_id": "local"},
                "owner": {"thread_id": "task-owner", "host_id": "owner-host"},
                "authority_ref": "synthetic://original-authority",
                "holds": ["synthetic://original-hold"],
                "payload": "Keep café and 雪.\nSecond line: 👋",
            }, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
            environment = {
                **os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
            }
            stream = None

            def command(script, *arguments):
                if script == PROTOTYPE:
                    sys.path.insert(0, str(SCRIPTS))
                    try:
                        sender = importlib.import_module("owner_admission_sender")
                        transport_module = importlib.import_module("codex_ipc_transport")

                        def transport(endpoint, limits, wait):
                            return transport_module.CliTransport(
                                endpoint, limits, wait,
                                connector=lambda _endpoint, _wait: stream,
                            )

                        stdout = io.StringIO()
                        stderr = io.StringIO()
                        with mock.patch.object(sender, "CliTransport", transport), \
                                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                            returncode = sender.main([
                                "--store", str(store), *arguments,
                            ])
                        return SimpleNamespace(
                            returncode=returncode, stdout=stdout.getvalue(), stderr=stderr.getvalue()
                        )
                    finally:
                        sys.path.remove(str(SCRIPTS))
                return subprocess.run(
                    [sys.executable, "-B", str(script), "--store", str(store), *arguments],
                    capture_output=True, text=True, timeout=10, env=environment,
                )

            def mailbox(*arguments):
                completed = command(SCRIPTS / "native_codex_mailbox.py", *arguments)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                return json.loads(completed.stdout)

            message_file = root / "message.json"
            message_file.write_text(json.dumps(original), encoding="utf-8")
            mailbox("init")
            mailbox("plan", "--input", str(message_file))
            self.assertEqual(mailbox("show", "owner-message")["state"], "planned")
            request = {
                "message_id": "owner-message", "attempt_id": "owner-attempt",
                "actor": actor, "recipient": original["recipient"],
                "evidence_ref": "synthetic://owner-evidence",
                "native": {
                    "route": {"endpoint": str(endpoint), "host": "local", "target": "owner-peer"},
                    "nominationRef": "synthetic://independent-nomination",
                    "purpose": "Forward the original peer message",
                    "authorityRefs": ["synthetic://original-authority"],
                    "holdRefs": ["synthetic://original-hold"],
                    "scope": {"send": True, "ownerAdmissionIntent": True, "holdsSatisfied": True},
                    "profile": {}, "observationSeconds": 0.1,
                },
                "capture": {"run_root": str(capture), "allowance_bytes": 8388608,
                            "terminal_provision_bytes": 524288, "later_forecast_bytes": 0},
            }
            if route_change is not None:
                request["native"]["route"].update(route_change)
            request_file = root / "request.json"
            request_file.write_text(json.dumps(request), encoding="utf-8")
            retained_attempt = b'{"existing":"original attempt"}'
            retained_rpc = b'{"existing":"original rpc"}'
            if capture_collision:
                (capture / "attempt.json").write_bytes(retained_attempt)
                (capture / "rpc.json").write_bytes(retained_rpc)
            stream = InjectedPeerStream(
                early_response=early_response, response_kind=response_kind,
                null_initialize=null_initialize, deep_initialize=deep_initialize,
                owner_response_kind=owner_response_kind,
                message_write_error=message_write_error,
                message_write_interrupt=message_write_interrupt,
            )
            if message_write_interrupt:
                # This models only a BaseException at the ordinary message-frame
                # write call, after the frame is presented to the stream; it does
                # not model abrupt termination at every possible instruction.
                with self.assertRaisesRegex(
                        KeyboardInterrupt, "synthetic-abrupt-message-write-interruption"):
                    command(PROTOTYPE, "--request", str(request_file))
                return mailbox("show", "owner-message"), list(stream.writes), stream.closed
            completed = command(PROTOTYPE, "--request", str(request_file))
            wire = stream.writes
            prewrite = [] if not (capture / "attempt.json").is_file() else [
                (capture / "attempt.json").read_bytes()
            ]
            if repeat:
                retained = {item.name: item.read_bytes() for item in capture.iterdir()}
                repeated = command(PROTOTYPE, "--request", str(request_file))
                self.assertEqual(repeated.returncode, 0, repeated.stderr)
                repeated_result = json.loads(repeated.stdout)
                self.assertEqual(repeated_result["reason"], "claim_not_acquired")
                self.assertFalse(repeated_result["claimed"])
                self.assertEqual(repeated_result["peer_input"], "not_attempted")
                self.assertEqual(repeated_result["owned_connection"], {"started": False, "closed": False})
                self.assertEqual({item.name: item.read_bytes() for item in capture.iterdir()}, retained)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stderr, "")
            if route_change is not None:
                result = json.loads(completed.stdout)
                self.assertFalse(result["claimed"])
                self.assertEqual(result["peer_input"], "not_attempted")
                self.assertEqual(result["owned_connection"], {"started": False, "closed": False})
                self.assertEqual(wire, [])
                self.assertEqual(list(capture.iterdir()), [])
                self.assertEqual(mailbox("show", "owner-message")["state"], "planned")
                return result, {}
            self.assertTrue(stream.closed)
            result = json.loads(completed.stdout)
            self.assertEqual(result["receipt"], "unknown")
            self.assertEqual(result["native_branch"], "unknown")
            self.assertTrue(result["ordinary_start_fallback_possible"])
            self.assertEqual(result["projection"]["receipt"], "unknown")
            self.assertEqual(result["projection"]["native_branch"], "unknown")
            self.assertEqual(result["owned_connection"], {"started": True, "closed": True})
            setup_refusal = (null_initialize or deep_initialize is not None
                             or owner_response_kind != "success")
            self.assertEqual(result["peer_input"],
                             "not_attempted" if capture_collision or setup_refusal
                             else "possible_submission")
            if setup_refusal:
                expected_methods = ["initialize"]
                if owner_response_kind != "success":
                    expected_methods.append("thread-owner-discovery")
                self.assertEqual([frame["method"] for frame in wire], expected_methods)
                self.assertEqual(json.loads((capture / "outbound.json").read_bytes()), wire)
                received = json.loads((capture / "received.json").read_bytes())
                if deep_initialize is not None:
                    self.assertEqual(received, [])
                elif null_initialize:
                    self.assertEqual([frame for _, frame in received], [{
                        "type": "response", "requestId": "initialize", "resultType": "success",
                        "method": "initialize", "result": None,
                    }])
                else:
                    self.assertEqual(
                        [frame["requestId"] for _, frame in received],
                        ["initialize", "owner"],
                    )
                self.assertEqual(json.loads((capture / "projection.json").read_bytes()), result["projection"])
                self.assertEqual(json.loads((capture / "normalized-input.json").read_bytes())["correlation"],
                                 "owner-attempt")
                acquisition = json.loads((capture / "acquisition.json").read_bytes())
                self.assertGreater(acquisition["incomingBytes"], 0)
                if received:
                    self.assertEqual(len({metadata["generation"] for metadata, _ in received}), 1)
                    self.assertEqual(received[0][0]["generation"], acquisition["connectionGeneration"])
                else:
                    self.assertEqual(acquisition["incomingBytes"], len(deep_initialize) + 4)
                    self.assertEqual(acquisition["events"], 1)
                    self.assertIn("frame-decode-error", acquisition["receiveStatus"])
                self.assertFalse((capture / "attempt.json").exists())
                recorded = mailbox("show", "owner-message")
                self.assertEqual({k: v for k, v in recorded.items() if k not in {"state", "attempts"}}, original)
                self.assertEqual(recorded["state"], "unknown")
                self.assertEqual(len(recorded["attempts"]), 1)
                self.assertEqual(recorded["attempts"][0]["attempt_id"], "owner-attempt")
                self.assertEqual([item["kind"] for item in recorded["attempts"][0]["observations"]],
                                 ["unknown", "not_delivered"])
                self.assertEqual(result["conclusive_bookkeeping"]["status"], "retained")
                return result, json.loads((capture / "rpc.json").read_bytes())
            expected_methods = ["initialize", "thread-owner-discovery"]
            if not capture_collision:
                expected_methods.append("thread-follower-start-turn")
            self.assertEqual([f["method"] for f in wire], expected_methods)
            self.assertEqual(json.loads((capture / "outbound.json").read_bytes()), wire)
            if capture_collision:
                self.assertEqual((capture / "attempt.json").read_bytes(), retained_attempt)
                self.assertEqual((capture / "rpc.json").read_bytes(), retained_rpc)
            else:
                self.assertEqual(prewrite, [(capture / "attempt.json").read_bytes()])
                start = wire[-1]
                # Exact equality also excludes hostId, settings, attachments,
                # injection, tool output, and other optional submission fields.
                self.assertEqual(start, {
                    "type": "request", "requestId": "owner-attempt", "sourceClientId": "native-client",
                    "targetClientId": "native-owner", "version": 2,
                    "method": "thread-follower-start-turn",
                    "params": {"conversationId": "owner-peer", "turnStart": {
                        "request": {"threadId": "owner-peer", "clientUserMessageId": "owner-attempt",
                            "input": [{"type": "text", "text": expected_payload,
                                       "text_elements": []}]},
                        "context": {"inheritThreadSettings": True,
                                    "useUserMessageAdmission": True}}},
                })
                pending = json.loads(prewrite[0])
                self.assertEqual(pending["envelope"], start)
                self.assertEqual(pending["correlation"], "owner-attempt")
                self.assertEqual(pending["authorityRefs"], ["synthetic://original-authority"])
                self.assertEqual(pending["holdRefs"], ["synthetic://original-hold"])
                self.assertEqual(pending["actor"], actor)
                self.assertEqual(pending["declaredOrigin"], original["sender"])
            recorded = mailbox("show", "owner-message")
            self.assertEqual({k: v for k, v in recorded.items() if k not in {"state", "attempts"}}, original)
            self.assertEqual(
                [item["kind"] for item in recorded["attempts"][0]["observations"]],
                ["unknown", "not_delivered"] if capture_collision else ["unknown"],
            )
            if capture_collision:
                self.assertEqual(result["conclusive_bookkeeping"]["status"], "retained")
            else:
                self.assertNotIn("conclusive_bookkeeping", result)
            self.assertEqual(json.loads((capture / "projection.json").read_bytes()), result["projection"])
            for name in ("normalized-input.json", "acquisition.json", "received.json"):
                self.assertTrue((capture / name).is_file(), name)
            return result, json.loads((capture / "rpc.json").read_bytes())

    def test_unsupported_correlated_result_types_preserve_unknown_submission_and_captures(self):
        for kind in ({}, None):
            with self.subTest(result_type=kind):
                result, rpc = self.exchange(response_kind=kind, repeat=True)
                self.assertTrue(result["claimed"])
                self.assertEqual(result["reason"], "rpc-outcome-unknown")
                self.assertEqual(result["peer_input"], "possible_submission")
                self.assertEqual(result["owned_connection"], {"started": True, "closed": True})
                self.assertEqual(result["projection"]["stage"], "possible-submission")
                self.assertEqual(rpc["status"], "unknown")
                self.assertEqual(rpc["originalResult"], [{
                    "type": "response", "requestId": "owner-attempt",
                    "resultType": kind, "method": "thread-follower-start-turn", "result": {},
                }])

    def test_decoder_recursion_during_initialize_refuses_with_captures_and_owned_close(self):
        raw = b'{"unused":' + b"[" * 10000 + b"0" + b"]" * 10000 + b"}"
        self.assertLess(len(raw), 65536)
        try:
            json.loads(raw)
        except RecursionError:
            pass
        else:
            self.skipTest("Decoder accepts this bounded nesting; no recursion-failure case on this interpreter.")
        result, rpc = self.exchange(deep_initialize=raw, repeat=True)
        self.assertTrue(result["claimed"])
        self.assertEqual(result["reason"], "frame-decode-error")
        self.assertEqual(result["firstDiagnostic"]["message"], "frame-decode-error")
        self.assertEqual(result["projection"]["stage"], "refused-before-write")
        self.assertEqual(rpc["status"], "unknown")
        self.assertEqual(rpc["originalResult"], [])

    def test_null_initialize_result_reports_refusal_and_preserves_evidence_without_peer_input(self):
        result, rpc = self.exchange(null_initialize=True)
        self.assertTrue(result["claimed"])
        self.assertEqual(result["reason"], "initialize-unavailable")
        self.assertEqual(result["firstDiagnostic"],
                         {"type": "Refusal", "message": "initialize-unavailable"})
        self.assertEqual(result["projection"]["stage"], "refused-before-write")
        self.assertEqual(result["projection"]["reason"], "initialize-unavailable")
        self.assertEqual(result["projection"]["evidence"], [])
        self.assertEqual(rpc["status"], "unknown")
        self.assertEqual(rpc["originalResult"], [])
        self.assertNotIn("capture_failure", result)

    def test_owner_refusal_retains_conclusive_nondelivery_after_owned_close(self):
        result, rpc = self.exchange(owner_response_kind="error")
        self.assertTrue(result["claimed"])
        self.assertEqual(result["reason"], "owner-unavailable")
        self.assertEqual(result["projection"]["stage"], "refused-before-write")
        self.assertEqual(rpc["status"], "unknown")
        self.assertEqual(rpc["originalResult"], [])

    def test_local_owner_request_preserves_peer_envelope_and_admission_flags(self):
        result, rpc = self.exchange()
        self.assertEqual(rpc["status"], "success")
        self.assertEqual(result["reason"], "rpc-success-effect-unconfirmed")
        self.assertEqual(result["projection"]["evidence"], [])

    def test_reply_observed_before_submission_is_not_credited_to_the_attempt(self):
        result, rpc = self.exchange(early_response=True)
        self.assertEqual(rpc["status"], "unknown")
        self.assertEqual(result["reason"], "rpc-outcome-unknown")
        self.assertEqual(result["projection"]["evidence"], [])

    def test_missing_reply_keeps_submission_unknown_without_resend(self):
        result, rpc = self.exchange(response_kind=NO_RESPONSE)
        self.assertEqual(rpc["status"], "unknown")
        self.assertEqual(result["reason"], "rpc-outcome-unknown")

    def test_rpc_error_does_not_claim_no_effect_or_receiver_receipt(self):
        result, rpc = self.exchange(response_kind="error")
        self.assertEqual(rpc["status"], "error")
        self.assertEqual(result["reason"], "rpc-error-effect-unknown")

    def test_message_write_failure_after_boundary_preserves_unknown(self):
        result, rpc = self.exchange(message_write_error=True)
        self.assertEqual(result["reason"], "partial-message-write")
        self.assertEqual(result["peer_input"], "possible_submission")
        self.assertEqual(result["projection"]["stage"], "possible-submission")
        self.assertNotIn("conclusive_bookkeeping", result)
        self.assertEqual(rpc["status"], "unknown")

    def test_abrupt_interruption_after_durable_unknown_preserves_original_attempt(self):
        recorded, wire, closed = self.exchange(message_write_interrupt=True)
        self.assertTrue(closed)
        methods = [frame["method"] for frame in wire]
        self.assertEqual(methods, [
            "initialize", "thread-owner-discovery", "thread-follower-start-turn",
        ])
        self.assertEqual(methods.count("thread-follower-start-turn"), 1)
        self.assertEqual(recorded["state"], "unknown")
        self.assertEqual(len(recorded["attempts"]), 1)
        attempt = recorded["attempts"][0]
        self.assertEqual(attempt["attempt_id"], "owner-attempt")
        self.assertEqual(attempt["submission"], "unknown")
        self.assertIsNone(attempt["reconciliation"])
        self.assertFalse(attempt["received"])
        self.assertFalse(attempt["handled"])
        self.assertFalse(attempt["completed"])
        self.assertEqual(
            [observation["kind"] for observation in attempt["observations"]],
            ["unknown"],
        )

    def test_repeat_invocation_cannot_reclaim_or_resend_the_original_attempt(self):
        self.exchange(repeat=True)

    def test_pending_capture_failure_prevents_input_and_survives_later_capture_failure(self):
        result, _ = self.exchange(capture_collision=True)
        self.assertEqual(result["projection"]["stage"], "refused-before-write")
        original = result["firstDiagnostic"]
        self.assertEqual(original["type"], "FileExistsError")
        self.assertIn("attempt.json", original["message"])
        self.assertEqual(result["capture_failure"]["originalFailure"], original)
        self.assertEqual([item["path"] for item in result["capture_failure"]["captureFailures"]],
                         ["attempt.json", "rpc.json"])

    def test_nonlocal_or_host_qualified_request_is_not_sent_as_local_version_two(self):
        for change in ({"host": "another-host"}, {"hostId": "local"}):
            with self.subTest(route_change=change):
                result, _ = self.exchange(route_change=change)
                self.assertEqual(result["reason"], "explicit-local-route-required")


if __name__ == "__main__":
    unittest.main()
