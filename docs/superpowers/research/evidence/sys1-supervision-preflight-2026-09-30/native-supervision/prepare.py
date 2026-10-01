"""Prepare four passive native probes; this command never launches a harness."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import uuid

from native_support import MODELS, VERSIONS


SOURCE = Path(__file__).resolve().parent
WORKLOADS = SOURCE.parent / "ordinary-workloads"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def dependency_inventory(package):
    """Bind the installed production dependency trees used by the copied integration."""
    pending = [package]
    visited, roots, files = set(), {}, []
    while pending:
        logical = pending.pop()
        resolved = logical.resolve(strict=True)
        roots[str(logical)] = str(resolved)
        if resolved in visited:
            continue
        visited.add(resolved)
        metadata = json.loads((resolved / "package.json").read_text())
        if logical != package:
            for directory, subdirectories, names in os.walk(resolved):
                subdirectories[:] = [name for name in subdirectories if name not in {"node_modules", ".git"}]
                files += [Path(directory) / name for name in names if (Path(directory) / name).is_file()]
        for name in metadata.get("dependencies", {}):
            candidates = [base / "node_modules" / name for base in [logical, *logical.parents]]
            target = next((candidate for candidate in candidates if (candidate / "package.json").is_file()), None)
            if target is None:
                # Node resolves nested dependencies from a symlink's real package location.
                target = next((base / "node_modules" / name for base in [resolved, *resolved.parents]
                               if (base / "node_modules" / name / "package.json").is_file()), None)
            if target is None:
                raise ValueError("installed runtime dependency unavailable: " + name)
            pending.append(target)
    return roots, files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    args = parser.parse_args()
    parent = args.parent
    if not parent.is_absolute() or parent.resolve() != parent or not parent.is_dir():
        raise ValueError("an existing, absolute scratch parent is required")
    batch = Path(tempfile.mkdtemp(prefix="ordinary-native-preflight-", dir=parent))
    runtime = [p for p in SOURCE.iterdir() if p.suffix in {".py", ".mjs"} and p.is_file()]
    runtime += [p for p in (SOURCE / "integration/dist").rglob("*") if p.is_file()]
    runtime += [SOURCE / "integration/package.json"]
    dependency_roots, dependency_files = dependency_inventory(SOURCE / "integration")
    runtime += dependency_files
    source_hashes = {str(p): digest(p) for p in runtime}
    node = shutil.which("node")
    if not node:
        raise ValueError("Node.js unavailable")
    manifests = []
    for harness in ("claude", "codex"):
        for case in ("parser-discovery", "report-sort"):
            root = batch / (harness + "-" + case)
            root.mkdir()
            project = root / "project"
            shutil.copytree(WORKLOADS / case / "project", project,
                            ignore=shutil.ignore_patterns("__pycache__"))
            (root / "sibling").mkdir()
            for name in ("deliveries", "acknowledgments", "hooks"):
                (root / "private" / name).mkdir(parents=True, exist_ok=True)
            for kind in ("config", "state", "cache"):
                (root / "integration-state" / kind).mkdir(parents=True)
            # A standalone fixture repository keeps sessionBase/workDiff local.
            git = ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false"]
            subprocess.run(git + ["init", "--quiet", "--initial-branch=main"], cwd=project, check=True)
            subprocess.run(git + ["add", "--all"], cwd=project, check=True)
            subprocess.run(git + ["commit", "--quiet", "-m", "test: seed synthetic supervision fixture"],
                           cwd=project, check=True)
            session_id = str(uuid.uuid4()) if harness == "claude" else None
            storage = Path.home() / (".claude/projects" if harness == "claude" else ".codex/sessions")
            hook_config = {"root": str(root), "harness": harness, "storage_root": str(storage),
                           "node": node, "max_hook_records": 64, "max_record_bytes": 134217728}
            save(root / "hook-config.json", hook_config)
            hook_command = shlex.join([sys.executable, str(SOURCE / "passive_hook.py"),
                                       "--config", str(root / "hook-config.json")])
            hooks = {event: [{"hooks": [{"type": "command", "command": hook_command,
                                         "timeout": 20}]}] for event in ("PostToolUse", "Stop")}
            if harness == "claude":
                settings_path = root / "settings.json"
                settings = {"hooks": hooks, "sandbox": {"enabled": True, "failIfUnavailable": True,
                    "allowUnsandboxedCommands": False, "network": {"allowedDomains": []},
                    "filesystem": {"denyRead": [str(Path.home()), str(root / "private"),
                                                   str(SOURCE)], "allowRead": [str(project)]}},
                    "permissions": {"deny": ["Read(//home/**)", "Read(/" + str(root / "private") + "/**)",
                                               "Read(/" + str(SOURCE) + "/**)"]}}
            else:
                settings_path = project / ".codex/hooks.json"
                settings_path.parent.mkdir()
                settings = {"hooks": hooks}
            save(settings_path, settings)
            prompts = ([(WORKLOADS / case / "prompt.md").read_text()] if case == "parser-discovery" else
                       [(WORKLOADS / name).read_text() for name in
                        ("report-initial-prompt.md", "report-json-amendment.md", "report-sorting-amendment.md")])
            manifest = {"schema": "sys1-supervision-native/v1", "purpose": "passive-context-qualification",
                        "harness": harness, "version": VERSIONS[harness], "model": MODELS[harness],
                        "effort": "medium", "case": case, "root": str(root), "project": str(project),
                        "sibling": str(root / "sibling"), "prompts": prompts,
                        "deadline_seconds": 180 if case == "parser-discovery" else 300,
                        "max_native_tool_calls": 40, "settings_path": str(settings_path),
                        "settings_sha256": digest(settings_path), "hook_config_sha256": digest(root / "hook-config.json"),
                        "source_sha256": source_hashes, "hook_command": hook_command,
                        "dependency_roots": dependency_roots,
                        "storage_root": str(storage), "claude_session_id": session_id,
                        "initial_project_sha256": {str(p.relative_to(project)): digest(p) for p in project.rglob("*")
                                                   if p.is_file() and ".git" not in p.relative_to(project).parts},
                        "external_effects": "Native provider requests and new native session records; no Jev call or live settings edit."}
            save(root / "manifest.json", manifest)
            manifests.append({"path": str(root / "manifest.json"), "sha256": digest(root / "manifest.json"),
                              "harness": harness, "case": case})
    save(batch / "inventory.json", {"purpose": "passive-context-qualification", "order": manifests,
                                    "maximum_episodes": 4, "automatic_retries": 0,
                                    "native_deadline_seconds_total": 960,
                                    "execution_authorized": False})
    print(json.dumps({"prepared": str(batch), "inventory": str(batch / "inventory.json"),
                      "episodes": 4, "native_sessions_started": 0}))


if __name__ == "__main__":
    main()
