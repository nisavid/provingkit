"""Public route-nomination command behavior over injected observations."""

import contextlib
import copy
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from tests.plugins.surreal_intercom.test_rolecasting_codex_owner_admission import (
    InjectedPeerStream,
)


ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = (
    ROOT / "plugins" / "surreal-intercom" / "skills"
    / "communicating-with-agents" / "scripts"
)


class FixtureObservation:
    """Primitive procfs, filesystem, process, and clock observations."""

    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.links = {
            "/proc/100/exe": "/usr/bin/python3",
            "/proc/100/ns/net": "net:[701]",
            "/proc/200/exe": "/opt/codex/app-server",
            "/proc/200/ns/net": "net:[701]",
            "/proc/300/exe": "/opt/codex/Codex",
            "/proc/300/ns/net": "net:[701]",
            "/proc/300/fd/11": "socket:[501]",
        }
        self.files = {
            "/proc/100/stat": self._process_stat(100, 200, 1001),
            "/proc/100/status": self._status(),
            "/proc/200/stat": self._process_stat(200, 300, 1002),
            "/proc/200/status": self._status(),
            "/proc/300/stat": self._process_stat(300, 1, 1003),
            "/proc/300/status": self._status(),
            "/proc/sys/kernel/random/boot_id": b"synthetic-boot\n",
            "/proc/300/net/unix": (
                b"Num RefCount Protocol Flags Type St Inode Path\n"
                + ("00000000: 00000002 00000000 00010000 0001 01 501 %s\n"
                   % endpoint).encode()
            ),
        }
        self.identities = {
            "/usr/bin/python3": (8, 101),
            "/opt/codex/app-server": (8, 102),
            "/opt/codex/Codex": (8, 103),
        }
        self.nodes = {
            str(endpoint.parent): SimpleNamespace(
                st_mode=stat.S_IFDIR | 0o700, st_uid=1000, st_dev=9, st_ino=601,
            ),
            str(endpoint): SimpleNamespace(
                st_mode=stat.S_IFSOCK | 0o600, st_uid=1000, st_dev=9, st_ino=602,
            ),
        }
        self.clock = 1000
        self.clock_step = 1
        self.link_sequences = {}
        self.descriptors = ["11"]

    @staticmethod
    def _process_stat(pid, ppid, start_ticks):
        fields = ["S", str(ppid), *("0" for _ in range(17)), str(start_ticks)]
        return f"{pid} (fixture process) {' '.join(fields)}\n".encode()

    @staticmethod
    def _status():
        return b"Name:\tfixture\nUid:\t1000\t1000\t1000\t1000\nGid:\t1000\t1000\t1000\t1000\n"

    def getpid(self):
        return 100

    def geteuid(self):
        return 1000

    def monotonic_milliseconds(self):
        value = self.clock
        self.clock += self.clock_step
        return value

    def read_bytes(self, path, maximum):
        data = self.files[str(path)]
        if len(data) > maximum:
            raise OSError("fixture read exceeds bound")
        return data

    def readlink(self, path, maximum):
        key = str(path)
        sequence = self.link_sequences.get(key)
        value = sequence.pop(0) if sequence else self.links[key]
        if len(value.encode()) > maximum:
            raise OSError("fixture link exceeds bound")
        return value

    def listdir(self, path, maximum_entries):
        self.assert_path(path, "/proc/300/fd")
        return list(self.descriptors)

    def executable_identity(self, process_link, resolved_path):
        device, inode = self.identities[resolved_path]
        return {"path": resolved_path, "device": device, "inode": inode}

    def lstat(self, path):
        return self.nodes[str(path)]

    @staticmethod
    def assert_path(actual, expected):
        if str(actual) != expected:
            raise AssertionError(f"unexpected fixture path: {actual}")


