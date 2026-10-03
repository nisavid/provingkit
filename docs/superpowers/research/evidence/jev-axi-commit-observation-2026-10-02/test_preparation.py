"""Exercise the preparation CLI using only local fixtures."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parent


class Preparation(unittest.TestCase):
    def test_failed_preparation_preserves_receipt_and_partial_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            source = parent / "source"
            shutil.copytree(SOURCE, source, ignore=shutil.ignore_patterns("__pycache__"))
            # No seed is supplied beside this copy: fail after reserving a root.
            result = subprocess.run([sys.executable, str(source / "prepare.py"),
                                     "--parent", str(parent)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            receipts = list(parent.glob("preparation-*.json"))
            self.assertEqual(len(receipts), 1)
            record = json.loads(receipts[0].read_text())
            self.assertEqual(record["status"], "failed")
            self.assertIn("FileNotFoundError", record["error"])
            self.assertTrue(Path(record["root"]).is_dir())
            self.assertFalse((Path(record["root"]) / "manifest.json").exists())

    def test_preparation_creates_bound_disposable_repository_without_native_run(self):
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            result = subprocess.run([sys.executable, str(SOURCE / "prepare.py"),
                                     "--parent", str(parent)], capture_output=True,
                                    text=True, check=True)
            summary = json.loads(result.stdout)
            self.assertEqual(summary["native_sessions_started"], 0)
            manifest_path = Path(summary["manifest"])
            manifest = json.loads(manifest_path.read_text())
            project = Path(manifest["project"])
            self.assertTrue((project / "report.py").is_file())
            self.assertTrue((project / "CONTRIBUTING.md").is_file())
            self.assertEqual(manifest["purpose"], "passive-commit-observation")
            self.assertEqual(manifest["profile"], "installed-codex-authoring")
            self.assertEqual(manifest["execution_authorized"], False)
            self.assertEqual(manifest["native_deadline_seconds"], 480)
            self.assertFalse((manifest_path.parent / "reservation.json").exists())
            self.assertTrue(all(hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
                                for path, digest in manifest["source_sha256"].items()))
            command = ["git", "config", "--get", "core.hooksPath"]
            hook_path = Path(subprocess.run(command, cwd=project, check=True,
                capture_output=True, text=True).stdout.strip())
            self.assertTrue((hook_path / "commit-msg").is_file())
            self.assertEqual(subprocess.run(["git", "status", "--porcelain"], cwd=project,
                check=True, capture_output=True).stdout, b"")


if __name__ == "__main__":
    unittest.main()
