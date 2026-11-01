#!/usr/bin/env python3
"""Validate or regenerate the independently installed host-trust helpers."""

from __future__ import annotations

import argparse
import os
import stat
import tempfile
from pathlib import Path


SOURCE = Path("scripts/host_trust.py")
PROJECTIONS = (
    Path("plugins/versionkeeping/skills/using-persistent-git-worktrees/scripts/host_trust.py"),
    Path("plugins/versionkeeping/skills/checkpointing-and-publishing-git-work/scripts/git_publication/host_trust.py"),
    Path("plugins/mergecraft/skills/graphite/scripts/host_trust.py"),
)


def _regular(path: Path) -> None:
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError(f"host-trust source/projection is not a regular file: {path}")


def validate(root: Path, *, projections: tuple[Path, ...] = PROJECTIONS) -> None:
    """Check a consumer's selected projections against the single source."""
    _regular(root / SOURCE)
    expected = (root / SOURCE).read_bytes()
    for relative in projections:
        path = root / relative
        _regular(path)
        if path.read_bytes() != expected:
            raise ValueError(f"host-trust projection drift: {relative}")


def write(root: Path) -> None:
    """Replace only the fixed projections, never a redirected destination."""
    _regular(root / SOURCE)
    content = (root / SOURCE).read_bytes()
    for relative in PROJECTIONS:
        path = root / relative
        for parent in path.parents:
            if parent == root.parent:
                break
            if parent.is_symlink():
                raise ValueError(f"host-trust projection parent is a symlink: {parent}")
        if path.exists() or path.is_symlink():
            _regular(path)
    for relative in PROJECTIONS:
        path = root / relative
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.chmod(0o644)
            if path.exists() or path.is_symlink():
                _regular(path)
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    validate(root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        root = args.root.absolute()
        if args.write:
            write(root)
        else:
            validate(root)
    except (OSError, ValueError) as error:
        parser.exit(1, f"ERROR: {error}\n")
    print("Host-trust projections updated" if args.write else "Host-trust projections valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
