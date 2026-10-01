"""Local controller and passive-hook checks; no native harness is started."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parent


class PreflightTests(unittest.TestCase):
    def run_guard(self, manifest, root):
        path = root / "manifest.json"
        path.write_text(json.dumps(manifest))
        (root / "receipts").mkdir()
        return subprocess.run([sys.executable, str(ROOT / "run.py"), "--receipt-dir", str(root / "receipts"), "--manifest", str(path),
                               "--expected-sha256", hashlib.sha256(path.read_bytes()).hexdigest()],
                              capture_output=True, text=True, timeout=10)

    def test_changed_source_is_rejected_before_controller_import(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            source = root / "source.py"
            source.write_text("changed source\n")
            result = self.run_guard({"purpose": "passive-context-qualification", "dependency_roots": {},
                                     "source_sha256": {str(source): "0" * 64}}, root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("runtime source differs", result.stderr)
            receipt = json.loads(next((root / "receipts").glob("*.json")).read_text())
            self.assertEqual(receipt["status"], "rejected-before-controller")
            self.assertFalse(receipt["controller_started"])
            self.assertEqual(receipt["exit_code"], result.returncode)
            self.assertEqual(receipt["stderr"], result.stderr)
            self.assertFalse((root / "private/reservation.json").exists())

    def test_existing_attempt_reservation_is_preserved(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            (root / "private").mkdir()
            reserved = root / "private/reservation.json"
            reserved.write_text("retained evidence\n")
            result = self.run_guard({"purpose": "passive-context-qualification", "dependency_roots": {},
                                     "source_sha256": {}, "root": str(root)}, root)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(reserved.read_text(), "retained evidence\n")
            receipt = json.loads(next((root / "receipts").glob("*.json")).read_text())
            self.assertEqual(receipt["status"], "rejected-before-controller")
            self.assertIn("reservation.json", receipt["error"])
            self.assertFalse((root / "private/outcome.json").exists())

    def test_native_hook_success_requires_matching_capture_count(self):
        from hook_receipts import HookReceipts
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            (root / "private/hooks").mkdir(parents=True)
            tracker = HookReceipts("claude", "settings.json")
            event = {"type": "system", "subtype": "hook_started", "hook_id": "native-1",
                     "hook_event": "Stop", "hook_name": "Stop:0", "session_id": "session"}
            self.assertTrue(tracker.receive(event, "session"))
            with self.assertRaisesRegex(ValueError, "unfinished native"):
                tracker.reconcile(root, "session", 1)
            event.update(subtype="hook_response", outcome="success", exit_code=0, stdout="", stderr="", output="")
            self.assertTrue(tracker.receive(event, "session"))
            with self.assertRaisesRegex(ValueError, "counts differ"):
                tracker.reconcile(root, "session", 1)
            (root / "private/hooks/observer-1.json").write_text(json.dumps({"invocation_id": "observer-1",
                "status": "captured", "raw_hook": {"session_id": "session", "cwd": str(root / "project"),
                                                   "hook_event_name": "Stop"}}))
            result = tracker.reconcile(root, "session", 1)
            self.assertEqual(result["event_counts"], {"Stop": 1})
            self.assertIn("no individual", result["claim"])

    def test_failed_codex_hook_is_rejected(self):
        from hook_receipts import HookReceipts
        tracker = HookReceipts("codex", "/fixture/.codex/hooks.json")
        run = {"id": "native-1", "eventName": "postToolUse", "sourcePath": "/fixture/.codex/hooks.json",
               "handlerType": "command", "executionMode": "sync", "entries": [], "status": "running",
               "scope": "turn", "startedAt": 123}
        event = {"method": "hook/started", "params": {"threadId": "session", "turnId": "turn", "run": run}}
        tracker.receive(event, "session")
        event["method"] = "hook/completed"
        run["status"] = "failed"
        with self.assertRaisesRegex(ValueError, "did not succeed"):
            tracker.receive(event, "session")

    def test_codex_policy_requires_both_temporary_write_exclusions(self):
        from native_support import verify_codex_sandbox
        policy = {"type": "workspaceWrite", "writableRoots": [], "networkAccess": False,
                  "excludeTmpdirEnvVar": True, "excludeSlashTmp": True}
        record = {"cwd": "/fixture", "sandbox": policy}
        verify_codex_sandbox(record, "/fixture", "thread-start")
        for key in ("excludeTmpdirEnvVar", "excludeSlashTmp"):
            changed = dict(policy)
            changed[key] = False
            with self.assertRaises(RuntimeError):
                verify_codex_sandbox({"cwd": "/fixture", "sandbox": changed}, "/fixture", "thread-start")
            changed.pop(key)
            with self.assertRaises(RuntimeError):
                verify_codex_sandbox({"cwd": "/fixture", "sandbox": changed}, "/fixture", "thread-start")

    def test_invalid_hook_configuration_signals_failure_without_agent_output(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            (root / "private/hooks").mkdir(parents=True)
            config = root / "hook-config.json"
            config.write_text("invalid JSON")
            result = subprocess.run([sys.executable, str(ROOT / "passive_hook.py"), "--config", str(config)],
                                    input="{}", capture_output=True, text=True, timeout=10)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (1, "", ""))
            marker = json.loads((root / "private/observer-failure.json").read_text())
            self.assertTrue(marker["error"])

    def test_passive_hooks_keep_cadence_and_stop_bookkeeping_without_output(self):
        with tempfile.TemporaryDirectory(prefix="sys1-passive-local-") as scratch:
            root = Path(scratch)
            project = root / "project"
            project.mkdir()
            (project / "seed.txt").write_text("seed\n")
            git = ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false"]
            for command in (["init", "--quiet"], ["add", "--all"], ["commit", "--quiet", "-m", "test: local fixture"]):
                subprocess.run(git + command, cwd=project, check=True, capture_output=True)
            (root / "private/hooks").mkdir(parents=True)
            session = str(uuid.uuid4())
            storage = root / "native/projects"
            transcript = storage / "fixture" / (session + ".jsonl")
            transcript.parent.mkdir(parents=True)
            transcript.write_text(json.dumps({"type": "user", "message": {"role": "user", "content": "Revise seed.txt."}}) + "\n")
            (root / "private/native-readiness.json").write_text(json.dumps({"verified": True, "session_id": session}))
            config = root / "hook-config.json"
            config.write_text(json.dumps({"root": str(root), "harness": "claude", "storage_root": str(storage),
                                          "node": "node", "max_hook_records": 64, "max_record_bytes": 134217728}))
            for index in range(10):
                (project / "seed.txt").write_text(str(index) + "\n")
                hook = {"cwd": str(project), "session_id": session, "transcript_path": str(transcript),
                        "hook_event_name": "PostToolUse", "tool_name": "Write", "tool_input": {"file_path": "seed.txt"},
                        "tool_response": {"success": True}}
                result = subprocess.run([sys.executable, str(ROOT / "passive_hook.py"), "--config", str(config)],
                                        input=json.dumps(hook), capture_output=True, text=True, timeout=20)
                self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))
            records = [json.loads(path.read_text()) for path in (root / "private/hooks").glob("*.json")]
            self.assertEqual(len(records), 10)
            self.assertTrue(all(record["status"] == "captured" for record in records))
            ordered = sorted(records, key=lambda record: record["bookkeeping"]["after"]["count"])
            self.assertEqual([record["bookkeeping"]["after"]["count"] for record in ordered], list(range(1, 11)))
            self.assertEqual([record["bookkeeping"]["cadence_eligible"] for record in ordered], [False] * 9 + [True])
            self.assertEqual(len({record["bookkeeping"]["after"]["base"] for record in ordered}), 1)
            hook["hook_event_name"] = "Stop"
            result = subprocess.run([sys.executable, str(ROOT / "passive_hook.py"), "--config", str(config)],
                                    input=json.dumps(hook), capture_output=True, text=True, timeout=20)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))
            stop = next(json.loads(path.read_text()) for path in (root / "private/hooks").glob("*.json")
                        if json.loads(path.read_text())["raw_hook"]["hook_event_name"] == "Stop")
            self.assertEqual(stop["bookkeeping"]["before"], stop["bookkeeping"]["after"])
            self.assertIn("diff", stop["bookkeeping"]["current_observation"]["state"])
            self.assertEqual(stop["bookkeeping"]["assessment"], "omitted_for_passive_qualification")
            # A record-publication failure must end qualification even if context and bookkeeping succeeded.
            (root / "private/hooks").rename(root / "private/retained-hooks")
            failed = subprocess.run([sys.executable, str(ROOT / "passive_hook.py"), "--config", str(config)],
                                    input=json.dumps(hook), capture_output=True, text=True, timeout=20)
            self.assertEqual((failed.returncode, failed.stdout, failed.stderr), (1, "", ""))
            marker = json.loads((root / "private/observer-failure.json").read_text())
            self.assertIn("No such file", marker["error"])
            self.assertEqual(len(list((root / "private/retained-hooks").glob("*.json"))), 11)



if __name__ == "__main__":
    unittest.main()
