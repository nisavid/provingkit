"""Ordinary host-supplied executable selection and observable drift checks.

This contract trusts the execution host, including its interpreter and system
namespace. It does not establish administrator ownership or host isolation.
Consumers retain their own configuration, provider, and private-state policy.
"""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path


class HostTrustError(OSError):
    """A selected host path is unavailable, unsuitable, or has changed."""


@dataclass(frozen=True)
class HostExecutable:
    """One fixed selection, with the path identities observed at binding."""

    path: str
    resolved_path: Path
    identities: tuple[tuple[Path, tuple[int, ...]], ...]


def is_host_namespace_anchor(path: Path) -> bool:
    """Identify only a lexical absolute filesystem root, without inspecting it."""
    return path.is_absolute() and path == Path(path.anchor)


def _identity(metadata: os.stat_result) -> tuple[int, ...]:
    if stat.S_ISDIR(metadata.st_mode):
        # Ancestor entry activity is not executable identity. These snapshots
        # retain object/owner/mode state, not timestamps or mutation history.
        return (
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_mode,
            metadata.st_uid,
            metadata.st_gid,
        )
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_nlink,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def bind_host_executable(
    path: Path,
    *,
    excluded_roots: tuple[Path, ...] = (),
    allow_symlink: bool = False,
) -> HostExecutable:
    """Bind an absolute, non-candidate host executable without consulting PATH.

    Ordinary mode trusts host-supplied ownership, but retains executable/type
    and mode checks. A caller must select the fixed platform path or its
    existing host registration; this function is not executable discovery.
    """
    path = Path(path)
    if not path.is_absolute() or ".." in path.parts:
        raise HostTrustError("host executable path must be absolute and normalized")
    try:
        resolved = path.resolve(strict=True)
        if not allow_symlink and resolved != path:
            raise HostTrustError("host executable path is redirected")
        for root in excluded_roots:
            lexical_root = Path(os.path.abspath(root))
            resolved_root = lexical_root.resolve(strict=True)
            if any(
                candidate.is_relative_to(excluded)
                for candidate in (path, resolved)
                for excluded in (lexical_root, resolved_root)
            ):
                raise HostTrustError("host executable is candidate-controlled")

        # Include both spellings so a link or its target cannot be silently
        # replaced. lstat never substitutes a link's target metadata.
        paths = dict.fromkeys((*reversed(path.parents), path,
                              *reversed(resolved.parents), resolved))
        identities = []
        for inspected in paths:
            metadata = inspected.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                if not allow_symlink:
                    raise HostTrustError("host executable path is redirected")
            else:
                wanted_type = stat.S_ISREG if inspected == resolved else stat.S_ISDIR
                if not wanted_type(metadata.st_mode) or metadata.st_mode & 0o022:
                    raise HostTrustError("host executable path has unsafe type or mode")
                if inspected == resolved and not metadata.st_mode & 0o111:
                    raise HostTrustError("host executable is not executable")
            identities.append((inspected, _identity(metadata)))
        return HostExecutable(str(path), resolved, tuple(identities))
    except (OSError, RuntimeError, ValueError) as error:
        if isinstance(error, HostTrustError):
            raise
        raise HostTrustError("host executable is unavailable") from error


def recheck_host_executable(bound: HostExecutable) -> None:
    """Reject observable replacement of a bound path or its namespace chain."""
    try:
        if Path(bound.path).resolve(strict=True) != bound.resolved_path:
            raise HostTrustError("host executable changed")
        for path, expected in bound.identities:
            if _identity(path.lstat()) != expected:
                raise HostTrustError("host executable changed")
    except (OSError, RuntimeError, ValueError) as error:
        if isinstance(error, HostTrustError):
            raise
        raise HostTrustError("host executable changed") from error
