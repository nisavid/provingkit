"""Consumer catalog refusal through a real CLI and disposable MCP child."""
from contextlib import contextmanager, redirect_stdout
import io
import json
import os
from pathlib import Path
import re
import signal
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from unittest.mock import patch

SCRIPTS = (
    Path(__file__).resolve().parents[3]
    / "plugins" / "surreal-intercom" / "skills" / "communicating-with-agents"
    / "scripts"
)


def retained_destination_catalog():
    """Retained structural profile; annotations are synthetic, never instructions."""
    return {"tools": [{"name": "SendMessage", "inputSchema": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "to": {
                "type": "string", "description": "Synthetic destination.",
                "allOf": [{"pattern": r"^[^\n\r]*$"}, {"pattern": r"^[\s\S]{0,300}$"}],
            },
            "message": {"type": "string", "default": ""},
            "summary": {"type": "string", "maxLength": 200},
            "notify_when_idle": {"type": "boolean"},
        },
        "required": ["to", "message"], "additionalProperties": False,
    }}]}


class ClaudeMcpSenderTests(unittest.TestCase):
    @contextmanager
    def consumer(
        self, mode="lost_reply", catalog=None, *, message_id="failure-1",
        original=None, actor=None,
        attempt_id="attempt-failure", evidence_ref="synthetic://evidence/failure",
        target="uds:/synthetic/selected-peer.sock",
    ):
        """Run only the public commands, with an invented store and stdio peer."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = root / "mailbox.sqlite3"
            trace = root / "child.jsonl"
            child = root / "peer_child.py"
            mailbox = SCRIPTS / "native_codex_mailbox.py"
            if original is None:
                original = {
                    "message_id": message_id, "correlation_id": "conversation-77",
                    "sender": {"thread_id": "original", "host_id": "origin-host"},
                    "recipient": {"thread_id": "recipient", "host_id": "peer-host"},
                    "owner": {"thread_id": "owner", "host_id": "local"},
                    "payload": "Intake only.\r\nKeep e\u0301 and café.\n",
                    "authority_ref": "synthetic://grant/intake",
                    "holds": ["No operational transfer.", "Publication remains held."],
                }
            source = root / "message.json"
            source.write_bytes(json.dumps(original).encode("utf-8"))

            def bookkeeping(*arguments, success=True):
                completed = subprocess.run(
                    [sys.executable, str(mailbox), "--store", str(store), *arguments],
                    capture_output=True, text=True, timeout=10,
                )
                self.assertEqual(completed.returncode, 0 if success else 2, completed.stderr)
                return json.loads(completed.stdout if success else completed.stderr)

            bookkeeping("init")
            bookkeeping("plan", "--input", str(source))
            if catalog is None:
                catalog = {"tools": [{
                    "name": "SendMessage", "inputSchema": {
                        "type": "object", "properties": {
                            "to": {"type": "string"}, "message": {"type": "string"},
                        },
                        "required": ["to", "message"], "additionalProperties": False,
                    },
                }]}
            catalog_file = root / "catalog.json"
            catalog_file.write_text(json.dumps(catalog), encoding="utf-8")
            child.write_text(textwrap.dedent("""\
                import json
                import os
                import subprocess
                import sys
                import time

                def retained():
                    shown = subprocess.run(
                        [sys.executable, sys.argv[4], "--store", sys.argv[5],
                         "show", sys.argv[6]],
                        capture_output=True, text=True, check=True, timeout=5,
                    )
                    return json.loads(shown.stdout)

                with open(sys.argv[1], "a", encoding="utf-8") as trace:
                    trace.write(json.dumps({
                        "started_pid": os.getpid(), "before_start": retained(),
                    }) + "\\n")
                    trace.flush()
                    for line in sys.stdin:
                        request = json.loads(line)
                        trace.write(json.dumps(request) + "\\n")
                        trace.flush()
                        method = request.get("method")
                        if method == "initialize":
                            response = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}}
                        elif method == "notifications/initialized":
                            continue
                        elif method == "tools/list":
                            with open(sys.argv[2], encoding="utf-8") as source:
                                response = json.load(source)
                        elif method == "tools/call":
                            trace.write(json.dumps({"before_call": retained()}) + "\\n")
                            trace.flush()
                            if sys.argv[3] == "lost_reply":
                                os.close(sys.stdout.fileno())
                                continue
                            if sys.argv[3] == "stdout_overflow":
                                os.write(sys.stdout.fileno(), b"X" * 16385)
                                continue
                            if sys.argv[3] == "stderr_overflow":
                                remaining = memoryview(b"E" * (2 * 1048576))
                                while remaining:
                                    written = os.write(sys.stderr.fileno(), remaining)
                                    remaining = remaining[written:]
                                continue
                            if sys.argv[3] == "call_deadline":
                                # Startup and catalog negotiation finish normally;
                                # only this owned child's call reply is delayed.
                                time.sleep(30)
                                continue
                            if sys.argv[3] == "envelope_submission":
                                response = {
                                    "content": [{"type": "text", "text": "Unvalidated tool text."}],
                                    "isError": False,
                                }
                            elif sys.argv[3] in ("tool_error", "tool_success"):
                                response = {
                                    "content": [{"type": "text", "text": "Private unvalidated tool text."}],
                                    "isError": sys.argv[3] == "tool_error",
                                }
                            else:
                                raise SystemExit(90)
                        else:
                            raise SystemExit(91)
                        print(json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": response}), flush=True)
                    trace.write(json.dumps({"stdin_eof": True}) + "\\n")
                raise SystemExit(23)
                """), encoding="utf-8")
            request = {
                "message_id": original["message_id"], "attempt_id": attempt_id,
                "actor": actor if actor is not None else {
                    "thread_id": "replacement", "host_id": "forward-host",
                },
                "recipient": original["recipient"],
                "target": target,
                "command": [
                    sys.executable, str(child), str(trace), str(catalog_file), mode,
                    str(mailbox), str(store), original["message_id"],
                ],
                "evidence_ref": evidence_ref,
                "limits": {"operation_seconds": 8, "stdout_bytes": 16384, "stderr_bytes": 4096},
            }
            request_file = root / "request.json"

            def send(raw=None):
                request_file.write_bytes(json.dumps(request).encode("utf-8") if raw is None else raw)
                completed = subprocess.run(
                    [sys.executable, "-B", str(SCRIPTS / "claude_mcp_sender.py"),
                     "--store", str(store), "--request", str(request_file)],
                    capture_output=True, text=True, timeout=12,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(completed.stderr, "")
                self.assertLessEqual(len(completed.stdout.encode("utf-8")), 2048)
                self.assertNotIn("Unvalidated tool text.", completed.stdout)
                return json.loads(completed.stdout)

            yield original, request, send, bookkeeping, trace, source

    def assert_no_receipt(self, retained, original):
        self.assertEqual({key: retained[key] for key in original}, original)
        for attempt in retained["attempts"]:
            for stage in ("received", "handled", "completed"):
                self.assertFalse(attempt[stage])

    def assert_no_replay(self, request, send, bookkeeping, trace, retained):
        trace_bytes = trace.read_bytes()
        for attempt_id in ("attempt-failure", "fresh-unreconciled-attempt"):
            request["attempt_id"] = attempt_id
            repeated = send()
            self.assertFalse(repeated["claimed"])
            self.assertEqual(repeated["reason"], "claim_not_acquired")
            self.assertEqual(repeated["owned_child"], {
                "started": False, "reaped": False, "exit_code": None,
            })
            self.assertEqual(trace.read_bytes(), trace_bytes)
            self.assertEqual(bookkeeping("show", "failure-1"), retained)

    def test_lost_reply_preserves_possible_submission_and_prevents_unreconciled_replay(self):
        for catalog in (None, retained_destination_catalog()):
            with self.subTest(catalog=catalog):
                with self.consumer(catalog=catalog) as (original, request, send, bookkeeping, trace, source):
                    result = send()
                    self.assertEqual(result["stage"], "call")
                    self.assertEqual(result["reason"], "stdout_eof")
                    self.assertEqual(result["peer_input"], "possible_submission")
                    self.assertTrue(result["claimed"])
                    self.assertEqual(result["owned_child"], {"started": True, "reaped": True, "exit_code": 23})
                    records = [json.loads(line) for line in trace.read_bytes().splitlines()]
                    self.assertGreater(records[0]["started_pid"], 0)
                    self.assertEqual([r["method"] for r in records if "method" in r], [
                        "initialize", "notifications/initialized", "tools/list", "tools/call",
                    ])
                    self.assertEqual(records[-1], {"stdin_eof": True})
                    retained = bookkeeping("show", "failure-1")
                    self.assert_no_receipt(retained, original)
                    self.assertEqual(retained["state"], "unknown")
                    self.assertEqual(len(retained["attempts"]), 1)
                    attempt = retained["attempts"][0]
                    self.assertEqual(attempt["actor"], request["actor"])
                    self.assertEqual([o["kind"] for o in attempt["observations"]], ["unknown", "unknown"])
                    self.assertEqual(json.loads(attempt["observations"][-1]["detail"]), {
                        "phase": "possible_submission", "path": "route", "to": "uds:/synthetic/selected-peer.sock",
                    })
                    self.assert_no_replay(request, send, bookkeeping, trace, retained)

    def test_recipient_mismatch_preserves_plan_without_claim_or_child(self):
        with self.consumer() as (original, request, send, bookkeeping, trace, source):
            planned = bookkeeping("show", "failure-1")
            request["recipient"] = {"thread_id": "different-recipient", "host_id": "peer-host"}
            result = send()
            self.assertEqual(result["stage"], "claim")
            self.assertEqual(result["reason"], "recipient_mismatch")
            self.assertFalse(result["claimed"])
            self.assertEqual(result["peer_input"], "not_attempted")
            self.assertEqual(result["owned_child"], {
                "started": False, "reaped": False, "exit_code": None,
            })
            self.assertFalse(trace.exists())
            retained = bookkeeping("show", "failure-1")
            self.assertEqual(retained, planned)
            self.assertEqual(retained["state"], "planned")
            self.assertEqual(retained["attempts"], [])
            self.assert_no_receipt(retained, original)

    def test_unsupported_required_arguments_refuse_without_tool_call(self):
        schemas = (
            {"type": "object", "properties": {
                "to": {"type": "string"}, "message": {"type": "string"},
                "priority": {"type": "string"},
            }, "required": ["to", "message", "priority"], "additionalProperties": False},
            {"type": "object", "properties": {
                "to": {"type": "integer"}, "message": {"type": "string"},
            }, "required": ["to", "message"], "additionalProperties": False},
        )
        for schema in schemas:
            with self.subTest(schema=schema):
                catalog = {"tools": [{"name": "SendMessage", "inputSchema": schema}]}
                with self.consumer(catalog=catalog) as (original, request, send, bookkeeping, trace, source):
                    result = send()
                    self.assertEqual(result["stage"], "catalog")
                    self.assertEqual(result["reason"], "unsupported_sendmessage_schema")
                    self.assertEqual(result["peer_input"], "not_attempted")
                    self.assertTrue(result["claimed"])
                    self.assertEqual(result["owned_child"], {
                        "started": True, "reaped": True, "exit_code": 23,
                    })
                    records = [json.loads(line) for line in trace.read_bytes().splitlines()]
                    self.assertGreater(records[0]["started_pid"], 0)
                    self.assertEqual([r["method"] for r in records if "method" in r], [
                        "initialize", "notifications/initialized", "tools/list",
                    ])
                    self.assertEqual(records[-1], {"stdin_eof": True})
                    retained = bookkeeping("show", "failure-1")
                    self.assert_no_receipt(retained, original)
                    self.assertEqual(retained["state"], "refused")
                    self.assertEqual(len(retained["attempts"]), 1)
                    self.assertEqual([o["kind"] for o in retained["attempts"][0]["observations"]], [
                        "unknown", "refused", "not_delivered",
                    ])

    def test_malformed_input_refuses_without_claim_child_or_replay(self):
        cases = (
            ("huge_operation_seconds", "invalid_limits"),
            ("deeply_nested_json", "local_or_protocol_failure"),
        )
        for case, reason in cases:
            for prior_state in ("planned", "unknown"):
                with self.subTest(input=case, prior_state=prior_state):
                    with self.consumer() as (
                        original, request, send, bookkeeping, trace, source,
                    ):
                        if prior_state == "unknown":
                            initial = send()
                            self.assertTrue(initial["claimed"])
                            self.assertEqual(initial["reason"], "stdout_eof")
                            self.assertEqual(initial["peer_input"], "possible_submission")
                            self.assertEqual(initial["owned_child"], {
                                "started": True, "reaped": True, "exit_code": 23,
                            })
                        retained = bookkeeping("show", "failure-1")
                        self.assertEqual(retained["state"], prior_state)
                        self.assertEqual(len(retained["attempts"]), int(prior_state == "unknown"))
                        trace_before = trace.read_bytes() if trace.exists() else None
                        for attempt_id in ("attempt-failure", "fresh-unreconciled-attempt"):
                            malformed = {**request, "attempt_id": attempt_id}
                            if case == "huge_operation_seconds":
                                malformed["limits"] = {
                                    **request["limits"], "operation_seconds": 10 ** 399,
                                }
                                raw = json.dumps(malformed).encode("utf-8")
                            else:
                                # Keep the request within the byte ceiling while
                                # exceeding the decoder's ordinary nesting depth.
                                malformed["evidence_ref"] = "nested-input-placeholder"
                                raw = json.dumps(malformed).encode("utf-8").replace(
                                    b'"nested-input-placeholder"',
                                    b"[" * 4000 + b"0" + b"]" * 4000,
                                )
                            self.assertLessEqual(len(raw), 32768)
                            result = send(raw=raw)
                            self.assertEqual(result["stage"], "request")
                            self.assertEqual(result["reason"], reason)
                            self.assertFalse(result["claimed"])
                            self.assertEqual(result["peer_input"], "not_attempted")
                            self.assertEqual(result["owned_child"], {
                                "started": False, "reaped": False, "exit_code": None,
                            })
                            self.assertEqual(bookkeeping("show", "failure-1"), retained)
                            self.assertEqual(
                                trace.read_bytes() if trace.exists() else None, trace_before,
                            )
                            self.assert_no_receipt(retained, original)

    def test_request_at_32768_bytes_is_admitted_and_submits(self):
        with self.consumer(mode="tool_success") as (
            original, request, send, bookkeeping, trace, source,
        ):
            encoded = json.dumps(request).encode("utf-8")
            self.assertLess(len(encoded), 32768)
            boundary = encoded + b" " * (32768 - len(encoded))
            self.assertEqual(len(boundary), 32768)
            result = send(raw=boundary)
            self.assertEqual(result["stage"], "call")
            self.assertEqual(result["reason"], "submitted")
            self.assertEqual(result["peer_input"], "submitted")
            self.assertTrue(result["claimed"])
            self.assertEqual(result["owned_child"], {
                "started": True, "reaped": True, "exit_code": 23,
            })
            records = [json.loads(line) for line in trace.read_bytes().splitlines()]
            self.assertGreater(records[0]["started_pid"], 0)
            self.assertEqual([r["method"] for r in records if "method" in r], [
                "initialize", "notifications/initialized", "tools/list", "tools/call",
            ])
            self.assertEqual(records[-1], {"stdin_eof": True})
            retained = bookkeeping("show", "failure-1")
            self.assert_no_receipt(retained, original)
            self.assertEqual(retained["state"], "submitted")
            self.assertEqual(len(retained["attempts"]), 1)
            self.assertEqual(
                [o["kind"] for o in retained["attempts"][0]["observations"]],
                ["unknown", "unknown", "submitted"],
            )
            self.assert_no_replay(request, send, bookkeeping, trace, retained)

    def test_oversized_control_frame_records_refusal_before_possible_submission(self):
        # The minimal supported catalog has no destination-length constraint.
        # This destination alone exceeds the entire outgoing frame ceiling.
        with self.consumer(mode="tool_success", target="uds:" + "x" * 4096) as (
            original, request, send, bookkeeping, trace, source,
        ):
            result = send()
            self.assertEqual(result["stage"], "catalog")
            self.assertEqual(result["reason"], "control_frame_limit")
            self.assertEqual(result["peer_input"], "not_attempted")
            self.assertTrue(result["claimed"])
            self.assertEqual(result["owned_child"], {
                "started": True, "reaped": True, "exit_code": 23,
            })
            records = [json.loads(line) for line in trace.read_bytes().splitlines()]
            self.assertGreater(records[0]["started_pid"], 0)
            self.assertEqual([r["method"] for r in records if "method" in r], [
                "initialize", "notifications/initialized", "tools/list",
            ])
            self.assertEqual(records[-1], {"stdin_eof": True})
            retained = bookkeeping("show", "failure-1")
            self.assert_no_receipt(retained, original)
            self.assertEqual(retained["state"], "refused")
            self.assertEqual(len(retained["attempts"]), 1)
            attempt = retained["attempts"][0]
            self.assertEqual(attempt["actor"], request["actor"])
            self.assertEqual(attempt["submission"], "refused")
            self.assertEqual([o["kind"] for o in attempt["observations"]], [
                "unknown", "refused", "not_delivered",
            ])
            self.assertEqual(json.loads(attempt["observations"][0]["detail"]), request)
            self.assertIn("no tools/call was sent", attempt["observations"][1]["detail"])
            self.assert_no_replay(request, send, bookkeeping, trace, retained)

    def test_oversized_payload_frame_records_refusal_without_a_call(self):
        oversized = {
            "message_id": "failure-1",
            "sender": {"thread_id": "original", "host_id": "origin-host"},
            "recipient": {"thread_id": "recipient", "host_id": "peer-host"},
            "owner": {"thread_id": "owner", "host_id": "local"},
            "payload": "x" * 4096, "authority_ref": "synthetic://grant/intake",
            "holds": [],
        }
        with self.consumer(mode="tool_success", original=oversized) as (
            original, request, send, bookkeeping, trace, source,
        ):
            result = send()
            self.assertEqual(result["reason"], "control_frame_limit")
            self.assertEqual(result["peer_input"], "not_attempted")
            records = [json.loads(line) for line in trace.read_bytes().splitlines()]
            self.assertNotIn("tools/call", [r.get("method") for r in records])
            retained = bookkeeping("show", "failure-1")
            self.assertEqual(retained["state"], "refused")
            observations = retained["attempts"][0]["observations"]
            self.assertEqual([o["kind"] for o in observations], ["unknown", "refused", "not_delivered"])
            # The frame-size refusal is definite too: no call was written in this attempt.
            self.assertEqual(json.loads(observations[2]["detail"]), {
                "evidence": "sender_phase_record", "path": "route",
                "phase": "refused_before_possible_submission", "reason": "control_frame_limit"})

    def test_an_uncertain_attempt_is_not_followed_by_another_through_the_senders_record(self):
        with self.consumer() as (original, request, send, bookkeeping, trace, source):
            first = send()
            self.assertEqual(first["peer_input"], "possible_submission")
            retained = bookkeeping("show", "failure-1")
            trace_bytes = trace.read_bytes()
            later = {**request, "attempt_id": "attempt-later", "after_attempt": "attempt-failure",
                     "decision_ref": "synthetic://decision/later"}
            repeated = send(raw=json.dumps(later).encode("utf-8"))
            self.assertFalse(repeated["claimed"])
            self.assertEqual(repeated["reason"], "claim_not_acquired")
            self.assertEqual(trace.read_bytes(), trace_bytes)
            self.assertEqual(bookkeeping("show", "failure-1"), retained)

    def test_stderr_overflow_at_one_mib_preserves_failure_and_uncertainty(self):
        with self.consumer(mode="stderr_overflow") as (
            original, request, send, bookkeeping, trace, source,
        ):
            request["limits"]["stderr_bytes"] = 1048576
            result = send()
            self.assertEqual(result["stage"], "call")
            self.assertEqual(result["reason"], "stderr_limit")
            self.assertEqual(result["peer_input"], "possible_submission")
            self.assertTrue(result["claimed"])
            closure = result["owned_child"]
            self.assertTrue(closure["started"])
            self.assertTrue(closure["reaped"])
            self.assertIn(closure["exit_code"], (23, -15, -9))
            self.assertEqual(closure["closure_error"], "stderr_limit")
            records = [json.loads(line) for line in trace.read_bytes().splitlines()]
            self.assertGreater(records[0]["started_pid"], 0)
            self.assertEqual([r["method"] for r in records if "method" in r], [
                "initialize", "notifications/initialized", "tools/list", "tools/call",
            ])
            retained = bookkeeping("show", "failure-1")
            self.assert_no_receipt(retained, original)
            self.assertEqual(retained["state"], "unknown")
            self.assertEqual(len(retained["attempts"]), 1)
            attempt = retained["attempts"][0]
            self.assertEqual(attempt["actor"], request["actor"])
            self.assertEqual([o["kind"] for o in attempt["observations"]], ["unknown", "unknown"])
            self.assertEqual(json.loads(attempt["observations"][-1]["detail"]), {
                "phase": "possible_submission", "path": "route", "to": request["target"],
            })
            self.assert_no_replay(request, send, bookkeeping, trace, retained)

    def test_call_deadline_preserves_uncertainty_and_reaps_owned_child(self):
        with self.consumer(mode="call_deadline") as (
            original, request, send, bookkeeping, trace, source,
        ):
            # Keep the ordinary eight-second protocol budget for startup and
            # negotiation; the child delays its call reply for thirty seconds.
            result = send()
            self.assertEqual(result["stage"], "call")
            self.assertEqual(result["reason"], "deadline")
            self.assertEqual(result["peer_input"], "possible_submission")
            self.assertTrue(result["claimed"])
            # The child ignores its closed input while it sleeps, so the sender
            # stops it with SIGTERM rather than waiting or killing it.
            self.assertEqual(result["owned_child"], {
                "started": True, "reaped": True, "exit_code": -15,
                "closed_by": "terminate",
            })
            records = [json.loads(line) for line in trace.read_bytes().splitlines()]
            self.assertGreater(records[0]["started_pid"], 0)
            self.assertEqual([r["method"] for r in records if "method" in r], [
                "initialize", "notifications/initialized", "tools/list", "tools/call",
            ])
            before_call = next(r["before_call"] for r in records if "before_call" in r)
            self.assertEqual(before_call["state"], "unknown")
            self.assertEqual(json.loads(before_call["attempts"][0]["observations"][-1]["detail"]), {
                "phase": "possible_submission", "path": "route", "to": request["target"],
            })
            self.assertFalse(any("stdin_eof" in r for r in records))
            retained = bookkeeping("show", "failure-1")
            self.assert_no_receipt(retained, original)
            self.assertEqual(retained["state"], "unknown")
            self.assertEqual(len(retained["attempts"]), 1)
            attempt = retained["attempts"][0]
            self.assertEqual(attempt["actor"], request["actor"])
            self.assertEqual([o["kind"] for o in attempt["observations"]], ["unknown", "unknown"])
            self.assertEqual(json.loads(attempt["observations"][-1]["detail"]), {
                "phase": "possible_submission", "path": "route", "to": request["target"],
            })
            self.assert_no_replay(request, send, bookkeeping, trace, retained)

    def test_request_over_32768_bytes_is_rejected_without_claim_or_child(self):
        with self.consumer() as (original, request, send, bookkeeping, trace, source):
            planned = bookkeeping("show", "failure-1")
            encoded = json.dumps(request).encode("utf-8")
            oversized = encoded + b" " * (32769 - len(encoded))
            self.assertEqual(len(oversized), 32769)
            result = send(raw=oversized)
            self.assertEqual(result["stage"], "request")
            self.assertEqual(result["reason"], "request_limit")
            self.assertFalse(result["claimed"])
            self.assertEqual(result["peer_input"], "not_attempted")
            self.assertEqual(result["owned_child"], {
                "started": False, "reaped": False, "exit_code": None,
            })
            self.assertFalse(trace.exists())
            retained = bookkeeping("show", "failure-1")
            self.assertEqual(retained, planned)
            self.assertEqual(retained["attempts"], [])
            self.assert_no_receipt(retained, original)

    def test_tool_error_stays_unknown_while_non_error_marks_only_submission(self):
        for mode, reason, state, peer_input in (
            ("tool_success", "submitted", "submitted", "submitted"),
            ("tool_error", "tool_error", "unknown", "possible_submission"),
        ):
            with self.subTest(mode=mode):
                with self.consumer(mode=mode) as (original, request, send, bookkeeping, trace, source):
                    result = send()
                    self.assertEqual(result["stage"], "call")
                    self.assertEqual(result["reason"], reason)
                    self.assertEqual(result["peer_input"], peer_input)
                    self.assertNotIn("Private unvalidated tool text.", json.dumps(result))
                    self.assertTrue(result["claimed"])
                    self.assertEqual(result["owned_child"], {
                        "started": True, "reaped": True, "exit_code": 23,
                    })
                    records = [json.loads(line) for line in trace.read_bytes().splitlines()]
                    self.assertGreater(records[0]["started_pid"], 0)
                    self.assertEqual([r["method"] for r in records if "method" in r], [
                        "initialize", "notifications/initialized", "tools/list", "tools/call",
                    ])
                    self.assertEqual(records[-1], {"stdin_eof": True})
                    retained = bookkeeping("show", "failure-1")
                    self.assert_no_receipt(retained, original)
                    self.assertEqual(retained["state"], state)
                    self.assertEqual(len(retained["attempts"]), 1)
                    attempt = retained["attempts"][0]
                    self.assertEqual(attempt["actor"], request["actor"])
                    self.assertEqual(attempt["submission"], state)
                    self.assertEqual([o["kind"] for o in attempt["observations"]], [
                        "unknown", "unknown", state,
                    ])
                    self.assertEqual(json.loads(attempt["observations"][-1]["detail"]), {
                        "target": "uds:/synthetic/selected-peer.sock",
                        "tool_result": {
                            "content": [{"type": "text", "text": "Private unvalidated tool text."}],
                            "isError": mode == "tool_error",
                        },
                    })
                    self.assert_no_replay(request, send, bookkeeping, trace, retained)

    def test_stdout_overflow_after_call_preserves_first_failure_and_uncertainty(self):
        with self.consumer(mode="stdout_overflow") as (original, request, send, bookkeeping, trace, source):
            result = send()
            self.assertEqual(result["stage"], "call")
            self.assertEqual(result["reason"], "stdout_limit")
            self.assertEqual(result["peer_input"], "possible_submission")
            self.assertTrue(result["claimed"])
            closure = result["owned_child"]
            self.assertTrue(closure["started"])
            self.assertTrue(closure["reaped"])
            self.assertIn(closure["exit_code"], (23, -15, -9))
            self.assertEqual(closure["closure_error"], "stdout_limit")
            records = [json.loads(line) for line in trace.read_bytes().splitlines()]
            self.assertGreater(records[0]["started_pid"], 0)
            self.assertEqual([r["method"] for r in records if "method" in r], [
                "initialize", "notifications/initialized", "tools/list", "tools/call",
            ])
            if closure["exit_code"] == 23:
                self.assertEqual(records[-1], {"stdin_eof": True})
            retained = bookkeeping("show", "failure-1")
            self.assert_no_receipt(retained, original)
            self.assertEqual(retained["state"], "unknown")
            self.assertEqual(len(retained["attempts"]), 1)
            attempt = retained["attempts"][0]
            self.assertEqual(attempt["actor"], request["actor"])
            self.assertEqual([o["kind"] for o in attempt["observations"]], ["unknown", "unknown"])
            self.assertEqual(json.loads(attempt["observations"][-1]["detail"]), {
                "phase": "possible_submission", "path": "route", "to": "uds:/synthetic/selected-peer.sock",
            })
            self.assert_no_replay(request, send, bookkeeping, trace, retained)

    def test_missing_sendmessage_refuses_before_peer_input_and_reaps_owned_child(self):
        original = {
            "message_id": "catalog-1",
            "sender": {"thread_id": "original", "host_id": "local"},
            "recipient": {"thread_id": "recipient", "host_id": "local"},
            "owner": {"thread_id": "owner", "host_id": "local"},
            "payload": "Intake only.\r\nKeep é and café.\n",
            "authority_ref": "synthetic://grant/intake",
            "holds": ["Publication remains held."],
        }
        actor = {"thread_id": "replacement", "host_id": "local"}
        with self.consumer(
            mode="catalog_only", catalog={"tools": []}, original=original, actor=actor,
            attempt_id="attempt-catalog", evidence_ref="synthetic://evidence/catalog",
            target="uds:/synthetic/nomination-only.sock",
        ) as (original, request, send, bookkeeping, trace, source):
            result = send()
            self.assertEqual(result["stage"], "catalog")
            self.assertEqual(result["reason"], "missing_sendmessage")
            self.assertEqual(result["peer_input"], "not_attempted")
            self.assertTrue(result["claimed"])
            self.assertEqual(result["attempt_id"], "attempt-catalog")
            self.assertEqual(result["owned_child"], {
                "started": True, "reaped": True, "exit_code": 23,
            })
            records = [json.loads(line) for line in trace.read_text().splitlines()]
            before = records[0]["before_start"]
            self.assertEqual(before["state"], "unknown")
            self.assertEqual(before["attempts"][0]["actor"], actor)
            self.assertEqual(before["attempts"][0]["observations"][-1]["kind"], "unknown")
            self.assertEqual(
                [record["method"] for record in records[1:-1]],
                ["initialize", "notifications/initialized", "tools/list"],
            )
            self.assertEqual(records[-1], {"stdin_eof": True})
            retained = bookkeeping("show", "catalog-1")
            self.assertEqual({key: retained[key] for key in original}, original)
            self.assertEqual(retained["state"], "refused")
            attempt = retained["attempts"][0]
            self.assertEqual(attempt["attempt_id"], "attempt-catalog")
            self.assertEqual(attempt["actor"], actor)
            self.assertEqual([item["kind"] for item in attempt["observations"]], [
                "unknown", "refused", "not_delivered"])
            self.assertEqual(attempt["observations"][-1]["evidence_ref"], request["evidence_ref"])
            self.assertFalse(attempt["received"])
            self.assertFalse(attempt["handled"])
            self.assertFalse(attempt["completed"])

    def test_peer_envelope_submission_preserves_content_and_does_not_imply_receipt(self):
        catalogs = (
            ("minimal", {"tools": [{
                "name": "SendMessage",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string"},
                        "message": {"type": "string"},
                    },
                    "required": ["to", "message"],
                    "additionalProperties": False,
                },
            }]}),
            ("annotated_with_optional_priority", {"tools": [{
                "name": "SendMessage",
                "inputSchema": {
                    "type": "object",
                    "title": "Send a peer message",
                    "description": "Submit the supplied destination and message.",
                    "properties": {
                        "to": {
                            "type": "string", "title": "Destination",
                            "description": "The explicitly selected peer.",
                            "default": "uds:/annotation-only/default.sock",
                        },
                        "message": {
                            "type": "string", "title": "Message",
                            "description": "The supplied peer envelope.",
                            "default": "Annotation only; never send this text.",
                        },
                        "priority": {"type": "string", "enum": ["normal", "urgent"]},
                    },
                    "required": ["to", "message"],
                    "additionalProperties": False,
                },
            }]}),
        )
        for name, catalog in catalogs:
            with self.subTest(catalog=name):
                self._assert_peer_envelope_submission(catalog)

    def assert_catalog_refusal(self, catalog, target, reason, diagnosis=None):
        with self.consumer(mode="tool_success", catalog=catalog) as (
            original, request, send, bookkeeping, trace, source,
        ):
            request["target"] = target
            result = send()
            self.assertEqual(result["stage"], "catalog")
            self.assertEqual(result["reason"], reason)
            self.assertEqual(result["peer_input"], "not_attempted")
            self.assertTrue(result["claimed"])
            self.assertEqual(result["owned_child"], {
                "started": True, "reaped": True, "exit_code": 23,
            })
            records = [json.loads(line) for line in trace.read_bytes().splitlines()]
            self.assertGreater(records[0]["started_pid"], 0)
            self.assertEqual([r["method"] for r in records if "method" in r], [
                "initialize", "notifications/initialized", "tools/list",
            ])
            self.assertEqual(records[-1], {"stdin_eof": True})
            retained = bookkeeping("show", "failure-1")
            self.assert_no_receipt(retained, original)
            self.assertEqual(retained["state"], "refused")
            self.assertEqual(len(retained["attempts"]), 1)
            observations = retained["attempts"][0]["observations"]
            self.assertEqual([o["kind"] for o in observations], ["unknown", "refused", "not_delivered"])
            self.assertEqual(json.loads(observations[0]["detail"])["target"], target)
            if diagnosis is not None:
                self.assertIn(diagnosis, observations[1]["detail"])
            self.assert_no_replay(request, send, bookkeeping, trace, retained)

    def test_destination_cr_or_lf_refuses_before_possible_submission(self):
        for target in ("uds:/synthetic/peer\r.sock", "uds:/synthetic/peer\n.sock"):
            with self.subTest(target=target):
                self.assert_catalog_refusal(
                    retained_destination_catalog(), target,
                    "destination_constraint_violation", "CR/LF",
                )

    def test_destination_above_300_code_units_refuses_before_possible_submission(self):
        self.assert_catalog_refusal(
            retained_destination_catalog(), "uds:" + "a" * 297,
            "destination_constraint_violation", "300 UTF-16 code units",
        )

    def test_astral_destination_above_300_code_units_refuses(self):
        self.assert_catalog_refusal(
            retained_destination_catalog(), "uds:" + "a" * 295 + "\U0001f600",
            "destination_constraint_violation", "300 UTF-16 code units",
        )

    def test_destination_at_300_code_units_preserves_the_supplied_target(self):
        for target in (
            "uds:" + "a" * 296,
            "uds:" + "é" * 296,
            "uds:" + "e\u0301" * 148,
            "uds:" + "\U0001f600" * 148,
        ):
            with self.subTest(target=target):
                self._assert_peer_envelope_submission(retained_destination_catalog(), target)

    def test_unknown_dialects_and_constraints_keep_unsupported_schema_refusal(self):
        mutations = (
            ("unknown_dialect", lambda schema: schema.update({"$schema": "https://example.invalid/schema"})),
            ("malformed_dialect", lambda schema: schema.update({"$schema": None})),
            ("root_constraint", lambda schema: schema.update({"maxProperties": 2})),
            ("direct_pattern", lambda schema: schema["properties"]["to"].update({"pattern": "^uds:"})),
            ("changed_pattern", lambda schema: schema["properties"]["to"].update({
                "allOf": [{"pattern": r"^[^\n\r]*$"}, {"pattern": r"^[\s\S]{0,301}$"}],
            })),
            ("extra_constraint", lambda schema: schema["properties"]["to"]["allOf"][0].update({"maxLength": 300})),
            ("partial_constraints", lambda schema: schema["properties"]["to"]["allOf"].pop()),
            ("malformed_constraints", lambda schema: schema["properties"]["to"].update({"allOf": {}})),
            ("message_constraint", lambda schema: schema["properties"]["message"].update({"maxLength": 100})),
            ("message_allof", lambda schema: schema["properties"]["message"].update({"allOf": []})),
        )
        for name, mutate in mutations:
            with self.subTest(profile=name):
                catalog = retained_destination_catalog()
                mutate(catalog["tools"][0]["inputSchema"])
                self.assert_catalog_refusal(
                    catalog, "uds:/synthetic/peer.sock", "unsupported_sendmessage_schema",
                )

    def test_legacy_profile_keeps_unconstrained_destination_behavior(self):
        catalog = retained_destination_catalog()
        schema = catalog["tools"][0]["inputSchema"]
        del schema["$schema"]
        del schema["properties"]["to"]["allOf"]
        schema["properties"]["to"]["default"] = "uds:/unused/default.sock"
        schema["properties"]["message"]["default"] = "Unused default."
        self._assert_peer_envelope_submission(catalog, "uds:" + "a" * 297 + "\r\n")

    def test_known_destination_constraints_do_not_require_a_dialect_annotation(self):
        catalog = retained_destination_catalog()
        del catalog["tools"][0]["inputSchema"]["$schema"]
        self._assert_peer_envelope_submission(catalog)
        self.assert_catalog_refusal(
            catalog, "uds:/synthetic/peer\n.sock",
            "destination_constraint_violation", "CR/LF",
        )

    def test_retained_destination_profile_submits_the_exact_peer_envelope(self):
        self._assert_peer_envelope_submission(retained_destination_catalog())

    def _assert_peer_envelope_submission(self, catalog, target="uds:/synthetic/selected-peer.sock"):
        with self.consumer(
            mode="envelope_submission", catalog=catalog,
            message_id="send-1",
            attempt_id="attempt-send", evidence_ref="synthetic://evidence/send", target=target,
        ) as (original, request, send, bookkeeping, trace, source):
            actor = request["actor"]
            result = send()
            self.assertEqual(result["stage"], "call")
            self.assertEqual(result["reason"], "submitted")
            self.assertEqual(result["peer_input"], "submitted")
            self.assertTrue(result["claimed"])
            self.assertEqual(result["owned_child"], {
                "started": True, "reaped": True, "exit_code": 23,
            })
            trace_bytes = trace.read_bytes()
            records = [json.loads(line) for line in trace_bytes.splitlines()]
            before = records[0]["before_start"]
            self.assertEqual(before["state"], "unknown")
            self.assertEqual(
                json.loads(before["attempts"][0]["observations"][0]["detail"])["target"],
                target,
            )
            requests = [record for record in records if "method" in record]
            self.assertEqual([record["method"] for record in requests], [
                "initialize", "notifications/initialized", "tools/list", "tools/call",
            ])
            call = requests[-1]
            self.assertEqual(call["params"]["name"], "SendMessage")
            self.assertEqual(set(call["params"]["arguments"]), {"to", "message"})
            self.assertEqual(call["params"]["arguments"]["to"], target)
            prefix, encoded = call["params"]["arguments"]["message"].split("\n", 1)
            self.assertEqual(prefix, "Peer message (no new operator authority).")
            envelope = json.loads(encoded)
            self.assertEqual(envelope, {
                "schema": "provingkit-peer-message-v1",
                "message_id": "send-1",
                "correlation_id": "conversation-77",
                "sender": {"thread_id": "original", "host_id": "origin-host"},
                "actor": {"thread_id": "replacement", "host_id": "forward-host"},
                "recipient": {"thread_id": "recipient", "host_id": "peer-host"},
                "owner": {"thread_id": "owner", "host_id": "local"},
                "authority_ref": "synthetic://grant/intake",
                "holds": ["No operational transfer.", "Publication remains held."],
                "payload": "Intake only.\r\nKeep e\u0301 and café.\n",
            })
            before_call = next(record["before_call"] for record in records if "before_call" in record)
            self.assertEqual(before_call["state"], "unknown")
            pending_detail = json.loads(before_call["attempts"][0]["observations"][-1]["detail"])
            self.assertEqual(pending_detail, {
                "phase": "possible_submission", "path": "route", "to": target,
            })
            self.assertEqual(records[-1], {"stdin_eof": True})
            retained = bookkeeping("show", "send-1")
            self.assertEqual({key: retained[key] for key in original}, original)
            self.assertEqual(retained["state"], "submitted")
            self.assertEqual(len(retained["attempts"]), 1)
            attempt = retained["attempts"][0]
            self.assertEqual(attempt["attempt_id"], "attempt-send")
            self.assertEqual(attempt["actor"], actor)
            self.assertEqual(attempt["submission"], "submitted")
            self.assertEqual([item["kind"] for item in attempt["observations"]], [
                "unknown", "unknown", "submitted",
            ])
            observation = attempt["observations"][-1]
            self.assertEqual(observation["evidence_ref"], "synthetic://evidence/send")
            self.assertEqual(json.loads(observation["detail"]), {
                "target": target,
                "tool_result": {
                    "content": [{"type": "text", "text": "Unvalidated tool text."}],
                    "isError": False,
                },
            })
            for stage in ("received", "handled", "completed"):
                self.assertFalse(attempt[stage])
            source.write_bytes(json.dumps({**original, "correlation_id": "changed"}).encode("utf-8"))
            self.assertIn("error", bookkeeping("plan", "--input", str(source), success=False))
            self.assertEqual(bookkeeping("show", "send-1"), retained)
            repeated = send()
            self.assertFalse(repeated["claimed"])
            self.assertEqual(repeated["reason"], "claim_not_acquired")
            self.assertEqual(repeated["owned_child"], {
                "started": False, "reaped": False, "exit_code": None,
            })
            self.assertEqual(trace.read_bytes(), trace_bytes)
            self.assertEqual(bookkeeping("show", "send-1"), retained)


NAME_CHILD = textwrap.dedent("""\
    import json
    import os
    import subprocess
    import sys
    import time

    trace_path, config_path = sys.argv[1], sys.argv[2]
    with open(config_path, encoding="utf-8") as source:
        config = json.load(source)
    pages = list(config["pages"])

    def record(value):
        with open(trace_path, "a", encoding="utf-8") as trace:
            trace.write(json.dumps(value) + "\\n")

    record({"started_pid": os.getpid()})
    if config.get("mode") == "writes_while_stopping":
        import signal

        def stop(*_):
            os.write(1, b"x" * 262144)
            os._exit(0)

        signal.signal(signal.SIGTERM, stop)
    if config.get("mode") == "descendant_holds_pipes":
        holder = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        record({"holder_pid": holder.pid})
    for line in sys.stdin:
        request = json.loads(line)
        record(request)
        method = request.get("method")
        if method == "initialize":
            response = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}}
        elif method == "notifications/initialized":
            continue
        elif method == "tools/list":
            response = config["catalog"]
        elif request["params"]["name"] == "ListAgents":
            response = {"content": [{"type": "text", "text": pages.pop(0)}]}
        else:
            record({"sendmessage_frame_bytes": len(line.encode("utf-8"))})
            response = {"content": [{"type": "text", "text":
                        "Message sent to the session; in that session's inbox, not yet read."}]}
        print(json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": response}), flush=True)
    record({"stdin_eof": True})
    if config.get("mode") in ("lingers_after_input_closes", "writes_while_stopping"):
        time.sleep(30)
    raise SystemExit(0)
    """)

LISTAGENTS_TOOL = {"name": "ListAgents", "inputSchema": {
    "$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object",
    "properties": {
        "channel": {"type": "string", "maxLength": 256},
        "q": {"type": "string", "maxLength": 256},
        "cursor": {"type": "string", "maxLength": 256},
    },
    "additionalProperties": False,
}}

DOT = "  ·  "
CALLER = (
    "This session is Fixture Origin [ab12ef] — the name other sessions use to message it "
    "(it is not listed below; a message to it would be a message to yourself)."
)
FOOTER = (
    "[Cloud sessions and other computers are not listed because Remote Control is off "
    "in this session. The user can turn it on with the Remote Control switch in the app; "
    "then list again.]"
)


def desktop_row(name, ref, *, status="idle", age="8h"):
    return "  " + DOT.join((
        f"{name} [{ref}]", "interactive", status, "Claude Desktop session", f"started {age} ago",
    ))


def desktop_listing(*rows, caller=CALLER):
    return "\n".join((caller, "", f"Peer sessions ({len(rows)}):", *rows, "", FOOTER))


LISTING = desktop_listing(
    desktop_row("claude-receiver", "3fa9c1", age="5m"),
    desktop_row("twin", "aa11bb", status="busy", age="1m"),
    desktop_row("twin", "cc22dd", age="2m"),
)


class ClaudeNameSendTests(unittest.TestCase):
    @contextmanager
    def name_consumer(self, *, name="claude-receiver", selection=None, pages=(LISTING,),
                      mode="ordinary", target=None, seconds=8, stdout_bytes=65536,
                      recipient_thread=None, payload="Compare the two results.\n",
                      constrained_destination=True):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = root / "mailbox.sqlite3"
            trace = root / "child.jsonl"
            child = root / "name_child.py"
            child.write_text(NAME_CHILD, encoding="utf-8")
            mailbox = SCRIPTS / "native_codex_mailbox.py"
            if recipient_thread is None:
                # On the name path the planned recipient is named by the requested name.
                recipient_thread = name if target is None else "claude-receiver"
            original = {
                "message_id": "send-1", "correlation_id": "exchange-9",
                "sender": {"thread_id": "original", "host_id": "origin-host"},
                "recipient": {"thread_id": recipient_thread, "host_id": "local"},
                "owner": {"thread_id": "owner", "host_id": "local"},
                "payload": payload,
                "authority_ref": "synthetic://grant/compare", "holds": ["No publication."],
            }
            (root / "message.json").write_text(json.dumps(original), encoding="utf-8")
            send_tool = retained_destination_catalog()["tools"][0]
            if not constrained_destination:
                del send_tool["inputSchema"]["properties"]["to"]["allOf"]
            config = {"pages": list(pages), "mode": mode,
                      "catalog": {"tools": [send_tool, LISTAGENTS_TOOL]}}
            (root / "config.json").write_text(json.dumps(config), encoding="utf-8")

            def bookkeeping(*arguments):
                completed = subprocess.run(
                    [sys.executable, str(mailbox), "--store", str(store), *arguments],
                    capture_output=True, text=True, timeout=10, check=True)
                return json.loads(completed.stdout)

            bookkeeping("init")
            bookkeeping("plan", "--input", str(root / "message.json"))
            request = {
                "message_id": "send-1", "attempt_id": "send-1/attempt/1",
                "actor": {"thread_id": "forwarder", "host_id": "local"},
                "recipient": original["recipient"],
                "command": [sys.executable, str(child), str(trace), str(root / "config.json")],
                "evidence_ref": "synthetic://evidence/name",
                "limits": {"operation_seconds": seconds, "stdout_bytes": stdout_bytes,
                           "stderr_bytes": 4096},
            }
            if target is None:
                request["name"] = name
            else:
                request["target"] = target
            if selection is not None:
                request["selection"] = selection

            def send():
                (root / "request.json").write_text(json.dumps(request), encoding="utf-8")
                started = time.monotonic()
                completed = subprocess.run(
                    [sys.executable, "-B", str(SCRIPTS / "claude_mcp_sender.py"),
                     "--store", str(store), "--request", str(root / "request.json")],
                    capture_output=True, text=True, timeout=40)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                result = json.loads(completed.stdout)
                result["elapsed"] = time.monotonic() - started
                return result

            def calls():
                records = [json.loads(line) for line in trace.read_text().splitlines()]
                return [r["params"] for r in records if r.get("method") == "tools/call"]

            try:
                yield original, request, send, bookkeeping, calls, trace
            finally:
                for line in trace.read_text().splitlines() if trace.exists() else []:
                    holder = json.loads(line).get("holder_pid")
                    if holder:
                        try:
                            os.kill(holder, signal.SIGKILL)
                        except OSError:
                            pass

    def assert_refused_without_send(self, result, reason, calls, bookkeeping, unreadable_rows=0):
        self.assertEqual(result["path"], "name")
        self.assertEqual(result["reason"], reason)
        self.assertEqual(result["peer_input"], "not_attempted")
        self.assertNotIn("SendMessage", [call["name"] for call in calls()])
        retained = bookkeeping("show", "send-1")
        self.assertEqual(retained["state"], "refused")
        observations = retained["attempts"][0]["observations"]
        self.assertEqual([o["kind"] for o in observations], ["unknown", "refused", "not_delivered"])
        self.assertIn("no sendmessage was sent", observations[1]["detail"].lower())
        # The sender's own phase record is the evidence that the attempt did not deliver.
        evidence = json.loads(observations[2]["detail"])
        self.assertEqual(result["unreadable_rows"], unreadable_rows)
        self.assertEqual(evidence, {
            "evidence": "sender_phase_record", "path": "name",
            "phase": "refused_before_possible_submission", "reason": reason,
            "unreadable_rows": unreadable_rows})
        return observations[1]["detail"]

    def test_name_submits_with_one_call_and_closes_without_a_signal(self):
        with self.name_consumer() as (original, request, send, bookkeeping, calls, trace):
            result = send()
            self.assertEqual(result["path"], "name")
            self.assertEqual(result["reason"], "submitted")
            self.assertEqual(result["owned_child"], {
                "started": True, "reaped": True, "exit_code": 0})
            made = calls()
            self.assertEqual([call["name"] for call in made], ["ListAgents", "SendMessage"])
            self.assertEqual(made[0]["arguments"], {})
            self.assertEqual(made[1]["arguments"]["to"], "claude-receiver")
            envelope = json.loads(made[1]["arguments"]["message"].split("\n", 1)[1])
            self.assertEqual(envelope["sender"], original["sender"])
            self.assertEqual(envelope["actor"], request["actor"])
            self.assertEqual(envelope["correlation_id"], "exchange-9")
            retained = bookkeeping("show", "send-1")
            self.assertEqual(retained["state"], "submitted")
            bound = json.loads(retained["attempts"][0]["observations"][1]["detail"])
            # The route path records the same shape without the row.
            self.assertEqual(set(bound), {"phase", "path", "to", "row", "unreadable_rows"})
            self.assertEqual(result["unreadable_rows"], 0)
            self.assertEqual(bound["unreadable_rows"], 0)
            self.assertEqual(bound["phase"], "possible_submission")
            self.assertEqual(bound["path"], "name")
            self.assertEqual(bound["to"], "claude-receiver")
            # The record keeps the row it addressed: its name, reference and kind.
            self.assertEqual(
                {key: bound["row"][key] for key in ("name", "ref", "kind")},
                {"name": "claude-receiver", "ref": "3fa9c1", "kind": "interactive"})
            self.assertEqual(retained["recipient"]["thread_id"], request["name"])

    def test_the_planned_recipient_must_carry_the_requested_name(self):
        # The record and the address must say the same thing; a session id is not the name.
        with self.name_consumer(recipient_thread="3fa9c1-session-id") as (
                _, request, send, bookkeeping, calls, trace):
            result = send()
            self.assertEqual(result["reason"], "recipient_name_mismatch")
            self.assertFalse(result["claimed"])
            self.assertEqual(result["owned_child"], {
                "started": False, "reaped": False, "exit_code": None})
            self.assertFalse(trace.exists())
            self.assertEqual(bookkeeping("show", "send-1")["state"], "planned")

    def test_a_child_that_outlives_its_closed_input_is_terminated_not_killed(self):
        with self.name_consumer(mode="lingers_after_input_closes", seconds=20) as (
                original, request, send, bookkeeping, calls, trace):
            result = send()
            self.assertEqual(result["reason"], "submitted")
            self.assertEqual(result["owned_child"], {
                "started": True, "reaped": True, "exit_code": -15,
                "closed_by": "terminate"})
            # Input-close grace plus SIGTERM, far short of the 20-second deadline.
            self.assertLess(result["elapsed"], 10)

    def test_a_child_that_writes_while_it_stops_is_drained_not_killed(self):
        with self.name_consumer(mode="writes_while_stopping", seconds=20,
                                stdout_bytes=1048576) as (
                original, request, send, bookkeeping, calls, trace):
            result = send()
            self.assertEqual(result["reason"], "submitted")
            # It exits by itself once its 256 KiB reach the drained pipe.
            self.assertEqual(result["owned_child"], {
                "started": True, "reaped": True, "exit_code": 0,
                "closed_by": "terminate"})
            self.assertLess(result["elapsed"], 10)

    def test_a_descendant_holding_the_pipes_does_not_extend_the_close(self):
        with self.name_consumer(mode="descendant_holds_pipes", seconds=20) as (
                original, request, send, bookkeeping, calls, trace):
            result = send()
            self.assertEqual(result["reason"], "submitted")
            self.assertEqual(result["owned_child"], {
                "started": True, "reaped": True, "exit_code": 0})
            self.assertLess(result["elapsed"], 10)

    def test_a_name_with_no_local_row_is_refused_before_the_call(self):
        with self.name_consumer(name="nobody") as (_, request, send, bookkeeping, calls, _t):
            self.assert_refused_without_send(send(), "no_matching_local_row", calls, bookkeeping)

    TWINS = [
        {"name": "twin", "ref": "aa11bb", "kind": "interactive", "local": True},
        {"name": "twin", "ref": "cc22dd", "kind": "interactive", "local": True},
    ]

    def test_an_ambiguous_name_without_selection_is_refused_before_the_call(self):
        with self.name_consumer(name="twin") as (_, request, send, bookkeeping, calls, _t):
            result = send()
            detail = self.assert_refused_without_send(result, "ambiguous_name", calls, bookkeeping)
            self.assertIn("2 rows", detail)
            # Each matching row of this attempt's listing, and no other row.
            self.assertEqual(result["needs"], "selection")
            self.assertCountEqual(result["candidates"], self.TWINS)

    def test_a_refused_ambiguous_name_continues_as_a_reconciled_later_attempt(self):
        with self.name_consumer(name="twin") as (_, request, send, bookkeeping, calls, trace):
            first = send()
            self.assertEqual(first["reason"], "ambiguous_name")
            self.assertCountEqual(first["candidates"], self.TWINS)
            # The caller asks for the later attempt with the selection and both fields.
            request.update({
                "attempt_id": "send-1/attempt/2", "selection": {"ref": "cc22dd"},
                "after_attempt": "send-1/attempt/1",
                "decision_ref": "synthetic://decision/select-cc22dd",
            })
            second = send()
            self.assertTrue(second["claimed"])
            self.assertEqual(second["reason"], "submitted")
            made = calls()
            self.assertEqual([call["name"] for call in made],
                             ["ListAgents", "ListAgents", "SendMessage"])
            self.assertEqual(made[-1]["arguments"]["to"], "twin [cc22dd]")
            retained = bookkeeping("show", "send-1")
            self.assertEqual(retained["state"], "submitted")
            first_attempt, second_attempt = retained["attempts"]
            self.assertEqual([o["kind"] for o in first_attempt["observations"]],
                             ["unknown", "refused", "not_delivered"])
            self.assertIsNone(first_attempt["reconciliation"])
            self.assertEqual(second_attempt["reconciliation"], {
                "after_attempt": "send-1/attempt/1",
                "nondelivery_ref": request["evidence_ref"],
                "decision_ref": "synthetic://decision/select-cc22dd",
            })
            self.assertEqual([o["kind"] for o in second_attempt["observations"]],
                             ["unknown", "unknown", "submitted"])

    def test_one_reconciliation_field_without_the_other_is_refused_before_any_claim(self):
        for field in ("after_attempt", "decision_ref"):
            with self.subTest(field=field), self.name_consumer() as (
                    _, request, send, bookkeeping, calls, trace):
                request[field] = "synthetic://only-one"
                result = send()
                self.assertEqual(result["reason"], "invalid_reconciliation")
                self.assertFalse(result["claimed"])
                self.assertFalse(trace.exists())
                self.assertEqual(bookkeeping("show", "send-1")["state"], "planned")

    def test_a_submitted_attempt_is_not_followed_by_another_through_the_senders_record(self):
        with self.name_consumer() as (_, request, send, bookkeeping, calls, trace):
            self.assertEqual(send()["reason"], "submitted")
            retained = bookkeeping("show", "send-1")
            request.update({"attempt_id": "send-1/attempt/2", "after_attempt": "send-1/attempt/1",
                            "decision_ref": "synthetic://decision/again"})
            repeated = send()
            self.assertFalse(repeated["claimed"])
            self.assertEqual(repeated["reason"], "claim_not_acquired")
            self.assertEqual([call["name"] for call in calls()], ["ListAgents", "SendMessage"])
            self.assertEqual(bookkeeping("show", "send-1"), retained)

    def test_a_selected_row_is_addressed_by_its_name_and_this_listings_ref(self):
        with self.name_consumer(name="twin", selection={"ref": "cc22dd"}) as (
                _, request, send, bookkeeping, calls, _t):
            result = send()
            self.assertEqual(result["reason"], "submitted")
            self.assertEqual(calls()[-1]["arguments"]["to"], "twin [cc22dd]")

    def test_a_selection_with_a_unique_name_must_match_that_row(self):
        with self.name_consumer(selection={"ref": "zz99yy"}) as (
                _, request, send, bookkeeping, calls, _t):
            result = send()
            self.assert_refused_without_send(
                result, "selection_not_in_listing", calls, bookkeeping)
            self.assertEqual([call["name"] for call in calls()], ["ListAgents"])
            self.assertEqual(result["candidates"], [
                {"name": "claude-receiver", "ref": "3fa9c1", "kind": "interactive", "local": True}])
        with self.name_consumer(selection={"ref": "3fa9c1"}) as (
                _, request, send, bookkeeping, calls, _t):
            self.assertEqual(send()["reason"], "submitted")
            self.assertEqual(calls()[-1]["arguments"]["to"], "claude-receiver")
            bound = json.loads(
                bookkeeping("show", "send-1")["attempts"][0]["observations"][1]["detail"])
            # A matching singleton selection checks the ref and sends the name bare.
            self.assertEqual(bound["to"], "claude-receiver")
            self.assertEqual((bound["row"]["name"], bound["row"]["ref"]),
                             ("claude-receiver", "3fa9c1"))

    def test_a_name_that_looks_like_a_route_is_refused_before_any_claim(self):
        route_name = "uds:/synthetic/outside.sock"
        listing = "\n".join([
            "Peer sessions (1):", "  " + route_name + DOT + "interactive" + DOT + "idle"])
        with self.name_consumer(name=route_name, pages=(listing,)) as (
                _, request, send, bookkeeping, calls, trace):
            result = send()
            self.assertEqual(result["reason"], "invalid_name")
            self.assertFalse(result["claimed"])
            self.assertFalse(trace.exists())
            self.assertEqual(bookkeeping("show", "send-1")["state"], "planned")

    def test_a_selection_must_match_exactly_one_row(self):
        for statuses in (("idle", "busy"), ("busy", "idle")):
            listing = desktop_listing(
                *(desktop_row("twin", "cc22dd", status=status) for status in statuses))
            with self.subTest(statuses=statuses), self.name_consumer(
                    name="twin", selection={"ref": "cc22dd"}, pages=(listing,)) as (
                    _, request, send, bookkeeping, calls, _t):
                result = send()
                detail = self.assert_refused_without_send(
                    result, "ambiguous_selection", calls, bookkeeping)
                self.assertIn("2 rows", detail)
                self.assertCountEqual(result["candidates"], [
                    {"name": "twin", "ref": "cc22dd", "kind": "interactive", "local": True},
                    {"name": "twin", "ref": "cc22dd", "kind": "interactive", "local": True},
                ])

    def test_no_matching_row_does_not_request_a_selection(self):
        with self.name_consumer(name="nobody", selection={"ref": "a1"}) as (
                _, request, send, bookkeeping, calls, _t):
            result = send()
            self.assert_refused_without_send(result, "selection_not_in_listing", calls, bookkeeping)
            self.assertEqual(result["candidates"], [])
            self.assertNotIn("needs", result)

    def test_an_inseparable_reference_collision_does_not_request_a_selection(self):
        listing = desktop_listing(
            desktop_row("alpha", "aa12bc"), desktop_row("alpha", "aa12bc", status="busy"))
        with self.name_consumer(name="alpha", pages=(listing,)) as (
                _, request, send, bookkeeping, calls, _t):
            result = send()
            self.assert_refused_without_send(result, "ambiguous_name", calls, bookkeeping)
            self.assertCountEqual([row["ref"] for row in result["candidates"]], ["aa12bc", "aa12bc"])
            self.assertNotIn("needs", result)

    def test_a_unique_local_reference_alternative_prompts_for_selection(self):
        listing = desktop_listing(
            desktop_row("alpha", "aa12bc"), desktop_row("alpha", "aa12bc", status="busy"),
            desktop_row("alpha", "bb34cd"))
        with self.name_consumer(name="alpha", selection={"ref": "aa12bc"}, pages=(listing,)) as (
                _, request, send, bookkeeping, calls, _t):
            result = send()
            self.assert_refused_without_send(result, "ambiguous_selection", calls, bookkeeping)
            self.assertEqual(result["needs"], "selection")
            self.assertIn({
                "name": "alpha", "ref": "bb34cd", "kind": "interactive", "local": True,
            }, result["candidates"])

    def test_a_300_unit_singleton_name_sends_bare_and_refuses_selection_before_listing(self):
        name = "x" * 300
        listing = desktop_listing(desktop_row(name, "aa12bc"))
        with self.name_consumer(name=name, pages=(listing,)) as (
                _, _, send, _, calls, _):
            self.assertEqual(send()["reason"], "submitted")
            self.assertEqual(calls()[-1]["arguments"]["to"], name)
        with self.name_consumer(name=name, pages=(listing,), selection={"ref": "aa12bc"}) as (
                _, _, send, bookkeeping, calls, _):
            result = send()
            self.assertEqual(result["reason"], "destination_constraint_violation")
            self.assertEqual(result["peer_input"], "not_attempted")
            self.assertEqual(calls(), [])
            self.assertNotIn("unreadable_rows", result)
            observations = bookkeeping("show", "send-1")["attempts"][0]["observations"]
            self.assertEqual([item["kind"] for item in observations],
                             ["unknown", "refused", "not_delivered"])
            self.assertNotIn("unreadable_rows", json.loads(observations[-1]["detail"]))

    def test_selected_300_unit_name_refuses_before_listing_in_both_catalog_profiles(self):
        name = "x" * 300
        listing = desktop_listing(desktop_row(name, "aa12bc"), desktop_row(name, "bb34cd"))
        for constrained in (True, False):
            with self.subTest(constrained=constrained), self.name_consumer(
                    name=name, pages=(listing,), selection={"ref": "aa12bc"},
                    constrained_destination=constrained) as (_, _, send, bookkeeping, calls, _):
                result = send()
                self.assertEqual(result["reason"], "destination_constraint_violation")
                self.assertEqual(result["peer_input"], "not_attempted")
                self.assertEqual(calls(), [])
                observations = bookkeeping("show", "send-1")["attempts"][0]["observations"]
                self.assertEqual([item["kind"] for item in observations],
                                 ["unknown", "refused", "not_delivered"])

    def test_a_singleton_bare_frame_sends_at_4096_bytes(self):
        listing = desktop_listing(desktop_row("alpha", "aa12bc"))
        with self.name_consumer(name="alpha", pages=(listing,), payload="x" * 3484) as (
                _, _, send, _, calls, trace):
            self.assertEqual(send()["reason"], "submitted")
            self.assertEqual(calls()[-1]["arguments"]["to"], "alpha")
            records = (json.loads(line) for line in trace.read_text().splitlines())
            self.assertEqual([record["sendmessage_frame_bytes"] for record in records
                              if "sendmessage_frame_bytes" in record], [4096])

    def test_a_selection_hint_requires_a_qualified_destination_that_fits(self):
        name = "x" * 300
        listing = desktop_listing(desktop_row(name, "aa12bc"), desktop_row(name, "bb34cd"))
        for constrained in (True, False):
            with self.subTest(constrained=constrained), self.name_consumer(
                    name=name, pages=(listing,), constrained_destination=constrained) as (
                    _, _, send, bookkeeping, calls, _):
                result = send()
                self.assert_refused_without_send(result, "ambiguous_name", calls, bookkeeping)
                self.assertCountEqual(result["candidates"], [
                    {"name": name, "ref": "aa12bc", "kind": "interactive", "local": True},
                    {"name": name, "ref": "bb34cd", "kind": "interactive", "local": True},
                ])
                self.assertNotIn("needs", result)

    def test_a_selection_hint_requires_a_qualified_frame_that_fits(self):
        listing = desktop_listing(
            desktop_row("alpha", "bb34cd"), desktop_row("alpha", "aa12bc"))
        # A qualified reference adds nine bytes. At 3,475 payload bytes it
        # fits exactly, while a bare address can carry 3,484.
        for length, needs, continuation in (
            (3484, None, "control_frame_limit"), (3475, "selection", "submitted"),
        ):
            with self.subTest(length=length), self.name_consumer(
                    name="alpha", pages=(listing,), payload="x" * length) as (
                    _, request, send, bookkeeping, calls, _t):
                result = send()
                self.assert_refused_without_send(result, "ambiguous_name", calls, bookkeeping)
                self.assertEqual(result.get("needs"), needs)
                request.update({
                    "attempt_id": "send-1/attempt/2", "selection": {"ref": "aa12bc"},
                    "after_attempt": "send-1/attempt/1",
                    "decision_ref": "synthetic://decision/select-aa12bc",
                })
                self.assertEqual(send()["reason"], continuation)
                if continuation == "submitted":
                    self.assertEqual(calls()[-1]["arguments"]["to"], "alpha [aa12bc]")
                else:
                    self.assertEqual([call["name"] for call in calls()], ["ListAgents"])

    def test_a_reference_not_in_this_attempts_listing_is_refused(self):
        # A ref that an earlier attempt's listing showed is not shown in this one.
        with self.name_consumer(name="twin", selection={"ref": "0ld0ne"}) as (
                _, request, send, bookkeeping, calls, _t):
            result = send()
            self.assert_refused_without_send(
                result, "selection_not_in_listing", calls, bookkeeping)
            self.assertCountEqual(result["candidates"], self.TWINS)

    def test_a_refused_name_send_tries_no_second_path_and_cannot_be_replayed(self):
        with self.name_consumer(name="nobody") as (_, request, send, bookkeeping, calls, _t):
            send()
            retained = bookkeeping("show", "send-1")
            self.assertEqual([call["name"] for call in calls()], ["ListAgents"])
            repeated = send()
            self.assertFalse(repeated["claimed"])
            self.assertEqual(repeated["reason"], "claim_not_acquired")
            self.assertEqual(bookkeeping("show", "send-1"), retained)

    def test_a_failure_between_refusal_observations_commits_neither(self):
        for path, target in (("name", None), ("route", "uds:" + "x" * 300)):
            with self.subTest(path=path), self.name_consumer(name="nobody", target=target) as (
                    _, request, send, bookkeeping, calls, trace):
                connection = sqlite3.connect(trace.parent / "mailbox.sqlite3")
                try:
                    connection.execute("""
                        CREATE TRIGGER fail_after_refused BEFORE INSERT ON observations
                        WHEN NEW.kind = 'not_delivered' AND EXISTS (
                            SELECT 1 FROM observations
                            WHERE attempt_id = NEW.attempt_id AND kind = 'refused'
                        )
                        BEGIN
                            SELECT RAISE(ABORT, 'synthetic failure after refused');
                        END
                    """)
                finally:
                    connection.close()

                result = send()
                self.assertEqual(result["path"], path)
                self.assertEqual(result["reason"], "local_or_protocol_failure")
                self.assertEqual(result["peer_input"], "not_attempted")
                self.assertNotIn("SendMessage", [call["name"] for call in calls()])
                # The show command opens a new connection after the failed sender exits.
                observations = bookkeeping("show", "send-1")["attempts"][0]["observations"]
                self.assertEqual([observation["kind"] for observation in observations], ["unknown"])

    def test_a_supplied_route_is_sent_by_that_route_without_the_name_path(self):
        with self.name_consumer(target="uds:/synthetic/prepared.sock") as (
                _, request, send, bookkeeping, calls, _t):
            result = send()
            self.assertEqual(result["path"], "route")
            self.assertEqual(result["reason"], "submitted")
            made = calls()
            self.assertEqual([call["name"] for call in made], ["SendMessage"])
            self.assertEqual(made[0]["arguments"]["to"], "uds:/synthetic/prepared.sock")

    def test_a_short_interactive_title_cannot_supply_a_bare_destination(self):
        for row in (
            "  alpha [draft]" + DOT + "interactive" + DOT + "idle",
            desktop_row("alpha [draft]", "aa12bc").replace(" [aa12bc]", ""),
        ):
            with self.subTest(row=row):
                self.assert_listing_refuses(desktop_listing(row), reason="unrecognized_listing")

    def assert_listing_refuses(self, *pages, name="alpha", selection=None, reason,
                               unreadable_rows=0):
        with self.name_consumer(name=name, selection=selection, pages=pages) as (
                _, _, send, bookkeeping, calls, _):
            result = send()
            self.assert_refused_without_send(result, reason, calls, bookkeeping, unreadable_rows)
            self.assertNotIn("candidates", result)
            self.assertEqual(calls(), [{"name": "ListAgents", "arguments": {}}])

    def test_a_clipped_former_name_cannot_hide_a_second_matching_peer(self):
        clipped = "  " + DOT.join(("alpha", "says it wa other until 1m ago", "bg", "idle"))
        self.assert_listing_refuses(desktop_listing(desktop_row("alpha", "aa12bc"), clipped),
                                    reason="unrecognized_listing")

    def test_a_reachability_count_cannot_authorize_sends_on_a_second_page(self):
        peers = [desktop_row(name, ref) for name, ref in (("beta", "bb34cd"), ("gamma", "cc56de"))]
        first = "\n".join((CALLER, "", "Peer sessions (3):", desktop_row("alpha", "aa12bc"), "",
                           '(… 2 more not shown — call again with cursor="1234abcd" for the next '
                           'page; SendMessage still finds 1 of them by name, or by a unique prefix '
                           'of 3+ characters)'))
        second = "\n".join(("Peer sessions (3):", *peers))
        for name in ("beta", "gamma"):
            with self.subTest(name=name):
                self.assert_listing_refuses(first, second, name=name, reason="listing_incomplete")

    def test_conflicting_reachability_counts_cannot_authorize_a_send(self):
        def page(row, cursor, remaining, reachable):
            return "\n".join(("Peer sessions (4):", row, "",
                              f'(… {remaining} more not shown — call again with cursor="{cursor}" '
                              f'for the next page; SendMessage still finds {reachable} of them by '
                              'name, or by a unique prefix of 3+ characters)'))

        first = CALLER + "\n\n" + page(desktop_row("alpha", "aa12bc"), "1234abcd", 3, "1")
        second = page(desktop_row("beta", "bb34cd"), "2345bcde", 2, "all")
        third = "\n".join(("Peer sessions (4):", desktop_row("gamma", "cc56de"),
                           desktop_row("delta", "dd78ef")))
        self.assert_listing_refuses(first, second, third, reason="listing_incomplete")

    def test_a_title_with_a_missing_row_notice_refuses_the_listing(self):
        self.assert_listing_refuses(desktop_listing(
            desktop_row("alpha", "aa12bc"),
            desktop_row('Draft "… and 2 more sessions not shown" notes', "bb34cd"),
        ), reason="unrecognized_listing")

    def test_a_title_with_a_listing_failure_notice_refuses_the_listing(self):
        self.assert_listing_refuses(desktop_listing(
            desktop_row("alpha", "aa12bc"),
            desktop_row('Draft "(nothing more to list; other sessions could not be read)" notes',
                        "bb34cd"),
        ), reason="unrecognized_listing")

    def test_embedded_heading_footer_and_formatter_notices_refuse_the_listing(self):
        for text in (
            "(session list too long to fetch completely — sessions beyond the first pages "
            "are missing from this listing)",
            "(session names and directories not chosen by a human are withheld on this "
            "connection — /rename a session on its own machine to give it an addressable "
            "name here)",
            "session list too long",
            "missing from this listing",
            "not chosen by a human",
            "withheld on this connection",
            "This session:",
            "not messageable by name",
            "message it by this exact name",
            "Remote Control is off",
            "Remote Control switch",
            "then list again",
            "call again with cursor",
            "for the next page",
            "SendMessage still finds",
            "the name other sessions use to message it",
            "would be a message to yourself",
            "address the main conversation",
        ):
            with self.subTest(control=text):
                self.assert_listing_refuses(desktop_listing(
                    desktop_row("alpha", "aa12bc"), desktop_row(f"Draft {text}", "bb34cd"),
                ), reason="unrecognized_listing")

    def test_a_peer_cannot_repeat_the_caller_name_and_reference(self):
        self.assert_listing_refuses(desktop_listing(desktop_row("Fixture Origin", "ab12ef")),
                                    name="Fixture Origin", reason="self_destination")

    def test_the_caller_name_is_refused_even_with_a_different_reference(self):
        self.assert_listing_refuses(desktop_listing(desktop_row("Fixture Origin", "aa12bc")),
                                    name="Fixture Origin", reason="self_destination")

    def test_notice_text_in_the_caller_name_refuses_the_listing(self):
        caller = CALLER.replace("Fixture Origin", "Fixture No reachable agents.")
        self.assert_listing_refuses(desktop_listing(desktop_row("alpha", "aa12bc"), caller=caller),
                                    reason="unrecognized_listing")

    def test_the_caller_reference_cannot_appear_on_an_unrelated_row(self):
        self.assert_listing_refuses(desktop_listing(
            desktop_row("alpha", "aa12bc"), desktop_row("other", "ab12ef"),
        ), reason="listing_incomplete")

    def test_a_selection_cannot_use_the_caller_reference(self):
        self.assert_listing_refuses(desktop_listing(desktop_row("alpha", "aa12bc")),
                                    selection={"ref": "ab12ef"}, reason="self_destination")

    def test_main_is_refused_even_when_a_desktop_row_has_that_name(self):
        peer = desktop_row("main", "aa12bc")
        self.assert_listing_refuses(desktop_listing(peer), name="main", reason="self_destination")
        process_heading = (
            "This process's main session is Fixture Origin [ab12ef] — the name OTHER sessions "
            'use to message it (it is not listed below; from inside this process, address the '
            'main conversation as "main").'
        )
        self.assert_listing_refuses(desktop_listing(peer, caller=process_heading),
                                    name="main", reason="unrecognized_listing")

    def test_a_zero_padded_start_age_refuses_the_listing(self):
        self.assert_listing_refuses(desktop_listing(desktop_row("alpha", "aa12bc", age="000000008h")),
                                    reason="unrecognized_listing")

    def test_an_unobserved_start_age_spelling_refuses_the_listing(self):
        for age in ("0h", "1.5s", "1h 2m", "-1h", "+1h", "1w", "١h"):
            with self.subTest(age=age):
                self.assert_listing_refuses(desktop_listing(desktop_row("alpha", "aa12bc", age=age)),
                                            reason="unrecognized_listing")

    def test_a_listing_with_any_unsupported_row_is_refused(self):
        for other in (
            "  " + DOT.join(("other [bb34cd]", "interactive", "idle")),
            "  " + DOT.join(("other [bb34cd]", "bg", "idle", "started 8h ago")),
            "  " + DOT.join(("other [bb34cd]", "Remote Control", "idle")),
            "  " + DOT.join(("other [bb34cd]", "cloud", "idle")),
            "  " + DOT.join(("other [bb34cd]", "chat")),
            desktop_row("other", "bb34cd", status="shell"),
            desktop_row("other", "bb34cd", status="idle (waiting)"),
            desktop_row("other", "bb34cd") + DOT + 'titled "draft" in Claude Desktop',
            desktop_row("other", "BB34CD"),
            desktop_row("other", "b2"),
            desktop_row("other", "bb34cd").replace(" [bb34cd]", ""),
            desktop_row("other" + DOT + "draft", "bb34cd"),
            desktop_row("other Peer sessions (9): draft", "bb34cd"),
            desktop_row("other Cloud sessions and other computers are not listed", "bb34cd"),
            desktop_row("other No reachable agents", "bb34cd"),
            desktop_row("other one session hidden", "bb34cd"),
            desktop_row("other (cloud session list could not be fetched just now)", "bb34cd"),
            desktop_row("other\u2028foreign line", "bb34cd"),
            desktop_row("other", "bb34cd").replace("  other", "   other"),
        ):
            with self.subTest(row=other):
                self.assert_listing_refuses(desktop_listing(desktop_row("alpha", "aa12bc"), other),
                                            reason="unrecognized_listing")

    def test_unrelated_bracketed_and_parenthesized_titles_are_skipped_and_counted(self):
        for title in ("other [draft]", "(draft) other", "[draft] other"):
            with self.subTest(title=title):
                listing = desktop_listing(desktop_row("alpha", "aa12bc"),
                                          desktop_row(title, "bb34cd"))
                with self.name_consumer(name="alpha", pages=(listing,)) as (
                        _, _, send, bookkeeping, calls, _):
                    result = send()
                    self.assertEqual(result["reason"], "submitted")
                    self.assertEqual(result["unreadable_rows"], 1)
                    self.assertEqual([call["name"] for call in calls()],
                                     ["ListAgents", "SendMessage"])
                    self.assertEqual(calls()[-1]["arguments"]["to"], "alpha")
                    observations = bookkeeping("show", "send-1")["attempts"][0]["observations"]
                    self.assertEqual(json.loads(observations[1]["detail"])["unreadable_rows"], 1)

    def test_an_unreadable_title_that_could_carry_the_requested_name_refuses(self):
        for title, selection in (("alpha [draft]", None),
                                 ("alpha [aa12bc]", {"ref": "aa12bc"})):
            with self.subTest(title=title, selection=selection):
                self.assert_listing_refuses(desktop_listing(
                    desktop_row("other [draft]", "cc56de"),
                    desktop_row("alpha", "aa12bc"),
                    desktop_row(title, "bb34cd"),
                ), selection=selection, reason="unrecognized_listing", unreadable_rows=1)

    def test_an_unreadable_peer_cannot_reuse_the_caller_reference(self):
        self.assert_listing_refuses(desktop_listing(
            desktop_row("alpha", "aa12bc"), desktop_row("other [draft]", "ab12ef"),
        ), reason="listing_incomplete")

    def test_running_subagent_compaction_and_shadowed_teammate_are_refused(self):
        for section, fields in (
            ("Subagents", ("other [b2]", "reviewer", "running", "started 1m ago",
                           "compacting its conversation for 1m")),
            ("Teammates", ("other", "reviewer", "roster",
                           "not messageable by name while a subagent in this session is "
                           "registered under that name (the name reaches the subagent)")),
        ):
            with self.subTest(section=section):
                listing = desktop_listing(desktop_row("alpha", "aa12bc")).replace(
                    "\n\n" + FOOTER,
                    f"\n\n{section} (1):\n  " + DOT.join(fields) + "\n\n" + FOOTER)
                self.assert_listing_refuses(listing, reason="unrecognized_listing")

    def test_a_listing_with_other_sections_or_notes_is_refused(self):
        for line in (
            "Cloud and Remote Control sessions (1):",
            "Subagents (1):",
            "Teammates (1):",
            "Chats (1):",
            '<other-sessions nonce="0123456789abcdef" untrusted="true">',
            "No reachable agents.",
            "(the session list on this machine could not be read just now)",
            "… and 2 more sessions not shown",
        ):
            with self.subTest(line=line):
                listing = desktop_listing(desktop_row("alpha", "aa12bc"), line)
                self.assert_listing_refuses(listing, reason="unrecognized_listing")

    def test_empty_listing_forms_and_a_mismatched_peer_total_are_refused(self):
        for listing in (
            "", "No reachable agents.", desktop_listing(),
            desktop_listing(desktop_row("alpha", "aa12bc")).replace("sessions (1)", "sessions (2)"),
        ):
            with self.subTest(listing=listing):
                self.assert_listing_refuses(listing, reason="listing_incomplete")

    def test_a_repeated_row_refuses_even_with_a_matching_count(self):
        other = desktop_row("other", "bb34cd")
        self.assert_listing_refuses(desktop_listing(desktop_row("alpha", "aa12bc"), other, other),
                                    reason="listing_incomplete")

    def test_a_later_duplicate_row_retains_the_earlier_skip(self):
        unreadable = desktop_row("other [draft]", "bb34cd")
        target = desktop_row("alpha", "aa12bc")
        self.assert_listing_refuses(desktop_listing(unreadable, target, target),
                                    reason="listing_incomplete", unreadable_rows=1)

    def test_an_unrelated_301_character_peer_title_refuses_the_listing(self):
        self.assert_listing_refuses(desktop_listing(
            desktop_row("alpha", "aa12bc"), desktop_row("x" * 301, "bb34cd"),
        ), reason="unrecognized_listing")

    def test_the_documented_desktop_listing_parses_and_addresses_each_example_row(self):
        reference = (SCRIPTS.parent / "references" / "claude-mcp-sender.md").read_text(
            encoding="utf-8")
        section = reference.split("## Find the named recipient", 1)[1]
        listing = section.split("```text\n", 1)[1].split("\n```", 1)[0]
        expected = [
            {"name": name, "ref": ref, "section": "Peer sessions", "kind": "interactive",
             "local": True}
            for name, ref in (("Fixture Team · Receiver", "aa12bc"), ("Second Peer", "bb34cd"))
        ]
        with patch.object(sys, "path", [str(SCRIPTS), *sys.path]):
            import claude_mcp_sender as sender

        self.assertEqual(list(sender.parse_listing(listing, expected[0]["name"], None)), expected)
        for row in expected:
            with self.subTest(name=row["name"]), self.name_consumer(
                    name=row["name"], pages=(listing,)) as (_, _, send, bookkeeping, calls, _):
                self.assertEqual(send()["reason"], "submitted")
                self.assertEqual(calls()[-1]["arguments"]["to"], row["name"])
                record = bookkeeping("show", "send-1")
                self.assertEqual(record["state"], "submitted")
                bound = json.loads(record["attempts"][0]["observations"][1]["detail"])
                self.assertEqual(bound["row"], row)
                self.assertEqual(bound["to"], row["name"])

    def test_the_listing_parser_accepts_the_duration_formatter_units(self):
        with patch.object(sys, "path", [str(SCRIPTS), *sys.path]):
            import claude_mcp_sender as sender

        examples = (
            ("Just Started", "a1b2c3", "idle", "0s"),
            ("Seconds", "d4e5f6", "busy", "12s"),
            ("Minutes", "c3d4e5", "idle", "5m"),
            ("Days", "b2c3d4", "busy", "2d"),
        )
        listing = desktop_listing(*(desktop_row(name, ref, status=status, age=age)
                                    for name, ref, status, age in examples))
        self.assertEqual(list(sender.parse_listing(listing, examples[0][0], None)), [
            {"name": name, "ref": ref, "section": "Peer sessions", "kind": "interactive",
             "local": True}
            for name, ref, _, _ in examples
        ])

    def test_listing_grammar_mutations_are_self_consistency_checks(self):
        with patch.object(sys, "path", [str(SCRIPTS), *sys.path]):
            import claude_mcp_sender as sender

        class ListingChild:
            def __init__(self, listing):
                self.listing = listing
                self.calls = []

            def start(self, _command):
                pass

            def send(self, request):
                self.request = request
                if request["method"] == "tools/call":
                    self.calls.append(request["params"]["name"])

            def reply(self, identity):
                if self.request["id"] != identity:
                    raise AssertionError("The sender read a reply for a different request.")
                if self.request["method"] == "initialize":
                    return {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}}
                if self.request["method"] == "tools/list":
                    return {"tools": [retained_destination_catalog()["tools"][0], LISTAGENTS_TOOL]}
                if self.calls[-1] == "ListAgents":
                    return {"content": [{"type": "text", "text": self.listing}]}
                return {"content": [{"type": "text", "text": "Synthetic submission."}]}

            def close(self):
                return {"started": True, "reaped": True, "exit_code": 0}

        # One target and a second peer exercise both row statuses. Independently
        # mutate the literal fixture, including mandatory blanks and other controls.
        lines = desktop_listing(desktop_row("alpha", "aa12bc"), desktop_row(
            "other", "bb34cd", status="busy", age="3h")).split("\n")
        mutations = {}

        def replace_line(index, replacement, description):
            listing = "\n".join((*lines[:index], *replacement, *lines[index + 1:]))
            mutations.setdefault(listing, (index, description))

        for index, line in enumerate(lines):
            replace_line(index, (), "delete line")
            replace_line(index, (line, line), "duplicate line")
            for destination in range(len(lines)):
                reordered = lines.copy()
                reordered.insert(destination, reordered.pop(index))
                if reordered != lines:
                    mutations.setdefault("\n".join(reordered), (index, "move line", destination))
            for digits in re.finditer(r"[0-9]+", line):
                changed = line[:digits.start()] + "9" * 4400 + line[digits.end():]
                replace_line(index, (changed,), ("oversize digits", digits.start()))
                if not line.startswith("  ") or digits.start() > line.index(DOT):
                    changed = line[:digits.start()] + line[digits.end():]
                    replace_line(index, (changed,), ("delete digits", digits.start()))
            for mark in re.finditer(r"[\[\]():;.—]|  ·  ", line):
                changed = line[:mark.start()] + line[mark.end():]
                replace_line(index, (changed,), ("delete punctuation", mark.start()))
            # Names are free text, and ref hex letters and age digits are not
            # keywords. Word positions are derived from the fixture's fields.
            if index == 0:
                phrase = " — the name "
                start, end = len("This session is "), line.index(phrase)
            elif line.startswith("  "):
                start, end = 0, line.index(DOT)
            else:
                start, end = 0, 0
            for word in re.finditer(r"[A-Za-z]+", line):
                if word.start() >= start and word.end() <= end:
                    continue
                for length in range(len(word[0])):
                    changed = line[:word.start() + length] + line[word.end():]
                    replace_line(index, (changed,), ("keyword prefix", word[0], length))
            if line.startswith("  "):
                fields = line.split(DOT)
                for field in range(len(fields)):
                    changed = DOT.join(fields[:field] + fields[field + 1:])
                    replace_line(index, (changed,), ("delete row field", field))
                for prefix in (line[1:], line[2:], line.replace("  ", "   ", 1),
                               re.sub(r" \[.+?\]", "", line, count=1),
                               re.sub(r"^  [^[]+", "  ", line)):
                    replace_line(index, (prefix,), "delete or alter row framing")
            if index == 0:
                for changed in (line[:start] + line[end:], line.replace("Fixture Origin ", ""),
                                line.replace(" [ab12ef]", "")):
                    replace_line(index, (changed,), "delete caller identity part")
        for index in range(len(lines) + 1):
            mutations["\n".join((*lines[:index], "Foreign line.", *lines[index:]))] = (
                index, "add foreign line")
        # Peer row order carries no meaning.
        del mutations["\n".join((*lines[:3], lines[4], lines[3], *lines[5:]))]
        cases = [(listing, description, 0, False) for listing, description in mutations.items()]
        skipped = desktop_row("other [draft]", "bb34cd")
        cases.extend((
            (desktop_listing(lines[3], skipped), "unrelated unreadable label", 1, True),
            (desktop_listing(skipped, "Foreign line."), "unknown line after skip", 1, False),
            (desktop_listing(skipped).replace("Peer sessions (1):", "Peer sessions (2):"),
             "count mismatch after skip", 1, False),
        ))

        with self.name_consumer(name="alpha") as (_, request, _, _, _, trace):
            store = trace.parent / "mailbox.sqlite3"
            request_path = trace.parent / "mutation.json"
            initialized_store = store.read_bytes()
            request_path.write_text(json.dumps(request), encoding="utf-8")
            for listing, description, expected_skips, submits in cases:
                with self.subTest(case=description):
                    store.write_bytes(initialized_store)
                    child = ListingChild(listing)
                    output = io.StringIO()
                    with redirect_stdout(output), patch.object(
                            sender, "StdioMcpChild", return_value=child), patch.object(sys, "argv", [
                                "claude_mcp_sender.py", "--store", str(store),
                                "--request", str(request_path)]):
                        self.assertEqual(sender.main(), 0)
                    result = json.loads(output.getvalue())
                    self.assertEqual(result["unreadable_rows"], expected_skips)
                    mailbox = sender.Mailbox(store)
                    try:
                        record = mailbox.get(request["message_id"])
                    finally:
                        mailbox.close()
                    observations = record["attempts"][0]["observations"]
                    kinds = [item["kind"] for item in observations]
                    if submits:
                        self.assertEqual(child.calls, ["ListAgents", "SendMessage"])
                        self.assertEqual(result["peer_input"], "submitted")
                        self.assertEqual(record["state"], "submitted")
                        self.assertEqual(kinds, ["unknown", "unknown", "submitted"])
                        evidence = json.loads(observations[1]["detail"])
                        self.assertEqual(evidence["to"], "alpha")
                    else:
                        self.assertEqual(child.calls, ["ListAgents"])
                        self.assertEqual(result["peer_input"], "not_attempted")
                        self.assertIn(result["reason"], {"unrecognized_listing",
                                                        "listing_incomplete"})
                        self.assertEqual(record["state"], "refused")
                        self.assertEqual(kinds, ["unknown", "refused", "not_delivered"])
                        evidence = json.loads(observations[-1]["detail"])
                    self.assertEqual(evidence["unreadable_rows"], expected_skips)

    def test_a_name_the_profile_cannot_address_is_refused_before_any_claim(self):
        for name in ("left" + DOT + "right", "(draft) review", "No reachable agents.", "<alpha",
                     "alpha\tpeer", "alpha\u2028peer", "alpha\0peer", "", " ", None):
            recipient = name if isinstance(name, str) and name.strip() else "fixture"
            with self.subTest(name=name), self.name_consumer(name=name, recipient_thread=recipient) as (
                    _, request, send, bookkeeping, calls, trace):
                result = send()
                self.assertEqual(result["reason"], "invalid_name")
                self.assertFalse(result["claimed"])
                self.assertFalse(trace.exists())
                self.assertEqual(bookkeeping("show", "send-1")["state"], "planned")

    def test_the_sender_reference_points_its_child_end_at_the_wake_decision(self):
        # Where the reference says no process remains for a later notice, it must not
        # read as saying that no wake is intended.
        reference = (SCRIPTS.parent / "references" / "claude-mcp-sender.md").read_text(
            encoding="utf-8")
        paragraph = next(part for part in reference.split("\n\n")
                         if "has no process to reach" in part)
        self.assertIn("2026-11-19 decision", paragraph)
        self.assertIn("(../SKILL.md)", paragraph)

    def test_a_listing_that_fails_records_a_refusal_without_a_send(self):
        # The child fails on the listing call, so no SendMessage could be written.
        with self.name_consumer(pages=()) as (_, request, send, bookkeeping, calls, _t):
            detail = self.assert_refused_without_send(send(), "listing_failed", calls, bookkeeping)
            self.assertIn("stdout_eof", detail)
