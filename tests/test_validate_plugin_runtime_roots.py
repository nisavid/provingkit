from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR = REPOSITORY / "scripts/validate_plugin_runtime_roots.py"


class ValidatePluginRuntimeRootsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.repository = Path(self.temporary_directory.name) / "repository"
        # Canonical sources also contain development evals. Stage the runtime
        # roots independently of topology so undeclared files remain visible.
        for plugin in ("versionkeeping", "mergecraft"):
            shutil.copytree(
                REPOSITORY / "plugins" / plugin,
                self.repository / "plugins" / plugin,
                symlinks=True,
                ignore=shutil.ignore_patterns("evals"),
            )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def validate(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), str(self.repository)],
            text=True,
            capture_output=True,
            check=False,
        )

    def assert_rejected(self, message: str) -> None:
        result = self.validate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(message, result.stderr)

    def test_accepts_declared_runtime_roots(self) -> None:
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_legacy_codex_adapter_in_standard_runtime_root(self) -> None:
        legacy = self.repository / "plugins/versionkeeping/.codex-plugin"
        legacy.mkdir()
        (legacy / "plugin.json").write_text("{}\n")

        self.assert_rejected("runtime root inventory drift")

    def test_rejects_development_and_generated_content(self) -> None:
        root = self.repository / "plugins/versionkeeping"
        (root / "evals").mkdir()
        (root / "evals/corpus.json").write_text("{}\n")
        self.assert_rejected("development subtree")
        shutil.rmtree(root / "evals")
        (root / "content-lock.json").write_text("{}\n")
        self.assert_rejected("generated content lock")

    def test_rejects_undeclared_or_cross_root_runtime_files(self) -> None:
        root = self.repository / "plugins/mergecraft"
        (root / "skills/graphite/extra.py").write_text("pass\n")
        self.assert_rejected("runtime root inventory drift")

        (root / "skills/graphite/extra.py").unlink()
        topology = root / "topology.json"
        content = topology.read_text().replace(
            '"skills/graphite/agents/openai.yaml"',
            '"../versionkeeping/skills/graphite/agents/openai.yaml"',
            1,
        )
        topology.write_text(content)
        self.assert_rejected("invalid runtime declaration")

    def test_rejects_omitted_graphite_helper_declaration(self) -> None:
        topology = self.repository / "plugins/mergecraft/topology.json"
        content = json.loads(topology.read_text())
        graphite = next(
            skill for skill in content["skills"] if skill["name"] == "graphite"
        )
        graphite["scripts"] = []
        topology.write_text(json.dumps(content, indent=2) + "\n")
        self.assert_rejected("runtime root inventory drift")

    def assert_loader_required(
        self, plugin: str, skill: str, script: str, expression: str, module: str
    ) -> None:
        relative = f"skills/{skill}/scripts/{module}"
        source = self.repository / "plugins" / plugin / "skills" / skill / "scripts" / script
        content = source.read_text()
        self.assertEqual(content.count(expression), 1)
        source.write_text(content.replace(expression, "unsupported_location", 1))
        self.assert_rejected(
            f"declared runtime dependency is unreachable: {plugin}/{relative}"
        )

    def test_rejects_omitted_worktree_host_trust_loader(self) -> None:
        self.assert_loader_required(
            "versionkeeping", "using-persistent-git-worktrees",
            "validate_worktree_target.py",
            'Path(__file__).resolve().with_name("host_trust.py")', "host_trust.py",
        )

    def test_rejects_omitted_graphite_host_trust_loader(self) -> None:
        self.assert_loader_required(
            "mergecraft", "graphite", "submit_draft_stack.py",
            'Path(__file__).with_name("host_trust.py")', "host_trust.py",
        )

    def test_rejects_omitted_relation_forge_loader(self) -> None:
        self.assert_loader_required(
            "mergecraft", "maintaining-issue-pr-relations", "relation_state.py",
            "Path(__file__).with_name('relation_forge.py')", "relation_forge.py",
        )

    def stage_worktree_loader(
        self, expression: str, *, api: str = "importlib.util.spec_from_file_location",
        imports: str = "import importlib.util\nfrom pathlib import Path\n",
        arguments: str | None = None,
    ) -> Path:
        root = self.repository / "plugins/versionkeeping/skills/using-persistent-git-worktrees/scripts"
        arguments = arguments if arguments is not None else f'f"{{__name__}}.helper", {expression}'
        (root / "validate_worktree_target.py").write_text(
            imports + f"spec = {api}({arguments})\n"
        )
        return root

    def test_accepts_literal_adjacent_loaders_without_prose_edges(self) -> None:
        for expression in (
            'Path(__file__).with_name("host_trust.py")',
            'Path(__file__).resolve().with_name("host_trust.py")',
        ):
            with self.subTest(expression=expression):
                self.stage_worktree_loader(expression)
                result = self.validate()
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_follows_adjacent_loader_transitive_import(self) -> None:
        root = self.stage_worktree_loader('Path(__file__).with_name("host_trust.py")')
        (root / "host_trust.py").write_text("import adjacent_dependency\n")
        (root / "adjacent_dependency.py").write_text("VALUE = 1\n")
        topology = self.repository / "plugins/versionkeeping/topology.json"
        content = json.loads(topology.read_text())
        component = next(item for item in content["skills"] if item["name"] == "using-persistent-git-worktrees")
        component["modules"].append("skills/using-persistent-git-worktrees/scripts/adjacent_dependency.py")
        topology.write_text(json.dumps(content, indent=2) + "\n")
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unsupported_loader_locations_supply_no_edge(self) -> None:
        expressions = (
            'helper_path',
            'Path(__file__).with_name("host_" + "trust.py")',
            'Path(__file__).with_name(f"host_trust.py")',
            'Path(other_file).with_name("host_trust.py")',
            'Path(__file__, "extra").with_name("host_trust.py")',
            'Path(__file__, strict=True).with_name("host_trust.py")',
            'Path(__file__).resolve(strict=True).with_name("host_trust.py")',
            'Path(__file__).resolve(True).with_name("host_trust.py")',
            'Path(__file__).absolute().with_name("host_trust.py")',
            'Path(__file__).with_name(name="host_trust.py")',
            'Path(__file__).with_name("host_trust.py", "extra")',
            'Path(__file__).with_name("../host_trust.py")',
            'Path(__file__).with_name("nested/host_trust.py")',
            'Path(__file__).with_name("nested\\\\host_trust.py")',
            'Path(__file__).with_name("/host_trust.py")',
            'Path(__file__).with_name("")',
            'Path(__file__).with_name(".py")',
            'Path(__file__).with_name("host_trust.txt")',
        )
        for expression in expressions:
            with self.subTest(expression=expression):
                self.stage_worktree_loader(expression)
                self.assert_rejected(
                    "declared runtime dependency is unreachable: versionkeeping/"
                    "skills/using-persistent-git-worktrees/scripts/host_trust.py"
                )

    def test_unsupported_loader_calls_supply_no_edge(self) -> None:
        expression = 'Path(__file__).with_name("host_trust.py")'
        cases = (
            ("other.spec_from_file_location", None, None),
            ("spec_from_file_location", None, None),
            ("importlib.util.spec_from_file_location", '"helper", helper_path', None),
            ("importlib.util.spec_from_file_location", f'"helper", {expression}, extra', None),
            ("importlib.util.spec_from_file_location", f'name="helper", location={expression}', None),
            ("importlib.util.spec_from_file_location", f'*["helper", {expression}]', None),
            ("importlib.util.spec_from_file_location", f'*names, {expression}', None),
            ("importlib.util.spec_from_file_location", f'"helper", {expression}, **options', None),
            ("importlib.util.spec_from_file_location", None, ""),
            ("importlib.util.spec_from_file_location", None, "import importlib.util as loader\nfrom pathlib import Path\n"),
            ("importlib.util.spec_from_file_location", None, "import importlib.util\nfrom pathlib import Path as P\n"),
        )
        for api, arguments, imports in cases:
            with self.subTest(api=api, arguments=arguments, imports=imports):
                options = {} if imports is None else {"imports": imports}
                self.stage_worktree_loader(expression, api=api, arguments=arguments, **options)
                self.assert_rejected(
                    "declared runtime dependency is unreachable: versionkeeping/"
                    "skills/using-persistent-git-worktrees/scripts/host_trust.py"
                )

    def test_rejects_adjacent_target_missing_file_and_declaration(self) -> None:
        root = self.stage_worktree_loader('Path(__file__).with_name("missing.py")')
        (root / "host_trust.py").unlink()
        topology = self.repository / "plugins/versionkeeping/topology.json"
        content = json.loads(topology.read_text())
        component = next(item for item in content["skills"] if item["name"] == "using-persistent-git-worktrees")
        component["modules"] = []
        topology.write_text(json.dumps(content, indent=2) + "\n")
        self.assert_rejected("undeclared adjacent Python dependency")

    def assert_host_trust_declaration_required(
        self, plugin: str, skill: str, module: str = "host_trust.py"
    ) -> None:
        topology = self.repository / "plugins" / plugin / "topology.json"
        content = json.loads(topology.read_text())
        component = next(item for item in content["skills"] if item["name"] == skill)
        component["modules"].remove(f"skills/{skill}/scripts/{module}")
        topology.write_text(json.dumps(content, indent=2) + "\n")
        self.assert_rejected(f"runtime root inventory drift: {plugin}")

    def test_rejects_omitted_worktree_host_trust_declaration(self) -> None:
        self.assert_host_trust_declaration_required(
            "versionkeeping", "using-persistent-git-worktrees"
        )

    def test_rejects_omitted_graphite_host_trust_declaration(self) -> None:
        self.assert_host_trust_declaration_required("mergecraft", "graphite")

    def test_rejects_omitted_publication_host_trust_declaration(self) -> None:
        self.assert_host_trust_declaration_required(
            "versionkeeping",
            "checkpointing-and-publishing-git-work",
            "git_publication/host_trust.py",
        )

    def test_rejects_degenerate_declaration_without_crashing(self) -> None:
        topology = self.repository / "plugins/versionkeeping/topology.json"
        content = topology.read_text().replace(
            '"skills/checkpointing-and-publishing-git-work/SKILL.md"',
            '"."',
            1,
        )
        topology.write_text(content)
        self.assert_rejected("invalid runtime declaration")

    def test_rejects_unknown_component_metadata(self) -> None:
        topology = self.repository / "plugins/mergecraft/topology.json"
        content = topology.read_text().replace(
            '      "name": "writing-reviewable-pr-descriptions",',
            '      "name": "writing-reviewable-pr-descriptions",\n'
            '      "unexpected": "metadata",',
            1,
        )
        topology.write_text(content)
        self.assert_rejected("runtime topology component shape drift")

    def test_rejects_declared_but_unreachable_reference(self) -> None:
        root = self.repository / "plugins/mergecraft"
        relative = (
            "skills/interacting-with-pr-review-feedback/references/"
            "declared-but-unreachable.md"
        )
        (root / relative).write_text("# Unreachable\n")
        topology_path = root / "topology.json"
        topology = json.loads(topology_path.read_text())
        component = next(
            item
            for item in topology["skills"]
            if item["name"] == "interacting-with-pr-review-feedback"
        )
        component["references"].append(relative)
        topology_path.write_text(json.dumps(topology, indent=2) + "\n")

        self.assert_rejected("declared runtime dependency is unreachable")

    def test_rejects_ambiguous_local_python_import(self) -> None:
        root = self.repository / "plugins/mergecraft"
        relative = "skills/graphite/scripts/reviewable_pr_state.py"
        (root / relative).write_text("# Conflicting local module\n")
        topology_path = root / "topology.json"
        topology = json.loads(topology_path.read_text())
        component = next(
            item for item in topology["skills"] if item["name"] == "graphite"
        )
        component["modules"].append(relative)
        topology_path.write_text(json.dumps(topology, indent=2) + "\n")

        self.assert_rejected("ambiguous local Python import")

    def test_repository_release_evidence_is_not_a_runtime_dependency(self) -> None:
        release = self.repository / "release/mergecraft"
        release.mkdir(parents=True)
        (release / "repository-evidence.json").write_text("{}\n")

        result = self.validate()

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_symlinked_plugins_ancestor(self) -> None:
        plugins = self.repository / "plugins"
        target = self.repository / "plugins-real"
        plugins.rename(target)
        plugins.symlink_to(target, target_is_directory=True)
        self.assert_rejected("plugins root must be a real directory")

    def test_rejects_symlinks_and_test_only_files(self) -> None:
        root = self.repository / "plugins/mergecraft/skills/graphite"
        (root / "linked.md").symlink_to("SKILL.md")
        self.assert_rejected("symlink")
        (root / "linked.md").unlink()
        (root / "fixtures").mkdir()
        (root / "fixtures/example.json").write_text("{}\n")
        self.assert_rejected("test-only content")


if __name__ == "__main__":
    unittest.main()
