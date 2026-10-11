"""Prepare fake observations or one separately accepted native amendment episode.

Native preparation discovers and binds the selected executable, effective
configuration, instructions, skills, resource trees, and connectors without
starting a thread or turn. Native control responses are observations; they do
not attest permission enforcement, assessment absence, or semantic success.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import time
import tomllib
import types


HERE = Path(__file__).resolve().parent
TRANSPORT = HERE / "compatibility_transport.py"
TRANSPORT_SHA256 = "e141c75a2d5a31bc07d8999c46f138a268ef560e11eb22132dc15192254504e7"
GIT_EVIDENCE = HERE / "compatibility_git.py"
GIT_EVIDENCE_SHA256 = "ce81f9bc88027d87e9f109a666a01e9ad00e41a718b1ce03dbfa2a92ae489b78"
SEED_PRODUCER_SHA256 = "3072c63a15a86d5c4094a57cbe0954543b4f1cc28707210a130dba0d799ce6c4"

TOOLS = {
    "commandExecution",
    "fileChange",
    "mcpToolCall",
    "dynamicToolCall",
    "collabAgentToolCall",
    "webSearch",
    "imageView",
    "sleep",
    "imageGeneration",
}

NATIVE_DISABLED_FEATURES = (
    "hooks",
    "plugin_hooks",
    "memories",
    "apps",
    "shell_snapshot",
    "browser_use",
    "computer_use",
    "image_generation",
)

PLUGIN_SERVERS = (
    ("unified-computer-use@openai-bundled", "cua_repl"),
    ("fork-ops@fork-ops", "fork-ops"),
)

OMISSION_OVERLAY_NAME = "AGENTS.override.md"
OMISSION_OVERLAY_RAW = (
    b"# Compatibility observation instruction overlay\n"
    b"\n"
    b"For this task, do not invoke, consult, or use `jev-axi` or any "
    b"Jev assessment.\n"
    b"All other standing instructions remain in effect.\n"
)

REQUIRED_AUTHORING_SKILLS = {
    "checkpointing-and-publishing-git-work",
    "tdd",
    "code-review",
    "capturing-agent-procedures",
    "writing-for-people",
    "review",
    "intent",
    "runtime",
    "structure",
    "loop",
    "adjudicate",
    "revise",
    "delegating-cross-agent-work",
    "choosing-agent-models",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()


def put(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)


def checked(path, expected):
    raw = path.read_bytes()
    require(sha(raw) == expected, "identity differs: " + str(path))
    return raw


def relative(root, name):
    require(
        isinstance(name, str) and name and "\\" not in name,
        "invalid declared path",
    )
    path = PurePosixPath(name)
    require(
        not path.is_absolute()
        and all(part not in ("", ".", "..") for part in name.split("/")),
        "invalid declared path",
    )
    target = root.joinpath(*path.parts)
    require(
        target.resolve() == target.absolute(),
        "symlink in declared path",
    )
    return target


def identity(path):
    raw = path.read_bytes()
    return {
        "path": str(path),
        "resolved": str(path.resolve()),
        "bytes": len(raw),
        "sha256": sha(raw),
    }


def require_identity(entry, label):
    require(
        isinstance(entry, dict)
        and set(entry) == {"path", "resolved", "bytes", "sha256"},
        "invalid " + label + " identity",
    )
    path = Path(entry["path"])
    require(
        path.is_absolute()
        and path.resolve() == Path(entry["resolved"])
        and identity(path) == entry,
        label + " identity differs: " + str(path),
    )


def codex_home():
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")


def selected_instruction(home):
    override = home / "AGENTS.override.md"
    path = override if override.is_file() else home / "AGENTS.md"
    require(path.is_file(), "native instruction source is unavailable")
    return path


def configured_servers(config_path):
    data = tomllib.loads(config_path.read_text())
    servers = data.get("mcp_servers", {})
    require(isinstance(servers, dict), "invalid configured connector table")
    names = sorted(servers)
    require(
        all(
            isinstance(name, str)
            and re.fullmatch(r"[A-Za-z0-9_-]+", name)
            for name in names
        ),
        "unsupported connector name",
    )
    return names


def native_command(
    executable,
    project,
    model,
    effort,
    server_names,
    path_env,
):
    command = [
        str(executable),
        "--no-daemon",
        "app-server",
        "--stdio",
        "--strict-config",
    ]
    for feature in NATIVE_DISABLED_FEATURES:
        command.extend(["--disable", feature])
    command.extend(["--enable", "plugins", "--enable", "multi_agent"])

    overrides = [
        "model=" + json.dumps(model),
        "model_reasoning_effort=" + json.dumps(effort),
        'web_search="disabled"',
        "mcp_servers={}",
        "agents.default_subagent_model=" + json.dumps(model),
        "agents.default_subagent_reasoning_effort=" + json.dumps(effort),
        "projects={"
        + json.dumps(str(project))
        + '={trust_level="trusted"}}',
        'shell_environment_policy={inherit="none",set={LANG="C",LC_ALL="C",PATH='
        + json.dumps(path_env)
        + ",TMPDIR="
        + json.dumps(str(project / ".runner-tmp"))
        + "}}",
    ]
    for name in server_names:
        overrides.append(f"mcp_servers.{name}.enabled=false")
    for plugin, name in PLUGIN_SERVERS:
        overrides.append(
            f"plugins.{plugin}.mcp_servers.{name}.enabled=false"
        )

    for value in overrides:
        command.extend(["-c", value])
    return command


def load_transport():
    transport = types.ModuleType("bound_compatibility_transport")
    raw = checked(TRANSPORT, TRANSPORT_SHA256)
    exec(compile(raw, str(TRANSPORT), "exec"), transport.__dict__)
    return transport


def load_git_evidence():
    raw = checked(GIT_EVIDENCE, GIT_EVIDENCE_SHA256)
    module = types.ModuleType("compatibility_git")
    exec(compile(raw, str(GIT_EVIDENCE), "exec"), module.__dict__)
    return module


def fake_profile(raw):
    profile = json.loads(raw)
    fields = {"kind", "command", "python_sha256", "fixture_sha256"}
    native_shaped = (
        profile.get("kind")
        == "cooperative-native-app-server-fake/v1"
    )
    require(
        (
            set(profile) == fields
            and profile["kind"] == "cooperative-python-fake/v1"
        )
        or (
            native_shaped
            and set(profile) == fields | {"app_server_profile"}
        ),
        "only an explicitly selected cooperative Python fake is supported; "
        "native is unqualified",
    )
    if native_shaped:
        expected = profile["app_server_profile"]
        require(
            isinstance(expected, dict)
            and set(expected)
            in (
                {"schema", "version"},
                {"schema", "version", "model", "effort"},
                {
                    "schema",
                    "version",
                    "model",
                    "effort",
                    "observe_turn",
                },
            )
            and expected["schema"]
            == "compatibility-native-protocol-profile/v1"
            and isinstance(expected["version"], str)
            and expected["version"],
            "invalid synthetic native metadata profile",
        )
        if "model" in expected:
            require(
                all(
                    isinstance(expected[key], str) and expected[key]
                    for key in ("model", "effort")
                ),
                "invalid synthetic model or effort",
            )
        if "observe_turn" in expected:
            require(
                type(expected["observe_turn"]) is bool,
                "synthetic observe_turn must be a Boolean",
            )

    command = profile["command"]
    require(
        isinstance(command, list)
        and len(command) == 5
        and command[:4] == [
            sys.executable,
            "-I",
            "-S",
            "-u",
        ],
        "unsupported fake command",
    )
    fixture = Path(command[4])
    require(
        fixture.is_absolute()
        and fixture.resolve() == fixture
        and fixture.suffix == ".py",
        "absolute regular Python fixture required",
    )
    checked(Path(sys.executable), profile["python_sha256"])
    return profile, fixture, checked(
        fixture,
        profile["fixture_sha256"],
    )


def skills_identity(result, project):
    rows = result.get("data")
    require(
        isinstance(rows, list)
        and len(rows) == 1
        and rows[0].get("cwd") == str(project)
        and rows[0].get("errors") == [],
        "skill discovery unavailable",
    )
    skills = rows[0].get("skills")
    require(isinstance(skills, list), "skill discovery unavailable")

    entries = []
    for item in skills:
        require(
            isinstance(item, dict)
            and isinstance(item.get("name"), str)
            and item["name"]
            and type(item.get("enabled")) is bool
            and isinstance(item.get("scope"), str),
            "invalid discovered skill",
        )
        path = Path(item.get("path", ""))
        require(
            path.is_absolute() and path.name == "SKILL.md",
            "skill entrypoint differs",
        )
        entries.append({
            "name": item["name"],
            "enabled": item["enabled"],
            "scope": item["scope"],
            **identity(path),
        })

    return sorted(
        entries,
        key=lambda entry: (
            entry["name"],
            entry["path"],
            entry["scope"],
        ),
    )


def resource_tree(root):
    return [
        identity(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    ]


def normalize_connectors(servers):
    result = []
    for server in servers:
        require(
            isinstance(server, dict)
            and isinstance(server.get("name"), str)
            and server["name"],
            "invalid connector identity",
        )
        plugin = server.get("pluginId")
        require(
            plugin is None or isinstance(plugin, str),
            "invalid connector plugin identity",
        )
        result.append({
            "name": server["name"],
            "pluginId": plugin,
        })
    return sorted(
        result,
        key=lambda entry: (
            entry["name"],
            entry["pluginId"] or "",
        ),
    )


def verify_native_profile_sources(profile):
    require_identity(profile["executable"], "native executable")
    for entry in profile["config_sources"]:
        require_identity(entry, "config source")
    for entry in profile["instructions"]:
        require_identity(entry, "instruction source")
    for entry in profile["skills"]:
        require_identity(
            {
                key: entry[key]
                for key in ("path", "resolved", "bytes", "sha256")
            },
            "skill entrypoint",
        )
    for root, entries in profile["resource_trees"].items():
        actual = resource_tree(Path(root))
        require(
            actual == entries,
            "authoring resource tree differs: " + root,
        )


def retain_native_preparation_failure(
    output,
    phase,
    failure,
):
    retained = []
    preparation = output / "preparation"
    if preparation.is_dir():
        for path in sorted(preparation.rglob("*")):
            if path.is_file():
                raw = path.read_bytes()
                retained.append({
                    "path": path.relative_to(output).as_posix(),
                    "bytes": len(raw),
                    "sha256": sha(raw),
                })
    record = {
        "schema": "compatibility-native-preparation-failure/v1",
        "status": "incomplete",
        "phase": phase,
        "error": {
            "type": type(failure).__name__,
            "message": str(failure),
        },
        "terminal_boundary": {
            "phase": phase,
            "native_tasks_started": 0,
        },
        "retained_evidence": retained,
    }
    raw = encoded(record) + b"\n"
    put(output / "preparation-failure.json", raw)


def native_profile(raw, project):
    profile = json.loads(raw)
    require(
        profile.get("schema") == "compatibility-native-profile/v2"
        and profile.get("kind") == "native-app-server/v1"
        and profile.get("native_tasks_started") == 0,
        "invalid native profile",
    )
    require(
        isinstance(profile.get("model"), str)
        and profile["model"]
        and isinstance(profile.get("effort"), str)
        and profile["effort"],
        "native model and effort are required",
    )
    omission = profile.get("assessment_omission")
    require(
        isinstance(omission, dict)
        and set(omission) == {
            "mechanism",
            "overlay",
            "disabled_features",
            "product_enforcement",
            "runtime_assessments_absent",
        }
        and omission["mechanism"]
        == "bound-cooperative-instruction-overlay"
        and omission["disabled_features"] == ["hooks", "plugin_hooks"]
        and omission["product_enforcement"] == "unobserved"
        and omission["runtime_assessments_absent"] is None,
        "assessment omission is not the bound cooperative request",
    )
    require_identity(
        omission["overlay"],
        "instruction source",
    )
    overlay_path = project / OMISSION_OVERLAY_NAME
    require(
        omission["overlay"] == identity(overlay_path)
        and overlay_path.read_bytes() == OMISSION_OVERLAY_RAW,
        "cooperative omission overlay differs",
    )
    require(
        isinstance(profile.get("cli_version"), str)
        and profile["cli_version"]
        and isinstance(profile.get("initialize_user_agent"), str)
        and profile["initialize_user_agent"],
        "native version observations are required",
    )
    require(
        isinstance(profile.get("effective_config_sha256"), str)
        and re.fullmatch(
            r"[0-9a-f]{64}",
            profile["effective_config_sha256"],
        )
        and isinstance(
            profile.get("config_requirements_sha256"),
            str,
        )
        and re.fullmatch(
            r"[0-9a-f]{64}",
            profile["config_requirements_sha256"],
        ),
        "configuration observations are not bound",
    )
    require(
        isinstance(profile.get("config_sources"), list)
        and len(profile["config_sources"]) == 1
        and isinstance(profile.get("instructions"), list)
        and len(profile["instructions"]) == 2
        and profile["instructions"][1] == omission["overlay"]
        and profile.get("expected_instruction_sources")
        == [
            profile["instructions"][0]["path"],
            profile["instructions"][1]["path"],
        ],
        "expected instruction sources differ from their bound identity",
    )
    require(
        isinstance(profile.get("skills"), list)
        and isinstance(profile.get("resource_trees"), dict)
        and isinstance(profile.get("connectors"), list),
        "native profile inventory is incomplete",
    )

    verify_native_profile_sources(profile)

    available = {}
    for entry in profile["skills"]:
        short_name = entry["name"].split(":")[-1]
        available.setdefault(short_name, []).append(entry)
    for name in REQUIRED_AUTHORING_SKILLS:
        entries = available.get(name, [])
        require(
            entries and any(entry["enabled"] for entry in entries),
            "required authoring skill is missing or disabled: " + name,
        )
        require(
            all(
                str(Path(entry["path"]).parent)
                in profile["resource_trees"]
                for entry in entries
                if entry["enabled"]
            ),
            "required authoring resource tree is unbound: " + name,
        )

    require(
        profile["connectors"]
        == normalize_connectors(profile["connectors"]),
        "native connector inventory is not normalized",
    )

    executable = Path(profile["executable"]["path"])
    require(
        executable.is_absolute()
        and executable.is_file()
        and bool(executable.stat().st_mode & 0o111),
        "absolute executable native file required",
    )
    config_path = Path(profile["config_sources"][0]["path"])
    expected_command = native_command(
        executable,
        project,
        profile["model"],
        profile["effort"],
        configured_servers(config_path),
        os.environ.get("PATH", ""),
    )
    require(
        profile.get("command") == expected_command,
        "native command or environment differs",
    )
    return (
        profile,
        executable,
        checked(executable, profile["executable"]["sha256"]),
    )


def validate_model_catalog(result, model, effort):
    require(
        result.get("nextCursor") is None
        and isinstance(result.get("data"), list),
        "complete model catalog required; paging is unqualified",
    )
    matches = [
        item
        for item in result["data"]
        if item.get("model") == model
    ]
    require(
        len(matches) == 1,
        "model unavailable or ambiguous: expected " + model,
    )
    efforts = [
        item.get("reasoningEffort")
        for item in matches[0].get(
            "supportedReasoningEfforts",
            [],
        )
    ]
    require(
        effort in efforts,
        f"effort unavailable for {model}: "
        f"expected {effort}, observed {efforts}",
    )


def discover_native(
    executable,
    project,
    output,
    model,
    effort,
    command,
    config_path,
    instruction_path,
    overlay_path,
    preparation_state,
):
    transport = load_transport()
    preparation = output / "preparation"
    preparation.mkdir(exist_ok=False)
    results = {}
    pending = {}

    def send(raw_send, message):
        if "id" in message:
            require(
                message["id"] not in pending,
                "duplicate native preparation RPC",
            )
            pending[message["id"]] = message["method"]
            preparation_state["phase"] = (
                "profile-discovery:" + message["method"]
            )
        raw_send(message)

    def begin(raw_send):
        send(raw_send, {
            "id": 1,
            "method": "initialize",
            "params": {
                "clientInfo": {
                    "name": "compatibility-native-preparation",
                    "version": "2",
                },
                "capabilities": {"experimentalApi": True},
            },
        })

    def receive(message, raw_send):
        method = message.get("method")
        ident = message.get("id")
        require(
            not (method is not None and ident is not None),
            "native preparation requested permission or user input",
        )
        require(
            ident in pending
            and "result" in message
            and "error" not in message,
            "native preparation RPC failed",
        )
        request = pending.pop(ident)
        result = message["result"]

        if request == "initialize":
            user_agent = result.get("userAgent")
            require(
                isinstance(user_agent, str) and user_agent,
                "native initialize user agent is unavailable",
            )
            results["initialize_user_agent"] = user_agent
            send(raw_send, {"method": "initialized"})
            send(raw_send, {
                "id": 2,
                "method": "model/list",
                "params": {
                    "cursor": None,
                    "includeHidden": True,
                },
            })
        elif request == "model/list":
            validate_model_catalog(result, model, effort)
            send(raw_send, {
                "id": 10,
                "method": "config/read",
                "params": {
                    "cwd": str(project),
                    "includeLayers": False,
                },
            })
        elif request == "config/read":
            require(
                isinstance(result.get("config"), dict)
                and isinstance(result.get("origins"), dict),
                "effective native configuration is unavailable",
            )
            results["effective_config"] = result
            send(raw_send, {
                "id": 11,
                "method": "configRequirements/read",
            })
        elif request == "configRequirements/read":
            require(
                isinstance(result, dict)
                and (
                    result.get("requirements") is None
                    or isinstance(result.get("requirements"), dict)
                ),
                "invalid native configuration requirements",
            )
            results["config_requirements"] = result
            send(raw_send, {
                "id": 12,
                "method": "skills/list",
                "params": {
                    "cwds": [str(project)],
                    "forceReload": True,
                },
            })
        elif request == "skills/list":
            results["skills"] = skills_identity(result, project)
            send(raw_send, {
                "id": 13,
                "method": "mcpServerStatus/list",
                "params": {
                    "cursor": None,
                    "detail": "full",
                },
            })
        elif request == "mcpServerStatus/list":
            servers = result.get("data")
            require(
                result.get("nextCursor") is None
                and isinstance(servers, list),
                "connector inventory incomplete during preparation",
            )
            require(
                all(
                    server.get("runtimeStatus") in (None, "disabled")
                    and server.get("tools") == {}
                    for server in servers
                ),
                "active connector outside the native profile "
                "during preparation",
            )
            results["connectors"] = normalize_connectors(servers)
            return True
        return False

    transport.collect(
        command,
        project,
        preparation,
        "profile-discovery",
        time.monotonic() + 30,
        on_line=receive,
        begin=begin,
        max_output_bytes=67108864,
    )
    preparation_state["phase"] = "profile-discovery:completion"
    require(not pending, "native preparation ended with pending RPCs")

    skills = results["skills"]
    resource_trees = {}
    for entry in skills:
        name = entry["name"].split(":")[-1]
        if name in REQUIRED_AUTHORING_SKILLS and entry["enabled"]:
            root = Path(entry["path"]).parent
            resource_trees[str(root)] = resource_tree(root)

    available = {
        entry["name"].split(":")[-1]
        for entry in skills
        if entry["enabled"]
    }
    missing = sorted(REQUIRED_AUTHORING_SKILLS - available)
    require(
        not missing,
        "required authoring skills are missing or disabled: "
        + ", ".join(missing),
    )

    preparation_state["phase"] = "native-cli-version"
    version = subprocess.run(
        [str(executable), "--version"],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.strip()
    require(version, "native CLI version is unavailable")

    profile = {
        "schema": "compatibility-native-profile/v2",
        "kind": "native-app-server/v1",
        "executable": identity(executable),
        "cli_version": version,
        "initialize_user_agent": results["initialize_user_agent"],
        "command": command,
        "model": model,
        "effort": effort,
        "assessment_omission": {
            "mechanism": "bound-cooperative-instruction-overlay",
            "overlay": identity(overlay_path),
            "disabled_features": ["hooks", "plugin_hooks"],
            "product_enforcement": "unobserved",
            "runtime_assessments_absent": None,
        },
        "effective_config_sha256": sha(
            encoded(results["effective_config"])
        ),
        "config_requirements_sha256": sha(
            encoded(results["config_requirements"])
        ),
        "config_sources": [identity(config_path)],
        "instructions": [
            identity(instruction_path),
            identity(overlay_path),
        ],
        "expected_instruction_sources": [
            str(instruction_path),
            str(overlay_path),
        ],
        "skills": skills,
        "resource_trees": resource_trees,
        "connectors": results["connectors"],
        "native_tasks_started": 0,
    }
    verify_native_profile_sources(profile)
    return profile


def seed_inputs(args):
    packet = args.seed_package.resolve()
    receipt_raw = checked(
        packet / "receipt.json",
        args.seed_receipt_sha256,
    )
    receipt = json.loads(receipt_raw)
    require(
        receipt["version"] == 1
        and receipt["status"] == "ready"
        and receipt["producer_sha256"] == SEED_PRODUCER_SHA256,
        "unsupported seed preparation",
    )
    spec_raw = checked(packet / "spec.json", receipt["spec_sha256"])
    entries = receipt["seed"]["files"]
    names = [entry["path"] for entry in entries]
    require(
        names == sorted(set(names)) and names,
        "invalid seed file list",
    )
    identities = [
        {
            key: entry[key]
            for key in ("path", "sha256", "executable")
        }
        for entry in entries
    ]
    require(
        sha(encoded(identities)) == receipt["seed"]["identity"],
        "seed identity differs",
    )
    selected = args.implementation
    require(
        selected
        and len(set(selected)) == len(selected)
        and set(selected) <= set(names),
        "implementation paths must name unique declared seed files",
    )

    seed = []
    for entry in entries:
        path = relative(packet / "seed", entry["path"])
        raw = checked(path, entry["sha256"])
        require(
            bool(path.stat().st_mode & 0o111)
            == entry["executable"],
            "seed executable mode differs",
        )
        seed.append((entry, path, raw))

    require(
        len(receipt["requests"]) == 2,
        "exactly two ordered requests required",
    )
    requests = [
        (relative(packet, entry["output"]), entry)
        for entry in receipt["requests"]
    ]
    request_bytes = [
        checked(path, entry["sha256"])
        for path, entry in requests
    ]
    for raw in request_bytes:
        raw.decode("utf-8")
    return (
        packet,
        receipt,
        receipt_raw,
        spec_raw,
        seed,
        requests,
        request_bytes,
    )


def prepare(args):
    (
        packet,
        receipt,
        receipt_raw,
        spec_raw,
        seed,
        requests,
        request_bytes,
    ) = seed_inputs(args)
    checked(TRANSPORT, TRANSPORT_SHA256)
    checked(HERE / "prepare_seed.py", SEED_PRODUCER_SHA256)

    native = args.native
    git_evidence = native or args.git_evidence
    if git_evidence:
        checked(GIT_EVIDENCE, GIT_EVIDENCE_SHA256)
    if native:
        require(
            args.profile is None
            and args.profile_sha256 is None
            and args.native_executable is not None
            and args.native_executable_sha256 is not None
            and isinstance(args.model, str)
            and args.model
            and isinstance(args.effort, str)
            and args.effort,
            "native preparation requires executable, model, and effort "
            "without an external profile",
        )
        executable = args.native_executable.absolute()
        require(
            executable.is_absolute()
            and executable.is_file()
            and bool(executable.stat().st_mode & 0o111),
            "absolute executable native file required",
        )
        checked(executable, args.native_executable_sha256)
        home = codex_home()
        config_path = home / "config.toml"
        require(
            config_path.is_file(),
            "native config.toml is unavailable",
        )
        instruction_path = selected_instruction(home)
        server_names = configured_servers(config_path)
        fixture = None
        fixture_raw = None
        profile_path = None
    else:
        require(
            args.profile is not None
            and args.profile_sha256 is not None
            and args.native_executable is None
            and args.native_executable_sha256 is None
            and args.model is None
            and args.effort is None,
            "fake preparation requires its explicit profile",
        )
        profile_path = args.profile.resolve()
        profile_raw = checked(
            profile_path,
            args.profile_sha256,
        )
        profile, fixture, fixture_raw = fake_profile(profile_raw)

    output = args.output.absolute()
    require(
        output.resolve() == output,
        "output must not traverse symlinks",
    )
    inputs = [
        packet,
        HERE,
        TRANSPORT,
        *(
            [
                executable,
                config_path.resolve(),
                instruction_path.resolve(),
            ]
            if native
            else [profile_path, fixture]
        ),
    ]
    require(
        all(
            output != path
            and output not in path.parents
            and path not in output.parents
            for path in inputs
        ),
        "output overlaps an input",
    )

    source_paths = [
        Path(__file__).resolve(),
        HERE / "prepare_seed.py",
        TRANSPORT,
        packet / "receipt.json",
        packet / "spec.json",
        *(path for _, path, _ in seed),
        *(path for path, _ in requests),
    ]
    if native:
        source_paths.extend([
            executable,
            config_path.resolve(),
            instruction_path.resolve(),
        ])
    else:
        source_paths.extend([
            Path(sys.executable),
            profile_path,
            fixture,
        ])
    if git_evidence:
        source_paths.append(GIT_EVIDENCE)
    sources = {
        str(path): sha(path.read_bytes())
        for path in source_paths
    }

    output.mkdir(exist_ok=False)
    put(output / "seed-receipt.json", receipt_raw)
    put(output / "seed-spec.json", spec_raw)
    for entry, _, raw in seed:
        path = relative(output / "project", entry["path"])
        put(path, raw)
        path.chmod(entry["mode"])
    for index, raw in enumerate(request_bytes):
        put(output / f"request-{index}.bin", raw)

    project = output / "project"
    baseline_git = None
    if native:
        preparation_state = {
            "phase": "native-input-overlay",
        }
        try:
            (project / ".runner-tmp").mkdir(exist_ok=False)
            overlay_path = project / OMISSION_OVERLAY_NAME
            require(
                not overlay_path.exists(),
                "seed already supplies the native omission overlay path",
            )
            put(overlay_path, OMISSION_OVERLAY_RAW)
            preparation_state["phase"] = "git-baseline"
            baseline_git = load_git_evidence().prepare(
                project, output / "baseline-git",
            )
            preparation_state["phase"] = "native-command"
            command = native_command(
                executable,
                project,
                args.model,
                args.effort,
                server_names,
                os.environ.get("PATH", ""),
            )
            profile = discover_native(
                executable,
                project,
                output,
                args.model,
                args.effort,
                command,
                config_path.resolve(),
                instruction_path.resolve(),
                overlay_path,
                preparation_state,
            )
            preparation_state["phase"] = "profile-serialization"
            profile_raw = encoded(profile) + b"\n"
            put(output / "profile.json", profile_raw)
            deadline = 3600
            maximum = 67108864
        except Exception as failure:
            try:
                retain_native_preparation_failure(
                    output,
                    preparation_state["phase"],
                    failure,
                )
            except Exception as persistence_failure:
                raise RuntimeError(
                    "native preparation failed during "
                    + preparation_state["phase"]
                    + "; structured failure persistence also failed: "
                    + ascii(persistence_failure)
                ) from failure
            raise
    else:
        if git_evidence:
            baseline_git = load_git_evidence().prepare(
                project, output / "baseline-git",
            )
        put(output / "profile.json", profile_raw)
        put(output / "fixture.py", fixture_raw)
        command = [
            sys.executable,
            "-I",
            "-S",
            "-u",
            str(output / "fixture.py"),
        ]
        deadline = 10
        maximum = 2097152

    manifest = {
        "schema": (
            "compatibility-native-observation/v1"
            if native
            else "compatibility-fake-observation/v1"
        ),
        "root": str(output),
        "source_sha256": sources,
        "seed_receipt_sha256": sha(receipt_raw),
        "seed_spec_sha256": sha(spec_raw),
        "seed_identity": receipt["seed"]["identity"],
        "profile_sha256": sha(profile_raw),
        "git_baseline": baseline_git,
        "request_sha256": [sha(raw) for raw in request_bytes],
        "initial_files": {
            entry["path"]: entry["sha256"]
            for entry in receipt["seed"]["files"]
        },
        "implementation_paths": sorted(args.implementation),
        "deadline_seconds": deadline,
        "command": command,
        "native_execution_authorized": False,
        "profile_qualification": (
            "native-prepared-not-accepted"
            if native
            else "cooperative-fake-only"
        ),
    }
    if native:
        manifest.update(
            max_output_bytes=maximum,
            shutdown_wait_seconds=[5, 5],
        )
    else:
        manifest["fixture_sha256"] = sha(fixture_raw)

    raw = encoded(manifest) + b"\n"
    put(output / "manifest.json", raw)
    return {
        "manifest": str(output / "manifest.json"),
        "sha256": sha(raw),
    }


def source_inventory(project, inventory):
    started = time.monotonic()
    inventory.update({
        "status": "complete",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "excluded": [".git", "__pycache__", "*.pyc", "*.pyo"],
        "files": [],
        "scope": "regular files at a non-atomic observation boundary",
    })

    def visit(directory):
        require(stat.S_ISDIR(directory.lstat().st_mode),
                "source directory is not a regular directory")
        for path in sorted(directory.iterdir()):
            if (path.name in (".git", "__pycache__")
                    or path.suffix in (".pyc", ".pyo")):
                continue
            name = path.relative_to(project).as_posix()
            name.encode("utf-8")
            mode = path.lstat().st_mode
            if stat.S_ISDIR(mode):
                visit(path)
            else:
                require(stat.S_ISREG(mode), "unsupported source entry: " + name)
                raw = path.read_bytes()
                permissions = stat.S_IMODE(mode)
                inventory["files"].append({
                    "path": name, "sha256": sha(raw), "bytes": len(raw),
                    "mode": permissions, "executable": bool(permissions & 0o111),
                })

    try:
        visit(project)
    except BaseException as failure:
        inventory.update(status="incomplete", error=ascii(failure))
        if not isinstance(failure, Exception):
            raise
    finally:
        inventory["files"].sort(key=lambda entry: entry["path"])
        inventory["identity"] = (
            sha(encoded(inventory["files"]))
            if inventory["status"] == "complete" else None
        )
        inventory["finished_at"] = datetime.now(timezone.utc).isoformat()
        inventory["elapsed_seconds"] = time.monotonic() - started


def retain_final_source(project, attempt, state, collection_end):
    files = []
    inventory = {
        "schema": "compatibility-final-source/v1",
        "thread_id": state["thread_id"],
        "turn_id": state["turn_id"],
        "collection_end": collection_end,
        "excluded": [
            ".git",
            "__pycache__",
            "*.pyc",
            "*.pyo",
        ],
        "source_directory": "final-source",
        "files": files,
    }
    status = "complete"
    error = None

    def copy_tree(directory):
        require(
            stat.S_ISDIR(directory.lstat().st_mode),
            "source directory is not a regular directory",
        )
        for path in sorted(directory.iterdir()):
            if (
                path.name in (".git", "__pycache__")
                or path.suffix in (".pyc", ".pyo")
            ):
                continue
            name = path.relative_to(project).as_posix()
            name.encode("utf-8")
            mode = path.lstat().st_mode
            if stat.S_ISDIR(mode):
                copy_tree(path)
            else:
                require(
                    stat.S_ISREG(mode),
                    "unsupported source entry: " + name,
                )
                raw = path.read_bytes()
                retained = attempt / "final-source" / name
                put(retained, raw)
                permissions = stat.S_IMODE(mode)
                retained.chmod(permissions)
                checked(retained, sha(raw))
                require(
                    stat.S_IMODE(retained.stat().st_mode)
                    == permissions,
                    "retained source mode differs: " + name,
                )
                files.append({
                    "path": name,
                    "sha256": sha(raw),
                    "bytes": len(raw),
                    "mode": permissions,
                    "executable": bool(permissions & 0o111),
                })

    try:
        (attempt / "final-source").mkdir(exist_ok=False)
        copy_tree(project)
    except Exception as failure:
        status = "incomplete"
        error = ascii(failure)

    try:
        files.sort(key=lambda entry: entry["path"])
        inventory["identity"] = sha(encoded(files))
        inventory["status"] = status
        if error is not None:
            inventory["error"] = error
        raw = encoded(inventory) + b"\n"
        put(attempt / "final-source.json", raw)
    except Exception as failure:
        return {
            "status": "incomplete",
            "error": ascii(failure),
        }

    return {
        "status": status,
        "inventory": "final-source.json",
        "sha256": sha(raw),
    }


def usage_identifiers(params):
    if (
        not isinstance(params, dict)
        or not isinstance(params.get("threadId"), str)
        or not isinstance(params.get("turnId"), str)
    ):
        return None
    usage = params.get("tokenUsage")
    if not isinstance(usage, dict):
        return None
    if (
        "modelContextWindow" in usage
        and usage["modelContextWindow"] is not None
        and type(usage["modelContextWindow"]) is not int
    ):
        return None
    for name in ("last", "total"):
        counters = usage.get(name)
        if not isinstance(counters, dict):
            return None
        for field in (
            "cachedInputTokens",
            "inputTokens",
            "outputTokens",
            "reasoningOutputTokens",
            "totalTokens",
        ):
            if type(counters.get(field)) is not int:
                return None
        if (
            "cacheWriteInputTokens" in counters
            and type(counters["cacheWriteInputTokens"]) is not int
        ):
            return None
    return params["threadId"], params["turnId"]


def native_sandbox(record, project, key="sandbox"):
    policy = record.get(key, {})
    require(
        policy.get("type") == "workspaceWrite"
        and policy.get("writableRoots", []) in (
            [],
            [str(project)],
        )
        and policy.get("networkAccess") is False
        and policy.get("excludeTmpdirEnvVar") is True
        and policy.get("excludeSlashTmp") is True,
        "effective native sandbox differs",
    )


def run(args):
    raw = checked(args.manifest, args.expected_sha256)
    manifest = json.loads(raw)
    root = args.manifest.resolve().parent
    native = (
        manifest.get("schema")
        == "compatibility-native-observation/v1"
    )
    require(
        manifest.get("schema")
        in (
            "compatibility-fake-observation/v1",
            "compatibility-native-observation/v1",
        )
        and manifest.get("root") == str(root)
        and manifest.get("native_execution_authorized") is False
        and manifest.get("profile_qualification")
        == (
            "native-prepared-not-accepted"
            if native
            else "cooperative-fake-only"
        ),
        "unsupported prepared observation",
    )
    require(
        args.accept_native if native else not args.accept_native,
        (
            "separately accepted native invocation required"
            if native
            else "native acceptance flag cannot change a fake manifest"
        ),
    )
    if native:
        require(
            type(manifest.get("deadline_seconds")) is int
            and manifest["deadline_seconds"] == 3600
            and type(manifest.get("max_output_bytes")) is int
            and manifest["max_output_bytes"] == 67108864
            and manifest.get("shutdown_wait_seconds") == [5, 5],
            "native transport bounds differ",
        )

    attempt = root / "attempt"
    attempt.mkdir(exist_ok=False)
    state = {
        "status": "incomplete",
        "thread_id": None,
        "turn_id": None,
        "amendment_rpc_accepted": False,
        "semantic_success": "not-assessed",
        "trigger_observation_sequence": None,
    }
    baseline_git = None
    usage_events = []
    invalid_usage_events = []
    last_received_sequence = None

    try:
        for name, expected in manifest["source_sha256"].items():
            checked(Path(name), expected)

        if native:
            require(manifest.get("git_baseline") is not None,
                    "native observation requires a bound Git baseline")
        baseline_ref = manifest.get("git_baseline")
        if baseline_ref is not None:
            require(baseline_ref.get("path") == "baseline-git/baseline.json",
                    "unsupported baseline Git record")
            baseline_git = json.loads(checked(
                root / baseline_ref["path"], baseline_ref["sha256"],
            ))
            load_git_evidence().verify(
                root / "project", baseline_git, attempt / "baseline-preflight",
            )

        profile_raw = checked(
            root / "profile.json",
            manifest["profile_sha256"],
        )
        project = root / "project"

        if native:
            profile, executable, _ = native_profile(
                profile_raw,
                project,
            )
            require(
                manifest["command"] == profile["command"],
                "prepared native command differs",
            )
            state.update(
                native_invocation_accepted=True,
                assessment_omission=profile[
                    "assessment_omission"
                ],
                permission_enforcement="unobserved",
            )
        else:
            profile, _, _ = fake_profile(profile_raw)
            checked(
                root / "fixture.py",
                profile["fixture_sha256"],
            )
            require(
                manifest["fixture_sha256"]
                == profile["fixture_sha256"]
                and manifest["command"]
                == [
                    sys.executable,
                    "-I",
                    "-S",
                    "-u",
                    str(root / "fixture.py"),
                ],
                "prepared command differs",
            )

        receipt = json.loads(checked(
            root / "seed-receipt.json",
            manifest["seed_receipt_sha256"],
        ))
        checked(
            root / "seed-spec.json",
            manifest["seed_spec_sha256"],
        )
        for name, expected in manifest["initial_files"].items():
            checked(relative(project, name), expected)
        for entry in receipt["seed"]["files"]:
            path = relative(project, entry["path"])
            mode = stat.S_IMODE(path.stat().st_mode)
            require(
                mode == entry["mode"]
                and bool(mode & 0o111) == entry["executable"],
                f"seed file mode differs: {path} "
                f"(expected {entry['mode']:04o}, got {mode:04o})",
            )

        requests = [
            checked(
                root / f"request-{index}.bin",
                expected,
            ).decode("utf-8")
            for index, expected
            in enumerate(manifest["request_sha256"])
        ]
        require(
            len(requests) == 2,
            "exactly two requests required",
        )

        if native:
            observed_version = subprocess.run(
                [str(executable), "--version"],
                cwd=project,
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            ).stdout.strip()
            require(
                observed_version == profile["cli_version"],
                "native CLI version differs from preparation",
            )

        transport = load_transport()
        native_shaped = native or (
            profile["kind"]
            == "cooperative-native-app-server-fake/v1"
        )

        with (attempt / "receipts.jsonl").open("xb") as journal:
            sequence = 0
            received_offset = 0
            sent_offset = 0
            pending = {}

            def record(kind, **fields):
                nonlocal sequence
                row = {
                    "sequence": sequence,
                    "observed_at": datetime.now(
                        timezone.utc
                    ).isoformat(),
                    "kind": kind,
                    **fields,
                }
                journal.write(encoded(row) + b"\n")
                journal.flush()
                sequence += 1
                return row["sequence"]

            def wire(filename, offset):
                with (attempt / filename).open("rb") as stream:
                    stream.seek(offset)
                    line = stream.readline()
                require(
                    line.endswith(b"\n"),
                    "incomplete retained protocol line",
                )
                return {
                    "file": filename,
                    "offset": offset,
                    "bytes": len(line),
                    "sha256": sha(line),
                }

            def send(raw_send, message):
                nonlocal sent_offset
                if message.get("method") == "turn/start" and baseline_git is not None:
                    load_git_evidence().verify(
                        project, baseline_git, attempt / "task-delivery-git",
                    )
                if "id" in message:
                    require(
                        message["id"] not in pending,
                        "duplicate outbound RPC",
                    )
                    pending[message["id"]] = message["method"]
                raw_send(message)
                reference = wire(
                    "collector-sent.jsonl",
                    sent_offset,
                )
                sent_offset += reference["bytes"]
                record(
                    "sent",
                    message=message,
                    wire=reference,
                )

            def begin(raw_send):
                send(raw_send, {
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "clientInfo": {
                            "name": (
                                "compatibility-native-observation"
                                if native
                                else "compatibility-fake-observation"
                            ),
                            "version": "2" if native else "1",
                        },
                        "capabilities": {
                            "experimentalApi": True,
                        },
                    },
                })

            def native_response(
                request,
                message,
                raw_send,
                event_sequence,
            ):
                result = message["result"]
                if request == "initialize":
                    require(
                        result.get("userAgent")
                        == profile["initialize_user_agent"],
                        "native initialize user agent differs",
                    )
                    send(raw_send, {"method": "initialized"})
                    send(raw_send, {
                        "id": 2,
                        "method": "model/list",
                        "params": {
                            "cursor": None,
                            "includeHidden": True,
                        },
                    })
                elif request == "model/list":
                    validate_model_catalog(
                        result,
                        profile["model"],
                        profile["effort"],
                    )
                    send(raw_send, {
                        "id": 10,
                        "method": "config/read",
                        "params": {
                            "cwd": str(project),
                            "includeLayers": False,
                        },
                    })
                elif request == "config/read":
                    require(
                        sha(encoded(result))
                        == profile["effective_config_sha256"],
                        "effective native configuration differs "
                        "from preparation",
                    )
                    send(raw_send, {
                        "id": 11,
                        "method": "configRequirements/read",
                    })
                elif request == "configRequirements/read":
                    require(
                        sha(encoded(result))
                        == profile[
                            "config_requirements_sha256"
                        ],
                        "native configuration requirements differ "
                        "from preparation",
                    )
                    send(raw_send, {
                        "id": 12,
                        "method": "skills/list",
                        "params": {
                            "cwds": [str(project)],
                            "forceReload": True,
                        },
                    })
                elif request == "skills/list":
                    require(
                        skills_identity(result, project)
                        == profile["skills"],
                        "native authoring inventory differs",
                    )
                    verify_native_profile_sources(profile)
                    send(raw_send, {
                        "id": 14,
                        "method": "thread/start",
                        "params": {
                            "cwd": str(project),
                            "model": profile["model"],
                            "approvalPolicy": "on-request",
                            "approvalsReviewer": "user",
                            "sandbox": "workspace-write",
                            "ephemeral": False,
                            "historyMode": "paginated",
                            "allowProviderModelFallback": False,
                            "runtimeWorkspaceRoots": [
                                str(project),
                            ],
                            "environments": [],
                            "config": {
                                "sandbox_workspace_write": {
                                    "writable_roots": [],
                                    "network_access": False,
                                    "exclude_tmpdir_env_var": True,
                                    "exclude_slash_tmp": True,
                                },
                            },
                        },
                    })
                elif request == "thread/start":
                    thread = result.get("thread", {})
                    require(
                        result.get("model") == profile["model"]
                        and result.get("reasoningEffort")
                        == profile["effort"]
                        and result.get("cwd") == str(project)
                        and result.get("runtimeWorkspaceRoots")
                        == [str(project)]
                        and result.get("approvalPolicy")
                        == "on-request"
                        and result.get("approvalsReviewer")
                        == "user"
                        and result.get("instructionSources")
                        == profile[
                            "expected_instruction_sources"
                        ]
                        and thread.get("cliVersion")
                        == profile["cli_version"].removeprefix(
                            "codex-cli "
                        )
                        and thread.get("turns") == [],
                        "fresh native thread or profile metadata "
                        "differs",
                    )
                    native_sandbox(result, project)
                    state["thread_id"] = thread["id"]
                    state["profile_observation_sequence"] = record(
                        "native-profile-observed",
                        response_sequence=event_sequence,
                        requested_model=profile["model"],
                        requested_turn_effort=profile["effort"],
                        effective_profile={
                            key: value
                            for key, value in result.items()
                            if key != "thread"
                        },
                    )
                    send(raw_send, {
                        "id": 13,
                        "method": "mcpServerStatus/list",
                        "params": {
                            "threadId": state["thread_id"],
                            "cursor": None,
                            "detail": "full",
                        },
                    })
                elif request == "mcpServerStatus/list":
                    servers = result.get("data")
                    require(
                        result.get("nextCursor") is None
                        and isinstance(servers, list)
                        and all(
                            server.get("runtimeStatus")
                            == "disabled"
                            and server.get("tools") == {}
                            for server in servers
                        ),
                        "active connector outside the native profile",
                    )
                    observed = normalize_connectors(servers)
                    require(
                        observed == profile["connectors"],
                        "native connector inventory differs",
                    )
                    verify_native_profile_sources(profile)
                    send(raw_send, {
                        "id": 3,
                        "method": "turn/start",
                        "params": {
                            "threadId": state["thread_id"],
                            "model": profile["model"],
                            "effort": profile["effort"],
                            "cwd": str(project),
                            "approvalPolicy": "on-request",
                            "approvalsReviewer": "user",
                            "runtimeWorkspaceRoots": [
                                str(project),
                            ],
                            "environments": [],
                            "input": [{
                                "type": "text",
                                "text": requests[0],
                                "text_elements": [],
                            }],
                            "sandboxPolicy": {
                                "type": "workspaceWrite",
                                "writableRoots": [],
                                "networkAccess": False,
                                "excludeTmpdirEnvVar": True,
                                "excludeSlashTmp": True,
                            },
                        },
                    })
                elif request == "turn/start":
                    state["turn_id"] = result["turn"]["id"]
                elif request == "turn/steer":
                    returned = result["turnId"]
                    require(
                        returned == state["turn_id"],
                        "steer returned another turn",
                    )
                    state["amendment_rpc_accepted"] = True
                    record(
                        "amendment-rpc-accepted",
                        response_sequence=event_sequence,
                        returned_turn_id=returned,
                        semantic_success="not-assessed",
                    )

            def fake_response(
                request,
                message,
                raw_send,
                event_sequence,
            ):
                result = message["result"]
                if request == "initialize":
                    if native_shaped:
                        expected = profile[
                            "app_server_profile"
                        ]["version"]
                        observed = result.get("userAgent")
                        require(
                            observed == expected,
                            f"server version differs: "
                            f"expected {expected}, "
                            f"observed {observed}",
                        )
                        if (
                            "model"
                            not in profile["app_server_profile"]
                        ):
                            raise ValueError(
                                "native-shaped fake metadata "
                                "sequence is incomplete"
                            )
                        send(raw_send, {"method": "initialized"})
                        send(raw_send, {
                            "id": 2,
                            "method": "model/list",
                            "params": {
                                "cursor": None,
                                "includeHidden": True,
                            },
                        })
                        return
                    send(raw_send, {"method": "initialized"})
                    send(raw_send, {
                        "id": 2,
                        "method": "thread/start",
                        "params": {"cwd": str(project)},
                    })
                elif request == "model/list":
                    expected = profile["app_server_profile"]
                    validate_model_catalog(
                        result,
                        expected["model"],
                        expected["effort"],
                    )
                    send(raw_send, {
                        "id": 10,
                        "method": "config/read",
                        "params": {
                            "cwd": str(project),
                            "includeLayers": False,
                        },
                    })
                elif request == "config/read":
                    require(
                        isinstance(result.get("config"), dict)
                        and isinstance(
                            result.get("origins"),
                            dict,
                        ),
                        "synthetic effective config and origins "
                        "required",
                    )
                    send(raw_send, {
                        "id": 11,
                        "method": "configRequirements/read",
                    })
                elif request == "configRequirements/read":
                    require(
                        isinstance(result, dict)
                        and (
                            result.get("requirements") is None
                            or isinstance(
                                result.get("requirements"),
                                dict,
                            )
                        ),
                        "invalid synthetic requirements observation",
                    )
                    send(raw_send, {
                        "id": 12,
                        "method": "skills/list",
                        "params": {
                            "cwds": [str(project)],
                            "forceReload": False,
                        },
                    })
                elif request == "skills/list":
                    require(
                        isinstance(result.get("data"), list),
                        "synthetic skills inventory required",
                    )
                    send(raw_send, {
                        "id": 13,
                        "method": "mcpServerStatus/list",
                        "params": {
                            "cursor": None,
                            "detail": "full",
                        },
                    })
                elif request == "mcpServerStatus/list":
                    require(
                        isinstance(result.get("data"), list)
                        and result.get("nextCursor") is None,
                        "complete synthetic MCP inventory required; "
                        "paging is unqualified",
                    )
                    send(raw_send, {
                        "id": 14,
                        "method": "thread/start",
                        "params": {
                            "cwd": str(project),
                            "model": profile[
                                "app_server_profile"
                            ]["model"],
                            "approvalPolicy": "on-request",
                            "approvalsReviewer": "user",
                            "sandbox": "workspace-write",
                            "ephemeral": False,
                            "historyMode": "paginated",
                            "allowProviderModelFallback": False,
                            "runtimeWorkspaceRoots": [str(project)],
                            "environments": [],
                            "config": {
                                "sandbox_workspace_write": {
                                    "writable_roots": [],
                                    "network_access": False,
                                    "exclude_tmpdir_env_var": True,
                                    "exclude_slash_tmp": True,
                                },
                            },
                        },
                    })
                elif request == "thread/start":
                    state["thread_id"] = result["thread"]["id"]
                    if native_shaped:
                        expected = profile["app_server_profile"]
                        require(
                            result["model"] == expected["model"],
                            f"thread model differs: expected "
                            f"{expected['model']}, observed "
                            f"{result['model']}",
                        )
                        require(
                            result.get("runtimeWorkspaceRoots")
                            == [str(project)],
                            "native-shaped runtime workspace roots "
                            "differ",
                        )
                        require(
                            result.get("reasoningEffort")
                            == expected["effort"],
                            "native-shaped thread reasoning effort "
                            "differs",
                        )
                        state[
                            "profile_observation_sequence"
                        ] = record(
                            "fake-profile-observed",
                            response_sequence=event_sequence,
                            requested_model=expected["model"],
                            requested_turn_effort=expected["effort"],
                            effective_profile={
                                key: value
                                for key, value in result.items()
                                if key != "thread"
                            },
                        )
                        if not expected.get(
                            "observe_turn",
                            False,
                        ):
                            state["status"] = (
                                "fake-profile-observed"
                            )
                            return True
                    params = {
                        "threadId": state["thread_id"],
                        "input": [{
                            "type": "text",
                            "text": requests[0],
                            "text_elements": [],
                        }],
                    }
                    if native_shaped:
                        params.update(
                            model=expected["model"],
                            effort=expected["effort"],
                            cwd=str(project),
                            approvalPolicy="on-request",
                            approvalsReviewer="user",
                            runtimeWorkspaceRoots=[str(project)],
                            environments=[],
                            sandboxPolicy={
                                "type": "workspaceWrite",
                                "writableRoots": [],
                                "networkAccess": False,
                                "excludeTmpdirEnvVar": True,
                                "excludeSlashTmp": True,
                            },
                        )
                    send(raw_send, {
                        "id": 3,
                        "method": "turn/start",
                        "params": params,
                    })
                elif request == "turn/start":
                    state["turn_id"] = result["turn"]["id"]
                elif request == "turn/steer":
                    returned = result["turnId"]
                    require(
                        returned == state["turn_id"],
                        "steer returned another turn",
                    )
                    state["amendment_rpc_accepted"] = True
                    record(
                        "amendment-rpc-accepted",
                        response_sequence=event_sequence,
                        returned_turn_id=returned,
                        semantic_success="not-assessed",
                    )
                return False

            def receive(message, raw_send):
                nonlocal received_offset
                nonlocal last_received_sequence

                reference = wire(
                    "collector-stdout.log",
                    received_offset,
                )
                received_offset += reference["bytes"]
                event_sequence = record(
                    "received",
                    message=message,
                    wire=reference,
                )
                last_received_sequence = event_sequence
                method = message.get("method")
                ident = message.get("id")

                if method is not None and ident is not None:
                    if native:
                        put(
                            attempt
                            / "native-unanswered-request.json",
                            encoded(message) + b"\n",
                        )
                        raise ValueError(
                            "native permission or user input "
                            "requires adjudication"
                        )
                    raise ValueError(
                        "server input request is unsupported "
                        "and remains unanswered"
                    )

                if ident is not None:
                    if native and "error" in message:
                        put(
                            attempt / "native-rpc-error.json",
                            encoded(message) + b"\n",
                        )
                    require(
                        ident in pending
                        and "result" in message
                        and "error" not in message,
                        "unexpected or rejected RPC response",
                    )
                    request = pending.pop(ident)
                    if native:
                        native_response(
                            request,
                            message,
                            raw_send,
                            event_sequence,
                        )
                    else:
                        terminal = fake_response(
                            request,
                            message,
                            raw_send,
                            event_sequence,
                        )
                        if terminal:
                            return True

                elif (
                    native_shaped
                    and method == "thread/settings/updated"
                ):
                    data = message.get("params", {})
                    if data.get("threadId") == state["thread_id"]:
                        settings = data.get(
                            "threadSettings",
                            {},
                        )
                        selected_model = (
                            profile["model"]
                            if native
                            else profile[
                                "app_server_profile"
                            ]["model"]
                        )
                        selected_effort = (
                            profile["effort"]
                            if native
                            else profile[
                                "app_server_profile"
                            ]["effort"]
                        )
                        require(
                            settings.get("model")
                            == selected_model
                            and settings.get("effort")
                            == selected_effort
                            and settings.get("cwd")
                            == str(project)
                            and settings.get("approvalPolicy")
                            == "on-request"
                            and settings.get(
                                "approvalsReviewer"
                            )
                            == "user",
                            "native turn settings differ",
                        )
                        native_sandbox(
                            settings,
                            project,
                            "sandboxPolicy",
                        )

                elif method == "thread/tokenUsage/updated":
                    identifiers = usage_identifiers(
                        message.get("params")
                    )
                    if identifiers is None:
                        invalid_usage_events.append(
                            event_sequence
                        )
                    else:
                        usage_events.append(
                            (event_sequence, *identifiers)
                        )

                elif method in ("item/started", "item/completed"):
                    data = message["params"]
                    item = data.get("item", {})
                    if (
                        data.get("threadId")
                        == state["thread_id"]
                        and data.get("turnId")
                        == state["turn_id"]
                        and state["turn_id"] is not None
                        and item.get("type") in TOOLS
                    ):
                        inventory = {}
                        details = {}
                        try:
                            source_inventory(project, inventory)
                            if method == "item/completed":
                                try:
                                    changed = {}
                                    for name in manifest["implementation_paths"]:
                                        path = relative(project, name)
                                        after = (
                                            sha(path.read_bytes())
                                            if path.exists() else None
                                        )
                                        before = manifest["initial_files"][name]
                                        if after != before:
                                            changed[name] = {
                                                "before": before,
                                                "after": after,
                                            }
                                except BaseException as failure:
                                    details["change_detection_error"] = ascii(failure)
                                    raise
                                details["changed"] = changed
                        finally:
                            observed = record(
                                "tool-" + method.split("/")[1],
                                event_sequence=event_sequence,
                                thread_id=state["thread_id"],
                                turn_id=state["turn_id"],
                                item=item,
                                item_sha256=sha(encoded(item)),
                                source_inventory=inventory,
                                **details,
                            )
                        if method == "item/started":
                            return False
                        if (
                            changed
                            and state[
                                "trigger_observation_sequence"
                            ]
                            is None
                        ):
                            state[
                                "trigger_observation_sequence"
                            ] = observed
                            record(
                                "amendment-trigger",
                                observation_sequence=observed,
                            )
                            send(raw_send, {
                                "id": 4,
                                "method": "turn/steer",
                                "params": {
                                    "threadId": state[
                                        "thread_id"
                                    ],
                                    "expectedTurnId": state[
                                        "turn_id"
                                    ],
                                    "input": [{
                                        "type": "text",
                                        "text": requests[1],
                                        "text_elements": [],
                                    }],
                                },
                            })

                elif method == "turn/completed":
                    data = message["params"]
                    if (
                        data.get("threadId")
                        == state["thread_id"]
                    ):
                        turn = data["turn"]
                        require(
                            turn["id"] == state["turn_id"]
                            and turn["status"] == "completed"
                            and turn.get("error") is None,
                            "turn did not complete successfully",
                        )
                        require(
                            state["amendment_rpc_accepted"]
                            and not pending,
                            "turn ended without an accepted "
                            "amendment",
                        )
                        record(
                            "turn-completed",
                            event_sequence=event_sequence,
                        )
                        return True
                return False

            transport.collect(
                manifest["command"],
                project,
                attempt,
                "collector",
                time.monotonic()
                + manifest["deadline_seconds"],
                on_line=receive,
                begin=begin,
                max_output_bytes=manifest.get(
                    "max_output_bytes",
                    2097152,
                ),
            )

        if state["status"] == "incomplete":
            state["status"] = (
                "native-observation-completed"
                if native
                else "fake-observation-completed"
            )
        return state

    except Exception as error:
        state["error"] = (
            type(error).__name__ + ": " + str(error)
        )
        raise

    finally:
        usage = {
            "schema": "compatibility-usage-observations/v1",
            "root_event_sequences": [],
            "other_event_sequences": [],
            "invalid_event_sequences": invalid_usage_events,
            "whole_episode_tokens": None,
            "whole_child_usage": {
                "status": "unknown",
                "reason": (
                    "the collector does not establish the "
                    "complete child set or complete child histories"
                ),
            },
            "collection_end": {
                "reason": {
                    "fake-observation-completed":
                        "root-turn-completed",
                    "native-observation-completed":
                        "root-turn-completed",
                    "fake-profile-observed": "profile-only",
                }.get(state["status"], "incomplete"),
                "event_sequence": last_received_sequence,
            },
        }
        for event_sequence, thread_id, turn_id in usage_events:
            category = (
                "root_event_sequences"
                if (
                    state["thread_id"] is not None
                    and state["turn_id"] is not None
                    and (thread_id, turn_id)
                    == (
                        state["thread_id"],
                        state["turn_id"],
                    )
                )
                else "other_event_sequences"
            )
            usage[category].append(event_sequence)

        state["usage_observations"] = usage
        state["final_source"] = retain_final_source(
            root / "project",
            attempt,
            state,
            usage["collection_end"],
        )
        if baseline_git is not None:
            try:
                final_inventory = {"status": "incomplete", "files": []}
                try:
                    final_inventory = json.loads(checked(
                        attempt / "final-source.json",
                        state["final_source"]["sha256"],
                    ))
                except Exception as error:
                    final_inventory["error"] = type(error).__name__ + ": " + str(error)
                state["final_git"] = load_git_evidence().capture(
                    root / "project", attempt / "final-git",
                    baseline_git, final_inventory,
                )
            except Exception as error:
                state["final_git"] = {
                    "status": "incomplete",
                    "error": type(error).__name__ + ": " + str(error),
                }
        elif manifest.get("git_baseline") is not None:
            state["final_git"] = {
                "status": "not-collected",
                "reason": "bound Git baseline not established before failure",
            }
        put(
            attempt / "outcome.json",
            encoded(state) + b"\n",
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(
        dest="operation",
        required=True,
    )

    preparation = commands.add_parser("prepare")
    preparation.add_argument(
        "--seed-package",
        type=Path,
        required=True,
    )
    preparation.add_argument(
        "--seed-receipt-sha256",
        required=True,
    )
    preparation.add_argument(
        "--git-evidence", action="store_true",
        help="include the mandatory native Git evidence in a cooperative fake",
    )
    preparation.add_argument("--profile", type=Path)
    preparation.add_argument("--profile-sha256")
    preparation.add_argument(
        "--implementation",
        action="append",
        required=True,
    )
    preparation.add_argument(
        "--output",
        type=Path,
        required=True,
    )
    preparation.add_argument(
        "--native",
        action="store_true",
    )
    preparation.add_argument(
        "--native-executable",
        type=Path,
    )
    preparation.add_argument(
        "--native-executable-sha256",
    )
    preparation.add_argument("--model")
    preparation.add_argument("--effort")

    execution = commands.add_parser("run")
    execution.add_argument(
        "--manifest",
        type=Path,
        required=True,
    )
    execution.add_argument(
        "--expected-sha256",
        required=True,
    )
    execution.add_argument(
        "--accept-native",
        action="store_true",
    )

    args = parser.parse_args()
    try:
        result = (
            prepare(args)
            if args.operation == "prepare"
            else run(args)
        )
    except Exception as error:
        print(
            type(error).__name__ + ": " + str(error),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
