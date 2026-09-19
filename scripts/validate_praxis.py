#!/usr/bin/env python3
"""Validate the Praxis Agent Plugin, its Claude projection, and its content lock.

The lock at ``release/plugin-content-locks/praxis.json`` pins the canonical
plugin bytes (including the Aeon Bell runtime resources), the three public Aeon
Bell test modules, and the closed public eval corpus inventory under
``evals/praxis`` at a candidate revision: the Aeon Bell application-evidence
corpus and the raw control-plane scenario definition.  It verifies source
identity only: it does not run those tests, does not execute or grade any
scenario (a scenario definition is not executed model evidence), does not
assert that the Aeon Bell engine or Codex status adapter behaves correctly,
and source membership grants no release, installation, or host-mutation
authority.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path

SCRIPT_DIRECTORY = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIRECTORY))

from agent_plugins_standard import (  # noqa: E402
    AgentPluginContractError,
    discover_direct_skills,
    load_agent_plugin_manifest,
    validate_skill_resource_links,
)

try:
    import yaml
except ModuleNotFoundError:
    yaml = None

PLUGIN_RELATIVE = Path("plugins/praxis")
PLUGIN_NAME = "praxis"
DISPLAY_NAME = "Praxis"
RELEASE_VERSION = "1.0.0"
TOPOLOGY_SCHEMA_VERSION = 1
DESCRIPTION_PREFIX = "Praxis: "
CODEX_CAPABILITIES = ["Orchestration"]
HOMEPAGE = "https://github.com/nisavid/provingkit/tree/main/plugins/praxis"
REPOSITORY = "https://github.com/nisavid/provingkit"
ROSTER = ("aeon-bell",)
RUNTIME_SCRIPTS = {
    "aeon-bell": (
        "skills/aeon-bell/scripts/aeon_bell.py",
        "skills/aeon-bell/scripts/codex_status.py",
    ),
}
JAVASCRIPT_RUNTIME_RESOURCES = {
    "aeon-bell": ("skills/aeon-bell/scripts/monitor_binding.js",),
}
PUBLIC_TESTS = (
    "tests/test_aeon_bell.py",
    "tests/test_aeon_bell_codex_status.py",
    "tests/test_aeon_bell_binding.py",
)
EVAL_CORPUS_ROOT = "evals/praxis"
# Closed inventory of the public eval corpus directory.  ``aeon-bell.json`` is
# the application-evidence corpus; ``corpus.json`` is the raw control-plane
# scenario definition consumed by ``evals/control-plane-matrix.json``.  Both
# are locked as source bytes; neither is executed model evidence.
EVAL_CORPORA = (
    "evals/praxis/aeon-bell.json",
    "evals/praxis/corpus.json",
)
CONTENT_LOCK_RELATIVE = Path("release/plugin-content-locks/praxis.json")
CONTENT_LOCK_CONTRACT = "praxis-content-lock-v1"
CONTENT_LOCK_SCHEMA_VERSION = 1
ROOT_FILES = {
    ".claude-plugin/plugin.json",
    "CHANGELOG.md",
    "LICENSE",
    "README.md",
    "plugin.json",
    "topology.json",
}
SAFE_FILE_MODES = frozenset({0o644, 0o755})
MAX_SKILL_LINES = 500
MAX_DESCRIPTION_CHARACTERS = 1024
SKILL_FRONTMATTER_REQUIRED = {"name", "description"}
SKILL_FRONTMATTER_OPTIONAL = {"license", "allowed-tools", "metadata"}
SKILL_NAME = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
PORTABILITY_PATTERNS = (
    re.compile(r"/users/[a-z0-9._-]", re.IGNORECASE),
    re.compile(r"/home/[a-z0-9._-]", re.IGNORECASE),
    re.compile(r"\bchezmoi\b", re.IGNORECASE),
    re.compile(r"\bsystalyze\b", re.IGNORECASE),
)
# Credential-shaped text must never ship in the plugin or its runtime scripts.
# The public test modules are exempt from these two heuristics only: they prove
# the adapter's redaction with synthetic credential-shaped fixtures and Codex
# protocol literals such as the ``apiKey`` account type, and they are locked as
# source bytes, not installed.
CREDENTIAL_PATTERNS = (
    re.compile(r"\bapi[\s_-]*key\b", re.IGNORECASE),
    re.compile(r"\bauthorization\s*:\s*bearer\b", re.IGNORECASE),
)
JAVASCRIPT_FORBIDDEN_AMBIENT_APIS = re.compile(
    r"\b(?:require|import|process|fetch|XMLHttpRequest|WebSocket|setTimeout|"
    r"setInterval|Deno|Bun)\b"
)


class ContractError(ValueError):
    """Raised for a stable, user-actionable plugin contract failure."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def require_nonempty_string(value: object, message: str) -> str:
    require(isinstance(value, str) and bool(value), message)
    return value


