"""Tests at Git's real commit-msg boundary; no native model or Jev call."""
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parent


class GitBoundary(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.git("init", "--quiet", "--initial-branch=main")
        self.git("config", "user.name", "Fixture Author")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.hooksPath", str(self.project / ".git/hooks"))
        (self.project / "value.txt").write_text("initial\n")
        self.git("add", "value.txt")
        self.git("commit", "--quiet", "-m", "test: seed fixture")
        self.records = self.root / "observations"
        self.records.mkdir()
        hook = self.project / ".git/hooks/commit-msg"
        hook.write_text("#!/bin/sh\nexec " + shlex.join([sys.executable,
            str(SOURCE / "observe_commit.py"), "--repository", str(self.project),
            "--records", str(self.records)]) + ' --message "$1"\n')
        hook.chmod(0o755)

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.project, check=True,
                              capture_output=True)

    def test_commit_records_exact_message_and_staged_change_without_steering(self):
        (self.project / "value.txt").write_text("staged value\n")
        self.git("add", "value.txt")
        (self.project / "value.txt").write_text("unstaged value\n")
        message = self.root / "message.txt"
        message.write_bytes(b"feat: record staged value\n\nKeep the worktree edit separate.\n")
        before = message.read_bytes()
        expected_tree = self.git("write-tree").stdout.decode().strip()
        result = self.git("commit", "--quiet", "--cleanup=verbatim", "-F", str(message))
        self.assertEqual((result.stdout, result.stderr), (b"", b""))
        self.assertEqual(message.read_bytes(), before)
        self.assertEqual(self.git("show", "HEAD:value.txt").stdout, b"staged value\n")
        records = list(self.records.iterdir())
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual((record / "message.bin").read_bytes(), before)
        patch = (record / "staged.patch").read_bytes()
        self.assertIn(b"+staged value", patch)
        self.assertNotIn(b"unstaged value", patch)
        metadata = json.loads((record / "record.json").read_text())
        self.assertEqual(metadata["status"], "captured")
        self.assertEqual(metadata["index_tree"], expected_tree)
        self.assertFalse(metadata["assessment_performed"])

    def test_rejected_and_repeated_commits_preserve_each_observation(self):
        (self.project / "value.txt").write_text("next value\n")
        self.git("add", "value.txt")
        hook = self.project / ".git/hooks/commit-msg"
        original = hook.read_text()
        hook.write_text(original.replace("exec ", "", 1) + "exit 1\n")
        attempt = subprocess.run(["git", "commit", "--quiet", "-m", "feat: next value"],
                                 cwd=self.project, capture_output=True)
        self.assertNotEqual(attempt.returncode, 0)
        first = {str(p.relative_to(self.records)): p.read_bytes()
                 for p in self.records.rglob("*") if p.is_file()}
        self.assertTrue(first)
        hook.write_text(original)
        self.git("commit", "--quiet", "-m", "feat: keep next value")
        self.assertEqual(len(list(self.records.iterdir())), 2)
        self.assertTrue(all((self.records / p).read_bytes() == b for p, b in first.items()))

    def test_unavailable_record_storage_does_not_block_the_commit(self):
        self.records.rmdir()
        (self.project / "value.txt").write_text("next value\n")
        self.git("add", "value.txt")
        result = self.git("commit", "--quiet", "-m", "feat: next value")
        self.assertEqual((result.stdout, result.stderr), (b"", b""))
        self.assertEqual(self.git("show", "HEAD:value.txt").stdout, b"next value\n")


if __name__ == "__main__":
    unittest.main()
