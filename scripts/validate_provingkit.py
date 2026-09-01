#!/usr/bin/env python3
"""Validate the source-stage Provingkit repository contract."""

from __future__ import annotations

import json
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path


DEFINITION_RELATIVE = Path("release/provingkit/definition-v1.json")
PROVENANCE_RELATIVE = Path("release/provingkit/cutover-provenance-v1.json")
COMMIT_MAP_RELATIVE = Path("release/provingkit/agents-commit-map.tsv")
HISTORICAL_IDENTITY_ALLOWLIST_RELATIVE = Path(
    "release/provingkit/historical-identity-allowlist-v1.json"
)
RELEASE_SCHEMA_RELATIVE = Path("release/provingkit/release-manifest-v1.schema.json")
CANONICAL_REPOSITORY = "https://github.com/nisavid/provingkit"
LEGACY_REPOSITORY = "https://github.com/nisavid" + "/agents"
LEGACY_REPOSITORY_SLUG = "nisavid" + "/agents"
LEGACY_IDENTITY_TOKENS = tuple(
    value.encode("ascii")
    for value in (
        LEGACY_REPOSITORY_SLUG,
        "github-nisavid-" + "agents",
        "agents-" + "stable",
        "nisavid-" + "agents",
    )
)
EXPECTED_MEMBERS = (
    (
        "rolecasting",
        "Rolecasting",
        "agent-plugin",
        "plugins/rolecasting/plugin.json",
        "plugins/rolecasting/.claude-plugin/plugin.json",
        "plugin-content-lock",
        "plugins/rolecasting/content-lock.json",
    ),
    (
        "tricritical",
        "Tricritical",
        "agent-plugin",
        "plugins/tricritical/plugin.json",
        "plugins/tricritical/.claude-plugin/plugin.json",
        "plugin-content-lock",
        "plugins/tricritical/content-lock.json",
    ),
    (
        "versionkeeping",
        "Versionkeeping",
        "agent-plugin",
        "plugins/versionkeeping/plugin.json",
        "plugins/versionkeeping/.claude-plugin/plugin.json",
        "plugin-content-lock",
        "release/plugin-content-locks/versionkeeping.json",
    ),
    (
        "mergecraft",
        "Mergecraft",
        "agent-plugin",
        "plugins/mergecraft/plugin.json",
        "plugins/mergecraft/.claude-plugin/plugin.json",
        "plugin-content-lock",
        "release/plugin-content-locks/mergecraft.json",
    ),
    (
        "artifact-customs",
        "Artifact Customs",
        "agent-plugin",
        "plugins/artifact-customs/plugin.json",
        "plugins/artifact-customs/.claude-plugin/plugin.json",
        "plugin-content-lock",
        "release/plugin-content-locks/artifact-customs.json",
    ),
    (
        "task-witness",
        "Task Witness",
        "code-only",
        "plugins/task-witness/plugin.json",
        "plugins/task-witness/.claude-plugin/plugin.json",
        "source-shape-review",
        "release/task-witness/source-shape-review.json",
    ),
)
EXPECTED_EXCLUDED_SOURCE = {
    "paths": [".scratch", "tooling"],
    "products": [
        "Base Loadout",
        "Hindsight",
        "personal tools",
        "unrelated experiments",
    ],
}
EXPECTED_SOURCE_ISSUES = (43, 44, 45, 52, 53, 56, 59, 65, 67, 79, 80)
RELEASE_CONTRACT_IDENTIFIER = "provingkit-release-manifest-v1"
RELEASE_CONTRACT_IDENTIFIER_ALLOWLIST = {
    RELEASE_SCHEMA_RELATIVE,
    Path("scripts/validate_provingkit.py"),
    Path("tests/test_validate_provingkit.py"),
}
MARKETPLACE_RELATIVE = Path(".claude-plugin/marketplace.json")
EXPECTED_MARKETPLACE = {
    "name": "provingkit",
    "owner": {"name": "Ivan D Vasin"},
    "description": (
        "Source projection for Provingkit's five Agent Plugins v1 members. "
        "This manifest is not a marketplace publication."
    ),
    "plugins": [
        {
            "name": member,
            "source": f"./plugins/{member}",
            "category": "developer-tools",
        }
        for member in (
            "rolecasting",
            "tricritical",
            "versionkeeping",
            "mergecraft",
            "artifact-customs",
        )
    ],
}
PYTEST_CONFIGURATION_RELATIVE = Path("pytest.ini")
EXPECTED_PYTEST_CONFIGURATION = (
    "[pytest]\ntestpaths = tests\nnorecursedirs = qualification/historical\n"
)