def require_integer(value: object, message: str) -> int:
    require(isinstance(value, int) and not isinstance(value, bool), message)
    return value


def safe_relative_path(value: object, field: str) -> Path:
    text = require_nonempty_string(value, f"{field} must be a nonempty string")
    relative = Path(text)
    require(
        not relative.is_absolute()
        and ".." not in relative.parts
        and relative.as_posix() == text,
        f"{field} must be a normalized relative path",
    )
    return relative


def reject_lexical_ancestor_symlinks(path: Path) -> Path:
    lexical_path = path if path.is_absolute() else Path.cwd() / path
    current = Path(lexical_path.anchor)
    for part in lexical_path.parts[1:]:
        if part in ("", "."):
            continue
        if part == "..":
            current = current.parent
            continue
        current /= part
        require(
            not current.is_symlink(),
            f"repository path contains a symlinked lexical ancestor: {current}",
        )
    return current


def locate_repository(repo_root: Path) -> Path:
    lexical_repo = reject_lexical_ancestor_symlinks(repo_root)
    resolved_repo = lexical_repo.resolve(strict=True)
    require(resolved_repo.is_dir(), "repository root must be a directory")
    return resolved_repo


def locate_plugin(repository: Path) -> Path:
    current = repository
    for part in PLUGIN_RELATIVE.parts:
        current /= part
        require(not current.is_symlink(), "plugin root path must not contain symlinks")
    resolved_root = current.resolve(strict=True)
    require(
        resolved_root.is_relative_to(repository) and resolved_root.is_dir(),
        "plugin root is invalid",
    )
    return resolved_root


def contained_path(root: Path, relative: str | Path, field: str) -> Path:
    relative = safe_relative_path(Path(relative).as_posix(), field)
    current = root
    for part in relative.parts:
        current /= part
        require(
            not current.is_symlink(),
            f"{field} path must not contain symlinks: {relative}",
        )
    return current


def read_bytes(root: Path, relative: str | Path, *, field: str = "file") -> bytes:
    current = contained_path(root, relative, field)
    try:
        resolved = current.resolve(strict=True)
    except OSError as error:
        raise ContractError(f"{field} is missing: {Path(relative).as_posix()}") from error
    require(
        resolved.is_relative_to(root.resolve(strict=True)) and resolved.is_file(),
        f"{field} is missing: {Path(relative).as_posix()}",
    )
    return resolved.read_bytes()


def read_text(root: Path, relative: str | Path, *, field: str = "file") -> str:
    try:
        return read_bytes(root, relative, field=field).decode("utf-8")
    except UnicodeDecodeError as error:
        raise ContractError(f"{field} is not UTF-8 text: {relative}") from error


def load_json(root: Path, relative: str | Path, field: str) -> dict:
    def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
        value: dict = {}
        for key, item in pairs:
            require(key not in value, f"{field} contains duplicate key: {key}")
            value[key] = item
        return value

    def reject_constant(value: str) -> object:
        raise ContractError(f"{field} contains non-finite JSON value: {value}")

    try:
        value = json.loads(
            read_text(root, relative, field=field),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_constant,
        )
    except json.JSONDecodeError as error:
        raise ContractError(f"{field} is not valid JSON") from error
    require(isinstance(value, dict), f"{field} must be an object")
    return value


def portable_text(text: str, field: str, *, credentials: bool = True) -> None:
    patterns = PORTABILITY_PATTERNS + (CREDENTIAL_PATTERNS if credentials else ())
    for pattern in patterns:
        require(
            pattern.search(text) is None,
            f"portability or credential leak in {field}",
        )


