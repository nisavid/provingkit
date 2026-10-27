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
import io
import json
import os
import shutil
import stat
import subprocess
import tarfile
import tempfile
from contextlib import contextmanager
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


def manifest_for_cursor(canonical: dict, *, has_agents: bool) -> dict:
    result = dict(canonical)
    result.pop("extensions", None)
    result["skills"] = "./skills/"
    if has_agents:
        result["agents"] = "./agents/"
    return result


def validate_non_overlapping_paths(source: Path, output: Path) -> None:
    if source == output or source in output.parents or output in source.parents:
        raise ValueError(
            f"source and output paths must not overlap: source={source}, output={output}"
        )


def prepare_output(output: Path, force: bool) -> Path:
    """Create an output without following links or trusting a shared namespace.

    Ownership protects subsequent path-based writes from other local users;
    descriptor-relative, symlink-safe removal also rejects leaf substitution.
    Processes with the current user's authority are outside that guarantee.
    """
    if (
        not hasattr(os, "O_DIRECTORY")
        or not hasattr(os, "O_NOFOLLOW")
        or not shutil.rmtree.avoids_symlink_attacks
        or os.open not in os.supports_dir_fd
        or os.mkdir not in os.supports_dir_fd
        or os.stat not in os.supports_dir_fd
    ):
        raise ValueError("safe artifact output requires no-follow directory operations")
    output = output.absolute()
    if output == output.parent or output.name == "..":
        raise ValueError(f"invalid artifact output: {output}")

    # macOS exposes /tmp and /var through root-owned aliases. Only such aliases
    # directly below a non-writable filesystem root are trusted; never resolve
    # the caller's output leaf or a link inside its selected parent hierarchy.
    root = Path(output.anchor)
    root_metadata = root.stat()
    first = root / output.parts[1]
    try:
        first_metadata = first.lstat()
    except FileNotFoundError:
        first_metadata = None
    if (
        len(output.parts) > 2
        and first_metadata is not None
        and stat.S_ISLNK(first_metadata.st_mode)
        and first_metadata.st_uid == 0
        and root_metadata.st_uid == 0
        and not root_metadata.st_mode & 0o022
    ):
        output = first.resolve(strict=True).joinpath(*output.parts[2:])

    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(output.anchor, flags)
    try:
        for component in (None, *output.parent.parts[1:]):
            if component is not None:
                try:
                    os.mkdir(component, 0o700, dir_fd=descriptor)
                except FileExistsError:
                    # Existing components are validated by the no-follow open below.
                    pass
                child = os.open(component, flags, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = child
            metadata = os.fstat(descriptor)
            if metadata.st_uid not in {0, os.geteuid()} or (
                metadata.st_mode & 0o022 and not metadata.st_mode & stat.S_ISVTX
            ):
                raise ValueError(
                    f"artifact output ancestor is writable by other users: {output}"
                )
        if metadata.st_uid != os.geteuid() or metadata.st_mode & 0o022:
            raise ValueError(
                "artifact output parent must be owned and not writable by other "
                f"users: {output}"
            )

        # Resolve only the verified parent, retaining the lexical output leaf.
        output = output.parent.resolve(strict=True) / output.name
        try:
            existing = os.stat(output.name, dir_fd=descriptor, follow_symlinks=False)
        except FileNotFoundError:
            existing = None
        if existing is not None:
            if not stat.S_ISDIR(existing.st_mode) or existing.st_uid != os.geteuid():
                raise ValueError(
                    f"artifact output must be an owned directory, not a symlink: {output}"
                )
            if not force:
                raise FileExistsError(f"output exists (use --force): {output}")
            shutil.rmtree(output.name, dir_fd=descriptor)
        # Keep even permissive-umask descendants inaccessible to other users
        # while the path-based projection writers populate the artifact.
        os.mkdir(output.name, 0o700, dir_fd=descriptor)
    finally:
        os.close(descriptor)
    return output


@contextmanager
def source_snapshot(source: Path, commit: str):
    with tempfile.TemporaryDirectory() as temporary:
        archive = subprocess.check_output(
            ["git", "archive", "--format=tar", commit], cwd=source
        )
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tar:
            tar.extractall(temporary)
        yield Path(temporary)


def build(
    source: Path,
    output: Path,
    target: str,
    slate: list[str],
    channel: str,
    force: bool,
) -> Path:
    source = Path(git("rev-parse", "--show-toplevel", cwd=source)).resolve()
    # Canonicalization is only for the overlap comparison, never deletion.
    validate_non_overlapping_paths(source, output.resolve())
    source_commit = git("rev-parse", "HEAD", cwd=source)
    short_commit = git("rev-parse", "--short=12", "HEAD", cwd=source)
    with source_snapshot(source, source_commit) as snapshot:
        return _build_snapshot(
            snapshot, output, target, slate, channel, force, source_commit, short_commit
        )


def _build_snapshot(
    source: Path,
    output: Path,
    target: str,
    slate: list[str],
    channel: str,
    force: bool,
    source_commit: str,
    short_commit: str,
) -> Path:
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

    policy_digest = sha256_bytes(canonical_json(policy))
    output = prepare_output(output, force)

    for plugin_id in slate:
        src = source / policy["source_root"] / plugin_id
        if not src.is_dir():
            raise FileNotFoundError(src)
        dst = output / target_spec["plugin_root"] / plugin_id
        selected = selected_files(src, target_spec)
        for path in selected:
            rel = path.relative_to(src)
            copy_file(path, dst / rel)
        if target == "cursor":
            canonical = json.loads((src / "plugin.json").read_text())
            has_agents = any(path.relative_to(src).parts[:1] == ("agents",) for path in selected)
            write_json(
                dst / ".cursor-plugin/plugin.json",
                manifest_for_cursor(canonical, has_agents=has_agents),
            )

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
    receipt = build(args.source.resolve(), args.output, args.target, slate, args.channel, args.force)
    print(receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