class ValidationError(ValueError):
    """The repository does not satisfy the Provingkit source contract."""


class _JsonObjectPairs(list[tuple[str, object]]):
    """Preserve every JSON member so duplicate contract keys remain visible."""


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    parsed: dict[str, object] = {}
    for key, value in pairs:
        if key in parsed:
            raise ValueError(f"duplicate JSON key: {key}")
        parsed[key] = value
    return parsed


def _reject_nonfinite(value: str) -> object:
    raise ValueError(f"non-finite JSON number: {value}")


def _load_json(path: Path, label: str) -> object:
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_nonfinite,
        )
    except (OSError, UnicodeError, ValueError) as error:
        raise ValidationError(f"{label} is unreadable") from error


def _sha256_uri(path: Path, label: str) -> str:
    try:
        return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"
    except OSError as error:
        raise ValidationError(f"{label} is unreadable") from error


def _validate_definition(repository: Path) -> None:
    path = repository / DEFINITION_RELATIVE
    if not path.is_file():
        raise ValidationError("versioned Provingkit definition is missing")
    definition = _load_json(path, "versioned Provingkit definition")
    if (
        not isinstance(definition, dict)
        or set(definition)
        != {
            "canonical_repository",
            "contract",
            "membership",
            "cutover_provenance",
            "excluded_source",
            "historical_identity_allowlist",
            "name",
            "release_manifest",
            "schema_version",
            "state",
        }
        or definition.get("contract") != "provingkit-definition-v1"
        or type(definition.get("schema_version")) is not int
        or definition["schema_version"] != 1
        or definition.get("name") != "Provingkit"
        or definition.get("canonical_repository") != CANONICAL_REPOSITORY
        or definition.get("state") != "source-stage-unreleased"
        or "version" in definition
        or definition.get("cutover_provenance") != PROVENANCE_RELATIVE.as_posix()
        or definition.get("historical_identity_allowlist")
        != HISTORICAL_IDENTITY_ALLOWLIST_RELATIVE.as_posix()
        or definition.get("excluded_source") != EXPECTED_EXCLUDED_SOURCE
    ):
        raise ValidationError("definition membership drift")
    if definition.get("release_manifest") != {
        "schema": RELEASE_SCHEMA_RELATIVE.as_posix(),
        "release_authority": "not-granted",
        "instances": [],
    }:
        raise ValidationError("definition release boundary drift")
    membership = definition.get("membership")
    if not isinstance(membership, dict) or set(membership) != {
        "all_members_required",
        "members",
        "mode",
        "partial_selection_is_provingkit",
    }:
        raise ValidationError("definition membership drift")
    members = membership.get("members")
    if not isinstance(members, list) or len(members) != len(EXPECTED_MEMBERS):
        raise ValidationError("definition membership drift")
    for member in members:
        if (
            not isinstance(member, dict)
            or set(member)
            != {
                "content_identity",
                "display_name",
                "distribution_kind",
                "id",
                "identity_manifests",
                "version",
            }
            or not isinstance(member.get("identity_manifests"), dict)
            or set(member["identity_manifests"]) != {"canonical", "claude"}
            or not isinstance(member.get("content_identity"), dict)
            or set(member["content_identity"]) != {"kind", "path", "sha256"}
        ):
            raise ValidationError("definition membership drift")
    observed = tuple(
        (
            member.get("id"),
            member.get("display_name"),
            member.get("distribution_kind"),
            member["identity_manifests"].get("canonical"),
            member["identity_manifests"].get("claude"),
            member["content_identity"].get("kind"),
            member["content_identity"].get("path"),
        )
        for member in members
    )
    if (
        observed != EXPECTED_MEMBERS
        or membership.get("mode") != "exact"
        or membership.get("all_members_required") is not True
        or membership.get("partial_selection_is_provingkit") is not False
    ):
        raise ValidationError("definition membership drift")
    for member, expected in zip(members, EXPECTED_MEMBERS, strict=True):
        (
            member_id,
            _,
            _,
            canonical_relative,
            claude_relative,
            _,
            content_identity_relative,
        ) = expected
        version = member.get("version")
        canonical_manifest = _load_json(
            repository / canonical_relative, "canonical member manifest"
        )
        claude_manifest = _load_json(
            repository / claude_relative, "Claude member manifest"
        )
        if (
            not isinstance(version, str)
            or re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version) is None
            or not isinstance(canonical_manifest, dict)
            or not isinstance(claude_manifest, dict)
            or canonical_manifest.get("name") != member_id
            or claude_manifest.get("name") != member_id
            or canonical_manifest.get("version") != version
            or claude_manifest.get("version") != version
        ):
            raise ValidationError("member identity drift")
        content_identity = member.get("content_identity")
        if not isinstance(content_identity, dict) or content_identity.get(
            "sha256"
        ) != _sha256_uri(
            repository / content_identity_relative,
            "member content identity",
        ):
            raise ValidationError("member content identity drift")
        expected_homepage = f"{CANONICAL_REPOSITORY}/tree/main/plugins/{member_id}"
        interface = (
            canonical_manifest.get("extensions", {})
            .get("com.openai", {})
            .get("interface", {})
        )
        if (
            canonical_manifest.get("repository") != CANONICAL_REPOSITORY
            or canonical_manifest.get("homepage") != expected_homepage
            or claude_manifest.get("repository") != CANONICAL_REPOSITORY
            or claude_manifest.get("homepage") != expected_homepage
            or not isinstance(interface, dict)
            or interface.get("websiteURL") != expected_homepage
        ):
            raise ValidationError("canonical repository identity drift")


