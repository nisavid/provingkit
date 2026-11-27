"""Exercise the public release builder with a single Intercom member."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]


class IntercomProjectionTests(unittest.TestCase):
    def test_projected_helpers_run_without_rolecasting_or_a_source_checkout(self):
        with tempfile.TemporaryDirectory(dir=ROOT.parent) as temporary:
            root = Path(temporary)
            source = root / "source"
            (source / "release").mkdir(parents=True)
            shutil.copyfile(
                ROOT / "release/artifact-projection-policy-v1.json",
                source / "release/artifact-projection-policy-v1.json",
            )
            shutil.copytree(
                ROOT / "plugins/surreal-intercom",
                source / "plugins/surreal-intercom",
            )
            for argv in (
                ["git", "init", "-q"], ["git", "add", "."],
                ["git", "-c", "user.name=Fixture", "-c",
                 "user.email=fixture@example.invalid", "commit", "-qm",
                 "test: isolated Intercom source"],
            ):
                subprocess.run(argv, cwd=source, check=True, capture_output=True)
            for target in ("agent-plugins", "claude"):
                with self.subTest(target=target):
                    output = root / target
                    result = subprocess.run([
                        sys.executable, "-B",
                        str(ROOT / "scripts/build_release_artifacts.py"),
                        "--source", str(source), "--output", str(output),
                        "--target", target, "--slate", "surreal-intercom",
                    ], capture_output=True, text=True, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    plugin = output / "plugins/surreal-intercom"
                    self.assertFalse((output / "plugins/rolecasting").exists())
                    for command in (
                        "native_codex_mailbox.py", "claude_mcp_sender.py",
                        "claude_route_nomination.py",
                        "codex_ipc_sender.py", "codex_ipc_idle_sender.py",
                        "codex_route_nomination.py", "owner_admission_sender.py",
                        "codex_daybreak_sender.py",
                        "codex_worker_observer.py",
                    ):
                        result = subprocess.run([
                            sys.executable, "-B", str(plugin / "skills/"
                            "communicating-with-agents/scripts" / command),
                            "--help",
                        ], cwd=root, capture_output=True, text=True, timeout=10)
                        self.assertEqual(result.returncode, 0, result.stderr)
                    nomination_reference = (
                        plugin / "skills/communicating-with-agents/references/"
                        "codex-route-nomination.md"
                    )
                    self.assertTrue(nomination_reference.is_file())
                    nomination_text = nomination_reference.read_text()
                    self.assertIn("codex-route-nomination-request-v2", nomination_text)
                    self.assertIn("Five seconds bounds acquisition only", nomination_text)
                    self.assertIn("Each of exactly two", nomination_text)
                    self.assertIn("2,048 descriptor entries", nomination_text)
                    self.assertIn("per-classification high-water values", nomination_text)
                    claude_nomination_reference = (
                        plugin / "skills/communicating-with-agents/references/"
                        "claude-route-nomination.md"
                    )
                    self.assertTrue(claude_nomination_reference.is_file())
                    claude_nomination_text = claude_nomination_reference.read_text()
                    self.assertIn("claude-route-nomination-request-v1", claude_nomination_text)
                    self.assertIn("claude-sender-request-preparation-v1", claude_nomination_text)
                    self.assertFalse((plugin / "DEVELOPING.md").exists())
                    self.assertFalse((plugin / "topology.json").exists())
                    self.assertEqual(
                        (plugin / ".claude-plugin/plugin.json").exists(),
                        target == "claude",
                    )
                    self.assertEqual(
                        (plugin / "skills/communicating-with-agents/agents/"
                         "openai.yaml").exists(), target == "agent-plugins",
                    )
                    skill_text = (
                        plugin / "skills/communicating-with-agents/SKILL.md"
                    ).read_text()
                    self.assertIn("Choose exactly one reply/wait case", skill_text)
                    self.assertIn("Reply expected, wait now", skill_text)
                    self.assertIn("Reply expected, do not wait now", skill_text)
                    self.assertIn("No reply expected", skill_text)
                    self.assertNotIn("When a reply or wait is requested", skill_text)
                    for reference in (
                        "codex-route-nomination.md", "claude-route-nomination.md",
                    ):
                        reference_text = (
                            plugin / "skills/communicating-with-agents/references" / reference
                        ).read_text()
                        self.assertIn(
                            "shared three-case reply/wait contract", reference_text,
                        )
                    self.assertTrue(
                        (plugin / "skills/communicating-with-agents/references/"
                         "codex-worker-observation-diagnostic.md").is_file()
                    )
                    run = root / (target + "-ordinary")
                    run.mkdir(mode=0o700)
                    driver = run / "projected_ordinary_flow.py"
                    shutil.copyfile(Path(__file__).with_name(driver.name), driver)
                    completed = subprocess.run([
                        sys.executable, "-I", "-S", "-B", str(driver),
                        str(plugin), str(run),
                    ], cwd=run, capture_output=True, text=True, timeout=30)
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    flow = json.loads(completed.stdout)
                    self.assertTrue(flow["origins"])
                    for origin in flow["origins"].values():
                        self.assertTrue(Path(origin).is_relative_to(plugin))
                    matrix = {
                        "native_reply_no_wait": {
                            "readiness": "native", "reply_expected": True,
                            "wait_requested": False,
                        },
                        "native_reply_wait": {
                            "readiness": "native", "reply_expected": True,
                            "wait_requested": True,
                        },
                        "native_no_reply": {
                            "readiness": "native", "reply_expected": False,
                            "wait_requested": False,
                        },
                        "nominated_reply_no_wait": {
                            "readiness": "nominated", "reply_expected": True,
                            "wait_requested": False,
                        },
                        "nominated_reply_wait": {
                            "readiness": "nominated", "reply_expected": True,
                            "wait_requested": True,
                        },
                        "nominated_no_reply": {
                            "readiness": "nominated", "reply_expected": False,
                            "wait_requested": False,
                        },
                    }
                    for direction, kind, state in (
                        ("codex", "claude-mcp", "unknown"),
                        ("claude", "codex-owner-admission", "unknown"),
                    ):
                        self.assertEqual(set(flow[direction]), set(matrix))
                        for name, preference in matrix.items():
                            case = flow[direction][name]
                            self.assertEqual(case["preference"], preference)
                            self.assertEqual(case["retained"]["state"], state)
                            nominated_reply = (
                                preference["readiness"] == "nominated"
                                and preference["reply_expected"]
                            )
                            self.assertEqual(case["nomination_used"], nominated_reply)
                            if nominated_reply:
                                self.assertEqual(
                                    case["retained"]["reply_route"]["kind"], kind,
                                )
                            else:
                                self.assertNotIn("reply_route", case["retained"])

    def test_intercom_can_be_selected_without_other_members(self):
        with tempfile.TemporaryDirectory(dir=ROOT.parent) as temporary:
            root = Path(temporary)
            source = root / "source"
            (source / "release").mkdir(parents=True)
            shutil.copyfile(
                ROOT / "release/artifact-projection-policy-v1.json",
                source / "release/artifact-projection-policy-v1.json",
            )
            plugin = source / "plugins/surreal-intercom"
            skill = plugin / "skills/communicating-with-agents"
            skill.mkdir(parents=True)
            (plugin / "plugin.json").write_text(json.dumps({
                "name": "surreal-intercom", "version": "1.0.0",
                "description": "A synthetic standalone communication member.",
            }))
            (skill / "SKILL.md").write_text(
                "---\nname: communicating-with-agents\n"
                "description: Communicate with an existing peer.\n---\n"
            )
            for argv in (
                ["git", "init", "-q"],
                ["git", "add", "."],
                ["git", "-c", "user.name=Fixture", "-c",
                 "user.email=fixture@example.invalid", "commit", "-qm",
                 "test: standalone source fixture"],
            ):
                subprocess.run(argv, cwd=source, check=True, capture_output=True)

            output = root / "artifact"
            result = subprocess.run([
                sys.executable, "-B", str(ROOT / "scripts/build_release_artifacts.py"),
                "--source", str(source), "--output", str(output),
                "--target", "agent-plugins", "--slate", "surreal-intercom",
            ], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            receipt = json.loads((output / "RECEIPT.json").read_text())
            self.assertEqual(receipt["plugin_slate"], ["surreal-intercom"])
            catalog = json.loads(
                (output / ".agents/plugins/marketplace.json").read_text()
            )
            self.assertEqual(
                [entry["name"] for entry in catalog["plugins"]],
                ["surreal-intercom"],
            )
            self.assertTrue(
                (output / "plugins/surreal-intercom/skills/"
                 "communicating-with-agents/SKILL.md").is_file()
            )


if __name__ == "__main__":
    unittest.main()
