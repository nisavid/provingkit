import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.build_release_artifacts import build


ROOT = Path(__file__).resolve().parents[1]


class ReleaseArtifactBuilderTests(unittest.TestCase):
    def stage(self, target: str, slate=None):
        with tempfile.TemporaryDirectory() as tmp:
            path = build(ROOT, Path(tmp) / target, target, slate or [], "preview", False)
            yield Path(tmp) / target, json.loads(path.read_text())

    def test_agent_plugins_projection_has_catalog_and_receipt(self):
        for output, receipt in self.stage("agent-plugins", ["proseweaving"]):
            self.assertTrue((output / ".agents/plugins/marketplace.json").is_file())
            self.assertTrue((output / "plugins/proseweaving/plugin.json").is_file())
            self.assertFalse(any("evals" in p.parts or "fixtures" in p.parts for p in output.rglob("*")))
            self.assertNotIn("task-witness", receipt["plugin_slate"])
            self.assertEqual(receipt["schema"], "provingkit-artifact-receipt-v1")
            self.assertEqual(len(receipt["artifact_sha256"]), 64)

    def test_target_adapters_are_distinct_and_do_not_leak_dev_files(self):
        for target in ("claude", "cursor"):
            for output, receipt in self.stage(target, ["proseweaving"]):
                self.assertTrue((output / (".claude-plugin" if target == "claude" else ".cursor-plugin") / "marketplace.json").is_file())
                self.assertFalse(any(p.name in {"content-lock.json", "topology.json"} for p in output.rglob("*")))
                self.assertFalse(any(p.name == "openai.yaml" for p in output.rglob("*")))
        for output, _ in self.stage("cursor", ["proseweaving"]):
            manifest = json.loads((output / "plugins/proseweaving/.cursor-plugin/plugin.json").read_text())
            self.assertEqual(manifest["skills"], "./skills/")
            self.assertEqual(manifest["agents"], "./agents/")
        for output, _ in self.stage("cursor", ["rolecasting"]):
            manifest = json.loads((output / "plugins/rolecasting/.cursor-plugin/plugin.json").read_text())
            self.assertEqual(manifest["skills"], "./skills/")
            self.assertNotIn("agents", manifest)

    def test_staging_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first"
            second = Path(tmp) / "second"
            r1 = json.loads(build(ROOT, first, "cursor", ["proseweaving"], "preview", False).read_text())
            r2 = json.loads(build(ROOT, second, "cursor", ["proseweaving"], "preview", False).read_text())
            self.assertEqual(r1["artifact_sha256"], r2["artifact_sha256"])
            self.assertEqual(r1["files"], r2["files"])

    def test_projection_slate_matches_the_kit_definition_membership(self):
        policy = json.loads((ROOT / "release/artifact-projection-policy-v1.json").read_text())
        definition = json.loads((ROOT / "release/provingkit/definition-v1.json").read_text())
        self.assertEqual(
            policy["slate"],
            [member["id"] for member in definition["membership"]["members"]],
        )
        self.assertIn("praxis", policy["slate"])

    def test_praxis_projection_ships_only_runtime_files(self):
        for output, receipt in self.stage("claude", ["praxis"]):
            self.assertTrue((output / "plugins/praxis/plugin.json").is_file())
            self.assertTrue((output / "plugins/praxis/.claude-plugin/plugin.json").is_file())
            self.assertFalse((output / "plugins/praxis/topology.json").exists())
            self.assertFalse(any("__pycache__" in p.parts or p.suffix == ".pyc" for p in output.rglob("*")))
            self.assertEqual(receipt["plugin_slate"], ["praxis"])

    def test_praxis_projection_ships_runtime_scripts_everywhere_and_codex_adapter_only_for_agent_plugins(self):
        # The skill's references route to both runtime scripts, so every
        # supported target must ship them; the Codex skill adapter is a native
        # component that only the agent-plugins projection carries.
        runtime_scripts = (
            "plugins/praxis/skills/aeon-bell/scripts/aeon_bell.py",
            "plugins/praxis/skills/aeon-bell/scripts/codex_status.py",
        )
        codex_adapter = "plugins/praxis/skills/aeon-bell/agents/openai.yaml"
        for target in ("agent-plugins", "claude", "cursor"):
            with self.subTest(target=target):
                for output, receipt in self.stage(target, ["praxis"]):
                    shipped = {entry["path"] for entry in receipt["files"]}
                    for script in runtime_scripts:
                        self.assertTrue((output / script).is_file(), script)
                        self.assertIn(script, shipped)
                    self.assertEqual((output / codex_adapter).is_file(), target == "agent-plugins")
                    self.assertEqual(codex_adapter in shipped, target == "agent-plugins")
                    self.assertEqual(receipt["plugin_slate"], ["praxis"])

    def test_code_only_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                build(ROOT, Path(tmp) / "bad", "agent-plugins", ["task-witness"], "preview", False)

    def test_source_and_output_paths_must_not_overlap(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            output = Path(tmp) / "output"
            output.mkdir()
            marker = output / "marker"
            marker.write_text("preserve this")
            for source, destination in (
                (ROOT, ROOT),
                (ROOT, output),
                (ROOT, output / "nested"),
                (ROOT / "plugins", ROOT),
                (ROOT / "plugins", ROOT / "release"),
            ):
                with self.subTest(source=source, output=destination):
                    with self.assertRaisesRegex(ValueError, "source and output paths must not overlap"):
                        build(source, destination, "agent-plugins", ["proseweaving"], "preview", True)
            self.assertEqual(marker.read_text(), "preserve this")

    def test_projection_uses_head_snapshot_when_source_is_dirty(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            (source / "release").mkdir()
            (source / "plugins/proseweaving").mkdir(parents=True)
            (source / "release/artifact-projection-policy-v1.json").write_text(
                json.dumps(
                    {
                        "slate": ["proseweaving"],
                        "source_root": "plugins",
                        "targets": {
                            "agent-plugins": {
                                "include": ["plugin.json"],
                                "exclude": [],
                                "plugin_root": "plugins",
                                "catalog": ".agents/plugins/marketplace.json",
                            }
                        },
                    }
                )
            )
            plugin = source / "plugins/proseweaving/plugin.json"
            plugin.write_text(json.dumps({"name": "proseweaving", "version": "1"}))
            subprocess.run(["git", "init", "-q"], cwd=source, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=source, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=source, check=True)
            subprocess.run(["git", "add", "."], cwd=source, check=True)
            subprocess.run(["git", "commit", "-qm", "test: fixture"], cwd=source, check=True)
            plugin.write_text(json.dumps({"name": "proseweaving", "version": "dirty"}))
            with tempfile.TemporaryDirectory() as output_dir:
                output = Path(build(source, Path(output_dir) / "artifact", "agent-plugins", ["proseweaving"], "preview", False))
                self.assertEqual(json.loads((output.parent / "plugins/proseweaving/plugin.json").read_text())["version"], "1")


if __name__ == "__main__":
    unittest.main()