def _validate_cutover_provenance(repository: Path) -> None:
    provenance = _load_json(
        repository / PROVENANCE_RELATIVE,
        "Provingkit cutover provenance",
    )
    if not isinstance(provenance, dict):
        raise ValidationError("cutover provenance drift")
    source = provenance.get("source_repository")
    if not isinstance(source, dict) or set(source) != {
        "cutover_baseline",
        "identity",
        "retained_extraction_input",
    }:
        raise ValidationError("cutover provenance drift")
    if (
        set(provenance)
        != {
            "adopted_qualification_history",
            "compatibility_aliases",
            "contract",
            "excluded_source",
            "historical_artifacts",
            "history_filter",
            "issue_migration",
            "release_resources",
            "schema_version",
            "source_repository",
        }
        or provenance.get("contract") != "provingkit-cutover-provenance-v1"
        or type(provenance.get("schema_version")) is not int
        or provenance["schema_version"] != 1
        or source.get("identity") != LEGACY_REPOSITORY
        or source.get("cutover_baseline")
        != {
            "original_commit": "44ee979cdae1d47f2ef3fdc713eaa6f04adf9892",
            "filtered_commit": "7dd8273ecab621be662d27c38706e33f2b48ae34",
        }
        or source.get("retained_extraction_input")
        != {
            "kind": "pull-request",
            "number": 69,
            "url": LEGACY_REPOSITORY + "/pull/69",
            "state": "open-unmerged",
            "production_disposition": "retained-input-not-accepted-behavior",
            "original_head": "02e3c721bdbd922883948bb3af84c5bafd702984",
            "filtered_head": "8edaf590736621352262457752d087bad835555d",
            "destination_ref": "refs/heads/retained/agents-pr-69",
        }
        or provenance.get("excluded_source")
        != {
            **EXPECTED_EXCLUDED_SOURCE,
            "repository_disposition": "retained-in-" + "nisavid-" + "agents",
        }
        or provenance.get("release_resources")
        != {"authority": "not-granted", "created": []}
    ):
        raise ValidationError("cutover provenance drift")

    history_filter = provenance.get("history_filter")
    if not isinstance(history_filter, dict) or set(history_filter) != {
        "commit_map",
        "full_repository_mirror",
        "method",
    }:
        raise ValidationError("cutover provenance drift")
    commit_map = history_filter.get("commit_map")
    expected_map_sha256 = (
        "sha256:eae83701b88ce2489b2bc4c373a90dc94f22040ec8af396fc040a01c6d9ec65f"
    )
    if (
        history_filter.get("method") != "git-filter-repo-path-projection-with-credential-fixture-sanitization"
        or history_filter.get("full_repository_mirror") is not False
        or commit_map
        != {
            "path": COMMIT_MAP_RELATIVE.as_posix(),
            "sha256": expected_map_sha256,
        }
        or _sha256_uri(repository / COMMIT_MAP_RELATIVE, "filtered commit map")
        != expected_map_sha256
    ):
        raise ValidationError("filtered commit map drift")
    try:
        map_lines = (
            (repository / COMMIT_MAP_RELATIVE).read_text(encoding="ascii").splitlines()
        )
        observed_map = dict(line.split() for line in map_lines[1:])
    except (OSError, UnicodeError, ValueError) as error:
        raise ValidationError("filtered commit map drift") from error
    expected_mappings = {
        "44ee979cdae1d47f2ef3fdc713eaa6f04adf9892": (
            "7dd8273ecab621be662d27c38706e33f2b48ae34"
        ),
        "02e3c721bdbd922883948bb3af84c5bafd702984": (
            "8edaf590736621352262457752d087bad835555d"
        ),
        "7064b02f3e7466eb3863040908186fc91df4a24e": (
            "e881043b57fe2242249561b9352e0335c537e30a"
        ),
        "a8410babc9e1b0c2a57b9f69db98a495133f6843": (
            "f9cefb0b3bdb2798791a5fd02907a79e43f38e67"
        ),
        "7fb6797033a619d79180bf256c661926218de26f": (
            "37add2e258fcf6e11eb057feadcf8ee51b4a2470"
        ),
        "0703e8df26c975a187cb6f36b8dfb21df8bcc6db": (
            "5d831beeb147072b815f80643400f0a60c8654ce"
        ),
    }
    if any(observed_map.get(old) != new for old, new in expected_mappings.items()):
        raise ValidationError("filtered commit map drift")

    adopted = provenance.get("adopted_qualification_history")
    expected_adopted = [
        {
            "platform": "linux",
            "source_branch": "refs/heads/ivan/task-witness-linux-qualification-harness",
            "source_range": {
                "commit_count": 21,
                "first_commit": "7064b02f3e7466eb3863040908186fc91df4a24e",
                "last_commit": "a8410babc9e1b0c2a57b9f69db98a495133f6843",
            },
            "filtered_source_range": {
                "first_commit": "e881043b57fe2242249561b9352e0335c537e30a",
                "last_commit": "f9cefb0b3bdb2798791a5fd02907a79e43f38e67",
            },
            "destination_range": {
                "first_commit": "56af80454bd356097f264bd81f0920234ae17bfc",
                "last_commit": "510662ed1df6a3eb24a2457648b4b9c5f6a8d066",
            },
            "historical_paths": [
                "qualification/historical/workflows/task-witness-linux-qualification.yml",
                "qualification/historical/scripts/harden_task_witness_linux_host.bash",
                "qualification/historical/scripts/prepare_task_witness_linux_qualification.py",
                "qualification/historical/tests/test_harden_task_witness_linux_host.bash",
                "qualification/historical/tests/test_task_witness_linux_qualification_harness.py",
            ],
            "evidence_disposition": "historical-stale-not-current-qualification",
        },
        {
            "platform": "macos",
            "source_branch": "refs/heads/ivan/task-witness-macos-qualification-harness",
            "source_range": {
                "commit_count": 36,
                "first_commit": "7fb6797033a619d79180bf256c661926218de26f",
                "last_commit": "0703e8df26c975a187cb6f36b8dfb21df8bcc6db",
            },
            "filtered_source_range": {
                "first_commit": "37add2e258fcf6e11eb057feadcf8ee51b4a2470",
                "last_commit": "5d831beeb147072b815f80643400f0a60c8654ce",
            },
            "destination_range": {
                "first_commit": "20f27835fec4e30d3ed171925e78f56945fd4487",
                "last_commit": "604c6e8702c4e3914e862bee58ab35f529866737",
            },
            "historical_paths": [
                "qualification/historical/workflows/task-witness-macos-host-probe.yml",
                "qualification/historical/scripts/probe_task_witness_macos_host.py",
                "qualification/historical/tests/test_task_witness_macos_host_probe.py",
            ],
            "evidence_disposition": "historical-stale-not-current-qualification",
        },
    ]
    if adopted != expected_adopted:
        raise ValidationError("cutover provenance drift")

    expected_compatibility_aliases = [
        {
            "kind": "repository",
            "legacy": LEGACY_REPOSITORY,
            "canonical": CANONICAL_REPOSITORY,
            "scope": "historical-links-only",
        },
        {
            "kind": "marketplace-source-name",
            "legacy": "nisavid-" + "agents",
            "canonical": "provingkit",
            "scope": "historical-source-metadata",
        },
        {
            "kind": "qualification-issuer",
            "legacy": "github-nisavid-" + "agents",
            "canonical": "github-nisavid-provingkit",
            "scope": "frozen-receipts",
        },
        {
            "kind": "source-selector",
            "legacy": "agents-" + "stable",
            "canonical": "provingkit-stable",
            "scope": "frozen-receipts",
        },
    ]
    if provenance.get("compatibility_aliases") != expected_compatibility_aliases:
        raise ValidationError("cutover provenance drift")

    migration = provenance.get("issue_migration")
    entries = migration.get("entries") if isinstance(migration, dict) else None
    if (
        not isinstance(entries, list)
        or any(not isinstance(entry, dict) for entry in entries)
        or set(migration)
        != {
            "source_repository",
            "destination_repository",
            "method",
            "state",
            "entries",
        }
        or migration.get("source_repository") != LEGACY_REPOSITORY_SLUG
        or migration.get("destination_repository") != "nisavid/provingkit"
        or migration.get("method") != "github-native-transfer"
        or tuple(entry.get("source_issue") for entry in entries)
        != EXPECTED_SOURCE_ISSUES
    ):
        raise ValidationError("issue migration ledger drift")
    for entry in entries:
        state = entry.get("state")
        destination_issue = entry.get("destination_issue")
        if not (
            set(entry) == {"source_issue", "destination_issue", "state"}
            and (
                (state == "pending-native-transfer" and destination_issue is None)
                or (
                    state == "transferred"
                    and isinstance(destination_issue, int)
                    and not isinstance(destination_issue, bool)
                    and destination_issue > 0
                )
            )
        ):
            raise ValidationError("issue migration ledger drift")
    entry_states = {entry["state"] for entry in entries}
    expected_migration_state = (
        "pending-native-transfer"
        if entry_states == {"pending-native-transfer"}
        else "transferred"
        if entry_states == {"transferred"}
        else "partial-native-transfer"
    )
    if migration.get("state") != expected_migration_state:
        raise ValidationError("issue migration ledger drift")
    destination_issues = [
        entry["destination_issue"]
        for entry in entries
        if entry["destination_issue"] is not None
    ]
    if len(destination_issues) != len(set(destination_issues)):
        raise ValidationError("issue migration ledger drift")

    issue_45 = next(entry for entry in entries if entry["source_issue"] == 45)
    owner_issue = (
        LEGACY_REPOSITORY + "/issues/45"
        if issue_45["state"] == "pending-native-transfer"
        else CANONICAL_REPOSITORY + f"/issues/{issue_45['destination_issue']}"
    )
    if provenance.get("historical_artifacts") != [
        {
            "path": "release/source-skill-lineage/source-manifest.json",
            "disposition": "historical-stale-pending-provingkit-rescout",
            "owner_issue": owner_issue,
        }
    ]:
        raise ValidationError("cutover provenance drift")


