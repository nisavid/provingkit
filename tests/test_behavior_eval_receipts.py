"""Constructed local artifacts exercise the ordinary receipt interface; no model runs."""

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts import behavior_eval_receipts as receipts


class ReceiptWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repository"
        self.repo.mkdir()
        self.private = self.root / "private"
        self.private.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Receipt Tests")
        self.git("config", "user.email", "receipts@example.invalid")
        source = Path(__file__).resolve().parents[1]
        for relative in (
            "release/behavior-eval-policy.json",
            "release/behavior-eval-receipt-v1.schema.json",
            "scripts/behavior_eval_receipts.py",
        ):
            self.write(relative, (source / relative).read_text())
        self.prefix = "plugins/example/skills/writing"
        self.write(self.prefix + "/SKILL.md", "Write a useful answer.\n")
        self.write(
            self.prefix + "/evals/fixtures/case.md", "Observed facts for an answer.\n"
        )
        self.write(
            self.prefix + "/evals/evals.json",
            {
                "skill_name": "writing",
                "evals": [
                    {
                        "id": 1,
                        "name": "answer",
                        "prompt": "Write the answer.",
                        "fixture_paths": ["evals/fixtures/case.md"],
                        "expected_output": "A useful answer with no invented facts.",
                        "expectations": [
                            {
                                "id": "facts",
                                "text": "Only supplied facts.",
                                "severity": "safety",
                            },
                            {
                                "id": "useful",
                                "text": "Useful answer.",
                                "severity": "quality",
                            },
                        ],
                    }
                ],
            },
        )
        self.write(
            self.prefix + "/evals/trigger-evals.json",
            [
                {"query": "Write the answer.", "should_trigger": True},
                {"query": "What time is it?", "should_trigger": False},
            ],
        )
        self.write(
            "release/plugin-content-locks/example.json",
            {"files": {"SKILL.md": "test-lock-identity"}},
        )
        self.spec = {
            "plugin": "example",
            "skill": "writing",
            "content_lock": "release/plugin-content-locks/example.json",
            "evals": self.prefix + "/evals/evals.json",
            "trigger_evals": self.prefix + "/evals/trigger-evals.json",
            "dependencies": [],
            "behavior_inputs": [],
            "shared_references": [],
            "closure_complete": True,
        }
        self.base = self.commit("base")
        self.write(self.prefix + "/SKILL.md", "Write a useful and accurate answer.\n")
        self.candidate = self.commit("candidate")

    def git(self, *arguments):
        result = subprocess.run(
            [
                "git",
                "-c",
                "core.hooksPath=/dev/null",
                "-c",
                "commit.gpgsign=false",
                *arguments,
            ],
            cwd=self.repo,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def write(self, relative, value):
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value) if not isinstance(value, str) else value)

    def commit(self, message):
        self.git("add", ".")
        self.git("commit", "-qm", message)
        return self.git("rev-parse", "HEAD")

    def results(self, snapshot):
        runs = []
        for repetition in (1, 2, 3):
            output = f"output-{repetition}.txt"
            grading = f"grading-{repetition}.json"
            (self.private / output).write_text(
                json.dumps(
                    {
                        "snapshot_sha256": receipts.document_digest(snapshot),
                        "case_id": "1",
                        "repetition": repetition,
                        "model_id": "test-executor-1",
                        "response": "Constructed executor artifact.",
                    }
                )
            )
            (self.private / grading).write_text(
                json.dumps(
                    {
                        "snapshot_sha256": receipts.document_digest(snapshot),
                        "case_id": "1",
                        "repetition": repetition,
                        "model_id": "test-grader-1",
                        "executor_output_sha256": hashlib.sha256(
                            (self.private / output).read_bytes()
                        ).hexdigest(),
                        "expectations": [
                            {"id": "facts", "passed": True},
                            {"id": "useful", "passed": repetition != 3},
                        ],
                    }
                )
            )
            runs.append(
                {
                    "case_id": "1",
                    "repetition": repetition,
                    "executor_output": output,
                    "grading": grading,
                }
            )
        triggers = []
        for case_id, triggered in (("1", True), ("2", False)):
            path = f"trigger-{case_id}.json"
            (self.private / path).write_text(
                json.dumps(
                    {
                        "snapshot_sha256": receipts.document_digest(snapshot),
                        "case_id": case_id,
                        "model_id": "test-executor-1",
                        "observation_kind": "recorded-invocation",
                        "triggered": triggered,
                    }
                )
            )
            triggers.append({"case_id": case_id, "observation": path})
        result = {
            "schema_version": 1,
            "snapshot_sha256": receipts.document_digest(snapshot),
            "executor_model_id": "test-executor-1",
            "grader_model_id": "test-grader-1",
            "runs": runs,
            "triggers": triggers,
        }
        path = self.private / "results.json"
        path.write_text(json.dumps(result))
        return path

    def test_changed_skill_accepts_complete_artifacts_at_quality_threshold(self):
        snapshot = receipts.prepare(self.repo, self.candidate, self.spec)
        receipt = receipts.produce(self.repo, snapshot, self.results(snapshot))
        result = receipts.check(
            self.repo,
            {
                "schema_version": 1,
                "base_revision": self.base,
                "candidate_revision": self.candidate,
                "skills": [self.spec],
                "inventory_complete": True,
                "changed_skills": [],
            },
            {"example/writing": receipt},
        )
        self.assertEqual(result["status"], "pass")
        self.assertEqual(
            result["skills"][0]["trigger_precision"], {"correct": 2, "total": 2}
        )
        self.assertEqual(receipt["candidate_revision"], self.candidate)

    def request(self, candidate=None):
        return {
            "schema_version": 1,
            "base_revision": self.base,
            "candidate_revision": candidate or self.candidate,
            "skills": [self.spec],
            "inventory_complete": True,
            "changed_skills": [],
        }

    def receipt(self):
        snapshot = receipts.prepare(self.repo, self.candidate, self.spec)
        return receipts.produce(self.repo, snapshot, self.results(snapshot))

    def test_one_safety_failure_fails_despite_other_passing_runs(self):
        receipt = self.receipt()
        receipt["runs"][2]["expectations"][0]["passed"] = False
        result = receipts.check(self.repo, self.request(), {"example/writing": receipt})
        self.assertEqual(result["status"], "fail")
        self.assertIn("threshold", result["skills"][0]["reason"])

    def test_duplicate_run_cannot_supply_missing_repetition(self):
        receipt = self.receipt()
        receipt["runs"][2] = receipt["runs"][1]
        result = receipts.check(self.repo, self.request(), {"example/writing": receipt})
        self.assertEqual(result["status"], "fail")
        self.assertIn("coverage", result["skills"][0]["reason"])

    def test_source_change_makes_receipt_stale(self):
        receipt = self.receipt()
        self.write(self.prefix + "/SKILL.md", "Changed after evaluation.")
        later = self.commit("source changed")
        result = receipts.check(
            self.repo, self.request(later), {"example/writing": receipt}
        )
        self.assertEqual(result["status"], "fail")
        self.assertIn("stale", result["skills"][0]["reason"])

    def test_changed_skill_without_receipt_fails_and_unchanged_candidate_is_noop(self):
        result = receipts.check(self.repo, self.request(), {})
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["skills"][0]["reason"], "receipt missing")
        request = self.request()
        request["base_revision"] = self.candidate
        self.assertEqual(
            receipts.check(self.repo, request, {})["status"], "not-required"
        )

    def test_source_mode_change_makes_receipt_stale(self):
        receipt = self.receipt()
        (self.repo / self.prefix / "SKILL.md").chmod(0o755)
        later = self.commit("mode changed")
        result = receipts.check(
            self.repo, self.request(later), {"example/writing": receipt}
        )
        self.assertEqual(result["status"], "fail")

    def test_producer_rejects_duplicate_expectation_in_grading_artifact(self):
        snapshot = receipts.prepare(self.repo, self.candidate, self.spec)
        result_path = self.results(snapshot)
        grading = self.private / "grading-1.json"
        document = json.loads(grading.read_text())
        document["expectations"].insert(0, {"id": "facts", "passed": False})
        grading.write_text(json.dumps(document))
        with self.assertRaisesRegex(receipts.ReceiptError, "coverage"):
            receipts.produce(self.repo, snapshot, result_path)

    def test_receipt_schema_rejects_raw_paths_and_active_attestation(self):
        for field, value in (
            ("private_path", "/private/model-output"),
            ("attestation", {"signed": True}),
        ):
            with self.subTest(field=field):
                receipt = self.receipt()
                receipt[field] = value
                result = receipts.check(
                    self.repo, self.request(), {"example/writing": receipt}
                )
                self.assertEqual(result["status"], "fail")
                self.assertIn("schema", result["skills"][0]["reason"])

    def test_severity_less_expectations_are_unsupported(self):
        path = self.repo / self.prefix / "evals/evals.json"
        document = json.loads(path.read_text())
        document["evals"][0]["expectations"] = ["Give a useful answer."]
        path.write_text(json.dumps(document))
        self.candidate = self.commit("unclassified corpus")
        with self.assertRaisesRegex(receipts.ReceiptError, "severity"):
            receipts.prepare(self.repo, self.candidate, self.spec)

    def test_private_artifact_must_bind_its_original_snapshot(self):
        snapshot = receipts.prepare(self.repo, self.candidate, self.spec)
        results_path = self.results(snapshot)
        # A bare historical response has no observation of this snapshot.
        (self.private / "output-1.txt").write_text("Unbound historical output.")
        with self.assertRaises(receipts.ReceiptError):
            receipts.produce(self.repo, snapshot, results_path)

    def test_waiver_record_cannot_grant_operator_authority(self):
        receipt = self.receipt()
        waiver = {
            key: receipt[key]
            for key in (
                "schema_version",
                "candidate_revision",
                "snapshot",
                "attestation",
            )
        }
        waiver.update(
            kind="waiver",
            reason="Operator-recorded exception awaiting decision verification.",
            operator_decision={"issued_by": "operator", "decision_sha256": "a" * 64},
            expiry={"event": "next-release", "after_release": "test-release-1"},
        )
        result = receipts.check(self.repo, self.request(), {"example/writing": waiver})
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["skills"][0]["status"], "waiver-pending")
        self.assertFalse(result["skills"][0]["operator_authority_verified"])

    def test_policy_cannot_lower_the_accepted_quality_threshold(self):
        policy_path = self.repo / "release/behavior-eval-policy.json"
        policy = json.loads(policy_path.read_text())
        policy["quality"]["required_passes"] = 1
        policy_path.write_text(json.dumps(policy))
        self.candidate = self.commit("weakened policy")
        with self.assertRaisesRegex(receipts.ReceiptError, "policy"):
            receipts.prepare(self.repo, self.candidate, self.spec)

    def test_cli_produces_a_receipt_and_checks_its_containing_commit(self):
        script = Path(receipts.__file__).resolve()
        spec_path = self.private / "spec.json"
        spec_path.write_text(json.dumps(self.spec))

        def cli(*args):
            return subprocess.run(
                ["python", str(script), "--repository", str(self.repo), *args],
                capture_output=True,
                text=True,
            )

        prepared = cli(
            "prepare", "--revision", self.candidate, "--skill-spec", str(spec_path)
        )
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        snapshot = json.loads(prepared.stdout)
        snapshot_path = self.private / "snapshot.json"
        snapshot_path.write_text(prepared.stdout)
        produced = cli(
            "produce",
            "--snapshot",
            str(snapshot_path),
            "--results",
            str(self.results(snapshot)),
        )
        self.assertEqual(produced.returncode, 0, produced.stderr)
        self.write("release/eval-receipts/example/writing.json", produced.stdout)
        containing = self.commit("receipt")
        request_path = self.private / "request.json"
        request_path.write_text(json.dumps(self.request(containing)))
        checked = cli(
            "check",
            "--request",
            str(request_path),
            "--receipts",
            str(self.repo / "release/eval-receipts"),
        )
        self.assertEqual(checked.returncode, 0, checked.stderr)
        result = json.loads(checked.stdout)
        self.assertEqual(result["candidate_revision"], containing)
        self.assertEqual(result["skills"][0]["evaluated_revision"], self.candidate)
        self.assertNotIn(str(self.private), produced.stdout)
        self.assertNotIn("Constructed executor artifact", produced.stdout)

    def test_receipt_rejects_incomplete_extra_or_mistyped_coverage(self):
        original = self.receipt()
        mutations = {
            "missing-run": lambda r: r["runs"].pop(),
            "extra-run": lambda r: r["runs"].append(copy.deepcopy(r["runs"][0])),
            "wrong-case": lambda r: r["runs"][0].update(case_id="unknown"),
            "Boolean-repetition": lambda r: r["runs"][0].update(repetition=True),
            "missing-expectation": lambda r: r["runs"][0]["expectations"].pop(),
            "wrong-severity": lambda r: r["runs"][0]["expectations"][0].update(
                severity="quality"
            ),
            "string-grade": lambda r: r["runs"][0]["expectations"][0].update(
                passed="true"
            ),
            "missing-trigger": lambda r: r["triggers"].pop(),
            "duplicate-trigger": lambda r: r["triggers"].__setitem__(
                1, copy.deepcopy(r["triggers"][0])
            ),
            "wrong-trigger-expectation": lambda r: r["triggers"][1].update(
                expected=True
            ),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                receipt = copy.deepcopy(original)
                mutate(receipt)
                self.assertEqual(
                    receipts.check(
                        self.repo, self.request(), {"example/writing": receipt}
                    )["status"],
                    "fail",
                )

    def test_quality_one_of_three_and_each_trigger_error_fail(self):
        original = self.receipt()
        for coordinate in ("quality", "positive-trigger", "negative-trigger"):
            with self.subTest(coordinate=coordinate):
                receipt = copy.deepcopy(original)
                if coordinate == "quality":
                    receipt["runs"][1]["expectations"][1]["passed"] = False
                else:
                    index = 0 if coordinate == "positive-trigger" else 1
                    receipt["triggers"][index]["triggered"] = not receipt["triggers"][
                        index
                    ]["expected"]
                result = receipts.check(
                    self.repo, self.request(), {"example/writing": receipt}
                )
                self.assertEqual(result["status"], "fail")

    def test_all_bound_input_roles_invalidate_old_results(self):
        self.write("shared/writing.md", "Shared instructions.")
        self.write("shared/style.md", "Behavioral style rules.")
        self.write("runner/settings.json", {"temperature": 0})
        self.spec["dependencies"] = ["runner/settings.json"]
        self.spec["behavior_inputs"] = ["shared/style.md"]
        self.spec["shared_references"] = ["shared/writing.md"]
        self.candidate = self.commit("complete closure")
        receipt = self.receipt()
        paths = [
            self.spec["evals"],
            self.prefix + "/evals/fixtures/case.md",
            self.spec["trigger_evals"],
            self.spec["content_lock"],
            "shared/writing.md",
            "shared/style.md",
            "runner/settings.json",
            "release/behavior-eval-policy.json",
            "release/behavior-eval-receipt-v1.schema.json",
            "scripts/behavior_eval_receipts.py",
        ]
        for relative in paths:
            with self.subTest(path=relative):
                path = self.repo / relative
                old = path.read_bytes()
                path.write_bytes(old + b"\n")
                candidate = self.commit("input change")
                result = receipts.check(
                    self.repo, self.request(candidate), {"example/writing": receipt}
                )
                self.assertEqual(result["status"], "fail")
                path.write_bytes(old)
                self.commit("restore input")

    def test_new_or_removed_source_file_invalidates_complete_inventory(self):
        receipt = self.receipt()
        new_path = self.prefix + "/references/extra.md"
        self.write(new_path, "New evaluated dependency.")
        later = self.commit("new file")
        self.assertEqual(
            receipts.check(
                self.repo, self.request(later), {"example/writing": receipt}
            )["status"],
            "fail",
        )
        (self.repo / new_path).unlink()
        (self.repo / self.prefix / "SKILL.md").unlink()
        later = self.commit("remove skill")
        self.assertEqual(
            receipts.check(
                self.repo, self.request(later), {"example/writing": receipt}
            )["status"],
            "fail",
        )

    def test_added_dependency_cannot_reuse_a_receipt_with_a_smaller_closure(self):
        receipt = self.receipt()
        self.write("shared/new-dependency.md", "New dependency.")
        later = self.commit("dependency")
        request = self.request(later)
        request["skills"] = [dict(self.spec, dependencies=["shared/new-dependency.md"])]
        result = receipts.check(self.repo, request, {"example/writing": receipt})
        self.assertEqual(result["status"], "fail")
        self.assertIn("stale", result["skills"][0]["reason"])

    def test_unrelated_change_and_explicit_empty_inventory_are_noops(self):
        self.write("README.md", "Unrelated documentation.")
        later = self.commit("documentation")
        request = self.request(later)
        request["base_revision"] = self.candidate
        self.assertEqual(
            receipts.check(self.repo, request, {})["status"], "not-required"
        )
        request["skills"] = []
        self.assertEqual(
            receipts.check(self.repo, request, {})["status"], "not-required"
        )

    def test_freshness_only_changes_do_not_select_an_untouched_skill(self):
        for relative in (
            self.spec["content_lock"],
            "scripts/behavior_eval_receipts.py",
            "release/behavior-eval-policy.json",
            "release/behavior-eval-receipt-v1.schema.json",
        ):
            with self.subTest(path=relative):
                path = self.repo / relative
                path.write_bytes(path.read_bytes() + b"\n")
                later = self.commit("freshness input changed")
                request = self.request(later)
                request["base_revision"] = self.candidate
                result = receipts.check(self.repo, request, {})
                self.assertEqual(result["status"], "not-required")
                self.assertEqual(result["skills"], [])

    def test_untouched_unsupported_corpus_is_a_noop_until_explicitly_selected(self):
        for corpus, reason in (
            ({"unsupported": "matrix"}, "unsupported"),
            ("not JSON", "invalid"),
        ):
            with self.subTest(corpus=corpus):
                self.write(self.spec["evals"], corpus)
                before = self.commit("unsupported corpus")
                self.write("README.md", f"Unrelated documentation: {reason}.")
                after = self.commit("unrelated change")
                request = self.request(after)
                request["base_revision"] = before
                result = receipts.check(self.repo, request, {})
                self.assertEqual(result["status"], "not-required")
                request["changed_skills"] = ["example/writing"]
                result = receipts.check(self.repo, request, {})
                self.assertEqual(result["status"], "fail")
                self.assertIn(reason, result["skills"][0]["reason"])

    def test_declared_behavior_inputs_select_skills_but_runner_dependencies_do_not(self):
        self.write("shared/style.md", "Writing style.")
        self.write("evals/owners.json", {"writing": ["shared/style.md"]})
        self.write("runner/settings.json", {"temperature": 0})
        self.spec["behavior_inputs"] = ["shared/style.md", "evals/owners.json"]
        self.spec["dependencies"] = ["runner/settings.json"]
        before = self.commit("declared input roles")
        for relative, expected in (
            ("runner/settings.json", []),
            ("shared/style.md", ["example/writing"]),
            ("evals/owners.json", ["example/writing"]),
        ):
            with self.subTest(path=relative):
                path = self.repo / relative
                path.write_bytes(path.read_bytes() + b"\n")
                after = self.commit("input changed")
                request = self.request(after)
                request["base_revision"] = before
                result = receipts.check(self.repo, request, {})
                self.assertEqual(
                    [item["skill"] for item in result["skills"]], expected
                )
                before = after

    def test_explicit_changed_id_requires_a_receipt_and_fresh_inputs(self):
        receipt = self.receipt()
        request = self.request()
        request["base_revision"] = self.candidate
        request["changed_skills"] = ["example/writing"]
        result = receipts.check(self.repo, request, {})
        self.assertEqual(result["skills"][0]["reason"], "receipt missing")
        self.assertEqual(
            receipts.check(self.repo, request, {"example/writing": receipt})["status"],
            "pass",
        )
        path = self.repo / "scripts/behavior_eval_receipts.py"
        path.write_bytes(path.read_bytes() + b"\n")
        request["candidate_revision"] = self.commit("checker input changed")
        result = receipts.check(self.repo, request, {"example/writing": receipt})
        self.assertEqual(result["status"], "fail")
        self.assertIn("stale evaluated input closure", result["skills"][0]["reason"])

    def test_global_file_declared_behavioral_selects_its_consumer(self):
        self.spec["behavior_inputs"] = [self.spec["content_lock"]]
        path = self.repo / self.spec["content_lock"]
        path.write_bytes(path.read_bytes() + b"\n")
        request = self.request(self.commit("behavioral lock changed"))
        request["base_revision"] = self.candidate
        result = receipts.check(self.repo, request, {})
        self.assertEqual(result["skills"][0]["reason"], "receipt missing")

    def test_nonnormalized_descriptor_paths_are_rejected_before_selection(self):
        self.write("shared/style.md", "Behavioral style rules.")
        request = self.request(self.commit("external behavior added"))
        request["base_revision"] = self.candidate
        for field in (
            "behavior_inputs",
            "shared_references",
            "dependencies",
            "evals",
            "trigger_evals",
            "content_lock",
            "fixture_root",
        ):
            for path in ("shared/./style.md", "shared//style.md", "./shared/style.md"):
                with self.subTest(field=field, path=path):
                    spec = dict(self.spec)
                    spec[field] = [path] if isinstance(spec.get(field), list) else path
                    request["skills"] = [spec]
                    with self.assertRaisesRegex(receipts.ReceiptError, "normalized"):
                        receipts.check(self.repo, request, {})

    def test_external_application_and_trigger_corpora_select_their_skill(self):
        for field in ("evals", "trigger_evals"):
            original = self.repo / self.spec[field]
            self.spec[field] = "evals/external/" + original.name
            self.write(self.spec[field], original.read_text())
        before = self.commit("external corpora")
        for field in ("evals", "trigger_evals"):
            with self.subTest(corpus=field):
                path = self.repo / self.spec[field]
                path.write_bytes(path.read_bytes() + b"\n")
                after = self.commit("external corpus changed")
                request = self.request(after)
                request["base_revision"] = before
                result = receipts.check(self.repo, request, {})
                self.assertEqual(result["skills"][0]["reason"], "receipt missing")
                before = after

    def test_incomplete_discovery_and_unknown_changed_skill_do_not_imply_noop(self):
        for field in ("inventory_complete", "changed_skills"):
            with self.subTest(field=field):
                request = self.request()
                del request[field]
                with self.assertRaises(receipts.ReceiptError):
                    receipts.check(self.repo, request, {})
        request = self.request()
        request["changed_skills"] = ["example/missing"]
        with self.assertRaisesRegex(receipts.ReceiptError, "absent"):
            receipts.check(self.repo, request, {})
        request = self.request()
        request["skills"] = [dict(self.spec, closure_complete=False)]
        with self.assertRaises(receipts.ReceiptError):
            receipts.check(self.repo, request, {})

    def test_shared_reference_change_requires_all_declared_projection_consumers(self):
        self.write("shared/writing.md", "Shared reference.")
        self.spec["shared_references"] = ["shared/writing.md"]
        other_prefix = "plugins/example/skills/neighbor"
        other = dict(
            self.spec, skill="neighbor", evals=other_prefix + "/evals/evals.json"
        )
        other_corpus = json.loads((self.repo / self.spec["evals"]).read_text())
        other_corpus["skill_name"] = "neighbor"
        self.write(other["evals"], other_corpus)
        self.write(other_prefix + "/SKILL.md", "Neighbor skill.")
        self.write(other_prefix + "/evals/fixtures/case.md", "Neighbor fixture.")
        before = self.commit("shared reference")
        self.write("shared/writing.md", "Changed shared reference.")
        after = self.commit("shared reference changed")
        request = self.request(after)
        request.update(base_revision=before, skills=[self.spec, other])
        result = receipts.check(self.repo, request, {})
        self.assertEqual(
            [(item["skill"], item["reason"]) for item in result["skills"]],
            [
                ("example/writing", "receipt missing"),
                ("example/neighbor", "receipt missing"),
            ],
        )

    def test_historical_result_cannot_be_rebound_by_editing_only_manifest(self):
        snapshot = receipts.prepare(self.repo, self.candidate, self.spec)
        results_path = self.results(snapshot)
        self.write(self.prefix + "/SKILL.md", "Different source.")
        later = self.commit("different source")
        new_snapshot = receipts.prepare(self.repo, later, self.spec)
        results = json.loads(results_path.read_text())
        results["snapshot_sha256"] = receipts.document_digest(new_snapshot)
        results_path.write_text(json.dumps(results))
        with self.assertRaisesRegex(receipts.ReceiptError, "another evaluation"):
            receipts.produce(self.repo, new_snapshot, results_path)

    def test_authored_selection_is_not_recorded_invocation(self):
        snapshot = receipts.prepare(self.repo, self.candidate, self.spec)
        results_path = self.results(snapshot)
        path = self.private / "trigger-1.json"
        value = json.loads(path.read_text())
        value["observation_kind"] = "authored-selection"
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(receipts.ReceiptError, "schema"):
            receipts.produce(self.repo, snapshot, results_path)

    def test_missing_and_unknown_artifacts_report_unavailable_evidence(self):
        snapshot = receipts.prepare(self.repo, self.candidate, self.spec)
        results_path = self.results(snapshot)
        results = json.loads(results_path.read_text())
        results["runs"][0]["case_id"] = "unknown"
        results_path.write_text(json.dumps(results))
        with self.assertRaises(receipts.ReceiptError):
            receipts.produce(self.repo, snapshot, results_path)
        results_path = self.results(snapshot)
        (self.private / "output-1.txt").unlink()
        with self.assertRaises(receipts.ReceiptError):
            receipts.produce(self.repo, snapshot, results_path)

    def test_external_fixture_change_requires_its_skill(self):
        self.write("evals/external/fixture.md", "External fixture.")
        self.spec["fixture_root"] = "evals/external"
        document = json.loads((self.repo / self.spec["evals"]).read_text())
        document["evals"][0]["fixture_paths"] = ["fixture.md"]
        self.write(self.spec["evals"], document)
        self.candidate = self.commit("external fixture")
        self.spec["dependencies"] = ["evals/external/fixture.md"]
        with self.assertRaisesRegex(receipts.ReceiptError, "external fixture"):
            receipts.prepare(self.repo, self.candidate, self.spec)
        self.spec["behavior_inputs"] = ["evals/external/fixture.md"]
        receipt = self.receipt()
        self.write("evals/external/fixture.md", "Changed external fixture.")
        later = self.commit("fixture change only")
        request = self.request(later)
        request["base_revision"] = self.candidate
        result = receipts.check(self.repo, request, {"example/writing": receipt})
        self.assertEqual(result["status"], "fail")

        (self.repo / "evals/external/fixture.md").unlink()
        request["candidate_revision"] = self.commit("owned fixture removed")
        result = receipts.check(self.repo, request, {})
        self.assertEqual(result["skills"][0]["reason"], "receipt missing")

    def test_cli_noop_does_not_consume_an_unrelated_malformed_receipt(self):
        self.write("release/eval-receipts/example/writing.json", "not valid JSON")
        later = self.commit("unrelated malformed evidence")
        request = self.request(later)
        request["base_revision"] = self.candidate
        path = self.private / "request.json"
        path.write_text(json.dumps(request))
        checked = subprocess.run(
            [
                "python",
                str(Path(receipts.__file__).resolve()),
                "--repository",
                str(self.repo),
                "check",
                "--request",
                str(path),
                "--receipts",
                str(self.repo / "release/eval-receipts"),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(checked.returncode, 0, checked.stdout)
        self.assertEqual(json.loads(checked.stdout)["status"], "not-required")

    def test_unknown_coordinate_is_rejected_even_when_artifacts_agree(self):
        snapshot = receipts.prepare(self.repo, self.candidate, self.spec)
        results_path = self.results(snapshot)
        results = json.loads(results_path.read_text())
        results["runs"][0]["case_id"] = "99"
        results_path.write_text(json.dumps(results))
        output = self.private / "output-1.txt"
        execution = json.loads(output.read_text())
        execution["case_id"] = "99"
        output.write_text(json.dumps(execution))
        grading = self.private / "grading-1.json"
        grade = json.loads(grading.read_text())
        grade.update(
            case_id="99",
            executor_output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
        )
        grading.write_text(json.dumps(grade))
        with self.assertRaisesRegex(receipts.ReceiptError, "coverage"):
            receipts.produce(self.repo, snapshot, results_path)

    def test_completed_empty_response_is_recorded_but_absent_response_is_rejected(self):
        snapshot = receipts.prepare(self.repo, self.candidate, self.spec)
        results_path = self.results(snapshot)
        output_path = self.private / "output-1.txt"
        output = json.loads(output_path.read_text())
        output["response"] = ""
        output_path.write_text(json.dumps(output))
        grade_path = self.private / "grading-1.json"
        grade = json.loads(grade_path.read_text())
        grade["executor_output_sha256"] = hashlib.sha256(
            output_path.read_bytes()
        ).hexdigest()
        for expectation in grade["expectations"]:
            expectation["passed"] = False
        grade_path.write_text(json.dumps(grade))
        receipt = receipts.produce(self.repo, snapshot, results_path)
        result = receipts.check(self.repo, self.request(), {"example/writing": receipt})
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["skills"][0]["reason"], "threshold failed")
        del output["response"]
        output_path.write_text(json.dumps(output))
        with self.assertRaisesRegex(receipts.ReceiptError, "execution schema"):
            receipts.produce(self.repo, snapshot, results_path)

    def test_rejected_readable_evidence_retains_its_record_identity(self):
        original = self.receipt()
        self.write(self.prefix + "/SKILL.md", "Source changed after evaluation.")
        later = self.commit("stale source")
        result = receipts.check(
            self.repo, self.request(later), {"example/writing": original}
        )
        self.assertEqual(
            result["skills"][0]["receipt_sha256"], receipts.document_digest(original)
        )
        for problem in ("coverage", "schema"):
            with self.subTest(problem=problem):
                receipt = copy.deepcopy(original)
                if problem == "coverage":
                    receipt["runs"].pop()
                else:
                    receipt["unexpected"] = "invalid receipt field"
                result = receipts.check(
                    self.repo, self.request(), {"example/writing": receipt}
                )
                self.assertEqual(result["status"], "fail")
                self.assertEqual(
                    result["skills"][0]["receipt_sha256"],
                    receipts.document_digest(receipt),
                )
                self.assertNotIn("evaluated_revision", result["skills"][0])

    def test_cli_rejects_uncanonicalizable_or_malformed_json_with_raw_identity(self):
        path = self.private / "request.json"
        path.write_text(json.dumps(self.request()))
        receipt_path = self.repo / "release/eval-receipts/example/writing.json"
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        for raw in (
            b'{"unexpected": 1e400}',
            b'{"unexpected": "\\ud800"}',
            b"{malformed",
        ):
            with self.subTest(raw=raw):
                receipt_path.write_bytes(raw)
                checked = subprocess.run(
                    [
                        "python",
                        str(Path(receipts.__file__).resolve()),
                        "--repository",
                        str(self.repo),
                        "check",
                        "--request",
                        str(path),
                        "--receipts",
                        str(self.repo / "release/eval-receipts"),
                    ],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(checked.returncode, 1, checked.stderr)
                result = json.loads(checked.stdout)
                self.assertEqual(result["status"], "fail")
                self.assertEqual(
                    result["skills"][0]["receipt_raw_sha256"],
                    hashlib.sha256(raw).hexdigest(),
                )
                self.assertNotIn("receipt_sha256", result["skills"][0])
                self.assertNotIn("evaluated_revision", result["skills"][0])
                self.assertEqual(checked.stderr, "")

    def test_document_inputs_without_canonical_identity_are_structured_rejections(self):
        for invalid in ({"unexpected": float("inf")}, {"unexpected": chr(0xD800)}):
            with self.subTest(value_type=type(invalid["unexpected"]).__name__):
                result = receipts.check(
                    self.repo, self.request(), {"example/writing": invalid}
                )
                self.assertEqual(result["status"], "fail")
                self.assertNotIn("receipt_sha256", result["skills"][0])
                self.assertNotIn("receipt_raw_sha256", result["skills"][0])


if __name__ == "__main__":
    unittest.main()
