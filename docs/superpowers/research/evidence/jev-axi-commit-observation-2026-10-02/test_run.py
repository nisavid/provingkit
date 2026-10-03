"""Run-CLI refusals, without any native agent or Jev request."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parent


class RunRefusal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "evidence" / SOURCE.name
        shutil.copytree(SOURCE, self.source, ignore=shutil.ignore_patterns("__pycache__"))
        seed = "sys1-representative-preflight-2026-10-01/representative-workload/project"
        shutil.copytree(SOURCE.parent / seed, self.source.parent / seed,
                        ignore=shutil.ignore_patterns("__pycache__"))
        self.sentinel = self.root / "native-imported"
        (self.source / "native.py").write_text(
            "from pathlib import Path\nPath(" + repr(str(self.sentinel)) + ").touch()\n")
        self.receipts = self.root / "receipts"
        self.receipts.mkdir()
        result = subprocess.run([sys.executable, str(self.source / "prepare.py"),
                                 "--parent", str(self.root)], capture_output=True,
                                text=True, check=True)
        prepared = json.loads(result.stdout)
        self.manifest = Path(prepared["manifest"])
        self.sha256 = prepared["sha256"]

    def invoke(self):
        return subprocess.run([sys.executable, str(self.source / "run.py"),
            "--manifest", str(self.manifest), "--expected-sha256", self.sha256,
            "--receipt-dir", str(self.receipts)], capture_output=True, text=True)

    def test_source_drift_is_retained_and_rejected_before_native_import(self):
        with (self.source / "observe_commit.py").open("a") as stream:
            stream.write("\n# changed after preparation\n")
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.sentinel.exists())
        records = list(self.receipts.glob("*.json"))
        self.assertEqual(len(records), 1)
        record = json.loads(records[0].read_text())
        self.assertEqual(record["status"], "rejected-before-native")
        self.assertIn("source drift", record["error"])

    def test_existing_episode_records_are_preserved_without_native_import(self):
        root = self.manifest.parent
        retained = {"reservation.json": b'{"prior": "reservation"}\n',
                    "outcome.json": b'{"prior": "outcome"}\n',
                    "native-stdout.log": b"previous native stream\n"}
        for name, content in retained.items():
            (root / name).write_bytes(content)
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.sentinel.exists())
        self.assertTrue(all((root / n).read_bytes() == b for n, b in retained.items()))
        receipt = json.loads(next(self.receipts.glob("*.json")).read_text())
        self.assertIn("already attempted", receipt["error"])

    def test_changed_fixture_is_rejected_before_native_import(self):
        manifest = json.loads(self.manifest.read_text())
        (Path(manifest["project"]) / "README.md").write_text("changed task\n")
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.sentinel.exists())
        receipt = json.loads(next(self.receipts.glob("*.json")).read_text())
        self.assertIn("fixture drift", receipt["error"])

    def test_changed_git_hook_configuration_is_rejected_before_native_import(self):
        project = Path(json.loads(self.manifest.read_text())["project"])
        subprocess.run(["git", "config", "core.hooksPath", "/dev/null"], cwd=project, check=True)
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.sentinel.exists())
        receipt = json.loads(next(self.receipts.glob("*.json")).read_text())
        self.assertIn("Git state drift", receipt["error"])

    def test_nonexecutable_observer_is_rejected_before_native_import(self):
        project = Path(json.loads(self.manifest.read_text())["project"])
        (project / ".observation/hooks/commit-msg").chmod(0o644)
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.sentinel.exists())
        receipt = json.loads(next(self.receipts.glob("*.json")).read_text())
        self.assertIn("Git state drift", receipt["error"])


if __name__ == "__main__":
    unittest.main()
