from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "scripts" / "validate_praxis.py"
PLUGIN_RELATIVE = Path("plugins/praxis")
LOCK_RELATIVE = Path("release/plugin-content-locks/praxis.json")
SKILL_RELATIVE = PLUGIN_RELATIVE / "skills" / "aeon-bell"
RUNTIME_RELATIVE = SKILL_RELATIVE / "scripts" / "aeon_bell.py"
ADAPTER_RELATIVE = SKILL_RELATIVE / "scripts" / "codex_status.py"
BINDING_RELATIVE = SKILL_RELATIVE / "scripts" / "monitor_binding.js"
PUBLIC_TEST_RELATIVE = Path("tests/test_aeon_bell.py")
ADAPTER_TEST_RELATIVE = Path("tests/test_aeon_bell_codex_status.py")
BINDING_TEST_RELATIVE = Path("tests/test_aeon_bell_binding.py")
EVAL_CORPUS_RELATIVE = Path("evals/praxis/aeon-bell.json")
SCENARIO_CORPUS_RELATIVE = Path("evals/praxis/corpus.json")
EVAL_CORPORA_RELATIVE = (EVAL_CORPUS_RELATIVE, SCENARIO_CORPUS_RELATIVE)

# PyYAML is a test dependency, as for the sibling validator suites: a missing
# module fails this module loudly instead of skipping every contract check.
import yaml  # noqa: E402,F401

# Every fixture below is synthetic.  The Aeon Bell skill, its engine and status
# adapter scripts, both public test modules, and the eval corpus are authored
# independently; these stand-ins exercise only the validator's source contract
# and never stand for the real equipment or its behavioral evidence.
SYNTHETIC_SKILL = """---
name: aeon-bell
description: Synthetic validator fixture for shared gate observation, task registration, and conditional dispatch.
---

# Aeon Bell (synthetic fixture)

This body is a validator test fixture, not the Praxis skill. It links the
[runtime script](scripts/aeon_bell.py), the [status adapter](scripts/codex_status.py),
and the [observation notes](references/observation.md).
"""
SYNTHETIC_REFERENCE = "# Observation notes (synthetic fixture)\n\nPlaceholder reference text.\n"
SYNTHETIC_RUNTIME = '''"""Synthetic validator fixture; not the Aeon Bell runtime."""

import sys


def main(argv: list[str]) -> int:
    print("synthetic fixture", argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
'''
SYNTHETIC_ADAPTER = '''"""Synthetic validator fixture; not the Aeon Bell Codex status adapter."""

import sys


def main(argv: list[str]) -> int:
    print("synthetic adapter fixture", argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
'''
SYNTHETIC_BINDING = '''(function () {
  "use strict";
  return Object.freeze({createStructuredMonitorBinding: function () { return {}; }});
}())
'''
SYNTHETIC_PUBLIC_TEST = '''"""Synthetic validator fixture; not the Aeon Bell test suite."""

import unittest


class SyntheticFixtureTests(unittest.TestCase):
    def test_fixture(self) -> None:
        self.assertTrue(True)
'''
SYNTHETIC_ADAPTER_TEST = '''"""Synthetic validator fixture; not the Aeon Bell adapter test suite."""

import unittest


class SyntheticAdapterFixtureTests(unittest.TestCase):
    def test_fixture(self) -> None:
        self.assertTrue(True)
'''
SYNTHETIC_BINDING_TEST = '''"""Synthetic validator fixture; not the Aeon Bell binding test suite."""

import unittest


class SyntheticBindingFixtureTests(unittest.TestCase):
    def test_fixture(self) -> None:
        self.assertTrue(True)
'''
SYNTHETIC_EVAL_CORPUS = {
    "note": "synthetic validator fixture; not the Aeon Bell eval corpus",
    "cases": [{"id": "synthetic-1"}],
}
# The raw control-plane scenario definition is a locked source input like the
# application-evidence corpus.  It declares a scenario; it carries no executed
# model run, grade, or gate result, and the validator pins its bytes only.
SYNTHETIC_SCENARIO_CORPUS = {
    "note": "synthetic validator fixture; not the Praxis control-plane scenario definition",
    "version": 1,
    "scenarios": [{"id": "synthetic-scenario-1"}],
}


class ValidatePraxisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name).resolve() / "repo"
        self.plugin = self.repo / PLUGIN_RELATIVE
        shutil.copytree(REPO_ROOT / PLUGIN_RELATIVE, self.plugin)
        # Once the real Aeon Bell skill lands, the checked-in tree carries it;
        # the fixture always exercises the validator against the synthetic stand-in.
        shutil.rmtree(self.plugin / "skills", ignore_errors=True)
        self.install_synthetic_skill()
        (self.repo / LOCK_RELATIVE).parent.mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def install_synthetic_skill(self) -> None:
        skill = self.repo / SKILL_RELATIVE
        (skill / "scripts").mkdir(parents=True)
        (skill / "references").mkdir()
        (skill / "SKILL.md").write_text(SYNTHETIC_SKILL, encoding="utf-8")
        (skill / "references" / "observation.md").write_text(
            SYNTHETIC_REFERENCE, encoding="utf-8"
        )
        runtime = self.repo / RUNTIME_RELATIVE
        runtime.write_text(SYNTHETIC_RUNTIME, encoding="utf-8")
        adapter = self.repo / ADAPTER_RELATIVE
        adapter.write_text(SYNTHETIC_ADAPTER, encoding="utf-8")
        (self.repo / BINDING_RELATIVE).write_text(SYNTHETIC_BINDING, encoding="utf-8")
        public_test = self.repo / PUBLIC_TEST_RELATIVE
        public_test.parent.mkdir(parents=True)
        public_test.write_text(SYNTHETIC_PUBLIC_TEST, encoding="utf-8")
        (self.repo / ADAPTER_TEST_RELATIVE).write_text(
            SYNTHETIC_ADAPTER_TEST, encoding="utf-8"
        )
        (self.repo / BINDING_TEST_RELATIVE).write_text(
            SYNTHETIC_BINDING_TEST, encoding="utf-8"
        )
        corpus = self.repo / EVAL_CORPUS_RELATIVE
        corpus.parent.mkdir(parents=True)
        corpus.write_text(
            json.dumps(SYNTHETIC_EVAL_CORPUS, indent=2) + "\n", encoding="utf-8"
        )
        (self.repo / SCENARIO_CORPUS_RELATIVE).write_text(
            json.dumps(SYNTHETIC_SCENARIO_CORPUS, indent=2) + "\n", encoding="utf-8"
        )
        for path in self.repo.rglob("*"):
            if path.is_file():
                path.chmod(0o755 if path == runtime else 0o644)
            elif path.is_dir():
                path.chmod(0o755)

    def validate(self, *arguments: str, repo: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), *arguments, str(repo or self.repo)],
            text=True,
            capture_output=True,
            check=False,
        )

    def write_lock(self) -> None:
        result = self.validate("--write-content-lock")
        self.assertEqual(result.returncode, 0, result.stderr)

    def assert_rejected(self, expected: str) -> None:
        result = self.validate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def lock(self) -> dict:
        return json.loads((self.repo / LOCK_RELATIVE).read_text(encoding="utf-8"))

    def test_scaffold_without_the_skill_reports_the_missing_roster(self) -> None:
        shutil.rmtree(self.plugin / "skills")

        result = self.validate("--write-content-lock")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("direct-child skill inventory drift", result.stderr)
        self.assertIn("aeon-bell", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse((self.repo / LOCK_RELATIVE).exists())

    def test_checked_in_candidate_passes_validation_against_its_content_lock(self) -> None:
        # The checked-in tree is a complete locked candidate: the Aeon Bell
        # skill, both runtime scripts, both public test modules, both eval
        # corpora, and the generated lock are all present.  The validator must
        # pass outright.  A fail-closed message here means a locked input
        # drifted or the lock is stale; the release owner regenerates the lock
        # through --write-content-lock, and this test never tolerates it.
        result = self.validate(repo=REPO_ROOT)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout, "Praxis contract validation passed\n")
        self.assertTrue((REPO_ROOT / LOCK_RELATIVE).is_file())

    def test_checked_in_eval_corpus_inventory_is_the_closed_two_file_set(self) -> None:
        # The validator's closed corpus inventory names exactly the checked-in
        # files under evals/praxis: the application-evidence corpus and the raw
        # control-plane scenario definition.  Neither is executed here.
        observed = sorted(
            path.relative_to(REPO_ROOT).as_posix()
            for path in (REPO_ROOT / "evals" / "praxis").iterdir()
        )
        self.assertEqual(
            observed, sorted(relative.as_posix() for relative in EVAL_CORPORA_RELATIVE)
        )
        result = self.validate(repo=REPO_ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn("eval corpus inventory drift", result.stderr)
        self.assertNotIn("eval corpus is missing", result.stderr)

    def test_validation_requires_the_generated_content_lock(self) -> None:
        self.assert_rejected("content lock is missing")

    def test_write_content_lock_then_validate_accepts_the_synthetic_fixture(self) -> None:
        result = self.validate("--write-content-lock")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "Praxis content lock updated\nPraxis contract validation passed\n",
        )
        self.assertTrue((self.repo / LOCK_RELATIVE).is_file())
        verification = self.validate()
        self.assertEqual(verification.returncode, 0, verification.stderr)
        self.assertEqual(verification.stdout, "Praxis contract validation passed\n")

    def test_lock_binds_plugin_bytes_public_tests_and_eval_corpus(self) -> None:
        self.write_lock()
        lock = self.lock()

        self.assertEqual(
            set(lock),
            {"algorithm", "contract", "files", "plugin_root", "schema_version"},
        )
        self.assertEqual(lock["contract"], "praxis-content-lock-v1")
        self.assertEqual(lock["schema_version"], 1)
        self.assertEqual(lock["algorithm"], "sha256")
        self.assertEqual(lock["plugin_root"], "plugins/praxis")
        files = lock["files"]
        self.assertIn("plugins/praxis/plugin.json", files)
        self.assertIn("plugins/praxis/.claude-plugin/plugin.json", files)
        self.assertIn("plugins/praxis/topology.json", files)
        self.assertIn("plugins/praxis/skills/aeon-bell/SKILL.md", files)
        self.assertIn(RUNTIME_RELATIVE.as_posix(), files)
        self.assertIn(ADAPTER_RELATIVE.as_posix(), files)
        self.assertIn(BINDING_RELATIVE.as_posix(), files)
        self.assertIn(PUBLIC_TEST_RELATIVE.as_posix(), files)
        self.assertIn(ADAPTER_TEST_RELATIVE.as_posix(), files)
        self.assertIn(BINDING_TEST_RELATIVE.as_posix(), files)
        self.assertIn(EVAL_CORPUS_RELATIVE.as_posix(), files)
        self.assertIn(SCENARIO_CORPUS_RELATIVE.as_posix(), files)
        self.assertEqual(
            {relative for relative in files if relative.startswith("evals/praxis/")},
            {relative.as_posix() for relative in EVAL_CORPORA_RELATIVE},
        )
        self.assertNotIn(LOCK_RELATIVE.as_posix(), files)
        self.assertEqual(list(files), sorted(files))
        for relative, entry in files.items():
            with self.subTest(relative=relative):
                self.assertEqual(set(entry), {"mode", "sha256"})
                self.assertRegex(entry["sha256"], r"\A[0-9a-f]{64}\Z")
                self.assertIn(entry["mode"], (0o644, 0o755))
        self.assertEqual(files[RUNTIME_RELATIVE.as_posix()]["mode"], 0o755)
        self.assertEqual(files[ADAPTER_RELATIVE.as_posix()]["mode"], 0o644)
        self.assertEqual(files[BINDING_RELATIVE.as_posix()]["mode"], 0o644)

    def test_lock_regeneration_is_byte_reproducible(self) -> None:
        self.write_lock()
        first = (self.repo / LOCK_RELATIVE).read_bytes()
        self.write_lock()

        self.assertEqual((self.repo / LOCK_RELATIVE).read_bytes(), first)
        self.assertEqual(
            first,
            (json.dumps(self.lock(), indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )

    def test_rejects_locked_input_mutation_without_lock_refresh(self) -> None:
        self.write_lock()
        pristine = {
            relative: (self.repo / relative).read_bytes()
            for relative in (
                SKILL_RELATIVE / "SKILL.md",
                RUNTIME_RELATIVE,
                ADAPTER_RELATIVE,
                BINDING_RELATIVE,
                PUBLIC_TEST_RELATIVE,
                ADAPTER_TEST_RELATIVE,
                BINDING_TEST_RELATIVE,
                EVAL_CORPUS_RELATIVE,
                SCENARIO_CORPUS_RELATIVE,
                PLUGIN_RELATIVE / "README.md",
            )
        }
        for relative, original in pristine.items():
            with self.subTest(relative=relative.as_posix()):
                path = self.repo / relative
                if relative == EVAL_CORPUS_RELATIVE:
                    mutated = json.loads(original)
                    mutated["cases"].append({"id": "synthetic-2"})
                    path.write_text(json.dumps(mutated, indent=2) + "\n", encoding="utf-8")
                elif relative == SCENARIO_CORPUS_RELATIVE:
                    mutated = json.loads(original)
                    mutated["scenarios"].append({"id": "synthetic-scenario-2"})
                    path.write_text(json.dumps(mutated, indent=2) + "\n", encoding="utf-8")
                elif relative == BINDING_RELATIVE:
                    path.write_bytes(
                        original.replace(b'  "use strict";\n', b'  "use strict";\n  // lock mutation\n', 1)
                    )
                else:
                    path.write_bytes(original + b"\n# mutated after locking\n")
                self.assert_rejected("content lock mismatch")
                path.write_bytes(original)
        self.assertEqual(self.validate().returncode, 0)

    def test_rejects_runtime_mode_drift_without_lock_refresh(self) -> None:
        self.write_lock()
        (self.repo / RUNTIME_RELATIVE).chmod(0o644)
        self.assert_rejected("content lock mismatch")

    def test_rejects_missing_public_test_and_eval_corpus(self) -> None:
        self.write_lock()
        for relative, expected in (
            (PUBLIC_TEST_RELATIVE, "public test is missing"),
            (ADAPTER_TEST_RELATIVE, "public test is missing"),
            (BINDING_TEST_RELATIVE, "public test is missing"),
            (EVAL_CORPUS_RELATIVE, "eval corpus is missing"),
            (SCENARIO_CORPUS_RELATIVE, "eval corpus is missing"),
        ):
            with self.subTest(relative=relative.as_posix()):
                path = self.repo / relative
                original = path.read_bytes()
                path.unlink()
                self.assert_rejected(expected)
                path.write_bytes(original)

    def test_rejects_unreferenced_eval_corpus_file(self) -> None:
        self.write_lock()
        (self.repo / EVAL_CORPUS_RELATIVE).with_name("orphan.json").write_text("{}\n")
        self.assert_rejected("eval corpus inventory drift")

    def test_rejects_eval_corpus_that_is_not_a_nonempty_object(self) -> None:
        self.write_lock()
        for relative in EVAL_CORPORA_RELATIVE:
            path = self.repo / relative
            original = path.read_bytes()
            for content in ("[]\n", "{}\n", "not json\n"):
                with self.subTest(relative=relative.as_posix(), content=content.strip()):
                    path.write_text(content, encoding="utf-8")
                    self.assert_rejected("eval corpus")
            path.write_bytes(original)
        self.assertEqual(self.validate().returncode, 0)

    def test_scenario_definition_is_locked_as_source_without_evidence_fields(self) -> None:
        # A raw scenario definition carries no observed model result.  The lock
        # pins its bytes; the validator neither executes the scenario nor
        # requires any status, grade, or gate field in it.
        self.write_lock()
        lock = self.lock()
        locked_scenario_definition = json.loads(
            (self.repo / SCENARIO_CORPUS_RELATIVE).read_text(encoding="utf-8")
        )
        self.assertEqual(set(locked_scenario_definition), {"note", "version", "scenarios"})
        for scenario in locked_scenario_definition["scenarios"]:
            self.assertFalse(
                {"status", "observed_invoke", "passed", "grade"} & set(scenario)
            )
        self.assertEqual(
            lock["files"][SCENARIO_CORPUS_RELATIVE.as_posix()]["mode"], 0o644
        )
        self.assertEqual(self.validate().returncode, 0)

    def test_rejects_public_test_that_does_not_parse(self) -> None:
        self.write_lock()
        for relative in (PUBLIC_TEST_RELATIVE, ADAPTER_TEST_RELATIVE, BINDING_TEST_RELATIVE):
            with self.subTest(relative=relative.as_posix()):
                path = self.repo / relative
                original = path.read_bytes()
                path.write_text("def (:\n", encoding="utf-8")
                self.assert_rejected("public test does not parse")
                path.write_bytes(original)

    def test_rejects_runtime_script_that_is_missing_or_does_not_parse(self) -> None:
        for relative in (RUNTIME_RELATIVE, ADAPTER_RELATIVE):
            with self.subTest(relative=relative.as_posix()):
                script = self.repo / relative
                original = script.read_bytes()
                script.write_text("def (:\n", encoding="utf-8")
                self.assert_rejected("runtime script does not parse")
                script.unlink()
                self.assert_rejected("runtime script is missing")
                script.write_bytes(original)
                script.chmod(0o755)

    def test_javascript_binding_is_governed_without_python_ast_parsing(self) -> None:
        binding = self.repo / BINDING_RELATIVE
        self.write_lock()
        original = binding.read_bytes()
        binding.write_text(
            '(function () {\n  "use strict";\n  return require("fs");\n}())\n',
            encoding="utf-8",
        )
        self.assert_rejected("JavaScript runtime resource uses a forbidden ambient API")
        binding.write_bytes(b"\xff")
        self.assert_rejected("JavaScript runtime resource is not UTF-8 text")
        binding.unlink()
        self.assert_rejected("JavaScript runtime resource is missing")
        binding.write_bytes(original)
        binding.chmod(0o600)
        self.assert_rejected("file mode is not portable")

    def test_source_identity_binds_adapter_evidence_without_running_it(self) -> None:
        # The lock pins the adapter script and its public test module as source
        # bytes.  Changing either without refreshing the lock is rejected, while
        # nothing here executes the adapter or its tests.
        self.write_lock()
        lock = self.lock()
        adapter = self.repo / ADAPTER_RELATIVE
        adapter_test = self.repo / ADAPTER_TEST_RELATIVE
        adapter.write_text(
            SYNTHETIC_ADAPTER.replace("synthetic adapter fixture", "changed"),
            encoding="utf-8",
        )
        self.assert_rejected("content lock mismatch")
        self.write_lock()
        self.assertNotEqual(
            self.lock()["files"][ADAPTER_RELATIVE.as_posix()]["sha256"],
            lock["files"][ADAPTER_RELATIVE.as_posix()]["sha256"],
        )
        adapter_test.write_text(
            SYNTHETIC_ADAPTER_TEST + "\n# adapter expectations changed\n",
            encoding="utf-8",
        )
        self.assert_rejected("content lock mismatch")
        adapter_test.unlink()
        result = self.validate("--write-content-lock")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public test is missing", result.stderr)
        self.assertIn(ADAPTER_TEST_RELATIVE.as_posix(), result.stderr)

    def test_rejects_roster_drift_in_skills_and_topology(self) -> None:
        extra = self.plugin / "skills" / "second-bell"
        extra.mkdir()
        (extra / "SKILL.md").write_text(
            "---\nname: second-bell\ndescription: Extra.\n---\n\nBody.\n", encoding="utf-8"
        )
        self.assert_rejected("direct-child skill inventory drift")
        shutil.rmtree(extra)

        topology_path = self.plugin / "topology.json"
        topology = json.loads(topology_path.read_text(encoding="utf-8"))
        topology["skills"]["second-bell"] = {"owns": ["extra"], "may_call": []}
        topology_path.write_text(json.dumps(topology, indent=2) + "\n", encoding="utf-8")
        self.assert_rejected("topology roster drift")

    def test_rejects_topology_shape_drift(self) -> None:
        topology_path = self.plugin / "topology.json"
        topology = json.loads(topology_path.read_text(encoding="utf-8"))
        cases = {
            "schema_version": ({**topology, "schema_version": 2}, "topology schema_version drift"),
            "empty owners": (
                {**topology, "skills": {"aeon-bell": {"owns": [], "may_call": []}}},
                "topology owners must be nonempty strings",
            ),
            "self call": (
                {
                    **topology,
                    "skills": {
                        "aeon-bell": {
                            "owns": ["x"],
                            "may_call": [{"skill": "aeon-bell", "when": "never"}],
                        }
                    },
                },
                "topology self-call is forbidden",
            ),
            "unknown key": ({**topology, "extra": True}, "topology keys drift"),
            "resource metadata on node": (
                {
                    **topology,
                    "skills": {
                        "aeon-bell": {
                            "owns": ["x"],
                            "may_call": [],
                            "entrypoint": "skills/aeon-bell/SKILL.md",
                            "scripts": ["skills/aeon-bell/scripts/aeon_bell.py"],
                        }
                    },
                },
                "topology node keys drift",
            ),
        }
        for label, (document, expected) in cases.items():
            with self.subTest(label=label):
                topology_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
                self.assert_rejected(expected)

    def test_rejects_skill_frontmatter_drift(self) -> None:
        skill = self.repo / SKILL_RELATIVE / "SKILL.md"
        cases = {
            "name": (
                SYNTHETIC_SKILL.replace("name: aeon-bell", "name: other-bell", 1),
                "frontmatter name drift",
            ),
            "missing description": (
                SYNTHETIC_SKILL.replace("description: Synthetic", "summary: Synthetic", 1),
                "frontmatter keys drift",
            ),
            "no frontmatter": ("# No frontmatter\n\nBody.\n", "opening and closing frontmatter"),
            "adapter syntax in body": (
                SYNTHETIC_SKILL + "\nInvoke $praxis:aeon-bell again.\n",
                "adapter-qualified syntax",
            ),
        }
        for label, (content, expected) in cases.items():
            with self.subTest(label=label):
                skill.write_text(content, encoding="utf-8")
                self.assert_rejected(expected)

    def test_rejects_skill_resource_link_that_escapes_or_is_missing(self) -> None:
        skill = self.repo / SKILL_RELATIVE / "SKILL.md"
        for destination, expected in (
            ("references/missing.md", "Agent Skill resource is missing"),
            (
                "../../../../tests/test_aeon_bell.py",
                "Agent Skill resource escapes plugin root",
            ),
        ):
            with self.subTest(destination=destination):
                skill.write_text(
                    SYNTHETIC_SKILL + f"\nSee [more]({destination}).\n", encoding="utf-8"
                )
                self.assert_rejected(expected)

    def test_rejects_claude_projection_and_manifest_identity_drift(self) -> None:
        claude_path = self.plugin / ".claude-plugin" / "plugin.json"
        canonical_path = self.plugin / "plugin.json"
        claude = json.loads(claude_path.read_text(encoding="utf-8"))
        canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
        cases = (
            (claude_path, {**claude, "description": "Praxis: something else."}, "Claude manifest projection drift: description"),
            (claude_path, {**claude, "displayName": "Practice"}, "Claude displayName drift"),
            (claude_path, {**claude, "version": "1.0.1"}, "Claude manifest projection drift: version"),
            (canonical_path, {**canonical, "version": "1.0.1"}, "canonical manifest version drift"),
            (canonical_path, {**canonical, "name": "provingkit"}, "canonical manifest name drift"),
            (canonical_path, {**canonical, "description": "Something else."}, "canonical manifest description prefix drift"),
        )
        for path, document, expected in cases:
            with self.subTest(expected=expected):
                original = path.read_text(encoding="utf-8")
                path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
                self.assert_rejected(expected)
                path.write_text(original, encoding="utf-8")

    def test_rejects_codex_default_prompt_namespace_drift(self) -> None:
        canonical_path = self.plugin / "plugin.json"
        canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
        interface = canonical["extensions"]["com.openai"]["interface"]
        for prompts in (["Use $praxis:other-bell here."], [], ["Use aeon-bell without a namespace."]):
            with self.subTest(prompts=prompts):
                interface["defaultPrompt"] = prompts
                canonical_path.write_text(json.dumps(canonical, indent=2) + "\n", encoding="utf-8")
                self.assert_rejected("Codex default prompts drift")

    def test_optional_codex_skill_adapter_is_validated_when_present(self) -> None:
        adapter = self.repo / SKILL_RELATIVE / "agents" / "openai.yaml"
        adapter.parent.mkdir()
        adapter.write_text(
            "interface:\n"
            '  display_name: "Aeon Bell"\n'
            '  short_description: "Synthetic fixture."\n'
            '  default_prompt: "Use $praxis:aeon-bell for the shared gate."\n',
            encoding="utf-8",
        )
        adapter.chmod(0o644)
        self.write_lock()
        self.assertEqual(self.validate().returncode, 0)
        adapter.write_text(
            "interface:\n"
            '  display_name: "Aeon Bell"\n'
            '  short_description: "Synthetic fixture."\n'
            '  default_prompt: "Use $proseweaving:writing-for-people instead."\n',
            encoding="utf-8",
        )
        self.assert_rejected("default prompt namespace drift")

    def test_rejects_symlinks_special_entries_and_generated_python_state(self) -> None:
        self.write_lock()
        link = self.plugin / "skills" / "aeon-bell" / "LICENSE.link"
        os.symlink(self.plugin / "LICENSE", link)
        self.assert_rejected("plugin inventory contains a symlink")
        link.unlink()
        cache = self.plugin / "skills" / "aeon-bell" / "scripts" / "__pycache__"
        cache.mkdir()
        (cache / "aeon_bell.cpython-313.pyc").write_bytes(b"\x00")
        self.assert_rejected("generated Python state")
        shutil.rmtree(cache)
        (self.plugin / "NOTES.md").write_text("stray\n", encoding="utf-8")
        self.assert_rejected("component inventory drift")

    def test_rejects_non_portable_file_modes(self) -> None:
        self.write_lock()
        (self.repo / SKILL_RELATIVE / "SKILL.md").chmod(0o600)
        self.assert_rejected("file mode is not portable")

    def test_rejects_portability_and_credential_leaks(self) -> None:
        self.write_lock()
        runtime = self.repo / RUNTIME_RELATIVE
        original = runtime.read_text(encoding="utf-8")
        for leak in (
            'STATE = "/Users/someone/.aeon-bell"\n',
            'STATE = "/home/someone/.aeon-bell"\n',
            'TOKEN = "api_key=abc"\n',
            'HEADER = "Authorization: Bearer abc"\n',
        ):
            with self.subTest(leak=leak.strip()):
                runtime.write_text(original + leak, encoding="utf-8")
                self.assert_rejected("portability or credential leak")
        runtime.write_text(original, encoding="utf-8")

    def test_public_tests_keep_portability_checks_but_may_carry_redaction_fixtures(
        self,
    ) -> None:
        # Public test modules prove the adapter redacts credential-shaped input,
        # so they legitimately contain such fixtures and Codex protocol literals.
        # Portability leaks in them are still rejected.
        self.write_lock()
        adapter_test = self.repo / ADAPTER_TEST_RELATIVE
        original = adapter_test.read_text(encoding="utf-8")
        adapter_test.write_text(
            original
            + 'AUTH = {"OPENAI_API_KEY": None, "type": "apiKey"}\n'
            + 'HEADER = "Authorization: Bearer synthetic"\n',
            encoding="utf-8",
        )
        self.write_lock()
        self.assertEqual(self.validate().returncode, 0)
        adapter_test.write_text(
            original + 'CODEX_HOME = "/home/someone/.codex"\n', encoding="utf-8"
        )
        self.assert_rejected("portability or credential leak")
        adapter_test.write_text(original, encoding="utf-8")

    def test_rejects_duplicate_keys_in_every_json_contract(self) -> None:
        self.write_lock()
        corpus_note = json.dumps("note") + ": " + json.dumps(SYNTHETIC_EVAL_CORPUS["note"]) + ","
        scenario_note = (
            json.dumps("note") + ": " + json.dumps(SYNTHETIC_SCENARIO_CORPUS["note"]) + ","
        )
        cases = (
            (self.plugin / "topology.json", '"schema_version": 1,'),
            (self.plugin / "plugin.json", '"name": "praxis",'),
            (self.plugin / ".claude-plugin" / "plugin.json", '"name": "praxis",'),
            (self.repo / EVAL_CORPUS_RELATIVE, corpus_note),
            (self.repo / SCENARIO_CORPUS_RELATIVE, scenario_note),
            (self.repo / LOCK_RELATIVE, '"algorithm": "sha256",'),
        )
        for path, fragment in cases:
            with self.subTest(path=path.name):
                content = path.read_text(encoding="utf-8")
                self.assertIn(fragment, content)
                path.write_text(
                    content.replace(fragment, fragment + " " + fragment, 1),
                    encoding="utf-8",
                )
                try:
                    self.assert_rejected("duplicate key")
                finally:
                    path.write_text(content, encoding="utf-8")

    def test_rejects_lock_edited_by_hand(self) -> None:
        self.write_lock()
        lock_path = self.repo / LOCK_RELATIVE
        lock = self.lock()
        lock["files"]["plugins/praxis/plugin.json"]["sha256"] = "0" * 64
        lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self.assert_rejected("content lock mismatch")
        lock = self.lock()
        del lock["files"][PUBLIC_TEST_RELATIVE.as_posix()]
        lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self.assert_rejected("content lock inventory drift")
        self.write_lock()
        lock = self.lock()
        del lock["files"][SCENARIO_CORPUS_RELATIVE.as_posix()]
        lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        self.assert_rejected("content lock inventory drift")
        self.write_lock()
        lock_path.write_text(json.dumps(self.lock()) + "\n", encoding="utf-8")
        self.assert_rejected("content lock is not canonical")

    def test_write_content_lock_refuses_to_write_while_inputs_are_incomplete(self) -> None:
        self.write_lock()
        before = (self.repo / LOCK_RELATIVE).read_bytes()
        (self.repo / PUBLIC_TEST_RELATIVE).unlink()

        result = self.validate("--write-content-lock")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public test is missing", result.stderr)
        self.assertEqual((self.repo / LOCK_RELATIVE).read_bytes(), before)
        self.assertFalse(list((self.repo / LOCK_RELATIVE).parent.glob(".*")))

    def test_write_content_lock_never_writes_the_lock_before_its_inputs_exist(self) -> None:
        (self.repo / RUNTIME_RELATIVE).unlink()

        result = self.validate("--write-content-lock")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("runtime script is missing", result.stderr)
        self.assertFalse((self.repo / LOCK_RELATIVE).exists())

    def test_rejects_unknown_flag_and_extra_arguments(self) -> None:
        self.assertEqual(self.validate("--unknown").returncode, 2)
        self.assertEqual(self.validate("extra", "arguments").returncode, 2)


if __name__ == "__main__":
    unittest.main()
