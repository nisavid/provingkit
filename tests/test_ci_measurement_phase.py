"""Exercise phase admission and artifact completeness without expensive suites."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from scripts import ci_measurement_phase as phase
from tests.test_measure_provingkit_suite import CandidateFixture

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/ci_measurement_phase.py"
HEAD = "a" * 40


class MeasurementPhaseTests(unittest.TestCase):
    def invoke(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(SCRIPT), *args], text=True, capture_output=True)

    def run_record(self, **changes: object) -> dict:
        return dict(id=19, head_sha=HEAD, head_branch="ivan/ci-measure-serial",
                    status="completed", conclusion="success", run_attempt=1,
                    path=".github/workflows/ci-scheduling-experiment.yml", **changes)

    def test_exact_unique_successful_baseline_is_selected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "runs.json").write_text(json.dumps([{"workflow_runs": [self.run_record()]}]))
            result = self.invoke("baseline-run", "--runs", str(root / "runs.json"),
                                 "--head", HEAD, "--output", str(root / "output"))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root / "output").read_text(), "run_id=19\n")

    def test_baseline_cannot_be_missing_duplicated_failed_or_different(self) -> None:
        for change in ("missing", "duplicate", "failed", "different", "rerun", "wrong-workflow"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                runs = [self.run_record()]
                if change == "missing": runs = []
                elif change == "duplicate": runs *= 2
                elif change == "failed": runs[0]["conclusion"] = "failure"
                elif change == "different": runs[0]["head_sha"] = "b" * 40
                elif change == "rerun": runs[0]["run_attempt"] = 2
                else: runs[0]["path"] = ".github/workflows/unrelated.yml"
                (root / "runs.json").write_text(json.dumps([{"workflow_runs": runs}]))
                result = self.invoke("baseline-run", "--runs", str(root / "runs.json"),
                                     "--head", HEAD, "--output", str(root / "output"))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("baseline", result.stderr)
                self.assertFalse((root / "output").exists())

    def test_separate_jobs_reject_missing_artifact_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index in range(3):
                folder = root / f"measurement-shard-{index}"
                folder.mkdir()
                (folder / "plan.json").write_text('{}')
                (folder / f"shard-{index}.json").write_text('{}')
            result = self.invoke("separate-jobs", "--candidate", str(root / "candidate"),
                                 "--input-dir", str(root), "--output", str(root / "result.json"))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("four shard artifacts", result.stderr)

    def test_separate_jobs_reject_different_plans_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index in range(4):
                folder = root / f"measurement-shard-{index}"
                folder.mkdir()
                (folder / "plan.json").write_text(json.dumps({"plan": index}))
                (folder / f"shard-{index}.json").write_text('{}')
            result = self.invoke("separate-jobs", "--candidate", str(root / "candidate"),
                                 "--input-dir", str(root), "--output", str(root / "result.json"))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("identical plans", result.stderr)

    def test_two_process_admission_requires_observed_capacity(self) -> None:
        for complete, capacity in ((False, 4), (True, None), (True, 1.5), (True, float("nan"))):
            with self.subTest(complete=complete, capacity=capacity), self.assertRaises(ValueError):
                phase.require_two_cpus({"environment": {"observations": {
                    "cgroup_capacity": {"complete": complete}, "effective_cpu_capacity": capacity}}})
        phase.require_two_cpus({"environment": {"observations": {
            "cgroup_capacity": {"complete": True}, "effective_cpu_capacity": 2}}})


class PhaseExecutionTests(CandidateFixture):
    def plan_fixture(self, workers=2):
        self.write("tests/test_validate_provingkit.py", '''import os
import unittest
class Example(unittest.TestCase):
    def test_a(self):
        if os.environ.get('MEASUREMENT_EXIT'): os._exit(7)
        self.assertNotIn('MEASUREMENT_FAIL', os.environ)
    def test_b(self): pass
    def test_c(self): pass
    def test_d(self): pass
''')
        self.commit()
        process, baseline = self.cli("run", "--candidate", self.candidate)
        self.assertEqual(process.returncode, 0, process.stderr)
        baseline_path = self.save("baseline.json", baseline)
        process, plan = self.cli("plan", "--baseline", baseline_path, "--workers", workers)
        self.assertEqual(process.returncode, 0, process.stderr)
        return baseline_path, self.save("plan.json", plan)

    def test_bundle_restore_preserves_complete_source_and_refs(self):
        baseline, _ = self.plan_fixture()
        bundle = self.root / "candidate.bundle"
        self.git("bundle", "create", str(bundle), "--all", "HEAD")
        bundle_digest = self.root / "bundle.sha256"
        bundle_digest.write_text(hashlib.sha256(bundle.read_bytes()).hexdigest() + "\n")
        destination = self.root / "restored"
        result = subprocess.run([sys.executable, str(SCRIPT), "restore-candidate",
                                 "--candidate", str(destination), "--bundle", str(bundle),
                                 "--bundle-digest", str(bundle_digest),
                                 "--acquisition", str(baseline)], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        restored = json.loads((self.root / "restored-discovery.json").read_text())["source"]
        original = json.loads(baseline.read_text())["source"]
        for key in ("head", "tree", "refs", "required_refs", "file_sha256", "object_inventory"):
            self.assertEqual(restored[key], original[key])
        self.assertEqual(restored["input_bundle_sha256"], bundle_digest.read_text().strip())
        reconstructed = self.save("reconstructed.json", {"source": restored})
        result = subprocess.run([sys.executable, str(SCRIPT), "restore-candidate",
                                 "--candidate", str(self.root / "second"), "--bundle", str(bundle),
                                 "--bundle-digest", str(bundle_digest), "--acquisition", str(baseline),
                                 "--baseline", str(reconstructed)], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.root / "restored-discovery.json").read_text())["source"], restored)
        bundle.write_bytes(bundle.read_bytes() + b"corrupt")
        result = subprocess.run([sys.executable, str(SCRIPT), "restore-candidate",
                                 "--candidate", str(self.root / "third"), "--bundle", str(bundle),
                                 "--bundle-digest", str(bundle_digest), "--acquisition", str(baseline)],
                                text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("acquisition digest", result.stderr)
        self.assertFalse((self.root / "third").exists())

    def test_two_real_workers_complete_or_fail_as_a_group(self):
        _, plan = self.plan_fixture()
        for condition in ("success", "MEASUREMENT_FAIL", "MEASUREMENT_EXIT"):
            with self.subTest(condition=condition):
                destination = self.root / condition
                args = SimpleNamespace(candidate=self.candidate, plan=plan, output_dir=destination)
                environment = {} if condition == "success" else {condition: "1"}
                # Exercise real subprocess execution independently of this test
                # host's CPU quota. Admission has its own observation tests.
                with patch.object(phase, "require_two_cpus"), patch.dict("os.environ", environment):
                    if condition == "success":
                        phase.in_job(args)
                    else:
                        with self.assertRaisesRegex(ValueError, "failed"):
                            phase.in_job(args)
                controller = json.loads((destination / "controller.json").read_text())
                self.assertEqual(len(controller["worker_returncodes"]), 2)
                aggregate = json.loads((destination / "aggregate.json").read_text())
                self.assertEqual(aggregate["successful"], condition == "success")
                self.assertTrue(any(json.loads(path.read_text())["successful"]
                                    for path in destination.glob("shard-*.json")))

    def test_four_real_artifacts_aggregate_and_missing_result_fails(self):
        _, plan = self.plan_fixture(4)
        inputs = self.root / "artifacts"
        for index in range(4):
            folder = inputs / f"measurement-shard-{index}"
            folder.mkdir(parents=True)
            (folder / "plan.json").write_bytes(plan.read_bytes())
            process, report = self.cli("run", "--candidate", self.candidate,
                                       "--plan", plan, "--shard-index", index)
            self.assertEqual(process.returncode, 0, process.stderr)
            (folder / f"shard-{index}.json").write_text(json.dumps(report))
        args = SimpleNamespace(candidate=self.candidate, input_dir=inputs,
                               output=self.root / "aggregate.json")
        phase.separate_jobs(args)
        self.assertTrue(json.loads(args.output.read_text())["successful"])
        (inputs / "measurement-shard-3/shard-3.json").unlink()
        with self.assertRaisesRegex(ValueError, "every shard"):
            phase.separate_jobs(args)

    def test_abrupt_worker_exit_leaves_no_running_descendant(self):
        _, plan = self.plan_fixture()
        content = (self.candidate / "tests/test_validate_provingkit.py").read_text()
        content = content.replace("        if os.environ.get('MEASUREMENT_EXIT'): os._exit(7)", '''        if os.environ.get('MEASUREMENT_DESCENDANT_PID'):
            import subprocess, sys, time
            from pathlib import Path
            child = "import os,signal,sys,time;from pathlib import Path;signal.signal(signal.SIGTERM, signal.SIG_IGN if os.environ.get('MEASUREMENT_IGNORE_TERM') else signal.SIG_DFL);Path(sys.argv[1]).write_text(str(os.getpid()));time.sleep(60)"
            subprocess.Popen([sys.executable, '-c', child, os.environ['MEASUREMENT_DESCENDANT_PID']])
            deadline = time.monotonic() + 5
            while not Path(os.environ['MEASUREMENT_DESCENDANT_PID']).exists():
                if time.monotonic() > deadline: raise RuntimeError('child did not start')
                time.sleep(0.01)
            os._exit(7)
        if os.environ.get('MEASUREMENT_EXIT'): os._exit(7)''')
        self.write("tests/test_validate_provingkit.py", content)
        self.commit()
        process, baseline = self.cli("run", "--candidate", self.candidate)
        self.assertEqual(process.returncode, 0, process.stderr)
        process, schedule = self.cli("plan", "--baseline", self.save("new-baseline.json", baseline),
                                     "--workers", 2)
        self.assertEqual(process.returncode, 0, process.stderr)
        plan = self.save("new-plan.json", schedule)
        for ignores_term in (False, True):
            with self.subTest(ignores_term=ignores_term):
                pid_file = self.root / f"descendant-{ignores_term}.pid"
                args = SimpleNamespace(candidate=self.candidate, plan=plan,
                                       output_dir=self.root / f"leaked-{ignores_term}")
                environment = {"MEASUREMENT_DESCENDANT_PID": str(pid_file),
                               "MEASUREMENT_IGNORE_TERM": "1" if ignores_term else ""}
                try:
                    with patch.object(phase, "require_two_cpus"), patch.dict("os.environ", environment):
                        with self.assertRaises(ValueError):
                            phase.in_job(args)
                    pid = int(pid_file.read_text())
                    deadline = time.monotonic() + 2
                    while self.process_is_running(pid) and time.monotonic() < deadline:
                        time.sleep(0.01)
                    self.assertFalse(self.process_is_running(pid), "owned descendant remains running")
                finally:
                    if pid_file.exists():
                        import os, signal
                        try:
                            os.kill(int(pid_file.read_text()), signal.SIGKILL)
                        except ProcessLookupError:
                            pass

    @staticmethod
    def process_is_running(pid):
        try:
            # Orphan zombies await the host's reaper but cannot execute work.
            return Path(f"/proc/{pid}/stat").read_text().split(")", 1)[1].split()[0] != "Z"
        except FileNotFoundError:
            return False
