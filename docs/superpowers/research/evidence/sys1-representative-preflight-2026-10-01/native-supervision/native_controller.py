"""Serialized native transport for one or three ordinary task turns."""

import hashlib
import json
import os
import time
import uuid
from pathlib import Path

from native_support import (CLAUDE_TOOLS, MODELS, SYSTEM_PROMPT, VERSIONS,
                            codex_common, discover_codex_hooks, require,
                            verify_claude_init, verify_codex_sandbox)
from hook_receipts import HookReceipts
from profile_inventory import capture_inventory, verify_sources
from observer import stamp
from artifact_checks import capture
from transport import collect, encoded, put


SCHEMA = "sys1-supervision-native/v1"


def atomic_record(path, value):
    temporary = path.parent / ("." + path.name + "." + uuid.uuid4().hex)
    try:
        put(temporary, encoded(value))
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def record(root, category, index, value):
    atomic_record(root / "private" / category / f"{index:03d}.json", value)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_version(harness, manifest, project, root, deadline):
    output, code = collect([harness, "--version"], project, root, "version",
                           min(deadline, time.monotonic() + 10))
    require(code == 0 and output.decode().strip() == manifest["version"],
            "native CLI version differs")


def codex_catalog(project, root, deadline):
    output, code = collect(["codex", "debug", "models"], project, root, "catalog",
                           min(deadline, time.monotonic() + 30))
    require(code == 0, "Codex model catalog failed")
    models = [item for item in json.loads(output).get("models", [])
              if item.get("slug") == MODELS["codex"]]
    require(len(models) == 1 and any(item.get("effort") == "medium"
            for item in models[0].get("supported_reasoning_levels", [])),
            "Codex medium catalog differs")


def checked(manifest, root):
    require(manifest.get("schema") == SCHEMA, "supervision manifest schema differs")
    harness = manifest.get("harness")
    require(harness in MODELS and manifest.get("version") == VERSIONS[harness]
            and manifest.get("model") == MODELS[harness]
            and manifest.get("effort") == "medium", "native selection differs")
    project, sibling = Path(manifest["project"]), Path(manifest["sibling"])
    require(root.is_absolute() and root.resolve() == root
            and project == root / "project" and sibling == root / "sibling"
            and project.is_dir() and sibling.is_dir()
            and project.resolve() == project and sibling.resolve() == sibling
            and not any(sibling.iterdir()),
            "ordinary task roots or empty compatibility sibling differ")
    if harness == "codex":
        temporary = project / ".runner-tmp"
        require(temporary.is_dir() and temporary.resolve() == temporary
                and not any(temporary.iterdir()), "prepared shell temporary directory differs")
    prompts = manifest.get("prompts")
    require(isinstance(prompts, list) and len(prompts) in (1, 3)
            and all(isinstance(text, str) and text.strip()
                    and 0 < len(text.encode()) <= 16384
                    for text in prompts), "ordinary prompts unavailable")
    limit = manifest.get("deadline_seconds")
    require(type(limit) is int and 0 < limit <= 1800, "native deadline differs")
    settings = Path(manifest["settings_path"])
    expected = root / "settings.json" if harness == "claude" else project / ".codex" / "hooks.json"
    require(settings == expected and digest(settings) == manifest["settings_sha256"],
            "native settings drift")
    require(digest(root / "hook-config.json") == manifest["hook_config_sha256"],
            "hook config drift")
    require(manifest.get("max_native_tool_calls") == 40, "native observation cap differs")
    expected_files = manifest.get("initial_project_sha256")
    actual_files = {str(path.relative_to(project)): digest(path) for path in project.rglob("*")
                    if path.is_file() and ".git" not in path.relative_to(project).parts}
    require(isinstance(expected_files, dict) and actual_files == expected_files
            and not any(path.is_symlink() for path in project.rglob("*")), "initial fixture drift")
    sources = manifest.get("source_sha256")
    require(isinstance(sources, dict) and sources
            and all(digest(Path(path)) == value for path, value in sources.items()),
            "source drift")
    private = root / "private"
    require(not (private / "native-readiness.json").exists()
            and all((private / name).is_dir()
                    and not any((private / name).iterdir())
                    for name in ("deliveries", "acknowledgments")),
            "controller records already exist or directories are missing")
    if harness == "claude":
        session = manifest.get("claude_session_id")
        require(isinstance(session, str) and uuid.UUID(session).version == 4,
                "Claude prebound session differs")
    return harness, project, sibling, prompts, limit