def portable_document(value: object, field: str) -> None:
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, str):
            portable_text(item, field)
        elif isinstance(item, dict):
            pending.extend(item.keys())
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)


def load_yaml_mapping(content: str, field: str) -> dict:
    require(yaml is not None, "PyYAML is required to validate skill metadata")

    class UniqueKeyLoader(yaml.SafeLoader):
        pass

    def construct_unique_mapping(loader, node, deep=False):
        mapping = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            try:
                duplicate = key in mapping
            except TypeError as error:
                raise ContractError(f"{field} keys must be scalar values") from error
            require(not duplicate, f"{field} contains duplicate key: {key}")
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping

    UniqueKeyLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_unique_mapping,
    )
    try:
        documents = list(yaml.load_all(content, Loader=UniqueKeyLoader))
    except yaml.YAMLError as error:
        raise ContractError(f"{field} contains invalid YAML: {error}") from error
    require(len(documents) == 1, f"{field} must contain exactly one YAML document")
    document = documents[0]
    require(isinstance(document, dict), f"{field} must contain a mapping")
    portable_document(document, field)
    return document


def load_skill_frontmatter(content: str, skill: str) -> dict:
    match = re.match(r"\A---\r?\n(?P<yaml>.*?)\r?\n---(?:\r?\n|\Z)", content, re.DOTALL)
    require(match is not None, f"{skill} must have opening and closing frontmatter")
    require(content[match.end() :].strip(), f"{skill} must have a skill body")
    return load_yaml_mapping(match.group("yaml"), f"{skill} frontmatter")


def validate_topology(root: Path) -> dict:
    topology = load_json(root, "topology.json", "Praxis topology")
    require(set(topology) == {"schema_version", "skills"}, "topology keys drift")
    require_integer(topology["schema_version"], "topology schema_version must be an integer")
    require(
        topology["schema_version"] == TOPOLOGY_SCHEMA_VERSION,
        "topology schema_version drift",
    )
    skills = topology["skills"]
    require(isinstance(skills, dict), "topology skills must be an object")
    require(
        tuple(sorted(skills)) == ROSTER,
        f"topology roster drift: expected {list(ROSTER)}, observed {sorted(skills)}",
    )
    owner_to_skill: dict[str, str] = {}
    for skill, node in skills.items():
        require(SKILL_NAME.fullmatch(skill) is not None, f"topology skill name is invalid: {skill}")
        require(isinstance(node, dict), f"topology node must be an object: {skill}")
        require(set(node) == {"owns", "may_call"}, f"topology node keys drift: {skill}")
        owners = node["owns"]
        require(
            isinstance(owners, list)
            and bool(owners)
            and all(isinstance(owner, str) and bool(owner) for owner in owners),
            f"topology owners must be nonempty strings: {skill}",
        )
        require(len(owners) == len(set(owners)), f"duplicate topology owner: {skill}")
        for owner in owners:
            require(owner not in owner_to_skill, f"topology owner is shared: {owner}")
            owner_to_skill[owner] = skill
        calls = node["may_call"]
        require(isinstance(calls, list), f"topology may_call must be a list: {skill}")
        observed_targets: set[str] = set()
        for position, call in enumerate(calls, start=1):
            require(
                isinstance(call, dict) and set(call) == {"skill", "when"},
                f"topology call {position} keys drift: {skill}",
            )
            target = require_nonempty_string(
                call["skill"], f"topology call target must be a string: {skill}"
            )
            require_nonempty_string(
                call["when"], f"topology call condition must be a string: {skill}"
            )
            require(target in skills, f"topology call target is unknown: {target}")
            require(target != skill, f"topology self-call is forbidden: {skill}")
            require(target not in observed_targets, f"duplicate topology call: {skill}")
            observed_targets.add(target)
    return topology


def validate_python_source(
    root: Path, relative: str, field: str, *, credentials: bool = True
) -> None:
    source = read_text(root, relative, field=field)
    require(source.strip(), f"{field} is empty: {relative}")
    try:
        ast.parse(source, filename=relative)
    except (SyntaxError, ValueError) as error:
        raise ContractError(f"{field} does not parse: {relative}") from error
    portable_text(source, relative, credentials=credentials)


