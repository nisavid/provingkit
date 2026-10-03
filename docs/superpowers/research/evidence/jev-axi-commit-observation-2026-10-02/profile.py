"""Inventory the installed Codex authoring profile without starting a task."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import tomllib

from transport import collect


MODEL = "gpt-6.1-sol"
EFFORT = "medium"
DISABLED = ("hooks", "plugin_hooks", "memories", "apps",
            "shell_snapshot", "browser_use", "computer_use", "image_generation")


def home():
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")


def identity(path):
    data = path.read_bytes()
    return {"path": str(path), "resolved": str(path.resolve()), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def command(project):
    args = ["codex", "--no-daemon", "app-server", "--stdio", "--strict-config"]
    for feature in DISABLED:
        args += ["--disable", feature]
    args += ["--enable", "plugins", "--enable", "multi_agent"]
    config = tomllib.loads((home() / "config.toml").read_text())
    settings = ['model="' + MODEL + '"', 'model_reasoning_effort="medium"',
                'web_search="disabled"', 'mcp_servers={}',
                'agents.max_concurrent_threads_per_session=2',
                'agents.default_subagent_model="' + MODEL + '"',
                'agents.default_subagent_reasoning_effort="high"',
                'projects={' + json.dumps(str(project)) + '={trust_level="trusted"}}',
                'shell_environment_policy={inherit="none",set={LANG="C",LC_ALL="C",'
                'PATH=' + json.dumps(os.environ["PATH"]) + ',TMPDIR='
                + json.dumps(str(project / ".runner-tmp")) + '}}']
    for name in sorted(config.get("mcp_servers", {})):
        if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
            raise ValueError("unsupported connector name")
        settings.append("mcp_servers." + name + ".enabled=false")
    for setting in settings:
        args += ["-c", setting]
    return args


def skills_identity(result, project):
    rows = result.get("data")
    if not isinstance(rows, list) or len(rows) != 1 or rows[0].get("cwd") != str(project) or rows[0].get("errors") != []:
        raise ValueError("skill discovery unavailable")
    entries = []
    for item in rows[0]["skills"]:
        path = Path(item["path"])
        if not path.is_absolute() or path.name != "SKILL.md":
            raise ValueError("skill entrypoint differs")
        entries.append({"name": item["name"], "enabled": item["enabled"],
                        "scope": item["scope"], **identity(path)})
    return entries


def verify_profile(profile):
    for root, expected in profile["resource_trees"].items():
        actual = [identity(p) for p in sorted(Path(root).rglob("*"))
                  if p.is_file() and "__pycache__" not in p.parts]
        if actual != expected:
            raise ValueError("authoring resource tree drift: " + root)
    for entry in [*profile["instructions"], *profile["skills"], *profile["references"]]:
        actual = identity(Path(entry["path"]))
        if any(actual[k] != entry[k] for k in actual):
            raise ValueError("authoring profile source drift: " + entry["path"])


def discover(project, root):
    result = {}
    def begin(send):
        send({"id": 1, "method": "initialize", "params": {
            "clientInfo": {"name": "passive-commit-profile", "version": "1"}}})
    def receive(message, send):
        if message.get("method") is not None and message.get("id") is not None:
            raise ValueError("unexpected native control request during inventory")
        if message.get("id") == 1:
            if "result" not in message:
                raise ValueError("native inventory initialization failed")
            send({"method": "initialized"})
            send({"id": 2, "method": "skills/list", "params": {
                "cwds": [str(project)], "forceReload": True}})
        elif message.get("id") == 2:
            if "result" not in message:
                raise ValueError("native skill inventory failed")
            result["skills"] = skills_identity(message["result"], project)
            return True
        return False
    collect(command(project), project, root, "profile-discovery", time.monotonic() + 30,
            on_line=receive, begin=begin)
    instruction_path = home() / "AGENTS.override.md"
    if not instruction_path.is_file():
        instruction_path = home() / "AGENTS.md"
    instructions = [identity(instruction_path), identity(home() / "config.toml")]
    references, trees = [], {}
    # Bind full resource trees for the named authoring procedures. All other
    # discovered skill entrypoints are bound; their transitive resources are not.
    names = {"checkpointing-and-publishing-git-work", "tdd", "code-review",
             "capturing-agent-procedures", "writing-for-people", "review", "intent",
             "runtime", "structure", "delegating-cross-agent-work", "choosing-agent-models"}
    for entry in result["skills"]:
        if entry["name"].split(":")[-1] in names and entry["enabled"]:
            tree = []
            for path in sorted(Path(entry["path"]).parent.rglob("*")):
                if path.is_file() and "__pycache__" not in path.parts:
                    tree.append(identity(path))
            trees[str(Path(entry["path"]).parent)] = tree
            references.extend(tree)
    result.update(schema="installed-authoring-profile/v1", instructions=instructions,
                  expected_instruction_sources=[str(instruction_path)],
                  references=references, resource_trees=trees, disabled_features=list(DISABLED),
                  native_command=command(project),
                  version=subprocess.run(["codex", "--version"], check=True,
                        capture_output=True, text=True).stdout.strip(),
                  model=MODEL, effort=EFFORT, native_tasks_started=0)
    verify_profile(result)
    return result