def observation(root, state, code):
    raw_path = root / "native-stdout.log"
    raw = raw_path.read_bytes()
    process = json.loads((root / "native-process.json").read_text())
    offset = process.get("terminal_callback_stdout_offset")
    require(type(offset) is int and 0 < offset <= len(raw)
            and raw[offset - 1:offset] == b"\n",
            "terminal callback boundary unavailable")
    return {"status": "incomplete" if state["incomplete"] else "observed",
            "incomplete_reason": state["incomplete"],
            "session_id": state["session"], "turns_completed": len(state["results"]),
            "native_results": state["results"],
            "raw_stdout_path": str(raw_path),
            "raw_stdout_sha256": hashlib.sha256(raw).hexdigest(),
            "callback_stdout_offset": offset,
            "callback_stdout_sha256": hashlib.sha256(raw[:offset]).hexdigest(),
            "undelivered_stdout_path": str(root / "native-undelivered-stdout.log"),
            "native_process_exit_code": code,
            "native_process_shutdown": "transport terminated process group after completion callback"}


def run_claude(manifest, root, project, sibling, prompts, deadline):
    session = manifest["claude_session_id"]
    hooks = HookReceipts("claude", manifest["settings_path"])
    command = ["claude", "-p", "--restricted", "--tools", ",".join(CLAUDE_TOOLS),
               "--setting-sources", "", "--settings", str(root / "settings.json"),
               "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
               "--disable-slash-commands", "--permission-mode", "auto",
               "--permission-prompts", "none",
               "--model", MODELS["claude"], "--effort", "medium",
               "--session-id", session, "--input-format", "stream-json",
               "--output-format", "stream-json", "--replay-user-messages",
               "--include-hook-events", "--verbose",
               "--system-prompt", SYSTEM_PROMPT]
    state = {"session": session, "control": False, "init": False, "index": 0,
             "sent": False, "ack": False, "envelope": None, "results": [],
             "incomplete": None, "tool_ids": set(), "tool_results": set(),
             "initialized_turns": set(), "tool_calls_observed": 0}

    def send_turn(send):
        index = state["index"]
        envelope = {"type": "user", "uuid": str(uuid.uuid4()), "session_id": "",
                    "parent_tool_use_id": None,
                    "message": {"role": "user", "content": prompts[index]}}
        record(root, "deliveries", index,
               {"schema": "sys1-native-delivery/v1", "harness": "claude",
                "session_id": session, "sequence": index, "text": prompts[index],
                "native_uuid": envelope["uuid"], "envelope": envelope,
                "sent_before": stamp()})
        state["envelope"], state["sent"], state["ack"] = envelope, True, False
        send(envelope)

    def maybe_first(send):
        if state["control"] and not state["sent"]:
            send_turn(send)

    def begin(send):
        send({"type": "control_request", "request_id": "sys1-supervision-initialize",
              "request": {"subtype": "initialize"}})

    def receive(event, send):
        require(not (root / "private/observer-failure.json").exists(), "passive observer unavailable")
        if hooks.receive(event, session):
            return False
        kind = event.get("type")
        if kind == "control_request":
            raise RuntimeError("native permission/control request requires adjudication")
        if kind == "control_response":
            response = event.get("response", {})
            require(response.get("request_id") == "sys1-supervision-initialize"
                    and response.get("subtype") == "success" and not state["control"],
                    "Claude control initialization differs")
            matches = [row for row in response.get("response", {}).get("models", [])
                       if row.get("value") == "opus"]
            require(len(matches) == 1
                    and matches[0].get("resolvedModel") == MODELS["claude"]
                    and "medium" in matches[0].get("supportedEffortLevels", []),
                    "Claude Opus/medium catalog differs")
            state["control"] = True
            maybe_first(send)
        elif kind == "system" and event.get("subtype") == "init":
            require(state["sent"] and state["index"] not in state["initialized_turns"]
                    and len(state["results"]) == state["index"], "duplicate or out-of-order Claude init")
            verify_claude_init(manifest, event)
            if not state["init"]:
                atomic_record(root / "private" / "native-readiness.json",
                              {"schema": "sys1-native-readiness/v1", "harness": "claude",
                               "session_id": session, "transcript_path": None,
                               "verified": True, "verified_at": stamp()})
            state["init"] = True
            state["initialized_turns"].add(state["index"])
            maybe_first(send)
        elif kind == "assistant":
            require(state["sent"] and event.get("session_id") == session,
                    "Claude assistant session differs")
            for part in event.get("message", {}).get("content", []):
                if isinstance(part, dict) and part.get("type") == "tool_use":
                    tool_id = part.get("id")
                    require(isinstance(tool_id, str) and tool_id
                            and tool_id not in state["tool_ids"],
                            "Claude tool identity differs")
                    state["tool_ids"].add(tool_id)
                    state["tool_calls_observed"] += 1
                    require(state["tool_calls_observed"] <= manifest["max_native_tool_calls"],
                            "observed native tool-call bound exceeded")
        elif kind == "user" and event.get("isReplay") is True:
            envelope = state["envelope"]
            require(state["sent"] and not state["ack"]
                    and event.get("uuid") == envelope["uuid"]
                    and event.get("message") == envelope["message"]
                    and event.get("session_id") == session,
                    "Claude replay acknowledgment differs")
            index = state["index"]
            record(root, "acknowledgments", index,
                   {"schema": "sys1-native-acknowledgment/v1", "harness": "claude",
                    "session_id": session, "sequence": index, "native_uuid": event["uuid"],
                    "message": event["message"], "observed_at": stamp()})
            state["ack"] = True
        elif kind == "user":
            payload = event.get("message", {})
            content = payload.get("content")
            require(state["ack"] and event.get("session_id") == session
                    and payload.get("role") == "user"
                    and isinstance(content, list) and content
                    and all(isinstance(part, dict) and part.get("type") == "tool_result"
                            for part in content), "Claude unbound user envelope")
            for part in content:
                tool_id = part.get("tool_use_id")
                require(isinstance(tool_id, str) and tool_id in state["tool_ids"]
                        and tool_id not in state["tool_results"],
                        "Claude unbound tool result")
                state["tool_results"].add(tool_id)
        elif kind == "result":
            require(state["sent"] and state["init"] and state["ack"]
                    and state["index"] in state["initialized_turns"]
                    and state["tool_ids"] == state["tool_results"]
                    and event.get("session_id") == session
                    and event.get("is_error") is False,
                    "Claude native result differs")
            index = state["index"]
            atomic_record(root / "private" / f"artifacts-{index:03d}.json", capture(project))
            state["results"].append(event)
            atomic_record(root / "private" / f"hook-agreement-{index:03d}.json",
                          hooks.reconcile(root, session, index + 1))
            if index == len(prompts) - 1:
                return True
            state["index"], state["sent"] = index + 1, False
            state["tool_ids"], state["tool_results"] = set(), set()
            send_turn(send)
        return False

    _, code = collect(command, project, root, "native", deadline,
                      on_line=receive, begin=begin)
    result = observation(root, state, code)
    result["harness"] = "claude"
    return result


