"""Consumer catalog refusal through a real CLI and disposable MCP child."""
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

SCRIPTS = (
    Path(__file__).resolve().parents[2]
    / "plugins" / "rolecasting" / "skills" / "delegating-cross-agent-work"
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
    def failure_consumer(self, mode="lost_reply", catalog=None):
        """Run only the public commands, with an invented store and stdio peer."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = root / "mailbox.sqlite3"
            trace = root / "child.jsonl"
            child = root / "failure_child.py"
            mailbox = SCRIPTS / "native_codex_mailbox.py"
            original = {
                "message_id": "failure-1", "correlation_id": "conversation-77",
                "sender": {"thread_id": "original", "host_id": "origin-host"},
                "recipient": {"thread_id": "recipient", "host_id": "peer-host"},
                "owner": {"thread_id": "owner", "host_id": "local"},
                "payload": "Intake only.\r\nKeep e\u0301 and café.\n",
                "authority_ref": "synthetic://grant/intake",
                "holds": ["No operational transfer.", "Publication remains held."],
            }
            source = root / "message.json"
            source.write_bytes(json.dumps(original).encode("utf-8"))

            def bookkeeping(*arguments):
                completed = subprocess.run(
                    [sys.executable, str(mailbox), "--store", str(store), *arguments],
                    capture_output=True, text=True, timeout=10,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                return json.loads(completed.stdout)

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
                import sys

                with open(sys.argv[1], "a", encoding="utf-8") as trace:
                    trace.write(json.dumps({"started_pid": os.getpid()}) + "\\n")
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
                            if sys.argv[3] == "lost_reply":
                                os.close(sys.stdout.fileno())
                                continue
                            if sys.argv[3] == "stdout_overflow":
                                os.write(sys.stdout.fileno(), b"X" * 16385)
                                continue
                            if sys.argv[3] in ("tool_error", "tool_success"):
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
                "message_id": "failure-1", "attempt_id": "attempt-failure",
                "actor": {"thread_id": "replacement", "host_id": "forward-host"},
                "recipient": original["recipient"],
                "target": "uds:/synthetic/selected-peer.sock",
                "command": [sys.executable, str(child), str(trace), str(catalog_file), mode],
                "evidence_ref": "synthetic://evidence/failure",
                "limits": {"operation_seconds": 8, "stdout_bytes": 16384, "stderr_bytes": 4096},
            }
            request_file = root / "request.json"

            def send(raw=None):
                request_file.write_bytes(json.dumps(request).encode("utf-8") if raw is None else raw)
                completed = subprocess.run(
                    [sys.executable, str(SCRIPTS / "claude_mcp_sender.py"),
                     "--store", str(store), "--request", str(request_file)],
                    capture_output=True, text=True, timeout=12,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(completed.stderr, "")
                self.assertLessEqual(len(completed.stdout.encode("utf-8")), 2048)
                return json.loads(completed.stdout)

            yield original, request, send, bookkeeping, trace

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
                with self.failure_consumer(catalog=catalog) as (original, request, send, bookkeeping, trace):
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
                        "phase": "possible_submission", "target": "uds:/synthetic/selected-peer.sock",
                    })
                    self.assert_no_replay(request, send, bookkeeping, trace, retained)

    def test_recipient_mismatch_preserves_plan_without_claim_or_child(self):
        with self.failure_consumer() as (original, request, send, bookkeeping, trace):
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
                with self.failure_consumer(catalog=catalog) as (original, request, send, bookkeeping, trace):
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
                        "unknown", "refused",
                    ])

    def test_request_over_32768_bytes_is_rejected_without_claim_or_child(self):
        with self.failure_consumer() as (original, request, send, bookkeeping, trace):
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
                with self.failure_consumer(mode=mode) as (original, request, send, bookkeeping, trace):
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
        with self.failure_consumer(mode="stdout_overflow") as (original, request, send, bookkeeping, trace):
            result = send()
            self.assertEqual(result["stage"], "call")
            self.assertEqual(result["reason"], "stdout_limit")
            self.assertEqual(result["peer_input"], "possible_submission")
            self.assertTrue(result["claimed"])
            closure = result["owned_child"]
            self.assertTrue(closure["started"])
            self.assertTrue(closure["reaped"])
            self.assertIn(closure["exit_code"], (23, -9))
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
                "phase": "possible_submission", "target": "uds:/synthetic/selected-peer.sock",
            })
            self.assert_no_replay(request, send, bookkeeping, trace, retained)

    def test_missing_sendmessage_refuses_before_peer_input_and_reaps_owned_child(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = root / "mailbox.sqlite3"
            trace = root / "child.jsonl"
            child = root / "catalog_child.py"
            mailbox = SCRIPTS / "native_codex_mailbox.py"

            def bookkeeping(*arguments):
                completed = subprocess.run(
                    [sys.executable, str(mailbox), "--store", str(store), *arguments],
                    capture_output=True, text=True, timeout=10,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                return json.loads(completed.stdout)

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
            source = root / "message.json"
            source.write_text(json.dumps(original), encoding="utf-8")
            bookkeeping("init")
            bookkeeping("plan", "--input", str(source))
            child.write_text(textwrap.dedent("""\
                import json
                import subprocess
                import sys

                with open(sys.argv[1], "w", encoding="utf-8") as trace:
                    retained = subprocess.run(
                        [sys.executable, sys.argv[2], "--store", sys.argv[3],
                         "show", "catalog-1"],
                        capture_output=True, text=True, check=True, timeout=5,
                    )
                    trace.write(json.dumps({"before_start": json.loads(retained.stdout)}) + "\\n")
                    trace.flush()
                    for line in sys.stdin:
                        request = json.loads(line)
                        trace.write(json.dumps(request) + "\\n")
                        trace.flush()
                        if request.get("method") == "initialize":
                            response = {
                                "protocolVersion": "2024-11-05",
                                "capabilities": {"tools": {}},
                                "serverInfo": {"name": "disposable-catalog", "version": "1"},
                            }
                        elif request.get("method") == "notifications/initialized":
                            continue
                        elif request.get("method") == "tools/list":
                            response = {"tools": []}
                        else:
                            raise SystemExit(90)
                        print(json.dumps({"jsonrpc": "2.0", "id": request["id"],
                                          "result": response}), flush=True)
                    trace.write(json.dumps({"stdin_eof": True}) + "\\n")
                raise SystemExit(23)
                """), encoding="utf-8")
            request = {
                "message_id": "catalog-1",
                "attempt_id": "attempt-catalog",
                "actor": actor,
                "recipient": original["recipient"],
                "target": "uds:/synthetic/nomination-only.sock",
                "command": [sys.executable, str(child), str(trace), str(mailbox), str(store)],
                "evidence_ref": "synthetic://evidence/catalog",
                "limits": {"operation_seconds": 8, "stdout_bytes": 16384, "stderr_bytes": 4096},
            }
            request_file = root / "request.json"
            request_file.write_bytes(json.dumps(request).encode("utf-8"))
            completed = subprocess.run(
                [sys.executable, str(SCRIPTS / "claude_mcp_sender.py"),
                 "--store", str(store), "--request", str(request_file)],
                capture_output=True, text=True, timeout=12,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stderr, "")
            self.assertLessEqual(len(completed.stdout.encode("utf-8")), 2048)
            result = json.loads(completed.stdout)
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
            self.assertEqual([item["kind"] for item in attempt["observations"]], ["unknown", "refused"])
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
        with self.failure_consumer(mode="tool_success", catalog=catalog) as (
            original, request, send, bookkeeping, trace,
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
            self.assertEqual([o["kind"] for o in observations], ["unknown", "refused"])
            self.assertEqual(json.loads(observations[0]["detail"])["target"], target)
            if diagnosis is not None:
                self.assertIn(diagnosis, observations[-1]["detail"])
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
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = root / "mailbox.sqlite3"
            trace = root / "child.jsonl"
            child = root / "send_child.py"
            catalog_file = root / "catalog.json"
            catalog_file.write_text(json.dumps(catalog), encoding="utf-8")
            mailbox = SCRIPTS / "native_codex_mailbox.py"

            def bookkeeping(*arguments, success=True):
                completed = subprocess.run(
                    [sys.executable, str(mailbox), "--store", str(store), *arguments],
                    capture_output=True, text=True, timeout=10,
                )
                self.assertEqual(completed.returncode, 0 if success else 2, completed.stderr)
                return json.loads(completed.stdout if success else completed.stderr)

            original = {
                "message_id": "send-1",
                "correlation_id": "conversation-77",
                "sender": {"thread_id": "original", "host_id": "origin-host"},
                "recipient": {"thread_id": "recipient", "host_id": "peer-host"},
                "owner": {"thread_id": "owner", "host_id": "local"},
                "payload": "Intake only.\r\nKeep e\u0301 and café.\n",
                "authority_ref": "synthetic://grant/intake",
                "holds": ["No operational transfer.", "Publication remains held."],
            }
            actor = {"thread_id": "replacement", "host_id": "forward-host"}
            source = root / "message.json"
            source.write_bytes(json.dumps(original).encode("utf-8"))
            bookkeeping("init")
            bookkeeping("plan", "--input", str(source))
            child.write_text(textwrap.dedent("""\
                import json
                import subprocess
                import sys

                def retained():
                    shown = subprocess.run(
                        [sys.executable, sys.argv[2], "--store", sys.argv[3],
                         "show", "send-1"],
                        capture_output=True, text=True, check=True, timeout=5,
                    )
                    return json.loads(shown.stdout)

                with open(sys.argv[1], "a", encoding="utf-8") as trace:
                    trace.write(json.dumps({"before_start": retained()}) + "\\n")
                    trace.flush()
                    for line in sys.stdin:
                        request = json.loads(line)
                        trace.write(json.dumps(request) + "\\n")
                        trace.flush()
                        if request.get("method") == "initialize":
                            response = {
                                "protocolVersion": "2024-11-05",
                                "capabilities": {"tools": {}},
                                "serverInfo": {"name": "disposable-send", "version": "1"},
                            }
                        elif request.get("method") == "notifications/initialized":
                            continue
                        elif request.get("method") == "tools/list":
                            with open(sys.argv[4], encoding="utf-8") as catalog_file:
                                response = json.load(catalog_file)
                        elif request.get("method") == "tools/call":
                            trace.write(json.dumps({"before_call": retained()}) + "\\n")
                            trace.flush()
                            response = {
                                "content": [{"type": "text", "text": "Unvalidated tool text."}],
                                "isError": False,
                            }
                        else:
                            raise SystemExit(90)
                        print(json.dumps({"jsonrpc": "2.0", "id": request["id"],
                                          "result": response}), flush=True)
                    trace.write(json.dumps({"stdin_eof": True}) + "\\n")
                raise SystemExit(23)
                """), encoding="utf-8")
            request = {
                "message_id": "send-1",
                "attempt_id": "attempt-send",
                "actor": actor,
                "recipient": original["recipient"],
                "target": target,
                "command": [
                    sys.executable, str(child), str(trace), str(mailbox), str(store),
                    str(catalog_file),
                ],
                "evidence_ref": "synthetic://evidence/send",
                "limits": {"operation_seconds": 8, "stdout_bytes": 16384, "stderr_bytes": 4096},
            }
            request_file = root / "request.json"
            request_file.write_bytes(json.dumps(request).encode("utf-8"))

            def send():
                completed = subprocess.run(
                    [sys.executable, str(SCRIPTS / "claude_mcp_sender.py"),
                     "--store", str(store), "--request", str(request_file)],
                    capture_output=True, text=True, timeout=12,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(completed.stderr, "")
                self.assertLessEqual(len(completed.stdout.encode("utf-8")), 2048)
                self.assertNotIn("Unvalidated tool text.", completed.stdout)
                return json.loads(completed.stdout)

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
                "phase": "possible_submission", "target": target,
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
