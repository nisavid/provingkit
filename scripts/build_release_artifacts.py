#!/usr/bin/env python3
"""Project canonical Provingkit source into installable harness artifacts.

This is a CI/DevOps operation. Harness installers consume its output; they
never invoke this script. The output is deliberately fresh, allowlisted, and
bound to a receipt containing the source revision and deterministic digest.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


SCHEMA = "provingkit-artifact-receipt-v1"
BUILDER_VERSION = "provingkit-artifact-projector-v1"
POLICY_PATH = Path("release/artifact-projection-policy-v1.json")


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git(*args: str, cwd: Path) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def matches(path: str, pattern: str) -> bool:
    return fnmatch.fnmatchcase(path, pattern) or fnmatch.fnmatchcase(path, pattern.removesuffix("/**"))


def selected_files(source: Path, spec: dict) -> list[Path]:
    include = spec["include"]
    exclude = spec["exclude"]
    result: list[Path] = []
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            if path.is_symlink():
                raise ValueError(f"symlink in plugin source: {path}")
            continue
        rel = path.relative_to(source).as_posix()
        if any(matches(rel, pattern) for pattern in exclude):
            continue
        if any(matches(rel, pattern) for pattern in include):
            if path.is_symlink():
                raise ValueError(f"symlink in plugin source: {path}")
            result.append(path)
    return result


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(value))


def tree_digest(root: Path) -> tuple[str, list[dict[str, str]]]:
    inventory: list[dict[str, str]] = []
    framed = bytearray(b"provingkit-tree-v1\0")
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        data = path.read_bytes()
        digest = sha256_bytes(data)
        inventory.append({"path": rel, "sha256": digest})
        name = rel.encode()
        framed.extend(len(name).to_bytes(8, "big"))
        framed.extend(name)
        framed.extend(len(data).to_bytes(8, "big"))
        framed.extend(data)
    return sha256_bytes(bytes(framed)), inventory


def manifest_for_cursor(canonical: dict) -> dict:
    result = dict(canonical)
    result.pop("extensions", None)
    result["skills"] = "./skills/"
    result["agents"] = "./agents/"
    return result


def validate_non_overlapping_paths(source: Path, output: Path) -> None:
    if source == output or source in output.parents or output in source.parents:
        raise ValueError(
            f"source and output paths must not overlap: source={source}, output={output}"
        )


def validate_clean_source(source: Path) -> None:
    status = git("status", "--porcelain=v1", "--untracked-files=all", cwd=source)
    if status:
        raise ValueError(
            "source checkout must be clean before projecting a commit-bound artifact"
        )


def build(source: Path, output: Path, target: str, slate: list[str], channel: str, force: bool) -> Path:
    source = source.resolve()
    output = output.resolve()
    validate_non_overlapping_paths(source, output)
    policy = json.loads((source / POLICY_PATH).read_text())
    if target not in policy["targets"]:
        raise ValueError(f"unsupported target: {target}")
    target_spec = policy["targets"][target]
    known = set(policy["slate"])
    if not slate:
        slate = list(policy["slate"])
    if set(slate) - known:
        raise ValueError(f"unknown plugin(s): {sorted(set(slate) - known)}")
    if "task-witness" in slate:
        raise ValueError("task-witness is code-only and has no install projection")
    if len(set(slate)) != len(slate):
        raise ValueError("plugin slate contains duplicates")

    validate_clean_source(source)
    source_commit = git("rev-parse", "HEAD", cwd=source)
    short_commit = git("rev-parse", "--short=12", "HEAD", cwd=source)
    policy_digest = sha256_bytes(canonical_json(policy))
    if output.exists():
        if not force:
            raise FileExistsError(f"output exists (use --force): {output}")
        shutil.rmtree(output)
    output.mkdir(parents=True)

    for plugin_id in slate:
        src = source / policy["source_root"] / plugin_id
        if not src.is_dir():
            raise FileNotFoundError(src)
        dst = output / target_spec["plugin_root"] / plugin_id
        for path in selected_files(src, target_spec):
            rel = path.relative_to(src)
            copy_file(path, dst / rel)
        if target == "cursor":
            canonical = json.loads((src / "plugin.json").read_text())
            write_json(dst / ".cursor-plugin/plugin.json", manifest_for_cursor(canonical))

    entries = []
    for plugin_id in slate:
        manifest = json.loads((source / policy["source_root"] / plugin_id / "plugin.json").read_text())
        if target == "agent-plugins":
            entries.append({"name": plugin_id, "source": {"source": "local", "path": f"./plugins/{plugin_id}"}, "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}, "category": "Productivity"})
        elif target == "claude":
            entries.append({"name": plugin_id, "description": manifest.get("description", ""), "version": manifest.get("version", "1.0.0"), "author": manifest.get("author", {}), "source": f"./plugins/{plugin_id}"})
        else:
            entries.append({"name": plugin_id, "source": f"./plugins/{plugin_id}"})
    catalog_rel = target_spec["catalog"]
    if target == "agent-plugins":
        catalog = {"name": "provingkit", "interface": {"displayName": "Provingkit"}, "plugins": entries}
    elif target == "claude":
        catalog = {"$schema": "https://anthropic.com/claude-code/marketplace.schema.json", "name": "provingkit", "description": "Provingkit installable plugins.", "owner": {"name": "Ivan D Vasin", "email": "ivan@nisavid.io"}, "plugins": entries}
    else:
        catalog = {"name": "provingkit", "owner": {"name": "Ivan D Vasin"}, "metadata": {"description": "Provingkit installable plugins."}, "plugins": entries}
    write_json(output / catalog_rel, catalog)

    artifact_digest, inventory = tree_digest(output)
    receipt = {
        "schema": SCHEMA,
        "builder": {"name": BUILDER_VERSION, "revision": source_commit},
        "source": {"repository": "https://github.com/nisavid/provingkit", "commit": source_commit, "preview_label": f"preview-{short_commit}", "channel": channel},
        "target": target,
        "plugin_slate": slate,
        "policy_sha256": policy_digest,
        "artifact_sha256": artifact_digest,
        "files": inventory,
    }
    write_json(output / "RECEIPT.json", receipt)
    return output / "RECEIPT.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target", choices=["agent-plugins", "claude", "cursor"], required=True)
    parser.add_argument("--slate", help="comma-separated plugin ids; defaults to the complete agent-plugin slate")
    parser.add_argument("--channel", choices=["preview", "main", "release"], default="preview")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    slate = [x for x in (args.slate.split(",") if args.slate else []) if x]
    receipt = build(args.source.resolve(), args.output.resolve(), args.target, slate, args.channel, args.force)
    print(receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
