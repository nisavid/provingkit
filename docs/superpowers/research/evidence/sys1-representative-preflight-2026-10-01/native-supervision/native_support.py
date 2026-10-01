import argparse
import hashlib
import importlib.util
import json
import os
import re
import shlex
import sys
import time
import tomllib
import uuid
from pathlib import Path
MODELS = {"claude": "claude-opus-5-5", "codex": "gpt-6.1-sol"}
CLAUDE_LISTED_PLUGINS = [
    {"name": "agents-md", "path": "builtin", "source": "agents-md@builtin"},
    {"name": "telemetry", "path": "builtin", "source": "telemetry@builtin"},
]
CLAUDE_LISTED_AGENTS = ["claude", "Explore", "general-purpose", "Plan", "statusline-setup"]
DISABLED = ("multi_agent", "plugins", "apps", "shell_snapshot", "memories",
            "skill_search", "browser_use", "computer_use", "image_generation", "view_image", "sleep_tool")
CLAUDE_TOOLS = ["Bash", "Edit", "Read", "Write"]
SYSTEM_PROMPT = "Work on the supplied local developer task. Stay in the project, do not access external services, install software, create commits, or delegate."

def require(value, message):
    if not value:
        raise RuntimeError(message)

def verify_codex_sandbox(record, project, surface, sibling=None):
    """Check native workspace-write state while accounting for the implicit cwd root."""
    fields = {
        "thread-start": ("sandbox", "workspaceWrite", "writableRoots", "networkAccess",
                         "excludeTmpdirEnvVar", "excludeSlashTmp"),
        "settings": ("sandboxPolicy", "workspaceWrite", "writableRoots", "networkAccess",
                     "excludeTmpdirEnvVar", "excludeSlashTmp"),
        "persisted": ("sandbox_policy", "workspace-write", "writable_roots", "network_access",
                      "exclude_tmpdir_env_var", "exclude_slash_tmp"),
    }
    require(surface in fields and isinstance(record, dict), "Codex sandbox surface differs")
    policy_key, policy_type, roots_key, network_key, tmpdir_key, slash_tmp_key = fields[surface]
    policy = record.get(policy_key)
    project = str(project)
    require(record.get("cwd") == project and isinstance(policy, dict), "Codex sandbox cwd/policy differs")
    # Codex includes cwd itself in its effective writable roots. These fields list
    # only additional roots, so an explicit copy of cwd is equivalent to none.
    roots = policy.get(roots_key, [])
    accepted = ([], [project]) if sibling is None else ([str(sibling)], [project, str(sibling)], [str(sibling), project])
    require(policy.get("type") == policy_type and roots in accepted
            and policy.get(network_key, False) is False
            and policy.get(tmpdir_key) is True
            and policy.get(slash_tmp_key) is True, "Codex sandbox differs")

def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")

def verify_claude_init(manifest, event):
    require(event.get("type") == "system" and event.get("subtype") == "init", "not a Claude init record")
    require(event.get("model") == MODELS["claude"] and event.get("cwd") == manifest["project"]
            and event.get("session_id") == manifest["claude_session_id"]
            and event.get("claude_code_version") == "2.1.284"
            and event.get("permissionMode") == "auto", "Claude native session/init differs")
    require(isinstance(event.get("tools"), list) and sorted(event["tools"]) == CLAUDE_TOOLS and event.get("mcp_servers") == [],
            "Claude tool/MCP inventory differs or is unavailable")
    require(event.get("plugins") == CLAUDE_LISTED_PLUGINS,
            "Claude listed built-in plugin inventory differs or is unavailable")
    require(event.get("skills") == [], "Claude listed skill inventory differs or is unavailable")
    require(event.get("agents") == CLAUDE_LISTED_AGENTS,
            "Claude listed agent inventory differs or is unavailable")
    return True

