"""Mailbox-backed command behavior with test-owned Unix peers and captures."""

import hashlib
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
    Path(__file__).resolve().parents[2]
    / "plugins" / "rolecasting" / "skills" / "delegating-cross-agent-work"
    / "scripts"
)


class CodexIdleSenderTests(unittest.TestCase):
    def test_explicit_idle_intent_retains_one_uncertain_original_submission(self):
        with tempfile.TemporaryDirectory(prefix="codex-ipc-") as temporary:
            root = Path(temporary)
            store = root / "mailbox.sqlite3"
            capture = root / "capture"
            capture.mkdir()
            original = {
                "message_id": "idle-message", "correlation_id": "shared-exchange",
                "sender": {"thread_id": "origin", "host_id": "origin-host"},
                "recipient": {"thread_id": "idle-peer", "host_id": "peer-host"},
                "owner": {"thread_id": "task-owner", "host_id": "owner-host"},
                "payload": "Keep café and 雪.\nSecond line: 👋",
                "authority_ref": "synthetic://original-authority",
                "holds": ["synthetic://original-hold"],
            }
            actor = {"thread_id": "forwarder", "host_id": "forwarder-host"}
            expected_payload = "Peer message (no new operator authority).\n" + json.dumps({
                "schema": "provingkit-peer-message-v1", "message_id": "idle-message",
                "correlation_id": "shared-exchange", "sender": {"thread_id": "origin", "host_id": "origin-host"},
                "actor": {"thread_id": "forwarder", "host_id": "forwarder-host"}, "recipient": {"thread_id": "idle-peer", "host_id": "peer-host"}, "owner": {"thread_id": "task-owner", "host_id": "owner-host"},
                "authority_ref": "synthetic://original-authority",
                "holds": ["synthetic://original-hold"],
                "payload": "Keep café and 雪.\nSecond line: 👋",
            }, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
            environment = {
                **os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
            }

            commands = []

            def command(script, *arguments):
                completed = subprocess.run(
                    [sys.executable, "-B", str(SCRIPTS / script),
                     "--store", str(store), *arguments],
                    capture_output=True, text=True, timeout=10, env=environment,
                )
                commands.append({"argv": completed.args, "exit": completed.returncode,
                                 "stdout": completed.stdout, "stderr": completed.stderr})
                evidence = os.environ.get("IDLE_SLICE_EVIDENCE")
                if evidence:
                    Path(evidence, "commands.json").write_text(json.dumps(commands, indent=2))
                return completed

            def mailbox(*arguments):
                completed = command("native_codex_mailbox.py", *arguments)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                return json.loads(completed.stdout)

            message_file = root / "message.json"
            message_file.write_text(json.dumps(original), encoding="utf-8")
            mailbox("init")
            mailbox("plan", "--input", str(message_file))
            self.assertEqual(mailbox("show", "idle-message")["state"], "planned")
            endpoint = root / "peer.sock"
            request = {
                "message_id": "idle-message", "attempt_id": "idle-attempt",
                "actor": actor, "recipient": original["recipient"],
                "evidence_ref": "synthetic://idle-evidence",
                "native": {
                    "route": {"endpoint": str(endpoint), "host": "peer-host", "target": "idle-peer"},
                    "nominationRef": "synthetic://independent-nomination",
                    "purpose": "Forward the original peer message",
                    "authorityRefs": ["synthetic://original-authority"],
                    "holdRefs": ["synthetic://original-hold"],
                    "scope": {"send": True, "acquireLoaded": True,
                              "holdsSatisfied": True, "idleStartIntent": True},
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

                        def snapshot():
                            return {
                                "type": "broadcast", "version": 11,
                                "method": "thread-stream-state-changed", "sourceClientId": "native-owner",
                                "targetClientIds": ["native-client"],
                                "params": {"hostId": "peer-host", "conversationId": "idle-peer",
                                    "change": {"type": "snapshot", "revision": 7,
                                        "conversationState": {"id": "idle-peer", "resumeState": "resumed",
                                            "mode": "durable", "threadStartKind": "default", "threadSource": "user",
                                            "threadRuntimeStatus": {"type": "idle"},
                                            "turns": [{"turnId": "previous-turn", "status": "completed", "items": []}]}}},
                            }

                        self.assertEqual(receive(), {"type": "request", "requestId": "initialize", "version": 0,
                                                     "method": "initialize", "params": {"clientType": "cli"}})
                        send({"type": "response", "requestId": "initialize", "resultType": "success",
                              "method": "initialize", "result": {"clientId": "native-client"}})
                        self.assertEqual(receive(), {"type": "request", "requestId": "owner", "sourceClientId": "native-client",
                            "version": 1, "method": "thread-owner-discovery",
                            "params": {"hostId": "peer-host", "conversationId": "idle-peer"}})
                        send({"type": "response", "requestId": "owner", "resultType": "success",
                              "method": "thread-owner-discovery", "handledByClientId": "native-owner"})
                        follow = {"type": "broadcast", "sourceClientId": "native-client", "targetClientIds": ["native-owner"],
                                  "version": 1, "method": "thread-stream-following-changed",
                                  "params": {"hostId": "peer-host", "conversationId": "idle-peer", "following": True}}
                        self.assertEqual(receive(), follow)
                        send(snapshot())
                        start = receive()
                        # Inspect the public create-only capture before answering input.
                        prewrite.append((capture / "attempt.json").read_bytes())
                        pending = json.loads(prewrite[0])
                        self.assertEqual(pending["revision"], 7)
                        self.assertIsInstance(pending["observedAt"], (int, float))
                        self.assertEqual(pending["observedProfile"], {
                            "mode": "durable", "threadStartKind": "default", "threadSource": "user"})
                        self.assertEqual(pending["observedRuntimeStatus"], "idle")
                        self.assertEqual(pending["envelope"], start)
                        self.assertEqual(pending["correlation"], "idle-attempt")
                        self.assertEqual(pending["binding"]["owner"], "native-owner")
                        self.assertTrue(pending["binding"]["generation"])
                        self.assertEqual(pending["payloadSha256"], hashlib.sha256(expected_payload.encode()).hexdigest())
                        self.assertEqual(start, {
                            "type": "request", "requestId": "idle-attempt", "sourceClientId": "native-client",
                            "targetClientId": "native-owner", "version": 2, "method": "thread-follower-start-turn",
                            "params": {"conversationId": "idle-peer", "turnStart": {
                                "request": {"threadId": "idle-peer", "clientUserMessageId": "idle-attempt",
                                    "input": [{"type": "text", "text": expected_payload, "text_elements": []}]},
                                "context": {"inheritThreadSettings": True}}},
                        })
                        send({"type": "response", "requestId": "idle-attempt", "resultType": "success",
                              "method": "thread-follower-start-turn", "result": {}})
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
                    completed = command("codex_ipc_idle_sender.py", "--request", str(request_file))
                finally:
                    server.join(timeout=5)
                    if server.is_alive():
                        listener.close()
                        server.join(timeout=4)
                self.assertFalse(server.is_alive(), "fixture server did not terminate")
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stderr, "")
            result = json.loads(completed.stdout)
            self.assertEqual(result["peer_input"], "possible_submission", result)
            self.assertEqual(errors, [])
            self.assertTrue(closed.is_set())
            self.assertTrue(result["claimed"])
            self.assertEqual(result["reason"], "rpc-success-effect-unconfirmed")
            self.assertEqual(result["owned_connection"], {"started": True, "closed": True})
            self.assertEqual(result["projection"]["stage"], "possible-submission")
            recorded = mailbox("show", "idle-message")
            self.assertEqual({k: v for k, v in recorded.items() if k not in {"state", "attempts"}}, original)
            self.assertEqual(recorded["state"], "unknown")
            self.assertEqual(len(recorded["attempts"]), 1)
            attempt = recorded["attempts"][0]
            self.assertEqual(attempt["attempt_id"], "idle-attempt")
            self.assertEqual(attempt["actor"], actor)
            self.assertFalse(attempt["received"])
            self.assertFalse(attempt["handled"])
            self.assertFalse(attempt["completed"])
            self.assertEqual([o["kind"] for o in attempt["observations"]], ["unknown"])
            self.assertTrue(all(o["evidence_ref"] == "synthetic://idle-evidence" for o in attempt["observations"]))
            pending = json.loads((capture / "attempt.json").read_bytes())
            self.assertEqual(prewrite, [(capture / "attempt.json").read_bytes()])
            self.assertEqual(pending["envelope"], wire[3])
            self.assertEqual(pending["correlation"], "idle-attempt")
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
            self.assertEqual(projection["evidence"], [])
            self.assertEqual(projection["receipt"], "unknown")
            self.assertFalse(projection["idle_observation_is_atomic"])
            self.assertIn("idle-observation-not-atomic", projection["limits"])
            self.assertEqual(result["receipt"], "unknown")
            rpc = json.loads((capture / "rpc.json").read_bytes())
            self.assertEqual(rpc["originalResult"], [{"type": "response", "requestId": "idle-attempt",
                "resultType": "success", "method": "thread-follower-start-turn", "result": {}}])
            self.assertEqual([f["method"] for f in wire], ["initialize", "thread-owner-discovery",
                "thread-stream-following-changed", "thread-follower-start-turn", "thread-stream-following-changed"])
            self.assertEqual(json.loads((capture / "outbound.json").read_bytes()), wire)
            received = json.loads((capture / "received.json").read_bytes())
            self.assertEqual(len(received), 4)
            self.assertTrue(all(r[0]["generation"] == pending["binding"]["generation"] for r in received))
            # One immutable claim never sends again after an uncertain submission.
            before = {p.name: p.read_bytes() for p in capture.iterdir()}
            # A listening endpoint makes an accidental repeat connection observable.
            endpoint.unlink()
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as duplicate_listener:
                duplicate_listener.bind(str(endpoint))
                duplicate_listener.listen(1)
                duplicate_listener.settimeout(0.15)
                repeated = command("codex_ipc_idle_sender.py", "--request", str(request_file))
                with self.assertRaises(TimeoutError):
                    duplicate_listener.accept()
            self.assertEqual({p.name: p.read_bytes() for p in capture.iterdir()}, before)
            self.assertEqual(json.loads(repeated.stdout)["owned_connection"], {"started": False, "closed": False})
            self.assertFalse(json.loads(repeated.stdout)["claimed"])
            self.assertEqual(repeated.returncode, 0, repeated.stderr)
            self.assertEqual(json.loads(repeated.stdout)["reason"], "claim_not_acquired")
            self.assertEqual(mailbox("show", "idle-message"), recorded)

            evidence = os.environ.get("IDLE_SLICE_EVIDENCE")
            if evidence:
                target = Path(evidence)
                shutil.copytree(capture, target / "capture")
                for name, value in {"mailbox-show.json": recorded, "wire.json": wire,
                                    "closure.json": {"eof_observed": closed.is_set(), "thread_alive": server.is_alive(),
                                                     "original_child_exit": completed.returncode}}.items():
                    (target / name).write_text(json.dumps(value, indent=2))


if __name__ == "__main__":
    unittest.main()
