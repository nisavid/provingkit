"""Consumer checks through the public Surreal Intercom validator CLI."""

from contextlib import contextmanager
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPOSITORY = Path(__file__).resolve().parents[1]


class SurrealIntercomValidatorTests(unittest.TestCase):
    @contextmanager
    def candidate(self):
        with tempfile.TemporaryDirectory(prefix="intercom-validator-") as temporary:
            repository = Path(temporary) / "repository"
            for relative in ("scripts", "plugins/surreal-intercom", "evals/surreal-intercom"):
                shutil.copytree(
                    REPOSITORY / relative, repository / relative,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                )
            lock = Path("release/plugin-content-locks/surreal-intercom.json")
            (repository / lock).parent.mkdir(parents=True, exist_ok=True)
            if (REPOSITORY / lock).is_file():
                shutil.copyfile(REPOSITORY / lock, repository / lock)
            yield repository

    def run_validator(self, repository, *arguments):
        return subprocess.run([
            sys.executable, "-B",
            str(repository / "scripts/validate_surreal_intercom.py"),
            str(repository), *arguments,
        ], capture_output=True, text=True, encoding="utf-8", timeout=30)

    def assert_valid(self, repository):
        result = self.run_validator(repository)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rejects_a_second_public_skill(self):
        with self.candidate() as repository:
            self.assert_valid(repository)
            extra = repository / "plugins/surreal-intercom/skills/sending-extra-messages"
            extra.mkdir()
            (extra / "SKILL.md").write_text(
                "---\nname: sending-extra-messages\n"
                "description: Send an additional synthetic message.\n---\n\n"
                "# Send Extra Messages\n", encoding="utf-8",
            )
            result = self.run_validator(repository)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("direct-child skill inventory drift", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_rejects_another_canonical_member_identity(self):
        with self.candidate() as repository:
            self.assert_valid(repository)
            manifest = repository / "plugins/surreal-intercom/plugin.json"
            document = json.loads(manifest.read_text())
            document["name"] = "unrelated-equipment"
            manifest.write_text(json.dumps(document))
            result = self.run_validator(repository)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("canonical member identity", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_rejects_a_claude_projection_with_another_version(self):
        with self.candidate() as repository:
            self.assert_valid(repository)
            manifest = repository / "plugins/surreal-intercom/.claude-plugin/plugin.json"
            document = json.loads(manifest.read_text())
            document["version"] = "1.1.0"
            manifest.write_text(json.dumps(document))
            result = self.run_validator(repository)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("Claude identity projection", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_rejects_a_default_prompt_for_an_unavailable_skill(self):
        with self.candidate() as repository:
            self.assert_valid(repository)
            manifest = repository / "plugins/surreal-intercom/plugin.json"
            document = json.loads(manifest.read_text())
            document["extensions"]["com.openai"]["interface"]["defaultPrompt"] = [
                "Use $surreal-intercom:unavailable-operation."
            ]
            manifest.write_text(json.dumps(document))
            result = self.run_validator(repository)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("default prompt", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_rejects_a_member_version_outside_the_supported_assignment(self):
        with self.candidate() as repository:
            self.assert_valid(repository)
            for relative in ("plugin.json", ".claude-plugin/plugin.json"):
                manifest = repository / "plugins/surreal-intercom" / relative
                document = json.loads(manifest.read_text())
                document["version"] = "9.9.9"
                manifest.write_text(json.dumps(document))
            result = self.run_validator(repository)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("supported member version", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_regeneration_binds_changed_source_without_silently_rebaselining_it(self):
        with self.candidate() as repository:
            result = self.run_validator(repository, "--write-content-lock")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            lock = repository / "release/plugin-content-locks/surreal-intercom.json"
            original = lock.read_bytes()
            document = json.loads(original)
            self.assertIn("skills/communicating-with-agents/scripts/peer_message.py",
                          document["files"])
            self.assert_valid(repository)
            source = repository / "plugins/surreal-intercom/skills/communicating-with-agents/scripts/peer_message.py"
            source.write_bytes(source.read_bytes() + b"\n# Changed candidate bytes.\n")
            result = self.run_validator(repository)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("content lock mismatch", result.stderr)
            self.assertEqual(lock.read_bytes(), original)
            result = self.run_validator(repository, "--write-content-lock")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            regenerated = lock.read_bytes()
            self.assertNotEqual(regenerated, original)
            self.assert_valid(repository)
            result = self.run_validator(repository, "--write-content-lock")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(lock.read_bytes(), regenerated)

    def test_invalid_resource_links_leave_the_previous_identity_intact(self):
        for destination in ("references/not-shipped.md", "../../../../outside.txt"):
            with self.subTest(destination=destination), self.candidate() as repository:
                self.assert_valid(repository)
                lock = repository / "release/plugin-content-locks/surreal-intercom.json"
                original = lock.read_bytes()
                (repository / "outside.txt").write_text("Synthetic outside resource.")
                skill = repository / "plugins/surreal-intercom/skills/communicating-with-agents/SKILL.md"
                skill.write_text(skill.read_text() + f"\n[Selected resource]({destination})\n")
                result = self.run_validator(repository, "--write-content-lock")
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("Agent Skill resource", result.stderr)
                self.assertEqual(lock.read_bytes(), original)
                self.assertNotIn("Traceback", result.stderr)

    def test_rejects_an_import_unavailable_in_the_standalone_plugin(self):
        with self.candidate() as repository:
            self.assert_valid(repository)
            lock = repository / "release/plugin-content-locks/surreal-intercom.json"
            original = lock.read_bytes()
            helper = repository / "plugins/surreal-intercom/skills/communicating-with-agents/scripts/owner_admission_sender.py"
            helper.write_text(helper.read_text() + "\nimport unshipped_peer_dependency\n")
            result = self.run_validator(repository, "--write-content-lock")
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("runtime import", result.stderr)
            self.assertEqual(lock.read_bytes(), original)
            self.assertNotIn("Traceback", result.stderr)

    def test_nested_procedure_resources_must_ship_before_identity_regeneration(self):
        with self.candidate() as repository:
            self.assert_valid(repository)
            lock = repository / "release/plugin-content-locks/surreal-intercom.json"
            original = lock.read_bytes()
            reference = repository / "plugins/surreal-intercom/skills/communicating-with-agents/references/codex-owner-admission.md"
            reference.write_text(reference.read_text() + "\n[Required command](../scripts/not-shipped.py)\n")
            result = self.run_validator(repository, "--write-content-lock")
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("Agent Skill resource is missing", result.stderr)
            self.assertEqual(lock.read_bytes(), original)
            self.assertNotIn("Traceback", result.stderr)

    def test_runtime_state_and_a_new_server_do_not_enter_the_installable_member(self):
        for relative in (".mcp.json", "skills/communicating-with-agents/evals/result.json",
                         "skills/communicating-with-agents/captures/frame.json"):
            with self.subTest(relative=relative), self.candidate() as repository:
                self.assert_valid(repository)
                lock = repository / "release/plugin-content-locks/surreal-intercom.json"
                original = lock.read_bytes()
                extra = repository / "plugins/surreal-intercom" / relative
                extra.parent.mkdir(parents=True, exist_ok=True)
                extra.write_text("{}\n")
                result = self.run_validator(repository, "--write-content-lock")
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("outside the installable source contract", result.stderr)
                self.assertEqual(lock.read_bytes(), original)

    def test_missing_external_evaluation_fixture_does_not_rebaseline_the_member(self):
        with self.candidate() as repository:
            self.assert_valid(repository)
            lock = repository / "release/plugin-content-locks/surreal-intercom.json"
            original = lock.read_bytes()
            (repository / "evals/surreal-intercom/skills/communicating-with-agents/fixtures/claude-native-send.md").unlink()
            result = self.run_validator(repository, "--write-content-lock")
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("evaluation fixture", result.stderr)
            self.assertEqual(lock.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
