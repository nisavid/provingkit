from __future__ import annotations

import io
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import measure_provingkit_suite as measurement

SCRIPT = Path(measurement.__file__).resolve()
REFS = (
    "refs/remotes/origin/retained/issue-81-history-import",
    "refs/remotes/origin/retained/agents-pr-69",
    "refs/remotes/origin/retained/pr-11-reviewed-carrier",
)


class CandidateFixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.candidate = self.root / "candidate"
        self.candidate.mkdir()
        self.git("init", "--quiet")
        self.git("config", "user.name", "Measurement Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.write("tests/__init__.py", "")
        self.write("scripts/__init__.py", "")
        self.write("scripts/validate_provingkit.py", "MARKER = 'candidate'\n")
        self.write(".github/workflows/provingkit-source.yml", "name: fixture\n")
        self.write("tests/test_validate_provingkit.py", """import unittest
from scripts import validate_provingkit
class Example(unittest.TestCase):
    def test_candidate_import(self):
        self.assertEqual(validate_provingkit.MARKER, 'candidate')
    @unittest.skip('intentional fixture skip')
    def test_skipped(self):
        self.fail('must not run')
""")
        self.commit()
        for ref in REFS:
            self.git("update-ref", ref, "HEAD")

    def git(self, *arguments):
        return subprocess.run(["git", "-C", str(self.candidate), *arguments],
                              check=True, text=True, capture_output=True).stdout.strip()

    def write(self, relative, content):
        target = self.candidate / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    def commit(self):
        self.git("add", ".")
        self.git("-c", "commit.gpgsign=false", "commit", "--quiet", "-m", "fixture")

    def cli(self, command, *arguments, environment=None):
        output = self.root / "report.json"
        output.unlink(missing_ok=True)
        process = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), command, *map(str, arguments),
             "--output", str(output)], text=True, capture_output=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", **(environment or {})},
        )
        return process, json.loads(output.read_text()) if output.exists() else None

    def save(self, name, document):
        path = self.root / name
        path.write_text(json.dumps(document))
        return path


