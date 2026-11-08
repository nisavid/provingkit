"""Mailbox-backed command behavior with test-owned Unix peers and captures."""

import json
import os
from pathlib import Path
import socket
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import unittest


SCRIPTS = (
    Path(__file__).resolve().parents[3]
    / "plugins" / "surreal-intercom" / "skills" / "communicating-with-agents"
    / "scripts"
)


class CodexIpcSenderTests(unittest.TestCase):
    def test_busy_peer_receipt_preserves_forwarded_envelope_and_attempt(self):
        with tempfile.TemporaryDirectory(prefix="codex-ipc-") as temporary:
            root = Path(temporary).resolve()
            store = root / "mailbox.sqlite3"
            capture = root / "capture"
            capture.mkdir()
            original = {
                "message_id": "busy-message", "correlation_id": "shared-exchange",
                "sender": {"thread_id": "origin", "host_id": "origin-host"},
                "recipient": {"thread_id": "busy-peer", "host_id": "peer-host"},
                "owner": {"thread_id": "task-owner", "host_id": "owner-host"},
                "payload": "Keep café and 雪.\nSecond line: 👋",
                "authority_ref": "synthetic://original-authority",
                "holds": ["synthetic://original-hold"],
            }
            actor = {"thread_id": "forwarder", "host_id": "forwarder-host"}
            expected_payload = "Peer message (no new operator authority).\n" + json.dumps({
                "schema": "provingkit-peer-message-v1", "message_id": "busy-message",
                "correlation_id": "shared-exchange", "sender": original["sender"],
                "actor": actor, "recipient": original["recipient"], "owner": original["owner"],
                "authority_ref": "synthetic://original-authority",
                "holds": ["synthetic://original-hold"],
                "payload": "Keep café and 雪.\nSecond line: 👋",
            }, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
            environment = {
                **os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
            }

            def command(script, *arguments):
                return subprocess.run(
                    [sys.executable, "-B", str(SCRIPTS / script),
                     "--store", str(store), *arguments],
                    capture_output=True, text=True, timeout=10, env=environment,
                )

            def mailbox(*arguments):
                completed = command("native_codex_mailbox.py", *arguments)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                return json.loads(completed.stdout)

            message_file = root / "message.json"
            message_file.write_text(json.dumps(original), encoding="utf-8")
            mailbox("init")
            mailbox("plan", "--input", str(message_file))
            self.assertEqual(mailbox("show", "busy-message")["state"], "planned")
            endpoint = root / "peer.sock"
            request = {
                "message_id": "busy-message", "attempt_id": "busy-attempt",
                "actor": actor, "recipient": original["recipient"],
                "evidence_ref": "synthetic://busy-evidence",
                "native": {
                    "route": {"endpoint": str(endpoint), "host": "peer-host", "target": "busy-peer"},
                    "nominationRef": "synthetic://independent-nomination",
                    "purpose": "Forward the original peer message",
                    "authorityRefs": ["synthetic://original-authority"],
                    "holdRefs": ["synthetic://original-hold"],
                    "scope": {"send": True, "acquireLoaded": True,
                              "holdsSatisfied": True, "busyOnly": True},
                    "profile": {}, "observationSeconds": 0.1,
                },
                "capture": {"run_root": str(capture), "allowance_bytes": 8388608,
                            "terminal_provision_bytes": 524288, "later_forecast_bytes": 0},
            }
            request_file = root / "request.json"
            request_file.write_text(json.dumps(request), encoding="utf-8")
            wire, errors, prewrite = [], [], []
            closed = threading.Event()

            def serve(listener):
                try:
                    try:
                        connection, _ = listener.accept()
                    except TimeoutError:
                        return  # The pre-implementation executable never connects.
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
                            self.assertLessEqual(length, 65536)
                            value = json.loads(exact(length))
                            wire.append(value)
                            return value

                        def send(value):
                            data = json.dumps(value).encode()
                            connection.sendall(struct.pack("<I", len(data)) + data)

                        def snapshot(receipt=False):
                            items = [{"type": "steeringUserMessage", "clientUserMessageId": "busy-attempt",
                                      "serverUserMessageId": "native-server-message", "status": "accepted"}] if receipt else []
                            return {
                                "type": "broadcast", "version": 11,
                                "method": "thread-stream-state-changed", "sourceClientId": "native-owner",
                                "targetClientIds": ["native-client"],
                                "params": {"hostId": "peer-host", "conversationId": "busy-peer",
                                           "change": {"type": "snapshot", "revision": 8 if receipt else 7,
                                                      "conversationState": {"id": "busy-peer", "resumeState": "resumed",
                                                          "threadRuntimeStatus": {"type": "active"},
                                                          "turns": [{"turnId": "active-turn", "status": "inProgress", "items": items}]}}},
                            }

                        self.assertEqual(receive(), {"type": "request", "requestId": "initialize", "version": 0,
                                                     "method": "initialize", "params": {"clientType": "cli"}})
                        send({"type": "response", "requestId": "initialize", "resultType": "success",
                              "method": "initialize", "result": {"clientId": "native-client"}})
                        self.assertEqual(receive(), {"type": "request", "requestId": "owner", "sourceClientId": "native-client",
                            "version": 1, "method": "thread-owner-discovery",
                            "params": {"hostId": "peer-host", "conversationId": "busy-peer"}})
                        send({"type": "response", "requestId": "owner", "resultType": "success",
                              "method": "thread-owner-discovery", "handledByClientId": "native-owner"})
                        follow = {"type": "broadcast", "sourceClientId": "native-client", "targetClientIds": ["native-owner"],
                                  "version": 1, "method": "thread-stream-following-changed",
                                  "params": {"hostId": "peer-host", "conversationId": "busy-peer", "following": True}}
                        self.assertEqual(receive(), follow)
                        send(snapshot())
                        steer = receive()
                        # This immutable capture must already exist when the write arrives.
                        prewrite.append((capture / "attempt.json").read_bytes())
                        self.assertEqual(steer, {
                            "type": "request", "requestId": "busy-attempt", "sourceClientId": "native-client",
                            "targetClientId": "native-owner", "version": 1, "method": "thread-follower-steer-turn",
                            "params": {"conversationId": "busy-peer", "attachments": [],
                                "input": [{"type": "text", "text": expected_payload, "text_elements": []}],
                                "clientUserMessageId": "busy-attempt", "restoreMessage": {"id": "busy-attempt",
                                    "context": {"prompt": expected_payload, "fileAttachments": [], "addedFiles": [],
                                        "imageAttachments": [], "pastedTextAttachments": [], "commentAttachments": [], "turnTrigger": "steer"}}},
                        })
                        send({"type": "response", "requestId": "busy-attempt", "resultType": "success",
                              "method": "thread-follower-steer-turn", "result": {}})
                        send(snapshot(receipt=True))
                        follow["params"]["following"] = False
                        self.assertEqual(receive(), follow)
                        # Keep the stream open through cleanup's observation deadline.
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
                    completed = command("codex_ipc_sender.py", "--request", str(request_file))
                finally:
                    server.join(timeout=5)
                    if server.is_alive():
                        listener.close()
                        server.join(timeout=4)
                self.assertFalse(server.is_alive(), "fixture server did not terminate")
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stderr, "")
            result = json.loads(completed.stdout)
            self.assertEqual(result["peer_input"], "received", result)
            self.assertEqual(errors, [])
            self.assertTrue(closed.is_set())
            self.assertTrue(result["claimed"])
            self.assertEqual(result["reason"], "rpc-success-effect-unconfirmed")
            self.assertEqual(result["owned_connection"], {"started": True, "closed": True})
            self.assertEqual(result["projection"]["stage"], "receipt")
            recorded = mailbox("show", "busy-message")
            self.assertEqual({k: v for k, v in recorded.items() if k not in {"state", "attempts"}}, original)
            self.assertEqual(recorded["state"], "received")
            self.assertEqual(len(recorded["attempts"]), 1)
            attempt = recorded["attempts"][0]
            self.assertEqual(attempt["attempt_id"], "busy-attempt")
            self.assertEqual(attempt["actor"], actor)
            self.assertTrue(attempt["received"])
            self.assertFalse(attempt["handled"])
            self.assertFalse(attempt["completed"])
            self.assertEqual([o["kind"] for o in attempt["observations"]], ["unknown", "received"])
            self.assertTrue(all(o["evidence_ref"] == "synthetic://busy-evidence" for o in attempt["observations"]))
            pending = json.loads((capture / "attempt.json").read_bytes())
            self.assertEqual(prewrite, [(capture / "attempt.json").read_bytes()])
            self.assertEqual(pending["envelope"], wire[3])
            self.assertEqual(pending["correlation"], "busy-attempt")
            self.assertEqual(pending["payload"], expected_payload)
            self.assertEqual(pending["actor"], actor)
            self.assertEqual(pending["declaredOrigin"], original["sender"])
            self.assertEqual(pending["authorityRefs"], ["synthetic://original-authority"])
            self.assertEqual(pending["holdRefs"], ["synthetic://original-hold"])
            self.assertEqual(pending["scope"], request["native"]["scope"])
            self.assertEqual(pending["nominationRef"], "synthetic://independent-nomination")
            self.assertEqual(json.loads((capture / "rpc.json").read_bytes())["status"], "success")
            projection = json.loads((capture / "projection.json").read_bytes())
            self.assertEqual(projection, result["projection"])
            self.assertEqual(projection["evidence"][0]["serverUserMessageId"], "native-server-message")
            self.assertEqual(projection["evidence"][0]["observation"]["correlation"], "busy-attempt")
            self.assertEqual(projection["evidence"][0]["observation"]["source"], "native-owner")
            self.assertEqual(json.loads((capture / "outbound.json").read_bytes()), wire)
            received = json.loads((capture / "received.json").read_bytes())
            self.assertEqual(len(received), 5)
            self.assertTrue(all(r[0]["generation"] == pending["binding"]["generation"] for r in received))
            # One immutable claim never sends again, even after a receipt.
            repeated = command("codex_ipc_sender.py", "--request", str(request_file))
            self.assertEqual(repeated.returncode, 0, repeated.stderr)
            self.assertEqual(json.loads(repeated.stdout)["reason"], "claim_not_acquired")
            self.assertEqual(mailbox("show", "busy-message"), recorded)

    def test_reconcile_recovers_original_attempt_receipt_without_peer_input(self):
        self.reconcile_fixture(live_receipt=True)

    def test_reconcile_without_receipt_preserves_original_uncertainty(self):
        self.reconcile_fixture(live_receipt=False)

    def test_reconcile_rejects_saved_receipt_with_different_owner_or_generation(self):
        for observation in (
            {"source": "different-owner", "generation": "original-generation"},
            {"source": "native-owner", "generation": "different-generation"},
        ):
            with self.subTest(observation=observation):
                self.reconcile_fixture(live_receipt=False, saved_observation=observation)

    def test_reconcile_reuses_correctly_bound_saved_receipt_without_acquisition(self):
        self.reconcile_fixture(
            live_receipt=False, known_saved=True,
            saved_observation={"source": "native-owner", "generation": "original-generation"},
        )

    def test_malformed_saved_receipt_refuses_without_reopening_or_changing_original_attempt(self):
        for saved in ([], {"evidence": None}, {"evidence": [None]},
                      {"evidence": [{"stage": "receipt", "source": "native-server-linked-message",
                                     "serverUserMessageId": "historical-server-message", "observation": []}]}):
            with self.subTest(saved=saved):
                self.reconcile_fixture(live_receipt=False, malformed_projection=saved)

    def test_saved_receipt_refusal_is_independent_of_malformed_evidence_order(self):
        receipt = {"stage": "receipt", "source": "native-server-linked-message",
                   "serverUserMessageId": "historical-server-message",
                   "observation": {"host": "peer-host", "target": "busy-peer", "correlation": "busy-attempt",
                                   "source": "native-owner", "generation": "original-generation"}}
        for malformed in (None, {"observation": []}):
            for evidence in ([receipt, malformed], [malformed, receipt]):
                with self.subTest(evidence=evidence):
                    self.reconcile_fixture(live_receipt=False, malformed_projection={
                        "stage": "receipt", "reason": "historical-receipt", "rpc": "unknown", "evidence": evidence,
                    })

    def reconcile_fixture(self, *, live_receipt, saved_observation=None, known_saved=False, malformed_projection=None):
        with tempfile.TemporaryDirectory(prefix="codex-ipc-") as temporary:
            root = Path(temporary).resolve()
            store = root / "mailbox.sqlite3"
            capture = root / "capture"
            capture.mkdir()
            original = {
                "message_id": "busy-message", "correlation_id": "shared-exchange",
                "sender": {"thread_id": "origin", "host_id": "origin-host"},
                "recipient": {"thread_id": "busy-peer", "host_id": "peer-host"},
                "owner": {"thread_id": "task-owner", "host_id": "owner-host"},
                "payload": "Keep café and 雪.\nSecond line: 👋",
                "authority_ref": "synthetic://original-authority",
                "holds": ["synthetic://original-hold"],
            }
            actor = {"thread_id": "forwarder", "host_id": "forwarder-host"}
            expected_payload = "Peer message (no new operator authority).\n" + json.dumps({
                "schema": "provingkit-peer-message-v1", "message_id": "busy-message",
                "correlation_id": "shared-exchange", "sender": original["sender"],
                "actor": actor, "recipient": original["recipient"], "owner": original["owner"],
                "authority_ref": "synthetic://original-authority",
                "holds": ["synthetic://original-hold"],
                "payload": "Keep café and 雪.\nSecond line: 👋",
            }, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
            environment = {
                **os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
            }

            def command(script, *arguments):
                return subprocess.run(
                    [sys.executable, "-B", str(SCRIPTS / script),
                     "--store", str(store), *arguments],
                    capture_output=True, text=True, timeout=10, env=environment,
                )

            def mailbox(*arguments):
                completed = command("native_codex_mailbox.py", *arguments)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                return json.loads(completed.stdout)

            message_file = root / "message.json"
            message_file.write_text(json.dumps(original), encoding="utf-8")
            mailbox("init")
            mailbox("plan", "--input", str(message_file))
            self.assertEqual(mailbox("show", "busy-message")["state"], "planned")
            mailbox("claim", "busy-message", "busy-attempt", "--actor-thread-id", "forwarder",
                    "--actor-host-id", "forwarder-host")
            old = root / "original"
            old.mkdir()
            original_attempt = {
                "correlation": "busy-attempt", "actor": actor, "declaredOrigin": original["sender"],
                "payload": expected_payload,
                "binding": {"host": "peer-host", "target": "busy-peer",
                            "owner": "native-owner", "generation": "original-generation"},
                "authorityRefs": ["synthetic://original-authority"],
                "holdRefs": ["synthetic://original-hold"],
                "scope": {"send": True, "acquireLoaded": True, "holdsSatisfied": True, "busyOnly": True},
            }
            for name, value in (("attempt.json", original_attempt), ("rpc.json", {"status": "unknown"}),
                                ("projection.json", {"stage": "possible-submission", "evidence": [], "rpc": "unknown"})):
                (old / name).write_text(json.dumps(value), encoding="utf-8")
            if saved_observation is not None:
                saved = {
                    "stage": "receipt", "reason": "historical-receipt", "rpc": "unknown",
                    "evidence": [{"stage": "receipt", "source": "native-server-linked-message",
                                  "serverUserMessageId": "historical-server-message",
                                  "observation": {"host": "peer-host", "target": "busy-peer",
                                                  "correlation": "busy-attempt", **saved_observation}}],
                }
                (old / "projection.json").write_text(json.dumps(saved), encoding="utf-8")
            if malformed_projection is not None:
                (old / "projection.json").write_text(json.dumps(malformed_projection), encoding="utf-8")
            original_bytes = {name: (old / name).read_bytes() for name in ("attempt.json", "rpc.json", "projection.json")}
            mailbox("observe", "busy-message", "busy-attempt", "unknown",
                    "--evidence-ref", "synthetic://original-unknown",
                    "--detail-file", str(old / "rpc.json"))
            before = mailbox("show", "busy-message")
            endpoint = root / "peer.sock"
            request = {
                "message_id": "busy-message", "attempt_id": "busy-attempt",
                "actor": {"thread_id": "reader", "host_id": "reader-host"}, "recipient": original["recipient"],
                "evidence_ref": "synthetic://busy-evidence",
                "native": {
                    "route": {"endpoint": str(endpoint), "host": "peer-host", "target": "busy-peer"},
                    "nominationRef": "synthetic://independent-nomination",
                    "purpose": "Forward the original peer message",
                    "authorityRefs": ["synthetic://original-authority"],
                    "holdRefs": ["synthetic://original-hold"],
                    "scope": {"send": False, "acquireLoaded": True,
                              "holdsSatisfied": True, "busyOnly": True},
                    "profile": {}, "observationSeconds": 0.1,
                },
                "capture": {"run_root": str(capture), "allowance_bytes": 8388608,
                            "terminal_provision_bytes": 524288, "later_forecast_bytes": 0},
            }
            request_file = root / "request.json"
            request_file.write_text(json.dumps(request), encoding="utf-8")
            wire, errors = [], []
            closed = threading.Event()

            def serve(listener):
                try:
                    try:
                        connection, _ = listener.accept()
                    except TimeoutError:
                        return  # The pre-implementation executable never connects.
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
                            self.assertLessEqual(length, 65536)
                            value = json.loads(exact(length))
                            wire.append(value)
                            return value

                        def send(value):
                            data = json.dumps(value).encode()
                            connection.sendall(struct.pack("<I", len(data)) + data)

                        def snapshot(receipt=False):
                            items = [{"type": "steeringUserMessage", "clientUserMessageId": "busy-attempt",
                                      "serverUserMessageId": "native-server-message", "status": "accepted"}] if receipt else []
                            return {
                                "type": "broadcast", "version": 11,
                                "method": "thread-stream-state-changed", "sourceClientId": "native-owner",
                                "targetClientIds": ["native-client"],
                                "params": {"hostId": "peer-host", "conversationId": "busy-peer",
                                           "change": {"type": "snapshot", "revision": 8 if receipt else 7,
                                                      "conversationState": {"id": "busy-peer", "resumeState": "resumed",
                                                          "threadRuntimeStatus": {"type": "idle"},
                                                          "turns": [{"turnId": "active-turn", "status": "completed", "items": items}]}}},
                            }

                        self.assertEqual(receive(), {"type": "request", "requestId": "initialize", "version": 0,
                                                     "method": "initialize", "params": {"clientType": "cli"}})
                        send({"type": "response", "requestId": "initialize", "resultType": "success",
                              "method": "initialize", "result": {"clientId": "native-client"}})
                        self.assertEqual(receive(), {"type": "request", "requestId": "owner", "sourceClientId": "native-client",
                            "version": 1, "method": "thread-owner-discovery",
                            "params": {"hostId": "peer-host", "conversationId": "busy-peer"}})
                        send({"type": "response", "requestId": "owner", "resultType": "success",
                              "method": "thread-owner-discovery", "handledByClientId": "native-owner"})
                        follow = {"type": "broadcast", "sourceClientId": "native-client", "targetClientIds": ["native-owner"],
                                  "version": 1, "method": "thread-stream-following-changed",
                                  "params": {"hostId": "peer-host", "conversationId": "busy-peer", "following": True}}
                        self.assertEqual(receive(), follow)
                        send(snapshot(receipt=live_receipt))
                        follow["params"]["following"] = False
                        self.assertEqual(receive(), follow)
                        # Keep the stream open through cleanup's observation deadline.
                        self.assertEqual(connection.recv(1), b"")
                        closed.set()
                except BaseException as error:
                    errors.append(error)

            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
                listener.bind(str(endpoint))
                listener.listen(1)
                if known_saved or malformed_projection is not None:
                    listener.setblocking(False)
                    completed = command("codex_ipc_sender.py", "--request", str(request_file),
                                        "--mode", "reconcile", "--original-attempt", str(old / "attempt.json"))
                    try:
                        connection, _ = listener.accept()
                    except BlockingIOError:
                        pass
                    else:
                        connection.close()
                        self.fail("saved receipt recovery connected to the nominated socket")
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    self.assertEqual(completed.stderr, "")
                    result = json.loads(completed.stdout)
                    self.assertFalse(result["claimed"])
                    if malformed_projection is not None:
                        self.assertEqual(result["peer_input"], "unknown")
                        self.assertEqual(result["reason"], "invalid-original-projection")
                        self.assertEqual(result["owned_connection"], {"started": False, "closed": False})
                        self.assertEqual(list(capture.iterdir()), [])
                        self.assertEqual({name: (old / name).read_bytes() for name in original_bytes}, original_bytes)
                        self.assertEqual(mailbox("show", "busy-message"), before)
                        return
                    self.assertEqual(result["peer_input"], "received")
                    self.assertEqual(result["reason"], "historical-receipt")
                    self.assertEqual(result["projection"], json.loads(original_bytes["projection.json"]))
                    self.assertEqual(result["owned_connection"], {"started": False, "closed": False})
                    self.assertEqual(list(capture.iterdir()), [])
                    for name, data in original_bytes.items():
                        self.assertEqual((old / name).read_bytes(), data)
                    recorded = mailbox("show", "busy-message")
                    self.assertEqual({k: v for k, v in recorded.items() if k not in {"state", "attempts"}}, original)
                    self.assertEqual(recorded["state"], "received")
                    self.assertEqual(len(recorded["attempts"]), 1)
                    attempt = recorded["attempts"][0]
                    self.assertEqual(attempt["attempt_id"], "busy-attempt")
                    self.assertEqual(attempt["actor"], actor)
                    self.assertTrue(attempt["received"])
                    self.assertFalse(attempt["handled"])
                    self.assertFalse(attempt["completed"])
                    self.assertEqual([o["kind"] for o in attempt["observations"]], ["unknown", "received"])
                    self.assertEqual(attempt["observations"][0], before["attempts"][0]["observations"][0])
                    self.assertEqual(attempt["observations"][1]["evidence_ref"], "synthetic://busy-evidence")
                    return
                listener.settimeout(1)
                server = threading.Thread(target=serve, args=(listener,))
                server.start()
                try:
                    completed = command("codex_ipc_sender.py", "--request", str(request_file),
                                        "--mode", "reconcile", "--original-attempt", str(old / "attempt.json"))
                finally:
                    server.join(timeout=5)
                    if server.is_alive():
                        listener.close()
                        server.join(timeout=4)
                self.assertFalse(server.is_alive(), "fixture server did not terminate")
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stderr, "")
            result = json.loads(completed.stdout)
            self.assertEqual(result["peer_input"], "received" if live_receipt else "unknown", result)
            self.assertEqual(errors, [])
            self.assertTrue(closed.is_set())
            self.assertFalse(result["claimed"])
            self.assertEqual(result["reason"], "read-only-reconciliation")
            self.assertEqual(result["owned_connection"], {"started": True, "closed": True})
            if live_receipt:
                self.assertEqual(result["peer_input"], "received", result)
                self.assertEqual(result["projection"]["stage"], "receipt")
                recorded = mailbox("show", "busy-message")
                self.assertEqual({k: v for k, v in recorded.items() if k not in {"state", "attempts"}}, original)
                self.assertEqual(recorded["state"], "received")
                self.assertEqual(len(recorded["attempts"]), 1)
                attempt = recorded["attempts"][0]
                self.assertEqual(attempt["attempt_id"], "busy-attempt")
                self.assertEqual(attempt["actor"], actor)
                self.assertTrue(attempt["received"])
                self.assertFalse(attempt["handled"])
                self.assertFalse(attempt["completed"])
                self.assertEqual([o["kind"] for o in attempt["observations"]], ["unknown", "received"])
                self.assertEqual(attempt["observations"][0], before["attempts"][0]["observations"][0])
                self.assertEqual(attempt["observations"][1]["evidence_ref"], "synthetic://busy-evidence")
                self.assertEqual(result["projection"]["evidence"][0]["serverUserMessageId"], "native-server-message")
            else:
                self.assertEqual(result["projection"]["stage"], "reconcile-unknown")
                self.assertEqual(result["projection"]["evidence"], [])
                self.assertEqual(mailbox("show", "busy-message"), before)
                self.assertEqual(result["peer_input"], "unknown", result)
            for name, data in original_bytes.items():
                self.assertEqual((old / name).read_bytes(), data)
            self.assertEqual(result["original"]["correlation"], "busy-attempt")
            self.assertEqual(result["original"]["actor"], actor)
            self.assertEqual(result["reader_actor"], request["actor"])
            self.assertEqual(result["projection"]["originalActor"], actor)
            self.assertEqual(result["projection"]["consumerActor"], request["actor"])
            self.assertEqual(json.loads((capture / "outbound.json").read_bytes()), wire)
            self.assertEqual([frame["method"] for frame in wire], [
                "initialize", "thread-owner-discovery", "thread-stream-following-changed",
                "thread-stream-following-changed"])
            self.assertFalse((capture / "attempt.json").exists())
            self.assertFalse((capture / "rpc.json").exists())

    def test_wrong_recipient_is_refused_before_claim_capture_or_connection(self):
        with tempfile.TemporaryDirectory(prefix="codex-ipc-") as temporary:
            root = Path(temporary).resolve()
            store = root / "mailbox.sqlite3"
            capture = root / "capture"
            capture.mkdir()
            original = {
                "message_id": "recipient-1",
                "sender": {"thread_id": "sender", "host_id": "local"},
                "recipient": {"thread_id": "planned-peer", "host_id": "peer-host"},
                "owner": {"thread_id": "owner", "host_id": "local"},
                "payload": "Synthetic recipient check.",
                "authority_ref": "synthetic://grant/recipient-check",
            }
            message_file = root / "message.json"
            message_file.write_text(json.dumps(original), encoding="utf-8")
            environment = {
                **os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
            }

            def command(script, *arguments):
                return subprocess.run(
                    [sys.executable, "-B", str(SCRIPTS / script),
                     "--store", str(store), *arguments],
                    capture_output=True, text=True, timeout=10, env=environment,
                )

            def mailbox(*arguments):
                completed = command("native_codex_mailbox.py", *arguments)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                return json.loads(completed.stdout)

            mailbox("init")
            mailbox("plan", "--input", str(message_file))
            planned = mailbox("show", "recipient-1")
            endpoint = root / "peer.sock"
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
                listener.bind(str(endpoint))
                listener.listen(1)
                listener.setblocking(False)
                request = {
                    "message_id": "recipient-1", "attempt_id": "attempt-recipient-1",
                    "actor": original["sender"],
                    "recipient": {"thread_id": "different-peer", "host_id": "peer-host"},
                    "evidence_ref": "synthetic://evidence/recipient-check",
                    "native": {
                        "route": {"endpoint": str(endpoint), "host": "peer-host",
                                  "target": "different-peer"},
                        "nominationRef": "synthetic://nomination/recipient-check",
                        "purpose": "Synthetic recipient check",
                        "authorityRefs": ["synthetic://grant/recipient-check"],
                        "holdRefs": [],
                        "scope": {"send": True, "acquireLoaded": True,
                                  "holdsSatisfied": True, "busyOnly": True},
                        "profile": {}, "observationSeconds": 1,
                    },
                    "capture": {
                        "run_root": str(capture), "allowance_bytes": 8388608,
                        "terminal_provision_bytes": 524288, "later_forecast_bytes": 0,
                    },
                }
                request_file = root / "request.json"
                request_file.write_text(json.dumps(request), encoding="utf-8")
                completed = command("codex_ipc_sender.py", "--request", str(request_file))
                self.assertEqual(mailbox("show", "recipient-1"), planned)
                self.assertEqual(planned["state"], "planned")
                self.assertEqual(planned["attempts"], [])
                self.assertEqual(list(capture.iterdir()), [])
                try:
                    connection, _ = listener.accept()
                except BlockingIOError:
                    pass
                else:
                    connection.close()
                    self.fail("recipient refusal connected to the nominated socket")
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(completed.stderr, "")
                result = json.loads(completed.stdout)
                self.assertIs(result["claimed"], False)
                self.assertEqual(result["peer_input"], "not_attempted")
                self.assertEqual(result["reason"], "recipient_mismatch")
                self.assertEqual(result["owned_connection"], {"started": False, "closed": False})


class CommandFailureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="codex-ipc-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.store = self.root / "mailbox.sqlite3"
        self.capture = self.root / "capture"
        self.capture.mkdir()
        self.endpoint = self.root / "peer.sock"
        self.original = {
            "message_id": "failure-message", "correlation_id": "failure-exchange",
            "sender": {"thread_id": "origin", "host_id": "origin-host"},
            "recipient": {"thread_id": "busy-peer", "host_id": "peer-host"},
            "owner": {"thread_id": "task-owner", "host_id": "owner-host"},
            "payload": "Keep café and 雪.", "authority_ref": "synthetic://authority",
            "holds": ["synthetic://hold"],
        }
        self.actor = {"thread_id": "forwarder", "host_id": "forwarder-host"}
        self.request = {
            "message_id": "failure-message", "attempt_id": "failure-attempt",
            "actor": self.actor, "recipient": self.original["recipient"],
            "evidence_ref": "synthetic://failure-evidence",
            "native": {
                "route": {"endpoint": str(self.endpoint), "host": "peer-host", "target": "busy-peer"},
                "nominationRef": "synthetic://nomination", "purpose": "Forward the original peer message",
                "authorityRefs": ["synthetic://authority"], "holdRefs": ["synthetic://hold"],
                "scope": {"send": True, "acquireLoaded": True, "holdsSatisfied": True, "busyOnly": True},
                "profile": {}, "observationSeconds": 0.1,
            },
            "capture": {"run_root": str(self.capture), "allowance_bytes": 8388608,
                        "terminal_provision_bytes": 524288, "later_forecast_bytes": 0},
        }
        self.request_file = self.root / "request.json"
        message_file = self.root / "message.json"
        message_file.write_text(json.dumps(self.original), encoding="utf-8")
        self.mailbox("init")
        self.mailbox("plan", "--input", str(message_file))

    def tearDown(self):
        evidence_root = os.environ.get("CODEX_IPC_TEST_EVIDENCE_ROOT")
        if evidence_root:
            destination = Path(evidence_root) / self._testMethodName
            destination.mkdir()
            for path in self.root.rglob("*"):
                if path.is_file():
                    target = destination / path.relative_to(self.root)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, target)

    def command(self, script, *arguments):
        completed = subprocess.run(
            [sys.executable, "-B", str(SCRIPTS / script), "--store", str(self.store), *arguments],
            capture_output=True, text=True, timeout=10,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"},
        )
        evidence_root = os.environ.get("CODEX_IPC_TEST_EVIDENCE_ROOT")
        if evidence_root:
            with (Path(evidence_root) / "commands.jsonl").open("a") as stream:
                stream.write(json.dumps({"test": self._testMethodName, "command": completed.args,
                                         "exit": completed.returncode, "stdout": completed.stdout,
                                         "stderr": completed.stderr}) + "\n")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
        return json.loads(completed.stdout)

    def mailbox(self, *arguments):
        return self.command("native_codex_mailbox.py", *arguments)

    def sender(self, *arguments):
        self.request_file.write_text(json.dumps(self.request), encoding="utf-8")
        return self.command("codex_ipc_sender.py", "--request", str(self.request_file), *arguments)

    def assert_no_connection(self, listener):
        listener.setblocking(False)
        try:
            connection, _ = listener.accept()
        except BlockingIOError:
            return
        connection.close()
        self.fail("refused command connected to the nominated socket")

    def test_request_byte_limit_precedes_claim_capture_and_connection(self):
        before = self.mailbox("show", "failure-message")
        self.request["native"]["purpose"] = "x" * 1048576
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(str(self.endpoint))
            listener.listen(1)
            result = self.sender()
            self.assertGreater(self.request_file.stat().st_size, 1048576)
            self.assertEqual(result["reason"], "request-byte-limit")
            self.assertFalse(result["claimed"])
            self.assertEqual(result["peer_input"], "not_attempted")
            self.assertEqual(result["owned_connection"], {"started": False, "closed": False})
            self.assertEqual(self.mailbox("show", "failure-message"), before)
            self.assertEqual(list(self.capture.iterdir()), [])
            self.assert_no_connection(listener)

    def test_malformed_scope_refuses_before_busy_or_idle_claim_and_connection(self):
        before = self.mailbox("show", "failure-message")
        for script in ("codex_ipc_sender.py", "codex_ipc_idle_sender.py"):
            for scope in ([], "not a mapping", None):
                with self.subTest(script=script, scope=scope), socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
                    listener.bind(str(self.endpoint))
                    listener.listen(1)
                    self.request["native"]["scope"] = scope
                    self.request_file.write_text(json.dumps(self.request), encoding="utf-8")
                    result = self.command(script, "--request", str(self.request_file))
                    self.assertFalse(result["claimed"])
                    self.assertEqual(result["peer_input"], "not_attempted")
                    self.assertEqual(result["owned_connection"], {"started": False, "closed": False})
                    self.assertEqual(self.mailbox("show", "failure-message"), before)
                    self.assertEqual(list(self.capture.iterdir()), [])
                    self.assert_no_connection(listener)
                self.endpoint.unlink()

    def test_missing_original_rpc_preserves_known_attempt_uncertainty(self):
        self.mailbox("claim", "failure-message", "failure-attempt", "--actor-thread-id", "forwarder",
                     "--actor-host-id", "forwarder-host")
        old = self.root / "original"
        old.mkdir()
        payload = "Peer message (no new operator authority).\n" + json.dumps({
            "schema": "provingkit-peer-message-v1", "message_id": "failure-message",
            "correlation_id": "failure-exchange", "sender": self.original["sender"],
            "actor": self.actor, "recipient": self.original["recipient"], "owner": self.original["owner"],
            "authority_ref": "synthetic://authority", "holds": ["synthetic://hold"],
            "payload": "Keep café and 雪.",
        }, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        attempt = {
            "correlation": "failure-attempt", "actor": self.actor, "declaredOrigin": self.original["sender"],
            "payload": payload,
            "binding": {"host": "peer-host", "target": "busy-peer", "owner": "native-owner",
                        "generation": "original-generation"},
            "authorityRefs": ["synthetic://authority"], "holdRefs": ["synthetic://hold"],
            "scope": self.request["native"]["scope"],
        }
        (old / "attempt.json").write_text(json.dumps(attempt), encoding="utf-8")
        (old / "projection.json").write_text(
            '{"stage":"possible-submission","rpc":"unknown","evidence":[]}', encoding="utf-8")
        (old / "received.json").write_text('[]', encoding="utf-8")
        self.mailbox("observe", "failure-message", "failure-attempt", "unknown",
                     "--evidence-ref", "synthetic://original-unknown", "--detail-file", str(old / "projection.json"))
        before = self.mailbox("show", "failure-message")
        original_bytes = {p.name: p.read_bytes() for p in old.iterdir()}
        self.request["actor"] = {"thread_id": "reader", "host_id": "reader-host"}
        self.request["native"]["scope"] = {"send": False, "acquireLoaded": True,
                                             "holdsSatisfied": True, "busyOnly": True}
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(str(self.endpoint))
            listener.listen(1)
            result = self.sender("--mode", "reconcile", "--original-attempt", str(old / "attempt.json"))
            self.assertEqual(result["peer_input"], "unknown", result)
            self.assertEqual(result["reason"], "original-rpc-unavailable")
            self.assertFalse(result["claimed"])
            self.assertEqual(result["owned_connection"], {"started": False, "closed": False})
            self.assertEqual(self.mailbox("show", "failure-message"), before)
            self.assertEqual({p.name: p.read_bytes() for p in old.iterdir()}, original_bytes)
            self.assertEqual(list(self.capture.iterdir()), [])
            self.assert_no_connection(listener)

    def snapshot(self, *, owner="native-owner", active=False):
        return {
            "type": "broadcast", "version": 11, "method": "thread-stream-state-changed",
            "sourceClientId": owner, "targetClientIds": ["native-client"],
            "params": {"hostId": "peer-host", "conversationId": "busy-peer",
                       "change": {"type": "snapshot", "revision": 7,
                                  "conversationState": {"id": "busy-peer", "resumeState": "resumed",
                                      "threadRuntimeStatus": {"type": "active" if active else "idle"},
                                      "turns": [{"turnId": "active-turn",
                                                 "status": "inProgress" if active else "completed", "items": []}]}}},
        }

    def peer_exchange(self, conversation, *, null_initialize=False):
        wire, sent, errors = [], [], []
        closed = threading.Event()
        follow = {"type": "broadcast", "sourceClientId": "native-client", "targetClientIds": ["native-owner"],
                  "version": 1, "method": "thread-stream-following-changed",
                  "params": {"hostId": "peer-host", "conversationId": "busy-peer", "following": True}}

        def serve(listener):
            try:
                connection, _ = listener.accept()
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
                        self.assertLessEqual(length, 65536)
                        value = json.loads(exact(length))
                        wire.append(value)
                        return value

                    def send(value, *additional):
                        values = (value, *additional)
                        frames = []
                        for item in values:
                            body = item if isinstance(item, bytes) else json.dumps(item).encode()
                            frames.append(struct.pack("<I", len(body)) + body)
                        data = b"".join(frames)
                        connection.sendall(data)
                        with (self.root / "fixture-sent.bin").open("ab") as stream:
                            stream.write(data)
                        sent.extend({"rawBodyHex": item.hex()} if isinstance(item, bytes) else item
                                    for item in values)

                    self.assertEqual(receive(), {"type": "request", "requestId": "initialize", "version": 0,
                                                 "method": "initialize", "params": {"clientType": "cli"}})
                    send({"type": "response", "requestId": "initialize", "resultType": "success",
                          "method": "initialize",
                          "result": None if null_initialize else {"clientId": "native-client"}})
                    if null_initialize:
                        self.assertEqual(connection.recv(1), b"")
                    else:
                        self.assertEqual(receive(), {"type": "request", "requestId": "owner", "sourceClientId": "native-client",
                            "version": 1, "method": "thread-owner-discovery",
                            "params": {"hostId": "peer-host", "conversationId": "busy-peer"}})
                        send({"type": "response", "requestId": "owner", "resultType": "success",
                              "method": "thread-owner-discovery", "handledByClientId": "native-owner"})
                        self.assertEqual(receive(), follow)
                        conversation(connection, receive, send, follow)
                self.assertEqual(connection.fileno(), -1)
                closed.set()
            except BaseException as error:
                errors.append(error)

        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(str(self.endpoint))
            listener.listen(1)
            listener.settimeout(3)
            server = threading.Thread(target=serve, args=(listener,))
            server.start()
            try:
                result = self.sender()
            finally:
                server.join(timeout=5)
                if server.is_alive():
                    listener.close()
                    server.join(timeout=4)
            self.assertFalse(server.is_alive(), "fixture peer did not terminate")
            self.assertEqual(errors, [])
            self.assertTrue(closed.is_set(), "fixture accepted socket did not close")
            listener.setblocking(False)
            recorded = self.mailbox("show", "failure-message")
            capture_bytes = {p.name: p.read_bytes() for p in self.capture.iterdir()}
            repeated = self.sender()
            self.assertEqual(repeated["reason"], "claim_not_acquired")
            self.assertFalse(repeated["claimed"])
            self.assertEqual(repeated["owned_connection"], {"started": False, "closed": False})
            self.assert_no_connection(listener)
            self.assertEqual(self.mailbox("show", "failure-message"), recorded)
            self.assertEqual({p.name: p.read_bytes() for p in self.capture.iterdir()}, capture_bytes)
        (self.root / "fixture-wire.json").write_text(json.dumps({"received": wire, "sent": sent}), encoding="utf-8")
        self.assertTrue(result["claimed"])
        self.assertEqual(result["owned_connection"], {"started": True, "closed": True})
        self.assertEqual(recorded["state"], "unknown")
        self.assertEqual(len(recorded["attempts"]), 1)
        self.assertEqual(recorded["attempts"][0]["attempt_id"], "failure-attempt")
        self.assertEqual([o["kind"] for o in recorded["attempts"][0]["observations"]], ["unknown"])
        self.assertFalse(recorded["attempts"][0]["received"])
        self.assertEqual({k: v for k, v in recorded.items() if k not in {"state", "attempts"}}, self.original)
        self.assertEqual(json.loads((self.capture / "outbound.json").read_bytes())[:len(wire)], wire)
        return result, wire, sent

    def test_null_initialize_result_reports_refusal_and_preserves_evidence_without_peer_input(self):
        result, wire, sent = self.peer_exchange(None, null_initialize=True)
        self.assertEqual(result["reason"], "initialize-unavailable")
        self.assertEqual(result["peer_input"], "not_attempted")
        self.assertEqual(result["projection"]["stage"], "refused-before-write")
        self.assertEqual(result["projection"]["reason"], "initialize-unavailable")
        self.assertEqual(result["projection"]["closure"], "no-subscription;owned-connection-closed")
        self.assertEqual(result["projection"]["evidence"], [])
        self.assertEqual([frame["method"] for frame in wire], ["initialize"])
        self.assertEqual(sent, [{
            "type": "response", "requestId": "initialize", "resultType": "success",
            "method": "initialize", "result": None,
        }])
        self.assertEqual(json.loads((self.capture / "outbound.json").read_bytes()), wire)
        received = json.loads((self.capture / "received.json").read_bytes())
        self.assertEqual([frame for _, frame in received], sent)
        self.assertEqual(json.loads((self.capture / "projection.json").read_bytes()), result["projection"])
        acquisition = json.loads((self.capture / "acquisition.json").read_bytes())
        self.assertGreater(acquisition["incomingBytes"], 0)
        self.assertEqual(received[0][0]["generation"], acquisition["connectionGeneration"])
        captured_request = json.loads((self.capture / "request-input.json").read_bytes())
        self.assertEqual(captured_request["correlation"], "failure-attempt")
        self.assertEqual(captured_request["route"]["host"], "peer-host")
        self.assertEqual(captured_request["route"]["target"], "busy-peer")
        self.assertEqual(captured_request["actor"], self.request["actor"])
        self.assertTrue((self.capture / "normalized-input.json").is_file())
        self.assertFalse((self.capture / "attempt.json").exists())
        self.assertFalse((self.capture / "rpc.json").exists())
        self.assertNotIn("capture_failure", result)

    def test_idle_peer_refuses_start_and_keeps_claim_uncertainty(self):
        def conversation(connection, receive, send, follow):
            send(self.snapshot())
            follow["params"]["following"] = False
            self.assertEqual(receive(), follow)
            self.assertEqual(connection.recv(1), b"")
        result, wire, sent = self.peer_exchange(conversation)
        self.assertEqual(result["reason"], "busy-only-start-forbidden")
        self.assertEqual(result["peer_input"], "not_attempted")
        self.assertEqual(result["projection"]["stage"], "refused-before-write")
        self.assertEqual(result["projection"]["evidence"], [])
        self.assertEqual([m["method"] for m in wire], ["initialize", "thread-owner-discovery",
            "thread-stream-following-changed", "thread-stream-following-changed"])
        self.assertEqual([m for _, m in json.loads((self.capture / "received.json").read_bytes())], sent)
        self.assertFalse((self.capture / "attempt.json").exists())
        self.assertFalse((self.capture / "rpc.json").exists())

    def test_snapshot_from_different_owner_is_rejected_before_peer_input(self):
        def conversation(connection, receive, send, follow):
            send(self.snapshot(owner="different-owner", active=True))
            follow["params"]["following"] = False
            self.assertEqual(receive(), follow)
            self.assertEqual(connection.recv(1), b"")
        result, wire, sent = self.peer_exchange(conversation)
        self.assertEqual(result["reason"], "unmatched-state-binding")
        self.assertEqual(result["peer_input"], "not_attempted")
        self.assertEqual(result["projection"]["stage"], "refused-before-write")
        self.assertEqual(result["projection"]["evidence"], [])
        self.assertEqual([m["method"] for m in wire], ["initialize", "thread-owner-discovery",
            "thread-stream-following-changed", "thread-stream-following-changed"])
        self.assertEqual([m for _, m in json.loads((self.capture / "received.json").read_bytes())], sent)
        self.assertFalse((self.capture / "attempt.json").exists())
        self.assertFalse((self.capture / "rpc.json").exists())

    def test_peer_close_after_exact_steer_preserves_possible_submission_and_no_resend(self):
        expected_payload = "Peer message (no new operator authority).\n" + json.dumps({
            "schema": "provingkit-peer-message-v1", "message_id": "failure-message",
            "correlation_id": "failure-exchange", "sender": self.original["sender"],
            "actor": self.actor, "recipient": self.original["recipient"], "owner": self.original["owner"],
            "authority_ref": "synthetic://authority", "holds": ["synthetic://hold"],
            "payload": "Keep café and 雪.",
        }, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        prewrite = []
        expected_steer = {
            "type": "request", "requestId": "failure-attempt", "sourceClientId": "native-client",
            "targetClientId": "native-owner", "version": 1, "method": "thread-follower-steer-turn",
            "params": {"conversationId": "busy-peer", "attachments": [],
                "input": [{"type": "text", "text": expected_payload, "text_elements": []}],
                "clientUserMessageId": "failure-attempt", "restoreMessage": {"id": "failure-attempt",
                    "context": {"prompt": expected_payload, "fileAttachments": [], "addedFiles": [],
                        "imageAttachments": [], "pastedTextAttachments": [], "commentAttachments": [], "turnTrigger": "steer"}}},
        }

        def conversation(connection, receive, send, follow):
            send(self.snapshot(active=True))
            self.assertEqual(receive(), expected_steer)
            prewrite.append((self.capture / "attempt.json").read_bytes())
            # Returning closes the actual accepted socket without an RPC reply.
        result, wire, sent = self.peer_exchange(conversation)
        self.assertEqual(result["peer_input"], "possible_submission")
        self.assertEqual(result["reason"], "stream-eof-unknown")
        self.assertEqual(result["projection"]["stage"], "possible-submission")
        self.assertEqual(result["projection"]["rpc"], "unknown")
        self.assertEqual(result["projection"]["evidence"], [])
        self.assertEqual([m["method"] for m in wire], ["initialize", "thread-owner-discovery",
            "thread-stream-following-changed", "thread-follower-steer-turn"])
        self.assertEqual(wire[3], expected_steer)
        pending = json.loads((self.capture / "attempt.json").read_bytes())
        self.assertEqual(prewrite, [(self.capture / "attempt.json").read_bytes()])
        self.assertEqual(pending["envelope"], expected_steer)
        self.assertEqual(pending["correlation"], "failure-attempt")
        self.assertEqual(pending["payload"], expected_payload)
        self.assertEqual(pending["actor"], self.actor)
        self.assertEqual(pending["declaredOrigin"], self.original["sender"])
        self.assertEqual(pending["authorityRefs"], ["synthetic://authority"])
        self.assertEqual(pending["holdRefs"], ["synthetic://hold"])
        self.assertEqual(pending["scope"], self.request["native"]["scope"])
        rpc = json.loads((self.capture / "rpc.json").read_bytes())
        self.assertEqual(rpc["status"], "unknown")
        self.assertEqual(rpc["originalResult"], [])
        self.assertEqual(rpc["effect"], "possible-submission")
        self.assertEqual(rpc["submitObservation"]["terminalReason"], "stream-eof-unknown")
        self.assertEqual(json.loads((self.capture / "projection.json").read_bytes()), result["projection"])
        self.assertEqual([m for _, m in json.loads((self.capture / "received.json").read_bytes())], sent)
        outbound = json.loads((self.capture / "outbound.json").read_bytes())
        self.assertEqual(outbound[:4], wire)
        self.assertEqual(outbound[4]["method"], "thread-stream-following-changed")
        self.assertFalse(outbound[4]["params"]["following"])
        self.assertEqual(len(outbound), 5)

    def test_unhashable_correlated_result_type_preserves_unknown_submission_and_captures(self):
        response = {
            "type": "response", "requestId": "failure-attempt", "resultType": [],
            "method": "thread-follower-steer-turn", "result": {},
        }
        prewrite = []

        def conversation(connection, receive, send, follow):
            send(self.snapshot(active=True))
            steer = receive()
            self.assertEqual(steer["method"], "thread-follower-steer-turn")
            self.assertEqual(steer["requestId"], "failure-attempt")
            prewrite.append((self.capture / "attempt.json").read_bytes())
            send(response)
            follow["params"]["following"] = False
            self.assertEqual(receive(), follow)
            self.assertEqual(connection.recv(1), b"")

        result, wire, sent = self.peer_exchange(conversation)
        self.assertEqual(result["reason"], "rpc-unknown-effect-unconfirmed")
        self.assertEqual(result["peer_input"], "possible_submission")
        self.assertEqual(result["projection"]["stage"], "possible-submission")
        self.assertEqual(result["projection"]["rpc"], "unknown")
        self.assertTrue(result["projection"]["closure"].endswith(";owned-connection-closed"))
        rpc = json.loads((self.capture / "rpc.json").read_bytes())
        self.assertEqual(rpc["status"], "unknown")
        self.assertEqual(rpc["originalResult"], [response])
        self.assertEqual(rpc["submitObservation"]["status"], "unknown")
        self.assertEqual(rpc["submitObservation"]["originalResult"], [response])
        self.assertEqual(rpc["effect"], "possible-submission")
        self.assertEqual(prewrite, [(self.capture / "attempt.json").read_bytes()])
        self.assertEqual(json.loads(prewrite[0])["envelope"], wire[3])
        self.assertEqual([frame for _, frame in json.loads(
            (self.capture / "received.json").read_bytes())], sent)
        for name in ("request-input.json", "normalized-input.json", "acquisition.json", "projection.json"):
            self.assertTrue((self.capture / name).is_file(), name)

    def test_decoder_recursion_after_rpc_preserves_prefix_and_closes(self):
        self.decoder_recursion_fixture(during_cleanup=False)

    def test_decoder_recursion_during_cleanup_preserves_rpc_and_closes(self):
        self.decoder_recursion_fixture(during_cleanup=True)

    def decoder_recursion_fixture(self, *, during_cleanup):
        raw = b'{"unused":' + b"[" * 10000 + b"0" + b"]" * 10000 + b"}"
        self.assertLess(len(raw), 65536)
        try:
            json.loads(raw)
        except RecursionError:
            pass
        else:
            self.skipTest("Decoder accepts this bounded nesting; no recursion-failure case on this interpreter.")
        response = {
            "type": "response", "requestId": "failure-attempt", "resultType": "success",
            "method": "thread-follower-steer-turn", "result": {},
        }
        prewrite = []

        def conversation(connection, receive, send, follow):
            send(self.snapshot(active=True))
            steer = receive()
            self.assertEqual(steer["method"], "thread-follower-steer-turn")
            self.assertEqual(steer["requestId"], "failure-attempt")
            prewrite.append((self.capture / "attempt.json").read_bytes())
            send(response) if during_cleanup else send(response, raw)
            follow["params"]["following"] = False
            self.assertEqual(receive(), follow)
            if during_cleanup:
                send(raw)
            self.assertEqual(connection.recv(1), b"")

        result, wire, sent = self.peer_exchange(conversation)
        self.assertEqual(result["reason"], "frame-decode-error")
        self.assertEqual(result["peer_input"], "possible_submission")
        self.assertEqual(result["projection"]["stage"], "possible-submission")
        self.assertEqual(result["projection"]["rpc"], "success")
        self.assertTrue(result["projection"]["closure"].endswith(";owned-connection-closed"))
        rpc = json.loads((self.capture / "rpc.json").read_bytes())
        self.assertEqual(rpc["status"], "success")
        self.assertEqual(rpc["originalResult"], [response])
        self.assertEqual(rpc["effect"], "possible-submission")
        received = json.loads((self.capture / "received.json").read_bytes())
        self.assertIn(response, [frame for _, frame in received])
        self.assertEqual(len(received), len(sent) - 1)
        acquisition = json.loads((self.capture / "acquisition.json").read_bytes())
        self.assertIn("frame-decode-error", acquisition["receiveStatus"])
        self.assertEqual(acquisition["events"], len(received) + 1)
        self.assertEqual(acquisition["incomingBytes"], (self.root / "fixture-sent.bin").stat().st_size)
        self.assertEqual(prewrite, [(self.capture / "attempt.json").read_bytes()])
        self.assertEqual(json.loads(prewrite[0])["envelope"], wire[3])
        for name in ("request-input.json", "normalized-input.json", "projection.json"):
            self.assertTrue((self.capture / name).is_file(), name)

    def test_malformed_post_write_snapshot_and_cleanup_preserve_known_submission(self):
        self.malformed_evidence_fixture(malformed_after_write=True)

    def test_first_post_write_refusal_survives_malformed_cleanup(self):
        self.malformed_evidence_fixture(malformed_after_write=False)

    def test_malformed_canonical_history_during_cleanup_preserves_rpc_and_closure(self):
        self.malformed_evidence_fixture(malformed_after_write=True, canonical_stage="cleanup")

    def test_malformed_canonical_history_after_submission_preserves_rpc_and_closure(self):
        self.malformed_evidence_fixture(malformed_after_write=True, canonical_stage="post-write")

    def test_first_refusal_survives_malformed_canonical_cleanup(self):
        self.malformed_evidence_fixture(malformed_after_write=False, canonical_stage="cleanup")

    def malformed_evidence_fixture(self, *, malformed_after_write, canonical_stage=None):
        response = {
            "type": "response", "requestId": "failure-attempt", "resultType": "success",
            "method": "thread-follower-steer-turn", "result": {},
        }
        if malformed_after_write:
            post_write = self.snapshot(active=True)
            post_write["params"]["change"]["revision"] = 8
            post_write["params"]["change"]["conversationState"]["turns"][0]["itemsPagination"] = None
        else:
            post_write = {"type": "broadcast", "method": "ipc-connection-reset"}
        cleanup = {"type": "broadcast", "method": "client-status-changed", "params": None}
        if canonical_stage is not None:
            malformed = self.snapshot(active=True)
            malformed["params"]["change"]["revision"] = 8 if canonical_stage == "post-write" else 9
            malformed["params"]["change"]["conversationState"]["turnHistory"] = {
                "kind": "canonical", "history": {
                    "islands": [{"entries": [{"value": 0}]}],
                    "entitiesByKey": [], "isComplete": True,
                },
            }
            if canonical_stage == "post-write":
                post_write = malformed
                cleanup = self.snapshot(active=True)
                cleanup["params"]["change"]["revision"] = 9
            else:
                cleanup = malformed
                if malformed_after_write:
                    post_write = self.snapshot(active=True)
                    post_write["params"]["change"]["revision"] = 8
        prewrite = []

        def conversation(connection, receive, send, follow):
            initial = self.snapshot(active=True)
            if canonical_stage is not None:
                original_turn = initial["params"]["change"]["conversationState"]["turns"][0]
                initial["params"]["change"]["conversationState"]["turnHistory"] = {
                    "kind": "canonical", "history": {
                        "islands": [{"entries": [{"value": "initial-turn"}]}],
                        "entitiesByKey": {"initial-turn": original_turn}, "isComplete": True,
                    },
                }
            send(initial)
            steer = receive()
            self.assertEqual(steer["method"], "thread-follower-steer-turn")
            self.assertEqual(steer["requestId"], "failure-attempt")
            self.assertEqual(steer["params"]["clientUserMessageId"], "failure-attempt")
            prewrite.append((self.capture / "attempt.json").read_bytes())
            send(response, post_write)
            follow["params"]["following"] = False
            self.assertEqual(receive(), follow)
            send(cleanup)
            # EOF is observed on the accepted socket, rather than inferred from
            # the fixture closing its own end.
            self.assertEqual(connection.recv(1), b"")

        result, wire, sent = self.peer_exchange(conversation)
        rpc = json.loads((self.capture / "rpc.json").read_bytes())
        self.assertEqual(rpc["status"], "success")
        self.assertEqual(rpc["originalResult"], [response])
        self.assertEqual(rpc["submitObservation"]["status"], "success")
        self.assertEqual(rpc["submitObservation"]["originalResult"], [response])
        self.assertEqual(rpc["effect"], "possible-submission")
        self.assertEqual(result["peer_input"], "possible_submission")
        self.assertEqual(result["projection"]["stage"], "possible-submission")
        self.assertEqual(result["projection"]["rpc"], "success")
        self.assertEqual(result["projection"]["evidence"], [])
        self.assertEqual(result["reason"], result["projection"]["reason"])
        if canonical_stage is not None and malformed_after_write:
            self.assertEqual(result["reason"], "unsupported-turn-history")
        if malformed_after_write:
            self.assertIsInstance(result["reason"], str)
            self.assertTrue(result["reason"])
            self.assertNotIn(result["reason"], {
                "invalid_request", "missing-state", "rpc-success-effect-unconfirmed",
                "observation-deadline-unknown",
            })
        else:
            self.assertEqual(result["reason"], "connection-reset-needs-new-binding")
        self.assertTrue(result["projection"]["closure"].endswith(";owned-connection-closed"))
        self.assertNotIn("capture_failure", result)
        self.assertEqual([m["method"] for m in wire], [
            "initialize", "thread-owner-discovery", "thread-stream-following-changed",
            "thread-follower-steer-turn", "thread-stream-following-changed",
        ])
        self.assertFalse(wire[-1]["params"]["following"])
        self.assertEqual(json.loads((self.capture / "outbound.json").read_bytes()), wire)
        self.assertEqual(prewrite, [(self.capture / "attempt.json").read_bytes()])
        pending = json.loads(prewrite[0])
        self.assertEqual(pending["envelope"], wire[3])
        self.assertEqual(pending["correlation"], "failure-attempt")
        self.assertEqual(pending["actor"], self.actor)
        self.assertEqual(pending["declaredOrigin"], self.original["sender"])
        self.assertEqual(pending["scope"], self.request["native"]["scope"])
        received = json.loads((self.capture / "received.json").read_bytes())
        self.assertEqual([m for _, m in received], sent)
        self.assertEqual(sent[-3:], [response, post_write, cleanup])
        self.assertEqual(json.loads((self.capture / "projection.json").read_bytes()), result["projection"])
        acquisition = json.loads((self.capture / "acquisition.json").read_bytes())
        self.assertEqual(acquisition["events"], len(sent))
        self.assertEqual(acquisition["incomingBytes"], (self.root / "fixture-sent.bin").stat().st_size)
        self.assertEqual({record["generation"] for record, _ in received}, {acquisition["connectionGeneration"]})
        captured_request = json.loads((self.capture / "request-input.json").read_bytes())
        self.assertEqual(captured_request["correlation"], "failure-attempt")
        self.assertEqual(captured_request["actor"], self.actor)
        self.assertEqual(captured_request["route"], self.request["native"]["route"])
        self.assertTrue((self.capture / "normalized-input.json").is_file())

    def test_missing_discovery_request_id_preserves_correlated_rpc_and_stops_acquisition(self):
        response = {
            "type": "response", "requestId": "failure-attempt", "resultType": "success",
            "method": "thread-follower-steer-turn", "result": {},
        }
        malformed = {"type": "client-discovery-request"}
        unread = {"type": "client-discovery-request", "requestId": "must-not-be-answered"}
        prewrite = []

        def conversation(connection, receive, send, follow):
            send(self.snapshot(active=True))
            steer = receive()
            self.assertEqual(steer["method"], "thread-follower-steer-turn")
            self.assertEqual(steer["requestId"], "failure-attempt")
            self.assertEqual(steer["params"]["clientUserMessageId"], "failure-attempt")
            prewrite.append((self.capture / "attempt.json").read_bytes())
            # Coalescing removes a race between rejecting the malformed frame
            # and placing the later, deliberately unread frame on the wire.
            send(response, malformed, unread)
            try:
                if connection.recv(1, socket.MSG_PEEK):
                    follow["params"]["following"] = False
                    self.assertEqual(receive(), follow)
                self.assertEqual(connection.recv(1), b"")
            except ConnectionResetError:
                pass  # Closing with the unread tail can reset the peer socket.

        result, wire, sent = self.peer_exchange(conversation)
        rpc = json.loads((self.capture / "rpc.json").read_bytes())
        self.assertEqual(rpc["status"], "success")
        self.assertEqual(rpc["originalResult"], [response])
        self.assertEqual(rpc["submitObservation"]["status"], "success")
        self.assertEqual(rpc["submitObservation"]["originalResult"], [response])
        terminal = rpc["submitObservation"]["terminalReason"]
        self.assertIsInstance(terminal, str)
        self.assertTrue(terminal)
        self.assertNotIn(terminal, {
            "invalid_request", "observation-deadline-unknown",
            "stream-eof-unknown", "rpc-success-effect-unconfirmed",
        })
        self.assertEqual(rpc["transportReason"], terminal)
        self.assertEqual(rpc["effect"], "possible-submission")
        self.assertEqual(result["reason"], terminal)
        self.assertEqual(result["peer_input"], "possible_submission")
        self.assertEqual(result["projection"]["stage"], "possible-submission")
        self.assertEqual(result["projection"]["rpc"], "success")
        self.assertEqual(result["projection"]["acquisitionReason"], terminal)
        self.assertEqual(result["projection"]["evidence"], [])
        self.assertTrue(result["projection"]["closure"].endswith(";owned-connection-closed"))
        self.assertNotIn("capture_failure", result)
        self.assertEqual([m["method"] for m in wire[:4]], [
            "initialize", "thread-owner-discovery", "thread-stream-following-changed",
            "thread-follower-steer-turn",
        ])
        self.assertLessEqual(len(wire), 5)
        if len(wire) == 5:
            self.assertEqual(wire[4]["method"], "thread-stream-following-changed")
            self.assertFalse(wire[4]["params"]["following"])
        outbound = json.loads((self.capture / "outbound.json").read_bytes())
        self.assertEqual(outbound[:4], wire[:4])
        self.assertLessEqual(len(outbound), 5)
        if len(outbound) == 5:
            self.assertEqual(outbound[4]["method"], "thread-stream-following-changed")
            self.assertFalse(outbound[4]["params"]["following"])
        self.assertEqual(prewrite, [(self.capture / "attempt.json").read_bytes()])
        self.assertEqual(json.loads(prewrite[0])["envelope"], wire[3])
        received = json.loads((self.capture / "received.json").read_bytes())
        self.assertEqual([m for _, m in received], sent[:-1])
        self.assertEqual(sent[-3:], [response, malformed, unread])
        self.assertEqual(json.loads((self.capture / "projection.json").read_bytes()), result["projection"])
        acquisition = json.loads((self.capture / "acquisition.json").read_bytes())
        self.assertIn(terminal, acquisition["receiveStatus"])
        self.assertEqual(acquisition["events"], len(sent) - 1)
        unread_bytes = 4 + len(json.dumps(unread).encode())
        self.assertEqual(acquisition["incomingBytes"],
                         (self.root / "fixture-sent.bin").stat().st_size - unread_bytes)
        self.assertEqual({record["generation"] for record, _ in received}, {acquisition["connectionGeneration"]})

    def test_frame_limit_diagnosis_survives_later_projection_capture_failure(self):
        sentinel = b"Keep this original projection sentinel.\n"
        (self.capture / "projection.json").write_bytes(sentinel)

        def conversation(connection, receive, send, follow):
            header = struct.pack("<I", 65537)
            (self.root / "fixture-announced-header.bin").write_bytes(header)
            connection.sendall(header)  # No body is sent for this rejected length.
            follow["params"]["following"] = False
            self.assertEqual(receive(), follow)
            self.assertEqual(connection.recv(1), b"")
        result, wire, sent = self.peer_exchange(conversation)
        self.assertEqual(result["reason"], "frame-byte-limit")
        self.assertEqual(result["peer_input"], "not_attempted")
        self.assertEqual(result["projection"]["stage"], "refused-before-write")
        self.assertEqual(result["projection"]["evidence"], [])
        self.assertEqual(result["capture_failure"]["originalFailure"]["message"], "frame-byte-limit")
        self.assertEqual(result["capture_failure"]["originalFailure"]["type"], "ReceivePrefixFailure")
        self.assertEqual(result["capture_failure"]["missingEvidence"], {"projection.json": "UNKNOWN"})
        self.assertEqual(len(result["capture_failure"]["captureFailures"]), 1)
        self.assertEqual(result["capture_failure"]["captureFailures"][0]["path"], "projection.json")
        self.assertEqual(result["capture_failure"]["captureFailures"][0]["type"], "FileExistsError")
        self.assertEqual((self.capture / "projection.json").read_bytes(), sentinel)
        self.assertEqual([m["method"] for m in wire], ["initialize", "thread-owner-discovery",
            "thread-stream-following-changed", "thread-stream-following-changed"])
        received = json.loads((self.capture / "received.json").read_bytes())
        self.assertEqual([m for _, m in received], sent)
        self.assertEqual(len(received), 2)
        self.assertEqual([m["method"] for _, m in received], ["initialize", "thread-owner-discovery"])
        prefix_size = (self.root / "fixture-sent.bin").stat().st_size
        acquisition = json.loads((self.capture / "acquisition.json").read_bytes())
        self.assertEqual(acquisition["rejectedFrame"], {
            "announcedLength": 65537, "frameBytes": 65536, "wireOffset": prefix_size})
        self.assertEqual(acquisition["incomingBytes"], prefix_size + 4)
        self.assertEqual(acquisition["events"], 2)
        self.assertEqual(acquisition["receiveStatus"], ["frame-byte-limit", "receive-disabled:frame-byte-limit"])
        self.assertEqual({r["generation"] for r, _ in received}, {acquisition["connectionGeneration"]})
        self.assertFalse((self.capture / "attempt.json").exists())
        self.assertFalse((self.capture / "rpc.json").exists())
