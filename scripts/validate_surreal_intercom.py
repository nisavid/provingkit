#!/usr/bin/env python3
"""Validate Surreal Intercom's standard manifest and contained skill resources."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

from agent_plugins_standard import (
    AgentPluginContractError,
    discover_direct_skills,
    load_agent_plugin_manifest,
    validate_skill_resource_links,
)
from member_versions import is_supported_member_version
from member_source_stage_cli import (
    add_context_arguments,
    check_context_if_requested,
    prepare_context_if_requested,
)
from refresh_transaction import (
    InputEntry,
    RefreshTransactionError,
    capture_input_entry,
    replace_generated_artifacts,
    snapshot_tree,
)

PLUGIN_RELATIVE = Path("plugins/surreal-intercom")
CONTENT_LOCK_RELATIVE = Path("release/plugin-content-locks/surreal-intercom.json")
EVALUATION_RELATIVE = Path("evals/surreal-intercom/skills/communicating-with-agents")
SOURCE_ENTRIES = {
    "plugin.json", ".claude-plugin", "skills", "README.md", "DEVELOPING.md",
    "LICENSE", "CHANGELOG.md", "topology.json",
}
EXTERNAL_STATE_DIRECTORIES = {"evals", "tests", "captures", "stores", "__pycache__"}


def validate_evaluations(root: Path, snapshot) -> None:
    if any(entry.kind not in {"regular", "directory"} for _, entry in snapshot):
        raise AgentPluginContractError("external evaluation resources must be regular files")
    triggers = json.loads((root / "trigger-evals.json").read_text(encoding="utf-8"))
    if (not isinstance(triggers, list)
            or any(not isinstance(item, dict)
                   or set(item) != {"query", "should_trigger"}
                   or not isinstance(item["query"], str) or not item["query"].strip()
                   or type(item["should_trigger"]) is not bool for item in triggers)
            or {item["should_trigger"] for item in triggers} != {True, False}):
        raise AgentPluginContractError("evaluation discovery requires positive and negative cases")
    corpus = json.loads((root / "evals.json").read_text(encoding="utf-8"))
    if (not isinstance(corpus, dict)
            or corpus.get("skill_name") != "communicating-with-agents"
            or not isinstance(corpus.get("evals"), list) or not corpus["evals"]):
        raise AgentPluginContractError("external evaluation corpus identity drift")
    for case in corpus["evals"]:
        if (not isinstance(case, dict) or not isinstance(case.get("files"), list)
                or not case["files"]):
            raise AgentPluginContractError("evaluation fixture list is missing")
        for relative in case["files"]:
            if (not isinstance(relative, str) or Path(relative).is_absolute()
                    or ".." in Path(relative).parts
                    or not (root / relative).is_file()):
                raise AgentPluginContractError("evaluation fixture is missing or uncontained")


def require_unchanged_sources(sources) -> None:
    for root, snapshot in sources:
        if snapshot_tree(root, error_type=AgentPluginContractError) != snapshot:
            raise AgentPluginContractError("validated source changed during regeneration")


def validate_skill_descriptor(root: Path, name: str) -> None:
    content = (root / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", content, re.DOTALL)
    if match is None:
        raise AgentPluginContractError("skill descriptor frontmatter is missing")
    try:
        metadata = yaml.safe_load(match.group(1))
    except yaml.YAMLError as error:
        raise AgentPluginContractError("skill descriptor frontmatter is invalid") from error
    if (not isinstance(metadata, dict) or metadata.get("name") != name
            or not isinstance(metadata.get("description"), str)
            or not metadata["description"].strip()):
        raise AgentPluginContractError("skill descriptor identity or description drift")


def validate(repository: Path):
    root = repository / PLUGIN_RELATIVE
    snapshot = snapshot_tree(root, error_type=AgentPluginContractError)
    evaluation_root = repository / EVALUATION_RELATIVE
    evaluation_snapshot = snapshot_tree(evaluation_root, error_type=AgentPluginContractError)
    sources = ((root, snapshot), (evaluation_root, evaluation_snapshot))
    manifest = load_agent_plugin_manifest(root)
    if manifest.get("name") != "surreal-intercom":
        raise AgentPluginContractError("canonical member identity drift")
    if not is_supported_member_version(manifest.get("version")):
        raise AgentPluginContractError("unsupported member version assignment")
    adapter = root / ".claude-plugin/plugin.json"
    if adapter.parent.is_symlink() or adapter.is_symlink() or not adapter.is_file():
        raise AgentPluginContractError("Claude identity projection must be a regular file")
    expected = {
        key: value for key, value in manifest.items()
        if key not in {"$schema", "extensions"}
    }
    expected["displayName"] = "Surreal Intercom"
    if json.loads(adapter.read_text(encoding="utf-8")) != expected:
        raise AgentPluginContractError("Claude identity projection drift")
    interface = manifest.get("extensions", {}).get("com.openai", {}).get("interface", {})
    if not isinstance(interface, dict):
        raise AgentPluginContractError("canonical interface must be an object")
    prompts = interface.get("defaultPrompt")
    target = "$surreal-intercom:communicating-with-agents"
    if (
        not isinstance(prompts, list) or len(prompts) != 1
        or not isinstance(prompts[0], str)
        or re.findall(r"\$[a-z0-9-]+:[a-z0-9-]+", prompts[0]) != [target]
    ):
        raise AgentPluginContractError("canonical default prompt target drift")
    native = root / "skills/communicating-with-agents/agents/openai.yaml"
    if native.is_symlink() or native.parent.is_symlink():
        raise AgentPluginContractError("skill default prompt must be a regular resource")
    native_interface = yaml.safe_load(native.read_text(encoding="utf-8"))
    if (
        not isinstance(native_interface, dict)
        or not isinstance(native_interface.get("interface"), dict)
        or native_interface["interface"].get("default_prompt") != prompts[0]
    ):
        raise AgentPluginContractError("skill default prompt projection drift")
    skills = discover_direct_skills(root)
    if skills != ("communicating-with-agents",):
        raise AgentPluginContractError(
            "Agent Plugins direct-child skill inventory drift"
        )
    validate_skill_descriptor(root, skills[0])
    validate_skill_resource_links(root, skills, recursive=True)
    if any(entry.kind not in {"regular", "directory"} for _, entry in snapshot):
        raise AgentPluginContractError("plugin resources must be regular contained files")
    for relative, _entry in snapshot:
        path = Path(relative)
        if not path.parts:
            continue
        if (path.parts[0] not in SOURCE_ENTRIES
                or EXTERNAL_STATE_DIRECTORIES.intersection(path.parts)
                or path.suffix in {".pyc", ".log", ".sqlite", ".sqlite3"}):
            raise AgentPluginContractError(
                f"resource outside the installable source contract: {relative}"
            )
    scripts = root / "skills/communicating-with-agents/scripts"
    local_modules = {path.stem for path in scripts.glob("*.py")}
    for path in sorted(scripts.glob("*.py")):
        try:
            nodes = ast.walk(ast.parse(path.read_text(encoding="utf-8"), filename=path.name))
            for node in nodes:
                modules = []
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    if node.level:
                        raise AgentPluginContractError("relative runtime import is unsupported")
                    modules = [node.module or ""]
                if any(name.split(".", 1)[0] not in local_modules | sys.stdlib_module_names
                       for name in modules):
                    raise AgentPluginContractError(f"uncontained runtime import: {path.name}")
        except SyntaxError as error:
            raise AgentPluginContractError(f"invalid runtime source: {path.name}") from error
    validate_evaluations(evaluation_root, evaluation_snapshot)
    document = {
        "schema_version": 1,
        "algorithm": "sha256",
        "files": {
            relative: entry.sha256 for relative, entry in snapshot
            if entry.kind == "regular"
        },
        "evaluations": {
            (EVALUATION_RELATIVE / relative).as_posix(): entry.sha256
            for relative, entry in evaluation_snapshot if entry.kind == "regular"
        },
    }
    require_unchanged_sources(sources)
    return sources, document


def write_content_lock(repository: Path, sources, document, previous: InputEntry) -> None:
    destination = repository / CONTENT_LOCK_RELATIVE
    if previous.kind not in {"missing", "regular"}:
        raise AgentPluginContractError("external content lock must be a regular file")
    mode = previous.mode if previous.mode is not None else 0o644
    content = (json.dumps(document, indent=2) + "\n").encode("utf-8")

    def recheck(_temporary_paths):
        require_unchanged_sources(sources)
        if capture_input_entry(destination, error_type=AgentPluginContractError) != previous:
            raise AgentPluginContractError("content lock changed during regeneration")

    def verify():
        require_unchanged_sources(sources)
        expected = InputEntry("regular", mode, hashlib.sha256(content).hexdigest())
        if capture_input_entry(destination, error_type=AgentPluginContractError) != expected:
            raise AgentPluginContractError("content lock replacement identity mismatch")

    replace_generated_artifacts(
        repository, {destination: (content, mode)}, recheck=recheck, verify=verify,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path, nargs="?", default=Path("."))
    parser.add_argument("--write-content-lock", action="store_true")
    add_context_arguments(parser)
    arguments = parser.parse_args(argv)
    context = None
    try:
        repository = arguments.repository.expanduser().absolute()
        context = prepare_context_if_requested(
            parser, arguments, repository, writing=arguments.write_content_lock,
        )
        previous = capture_input_entry(
            repository / CONTENT_LOCK_RELATIVE, error_type=AgentPluginContractError,
        ) if arguments.write_content_lock else None
        sources, document = validate(repository)
        if arguments.write_content_lock:
            write_content_lock(repository, sources, document, previous)
        actual = json.loads((repository / CONTENT_LOCK_RELATIVE).read_text(encoding="utf-8"))
        if actual != document:
            raise AgentPluginContractError("semantic content lock mismatch")
    except (AgentPluginContractError, RefreshTransactionError, OSError,
            UnicodeDecodeError, ValueError, yaml.YAMLError) as error:
        print(f"Surreal Intercom contract failed: {error}", file=sys.stderr)
        return 1
    print("Surreal Intercom contract checks passed",
          file=sys.stderr if context is not None else sys.stdout)
    if context is not None:
        return check_context_if_requested(context, "surreal-intercom")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
