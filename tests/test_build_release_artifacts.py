import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import build_release_artifacts as builder
from scripts.build_release_artifacts import build


ROOT = Path(__file__).resolve().parents[1]
TARGETS = ("agent-plugins", "claude", "cursor")
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\((?P<target>[^)\s]+)(?:\s+[^)]*)?\)")
MARKDOWN_REFERENCE = re.compile(r"^ {0,3}\[[^\]]+\]:[ \t]*(?P<target>\S+)", re.MULTILINE)
SOURCE_TREE_URL = "https://github.com/nisavid/provingkit/blob/main/"


def markdown_link_targets(text: str):
    """Yield every inline and reference-definition link target, without its fragment."""
    for pattern in (MARKDOWN_LINK, MARKDOWN_REFERENCE):
        for match in pattern.finditer(text):
            yield match.group("target").removeprefix("<").removesuffix(">").split("#", 1)[0]


def developer_pages():
    """The members' source-only developer pages, which no target may ship."""
    return sorted(ROOT.glob("plugins/*/DEVELOPING.md"))


def developer_page_links():
    for page in developer_pages():
        for link in markdown_link_targets(page.read_text(encoding="utf-8")):
            yield "source", page.relative_to(ROOT).as_posix(), page.parent, link


def is_relative(link: str) -> bool:
    return bool(link) and ":" not in link.split("/", 1)[0]


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

    def test_assigned_local_alpha_projects_all_six_claude_versions(self):
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

    def shipped_readme_links(self):
        for target in TARGETS:
            for output, receipt in self.stage(target):
                readmes = sorted(output.glob("plugins/*/README.md"))
                self.assertEqual([path.parent.name for path in readmes], sorted(receipt["plugin_slate"]))
                for readme in readmes:
                    for link in markdown_link_targets(readme.read_text(encoding="utf-8")):
                        yield target, readme.relative_to(output).as_posix(), readme.parent, link

    def test_shipped_readmes_link_only_shipped_files(self):
        for origin, document, parent, link in self.shipped_readme_links():
            if is_relative(link):
                with self.subTest(origin=origin, document=document, link=link):
                    self.assertTrue((parent / link).is_file())

    def test_developer_page_relative_links_resolve(self):
        for origin, document, parent, link in developer_page_links():
            if is_relative(link):
                with self.subTest(origin=origin, document=document, link=link):
                    self.assertTrue((parent / link).is_file())

    def test_source_tree_urls_name_source_files(self):
        for origin, document, _, link in [*self.shipped_readme_links(), *developer_page_links()]:
            if link.startswith(SOURCE_TREE_URL):
                with self.subTest(origin=origin, document=document, link=link):
                    self.assertTrue((ROOT / link.removeprefix(SOURCE_TREE_URL)).is_file())

    def test_developer_pages_stay_in_source(self):
        members = [page.parent.name for page in developer_pages()]
        self.assertEqual(members, ["mergecraft", "versionkeeping"])
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