def codex_common(manifest, project, override=None):
    command = ["codex", "--no-daemon", "app-server", "--stdio", "--strict-config", "--enable", "hooks"]
    for name in DISABLED:
        command += ["--disable", name]
    settings = [f'model="{MODELS["codex"]}"', "developer_instructions=" + json.dumps(SYSTEM_PROMPT), 'model_reasoning_effort="medium"', 'web_search="disabled"',
                "project_doc_max_bytes=0", "mcp_servers={}",
                'shell_environment_policy={inherit="none",set={LANG="C",LC_ALL="C",PATH="/usr/bin:/bin",'
                + ",".join(key + "=" + json.dumps(str(Path(project) / ".runner-tmp"))
                           for key in ("TMPDIR", "TMP", "TEMP")) + "}}",
                "projects={" + json.dumps(str(project)) + '={trust_level="trusted"}}']
    user_config = Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex")) / "config.toml"
    if user_config.exists():
        for name in sorted(tomllib.loads(user_config.read_text()).get("mcp_servers", {})):
            require(re.fullmatch(r"[A-Za-z0-9_-]+", name), "unsupported inherited connector name")
            settings.append("mcp_servers." + name + ".enabled=false")
    if override:
        settings.append(override)
    for setting in settings:
        command += ["-c", setting]
    return command

def discover_codex_hooks(manifest, root, collect):
    project = Path(manifest["project"])
    source = str(project / ".codex" / "hooks.json")
    command = codex_common(manifest, project)
    def inventory(command, label):
        result = {}
        def begin(send):
            send({"id": 1, "method": "initialize", "params": {"clientInfo": {"name": "sys1-context-probe", "version": "1"}}})
        def receive(message, send):
            if message.get("id") == 1:
                require("result" in message, "Codex discovery initialize failed")
                send({"method": "initialized"})
                send({"id": 2, "method": "hooks/list", "params": {"cwds": [str(project)]}})
            elif message.get("id") == 2:
                require("result" in message, "Codex hooks/list failed")
                result.update(message["result"])
                return True
            return False
        collect(command, project, root, label, time.monotonic() + 30, on_line=receive, begin=begin)
        rows = result.get("data")
        require(isinstance(rows, list) and len(rows) == 1 and rows[0].get("cwd") == str(project)
                and rows[0].get("errors") == [], "Codex hook inventory unavailable")
        hooks = rows[0].get("hooks", [])
        candidates = [item for item in hooks if item.get("sourcePath") == source]
        require(len(candidates) == 2 and {item.get("eventName") for item in candidates} == {"postToolUse", "stop"},
                "Codex probe hook candidates differ")
        require(all(item.get("command") == manifest["hook_command"] and item.get("source") == "project"
                    and item.get("handlerType") == "command" for item in candidates), "Codex hook identity differs")
        return hooks, candidates
    first, candidates = inventory(command, "hook-discovery-first")
    keys = {item["key"] for item in candidates}
    entries = []
    for item in first:
        key = item.get("key")
        digest = item.get("currentHash")
        require(isinstance(key, str) and isinstance(digest, str) and digest.startswith("sha256:"), "Codex hook hash missing")
        entries.append(json.dumps(key) + "={" +
                       ("enabled=true,trusted_hash=" + json.dumps(digest) if key in keys else "enabled=false") + "}")
    override = "hooks.state={" + ",".join(entries) + "}"
    second, approved = inventory(codex_common(manifest, project, override), "hook-discovery-second")
    require({item["key"] for item in approved} == keys and
            all(item.get("enabled") is True and item.get("trustStatus") == "trusted" for item in approved) and
            all(item.get("enabled") is False for item in second if item["key"] not in keys),
            "Codex hook inventory trust/enablement differs")
    save(root / "private" / "hook-discovery.json", {"before": first, "after": second, "override": override})
    return override

VERSIONS = {'claude': '2.1.284 (Claude Code)', 'codex': 'codex-cli 0.159.0'}
