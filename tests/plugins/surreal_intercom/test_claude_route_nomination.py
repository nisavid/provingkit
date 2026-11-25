"""Receiver-produced Claude route nomination and sender-request preparation."""

import contextlib
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = (
    ROOT / "plugins" / "surreal-intercom" / "skills"
    / "communicating-with-agents" / "scripts"
)
HELPER = SCRIPTS / "claude_route_nomination.py"
PLUGIN = ROOT / "plugins" / "surreal-intercom"


class ClaudeRouteNominationTests(unittest.TestCase):
    def load_modules(self):
        self.assertTrue(HELPER.is_file(), "the public Claude route helper is missing")
        sys.path.insert(0, str(SCRIPTS))
        try:
            route = importlib.import_module("claude_route_nomination")
            sender = importlib.import_module("claude_mcp_sender")
            mailbox = importlib.import_module("native_codex_mailbox")
        finally:
            sys.path.remove(str(SCRIPTS))
        return route, sender, mailbox

    @staticmethod
    def capture(root):
        return {
            "run_root": str(root),
            "allowance_bytes": 8 * 1024 * 1024,
            "terminal_provision_bytes": 512 * 1024,
            "later_forecast_bytes": 0,
        }

    @staticmethod
    def write(path, value):
        path.write_text(json.dumps(value), encoding="utf-8")

    def initialize_mailbox(self, mailbox_module, path):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = mailbox_module.main(["--store", str(path), "init"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(output.getvalue()), {"initialized": True})

    def produce(self, route, root, recipient=None, environment=None, lookup=None):
        if recipient is None:
            recipient = {"thread_id": "claude-receiver", "host_id": "local"}
        request = {
            "schema": "claude-route-nomination-request-v1",
            "recipient": recipient,
            "producer": recipient,
            "publication": {
                "path": str(root / "nomination.json"),
                "ownerUid": os.geteuid(),
                "capture": self.capture(root),
            },
        }
        request_path = root / "producer-request.json"
        self.write(request_path, request)
        if environment is None:
            environment = {
                "CLAUDE_CODE_HOST_SESSION_ID": recipient["thread_id"],
                "CLAUDE_CODE_MESSAGING_SOCKET": "/synthetic/receiver/messaging.sock",
                "PATH": "/synthetic/bin",
            }
        if lookup is None:
            lookup = lambda _name, _path: "/synthetic/bin/claude"
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = route.main(
                ["nominate", "--request", str(request_path)],
                effective_uid=os.geteuid(), environment=environment,
                launcher_lookup=lookup,
            )
        return exit_code, json.loads(output.getvalue()), recipient

    def prepare_input(self, root, nomination, recipient):
        return {
            "schema": "claude-sender-request-preparation-v1",
            "nomination": nomination,
            "message": {
                "message_id": "message-1",
                "sender": {"thread_id": "sender", "host_id": "local"},
                "recipient": recipient,
                "owner": {"thread_id": "owner", "host_id": "local"},
                "payload": "Preserve uncertainty.",
                "authority_ref": "synthetic://original-grant",
                "holds": [],
            },
            "attempt_id": "message-1/attempt/1",
            "actor": {"thread_id": "actor", "host_id": "local"},
            "limits": {
                "operation_seconds": 30,
                "stdout_bytes": 65536,
                "stderr_bytes": 65536,
            },
            "mailbox": str(root / "mailbox.sqlite3"),
            "publication": {
                "path": str(root / "sender-request.json"),
                "ownerUid": os.geteuid(),
                "capture": self.capture(root),
            },
        }

    def test_receiver_acquires_nomination_and_prepares_real_sender_request(self):
        route, sender, mailbox_module = self.load_modules()
        with tempfile.TemporaryDirectory(prefix="claude-route-") as temporary:
            root = Path(temporary).resolve()
            root.chmod(0o700)
            recipient = {"thread_id": "claude-receiver", "host_id": "local"}
            producer_request = {
                "schema": "claude-route-nomination-request-v1",
                "recipient": recipient,
                "producer": recipient,
                "publication": {
                    "path": str(root / "nomination.json"),
                    "ownerUid": os.geteuid(),
                    "capture": self.capture(root),
                },
            }
            producer_path = root / "producer-request.json"
            self.write(producer_path, producer_request)
            environment = {
                "CLAUDE_CODE_HOST_SESSION_ID": recipient["thread_id"],
                "CLAUDE_CODE_MESSAGING_SOCKET": "/synthetic/receiver/messaging.sock",
                "PATH": "/synthetic/credential-wrapper/bin:/usr/bin",
            }
            lookup_calls = []

            def lookup(invoked_name, path):
                lookup_calls.append((invoked_name, path))
                return "/synthetic/credential-wrapper/bin/claude"

            producer_stdout = io.StringIO()
            with contextlib.redirect_stdout(producer_stdout):
                producer_exit = route.main(
                    ["nominate", "--request", str(producer_path)],
                    effective_uid=os.geteuid(), environment=environment,
                    launcher_lookup=lookup,
                )
            self.assertEqual(producer_exit, 0)
            publication = json.loads(producer_stdout.getvalue())
            self.assertTrue(publication["published"])
            self.assertEqual(publication["closure"], "no-provider-started")
            self.assertEqual(lookup_calls, [("claude", environment["PATH"])])
            self.assertNotIn(environment["CLAUDE_CODE_MESSAGING_SOCKET"], producer_stdout.getvalue())
            self.assertNotIn("credential-wrapper", producer_stdout.getvalue())

            message = {
                "message_id": "ordinary-message",
                "correlation_id": "ordinary-exchange",
                "sender": {"thread_id": "original-sender", "host_id": "local"},
                "recipient": recipient,
                "owner": {"thread_id": "obligation-owner", "host_id": "local"},
                "payload": "Keep the original obligation and report uncertainty.",
                "authority_ref": "synthetic://original-grant",
                "holds": ["retain-original-attempt"],
            }
            prepare_request = {
                "schema": "claude-sender-request-preparation-v1",
                "nomination": {
                    "path": publication["path"],
                    "bytes": publication["bytes"],
                    "sha256": publication["sha256"],
                },
                "message": message,
                "attempt_id": "ordinary-message/attempt/1",
                "actor": {"thread_id": "submitting-actor", "host_id": "local"},
                "limits": {
                    "operation_seconds": 30,
                    "stdout_bytes": 65536,
                    "stderr_bytes": 65536,
                },
                "mailbox": str(root / "mailbox.sqlite3"),
                "publication": {
                    "path": str(root / "sender-request.json"),
                    "ownerUid": os.geteuid(),
                    "capture": self.capture(root),
                },
            }
            prepare_path = root / "prepare-input.json"
            self.write(prepare_path, prepare_request)
            self.initialize_mailbox(mailbox_module, prepare_request["mailbox"])
            prepare_stdout = io.StringIO()
            with contextlib.redirect_stdout(prepare_stdout):
                prepare_exit = route.main(
                    ["prepare", "--request", str(prepare_path)],
                    effective_uid=os.geteuid(),
                )
            self.assertEqual(prepare_exit, 0)
            prepared = json.loads(prepare_stdout.getvalue())
            self.assertTrue(prepared["prepared"])
            self.assertEqual(prepared["closure"], "no-provider-started")
            self.assertNotIn(environment["CLAUDE_CODE_MESSAGING_SOCKET"], prepare_stdout.getvalue())

            sender_request = json.loads(Path(prepared["path"]).read_text(encoding="utf-8"))
            sender.validate(sender_request)
            self.assertEqual(sender_request["message_id"], message["message_id"])
            self.assertEqual(sender_request["attempt_id"], prepare_request["attempt_id"])
            self.assertEqual(sender_request["actor"], prepare_request["actor"])
            self.assertEqual(sender_request["recipient"], recipient)
            self.assertEqual(sender_request["target"], "uds:/synthetic/receiver/messaging.sock")
            self.assertEqual(sender_request["command"], [
                "/synthetic/credential-wrapper/bin/claude", "mcp", "serve",
            ])
            self.assertEqual(sender_request["limits"], prepare_request["limits"])
            self.assertEqual(
                sender_request["evidence_ref"],
                "sha256:" + publication["sha256"],
            )

            mailbox = mailbox_module.Mailbox(prepare_request["mailbox"])
            try:
                retained = mailbox.get(message["message_id"])
            finally:
                mailbox.close()
            self.assertEqual(retained["correlation_id"], message["correlation_id"])
            self.assertEqual(retained["sender"], message["sender"])
            self.assertEqual(retained["owner"], message["owner"])
            self.assertEqual(retained["holds"], message["holds"])
            self.assertEqual(retained["state"], "planned")
            self.assertEqual(Path(prepared["path"]).stat().st_mode & 0o777, 0o600)
            self.assertEqual(Path(prepare_request["mailbox"]).stat().st_mode & 0o777, 0o600)

    def test_prepare_refuses_missing_recovery_mailbox_without_replacing_it(self):
        route, _, mailbox_module = self.load_modules()
        with tempfile.TemporaryDirectory(prefix="claude-route-") as temporary:
            root = Path(temporary).resolve()
            root.chmod(0o700)
            _, publication, recipient = self.produce(route, root)
            request = self.prepare_input(root, {
                "path": publication["path"],
                "bytes": publication["bytes"],
                "sha256": publication["sha256"],
            }, recipient)
            mailbox_path = Path(request["mailbox"])
            self.initialize_mailbox(mailbox_module, mailbox_path)
            retained = root / "retained-mailbox.sqlite3"
            mailbox_path.rename(retained)
            retained_bytes = retained.read_bytes()
            request_path = root / "prepare-input.json"
            self.write(request_path, request)

            output = io.StringIO()
            errors = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                exit_code = route.main(
                    ["prepare", "--request", str(request_path)],
                    effective_uid=os.geteuid(),
                )

            self.assertEqual(exit_code, 0)
            result = json.loads(output.getvalue())
            self.assertFalse(result["prepared"])
            self.assertEqual(result["reason"], "mailbox-unavailable")
            self.assertEqual(result["closure"], "no-provider-started")
            self.assertEqual(errors.getvalue(), "")
            self.assertFalse(mailbox_path.exists())
            self.assertFalse(Path(request["publication"]["path"]).exists())
            self.assertEqual(retained.read_bytes(), retained_bytes)

    def test_prepare_by_name_uses_the_senders_own_launcher_and_no_nomination(self):
        route, sender, mailbox_module = self.load_modules()
        with tempfile.TemporaryDirectory(prefix="claude-route-") as temporary:
            root = Path(temporary).resolve()
            root.chmod(0o700)
            recipient = {"thread_id": "claude-receiver", "host_id": "local"}
            request = self.prepare_input(root, None, recipient)
            del request["nomination"]
            request["schema"] = "claude-name-request-preparation-v1"
            request["name"] = "claude-receiver"
            mailbox_path = Path(request["mailbox"])
            self.initialize_mailbox(mailbox_module, mailbox_path)
            request_path = root / "prepare-input.json"
            self.write(request_path, request)
            lookups = []

            def lookup(name, path):
                lookups.append((name, path))
                return "/synthetic/credential-wrapper/bin/claude"

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                route.main(["prepare", "--request", str(request_path)],
                           effective_uid=os.geteuid(),
                           environment={"PATH": "/synthetic/credential-wrapper/bin:/usr/bin"},
                           launcher_lookup=lookup)
            result = json.loads(output.getvalue())
            self.assertTrue(result["prepared"], result)
            self.assertEqual(lookups, [("claude", "/synthetic/credential-wrapper/bin:/usr/bin")])
            prepared = json.loads(Path(result["path"]).read_text(encoding="utf-8"))
            sender.validate(prepared)
            self.assertEqual(prepared["name"], "claude-receiver")
            self.assertNotIn("target", prepared)
            self.assertEqual(prepared["command"],
                             ["/synthetic/credential-wrapper/bin/claude", "mcp", "serve"])
            self.assertEqual(prepared["recipient"], recipient)

    def test_prepare_passes_a_later_attempts_fields_through_both_or_neither(self):
        route, sender, mailbox_module = self.load_modules()
        reconciliation = {"after_attempt": "message-1/attempt/1",
                          "decision_ref": "synthetic://decision/select"}
        for fields in (("after_attempt", "decision_ref"), ("after_attempt",), ("decision_ref",)):
            with self.subTest(fields=fields), tempfile.TemporaryDirectory(
                    prefix="claude-route-") as temporary:
                root = Path(temporary).resolve()
                root.chmod(0o700)
                recipient = {"thread_id": "twin", "host_id": "local"}
                request = self.prepare_input(root, None, recipient)
                del request["nomination"]
                request.update({"schema": "claude-name-request-preparation-v1", "name": "twin",
                                "selection": {"ref": "cc22dd"}, "attempt_id": "message-1/attempt/2"})
                request.update({key: reconciliation[key] for key in fields})
                self.initialize_mailbox(mailbox_module, Path(request["mailbox"]))
                request_path = root / "prepare-input.json"
                self.write(request_path, request)
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    route.main(["prepare", "--request", str(request_path)],
                               effective_uid=os.geteuid(),
                               environment={"PATH": "/synthetic/bin"},
                               launcher_lookup=lambda _name, _path: "/synthetic/bin/claude")
                result = json.loads(output.getvalue())
                if len(fields) == 2:
                    self.assertTrue(result["prepared"], result)
                    prepared = json.loads(Path(result["path"]).read_text(encoding="utf-8"))
                    sender.validate(prepared)
                    self.assertEqual(
                        {key: prepared[key] for key in reconciliation}, reconciliation)
                else:
                    self.assertEqual(result, {
                        "prepared": False, "reason": "invalid_reconciliation",
                        "closure": "no-provider-started"})
                    self.assertFalse(Path(request["publication"]["path"]).exists())

    def test_prepare_refuses_an_oversized_frame_before_planning_or_publishing(self):
        route, _, mailbox_module = self.load_modules()
        with tempfile.TemporaryDirectory(prefix="claude-route-") as temporary:
            root = Path(temporary).resolve()
            root.chmod(0o700)
            _, publication, recipient = self.produce(route, root)
            nomination = {key: publication[key] for key in ("path", "bytes", "sha256")}
            request = self.prepare_input(root, nomination, recipient)
            mailbox_path = Path(request["mailbox"])
            self.initialize_mailbox(mailbox_module, mailbox_path)
            # Fits the 32,768-byte request file but not the 4,096-byte call frame.
            request["message"]["payload"] = "x" * 4096
            request_path = root / "prepare-input.json"
            self.write(request_path, request)

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = route.main(
                    ["prepare", "--request", str(request_path)],
                    effective_uid=os.geteuid(),
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(json.loads(output.getvalue()), {
                "prepared": False, "reason": "sender-frame-byte-limit",
                "closure": "no-provider-started",
            })
            self.assertFalse(Path(request["publication"]["path"]).exists())
            mailbox = mailbox_module.Mailbox(mailbox_path)
            try:
                self.assertEqual(mailbox.pending(), [])
            finally:
                mailbox.close()

            request["message"]["payload"] = "Fits."
            self.write(request_path, request)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                route.main(["prepare", "--request", str(request_path)],
                           effective_uid=os.geteuid())
            self.assertTrue(json.loads(output.getvalue())["prepared"])

    def test_prepare_refuses_a_name_that_looks_like_a_route(self):
        route, _, mailbox_module = self.load_modules()
        with tempfile.TemporaryDirectory(prefix="claude-route-") as temporary:
            root = Path(temporary).resolve()
            root.chmod(0o700)
            recipient = {"thread_id": "claude-receiver", "host_id": "local"}
            request = self.prepare_input(root, None, recipient)
            del request["nomination"]
            request["schema"] = "claude-name-request-preparation-v1"
            request["name"] = "uds:/synthetic/outside.sock"
            mailbox_path = Path(request["mailbox"])
            self.initialize_mailbox(mailbox_module, mailbox_path)
            request_path = root / "prepare-input.json"
            self.write(request_path, request)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                route.main(["prepare", "--request", str(request_path)],
                           effective_uid=os.geteuid(),
                           environment={"PATH": "/synthetic/bin"},
                           launcher_lookup=lambda _name, _path: "/synthetic/bin/claude")
            self.assertEqual(json.loads(output.getvalue()), {
                "prepared": False, "reason": "invalid_name", "closure": "no-provider-started",
            })
            self.assertFalse(Path(request["publication"]["path"]).exists())

    def test_prepare_refuses_a_name_the_listing_profile_cannot_address(self):
        route, _, mailbox_module = self.load_modules()
        for name in ("left  ·  right", "(draft) review"):
            with self.subTest(name=name), tempfile.TemporaryDirectory(
                    prefix="claude-route-") as temporary:
                root = Path(temporary).resolve()
                root.chmod(0o700)
                request = self.prepare_input(root, None, {"thread_id": name, "host_id": "local"})
                del request["nomination"]
                request.update({"schema": "claude-name-request-preparation-v1", "name": name})
                self.initialize_mailbox(mailbox_module, Path(request["mailbox"]))
                request_path = root / "prepare-input.json"
                self.write(request_path, request)
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    route.main(["prepare", "--request", str(request_path)],
                               effective_uid=os.geteuid(),
                               environment={"PATH": "/synthetic/bin"},
                               launcher_lookup=lambda _name, _path: "/synthetic/bin/claude")
                self.assertEqual(json.loads(output.getvalue()), {
                    "prepared": False, "reason": "invalid_name",
                    "closure": "no-provider-started"})
                self.assertFalse(Path(request["publication"]["path"]).exists())

    def test_prepare_refuses_a_recipient_that_does_not_carry_the_name(self):
        route, _, mailbox_module = self.load_modules()
        with tempfile.TemporaryDirectory(prefix="claude-route-") as temporary:
            root = Path(temporary).resolve()
            root.chmod(0o700)
            # A session id is not the name the listing prints.
            recipient = {"thread_id": "3fa9c1-session-id", "host_id": "local"}
            request = self.prepare_input(root, None, recipient)
            del request["nomination"]
            request["schema"] = "claude-name-request-preparation-v1"
            request["name"] = "claude-receiver"
            mailbox_path = Path(request["mailbox"])
            self.initialize_mailbox(mailbox_module, mailbox_path)
            request_path = root / "prepare-input.json"
            self.write(request_path, request)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                route.main(["prepare", "--request", str(request_path)],
                           effective_uid=os.geteuid(),
                           environment={"PATH": "/synthetic/bin"},
                           launcher_lookup=lambda _name, _path: "/synthetic/bin/claude")
            self.assertEqual(json.loads(output.getvalue()), {
                "prepared": False, "reason": "recipient-name-mismatch",
                "closure": "no-provider-started",
            })
            self.assertFalse(Path(request["publication"]["path"]).exists())
            mailbox = mailbox_module.Mailbox(mailbox_path)
            try:
                self.assertEqual(mailbox.pending(), [])
            finally:
                mailbox.close()

    def test_prepare_measures_a_selected_name_frame_as_the_sender_sends_it(self):
        route, sender, mailbox_module = self.load_modules()
        with tempfile.TemporaryDirectory(prefix="claude-route-") as temporary:
            root = Path(temporary).resolve()
            root.chmod(0o700)
            recipient = {"thread_id": "twin", "host_id": "local"}
            request = self.prepare_input(root, None, recipient)
            del request["nomination"]
            request["schema"] = "claude-name-request-preparation-v1"
            request["name"] = "twin"
            request["selection"] = {"ref": "cc22dd"}
            mailbox_path = Path(request["mailbox"])
            self.initialize_mailbox(mailbox_module, mailbox_path)
            request_path = root / "prepare-input.json"

            def frame_bytes(to):
                return len(json.dumps(
                    sender.sendmessage_call(request["message"], request["actor"], to),
                    ensure_ascii=True, separators=(",", ":")).encode()) + 1

            def prepare():
                self.write(request_path, request)
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    route.main(["prepare", "--request", str(request_path)],
                               effective_uid=os.geteuid(),
                               environment={"PATH": "/synthetic/bin"},
                               launcher_lookup=lambda _name, _path: "/synthetic/bin/claude")
                return json.loads(output.getvalue())

            # The bare name's frame is exactly at the ceiling; the sent `twin [cc22dd]` is over it.
            request["message"]["payload"] = ""
            request["message"]["payload"] = "x" * (4096 - frame_bytes("twin"))
            self.assertEqual(frame_bytes("twin"), 4096)
            self.assertGreater(frame_bytes("twin [cc22dd]"), 4096)
            self.assertEqual(prepare(), {
                "prepared": False, "reason": "sender-frame-byte-limit",
                "closure": "no-provider-started",
            })
            self.assertFalse(Path(request["publication"]["path"]).exists())

            # At the ceiling with the selected `to`, the request is prepared.
            request["message"]["payload"] = ""
            request["message"]["payload"] = "x" * (4096 - frame_bytes("twin [cc22dd]"))
            self.assertEqual(frame_bytes("twin [cc22dd]"), 4096)
            result = prepare()
            self.assertTrue(result["prepared"], result)
            prepared = json.loads(Path(result["path"]).read_text(encoding="utf-8"))
            self.assertEqual(sender.request_destination(prepared), "twin [cc22dd]")

    def test_prepare_returns_safe_refusal_for_existing_corrupt_mailbox(self):
        route, _, _ = self.load_modules()
        with tempfile.TemporaryDirectory(prefix="claude-route-") as temporary:
            root = Path(temporary).resolve()
            root.chmod(0o700)
            _, publication, recipient = self.produce(route, root)
            request = self.prepare_input(root, {
                "path": publication["path"],
                "bytes": publication["bytes"],
                "sha256": publication["sha256"],
            }, recipient)
            mailbox_path = Path(request["mailbox"])
            corrupt_bytes = b"not a SQLite mailbox\nprivate detail"
            mailbox_path.write_bytes(corrupt_bytes)
            mailbox_path.chmod(0o600)
            request_path = root / "prepare-input.json"
            self.write(request_path, request)

            output = io.StringIO()
            errors = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                exit_code = route.main(
                    ["prepare", "--request", str(request_path)],
                    effective_uid=os.geteuid(),
                )

            self.assertEqual(exit_code, 0)
            result = json.loads(output.getvalue())
            self.assertFalse(result["prepared"])
            self.assertEqual(result["reason"], "mailbox-unavailable")
            self.assertEqual(result["closure"], "no-provider-started")
            self.assertEqual(errors.getvalue(), "")
            self.assertNotIn("database", output.getvalue().lower())
            self.assertNotIn("traceback", output.getvalue().lower())
            self.assertEqual(mailbox_path.read_bytes(), corrupt_bytes)
            self.assertFalse(Path(request["publication"]["path"]).exists())

    def test_prepare_refuses_a_re_pinned_malformed_private_target(self):
        route, _, _ = self.load_modules()
        with tempfile.TemporaryDirectory(prefix="claude-route-") as temporary:
            root = Path(temporary).resolve()
            root.chmod(0o700)
            _, publication, recipient = self.produce(route, root)
            nomination_path = Path(publication["path"])
            record = json.loads(nomination_path.read_text(encoding="utf-8"))
            record["route"]["target"] = "uds:/synthetic/receiver/../replacement.sock"
            raw = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
            nomination_path.write_bytes(raw)
            pin = {
                "path": str(nomination_path),
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
            request = self.prepare_input(root, pin, recipient)
            request_path = root / "prepare-input.json"
            self.write(request_path, request)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = route.main(
                    ["prepare", "--request", str(request_path)],
                    effective_uid=os.geteuid(),
                )
            self.assertEqual(exit_code, 0)
            result = json.loads(output.getvalue())
            self.assertFalse(result["prepared"])
            self.assertEqual(result["reason"], "malformed-private-nomination")
            self.assertFalse(Path(request["mailbox"]).exists())
            self.assertFalse(Path(request["publication"]["path"]).exists())

    def test_nominate_returns_a_safe_missing_launcher_control_reason(self):
        route, _, _ = self.load_modules()
        with tempfile.TemporaryDirectory(prefix="claude-route-") as temporary:
            root = Path(temporary).resolve()
            root.chmod(0o700)

            def unavailable(_name, _path):
                raise OSError("private resolver detail")

            exit_code, result, _ = self.produce(route, root, lookup=unavailable)
            self.assertEqual(exit_code, 0)
            self.assertFalse(result["published"])
            self.assertEqual(result["reason"], "launcher-control-unavailable")
            self.assertNotIn("private resolver detail", json.dumps(result))
            self.assertFalse((root / "nomination.json").exists())

    def test_nominate_refuses_changed_recipient_missing_fields_and_launcher(self):
        route, _, _ = self.load_modules()
        cases = (
            (
                "recipient mismatch",
                {
                    "CLAUDE_CODE_HOST_SESSION_ID": "another-receiver",
                    "CLAUDE_CODE_MESSAGING_SOCKET": "/synthetic/receiver.sock",
                    "PATH": "/synthetic/bin",
                },
                lambda _name, _path: "/synthetic/bin/claude",
                "recipient-host-session-mismatch",
            ),
            (
                "missing host field",
                {
                    "CLAUDE_CODE_MESSAGING_SOCKET": "/synthetic/receiver.sock",
                    "PATH": "/synthetic/bin",
                },
                lambda _name, _path: "/synthetic/bin/claude",
                "host-session-field-unavailable",
            ),
            (
                "missing socket field",
                {
                    "CLAUDE_CODE_HOST_SESSION_ID": "claude-receiver",
                    "PATH": "/synthetic/bin",
                },
                lambda _name, _path: "/synthetic/bin/claude",
                "messaging-socket-field-unavailable",
            ),
            (
                "missing launcher path control",
                {
                    "CLAUDE_CODE_HOST_SESSION_ID": "claude-receiver",
                    "CLAUDE_CODE_MESSAGING_SOCKET": "/synthetic/receiver.sock",
                },
                lambda _name, _path: "/synthetic/bin/claude",
                "launcher-control-unavailable",
            ),
            (
                "launcher absent",
                {
                    "CLAUDE_CODE_HOST_SESSION_ID": "claude-receiver",
                    "CLAUDE_CODE_MESSAGING_SOCKET": "/synthetic/receiver.sock",
                    "PATH": "/synthetic/bin",
                },
                lambda _name, _path: None,
                "claude-launcher-unavailable",
            ),
        )
        for name, environment, lookup, reason in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory(
                prefix="claude-route-"
            ) as temporary:
                root = Path(temporary).resolve()
                root.chmod(0o700)
                exit_code, result, _ = self.produce(
                    route, root, environment=environment, lookup=lookup,
                )
                self.assertEqual(exit_code, 0)
                self.assertFalse(result["published"])
                self.assertEqual(result["reason"], reason)
                self.assertEqual(result["closure"], "no-provider-started")
                self.assertFalse((root / "nomination.json").exists())

    def test_prepare_refuses_changed_nomination_and_recipient(self):
        route, _, _ = self.load_modules()
        with tempfile.TemporaryDirectory(prefix="claude-route-") as temporary:
            root = Path(temporary).resolve()
            root.chmod(0o700)
            _, publication, recipient = self.produce(route, root)
            nomination_path = Path(publication["path"])
            nomination_path.write_bytes(nomination_path.read_bytes() + b" ")
            request = self.prepare_input(root, {
                "path": publication["path"],
                "bytes": publication["bytes"],
                "sha256": publication["sha256"],
            }, recipient)
            request_path = root / "prepare-input.json"
            self.write(request_path, request)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                route.main(
                    ["prepare", "--request", str(request_path)],
                    effective_uid=os.geteuid(),
                )
            result = json.loads(output.getvalue())
            self.assertFalse(result["prepared"])
            self.assertEqual(result["reason"], "unqualified-private-nomination")
            self.assertFalse(Path(request["mailbox"]).exists())

        with tempfile.TemporaryDirectory(prefix="claude-route-") as temporary:
            root = Path(temporary).resolve()
            root.chmod(0o700)
            _, publication, recipient = self.produce(route, root)
            request = self.prepare_input(root, {
                "path": publication["path"],
                "bytes": publication["bytes"],
                "sha256": publication["sha256"],
            }, recipient)
            request["message"]["recipient"] = {
                "thread_id": "another-receiver", "host_id": "local",
            }
            request_path = root / "prepare-input.json"
            self.write(request_path, request)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                route.main(
                    ["prepare", "--request", str(request_path)],
                    effective_uid=os.geteuid(),
                )
            result = json.loads(output.getvalue())
            self.assertFalse(result["prepared"])
            self.assertEqual(result["reason"], "recipient-nomination-mismatch")
            self.assertFalse(Path(request["mailbox"]).exists())

    def test_nomination_publication_is_create_only_and_preserves_existing_bytes(self):
        route, _, _ = self.load_modules()
        with tempfile.TemporaryDirectory(prefix="claude-route-") as temporary:
            root = Path(temporary).resolve()
            root.chmod(0o700)
            existing = root / "nomination.json"
            existing.write_bytes(b"existing private bytes")
            existing.chmod(0o600)
            exit_code, result, _ = self.produce(route, root)
            self.assertEqual(exit_code, 0)
            self.assertFalse(result["published"])
            self.assertEqual(result["reason"], "private-output-already-exists")
            self.assertEqual(existing.read_bytes(), b"existing private bytes")
            self.assertEqual(result["closure"], "no-provider-started")

    def test_reply_through_an_unchanged_received_claude_route_reaches_the_original_sender(self):
        from tests.plugins.surreal_intercom import projected_ordinary_flow as flow

        route, _sender, mailbox_module = self.load_modules()
        peer_message = importlib.import_module("peer_message")
        with tempfile.TemporaryDirectory(prefix="claude-return-") as temporary:
            root = Path(temporary).resolve()
            root.chmod(0o700)
            launcher = root / "claude"
            launcher.write_text(f"#!{sys.executable}\n" + flow.MCP_CHILD, encoding="utf-8")
            launcher.chmod(0o700)
            origin = {"thread_id": "claude-origin", "host_id": "local"}
            replier = {"thread_id": "codex-replier", "host_id": "local"}
            publication = flow.invoke(route.main, ["nominate", "--request", str(flow.write(
                root / "produce.json", {
                    "schema": "claude-route-nomination-request-v1", "recipient": origin,
                    "producer": origin, "publication": {
                        "path": str(root / "nomination.json"), "ownerUid": os.geteuid(),
                        "capture": self.capture(root)},
                }))], environment={
                    "CLAUDE_CODE_HOST_SESSION_ID": origin["thread_id"],
                    "CLAUDE_CODE_MESSAGING_SOCKET": "/synthetic/origin/messaging.sock",
                    "PATH": str(root)}, launcher_lookup=lambda _name, _path: str(launcher))
            self.assertTrue(publication["published"], publication)
            outbound = flow.message("outbound", replier, sender=origin)
            outbound["reply_route"] = flow.procedure_reply_route(PLUGIN, "claude-mcp", {
                "$REPLY_RECIPIENT_THREAD_ID": origin["thread_id"],
                "$REPLY_RECIPIENT_HOST_ID": origin["host_id"],
                "$REPLY_SUBMITTER_THREAD_ID": replier["thread_id"],
                "$REPLY_SUBMITTER_HOST_ID": replier["host_id"],
                "$CORRELATION_ID": outbound["correlation_id"],
                "$NOMINATION_PATH": publication["path"],
                "$NOMINATION_SHA256": publication["sha256"],
                "$NOMINATION_SIZE": publication["bytes"],
            })
            # The replier sees only the delivered envelope and takes its route as it arrived.
            received = json.loads(
                peer_message.serialize_peer_message(outbound, origin).split("\n", 1)[1])
            received_route = received["reply_route"]
            reply = {
                "message_id": "reply-1", "correlation_id": received_route["correlation_id"],
                "sender": received["recipient"], "recipient": received_route["recipient"],
                "owner": received["recipient"], "payload": "The comparison is complete.\n",
                "authority_ref": "synthetic://authority/reply", "holds": received["holds"],
            }
            store = root / "mailbox.sqlite3"
            self.initialize_mailbox(mailbox_module, store)
            prepared = flow.invoke(route.main, ["prepare", "--request", str(flow.write(
                root / "prepare.json", {
                    "schema": "claude-sender-request-preparation-v1",
                    "nomination": received_route["nomination"], "message": reply,
                    "attempt_id": "reply-1/attempt/1", "actor": received_route["submitter"],
                    "limits": {"operation_seconds": 8, "stdout_bytes": 65536,
                               "stderr_bytes": 65536},
                    "mailbox": str(store), "publication": {
                        "path": str(root / "sender-request.json"), "ownerUid": os.geteuid(),
                        "capture": self.capture(root)},
                }))])
            self.assertTrue(prepared["prepared"], prepared)
            completed = subprocess.run([
                sys.executable, "-B", str(SCRIPTS / "claude_mcp_sender.py"),
                "--store", str(store), "--request", prepared["path"],
            ], capture_output=True, text=True, timeout=12)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(result["reason"], "submitted", result)
            records = [json.loads(line) for line in
                       (root / "child.jsonl").read_text(encoding="utf-8").splitlines()]
            call = records[-2]["params"]
            self.assertEqual(call["name"], "SendMessage")
            self.assertEqual(call["arguments"]["to"], "uds:/synthetic/origin/messaging.sock")
            envelope = json.loads(call["arguments"]["message"].split("\n", 1)[1])
            self.assertEqual(envelope["recipient"], outbound["sender"])
            self.assertEqual(envelope["correlation_id"], outbound["correlation_id"])
            self.assertEqual(envelope["sender"], replier)
            self.assertEqual(envelope["actor"], replier)
            self.assertNotIn("reply_route", envelope)

    def test_a_reply_through_an_unchanged_route_binds_when_the_outbound_went_by_name(self):
        from unittest import mock
        from tests.plugins.surreal_intercom import projected_ordinary_flow as flow

        names = ("claude_route_nomination", "native_codex_mailbox", "peer_message",
                 "codex_route_nomination", "owner_admission_sender", "codex_ipc_transport")
        sys.path.insert(0, str(SCRIPTS))
        try:
            modules = {name: importlib.import_module(name) for name in names}
        finally:
            sys.path.remove(str(SCRIPTS))
        route, mailbox_module, peer_message = (modules[name] for name in names[:3])
        admission, transport = modules["owner_admission_sender"], modules["codex_ipc_transport"]
        limits = {"operation_seconds": 8, "stdout_bytes": 65536, "stderr_bytes": 65536}
        for kind in ("claude-mcp", "codex-owner-admission"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory(
                    prefix="by-name-return-") as temporary:
                root = Path(temporary).resolve()
                root.chmod(0o700)
                # The outbound recipient is planned under the name its listing row prints.
                receiver = {"thread_id": "claude-receiver", "host_id": "local"}
                if kind == "claude-mcp":
                    origin = {"thread_id": "claude-origin", "host_id": "local"}
                    return_launcher = root / "claude"
                    return_launcher.write_text(
                        f"#!{sys.executable}\n" + flow.MCP_CHILD, encoding="utf-8")
                    return_launcher.chmod(0o700)
                    publication = flow.invoke(route.main, ["nominate", "--request", str(flow.write(
                        root / "produce.json", {
                            "schema": "claude-route-nomination-request-v1", "recipient": origin,
                            "producer": origin, "publication": {
                                "path": str(root / "nomination.json"), "ownerUid": os.geteuid(),
                                "capture": self.capture(root)},
                        }))], environment={
                            "CLAUDE_CODE_HOST_SESSION_ID": origin["thread_id"],
                            "CLAUDE_CODE_MESSAGING_SOCKET": "/synthetic/origin/messaging.sock",
                            "PATH": str(root)},
                        launcher_lookup=lambda _name, _path: str(return_launcher))
                    self.assertTrue(publication["published"], publication)
                    outbound = flow.message("outbound", receiver, sender=origin)
                    outbound["reply_route"] = flow.procedure_reply_route(PLUGIN, kind, {
                        "$REPLY_RECIPIENT_THREAD_ID": origin["thread_id"],
                        "$REPLY_RECIPIENT_HOST_ID": origin["host_id"],
                        "$REPLY_SUBMITTER_THREAD_ID": receiver["thread_id"],
                        "$REPLY_SUBMITTER_HOST_ID": receiver["host_id"],
                        "$CORRELATION_ID": outbound["correlation_id"],
                        "$NOMINATION_PATH": publication["path"],
                        "$NOMINATION_SHA256": publication["sha256"],
                        "$NOMINATION_SIZE": publication["bytes"],
                    })
                else:
                    origin = {"thread_id": "codex-origin", "host_id": "local"}
                    outbound = flow.message("outbound", receiver, sender=origin)
                    outbound["reply_route"] = flow.codex_return_route(
                        root / "return", modules, PLUGIN, origin, receiver,
                        outbound["correlation_id"])

                # Send the outbound by name through the sender's own child.
                name_root = root / "name"
                name_root.mkdir(mode=0o700)
                name_launcher = name_root / "claude"
                name_launcher.write_text(f"#!{sys.executable}\n" + BY_NAME_CHILD, encoding="utf-8")
                name_launcher.chmod(0o700)
                outbound_store = root / "outbound.sqlite3"
                self.initialize_mailbox(mailbox_module, outbound_store)
                prepared = flow.invoke(route.main, ["prepare", "--request", str(flow.write(
                    root / "prepare-outbound.json", {
                        "schema": "claude-name-request-preparation-v1", "name": "claude-receiver",
                        "message": outbound, "attempt_id": "outbound/attempt/1",
                        "actor": origin, "limits": limits, "mailbox": str(outbound_store),
                        "publication": {
                            "path": str(root / "outbound-request.json"), "ownerUid": os.geteuid(),
                            "capture": self.capture(root)},
                    }))], environment={"PATH": str(name_root)},
                    launcher_lookup=lambda _name, _path: str(name_launcher))
                self.assertTrue(prepared["prepared"], prepared)
                sent = subprocess.run([
                    sys.executable, "-B", str(SCRIPTS / "claude_mcp_sender.py"),
                    "--store", str(outbound_store), "--request", prepared["path"],
                ], capture_output=True, text=True, timeout=12)
                self.assertEqual(sent.returncode, 0, sent.stderr)
                sent_result = json.loads(sent.stdout)
                self.assertEqual((sent_result["path"], sent_result["reason"]), ("name", "submitted"))
                outbound_call = [
                    json.loads(line)["params"] for line in
                    (name_root / "name-child.jsonl").read_text(encoding="utf-8").splitlines()
                    if json.loads(line).get("method") == "tools/call"][-1]
                self.assertEqual(outbound_call["arguments"]["to"], "claude-receiver")

                # The recipient replies through the route exactly as it arrived.
                received = json.loads(outbound_call["arguments"]["message"].split("\n", 1)[1])
                received_route = received["reply_route"]
                self.assertEqual(received_route, outbound["reply_route"])
                reply = {
                    "message_id": "reply-1", "correlation_id": received_route["correlation_id"],
                    "sender": received["recipient"], "recipient": received_route["recipient"],
                    "owner": received["recipient"], "payload": "The comparison is complete.\n",
                    "authority_ref": "synthetic://authority/reply", "holds": received["holds"],
                }
                reply_store = root / "reply.sqlite3"
                self.initialize_mailbox(mailbox_module, reply_store)
                if kind == "claude-mcp":
                    reply_prepared = flow.invoke(route.main, ["prepare", "--request", str(
                        flow.write(root / "prepare-reply.json", {
                            "schema": "claude-sender-request-preparation-v1",
                            "nomination": received_route["nomination"], "message": reply,
                            "attempt_id": "reply-1/attempt/1",
                            "actor": received_route["submitter"], "limits": limits,
                            "mailbox": str(reply_store), "publication": {
                                "path": str(root / "reply-request.json"),
                                "ownerUid": os.geteuid(), "capture": self.capture(root)},
                        }))])
                    self.assertTrue(reply_prepared["prepared"], reply_prepared)
                    replied = subprocess.run([
                        sys.executable, "-B", str(SCRIPTS / "claude_mcp_sender.py"),
                        "--store", str(reply_store), "--request", reply_prepared["path"],
                    ], capture_output=True, text=True, timeout=12)
                    self.assertEqual(replied.returncode, 0, replied.stderr)
                    self.assertEqual(json.loads(replied.stdout)["reason"], "submitted")
                    records = [json.loads(line) for line in
                               (root / "child.jsonl").read_text(encoding="utf-8").splitlines()]
                    call = records[-2]["params"]
                    self.assertEqual(call["arguments"]["to"], "uds:/synthetic/origin/messaging.sock")
                    text = call["arguments"]["message"]
                else:
                    flow.invoke(mailbox_module.main, [
                        "--store", str(reply_store), "plan", "--input",
                        str(flow.write(root / "reply.json", reply))])
                    run = root / "send"
                    run.mkdir(mode=0o700)
                    nomination = json.loads(Path(received_route["nomination"]["path"]).read_bytes())
                    peer = flow.Peer(nomination["acceptor"], "reply-1/attempt/1")

                    def connect(endpoint, connection_limits, wait):
                        self.assertEqual(endpoint, nomination["route"]["endpoint"])
                        return transport.CliTransport(
                            endpoint, connection_limits, wait,
                            connector=lambda _endpoint, _wait: peer)

                    with mock.patch.object(admission, "CliTransport", connect):
                        result = flow.invoke(admission.main, [
                            "--store", str(reply_store), "--request", str(flow.write(
                                root / "send.json", {
                                    "message_id": reply["message_id"],
                                    "attempt_id": "reply-1/attempt/1",
                                    "actor": received_route["submitter"],
                                    "recipient": reply["recipient"],
                                    "evidence_ref": "synthetic://reply-send",
                                    "native": {
                                        "nomination": received_route["nomination"],
                                        "purpose": "Return the requested reply",
                                        "authorityRefs": [reply["authority_ref"]],
                                        "holdRefs": reply["holds"],
                                        "scope": {"send": True, "ownerAdmissionIntent": True,
                                                  "holdsSatisfied": True},
                                        "profile": {}, "observationSeconds": 0.1,
                                    },
                                    "capture": flow.capture(run),
                                }))], clock=lambda: 7005)
                    self.assertTrue(result["claimed"], result)
                    self.assertEqual(result["peer_input"], "possible_submission", result)
                    self.assertEqual(peer.frames[1]["params"]["conversationId"], origin["thread_id"])
                    text = peer.frames[-1]["params"]["turnStart"]["request"]["input"][0]["text"]
                envelope = json.loads(text.split("\n", 1)[1])
                self.assertEqual(envelope["recipient"], outbound["sender"])
                self.assertEqual(envelope["correlation_id"], outbound["correlation_id"])
                self.assertEqual(envelope["sender"], receiver)
                self.assertEqual(envelope["actor"], receiver)
                self.assertNotIn("reply_route", envelope)


# A `claude mcp serve` stand-in that lists one local session and accepts one send by name.
BY_NAME_CHILD = '''import json
import sys
from pathlib import Path

assert sys.argv[1:] == ["mcp", "serve"], sys.argv
LISTING = "Peer sessions (1):\\n  claude-receiver [3fa9c1]  \\u00b7  interactive  \\u00b7  idle"
CURSOR = {"type": "string"}
CATALOG = {"tools": [
    {"name": "SendMessage", "inputSchema": {
        "type": "object", "properties": {"to": {"type": "string"}, "message": {"type": "string"}},
        "required": ["to", "message"], "additionalProperties": False}},
    {"name": "ListAgents", "inputSchema": {
        "type": "object", "properties": {"cursor": CURSOR}, "additionalProperties": False}},
]}
with Path(__file__).with_name("name-child.jsonl").open("w", encoding="utf-8") as trace:
    for line in sys.stdin:
        request = json.loads(line)
        trace.write(json.dumps(request) + "\\n")
        trace.flush()
        method = request["method"]
        if method == "notifications/initialized":
            continue
        if method == "initialize":
            result = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}}
        elif method == "tools/list":
            result = CATALOG
        elif request["params"]["name"] == "ListAgents":
            result = {"content": [{"type": "text", "text": LISTING}]}
        else:
            result = {"content": [{"type": "text", "text": "In the inbox, not yet read."}]}
        print(json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": result}), flush=True)
'''


if __name__ == "__main__":
    unittest.main()
