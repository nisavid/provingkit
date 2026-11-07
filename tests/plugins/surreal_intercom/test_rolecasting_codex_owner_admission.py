"""Local owner-admission encoding through a disposable Unix peer."""

import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import unittest


ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = (
    ROOT / "plugins" / "surreal-intercom" / "skills"
    / "communicating-with-agents" / "scripts"
)
PROTOTYPE = SCRIPTS / "owner_admission_sender.py"


class CodexOwnerAdmissionTests(unittest.TestCase):
    def exchange(self, *, early_response=False, response_kind="success", repeat=False,
                 capture_collision=False, route_change=None):
        with tempfile.TemporaryDirectory(prefix="codex-owner-") as temporary:
            root = Path(temporary)
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

            def command(script, *arguments):
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
            wire, errors, prewrite = [], [], []
            closed = threading.Event()

            def serve(listener):
                try:
                    try:
                        connection, _ = listener.accept()
                    except TimeoutError:
                        return  # An absent prototype never connects.
                    with connection:
                        connection.settimeout(3)

                        def receive():
                            def exact(count):
                                data = b""
                                while len(data) < count:
                                    part = connection.recv(count - len(data))
                                    if not part:
                                        raise AssertionError("unexpected fixture EOF")
                                    data += part
                                return data
                            length = struct.unpack("<I", exact(4))[0]
                            self.assertGreater(length, 0)
                            self.assertLessEqual(length, 65536)
                            value = json.loads(exact(length))
                            wire.append(value)
                            return value

                        def send(value):
                            data = json.dumps(value).encode()
                            connection.sendall(struct.pack("<I", len(data)) + data)

                        self.assertEqual(receive(), {
                            "type": "request", "requestId": "initialize", "version": 0,
                            "method": "initialize", "params": {"clientType": "cli"},
                        })
                        response = {"type": "response", "requestId": "owner-attempt",
                                    "resultType": response_kind, "method": "thread-follower-start-turn",
                                    "result": {}}
                        if early_response:
                            send(response)
                        send({"type": "response", "requestId": "initialize", "resultType": "success",
                              "method": "initialize", "result": {"clientId": "native-client"}})
                        self.assertEqual(receive(), {
                            "type": "request", "requestId": "owner", "sourceClientId": "native-client",
                            "version": 1, "method": "thread-owner-discovery",
                            "params": {"hostId": "local", "conversationId": "owner-peer"},
                        })
                        send({"type": "response", "requestId": "owner", "resultType": "success",
                              "method": "thread-owner-discovery", "handledByClientId": "native-owner"})
                        if capture_collision:
                            self.assertEqual(connection.recv(1), b"")
                            closed.set()
                            return
                        start = receive()
                        prewrite.append((capture / "attempt.json").read_bytes())
                        # Exact equality also excludes hostId, settings, attachments,
                        # injection, tool output, and other optional submission fields.
                        self.assertEqual(start, {
                            "type": "request", "requestId": "owner-attempt", "sourceClientId": "native-client",
                            "targetClientId": "native-owner", "version": 2, "method": "thread-follower-start-turn",
                            "params": {"conversationId": "owner-peer", "turnStart": {
                                "request": {"threadId": "owner-peer", "clientUserMessageId": "owner-attempt",
                                    "input": [{"type": "text", "text": expected_payload, "text_elements": []}]},
                                "context": {"inheritThreadSettings": True, "useUserMessageAdmission": True}}},
                        })
                        pending = json.loads(prewrite[0])
                        self.assertEqual(pending["envelope"], start)
                        self.assertEqual(pending["correlation"], "owner-attempt")
                        self.assertEqual(pending["authorityRefs"], ["synthetic://original-authority"])
                        self.assertEqual(pending["holdRefs"], ["synthetic://original-hold"])
                        self.assertEqual(pending["actor"], actor)
                        self.assertEqual(pending["declaredOrigin"], original["sender"])
                        if not early_response and response_kind is not None:
                            send(response)
                        self.assertEqual(connection.recv(1), b"")
                        closed.set()
                except BaseException as error:
                    errors.append(error)

            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
                listener.bind(str(endpoint))
                listener.listen(1)
                listener.settimeout(1)
                server = threading.Thread(target=serve, args=(listener,))
                server.start()
                try:
                    completed = command(PROTOTYPE, "--request", str(request_file))
                finally:
                    server.join(timeout=5)
                    if server.is_alive():
                        listener.close()
                        server.join(timeout=4)
                self.assertFalse(server.is_alive(), "fixture server did not terminate")
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
                    listener.settimeout(0.1)
                    with self.assertRaises(TimeoutError):
                        listener.accept()
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stderr, "")
            self.assertEqual(errors, [])
            if route_change is not None:
                result = json.loads(completed.stdout)
                self.assertFalse(result["claimed"])
                self.assertEqual(result["peer_input"], "not_attempted")
                self.assertEqual(result["owned_connection"], {"started": False, "closed": False})
                self.assertEqual(wire, [])
                self.assertEqual(list(capture.iterdir()), [])
                self.assertEqual(mailbox("show", "owner-message")["state"], "planned")
                return result, {}
            self.assertTrue(closed.is_set())
            result = json.loads(completed.stdout)
            self.assertEqual(result["receipt"], "unknown")
            self.assertEqual(result["native_branch"], "unknown")
            self.assertTrue(result["ordinary_start_fallback_possible"])
            self.assertEqual(result["projection"]["receipt"], "unknown")
            self.assertEqual(result["projection"]["native_branch"], "unknown")
            self.assertEqual(result["owned_connection"], {"started": True, "closed": True})
            self.assertEqual(result["peer_input"],
                             "not_attempted" if capture_collision else "possible_submission")
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
            recorded = mailbox("show", "owner-message")
            self.assertEqual({k: v for k, v in recorded.items() if k not in {"state", "attempts"}}, original)
            return result, json.loads((capture / "rpc.json").read_bytes())

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
        result, rpc = self.exchange(response_kind=None)
        self.assertEqual(rpc["status"], "unknown")
        self.assertEqual(result["reason"], "rpc-outcome-unknown")

    def test_rpc_error_does_not_claim_no_effect_or_receiver_receipt(self):
        result, rpc = self.exchange(response_kind="error")
        self.assertEqual(rpc["status"], "error")
        self.assertEqual(result["reason"], "rpc-error-effect-unknown")

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