def validate_codex_skill_adapter(root: Path, skill: str) -> None:
    adapter_path = f"skills/{skill}/agents/openai.yaml"
    if not (root / adapter_path).exists():
        return
    adapter = load_yaml_mapping(
        read_text(root, adapter_path, field=f"{skill} skill interface"),
        f"{skill} skill interface",
    )
    require(set(adapter) == {"interface"}, f"{skill} skill interface keys drift")
    interface = adapter["interface"]
    require(isinstance(interface, dict), f"{skill} interface must be a mapping")
    require(
        set(interface) == {"display_name", "short_description", "default_prompt"},
        f"{skill} interface schema drift",
    )
    for field in ("display_name", "short_description", "default_prompt"):
        require_nonempty_string(interface[field], f"{skill} interface {field} must be a string")
    tokens = re.findall(r"\$[a-z0-9-]+:[a-z0-9-]+", interface["default_prompt"])
    require(
        tokens == [f"${PLUGIN_NAME}:{skill}"],
        f"{skill} default prompt namespace drift",
    )


def validate_skills(root: Path, topology: dict) -> None:
    discovered = discover_direct_skills(root)
    require(
        discovered == ROSTER,
        f"Agent Plugins direct-child skill inventory drift: expected {list(ROSTER)}, "
        f"observed {list(discovered)}",
    )
    for skill in ROSTER:
        for relative in RUNTIME_SCRIPTS[skill]:
            validate_python_source(root, relative, "runtime script")
        for relative in JAVASCRIPT_RUNTIME_RESOURCES[skill]:
            validate_javascript_runtime_resource(root, relative)
    validate_skill_resource_links(root, discovered)
    for skill in ROSTER:
        skill_path = f"skills/{skill}/SKILL.md"
        content = read_text(root, skill_path, field=f"{skill} SKILL.md")
        frontmatter = load_skill_frontmatter(content, skill)
        require(
            SKILL_FRONTMATTER_REQUIRED <= set(frontmatter)
            <= SKILL_FRONTMATTER_REQUIRED | SKILL_FRONTMATTER_OPTIONAL,
            f"{skill} frontmatter keys drift",
        )
        require(frontmatter["name"] == skill, f"{skill} frontmatter name drift")
        description = require_nonempty_string(
            frontmatter["description"], f"{skill} description must be a string"
        )
        require(
            len(description) <= MAX_DESCRIPTION_CHARACTERS,
            f"{skill} description exceeds the Agent Skills budget",
        )
        require(
            len(content.splitlines()) <= MAX_SKILL_LINES,
            f"progressive-disclosure line budget exceeded: {skill}",
        )
        require(
            f"${PLUGIN_NAME}:" not in content,
            f"semantic body contains adapter-qualified syntax: {skill}",
        )
        for call in topology["skills"][skill]["may_call"]:
            target = call["skill"]
            require(
                f"](../{target}/SKILL.md)" in content,
                f"topology call is not projected in skill body: {skill} -> {target}",
            )
        validate_codex_skill_adapter(root, skill)