class ReleaseArtifactPolicySafetyTests(unittest.TestCase):
    """Exercise the public builder with committed, isolated candidate sources."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.parent = Path(temporary.name).resolve()
        self.source = self.parent / "source"
        (self.source / "release").mkdir(parents=True)
        plugin = self.source / "plugins/proseweaving"
        plugin.mkdir(parents=True)
        (plugin / "plugin.json").write_text(json.dumps({"name": "proseweaving"}))
        self.policy = {
            "source_root": "plugins", "slate": ["proseweaving"],
            "targets": {target: {
                "include": ["plugin.json"], "exclude": [],
                "plugin_root": "plugins", "catalog": f".{target}/marketplace.json",
            } for target in TARGETS},
        }
        self.output = self.parent / "artifact"
        self.output.mkdir()
        self.marker = self.output / "preserve.txt"
        self.marker.write_text("previous artifact")
        subprocess.run(["git", "init", "-q"], cwd=self.source, check=True)

    def commit_candidate(self, *, write_policy=True):
        if write_policy:
            (self.source / builder.POLICY_PATH).write_text(json.dumps(self.policy))
        subprocess.run(["git", "add", "."], cwd=self.source, check=True)
        subprocess.run([
            "git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "--allow-empty", "-qm", "test: projection policy fixture",
        ], cwd=self.source, check=True)

    def assert_rejected_before_output(self, target="agent-plugins", slate=None):
        # Prevent output mutation even if a regression reaches the writer. The
        # real policy parsing, Git snapshot, and source validation still run.
        with mock.patch.object(builder, "prepare_output", side_effect=AssertionError(
            "invalid candidate reached output preparation"
        )):
            with self.assertRaises(ValueError):
                build(self.source, self.output, target, slate or [], "preview", True)
        self.assertEqual(self.marker.read_text(), "previous artifact")
        self.assertEqual(list(self.output.iterdir()), [self.marker])

    def test_absolute_catalog_is_rejected_before_output_mutation(self):
        self.policy["targets"]["agent-plugins"]["catalog"] = str(self.parent / "outside.json")
        self.commit_candidate()
        self.assert_rejected_before_output()
        self.assertFalse((self.parent / "outside.json").exists())

    def test_policy_paths_reject_unsafe_syntax_and_types(self):
        invalid = (
            "", ".", "..", "../outside", "nested/../outside", "/outside",
            "//server/share", "C:/outside", "C:\\outside", "plugins\\outside",
            "nested//dir", "nested/./dir", "nested/", "bad\0path", None, 42, [],
        )
        for field in ("source_root", "plugin_root", "catalog"):
            owner = self.policy if field == "source_root" else self.policy["targets"]["agent-plugins"]
            original = owner[field]
            for value in invalid:
                with self.subTest(field=field, value=value):
                    owner[field] = value
                    self.commit_candidate()
                    self.assert_rejected_before_output()
            owner[field] = original

    def test_policy_and_requested_plugin_ids_are_single_components(self):
        for value in ("", ".", "..", "../outside", "/outside", "nested/plugin",
                      "C:/outside", "plugins\\outside", None, 42, []):
            with self.subTest(value=value):
                self.policy["slate"] = ["proseweaving", value]
                self.commit_candidate()
                # Validate the policy slate even when selecting a safe subset.
                self.assert_rejected_before_output(slate=["proseweaving"])
        self.policy["slate"] = ["proseweaving"]
        self.commit_candidate()
        self.assert_rejected_before_output(slate=["../outside"])

    def test_source_root_symlink_is_rejected(self):
        (self.source / "plugins").rename(self.source / "canonical")
        (self.source / "plugins").symlink_to("canonical", target_is_directory=True)
        self.commit_candidate()
        self.assert_rejected_before_output()

    def test_plugin_root_symlink_is_rejected(self):
        (self.source / "plugins/proseweaving").rename(self.source / "plugins/actual")
        (self.source / "plugins/proseweaving").symlink_to("actual", target_is_directory=True)
        self.commit_candidate()
        self.assert_rejected_before_output()

    def test_policy_file_and_ancestor_symlinks_are_rejected(self):
        self.commit_candidate()
        path = self.source / builder.POLICY_PATH
        path.rename(self.source / "release/policy.json")
        path.symlink_to("policy.json")
        self.commit_candidate(write_policy=False)
        self.assert_rejected_before_output()
        path.unlink()
        (self.source / "release/policy.json").rename(path)
        (self.source / "release").rename(self.source / "policy-source")
        (self.source / "release").symlink_to("policy-source", target_is_directory=True)
        self.commit_candidate(write_policy=False)
        self.assert_rejected_before_output()

    def test_excluded_manifest_symlink_is_rejected_for_every_target(self):
        plugin = self.source / "plugins/proseweaving"
        (plugin / "plugin.json").rename(plugin / "identity.json")
        (plugin / "plugin.json").symlink_to("identity.json")
        for target in TARGETS:
            self.policy["targets"][target]["exclude"] = ["plugin.json"]
        self.commit_candidate()
        for target in TARGETS:
            with self.subTest(target=target):
                self.assert_rejected_before_output(target)

    def test_selected_file_and_directory_symlinks_are_rejected(self):
        plugin = self.source / "plugins/proseweaving"
        (plugin / "text.txt").write_text("fixture content")
        link = plugin / "README.md"
        link.symlink_to("text.txt")
        self.policy["targets"]["agent-plugins"]["include"].append("README.md")
        self.commit_candidate()
        self.assert_rejected_before_output()
        link.unlink()
        (plugin / "references").symlink_to(".", target_is_directory=True)
        self.commit_candidate()
        self.assert_rejected_before_output()

    def test_nested_relative_paths_and_partial_slates_remain_supported(self):
        (self.source / "nested").mkdir()
        (self.source / "plugins").rename(self.source / "nested/plugins")
        self.policy["source_root"] = "nested/plugins"
        self.policy["slate"].append("unselected")
        for target in TARGETS:
            spec = self.policy["targets"][target]
            spec["plugin_root"] = "nested/plugins"
            spec["catalog"] = "nested/catalog/marketplace.json"
        self.commit_candidate()
        for target in TARGETS:
            with self.subTest(target=target):
                receipt_path = build(self.source, self.output, target,
                                     ["proseweaving"], "preview", True)
                receipt = json.loads(receipt_path.read_text())
                self.assertEqual(receipt["plugin_slate"], ["proseweaving"])
                self.assertTrue((self.output / "nested/plugins/proseweaving/plugin.json").is_file())
                self.assertTrue((self.output / "nested/catalog/marketplace.json").is_file())
                self.assertTrue(all((self.output / item["path"]).resolve().is_relative_to(self.output)
                                    for item in receipt["files"]))


class ReleaseArtifactOutputSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temporary.cleanup)
        cls.source = Path(temporary.name).resolve()
        (cls.source / "release").mkdir()
        (cls.source / builder.POLICY_PATH).write_text(json.dumps({
            "slate": ["proseweaving", "task-witness"],
            "source_root": "plugins",
            "targets": {"agent-plugins": {
                "include": ["plugin.json"], "exclude": [],
                "plugin_root": "plugins", "catalog": ".agents/plugins/marketplace.json",
            }},
        }))
        plugin = cls.source / "plugins/proseweaving"
        plugin.mkdir(parents=True)
        (plugin / "plugin.json").write_text(json.dumps({"name": "proseweaving"}))
        subprocess.run(["git", "init", "-q"], cwd=cls.source, check=True)
        subprocess.run(["git", "add", "."], cwd=cls.source, check=True)
        subprocess.run([
            "git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
            "commit", "-qm", "test: minimal artifact source",
        ], cwd=cls.source, check=True)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.parent = Path(temporary.name).resolve()
        self.sentinel = self.parent / "sentinel"
        self.sentinel.mkdir()
        self.marker = self.sentinel / "preserve.txt"
        self.marker.write_text("preserve this")
        self.output = self.parent / "artifact"

    def assert_sentinel_preserved(self):
        self.assertEqual(self.marker.read_text(), "preserve this")
        self.assertEqual(list(self.sentinel.iterdir()), [self.marker])

    def test_build_refuses_output_symlink_without_touching_target(self):
        for force in (False, True):
            for suffix in ("", "/", "/."):
                with self.subTest(force=force, suffix=suffix):
                    self.output.symlink_to(self.sentinel, target_is_directory=True)
                    try:
                        with self.assertRaisesRegex(ValueError, "not a symlink"):
                            build(self.source, Path(str(self.output) + suffix), "agent-plugins", ["proseweaving"], "preview", force)
                        self.assertTrue(self.output.is_symlink())
                        self.assert_sentinel_preserved()
                    finally:
                        self.output.unlink()

    def test_cli_preserves_output_symlink_identity(self):
        self.output.symlink_to(self.sentinel, target_is_directory=True)
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/build_release_artifacts.py"),
             "--source", str(self.source), "--output", str(self.output),
             "--target", "agent-plugins", "--slate", "proseweaving", "--force"],
            text=True, capture_output=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not a symlink", result.stderr)
        self.assertTrue(self.output.is_symlink())
        self.assert_sentinel_preserved()

    def test_dangling_output_symlink_is_refused(self):
        destination = self.parent / "missing"
        self.output.symlink_to(destination, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "not a symlink"):
            builder.prepare_output(self.output, True)
        self.assertTrue(self.output.is_symlink())
        self.assertFalse(destination.exists())

    def test_parent_symlinks_are_not_followed_even_before_dotdot(self):
        alias = self.parent / "alias"
        alias.symlink_to(self.sentinel, target_is_directory=True)
        for output in (alias / "artifact", alias / "nested/artifact", alias / "../artifact"):
            with self.subTest(output=output):
                with self.assertRaises(OSError):
                    builder.prepare_output(output, True)
                self.assert_sentinel_preserved()

    def test_group_or_world_writable_parent_is_refused(self):
        shared = self.parent / "shared"
        shared.mkdir()
        for mode in (0o770, 0o777, 0o1777):
            with self.subTest(mode=oct(mode)):
                shared.chmod(mode)
                with self.assertRaisesRegex(ValueError, "writable by other users"):
                    builder.prepare_output(shared / "artifact", True)
                self.assertEqual(list(shared.iterdir()), [])
        shared.chmod(0o700)

    def test_nonsticky_writable_ancestor_is_refused(self):
        shared = self.parent / "shared"
        private = shared / "private"
        private.mkdir(parents=True, mode=0o700)
        shared.chmod(0o777)
        with self.assertRaisesRegex(ValueError, "ancestor is writable"):
            builder.prepare_output(private / "artifact", True)
        self.assertFalse((private / "artifact").exists())
        shared.chmod(0o700)

    def test_foreign_owned_ancestor_is_refused(self):
        real_fstat = os.fstat
        identity = self.parent.stat().st_ino

        def foreign_owner(descriptor):
            metadata = real_fstat(descriptor)
            if metadata.st_ino == identity:
                fields = list(metadata)
                fields[4] = os.geteuid() + 10001
                return os.stat_result(fields)
            return metadata

        with mock.patch.object(builder.os, "fstat", side_effect=foreign_owner):
            with self.assertRaisesRegex(ValueError, "ancestor is writable"):
                builder.prepare_output(self.output, True)
        self.assertFalse(self.output.exists())

    def test_trusted_root_alias_preserves_the_output_leaf(self):
        # Model a root-owned /tmp-style alias without changing the host root.
        alias = Path(self.parent.anchor) / "provingkit-system-alias"
        real_lstat = Path.lstat
        real_resolve = Path.resolve

        def alias_lstat(path):
            if path == alias:
                fields = list(self.parent.lstat())
                fields[0] = stat.S_IFLNK | 0o777
                fields[4] = 0
                return os.stat_result(fields)
            return real_lstat(path)

        def alias_resolve(path, *args, **kwargs):
            if path == alias:
                return self.parent
            return real_resolve(path, *args, **kwargs)

        self.output.symlink_to(self.sentinel, target_is_directory=True)
        with mock.patch.object(Path, "lstat", alias_lstat), mock.patch.object(Path, "resolve", alias_resolve):
            with self.assertRaisesRegex(ValueError, "not a symlink"):
                builder.prepare_output(alias / self.output.name, True)
            self.output.unlink()
            self.assertEqual(builder.prepare_output(alias / self.output.name, False), self.output)
        self.assert_sentinel_preserved()

    def test_private_child_of_sticky_directory_is_supported(self):
        shared = self.parent / "shared"
        private = shared / "private"
        private.mkdir(parents=True, mode=0o700)
        shared.chmod(0o1777)
        output = builder.prepare_output(private / "artifact", False)
        self.assertTrue(output.is_dir())

    def test_leaf_swap_before_recursive_removal_preserves_target(self):
        self.output.mkdir()
        (self.output / "old.txt").write_text("old artifact")
        real_rmtree = shutil.rmtree

        def swap_then_remove(path, *, dir_fd):
            self.output.rename(self.parent / "old-artifact")
            self.output.symlink_to(self.sentinel, target_is_directory=True)
            return real_rmtree(path, dir_fd=dir_fd)

        with mock.patch.object(builder.shutil, "rmtree", side_effect=swap_then_remove) as removal:
            removal.avoids_symlink_attacks = True
            with self.assertRaises(OSError):
                builder.prepare_output(self.output, True)
        self.assertTrue(self.output.is_symlink())
        self.assert_sentinel_preserved()

    def test_nested_symlink_is_removed_without_following_it(self):
        self.output.mkdir()
        (self.output / "link").symlink_to(self.sentinel, target_is_directory=True)
        builder.prepare_output(self.output, True)
        self.assertEqual(list(self.output.iterdir()), [])
        self.assert_sentinel_preserved()

    def test_missing_parents_and_existing_output_contract(self):
        output = self.parent / "new/nested/artifact"
        self.assertEqual(builder.prepare_output(output, False), output)
        marker = output / "old.txt"
        marker.write_text("old artifact")
        with self.assertRaises(FileExistsError):
            builder.prepare_output(output, False)
        self.assertEqual(marker.read_text(), "old artifact")
        builder.prepare_output(output, True)
        self.assertEqual(list(output.iterdir()), [])

    def test_unsupported_safe_removal_fails_before_mutation(self):
        with mock.patch.object(builder.shutil.rmtree, "avoids_symlink_attacks", False):
            with self.assertRaisesRegex(ValueError, "no-follow directory operations"):
                builder.prepare_output(self.output, True)
        self.assertFalse(self.output.exists())
        self.assert_sentinel_preserved()

    def test_root_and_dotdot_output_leaf_are_refused(self):
        for output in (Path(self.parent.anchor), self.parent / ".."):
            with self.subTest(output=output):
                with self.assertRaisesRegex(ValueError, "invalid artifact output"):
                    builder.prepare_output(output, True)
        self.assert_sentinel_preserved()

    def test_regular_file_output_is_preserved(self):
        self.output.write_text("not an artifact directory")
        with self.assertRaises(ValueError):
            builder.prepare_output(self.output, True)
        self.assertEqual(self.output.read_text(), "not an artifact directory")

    def test_forced_rebuild_preserves_receipt_and_projection(self):
        first = build(self.source, self.output, "agent-plugins", ["proseweaving"], "preview", False)
        receipt = first.read_bytes()
        (self.output / "old.txt").write_text("old artifact")
        second = build(self.source, self.output, "agent-plugins", ["proseweaving"], "preview", True)
        self.assertEqual(first, second)
        self.assertEqual(second.read_bytes(), receipt)
        self.assertFalse((self.output / "old.txt").exists())

    def test_projection_remains_private_with_permissive_umask(self):
        self.parent.chmod(0o755)
        real_copy = builder.copy_file

        def check_copy(src, dst):
            real_copy(src, dst)
            # Default-mode descendant directories may be writable under this
            # umask; other users must not be able to traverse the output root.
            self.assertEqual(stat.S_IMODE(self.output.stat().st_mode) & 0o077, 0)

        previous_umask = os.umask(0)
        try:
            with mock.patch.object(builder, "copy_file", side_effect=check_copy) as copied:
                build(self.source, self.output, "agent-plugins", ["proseweaving"], "preview", False)
                self.assertTrue(copied.called)
        finally:
            os.umask(previous_umask)

    def test_invalid_build_request_does_not_remove_existing_output(self):
        self.output.mkdir()
        marker = self.output / "old.txt"
        marker.write_text("old artifact")
        for target, slate in (("unsupported", []), ("agent-plugins", ["unknown"]),
                              ("agent-plugins", ["proseweaving", "proseweaving"]),
                              ("agent-plugins", ["task-witness"])):
            with self.subTest(target=target, slate=slate):
                with self.assertRaises(ValueError):
                    build(self.source, self.output, target, slate, "preview", True)
                self.assertEqual(marker.read_text(), "old artifact")


if __name__ == "__main__":
    unittest.main()
