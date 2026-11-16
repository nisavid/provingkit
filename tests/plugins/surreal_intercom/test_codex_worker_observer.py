"""Diagnostic observer behavior through its public CLI and synthetic Unix peer."""

import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest


ROOT = Path(__file__).resolve().parents[3]
OBSERVER = (
    ROOT / "plugins/surreal-intercom/skills/communicating-with-agents/scripts"
    / "codex_worker_observer.py"
)


def frame(value):
    body = value if isinstance(value, bytes) else json.dumps(value, separators=(",", ":")).encode()
    return struct.pack("<I", len(body)) + body


class CodexWorkerObserverTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="codex-worker-observer-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.endpoint = self.root / "peer.sock"
        self.input_path = self.root / "input.json"
        self.output_path = self.root / "result.json"
        self.wire = []
        self.sent = []
        self.errors = []
        self.document = {
            "schema": "provingkit-codex-worker-observation-diagnostic-v1",
            "observationId": "synthetic-observation",
            "actor": {"threadId": "observer", "hostId": "test-host"},
            "route": {
                "endpoint": str(self.endpoint), "host": "local",
                "target": "worker-thread", "routeRef": "synthetic://route",
                "permissionRef": "synthetic://diagnostic-permission",
            },
            "scope": {"diagnosticObservation": True, "send": False},
            "profile": {
                "inputBytes": 1048576, "routeBytes": 65536,
                "frameBytes": 65536, "incomingBytes": 262144, "events": 64,
                "resultBytes": 8192, "stdoutBytes": 8192, "stderrBytes": 8192,
                "outgoingFrameBytes": 4096, "writes": 70,
                "networkSeconds": 10, "ioSeconds": 1, "cleanupReserveSeconds": 1,
                "observationSeconds": 0.05, "maxReceiptAgeSeconds": 10,
            },
        }

    def snapshot(self, revision=7, *, owner="worker-owner", target="worker-thread",
                 runtime="idle", turns=None, complete=True):
        if turns is None:
            turns = [{"turnId": "finished-turn", "status": "completed", "items": []}]
        return {
            "type": "broadcast", "version": 11,
            "method": "thread-stream-state-changed",
            "sourceClientId": owner, "targetClientIds": ["observer-client"],
            "params": {
                "hostId": "local", "conversationId": target,
                "change": {
                    "type": "snapshot", "revision": revision,
                    "conversationState": {
                        "id": target, "threadRuntimeStatus": {"type": runtime},
                        "resumeState": "resumed",
                        "turnsPagination": {"hasLoadedOldest": complete},
                        "turns": turns,
                    },
                },
            },
        }

    def receive(self, connection):
        header = b""
        while len(header) < 4:
            part = connection.recv(4 - len(header))
            if not part:
                raise AssertionError("missing frame header")
            header += part
        length = struct.unpack("<I", header)[0]
        body = b""
        while len(body) < length:
            part = connection.recv(length - len(body))
            if not part:
                raise AssertionError("missing frame body")
            body += part
        value = json.loads(body)
        self.wire.append(value)
        return value

    def send(self, connection, *values):
        data = b"".join(frame(value) for value in values)
        connection.sendall(data)
        self.sent.extend(values)

    def write_input(self):
        self.input_path.write_text(json.dumps(self.document), encoding="utf-8")

    def invoke(self, *, output=None, timeout=5):
        self.write_input()
        return subprocess.run(
            [sys.executable, "-B", str(OBSERVER), "--input", str(self.input_path),
             "--output", str(output or self.output_path)],
            capture_output=True, text=True, timeout=timeout,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"},
        )

    def serve_standard(self, conversation, *, expect_cleanup=True, allow_peer_disconnect=False,
                       after_unfollow=None):
        def serve(listener):
            try:
                connection, _ = listener.accept()
                with connection:
                    connection.settimeout(2)
                    self.assertEqual(self.receive(connection), {
                        "type": "request", "requestId": "initialize", "version": 0,
                        "method": "initialize", "params": {"clientType": "cli"},
                    })
                    self.send(connection, {
                        "type": "response", "requestId": "initialize",
                        "method": "initialize", "resultType": "success",
                        "result": {"clientId": "observer-client"},
                    })
                    self.assertEqual(self.receive(connection)["method"], "thread-owner-discovery")
                    self.send(connection, {
                        "type": "response", "requestId": "owner",
                        "method": "thread-owner-discovery", "resultType": "success",
                        "handledByClientId": "worker-owner",
                    })
                    follow = self.receive(connection)
                    self.assertEqual(follow["method"], "thread-stream-following-changed")
                    self.assertTrue(follow["params"]["following"])
                    conversation(connection)
                    if expect_cleanup:
                        unfollow = self.receive(connection)
                        self.assertEqual(unfollow["method"], "thread-stream-following-changed")
                        self.assertFalse(unfollow["params"]["following"])
                        if after_unfollow is not None:
                            after_unfollow(connection)
            except BaseException as error:
                self.errors.append(error)

        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(str(self.endpoint))
            listener.listen(1)
            listener.settimeout(2)
            server = threading.Thread(target=serve, args=(listener,))
            server.start()
            completed = self.invoke()
            server.join(timeout=3)
            if server.is_alive():
                listener.close()
                server.join(timeout=2)
        self.assertFalse(server.is_alive(), "synthetic peer did not terminate")
        if allow_peer_disconnect:
            self.assertTrue(all(isinstance(error, BrokenPipeError) for error in self.errors), self.errors)
        else:
            self.assertEqual(self.errors, [])
        return completed

    def result(self, path=None):
        return json.loads((path or self.output_path).read_text(encoding="utf-8"))

    def assert_observed(self, completed, *, activity="idle", target="worker-thread"):
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(completed.stderr, "")
        self.assertTrue(self.output_path.is_file(), "successful exit omitted its result")
        result = self.result()
        self.assertEqual(result["status"], "observed")
        self.assertEqual(result["activity"], activity)
        self.assertEqual(result["binding"]["target"], target)
        return result

    def reset_fixture(self):
        self.endpoint.unlink()
        self.output_path.unlink()
        self.wire.clear()
        self.sent.clear()
        self.errors.clear()

    def test_reports_bounded_selected_view_without_send_traffic(self):
        def conversation(connection):
            before = self.snapshot(7, turns=[{
                "turnId": "finished-turn", "status": "completed",
                "items": [{"type": "agentMessage", "text": "raw-history-marker-one"}],
            }])
            after = self.snapshot(8, turns=[{
                "turnId": "finished-turn", "status": "completed",
                "items": [{"type": "agentMessage", "text": "raw-history-marker-two"}],
            }])
            self.send(connection, before, after)

        completed = self.serve_standard(conversation)
        result = self.assert_observed(completed)
        self.assertTrue(result["selectedViewComparison"]["equal"])
        self.assertEqual(result["history"]["last"], {"support": "supported", "complete": True})
        self.assertEqual(result["acquisition"]["completedSnapshots"], 2)
        self.assertLessEqual(len(self.output_path.read_bytes()), 8192)
        self.assertLessEqual(len(completed.stdout.encode()), 8192)
        self.assertLessEqual(len(completed.stderr.encode()), 8192)
        self.assertNotIn("raw-history-marker-one", self.output_path.read_text(encoding="utf-8"))
        self.assertNotIn("raw-history-marker-two", self.output_path.read_text(encoding="utf-8"))
        self.assertEqual([item["method"] for item in self.wire], [
            "initialize", "thread-owner-discovery",
            "thread-stream-following-changed", "thread-stream-following-changed",
        ])
        self.assertFalse(any("turn" in item["method"] for item in self.wire))
        self.assertEqual(result["closure"], {
            "subscription": "unfollow-sent-ack-unknown", "connection": "closed",
        })

    def test_driver_rejects_wrong_expected_view_target_and_missing_result(self):
        completed = self.serve_standard(lambda connection: self.send(connection, self.snapshot()))
        self.assert_observed(completed)
        with self.assertRaises(AssertionError):
            self.assert_observed(completed, activity="active")
        with self.assertRaises(AssertionError):
            self.assert_observed(completed, target="other-worker")
        self.output_path.unlink()
        with self.assertRaises(AssertionError):
            self.assert_observed(completed)

    def test_wrong_owner_and_target_bindings_are_unknown(self):
        messages = (self.snapshot(owner="other-owner"), self.snapshot(target="other-worker"))
        for message in messages:
            with self.subTest(source=message["sourceClientId"], target=message["params"]["conversationId"]):
                completed = self.serve_standard(lambda connection, value=message: self.send(connection, value))
                self.assertEqual(completed.returncode, 2)
                self.assertEqual(self.result()["terminal"], {
                    "state": "unknown", "reason": "unmatched-state-binding",
                })
                if message is not messages[-1]:
                    self.reset_fixture()

    def test_embedded_conversation_target_must_match_route(self):
        message = self.snapshot()
        message["params"]["change"]["conversationState"]["id"] = "other-worker"

        completed = self.serve_standard(lambda connection: self.send(connection, message))

        self.assertEqual(completed.returncode, 2)
        self.assertEqual(self.result()["terminal"], {
            "state": "unknown", "reason": "snapshot-target-mismatch",
        })

    def test_malformed_target_clients_and_boolean_revision_are_unknown(self):
        cases = (
            ("targetClientIds", "prefix-observer-client-suffix", "invalid-target-client-ids"),
            ("targetClientIds", {"observer-client": True}, "invalid-target-client-ids"),
            ("revision", True, "invalid-revision"),
        )
        for index, (field, value, reason) in enumerate(cases):
            with self.subTest(field=field, value=value):
                message = self.snapshot()
                if field == "targetClientIds":
                    message[field] = value
                else:
                    message["params"]["change"][field] = value
                completed = self.serve_standard(
                    lambda connection, frame_value=message: self.send(connection, frame_value))
                result = self.result()
                if index + 1 < len(cases):
                    self.reset_fixture()
                self.assertEqual(completed.returncode, 2)
                self.assertEqual(result["terminal"], {
                    "state": "unknown", "reason": reason,
                })

    def test_list_params_is_a_bounded_refusal_and_connection_closes(self):
        message = self.snapshot()
        message["params"] = []

        completed = self.serve_standard(lambda connection: self.send(connection, message))

        self.assertEqual(completed.returncode, 2, completed.stdout + completed.stderr)
        result = self.result()
        self.assertEqual(result["terminal"], {
            "state": "unknown", "reason": "invalid-state-params",
        })
        self.assertEqual(result["closure"]["connection"], "closed")
        self.assertLessEqual(len(completed.stderr.encode()), 8192)

    def test_list_client_status_params_is_a_bounded_refusal_and_connection_closes(self):
        message = {"type": "broadcast", "method": "client-status-changed", "params": []}

        completed = self.serve_standard(lambda connection: self.send(connection, message))

        self.assertEqual(completed.returncode, 2, completed.stdout + completed.stderr)
        result = self.result()
        self.assertEqual(result["terminal"], {
            "state": "unknown", "reason": "invalid-client-status-params",
        })
        self.assertEqual(result["closure"]["connection"], "closed")

    def test_list_conversation_state_is_a_bounded_refusal_and_connection_closes(self):
        message = self.snapshot()
        message["params"]["change"]["conversationState"] = []

        completed = self.serve_standard(lambda connection: self.send(connection, message))

        self.assertEqual(completed.returncode, 2, completed.stdout + completed.stderr)
        result = self.result()
        self.assertEqual(result["terminal"], {
            "state": "unknown", "reason": "invalid-conversation-state",
        })
        self.assertEqual(result["closure"]["connection"], "closed")
        self.assertLessEqual(len(completed.stderr.encode()), 8192)

    def test_list_runtime_status_is_a_bounded_refusal_and_connection_closes(self):
        message = self.snapshot()
        message["params"]["change"]["conversationState"]["threadRuntimeStatus"] = []

        completed = self.serve_standard(lambda connection: self.send(connection, message))

        self.assertEqual(completed.returncode, 2, completed.stdout + completed.stderr)
        result = self.result()
        self.assertEqual(result["terminal"], {
            "state": "unknown", "reason": "invalid-thread-runtime-status",
        })
        self.assertEqual(result["closure"]["connection"], "closed")

    def test_malformed_nested_history_is_finalized_as_unsupported(self):
        message = self.snapshot()
        message["params"]["change"]["conversationState"]["turnsPagination"] = []

        completed = self.serve_standard(lambda connection: self.send(connection, message))

        result = self.assert_observed(completed)
        self.assertEqual(result["history"]["last"]["support"], "unsupported")
        self.assertIsNone(result["selectedViewComparison"]["equal"])
        self.assertEqual(result["closure"]["connection"], "closed")

    def test_stale_revision_and_connection_reset_are_unknown(self):
        cases = (
            (lambda connection: self.send(connection, self.snapshot(8), self.snapshot(7)), "stale-revision"),
            (lambda connection: self.send(connection, self.snapshot(), {
                "type": "broadcast", "method": "ipc-connection-reset",
            }), "connection-reset-needs-new-binding"),
        )
        for index, (conversation, reason) in enumerate(cases):
            with self.subTest(reason=reason):
                completed = self.serve_standard(conversation)
                self.assertEqual(completed.returncode, 2)
                result = self.result()
                self.assertEqual(result["terminal"], {"state": "unknown", "reason": reason})
                self.assertEqual(result["binding"]["upstreamFreshness"], "unknown")
                if index + 1 < len(cases):
                    self.reset_fixture()

    def test_reset_before_owner_response_is_consumed_and_connection_closes(self):
        def serve(listener):
            try:
                connection, _ = listener.accept()
                with connection:
                    connection.settimeout(2)
                    self.receive(connection)
                    self.send(connection, {
                        "type": "response", "requestId": "initialize", "method": "initialize",
                        "resultType": "success", "result": {"clientId": "observer-client"},
                    })
                    self.receive(connection)
                    self.send(
                        connection,
                        {"type": "broadcast", "method": "ipc-connection-reset"},
                        {
                            "type": "response", "requestId": "owner",
                            "method": "thread-owner-discovery", "resultType": "success",
                            "handledByClientId": "worker-owner",
                        },
                    )
                    self.assertEqual(connection.recv(1), b"")
            except BaseException as error:
                self.errors.append(error)

        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(str(self.endpoint))
            listener.listen(1)
            server = threading.Thread(target=serve, args=(listener,))
            server.start()
            completed = self.invoke()
            server.join(timeout=3)

        self.assertFalse(server.is_alive())
        self.assertEqual(self.errors, [])
        self.assertEqual(completed.returncode, 2)
        result = self.result()
        self.assertEqual(result["terminal"], {
            "state": "unknown", "reason": "connection-reset-needs-new-binding",
        })
        self.assertEqual(result["acquisition"]["events"], 3)
        self.assertEqual(result["acquisition"]["completedSnapshots"], 0)
        self.assertEqual(result["closure"]["connection"], "closed")

    def test_initialize_batch_preserves_reset_before_invalid_client_refusal(self):
        invalid_clients = (("missing", None), ("blank", ""), ("non-text", []))
        for index, (name, client) in enumerate(invalid_clients):
            def serve(listener):
                try:
                    connection, _ = listener.accept()
                    with connection:
                        connection.settimeout(2)
                        self.receive(connection)
                        result = {} if name == "missing" else {"clientId": client}
                        self.send(
                            connection,
                            {"type": "broadcast", "method": "ipc-connection-reset"},
                            {
                                "type": "response", "requestId": "initialize",
                                "method": "initialize", "resultType": "success",
                                "result": result,
                            },
                        )
                        self.assertEqual(connection.recv(1), b"")
                except BaseException as error:
                    self.errors.append(error)

            with self.subTest(client=name), socket.socket(
                    socket.AF_UNIX, socket.SOCK_STREAM) as listener:
                listener.bind(str(self.endpoint))
                listener.listen(1)
                server = threading.Thread(target=serve, args=(listener,))
                server.start()
                completed = self.invoke()
                server.join(timeout=3)

            self.assertFalse(server.is_alive())
            self.assertEqual(self.errors, [])
            self.assertEqual(completed.returncode, 2)
            result = self.result()
            self.assertEqual(result["terminal"], {
                "state": "unknown", "reason": "connection-reset-needs-new-binding",
            })
            self.assertEqual(result["acquisition"]["events"], 2)
            self.assertEqual(result["acquisition"]["completedSnapshots"], 0)
            self.assertEqual(result["closure"], {
                "subscription": "not-followed", "connection": "closed",
            })
            self.assertEqual([message["method"] for message in self.wire], ["initialize"])
            if index + 1 < len(invalid_clients):
                self.reset_fixture()

    def test_invalid_initialize_client_refuses_before_owner_discovery(self):
        def serve(listener):
            try:
                connection, _ = listener.accept()
                with connection:
                    connection.settimeout(2)
                    self.receive(connection)
                    self.send(connection, {
                        "type": "response", "requestId": "initialize", "method": "initialize",
                        "resultType": "success", "result": {"clientId": ""},
                    })
                    self.assertEqual(connection.recv(1), b"")
            except BaseException as error:
                self.errors.append(error)

        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(str(self.endpoint))
            listener.listen(1)
            server = threading.Thread(target=serve, args=(listener,))
            server.start()
            completed = self.invoke()
            server.join(timeout=3)

        self.assertFalse(server.is_alive())
        self.assertEqual(self.errors, [])
        self.assertEqual(completed.returncode, 2)
        result = self.result()
        self.assertEqual(result["terminal"], {"state": "refused", "reason": "native-client"})
        self.assertEqual(result["acquisition"]["events"], 1)
        self.assertEqual(result["closure"], {
            "subscription": "not-followed", "connection": "closed",
        })
        self.assertEqual([message["method"] for message in self.wire], ["initialize"])

    def test_discovery_reconciles_disconnect_with_correlated_owner(self):
        cases = (
            ("worker-owner", False, False),
            ("other-owner", True, False),
            (None, True, True),
        )
        for index, (disconnected_client, expect_follow, include_state) in enumerate(cases):
            def serve(listener):
                try:
                    connection, _ = listener.accept()
                    with connection:
                        connection.settimeout(2)
                        self.receive(connection)
                        self.send(connection, {
                            "type": "response", "requestId": "initialize", "method": "initialize",
                            "resultType": "success", "result": {"clientId": "observer-client"},
                        })
                        self.receive(connection)
                        owner_records = []
                        if disconnected_client is not None:
                            owner_records.append({
                                "type": "broadcast", "method": "client-status-changed",
                                "params": {"clientId": disconnected_client, "status": "disconnected"},
                            })
                        if include_state:
                            owner_records.append(self.snapshot())
                        owner_records.append({
                            "type": "response", "requestId": "owner",
                            "method": "thread-owner-discovery", "resultType": "success",
                            "handledByClientId": "worker-owner",
                        })
                        self.send(connection, *owner_records)
                        if expect_follow:
                            follow = self.receive(connection)
                            self.assertTrue(follow["params"]["following"])
                            if not include_state:
                                self.send(connection, self.snapshot())
                            unfollow = self.receive(connection)
                            self.assertFalse(unfollow["params"]["following"])
                        else:
                            self.assertEqual(connection.recv(1), b"")
                except BaseException as error:
                    self.errors.append(error)

            with self.subTest(disconnected_client=disconnected_client,
                              include_state=include_state), socket.socket(
                    socket.AF_UNIX, socket.SOCK_STREAM) as listener:
                listener.bind(str(self.endpoint))
                listener.listen(1)
                server = threading.Thread(target=serve, args=(listener,))
                server.start()
                completed = self.invoke()
                server.join(timeout=3)

            self.assertFalse(server.is_alive())
            self.assertEqual(self.errors, [])
            if expect_follow:
                result = self.assert_observed(completed)
                self.assertEqual(result["acquisition"]["completedSnapshots"], 1)
            else:
                self.assertEqual(completed.returncode, 2)
                result = self.result()
                self.assertEqual(result["terminal"], {
                    "state": "unknown", "reason": "owner-disconnected-needs-new-binding",
                })
                self.assertEqual(result["binding"]["owner"], "worker-owner")
                self.assertEqual(result["acquisition"]["completedSnapshots"], 0)
                self.assertEqual([message["method"] for message in self.wire], [
                    "initialize", "thread-owner-discovery",
                ])
            if index + 1 < len(cases):
                self.reset_fixture()

    def test_cleanup_reset_and_owner_disconnect_invalidate_observation(self):
        cleanup_messages = (
            ({"type": "broadcast", "method": "ipc-connection-reset"},
             "connection-reset-needs-new-binding"),
            ({
                "type": "broadcast", "method": "client-status-changed",
                "params": {"clientId": "worker-owner", "status": "disconnected"},
            }, "owner-disconnected-needs-new-binding"),
        )
        for index, (cleanup_message, reason) in enumerate(cleanup_messages):
            with self.subTest(reason=reason):
                completed = self.serve_standard(
                    lambda connection: self.send(connection, self.snapshot()),
                    after_unfollow=lambda connection, value=cleanup_message: self.send(connection, value),
                )
                self.assertEqual(completed.returncode, 2)
                result = self.result()
                self.assertEqual(result["terminal"], {"state": "unknown", "reason": reason})
                self.assertEqual(result["acquisition"]["events"], 4)
                self.assertEqual(result["acquisition"]["completedSnapshots"], 1)
                self.assertEqual(result["closure"], {
                    "subscription": "unfollow-sent-ack-unknown", "connection": "closed",
                })
                if index + 1 < len(cleanup_messages):
                    self.reset_fixture()

    def test_cleanup_conflict_at_same_revision_invalidates_observation(self):
        completed = self.serve_standard(
            lambda connection: self.send(connection, self.snapshot(7, runtime="idle")),
            after_unfollow=lambda connection: self.send(
                connection, self.snapshot(7, runtime="active"),
            ),
        )

        self.assertEqual(completed.returncode, 2)
        result = self.result()
        self.assertEqual(result["terminal"], {
            "state": "unknown", "reason": "conflicting-same-revision",
        })
        self.assertEqual(result["acquisition"]["completedSnapshots"], 2)

    def test_malformed_cleanup_change_invalidates_observation(self):
        message = self.snapshot()
        message["params"]["change"] = []
        completed = self.serve_standard(
            lambda connection: self.send(connection, self.snapshot()),
            after_unfollow=lambda connection: self.send(connection, message),
        )

        self.assertEqual(completed.returncode, 2)
        result = self.result()
        self.assertEqual(result["terminal"], {
            "state": "unknown", "reason": "invalid-state-change",
        })
        self.assertEqual(result["acquisition"]["completedSnapshots"], 1)
        self.assertEqual(result["closure"]["subscription"], "unfollow-sent-ack-unknown")

    def test_conflicting_snapshots_at_one_revision_are_unknown(self):
        completed = self.serve_standard(lambda connection: self.send(
            connection, self.snapshot(7, runtime="idle"), self.snapshot(7, runtime="active"),
        ))

        self.assertEqual(completed.returncode, 2)
        result = self.result()
        self.assertEqual(result["terminal"], {
            "state": "unknown", "reason": "conflicting-same-revision",
        })
        self.assertEqual(result["acquisition"]["completedSnapshots"], 2)
        self.assertEqual(result["selectedViewComparison"]["first"]["activity"], "idle")
        self.assertEqual(result["selectedViewComparison"]["last"]["activity"], "active")

    def test_identical_snapshots_at_one_revision_remain_observable(self):
        message = self.snapshot(7)
        completed = self.serve_standard(lambda connection: self.send(connection, message, message))

        result = self.assert_observed(completed)
        self.assertTrue(result["selectedViewComparison"]["equal"])
        self.assertEqual(result["acquisition"]["completedSnapshots"], 2)

    def test_partial_and_unsupported_history_remain_explicit(self):
        completed = self.serve_standard(
            lambda connection: self.send(connection, self.snapshot(complete=False)))
        partial = self.assert_observed(completed)
        self.assertEqual(partial["history"]["last"], {"support": "supported", "complete": False})
        self.reset_fixture()

        completed = self.serve_standard(lambda connection: self.send(connection, self.snapshot(
            turns=[{"turnId": "mystery", "status": "invented", "items": []}],
        )))
        unsupported = self.assert_observed(completed)
        self.assertEqual(unsupported["history"]["last"]["support"], "unsupported")
        self.assertFalse(unsupported["history"]["last"]["complete"])
        self.assertIsNone(unsupported["selectedViewComparison"]["equal"])

    def test_distinct_unsupported_runtime_types_do_not_compare_equal(self):
        completed = self.serve_standard(lambda connection: self.send(
            connection,
            self.snapshot(7, runtime="starting"),
            self.snapshot(8, runtime="stopping"),
        ))

        result = self.assert_observed(completed, activity="unknown")
        comparison = result["selectedViewComparison"]
        self.assertEqual(comparison["first"]["threadRuntimeStatusType"], "starting")
        self.assertEqual(comparison["last"]["threadRuntimeStatusType"], "stopping")
        self.assertFalse(comparison["equal"])

    def assert_no_connection(self, listener):
        listener.setblocking(False)
        with self.assertRaises(BlockingIOError):
            listener.accept()

    def test_aggregate_input_and_route_record_limits_refuse_before_connection(self):
        cases = (("observationId", "x" * 1048576, "input-byte-limit"),
                 ("routeRef", "x" * 65536, "route-byte-limit"))
        for index, (key, value, reason) in enumerate(cases):
            with self.subTest(reason=reason), socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
                listener.bind(str(self.endpoint))
                listener.listen(1)
                if key == "observationId":
                    self.document[key] = value
                else:
                    self.document["route"][key] = value
                completed = self.invoke()
                self.assertEqual(completed.returncode, 2)
                self.assertEqual(self.result()["terminal"]["reason"], reason)
                self.assert_no_connection(listener)
            self.document["observationId"] = "synthetic-observation"
            self.document["route"]["routeRef"] = "synthetic://route"
            if index + 1 < len(cases):
                self.endpoint.unlink()
                self.output_path.unlink()

    def test_recursive_input_is_a_bounded_refusal_before_connection(self):
        raw = b'{"unused":' + b"[" * 50000 + b"0" + b"]" * 50000 + b"}"
        try:
            json.loads(raw)
        except RecursionError:
            pass
        else:
            self.skipTest("Decoder accepts this bounded nesting on this interpreter.")
        self.input_path.write_bytes(raw)

        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(str(self.endpoint))
            listener.listen(1)
            completed = subprocess.run(
                [sys.executable, "-B", str(OBSERVER), "--input", str(self.input_path),
                 "--output", str(self.output_path)],
                capture_output=True, text=True, timeout=5,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"},
            )
            self.assertEqual(completed.returncode, 2, completed.stdout + completed.stderr)
            self.assertEqual(self.result()["terminal"], {
                "state": "refused", "reason": "input-decode-error",
            })
            self.assertLessEqual(len(completed.stderr.encode()), 8192)
            self.assert_no_connection(listener)

    def test_cleanup_reserve_is_fixed_before_connection(self):
        self.document["profile"]["cleanupReserveSeconds"] = 0.5
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(str(self.endpoint))
            listener.listen(1)
            completed = self.invoke()
            self.assertEqual(completed.returncode, 2)
            self.assertEqual(
                self.result()["terminal"]["reason"],
                "one-second-cleanup-reserve-required",
            )
            self.assert_no_connection(listener)

    def test_frame_wire_event_write_and_result_limits_refuse_exactly(self):
        completed = self.serve_standard(
            lambda connection: connection.sendall(struct.pack("<I", 65537)))
        result = self.result()
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(result["terminal"]["reason"], "frame-byte-limit")
        self.assertEqual(result["acquisition"]["rejectedFrame"]["announcedLength"], 65537)

        cases = (
            ({"events": 2}, "event-limit", lambda connection: self.send(connection, self.snapshot()), True),
            ({"writes": 3}, "outgoing-write-limit", lambda connection: self.send(connection, {
                "type": "client-discovery-request", "requestId": "negative-discovery",
            }), False),
            ({"resultBytes": 1024}, "result-byte-limit", lambda connection: self.send(connection, self.snapshot()), True),
        )
        defaults = {"events": 64, "writes": 70, "resultBytes": 8192}
        for profile, reason, conversation, expect_cleanup in cases:
            with self.subTest(reason=reason):
                self.reset_fixture()
                self.document["profile"].update(profile)
                completed = self.serve_standard(
                    conversation, expect_cleanup=expect_cleanup, allow_peer_disconnect=True,
                )
                result = self.result()
                self.assertEqual(completed.returncode, 2)
                self.assertEqual(result["terminal"]["reason"], reason)
                for changed in profile:
                    self.document["profile"][changed] = defaults[changed]

    def test_snapshot_cannot_mask_later_event_exhaustion(self):
        self.document["profile"]["events"] = 3

        completed = self.serve_standard(
            lambda connection: self.send(connection, self.snapshot()))

        self.assertEqual(completed.returncode, 2)
        result = self.result()
        self.assertEqual(result["terminal"], {"state": "unknown", "reason": "event-limit"})
        self.assertEqual(result["acquisition"]["completedSnapshots"], 1)
        self.assertIn("event-limit", result["acquisition"]["receiveStatus"])

    def test_snapshot_cannot_mask_later_wire_exhaustion(self):
        initialize = {
            "type": "response", "requestId": "initialize",
            "method": "initialize", "resultType": "success",
            "result": {"clientId": "observer-client"},
        }
        owner = {
            "type": "response", "requestId": "owner",
            "method": "thread-owner-discovery", "resultType": "success",
            "handledByClientId": "worker-owner",
        }
        message = self.snapshot()
        self.document["profile"]["incomingBytes"] = sum(
            len(frame(value)) for value in (initialize, owner, message)
        )

        completed = self.serve_standard(lambda connection: self.send(connection, message))

        self.assertEqual(completed.returncode, 2)
        result = self.result()
        self.assertEqual(result["terminal"], {
            "state": "unknown", "reason": "incoming-byte-limit",
        })
        self.assertEqual(result["acquisition"]["completedSnapshots"], 1)
        self.assertEqual(
            result["acquisition"]["incomingBytes"], self.document["profile"]["incomingBytes"],
        )
        self.assertIn("incoming-byte-limit", result["acquisition"]["receiveStatus"])

    def test_total_wire_limit_is_shared_from_initialize(self):
        self.document["profile"]["incomingBytes"] = 32

        def serve(listener):
            try:
                connection, _ = listener.accept()
                with connection:
                    connection.settimeout(2)
                    self.receive(connection)
                    self.send(connection, {
                        "type": "response", "requestId": "initialize",
                        "method": "initialize", "resultType": "success",
                        "result": {"clientId": "observer-client"},
                    })
            except BaseException as error:
                self.errors.append(error)

        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(str(self.endpoint))
            listener.listen(1)
            server = threading.Thread(target=serve, args=(listener,))
            server.start()
            completed = self.invoke()
            server.join(timeout=3)
        self.assertEqual(self.errors, [])
        self.assertEqual(completed.returncode, 2)
        result = self.result()
        self.assertEqual(result["terminal"]["reason"], "incoming-byte-limit")
        self.assertLessEqual(result["acquisition"]["incomingBytes"], 32)

    def test_outgoing_frame_limit_refuses_before_oversized_owner_discovery_write(self):
        self.document["route"]["target"] = "worker-" + "x" * 4096

        def serve(listener):
            try:
                connection, _ = listener.accept()
                with connection:
                    connection.settimeout(2)
                    self.receive(connection)
                    self.send(connection, {
                        "type": "response", "requestId": "initialize",
                        "method": "initialize", "resultType": "success",
                        "result": {"clientId": "observer-client"},
                    })
                    self.assertEqual(connection.recv(1), b"")
            except BaseException as error:
                self.errors.append(error)

        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(str(self.endpoint))
            listener.listen(1)
            server = threading.Thread(target=serve, args=(listener,))
            server.start()
            completed = self.invoke()
            server.join(timeout=3)
        self.assertEqual(self.errors, [])
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(self.result()["terminal"]["reason"], "outgoing-frame-limit")
        self.assertEqual([item["method"] for item in self.wire], ["initialize"])

    def test_observation_timeout_is_unknown_and_cleanup_stays_in_budget(self):
        self.document["profile"].update({
            "networkSeconds": 1.2, "ioSeconds": 0.1,
            "cleanupReserveSeconds": 1, "observationSeconds": 0.1,
        })
        started = time.monotonic()
        completed = self.serve_standard(lambda _connection: None)
        elapsed = time.monotonic() - started
        result = self.result()
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(result["terminal"]["reason"], "observation-deadline-unknown")
        self.assertLess(elapsed, 1)
        self.assertEqual(result["closure"]["subscription"], "unfollow-sent-ack-unknown")
        self.assertLessEqual(result["acquisition"]["elapsedSeconds"], 1.2)

    def test_receipt_age_bound_refuses_a_snapshot_held_past_the_selected_age(self):
        self.document["profile"].update({
            "observationSeconds": 0.05, "maxReceiptAgeSeconds": 0.01,
        })
        completed = self.serve_standard(
            lambda connection: self.send(connection, self.snapshot()))
        result = self.result()
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(result["terminal"], {
            "state": "unknown", "reason": "stale-snapshot-receipt",
        })
        self.assertGreater(result["localReceipt"]["lastAgeSeconds"], 0.01)

    def test_malformed_and_partial_frames_preserve_failure_and_cleanup(self):
        def malformed(connection):
            connection.sendall(frame(b"{"))

        def partial(connection):
            connection.sendall(struct.pack("<I", 10) + b"abc")
            connection.shutdown(socket.SHUT_WR)

        cases = ((malformed, "frame-decode-error"), (partial, "stream-eof-unknown"))
        for index, (conversation, reason) in enumerate(cases):
            with self.subTest(reason=reason):
                completed = self.serve_standard(conversation)
                self.assertEqual(completed.returncode, 2)
                result = self.result()
                self.assertEqual(result["terminal"]["reason"], reason)
                self.assertEqual(result["closure"]["connection"], "closed")
                if index + 1 < len(cases):
                    self.reset_fixture()

    def test_snapshot_prefix_survives_partial_follow_frame_and_finishes_unknown(self):
        def conversation(connection):
            self.send(connection, self.snapshot())
            connection.sendall(struct.pack("<I", 10) + b"abc")
            connection.shutdown(socket.SHUT_WR)

        completed = self.serve_standard(conversation)

        self.assertEqual(completed.returncode, 2)
        result = self.result()
        self.assertEqual(result["terminal"], {
            "state": "unknown", "reason": "stream-eof-unknown",
        })
        self.assertEqual(result["acquisition"]["completedSnapshots"], 1)
        self.assertEqual(result["selectedViewComparison"]["first"]["activity"], "idle")
        self.assertEqual(result["closure"], {
            "subscription": "unfollow-sent-ack-unknown", "connection": "closed",
        })

    def test_snapshot_prefix_with_stalled_partial_frame_finishes_unknown(self):
        def conversation(connection):
            self.send(connection, self.snapshot())
            connection.sendall(struct.pack("<I", 10) + b"abc")

        completed = self.serve_standard(conversation)

        self.assertEqual(completed.returncode, 2)
        result = self.result()
        self.assertEqual(result["terminal"], {
            "state": "unknown", "reason": "observation-deadline-unknown",
        })
        self.assertEqual(result["acquisition"]["completedSnapshots"], 1)
        self.assertIn("observation-deadline-unknown", result["acquisition"]["receiveStatus"])

    def test_snapshot_prefix_survives_malformed_follow_frame(self):
        completed = self.serve_standard(
            lambda connection: connection.sendall(frame(self.snapshot()) + frame(b"{")))

        self.assertEqual(completed.returncode, 2)
        result = self.result()
        self.assertEqual(result["terminal"], {
            "state": "unknown", "reason": "frame-decode-error",
        })
        self.assertEqual(result["acquisition"]["completedSnapshots"], 1)
        self.assertEqual(result["selectedViewComparison"]["first"]["activity"], "idle")
        self.assertIn("frame-decode-error", result["acquisition"]["receiveStatus"])

    def test_malformed_and_oversized_cleanup_invalidate_snapshot(self):
        cleanup_cases = (
            (lambda connection: connection.sendall(frame(b"{")), "frame-decode-error"),
            (lambda connection: connection.sendall(struct.pack("<I", 65537)), "frame-byte-limit"),
        )
        for index, (cleanup, reason) in enumerate(cleanup_cases):
            with self.subTest(reason=reason):
                completed = self.serve_standard(
                    lambda connection: self.send(connection, self.snapshot()),
                    after_unfollow=cleanup,
                )
                self.assertEqual(completed.returncode, 2)
                result = self.result()
                self.assertEqual(result["terminal"], {"state": "unknown", "reason": reason})
                self.assertEqual(result["acquisition"]["completedSnapshots"], 1)
                self.assertIn(reason, result["acquisition"]["receiveStatus"])
                self.assertEqual(result["closure"], {
                    "subscription": "unfollow-sent-ack-unknown", "connection": "closed",
                })
                if index + 1 < len(cleanup_cases):
                    self.reset_fixture()

    def test_cleanup_reset_prefix_survives_malformed_suffix(self):
        def cleanup(connection):
            connection.sendall(
                frame({"type": "broadcast", "method": "ipc-connection-reset"})
                + frame(b"{")
            )

        completed = self.serve_standard(
            lambda connection: self.send(connection, self.snapshot()),
            after_unfollow=cleanup,
        )

        self.assertEqual(completed.returncode, 2)
        result = self.result()
        self.assertEqual(result["terminal"], {
            "state": "unknown", "reason": "connection-reset-needs-new-binding",
        })
        self.assertEqual(result["acquisition"]["completedSnapshots"], 1)
        self.assertEqual(result["acquisition"]["events"], 5)
        self.assertIn("frame-decode-error", result["acquisition"]["receiveStatus"])
        self.assertEqual(result["closure"], {
            "subscription": "unfollow-sent-ack-unknown", "connection": "closed",
        })

    def test_output_collision_refuses_without_connection_and_preserves_bytes(self):
        original = b"existing-result\n"
        self.output_path.write_bytes(original)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(str(self.endpoint))
            listener.listen(1)
            completed = self.invoke()
            self.assertEqual(completed.returncode, 3)
            self.assertIn("output-collision", completed.stdout)
            self.assertEqual(self.output_path.read_bytes(), original)
            self.assert_no_connection(listener)

    def test_output_finalization_failure_is_bounded_after_owned_cleanup(self):
        result_directory = self.root / "result-directory"
        result_directory.mkdir()
        output = result_directory / "result.json"
        moved = self.root / "moved-result-directory"

        def serve(listener):
            try:
                connection, _ = listener.accept()
                with connection:
                    connection.settimeout(2)
                    self.receive(connection)
                    self.send(connection, {
                        "type": "response", "requestId": "initialize", "method": "initialize",
                        "resultType": "success", "result": {"clientId": "observer-client"},
                    })
                    self.receive(connection)
                    self.send(connection, {
                        "type": "response", "requestId": "owner", "method": "thread-owner-discovery",
                        "resultType": "success", "handledByClientId": "worker-owner",
                    })
                    self.receive(connection)
                    self.send(connection, self.snapshot())
                    result_directory.rename(moved)
                    self.receive(connection)
            except BaseException as error:
                self.errors.append(error)

        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
            listener.bind(str(self.endpoint))
            listener.listen(1)
            server = threading.Thread(target=serve, args=(listener,))
            server.start()
            completed = self.invoke(output=output)
            server.join(timeout=3)
        self.assertEqual(self.errors, [])
        self.assertEqual(completed.returncode, 3)
        self.assertIn("output-finalization-failed", completed.stdout)
        self.assertFalse(output.exists())
        self.assertFalse(any(path.name.endswith(".tmp") for path in moved.iterdir()))

    def test_output_finalization_preserves_unowned_staging_objects(self):
        for kind in ("regular", "symlink", "directory"):
            with self.subTest(kind=kind):
                endpoint = self.root / f"peer-{kind}.sock"
                output = self.root / f"result-{kind}.json"
                self.document["route"]["endpoint"] = str(endpoint)
                ready = threading.Event()
                release = threading.Event()
                errors = []

                def serve(listener):
                    try:
                        connection, _ = listener.accept()
                        with connection:
                            connection.settimeout(2)
                            self.receive(connection)
                            self.send(connection, {
                                "type": "response", "requestId": "initialize",
                                "method": "initialize", "resultType": "success",
                                "result": {"clientId": "observer-client"},
                            })
                            self.receive(connection)
                            self.send(connection, {
                                "type": "response", "requestId": "owner",
                                "method": "thread-owner-discovery", "resultType": "success",
                                "handledByClientId": "worker-owner",
                            })
                            self.receive(connection)
                            ready.set()
                            if not release.wait(2):
                                raise AssertionError("staging-object release timed out")
                            self.send(connection, self.snapshot())
                            self.receive(connection)
                    except BaseException as error:
                        errors.append(error)

                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
                    listener.bind(str(endpoint))
                    listener.listen(1)
                    server = threading.Thread(target=serve, args=(listener,))
                    server.start()
                    self.write_input()
                    process = subprocess.Popen(
                        [sys.executable, "-B", str(OBSERVER),
                         "--input", str(self.input_path), "--output", str(output)],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
                             "PYTHONNOUSERSITE": "1"},
                    )
                    self.assertTrue(ready.wait(2), "observer did not reach follow")
                    staging = output.with_name(f".{output.name}.{process.pid}.tmp")
                    sentinel = self.root / f"sentinel-{kind}"
                    if kind == "regular":
                        staging.write_bytes(b"preexisting-staging\n")
                    elif kind == "symlink":
                        sentinel.write_bytes(b"symlink-target\n")
                        staging.symlink_to(sentinel)
                    else:
                        staging.mkdir()
                        (staging / "marker").write_bytes(b"directory-marker\n")
                    release.set()
                    stdout, stderr = process.communicate(timeout=5)
                    server.join(timeout=3)

                self.assertFalse(server.is_alive())
                self.assertEqual(errors, [])
                self.assertEqual(process.returncode, 3, stdout + stderr)
                self.assertEqual(
                    stdout,
                    '{"reason":"output-finalization-failed","status":"refused"}\n',
                )
                self.assertEqual(stderr, "")
                self.assertFalse(output.exists())
                if kind == "regular":
                    self.assertEqual(staging.read_bytes(), b"preexisting-staging\n")
                elif kind == "symlink":
                    self.assertTrue(staging.is_symlink())
                    self.assertEqual(os.readlink(staging), str(sentinel))
                else:
                    self.assertTrue(staging.is_dir())
                    self.assertEqual(
                        (staging / "marker").read_bytes(), b"directory-marker\n")

    def test_peer_close_makes_cleanup_unknown_but_owned_connection_closes(self):
        def conversation(connection):
            self.send(connection, self.snapshot())
            connection.shutdown(socket.SHUT_RDWR)

        completed = self.serve_standard(conversation, expect_cleanup=False)
        result = self.assert_observed(completed)
        self.assertTrue(result["closure"]["subscription"].startswith("unfollow-unknown:"))
        self.assertEqual(result["closure"]["connection"], "closed")


if __name__ == "__main__":
    unittest.main()
