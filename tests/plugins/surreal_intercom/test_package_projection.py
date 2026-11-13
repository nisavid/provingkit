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
                    for name in ("a", "b"):
                        self.assertEqual(flow["codex"][name]["retained"]["state"], "unknown")
                    self.assertEqual(flow["claude"]["retained"]["state"], "submitted")

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