def validate_manifests(root: Path) -> None:
    canonical = load_agent_plugin_manifest(root)
    claude = load_json(root, ".claude-plugin/plugin.json", "Claude manifest")
    identity_fields = {
        "name",
        "version",
        "description",
        "author",
        "homepage",
        "repository",
        "license",
        "keywords",
    }
    require(
        set(canonical) == identity_fields | {"$schema", "extensions"},
        "canonical Agent Plugin manifest keys drift",
    )
    require(set(claude) == identity_fields | {"displayName"}, "Claude manifest keys drift")
    for field in ("name", "version", "description", "homepage", "repository", "license"):
        require_nonempty_string(canonical[field], f"canonical manifest {field} must be a string")
    require(canonical["name"] == PLUGIN_NAME, "canonical manifest name drift")
    require(canonical["version"] == RELEASE_VERSION, "canonical manifest version drift")
    require(canonical["license"] == "MIT", "canonical manifest license drift")
    require(canonical["repository"] == REPOSITORY, "canonical manifest repository drift")
    require(canonical["homepage"] == HOMEPAGE, "canonical manifest homepage drift")
    require(
        canonical["description"].startswith(DESCRIPTION_PREFIX),
        "canonical manifest description prefix drift",
    )
    keywords = canonical["keywords"]
    require(
        isinstance(keywords, list)
        and bool(keywords)
        and all(isinstance(item, str) and bool(item) for item in keywords),
        "canonical manifest keywords must be nonempty strings",
    )
    author = canonical["author"]
    require(
        isinstance(author, dict) and set(author) == {"name", "url"},
        "canonical manifest author schema drift",
    )
    for field in ("name", "url"):
        require_nonempty_string(author[field], f"canonical manifest author {field} must be a string")
    for field in sorted(identity_fields):
        require(claude[field] == canonical[field], f"Claude manifest projection drift: {field}")
    require_nonempty_string(claude["displayName"], "Claude displayName must be a string")
    require(claude["displayName"] == DISPLAY_NAME, "Claude displayName drift")
    extensions = canonical["extensions"]
    require(
        isinstance(extensions, dict) and set(extensions) == {"com.openai"},
        "canonical manifest extension inventory drift",
    )
    openai = extensions["com.openai"]
    require(isinstance(openai, dict) and set(openai) == {"interface"}, "Codex extension keys drift")
    interface = openai["interface"]
    require(isinstance(interface, dict), "Codex interface must be an object")
    require(
        set(interface)
        == {
            "displayName",
            "shortDescription",
            "longDescription",
            "developerName",
            "category",
            "capabilities",
            "websiteURL",
            "defaultPrompt",
        },
        "Codex interface keys drift",
    )
    for field in (
        "displayName",
        "shortDescription",
        "longDescription",
        "developerName",
        "category",
        "websiteURL",
    ):
        require_nonempty_string(interface[field], f"Codex interface {field} must be a string")
    require(
        interface["displayName"] == DISPLAY_NAME and interface["websiteURL"] == HOMEPAGE,
        "Codex interface metadata drift",
    )
    require(interface["capabilities"] == CODEX_CAPABILITIES, "Codex interface capabilities drift")
    prompts = interface["defaultPrompt"]
    require(
        isinstance(prompts, list) and all(isinstance(prompt, str) for prompt in prompts),
        "Codex default prompts must be strings",
    )
    referenced = [re.findall(r"\$[a-z0-9-]+:[a-z0-9-]+", prompt) for prompt in prompts]
    require(
        referenced == [[f"${PLUGIN_NAME}:{skill}"] for skill in ROSTER],
        "Codex default prompts drift: one prompt per roster skill in the plugin namespace",
    )
    portable_document(canonical, "canonical manifest")
    portable_document(claude, "Claude manifest")


def validate_readme_and_changelog(root: Path) -> None:
    readme = read_text(root, "README.md", field="README")
    for skill in ROSTER:
        require(f"`{skill}`" in readme, f"README does not name the roster skill: {skill}")
        require(
            f"skills/{skill}/SKILL.md" in readme,
            f"README does not name the skill entrypoint: {skill}",
        )
    changelog = read_text(root, "CHANGELOG.md", field="CHANGELOG")
    require(
        re.search(r"^## \S", changelog, re.MULTILINE) is not None,
        "changelog lacks a release or unreleased section",
    )


