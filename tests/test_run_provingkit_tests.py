"""Exercise the production command with disposable complete-method suites."""
from __future__ import annotations

import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest


RUNNER = Path(__file__).resolve().parents[1] / "scripts/run_provingkit_tests.py"


class ProvingkitTestExecutionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.candidate = self.root / "candidate"
        (self.candidate / "tests").mkdir(parents=True)
        (self.candidate / "tests/__init__.py").write_text("")
        self.output = self.root / "results"

    def write_suite(self, content):
        (self.candidate / "tests/test_validate_provingkit.py").write_text(content)

    def run_suite(self, *arguments, affinity=None):
        return subprocess.run(
            [sys.executable, "-B", str(RUNNER), str(self.candidate),
             "--output-dir", str(self.output), *arguments],
            capture_output=True, text=True, timeout=20,
            preexec_fn=(lambda: os.sched_setaffinity(0, affinity)) if affinity else None,
        )

    def test_every_current_method_runs_with_its_subtests_and_skip_reason(self):
        self.write_suite('''import unittest
class Example(unittest.TestCase):
    def test_first(self):
        for value in [2, 4, 6]:
            with self.subTest(value=value):
                self.assertEqual(value % 2, 0)
    @unittest.skip("requires the optional fixture dependency")
    def test_optional(self):
        self.fail("the skipped method must not run")
    def test_second(self):
        self.assertTrue(True)
    def test_new_without_a_timing_hint(self):
        self.assertEqual("new".upper(), "NEW")
''')
        process = self.run_suite()
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        report = json.loads((self.output / "result.json").read_text())
        self.assertTrue(report["successful"])
        records = {record["id"].rsplit(".", 1)[1]: record for record in report["records"]}
        self.assertEqual(set(records), {
            "test_first", "test_optional", "test_second", "test_new_without_a_timing_hint",
        })
        self.assertEqual(len(report["records"]), 4)
        self.assertEqual(records["test_first"]["subtests"], {
            "success": 3, "failure": 0, "error": 0, "skip": 0,
        })
        self.assertEqual(records["test_optional"]["outcome"], "skip")
        self.assertEqual(records["test_optional"]["skip_reasons"], [
            "requires the optional fixture dependency",
        ])
        self.assertEqual(len(report["workers"]), 2)

    def test_duplicate_discovery_cannot_report_success(self):
        self.write_suite('''import unittest
class Example(unittest.TestCase):
    def test_repeated(self): pass
def load_tests(loader, suite, pattern):
    return unittest.TestSuite([Example("test_repeated"), Example("test_repeated")])
''')
        process = self.run_suite()
        self.assertNotEqual(process.returncode, 0)
        report = json.loads((self.output / "result.json").read_text())
        self.assertFalse(report["successful"])
        self.assertIn("duplicate", report["error"])

    def test_changed_worker_discovery_cannot_silently_drop_a_method(self):
        self.write_suite('''from pathlib import Path
import unittest
class Example(unittest.TestCase):
    def test_a(self): pass
    def test_b(self): pass
    def test_c(self): pass
def load_tests(loader, suite, pattern):
    marker = Path(__file__).with_suffix(".discovered")
    if marker.exists():
        return unittest.TestSuite([Example("test_a"), Example("test_c")])
    marker.write_text("discovered")
    return suite
''')
        process = self.run_suite()
        self.assertNotEqual(process.returncode, 0)
        report = json.loads((self.output / "result.json").read_text())
        self.assertFalse(report["successful"])

    def test_successful_unittest_status_cannot_hide_missing_duplicate_or_unknown_execution(self):
        for behavior in ("missing", "duplicate", "unknown", "incomplete"):
            with self.subTest(behavior=behavior):
                self.output = self.root / behavior
                self.write_suite(f'''import unittest
class Example(unittest.TestCase):
    def test_a(self): pass
    def test_b(self): pass
    def run(self, result=None):
        if self._testMethodName != "test_a":
            return super().run(result)
        if {behavior!r} == "missing":
            return result
        if {behavior!r} == "incomplete":
            result.startTest(self)
            result.stopTest(self)
            return result
        if {behavior!r} == "unknown":
            self._testMethodName = "test_uncollected"
            setattr(self, "test_uncollected", lambda: None)
        super().run(result)
        if {behavior!r} == "duplicate":
            super().run(result)
        return result
''')
                process = self.run_suite()
                self.assertNotEqual(process.returncode, 0)
                report = json.loads((self.output / "result.json").read_text())
                self.assertFalse(report["successful"])

    def test_two_workers_require_two_effective_cpus(self):
        self.write_suite('''import unittest
class Example(unittest.TestCase):
    def test_a(self): pass
    def test_b(self): pass
''')
        process = self.run_suite(affinity={min(os.sched_getaffinity(0))})
        self.assertNotEqual(process.returncode, 0)
        report = json.loads((self.output / "result.json").read_text())
        self.assertFalse(report["successful"])
        self.assertIn("CPU", report["error"])
        self.assertFalse(list(self.output.glob("worker-*.json")))

    @staticmethod
    def running(pid):
        try:
            return Path(f"/proc/{pid}/stat").read_text().split(")", 1)[1].split()[0] != "Z"
        except FileNotFoundError:
            return False

    def test_completed_worker_leaves_no_running_descendant(self):
        pid_file = self.root / "owned-child.pid"
        self.write_suite(f'''import subprocess, sys, time, unittest
from pathlib import Path
class Example(unittest.TestCase):
    def test_child(self):
        child = "import os,signal,time;from pathlib import Path;signal.signal(signal.SIGTERM,signal.SIG_IGN);Path({str(pid_file)!r}).write_text(str(os.getpid()));time.sleep(60)"
        subprocess.Popen([sys.executable, "-c", child], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.monotonic() + 5
        while not Path({str(pid_file)!r}).exists():
            if time.monotonic() > deadline: raise RuntimeError("child failed to start")
            time.sleep(0.01)
    def test_other(self): pass
''')
        try:
            process = self.run_suite()
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            pid = int(pid_file.read_text())
            deadline = time.monotonic() + 2
            while self.running(pid) and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertFalse(self.running(pid), "owned descendant is still running")
            cleanup = json.loads((self.output / "cleanup.json").read_text())
            self.assertTrue(cleanup["successful"])
            self.assertEqual(cleanup["live_members"], [])
        finally:
            if pid_file.exists() and self.running(int(pid_file.read_text())):
                os.kill(int(pid_file.read_text()), signal.SIGKILL)

    def test_timed_out_suite_is_unsuccessful_and_stops_both_workers(self):
        self.write_suite('''import os, time, unittest
from pathlib import Path
class Example(unittest.TestCase):
    def test_a(self):
        Path(__file__).with_name("worker-a.pid").write_text(str(os.getpid()))
        time.sleep(10)
    def test_b(self):
        Path(__file__).with_name("worker-b.pid").write_text(str(os.getpid()))
        time.sleep(10)
''')
        process = self.run_suite("--timeout-seconds", "2")
        self.assertNotEqual(process.returncode, 0)
        report = json.loads((self.output / "result.json").read_text())
        self.assertFalse(report["successful"])
        self.assertIn("timed out", report["error"])
        pid_files = list((self.candidate / "tests").glob("worker-*.pid"))
        self.assertEqual(len(pid_files), 2, "both workers must reach the timed operation")
        for pid_file in pid_files:
            self.assertFalse(self.running(int(pid_file.read_text())))

    def test_cancellation_is_unsuccessful_and_stops_owned_workers(self):
        self.write_suite('''import os, time, unittest
from pathlib import Path
class Example(unittest.TestCase):
    def test_a(self):
        Path(__file__).with_name("worker-a.pid").write_text(str(os.getpid()))
        time.sleep(10)
    def test_b(self):
        Path(__file__).with_name("worker-b.pid").write_text(str(os.getpid()))
        time.sleep(10)
''')
        process = subprocess.Popen(
            [sys.executable, "-B", str(RUNNER), str(self.candidate),
             "--output-dir", str(self.output)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        pid_files = [self.candidate / f"tests/worker-{letter}.pid" for letter in "ab"]
        try:
            deadline = time.monotonic() + 5
            while not all(path.exists() for path in pid_files):
                self.assertIsNone(process.poll(), "controller exited before the workers started")
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.01)
            process.send_signal(signal.SIGTERM)
            self.assertNotEqual(process.wait(timeout=5), 0)
            report = json.loads((self.output / "result.json").read_text())
            self.assertFalse(report["successful"])
            self.assertIn("signal", report["error"])
            for path in pid_files:
                self.assertFalse(self.running(int(path.read_text())))
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            for path in pid_files:
                if path.exists() and self.running(int(path.read_text())):
                    os.killpg(int(path.read_text()), signal.SIGKILL)

    def test_discovery_timeout_is_unsuccessful_and_cleans_its_process(self):
        pid_file = self.root / "discovery.pid"
        self.write_suite(f'''import os, time, unittest
from pathlib import Path
Path({str(pid_file)!r}).write_text(str(os.getpid()))
time.sleep(20)
class Example(unittest.TestCase):
    def test_a(self): pass
    def test_b(self): pass
''')
        start = time.monotonic()
        process = self.run_suite("--timeout-seconds", "2")
        self.assertNotEqual(process.returncode, 0)
        self.assertLess(time.monotonic() - start, 8)
        report = json.loads((self.output / "result.json").read_text())
        self.assertFalse(report["successful"])
        self.assertIn("timed out", report["error"])
        self.assertFalse(self.running(int(pid_file.read_text())))

    def test_timing_hints_balance_whole_methods_without_defining_coverage(self):
        self.write_suite('''import unittest
class Example(unittest.TestCase):
    def test_a(self): pass
    def test_b(self): pass
    def test_c(self): pass
    def test_d(self): pass
''')
        hints = self.root / "timings.json"
        prefix = "tests.test_validate_provingkit.Example."
        hints.write_text(json.dumps({prefix + name: duration for name, duration in (
            ("test_a", 8), ("test_b", 7), ("test_c", 1), ("test_removed", 999),
        )}))
        process = self.run_suite("--timing-hints", str(hints))
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        plan = json.loads((self.output / "plan.json").read_text())
        # Unknown test_d gets the longest known estimate (8). Removed IDs cannot run.
        self.assertEqual(plan["workers"], [
            [prefix + "test_a", prefix + "test_b"],
            [prefix + "test_c", prefix + "test_d"],
        ])
        records = json.loads((self.output / "result.json").read_text())["records"]
        self.assertEqual(len(records), 4)
        self.assertEqual({r["id"] for r in records}, {prefix + f"test_{s}" for s in "abcd"})

    def test_failed_subtest_keeps_logs_records_and_separate_temporary_fixtures(self):
        self.write_suite('''import os, tempfile, unittest
from pathlib import Path
class Example(unittest.TestCase):
    def test_failure(self):
        print("failure worker diagnostic", flush=True)
        Path(tempfile.gettempdir(), "fixture").write_text("first worker")
        with self.subTest(case="failure"):
            self.fail("intentional subtest failure")
        with self.subTest(case="skip"):
            self.skipTest("optional subcase")
    def test_success(self):
        self.assertFalse(Path(tempfile.gettempdir(), "fixture").exists())
        print("success worker diagnostic", flush=True)
''')
        process = self.run_suite()
        self.assertNotEqual(process.returncode, 0)
        report = json.loads((self.output / "result.json").read_text())
        self.assertFalse(report["successful"])
        records = {r["id"].rsplit(".", 1)[1]: r for r in report["records"]}
        self.assertEqual(records["test_failure"]["outcome"], "failure")
        self.assertEqual(records["test_failure"]["subtests"]["failure"], 1)
        self.assertEqual(records["test_failure"]["skip_reasons"], ["optional subcase"])
        self.assertEqual(records["test_success"]["outcome"], "success")
        logs = "\n".join(p.read_text() for p in self.output.glob("worker-*.log"))
        self.assertIn("failure worker diagnostic", logs)
        self.assertIn("success worker diagnostic", logs)
        self.assertIn("intentional subtest failure", logs)
        self.assertFalse(list(self.output.glob("tmp-*")), "owned temporary fixtures survived")
        self.assertGreater(report["duration_seconds"], 0)
        for worker in report["workers"]:
            self.assertGreater(worker["cpu_seconds"], 0)

    def test_worker_exit_without_a_result_cannot_succeed(self):
        self.write_suite('''import os, unittest
class Example(unittest.TestCase):
    def test_exit(self): os._exit(0)
    def test_other(self): pass
''')
        process = self.run_suite()
        self.assertNotEqual(process.returncode, 0)
        report = json.loads((self.output / "result.json").read_text())
        self.assertFalse(report["successful"])
        self.assertTrue(list(self.output.glob("worker-*.log")))

    def test_evidence_directory_must_be_outside_the_candidate(self):
        self.write_suite('''import unittest
class Example(unittest.TestCase):
    def test_a(self): pass
    def test_b(self): pass
''')
        self.output = self.candidate / "results"
        process = self.run_suite()
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("outside", process.stderr)
        self.assertFalse(self.output.exists())

    def test_changed_tracked_candidate_cannot_report_success(self):
        self.write_suite('''from pathlib import Path
import unittest
class Example(unittest.TestCase):
    def test_a(self):
        Path(__file__).with_name("fixture.txt").write_text("changed source")
    def test_b(self): pass
''')
        (self.candidate / "tests/fixture.txt").write_text("original source")
        subprocess.run(["git", "init", "--quiet", str(self.candidate)], check=True)
        subprocess.run(["git", "-C", str(self.candidate), "add", "tests"], check=True)
        subprocess.run([
            "git", "-C", str(self.candidate), "-c", "user.name=Provingkit Test",
            "-c", "user.email=provingkit-test@example.invalid", "-c", "commit.gpgsign=false",
            "commit", "--quiet", "-m", "Synthetic candidate",
        ], check=True)
        process = self.run_suite()
        self.assertNotEqual(process.returncode, 0)
        report = json.loads((self.output / "result.json").read_text())
        self.assertFalse(report["successful"])
        self.assertIn("candidate changed", report["error"])

    def test_intentionally_skipped_subtest_is_a_completed_successful_method(self):
        self.write_suite('''import unittest
class Example(unittest.TestCase):
    def test_partial_skip(self):
        with self.subTest(case="pass"): self.assertTrue(True)
        with self.subTest(case="optional"): self.skipTest("optional subcase")
    def test_other(self): pass
''')
        process = self.run_suite()
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        report = json.loads((self.output / "result.json").read_text())
        record = next(r for r in report["records"] if r["id"].endswith(".test_partial_skip"))
        self.assertEqual(record["outcome"], "success")
        self.assertEqual(record["subtests"], {"success": 1, "failure": 0, "error": 0, "skip": 1})
        self.assertEqual(record["skip_reasons"], ["optional subcase"])

    def test_cancellation_during_cleanup_still_stops_descendants(self):
        pid_file, term_file = self.root / "child.pid", self.root / "child.term"
        self.write_suite(f'''import subprocess, sys, time, unittest
from pathlib import Path
class Example(unittest.TestCase):
    def test_child(self):
        child = "import os,signal,time;from pathlib import Path;signal.signal(signal.SIGTERM,lambda *args:Path({str(term_file)!r}).write_text('term'));Path({str(pid_file)!r}).write_text(str(os.getpid()));time.sleep(60)"
        subprocess.Popen([sys.executable, "-c", child], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        while not Path({str(pid_file)!r}).exists(): time.sleep(0.01)
    def test_other(self): pass
''')
        process = subprocess.Popen(
            [sys.executable, "-B", str(RUNNER), str(self.candidate), "--output-dir", str(self.output)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        try:
            deadline = time.monotonic() + 5
            while not term_file.exists():
                self.assertIsNone(process.poll())
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.01)
            process.send_signal(signal.SIGTERM)
            self.assertNotEqual(process.wait(timeout=5), 0)
            self.assertFalse(self.running(int(pid_file.read_text())), "cleanup was interrupted")
            self.assertTrue(json.loads((self.output / "cleanup.json").read_text())["successful"])
            self.assertFalse(json.loads((self.output / "result.json").read_text())["successful"])
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            if pid_file.exists() and self.running(int(pid_file.read_text())):
                os.kill(int(pid_file.read_text()), signal.SIGKILL)


if __name__ == "__main__":
    unittest.main()