def _validate_excluded_source(repository: Path) -> None:
    prohibited = (
        Path(".scratch"),
        Path("tooling"),
        Path("plugins/base-loadout"),
        Path("plugins/hindsight"),
    )
    if any((repository / relative).exists() for relative in prohibited):
        raise ValidationError("excluded source present")
    plugin_root = repository / "plugins"
    try:
        observed_plugins = {
            path.name for path in plugin_root.iterdir() if path.is_dir()
        }
    except OSError as error:
        raise ValidationError("member source root is unreadable") from error
    if observed_plugins != {member[0] for member in EXPECTED_MEMBERS}:
        raise ValidationError("excluded source present")


def _validate_historical_identities(repository: Path) -> None:
    allowlist = _load_json(
        repository / HISTORICAL_IDENTITY_ALLOWLIST_RELATIVE,
        "historical identity allowlist",
    )
    if (
        not isinstance(allowlist, dict)
        or set(allowlist) != {"contract", "entries", "matching", "schema_version"}
        or allowlist.get("contract") != "provingkit-historical-identity-allowlist-v1"
        or type(allowlist.get("schema_version")) is not int
        or allowlist["schema_version"] != 1
        or allowlist.get("matching") != "exact-relative-path-and-whole-file-sha256"
        or not isinstance(allowlist.get("entries"), list)
    ):
        raise ValidationError("historical identity allowlist drift")

    entries = allowlist["entries"]
    allowed: dict[str, dict[str, object]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {
            "disposition",
            "path",
            "sha256",
        }:
            raise ValidationError("historical identity allowlist drift")
        relative = entry.get("path")
        if not isinstance(relative, str):
            raise ValidationError("historical identity allowlist drift")
        relative_path = Path(relative)
        if (
            relative_path.is_absolute()
            or ".." in relative_path.parts
            or relative_path.as_posix() != relative
            or relative == HISTORICAL_IDENTITY_ALLOWLIST_RELATIVE.as_posix()
            or relative in allowed
            or not isinstance(entry.get("disposition"), str)
            or not entry["disposition"]
            or not isinstance(entry.get("sha256"), str)
            or re.fullmatch(r"sha256:[0-9a-f]{64}", entry["sha256"]) is None
        ):
            raise ValidationError("historical identity allowlist drift")
        allowed[relative] = entry
    if list(allowed) != sorted(allowed):
        raise ValidationError("historical identity allowlist drift")

    observed: dict[str, bytes] = {}
    try:
        candidates = sorted(repository.rglob("*"))
    except OSError as error:
        raise ValidationError("repository identity scan failed") from error
    for path in candidates:
        relative_path = path.relative_to(repository)
        if ".git" in relative_path.parts or "__pycache__" in relative_path.parts:
            continue
        if path.is_symlink():
            raise ValidationError("repository identity scan rejects symbolic links")
        if (
            not path.is_file()
            or relative_path == HISTORICAL_IDENTITY_ALLOWLIST_RELATIVE
        ):
            continue
        try:
            content = path.read_bytes()
        except OSError as error:
            raise ValidationError("repository identity scan failed") from error
        if any(token in content for token in LEGACY_IDENTITY_TOKENS):
            observed[relative_path.as_posix()] = content

    unexpected = sorted(set(observed) - set(allowed))
    if unexpected:
        raise ValidationError(
            "unallowlisted legacy repository identity: " + ", ".join(unexpected)
        )
    if set(allowed) != set(observed):
        raise ValidationError("historical identity allowlist drift")
    for relative, entry in allowed.items():
        digest = "sha256:" + hashlib.sha256(observed[relative]).hexdigest()
        if entry.get("sha256") != digest:
            raise ValidationError("historical identity allowlist hash drift")


def _validate_release_boundary(repository: Path) -> None:
    schema = _load_json(
        repository / RELEASE_SCHEMA_RELATIVE,
        "Provingkit release-manifest schema",
    )
    if (
        not isinstance(schema, dict)
        or schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema"
        or schema.get("$id")
        != (
            "https://raw.githubusercontent.com/nisavid/provingkit/main/"
            "release/provingkit/release-manifest-v1.schema.json"
        )
        or schema.get("title") != "Provingkit immutable release manifest v1"
    ):
        raise ValidationError("release-manifest schema drift")
    try:
        from jsonschema import Draft202012Validator
        from jsonschema.exceptions import SchemaError
    except ImportError as error:
        raise ValidationError(
            "jsonschema is required to validate the release-manifest schema"
        ) from error
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        raise ValidationError("release-manifest schema is invalid") from error
    try:
        candidate_paths = sorted(repository.rglob("*"))
    except OSError as error:
        raise ValidationError("release manifest boundary is unreadable") from error
    for path in candidate_paths:
        relative = path.relative_to(repository)
        if (
            not path.is_file()
            or ".git" in relative.parts
            or "__pycache__" in relative.parts
        ):
            continue
        try:
            content = path.read_bytes()
        except OSError as error:
            raise ValidationError("release manifest boundary is unreadable") from error
        if (
            path.name.startswith("release-manifest-")
            and relative != RELEASE_SCHEMA_RELATIVE
        ):
            raise ValidationError("release manifest instance is not authorized")
        if (
            RELEASE_CONTRACT_IDENTIFIER.encode("ascii") in content
            and relative not in RELEASE_CONTRACT_IDENTIFIER_ALLOWLIST
        ):
            raise ValidationError("release manifest instance is not authorized")
        try:
            candidate = json.loads(
                content.decode("utf-8"),
                object_pairs_hook=_JsonObjectPairs,
            )
        except (UnicodeError, ValueError):
            continue
        if (
            isinstance(candidate, _JsonObjectPairs)
            and any(
                key == "contract" and value == RELEASE_CONTRACT_IDENTIFIER
                for key, value in candidate
            )
            and relative != RELEASE_SCHEMA_RELATIVE
        ):
            raise ValidationError("release manifest instance is not authorized")


def _validate_marketplace(repository: Path) -> None:
    marketplace = _load_json(
        repository / MARKETPLACE_RELATIVE,
        "Provingkit marketplace source projection",
    )
    if marketplace != EXPECTED_MARKETPLACE:
        raise ValidationError("marketplace source projection drift")


def _run_git(repository: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    for name in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    ):
        environment.pop(name, None)
    try:
        return subprocess.run(
            ["git", "-C", str(repository), *arguments],
            text=True,
            capture_output=True,
            check=False,
            timeout=15,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValidationError("Git history attestation unavailable") from error


def _require_git_output(repository: Path, *arguments: str) -> str:
    result = _run_git(repository, *arguments)
    if result.returncode != 0:
        raise ValidationError("Git history attestation unavailable")
    return result.stdout.strip()


def _validate_history(repository: Path) -> None:
    top_level = _require_git_output(repository, "rev-parse", "--show-toplevel")
    try:
        if Path(top_level).resolve(strict=True) != repository.resolve(strict=True):
            raise ValidationError("Git history attestation unavailable")
    except OSError as error:
        raise ValidationError("Git history attestation unavailable") from error
    if (
        _require_git_output(repository, "rev-parse", "--is-shallow-repository")
        != "false"
    ):
        raise ValidationError("Git history attestation requires a complete repository")
    if _require_git_output(
        repository,
        "for-each-ref",
        "--format=%(refname)",
        "refs/replace",
    ):
        raise ValidationError("Git history attestation rejects replacement objects")

    baseline = "7dd8273ecab621be662d27c38706e33f2b48ae34"
    retained = "8edaf590736621352262457752d087bad835555d"
    linux_first = "56af80454bd356097f264bd81f0920234ae17bfc"
    linux_last = "510662ed1df6a3eb24a2457648b4b9c5f6a8d066"
    macos_first = "20f27835fec4e30d3ed171925e78f56945fd4487"
    macos_last = "604c6e8702c4e3914e862bee58ab35f529866737"
    for commit in (
        baseline,
        retained,
        linux_first,
        linux_last,
        macos_first,
        macos_last,
        "HEAD",
    ):
        _require_git_output(repository, "rev-parse", "--verify", f"{commit}^{{commit}}")

    if (
        _require_git_output(repository, "rev-parse", f"{linux_first}^") != baseline
        or _require_git_output(
            repository, "rev-list", "--count", f"{baseline}..{linux_last}"
        )
        != "21"
        or _require_git_output(repository, "rev-parse", f"{macos_first}^") != linux_last
        or _require_git_output(
            repository,
            "rev-list",
            "--count",
            f"{linux_last}..{macos_last}",
        )
        != "36"
    ):
        raise ValidationError("Git history attestation drift")
    for ancestor, descendant in ((baseline, "HEAD"), (macos_last, "HEAD")):
        ancestry = _run_git(
            repository,
            "merge-base",
            "--is-ancestor",
            ancestor,
            descendant,
        )
        if ancestry.returncode != 0:
            raise ValidationError("Git history attestation drift")

    retained_ancestry = _run_git(
        repository,
        "merge-base",
        "--is-ancestor",
        retained,
        "HEAD",
    )
    if retained_ancestry.returncode == 0:
        raise ValidationError("retained extraction input was accepted into HEAD")
    if retained_ancestry.returncode != 1:
        raise ValidationError("Git history attestation unavailable")

    retained_refs = (
        "refs/heads/retained/agents-pr-69",
        "refs/remotes/origin/retained/agents-pr-69",
    )
    observed_refs = {
        result.stdout.strip()
        for ref in retained_refs
        if (
            result := _run_git(repository, "show-ref", "--verify", "--hash", ref)
        ).returncode
        == 0
    }
    if retained not in observed_refs:
        raise ValidationError("retained extraction-input ref attestation drift")

    ref_inventory = _require_git_output(
        repository,
        "for-each-ref",
        "--format=%(refname) %(objectname)",
        "refs/heads",
        "refs/remotes/origin",
    ).splitlines()
    if not ref_inventory:
        raise ValidationError("destination ref inventory is empty")
    for record in ref_inventory:
        try:
            ref_name, object_id = record.split()
        except ValueError as error:
            raise ValidationError("destination ref inventory drift") from error
        _require_git_output(
            repository, "rev-parse", "--verify", f"{object_id}^{{commit}}"
        )
        if ref_name in retained_refs:
            if object_id != retained:
                raise ValidationError("retained extraction-input ref attestation drift")
            continue
        retained_in_ref = _run_git(
            repository,
            "merge-base",
            "--is-ancestor",
            retained,
            object_id,
        )
        if retained_in_ref.returncode == 0:
            raise ValidationError("retained extraction input was accepted into a ref")
        if retained_in_ref.returncode != 1:
            raise ValidationError("Git history attestation unavailable")

    tags = _require_git_output(
        repository,
        "for-each-ref",
        "--format=%(refname)",
        "refs/tags",
    )
    if tags:
        raise ValidationError("source-stage repository contains an unauthorized tag")

    history_paths = _require_git_output(
        repository,
        "log",
        "--format=",
        "--name-only",
        "-z",
        "--all",
    ).split("\0")
    prohibited_history_roots = (
        ".scratch",
        "tooling",
        "base-loadout",
        "hindsight",
        "plugins/base-loadout",
        "plugins/hindsight",
    )
    if any(
        path == root or path.startswith(root + "/")
        for path in history_paths
        for root in prohibited_history_roots
    ):
        raise ValidationError("excluded source is reachable in published history")


def _validate_historical_qualification_boundary(repository: Path) -> None:
    try:
        configuration = (repository / PYTEST_CONFIGURATION_RELATIVE).read_text(
            encoding="utf-8"
        )
    except (OSError, UnicodeError) as error:
        raise ValidationError(
            "historical qualification discovery boundary is missing"
        ) from error
    if configuration != EXPECTED_PYTEST_CONFIGURATION:
        raise ValidationError("historical qualification discovery boundary drift")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: validate_provingkit.py REPOSITORY", file=sys.stderr)
        return 2
    repository = Path(argv[1])
    if not repository.is_dir():
        print("Provingkit repository is not a directory", file=sys.stderr)
        return 1
    try:
        _validate_definition(repository)
        _validate_excluded_source(repository)
        _validate_marketplace(repository)
        _validate_cutover_provenance(repository)
        _validate_historical_qualification_boundary(repository)
        _validate_historical_identities(repository)
        _validate_release_boundary(repository)
        _validate_history(repository)
    except ValidationError as error:
        print(str(error), file=sys.stderr)
        return 1
    print("Provingkit source validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
