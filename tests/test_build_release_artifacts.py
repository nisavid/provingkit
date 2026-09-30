import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.build_release_artifacts import _build_snapshot, build


ROOT = Path(__file__).resolve().parents[1]
TARGETS = ("agent-plugins", "claude", "cursor")


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

    def test_assigned_local_alpha_projects_all_seven_claude_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            policy = ROOT / "release/artifact-projection-policy-v1.json"
            (source / "release").mkdir()
            (source / "release/artifact-projection-policy-v1.json").write_bytes(
                policy.read_bytes()
            )
            members = json.loads(policy.read_text())["slate"]
            for member in members:
                root = source / "plugins" / member
                (root / ".claude-plugin").mkdir(parents=True)
                manifest = {"name": member, "version": "0.1.0-alpha.2"}
                (root / "plugin.json").write_text(json.dumps(manifest))
                (root / ".claude-plugin/plugin.json").write_text(json.dumps(manifest))
            subprocess.run(["git", "init", "-q"], cwd=source, check=True)
            subprocess.run(["git", "add", "."], cwd=source, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Test",
                    "-c",
                    "user.email=test@example.invalid",
                    "commit",
                    "-qm",
                    "test: alpha source fixture",
                ],
                cwd=source,
                check=True,
            )

            output = Path(tmp) / "claude"
            receipt = json.loads(
                build(source, output, "claude", [], "preview", False).read_text()
            )
            catalog = json.loads(
                (output / ".claude-plugin/marketplace.json").read_text()
            )
            self.assertEqual(
                {entry["name"]: entry["version"] for entry in catalog["plugins"]},
                {member: "0.1.0-alpha.2" for member in members},
            )
            for member in members:
                manifest = json.loads(
                    (
                        output / "plugins" / member / ".claude-plugin/plugin.json"
                    ).read_text()
                )
                self.assertEqual(manifest["version"], "0.1.0-alpha.2")
            self.assertEqual(receipt["plugin_slate"], members)

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

    def test_developer_pages_stay_in_source(self):
        members = ["praxis"]
        for member in members:
            self.assertTrue((ROOT / "plugins" / member / "DEVELOPING.md").is_file())
        for target in TARGETS:
            for output, _ in self.stage(target, members):
                self.assertFalse(any(p.name == "DEVELOPING.md" for p in output.rglob("*")))

    def test_staging_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first"
            second = Path(tmp) / "second"
            r1 = json.loads(build(ROOT, first, "cursor", ["proseweaving"], "preview", False).read_text())
            r2 = json.loads(build(ROOT, second, "cursor", ["proseweaving"], "preview", False).read_text())
            self.assertEqual(r1["artifact_sha256"], r2["artifact_sha256"])
            self.assertEqual(r1["files"], r2["files"])

    def test_praxis_slate_and_runtime_projection(self):
        policy = json.loads((ROOT / "release/artifact-projection-policy-v1.json").read_text())
        definition = json.loads((ROOT / "release/provingkit/definition-v1.json").read_text())
        self.assertEqual(policy["slate"], [m["id"] for m in definition["membership"]["members"]])
        runtime = (
            "plugins/praxis/skills/constructing-agent-policies/scripts/policy_eval_runner.py",
            "plugins/praxis/skills/constructing-agent-policies/scripts/gh_stub.py",
        )
        adapter = "plugins/praxis/skills/constructing-agent-policies/agents/openai.yaml"
        for target in ("agent-plugins", "claude", "cursor"):
            with self.subTest(target=target):
                with tempfile.TemporaryDirectory() as directory:
                    output = Path(directory) / target
                    receipt_path = _build_snapshot(
                        ROOT, output, target, ["praxis"], "preview", False,
                        "0" * 40, "0" * 12,
                    )
                    receipt = json.loads(receipt_path.read_text())
                    self.assertEqual(receipt["plugin_slate"], ["praxis"])
                    self.assertFalse((output / "plugins/praxis/topology.json").exists())
                    for path in runtime:
                        self.assertTrue((output / path).is_file(), path)
                    self.assertEqual((output / adapter).is_file(), target == "agent-plugins")

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
