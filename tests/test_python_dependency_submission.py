"""Consumer examples for the offline snapshot CLI and its workflow caller."""

import json
from datetime import datetime, timedelta
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/build_python_dependency_snapshot.py"
WORKFLOW = ROOT / ".github/workflows/dependency-submission.yml"
ENVIRONMENT = {
    "implementation_name": "cpython", "implementation_version": "3.13.0",
    "os_name": "posix", "platform_machine": "x86_64",
    "platform_release": "fixture", "platform_system": "Linux",
    "platform_version": "fixture", "python_full_version": "3.13.0",
    "platform_python_implementation": "CPython", "python_version": "3.13",
    "sys_platform": "linux",
}


class PythonDependencySubmissionTests(unittest.TestCase):
    def direct_report(self, **metadata):
        return {
            "version": "1", "pip_version": "26.2.2", "environment": ENVIRONMENT,
            "install": [{"requested": True, "is_direct": False,
                         "metadata": {"name": "direct", "version": "1.0", **metadata}}],
        }

    def run_snapshot(self, report, requirements="direct==1.0\n", extra_args=(), raw_report=None,
                     existing_snapshot=None):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "requirements.txt").write_text(requirements, encoding="utf-8")
            (root / "report.json").write_text(
                json.dumps(report) if raw_report is None else raw_report, encoding="utf-8",
            )
            output = root / "snapshot.json"
            if existing_snapshot is not None:
                output.write_text(json.dumps(existing_snapshot), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable, str(CLI),
                    "--requirements", str(root / "requirements.txt"),
                    "--report", str(root / "report.json"),
                    "--sha", "a" * 40, "--ref", "refs/heads/main",
                    "--repository", "example/project", "--run-id", "123",
                    "--output", str(output), *extra_args,
                ],
                capture_output=True, text=True, timeout=15, check=False,
            )
            snapshot = json.loads(output.read_text()) if output.exists() else None
            return result, snapshot

    def test_snapshot_retains_the_resolved_transitive_packages_and_edges(self):
        report = {
            "version": "1", "pip_version": "26.2.2",
            "environment": ENVIRONMENT,
            "install": [
                {"requested": True, "is_direct": False,
                 "metadata": {"name": "direct", "version": "1.0",
                              "requires_dist": ["middle>=2.0"]}},
                {"requested": False, "is_direct": False,
                 "metadata": {"name": "middle", "version": "2.1",
                              "requires_dist": ["leaf==3.0"]}},
                {"requested": False, "is_direct": False,
                 "metadata": {"name": "leaf", "version": "3.0"}},
            ],
        }
        result, snapshot = self.run_snapshot(report)
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = {
            "pkg:pypi/direct@1.0": {"package_url": "pkg:pypi/direct@1.0",
                       "relationship": "direct", "scope": "development",
                       "dependencies": ["pkg:pypi/middle@2.1"]},
            "pkg:pypi/middle@2.1": {"package_url": "pkg:pypi/middle@2.1",
                       "relationship": "indirect", "scope": "development",
                       "dependencies": ["pkg:pypi/leaf@3.0"]},
            "pkg:pypi/leaf@3.0": {"package_url": "pkg:pypi/leaf@3.0",
                     "relationship": "indirect", "scope": "development",
                     "dependencies": []},
        }
        self.assertEqual(
            snapshot["manifests"]["requirements.txt"]["resolved"], expected,
            "The snapshot must retain every resolved package and its dependency edges",
        )

    def test_edges_follow_the_reported_environment_without_unselected_extras(self):
        report = {
            "version": "1", "pip_version": "26.2.2", "environment": ENVIRONMENT,
            "install": [
                {"requested": True, "is_direct": False,
                 "metadata": {"name": "direct", "version": "1.0",
                              "requires_dist": [
                                  "active>=2; python_version >= '3.13'",
                                  "old; python_version < '3.13'",
                                  "optional; extra == 'format'",
                              ]}},
                {"requested": False, "is_direct": False,
                 "metadata": {"name": "active", "version": "2.0"}},
            ],
        }
        result, snapshot = self.run_snapshot(report)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            snapshot["manifests"]["requirements.txt"]["resolved"]["pkg:pypi/direct@1.0"]["dependencies"],
            ["pkg:pypi/active@2.0"],
            "Inactive environment requirements and unselected extras are not dependency edges",
        )

    def test_environment_values_have_an_explicit_byte_bound(self):
        for value, expected_exit in (("10" + ".0" * 127, 0), ("100" + ".0" * 127, 1)):
            with self.subTest(bytes=len(value.encode())):
                report = self.direct_report(requires_dist=["leaf; python_full_version >= '0'"])
                report["environment"] = {**ENVIRONMENT, "python_full_version": value}
                report["install"].append({"requested": False, "is_direct": False,
                                          "metadata": {"name": "leaf", "version": "2.0"}})
                result, snapshot = self.run_snapshot(report)
                self.assertEqual(result.returncode, expected_exit, result.stderr)
                if expected_exit:
                    self.assertIsNone(snapshot)
                    self.assertIn("environment value exceeds 256 bytes", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)

    def test_flat_markers_have_an_explicit_requirement_byte_bound(self):
        atom = "python_full_version >= '0'"
        count = (128 * 1024 - 6 + 5) // (len(atom) + 5)
        expression = "leaf; " + " and ".join([atom] * count)
        for size, expected_exit in ((128 * 1024, 0), (128 * 1024 + 1, 1)):
            with self.subTest(bytes=size):
                requirement = expression + " " * (size - len(expression))
                report = self.direct_report(requires_dist=[requirement])
                report["environment"] = {**ENVIRONMENT, "python_full_version": "10" + ".0" * 127}
                report["install"].append({"requested": False, "is_direct": False,
                                          "metadata": {"name": "leaf", "version": "2.0"}})
                result, snapshot = self.run_snapshot(report)
                self.assertEqual(result.returncode, expected_exit, result.stderr)
                if expected_exit:
                    self.assertIsNone(snapshot)
                    self.assertIn("requirement exceeds 128 KiB", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                else:
                    self.assertEqual(snapshot["manifests"]["requirements.txt"]["resolved"]["pkg:pypi/direct@1.0"]["dependencies"],
                                     ["pkg:pypi/leaf@2.0"])

    def test_report_keys_cannot_activate_an_unsupported_marker_context(self):
        for key in ("extras", "dependency_groups"):
            with self.subTest(context=key):
                report = self.direct_report(requires_dist=[f'optional; "format" in {key}'])
                report["environment"] = {**ENVIRONMENT, key: "format"}
                report["install"].append({"requested": False, "is_direct": False,
                                          "metadata": {"name": "optional", "version": "1.0"}})
                result, snapshot = self.run_snapshot(report)
                self.assertEqual(result.returncode, 1, "Unsupported contexts cannot authorize an edge")
                self.assertIsNone(snapshot)
                self.assertNotIn("Traceback", result.stderr)

    def test_snapshot_binds_the_declared_source_and_submission_producer(self):
        result, snapshot = self.run_snapshot(self.direct_report())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(snapshot.get("version"), 0, "Produce the supported submission format")
        self.assertEqual(snapshot["sha"], "a" * 40)
        self.assertEqual(snapshot["ref"], "refs/heads/main")
        self.assertEqual(snapshot["job"], {
            "id": "123", "correlator": "python-validation-dependencies",
            "html_url": "https://github.com/example/project/actions/runs/123",
        })
        self.assertEqual(snapshot["detector"], {
            "name": "provingkit-pip-report", "version": "1",
            "url": "https://github.com/example/project/blob/" + "a" * 40
                   + "/scripts/build_python_dependency_snapshot.py",
        })
        manifest = snapshot["manifests"]["requirements.txt"]
        self.assertEqual(manifest["name"], "requirements.txt")
        self.assertEqual(manifest["file"], {"source_location": "requirements.txt"})
        self.assertEqual(datetime.fromisoformat(snapshot["scanned"]).utcoffset(), timedelta(0))

    def test_incomplete_resolution_cannot_be_submitted_as_a_success(self):
        result, snapshot = self.run_snapshot(self.direct_report(requires_dist=["missing>=2"]))
        self.assertEqual(result.returncode, 1, "A missing resolved dependency must reject")
        self.assertIsNone(snapshot, "Do not leave a successful-looking snapshot after refusal")
        self.assertIn("missing resolved dependency", result.stderr)

    def test_another_requirements_inventory_cannot_supply_the_snapshot(self):
        result, snapshot = self.run_snapshot(self.direct_report(), "different==1.0\n")
        self.assertEqual(result.returncode, 1, "Bind requested packages to the maintained inventory")
        self.assertIsNone(snapshot)
        self.assertIn("requirements inventory", result.stderr)

    def test_submission_identity_refuses_an_untrusted_ref(self):
        result, snapshot = self.run_snapshot(
            self.direct_report(), extra_args=("--ref", "refs/pull/12/merge"),
        )
        self.assertEqual(result.returncode, 1, "The producer is restricted to trusted main")
        self.assertIsNone(snapshot)
        self.assertIn("source identity", result.stderr)

    def test_a_present_but_incompatible_dependency_does_not_establish_resolution(self):
        report = self.direct_report(requires_dist=["leaf>=2"])
        report["install"].append({"requested": False, "is_direct": False,
                                  "metadata": {"name": "leaf", "version": "1.0"}})
        result, snapshot = self.run_snapshot(report)
        self.assertEqual(result.returncode, 1, "Check resolved dependency versions, not only names")
        self.assertIsNone(snapshot)
        self.assertIn("dependency version", result.stderr)

    def test_many_version_exclusions_with_a_local_version_remain_usable(self):
        exclusions = ",".join(f"!={i}" for i in range(10000))
        report = self.direct_report(requires_dist=["leaf" + exclusions])
        report["install"].append({"requested": False, "is_direct": False,
                                  "metadata": {"name": "leaf", "version": "100001+vendor"}})
        result, snapshot = self.run_snapshot(report)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(snapshot["manifests"]["requirements.txt"]["resolved"]["pkg:pypi/direct@1.0"]["dependencies"],
                         ["pkg:pypi/leaf@100001%2Bvendor"])

    def test_oversized_resolved_versions_are_refused_before_comparison(self):
        version = "1" + ".0" * 30000
        report = self.direct_report(requires_dist=["leaf" + ",".join([">=1"] * 10000)])
        report["install"].append({"requested": False, "is_direct": False,
                                  "metadata": {"name": "leaf", "version": version}})
        result, snapshot = self.run_snapshot(report)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIsNone(snapshot)
        self.assertIn("resolved version exceeds 256 bytes", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_resolved_version_bound_covers_many_same_family_comparisons(self):
        for family, expected_exit in (("1", 0), ("10", 1)):
            with self.subTest(family=family):
                version = family + ".0" * 124 + "a100000"
                clause = f">{family}a"
                count = (128 * 1024 - 3) // (len(clause) + 1)
                requirement = "leaf" + ",".join([clause] * count)
                requirement += " " * (128 * 1024 - len(requirement))
                report = self.direct_report(requires_dist=[requirement])
                report["install"].append({"requested": False, "is_direct": False,
                                          "metadata": {"name": "leaf", "version": version}})
                result, snapshot = self.run_snapshot(report)
                self.assertEqual(result.returncode, expected_exit, result.stderr)
                if expected_exit:
                    self.assertIsNone(snapshot)
                    self.assertIn("resolved version exceeds 256 bytes", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                else:
                    self.assertEqual(snapshot["manifests"]["requirements.txt"]["resolved"]["pkg:pypi/leaf@" + version]["package_url"],
                                     "pkg:pypi/leaf@" + version)

    def test_parenthesis_bound_parses_at_the_limit_and_refuses_above_it(self):
        for count, expected_exit in ((32, 0), (33, 1)):
            with self.subTest(parentheses=count):
                marker = "(" * count + "python_version >= '3.13'" + ")" * count
                report = self.direct_report(requires_dist=["leaf>=2; " + marker])
                report["install"].append({"requested": False, "is_direct": False,
                                          "metadata": {"name": "leaf", "version": "2.0"}})
                result, snapshot = self.run_snapshot(report)
                self.assertEqual(result.returncode, expected_exit, result.stderr)
                if count == 32:
                    self.assertEqual(snapshot["manifests"]["requirements.txt"]["resolved"]["pkg:pypi/direct@1.0"]["dependencies"],
                                     ["pkg:pypi/leaf@2.0"])
                else:
                    self.assertIsNone(snapshot)
                    self.assertIn("requirement parenthesis limit", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)

    def test_duplicate_package_identities_cannot_hide_contradictory_records(self):
        report = self.direct_report()
        report["install"].append({"requested": True, "is_direct": False,
                                  "metadata": {"name": "Direct", "version": "1.0"}})
        result, snapshot = self.run_snapshot(report)
        self.assertEqual(result.returncode, 1, "Normalize identities without overwriting evidence")
        self.assertIsNone(snapshot)
        self.assertIn("duplicate package", result.stderr)

    def test_report_booleans_are_not_inferred_from_arbitrary_strings(self):
        report = self.direct_report()
        report["install"][0]["requested"] = "true"
        result, snapshot = self.run_snapshot(report)
        self.assertEqual(result.returncode, 1, "Malformed report types cannot establish an inventory")
        self.assertIsNone(snapshot)
        self.assertIn("invalid pip report", result.stderr)

    def test_duplicate_json_fields_do_not_select_the_last_claim(self):
        raw = json.dumps(self.direct_report()).replace('"version": "1"', '"version": "2", "version": "1"', 1)
        result, snapshot = self.run_snapshot(None, raw_report=raw)
        self.assertEqual(result.returncode, 1, "Ambiguous JSON cannot establish snapshot evidence")
        self.assertIsNone(snapshot)
        self.assertIn("duplicate JSON", result.stderr)

    def test_direct_urls_are_refused_even_when_their_markers_are_inactive(self):
        for marker in ("", " ; python_version < '3.0'"):
            with self.subTest(marker=marker):
                report = self.direct_report(requires_dist=["leaf @ https://example.invalid/leaf.whl" + marker])
                result, snapshot = self.run_snapshot(report)
                self.assertEqual(result.returncode, 1, "Direct URLs remain outside the adapter contract")
                self.assertIsNone(snapshot)
                self.assertIn("direct URL", result.stderr)

    def test_selected_extras_cannot_be_silently_reported_as_default_dependencies(self):
        report = self.direct_report()
        report["install"][0]["requested_extras"] = ["format"]
        result, snapshot = self.run_snapshot(report)
        self.assertEqual(result.returncode, 1, "Unsupported selected extras must stay explicit")
        self.assertIsNone(snapshot)
        self.assertIn("selected extras", result.stderr)

    def test_unrelated_installed_packages_do_not_expand_the_manifest(self):
        report = self.direct_report()
        report["install"].append({"requested": False, "is_direct": False,
                                  "metadata": {"name": "unrelated", "version": "2.0"}})
        result, snapshot = self.run_snapshot(report)
        self.assertEqual(result.returncode, 1, "Only the reachable requirements closure is evidence")
        self.assertIsNone(snapshot)
        self.assertIn("unreachable", result.stderr)

    def test_an_existing_snapshot_is_preserved_instead_of_replaced(self):
        result, snapshot = self.run_snapshot(self.direct_report(), existing_snapshot={"kept": True})
        self.assertEqual(result.returncode, 1, "A fresh output path is required")
        self.assertEqual(snapshot, {"kept": True})

    def test_workflow_verifies_prs_and_keeps_submission_on_trusted_main(self):
        workflow = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        self.assertIn("pull_request", workflow["on"], "Verify changes before they reach main")
        self.assertNotIn("pull_request_target", workflow["on"])
        self.assertEqual(workflow["on"]["push"]["branches"], ["main"])
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        verify, submit = workflow["jobs"]["verify"], workflow["jobs"]["submit"]
        self.assertEqual(verify.get("permissions", workflow["permissions"]), {"contents": "read"})
        self.assertEqual(submit["permissions"], {"contents": "write"})
        self.assertEqual(submit["needs"], "verify")
        self.assertEqual(
            " ".join(submit["if"].split()),
            "github.repository == 'nisavid/provingkit' && github.ref == 'refs/heads/main' && "
            "(github.event_name == 'push' || github.event_name == 'workflow_dispatch')",
        )
        for job in (verify, submit):
            self.assertNotEqual(job.get("continue-on-error"), "true")
            for step in job["steps"]:
                self.assertNotEqual(step.get("continue-on-error"), "true")
                if "uses" in step:
                    self.assertRegex(step["uses"], r"@[0-9a-f]{40}$")
        commands = "\n".join(step.get("run", "") for step in submit["steps"])
        self.assertIn("--report", commands)
        resolution = "\n".join(step.get("run", "") for step in verify["steps"])
        self.assertIn("--report", resolution)
        self.assertIn("-r requirements.txt", resolution)
        self.assertIn("scripts/build_python_dependency_snapshot.py", commands)
        self.assertIn("--input", commands)

    def test_same_run_metadata_transfer_preserves_dependency_evidence(self):
        workflow = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        steps = workflow["jobs"]["verify"]["steps"]
        producer = next(step for step in steps
                        if step.get("id") == "inventory")
        resolution = next(step for step in steps if "--report" in step.get("run", ""))
        verification = next(step for step in steps if "-m unittest" in step.get("run", ""))
        self.assertLess(steps.index(resolution), steps.index(producer))
        self.assertLess(steps.index(producer), steps.index(verification),
                        "Capture pip metadata before tests execute installed dependency code")
        self.assertIsNone(verification.get("if"), "Tests must still gate the whole verify job")
        consumer = next(step for step in workflow["jobs"]["submit"]["steps"]
                        if step.get("name") == "Read the same-run dependency metadata")
        self.assertEqual(workflow["jobs"]["verify"]["outputs"]["report"],
                         "${{ steps.inventory.outputs.report }}")
        self.assertEqual(consumer["env"]["REPORT_BASE64"], "${{ needs.verify.outputs.report }}")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, target = root / "source", root / "target"
            source.mkdir()
            target.mkdir()
            output = root / "job-output"
            expected = self.direct_report(requires_dist=["leaf>=2"])
            expected["install"].append({"requested": False, "is_direct": False,
                                        "metadata": {"name": "leaf", "version": "2.0"}})
            report = json.loads(json.dumps(expected))
            expected.pop("pip_version")
            report["install"][0]["metadata"]["description"] = "Omit presentation metadata"
            (source / "python-install-report.json").write_text(json.dumps(report), encoding="utf-8")
            environment = {**os.environ, "BASH_ENV": "", "ENV": ""}
            encoded = subprocess.run(
                ["bash", "-c", producer["run"]],
                env={**environment, "RUNNER_TEMP": str(source), "GITHUB_OUTPUT": str(output)},
                capture_output=True, text=True, timeout=15, check=False,
            )
            self.assertEqual(encoded.returncode, 0, encoded.stderr)
            lines = output.read_text().splitlines()
            self.assertEqual(len(lines), 1)
            self.assertTrue(lines[0].startswith("report="))
            (source / "python-install-report.json").write_text(
                json.dumps(self.direct_report()), encoding="utf-8",
            )
            decoded = subprocess.run(
                ["bash", "-c", consumer["run"]],
                env={**environment, "RUNNER_TEMP": str(target), "REPORT_BASE64": lines[0][7:]},
                capture_output=True, text=True, timeout=15, check=False,
            )
            self.assertEqual(decoded.returncode, 0, decoded.stderr)
            transferred = target / "python-install-report.json"
            self.assertEqual(json.loads(transferred.read_text()), expected)
            converted, snapshot = self.run_snapshot(json.loads(transferred.read_text()))
            self.assertEqual(converted.returncode, 0, converted.stderr)
            resolved = snapshot["manifests"]["requirements.txt"]["resolved"]
            self.assertEqual(len(resolved), 2)
            self.assertEqual(resolved["pkg:pypi/direct@1.0"]["dependencies"],
                             ["pkg:pypi/leaf@2.0"])
            transferred.unlink()
            missing = subprocess.run(
                ["bash", "-c", consumer["run"]],
                env={**environment, "RUNNER_TEMP": str(target), "REPORT_BASE64": ""},
                capture_output=True, text=True, timeout=15, check=False,
            )
            self.assertNotEqual(missing.returncode, 0)
            self.assertFalse(transferred.exists(), "Missing job output cannot become a report")

    def test_project_dependency_installation_has_no_repository_write_permission(self):
        workflow = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        installers = [job for job in workflow["jobs"].values()
                      if any("-r requirements.txt" in step.get("run", "")
                             for step in job["steps"])]
        self.assertTrue(installers, "The reported inventory must come from maintained requirements")
        for job in installers:
            permissions = job.get("permissions", workflow["permissions"])
            self.assertEqual(permissions, {"contents": "read"},
                             "Project dependency code must not execute in a repository-write job")

    def test_caller_refuses_a_substituted_parser_wheel_before_installation(self):
        workflow = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        resolver = next(step for step in workflow["jobs"]["submit"]["steps"]
                        if step.get("name") == "Install the reviewed metadata parser")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "requirements.txt").write_text(
                (ROOT / "requirements.txt").read_text(encoding="utf-8"), encoding="utf-8",
            )
            fake_bin = root / "bin"
            fake_bin.mkdir()
            marker = root / "installation-called"
            fake_python = fake_bin / "python"
            fake_python.write_text(
                '#!/bin/sh\n'
                'if [ "$2" = venv ]; then mkdir -p "$3/bin"; cp "$0" "$3/bin/python"; exit 0; fi\n'
                'if [ "$3" = download ] || [ "$3:$4" = --isolated:download ]; then\n'
                '  while [ "$1" != --dest ]; do shift; done\n'
                '  printf substitute > "$2/packaging-26.3-py3-none-any.whl"; exit 0\n'
                'fi\n'
                'printf called > "$INSTALL_MARKER"\nexit 99\n', encoding="utf-8",
            )
            fake_python.chmod(0o755)
            result = subprocess.run(
                ["bash", "-c", resolver["run"]], cwd=root,
                env={**os.environ, "PATH": str(fake_bin) + os.pathsep + os.environ["PATH"],
                     "RUNNER_TEMP": str(root), "INSTALL_MARKER": str(marker),
                     "BASH_ENV": "", "ENV": ""},
                capture_output=True, text=True, timeout=15, check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(marker.exists(), "A substituted parser must never reach installation")
            self.assertIn("FAILED", result.stdout + result.stderr)

    def test_only_the_snapshot_actuator_receives_the_submission_token(self):
        workflow = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        submit = workflow["jobs"]["submit"]
        build = next(step for step in submit["steps"]
                     if "scripts/build_python_dependency_snapshot.py" in step.get("run", ""))
        actuator = next(step for step in submit["steps"]
                        if 'gh api --method POST' in step.get("run", ""))
        for environment in (workflow.get("env", {}), submit.get("env", {}), build.get("env", {})):
            self.assertNotIn("GH_TOKEN", environment, "Conversion does not need the write token")
        self.assertNotIn("gh api", build["run"])
        self.assertNotRegex(actuator["run"], r"(?m)^\s*(?:\S*/)?python[0-9.]*\s")
        self.assertNotIn("scripts/build_python_dependency_snapshot.py", actuator["run"])
        self.assertEqual(actuator["env"]["GH_TOKEN"], "${{ github.token }}")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "scripts").mkdir()
            shutil.copyfile(CLI, root / "scripts" / CLI.name)
            (root / "requirements.txt").write_text("direct==1.0\n", encoding="utf-8")
            runtime = root / "runtime"
            runtime.mkdir()
            (runtime / "python-install-report.json").write_text(json.dumps(self.direct_report()))
            interpreter = root / ".dependency-venv" / "bin" / "python"
            interpreter.parent.mkdir(parents=True)
            interpreter.write_text(
                '#!/bin/sh\nprintf "%s" "${GH_TOKEN-unset}" > "$CONVERTER_TOKEN_OBSERVATION"\n'
                'exec "$REAL_PYTHON" "$@"\n', encoding="utf-8",
            )
            interpreter.chmod(0o755)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            fake_gh = fake_bin / "gh"
            fake_gh.write_text(
                '#!/bin/sh\nprintf "%s" "${GH_TOKEN-unset}" > "$ACTUATOR_TOKEN_OBSERVATION"\n'
                'if [ "$2" = --method ]; then exit 0; fi\nprintf "%s\\n" "$GITHUB_SHA"\n',
                encoding="utf-8",
            )
            fake_gh.chmod(0o755)
            converter_token, actuator_token = root / "converter-token", root / "actuator-token"
            environment = {key: value for key, value in os.environ.items()
                           if key not in {"GH_TOKEN", "GITHUB_TOKEN"}}
            environment.update({
                "PATH": str(fake_bin) + os.pathsep + os.environ["PATH"],
                "RUNNER_TEMP": str(runtime), "REAL_PYTHON": sys.executable,
                "CONVERTER_TOKEN_OBSERVATION": str(converter_token),
                "ACTUATOR_TOKEN_OBSERVATION": str(actuator_token),
                "GITHUB_SHA": "a" * 40, "GITHUB_REF": "refs/heads/main",
                "GITHUB_REPOSITORY": "example/project", "GITHUB_RUN_ID": "123",
                "BASH_ENV": "", "ENV": "",
            })
            built = subprocess.run(["bash", "-c", build["run"]], cwd=root, env=environment,
                                   capture_output=True, text=True, timeout=15, check=False)
            self.assertEqual(built.returncode, 0, built.stderr)
            self.assertEqual(converter_token.read_text(), "unset")
            submitted = subprocess.run(
                ["bash", "-c", actuator["run"]], cwd=root,
                env={**environment, "GH_TOKEN": "fixture-submission-token"},
                capture_output=True, text=True, timeout=15, check=False,
            )
            self.assertEqual(submitted.returncode, 0, submitted.stderr)
            self.assertEqual(actuator_token.read_text(), "fixture-submission-token")

    def test_caller_does_not_reach_github_after_the_real_converter_refuses(self):
        workflow = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
        build = next(step for step in workflow["jobs"]["submit"]["steps"]
                     if step.get("name") == "Build the dependency snapshot")
        actuator = next(step for step in workflow["jobs"]["submit"]["steps"]
                        if step.get("name") == "Submit the dependency snapshot")
        self.assertIsNone(actuator.get("if"), "Keep Actions' default success gate")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "scripts").mkdir()
            shutil.copyfile(CLI, root / "scripts" / CLI.name)
            (root / ".dependency-venv").symlink_to(sys.prefix, target_is_directory=True)
            (root / "requirements.txt").write_text("direct==1.0\n", encoding="utf-8")
            runtime = root / "runtime"
            runtime.mkdir()
            report = self.direct_report(requires_dist=["missing>=2"])
            (runtime / "python-install-report.json").write_text(json.dumps(report), encoding="utf-8")
            fake_bin = root / "bin"
            fake_bin.mkdir()
            marker = root / "github-called"
            fake_gh = fake_bin / "gh"
            fake_gh.write_text('#!/bin/sh\nprintf called > "$CALL_MARKER"\nexit 99\n', encoding="utf-8")
            fake_gh.chmod(0o755)
            environment = {
                **os.environ, "PATH": str(fake_bin) + os.pathsep + os.environ["PATH"],
                "CALL_MARKER": str(marker), "RUNNER_TEMP": str(runtime),
                "GITHUB_SHA": "a" * 40, "GITHUB_REF": "refs/heads/main",
                "GITHUB_REPOSITORY": "example/project", "GITHUB_RUN_ID": "123",
                "GH_TOKEN": "unused-fixture", "BASH_ENV": "", "ENV": "",
            }
            result = subprocess.run(
                ["bash", "-c", build["run"] + "\n" + actuator["run"]], cwd=root, env=environment,
                capture_output=True, text=True, timeout=15, check=False,
            )
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("missing resolved dependency", result.stderr)
            self.assertFalse(marker.exists(), "Neither a GitHub read nor submission may follow refusal")


if __name__ == "__main__":
    unittest.main()
