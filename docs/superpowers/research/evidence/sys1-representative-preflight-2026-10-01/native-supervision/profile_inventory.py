"""Bind the skill entrypoints returned by native Codex inventory.

This records entrypoints, not transitive references or every ambient instruction.
"""

import hashlib
import json
from pathlib import Path

from native_support import require


MAX_ENTRY_BYTES = 262144
MAX_TOTAL_BYTES = 16777216


def entry_identity(path):
    require(path.is_absolute() and path.name == "SKILL.md" and path.is_file(),
            "native skill entrypoint unavailable")
    with path.open("rb") as stream:
        data = stream.read(MAX_ENTRY_BYTES + 1)
    require(len(data) <= MAX_ENTRY_BYTES, "native skill entrypoint exceeds capture bound")
    return str(path.resolve(strict=True)), hashlib.sha256(data).hexdigest(), len(data)


def capture_inventory(response, project):
    rows = response.get("data")
    require(isinstance(rows, list) and len(rows) == 1
            and rows[0].get("cwd") == str(project) and rows[0].get("errors") == [],
            "native skill inventory unavailable")
    skills = rows[0].get("skills")
    require(isinstance(skills, list) and len(skills) <= 2048,
            "native skill inventory exceeds capture bound")
    entries, total = [], 0
    for skill in skills:
        require(isinstance(skill, dict) and isinstance(skill.get("name"), str)
                and skill["name"] and isinstance(skill.get("description"), str)
                and skill.get("scope") in {"user", "repo", "system", "admin"}
                and type(skill.get("enabled")) is bool and isinstance(skill.get("path"), str),
                "native skill metadata differs")
        resolved, sha256, size = entry_identity(Path(skill["path"]))
        total += size
        require(total <= MAX_TOTAL_BYTES, "native skill inventory exceeds capture bound")
        entries.append({"name": skill["name"], "scope": skill["scope"],
                        "enabled": skill["enabled"], "path": skill["path"],
                        "resolved_path": resolved, "sha256": sha256, "bytes": size})
    return {"schema": "sys1-native-skill-inventory/v1", "cwd": str(project),
            "metadata_sha256": hashlib.sha256(json.dumps(response, sort_keys=True,
                separators=(",", ":")).encode()).hexdigest(), "entries": entries,
            "claim": "Listed skill entrypoints only; transitive references and other ambient instructions are unbound."}


def verify_sources(profile):
    for entry in profile["entries"]:
        resolved, sha256, size = entry_identity(Path(entry["path"]))
        require((resolved, sha256, size) ==
                (entry["resolved_path"], entry["sha256"], entry["bytes"]),
                "skill entrypoint changed during native episode")
