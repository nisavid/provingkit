#!/usr/bin/env python3
"""Build a pinned, offline Cloud coordination distribution into a new directory.

This stages support documents and the complete Agent Plugins projection from
one Git commit. It does not install, publish, activate, or update an export.
"""

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid

if __package__:
    from . import build_release_artifacts as projector
else:
    import build_release_artifacts as projector


SCHEMA = "provingkit-cloud-coordination-v1"
BUILDER_VERSION = "provingkit-cloud-coordination-builder-v1"
DOCUMENTS = ("README.md", "BOOTSTRAP.md", "role-policy.md")


@contextmanager
def _staging(output: Path):
    # Use the output namespace so an unrelated system temporary directory's
    # ownership does not add requirements beyond the projector's output guard.
    staged = projector.prepare_output(
        output.parent / f".{output.name}.staging-{uuid.uuid4().hex}", False
    )
    try:
        yield staged
    finally:
        if staged.exists():
            shutil.rmtree(staged)


def _relative_file(root: Path, relative: Path) -> str:
    path = projector.contained_path(root, relative)
    if not path.is_file():
        raise FileNotFoundError(path)
    return relative.as_posix()


def build(source: Path, output: Path, source_commit: str) -> Path:
    """Return the new manifest; reject mutable refs and every existing output.

    Public consumer boundary: real Git provides one immutable source snapshot;
    the existing release projector owns runtime selection and its receipt.
    """
    if not isinstance(source_commit, str) or not re.fullmatch(
        r"(?:[0-9a-f]{40}|[0-9a-f]{64})", source_commit
    ):
        raise ValueError("source_commit must be a full lowercase Git commit object ID")
    source = Path(projector.git("rev-parse", "--show-toplevel", cwd=source)).resolve()
    projector.validate_non_overlapping_paths(source, output.resolve())
    resolved = projector.git("rev-parse", "--verify", f"{source_commit}^{{commit}}", cwd=source)
    if resolved != source_commit:
        raise ValueError("source_commit must identify a commit, not a tag object")
    short_commit = projector.git("rev-parse", "--short=12", source_commit, cwd=source)

    with projector.source_snapshot(source, source_commit) as snapshot:
        # Stage and validate the complete candidate before creating the requested
        # output. Neither dirty checkout bytes nor a second HEAD lookup is used.
        with _staging(output) as staged:
            for name in DOCUMENTS:
                relative = Path("docs/cloud-coordination") / name
                _relative_file(snapshot, relative)
                projector.copy_file(snapshot / relative, staged / name)

            receipt_path = projector._build_snapshot(
                snapshot, staged / "runtime", "agent-plugins", [], "preview",
                False, source_commit, short_commit,
            )
            policy = json.loads(projector.contained_path(snapshot, projector.POLICY_PATH).read_bytes())
            target = policy["targets"]["agent-plugins"]
            plugin_root = Path("runtime") / projector.relative_policy_path(
                target["plugin_root"], "plugin_root"
            )
            delegation = plugin_root / "rolecasting/skills/delegating-cross-agent-work"
            skills = {
                "delegating_cross_agent_work": _relative_file(staged, delegation / "SKILL.md"),
                "choosing_agent_models": _relative_file(
                    staged, plugin_root / "rolecasting/skills/choosing-agent-models/SKILL.md"
                ),
            }
            driver = {
                "reference": _relative_file(staged, delegation / "references/native-tree-driver.md"),
                "script": _relative_file(staged, delegation / "scripts/native_tree.py"),
            }
            receipt_bytes = receipt_path.read_bytes()
            runtime_receipt = json.loads(receipt_bytes)
            artifact_digest, inventory = projector.tree_digest(staged)
            manifest = {
                "schema": SCHEMA,
                "builder": {"name": BUILDER_VERSION, "revision": source_commit},
                "source": {
                    "repository": runtime_receipt["source"]["repository"],
                    "commit": source_commit,
                },
                "profile": "chatgpt-codex-native-tree-v1",
                "scope": {
                    "supported": ["manual-entrypoint", "one-current-controller-native-tree"],
                    "nonclaims": [
                        "automatic-startup", "global-startup", "independent-persistent-chats",
                        "cross-root-restoration", "root-wake", "product-attestation",
                        "model-attestation", "permission-attestation", "exactly-once-effects",
                    ],
                },
                "qualification": {
                    "status": "not-qualified-by-build",
                    "installation": "not-performed", "deployment": "not-performed",
                },
                "startup": {
                    "mode": "manual", "entrypoint": "BOOTSTRAP.md",
                    "procedure": "README.md", "role_policy": "role-policy.md",
                },
                "runtime": {
                    "root": "runtime", "target": "agent-plugins",
                    "catalog": _relative_file(staged, Path("runtime") / target["catalog"]),
                    "receipt": {
                        "path": receipt_path.relative_to(staged).as_posix(),
                        "sha256": projector.sha256_bytes(receipt_bytes),
                    },
                    "skills": skills, "driver": driver,
                },
                "artifact_sha256": artifact_digest,
                "files": inventory,
            }
            # The complete inventory includes the exact runtime receipt bytes;
            # MANIFEST.json excludes itself rather than claiming a self-hash.
            projector.write_json(staged / "MANIFEST.json", manifest)
            output = projector.prepare_output(output, False)
            # The guard reserves a fresh private directory. The sibling stage
            # is on the same filesystem, so complete contents appear together.
            # As with the projector, concurrent changes by this user are outside
            # the filesystem guard's guarantee.
            os.replace(staged, output)
            return output / "MANIFEST.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path.cwd())
    parser.add_argument("--source-commit", required=True, help="full immutable Git commit object ID")
    parser.add_argument("--output", type=Path, required=True, help="new distribution directory")
    args = parser.parse_args()
    try:
        manifest = build(args.source, args.output, args.source_commit)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.error(str(error))
    print(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