class CandidateCLITests(CandidateFixture):
    def test_hosted_run_identity_is_observed_without_changing_compatibility(self):
        process, first = self.cli("discover", "--candidate", self.candidate,
                                  environment={"ImageOS": "fixture-image", "GITHUB_RUN_ID": "123",
                                               "GITHUB_JOB": "first", "GITHUB_SHA": "c" * 40,
                                               "UNRELATED_MEASUREMENT_VALUE": "do-not-record"})
        self.assertEqual(process.returncode, 0, process.stderr)
        observed = first["environment"]["observations"]["hosted"]
        self.assertEqual(observed["ImageOS"], "fixture-image")
        self.assertEqual(observed["GITHUB_RUN_ID"], "123")
        self.assertEqual(observed["GITHUB_SHA"], "c" * 40)
        self.assertNotIn("do-not-record", json.dumps(first))
        process, second = self.cli("discover", "--candidate", self.candidate,
                                   environment={"GITHUB_JOB": "second", "GITHUB_RUN_ID": "456"})
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(first["environment"]["compatibility"], second["environment"]["compatibility"])
        self.assertNotEqual(observed, second["environment"]["observations"]["hosted"])

    def test_plan_rejects_checkout_or_input_bundle_drift_before_execution(self):
        process, baseline = self.cli("run", "--candidate", self.candidate)
        self.assertEqual(process.returncode, 0, process.stderr)
        plan_path = self.save("plan.json", measurement.create_plan(baseline, 2))
        self.git("config", "core.filemode", "false")
        process, rejected = self.cli("run", "--candidate", self.candidate,
                                     "--plan", plan_path, "--shard-index", 0)
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("changed", rejected["error"])
        self.assertNotIn("records", rejected)
        self.git("config", "core.filemode", "true")
        (self.candidate / ".git/ci-measurement-bundle.sha256").write_text("b" * 64 + "\n")
        process, rejected = self.cli("run", "--candidate", self.candidate,
                                     "--plan", plan_path, "--shard-index", 0)
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("changed", rejected["error"])
        self.assertNotIn("records", rejected)

    def test_missing_reachable_object_is_rejected(self):
        blob = self.git("rev-parse", "HEAD:tests/test_validate_provingkit.py")
        (self.candidate / ".git/objects" / blob[:2] / blob[2:]).unlink()
        process, rejected = self.cli("discover", "--candidate", self.candidate)
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("missing objects", rejected["error"])

    def test_identity_covers_detached_head_objects_tags_checkout_config_and_input_bundle(self):
        process, initial = self.cli("discover", "--candidate", self.candidate)
        self.assertEqual(process.returncode, 0, process.stderr)
        inventory = initial["source"]["object_inventory"]
        self.assertEqual(inventory["type_counts"]["tag"], 0)
        self.assertEqual(inventory["tag_ids"], [])
        self.git("-c", "tag.gpgsign=false", "tag", "--annotate", "fixture-tag", "--message", "tag identity")
        tag_id = self.git("rev-parse", "refs/tags/fixture-tag")
        detached = self.git("-c", "commit.gpgsign=false", "commit-tree", "HEAD^{tree}", "-m", "detached fixture")
        self.git("checkout", "--quiet", "--detach", detached)
        self.git("config", "core.autocrlf", "false")
        bundle_digest = "a" * 64
        (self.candidate / ".git/ci-measurement-bundle.sha256").write_text(bundle_digest + "\n")
        process, changed = self.cli("discover", "--candidate", self.candidate)
        self.assertEqual(process.returncode, 0, process.stderr)
        observed = changed["source"]["object_inventory"]
        self.assertEqual(observed["count"], inventory["count"] + 2)
        self.assertEqual(observed["type_counts"]["commit"], inventory["type_counts"]["commit"] + 1)
        self.assertEqual(observed["tag_ids"], [tag_id])
        self.assertNotEqual(observed["sha256"], inventory["sha256"])
        self.assertEqual(changed["source"]["head"], detached)
        self.assertEqual(changed["source"]["git_config"]["core.autocrlf"], "false")
        self.assertEqual(changed["source"]["input_bundle_sha256"], bundle_digest)
        self.assertIn("git version", changed["environment"]["compatibility"]["git_version"])
        self.assertIn("GIT_CONFIG_NOSYSTEM", changed["environment"]["compatibility"]["git_config_environment"])
        (self.candidate / ".git/ci-measurement-bundle.sha256").write_text("invalid")
        process, rejected = self.cli("discover", "--candidate", self.candidate)
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("bundle", rejected["error"])

    def test_cli_resolves_relative_paths_before_entering_candidate(self):
        process = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "run", "--candidate", "candidate",
             "--output", "relative-result.json"], cwd=self.root, text=True, capture_output=True,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertTrue(json.loads((self.root / "relative-result.json").read_text())["successful"])

    def test_discovery_rejects_import_errors_and_empty_suites(self):
        for content, expected in (("raise RuntimeError('broken import')\n", "broken import"),
                                  ("import unittest\n", "nonempty")):
            with self.subTest(content=content):
                self.write("tests/test_validate_provingkit.py", content)
                self.commit()
                process, report = self.cli("discover", "--candidate", self.candidate)
                self.assertNotEqual(process.returncode, 0)
                self.assertFalse(report["successful"])
                self.assertIn(expected, report["error"])

    def test_dirty_candidate_and_execution_drift_are_rejected(self):
        self.write("untracked.txt", "untracked")
        process, report = self.cli("discover", "--candidate", self.candidate)
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("not clean", report["error"])
        (self.candidate / "untracked.txt").unlink()
        self.write("tests/test_validate_provingkit.py", """import unittest
from pathlib import Path
class Example(unittest.TestCase):
    def test_changes_source(self):
        Path(__file__).write_text('# changed source')
""")
        self.commit()
        process, report = self.cli("run", "--candidate", self.candidate)
        self.assertNotEqual(process.returncode, 0)
        self.assertFalse(report["successful"])
        self.assertEqual(report["records"][0]["outcome"], "success")
        self.assertIn("changed", report["error"])
        self.assertNotEqual(report["source_after"]["status"], "")

    def test_plan_rejects_incomplete_failed_or_inconsistent_baselines(self):
        process, baseline = self.cli("run", "--candidate", self.candidate)
        self.assertEqual(process.returncode, 0, process.stderr)
        mutations = {
            "failed": lambda value: value.update(successful=False),
            "missing": lambda value: value["records"].pop(),
            "duplicate": lambda value: value["records"].append(copy.deepcopy(value["records"][0])),
            "unknown": lambda value: value["records"][0].update(id="unknown.test"),
            "not stopped": lambda value: value["stopped_ids"].pop(),
            "source drift": lambda value: value["source_after"].update(head="changed"),
            "bad duration": lambda value: value["records"][0].update(duration_seconds=-1),
            "outcome": lambda value: value["records"][0].update(outcome="unexpected_success"),
            "suite omission": lambda value: value["suite"]["ids"].pop(),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                invalid = copy.deepcopy(baseline)
                mutate(invalid)
                path = self.save("invalid-baseline.json", invalid)
                process, report = self.cli("plan", "--baseline", path, "--workers", 2)
                self.assertNotEqual(process.returncode, 0)
                self.assertFalse(report["successful"])

    def test_shards_aggregate_only_after_every_discovered_method_runs(self):
        process, baseline = self.cli("run", "--candidate", self.candidate)
        self.assertEqual(process.returncode, 0, process.stderr)
        baseline_path = self.save("baseline.json", baseline)
        process, plan = self.cli("plan", "--baseline", baseline_path, "--workers", 2)
        self.assertEqual(process.returncode, 0, process.stderr)
        plan_path = self.save("plan.json", plan)
        results = []
        for shard in range(2):
            process, result = self.cli("run", "--candidate", self.candidate,
                                       "--plan", plan_path, "--shard-index", shard)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertEqual(result["selected_ids"], plan["shards"][shard]["ids"])
            results.append(self.save(f"shard-{shard}.json", result))
        process, aggregate = self.cli("aggregate", "--candidate", self.candidate,
                                      "--plan", plan_path, "--results", *results)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertTrue(aggregate["successful"])
        self.assertCountEqual([record["id"] for record in aggregate["records"]], baseline["suite"]["ids"])
        self.assertEqual(sum(record["outcome"] == "skip" for record in aggregate["records"]), 1)
        process, aggregate = self.cli("aggregate", "--candidate", self.candidate,
                                      "--plan", plan_path, "--results", results[0])
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("shard", aggregate["error"])

    def test_aggregate_rejects_inconsistent_method_and_shard_records(self):
        process, baseline = self.cli("run", "--candidate", self.candidate)
        self.assertEqual(process.returncode, 0, process.stderr)
        plan = measurement.create_plan(baseline, 2)
        plan_path = self.save("plan.json", plan)
        results = []
        for shard in range(2):
            process, result = self.cli("run", "--candidate", self.candidate,
                                       "--plan", plan_path, "--shard-index", shard)
            self.assertEqual(process.returncode, 0, process.stderr)
            results.append(result)
        mutations = {
            "duplicate shard": lambda values: values[1].update(shard_index=0),
            "unknown shard": lambda values: values[1].update(shard_index=9),
            "missing record": lambda values: values[0]["records"].clear(),
            "duplicate record": lambda values: values[0]["records"].append(copy.deepcopy(values[0]["records"][0])),
            "unknown method": lambda values: values[0]["records"][0].update(id="unknown.test"),
            "method not executed": lambda values: values[0]["started_ids"].clear(),
            "source changed": lambda values: values[0]["source"].update(head="changed"),
            "wrong plan": lambda values: values[0].update(plan_sha256="wrong"),
            "dependency changed": lambda values: values[0]["environment"]["compatibility"]["dependencies"].update(pytest="new"),
            "transitive dependency changed": lambda values: values[0]["environment"]["compatibility"]["distributions"].update({"rpds-py": "different"}),
            "hidden subtest failure": lambda values: values[0]["records"][0]["subtests"].update(failure=1),
            "object inventory mismatch": lambda values: [values[0][key]["object_inventory"].update(sha256="0" * 64)
                                                         for key in ("source", "source_after")],
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                invalid = copy.deepcopy(results)
                mutate(invalid)
                paths = [self.save(f"invalid-{index}.json", value) for index, value in enumerate(invalid)]
                process, report = self.cli("aggregate", "--candidate", self.candidate,
                                           "--plan", plan_path, "--results", *paths)
                self.assertNotEqual(process.returncode, 0)
                self.assertFalse(report["successful"])

    def test_aggregate_requires_baseline_outcomes_and_subtests_but_allows_new_timings(self):
        self.write("tests/test_validate_provingkit.py", """import unittest
class Example(unittest.TestCase):
    def test_subtests(self):
        for value in (1, 2):
            with self.subTest(value=value):
                self.assertGreater(value, 0)
    def test_success(self): pass
""")
        self.commit()
        process, baseline = self.cli("run", "--candidate", self.candidate)
        self.assertEqual(process.returncode, 0, process.stderr)
        plan_path = self.save("plan.json", measurement.create_plan(baseline, 2))
        results = []
        for shard in range(2):
            process, result = self.cli("run", "--candidate", self.candidate,
                                       "--plan", plan_path, "--shard-index", shard)
            self.assertEqual(process.returncode, 0, process.stderr)
            results.append(result)
        for name in ("added skip", "fewer subtests", "new durations"):
            with self.subTest(name=name):
                changed = copy.deepcopy(results)
                for result in changed:
                    for record in result["records"]:
                        if name == "added skip" and record["id"].endswith("test_success"):
                            record.update(outcome="skip", skip_reasons=["parallel-only skip"])
                            result["skips"] += 1
                        elif name == "fewer subtests" and record["id"].endswith("test_subtests"):
                            record["subtests"]["success"] = 1
                        elif name == "new durations":
                            record["duration_seconds"] = 10.0
                paths = [self.save(f"changed-{index}.json", result) for index, result in enumerate(changed)]
                process, report = self.cli("aggregate", "--candidate", self.candidate,
                                           "--plan", plan_path, "--results", *paths)
                if name == "new durations":
                    self.assertEqual(process.returncode, 0, process.stderr)
                else:
                    self.assertNotEqual(process.returncode, 0)
                    self.assertIn("baseline", report["error"])

    def test_partition_rejects_missing_duplicate_unknown_methods_and_shards(self):
        process, baseline = self.cli("run", "--candidate", self.candidate)
        self.assertEqual(process.returncode, 0, process.stderr)
        plan = measurement.create_plan(baseline, 2)
        mutations = {
            "missing method": lambda value: value["shards"][0]["ids"].clear(),
            "duplicate method": lambda value: value["shards"][1]["ids"].extend(value["shards"][0]["ids"]),
            "unknown method": lambda value: value["shards"][0]["ids"].append("unknown.test"),
            "missing shard": lambda value: value["shards"].pop(),
            "duplicate shard": lambda value: value["shards"][1].update(index=0),
            "unknown shard": lambda value: value["shards"][1].update(index=9),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                invalid = copy.deepcopy(plan)
                mutate(invalid)
                invalid.pop("plan_sha256")
                invalid["plan_sha256"] = measurement.digest(invalid)
                path = self.save("invalid-plan.json", invalid)
                process, report = self.cli("run", "--candidate", self.candidate,
                                           "--plan", path, "--shard-index", 0)
                self.assertNotEqual(process.returncode, 0)
                self.assertFalse(report["successful"])
                self.assertNotIn("records", report)

    def test_new_candidate_method_invalidates_an_existing_plan(self):
        process, baseline = self.cli("run", "--candidate", self.candidate)
        self.assertEqual(process.returncode, 0, process.stderr)
        plan_path = self.save("plan.json", measurement.create_plan(baseline, 2))
        with (self.candidate / "tests/test_validate_provingkit.py").open("a") as stream:
            stream.write("    def test_new_method(self): pass\n")
        self.commit()
        process, report = self.cli("run", "--candidate", self.candidate,
                                   "--plan", plan_path, "--shard-index", 0)
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("changed", report["error"])
        self.assertNotIn("records", report)

    def test_ambiguous_json_receipts_are_rejected(self):
        process, baseline = self.cli("run", "--candidate", self.candidate)
        self.assertEqual(process.returncode, 0, process.stderr)
        path = self.root / "ambiguous.json"
        path.write_text('{"successful": false, ' + json.dumps(baseline)[1:])
        process, report = self.cli("plan", "--baseline", path, "--workers", 2)
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("duplicate", report["error"])

    def test_plan_balances_complete_methods_deterministically(self):
        self.write("tests/test_validate_provingkit.py", """import unittest
class Example(unittest.TestCase):
    def test_a(self): pass
    def test_b(self): pass
    def test_c(self): pass
    def test_d(self): pass
""")
        self.commit()
        process, baseline = self.cli("run", "--candidate", self.candidate)
        self.assertEqual(process.returncode, 0, process.stderr)
        for record, duration in zip(baseline["records"], (8.0, 6.0, 4.0, 2.0)):
            record["duration_seconds"] = duration
        baseline_path = self.save("baseline.json", baseline)
        process, plan = self.cli("plan", "--baseline", baseline_path, "--workers", 2)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual([[name.rsplit('.', 1)[-1] for name in shard["ids"]]
                          for shard in plan["shards"]], [["test_a", "test_d"], ["test_b", "test_c"]])
        self.assertEqual([shard["estimated_seconds"] for shard in plan["shards"]], [10.0, 10.0])
        process, repeated = self.cli("plan", "--baseline", baseline_path, "--workers", 2)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(plan, repeated)
        self.assertEqual(plan["source"], baseline["source"])

    def test_run_keeps_candidate_imports_and_records_failures_before_nonzero_exit(self):
        self.write("tests/test_validate_provingkit.py", """import unittest
from scripts import validate_provingkit
class Example(unittest.TestCase):
    def test_subtests(self):
        self.assertEqual(validate_provingkit.MARKER, 'candidate')
        for value in (1, 2, 3):
            with self.subTest(value=value):
                self.assertNotEqual(value, 2)
    @unittest.skip('intentional fixture skip')
    def test_skipped(self):
        self.fail('must not run')
""")
        self.commit()
        process, report = self.cli("run", "--candidate", self.candidate)
        self.assertEqual(process.returncode, 1, process.stderr)
        self.assertFalse(report["successful"])
        self.assertIn("value=2", process.stderr)
        self.assertEqual(report["started_ids"], report["suite"]["ids"])
        self.assertEqual(report["stopped_ids"], report["suite"]["ids"])
        self.assertEqual([record["outcome"] for record in report["records"]], ["skip", "failure"])
        self.assertEqual(report["source"], report["source_after"])
        self.assertIn("pytest", report["environment"]["compatibility"]["dependencies"])

    def test_discovery_binds_the_clean_candidate_and_rejects_missing_history_refs(self):
        process, report = self.cli("discover", "--candidate", self.candidate)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(report["suite"]["ids"], [
            "tests.test_validate_provingkit.Example.test_candidate_import",
            "tests.test_validate_provingkit.Example.test_skipped",
        ])
        self.assertEqual(report["source"]["head"], self.git("rev-parse", "HEAD"))
        self.assertEqual(report["source"]["status"], "")
        self.assertEqual(set(report["source"]["required_refs"]), set(REFS))
        self.git("update-ref", "-d", REFS[0])
        process, report = self.cli("discover", "--candidate", self.candidate)
        self.assertNotEqual(process.returncode, 0)
        self.assertIn(REFS[0], report["error"])



class MeasurementTests(unittest.TestCase):
    def test_complete_distribution_inventory_detects_transitive_version_change(self):
        distribution = SimpleNamespace(metadata={"Name": "rpds_py"}, version="1.0")
        with patch.object(measurement.importlib.metadata, "distributions", return_value=[distribution]):
            first = measurement.environment_identity()["compatibility"]
            distribution.version = "2.0"
            second = measurement.environment_identity()["compatibility"]
        self.assertEqual(first["distributions"], {"rpds-py": "1.0"})
        self.assertNotEqual(first, second)

    def test_cpu_capacity_uses_current_cgroup_and_restrictive_ancestor(self):
        with tempfile.TemporaryDirectory() as directory:
            mount = Path(directory)
            current = mount / "job" / "worker"
            current.mkdir(parents=True)
            (mount / "cpu.max").write_text("max 100000\n")
            (mount / "job/cpu.max").write_text("150000 100000\n")
            (current / "cpu.max").write_text("400000 100000\n")
            mountinfo = f"1 0 0:1 / {mount} rw - cgroup2 cgroup rw\n"
            observed = measurement.cgroup_capacity("0::/job/worker\n", mountinfo, 8)
            self.assertTrue(observed["complete"])
            self.assertEqual(observed["effective_cpu_capacity"], 1.5)
            self.assertEqual(len(observed["ancestors"]), 3)
            (mount / "job/cpu.max").unlink()
            observed = measurement.cgroup_capacity("0::/job/worker\n", mountinfo, 8)
            self.assertFalse(observed["complete"])
            self.assertIsNone(observed["effective_cpu_capacity"])

    def test_whole_methods_keep_subtest_failures_and_intentional_skips(self):
        class Example(unittest.TestCase):
            def test_subtests(self):
                for value in (1, 2, 3):
                    with self.subTest(value=value):
                        self.assertNotEqual(value, 2)

            @unittest.skip("fixture is intentionally unavailable")
            def test_skipped(self):
                self.fail("must remain skipped")

        suite = unittest.defaultTestLoader.loadTestsFromTestCase(Example)
        stderr = io.StringIO()
        report = measurement.measure_suite(suite, stream=stderr)
        self.assertFalse(report["successful"])
        records = {record["id"].rsplit(".", 1)[-1]: record for record in report["records"]}
        self.assertEqual(records["test_subtests"]["outcome"], "failure")
        self.assertEqual(records["test_subtests"]["subtests"], {"success": 2, "failure": 1, "error": 0, "skip": 0})
        self.assertEqual(records["test_skipped"]["outcome"], "skip")
        self.assertEqual(records["test_skipped"]["skip_reasons"], ["fixture is intentionally unavailable"])
        self.assertEqual(report["started_ids"], report["stopped_ids"])
        self.assertEqual(len(report["started_ids"]), 2)
        self.assertIn("value=2", stderr.getvalue())
        self.assertIn("FAILED", stderr.getvalue())
        self.assertTrue(all(record["duration_seconds"] >= 0 for record in report["records"]))


if __name__ == "__main__":
    unittest.main()
