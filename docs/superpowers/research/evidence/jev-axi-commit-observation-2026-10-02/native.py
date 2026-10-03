"""One accepted native authoring turn, retaining transport and child histories.

Permission and user-input requests are observations that stop this run. The
controller never answers them, supplies additional task input, or retries.
"""

import hashlib
import json
from pathlib import Path
import subprocess
import time

from profile import MODEL, EFFORT, command, skills_identity, verify_profile
from git_state import snapshot
from transport import collect, encoded, put

TOOL_ITEMS = {"commandExecution", "fileChange", "mcpToolCall", "dynamicToolCall",
              "collabAgentToolCall", "webSearch", "imageView", "sleep", "imageGeneration"}


def require(value, message):
    if not value:
        raise ValueError(message)


def sandbox(record, project, key="sandbox"):
    policy = record.get(key, {})
    require(policy.get("type") == "workspaceWrite"
            and policy.get("writableRoots", []) in ([], [str(project)])
            and policy.get("networkAccess", False) is False
            and policy.get("excludeTmpdirEnvVar") is True
            and policy.get("excludeSlashTmp") is True,
            "effective native sandbox differs")


def git_evidence(project, baseline):
    deadline = time.monotonic() + 10
    def remaining():
        seconds = deadline - time.monotonic()
        require(seconds > 0, "final Git capture deadline exceeded")
        return min(seconds, 5)
    def git(*args):
        return subprocess.run(["git", *args], cwd=project, check=True,
                              capture_output=True, timeout=remaining()).stdout
    commits = git("rev-list", "--reverse", baseline + "..HEAD").decode().splitlines()
    require(len(commits) <= 20, "commit observation count exceeded")
    records = []
    for directory in sorted((project / ".observation/records").iterdir()):
        remaining()
        record = {"directory": directory.name, "valid": False, "metadata": {},
                  "retained_files": {}}
        records.append(record)
        try:
            require(directory.is_dir() and not directory.is_symlink(), "unexpected observer entry")
            for path in sorted(directory.iterdir()):
                require(path.is_file() and not path.is_symlink(), "unexpected observer artifact")
                raw = path.read_bytes()
                record["retained_files"][path.name] = {"bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest()}
            data = json.loads((directory / "record.json").read_text())
            record["metadata"] = data
            require(data.get("status") == "captured", "incomplete observer record")
            require(set(data.get("artifacts", {})) == {"message.bin", "staged.patch"},
                    "missing observer artifacts")
            require(all(record["retained_files"].get(name) == artifact
                        for name, artifact in data["artifacts"].items()),
                    "observer artifact identity differs")
            record["valid"] = True
        except Exception as error:
            record["error"] = type(error).__name__ + ": " + str(error)
    details = []
    for commit in commits:
        tree = git("rev-parse", commit + "^{tree}").decode().strip()
        parents = git("show", "-s", "--format=%P", commit).decode().strip().split()
        matches = [r["directory"] for r in records if r["valid"]
                   and r["metadata"].get("index_tree") == tree
                   and parents == [r["metadata"].get("parent")]]
        details.append({"commit": commit, "tree": tree, "parents": parents,
                        "message": git("show", "-s", "--format=%B", commit).decode(),
                        "matching_observations": matches})
    files = {}
    for path in project.rglob("*"):
        remaining()
        relative = path.relative_to(project)
        if any(part in {".git", ".observation", ".runner-tmp", "__pycache__"} for part in relative.parts):
            continue
        require(not path.is_symlink(), "unexpected fixture symlink")
        if path.is_file():
            files[str(relative)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"commits": details, "observations": records, "final_files": files,
            "status_porcelain": git("status", "--porcelain").decode(),
            "git_boundary": ("unqualified" if any(not r["valid"] for r in records) else
                             "unobserved" if not details else
                             "matched" if all(x["matching_observations"] for x in details) else
                             "unqualified")}


def run(manifest):
    root, project = Path(manifest["root"]), Path(manifest["project"])
    profile_bytes = (root / "profile.json").read_bytes()
    require(hashlib.sha256(profile_bytes).hexdigest() == manifest["profile_sha256"],
            "prepared profile identity differs")
    profile = json.loads(profile_bytes)
    verify_profile(profile)
    native_command = command(project)
    require(native_command == profile["native_command"], "native command or environment drift")
    version = subprocess.run(["codex", "--version"], capture_output=True, text=True,
                             check=True, timeout=10).stdout.strip()
    require(version == profile["version"], "native version drift")
    deadline = time.monotonic() + manifest["native_deadline_seconds"]
    state = {"thread": None, "turn": None, "usage": [], "children": [],
             "tools": set(), "spawns": set(), "histories": {}, "pending": [],
             "metadata": {}, "settings": []}

    def begin(send):
        send({"id": 1, "method": "initialize", "params": {
            "clientInfo": {"name": "passive-commit-observation", "version": "1"}}})

    def read_next(send):
        if not state["pending"]:
            return True
        target = state["pending"][0]
        send({"id": 10, "method": "thread/read", "params": {
            "threadId": target, "includeTurns": False}})
        return False

    def receive(message, send):
        method, ident = message.get("method"), message.get("id")
        if method is not None and ident is not None:
            put(root / "native-unanswered-request.json", encoded(message))
            raise ValueError("native permission or user input requires adjudication")
        if method == "thread/tokenUsage/updated":
            state["usage"].append(message["params"])
        if method == "thread/settings/updated":
            data = message["params"]
            if data.get("threadId") == state["thread"]:
                settings = data["threadSettings"]
                require(settings.get("model") == MODEL and settings.get("effort") == EFFORT
                        and settings.get("approvalPolicy") == "on-request"
                        and settings.get("approvalsReviewer") == "user",
                        "native turn settings differ")
                sandbox(settings, project, "sandboxPolicy")
                state["settings"].append(settings)
        if method in {"item/started", "item/completed"}:
            data = message["params"]
            item = data.get("item", {})
            if item.get("type") in TOOL_ITEMS:
                state["tools"].add((data.get("threadId"), item.get("id")))
                require(len(state["tools"]) <= manifest["maximum_tool_calls"],
                        "observed tool-call limit exceeded")
            if item.get("type") == "hookPrompt":
                raise ValueError("unexpected native hook delivery")
            if item.get("type") == "collabAgentToolCall":
                if item.get("tool") == "spawnAgent":
                    state["spawns"].add(item["id"])
                    require(len(state["spawns"]) <= 2, "observed child dispatch limit exceeded")
                    require(item.get("model") in (None, MODEL)
                            and item.get("reasoningEffort") in (None, "low", "medium", "high"),
                            "native child selection exceeds the contract")
                for child in item.get("receiverThreadIds", []):
                    if child != state["thread"] and child not in state["children"]:
                        state["children"].append(child)
        if ident == 1:
            require("result" in message, "initialize failed")
            send({"method": "initialized"})
            send({"id": 2, "method": "model/list", "params": {"limit": 100}})
        elif ident == 2:
            result = message.get("result", {})
            require(result.get("nextCursor") is None, "model catalog pagination required")
            matches = [x for x in result.get("data", []) if x.get("model") == MODEL]
            require(len(matches) == 1 and {"medium", "high"}.issubset({x["reasoningEffort"]
                    for x in matches[0]["supportedReasoningEfforts"]}), "model capability differs")
            put(root / "native-model-selection.json", encoded(matches[0]))
            send({"id": 3, "method": "thread/start", "params": {
                "model": MODEL, "cwd": str(project), "approvalPolicy": "on-request",
                "approvalsReviewer": "user", "sandbox": "workspace-write", "ephemeral": False,
                "historyMode": "paginated", "allowProviderModelFallback": False,
                "config": {"sandbox_workspace_write": {"writable_roots": [],
                    "network_access": False, "exclude_tmpdir_env_var": True,
                    "exclude_slash_tmp": True}}}})
        elif ident == 3:
            result = message.get("result", {})
            put(root / "native-instruction-sources.json", encoded(result.get("instructionSources")))
            require(result.get("instructionSources") == profile["expected_instruction_sources"],
                    "loaded instruction sources differ from prepared inventory")
            thread = result.get("thread", {})
            require(result.get("model") == MODEL and result.get("cwd") == str(project)
                    and result.get("approvalPolicy") == "on-request"
                    and result.get("approvalsReviewer") == "user"
                    and thread.get("cliVersion") == profile["version"].removeprefix("codex-cli ")
                    and thread.get("turns") == [], "fresh native thread differs")
            sandbox(result, project)
            state["thread"] = thread["id"]
            send({"id": 4, "method": "skills/list", "params": {
                "cwds": [str(project)], "forceReload": True}})
        elif ident == 4:
            actual = skills_identity(message.get("result", {}), project)
            require(actual == profile["skills"], "native authoring inventory drift")
            send({"id": 5, "method": "mcpServerStatus/list", "params": {
                "threadId": state["thread"], "limit": 100}})
        elif ident == 5:
            result = message.get("result", {})
            require(result.get("nextCursor") is None and isinstance(result.get("data"), list)
                    and all(x.get("runtimeStatus") == "disabled" and x.get("tools") == {}
                            for x in result["data"]), "active connector outside the profile")
            verify_profile(profile)
            require(snapshot(project) == manifest["git_state"], "Git state drift before task delivery")
            send({"id": 6, "method": "turn/start", "params": {
                "threadId": state["thread"], "model": MODEL, "effort": EFFORT,
                "cwd": str(project), "approvalPolicy": "on-request", "approvalsReviewer": "user",
                "input": [{"type": "text", "text": manifest["prompt"], "text_elements": []}],
                "sandboxPolicy": {"type": "workspaceWrite", "writableRoots": [],
                    "networkAccess": False, "excludeTmpdirEnvVar": True, "excludeSlashTmp": True}}})
        elif ident == 6:
            require("result" in message, "native turn start failed")
            state["turn"] = message["result"]["turn"]["id"]
        elif method == "turn/completed" and message["params"].get("threadId") == state["thread"]:
            turn = message["params"]["turn"]
            require(turn.get("id") == state["turn"] and turn.get("status") == "completed"
                    and turn.get("error") is None, "native turn did not complete")
            state["pending"] = [state["thread"], *state["children"]]
            return read_next(send)
        elif ident == 10:
            thread = message.get("result", {}).get("thread", {})
            target = state["pending"][0]
            require(thread.get("id") == target and thread.get("cwd") == str(project),
                    "native history identity differs")
            state["metadata"][target] = thread
            send({"id": 11, "method": "thread/turns/list", "params": {
                "threadId": target, "limit": 100, "sortDirection": "asc", "itemsView": "full"}})
        elif ident == 11:
            target = state["pending"][0]
            result = message.get("result", {})
            require(result.get("nextCursor") is None and isinstance(result.get("data"), list),
                    "native history incomplete or paginated")
            turns = result["data"]
            require(turns and all(x.get("status") == "completed" and x.get("error") is None
                    and x.get("itemsView", "full") == "full" for x in turns), "native history nonterminal")
            if target == state["thread"]:
                users = [x for turn in turns for x in turn["items"] if x.get("type") == "userMessage"]
                content = users[0].get("content", []) if len(users) == 1 else []
                require(len(turns) == 1 and turns[0]["id"] == state["turn"] and len(users) == 1
                        and len(content) == 1 and content[0].get("type") == "text"
                        and content[0].get("text") == manifest["prompt"]
                        and content[0].get("text_elements", []) == [], "delivered task differs")
            state["histories"][target] = turns
            for turn in turns:
                for item in turn["items"]:
                    if item.get("type") == "collabAgentToolCall" and item.get("tool") == "spawnAgent":
                        require(target == state["thread"], "unexpected nested delegation")
                        require(item.get("model") in (None, MODEL)
                                and item.get("reasoningEffort") in (None, "low", "medium", "high"),
                                "native child selection exceeds the contract")
                        state["spawns"].add(item["id"])
                        require(len(state["spawns"]) <= 2, "observed child dispatch limit exceeded")
                        for child in item.get("receiverThreadIds", []):
                            if child not in state["children"]:
                                state["children"].append(child)
                                state["pending"].append(child)
            state["pending"].pop(0)
            return read_next(send)
        return False

    primary_error = None
    capture_error = None
    evidence = None
    try:
        collect(native_command, project, root, "native", deadline, on_line=receive, begin=begin)
        verify_profile(profile)
        require(state["histories"] and state["settings"], "native observation incomplete")
    except Exception as error:
        primary_error = error
    finally:
        # collect has shut down the process group before final fixture capture.
        try:
            evidence = git_evidence(project, manifest["baseline"])
            put(root / "git-evidence.json", encoded(evidence))
        except Exception as error:
            capture_error = error
            state["git_capture_error"] = type(error).__name__ + ": " + str(error)
        if primary_error is not None:
            state["primary_error"] = type(primary_error).__name__ + ": " + str(primary_error)
        serializable = {**state, "tools": sorted(state["tools"]), "spawns": sorted(state["spawns"])}
        put(root / "outcome.json", encoded(serializable))
    if primary_error is not None:
        raise primary_error
    if capture_error is not None:
        raise capture_error
    return {"thread": state["thread"], "turn": state["turn"], "children": state["children"],
            "status": "native-turn-observed", "git_boundary": evidence["git_boundary"],
            "cost_claim": "usage endpoints retained; no aggregate or billing claim"}