def plugin_inventory(root: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    directories: set[str] = set()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        metadata = path.lstat()
        require(
            not stat.S_ISLNK(metadata.st_mode),
            f"plugin inventory contains a symlink: {relative}",
        )
        parts = Path(relative).parts
        require(
            "__pycache__" not in parts and not relative.endswith((".pyc", ".pyo")),
            f"plugin inventory contains generated Python state: {relative}",
        )
        require(
            not any(part.startswith(".") for part in parts[1:])
            and (not parts[0].startswith(".") or parts[0] == ".claude-plugin"),
            f"plugin inventory contains a hidden entry: {relative}",
        )
        if stat.S_ISREG(metadata.st_mode):
            files[relative] = path
        else:
            require(
                stat.S_ISDIR(metadata.st_mode),
                f"plugin inventory contains a special entry: {relative}",
            )
            directories.add(relative)
    skill_prefixes = tuple(f"skills/{skill}/" for skill in ROSTER)
    unexpected = sorted(
        relative
        for relative in files
        if relative not in ROOT_FILES and not relative.startswith(skill_prefixes)
    )
    missing = sorted(ROOT_FILES - set(files))
    require(
        not unexpected and not missing,
        f"component inventory drift: unexpected {unexpected}, missing {missing}",
    )
    expected_directories: set[str] = set()
    for relative in files:
        parent = Path(relative).parent
        while parent != Path("."):
            expected_directories.add(parent.as_posix())
            parent = parent.parent
    require(directories == expected_directories, "component directory drift: empty directory")
    return files


def validate_portable_file(path: Path, label: str) -> bytes:
    metadata = path.lstat()
    require(stat.S_ISREG(metadata.st_mode), f"{label} must be a regular file")
    require(
        stat.S_IMODE(metadata.st_mode) in SAFE_FILE_MODES,
        f"file mode is not portable (expected 0644 or 0755): {label}",
    )
    content = path.read_bytes()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ContractError(f"{label} is not UTF-8 text") from error
    portable_text(text, label, credentials=label not in PUBLIC_TESTS)
    return content


def validate_javascript_runtime_resource(root: Path, relative: str) -> None:
    path = contained_path(root, relative, "JavaScript runtime resource")
    try:
        path.resolve(strict=True)
    except OSError as error:
        raise ContractError(
            f"JavaScript runtime resource is missing: {relative}"
        ) from error
    content = validate_portable_file(path, "JavaScript runtime resource")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ContractError("JavaScript runtime resource is not UTF-8 text") from error
    require(text.strip(), "JavaScript runtime resource must be nonempty")
    require(
        text.startswith("(function () {\n  \"use strict\";") and text.rstrip().endswith("}())"),
        "JavaScript runtime resource must be one strict IIFE expression",
    )
    require(
        JAVASCRIPT_FORBIDDEN_AMBIENT_APIS.search(text) is None,
        "JavaScript runtime resource uses a forbidden ambient API",
    )


def validate_public_evidence(repository: Path) -> None:
    for relative in PUBLIC_TESTS:
        validate_python_source(repository, relative, "public test", credentials=False)
    corpus_root = contained_path(repository, EVAL_CORPUS_ROOT, "eval corpus root")
    for relative in EVAL_CORPORA:
        corpus = load_json(repository, relative, "eval corpus")
        require(bool(corpus), f"eval corpus must be a nonempty object: {relative}")
        portable_document(corpus, relative)
    require(
        corpus_root.is_dir() and not corpus_root.is_symlink(),
        f"eval corpus is missing: {EVAL_CORPUS_ROOT}",
    )
    observed = sorted(
        (Path(EVAL_CORPUS_ROOT) / path.name).as_posix()
        for path in corpus_root.iterdir()
    )
    require(
        observed == sorted(EVAL_CORPORA),
        f"eval corpus inventory drift: expected {sorted(EVAL_CORPORA)}, observed {observed}",
    )


def locked_inputs(repository: Path, plugin: Path) -> dict[str, Path]:
    inputs = {
        (PLUGIN_RELATIVE / relative).as_posix(): path
        for relative, path in plugin_inventory(plugin).items()
    }
    for relative in (*PUBLIC_TESTS, *EVAL_CORPORA):
        inputs[relative] = contained_path(repository, relative, "locked input")
    return inputs


def content_lock_document(inputs: dict[str, Path]) -> dict:
    files = {}
    for relative in sorted(inputs):
        content = validate_portable_file(inputs[relative], relative)
        files[relative] = {
            "mode": stat.S_IMODE(inputs[relative].lstat().st_mode),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
    return {
        "algorithm": "sha256",
        "contract": CONTENT_LOCK_CONTRACT,
        "files": files,
        "plugin_root": PLUGIN_RELATIVE.as_posix(),
        "schema_version": CONTENT_LOCK_SCHEMA_VERSION,
    }


def canonical_lock_bytes(document: dict) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")


def validate_content_lock(repository: Path, expected: dict) -> None:
    lock_path = contained_path(repository, CONTENT_LOCK_RELATIVE, "content lock")
    require(lock_path.is_file(), f"content lock is missing: {CONTENT_LOCK_RELATIVE.as_posix()}")
    raw = read_bytes(repository, CONTENT_LOCK_RELATIVE, field="content lock")
    lock = load_json(repository, CONTENT_LOCK_RELATIVE, "content lock")
    require(
        set(lock) == {"algorithm", "contract", "files", "plugin_root", "schema_version"},
        "content lock keys drift",
    )
    require(lock["contract"] == CONTENT_LOCK_CONTRACT, "content lock contract drift")
    require_integer(lock["schema_version"], "content lock schema_version must be an integer")
    require(lock["schema_version"] == CONTENT_LOCK_SCHEMA_VERSION, "content lock schema_version drift")
    require(lock["algorithm"] == "sha256", "content lock algorithm drift")
    require(lock["plugin_root"] == PLUGIN_RELATIVE.as_posix(), "content lock plugin root drift")
    files = lock["files"]
    require(isinstance(files, dict) and bool(files), "content lock files must be an object")
    for relative, entry in files.items():
        safe_relative_path(relative, "content lock path")
        require(
            isinstance(entry, dict)
            and set(entry) == {"mode", "sha256"}
            and isinstance(entry["sha256"], str)
            and re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]) is not None
            and isinstance(entry["mode"], int)
            and not isinstance(entry["mode"], bool)
            and entry["mode"] in SAFE_FILE_MODES,
            f"content lock entry is invalid: {relative}",
        )
    require(set(files) == set(expected["files"]), "content lock inventory drift")
    require(files == expected["files"], "content lock mismatch: locked inputs changed")
    require(raw == canonical_lock_bytes(expected), "content lock is not canonical")


