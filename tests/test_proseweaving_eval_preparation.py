"""Public offline writer-preparation and consumer contracts."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = "scripts/prepare_proseweaving_eval.py"
TOOLS = [
    SCRIPT,
    "scripts/validate_proseweaving.py",
    "scripts/evidence_transport.py",
    "scripts/agent_plugins_standard.py",
    "scripts/member_versions.py",
    "scripts/member_source_stage_cli.py",
    "docs/proseweaving-evaluation-preparation.md",
]
SKILL = "---\nname: writing-for-people\ndescription: Use when comparing a pair for a reader.\n---\n\nExplain the supplied comparison.\n"
EXPECTED_ACTOR = b'{"prompt":"Compare A and B.","fixture":"A costs 3; B costs 5.\\n","candidate_bundle":{"skills/writing-for-people/SKILL.md":"---\\nname: writing-for-people\\ndescription: Use when comparing a pair for a reader.\\n---\\n\\nExplain the supplied comparison.\\n"}}\n'


@unittest.skipUnless(os.name == "posix", "POSIX preparation contract")
class WriterPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        self.output = self.base / "output"
        self.env = {
            **os.environ,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_COUNT": "0",
        }
        for key in list(self.env):
            if key.startswith("GIT_") and key not in {
                "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM",
                "GIT_CONFIG_NOSYSTEM", "GIT_CONFIG_COUNT",
            }:
                self.env.pop(key)
        for path in TOOLS:
            source = ROOT / path
            if source.exists():
                target = self.repo / path
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
        plugin = self.repo / "plugins/proseweaving"
        shutil.copytree(ROOT / "plugins/proseweaving", plugin,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        writer = plugin / "skills/writing-for-people"
        (writer / "SKILL.md").write_text(SKILL)
        shutil.rmtree(writer / "references")
        shutil.rmtree(writer / "evals/fixtures")
        (writer / "evals/fixtures").mkdir()
        cases = []
        for number in range(1, 6):
            name = f"case-{number}.md"
            (writer / "evals/fixtures" / name).write_text("A costs 3; B costs 5.\n")
            cases.append({
                "id": number, "name": f"comparison-{number}",
                "prompt": "Compare A and B." if number == 1 else f"Compare pair {number}.",
                "fixture_paths": [f"evals/fixtures/{name}"],
                "expected_output": "Keep this grading-only sentence private.",
                "expectations": [
                    {"id": "facts", "text": "Use the supplied costs.", "severity": "safety"},
                    {"id": "choice", "text": "Explain the comparison.", "severity": "quality"},
                    {"id": "reader", "text": "Write for the reader.", "severity": "quality"},
                ],
            })
        (writer / "evals/evals.json").write_text(json.dumps({
            "skill_name": "writing-for-people", "evals": cases,
        }) + "\n")
        validated = subprocess.run([
            sys.executable, str(self.repo / "scripts/validate_proseweaving.py"),
            "--write-content-lock", str(self.repo),
        ], env=self.env, capture_output=True)
        self.assertEqual(validated.returncode, 0, validated.stderr.decode())
        self.git("init", "-q")
        self.revision = self.commit()

    def git(self, *arguments):
        result = subprocess.run(
            ["git", "-C", str(self.repo), *arguments],
            env=self.env, capture_output=True, check=True,
        )
        return result.stdout.decode().strip()

    def commit(self):
        self.git("add", ".")
        self.git("-c", "user.name=Fixture", "-c",
                 "user.email=fixture@example.invalid", "commit", "-qm", "fixture")
        return self.git("rev-parse", "HEAD")

    def prepare(self, revision=None, source_repository=None, **options):
        return subprocess.run([
            sys.executable, str(self.repo / SCRIPT), "prepare",
            "--repository", str(source_repository or self.repo),
            "--source-revision", revision or self.revision,
            "--output-dir", str(self.output),
        ], env=self.env, capture_output=True, timeout=30, **options)

    def test_prepares_literal_actor_inputs_and_three_unstarted_repetitions(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual((self.output / "requests/case-001.json").read_bytes(),
                         EXPECTED_ACTOR)
        coordinates = json.loads((self.output / "coordinates.json").read_bytes())
        self.assertEqual(
            [(row["case_id"], row["repetition"], row["state"]) for row in coordinates],
            [(case, repeat, "unstarted")
             for case in [1, 2, 3, 4, 5] for repeat in [1, 2, 3]],
        )
        self.assertEqual(len(list((self.output / "requests").glob("*.json"))), 5)
        self.assertEqual(result.stdout, (self.output / "outcome.json").read_bytes())

    def test_uses_selected_commit_when_worktree_fixture_changes(self):
        fixture = self.repo / "plugins/proseweaving/skills/writing-for-people/evals/fixtures/case-1.md"
        fixture.write_text("A costs 999; B costs 1.\n")
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual((self.output / "requests/case-001.json").read_bytes(),
                         EXPECTED_ACTOR)

    def test_rejects_symlinked_output_parent_without_creating_batch(self):
        outside = self.base / "outside"
        outside.mkdir()
        link = self.base / "link"
        link.symlink_to(outside, target_is_directory=True)
        self.output = link / "batch"
        result = self.prepare()
        self.assertEqual(result.returncode, 2)
        self.assertFalse((outside / "batch").exists())

    def consumer(self):
        if hasattr(self, "consumer_module"):
            return self.consumer_module
        import importlib.util
        spec = importlib.util.spec_from_file_location("writer_preparation_consumer",
                                                     self.repo / SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.consumer_module = module
        return module

    def test_consumer_accepts_complete_retained_batch_and_actual_outcome(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        module = self.consumer()
        prepared = module.verify_preparation(
            self.output, repository=self.repo, source_revision=self.revision,
            stdout=result.stdout, returncode=result.returncode,
        )
        self.assertEqual(prepared["source_revision"], self.revision)
        self.assertEqual(prepared["coordinate_count"], 15)

    def check(self, result, **changes):
        return self.consumer().verify_preparation(
            self.output, repository=self.repo, source_revision=self.revision,
            stdout=changes.get("stdout", result.stdout),
            returncode=changes.get("returncode", result.returncode),
        )

    def test_rejects_executing_method_from_another_revision(self):
        path = self.repo / SCRIPT
        path.write_text(path.read_text() + "\n# uncommitted method change\n")
        result = self.prepare()
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.output.exists())

    def test_rejects_abbreviated_commit_before_output_reservation(self):
        result = self.prepare(self.revision[:12])
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.output.exists())

    def test_rejects_committed_source_symlink(self):
        fixture = self.repo / "plugins/proseweaving/skills/writing-for-people/evals/fixtures/case-1.md"
        fixture.unlink()
        fixture.symlink_to("case-2.md")
        self.revision = self.commit()
        result = self.prepare()
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.output.exists())

    def test_existing_batch_is_not_overwritten(self):
        first = self.prepare()
        self.assertEqual(first.returncode, 0)
        before = {p.relative_to(self.output).as_posix(): p.read_bytes()
                  for p in self.output.rglob("*") if p.is_file()}
        second = self.prepare()
        self.assertEqual(second.returncode, 2)
        after = {p.relative_to(self.output).as_posix(): p.read_bytes()
                 for p in self.output.rglob("*") if p.is_file()}
        self.assertEqual(after, before)

    def test_consumer_rejects_rebound_complete_packet_with_changed_actor(self):
        import hashlib
        result = self.prepare()
        self.assertEqual(result.returncode, 0)
        actor_path = self.output / "requests/case-001.json"
        changed = actor_path.read_bytes().replace(b"Compare A and B.", b"Invent a third option.")
        actor_path.write_bytes(changed)
        preparation_path = self.output / "preparation.json"
        prepared = json.loads(preparation_path.read_bytes())
        for row in prepared["artifacts"]:
            if row["path"] == "requests/case-001.json":
                row["bytes"] = len(changed)
                row["sha256"] = hashlib.sha256(changed).hexdigest()
        raw = json.dumps(prepared, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":")).encode() + b"\n"
        preparation_path.write_bytes(raw)
        outcome_path = self.output / "outcome.json"
        outcome = json.loads(outcome_path.read_bytes())
        outcome["preparation"]["bytes"] = len(raw)
        outcome["preparation"]["sha256"] = hashlib.sha256(raw).hexdigest()
        observed = json.dumps(outcome, sort_keys=True, ensure_ascii=False,
                              separators=(",", ":")).encode() + b"\n"
        outcome_path.write_bytes(observed)
        module = self.consumer()
        with self.assertRaises(module.PreparationError):
            module.verify_preparation(
                self.output, repository=self.repo, source_revision=self.revision,
                stdout=observed, returncode=0,
            )

    def test_consumer_rejects_extra_empty_directory(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0)
        (self.output / "unlisted").mkdir(mode=0o700)
        module = self.consumer()
        with self.assertRaises(module.PreparationError):
            self.check(result)

    def test_consumer_rejects_extra_file(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0)
        extra = self.output / "unlisted.json"
        extra.write_bytes(b"{}\n")
        extra.chmod(0o600)
        module = self.consumer()
        with self.assertRaises(module.PreparationError):
            self.check(result)

    def test_consumer_rejects_changed_private_mode(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0)
        (self.output / "requests/case-001.json").chmod(0o644)
        module = self.consumer()
        with self.assertRaises(module.PreparationError):
            self.check(result)

    def test_consumer_rejects_incomplete_stdout_or_nonzero_exit(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0)
        module = self.consumer()
        for changes in [{"stdout": result.stdout[:-1]}, {"returncode": 1}]:
            with self.subTest(changes=changes):
                with self.assertRaises(module.PreparationError):
                    self.check(result, **changes)

    @unittest.skipUnless(os.name == "posix", "Controlled POSIX file-size limit")
    def test_write_limit_retains_partial_files_and_unsuccessful_outcome(self):
        import resource
        import signal
        fixture = self.repo / "plugins/proseweaving/skills/writing-for-people/evals/fixtures/case-1.md"
        fixture.write_text("\tX" * 40000)
        validated = subprocess.run([
            sys.executable, str(self.repo / "scripts/validate_proseweaving.py"),
            "--write-content-lock", str(self.repo),
        ], env=self.env, capture_output=True)
        self.assertEqual(validated.returncode, 0, validated.stderr.decode())
        self.revision = self.commit()

        def file_ceiling():
            signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
            resource.setrlimit(resource.RLIMIT_FSIZE, (102400, 102400))

        result = self.prepare(preexec_fn=file_ceiling)
        self.assertEqual(result.returncode, 1, result.stderr.decode())
        outcome = json.loads(result.stdout)
        self.assertEqual(outcome["status"], "incomplete")
        self.assertTrue((self.output / "coordinates.json").is_file())
        self.assertFalse((self.output / "preparation.json").exists())
        self.assertEqual(result.stdout, (self.output / "outcome.json").read_bytes())

    def test_consumer_reports_missing_output_as_preparation_error(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0)
        shutil.rmtree(self.output)
        module = self.consumer()
        with self.assertRaises(module.PreparationError):
            self.check(result)

    def test_rejects_symlinked_repository_input(self):
        alias = self.base / "repository-link"
        alias.symlink_to(self.repo, target_is_directory=True)
        result = self.prepare(source_repository=alias)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
