"""Consumer examples using real Git snapshots and the public builder boundary."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.build_cloud_coordination import build


ROOT = Path(__file__).resolve().parents[1]
DELEGATION = "plugins/rolecasting/skills/delegating-cross-agent-work"


class CloudCoordinationDistributionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT.parent)
        self.addCleanup(temporary.cleanup)
        self.parent = Path(temporary.name).resolve()
        self.source = self.parent / "source"
        self.source.mkdir()
        self.output = self.parent / "cloud-coordination"
        self.policy = {
            "source_root": "plugins",
            "slate": ["rolecasting", "proseweaving"],
            "targets": {"agent-plugins": {
                "plugin_root": "plugins",
                "catalog": ".agents/plugins/marketplace.json",
                "include": ["plugin.json", "skills/**"], "exclude": [],
            }},
        }
        self.write("release/artifact-projection-policy-v1.json", json.dumps(self.policy))
        for name in ("README.md", "BOOTSTRAP.md", "role-policy.md"):
            self.write(f"docs/cloud-coordination/{name}", f"Pinned {name}\n")
        for name in self.policy["slate"]:
            self.write(f"plugins/{name}/plugin.json", json.dumps({"name": name}))
        self.write(f"{DELEGATION}/SKILL.md", "Pinned delegation\n")
        self.write(f"{DELEGATION}/scripts/native_tree.py", "# pinned driver\n")
        self.write(f"{DELEGATION}/references/native-tree-driver.md", "Pinned procedure\n")
        self.write("plugins/rolecasting/skills/choosing-agent-models/SKILL.md", "Pinned selection\n")
        self.git("init", "-q")
        self.commit = self.commit_source()

    def write(self, relative, text):
        path = self.source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.source, text=True).strip()

    def commit_source(self):
        self.git("add", ".")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "commit", "--allow-empty", "-qm", "test: pinned fixture")
        return self.git("rev-parse", "HEAD")

    def manifest(self, output=None, commit=None):
        path = build(self.source, output or self.output, commit or self.commit)
        self.assertEqual(path.name, "MANIFEST.json")
        return json.loads(path.read_bytes())

    def test_distribution_binds_complete_runtime_and_manual_entrypoint(self):
        manifest = self.manifest()
        self.assertEqual(manifest["source"]["commit"], self.commit)
        self.assertEqual(manifest["startup"], {
            "mode": "manual", "entrypoint": "BOOTSTRAP.md",
            "procedure": "README.md", "role_policy": "role-policy.md",
        })
        runtime = manifest["runtime"]
        self.assertEqual(runtime["target"], "agent-plugins")
        receipt = json.loads((self.output / runtime["receipt"]["path"]).read_bytes())
        self.assertEqual(receipt["source"]["commit"], self.commit)
        self.assertEqual(receipt["plugin_slate"], self.policy["slate"])
        catalog = json.loads((self.output / runtime["catalog"]).read_bytes())
        self.assertEqual([item["name"] for item in catalog["plugins"]], self.policy["slate"])
        for name in ("README.md", "BOOTSTRAP.md", "role-policy.md"):
            self.assertEqual((self.output / name).read_text(), f"Pinned {name}\n")
        self.assertEqual(runtime["driver"]["script"], f"runtime/{DELEGATION}/scripts/native_tree.py")
        for locator in [*runtime["skills"].values(), *runtime["driver"].values()]:
            self.assertTrue((self.output / locator).is_file(), locator)

    def test_exact_byte_hashes_cover_every_payload_file_but_not_manifest(self):
        manifest = self.manifest()
        actual = {
            path.relative_to(self.output).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in self.output.rglob("*")
            if path.is_file() and path.name != "MANIFEST.json"
        }
        self.assertEqual({item["path"]: item["sha256"] for item in manifest["files"]}, actual)
        receipt = manifest["runtime"]["receipt"]
        self.assertEqual(receipt["sha256"], actual[receipt["path"]])
        self.assertNotIn("MANIFEST.json", actual)

    def test_manifest_declares_repository_scope_and_unqualified_boundaries(self):
        manifest = self.manifest()
        receipt = json.loads((self.output / manifest["runtime"]["receipt"]["path"]).read_bytes())
        self.assertEqual(manifest["source"]["repository"], "https://github.com/nisavid/provingkit")
        self.assertEqual(manifest["source"]["repository"], receipt["source"]["repository"])
        self.assertEqual(manifest["scope"], {
            "supported": ["manual-entrypoint", "one-current-controller-native-tree"],
            "nonclaims": [
                "automatic-startup", "global-startup", "independent-persistent-chats",
                "cross-root-restoration", "root-wake", "product-attestation",
                "model-attestation", "permission-attestation", "exactly-once-effects",
            ],
        })
        self.assertEqual(manifest["qualification"], {
            "status": "not-qualified-by-build",
            "installation": "not-performed", "deployment": "not-performed",
        })

    def test_explicit_commit_excludes_later_commits_dirty_files_and_untracked_files(self):
        self.write("docs/cloud-coordination/README.md", "later committed procedure\n")
        self.write(f"{DELEGATION}/scripts/native_tree.py", "# later committed driver\n")
        self.commit_source()
        self.write("docs/cloud-coordination/README.md", "dirty procedure\n")
        self.write(f"{DELEGATION}/scripts/native_tree.py", "# dirty driver\n")
        self.write(f"{DELEGATION}/scripts/untracked.py", "# must not ship\n")
        self.manifest()
        self.assertEqual((self.output / "README.md").read_text(), "Pinned README.md\n")
        self.assertEqual((self.output / f"runtime/{DELEGATION}/scripts/native_tree.py").read_text(), "# pinned driver\n")
        self.assertFalse((self.output / f"runtime/{DELEGATION}/scripts/untracked.py").exists())

    def test_same_commit_produces_identical_bytes_in_different_output_paths(self):
        first = self.manifest()
        second = self.manifest(self.parent / "another-output")
        self.assertEqual(first, second)
        for item in first["files"] + [{"path": "MANIFEST.json"}]:
            relative = item["path"]
            self.assertEqual((self.output / relative).read_bytes(),
                             (self.parent / "another-output" / relative).read_bytes())

    def test_locators_follow_the_pinned_projection_policy(self):
        self.policy["targets"]["agent-plugins"].update({
            "plugin_root": "nested/members", "catalog": "catalog/local.json",
        })
        self.write("release/artifact-projection-policy-v1.json", json.dumps(self.policy))
        manifest = self.manifest(commit=self.commit_source())
        runtime = manifest["runtime"]
        self.assertEqual(runtime["catalog"], "runtime/catalog/local.json")
        self.assertEqual(runtime["skills"]["delegating_cross_agent_work"],
                         "runtime/nested/members/rolecasting/skills/delegating-cross-agent-work/SKILL.md")
        for locator in [runtime["catalog"], *runtime["skills"].values(), *runtime["driver"].values()]:
            self.assertTrue((self.output / locator).is_file(), locator)

    def test_existing_export_is_refused_and_preserved(self):
        self.output.mkdir()
        marker = self.output / "existing-export.txt"
        marker.write_bytes(b"preserve exact bytes\n")
        with self.assertRaises(FileExistsError):
            self.manifest()
        self.assertEqual(list(self.output.iterdir()), [marker])
        self.assertEqual(marker.read_bytes(), b"preserve exact bytes\n")

    def test_source_ref_must_be_a_full_immutable_commit(self):
        for value in ("HEAD", self.commit[:12], self.commit + "^{tree}"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    build(self.source, self.output, value)
                self.assertFalse(self.output.exists())

    def test_symlink_output_preserves_the_existing_export(self):
        previous = self.parent / "existing-export"
        previous.mkdir()
        marker = previous / "preserve.txt"
        marker.write_bytes(b"existing export")
        self.output.symlink_to(previous, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.manifest()
        self.assertTrue(self.output.is_symlink())
        self.assertEqual(marker.read_bytes(), b"existing export")
        self.assertEqual(list(previous.iterdir()), [marker])

    def test_source_and_output_cannot_overlap(self):
        with self.assertRaises(ValueError):
            build(self.source, self.source / "export", self.commit)
        self.assertFalse((self.source / "export").exists())

    def test_missing_runtime_entrypoint_fails_before_creating_output(self):
        (self.source / f"{DELEGATION}/scripts/native_tree.py").unlink()
        commit = self.commit_source()
        with self.assertRaises(FileNotFoundError):
            build(self.source, self.output, commit)
        self.assertFalse(self.output.exists())

    def test_symlink_support_document_is_rejected_before_output_creation(self):
        readme = self.source / "docs/cloud-coordination/README.md"
        readme.unlink()
        readme.symlink_to("role-policy.md")
        commit = self.commit_source()
        with self.assertRaises(ValueError):
            build(self.source, self.output, commit)
        self.assertFalse(self.output.exists())

    def test_cli_builds_pinned_distribution_and_refuses_existing_output(self):
        command = [sys.executable, str(ROOT / "scripts/build_cloud_coordination.py"),
                   "--source", str(self.source), "--source-commit", self.commit,
                   "--output", str(self.output)]
        first = subprocess.run(command, text=True, capture_output=True, check=False)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(Path(first.stdout.strip()), self.output / "MANIFEST.json")
        retained = (self.output / "MANIFEST.json").read_bytes()
        second = subprocess.run(command, text=True, capture_output=True, check=False)
        self.assertNotEqual(second.returncode, 0)
        self.assertEqual((self.output / "MANIFEST.json").read_bytes(), retained)


if __name__ == "__main__":
    unittest.main()