def inspect_contract(repository: Path, plugin: Path) -> dict:
    topology = validate_topology(plugin)
    validate_skills(plugin, topology)
    validate_manifests(plugin)
    validate_readme_and_changelog(plugin)
    validate_public_evidence(repository)
    return content_lock_document(locked_inputs(repository, plugin))


def publish_content_lock(repository: Path, document: dict) -> None:
    lock_path = repository / CONTENT_LOCK_RELATIVE
    stage = lock_path.with_name(f".{lock_path.name}.praxis-stage")
    require(
        lock_path.parent.is_dir() and not lock_path.parent.is_symlink(),
        f"content lock directory is missing: {lock_path.parent.relative_to(repository).as_posix()}",
    )
    try:
        stage.write_bytes(canonical_lock_bytes(document))
        stage.chmod(0o644)
        os.replace(stage, lock_path)
    finally:
        if stage.exists():
            stage.unlink()


def restore_content_lock(repository: Path, preimage: bytes | None) -> None:
    lock_path = repository / CONTENT_LOCK_RELATIVE
    if preimage is None:
        if lock_path.exists():
            lock_path.unlink()
    else:
        lock_path.write_bytes(preimage)


def usage() -> None:
    print("usage: validate_praxis.py [--write-content-lock] [repo-root]", file=sys.stderr)


def main() -> None:
    arguments = sys.argv[1:]
    write_lock = bool(arguments and arguments[0] == "--write-content-lock")
    if write_lock:
        arguments = arguments[1:]
    if len(arguments) > 1 or (arguments and arguments[0].startswith("-")):
        usage()
        raise SystemExit(2)
    try:
        repository = locate_repository(Path(arguments[0]) if arguments else Path.cwd())
        plugin = locate_plugin(repository)
        expected = inspect_contract(repository, plugin)
        if write_lock:
            lock_path = repository / CONTENT_LOCK_RELATIVE
            preimage = lock_path.read_bytes() if lock_path.exists() else None
            try:
                publish_content_lock(repository, expected)
                validate_content_lock(repository, inspect_contract(repository, plugin))
            except Exception:
                restore_content_lock(repository, preimage)
                raise
        else:
            validate_content_lock(repository, expected)
    except (
        AgentPluginContractError,
        ContractError,
        OSError,
        UnicodeDecodeError,
    ) as error:
        print(f"Praxis contract validation failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    if write_lock:
        print("Praxis content lock updated")
    print("Praxis contract validation passed")


if __name__ == "__main__":
    main()
