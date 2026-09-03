#!/usr/bin/env python3
"""Validate the source-stage Provingkit repository contract."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
import subprocess
import sys
from html import unescape as unescape_html
from pathlib import Path
from urllib.parse import unquote_to_bytes

try:
    import idna
except ModuleNotFoundError:
    idna = None


DEFINITION_RELATIVE = Path("release/provingkit/definition-v1.json")
PROVENANCE_RELATIVE = Path("release/provingkit/cutover-provenance-v1.json")
COMMIT_MAP_RELATIVE = Path("release/provingkit/agents-commit-map.tsv")
ADOPTED_HISTORY_IMPORT_MAP_RELATIVE = Path(
    "release/provingkit/adopted-history-import-map-v1.tsv"
)
ADOPTED_HISTORY_DELTA_BUNDLE_RELATIVE = Path(
    "release/provingkit/adopted-history-delta-bundle-v1.json"
)
HISTORICAL_IDENTITY_ALLOWLIST_RELATIVE = Path(
    "release/provingkit/historical-identity-allowlist-v1.json"
)
RELEASE_SCHEMA_RELATIVE = Path("release/provingkit/release-manifest-v1.schema.json")
CANONICAL_REPOSITORY = "https://github.com/nisavid/provingkit"
LEGACY_REPOSITORY = "https://github.com/nisavid" + "/agents"
LEGACY_REPOSITORY_SLUG = "nisavid" + "/agents"
AGENTS_ISSUE_50 = f"{LEGACY_REPOSITORY}/issues/50"
AGENTS_ISSUE_51 = f"{LEGACY_REPOSITORY}/issues/51"
SOURCE_DISPOSITION_LEDGER_RELATIVE = Path(
    "release/source-skill-disposition/disposition-ledger.json"
)
SOURCE_DISPOSITION_REFRESH_RELATIVE = Path(
    "release/source-skill-disposition/release-refresh-contract.json"
)
ACTIVE_LEGACY_REPOSITORY_GUIDANCE_RELATIVE = Path("CONTEXT.md")
LEGACY_IDENTITY_TOKENS = tuple(
    value.encode("ascii")
    for value in (
        LEGACY_REPOSITORY_SLUG,
        "github-nisavid-" + "agents",
        "agents-" + "stable",
        "nisavid-" + "agents",
    )
)
IDENTITY_SCAN_MAX_DECODE_PASSES = 8
JSON_ASCII_ESCAPE_PATTERN = re.compile(rb"\\u00([0-7][0-9A-Fa-f])")
SPECIAL_URL_IGNORED_CONTROL_PATTERN = rb"(?:[\t\r\n]|\\(?:[tnr]|u000[9AaDd]))*"
SPECIAL_URL_START_PATTERN = re.compile(
    rb"(?<![A-Za-z0-9+._-])"
    rb"h"
    + SPECIAL_URL_IGNORED_CONTROL_PATTERN
    + rb"t"
    + SPECIAL_URL_IGNORED_CONTROL_PATTERN
    + rb"t"
    + SPECIAL_URL_IGNORED_CONTROL_PATTERN
    + rb"p"
    + SPECIAL_URL_IGNORED_CONTROL_PATTERN
    + rb"(?:s"
    + SPECIAL_URL_IGNORED_CONTROL_PATTERN
    + rb")?:",
    re.IGNORECASE,
)
JSON_URL_IGNORED_CONTROL_ESCAPE_PATTERN = re.compile(
    rb"\\(?:[tnr]|u000[9AaDd])",
    re.IGNORECASE,
)
SPECIAL_URL_TOKEN_PATTERN = re.compile(
    rb"[^\x00-\x20\"'<>,;()\[\]{}|`]+"
)
SPECIAL_URL_PATH_HARD_DELIMITERS = frozenset(
    b" \t\r\n\f\v\"'<>,;()[]{}|`"
)
ACTIVE_LEGACY_REPOSITORY_GUIDANCE_BLOCK = (
    "**Base Loadout**:\n"
    f"The portable declaration in `{LEGACY_REPOSITORY_SLUG}` that selects a "
    "Provingkit release; it is that repository's only Loadout.\n"
    "_Avoid_: Profile, preset\n\n"
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
EXPECTED_CUTOVER_MEMBER_VERSIONS = {
    "rolecasting": "1.0.0",
    "tricritical": "1.0.0",
    "versionkeeping": "1.0.0",
    "mergecraft": "1.0.0",
    "artifact-customs": "1.0.0",
    "task-witness": "1.0.0",
}
EXPECTED_EXCLUDED_SOURCE = {
    "paths": [".scratch", "tooling"],
    "products": [
        "Base Loadout",
        "Hindsight",
        "personal tools",
        "unrelated experiments",
    ],
}
EXPECTED_SOURCE_ISSUES = (43, 44, 45, 52, 53, 56, 59, 65, 79, 80)
EXPECTED_HISTORY_RELOCATIONS = (
    (
        ".github/workflows/task-witness-linux-qualification.yml",
        "qualification/historical/workflows/task-witness-linux-qualification.yml",
        "a431199bc2a542786d13a06904715dfbb4459250",
    ),
    (
        "scripts/harden_task_witness_linux_host.bash",
        "qualification/historical/scripts/harden_task_witness_linux_host.bash",
        "5e5283830a8bfbd8c6e5d397099a8da708631846",
    ),
    (
        "scripts/prepare_task_witness_linux_qualification.py",
        "qualification/historical/scripts/prepare_task_witness_linux_qualification.py",
        "140e27a5babc9b69d2011511f6fa7d88d12af6a0",
    ),
    (
        "tests/test_harden_task_witness_linux_host.bash",
        "qualification/historical/tests/test_harden_task_witness_linux_host.bash",
        "b8c3adbea9c5889130fac2ade4affda0b97f816b",
    ),
    (
        "tests/test_task_witness_linux_qualification_harness.py",
        "qualification/historical/tests/test_task_witness_linux_qualification_harness.py",
        "8fe8cdde6e27f96f25931e18ce16b39f66c36a47",
    ),
    (
        ".github/workflows/task-witness-macos-host-probe.yml",
        "qualification/historical/workflows/task-witness-macos-host-probe.yml",
        "07e5e25aabdcd6d31d1931a6e4faba1e3040d40c",
    ),
    (
        "scripts/probe_task_witness_macos_host.py",
        "qualification/historical/scripts/probe_task_witness_macos_host.py",
        "8f3692bfcdb08558a3e9fcfb68054b7458613c7d",
    ),
    (
        "tests/test_task_witness_macos_host_probe.py",
        "qualification/historical/tests/test_task_witness_macos_host_probe.py",
        "06f2ba91a0e14453084d60d2781df765eb28b2ca",
    ),
)
EXPECTED_HISTORY_SOURCE_ROOTS = (
    (
        "linux",
        "refs/heads/ivan/task-witness-linux-qualification-harness",
        "a8410babc9e1b0c2a57b9f69db98a495133f6843",
    ),
    (
        "macos",
        "refs/heads/ivan/task-witness-macos-qualification-harness",
        "0703e8df26c975a187cb6f36b8dfb21df8bcc6db",
    ),
)
ADOPTED_HISTORY_DELTA_BUNDLE_SHA256 = (
    "sha256:c9f5e9a2f9cfee80e943eeb859d4f5b072f98150e7018e474710f709c6e1b9ae"
)
ADOPTED_HISTORY_DELTA_CONTENT_SHA256 = (
    "sha256:d14da319649492e7ecb64d20a578983cb2cd88e00a5e4d3a1ed7e49a1a526cc5"
)
ADOPTED_HISTORY_IMPORT_TIP = "caf9a58769af746fd5b514beff5cb305788f7e1c"
OID_SHA1_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
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
    "pythonpath = .\n"
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


def _strip_reference_once(value: object, reference: str) -> str:
    if not isinstance(value, str):
        raise ValidationError("active legacy tracker reference scope drift")
    pattern = re.compile(
        r"(?<![A-Za-z0-9._~:/?#\[\]@!$&'*+,;=%-])"
        + re.escape(reference)
        + r"(?![A-Za-z0-9._~:/?#\[\]@!$&'*+,;=%-])"
    )
    if len(pattern.findall(value)) != 1:
        raise ValidationError("active legacy tracker reference scope drift")
    return pattern.sub("", value)


def _identity_scan_content(relative_path: Path, content: bytes) -> bytes:
    if relative_path == ACTIVE_LEGACY_REPOSITORY_GUIDANCE_RELATIVE:
        try:
            guidance = content.decode("utf-8")
        except UnicodeError as error:
            raise ValidationError(
                "active legacy repository guidance scope drift"
            ) from error
        if guidance.count(ACTIVE_LEGACY_REPOSITORY_GUIDANCE_BLOCK) != 1:
            raise ValidationError("active legacy repository guidance scope drift")
        return guidance.replace(
            ACTIVE_LEGACY_REPOSITORY_GUIDANCE_BLOCK,
            ACTIVE_LEGACY_REPOSITORY_GUIDANCE_BLOCK.replace(
                LEGACY_REPOSITORY_SLUG,
                "",
            ),
            1,
        ).encode("utf-8")
    if relative_path not in {
        SOURCE_DISPOSITION_LEDGER_RELATIVE,
        SOURCE_DISPOSITION_REFRESH_RELATIVE,
    }:
        return content
    try:
        parsed = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_nonfinite,
        )
        if not isinstance(parsed, dict):
            raise TypeError
        if relative_path == SOURCE_DISPOSITION_LEDGER_RELATIVE:
            dispositions = parsed["dispositions"]
            records = [
                record
                for record in dispositions
                if isinstance(record, dict)
                and record.get("contribution_id")
                == "superpowers-contribution-unresolved"
            ]
            if len(records) != 1:
                raise ValueError
            record = records[0]
            if record.get("follow_up_issues") != [AGENTS_ISSUE_51]:
                raise ValueError
            record["follow_up_issues"] = [""]
            skill_records = [
                item
                for item in record["skill_dispositions"]
                if isinstance(item, dict)
                and item.get("skill_ids") == ["systematic-debugging"]
            ]
            if len(skill_records) != 1:
                raise ValueError
            skill_records[0]["rationale"] = _strip_reference_once(
                skill_records[0].get("rationale"), AGENTS_ISSUE_51
            )
        else:
            follow_ups = parsed["follow_up_issues"]
            if (
                not isinstance(follow_ups, list)
                or not follow_ups
                or not isinstance(follow_ups[0], dict)
                or follow_ups[0].get("issue") != AGENTS_ISSUE_51
            ):
                raise ValueError
            follow_ups[0]["issue"] = ""
            workflow = parsed["workflow"]
            if (
                not isinstance(workflow, dict)
                or workflow.get("convergence_owner_issue") != AGENTS_ISSUE_51
                or workflow.get("source_disposition_owner_issue")
                != AGENTS_ISSUE_50
            ):
                raise ValueError
            workflow["convergence_owner_issue"] = ""
            workflow["source_disposition_owner_issue"] = ""
    except (KeyError, TypeError, UnicodeError, ValueError) as error:
        if isinstance(error, ValidationError):
            raise
        raise ValidationError("active legacy tracker reference scope drift") from error
    return json.dumps(parsed, ensure_ascii=False).encode("utf-8")


def _decode_identity_scan_syntax_once(content: bytes) -> bytes:
    decoded = content
    decoded = JSON_ASCII_ESCAPE_PATTERN.sub(
        lambda match: bytes((int(match.group(1), 16),)),
        decoded,
    )
    decoded = decoded.replace(b"\\/", b"/")
    text = decoded.decode("utf-8", errors="surrogateescape")
    return unescape_html(text).encode("utf-8", errors="surrogateescape")


def _decode_identity_scan_content_once(content: bytes) -> bytes:
    return _decode_identity_scan_syntax_once(unquote_to_bytes(content))


def _decode_identity_component(value: bytes) -> bytes:
    decoded = value
    for _ in range(IDENTITY_SCAN_MAX_DECODE_PASSES):
        next_value = unquote_to_bytes(decoded)
        if next_value == decoded:
            return decoded
        decoded = next_value
    if unquote_to_bytes(decoded) != decoded:
        raise ValidationError("repository identity encoding depth exceeds limit")
    return decoded


def _special_url_hard_delimiter(byte: int) -> bool:
    return byte <= 0x20 or byte in SPECIAL_URL_PATH_HARD_DELIMITERS


def _hard_path_segment_pop_end(source: bytes, hard_index: int) -> int | None:
    index = hard_index + 1
    depth = 1
    space_group = source[hard_index] in b" \t\f\v"
    text_after_space = False
    while index < len(source):
        segment_end = index
        while segment_end < len(source):
            byte = source[segment_end]
            if byte in b"/\\?#":
                break
            if byte in b"\r\n":
                return None
            if _special_url_hard_delimiter(byte):
                if byte in b" \t\f\v":
                    if space_group and text_after_space:
                        return None
                    space_group = True
                    text_after_space = False
                segment_end += 1
                continue
            if space_group:
                text_after_space = True
            segment_end += 1
        if segment_end == len(source) or source[segment_end] not in b"/\\":
            return None
        index = segment_end + 1
        next_segment_end = index
        while next_segment_end < len(source):
            if source[next_segment_end] in b"/\\?#" or _special_url_hard_delimiter(
                source[next_segment_end]
            ):
                break
            next_segment_end += 1
        segment = _decode_identity_component(source[index:next_segment_end])
        if segment == b"..":
            depth -= 1
            if depth == 0:
                return next_segment_end
        elif segment and segment != b".":
            depth += 1
        index = next_segment_end
    return None


def _special_url_candidate_end(source: bytes, scheme_end: int) -> int:
    index = scheme_end
    while index < len(source) and source[index] in b"/\\":
        index += 1

    authority_end = index
    while authority_end < len(source):
        json_control = JSON_URL_IGNORED_CONTROL_ESCAPE_PATTERN.match(
            source, authority_end
        )
        if json_control is not None:
            authority_end = json_control.end()
            continue
        if source[authority_end] in b"/\\?#":
            break
        authority_end += 1
    last_userinfo = source.rfind(b"@", index, authority_end)

    while index < len(source):
        json_control = JSON_URL_IGNORED_CONTROL_ESCAPE_PATTERN.match(source, index)
        if json_control is not None:
            index = json_control.end()
            continue
        byte = source[index]
        if byte in b"\t\r\n":
            index += 1
            continue
        if byte in b"/\\":
            index += 1
            break
        if byte in b"?#":
            while index < len(source) and not _special_url_hard_delimiter(
                source[index]
            ):
                index += 1
            return index
        if _special_url_hard_delimiter(byte):
            if last_userinfo < index:
                return index
        index += 1

    while index < len(source):
        json_control = JSON_URL_IGNORED_CONTROL_ESCAPE_PATTERN.match(source, index)
        if json_control is not None:
            index = json_control.end()
            continue
        byte = source[index]
        if byte in b"/\\":
            index += 1
            continue
        if byte in b"?#":
            while index < len(source) and not _special_url_hard_delimiter(
                source[index]
            ):
                index += 1
            return index
        if byte == ord("\t"):
            index += 1
            continue
        if _special_url_hard_delimiter(byte):
            record_boundary = byte in b"\r\n"
            pop_end = (
                None
                if record_boundary
                else _hard_path_segment_pop_end(source, index)
            )
            if pop_end is not None:
                index = pop_end
                continue
            return index
        index += 1
    return index


def _decode_url_literal_syntax(
    candidate: bytes,
    *,
    remove_json_controls: bool,
) -> bytes:
    decoded = candidate
    for _ in range(IDENTITY_SCAN_MAX_DECODE_PASSES):
        next_value = JSON_ASCII_ESCAPE_PATTERN.sub(
            lambda match: bytes((int(match.group(1), 16),)),
            decoded,
        )
        if remove_json_controls:
            next_value = JSON_URL_IGNORED_CONTROL_ESCAPE_PATTERN.sub(
                b"", next_value
            )
        next_value = next_value.translate(None, b"\t\r\n")
        next_value = next_value.replace(b"\\/", b"/")
        text = next_value.decode("utf-8", errors="surrogateescape")
        next_value = unescape_html(text).encode(
            "utf-8", errors="surrogateescape"
        )
        if next_value == decoded:
            return decoded.replace(b"\\", b"/")
        decoded = next_value
    return decoded.replace(b"\\", b"/")


def _canonical_github_path(special_url: bytes) -> bytes | None:
    remainder = special_url.partition(b":")[2].lstrip(b"/")
    delimiter_positions = [
        position
        for delimiter in (b"/", b"?", b"#")
        if (position := remainder.find(delimiter)) >= 0
    ]
    authority_end = min(delimiter_positions, default=len(remainder))
    authority = remainder[:authority_end]
    host_port = authority.rsplit(b"@", maxsplit=1)[-1]
    encoded_host = host_port
    possible_host, separator, possible_port = host_port.rpartition(b":")
    if separator:
        if possible_port:
            normalized_port = possible_port.lstrip(b"0") or b"0"
            if (
                not possible_port.isdigit()
                or len(normalized_port) > 5
                or (
                    len(normalized_port) == 5
                    and normalized_port > b"65535"
                )
            ):
                return None
        encoded_host = possible_host
    if idna is None:
        raise ValidationError("idna is required for URL identity validation")
    try:
        host = idna.encode(
            unquote_to_bytes(encoded_host).decode("utf-8"),
            uts46=True,
            std3_rules=True,
            transitional=False,
        ).lower()
    except (UnicodeError, idna.IDNAError):
        return None
    if host.endswith(b"."):
        host = host[:-1]
    if host != b"github.com":
        return None

    path = b""
    if remainder[authority_end : authority_end + 1] == b"/":
        path = re.split(rb"[?#]", remainder[authority_end:], maxsplit=1)[0]
    path = _decode_identity_component(path).replace(b"\\", b"/")
    segments: list[bytes] = []
    for segment in path.split(b"/"):
        if not segment or segment == b".":
            continue
        if segment == b"..":
            if segments:
                segments.pop()
            continue
        segments.append(segment)
    return b"/".join(segments) if segments else None


def _canonical_github_url_paths_from_source(source: bytes) -> list[bytes]:
    canonical_paths: list[bytes] = []
    search_start = 0
    while match := SPECIAL_URL_START_PATTERN.search(source, search_start):
        candidate_end = _special_url_candidate_end(source, match.end())
        candidate = source[match.start() : candidate_end]
        syntax_variants = {
            _decode_url_literal_syntax(
                candidate,
                remove_json_controls=remove_json_controls,
            )
            for remove_json_controls in (False, True)
        }
        for special_url in syntax_variants:
            canonical_path = _canonical_github_path(special_url)
            if canonical_path is not None:
                canonical_paths.append(canonical_path)
        search_start = max(candidate_end, match.end())
    return canonical_paths


def _json_string_values(content: bytes) -> list[bytes]:
    try:
        parsed = json.loads(
            content,
            parse_constant=lambda _value: None,
            parse_float=lambda _value: None,
            parse_int=lambda _value: None,
        )
    except (json.JSONDecodeError, UnicodeDecodeError, RecursionError, ValueError):
        return []
    values: list[bytes] = []
    pending = [parsed]
    while pending:
        value = pending.pop()
        if isinstance(value, str):
            start = 0
            for index, character in enumerate(value):
                if 0xD800 <= ord(character) <= 0xDFFF:
                    if start < index:
                        values.append(value[start:index].encode("utf-8"))
                    start = index + 1
            if start < len(value):
                values.append(value[start:].encode("utf-8"))
        elif isinstance(value, list):
            pending.extend(value)
        elif isinstance(value, dict):
            pending.extend(value.keys())
            pending.extend(value.values())
    return values


def _canonical_github_url_paths(content: bytes) -> list[bytes]:
    undecoded_sources = [content, *_json_string_values(content)]
    sources: list[bytes] = []
    seen_sources: set[bytes] = set()
    for undecoded_source in undecoded_sources:
        source = undecoded_source
        for _ in range(IDENTITY_SCAN_MAX_DECODE_PASSES + 1):
            if source not in seen_sources:
                seen_sources.add(source)
                sources.append(source)
            next_source = _decode_identity_scan_syntax_once(source)
            if next_source == source:
                break
            source = next_source
    canonical_paths: list[bytes] = []
    for source in sources:
        canonical_paths.extend(_canonical_github_url_paths_from_source(source))
        for token_match in SPECIAL_URL_TOKEN_PATTERN.finditer(source):
            token = token_match.group()
            if SPECIAL_URL_START_PATTERN.search(token) is not None:
                continue
            decoded = token
            for _ in range(IDENTITY_SCAN_MAX_DECODE_PASSES):
                syntax_decoded = _decode_identity_scan_syntax_once(decoded)
                if SPECIAL_URL_START_PATTERN.search(syntax_decoded) is not None:
                    canonical_paths.extend(
                        _canonical_github_url_paths_from_source(syntax_decoded)
                    )
                    break
                next_value = unquote_to_bytes(syntax_decoded)
                if next_value == decoded:
                    break
                decoded = next_value
                if SPECIAL_URL_START_PATTERN.search(decoded) is not None:
                    canonical_paths.extend(
                        _canonical_github_url_paths_from_source(decoded)
                    )
                    break
    return canonical_paths


def _normalize_identity_scan_content(content: bytes) -> bytes:
    normalized = content
    canonical_paths = _canonical_github_url_paths(content)
    for _ in range(IDENTITY_SCAN_MAX_DECODE_PASSES):
        decoded = _decode_identity_scan_content_once(normalized)
        if decoded == normalized:
            return (decoded + b"\n" + b"\n".join(canonical_paths)).lower()
        normalized = decoded
    if _decode_identity_scan_content_once(normalized) != normalized:
        raise ValidationError("repository identity encoding depth exceeds limit")
    return (normalized + b"\n" + b"\n".join(canonical_paths)).lower()


def _sha256_uri(path: Path, label: str) -> str:
    try:
        return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"
    except OSError as error:
        raise ValidationError(f"{label} is unreadable") from error


def _decode_canonical_base64(value: object) -> bytes:
    if not isinstance(value, str):
        raise ValidationError("adopted history delta bundle drift")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValidationError("adopted history delta bundle drift") from error
    if base64.b64encode(decoded).decode("ascii") != value:
        raise ValidationError("adopted history delta bundle drift")
    return decoded


def _expected_history_source_roots() -> list[dict[str, object]]:
    return [
        {
            "disposition": "protected-non-release-source-history-evidence",
            "platform": platform,
            "ref": ref,
            "repository": LEGACY_REPOSITORY_SLUG,
            "ruleset_id": 22049569,
            "tip": tip,
        }
        for platform, ref, tip in EXPECTED_HISTORY_SOURCE_ROOTS
    ]


def _validate_adopted_history_delta_bundle(
    repository: Path,
    import_rows: list[list[str]],
) -> dict[str, bytes]:
    bundle_path = repository / ADOPTED_HISTORY_DELTA_BUNDLE_RELATIVE
    if (
        _sha256_uri(bundle_path, "adopted history delta bundle")
        != ADOPTED_HISTORY_DELTA_BUNDLE_SHA256
    ):
        raise ValidationError("adopted history delta bundle drift")
    bundle = _load_json(bundle_path, "adopted history delta bundle")
    if not isinstance(bundle, dict) or set(bundle) != {
        "content_sha256",
        "contract",
        "delta_contract",
        "map",
        "rows",
        "schema_version",
        "source_roots",
    }:
        raise ValidationError("adopted history delta bundle drift")
    if (
        bundle.get("contract")
        != "provingkit-adopted-history-delta-bundle-v1"
        or type(bundle.get("schema_version")) is not int
        or bundle["schema_version"] != 1
        or bundle.get("content_sha256")
        != ADOPTED_HISTORY_DELTA_CONTENT_SHA256
        or bundle.get("delta_contract")
        != {
            "encoding": "base64-rfc4648-canonical",
            "filtered_intermediate_disposition": (
                "raw-delta-evidence-bundled-commit-objects-not-retained"
            ),
            "full_command": [
                "git",
                "diff-tree",
                "-r",
                "--raw",
                "-z",
                "--no-commit-id",
                "--no-renames",
                "--abbrev=40",
                "<commit>^",
                "<commit>",
                "--",
            ],
            "projected_pathspecs": ["scripts", "tests"],
        }
        or bundle.get("map")
        != {
            "path": ADOPTED_HISTORY_IMPORT_MAP_RELATIVE.as_posix(),
            "row_count": 57,
            "sha256": (
                "sha256:"
                "6cf416a0be58f050745d2eaad02208e7a0a030dc200a0e55bb4fadb708d37a6f"
            ),
        }
        or bundle.get("source_roots") != _expected_history_source_roots()
    ):
        raise ValidationError("adopted history delta bundle drift")
    canonical_content = dict(bundle)
    canonical_content.pop("content_sha256")
    canonical_bytes = json.dumps(
        canonical_content,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    if (
        "sha256:" + hashlib.sha256(canonical_bytes).hexdigest()
        != ADOPTED_HISTORY_DELTA_CONTENT_SHA256
    ):
        raise ValidationError("adopted history delta bundle drift")

    rows = bundle.get("rows")
    if not isinstance(rows, list) or len(rows) != 57 or len(import_rows) != 57:
        raise ValidationError("adopted history delta bundle drift")
    retained_deltas: dict[str, bytes] = {}
    expected_row_keys = {
        "filtered_commit",
        "filtered_full_delta_base64",
        "ordinal",
        "original_commit",
        "original_full_delta_base64",
        "original_projected_delta_base64",
        "platform",
        "retained_import_commit",
    }
    for row, map_row in zip(rows, import_rows, strict=True):
        if (
            not isinstance(row, dict)
            or set(row) != expected_row_keys
            or type(row.get("ordinal")) is not int
            or row["platform"] != map_row[0]
            or row["ordinal"] != int(map_row[1])
            or row["original_commit"] != map_row[2]
            or row["filtered_commit"] != map_row[3]
            or row["retained_import_commit"] != map_row[4]
        ):
            raise ValidationError("adopted history delta bundle drift")
        original_full = _decode_canonical_base64(
            row["original_full_delta_base64"]
        )
        original_projected = _decode_canonical_base64(
            row["original_projected_delta_base64"]
        )
        filtered_full = _decode_canonical_base64(
            row["filtered_full_delta_base64"]
        )
        if (
            hashlib.sha256(original_full).hexdigest() != map_row[5]
            or original_projected != filtered_full
            or hashlib.sha256(original_projected).hexdigest() != map_row[6]
        ):
            raise ValidationError("adopted history delta bundle drift")
        retained_deltas[map_row[4]] = original_full
    return retained_deltas


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
        if version != EXPECTED_CUTOVER_MEMBER_VERSIONS[member_id]:
            raise ValidationError("cutover member version drift")
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
            "adopted_history_import",
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

    expected_import_map_sha256 = (
        "sha256:6cf416a0be58f050745d2eaad02208e7a0a030dc200a0e55bb4fadb708d37a6f"
    )
    expected_import = {
        "delta_bundle": {
            "contract": "provingkit-adopted-history-delta-bundle-v1",
            "path": ADOPTED_HISTORY_DELTA_BUNDLE_RELATIVE.as_posix(),
            "row_count": 57,
            "sha256": ADOPTED_HISTORY_DELTA_BUNDLE_SHA256,
            "content_sha256": ADOPTED_HISTORY_DELTA_CONTENT_SHA256,
            "source_roots": _expected_history_source_roots(),
        },
        "final_main_mapping": {
            "state": "pending-rebase-merge",
            "completion_gate": "required-before-closing-source-issue-81",
        },
        "patch_correspondence": {
            "digest": "sha256",
            "full_delta_contract": (
                "canonical-git-raw-recursive-tree-delta-parent-to-commit-v1"
            ),
            "original_to_filtered": (
                "scripts-tests-tree-delta-equals-filtered-full-tree-delta"
            ),
            "original_to_retained_import": "full-tree-delta-bytes-equal",
            "tree_delta_command": [
                "git",
                "diff-tree",
                "-r",
                "--raw",
                "-z",
                "--no-commit-id",
                "--no-renames",
                "--abbrev=40",
                "<commit>^",
                "<commit>",
                "--",
            ],
            "projected_pathspecs": ["scripts", "tests"],
        },
        "relocations": [
            {"from": source, "to": destination, "blob": blob}
            for source, destination, blob in EXPECTED_HISTORY_RELOCATIONS
        ],
        "retained_ref": {
            "ref": "refs/heads/retained/issue-81-history-import",
            "disposition": "immutable-non-release-history-evidence",
        },
        "review_map": {
            "contract": "provingkit-adopted-history-import-map-v1",
            "path": ADOPTED_HISTORY_IMPORT_MAP_RELATIVE.as_posix(),
            "row_count": 57,
            "sha256": expected_import_map_sha256,
        },
    }
    if (
        provenance.get("adopted_history_import") != expected_import
        or _sha256_uri(
            repository / ADOPTED_HISTORY_IMPORT_MAP_RELATIVE,
            "adopted history import map",
        )
        != expected_import_map_sha256
    ):
        raise ValidationError("adopted history import map drift")
    try:
        import_lines = (
            (repository / ADOPTED_HISTORY_IMPORT_MAP_RELATIVE)
            .read_text(encoding="ascii")
            .splitlines()
        )
        import_header = import_lines[0].split("\t")
        import_rows = [line.split("\t") for line in import_lines[1:]]
    except (OSError, UnicodeError, IndexError) as error:
        raise ValidationError("adopted history import map drift") from error
    if import_header != [
        "platform",
        "ordinal",
        "original_commit",
        "filtered_commit",
        "retained_import_commit",
        "full_tree_delta_sha256",
        "projected_tree_delta_sha256",
    ] or len(import_rows) != 57:
        raise ValidationError("adopted history import map drift")
    expected_ordinals = [("linux", str(value)) for value in range(1, 22)] + [
        ("macos", str(value)) for value in range(1, 37)
    ]
    if any(len(row) != len(import_header) for row in import_rows):
        raise ValidationError("adopted history import map drift")
    if [(row[0], row[1]) for row in import_rows] != expected_ordinals:
        raise ValidationError("adopted history import map drift")
    originals = [row[2] for row in import_rows]
    filtereds = [row[3] for row in import_rows]
    retained_imports = [row[4] for row in import_rows]
    if (
        any(not OID_SHA1_PATTERN.fullmatch(value) for value in originals)
        or any(not OID_SHA1_PATTERN.fullmatch(value) for value in filtereds)
        or any(not OID_SHA1_PATTERN.fullmatch(value) for value in retained_imports)
        or any(
            not SHA256_PATTERN.fullmatch(value)
            for row in import_rows
            for value in row[5:]
        )
        or len(set(originals)) != 57
        or len(set(filtereds)) != 57
        or len(set(retained_imports)) != 57
        or any(
            observed_map.get(original) != filtered
            for original, filtered in zip(originals, filtereds, strict=True)
        )
    ):
        raise ValidationError("adopted history import map drift")

    _validate_adopted_history_delta_bundle(repository, import_rows)

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
            "retained_import_range": {
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
            "retained_import_range": {
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
    if (
        retained_imports[:1]
        != [expected_adopted[0]["retained_import_range"]["first_commit"]]
        or retained_imports[20:21]
        != [expected_adopted[0]["retained_import_range"]["last_commit"]]
        or retained_imports[21:22]
        != [expected_adopted[1]["retained_import_range"]["first_commit"]]
        or retained_imports[-1:]
        != [expected_adopted[1]["retained_import_range"]["last_commit"]]
    ):
        raise ValidationError("adopted history import map drift")

    expected_compatibility_aliases = [
        {
            "kind": "repository",
            "legacy": LEGACY_REPOSITORY,
            "canonical": CANONICAL_REPOSITORY,
            "scope": "frozen-receipts",
        },
        {
            "kind": "repository-id",
            "legacy": LEGACY_REPOSITORY_SLUG,
            "canonical": "nisavid/provingkit",
            "scope": "frozen-receipts",
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
        or len(allowlist["entries"]) != 38
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
        identity_content = _normalize_identity_scan_content(
            _identity_scan_content(relative_path, content)
        )
        if any(token in identity_content for token in LEGACY_IDENTITY_TOKENS):
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

    definition = _load_json(
        repository / DEFINITION_RELATIVE,
        "versioned Provingkit definition",
    )
    membership = definition.get("membership") if isinstance(definition, dict) else None
    definition_members = (
        membership.get("members") if isinstance(membership, dict) else None
    )
    schema_properties = schema.get("properties")
    schema_definitions = schema.get("$defs")
    schema_members = (
        schema_properties.get("members")
        if isinstance(schema_properties, dict)
        else None
    )
    schema_prefix_items = (
        schema_members.get("prefixItems") if isinstance(schema_members, dict) else None
    )
    if (
        not isinstance(definition_members, list)
        or not isinstance(schema_definitions, dict)
        or not isinstance(schema_prefix_items, list)
        or len(schema_prefix_items) != len(definition_members)
        or schema_members.get("type") != "array"
        or schema_members.get("minItems") != len(definition_members)
        or schema_members.get("maxItems") != len(definition_members)
        or schema_members.get("items") is not False
    ):
        raise ValidationError("release-manifest schema member projection drift")

    definition_projection: list[tuple[object, ...]] = []
    schema_projection: list[tuple[object, ...]] = []
    for member in definition_members:
        if not isinstance(member, dict):
            raise ValidationError("release-manifest schema member projection drift")
        identity_manifests = member.get("identity_manifests")
        content_identity = member.get("content_identity")
        if not isinstance(identity_manifests, dict) or not isinstance(
            content_identity, dict
        ):
            raise ValidationError("release-manifest schema member projection drift")
        definition_projection.append(
            (
                member.get("id"),
                member.get("distribution_kind"),
                member.get("version"),
                identity_manifests.get("canonical"),
                identity_manifests.get("claude"),
                content_identity.get("kind"),
                content_identity.get("path"),
            )
        )

    for prefix_item in schema_prefix_items:
        reference = prefix_item.get("$ref") if isinstance(prefix_item, dict) else None
        if not isinstance(reference, str) or not reference.startswith("#/$defs/"):
            raise ValidationError("release-manifest schema member projection drift")
        member_schema = schema_definitions.get(reference.removeprefix("#/$defs/"))
        member_properties = (
            member_schema.get("properties")
            if isinstance(member_schema, dict)
            else None
        )
        if (
            not isinstance(member_schema, dict)
            or member_schema.get("$ref") != "#/$defs/member"
            or not isinstance(member_properties, dict)
        ):
            raise ValidationError("release-manifest schema member projection drift")
        manifest_properties = member_properties.get("identity_manifests", {}).get(
            "properties", {}
        )
        content_properties = member_properties.get("content_identity", {}).get(
            "properties", {}
        )
        try:
            canonical_path = manifest_properties["canonical"]["properties"]["path"][
                "const"
            ]
            claude_path = manifest_properties["claude"]["properties"]["path"][
                "const"
            ]
            content_kind = content_properties["kind"]["const"]
            content_path = content_properties["path"]["const"]
            member_id = member_properties["id"]["const"]
            distribution_kind = member_properties["distribution_kind"]["const"]
            version = member_properties["version"]["const"]
        except (KeyError, TypeError):
            raise ValidationError(
                "release-manifest schema member projection drift"
            ) from None
        schema_projection.append(
            (
                member_id,
                distribution_kind,
                version,
                canonical_path,
                claude_path,
                content_kind,
                content_path,
            )
        )
    if schema_projection != definition_projection:
        raise ValidationError("release-manifest schema member projection drift")

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


def _require_git_bytes(repository: Path, *arguments: str) -> bytes:
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
        result = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            capture_output=True,
            check=False,
            timeout=15,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValidationError("Git history attestation unavailable") from error
    if result.returncode != 0:
        raise ValidationError("Git history attestation unavailable")
    return result.stdout


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
    try:
        import_rows = [
            line.split("\t")
            for line in (
                repository / ADOPTED_HISTORY_IMPORT_MAP_RELATIVE
            ).read_text(encoding="ascii").splitlines()[1:]
        ]
    except (OSError, UnicodeError) as error:
        raise ValidationError("adopted history import map drift") from error
    bundled_original_deltas = _validate_adopted_history_delta_bundle(
        repository, import_rows
    )
    linux_first = import_rows[0][4]
    linux_last = import_rows[20][4]
    macos_first = import_rows[21][4]
    macos_last = import_rows[-1][4]
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
    for ancestor, descendant in ((baseline, "HEAD"),):
        ancestry = _run_git(
            repository,
            "merge-base",
            "--is-ancestor",
            ancestor,
            descendant,
        )
        if ancestry.returncode != 0:
            raise ValidationError("Git history attestation drift")

    previous = baseline
    for row in import_rows:
        original, retained_import = row[2], row[4]
        if _require_git_output(repository, "rev-parse", f"{retained_import}^") != previous:
            raise ValidationError("adopted history import ancestry drift")
        message = _require_git_output(
            repository, "show", "-s", "--format=%B", retained_import
        )
        trailers = re.findall(
            r"^\(cherry picked from commit ([0-9a-f]{40})\)$",
            message,
            flags=re.MULTILINE,
        )
        if trailers != [original]:
            raise ValidationError("adopted history import trailer drift")
        tree_delta = _require_git_bytes(
            repository,
            "diff-tree",
            "-r",
            "--raw",
            "-z",
            "--no-commit-id",
            "--no-renames",
            "--abbrev=40",
            f"{retained_import}^",
            retained_import,
            "--",
        )
        if (
            tree_delta != bundled_original_deltas[retained_import]
            or hashlib.sha256(tree_delta).hexdigest() != row[5]
        ):
            raise ValidationError("adopted history import tree-delta drift")
        previous = retained_import

    import_ref_names = (
        "refs/heads/retained/issue-81-history-import",
        "refs/remotes/origin/retained/issue-81-history-import",
    )
    observed_import_refs = {
        result.stdout.strip()
        for ref in import_ref_names
        if (
            result := _run_git(repository, "show-ref", "--verify", "--hash", ref)
        ).returncode
        == 0
    }
    import_in_head = _run_git(
        repository,
        "merge-base",
        "--is-ancestor",
        macos_last,
        "HEAD",
    )
    if import_in_head.returncode not in (0, 1):
        raise ValidationError("Git history attestation unavailable")
    if not observed_import_refs and import_in_head.returncode != 0:
        raise ValidationError("retained history-import ref attestation drift")
    for object_id in observed_import_refs:
        if object_id != ADOPTED_HISTORY_IMPORT_TIP:
            raise ValidationError("retained history-import ref attestation drift")

    for source, destination, expected_blob in EXPECTED_HISTORY_RELOCATIONS:
        observed_blob = _require_git_output(repository, "rev-parse", f"HEAD:{destination}")
        if observed_blob != expected_blob:
            raise ValidationError("historical qualification relocation drift")
        source_probe = _run_git(repository, "cat-file", "-e", f"HEAD:{source}")
        if source_probe.returncode == 0:
            raise ValidationError("historical qualification relocation drift")
        if source_probe.returncode not in (1, 128):
            raise ValidationError("Git history attestation unavailable")

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
