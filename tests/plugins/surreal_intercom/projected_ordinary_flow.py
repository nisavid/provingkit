"""Detached synthetic consumers of one standalone Intercom projection."""

import contextlib
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import sys
from types import SimpleNamespace
from unittest import mock


def write(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def invoke(main, argv, **kwargs):
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = main(argv, **kwargs)
    assert code == 0, output.getvalue()
    return json.loads(output.getvalue())


def capture(root):
    return {"run_root": str(root), "allowance_bytes": 8388608,
            "terminal_provision_bytes": 524288, "later_forecast_bytes": 0}


class Observation:
    """Primitive invented observations; no process or socket inspection."""

    def __init__(self, endpoint):
        self.uid = os.geteuid()
        self.clock = 1000
        self.links = {
            "/proc/100/exe": "/synthetic/python",
            "/proc/200/exe": "/synthetic/app-server",
            "/proc/300/exe": "/synthetic/Codex",
            "/proc/300/fd/11": "socket:[501]",
            **{f"/proc/{pid}/ns/net": "net:[701]" for pid in (100, 200, 300)},
        }
        self.files = {
            "/proc/sys/kernel/random/boot_id": b"synthetic-boot\n",
            "/proc/300/net/unix": (
                "Num RefCount Protocol Flags Type St Inode Path\n"
                f"00000000: 00000002 00000000 00010000 0001 01 501 {endpoint}\n"
            ).encode(),
        }
        for pid, parent, ticks in ((100, 200, 1001), (200, 300, 1002), (300, 1, 1003)):
            fields = ["S", str(parent), *("0" for _ in range(17)), str(ticks)]
            self.files[f"/proc/{pid}/stat"] = f"{pid} (fixture) {' '.join(fields)}\n".encode()
            self.files[f"/proc/{pid}/status"] = (
                f"Name:\tfixture\nUid:\t{self.uid}\t{self.uid}\t{self.uid}\t{self.uid}\n"
                f"Gid:\t{self.uid}\t{self.uid}\t{self.uid}\t{self.uid}\n"
            ).encode()
        self.nodes = {
            str(endpoint.parent): SimpleNamespace(
                st_mode=stat.S_IFDIR | 0o700, st_uid=self.uid, st_dev=9, st_ino=601),
            str(endpoint): SimpleNamespace(
                st_mode=stat.S_IFSOCK | 0o600, st_uid=self.uid, st_dev=9, st_ino=602),
        }

    def getpid(self):
        return 100

    def geteuid(self):
        return self.uid

    def monotonic_milliseconds(self):
        self.clock += 1
        return self.clock

    def read_bytes(self, path, maximum):
        value = self.files[str(path)]
        assert len(value) <= maximum
        return value

    def readlink(self, path, maximum):
        value = self.links[str(path)]
        assert len(value.encode()) <= maximum
        return value

    def listdir(self, path, maximum_entries):
        assert str(path) == "/proc/300/fd"
        assert maximum_entries >= 1
        return ["11"]

    def executable_identity(self, process_link, resolved_path):
        names = ("/synthetic/python", "/synthetic/app-server", "/synthetic/Codex")
        return {"path": resolved_path, "device": 8, "inode": 101 + names.index(resolved_path)}

    def lstat(self, path):
        return self.nodes[str(path)]


class Peer:
    """An in-memory framed peer, never a live endpoint."""

    def __init__(self, identity, attempt):
        self.identity = identity
        self.attempt = attempt
        self.frames = []
        self.responses = bytearray()
        self.closed = False

    def peer_identity(self):
        return self.identity

    def read(self, maximum, timeout):
        if not self.responses:
            raise TimeoutError
        data = bytes(self.responses[:maximum])
        del self.responses[:maximum]
        return data

    def write(self, data, timeout):
        size = struct.unpack("<I", data[:4])[0]
        frame = json.loads(data[4:4 + size])
        self.frames.append(frame)
        method = frame["method"]
        if method == "initialize":
            response = {"requestId": "initialize", "result": {"clientId": "synthetic-client"}}
        elif method == "thread-owner-discovery":
            response = {"requestId": "owner", "handledByClientId": "synthetic-owner"}
        else:
            assert method == "thread-follower-start-turn"
            response = {"requestId": self.attempt, "result": {}}
        response.update(type="response", resultType="success", method=method)
        body = json.dumps(response).encode()
        self.responses.extend(struct.pack("<I", len(body)) + body)

    def close(self):
        self.closed = True


def message(name, recipient):
    return {
        "message_id": f"message-{name}", "correlation_id": f"exchange-{name}",
        "sender": {"thread_id": f"origin-{name}", "host_id": "origin-host"},
        "recipient": recipient,
        "owner": {"thread_id": f"owner-{name}", "host_id": "owner-host"},
        "payload": f"Independent {name}.\r\nKeep é, café, and 雪.\n",
        "authority_ref": f"synthetic://authority/send-{name}",
        "holds": ["synthetic://original-hold"],
    }


def assert_envelope(envelope, original, actor):
    assert envelope == {"schema": "provingkit-peer-message-v1", **original, "actor": actor}


def codex_flow(root, modules):
    producer, sender, transport, mailbox = (modules[name] for name in (
        "codex_route_nomination", "owner_admission_sender", "codex_ipc_transport",
        "native_codex_mailbox"))
    recipient = {"thread_id": "codex-recipient", "host_id": "local"}
    actor = {"thread_id": "codex-submitter", "host_id": "local"}
    operation = "route-acquisition"
    invocation = {
        "control": "native-read-thread-command-execution", "taskRef": "synthetic://task",
        "attemptId": operation, "chat": recipient,
        "command": ["/synthetic/python", "-B", "/synthetic/codex_route_nomination.py",
                    "--request", "/synthetic/request.json"],
        "workingDirectory": "/synthetic/worktree",
        "helper": {"path": "/synthetic/codex_route_nomination.py", "sha256": "a" * 64},
    }
    permissions = {}
    for name, act, consumer in (
        ("metadata", "acquire-route-metadata", "nomination-controller"),
        ("nomination", "publish-route-nomination", "codex-route-nomination"),
        ("routeUse", "consume-route-nomination", "owner-admission-sender"),
    ):
        permissions[name] = {
            "evidenceRef": f"synthetic://authority/{name}",
            "issuer": {"thread_id": "operator", "host_id": "native"},
            "actor": actor if name == "routeUse" else recipient,
            "act": act, "chat": recipient, "operationId": operation,
            "validityRef": f"synthetic://validity/{name}",
            "revocationRef": f"synthetic://revocation/{name}", "consumer": consumer,
        }
    roles = []
    for index, (role, discriminator, executable) in enumerate((
        ("helper", "invoked-helper", "python"),
        ("app-server", "direct-parent-app-server", "app-server"),
        ("desktop-main", "direct-parent-desktop-main", "Codex"),
    )):
        roles.append({"role": role, "discriminator": discriminator,
                      "evidenceRef": f"synthetic://source/{role}",
                      "executable": {"path": f"/synthetic/{executable}",
                                     "device": 8, "inode": 101 + index}})
    request = {
        "schema": "codex-route-nomination-request-v2", "recipient": recipient,
        "producer": recipient, "submitter": actor, "operationId": operation,
        "invocation": invocation, "permissions": permissions,
        "acquisitionHolds": ["synthetic://original-hold"],
        "selection": {"launchSourceRef": "synthetic://launch",
                      "listenerSourceRef": "synthetic://listener", "roles": roles,
                      "routeForm": "direct-primary"},
        "publication": {"path": str(root / "nomination.json"),
                        "ownerUid": os.geteuid(), "capture": capture(root)},
    }
    publication = invoke(producer.main, ["--request", str(write(root / "produce.json", request))],
                         observer=Observation(root / "codex-home/ipc/ipc.sock"))
    assert publication["published"] is True, publication
    assert publication["closure"] == "no-connection-opened"
    nomination_path = Path(publication["path"])
    nomination_bytes = nomination_path.read_bytes()
    assert len(nomination_bytes) == publication["bytes"]
    assert hashlib.sha256(nomination_bytes).hexdigest() == publication["sha256"]
    nomination = json.loads(nomination_bytes)
    assert nomination["schema"] == "codex-route-nomination-v2"
    assert nomination["producer"] == recipient and nomination["submitter"] == actor
    store = root / "mailbox.sqlite3"
    invoke(mailbox.main, ["--store", str(store), "init"])
    results = {}
    for name in ("a", "b"):
        original = message(name, recipient)
        attempt = f"attempt-{name}"
        invoke(mailbox.main, ["--store", str(store), "plan", "--input",
                              str(write(root / f"message-{name}.json", original))])
        run = root / f"send-{name}"
        run.mkdir(mode=0o700)
        send_request = {
            "message_id": original["message_id"], "attempt_id": attempt,
            "actor": actor, "recipient": recipient, "evidence_ref": f"synthetic://send/{name}",
            "native": {
                "nomination": {"path": str(nomination_path), "sha256": publication["sha256"],
                               "size": publication["bytes"],
                               "invocation": {**invocation, "evidenceRef": "synthetic://completed",
                                              "nativeItemId": "item-1", "status": "completed",
                                              "exitCode": 0}},
                "purpose": "Forward the original peer message",
                "authorityRefs": [original["authority_ref"]], "holdRefs": original["holds"],
                "scope": {"send": True, "ownerAdmissionIntent": True, "holdsSatisfied": True},
                "profile": {}, "observationSeconds": 0.1,
            },
            "capture": capture(run),
        }
        peer = Peer(nomination["acceptor"], attempt)

        def connect(endpoint, limits, wait):
            assert endpoint == str(root / "codex-home/ipc/ipc.sock")
            return transport.CliTransport(endpoint, limits, wait,
                                          connector=lambda _endpoint, _wait: peer)

        with mock.patch.object(sender, "CliTransport", connect):
            result = invoke(sender.main, ["--store", str(store), "--request",
                                          str(write(root / f"send-{name}.json", send_request))],
                            clock=lambda: 7005)
        assert result["claimed"] is True, result
        assert result["reason"] == "rpc-success-effect-unconfirmed", result
        assert result["peer_input"] == "possible_submission"
        assert result["receipt"] == "unknown" and result["native_branch"] == "unknown"
        assert result["owned_connection"] == {"started": True, "closed": True}
        assert peer.closed
        assert [frame["method"] for frame in peer.frames] == [
            "initialize", "thread-owner-discovery", "thread-follower-start-turn"]
        payload = peer.frames[-1]["params"]["turnStart"]["request"]["input"][0]["text"]
        assert_envelope(json.loads(payload.split("\n", 1)[1]), original, actor)
        retained = invoke(mailbox.main, ["--store", str(store), "show", original["message_id"]])
        assert {key: retained[key] for key in original} == original
        assert retained["state"] == "unknown"
        assert len(retained["attempts"]) == 1
        owned = retained["attempts"][0]
        assert owned["attempt_id"] == attempt and owned["actor"] == actor
        assert not any(owned[stage] for stage in ("received", "handled", "completed"))
        assert nomination_path.read_bytes() == nomination_bytes
        results[name] = {"result": result, "retained": retained}
    return results


MCP_CHILD = '''import json
import sys
from pathlib import Path

assert sys.argv[1:] == ["mcp", "serve"], sys.argv
trace = Path(__file__).with_name("child.jsonl")
with trace.open("w", encoding="utf-8") as output:
    for line in sys.stdin:
        request = json.loads(line)
        output.write(json.dumps(request) + "\\n")
        output.flush()
        method = request["method"]
        if method == "notifications/initialized":
            continue
        if method == "initialize":
            result = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}}
        elif method == "tools/list":
            result = {"tools": [{"name": "SendMessage", "inputSchema": {
                "type": "object", "properties": {
                    "to": {"type": "string"}, "message": {"type": "string"}},
                "required": ["to", "message"], "additionalProperties": False}}]}
        else:
            assert method == "tools/call"
            result = {"content": [{"type": "text", "text": "Synthetic submission."}], "isError": False}
        print(json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": result}), flush=True)
    output.write(json.dumps({"stdin_eof": True}) + "\\n")
raise SystemExit(23)
'''


def claude_flow(root, modules, scripts):
    route, mailbox = (modules[name] for name in ("claude_route_nomination", "native_codex_mailbox"))
    launcher = root / "claude"
    launcher.write_text(f"#!{sys.executable}\n" + MCP_CHILD, encoding="utf-8")
    launcher.chmod(0o700)
    recipient = {"thread_id": "claude-recipient", "host_id": "local"}
    publication = invoke(route.main, ["nominate", "--request", str(write(root / "produce.json", {
        "schema": "claude-route-nomination-request-v1", "recipient": recipient,
        "producer": recipient, "publication": {"path": str(root / "nomination.json"),
                                                "ownerUid": os.geteuid(), "capture": capture(root)},
    }))], environment={"CLAUDE_CODE_HOST_SESSION_ID": recipient["thread_id"],
                      "CLAUDE_CODE_MESSAGING_SOCKET": "/synthetic/receiver/messaging.sock",
                      "PATH": str(root)}, launcher_lookup=lambda _name, _path: str(launcher))
    assert publication["published"] is True, publication
    assert publication["closure"] == "no-provider-started"
    raw = Path(publication["path"]).read_bytes()
    assert publication["bytes"] == len(raw)
    assert publication["sha256"] == hashlib.sha256(raw).hexdigest()
    nominated = json.loads(raw)
    assert nominated["recipient"] == recipient and nominated["producer"] == recipient
    assert nominated["launch"]["command"] == [str(launcher), "mcp", "serve"]
    original = message("claude", recipient)
    actor = {"thread_id": "claude-submitter", "host_id": "local"}
    store = root / "mailbox.sqlite3"
    prepared = invoke(route.main, ["prepare", "--request", str(write(root / "prepare.json", {
        "schema": "claude-sender-request-preparation-v1",
        "nomination": {key: publication[key] for key in ("path", "bytes", "sha256")},
        "message": original, "attempt_id": "attempt-claude", "actor": actor,
        "limits": {"operation_seconds": 8, "stdout_bytes": 65536, "stderr_bytes": 65536},
        "mailbox": str(store), "publication": {"path": str(root / "sender.json"),
                                                "ownerUid": os.geteuid(), "capture": capture(root)},
    }))])
    assert prepared["prepared"] is True, prepared
    request_path = Path(prepared["path"])
    request_bytes = request_path.read_bytes()
    assert prepared["bytes"] == len(request_bytes)
    assert prepared["sha256"] == hashlib.sha256(request_bytes).hexdigest()
    assert json.loads(request_bytes)["command"] == [str(launcher), "mcp", "serve"]
    bootstrap = (
        "import pathlib,sys; scripts=pathlib.Path(sys.argv[1]); "
        "sys.path.insert(0,str(scripts)); import claude_mcp_sender; "
        "assert pathlib.Path(claude_mcp_sender.__file__).resolve().parent == scripts; "
        "sys.argv=['claude_mcp_sender.py',*sys.argv[2:]]; "
        "raise SystemExit(claude_mcp_sender.main())"
    )
    completed = subprocess.run([
        sys.executable, "-I", "-S", "-B", "-c", bootstrap, str(scripts),
        "--store", str(store), "--request", str(request_path),
    ], capture_output=True, text=True, timeout=12)
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["claimed"] is True and result["reason"] == "submitted", result
    assert result["stage"] == "call" and result["peer_input"] == "submitted"
    assert result["owned_child"] == {"started": True, "reaped": True, "exit_code": 23}
    records = [json.loads(line) for line in (root / "child.jsonl").read_text().splitlines()]
    assert [record["method"] for record in records[:-1]] == [
        "initialize", "notifications/initialized", "tools/list", "tools/call"]
    assert records[-1] == {"stdin_eof": True}
    call = records[-2]["params"]
    assert call["name"] == "SendMessage"
    assert call["arguments"]["to"] == "uds:/synthetic/receiver/messaging.sock"
    assert_envelope(json.loads(call["arguments"]["message"].split("\n", 1)[1]), original, actor)
    retained = invoke(mailbox.main, ["--store", str(store), "show", original["message_id"]])
    assert {key: retained[key] for key in original} == original
    assert retained["state"] == "submitted" and len(retained["attempts"]) == 1
    attempt = retained["attempts"][0]
    assert attempt["attempt_id"] == "attempt-claude" and attempt["actor"] == actor
    assert not any(attempt[stage] for stage in ("received", "handled", "completed"))
    assert request_path.read_bytes() == request_bytes
    assert Path(publication["path"]).read_bytes() == raw
    return {"result": result, "retained": retained}


def main():
    plugin, root = (Path(argument).resolve() for argument in sys.argv[1:])
    scripts = plugin / "skills/communicating-with-agents/scripts"
    names = ("codex_route_nomination", "owner_admission_sender", "codex_ipc_transport",
             "native_codex_mailbox", "claude_route_nomination", "claude_mcp_sender")
    assert not any(name in sys.modules for name in names)
    sys.path.insert(0, str(scripts))
    modules = {name: importlib.import_module(name) for name in names}
    origins = {}
    for name, module in tuple(sys.modules.items()):
        location = getattr(module, "__file__", None)
        if location and Path(location).name in {path.name for path in scripts.glob("*.py")}:
            path = Path(location).resolve()
            assert path.is_relative_to(scripts), (name, str(path))
            origins[name] = str(path)
    assert set(names) <= origins.keys()
    codex = root / "codex"
    claude = root / "claude"
    codex.mkdir(mode=0o700)
    claude.mkdir(mode=0o700)
    print(json.dumps({"origins": origins, "codex": codex_flow(codex, modules),
                      "claude": claude_flow(claude, modules, scripts)}, sort_keys=True))


if __name__ == "__main__":
    main()
