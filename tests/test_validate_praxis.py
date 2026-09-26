"""Praxis source contract tests at the validator's public CLI seam."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate_praxis.py"
SKILL = "plugins/praxis/skills/constructing-agent-policies"
LOCK = "release/plugin-content-locks/praxis.json"
TESTS = ("tests/test_policy_eval_runner.py", "tests/test_validate_praxis.py")
RESOURCES = (
    f"{SKILL}/SKILL.md",
    f"{SKILL}/references/policy-design.md",
    f"{SKILL}/references/evaluation.md",
    f"{SKILL}/scripts/policy_eval_runner.py",
    f"{SKILL}/scripts/gh_stub.py",
    f"{SKILL}/agents/openai.yaml",
)


class PraxisContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo"
        shutil.copytree(ROOT / "plugins/praxis", self.repo / "plugins/praxis",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for relative in TESTS:
            target = self.repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        (self.repo / LOCK).parent.mkdir(parents=True)

    def run_validator(self, *flags: str, repo: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(VALIDATOR), *flags, str(repo or self.repo)],
                              capture_output=True, text=True, check=False)

    def write_lock(self) -> None:
        result = self.run_validator("--write-content-lock")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_checked_in_candidate_and_generated_lock_validate(self) -> None:
        result = self.run_validator(repo=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "Praxis contract validation passed\n")

    def test_one_skill_roster_and_real_resources_are_locked(self) -> None:
        self.write_lock()
        lock = json.loads((self.repo / LOCK).read_text())
        self.assertEqual(lock["contract"], "praxis-content-lock-v1")
        self.assertEqual(lock["plugin_root"], "plugins/praxis")
        self.assertEqual(set(lock["files"]) & set(RESOURCES), set(RESOURCES))
        self.assertEqual(set(lock["files"]) & set(TESTS), set(TESTS))
        self.assertFalse(any("aeon-bell" in path for path in lock["files"]))
        self.assertEqual(self.run_validator().returncode, 0)

    def test_missing_required_resource_is_rejected(self) -> None:
        self.write_lock()
        (self.repo / RESOURCES[1]).unlink()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required skill resource is missing", result.stderr)

    def test_missing_public_test_is_rejected(self) -> None:
        self.write_lock()
        (self.repo / TESTS[0]).unlink()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public test is missing", result.stderr)

    def test_extra_skill_is_rejected(self) -> None:
        self.write_lock()
        extra = self.repo / "plugins/praxis/skills/extra/SKILL.md"
        extra.parent.mkdir()
        extra.write_text("---\nname: extra\ndescription: Extra.\n---\n\n# Extra\n")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("direct-child skill inventory drift", result.stderr)

    def test_declared_corpus_directory_is_optional_until_its_contract_lands(self) -> None:
        self.write_lock()
        self.assertEqual(self.run_validator().returncode, 0)
        corpus = self.repo / "evals/praxis/constructing-agent-policies"
        corpus.mkdir(parents=True)
        (corpus / "case.json").write_text('{"scenarios":[]}\n')
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("eval corpus inventory needs declaration", result.stderr)

    def test_lock_rejects_changed_source(self) -> None:
        self.write_lock()
        manifest = self.repo / "plugins/praxis/plugin.json"
        manifest.write_bytes(manifest.read_bytes() + b"\n")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("content lock mismatch", result.stderr)


if __name__ == "__main__":
    unittest.main()

