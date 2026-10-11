"""Public preparation/run CLI contract; no provider or native model."""
import hashlib
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
COLLECTOR = HERE / "collect_observation.py"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode()


class CollectorCLI(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name)
        hooks = base / "empty-hooks"
        hooks.mkdir()
        config = base / "gitconfig"
        config.write_text(
            "[user]\nname = Compatibility Fixture\nemail = fixture@example.invalid\n"
            "[commit]\ngpgsign = false\n[core]\nhooksPath = " + str(hooks) + "\n"
        )
        environment = {name: value for name, value in os.environ.items()
                       if not name.startswith("GIT_")}
        environment.update(GIT_CONFIG_GLOBAL=str(config),
                           GIT_CONFIG_SYSTEM=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        changing_environment = patch.dict(os.environ, environment, clear=True)
        changing_environment.start()
        self.addCleanup(changing_environment.stop)

    def test_native_cli_discovers_profile_requires_acceptance_and_refuses_drift(self):
        cli, _, legacy = self.prepare_failure_fixture("sys.stdin.buffer.read()\n")
        base = legacy.parent
        packet = base / "packet"
        codex_home = base / "codex-home"
        codex_home.mkdir()
        instruction = codex_home / "AGENTS.md"
        instruction.write_text("# Synthetic native instructions\n")
        (codex_home / "config.toml").write_text(
            '[mcp_servers.alpha]\ncommand = "unused"\n'
        )

        required = (
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
        )
        skills = []
        for name in required:
            path = codex_home / "skills" / name / "SKILL.md"
            path.parent.mkdir(parents=True)
            path.write_text(f"# {name}\n")
            reference = path.parent / "references" / "contract.md"
            reference.parent.mkdir()
            reference.write_text(f"# {name} contract\n")
            skills.append({
                "name": name,
                "enabled": True,
                "scope": "user",
                "path": str(path),
            })
        jev_axi = codex_home / "skills" / "jev-axi" / "SKILL.md"
        jev_axi.parent.mkdir(parents=True)
        jev_axi.write_text("# jev-axi\n")
        skills.append({
            "name": "jev-axi",
            "enabled": True,
            "scope": "user",
            "path": str(jev_axi),
        })

        effective_config = {
            "config": {
                "model": "gpt-6.1-sol",
                "model_reasoning_effort": "medium",
                "agents": {
                    # A legitimate installed setting is observation data. The
                    # collector must not replace or reject it.
                    "max_concurrent_threads_per_session": 8,
                },
            },
            "origins": {},
        }
        requirements = {"requirements": None}
        connectors = [
            {
                "name": "alpha",
                "pluginId": None,
                "runtimeStatus": "disabled",
                "tools": {},
            },
            {
                "name": "cua_repl",
                "pluginId": "unified-computer-use@openai-bundled",
                "runtimeStatus": "disabled",
                "tools": {},
            },
        ]

        executable = base / "codex-fixture"
        executable.write_text(
            "#!" + sys.executable + "\n"
            + "SKILLS = " + repr(skills) + "\n"
            + "EFFECTIVE_CONFIG = " + repr(effective_config) + "\n"
            + "REQUIREMENTS = " + repr(requirements) + "\n"
            + "CONNECTORS = " + repr(connectors) + "\n"
            + "INSTRUCTION = " + repr(str(instruction)) + "\n"
            + r'''
import json
from pathlib import Path
import sys

if sys.argv[1:] == ["--version"]:
    print("codex-cli 9.9.9")
    raise SystemExit(0)

assert sys.argv[1:5] == [
    "--no-daemon", "app-server", "--stdio", "--strict-config"
], sys.argv
arguments = sys.argv[1:]
for feature in (
    "hooks", "plugin_hooks", "memories", "apps", "shell_snapshot",
    "browser_use", "computer_use", "image_generation",
):
    position = arguments.index("--disable")
    assert feature in arguments, (feature, arguments)
assert "agents.max_concurrent_threads_per_session=2" not in arguments
assert not any("synthetic_assessments" in value for value in arguments)

counter = Path(__file__).with_name("native-launch-count")
launches = int(counter.read_text()) if counter.exists() else 0
counter.write_text(str(launches + 1))

def receive(method=None):
    message = json.loads(sys.stdin.buffer.readline())
    if method is not None:
        assert message["method"] == method, message
    return message

def emit(request, result):
    sys.stdout.buffer.write((json.dumps({
        "id": request["id"], "result": result,
    }) + "\n").encode())
    sys.stdout.buffer.flush()

def notify(message):
    sys.stdout.buffer.write((json.dumps(message) + "\n").encode())
    sys.stdout.buffer.flush()

first = receive("initialize")
emit(first, {
    "userAgent": "synthetic-native/9.9.9",
    "codexHome": str(Path(INSTRUCTION).parent),
    "platformFamily": "unix",
    "platformOs": "linux",
})
receive("initialized")

listing = receive("model/list")
emit(listing, {
    "data": [{
        "id": "synthetic-sol",
        "model": "gpt-6.1-sol",
        "displayName": "Synthetic Sol",
        "description": "Cooperative native fixture",
        "hidden": False,
        "isDefault": True,
        "defaultReasoningEffort": "medium",
        "supportedReasoningEfforts": [{
            "reasoningEffort": "medium",
            "description": "Medium",
        }],
    }],
    "nextCursor": None,
})

config = receive("config/read")
assert config["params"] == {
    "cwd": str(Path.cwd()),
    "includeLayers": False,
}, config
emit(config, EFFECTIVE_CONFIG)

requirements = receive("configRequirements/read")
assert requirements.get("params") is None, requirements
emit(requirements, REQUIREMENTS)

skills = receive("skills/list")
assert skills["params"] == {
    "cwds": [str(Path.cwd())],
    "forceReload": True,
}, skills
# Deliberately vary row order between launches.
returned_skills = list(reversed(SKILLS)) if launches else SKILLS
emit(skills, {
    "data": [{
        "cwd": str(Path.cwd()),
        "skills": returned_skills,
        "errors": [],
    }],
})

next_message = receive()
if next_message["method"] == "mcpServerStatus/list":
    assert next_message["params"] == {
        "cursor": None,
        "detail": "full",
    }, next_message
    emit(next_message, {
        "data": list(reversed(CONNECTORS)),
        "nextCursor": None,
    })
    # Preparation must stop here without creating a thread or turn.
    sys.stdin.buffer.read()
    raise SystemExit(0)

assert next_message["method"] == "thread/start", next_message
overlay = Path.cwd() / "AGENTS.override.md"
assert overlay.read_text() == (
    "# Compatibility observation instruction overlay\n\n"
    "For this task, do not invoke, consult, or use `jev-axi` or any "
    "Jev assessment.\n"
    "All other standing instructions remain in effect.\n"
), overlay.read_text()
assert next_message["params"] == {
    "cwd": str(Path.cwd()),
    "model": "gpt-6.1-sol",
    "approvalPolicy": "on-request",
    "approvalsReviewer": "user",
    "sandbox": "workspace-write",
    "ephemeral": False,
    "historyMode": "paginated",
    "allowProviderModelFallback": False,
    "runtimeWorkspaceRoots": [str(Path.cwd())],
    "environments": [],
    "config": {
        "sandbox_workspace_write": {
            "writable_roots": [],
            "network_access": False,
            "exclude_tmpdir_env_var": True,
            "exclude_slash_tmp": True,
        },
    },
}, next_message
emit(next_message, {
    "model": "gpt-6.1-sol",
    "cwd": str(Path.cwd()),
    "approvalPolicy": "on-request",
    "approvalsReviewer": "user",
    "instructionSources": [INSTRUCTION, str(overlay)],
    "runtimeWorkspaceRoots": [str(Path.cwd())],
    "reasoningEffort": "medium",
    "modelProvider": "unrelated-provider",
    "serviceTier": "unrelated-tier",
    "activePermissionProfile": {
        "id": "unrelated-profile",
        "extends": None,
    },
    "sandbox": {
        "type": "workspaceWrite",
        "writableRoots": [],
        "networkAccess": False,
        "excludeTmpdirEnvVar": True,
        "excludeSlashTmp": True,
    },
    "thread": {
        "id": "native-thread",
        "cliVersion": "9.9.9",
        "turns": [],
    },
})

servers = receive("mcpServerStatus/list")
assert servers["params"] == {
    "threadId": "native-thread",
    "cursor": None,
    "detail": "full",
}, servers
emit(servers, {
    "data": CONNECTORS,
    "nextCursor": None,
})

task = receive("turn/start")
assert task["params"] == {
    "threadId": "native-thread",
    "model": "gpt-6.1-sol",
    "effort": "medium",
    "cwd": str(Path.cwd()),
    "approvalPolicy": "on-request",
    "approvalsReviewer": "user",
    "runtimeWorkspaceRoots": [str(Path.cwd())],
    "environments": [],
    "input": [{
        "type": "text",
        "text": "Add JSON output.",
        "text_elements": [],
    }],
    "sandboxPolicy": {
        "type": "workspaceWrite",
        "writableRoots": [],
        "networkAccess": False,
        "excludeTmpdirEnvVar": True,
        "excludeSlashTmp": True,
    },
}, task
emit(task, {
    "turn": {
        "id": "native-turn",
        "items": [],
        "status": "inProgress",
    },
})

if (Path.cwd().parent / "contradictory-settings").exists():
    notify({
        "method": "thread/settings/updated",
        "params": {
            "threadId": "native-thread",
            "threadSettings": {
                "model": "gpt-6.1-sol",
                "effort": "medium",
                "cwd": str(Path.cwd().parent),
                "approvalPolicy": "on-request",
                "approvalsReviewer": "user",
                "sandboxPolicy": {
                    "type": "workspaceWrite",
                    "writableRoots": [],
                    "networkAccess": False,
                    "excludeTmpdirEnvVar": True,
                    "excludeSlashTmp": True,
                },
            },
        },
    })

sys.stderr.buffer.write(b"x" * 2097153)
sys.stderr.buffer.flush()
Path("inventory.py").write_text("DEFAULT = 'json'\n")
notify({
    "method": "item/completed",
    "params": {
        "threadId": "native-thread",
        "turnId": "native-turn",
        "item": {
            "type": "fileChange",
            "id": "native-change",
            "status": "completed",
        },
    },
})
steer = receive("turn/steer")
assert steer["params"]["threadId"] == "native-thread", steer
assert steer["params"]["expectedTurnId"] == "native-turn", steer
assert steer["params"]["input"] == [{
    "type": "text",
    "text": "Preserve the existing default.",
    "text_elements": [],
}], steer
emit(steer, {"turnId": "native-turn"})
Path("inventory.py").write_text("DEFAULT = 'text'\nJSON_FLAG = True\n")
completed = {
    "method": "turn/completed",
    "params": {
        "threadId": "native-thread",
        "turn": {
            "id": "native-turn",
            "status": "completed",
            "error": None,
        },
    },
}
tail_request = {
    "id": 99,
    "method": "item/commandExecution/requestApproval",
    "params": {
        "threadId": "native-thread",
        "turnId": "native-turn",
        "itemId": "tail",
        "reason": "tail request",
    },
}
if (Path.cwd().parent / "completion-tail-same-write").exists():
    sys.stdout.buffer.write((
        json.dumps(completed) + "\n"
        + json.dumps(tail_request) + "\n"
    ).encode())
    sys.stdout.buffer.flush()
elif (Path.cwd().parent / "completion-tail-separate-writes").exists():
    notify(completed)
    notify(tail_request)
else:
    notify(completed)
sys.stdin.buffer.read()
''')
        executable.chmod(0o755)

        environment = dict(os.environ, CODEX_HOME=str(codex_home))

        def native_cli(*args):
            return subprocess.run(
                [sys.executable, "-B", *map(str, args)],
                capture_output=True,
                timeout=30,
                env=environment,
            )

        def prepare_native(output):
            result = native_cli(
                COLLECTOR,
                "prepare",
                "--native",
                "--native-executable", executable,
                "--native-executable-sha256", sha(executable.read_bytes()),
                "--model", "gpt-6.1-sol",
                "--effort", "medium",
                "--seed-package", packet,
                "--seed-receipt-sha256",
                sha((packet / "receipt.json").read_bytes()),
                "--implementation", "inventory.py",
                "--output", output,
            )
            self.assertEqual(result.returncode, 0, result.stderr.decode())

        output = base / "native-observation"
        prepare_native(output)
        self.assertEqual((base / "native-launch-count").read_text(), "1")

        preparation_sent = [
            json.loads(line)
            for line in (
                output / "preparation/profile-discovery-sent.jsonl"
            ).read_bytes().splitlines()
        ]
        self.assertEqual(
            [message["method"] for message in preparation_sent],
            [
                "initialize",
                "initialized",
                "model/list",
                "config/read",
                "configRequirements/read",
                "skills/list",
                "mcpServerStatus/list",
            ],
        )
        self.assertFalse(any(
            message["method"] in {"thread/start", "turn/start"}
            for message in preparation_sent
        ))

        manifest_raw = (output / "manifest.json").read_bytes()
        manifest = json.loads(manifest_raw)
        profile = json.loads((output / "profile.json").read_bytes())
        self.assertEqual(manifest["schema"], "compatibility-native-observation/v1")
        baseline = json.loads((output / manifest["git_baseline"]["path"]).read_bytes())
        self.assertEqual(baseline["status"], "ready")
        self.assertIn("AGENTS.override.md", [entry["path"] for entry in baseline["source_inventory"]])
        self.assertEqual(manifest["deadline_seconds"], 3600)
        self.assertEqual(manifest["max_output_bytes"], 67108864)
        self.assertEqual(manifest["shutdown_wait_seconds"], [5, 5])
        self.assertIn("--disable", manifest["command"])
        self.assertIn("hooks", manifest["command"])
        self.assertIn("plugin_hooks", manifest["command"])
        self.assertNotIn(
            "agents.max_concurrent_threads_per_session=2",
            manifest["command"],
        )
        self.assertFalse(any(
            "synthetic_assessments" in value
            for value in manifest["command"]
        ))
        self.assertIsNone(
            profile["assessment_omission"]["runtime_assessments_absent"]
        )
        self.assertEqual(
            profile["assessment_omission"]["mechanism"],
            "bound-cooperative-instruction-overlay",
        )
        self.assertEqual(
            profile["assessment_omission"]["product_enforcement"],
            "unobserved",
        )
        self.assertEqual(
            profile["assessment_omission"]["overlay"],
            profile["instructions"][1],
        )
        self.assertEqual(
            profile["expected_instruction_sources"],
            [profile["instructions"][0]["path"],
             profile["instructions"][1]["path"]],
        )
        self.assertEqual(
            Path(profile["instructions"][1]["path"]).read_text(),
            "# Compatibility observation instruction overlay\n\n"
            "For this task, do not invoke, consult, or use `jev-axi` or any "
            "Jev assessment.\n"
            "All other standing instructions remain in effect.\n",
        )
        jev_entries = [
            entry for entry in profile["skills"]
            if entry["name"].split(":")[-1] == "jev-axi"
        ]
        self.assertTrue(jev_entries)
        self.assertTrue(any(entry["enabled"] for entry in jev_entries))
        self.assertEqual(profile["native_tasks_started"], 0)
        for name in ("loop", "adjudicate", "revise"):
            entry, = [
                item for item in profile["skills"]
                if item["name"].split(":")[-1] == name
            ]
            root = str(Path(entry["path"]).parent)
            retained = profile["resource_trees"][root]
            self.assertIn(
                str(Path(root) / "references" / "contract.md"),
                [item["path"] for item in retained],
            )

        run = (
            COLLECTOR,
            "run",
            "--manifest", output / "manifest.json",
            "--expected-sha256", sha(manifest_raw),
        )
        refused = native_cli(*run)
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn(
            b"separately accepted native invocation required",
            refused.stderr,
        )
        self.assertFalse((output / "attempt").exists())
        self.assertEqual((base / "native-launch-count").read_text(), "1")

        result = native_cli(*run, "--accept-native")
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual((base / "native-launch-count").read_text(), "2")
        attempt = output / "attempt"
        outcome_raw = (attempt / "outcome.json").read_bytes()
        outcome = json.loads(outcome_raw)
        self.assertEqual(outcome["status"], "native-observation-completed")
        self.assertTrue(outcome["amendment_rpc_accepted"])
        self.assertEqual(outcome["semantic_success"], "not-assessed")
        self.assertIsNone(
            outcome["assessment_omission"]["runtime_assessments_absent"]
        )
        self.assertEqual(outcome["permission_enforcement"], "unobserved")
        self.assertEqual(
            outcome["usage_observations"]["whole_child_usage"]["status"],
            "unknown",
        )
        self.assertEqual(
            (attempt / "collector-stderr.log").read_bytes(),
            b"x" * 2097153,
        )
        process = json.loads(
            (attempt / "collector-process.json").read_bytes()
        )
        self.assertEqual(process["retained_prefix_limit"], 67108864)
        self.assertEqual(outcome["final_source"]["status"], "complete")
        self.assertNotEqual(
            native_cli(*run, "--accept-native").returncode,
            0,
        )
        self.assertEqual(
            (attempt / "outcome.json").read_bytes(),
            outcome_raw,
        )

        for mode in (
            "completion-tail-same-write",
            "completion-tail-separate-writes",
        ):
            with self.subTest(native_completion_tail=mode):
                tail_output = base / ("native-" + mode)
                prepare_native(tail_output)
                (tail_output / mode).write_text("enabled\n")
                tail_manifest = (
                    tail_output / "manifest.json"
                ).read_bytes()
                tail_result = native_cli(
                    COLLECTOR,
                    "run",
                    "--manifest", tail_output / "manifest.json",
                    "--expected-sha256", sha(tail_manifest),
                    "--accept-native",
                )
                self.assertNotEqual(tail_result.returncode, 0)
                tail_attempt = tail_output / "attempt"
                tail_outcome = json.loads(
                    (tail_attempt / "outcome.json").read_bytes()
                )
                self.assertEqual(tail_outcome["status"], "incomplete")
                retained_request = json.loads(
                    (
                        tail_attempt / "native-unanswered-request.json"
                    ).read_bytes()
                )
                self.assertEqual(retained_request["id"], 99)
                self.assertEqual(
                    retained_request["method"],
                    "item/commandExecution/requestApproval",
                )
                tail_rows = [
                    json.loads(line)
                    for line in (
                        tail_attempt / "receipts.jsonl"
                    ).read_bytes().splitlines()
                ]
                received = [
                    row["message"]
                    for row in tail_rows
                    if row["kind"] == "received"
                ]
                self.assertEqual(
                    received[-2]["method"],
                    "turn/completed",
                )
                self.assertEqual(received[-1], retained_request)

        settings_output = base / "native-contradictory-settings"
        prepare_native(settings_output)
        (
            settings_output / "contradictory-settings"
        ).write_text("enabled\n")
        settings_manifest = (
            settings_output / "manifest.json"
        ).read_bytes()
        settings_result = native_cli(
            COLLECTOR,
            "run",
            "--manifest", settings_output / "manifest.json",
            "--expected-sha256", sha(settings_manifest),
            "--accept-native",
        )
        self.assertNotEqual(settings_result.returncode, 0)
        settings_outcome = json.loads(
            (
                settings_output / "attempt" / "outcome.json"
            ).read_bytes()
        )
        self.assertEqual(settings_outcome["status"], "incomplete")
        self.assertIn(
            "native turn settings differ",
            settings_outcome["error"],
        )

        drift_output = base / "native-drift-observation"
        prepare_native(drift_output)
        launches_before_drift = (
            base / "native-launch-count"
        ).read_text()
        instruction.write_text("# Drifted native instructions\n")
        drift_manifest = (drift_output / "manifest.json").read_bytes()
        drift = native_cli(
            COLLECTOR,
            "run",
            "--manifest", drift_output / "manifest.json",
            "--expected-sha256", sha(drift_manifest),
            "--accept-native",
        )
        self.assertNotEqual(drift.returncode, 0)
        self.assertEqual(
            (base / "native-launch-count").read_text(),
            launches_before_drift,
        )
        drift_attempt = drift_output / "attempt"
        self.assertTrue((drift_attempt / "outcome.json").is_file())
        self.assertFalse(
            (drift_attempt / "collector-process.json").exists()
        )
        self.assertFalse(
            (drift_attempt / "collector-sent.jsonl").exists()
        )

        instruction.write_text("# Synthetic native instructions\n")
        overlay_output = base / "native-overlay-drift-observation"
        prepare_native(overlay_output)
        launches_before_overlay_drift = (
            base / "native-launch-count"
        ).read_text()
        overlay = overlay_output / "project" / "AGENTS.override.md"
        overlay.write_text("# Removed omission instruction\n")
        overlay_manifest = (
            overlay_output / "manifest.json"
        ).read_bytes()
        overlay_drift = native_cli(
            COLLECTOR,
            "run",
            "--manifest", overlay_output / "manifest.json",
            "--expected-sha256", sha(overlay_manifest),
            "--accept-native",
        )
        self.assertNotEqual(overlay_drift.returncode, 0)
        self.assertEqual(
            (base / "native-launch-count").read_text(),
            launches_before_overlay_drift,
        )
        overlay_attempt = overlay_output / "attempt"
        overlay_outcome = json.loads(
            (overlay_attempt / "outcome.json").read_bytes()
        )
        self.assertIn(
            "baseline Git state changed before task delivery",
            overlay_outcome["error"],
        )
        self.assertEqual(overlay_outcome["status"], "incomplete")
        overlay_preflight = json.loads(
            (overlay_attempt / "baseline-preflight" / "preflight.json").read_bytes()
        )
        self.assertEqual(overlay_preflight["status"], "incomplete")
        self.assertFalse(
            (overlay_attempt / "collector-process.json").exists()
        )
        self.assertFalse(
            (overlay_attempt / "collector-sent.jsonl").exists()
        )

        for name in ("loop", "adjudicate", "revise"):
            with self.subTest(resource_drift=name):
                resource_output = (
                    base / f"native-{name}-resource-drift-observation"
                )
                prepare_native(resource_output)
                launches_before_resource_drift = (
                    base / "native-launch-count"
                ).read_text()
                reference = (
                    codex_home / "skills" / name
                    / "references" / "contract.md"
                )
                original = reference.read_text()
                reference.write_text(original + "# Drift\n")
                resource_manifest = (
                    resource_output / "manifest.json"
                ).read_bytes()
                resource_drift = native_cli(
                    COLLECTOR,
                    "run",
                    "--manifest", resource_output / "manifest.json",
                    "--expected-sha256", sha(resource_manifest),
                    "--accept-native",
                )
                self.assertNotEqual(resource_drift.returncode, 0)
                self.assertEqual(
                    (base / "native-launch-count").read_text(),
                    launches_before_resource_drift,
                )
                resource_attempt = resource_output / "attempt"
                resource_outcome = json.loads(
                    (resource_attempt / "outcome.json").read_bytes()
                )
                self.assertIn(
                    "authoring resource tree differs",
                    resource_outcome["error"],
                )
                self.assertFalse(
                    (resource_attempt / "collector-sent.jsonl").exists()
                )
                reference.write_text(original)

    def prepare_usage_fixture(self, notifications, reject=False):
        tail = "for message in " + repr(notifications) + ":\n    emit(message)\n"
        tail += '''
Path("inventory.py").write_text("DEFAULT = 'json'\\n")
emit({"method": "item/completed", "params": {"threadId": "thread-1", "turnId": "turn-1",
    "item": {"type": "commandExecution", "id": "change", "status": "completed"}}})
steer = receive()
'''
        tail += ('''emit({"id": steer["id"], "error": {"code": -32000, "message": "rejected"}})
''' if reject else '''emit({"id": steer["id"], "result": {"turnId": "turn-1"}})
emit({"method": "turn/completed", "params": {"threadId": "thread-1",
    "turn": {"id": "turn-1", "status": "completed", "error": None}}})
''')
        return self.prepare_failure_fixture(tail + "sys.stdin.buffer.read()\n")

    def test_usage_index_preserves_snapshots_without_combining_threads_or_totals(self):
        breakdown = {"cachedInputTokens": 20, "inputTokens": 100, "outputTokens": 10,
                     "reasoningOutputTokens": 4, "totalTokens": 110}
        first = {"method": "thread/tokenUsage/updated", "params": {
            "threadId": "thread-1", "turnId": "turn-1",
            "tokenUsage": {"last": breakdown, "total": breakdown}}}
        later = json.loads(json.dumps(first))
        later["params"]["tokenUsage"]["total"] = {
            "cachedInputTokens": 25, "inputTokens": 130, "outputTokens": 15,
            "reasoningOutputTokens": 6, "totalTokens": 145}
        other_thread = json.loads(json.dumps(first))
        other_thread["params"]["threadId"] = "unattributed-thread"
        other_turn = json.loads(json.dumps(first))
        other_turn["params"]["turnId"] = "another-turn"
        messages = [first, first, later, first, other_thread, other_turn]
        cli, run, output = self.prepare_usage_fixture(messages)
        result = cli(*run)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        attempt = output / "attempt"
        outcome = json.loads((attempt / "outcome.json").read_bytes())
        rows = [json.loads(line) for line in (attempt / "receipts.jsonl").read_bytes().splitlines()]
        usage_rows = [row for row in rows if row.get("message", {}).get("method") ==
                      "thread/tokenUsage/updated"]
        self.assertEqual([row["message"] for row in usage_rows], messages)
        index = outcome["usage_observations"]
        self.assertEqual(index["root_event_sequences"], [row["sequence"] for row in usage_rows[:4]])
        self.assertEqual(index["other_event_sequences"], [row["sequence"] for row in usage_rows[4:]])
        self.assertEqual(index["invalid_event_sequences"], [])
        self.assertIsNone(index["whole_episode_tokens"])
        completion, = [row for row in rows if row.get("message", {}).get("method") == "turn/completed"]
        self.assertEqual(index["collection_end"], {
            "reason": "root-turn-completed", "event_sequence": completion["sequence"]})
        inbound = (attempt / "collector-stdout.log").read_bytes()
        for row in usage_rows:
            ref = row["wire"]
            raw = inbound[ref["offset"]:ref["offset"] + ref["bytes"]]
            self.assertEqual(sha(raw), ref["sha256"])
            self.assertEqual(json.loads(raw), row["message"])

    def test_usage_index_marks_missing_counters_without_filling_optional_values(self):
        counts = {"cachedInputTokens": 0, "inputTokens": 12, "outputTokens": 3,
                  "reasoningOutputTokens": 1, "totalTokens": 15}
        valid = {"method": "thread/tokenUsage/updated", "params": {
            "threadId": "thread-1", "turnId": "turn-1",
            "tokenUsage": {"last": counts, "total": counts}}}
        missing = json.loads(json.dumps(valid))
        del missing["params"]["tokenUsage"]["total"]["outputTokens"]
        boolean = json.loads(json.dumps(valid))
        boolean["params"]["tokenUsage"]["last"]["inputTokens"] = True
        malformed = {"method": "thread/tokenUsage/updated", "params": None}
        explicit = json.loads(json.dumps(valid))
        explicit["params"]["tokenUsage"]["modelContextWindow"] = None
        explicit["params"]["tokenUsage"]["total"]["cacheWriteInputTokens"] = 0
        messages = [missing, boolean, malformed, valid, explicit]
        cli, run, output = self.prepare_usage_fixture(messages)
        result = cli(*run)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        attempt = output / "attempt"
        outcome = json.loads((attempt / "outcome.json").read_bytes())
        rows = [json.loads(line) for line in (attempt / "receipts.jsonl").read_bytes().splitlines()]
        usage_rows = [row for row in rows if row.get("message", {}).get("method") ==
                      "thread/tokenUsage/updated"]
        self.assertEqual([row["message"] for row in usage_rows], messages)
        index = outcome["usage_observations"]
        self.assertEqual(index["root_event_sequences"], [row["sequence"] for row in usage_rows[3:]])
        self.assertEqual(index["invalid_event_sequences"], [row["sequence"] for row in usage_rows[:3]])
        self.assertEqual(index["other_event_sequences"], [])
        self.assertIsNone(index["whole_episode_tokens"])
        self.assertEqual(outcome["status"], "fake-observation-completed")

    def test_usage_absence_and_failed_attempt_remain_unknown_and_preserved(self):
        counts = {"cachedInputTokens": 0, "inputTokens": 12, "outputTokens": 3,
                  "reasoningOutputTokens": 1, "totalTokens": 15}
        message = {"method": "thread/tokenUsage/updated", "params": {
            "threadId": "thread-1", "turnId": "turn-1",
            "tokenUsage": {"last": counts, "total": counts}}}
        for messages, reject in (([], False), ([message], True)):
            with self.subTest(reject=reject):
                cli, run, output = self.prepare_usage_fixture(messages, reject=reject)
                result = cli(*run)
                self.assertEqual(result.returncode, 1 if reject else 0, result.stderr.decode())
                attempt = output / "attempt"
                before = {p.name: p.read_bytes() for p in attempt.iterdir() if p.is_file()}
                outcome = json.loads(before["outcome.json"])
                index = outcome["usage_observations"]
                self.assertIsNone(index["whole_episode_tokens"])
                self.assertEqual(index["other_event_sequences"], [])
                self.assertEqual(index["invalid_event_sequences"], [])
                rows = [json.loads(line) for line in before["receipts.jsonl"].splitlines()]
                received = [row for row in rows if row["kind"] == "received"]
                if reject:
                    usage, = [row for row in received if row["message"].get("method") ==
                              "thread/tokenUsage/updated"]
                    self.assertEqual(index["root_event_sequences"], [usage["sequence"]])
                    self.assertEqual(outcome["status"], "incomplete")
                else:
                    self.assertEqual(index["root_event_sequences"], [])
                self.assertEqual(index["collection_end"], {
                    "reason": "incomplete" if reject else "root-turn-completed",
                    "event_sequence": received[-1]["sequence"]})
                self.assertNotEqual(cli(*run).returncode, 0)
                self.assertEqual({p.name: p.read_bytes() for p in attempt.iterdir() if p.is_file()}, before)

    def test_tool_inventory_distinguishes_tested_files_from_later_documentation_edit(self):
        cli, run, output = self.prepare_failure_fixture(r'''
import time

def completed(ident, command, output):
    emit({"method": "item/completed", "params": {
        "threadId": "thread-1", "turnId": "turn-1",
        "item": {"type": "commandExecution", "id": ident,
                 "status": "completed", "command": command,
                 "aggregatedOutput": output, "exitCode": 0}}})
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        rows = [json.loads(line) for line in
                Path("../attempt/receipts.jsonl").read_text().splitlines()]
        if any(row["kind"] == "tool-completed" and row["item"]["id"] == ident
               for row in rows):
            return
        time.sleep(0.005)
    raise RuntimeError("collector did not record the tool boundary")

completed("tests", "python -m unittest", "Ran 3 tests\nOK\n")
Path("README.md").write_bytes(b"Updated usage\n")
Path("inventory.py").write_bytes(b"DEFAULT = 'json'\n")
completed("edit", "update files", "")
steer = receive()
emit({"id": steer["id"], "result": {"turnId": "turn-1"}})
emit({"method": "turn/completed", "params": {"threadId": "thread-1",
    "turn": {"id": "turn-1", "status": "completed", "error": None}}})
sys.stdin.buffer.read()
''', extra_seed_files={"README.md": b"Original usage\n"})
        result = cli(*run)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        attempt = output / "attempt"
        rows = [json.loads(line) for line in
                (attempt / "receipts.jsonl").read_bytes().splitlines()]
        tests, = [row for row in rows if row["kind"] == "tool-completed"
                  and row["item"]["id"] == "tests"]
        self.assertIn("source_inventory", tests)
        inventory = tests["source_inventory"]
        self.assertEqual(inventory["status"], "complete")
        files = {entry["path"]: entry for entry in inventory["files"]}
        self.assertEqual(files["README.md"]["sha256"], sha(b"Original usage\n"))
        self.assertEqual(files["inventory.py"]["sha256"], sha(b"DEFAULT = 'text'\n"))
        self.assertEqual(tests["item"]["aggregatedOutput"], "Ran 3 tests\nOK\n")
        original = next(row for row in rows if row["sequence"] == tests["event_sequence"])
        self.assertEqual(original["message"]["params"]["item"], tests["item"])
        final = json.loads((attempt / "final-source.json").read_bytes())
        self.assertNotEqual(inventory["identity"], final["identity"])
        self.assertGreaterEqual(inventory["elapsed_seconds"], 0)
        self.assertIn("started_at", inventory)
        self.assertIn("finished_at", inventory)

    def test_started_and_completed_inventories_match_a_later_test_to_final_files(self):
        variants = {
            "added": 'Path("new_module.py").write_bytes(b"NEW = True\\n")',
            "removed": 'Path("helper.py").unlink()',
            "mode": 'Path("helper.py").chmod(0o755)',
            "undeclared": 'Path("helper.py").write_bytes(b"VALUE = 2\\n")',
            "documentation": 'Path("README.md").write_bytes(b"Updated\\n")',
        }
        for name, mutation in variants.items():
            with self.subTest(change=name):
                cli, run, output = self.prepare_failure_fixture(r'''
import time

def boundary(method, ident):
    emit({"method": method, "params": {"threadId": "thread-1", "turnId": "turn-1",
        "item": {"type": "commandExecution", "id": ident,
                 "command": "python -m unittest", "status": "completed",
                 "exitCode": 0, "aggregatedOutput": "Ran 3 tests\nOK\n"}}})
    deadline = time.monotonic() + 0.5
    while time.monotonic() < deadline:
        rows = [json.loads(line) for line in
                Path("../attempt/receipts.jsonl").read_text().splitlines()]
        if any(row["kind"] == "tool-" + method.split("/")[1]
               and row["item"]["id"] == ident for row in rows):
            return
        time.sleep(0.005)

boundary("item/started", "old-tests")
boundary("item/completed", "old-tests")
MUTATION
Path("inventory.py").write_bytes(b"DEFAULT = 'json'\n")
boundary("item/completed", "edit")
steer = receive()
emit({"id": steer["id"], "result": {"turnId": "turn-1"}})
boundary("item/started", "final-tests")
boundary("item/completed", "final-tests")
emit({"method": "turn/completed", "params": {"threadId": "thread-1",
    "turn": {"id": "turn-1", "status": "completed", "error": None}}})
sys.stdin.buffer.read()
        '''.replace('MUTATION', mutation),
                    extra_seed_files={'helper.py': b'VALUE = 1\n', 'README.md': b'Original\n'})
                result = cli(*run)
                self.assertEqual(result.returncode, 0, result.stderr.decode())
                attempt = output / "attempt"
                rows = [json.loads(line) for line in
                        (attempt / "receipts.jsonl").read_bytes().splitlines()]
                boundaries = {(row["kind"], row["item"]["id"]): row for row in rows
                              if row["kind"] in ("tool-started", "tool-completed")}
                self.assertIn(("tool-started", "final-tests"), boundaries)
                final = json.loads((attempt / "final-source.json").read_bytes())
                for kind in ("tool-started", "tool-completed"):
                    inventory = boundaries[kind, "final-tests"]["source_inventory"]
                    self.assertEqual(inventory["status"], "complete")
                    self.assertEqual(inventory["identity"], final["identity"])
                    self.assertNotEqual(boundaries[kind, "old-tests"]["source_inventory"]["identity"],
                                        final["identity"])

    def test_final_source_capture_retains_post_amendment_refactor(self):
        trigger_bytes = b"DEFAULT = 'json'\n"
        final_bytes = b"from lib.replacement import DEFAULT\n"
        replacement_bytes = b"DEFAULT = 'text'\nJSON_FLAG = True\n"
        readme_bytes = b"# Disposable inventory project\n"
        cli, run, output = self.prepare_failure_fixture(r'''
Path("inventory.py").write_bytes(b"DEFAULT = 'json'\n")
emit({"method": "item/completed", "params": {"threadId": "thread-1", "turnId": "turn-1",
    "item": {"type": "commandExecution", "id": "trigger", "status": "completed"}}})
steer = receive()
assert steer["method"] == "turn/steer", steer
assert steer["params"]["expectedTurnId"] == "turn-1", steer
emit({"id": steer["id"], "result": {"turnId": "turn-1"}})
Path("inventory.py").write_bytes(b"from lib.replacement import DEFAULT\n")
Path("inventory.py").chmod(0o644)
Path("lib").mkdir()
Path("lib/replacement.py").write_bytes(b"DEFAULT = 'text'\nJSON_FLAG = True\n")
Path("lib/replacement.py").chmod(0o755)
Path("old_formatter.py").unlink()
for directory in (".git", "__pycache__", "lib/__pycache__"):
    Path(directory).mkdir(parents=True, exist_ok=True)
    Path(directory, "excluded").write_bytes(b"not candidate source\n")
Path("loose.pyc").write_bytes(b"compiled cache\n")
Path("lib/loose.pyo").write_bytes(b"compiled cache\n")
emit({"method": "turn/completed", "params": {"threadId": "thread-1",
    "turn": {"id": "turn-1", "status": "completed", "error": None}}})
sys.stdin.buffer.read()
''', seed_mode=0o755, extra_seed_files={"old_formatter.py": b"DEFAULT = 'text'\n",
                      "README.md": readme_bytes})
        manifest = json.loads((output / "manifest.json").read_bytes())
        self.assertEqual(manifest["implementation_paths"], ["inventory.py"])
        self.assertIn("old_formatter.py", manifest["initial_files"])
        result = cli(*run)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        attempt = output / "attempt"
        outcome = json.loads((attempt / "outcome.json").read_bytes())
        self.assertEqual(outcome["status"], "fake-observation-completed")
        self.assertTrue(outcome["amendment_rpc_accepted"])
        self.assertEqual(outcome["semantic_success"], "not-assessed")
        rows = [json.loads(line) for line in
                (attempt / "receipts.jsonl").read_bytes().splitlines()]
        trigger = next(row for row in rows
                       if row["sequence"] == outcome["trigger_observation_sequence"])
        self.assertEqual(trigger["changed"], {"inventory.py": {
            "before": manifest["initial_files"]["inventory.py"], "after": sha(trigger_bytes)}})
        completed, = [row for row in rows if row.get("message", {}).get("method") ==
                      "turn/completed"]
        boundary = {"reason": "root-turn-completed", "event_sequence": completed["sequence"]}
        self.assertEqual(outcome["usage_observations"]["collection_end"], boundary)

        # This inventory and retained tree are a proposed public evidence contract.
        self.assertIn("final_source", outcome, "the attempt must retain its final candidate")
        reference = outcome["final_source"]
        self.assertEqual(reference["status"], "complete")
        self.assertEqual(reference["inventory"], "final-source.json")
        inventory_raw = (attempt / reference["inventory"]).read_bytes()
        self.assertEqual(reference["sha256"], sha(inventory_raw))
        inventory = json.loads(inventory_raw)
        self.assertEqual(inventory["schema"], "compatibility-final-source/v1")
        self.assertEqual((inventory["thread_id"], inventory["turn_id"]),
                         (outcome["thread_id"], outcome["turn_id"]))
        self.assertEqual(inventory["collection_end"], boundary)
        self.assertEqual(inventory["excluded"], [".git", "__pycache__", "*.pyc", "*.pyo"])
        self.assertEqual(inventory["source_directory"], "final-source")
        expected = {"README.md": (readme_bytes, 0o644),
                    "inventory.py": (final_bytes, 0o644),
                    "lib/replacement.py": (replacement_bytes, 0o755)}
        files = [{"path": name, "sha256": sha(raw), "bytes": len(raw),
                  "mode": mode, "executable": bool(mode & 0o111)}
                 for name, (raw, mode) in sorted(expected.items())]
        self.assertEqual(inventory["files"], files)
        self.assertEqual(inventory["identity"], sha(encoded(files)))
        snapshot = attempt / inventory["source_directory"]
        self.assertEqual(sorted(path.relative_to(snapshot).as_posix()
                                for path in snapshot.rglob("*") if path.is_file()),
                         sorted(expected))
        self.assertFalse((snapshot / "old_formatter.py").exists())
        self.assertNotEqual(sha(final_bytes), trigger["changed"]["inventory.py"]["after"])
        # The disposable project may change after collection; evidence must retain its bytes.
        (output / "project/inventory.py").write_bytes(b"# later workspace change\n")
        (output / "project/lib/replacement.py").unlink()
        for name, (raw, mode) in expected.items():
            retained = snapshot / name
            self.assertEqual(retained.read_bytes(), raw)
            self.assertEqual(retained.stat().st_mode & 0o7777, mode)
        self.assertEqual((attempt / reference["inventory"]).read_bytes(), inventory_raw)

    @unittest.skipUnless(os.name == "posix", "POSIX byte filenames")
    def test_unencodable_source_name_preserves_collection_outcome(self):
        cli, run, output = self.prepare_failure_fixture(r'''
Path("inventory.py").write_bytes(b"DEFAULT = 'json'\n")
emit({"method": "item/completed", "params": {"threadId": "thread-1", "turnId": "turn-1",
    "item": {"type": "commandExecution", "id": "change", "status": "completed"}}})
steer = receive()
assert steer["method"] == "turn/steer", steer
emit({"id": steer["id"], "result": {"turnId": "turn-1"}})
with open(b"bad-\xff.txt", "wb") as stream:
    stream.write(b"ordinary fixture output\n")
emit({"method": "turn/completed", "params": {"threadId": "thread-1",
    "turn": {"id": "turn-1", "status": "completed", "error": None}}})
sys.stdin.buffer.read()
''')
        result = cli(*run)
        attempt = output / "attempt"
        outcome_path = attempt / "outcome.json"
        self.assertTrue(outcome_path.is_file(), result.stderr.decode())
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        outcome = json.loads(outcome_path.read_bytes())
        self.assertEqual(outcome["status"], "fake-observation-completed")
        self.assertTrue(outcome["amendment_rpc_accepted"])
        self.assertEqual((outcome["thread_id"], outcome["turn_id"]), ("thread-1", "turn-1"))
        self.assertEqual(outcome["semantic_success"], "not-assessed")
        rows = [json.loads(line) for line in (attempt / "receipts.jsonl").read_bytes().splitlines()]
        completed, = [row for row in rows if row.get("message", {}).get("method") == "turn/completed"]
        self.assertEqual(outcome["usage_observations"]["collection_end"],
                         {"reason": "root-turn-completed", "event_sequence": completed["sequence"]})
        self.assertEqual(outcome["final_source"]["status"], "incomplete")

    def prepare_failure_fixture(self, tail, seed_mode=0o644, mark_launch=False,
                                extra_seed_files=None, git_evidence=False, thread_setup=""):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name)
        seed = base / "seed"
        seed.mkdir()
        initial = {"inventory.py": b"DEFAULT = 'text'\n", **(extra_seed_files or {})}
        for name, raw in initial.items():
            path = seed / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            path.chmod(seed_mode if name == "inventory.py" else 0o644)
        entries = [{"path": name, "sha256": sha(raw),
                    "executable": bool(seed_mode & 0o111) if name == "inventory.py" else False}
                   for name, raw in sorted(initial.items())]
        requests = []
        for index, text in enumerate([b"Add JSON output.", b"Preserve the existing default."]):
            (base / str(index)).write_bytes(text)
            requests.append({"path": str(index), "sha256": sha(text)})
        spec = {"version": 1, "seed": {"path": "seed", "files": entries,
                "identity": sha(encoded(entries))}, "requests": requests,
                "observation_cases": [], "constructed_candidates": []}
        (base / "spec.json").write_bytes(encoded(spec))
        packet, output = base / "packet", base / "observation"
        def cli(*args):
            return subprocess.run([sys.executable, "-B", *map(str, args)],
                                  capture_output=True, timeout=15)
        prepared = cli(HERE / "prepare_seed.py", "--spec", base / "spec.json", "--output", packet)
        self.assertEqual(prepared.returncode, 0, prepared.stderr.decode())
        fixture = base / "fake.py"
        launch_marker = ("from pathlib import Path\n"
                         "Path(__file__).with_name('fake-launched').write_text('launched')\n"
                         if mark_launch else "")
        fixture.write_text(launch_marker + """import json
from pathlib import Path
import sys

EMITTED_BYTES = 0

def receive():
    return json.loads(sys.stdin.buffer.readline())

def emit(value):
    global EMITTED_BYTES
    raw = (json.dumps(value) + "\\n").encode()
    sys.stdout.buffer.write(raw)
    sys.stdout.buffer.flush()
    EMITTED_BYTES += len(raw)

first = receive()
emit({"id": first["id"], "result": {}})
receive()
thread = receive()
""" + thread_setup + """
emit({"id": thread["id"], "result": {"thread": {"id": "thread-1"}}})
task = receive()
emit({"id": task["id"], "result": {"turn": {"id": "turn-1"}}})
""" + tail)
        profile = {"kind": "cooperative-python-fake/v1",
                   "command": [sys.executable, "-I", "-S", "-u", str(fixture)],
                   "python_sha256": sha(Path(sys.executable).read_bytes()),
                   "fixture_sha256": sha(fixture.read_bytes())}
        profile_path = base / "profile.json"
        profile_path.write_bytes(encoded(profile))
        prepared = cli(COLLECTOR, "prepare", "--seed-package", packet,
                       "--seed-receipt-sha256", sha((packet / "receipt.json").read_bytes()),
                       "--profile", profile_path, "--profile-sha256", sha(profile_path.read_bytes()),
                       "--implementation", "inventory.py", "--output", output,
                       *(["--git-evidence"] if git_evidence else []))
        self.assertEqual(prepared.returncode, 0, prepared.stderr.decode())
        run = (COLLECTOR, "run", "--manifest", output / "manifest.json",
               "--expected-sha256", sha((output / "manifest.json").read_bytes()))
        return cli, run, output

    def test_seed_mode_drift_is_rejected_before_launch_and_preserves_attempt(self):
        for original, changed in ((0o755, 0o644), (0o755, 0o744), (0o644, 0o755)):
            with self.subTest(original=oct(original), changed=oct(changed)):
                cli, run, output = self.prepare_failure_fixture(
                    "raise AssertionError('must not launch')\n",
                    seed_mode=original, mark_launch=True)
                project_file = output / "project" / "inventory.py"
                initial = project_file.read_bytes()
                self.assertEqual(project_file.stat().st_mode & 0o7777, original)
                project_file.chmod(changed)
                self.assertEqual(project_file.read_bytes(), initial)
                self.assertNotEqual(cli(*run).returncode, 0)
                attempt = output / "attempt"
                outcome_raw = (attempt / "outcome.json").read_bytes()
                outcome = json.loads(outcome_raw)
                self.assertEqual(outcome["status"], "incomplete")
                self.assertIn("seed file mode differs", outcome["error"])
                self.assertIn("inventory.py", outcome["error"])
                self.assertIsNone(outcome["thread_id"])
                self.assertIsNone(outcome["turn_id"])
                self.assertFalse(outcome["amendment_rpc_accepted"])
                self.assertFalse((output / "fake-launched").exists())
                self.assertFalse((attempt / "collector-process.json").exists())
                self.assertFalse((attempt / "collector-sent.jsonl").exists())
                self.assertFalse((attempt / "collector-stdout.log").exists())
                self.assertNotEqual(cli(*run).returncode, 0)
                self.assertEqual((attempt / "outcome.json").read_bytes(), outcome_raw)
                self.assertEqual(project_file.read_bytes(), initial)
                self.assertEqual(project_file.stat().st_mode & 0o7777, changed)

    def test_completed_turn_race_preserves_attempt_without_resending_amendment(self):
        cli, run, output = self.prepare_failure_fixture("""
Path("inventory.py").write_text("DEFAULT = 'json'\\n")
changed = {"method": "item/completed", "params": {"threadId": "thread-1", "turnId": "turn-1",
    "item": {"type": "commandExecution", "id": "change", "status": "completed"}}}
completed = {"method": "turn/completed", "params": {"threadId": "thread-1",
    "turn": {"id": "turn-1", "status": "completed", "error": None}}}
sys.stdout.buffer.write((json.dumps(changed) + "\\n" + json.dumps(completed) + "\\n").encode())
sys.stdout.buffer.flush()
sys.stdin.buffer.read()
""")
        result = cli(*run)
        self.assertNotEqual(result.returncode, 0)
        attempt = output / "attempt"
        outcome_raw = (attempt / "outcome.json").read_bytes()
        outcome = json.loads(outcome_raw)
        self.assertEqual(outcome["status"], "incomplete")
        self.assertFalse(outcome["amendment_rpc_accepted"])
        self.assertEqual(outcome["semantic_success"], "not-assessed")
        self.assertIn("turn ended without an accepted amendment", outcome["error"])
        sent_raw = (attempt / "collector-sent.jsonl").read_bytes()
        sent = [json.loads(line) for line in sent_raw.splitlines()]
        self.assertEqual([item["method"] for item in sent].count("turn/start"), 1)
        self.assertEqual([item["method"] for item in sent].count("turn/steer"), 1)
        received = [json.loads(line) for line in (attempt / "collector-stdout.log").read_bytes().splitlines()]
        self.assertEqual(received[-1]["method"], "turn/completed")
        self.assertNotEqual(cli(*run).returncode, 0)
        self.assertEqual((attempt / "outcome.json").read_bytes(), outcome_raw)
        self.assertEqual((attempt / "collector-sent.jsonl").read_bytes(), sent_raw)

    def test_complete_tail_requests_after_completion_remain_unanswered(self):
        for same_write in (True, False):
            with self.subTest(same_write=same_write):
                emission = (
                    "sys.stdout.buffer.write((json.dumps(completed) + "
                    "'\\n' + json.dumps(request) + '\\n').encode())\n"
                    if same_write
                    else
                    "sys.stdout.buffer.write((json.dumps(completed) + "
                    "'\\n').encode())\n"
                    "sys.stdout.buffer.flush()\n"
                    "sys.stdout.buffer.write((json.dumps(request) + "
                    "'\\n').encode())\n"
                )
                cli, run, output = self.prepare_failure_fixture(
                    """
Path("inventory.py").write_text("DEFAULT = 'json'\\n")
emit({"method": "item/completed", "params": {
    "threadId": "thread-1", "turnId": "turn-1",
    "item": {"type": "commandExecution", "id": "change",
             "status": "completed"}}})
steer = receive()
emit({"id": steer["id"], "result": {"turnId": "turn-1"}})
completed = {"method": "turn/completed", "params": {
    "threadId": "thread-1",
    "turn": {"id": "turn-1", "status": "completed", "error": None}}}
request = {"id": 99, "method": "item/commandExecution/requestApproval",
    "params": {"threadId": "thread-1", "turnId": "turn-1",
               "itemId": "tail", "reason": "tail request"}}
"""
                    + emission
                    + """
sys.stdout.buffer.flush()
sys.stdin.buffer.read()
"""
                )
                result = cli(*run)
                self.assertNotEqual(result.returncode, 0)
                attempt = output / "attempt"
                outcome = json.loads(
                    (attempt / "outcome.json").read_bytes()
                )
                self.assertEqual(outcome["status"], "incomplete")
                self.assertIn("remains unanswered", outcome["error"])
                rows = [
                    json.loads(line)
                    for line in (
                        attempt / "receipts.jsonl"
                    ).read_bytes().splitlines()
                ]
                received = [
                    row for row in rows if row["kind"] == "received"
                ]
                self.assertEqual(
                    received[-2]["message"]["method"],
                    "turn/completed",
                )
                self.assertEqual(received[-1]["message"]["id"], 99)
                self.assertEqual(received[-1]["message"]["method"],
                                 "item/commandExecution/requestApproval")
                sent = [
                    json.loads(line)
                    for line in (
                        attempt / "collector-sent.jsonl"
                    ).read_bytes().splitlines()
                ]
                self.assertFalse(
                    any(message.get("id") == 99 for message in sent)
                )
                self.assertEqual(
                    (attempt / "collector-undelivered-stdout.log")
                    .read_bytes(),
                    b"",
                )

    def test_shutdown_never_parses_stdout_beyond_retained_prefix(self):
        cli, _, output = self.prepare_failure_fixture(r'''
import os
import signal

Path("inventory.py").write_text("DEFAULT = 'json'\n")
emit({"method": "item/completed", "params": {
    "threadId": "thread-1", "turnId": "turn-1",
    "item": {"type": "commandExecution", "id": "change",
             "status": "completed"}}})
steer = receive()
emit({"id": steer["id"], "result": {"turnId": "turn-1"}})

limit = 4096
completed = {"method": "turn/completed", "params": {
    "threadId": "thread-1",
    "turn": {"id": "turn-1", "status": "completed", "error": None}}}
request = {"id": 99, "method": "item/commandExecution/requestApproval",
    "params": {"threadId": "thread-1", "turnId": "turn-1",
               "itemId": "unretained", "reason": "unretained request"}}

def terminate(signum, frame):
    remaining = limit - EMITTED_BYTES
    empty = {"method": "padding", "params": {"value": ""}}
    overhead = len((json.dumps(empty) + "\n").encode())
    assert remaining >= overhead, (remaining, overhead)
    padding = {"method": "padding", "params": {
        "value": "x" * (remaining - overhead)}}
    padding_raw = (json.dumps(padding) + "\n").encode()
    request_raw = (json.dumps(request) + "\n").encode()
    assert len(padding_raw) == remaining
    os.write(sys.stdout.fileno(), padding_raw + request_raw)
    os._exit(0)

signal.signal(signal.SIGTERM, terminate)
emit(completed)
signal.pause()
''')
        manifest_path = output / "manifest.json"
        manifest = json.loads(manifest_path.read_bytes())
        manifest["max_output_bytes"] = 4096
        manifest_raw = encoded(manifest) + b"\n"
        manifest_path.write_bytes(manifest_raw)
        run = (
            COLLECTOR,
            "run",
            "--manifest", manifest_path,
            "--expected-sha256", sha(manifest_raw),
        )

        result = cli(*run)
        self.assertNotEqual(result.returncode, 0)
        attempt = output / "attempt"
        outcome = json.loads(
            (attempt / "outcome.json").read_bytes()
        )
        self.assertIn("output bound exceeded", outcome["error"])
        rows = [
            json.loads(line)
            for line in (
                attempt / "receipts.jsonl"
            ).read_bytes().splitlines()
        ]
        received = [
            row["message"]
            for row in rows
            if row["kind"] == "received"
        ]
        self.assertEqual(received[-2]["method"], "turn/completed")
        self.assertEqual(received[-1]["method"], "padding")
        self.assertFalse(any(
            message.get("id") == 99
            for message in received
        ))
        retained = (
            attempt / "collector-stdout.log"
        ).read_bytes()
        self.assertEqual(len(retained), 4096)
        self.assertNotIn(
            b"item/commandExecution/requestApproval",
            retained,
        )
        process = json.loads(
            (attempt / "collector-process.json").read_bytes()
        )
        self.assertGreater(process["received_bytes"], 4096)
        self.assertEqual(process["retained_prefix_limit"], 4096)

    def test_rejected_steering_retains_error_and_does_not_start_another_turn(self):
        cli, run, output = self.prepare_failure_fixture("""
Path("inventory.py").write_text("DEFAULT = 'json'\\n")
emit({"method": "item/completed", "params": {"threadId": "thread-1", "turnId": "turn-1",
    "item": {"type": "commandExecution", "id": "change", "status": "completed"}}})
steer = receive()
emit({"id": steer["id"], "error": {"code": -32000, "message": "turn is no longer active"}})
sys.stdin.buffer.read()
""")
        self.assertNotEqual(cli(*run).returncode, 0)
        attempt = output / "attempt"
        outcome = json.loads((attempt / "outcome.json").read_bytes())
        self.assertEqual(outcome["status"], "incomplete")
        self.assertFalse(outcome["amendment_rpc_accepted"])
        sent = [json.loads(line) for line in (attempt / "collector-sent.jsonl").read_bytes().splitlines()]
        self.assertEqual([item["method"] for item in sent],
                         ["initialize", "initialized", "thread/start", "turn/start", "turn/steer"])
        received = [json.loads(line) for line in (attempt / "collector-stdout.log").read_bytes().splitlines()]
        self.assertEqual(received[-1], {"id": 4, "error": {
            "code": -32000, "message": "turn is no longer active"}})
        rows = [json.loads(line) for line in (attempt / "receipts.jsonl").read_bytes().splitlines()]
        self.assertEqual(rows[-1]["message"], received[-1])
        self.assertFalse(any(row["kind"] == "amendment-rpc-accepted" for row in rows))

    def test_permission_request_remains_unanswered_and_retained(self):
        cli, run, output = self.prepare_failure_fixture("""
emit({"id": 99, "method": "item/commandExecution/requestApproval", "params": {
    "threadId": "thread-1", "turnId": "turn-1", "itemId": "edit", "reason": "fixture permission"}})
sys.stdin.buffer.read()
""")
        self.assertNotEqual(cli(*run).returncode, 0)
        attempt = output / "attempt"
        outcome = json.loads((attempt / "outcome.json").read_bytes())
        self.assertEqual(outcome["status"], "incomplete")
        self.assertIn("remains unanswered", outcome["error"])
        sent = [json.loads(line) for line in (attempt / "collector-sent.jsonl").read_bytes().splitlines()]
        self.assertEqual([item["method"] for item in sent],
                         ["initialize", "initialized", "thread/start", "turn/start"])
        self.assertFalse(any(item.get("id") == 99 for item in sent))
        rows = [json.loads(line) for line in (attempt / "receipts.jsonl").read_bytes().splitlines()]
        request = rows[-1]["message"]
        self.assertEqual(request["id"], 99)
        self.assertEqual(request["method"], "item/commandExecution/requestApproval")
        self.assertIsNone(outcome["trigger_observation_sequence"])

    def test_profile_drift_is_recorded_before_launch_and_preserves_failed_attempt(self):
        cli, run, output = self.prepare_failure_fixture("raise AssertionError('must not launch')\n")
        profile = output.parent / "profile.json"
        profile.write_bytes(profile.read_bytes() + b" ")
        self.assertNotEqual(cli(*run).returncode, 0)
        attempt = output / "attempt"
        outcome_raw = (attempt / "outcome.json").read_bytes()
        outcome = json.loads(outcome_raw)
        self.assertEqual(outcome["status"], "incomplete")
        self.assertIn("identity differs:", outcome["error"])
        self.assertIn("profile.json", outcome["error"])
        self.assertIsNone(outcome["thread_id"])
        self.assertFalse((attempt / "collector-sent.jsonl").exists())
        self.assertFalse((attempt / "collector-process.json").exists())
        self.assertNotEqual(cli(*run).returncode, 0)
        self.assertEqual((attempt / "outcome.json").read_bytes(), outcome_raw)

    def test_native_profile_is_refused_before_preparation(self):
        cli, _, output = self.prepare_failure_fixture("raise AssertionError('must not launch')\n")
        profile_path = output.parent / "profile.json"
        profile = json.loads(profile_path.read_bytes())
        profile["kind"] = "native-app-server"
        profile_path.write_bytes(encoded(profile))
        packet = output.parent / "packet"
        rejected = output.parent / "native-rejected"
        result = cli(COLLECTOR, "prepare", "--seed-package", packet,
                     "--seed-receipt-sha256", sha((packet / "receipt.json").read_bytes()),
                     "--profile", profile_path, "--profile-sha256", sha(profile_path.read_bytes()),
                     "--implementation", "inventory.py", "--output", rejected)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"native is unqualified", result.stderr)
        self.assertFalse(rejected.exists())
        self.assertFalse((output / "attempt").exists())

    def test_allocated_native_discovery_failures_retain_structured_evidence(self):
        stages = (
            "initialize",
            "model/list",
            "config/read",
            "configRequirements/read",
            "skills/list",
            "mcpServerStatus/list",
            "native-cli-version",
        )
        required = (
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
        )
        for stage in stages:
            with self.subTest(stage=stage):
                _, _, legacy = self.prepare_failure_fixture(
                    "sys.stdin.buffer.read()\n"
                )
                base = legacy.parent
                packet = base / "packet"
                codex_home = base / "codex-home"
                codex_home.mkdir()
                instruction = codex_home / "AGENTS.md"
                instruction.write_text("# Synthetic instructions\n")
                (codex_home / "config.toml").write_text("")
                skills = []
                for name in required:
                    path = codex_home / "skills" / name / "SKILL.md"
                    path.parent.mkdir(parents=True)
                    path.write_text(f"# {name}\n")
                    reference = (
                        path.parent / "references" / "contract.md"
                    )
                    reference.parent.mkdir()
                    reference.write_text(f"# {name} contract\n")
                    skills.append({
                        "name": name,
                        "enabled": True,
                        "scope": "user",
                        "path": str(path),
                    })

                executable = base / "failing-codex"
                executable.write_text(
                    "#!" + sys.executable + "\n"
                    + "FAIL = " + repr(stage) + "\n"
                    + "SKILLS = " + repr(skills) + "\n"
                    + r'''
import json
from pathlib import Path
import sys

if sys.argv[1:] == ["--version"]:
    if FAIL != "native-cli-version":
        print("codex-cli 9.9.9")
    raise SystemExit(0)

def receive(method):
    message = json.loads(sys.stdin.buffer.readline())
    assert message["method"] == method, message
    return message

def answer(request, result, stage):
    if FAIL == stage:
        response = {
            "id": request["id"],
            "error": {
                "code": -32000,
                "message": "synthetic " + stage + " failure",
            },
        }
    else:
        response = {"id": request["id"], "result": result}
    sys.stdout.buffer.write(
        (json.dumps(response) + "\n").encode()
    )
    sys.stdout.buffer.flush()
    if FAIL == stage:
        sys.stdin.buffer.read()
        raise SystemExit(0)

initial = receive("initialize")
answer(initial, {"userAgent": "synthetic-native/9.9.9"},
       "initialize")
receive("initialized")
listing = receive("model/list")
answer(listing, {
    "data": [{
        "model": "gpt-6.1-sol",
        "supportedReasoningEfforts": [{
            "reasoningEffort": "medium",
        }],
    }],
    "nextCursor": None,
}, "model/list")
config = receive("config/read")
answer(config, {"config": {}, "origins": {}}, "config/read")
requirements = receive("configRequirements/read")
answer(requirements, {"requirements": None},
       "configRequirements/read")
skills = receive("skills/list")
answer(skills, {
    "data": [{
        "cwd": str(Path.cwd()),
        "skills": SKILLS,
        "errors": [],
    }],
}, "skills/list")
servers = receive("mcpServerStatus/list")
answer(servers, {"data": [], "nextCursor": None},
       "mcpServerStatus/list")
sys.stdin.buffer.read()
''')
                executable.chmod(0o755)
                output = base / "failed-native-preparation"
                environment = dict(
                    os.environ,
                    CODEX_HOME=str(codex_home),
                )
                result = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(COLLECTOR),
                        "prepare",
                        "--native",
                        "--native-executable", str(executable),
                        "--native-executable-sha256",
                        sha(executable.read_bytes()),
                        "--model", "gpt-6.1-sol",
                        "--effort", "medium",
                        "--seed-package", str(packet),
                        "--seed-receipt-sha256",
                        sha((packet / "receipt.json").read_bytes()),
                        "--implementation", "inventory.py",
                        "--output", str(output),
                    ],
                    capture_output=True,
                    timeout=30,
                    env=environment,
                )
                self.assertNotEqual(result.returncode, 0)
                failure_path = output / "preparation-failure.json"
                self.assertTrue(failure_path.is_file())
                failure = json.loads(failure_path.read_bytes())
                self.assertEqual(
                    failure["schema"],
                    "compatibility-native-preparation-failure/v1",
                )
                self.assertEqual(failure["status"], "incomplete")
                expected_phase = (
                    stage if stage == "native-cli-version"
                    else "profile-discovery:" + stage
                )
                self.assertEqual(failure["phase"], expected_phase)
                self.assertEqual(
                    failure["terminal_boundary"],
                    {
                        "phase": expected_phase,
                        "native_tasks_started": 0,
                    },
                )
                retained = {
                    entry["path"]
                    for entry in failure["retained_evidence"]
                }
                self.assertIn(
                    "preparation/profile-discovery-stdout.log",
                    retained,
                )
                self.assertIn(
                    "preparation/profile-discovery-stderr.log",
                    retained,
                )
                self.assertIn(
                    "preparation/profile-discovery-sent.jsonl",
                    retained,
                )
                self.assertIn(
                    "preparation/profile-discovery-process.json",
                    retained,
                )
                sent = [
                    json.loads(line)
                    for line in (
                        output
                        / "preparation"
                        / "profile-discovery-sent.jsonl"
                    ).read_bytes().splitlines()
                ]
                self.assertFalse(any(
                    message["method"] in {
                        "thread/start",
                        "turn/start",
                    }
                    for message in sent
                ))
                self.assertFalse((output / "manifest.json").exists())

    def test_native_failure_before_output_allocation_remains_a_diagnostic(self):
        cli, _, legacy = self.prepare_failure_fixture(
            "sys.stdin.buffer.read()\n"
        )
        base = legacy.parent
        packet = base / "packet"
        output = base / "unallocated-native-failure"
        missing = base / "missing-native-executable"
        result = cli(
            COLLECTOR,
            "prepare",
            "--native",
            "--native-executable", missing,
            "--native-executable-sha256", "0" * 64,
            "--model", "gpt-6.1-sol",
            "--effort", "medium",
            "--seed-package", packet,
            "--seed-receipt-sha256",
            sha((packet / "receipt.json").read_bytes()),
            "--implementation", "inventory.py",
            "--output", output,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(output.exists())
        self.assertIn(
            b"absolute executable native file required",
            result.stderr,
        )

    def test_native_shaped_fake_version_mismatch_refuses_task_and_retains_attempt(self):
        cli, _, legacy_output = self.prepare_failure_fixture("sys.stdin.buffer.read()\n")
        base = legacy_output.parent
        fixture = base / "fake.py"
        fixture.write_text(r'''import json
import sys

initial = json.loads(sys.stdin.buffer.readline())
assert initial["method"] == "initialize", initial
sys.stdout.buffer.write((json.dumps({
    "id": initial["id"], "result": {"userAgent": "synthetic-native/other"}
}) + "\n").encode())
sys.stdout.buffer.flush()
sys.stdin.buffer.read()
''')
        profile_path = base / "profile.json"
        profile = json.loads(profile_path.read_bytes())
        profile["kind"] = "cooperative-native-app-server-fake/v1"
        profile["fixture_sha256"] = sha(fixture.read_bytes())
        profile["app_server_profile"] = {
            "schema": "compatibility-native-protocol-profile/v1",
            "version": "synthetic-native/expected"}
        profile_path.write_bytes(encoded(profile))
        packet, output = base / "packet", base / "native-shaped-observation"
        prepared = cli(COLLECTOR, "prepare", "--seed-package", packet,
                       "--seed-receipt-sha256", sha((packet / "receipt.json").read_bytes()),
                       "--profile", profile_path, "--profile-sha256", sha(profile_path.read_bytes()),
                       "--implementation", "inventory.py", "--output", output)
        self.assertEqual(prepared.returncode, 0, prepared.stderr.decode())
        run = (COLLECTOR, "run", "--manifest", output / "manifest.json",
               "--expected-sha256", sha((output / "manifest.json").read_bytes()))
        result = cli(*run)
        self.assertNotEqual(result.returncode, 0, result.stdout.decode())
        attempt = output / "attempt"
        outcome = json.loads((attempt / "outcome.json").read_bytes())
        self.assertEqual(outcome["status"], "incomplete")
        self.assertIsNone(outcome["turn_id"])
        self.assertIn("version", outcome["error"])
        self.assertIn("synthetic-native/expected", outcome["error"])
        self.assertIn("synthetic-native/other", outcome["error"])
        sent = [json.loads(line) for line in
                (attempt / "collector-sent.jsonl").read_bytes().splitlines()]
        self.assertEqual(sent[0]["method"], "initialize")
        self.assertFalse(any(message["method"] == "turn/start" for message in sent))
        received = [json.loads(line) for line in
                    (attempt / "collector-stdout.log").read_bytes().splitlines()]
        self.assertEqual(received[0], {"id": sent[0]["id"], "result": {
            "userAgent": "synthetic-native/other"}})

    def test_native_shaped_fake_catalog_ending_controls_effort_check(self):
        for cursor_present, cursor in ((True, None), (False, None), (True, "next-page")):
            with self.subTest(cursor_present=cursor_present, cursor=cursor):
                cli, _, legacy_output = self.prepare_failure_fixture("sys.stdin.buffer.read()\n")
                base = legacy_output.parent
                catalog = {"data": [{
                    "id": "synthetic-sol", "model": "gpt-6.1-sol",
                    "displayName": "Synthetic Sol", "description": "Synthetic catalog only",
                    "hidden": False, "isDefault": True, "defaultReasoningEffort": "low",
                    "supportedReasoningEfforts": [
                        {"reasoningEffort": "low", "description": "Synthetic low effort"}],
                }], "nextCursor": None}
                if cursor_present:
                    catalog["nextCursor"] = cursor
                else:
                    del catalog["nextCursor"]
                initialize = {"userAgent": "synthetic-native/expected",
                              "codexHome": "/synthetic/codex",
                              "platformFamily": "unix", "platformOs": "linux"}
                fixture = base / "fake.py"
                fixture.write_text("INITIALIZE = " + repr(initialize) + "\n"
                                   + "CATALOG = " + repr(catalog) + "\n" + r'''
import json
import sys

def receive(method):
    message = json.loads(sys.stdin.buffer.readline())
    assert message["method"] == method, message
    return message

def emit(value):
    sys.stdout.buffer.write((json.dumps(value) + "\n").encode())
    sys.stdout.buffer.flush()

first = receive("initialize")
emit({"id": first["id"], "result": INITIALIZE})
initialized = receive("initialized")
assert "id" not in initialized, initialized
listing = receive("model/list")
assert listing["params"].get("cursor") is None, listing
assert listing["params"].get("includeHidden") is True, listing
emit({"id": listing["id"], "result": CATALOG})
# Stay alive until the collector closes its owned process.
sys.stdin.buffer.read()
''')
                profile_path = base / "profile.json"
                profile = json.loads(profile_path.read_bytes())
                profile["kind"] = "cooperative-native-app-server-fake/v1"
                profile["fixture_sha256"] = sha(fixture.read_bytes())
                profile["app_server_profile"] = {
                    "schema": "compatibility-native-protocol-profile/v1",
                    "version": "synthetic-native/expected",
                    "model": "gpt-6.1-sol", "effort": "medium"}
                profile_path.write_bytes(encoded(profile))
                packet, output = base / "packet", base / "unsupported-effort-observation"
                prepared = cli(COLLECTOR, "prepare", "--seed-package", packet,
                               "--seed-receipt-sha256", sha((packet / "receipt.json").read_bytes()),
                               "--profile", profile_path, "--profile-sha256", sha(profile_path.read_bytes()),
                               "--implementation", "inventory.py", "--output", output)
                self.assertEqual(prepared.returncode, 0, prepared.stderr.decode())
                result = cli(COLLECTOR, "run", "--manifest", output / "manifest.json",
                             "--expected-sha256", sha((output / "manifest.json").read_bytes()))
                self.assertNotEqual(result.returncode, 0, result.stdout.decode())
                attempt = output / "attempt"
                outcome = json.loads((attempt / "outcome.json").read_bytes())
                self.assertEqual(outcome["status"], "incomplete")
                self.assertIsNone(outcome["thread_id"])
                self.assertIsNone(outcome["turn_id"])
                self.assertFalse(outcome["amendment_rpc_accepted"])
                self.assertEqual(outcome["semantic_success"], "not-assessed")
                self.assertIsNone(outcome["trigger_observation_sequence"])
                if cursor is not None:
                    self.assertIn("paging", outcome["error"])
                    self.assertNotIn("effort unavailable", outcome["error"])
                else:
                    self.assertIn("effort", outcome["error"])
                    self.assertIn("gpt-6.1-sol", outcome["error"])
                    self.assertIn("medium", outcome["error"])
                    self.assertIn("low", outcome["error"])
                sent = [json.loads(line) for line in
                        (attempt / "collector-sent.jsonl").read_bytes().splitlines()]
                self.assertEqual([message["method"] for message in sent],
                                 ["initialize", "initialized", "model/list"])
                self.assertIsNone(sent[2]["params"].get("cursor"))
                self.assertTrue(sent[2]["params"]["includeHidden"])
                received = [json.loads(line) for line in
                            (attempt / "collector-stdout.log").read_bytes().splitlines()]
                self.assertEqual(received, [
                    {"id": sent[0]["id"], "result": initialize},
                    {"id": sent[2]["id"], "result": catalog}])
                rows = [json.loads(line) for line in
                        (attempt / "receipts.jsonl").read_bytes().splitlines()]
                retained = [row for row in rows if row["kind"] == "received"]
                self.assertEqual([row["message"] for row in retained], received)
                inbound = (attempt / "collector-stdout.log").read_bytes()
                for row in retained:
                    reference = row["wire"]
                    self.assertEqual(reference["file"], "collector-stdout.log")
                    raw = inbound[reference["offset"]:reference["offset"] + reference["bytes"]]
                    self.assertEqual(sha(raw), reference["sha256"])
                    self.assertEqual(json.loads(raw), row["message"])


    def prepare_native_profile_fixture(
        self,
        response_model="gpt-6.1-sol",
        mcp_result=None,
        observe_turn=False,
        reject_steer=False,
        response_roots="matching",
        response_effort="medium",
        settings_cwd=None,
        metadata_variant="null",
    ):
        cli, _, legacy_output = self.prepare_failure_fixture("sys.stdin.buffer.read()\n")
        base = legacy_output.parent
        fixture = base / "fake.py"
        fixture.write_text("RESPONSE_MODEL = " + repr(response_model) + "\nMCP_RESULT = "
                           + repr({"data": []} if mcp_result is None else mcp_result)
                           + "\nOBSERVE_TURN = " + repr(observe_turn)
                           + "\nREJECT_STEER = " + repr(reject_steer)
                           + "\nRESPONSE_ROOTS = " + repr(response_roots)
                           + "\nRESPONSE_EFFORT = " + repr(response_effort)
                           + "\nSETTINGS_CWD = " + repr(settings_cwd)
                           + "\nMETADATA_VARIANT = " + repr(metadata_variant)
                           + "\n" + r'''
import json
from pathlib import Path
import sys

def receive(method):
    message = json.loads(sys.stdin.buffer.readline())
    assert message["method"] == method, message
    return message

def emit(request, result):
    sys.stdout.buffer.write((json.dumps({"id": request["id"], "result": result}) + "\n").encode())
    sys.stdout.buffer.flush()

first = receive("initialize")
emit(first, {"userAgent": "synthetic-native/expected", "codexHome": "/synthetic/codex",
             "platformFamily": "unix", "platformOs": "linux"})
receive("initialized")
listing = receive("model/list")
emit(listing, {"data": [{"id": "synthetic-sol", "model": "gpt-6.1-sol",
    "displayName": "Synthetic Sol", "description": "Cooperative fixture",
    "hidden": False, "isDefault": True, "defaultReasoningEffort": "low",
    "supportedReasoningEfforts": [{"reasoningEffort": "medium", "description": "Medium"}]}]})
config = receive("config/read")
assert config["params"] == {"cwd": str(Path.cwd()), "includeLayers": False}, config
emit(config, {"config": {"model": "gpt-6-luna", "model_reasoning_effort": "low"},
              "origins": {}})
requirements = receive("configRequirements/read")
assert requirements.get("params") is None, requirements
emit(requirements, {})
skills = receive("skills/list")
assert skills["params"] == {"cwds": [str(Path.cwd())], "forceReload": False}, skills
emit(skills, {"data": [{"cwd": str(Path.cwd()), "skills": [], "errors": []}]})
servers = receive("mcpServerStatus/list")
assert servers["params"] == {"cursor": None, "detail": "full"}, servers
emit(servers, MCP_RESULT)
thread = receive("thread/start")
assert thread["params"] == {
    "cwd": str(Path.cwd()),
    "model": "gpt-6.1-sol",
    "approvalPolicy": "on-request",
    "approvalsReviewer": "user",
    "sandbox": "workspace-write",
    "ephemeral": False,
    "historyMode": "paginated",
    "allowProviderModelFallback": False,
    "runtimeWorkspaceRoots": [str(Path.cwd())],
    "environments": [],
    "config": {
        "sandbox_workspace_write": {
            "writable_roots": [],
            "network_access": False,
            "exclude_tmpdir_env_var": True,
            "exclude_slash_tmp": True,
        },
    },
}, thread
metadata = (
    {
        "modelProvider": "unrelated-provider",
        "serviceTier": "unrelated-tier",
        "activePermissionProfile": {
            "id": "unrelated-profile",
            "extends": None,
        },
    }
    if METADATA_VARIANT == "differing"
    else {
        "modelProvider": None,
        "serviceTier": None,
        "activePermissionProfile": None,
    }
)
thread_result = {"model": RESPONSE_MODEL,
    "cwd": str(Path.cwd()), "approvalPolicy": "on-request",
    "approvalsReviewer": "user",
    "sandbox": {"type": "readOnly", "networkAccess": False},
    "reasoningEffort": RESPONSE_EFFORT,
    "thread": {"id": "profile-thread", "sessionId": "profile-session",
        "projectId": None, "cliVersion": "synthetic-native/expected", "createdAt": 1,
        "updatedAt": 1, "cwd": str(Path.cwd()), "ephemeral": True,
        "modelProvider": metadata["modelProvider"], "preview": "",
        "source": "appServer",
        "status": {"type": "idle"}, "turns": []}}
thread_result.update(metadata)
if RESPONSE_ROOTS == "matching":
    thread_result["runtimeWorkspaceRoots"] = [str(Path.cwd())]
elif RESPONSE_ROOTS == "wrong":
    thread_result["runtimeWorkspaceRoots"] = [str(Path.cwd().parent)]
elif RESPONSE_ROOTS == "extra":
    thread_result["runtimeWorkspaceRoots"] = [
        str(Path.cwd()),
        str(Path.cwd().parent),
    ]
elif RESPONSE_ROOTS != "missing":
    raise AssertionError(RESPONSE_ROOTS)
emit(thread, thread_result)
if OBSERVE_TURN:
    task = receive("turn/start")
    assert task["params"] == {
        "threadId": "profile-thread",
        "model": "gpt-6.1-sol",
        "effort": "medium",
        "cwd": str(Path.cwd()),
        "approvalPolicy": "on-request",
        "approvalsReviewer": "user",
        "runtimeWorkspaceRoots": [str(Path.cwd())],
        "environments": [],
        "input": [{
            "type": "text",
            "text": "Add JSON output.",
            "text_elements": [],
        }],
        "sandboxPolicy": {
            "type": "workspaceWrite",
            "writableRoots": [],
            "networkAccess": False,
            "excludeTmpdirEnvVar": True,
            "excludeSlashTmp": True,
        },
    }, task
    emit(task, {"turn": {"id": "profile-turn", "items": [], "status": "inProgress"}})
    if SETTINGS_CWD is not None:
        settings_cwd = (
            str(Path.cwd())
            if SETTINGS_CWD == "matching"
            else str(Path.cwd().parent)
        )
        sys.stdout.buffer.write((json.dumps({
            "method": "thread/settings/updated",
            "params": {
                "threadId": "profile-thread",
                "threadSettings": {
                    "model": "gpt-6.1-sol",
                    "effort": "medium",
                    "cwd": settings_cwd,
                    "approvalPolicy": "on-request",
                    "approvalsReviewer": "user",
                    "sandboxPolicy": {
                        "type": "workspaceWrite",
                        "writableRoots": [],
                        "networkAccess": False,
                        "excludeTmpdirEnvVar": True,
                        "excludeSlashTmp": True,
                    },
                },
            },
        }) + "\n").encode())
        sys.stdout.buffer.flush()
    Path("inventory.py").write_text("DEFAULT = 'json'\n")
    changed = {"method": "item/completed", "params": {
        "threadId": "profile-thread", "turnId": "profile-turn", "completedAtMs": 1,
        "item": {"type": "fileChange", "id": "implementation-change", "status": "completed",
            "changes": [{"path": "inventory.py", "kind": {"type": "update"},
                         "diff": "-DEFAULT = 'text'\n+DEFAULT = 'json'\n"}]}}}
    sys.stdout.buffer.write((json.dumps(changed) + "\n").encode())
    sys.stdout.buffer.flush()
    steer = receive("turn/steer")
    assert steer["params"]["threadId"] == "profile-thread", steer
    assert steer["params"]["expectedTurnId"] == "profile-turn", steer
    if REJECT_STEER:
        sys.stdout.buffer.write((json.dumps({"id": steer["id"], "error": {
            "code": -32000, "message": "turn is no longer active"}}) + "\n").encode())
        sys.stdout.buffer.flush()
    else:
        emit(steer, {"turnId": "profile-turn"})
        Path("inventory.py").write_text("DEFAULT = 'text'\nJSON_FLAG = True\n")
        completed = {"method": "turn/completed", "params": {"threadId": "profile-thread",
            "turn": {"id": "profile-turn", "items": [], "status": "completed", "error": None}}}
        sys.stdout.buffer.write((json.dumps(completed) + "\n").encode())
        sys.stdout.buffer.flush()
sys.stdin.buffer.read()
''')
        profile_path = base / "profile.json"
        profile = json.loads(profile_path.read_bytes())
        profile.update(kind="cooperative-native-app-server-fake/v1",
                       fixture_sha256=sha(fixture.read_bytes()),
                       app_server_profile={"schema": "compatibility-native-protocol-profile/v1",
                           "version": "synthetic-native/expected", "model": "gpt-6.1-sol",
                           "effort": "medium"})
        if observe_turn:
            profile["app_server_profile"]["observe_turn"] = True
        profile_path.write_bytes(encoded(profile))
        packet, output = base / "packet", base / "profile-observation"
        prepared = cli(COLLECTOR, "prepare", "--seed-package", packet,
                       "--seed-receipt-sha256", sha((packet / "receipt.json").read_bytes()),
                       "--profile", profile_path, "--profile-sha256", sha(profile_path.read_bytes()),
                       "--implementation", "inventory.py", "--output", output)
        self.assertEqual(prepared.returncode, 0, prepared.stderr.decode())
        run = (COLLECTOR, "run", "--manifest", output / "manifest.json",
               "--expected-sha256", sha((output / "manifest.json").read_bytes()))
        return cli, run, output

    def test_native_shaped_fake_delivers_bound_requests_and_preserves_steering_outcome(self):
        for rejected in (False, True):
            with self.subTest(rejected=rejected):
                cli, run, output = self.prepare_native_profile_fixture(
                    observe_turn=True, reject_steer=rejected)
                result = cli(*run)
                self.assertEqual(result.returncode == 0, not rejected, result.stderr.decode())
                attempt = output / "attempt"
                outcome_raw = (attempt / "outcome.json").read_bytes()
                outcome = json.loads(outcome_raw)
                self.assertEqual(outcome["status"],
                                 "incomplete" if rejected else "fake-observation-completed")
                self.assertEqual(outcome["thread_id"], "profile-thread")
                self.assertEqual(outcome["turn_id"], "profile-turn")
                self.assertEqual(outcome["amendment_rpc_accepted"], not rejected)
                self.assertEqual(outcome["semantic_success"], "not-assessed")
                self.assertIsNotNone(outcome["trigger_observation_sequence"])
                sent_raw = (attempt / "collector-sent.jsonl").read_bytes()
                sent = [json.loads(line) for line in sent_raw.splitlines()]
                self.assertEqual([m["method"] for m in sent][-2:], ["turn/start", "turn/steer"])
                task, steer = sent[-2:]
                self.assertEqual(task["params"]["model"], "gpt-6.1-sol")
                self.assertEqual(task["params"]["effort"], "medium")
                for index, message in enumerate((task, steer)):
                    self.assertEqual(message["params"]["input"], [{"type": "text",
                        "text": (output / f"request-{index}.bin").read_text(), "text_elements": []}])
                rows = [json.loads(line) for line in (attempt / "receipts.jsonl").read_bytes().splitlines()]
                observed = next(row for row in rows if row["kind"] == "fake-profile-observed")
                self.assertEqual(observed["effective_profile"]["reasoningEffort"], "medium")
                trigger = next(row for row in rows
                               if row["sequence"] == outcome["trigger_observation_sequence"])
                self.assertEqual(set(trigger["changed"]), {"inventory.py"})
                received = [json.loads(line) for line in (attempt / "collector-stdout.log").read_bytes().splitlines()]
                if rejected:
                    self.assertEqual(received[-1]["error"]["message"], "turn is no longer active")
                    self.assertIn("rejected RPC", outcome["error"])
                else:
                    self.assertEqual(received[-1]["method"], "turn/completed")
                    self.assertEqual((output / "project/inventory.py").read_text(),
                                     "DEFAULT = 'text'\nJSON_FLAG = True\n")
                self.assertNotEqual(cli(*run).returncode, 0)
                self.assertEqual((attempt / "outcome.json").read_bytes(), outcome_raw)
                self.assertEqual((attempt / "collector-sent.jsonl").read_bytes(), sent_raw)

    def test_native_shaped_fake_refuses_unbound_roots_and_effort_before_turn(self):
        cases = (
            ("missing-roots", "missing", "medium"),
            ("wrong-roots", "wrong", "medium"),
            ("extra-roots", "extra", "medium"),
            ("wrong-effort", "matching", "low"),
            ("null-effort", "matching", None),
        )
        for name, roots, effort in cases:
            with self.subTest(case=name):
                cli, run, output = self.prepare_native_profile_fixture(
                    observe_turn=True,
                    response_roots=roots,
                    response_effort=effort,
                )
                result = cli(*run)
                self.assertNotEqual(result.returncode, 0)
                attempt = output / "attempt"
                outcome = json.loads(
                    (attempt / "outcome.json").read_bytes()
                )
                self.assertEqual(outcome["status"], "incomplete")
                sent = [
                    json.loads(line)
                    for line in (
                        attempt / "collector-sent.jsonl"
                    ).read_bytes().splitlines()
                ]
                self.assertEqual(sent[-1]["method"], "thread/start")
                self.assertFalse(any(
                    message["method"] == "turn/start"
                    for message in sent
                ))
                if roots != "matching":
                    self.assertIn(
                        "runtime workspace roots differ",
                        outcome["error"],
                    )
                else:
                    self.assertIn(
                        "thread reasoning effort differs",
                        outcome["error"],
                    )

    def test_native_shaped_fake_ignores_unrelated_profile_metadata(self):
        for metadata_variant in ("null", "differing"):
            with self.subTest(metadata_variant=metadata_variant):
                cli, run, output = self.prepare_native_profile_fixture(
                    observe_turn=True,
                    metadata_variant=metadata_variant,
                )
                result = cli(*run)
                self.assertEqual(
                    result.returncode,
                    0,
                    result.stderr.decode(),
                )
                sent = [
                    json.loads(line)
                    for line in (
                        output / "attempt"
                        / "collector-sent.jsonl"
                    ).read_bytes().splitlines()
                ]
                self.assertTrue(any(
                    message["method"] == "turn/start"
                    for message in sent
                ))

    def test_native_shaped_fake_rejects_contradictory_settings_cwd(self):
        cli, run, output = self.prepare_native_profile_fixture(
            observe_turn=True,
            settings_cwd="wrong",
        )
        result = cli(*run)
        self.assertNotEqual(result.returncode, 0)
        outcome = json.loads(
            (
                output / "attempt" / "outcome.json"
            ).read_bytes()
        )
        self.assertEqual(outcome["status"], "incomplete")
        self.assertIn(
            "native turn settings differ",
            outcome["error"],
        )

    def test_native_shaped_fake_records_profile_without_delivering_a_task(self):
        cli, run, output = self.prepare_native_profile_fixture()
        result = cli(*run)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        attempt = output / "attempt"
        outcome_raw = (attempt / "outcome.json").read_bytes()
        outcome = json.loads(outcome_raw)
        self.assertEqual(outcome["status"], "fake-profile-observed")
        self.assertEqual(outcome["thread_id"], "profile-thread")
        self.assertIsNone(outcome["turn_id"])
        self.assertFalse(outcome["amendment_rpc_accepted"])
        self.assertEqual(outcome["semantic_success"], "not-assessed")
        self.assertIsNone(outcome["trigger_observation_sequence"])
        sent_raw = (attempt / "collector-sent.jsonl").read_bytes()
        sent = [json.loads(line) for line in sent_raw.splitlines()]
        self.assertEqual([message["method"] for message in sent], [
            "initialize", "initialized", "model/list", "config/read", "configRequirements/read",
            "skills/list", "mcpServerStatus/list", "thread/start"])
        rows = [json.loads(line) for line in (attempt / "receipts.jsonl").read_bytes().splitlines()]
        observations = [row for row in rows if row["kind"] == "fake-profile-observed"]
        self.assertEqual(len(observations), 1)
        observation = observations[0]
        self.assertEqual(outcome["profile_observation_sequence"], observation["sequence"])
        self.assertEqual(observation["requested_model"], "gpt-6.1-sol")
        self.assertEqual(observation["requested_turn_effort"], "medium")
        self.assertEqual(observation["effective_profile"]["reasoningEffort"], "medium")
        self.assertIsNone(observation["effective_profile"]["activePermissionProfile"])
        response = next(row for row in rows if row["sequence"] == observation["response_sequence"])
        self.assertEqual(response["message"]["result"]["thread"]["id"], "profile-thread")
        retained = [row for row in rows if row["kind"] == "received"]
        self.assertEqual(retained[2]["message"]["result"]["config"]["model"], "gpt-6-luna")
        self.assertEqual(retained[3]["message"]["result"], {})
        inbound = (attempt / "collector-stdout.log").read_bytes()
        for row in retained:
            reference = row["wire"]
            raw = inbound[reference["offset"]:reference["offset"] + reference["bytes"]]
            self.assertEqual(sha(raw), reference["sha256"])
            self.assertEqual(json.loads(raw), row["message"])
        self.assertNotEqual(cli(*run).returncode, 0)
        self.assertEqual((attempt / "outcome.json").read_bytes(), outcome_raw)
        self.assertEqual((attempt / "collector-sent.jsonl").read_bytes(), sent_raw)

    def test_native_shaped_fake_retains_wrong_thread_model_without_task_delivery(self):
        cli, run, output = self.prepare_native_profile_fixture(response_model="gpt-6-luna")
        result = cli(*run)
        self.assertNotEqual(result.returncode, 0)
        attempt = output / "attempt"
        outcome = json.loads((attempt / "outcome.json").read_bytes())
        self.assertEqual(outcome["status"], "incomplete")
        self.assertEqual(outcome["thread_id"], "profile-thread")
        self.assertIsNone(outcome["turn_id"])
        self.assertIn("thread model differs", outcome["error"])
        self.assertIn("gpt-6.1-sol", outcome["error"])
        self.assertIn("gpt-6-luna", outcome["error"])
        sent = [json.loads(line) for line in (attempt / "collector-sent.jsonl").read_bytes().splitlines()]
        self.assertEqual(sent[-1]["method"], "thread/start")
        self.assertFalse(any(row["method"] in {"turn/start", "turn/steer"} for row in sent))
        received = [json.loads(line) for line in (attempt / "collector-stdout.log").read_bytes().splitlines()]
        self.assertEqual(received[-1]["result"]["model"], "gpt-6-luna")

    def test_native_shaped_fake_preserves_incomplete_mcp_inventory_before_thread(self):
        inventory = {"data": [], "nextCursor": "another-page"}
        cli, run, output = self.prepare_native_profile_fixture(mcp_result=inventory)
        self.assertNotEqual(cli(*run).returncode, 0)
        attempt = output / "attempt"
        outcome = json.loads((attempt / "outcome.json").read_bytes())
        self.assertEqual(outcome["status"], "incomplete")
        self.assertIsNone(outcome["thread_id"])
        self.assertIsNone(outcome["turn_id"])
        self.assertIn("paging is unqualified", outcome["error"])
        sent = [json.loads(line) for line in (attempt / "collector-sent.jsonl").read_bytes().splitlines()]
        self.assertEqual(sent[-1]["method"], "mcpServerStatus/list")
        self.assertFalse(any(row["method"] in {"thread/start", "turn/start", "turn/steer"} for row in sent))
        received = [json.loads(line) for line in (attempt / "collector-stdout.log").read_bytes().splitlines()]
        self.assertEqual(received[-1]["result"], inventory)

    def test_amends_once_after_first_implementation_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            seed = base / "seed"
            seed.mkdir()
            initial = {"inventory.py": b"DEFAULT = 'text'\n",
                       "tests.py": b"# ordinary tests\n"}
            for name, raw in initial.items():
                (seed / name).write_bytes(raw)
            (seed / "inventory.py").chmod(0o755)
            entries = [{"path": name, "sha256": sha(raw),
                        "executable": name == "inventory.py"}
                       for name, raw in sorted(initial.items())]
            requests = []
            for index, name in enumerate(("01-add-json.md", "02-preserve-default.md")):
                raw = (HERE / "requests" / name).read_bytes()
                target = base / str(index)
                target.write_bytes(raw)
                requests.append({"path": target.name, "sha256": sha(raw)})
            spec = {"version": 1, "seed": {"path": "seed", "files": entries,
                    "identity": sha(encoded(entries))}, "requests": requests,
                    "observation_cases": [], "constructed_candidates": []}
            (base / "spec.json").write_bytes(encoded(spec))
            packet, output = base / "packet", base / "observation"

            def cli(*args, success=True):
                result = subprocess.run([sys.executable, "-B", *map(str, args)],
                                        capture_output=True, timeout=15)
                if success:
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                else:
                    self.assertNotEqual(result.returncode, 0)
                return result

            cli(HERE / "prepare_seed.py", "--spec", base / "spec.json",
                "--output", packet)
            fixture = base / "fake.py"
            # This barrier uses the public evidence package, not a fake RPC.
            fixture.write_text(
                "OUTPUT = " + repr(str(output)) + "\n" + r'''
import json
from pathlib import Path
import sys
import time

def receive(method):
    message = json.loads(sys.stdin.buffer.readline())
    assert message["method"] == method, message
    return message

def emit(value):
    sys.stdout.buffer.write((json.dumps(value, separators=(",", ":")) + "\n").encode())
    sys.stdout.buffer.flush()

def tool(ident):
    emit({"method": "item/completed", "params": {
        "threadId": "thread-1", "turnId": "turn-1",
        "item": {"type": "commandExecution", "id": ident, "status": "completed"}}})

first = receive("initialize")
emit({"id": first["id"], "result": {}})
receive("initialized")
thread = receive("thread/start")
emit({"id": thread["id"], "result": {"thread": {"id": "thread-1"}}})
task = receive("turn/start")
assert task["params"]["threadId"] == "thread-1"
emit({"id": task["id"], "result": {"turn": {"id": "turn-1"}}})
Path("tests.py").write_bytes(b"# test-only change\n")
tool("tests-only")
deadline = time.monotonic() + 5
while True:
    journal = Path(OUTPUT, "attempt", "receipts.jsonl")
    rows = [json.loads(line) for line in journal.read_bytes().splitlines()]
    if any(row["kind"] == "tool-completed" and
           row["item"]["id"] == "tests-only" for row in rows):
        break
    assert time.monotonic() < deadline, "test observation was not retained"
    time.sleep(0.01)
Path("inventory.py").write_bytes(b"DEFAULT = 'json'\n")
tool("implementation-1")
steer = receive("turn/steer")
assert steer["params"]["threadId"] == "thread-1"
assert steer["params"]["expectedTurnId"] == "turn-1"
emit({"id": steer["id"], "result": {"turnId": "turn-1"}})
tool("implementation-1")
Path("inventory.py").write_bytes(b"DEFAULT = 'text'\nJSON = True\n")
tool("implementation-2")
emit({"method": "turn/completed", "params": {
    "threadId": "thread-1", "turn": {"id": "turn-1", "status": "completed", "error": None}}})
# Stay alive for the collector's normal owned-process shutdown.
sys.stdin.buffer.read()
''')
            profile = {"kind": "cooperative-python-fake/v1",
                       "command": [sys.executable, "-I", "-S", "-u", str(fixture)],
                       "python_sha256": sha(Path(sys.executable).read_bytes()),
                       "fixture_sha256": sha(fixture.read_bytes())}
            profile_path = base / "profile.json"
            profile_path.write_bytes(encoded(profile))
            prepare = (COLLECTOR, "prepare", "--seed-package", packet,
                       "--seed-receipt-sha256", sha((packet / "receipt.json").read_bytes()),
                       "--profile", profile_path, "--profile-sha256",
                       sha(profile_path.read_bytes()), "--implementation", "inventory.py",
                       "--output", output)
            cli(*prepare)
            self.assertEqual((output / "project" / "inventory.py").stat().st_mode & 0o7777, 0o755)
            manifest_raw = (output / "manifest.json").read_bytes()
            manifest = json.loads(manifest_raw)
            self.assertEqual(manifest["seed_receipt_sha256"],
                             sha((packet / "receipt.json").read_bytes()))
            self.assertEqual(manifest["seed_identity"], spec["seed"]["identity"])
            self.assertEqual(manifest["profile_sha256"], sha(profile_path.read_bytes()))
            self.assertEqual(manifest["request_sha256"], [r["sha256"] for r in requests])
            self.assertFalse(manifest["native_execution_authorized"])
            self.assertEqual(manifest["profile_qualification"], "cooperative-fake-only")
            cli(*prepare, success=False)
            self.assertEqual((output / "manifest.json").read_bytes(), manifest_raw)
            run = (COLLECTOR, "run", "--manifest", output / "manifest.json",
                   "--expected-sha256", sha(manifest_raw))
            cli(*run)
            attempt = output / "attempt"
            sent_raw = (attempt / "collector-sent.jsonl").read_bytes()
            inbound = (attempt / "collector-stdout.log").read_bytes()
            sent = [json.loads(line) for line in sent_raw.splitlines()]
            self.assertEqual([m["method"] for m in sent],
                             ["initialize", "initialized", "thread/start", "turn/start", "turn/steer"])
            for message, index in ((sent[3], 0), (sent[4], 1)):
                self.assertEqual(message["params"]["input"], [{"type": "text",
                    "text": (packet / "requests" / f"{index:04d}").read_bytes().decode("utf-8"),
                    "text_elements": []}])
            rows_raw = (attempt / "receipts.jsonl").read_bytes()
            rows = [json.loads(line) for line in rows_raw.splitlines()]
            self.assertEqual([r["sequence"] for r in rows], list(range(len(rows))))
            scans = [r for r in rows if r["kind"] == "tool-completed"]
            self.assertEqual([r["item"]["id"] for r in scans],
                             ["tests-only", "implementation-1", "implementation-1", "implementation-2"])
            self.assertEqual(scans[0]["changed"], {})
            trigger, = [r for r in rows if r["kind"] == "amendment-trigger"]
            self.assertEqual(trigger["observation_sequence"], scans[1]["sequence"])
            self.assertEqual(scans[1]["changed"], {"inventory.py": {
                "before": sha(initial["inventory.py"]), "after": sha(b"DEFAULT = 'json'\n")}})
            self.assertEqual(scans[1]["item_sha256"], sha(encoded(scans[1]["item"])))
            accepted, = [r for r in rows if r["kind"] == "amendment-rpc-accepted"]
            self.assertGreater(accepted["sequence"], trigger["sequence"])
            self.assertEqual(accepted["returned_turn_id"], "turn-1")
            for row in rows:
                if "wire" in row:
                    reference = row["wire"]
                    raw = sent_raw if reference["file"] == "collector-sent.jsonl" else inbound
                    part = raw[reference["offset"]:reference["offset"] + reference["bytes"]]
                    self.assertEqual(sha(part), reference["sha256"])
                    self.assertEqual(json.loads(part), row["message"])
            outcome_raw = (attempt / "outcome.json").read_bytes()
            outcome = json.loads(outcome_raw)
            self.assertEqual(outcome["status"], "fake-observation-completed")
            self.assertEqual((outcome["thread_id"], outcome["turn_id"]), ("thread-1", "turn-1"))
            self.assertTrue(outcome["amendment_rpc_accepted"])
            self.assertEqual(outcome["semantic_success"], "not-assessed")
            self.assertEqual(outcome["trigger_observation_sequence"], scans[1]["sequence"])
            cli(*run, success=False)
            self.assertEqual((attempt / "outcome.json").read_bytes(), outcome_raw)
            self.assertEqual((attempt / "receipts.jsonl").read_bytes(), rows_raw)

    def test_git_baseline_is_a_clean_local_seed_with_retained_identity(self):
        _, _, output = self.prepare_failure_fixture(
            "sys.stdin.buffer.read()\n", git_evidence=True,
        )
        manifest = json.loads((output / "manifest.json").read_bytes())
        ref = manifest["git_baseline"]
        raw = (output / ref["path"]).read_bytes()
        self.assertEqual(sha(raw), ref["sha256"])
        baseline = json.loads(raw)
        self.assertEqual(baseline["status"], "ready")
        self.assertEqual(baseline["branch"], "compatibility-observation")
        self.assertEqual(baseline["initial_status"], "clean")
        self.assertEqual(baseline["remotes"], "none-observed")
        names = {entry["name"]: entry["record"] for entry in baseline["commands"]}
        directory = output / "baseline-git"
        for name in ("author-identity", "committer-identity"):
            record = json.loads((directory / names[name]["path"]).read_bytes())
            content = (directory / name / record["stdout"]["path"]).read_bytes()
            self.assertIn(b"Compatibility Fixture <fixture@example.invalid>", content)
            self.assertEqual(record["exit_code"], 0)
            self.assertLessEqual(record["started_monotonic_ns"], record["finished_monotonic_ns"])
        commit_record = json.loads((directory / names["seed-commit"]["path"]).read_bytes())
        commit = (directory / "seed-commit" / commit_record["stdout"]["path"]).read_bytes()
        self.assertIn(b"commit " + baseline["head"].encode(), commit)
        self.assertIn(b"chore: prepare compatibility observation seed", commit)
        self.assertEqual([entry["path"] for entry in baseline["source_inventory"]], ["inventory.py"])
        self.assertFalse((output / "attempt").exists())

    def test_git_baseline_drift_refuses_task_and_preserves_attempt(self):
        for change in ("untracked", "head", "branch"):
            with self.subTest(change=change):
                cli, run, output = self.prepare_failure_fixture(
                    "sys.stdin.buffer.read()\n", mark_launch=True,
                    git_evidence=True,
                )
                project = output / "project"
                if change == "untracked":
                    (project / "unrelated.txt").write_text("not part of the seed\n")
                elif change == "head":
                    changed = subprocess.run(
                        ["git", "-C", str(project), "commit", "--allow-empty", "-m", "chore: change baseline"],
                        capture_output=True, timeout=10,
                    )
                    self.assertEqual(changed.returncode, 0, changed.stderr.decode())
                else:
                    changed = subprocess.run(
                        ["git", "-C", str(project), "checkout", "-b", "other-branch"],
                        capture_output=True, timeout=10,
                    )
                    self.assertEqual(changed.returncode, 0, changed.stderr.decode())
                result = cli(*run)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b"baseline Git state changed", result.stderr)
                self.assertFalse((output.parent / "fake-launched").exists())
                outcome = json.loads((output / "attempt/outcome.json").read_bytes())
                self.assertEqual(outcome["status"], "incomplete")
                self.assertIsNone(outcome["turn_id"])
                self.assertEqual(outcome["final_source"]["status"], "complete")
                before = (output / "attempt/outcome.json").read_bytes()
                self.assertNotEqual(cli(*run).returncode, 0)
                self.assertEqual((output / "attempt/outcome.json").read_bytes(), before)

    def test_failed_git_construction_retains_command_evidence_without_launch(self):
        _, _, legacy = self.prepare_failure_fixture(
            "sys.stdin.buffer.read()\n", mark_launch=True,
        )
        base = legacy.parent
        profile = base / "profile.json"
        output = base / "failed-git-preparation"
        environment = dict(os.environ, GIT_AUTHOR_NAME="", GIT_AUTHOR_EMAIL="")
        result = subprocess.run([
            sys.executable, "-B", str(COLLECTOR), "prepare", "--git-evidence",
            "--seed-package", str(base / "packet"),
            "--seed-receipt-sha256", sha((base / "packet/receipt.json").read_bytes()),
            "--profile", str(profile), "--profile-sha256", sha(profile.read_bytes()),
            "--implementation", "inventory.py", "--output", str(output),
        ], capture_output=True, timeout=15, env=environment)
        self.assertNotEqual(result.returncode, 0)
        baseline = json.loads((output / "baseline-git/baseline.json").read_bytes())
        self.assertEqual(baseline["status"], "failed")
        self.assertIn("author-identity", baseline["error"])
        failed = json.loads((output / "baseline-git/author-identity/record.json").read_bytes())
        self.assertNotEqual(failed["exit_code"], 0)
        self.assertTrue((output / "baseline-git/author-identity/stderr.bin").read_bytes())
        self.assertFalse((output / "manifest.json").exists())
        self.assertFalse((base / "fake-launched").exists())

    def test_final_git_retains_task_commit_staged_and_untracked_work(self):
        tail = r'''
import subprocess
Path("inventory.py").write_text("DEFAULT = 'json'\n")
emit({"method": "item/completed", "params": {
    "threadId": "thread-1", "turnId": "turn-1",
    "item": {"type": "commandExecution", "id": "change", "status": "completed"}}})
steer = receive()
emit({"id": steer["id"], "result": {"turnId": "turn-1"}})
Path("inventory.py").write_text("DEFAULT = 'text'\nJSON = True\n")
subprocess.run(["git", "add", "inventory.py"], check=True, capture_output=True)
subprocess.run(["git", "commit", "-m", "feat: preserve default and add opt-in JSON"], check=True, capture_output=True)
Path("staged.txt").write_text("unfinished staged work\n")
subprocess.run(["git", "add", "staged.txt"], check=True, capture_output=True)
Path("untracked.txt").write_text("unfinished untracked work\n")
emit({"method": "turn/completed", "params": {
    "threadId": "thread-1", "turn": {"id": "turn-1", "status": "completed", "error": None}}})
sys.stdin.buffer.read()
'''
        cli, run, output = self.prepare_failure_fixture(tail, git_evidence=True)
        result = cli(*run)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        attempt = output / "attempt"
        outcome = json.loads((attempt / "outcome.json").read_bytes())
        self.assertEqual(outcome["status"], "fake-observation-completed")
        self.assertEqual(outcome["semantic_success"], "not-assessed")
        final = json.loads((attempt / outcome["final_git"]["inventory"]).read_bytes())
        self.assertEqual(final["status"], "complete")
        self.assertNotEqual(final["head"], final["baseline_head"])
        self.assertEqual(final["source_correspondence"], "matched-at-recorded-boundaries")
        self.assertIn(b"feat: preserve default and add opt-in JSON", (attempt / "final-git/commits/stdout.bin").read_bytes())
        self.assertIn(b"inventory.py", (attempt / "final-git/committed-paths/stdout.bin").read_bytes())
        status = (attempt / "final-git/status/stdout.bin").read_bytes()
        self.assertIn(b"A  staged.txt\0", status)
        self.assertIn(b"?? untracked.txt\0", status)
        self.assertEqual((attempt / "final-git/untracked/stdout.bin").read_bytes(), b"untracked.txt\0")
        self.assertEqual((attempt / "final-git/remotes/stdout.bin").read_bytes(), b"")
        source = json.loads((attempt / "final-source.json").read_bytes())
        self.assertEqual({entry["path"] for entry in source["files"]},
                         {"inventory.py", "staged.txt", "untracked.txt"})
        self.assertEqual(json.loads((attempt / "task-delivery-git/preflight.json").read_bytes())["status"], "matched")

    def test_final_git_failure_preserves_collection_outcome_source_and_usage(self):
        tail = r'''
import shutil
Path("inventory.py").write_text("DEFAULT = 'json'\n")
emit({"method": "item/completed", "params": {
    "threadId": "thread-1", "turnId": "turn-1",
    "item": {"type": "commandExecution", "id": "change", "status": "completed"}}})
steer = receive()
emit({"id": steer["id"], "result": {"turnId": "turn-1"}})
Path("inventory.py").write_text("DEFAULT = 'text'\nJSON = True\n")
shutil.rmtree(".git")
emit({"method": "turn/completed", "params": {
    "threadId": "thread-1", "turn": {"id": "turn-1", "status": "completed", "error": None}}})
sys.stdin.buffer.read()
'''
        cli, run, output = self.prepare_failure_fixture(tail, git_evidence=True)
        result = cli(*run)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        attempt = output / "attempt"
        outcome = json.loads((attempt / "outcome.json").read_bytes())
        self.assertEqual(outcome["status"], "fake-observation-completed")
        self.assertEqual(outcome["final_source"]["status"], "complete")
        self.assertEqual(outcome["final_git"]["status"], "incomplete")
        self.assertIn("usage_observations", outcome)
        final = json.loads((attempt / "final-git/final-git.json").read_bytes())
        self.assertIn("Git command failed: head", final["errors"])
        self.assertNotIn("head", final)
        self.assertEqual((attempt / "final-source/inventory.py").read_text(), "DEFAULT = 'text'\nJSON = True\n")

    def test_deadline_preserves_partial_tool_inventory_and_failed_attempt(self):
        for boundary in ("started", "completed"):
            with self.subTest(boundary=boundary):
                with tempfile.TemporaryDirectory() as temporary:
                    control = Path(temporary)
                    trigger = control / "slow-read-trigger"
                    completed = control / "slow-read-completed"
                    item = {
                        "type": "commandExecution", "id": "author-test",
                        "command": "python -m unittest",
                        "status": "inProgress" if boundary == "started" else "completed",
                    }
                    if boundary == "completed":
                        item.update(exitCode=0, aggregatedOutput="OK\n")
                    event = {"method": "item/" + boundary, "params": {
                        "threadId": "thread-1", "turnId": "turn-1", "item": item,
                    }}
                    tail = (
                        "Path(" + repr(str(trigger)) + ").write_text('ready')\n"
                        "emit(" + repr(event) + ")\n"
                        "sys.stdin.buffer.read()\n"
                    )
                    cli, _, output = self.prepare_failure_fixture(
                        tail,
                        extra_seed_files={
                            "a-scanned.txt": b"Retain this entry.\n",
                            "z-slow.txt": b"The delayed file.\n",
                        },
                    )
                    manifest_path = output / "manifest.json"
                    manifest = json.loads(manifest_path.read_bytes())
                    manifest["deadline_seconds"] = 1
                    manifest_raw = encoded(manifest) + b"\n"
                    manifest_path.write_bytes(manifest_raw)
                    run = (
                        "run", "--manifest", manifest_path,
                        "--expected-sha256", sha(manifest_raw),
                    )
                    # Delay one real filesystem read; keep the public CLI and
                    # transport intact. The trigger is armed by the fake event.
                    wrapper = control / "delayed-filesystem.py"
                    wrapper.write_text(
                        "from pathlib import Path\n"
                        "import runpy, sys, time\n"
                        "from unittest.mock import patch\n"
                        "TRIGGER = Path(" + repr(str(trigger)) + ")\n"
                        "COMPLETED = Path(" + repr(str(completed)) + ")\n"
                        "original = Path.read_bytes\n"
                        "def delayed_read(path):\n"
                        "    if path.name == 'z-slow.txt' and TRIGGER.exists():\n"
                        "        TRIGGER.unlink()\n"
                        "        time.sleep(3)\n"
                        "        COMPLETED.write_text('read continued')\n"
                        "    return original(path)\n"
                        "sys.path.insert(0, " + repr(str(HERE)) + ")\n"
                        "sys.argv[0] = " + repr(str(COLLECTOR)) + "\n"
                        "with patch.object(Path, 'read_bytes', delayed_read):\n"
                        "    runpy.run_path(sys.argv[0], run_name='__main__')\n"
                    )

                    result = cli(wrapper, *run)

                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertFalse(trigger.exists(), "the delayed read was not reached")
                    self.assertFalse(completed.exists(), "the deadline did not interrupt the read")
                    attempt = output / "attempt"
                    rows = [json.loads(line) for line in
                            (attempt / "receipts.jsonl").read_bytes().splitlines()]
                    received = next(row for row in rows
                                    if row["kind"] == "received"
                                    and row["message"] == event)
                    retained = [row for row in rows
                                if row["kind"] == "tool-" + boundary]
                    self.assertEqual(len(retained), 1)
                    record = retained[0]
                    self.assertEqual(record["event_sequence"], received["sequence"])
                    self.assertEqual(record["item"], item)
                    self.assertEqual(record["thread_id"], "thread-1")
                    self.assertEqual(record["turn_id"], "turn-1")
                    inventory = record["source_inventory"]
                    self.assertEqual(inventory["status"], "incomplete")
                    self.assertIsNone(inventory["identity"])
                    self.assertTrue(inventory["error"])
                    self.assertEqual([entry["path"] for entry in inventory["files"]],
                                     ["a-scanned.txt", "inventory.py"])
                    self.assertEqual(inventory["files"][0]["sha256"],
                                     sha(b"Retain this entry.\n"))
                    self.assertTrue(inventory["started_at"])
                    self.assertTrue(inventory["finished_at"])
                    self.assertGreater(inventory["elapsed_seconds"], 0)
                    outcome = json.loads((attempt / "outcome.json").read_bytes())
                    self.assertEqual(outcome["status"], "incomplete")
                    self.assertEqual(outcome["error"], "TimeoutError: collector deadline exceeded")
                    process = json.loads((attempt / "collector-process.json").read_bytes())
                    self.assertIsNotNone(process["exit_code"])
                    preserved = {p.relative_to(attempt).as_posix(): p.read_bytes()
                                 for p in attempt.rglob("*") if p.is_file()}
                    repeated = cli(COLLECTOR, *run)
                    self.assertNotEqual(repeated.returncode, 0)
                    self.assertEqual(
                        {p.relative_to(attempt).as_posix(): p.read_bytes()
                         for p in attempt.rglob("*") if p.is_file()},
                        preserved,
                    )

    def test_callback_deadline_interrupts_slow_git_qualification_and_retains_attempt(self):
        with tempfile.TemporaryDirectory() as temporary:
            control = Path(temporary)
            real_git = shutil.which("git")
            self.assertIsNotNone(real_git)
            real_git = str(Path(real_git).resolve())
            trigger = control / "slow-git-trigger"
            completed = control / "slow-git-completed"
            wrapper = control / "git"
            wrapper.write_text(
                "#!" + sys.executable + "\n"
                "import os\n"
                "from pathlib import Path\n"
                "import sys\n"
                "import time\n\n"
                "REAL_GIT = " + repr(real_git) + "\n"
                "TRIGGER = Path(" + repr(str(trigger)) + ")\n"
                "COMPLETED = Path(" + repr(str(completed)) + ")\n"
                "if TRIGGER.exists():\n"
                "    TRIGGER.unlink()\n"
                "    time.sleep(3)\n"
                "    COMPLETED.write_text('completed\\n')\n"
                "os.execv(REAL_GIT, [REAL_GIT, *sys.argv[1:]])\n"
            )
            wrapper.chmod(0o755)
            path_env = (
                str(control)
                + os.pathsep
                + os.environ.get("PATH", "")
            )

            with patch.dict(os.environ, {"PATH": path_env}):
                cli, _, output = self.prepare_failure_fixture(
                    "raise AssertionError('task must not be delivered')\n",
                    git_evidence=True,
                    thread_setup=(
                        "Path(" + repr(str(trigger)) + ")"
                        ".write_text('triggered\\n')\n"
                    ),
                )
                manifest_path = output / "manifest.json"
                manifest = json.loads(manifest_path.read_bytes())
                manifest["deadline_seconds"] = 1
                manifest_raw = encoded(manifest) + b"\n"
                manifest_path.write_bytes(manifest_raw)
                run = (
                    COLLECTOR,
                    "run",
                    "--manifest", manifest_path,
                    "--expected-sha256", sha(manifest_raw),
                )

                started = time.monotonic()
                result = cli(*run)
                elapsed = time.monotonic() - started

                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(
                    completed.exists(),
                    "callback work continued beyond the collector deadline",
                )
                self.assertLess(elapsed, 11)

                attempt = output / "attempt"
                outcome = json.loads(
                    (attempt / "outcome.json").read_bytes()
                )
                self.assertEqual(outcome["status"], "incomplete")
                self.assertEqual(
                    outcome["error"],
                    "TimeoutError: collector deadline exceeded",
                )
                self.assertEqual(
                    outcome["final_source"]["status"],
                    "complete",
                )

                process = json.loads(
                    (attempt / "collector-process.json").read_bytes()
                )
                self.assertIsNotNone(process["exit_code"])
                self.assertLessEqual(
                    process["received_bytes"],
                    process["retained_prefix_limit"],
                )

                sent = [
                    json.loads(line)
                    for line in (
                        attempt / "collector-sent.jsonl"
                    ).read_bytes().splitlines()
                ]
                self.assertEqual(
                    [message["method"] for message in sent],
                    ["initialize", "initialized", "thread/start"],
                )

                rows = [
                    json.loads(line)
                    for line in (
                        attempt / "receipts.jsonl"
                    ).read_bytes().splitlines()
                ]
                retained_thread_responses = [
                    row
                    for row in rows
                    if row["kind"] == "received"
                    and row["message"].get("result", {})
                    .get("thread", {}).get("id") == "thread-1"
                ]
                self.assertEqual(
                    len(retained_thread_responses),
                    1,
                )

    def test_git_metadata_drift_before_task_delivery_is_retained(self):
        cli, run, output = self.prepare_failure_fixture(
            "sys.stdin.buffer.read()\n", git_evidence=True,
            thread_setup="Path('metadata-output.txt').write_text('metadata side effect\\n')\n",
        )
        result = cli(*run)
        self.assertNotEqual(result.returncode, 0)
        attempt = output / "attempt"
        sent = [json.loads(line) for line in (attempt / "collector-sent.jsonl").read_bytes().splitlines()]
        self.assertTrue(any(message["method"] == "thread/start" for message in sent))
        self.assertFalse(any(message["method"] == "turn/start" for message in sent))
        check = json.loads((attempt / "task-delivery-git/preflight.json").read_bytes())
        self.assertEqual(check["status"], "incomplete")
        self.assertIn("baseline Git state changed", check["error"])
        outcome = json.loads((attempt / "outcome.json").read_bytes())
        self.assertEqual(outcome["status"], "incomplete")
        self.assertEqual(outcome["final_source"]["status"], "complete")


if __name__ == "__main__":
    unittest.main()