def verify_history(result, ids, prompts):
    turns = result.get("data")
    require(result.get("nextCursor") is None and isinstance(turns, list)
            and [turn.get("id") for turn in turns] == ids,
            "Codex full history IDs/order differ")
    for index, turn in enumerate(turns):
        require(turn.get("status") == "completed" and turn.get("error") is None
                and turn.get("itemsView") == "full",
                "Codex history turn incomplete")
        users = [item for item in turn.get("items", [])
                 if item.get("type") == "userMessage"]
        require(len(users) == 1 and users[0].get("content") ==
                [{"type": "text", "text": prompts[index], "text_elements": []}],
                "Codex native user content differs")
    return turns


def run_codex(manifest, root, project, sibling, prompts, deadline):
    codex_catalog(project, root, deadline)
    hooks = HookReceipts("codex", manifest["settings_path"])
    def within_deadline(command, cwd, attempt, label, requested, **callbacks):
        return collect(command, cwd, attempt, label, min(deadline, requested),
                       **callbacks)
    override = discover_codex_hooks(manifest, root, within_deadline)
    command = codex_common(manifest, project, override)
    state = {"phase": "initialize", "session": None, "path": None,
             "index": 0, "ids": [], "results": [], "incomplete": None,
             "settings": [], "usage_notifications": [], "tool_item_ids": set(), "profile": None}

    def send_turn(send):
        verify_sources(state["profile"])
        index = state["index"]
        request = {"id": 100 + index, "method": "turn/start",
                   "params": {"threadId": state["session"],
                              "input": [{"type": "text", "text": prompts[index],
                                         "text_elements": []}],
                              "model": MODELS["codex"], "effort": "medium",
                              "approvalPolicy": "on-request",
                              "approvalsReviewer": "user",
                              "cwd": str(project), "sandboxPolicy": {
                                  "type": "workspaceWrite",
                                  "writableRoots": [],
                                  "networkAccess": False,
                                  "excludeTmpdirEnvVar": True, "excludeSlashTmp": True}}}
        record(root, "deliveries", index,
               {"schema": "sys1-native-delivery/v1", "harness": "codex",
                "session_id": state["session"], "sequence": index,
                "text": prompts[index], "request": request,
                "sent_before": stamp()})
        state["phase"] = "turn-start"
        send(request)

    def begin(send):
        send({"id": 1, "method": "initialize",
              "params": {"clientInfo": {"name": "sys1-supervision", "version": "1"}}})

    def receive(message, send):
        require(not (root / "private/observer-failure.json").exists(), "passive observer unavailable")
        if hooks.receive(message, state["session"]):
            return False
        method, ident = message.get("method"), message.get("id")
        if method == "item/started":
            params = message.get("params", {})
            item = params.get("item", {})
            if item.get("type") in {"commandExecution", "fileChange"}:
                require(params.get("threadId") == state["session"], "native item session differs")
                state["tool_item_ids"].add(item.get("id"))
                require(len(state["tool_item_ids"]) <= manifest["max_native_tool_calls"],
                        "observed native tool-call bound exceeded")
        if method == "thread/settings/updated":
            params = message.get("params", {})
            settings = params.get("threadSettings", {})
            require(params.get("threadId") == state["session"]
                    and settings.get("model") == MODELS["codex"]
                    and settings.get("effort") == "medium"
                    and settings.get("approvalPolicy") == "on-request"
                    and settings.get("approvalsReviewer") == "user",
                    "Codex effective settings differ")
            verify_codex_sandbox(settings, project, "settings")
            state["settings"].append(message)
            return False
        if method == "thread/tokenUsage/updated":
            state["usage_notifications"].append(message)
            return False
        if method is not None and ident is not None:
            raise RuntimeError("native permission/server request requires adjudication")
        if ident == 1:
            require(state["phase"] == "initialize" and "result" in message,
                    "Codex initialize differs")
            state["phase"] = "thread-start"
            send({"method": "initialized"})
            send({"id": 2, "method": "thread/start",
                  "params": {"model": MODELS["codex"], "cwd": str(project),
                             "approvalPolicy": "on-request",
                             "approvalsReviewer": "user",
                             "sandbox": "workspace-write", "ephemeral": False,
                             "config": {"sandbox_workspace_write": {
                                 "writable_roots": [],
                                 "network_access": False,
                                 "exclude_tmpdir_env_var": True, "exclude_slash_tmp": True}}}})
        elif ident == 2:
            require(state["phase"] == "thread-start" and "result" in message,
                    "Codex thread/start failed")
            response = message["result"]
            thread = response["thread"]
            require(thread.get("cliVersion") == VERSIONS["codex"].removeprefix("codex-cli ")
                    and thread.get("ephemeral") is False
                    and thread.get("turns") == []
                    and response.get("model") == MODELS["codex"]
                    and response.get("reasoningEffort") == "medium"
                    and response.get("cwd") == str(project)
                    and response.get("approvalPolicy") == "on-request"
                    and response.get("approvalsReviewer") == "user",
                    "Codex fresh thread/settings differ")
            verify_codex_sandbox(response, project, "thread-start")
            session = thread.get("id")
            path = Path(thread.get("path") or "")
            storage = Path(manifest["storage_root"])
            require(isinstance(session, str) and session
                    and path.is_absolute() and path.parent.resolve() == path.parent
                    and path.is_relative_to(storage)
                    and len(path.parent.relative_to(storage).parts) == 3
                    and path.name.endswith("-" + session + ".jsonl"),
                    "Codex native session/transcript identity differs")
            state["session"], state["path"] = session, str(path)
            state["phase"] = "connectors"
            send({"id": 3, "method": "mcpServerStatus/list",
                  "params": {"threadId": session, "limit": 100}})
        elif ident == 3:
            require(state["phase"] == "connectors" and "result" in message,
                    "Codex connector inventory unavailable")
            result = message["result"]
            require(result.get("nextCursor") is None
                    and isinstance(result.get("data"), list)
                    and all(item.get("runtimeStatus") == "disabled"
                            and item.get("tools") == {}
                            and item.get("resources") == []
                            and item.get("resourceTemplates") == []
                            for item in result["data"]),
                    "Codex inherited connector active")
            state["phase"] = "skills"
            send({"id": 4, "method": "skills/list",
                  "params": {"cwds": [str(project)], "forceReload": True}})
        elif ident == 4:
            require(state["phase"] == "skills" and "result" in message,
                    "Codex skill inventory unavailable")
            state["profile"] = capture_inventory(message["result"], project)
            atomic_record(root / "private" / "profile-inventory.json", state["profile"])
            atomic_record(root / "private" / "native-readiness.json",
                          {"schema": "sys1-native-readiness/v1",
                           "harness": "codex", "session_id": state["session"],
                           "transcript_path": state["path"], "verified": True,
                           "verified_at": stamp()})
            send_turn(send)
        elif ident == 100 + state["index"]:
            require(state["phase"] == "turn-start" and "result" in message,
                    "Codex turn/start failed")
            turn_id = message["result"]["turn"]["id"]
            require(isinstance(turn_id, str) and turn_id
                    and turn_id not in state["ids"],
                    "Codex native turn ID differs")
            state["ids"].append(turn_id)
            index = state["index"]
            record(root, "acknowledgments", index,
                   {"schema": "sys1-native-acknowledgment/v1",
                    "harness": "codex", "session_id": state["session"],
                    "sequence": index, "turn_id": turn_id,
                    "observed_at": stamp()})
            state["phase"] = "running"
        elif method == "turn/completed":
            params = message.get("params", {})
            turn = params.get("turn", {})
            require(state["phase"] == "running"
                    and params.get("threadId") == state["session"]
                    and turn.get("id") == state["ids"][-1]
                    and turn.get("status") == "completed"
                    and turn.get("error") is None,
                    "Codex native turn completion differs")
            state["phase"] = "history"
            index = state["index"]
            send({"id": 200 + index, "method": "thread/turns/list",
                  "params": {"threadId": state["session"], "limit": 20,
                             "sortDirection": "asc", "itemsView": "full"}})
        elif ident == 200 + state["index"]:
            require(state["phase"] == "history" and "result" in message,
                    "Codex full history unavailable")
            turns = verify_history(message["result"], state["ids"], prompts)
            state["results"] = turns
            index = state["index"]
            atomic_record(root / "private" / f"artifacts-{index:03d}.json", capture(project))
            atomic_record(root / "private" / f"hook-agreement-{index:03d}.json",
                          hooks.reconcile(root, state["session"], index + 1))
            if index == len(prompts) - 1:
                verify_sources(state["profile"])
                return True
            state["index"] = index + 1
            send_turn(send)
        elif ident is not None:
            raise RuntimeError("unexpected Codex response ID")
        return False

    _, code = collect(command, project, root, "native", deadline,
                      on_line=receive, begin=begin)
    result = observation(root, state, code)
    result.update(harness="codex", transcript_path=state["path"],
                  turn_ids=state["ids"], settings_updates=state["settings"],
                  usage_notifications=state["usage_notifications"])
    return result


def run(manifest, root):
    """Run one externally reserved episode; preserve observations without policy labels."""
    root = Path(root)
    harness, project, sibling, prompts, seconds = checked(manifest, root)
    deadline = time.monotonic() + seconds
    check_version(harness, manifest, project, root, deadline)
    if harness == "claude":
        return run_claude(manifest, root, project, sibling, prompts, deadline)
    return run_codex(manifest, root, project, sibling, prompts, deadline)
