from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_feedback_response_eval.py"
sys.path.insert(0, str(ROOT / "scripts"))
import validate_feedback_response_evidence as evidence


class PreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed_temporary = tempfile.TemporaryDirectory()
        cls.seed = Path(cls.seed_temporary.name) / "repository"
        cls.seed.mkdir()
        cls.cases = json.loads((ROOT / evidence.MANIFEST).read_text())["evals"]
        cls.inputs = {path: (ROOT / path).read_bytes()
                      for path in evidence.source_paths(ROOT, cls.cases)}
        for path, content in cls.inputs.items():
            target = cls.seed / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            target.chmod(0o755 if (ROOT / path).stat().st_mode & 0o111 else 0o644)
        cls.git(cls.seed, "init", "--quiet")
        cls.git(cls.seed, "add", "--all")
        cls.git(cls.seed, "commit", "--quiet", "-m", "test: freeze preparation inputs")
        cls.revision = cls.git(cls.seed, "rev-parse", "HEAD").decode().strip()

    @classmethod
    def tearDownClass(cls):
        cls.seed_temporary.cleanup()

    @staticmethod
    def git(repository, *arguments):
        return subprocess.run(
            ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
             "-c", "user.name=Preparation Test", "-c", "user.email=preparation@example.invalid",
             "-C", str(repository), *arguments], check=True, capture_output=True,
        ).stdout

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.repository = self.directory / "repository"
        self.git(self.directory, "clone", "--quiet", "--shared", str(self.seed), str(self.repository))
        self.output = self.directory / "prepared"
        self.captures = []

    def prepare(self, revision=None, environment=None):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "prepare", "--repository", str(self.repository),
             "--source-revision", revision or self.revision, "--output-dir", str(self.output)],
            capture_output=True, env=environment, timeout=45,
        )
        capture = {"returncode": result.returncode, "stdout": result.stdout.decode(),
                   "stderr": result.stderr.decode()}
        self.captures.append(capture)
        # Retain the externally observed outcome separately from producer artifacts.
        (self.directory / f"capture-{len(self.captures)}.json").write_text(json.dumps(capture))
        self.assertEqual(result.stderr, b"")
        return result, json.loads(result.stdout)

    def artifact(self, reference):
        path = reference["path"]
        self.assertEqual(Path(path).as_posix(), path)
        self.assertFalse(Path(path).is_absolute())
        self.assertNotIn("..", Path(path).parts)
        content = (self.output / path).read_bytes()
        self.assertEqual(len(content), reference["byte_count"])
        self.assertEqual(hashlib.sha256(content).hexdigest(), reference["sha256"])
        return content

    def verify_record(self, result, outcome):
        self.assertEqual(result.returncode, 0, outcome)
        self.assertEqual(outcome["status"], "complete")
        record = json.loads(self.artifact(outcome["record"]))
        self.assertEqual(record["preparation_id"], outcome["preparation_id"])
        material = {key: value for key, value in record.items() if key != "preparation_id"}
        self.assertEqual(evidence.digest(evidence.canonical(material)), record["preparation_id"])

        def verify_references(value):
            if isinstance(value, dict):
                if set(value) == {"path", "byte_count", "sha256"}:
                    self.artifact(value)
                else:
                    for item in value.values():
                        verify_references(item)
            elif isinstance(value, list):
                for item in value:
                    verify_references(item)

        verify_references(record)
        self.assertEqual(record["source"]["commit"], self.revision)
        self.assertEqual(record["source"]["tree"],
                         self.git(self.repository, "rev-parse", self.revision + "^{tree}").decode().strip())
        self.assertEqual({row["path"] for row in record["source"]["files"]}, set(self.inputs))
        export = self.directory / f"verified-{len(self.captures)}"
        for row in record["source"]["files"]:
            content = self.artifact(row["artifact"])
            self.assertEqual(content, self.inputs[row["path"]])
            self.assertEqual(row["git_blob_id"],
                             hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest())
            target = export / row["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        expected = {(case["id"], variant, repetition) for case in self.cases
                    for variant in ("with_skill", "without_skill") for repetition in (1, 2, 3)}
        self.assertEqual({(row["case_id"], row["variant"], row["repetition"])
                          for row in record["slots"]}, expected)
        self.assertEqual(len(record["slots"]), 78)
        case_map = {case["id"]: case for case in self.cases}
        for row in record["slots"]:
            self.assertEqual(row["state"], "unstarted")
            request = self.artifact(row["request"])
            self.assertEqual(request, evidence.executor_request(
                export, case_map[row["case_id"]], row["variant"]).encode())
            self.assertEqual(set(json.loads(request)), {"prompt", "fixture", "candidate_bundle"})
        grading = json.loads(self.artifact(record["grading_dependencies"]))
        self.assertEqual([case["expected_output"] for case in grading["cases"]],
                         [case_map[index]["expected_output"] for index in range(13)])
        self.assertEqual({row["path"] for row in record["processing"]["files"]},
                         {"scripts/run_feedback_response_eval.py", "scripts/evidence_transport.py",
                          "scripts/validate_feedback_response_evidence.py", "docs/feedback-response-evaluation.md"})
        invocation = self.output / "invocations" / outcome["invocation_id"]
        self.assertEqual(json.loads((invocation / "complete.json").read_bytes()), outcome)
        return record

    def test_prepares_all_slots_from_commit_despite_dirty_and_untracked_inputs(self):
        candidate = self.repository / evidence.CANDIDATE_PATHS[0]
        candidate.write_text("uncommitted candidate poison")
        untracked = self.repository / (evidence.SKILL + "/scripts/untracked.py")
        untracked.write_text("untracked runtime poison")
        result, outcome = self.prepare()
        record = self.verify_record(result, outcome)
        self.assertNotIn(str(untracked.relative_to(self.repository)),
                         {row["path"] for row in record["source"]["files"]})
        self.assertTrue(all((self.output / row["artifact"]["path"]).stat().st_mode & 0o777 == 0o600
                            for row in record["source"]["files"]))

    def test_same_byte_reuse_preserves_artifacts_and_records_distinct_invocation(self):
        first, outcome = self.prepare()
        self.verify_record(first, outcome)
        before = {path: (path.read_bytes(), path.stat().st_ino)
                  for path in self.output.rglob("*") if path.is_file()}
        second, repeated = self.prepare()
        self.verify_record(second, repeated)
        self.assertNotEqual(outcome["invocation_id"], repeated["invocation_id"])
        self.assertEqual(outcome["record"], repeated["record"])
        for path, identity in before.items():
            self.assertEqual((path.read_bytes(), path.stat().st_ino), identity)

    def test_corrupt_artifact_is_not_replaced_and_previous_record_survives(self):
        first, outcome = self.prepare()
        record = self.verify_record(first, outcome)
        path = self.output / record["slots"][0]["request"]["path"]
        path.write_bytes(b"corrupt retained request")
        record_before = (self.output / "preparation.json").read_bytes()
        second, failed = self.prepare()
        self.assertEqual(second.returncode, 1)
        self.assertEqual(failed["status"], "incomplete")
        self.assertEqual(path.read_bytes(), b"corrupt retained request")
        self.assertEqual((self.output / "preparation.json").read_bytes(), record_before)
        third, blocked = self.prepare()
        self.assertEqual(third.returncode, 1)
        self.assertIn("earlier invocation", blocked["reason"])

    def test_different_record_collision_preserves_existing_bytes(self):
        self.output.mkdir()
        (self.output / "preparation.json").write_bytes(b"earlier record")
        result, outcome = self.prepare()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(outcome["status"], "indeterminate")
        self.assertEqual((self.output / "preparation.json").read_bytes(), b"earlier record")
        self.assertTrue(list((self.output / "artifacts").iterdir()))

    def test_reuse_rejects_public_artifact_permissions_without_repair(self):
        result, outcome = self.prepare()
        record = self.verify_record(result, outcome)
        reference = record["slots"][0]["request"]
        path = self.output / reference["path"]
        before = path.read_bytes()
        path.chmod(0o644)
        repeated, failed = self.prepare()
        self.assertEqual(repeated.returncode, 1)
        self.assertEqual(failed["status"], "incomplete")
        self.assertIn("permissions", failed["reason"])
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(path.stat().st_mode & 0o777, 0o644)

    def test_committed_selected_symlink_fails_before_publication(self):
        target = self.repository / evidence.CANDIDATE_PATHS[0]
        target.unlink()
        target.symlink_to("/etc/passwd")
        self.git(self.repository, "add", "--all")
        self.git(self.repository, "commit", "--quiet", "-m", "test: unsafe source")
        revision = self.git(self.repository, "rev-parse", "HEAD").decode().strip()
        result, outcome = self.prepare(revision)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(outcome["status"], "incomplete")
        self.assertFalse(self.output.exists())

    def test_export_ignore_cannot_silently_narrow_the_committed_inventory(self):
        (self.repository / ".gitattributes").write_text(evidence.CANDIDATE_PATHS[0] + " export-ignore\n")
        self.git(self.repository, "add", "--all")
        self.git(self.repository, "commit", "--quiet", "-m", "test: omitted export")
        revision = self.git(self.repository, "rev-parse", "HEAD").decode().strip()
        result, outcome = self.prepare(revision)
        self.assertEqual(result.returncode, 1)
        self.assertIn("inventory is incomplete", outcome["reason"])
        self.assertFalse(self.output.exists())

    def test_final_record_visibility_does_not_override_observed_sync_failure(self):
        injection = self.directory / "injection"
        injection.mkdir()
        (injection / "sitecustomize.py").write_text(
            "import os\nfrom pathlib import Path\n"
            "original = os.fsync\nfired = False\n"
            "def fail_once(descriptor):\n"
            "    global fired\n"
            "    if not fired and Path(os.environ['TEST_VISIBLE_RECORD']).exists():\n"
            "        fired = True\n"
            "        raise OSError('injected sync failure after record visibility')\n"
            "    return original(descriptor)\n"
            "os.fsync = fail_once\n"
        )
        environment = {**os.environ, "PYTHONPATH": str(injection),
                       "TEST_VISIBLE_RECORD": str(self.output / "preparation.json")}
        result, outcome = self.prepare(environment=environment)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(outcome["status"], "indeterminate")
        record = json.loads(self.artifact(outcome["record"]))
        for row in record["source"]["files"]:
            self.artifact(row["artifact"])
        self.assertTrue((self.output / "invocations" / outcome["invocation_id"] / "failed.json").exists())
        repeated, blocked = self.prepare()
        self.assertEqual(repeated.returncode, 1)
        self.assertIn("earlier invocation", blocked["reason"])

    def test_no_model_or_forge_executable_is_invoked(self):
        bin_directory = self.directory / "bin"
        bin_directory.mkdir()
        marker = self.directory / "unexpected-execution"
        for name in ("gh", "codex", "claude"):
            command = bin_directory / name
            command.write_text(f"#!/bin/sh\n: > '{marker}'\nexit 99\n")
            command.chmod(0o755)
        environment = {**os.environ, "PATH": str(bin_directory) + os.pathsep + os.environ["PATH"]}
        result, outcome = self.prepare(environment=environment)
        self.verify_record(result, outcome)
        self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
