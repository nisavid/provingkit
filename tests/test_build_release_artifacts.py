import json
import tempfile
import unittest
from unittest import mock
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

    def test_staging_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first"
            second = Path(tmp) / "second"
            r1 = json.loads(build(ROOT, first, "cursor", ["proseweaving"], "preview", False).read_text())
            r2 = json.loads(build(ROOT, second, "cursor", ["proseweaving"], "preview", False).read_text())
            self.assertEqual(r1["artifact_sha256"], r2["artifact_sha256"])
            self.assertEqual(r1["files"], r2["files"])

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
                (ROOT, output / "nested"),
                (ROOT / "plugins", ROOT),
            ):
                with self.subTest(source=source, output=destination):
                    with self.assertRaisesRegex(ValueError, "source and output paths must not overlap"):
                        build(source, destination, "agent-plugins", ["proseweaving"], "preview", True)
            self.assertEqual(marker.read_text(), "preserve this")

    def test_dirty_source_is_rejected_before_projection(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            (source / "release").mkdir()
            (source / "release/artifact-projection-policy-v1.json").write_text(
                json.dumps(
                    {
                        "slate": ["proseweaving"],
                        "source_root": "plugins",
                        "targets": {
                            "agent-plugins": {
                                "include": [],
                                "exclude": [],
                                "plugin_root": "plugins",
                                "catalog": ".agents/plugins/marketplace.json",
                            }
                        },
                    }
                )
            )
            with mock.patch(
                "scripts.build_release_artifacts.git",
                return_value=" M plugins/proseweaving/SKILL.md",
            ):
                with self.assertRaisesRegex(ValueError, "source checkout must be clean"):
                    build(
                        source,
                        Path(tmp) / "output",
                        "agent-plugins",
                        ["proseweaving"],
                        "preview",
                        False,
                    )


if __name__ == "__main__":
    unittest.main()