class CodexRouteNominationTests(unittest.TestCase):
    def supplied_sample_request(self, root):
        endpoint = root / "codex-home" / "ipc" / "ipc.sock"
        actor = {"thread_id": "forwarder", "host_id": "forwarder-host"}
        recipient = {"thread_id": "owner-peer", "host_id": "local"}
        python_identity = {"path": "/usr/bin/python3", "device": 8, "inode": 101}
        server_identity = {"path": "/opt/codex/app-server", "device": 8, "inode": 102}
        desktop_identity = {"path": "/opt/codex/Codex", "device": 8, "inode": 103}
        ancestors = [
            {"pid": 100, "ppid": 200, "uid": 1000, "gid": 1000,
             "startTicks": 1001, "role": "helper",
             "roleEvidence": "synthetic://source/helper", "executable": python_identity},
            {"pid": 200, "ppid": 300, "uid": 1000, "gid": 1000,
             "startTicks": 1002, "role": "app-server",
             "roleEvidence": "synthetic://source/app-server", "executable": server_identity},
            {"pid": 300, "ppid": 1, "uid": 1000, "gid": 1000,
             "startTicks": 1003, "role": "desktop-main",
             "roleEvidence": "synthetic://source/desktop-main", "executable": desktop_identity},
        ]
        view = {
            "bootId": "synthetic-boot", "networkNamespace": "net:[701]",
            "ancestors": ancestors,
            "listeners": [{
                "pid": 300, "fd": 11, "socketInode": 501, "kind": "stream",
                "state": "listening", "routeForm": "direct-primary",
                "path": str(endpoint),
            }],
            "ipcDirectory": {
                "path": str(endpoint.parent), "kind": "directory", "uid": 1000,
                "mode": 0o700, "symlink": False, "device": 9, "inode": 601,
            },
            "socket": {
                "path": str(endpoint), "kind": "socket", "uid": 1000,
                "mode": 0o600, "symlink": False, "device": 9, "inode": 602,
            },
        }
        permissions = {}
        for name, act, consumer in (
            ("metadata", "acquire-route-metadata", "nomination-controller"),
            ("nomination", "publish-route-nomination", "codex-route-nomination"),
            ("routeUse", "consume-route-nomination", "owner-admission-sender"),
        ):
            permissions[name] = {
                "evidenceRef": "synthetic://authority/" + name,
                "issuer": {"thread_id": "operator", "host_id": "native"},
                "actor": actor, "act": act, "chat": recipient,
                "operationId": "shared-exchange",
                "validityRef": "synthetic://validity/" + name,
                "revocationRef": "synthetic://revocation/" + name,
                "consumer": consumer,
            }
        nomination_path = root / "nomination.json"
        return {
            "schema": "codex-route-nomination-request-v1",
            "invocation": {
                "evidenceRef": "synthetic://native-command", "nativeItemId": "item-1",
                "taskRef": "synthetic://task", "attemptId": "shared-exchange",
                "chat": recipient,
                "command": ["/usr/bin/python3", "-B", "/opt/helpers/codex_route_nomination.py",
                            "--request", "/private/request.json"],
                "workingDirectory": "/synthetic/worktree", "status": "completed",
                "exitCode": 0, "evidenceComplete": True,
                "helper": {"path": "/opt/helpers/codex_route_nomination.py",
                           "sha256": "a" * 64},
            },
            "permissions": permissions, "recipient": recipient, "actor": actor,
            "exchange": "shared-exchange", "holds": ["synthetic://original-hold"],
            "sample": {
                "startedMilliseconds": 1000, "finishedMilliseconds": 1004,
                "before": view, "after": copy.deepcopy(view),
                "bounds": {
                    "complete": True, "sharedWatchdogMilliseconds": 5000,
                    "descriptorEntries": 12, "unixRows": 30, "unixBytes": 4096,
                    "descriptorLinkBytes": 512, "maxMetadataBytes": 1024,
                },
            },
            "publication": {
                "path": str(nomination_path), "ownerUid": nomination_path.parent.stat().st_uid,
                "capture": {"run_root": str(root), "allowance_bytes": 8388608,
                            "terminal_provision_bytes": 524288,
                            "later_forecast_bytes": 0},
            },
        }

    def invoke(self, request, root, observer=None):
        request_path = root / "request.json"
        request_path.write_text(json.dumps(request), encoding="utf-8")
        sys.path.insert(0, str(SCRIPTS))
        try:
            module = importlib.import_module("codex_route_nomination")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                kwargs = {"effective_uid": request["publication"]["ownerUid"]}
                if observer is None and request.get("schema") == "codex-route-nomination-request-v2":
                    observer = FixtureObservation(root / "codex-home" / "ipc" / "ipc.sock")
                if observer is not None:
                    kwargs["observer"] = observer
                exit_code = module.main(["--request", str(request_path)], **kwargs)
        finally:
            sys.path.remove(str(SCRIPTS))
        return exit_code, json.loads(output.getvalue())

    def production_request(self, root):
        request = self.supplied_sample_request(root)
        actor = request.pop("actor")
        request["schema"] = "codex-route-nomination-request-v2"
        request["producer"] = request["recipient"]
        request["submitter"] = actor
        request["operationId"] = request.pop("exchange")
        request["acquisitionHolds"] = request.pop("holds")
        request.pop("sample")
        invocation = request["invocation"]
        for key in ("evidenceRef", "nativeItemId", "status", "exitCode", "evidenceComplete"):
            invocation.pop(key)
        invocation["control"] = "native-read-thread-command-execution"
        request["selection"] = {
            "launchSourceRef": "synthetic://installed-launch-source",
            "listenerSourceRef": "synthetic://installed-listener-source",
            "roles": [
                {"role": "helper", "discriminator": "invoked-helper",
                 "evidenceRef": "synthetic://source/helper",
                 "executable": {"path": "/usr/bin/python3", "device": 8, "inode": 101}},
                {"role": "app-server", "discriminator": "direct-parent-app-server",
                 "evidenceRef": "synthetic://source/app-server",
                 "executable": {"path": "/opt/codex/app-server", "device": 8, "inode": 102}},
                {"role": "desktop-main", "discriminator": "direct-parent-desktop-main",
                 "evidenceRef": "synthetic://source/desktop-main",
                 "executable": {"path": "/opt/codex/Codex", "device": 8, "inode": 103}},
            ],
            "routeForm": "direct-primary",
        }
        request["permissions"]["metadata"]["actor"] = request["producer"]
        request["permissions"]["nomination"]["actor"] = request["producer"]
        request["permissions"]["routeUse"]["actor"] = request["submitter"]
        return request

    def request(self, root):
        return self.production_request(root)

    def test_public_producer_collects_from_invoked_ancestry_without_a_completed_sample(self):
        with tempfile.TemporaryDirectory(prefix="codex-production-nomination-") as temporary:
            root = Path(temporary).resolve()
            root.chmod(0o700)
            request = self.production_request(root)
            observer = FixtureObservation(root / "codex-home" / "ipc" / "ipc.sock")

            exit_code, result = self.invoke(request, root, observer)

            self.assertEqual(exit_code, 0)
            self.assertTrue(result["published"])
            record = json.loads(Path(result["path"]).read_bytes())
            self.assertEqual(record["schema"], "codex-route-nomination-v2")
            self.assertEqual(record["producer"], request["producer"])
            self.assertEqual(record["submitter"], request["submitter"])
            self.assertEqual(record["acceptor"]["pid"], 300)
            self.assertEqual(set(record["freshness"]), {"observedAtMilliseconds"})
            self.assertGreaterEqual(record["freshness"]["observedAtMilliseconds"], 1000)

    def test_bound_stream_without_listen_flag_is_not_published(self):
        with tempfile.TemporaryDirectory(prefix="codex-nonlistener-") as temporary:
            root = Path(temporary).resolve()
            root.chmod(0o700)
            request = self.production_request(root)
            observer = FixtureObservation(root / "codex-home" / "ipc" / "ipc.sock")
            observer.files["/proc/300/net/unix"] = observer.files[
                "/proc/300/net/unix"
            ].replace(b"00010000", b"00000000")

            exit_code, result = self.invoke(request, root, observer)

            self.assertEqual(exit_code, 0)
            self.assertFalse(result["published"])
            self.assertEqual(result["reason"], "ambiguous-or-unsupported-listener")
            self.assertFalse(Path(request["publication"]["path"]).exists())

    def test_same_pid_executable_change_at_final_role_check_refuses_publication(self):
        with tempfile.TemporaryDirectory(prefix="codex-production-recheck-") as temporary:
            root = Path(temporary).resolve()
            root.chmod(0o700)
            request = self.production_request(root)
            observer = FixtureObservation(root / "codex-home" / "ipc" / "ipc.sock")
            observer.identities["/opt/codex/replaced-server"] = (8, 999)
            observer.link_sequences["/proc/200/exe"] = [
                "/opt/codex/app-server", "/opt/codex/replaced-server",
            ]

            exit_code, result = self.invoke(request, root, observer)

            self.assertEqual(exit_code, 0)
            self.assertFalse(result["published"])
            self.assertEqual(result["reason"], "sample-identity-changed")
            self.assertFalse(Path(request["publication"]["path"]).exists())

    def test_caller_supplied_completed_sample_is_not_a_production_acquisition(self):
        with tempfile.TemporaryDirectory(prefix="codex-supplied-sample-") as temporary:
            root = Path(temporary).resolve()
            root.chmod(0o700)
            request = self.supplied_sample_request(root)

            exit_code, result = self.invoke(request, root)

            self.assertEqual(exit_code, 0)
            self.assertFalse(result["published"])
            self.assertEqual(result["reason"], "invalid-nomination-request")
            self.assertFalse(Path(request["publication"]["path"]).exists())

    def consume(self, change_peer=None, *, now_milliseconds=None, change_after_discovery=None,
                mutate_sender=None, same_actor=False, second_original=None,
                second_attempt_id=None):
        temporary = tempfile.TemporaryDirectory(prefix="codex-nomination-consume-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name).resolve()
        root.chmod(0o700)
        producer_request = self.production_request(root)
        if same_actor:
            producer_request["submitter"] = producer_request["producer"]
            producer_request["permissions"]["routeUse"]["actor"] = producer_request["producer"]
        observer = FixtureObservation(root / "codex-home" / "ipc" / "ipc.sock")
        _, publication = self.invoke(producer_request, root, observer)
        nomination_path = Path(publication["path"])
        nomination_bytes = nomination_path.read_bytes()
        nomination = json.loads(nomination_bytes)
        peer = copy.deepcopy(nomination["acceptor"])
        if change_peer is not None:
            change_peer(peer)
        peer_observations = peer
        if change_after_discovery is not None:
            changed = copy.deepcopy(peer)
            change_after_discovery(changed)
            peer_observations = [peer, changed]
        stream = InjectedPeerStream(peer_observations)

        store = root / "mailbox.sqlite3"
        original = {
            "message_id": "owner-message", "correlation_id": "shared-exchange",
            "sender": {"thread_id": "origin", "host_id": "origin-host"},
            "recipient": producer_request["recipient"],
            "owner": {"thread_id": "task-owner", "host_id": "owner-host"},
            "payload": "Guard this payload.",
            "authority_ref": "synthetic://authority/send-a",
            "holds": ["synthetic://original-hold"],
        }
        message_path = root / "message.json"
        message_path.write_text(json.dumps(original), encoding="utf-8")
        second_message_path = None
        if second_original is not None:
            second_message_path = root / "second-message.json"
            second_message_path.write_text(json.dumps(second_original), encoding="utf-8")
        environment = {
            **os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
        }
        mailbox_commands = [["init"], ["plan", "--input", str(message_path)]]
        if second_message_path is not None:
            mailbox_commands.append(["plan", "--input", str(second_message_path)])
        for arguments in mailbox_commands:
            completed = subprocess.run([
                sys.executable, "-B", str(SCRIPTS / "native_codex_mailbox.py"),
                "--store", str(store), *arguments,
            ], capture_output=True, text=True, timeout=10, env=environment)
            self.assertEqual(completed.returncode, 0, completed.stderr)
        capture = root / "capture"
        capture.mkdir(mode=0o700)
        sender_request = {
            "message_id": "owner-message", "attempt_id": "owner-attempt",
            "actor": producer_request["submitter"],
            "recipient": producer_request["recipient"],
            "evidence_ref": "synthetic://owner-evidence",
            "native": {
                "nomination": {
                    "path": str(nomination_path), "sha256": publication["sha256"],
                    "size": publication["bytes"],
                },
                "purpose": "Forward the original peer message",
                "authorityRefs": [original["authority_ref"]],
                "holdRefs": original["holds"],
                "scope": {"send": True, "ownerAdmissionIntent": True,
                          "holdsSatisfied": True},
                "profile": {}, "observationSeconds": 0.1,
            },
            "capture": {"run_root": str(capture), "allowance_bytes": 8388608,
                        "terminal_provision_bytes": 524288, "later_forecast_bytes": 0},
        }
        expected = producer_request["invocation"]
        sender_request["native"]["nomination"]["invocation"] = {
            **expected,
            "evidenceRef": "synthetic://native-command/completed",
            "nativeItemId": "native-item-1", "status": "completed", "exitCode": 0,
        }
        if mutate_sender is not None:
            mutate_sender(sender_request)
        sender_request_path = root / "sender-request.json"
        sender_request_path.write_text(json.dumps(sender_request), encoding="utf-8")
        sys.path.insert(0, str(SCRIPTS))
        try:
            sender = importlib.import_module("owner_admission_sender")
            transport_module = importlib.import_module("codex_ipc_transport")
        finally:
            sys.path.remove(str(SCRIPTS))

        def send(request_path, peer_stream):
            def transport(endpoint, limits, wait):
                return transport_module.CliTransport(
                    endpoint, limits, wait,
                    connector=lambda _endpoint, _wait: peer_stream,
                )

            output = io.StringIO()
            with mock.patch.object(sender, "CliTransport", transport), \
                    contextlib.redirect_stdout(output):
                kwargs = {"effective_uid": producer_request["publication"]["ownerUid"]}
                kwargs["clock"] = lambda: 7005 if now_milliseconds is None else now_milliseconds
                code = sender.main(
                    ["--store", str(store), "--request", str(request_path)], **kwargs,
                )
            return code, json.loads(output.getvalue())

        exit_code, result = send(sender_request_path, stream)
        if second_original is None:
            return exit_code, result, stream

        second_capture = root / "second-capture"
        second_capture.mkdir(mode=0o700)
        second_sender_request = copy.deepcopy(sender_request)
        second_sender_request.update(
            message_id=second_original["message_id"], attempt_id=second_attempt_id,
            evidence_ref="synthetic://owner-evidence/b",
        )
        second_sender_request["native"]["authorityRefs"] = [
            second_original["authority_ref"]
        ]
        second_sender_request["native"]["holdRefs"] = second_original["holds"]
        second_sender_request["capture"]["run_root"] = str(second_capture)
        second_sender_request_path = root / "second-sender-request.json"
        second_sender_request_path.write_text(
            json.dumps(second_sender_request), encoding="utf-8",
        )
        second_stream = InjectedPeerStream(
            copy.deepcopy(peer), response_request_id=second_attempt_id,
        )
        second_exit_code, second_result = send(second_sender_request_path, second_stream)

        mailbox_records = {}
        for name, message_id in (("a", original["message_id"]),
                                 ("b", second_original["message_id"])):
            completed = subprocess.run([
                sys.executable, "-B", str(SCRIPTS / "native_codex_mailbox.py"),
                "--store", str(store), "show", message_id,
            ], capture_output=True, text=True, timeout=10, env=environment)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            mailbox_records[name] = json.loads(completed.stdout)
        return {
            "a": (exit_code, result, stream),
            "b": (second_exit_code, second_result, second_stream),
            "original_a": original, "original_b": second_original,
            "request_a": sender_request, "request_b": second_sender_request,
            "nomination_before": nomination_bytes,
            "nomination_after": nomination_path.read_bytes(),
            "mailbox": mailbox_records,
        }

    def test_collected_direct_primary_route_publishes_one_private_provisional_record(self):
        with tempfile.TemporaryDirectory(prefix="codex-nomination-") as temporary:
            root = Path(temporary).resolve()
            root.chmod(0o700)
            request = self.request(root)
            exit_code, result = self.invoke(request, root)

            self.assertEqual(exit_code, 0)
            self.assertTrue(result["published"])
            self.assertEqual(result["reason"], "published")
            self.assertEqual(result["closure"], "no-connection-opened")
            self.assertEqual(set(result), {"published", "reason", "path", "bytes",
                                           "sha256", "closure"})
            path = Path(result["path"])
            data = path.read_bytes()
            self.assertEqual(result["bytes"], len(data))
            self.assertLessEqual(len(data), 4096)
            self.assertEqual(result["sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            record = json.loads(data)
            self.assertEqual(record["status"], "provisional")
            self.assertEqual(record["route"]["target"], "owner-peer")
            self.assertEqual(record["acceptor"]["pid"], 300)
            self.assertEqual(record["privacy"], {
                "boundary": "unix-account-private", "sameUidIsolation": False,
                "pathIsAuthority": False,
            })

    def test_changed_identity_unsupported_routes_and_incomplete_evidence_refuse_publication(self):
        def alternate_listener(request, observer):
            observer.descriptors.append("12")
            observer.links["/proc/300/fd/12"] = "socket:[502]"
            observer.files["/proc/300/net/unix"] += (
                b"00000001: 00000002 00000000 00010000 0001 01 502 /tmp/codex-1000.sock\n"
            )

        mutations = {
            "unrecognized-launcher": (
                lambda request, observer: request["selection"]["roles"].insert(1, {
                    "role": "launcher", "discriminator": "unrecognized-launcher",
                    "evidenceRef": "synthetic://source/launcher",
                    "executable": {"path": "/opt/launcher", "device": 8, "inode": 104},
                }),
                "unsupported-launch-chain",
            ),
            "alternate-listener": (
                alternate_listener,
                "ambiguous-or-unsupported-listener",
            ),
            "descriptor-bound-hit": (
                lambda request, observer: setattr(
                    observer, "descriptors", [str(index) for index in range(513)]
                ),
                "incomplete-or-oversized-sample",
            ),
            "shared-watchdog-exceeded": (
                lambda request, observer: setattr(observer, "clock_step", 600),
                "sample-watchdog-exceeded",
            ),
            "wrong-route-operation": (
                lambda request, observer: request["permissions"]["routeUse"].update(
                    operationId="other"
                ),
                "permission-binding-mismatch",
            ),
            "metadata-bound-to-submitter": (
                lambda request, observer: request["permissions"]["metadata"].update(
                    actor=request["submitter"]
                ),
                "permission-binding-mismatch",
            ),
            "route-use-bound-to-producer": (
                lambda request, observer: request["permissions"]["routeUse"].update(
                    actor=request["producer"]
                ),
                "permission-binding-mismatch",
            ),
            "nomination-act-swapped": (
                lambda request, observer: request["permissions"]["nomination"].update(
                    act="send-peer-message"
                ),
                "permission-binding-mismatch",
            ),
            "truncated-native-evidence": (
                lambda request, observer: request["invocation"]["helper"].update(sha256=""),
                "incomplete-native-invocation",
            ),
            "missing-role-source": (
                lambda request, observer: request["selection"]["roles"][1].update(
                    evidenceRef=""
                ),
                "role-evidence-unavailable",
            ),
        }
        for name, (mutate, reason) in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory(
                    prefix="codex-nomination-refusal-") as temporary:
                root = Path(temporary).resolve()
                root.chmod(0o700)
                request = self.request(root)
                observer = FixtureObservation(root / "codex-home" / "ipc" / "ipc.sock")
                mutate(request, observer)
                exit_code, result = self.invoke(request, root, observer)
                self.assertEqual(exit_code, 0)
                self.assertFalse(result["published"])
                self.assertEqual(result["reason"], reason)
                self.assertEqual(result["closure"], "no-connection-opened")
                self.assertFalse(Path(request["publication"]["path"]).exists())

    def test_existing_final_record_is_never_replaced(self):
        with tempfile.TemporaryDirectory(prefix="codex-nomination-existing-") as temporary:
            root = Path(temporary).resolve()
            root.chmod(0o700)
            request = self.request(root)
            _, first = self.invoke(request, root)
            path = Path(first["path"])
            retained = path.read_bytes()

            exit_code, second = self.invoke(request, root)

            self.assertEqual(exit_code, 0)
            self.assertFalse(second["published"])
            self.assertEqual(second["reason"], "nomination-already-exists")
            self.assertEqual(path.read_bytes(), retained)

    def test_guarded_owner_admission_uses_the_nominated_peer_and_same_connection(self):
        exit_code, result, stream = self.consume()

        self.assertEqual(exit_code, 0)
        self.assertEqual(result["reason"], "rpc-success-effect-unconfirmed")
        self.assertEqual(result["peer_input"], "possible_submission")
        self.assertEqual(
            [frame["method"] for frame in stream.writes],
            ["initialize", "thread-owner-discovery", "thread-follower-start-turn"],
        )
        self.assertEqual(stream.peer_identity_calls, 2)
        self.assertTrue(stream.closed)

    def test_distinct_submitter_consumes_unchanged_nomination_after_five_seconds(self):
        exit_code, result, stream = self.consume()

        self.assertEqual(exit_code, 0)
        self.assertEqual(result["reason"], "rpc-success-effect-unconfirmed")
        self.assertEqual(result["peer_input"], "possible_submission")
        self.assertEqual(
            [frame["method"] for frame in stream.writes],
            ["initialize", "thread-owner-discovery", "thread-follower-start-turn"],
        )
        payload = stream.writes[-1]["params"]["turnStart"]["request"]["input"][0]["text"]
        envelope = json.loads(payload.split("\n", 1)[1])
        self.assertEqual(envelope["sender"], {"thread_id": "origin", "host_id": "origin-host"})
        self.assertEqual(envelope["actor"], {"thread_id": "forwarder",
                                             "host_id": "forwarder-host"})
        self.assertEqual(envelope["owner"], {"thread_id": "task-owner",
                                             "host_id": "owner-host"})

    def test_same_codex_actor_can_produce_and_submit_when_each_grant_matches(self):
        exit_code, result, stream = self.consume(same_actor=True)

        self.assertEqual(exit_code, 0)
        self.assertEqual(result["reason"], "rpc-success-effect-unconfirmed")
        payload = stream.writes[-1]["params"]["turnStart"]["request"]["input"][0]["text"]
        envelope = json.loads(payload.split("\n", 1)[1])
        self.assertEqual(envelope["actor"], {"thread_id": "owner-peer", "host_id": "local"})

    def test_one_guarded_route_carries_two_independently_initiated_messages(self):
        second_original = {
            "message_id": "independent-message-b",
            "correlation_id": "independent-exchange-b",
            "sender": {"thread_id": "second-origin", "host_id": "second-origin-host"},
            "recipient": {"thread_id": "owner-peer", "host_id": "local"},
            "owner": {"thread_id": "second-owner", "host_id": "second-owner-host"},
            "payload": "Carry independent message B.",
            "authority_ref": "synthetic://authority/send-b",
            "holds": ["synthetic://original-hold"],
        }

        with mock.patch.object(self, "invoke", wraps=self.invoke) as producer:
            observed = self.consume(
                second_original=second_original,
                second_attempt_id="independent-attempt-b",
            )

        a_exit, a_result, a_stream = observed["a"]
        b_exit, b_result, b_stream = observed["b"]
        self.assertEqual((a_exit, b_exit), (0, 0))
        self.assertEqual(producer.call_count, 1)
        self.assertEqual(observed["nomination_after"], observed["nomination_before"])

        # These are independently supplied mailbox and request bindings. The
        # guarded sender's acceptance below remains the enforcement observation.
        self.assertEqual(observed["original_a"]["message_id"], "owner-message")
        self.assertEqual(observed["original_a"]["correlation_id"], "shared-exchange")
        self.assertEqual(observed["request_a"]["attempt_id"], "owner-attempt")
        self.assertEqual(observed["original_b"]["message_id"], "independent-message-b")
        self.assertEqual(observed["original_b"]["correlation_id"], "independent-exchange-b")
        self.assertEqual(observed["request_b"]["attempt_id"], "independent-attempt-b")
        self.assertNotEqual(observed["original_a"]["message_id"],
                            observed["original_b"]["message_id"])
        self.assertNotEqual(observed["original_a"]["correlation_id"],
                            observed["original_b"]["correlation_id"])
        self.assertNotEqual(observed["request_a"]["attempt_id"],
                            observed["request_b"]["attempt_id"])
        for request, authority_ref in (
                (observed["request_a"], "synthetic://authority/send-a"),
                (observed["request_b"], "synthetic://authority/send-b")):
            self.assertIn("nomination", request["native"])
            self.assertNotIn("route", request["native"])
            self.assertEqual(request["actor"],
                             {"thread_id": "forwarder", "host_id": "forwarder-host"})
            self.assertEqual(request["native"]["authorityRefs"],
                             [authority_ref])

        self.assertEqual(a_result["reason"], "rpc-success-effect-unconfirmed")
        self.assertEqual(a_result["peer_input"], "possible_submission")
        self.assertEqual(b_result["reason"], "rpc-success-effect-unconfirmed")
        self.assertEqual(b_result["peer_input"], "possible_submission")
        self.assertEqual(
            [frame["method"] for frame in a_stream.writes],
            ["initialize", "thread-owner-discovery", "thread-follower-start-turn"],
        )
        self.assertEqual(
            [frame["method"] for frame in b_stream.writes],
            ["initialize", "thread-owner-discovery", "thread-follower-start-turn"],
        )

        def peer_message(peer_stream):
            payload = peer_stream.writes[-1]["params"]["turnStart"]["request"]["input"][0]["text"]
            return json.loads(payload.split("\n", 1)[1])

        message_a = peer_message(a_stream)
        message_b = peer_message(b_stream)
        self.assertEqual(
            (message_a["message_id"], message_a["correlation_id"]),
            ("owner-message", "shared-exchange"),
        )
        self.assertEqual(
            (message_b["message_id"], message_b["correlation_id"]),
            ("independent-message-b", "independent-exchange-b"),
        )
        for name, attempt_id in (("a", "owner-attempt"),
                                 ("b", "independent-attempt-b")):
            self.assertEqual(observed["mailbox"][name]["state"], "unknown")
            self.assertEqual(
                [attempt["attempt_id"] for attempt in observed["mailbox"][name]["attempts"]],
                [attempt_id],
            )

    def test_swapped_submitter_and_changed_attempt_authority_or_holds_refuse_before_connection(self):
        mutations = {
            "swapped-submitter": (
                lambda request: request.update(actor=request["recipient"]),
                "nomination-binding-mismatch",
            ),
            "changed-attempt": (
                lambda request: request["native"]["nomination"]["invocation"].update(
                    attemptId="other-exchange"
                ),
                "native-invocation-binding-mismatch",
            ),
            "changed-authority": (
                lambda request: request["native"].update(
                    authorityRefs=["synthetic://other-authority"]
                ),
                "original-authority-or-holds-mismatch",
            ),
            "changed-hold": (
                lambda request: request["native"].update(
                    holdRefs=["synthetic://other-hold"]
                ),
                "original-authority-or-holds-mismatch",
            ),
        }
        for name, (mutate, reason) in mutations.items():
            with self.subTest(name=name):
                exit_code, result, stream = self.consume(mutate_sender=mutate)
                self.assertEqual(exit_code, 0)
                self.assertEqual(result["reason"], reason)
                self.assertEqual(result["peer_input"], "not_attempted")
                self.assertEqual(result["owned_connection"], {"started": False, "closed": False})
                self.assertEqual(stream.writes, [])
                self.assertFalse(stream.closed)

    def test_every_nominated_peer_identity_field_refuses_before_protocol_writes(self):
        mutations = {
            "pid": lambda peer: peer.update(pid=peer["pid"] + 1),
            "uid": lambda peer: peer.update(uid=peer["uid"] + 1),
            "gid": lambda peer: peer.update(gid=peer["gid"] + 1),
            "start": lambda peer: peer.update(startTicks=peer["startTicks"] + 1),
            "boot": lambda peer: peer.update(bootId="other-boot"),
            "namespace": lambda peer: peer.update(networkNamespace="net:[999]"),
            "executable": lambda peer: peer["executable"].update(inode=999),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                exit_code, result, stream = self.consume(mutate)
                self.assertEqual(exit_code, 0)
                self.assertEqual(result["reason"], "connected-peer-mismatch")
                self.assertEqual(result["peer_input"], "not_attempted")
                self.assertEqual(stream.writes, [])
                self.assertEqual(stream.peer_identity_calls, 1)
                self.assertTrue(stream.closed)

    def test_peer_identity_change_after_owner_discovery_refuses_the_message_write(self):
        exit_code, result, stream = self.consume(
            change_after_discovery=lambda peer: peer.update(startTicks=peer["startTicks"] + 1)
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(result["reason"], "connected-peer-changed-before-message")
        self.assertEqual(result["peer_input"], "not_attempted")
        self.assertEqual(
            [frame["method"] for frame in stream.writes],
            ["initialize", "thread-owner-discovery"],
        )
        self.assertTrue(stream.closed)

if __name__ == "__main__":
    unittest.main()

