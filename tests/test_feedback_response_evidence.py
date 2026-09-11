import copy
import importlib.util
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "scripts/validate_feedback_response_evidence.py"
spec = importlib.util.spec_from_file_location("feedback_evidence", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class EvidenceTests(unittest.TestCase):
    def test_canonical_request_preserves_unicode_and_newlines(self):
        self.assertEqual(
            module.canonical({"z": "é\r\n", "a": 1}), '{"a":1,"z":"é\\r\\n"}'
        )

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(module.EvidenceError):
            module.strict_json('{"x":1,"x":2}')

    def test_non_relative_paths_rejected(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            for path in ("../x", "/x", "a/../x", "./x", "a//x"):
                with self.subTest(path=path), self.assertRaises(module.EvidenceError):
                    module.read_source(Path(directory), path)

    def test_symlink_parent_rejected(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "real").mkdir()
            (root / "real/x").write_text("x")
            (root / "link").symlink_to(root / "real", target_is_directory=True)
            with self.assertRaises(module.EvidenceError):
                module.read_source(root, "link/x")

class RetainedEvidenceTests(unittest.TestCase):
    def setUp(self):
        import tempfile

        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.case = {
            "id": 4,
            "prompt": "Respond.",
            "files": ["interacting-with-pr-review-feedback/fixtures/example.md"],
            "expected_output": "A contract-preserving response.",
            "expectations": ["Preserve the contract."],
        }
        paths = list(module.CANDIDATE_PATHS) + [
            module.MANIFEST,
            "evals/mergecraft/skills/interacting-with-pr-review-feedback/fixtures/example.md",
            f"{module.SKILL}/scripts/response_runtime.py",
            f"{module.SKILL}/scripts/response_identity_lifecycle.py",
            f"{module.SKILL}/scripts/response_source_owner.py",
            "tests/plugins/mergecraft/interacting-with-pr-review-feedback/test_runtime.py",
            "tests/plugins/mergecraft/interacting-with-pr-review-feedback/fixtures/example.json",
            "plugins/mergecraft/skills/addressing-pr-review-feedback/scripts/review_feedback_state.py",
            "tests/plugins/mergecraft/addressing-pr-review-feedback/test_state.py",
            "tests/plugins/mergecraft/addressing-pr-review-feedback/fixtures/example.json",
        ]
        for path in paths:
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("source")
        (self.root / module.MANIFEST).write_text(
            module.canonical(
                {
                    "skill_name": "interacting-with-pr-review-feedback",
                    "evals": [self.case],
                }
            )
        )
        policy = {
            "4": [
                {
                    "id": "case-4-expectation-1",
                    "text": self.case["expectations"][0],
                    "severity": "safety",
                }
            ]
        }
        prior_text = self.prior_document_text()
        self.document = {
            "schema_version": 2,
            "runs": 3,
            "model": "Daybreak",
            "reasoning_effort": "high",
            "candidate_paths": list(module.CANDIDATE_PATHS),
            "source_sha256": {
                p: module.digest(module.read_source(self.root, p))
                for p in module.source_paths(self.root, [self.case])
            },
            "expectation_policy": policy,
            "authority": copy.deepcopy(module.LOCAL_AUTHORITY),
            "history": module.history_envelope(prior_text),
            "records": [],
        }
        for variant in ("with_skill", "without_skill"):
            for repetition in range(1, 4):
                request = module.executor_request(self.root, self.case, variant)
                identity = f"{variant}-{repetition}"
                response = "This scenario is blocked pending source evidence."
                grades = [
                    {
                        "id": "case-4-expectation-1",
                        "passed": True,
                        "evidence": "Exact observation.",
                    }
                ]
                grading_request = module.canonical(
                    {
                        "executor_request": module.strict_json(request),
                        "response": response,
                        "response_sha256": module.digest(response),
                        "expected_output": self.case["expected_output"],
                        "expectations": policy["4"],
                    }
                )
                grading_response = module.canonical({"expectations": grades})
                self.document["records"].append(
                    {
                        "case_id": 4,
                        "variant": variant,
                        "repetition": repetition,
                        "execution_session_id": identity,
                        "execution_model": "Daybreak",
                        "execution_reasoning_effort": "high",
                        "execution_turn_status": "completed",
                        "request": request,
                        "request_sha256": module.digest(request),
                        "response": response,
                        "response_sha256": module.digest(response),
                        "tool_events": [],
                        "grading_session_id": "grade-" + identity,
                        "grading_model": "Daybreak",
                        "grading_reasoning_effort": "high",
                        "grading_turn_status": "completed",
                        "grading_request": grading_request,
                        "grading_request_sha256": module.digest(grading_request),
                        "grading_response": grading_response,
                        "grading_response_sha256": module.digest(grading_response),
                        "grading_tool_events": [],
                        "grades": grades,
                    }
                )

    @staticmethod
    def historical_exchange(identity="old"):
        request = '{"prompt":"old"}'
        response = "Old result."
        return {
            "job_id": identity,
            "session_id": "session-" + identity,
            "model": "Daybreak",
            "reasoning_effort": "high",
            "request": request,
            "request_sha256": module.digest(request),
            "response": response,
            "response_sha256": module.digest(response),
            "tool_events": [],
            "turn_status": "completed",
        }

    def retained_experiment_text(
        self,
        *,
        selected=False,
        executions=None,
        missing=None,
        completed_execution_count=None,
        raw_grades=None,
    ):
        executions = (
            [self.historical_exchange("retained-execution")]
            if executions is None
            else executions
        )
        missing = ["case-2-with_skill-1"] if missing is None else missing
        raw_grades = [] if raw_grades is None else raw_grades
        if completed_execution_count is None:
            completed_execution_count = sum(
                execution["turn_status"] == "completed" for execution in executions
            )
        return (
            module.canonical(
                {
                    "name": "constructed-retention-fixture",
                    "selected": selected,
                    "reason": "Excluded constructed fixture.",
                    "stopped_at": "2026-09-09T00:00:00+00:00",
                    "launcher_exit_code": 130,
                    "planned_coordinates": len(executions) + len(missing),
                    "completed_execution_count": completed_execution_count,
                    "uncompleted_or_unrecorded_job_ids": missing,
                    "frozen_inputs": {"candidate": "constructed"},
                    "raw_executions": executions,
                    "raw_grades": raw_grades,
                }
            )
            + "\n"
        )

    def prior_document_text(self):
        prior = {
            "schema_version": 1,
            "runs": 3,
            "model": "Daybreak",
            "reasoning_effort": "high",
            "candidate_paths": ["old"],
            "source_sha256": {"old": "0" * 64},
            "expectation_policy": {},
            "records": [
                {
                    "request": "old selected request",
                    "request_sha256": module.digest("old selected request"),
                    "response": "old selected response",
                    "response_sha256": module.digest("old selected response"),
                    "tool_events": [],
                    "grading_request": "old grade request",
                    "grading_request_sha256": module.digest("old grade request"),
                    "grading_response": "old grade response",
                    "grading_response_sha256": module.digest("old grade response"),
                }
            ],
            "method": {"authority": "Unsigned local development observation."},
            "unqualified_path_labeled_handoff": {
                "selected": False,
                "reason": "Path labels were exposed.",
                "executions": [self.historical_exchange("path-labeled")],
            },
            "prior_experiments": [
                {
                    "schema_version": 1,
                    "selected": False,
                    "reason": "Candidate was insufficient.",
                    "records": [
                        {
                            "execution": self.historical_exchange("old-execution"),
                            "grading": self.historical_exchange("old-grading"),
                        }
                    ],
                }
            ],
            "isolation_correction": "Later selected requests remove path labels.",
            "grading_contract_audit": self.historical_exchange("grading-audit"),
        }
        return module.canonical(prior) + "\n"

    def unchecked_history_with_experiment(self, experiment):
        value = module.strict_json(experiment)
        history = module.history_envelope(self.prior_document_text())
        history["additional_experiments"].append(
            {
                "document": experiment,
                "document_sha256": module.digest(experiment),
                "selected": False,
                "exclusion_reason": value["reason"],
                "availability": module.history_availability(value),
                "completion": {
                    "planned_coordinates": value["planned_coordinates"],
                    "recorded_executions": len(value["raw_executions"]),
                    "uncompleted_or_unrecorded_coordinates": len(
                        value["uncompleted_or_unrecorded_job_ids"]
                    ),
                    "recorded_grades": len(value["raw_grades"]),
                    "state": "complete"
                    if not value["uncompleted_or_unrecorded_job_ids"]
                    and value["completed_execution_count"]
                    == value["planned_coordinates"]
                    else "partial",
                },
            }
        )
        return history

    def sync_grading_response(self, record):
        record["grading_response"] = module.canonical({"expectations": record["grades"]})
        record["grading_response_sha256"] = module.digest(record["grading_response"])

    def sync_executor_request(self, record, request):
        record["request"] = module.canonical(request)
        record["request_sha256"] = module.digest(record["request"])
        grading_request = module.strict_json(record["grading_request"])
        grading_request["executor_request"] = request
        record["grading_request"] = module.canonical(grading_request)
        record["grading_request_sha256"] = module.digest(record["grading_request"])

    def validate(self):
        path = self.root / module.EVIDENCE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(module.canonical(self.document))
        return module.validate(self.root)

    def test_complete_bound_evidence_passes_and_scenario_block_is_graded(self):
        self.assertEqual(self.validate()["runs"], 3)

    def test_executor_gets_content_without_fixture_or_candidate_path_labels(self):
        request = module.strict_json(self.document["records"][0]["request"])
        self.assertEqual(request["fixture"], ["source"])
        self.assertEqual(request["candidate_bundle"], ["source"] * 3)
        self.assertNotIn("fixtures/example.md", self.document["records"][0]["request"])

    def test_identity_helper_is_source_evidence_not_executor_prompt_content(self):
        helper = f"{module.SKILL}/scripts/response_identity_lifecycle.py"
        self.assertIn(helper, module.source_paths(self.root, [self.case]))
        self.assertNotIn(helper, module.CANDIDATE_PATHS)
        request = module.strict_json(self.document["records"][0]["request"])
        self.assertEqual(
            request["candidate_bundle"],
            [
                module.read_source(self.root, path).decode("utf-8")
                for path in module.CANDIDATE_PATHS
            ],
        )

    def test_source_owner_helper_is_source_evidence_not_executor_prompt_content(self):
        helper = f"{module.SKILL}/scripts/response_source_owner.py"
        self.assertIn(helper, module.source_paths(self.root, [self.case]))
        self.assertNotIn(helper, module.CANDIDATE_PATHS)

    def test_stale_source_rejected(self):
        (self.root / module.CANDIDATE_PATHS[0]).write_text("changed")
        with self.assertRaisesRegex(module.EvidenceError, "source digest"):
            self.validate()

    def test_stale_identity_helper_source_evidence_is_rejected(self):
        helper = self.root / module.SKILL / "scripts/response_identity_lifecycle.py"
        helper.write_text("changed helper", encoding="utf-8")
        with self.assertRaisesRegex(module.EvidenceError, "source digest"):
            self.validate()

    def test_stale_source_owner_helper_source_evidence_is_rejected(self):
        helper = self.root / module.SKILL / "scripts/response_source_owner.py"
        helper.write_text("changed source-owner helper", encoding="utf-8")
        with self.assertRaisesRegex(module.EvidenceError, "source digest"):
            self.validate()

    def test_leaked_expectation_in_request_rejected_even_with_valid_digest(self):
        record = self.document["records"][0]
        request = module.strict_json(record["request"])
        request["expectations"] = self.case["expectations"]
        record["request"] = module.canonical(request)
        record["request_sha256"] = module.digest(record["request"])
        with self.assertRaisesRegex(module.EvidenceError, "frozen inputs"):
            self.validate()

    def test_duplicate_session_rejected(self):
        record = self.document["records"][0]
        record["grading_session_id"] = record["execution_session_id"]
        with self.assertRaisesRegex(module.EvidenceError, "sessions"):
            self.validate()

    def test_safety_requires_every_repetition(self):
        record = self.document["records"][0]
        record["grades"][0]["passed"] = False
        self.sync_grading_response(record)
        with self.assertRaisesRegex(module.EvidenceError, "threshold"):
            self.validate()

    def test_evidence_cannot_downgrade_current_expectation_to_quality(self):
        self.document["expectation_policy"]["4"][0]["severity"] = "quality"
        for record in self.document["records"]:
            request = module.strict_json(record["grading_request"])
            request["expectations"] = self.document["expectation_policy"]["4"]
            record["grading_request"] = module.canonical(request)
            record["grading_request_sha256"] = module.digest(record["grading_request"])
        for record in (self.document["records"][0], self.document["records"][3]):
            record["grades"][0]["passed"] = False
            self.sync_grading_response(record)
        with self.assertRaisesRegex(module.EvidenceError, "expectation policy"):
            self.validate()

    def test_dynamically_added_manifest_expectation_is_also_fixed_as_safety(self):
        expectation = "Preserve a dynamically added safety expectation."
        self.case["expectations"].append(expectation)
        (self.root / module.MANIFEST).write_text(
            module.canonical(
                {
                    "skill_name": "interacting-with-pr-review-feedback",
                    "evals": [self.case],
                }
            )
        )
        self.document["source_sha256"][module.MANIFEST] = module.digest(
            module.read_source(self.root, module.MANIFEST)
        )
        added_policy = {
            "id": "case-4-expectation-2",
            "text": expectation,
            "severity": "quality",
        }
        self.document["expectation_policy"]["4"].append(added_policy)
        for record in self.document["records"]:
            record["grades"].append(
                {
                    "id": added_policy["id"],
                    "passed": record["repetition"] != 1,
                    "evidence": "Exact dynamic observation.",
                }
            )
            record["grading_request"] = module.grading_request(
                self.case,
                record["request"],
                record["response"],
                record["response_sha256"],
                self.document["expectation_policy"]["4"],
            )
            record["grading_request_sha256"] = module.digest(
                record["grading_request"]
            )
            self.sync_grading_response(record)

        with self.assertRaisesRegex(module.EvidenceError, "expectation policy"):
            self.validate()

    def test_duplicate_coordinate_rejected(self):
        self.document["records"][1]["repetition"] = 1
        with self.assertRaisesRegex(module.EvidenceError, "coordinate"):
            self.validate()

    def test_missing_grading_field_rejected(self):
        del self.document["records"][0]["grading_request"]
        with self.assertRaisesRegex(module.EvidenceError, "record schema"):
            self.validate()

    def test_unknown_record_field_rejected(self):
        self.document["records"][0]["attested_by_provider"] = True
        with self.assertRaisesRegex(module.EvidenceError, "record schema"):
            self.validate()

    def test_unknown_top_level_field_rejected(self):
        self.document["provider_attestation"] = "claimed"
        with self.assertRaisesRegex(module.EvidenceError, "top-level schema"):
            self.validate()

    def test_altered_grading_request_digest_rejected(self):
        self.document["records"][0]["grading_request_sha256"] = "0" * 64
        with self.assertRaisesRegex(module.EvidenceError, "grading request digest"):
            self.validate()

    def test_grading_request_response_mismatch_rejected(self):
        record = self.document["records"][0]
        request = module.strict_json(record["grading_request"])
        request["response"] = "Another response."
        record["grading_request"] = module.canonical(request)
        record["grading_request_sha256"] = module.digest(record["grading_request"])
        with self.assertRaisesRegex(module.EvidenceError, "canonical grading request"):
            self.validate()

    def test_grading_request_expected_output_mismatch_rejected(self):
        record = self.document["records"][0]
        request = module.strict_json(record["grading_request"])
        request["expected_output"] = "Altered."
        record["grading_request"] = module.canonical(request)
        record["grading_request_sha256"] = module.digest(record["grading_request"])
        with self.assertRaisesRegex(module.EvidenceError, "canonical grading request"):
            self.validate()

    def test_grading_request_expectations_mismatch_rejected(self):
        record = self.document["records"][0]
        request = module.strict_json(record["grading_request"])
        request["expectations"][0]["text"] = "Altered."
        record["grading_request"] = module.canonical(request)
        record["grading_request_sha256"] = module.digest(record["grading_request"])
        with self.assertRaisesRegex(module.EvidenceError, "canonical grading request"):
            self.validate()

    def test_grading_response_digest_mismatch_rejected(self):
        self.document["records"][0]["grading_response_sha256"] = "0" * 64
        with self.assertRaisesRegex(module.EvidenceError, "grading response digest"):
            self.validate()

    def test_grades_disagree_with_grading_response_rejected(self):
        self.document["records"][0]["grades"][0]["passed"] = False
        with self.assertRaisesRegex(module.EvidenceError, "grades differ"):
            self.validate()

    def test_unknown_grading_response_field_rejected(self):
        record = self.document["records"][0]
        response = module.strict_json(record["grading_response"])
        response["summary"] = "extra"
        record["grading_response"] = module.canonical(response)
        record["grading_response_sha256"] = module.digest(record["grading_response"])
        with self.assertRaisesRegex(module.EvidenceError, "grading response schema"):
            self.validate()

    def test_empty_selected_output_rejected(self):
        record = self.document["records"][0]
        record["response"] = ""
        record["response_sha256"] = module.digest("")
        with self.assertRaisesRegex(module.EvidenceError, "nonempty"):
            self.validate()

    def test_non_completed_selected_execution_rejected(self):
        self.document["records"][0]["execution_turn_status"] = "failed"
        with self.assertRaisesRegex(module.EvidenceError, "execution did not complete"):
            self.validate()

    def test_failure_payload_with_passing_grades_is_rejected_by_typed_state(self):
        record = self.document["records"][0]
        record["execution_turn_status"] = "interrupted"
        record["response"] = "Transport failed before a complete response."
        record["response_sha256"] = module.digest(record["response"])
        with self.assertRaisesRegex(module.EvidenceError, "execution did not complete"):
            self.validate()

    def test_non_completed_grading_rejected(self):
        self.document["records"][0]["grading_turn_status"] = "failed"
        with self.assertRaisesRegex(module.EvidenceError, "grading did not complete"):
            self.validate()

    def test_selected_model_metadata_mismatch_rejected(self):
        self.document["records"][0]["execution_model"] = "other"
        with self.assertRaisesRegex(module.EvidenceError, "execution model"):
            self.validate()

    def test_missing_declared_history_rejected(self):
        del self.document["history"]
        with self.assertRaisesRegex(module.EvidenceError, "top-level schema"):
            self.validate()

    def test_altered_prior_history_digest_rejected(self):
        self.document["history"]["prior_document_sha256"] = "0" * 64
        with self.assertRaisesRegex(module.EvidenceError, "prior document digest"):
            self.validate()

    def test_constructed_history_retains_exact_documents_and_digest_binding(self):
        prior_text = self.prior_document_text()
        experiment_text = self.retained_experiment_text()

        history = module.history_envelope(prior_text, [experiment_text])
        module.validate_history(history)

        retained = history["additional_experiments"][0]
        self.assertEqual(history["prior_document"], prior_text)
        self.assertEqual(history["prior_document_sha256"], module.digest(prior_text))
        self.assertEqual(retained["document"], experiment_text)
        self.assertEqual(retained["document_sha256"], module.digest(experiment_text))
        self.assertFalse(retained["selected"])
        self.assertEqual(retained["availability"]["exchange_records"], 1)
        self.assertEqual(retained["availability"]["grading_linkage"], "unavailable")
        self.assertEqual(
            retained["completion"],
            {
                "planned_coordinates": 2,
                "recorded_executions": 1,
                "uncompleted_or_unrecorded_coordinates": 1,
                "recorded_grades": 0,
                "state": "partial",
            },
        )

    def test_duplicate_additional_history_document_rejected(self):
        experiment = self.retained_experiment_text()
        history = module.history_envelope(self.prior_document_text(), [experiment])
        history["additional_experiments"].append(
            copy.deepcopy(history["additional_experiments"][0])
        )

        with self.assertRaisesRegex(
            module.EvidenceError, "additional experiment document digest inventory"
        ):
            module.validate_history(history)

    def test_unique_additional_history_documents_remain_accepted(self):
        first = self.retained_experiment_text()
        second_value = module.strict_json(first)
        second_value["name"] = "second-constructed-retention-fixture"
        second = module.canonical(second_value) + "\n"

        history = module.history_envelope(self.prior_document_text(), [first, second])
        module.validate_history(history)

        self.assertEqual(
            [entry["document"] for entry in history["additional_experiments"]],
            [first, second],
        )
        self.assertEqual(
            [entry["document_sha256"] for entry in history["additional_experiments"]],
            [module.digest(first), module.digest(second)],
        )

    def test_altered_retained_experiment_document_digest_rejected(self):
        self.document["history"] = module.history_envelope(
            self.prior_document_text(), [self.retained_experiment_text()]
        )
        self.document["history"]["additional_experiments"][0][
            "document_sha256"
        ] = "0" * 64
        with self.assertRaisesRegex(module.EvidenceError, "experiment document digest"):
            self.validate()

    def test_retained_experiment_requires_declared_exclusion(self):
        with self.assertRaisesRegex(module.EvidenceError, "must be excluded"):
            module.history_envelope(
                self.prior_document_text(),
                [self.retained_experiment_text(selected=True)],
            )

    def test_retained_experiment_reports_partial_availability(self):
        retained = module.history_envelope(
            self.prior_document_text(), [self.retained_experiment_text()]
        )["additional_experiments"][0]

        self.assertEqual(retained["availability"]["exchange_records"], 1)
        self.assertEqual(
            retained["availability"]["completion_state"], "recorded_for_all"
        )
        self.assertEqual(retained["completion"]["state"], "partial")
        self.assertEqual(retained["completion"]["recorded_executions"], 1)
        self.assertEqual(
            retained["completion"]["uncompleted_or_unrecorded_coordinates"], 1
        )

    def test_failed_retained_execution_counts_as_uncompleted_through_validate_history(
        self,
    ):
        failed = self.historical_exchange("failed")
        failed["turn_status"] = "failed"
        experiment = self.retained_experiment_text(
            executions=[failed],
            missing=[],
            completed_execution_count=0,
        )
        history = module.history_envelope(
            self.prior_document_text(), [experiment]
        )

        module.validate_history(history)

        self.assertEqual(
            history["additional_experiments"][0]["completion"],
            {
                "planned_coordinates": 1,
                "recorded_executions": 1,
                "uncompleted_or_unrecorded_coordinates": 1,
                "recorded_grades": 0,
                "state": "partial",
            },
        )

    def test_interrupted_retained_execution_counts_as_uncompleted_through_validate_history(
        self,
    ):
        interrupted = self.historical_exchange("interrupted")
        interrupted["turn_status"] = "interrupted"
        experiment = self.retained_experiment_text(
            executions=[interrupted],
            missing=[],
            completed_execution_count=0,
        )
        history = module.history_envelope(
            self.prior_document_text(), [experiment]
        )

        module.validate_history(history)

        self.assertEqual(
            history["additional_experiments"][0]["completion"],
            {
                "planned_coordinates": 1,
                "recorded_executions": 1,
                "uncompleted_or_unrecorded_coordinates": 1,
                "recorded_grades": 0,
                "state": "partial",
            },
        )

    def test_all_complete_retained_history_conserves_planned_coordinates_through_validate_history(
        self,
    ):
        executions = [
            self.historical_exchange("completed-1"),
            self.historical_exchange("completed-2"),
        ]
        experiment = self.retained_experiment_text(
            executions=executions,
            missing=[],
            completed_execution_count=2,
        )
        history = module.history_envelope(
            self.prior_document_text(), [experiment]
        )

        module.validate_history(history)

        self.assertEqual(
            history["additional_experiments"][0]["completion"],
            {
                "planned_coordinates": 2,
                "recorded_executions": 2,
                "uncompleted_or_unrecorded_coordinates": 0,
                "recorded_grades": 0,
                "state": "complete",
            },
        )

    def test_absent_retained_coordinates_count_as_unrecorded_through_validate_history(
        self,
    ):
        experiment = self.retained_experiment_text(
            executions=[self.historical_exchange("completed")],
            missing=["absent-1", "absent-2"],
            completed_execution_count=1,
        )
        history = module.history_envelope(
            self.prior_document_text(), [experiment]
        )

        module.validate_history(history)

        self.assertEqual(
            history["additional_experiments"][0]["completion"],
            {
                "planned_coordinates": 3,
                "recorded_executions": 1,
                "uncompleted_or_unrecorded_coordinates": 2,
                "recorded_grades": 0,
                "state": "partial",
            },
        )

    def test_mixed_retained_outcomes_conserve_planned_coordinates_through_validate_history(
        self,
    ):
        completed = self.historical_exchange("completed")
        failed = self.historical_exchange("failed")
        failed["turn_status"] = "failed"
        interrupted = self.historical_exchange("interrupted")
        interrupted["turn_status"] = "interrupted"
        experiment = self.retained_experiment_text(
            executions=[completed, failed, interrupted],
            missing=["absent"],
            completed_execution_count=1,
        )
        history = module.history_envelope(
            self.prior_document_text(), [experiment]
        )

        module.validate_history(history)

        self.assertEqual(
            history["additional_experiments"][0]["completion"],
            {
                "planned_coordinates": 4,
                "recorded_executions": 3,
                "uncompleted_or_unrecorded_coordinates": 3,
                "recorded_grades": 0,
                "state": "partial",
            },
        )

    def test_validate_history_rejects_authored_missing_only_completion_summary(
        self,
    ):
        completed = self.historical_exchange("completed")
        failed = self.historical_exchange("failed")
        failed["turn_status"] = "failed"
        experiment = self.retained_experiment_text(
            executions=[completed, failed],
            missing=["absent"],
            completed_execution_count=1,
        )
        history = module.history_envelope(
            self.prior_document_text(), [experiment]
        )
        history["additional_experiments"][0]["completion"][
            "uncompleted_or_unrecorded_coordinates"
        ] = 1

        with self.assertRaisesRegex(module.EvidenceError, "history envelope drift"):
            module.validate_history(history)

    def test_retained_experiment_does_not_enter_selected_matrix(self):
        selected_records = copy.deepcopy(self.document["records"])
        self.document["history"] = module.history_envelope(
            self.prior_document_text(), [self.retained_experiment_text()]
        )

        validated = self.validate()

        self.assertEqual(validated["records"], selected_records)
        self.assertEqual(len(validated["records"]), 6)

    def test_failed_and_interrupted_retained_executions_remain_exact_and_unselected(
        self,
    ):
        failed = self.historical_exchange("failed")
        failed["turn_status"] = "failed"
        interrupted = self.historical_exchange("interrupted")
        interrupted["turn_status"] = "interrupted"
        experiment = self.retained_experiment_text(
            executions=[failed, interrupted],
            missing=[],
            completed_execution_count=0,
        )

        retained = module.history_envelope(
            self.prior_document_text(), [experiment]
        )["additional_experiments"][0]

        self.assertEqual(retained["document"], experiment)
        self.assertFalse(retained["selected"])
        self.assertEqual(retained["completion"]["state"], "partial")

    def test_duplicate_retained_grading_coordinate_rejected(self):
        grade = self.historical_exchange("retained-execution")
        experiment = self.retained_experiment_text(raw_grades=[grade, grade])

        with self.assertRaisesRegex(
            module.EvidenceError, "grading coordinate inventory"
        ):
            module.validate_history(self.unchecked_history_with_experiment(experiment))

    def test_retained_grading_coordinate_without_execution_rejected(self):
        grade = self.historical_exchange("orphan-grade")
        experiment = self.retained_experiment_text(raw_grades=[grade])

        with self.assertRaisesRegex(
            module.EvidenceError, "grading coordinate inventory"
        ):
            module.validate_history(self.unchecked_history_with_experiment(experiment))

    def test_malformed_retention_records_rejected(self):
        malformed = module.strict_json(self.retained_experiment_text())
        cases = []
        wrong_count = copy.deepcopy(malformed)
        wrong_count["completed_execution_count"] = 0
        cases.append((wrong_count, "completed execution count mismatch"))
        missing_digest = copy.deepcopy(malformed)
        del missing_digest["raw_executions"][0]["response_sha256"]
        cases.append((missing_digest, "launcher record schema"))
        overlapping = copy.deepcopy(malformed)
        overlapping["uncompleted_or_unrecorded_job_ids"] = [
            overlapping["raw_executions"][0]["job_id"]
        ]
        cases.append((overlapping, "execution coordinate inventory"))

        for value, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(
                module.EvidenceError, message
            ):
                module.history_envelope(
                    self.prior_document_text(), [module.canonical(value)]
                )

    def test_altered_history_entry_rejected(self):
        self.document["history"]["entries"][0]["raw_sha256"] = "0" * 64
        with self.assertRaisesRegex(module.EvidenceError, "history entry"):
            self.validate()

    def test_missing_history_exclusion_reason_rejected(self):
        self.document["history"]["entries"][0]["exclusion_reason"] = ""
        with self.assertRaisesRegex(module.EvidenceError, "exclusion reason"):
            self.validate()

    def test_selected_unqualified_history_rejected(self):
        self.document["history"]["entries"][0]["selected"] = True
        with self.assertRaisesRegex(module.EvidenceError, "unqualified history"):
            self.validate()

    def test_unknown_history_field_rejected(self):
        self.document["history"]["provider_ledger"] = []
        with self.assertRaisesRegex(module.EvidenceError, "history schema"):
            self.validate()

    def test_missing_authority_boundary_rejected(self):
        del self.document["authority"]
        with self.assertRaisesRegex(module.EvidenceError, "top-level schema"):
            self.validate()

    def test_altered_authority_boundary_rejected(self):
        self.document["authority"]["session_identity"] = "authenticated"
        with self.assertRaisesRegex(module.EvidenceError, "authority boundary"):
            self.validate()

    def test_legacy_missing_completion_is_marked_unavailable_and_unqualified(self):
        entry = next(
            entry
            for entry in self.document["history"]["entries"]
            if entry["kind"] == "prior_selected_records"
        )
        self.assertFalse(entry["selected"])
        self.assertEqual(entry["availability"]["completion_state"], "unavailable")
        self.assertEqual(self.validate()["history"]["prior_document"], self.prior_document_text())

    def test_schema2_predecessor_repeats_refresh_with_exact_unselected_history(self):
        experiment = self.retained_experiment_text()
        self.document["history"] = module.history_envelope(
            self.prior_document_text(), [experiment]
        )
        module.validate(self.root, document=self.document)
        first_text = module.canonical(self.document) + "\n"

        second = copy.deepcopy(self.document)
        second["history"] = module.history_envelope(first_text)
        module.validate(self.root, document=second)
        second_text = module.canonical(second) + "\n"

        third = copy.deepcopy(self.document)
        third["history"] = module.history_envelope(second_text)
        module.validate(self.root, document=third)

        self.assertEqual(third["history"]["prior_document"], second_text)
        self.assertEqual(
            module.strict_json(third["history"]["prior_document"])["history"][
                "prior_document"
            ],
            first_text,
        )
        self.assertEqual(
            second["history"]["entries"][1:], self.document["history"]["entries"]
        )
        self.assertEqual(third["history"]["entries"][1:], second["history"]["entries"])
        self.assertEqual(
            third["history"]["entries"][0]["raw_json"],
            module.canonical(second["records"]),
        )
        self.assertEqual(
            third["history"]["entries"][0]["raw_sha256"],
            module.digest(module.canonical(second["records"])),
        )
        self.assertEqual(
            third["history"]["entries"][0]["availability"]["completion_state"],
            "recorded_for_all",
        )
        self.assertTrue(
            all(entry["selected"] is False for entry in third["history"]["entries"])
        )
        self.assertEqual(
            third["history"]["additional_experiments"],
            self.document["history"]["additional_experiments"],
        )
        self.assertEqual(
            third["history"]["additional_experiments"][0]["document"], experiment
        )

    def test_schema2_predecessor_selected_threshold_is_not_reinterpreted(self):
        prior = copy.deepcopy(self.document)
        prior["records"][0]["grades"][0]["passed"] = False
        self.sync_grading_response(prior["records"][0])

        with self.assertRaisesRegex(module.EvidenceError, "candidate threshold"):
            module.history_envelope(module.canonical(prior) + "\n")

    def test_schema2_predecessor_rejects_candidate_bytes_not_bound_to_own_source_map(
        self,
    ):
        predecessor = copy.deepcopy(self.document)
        record = next(
            record
            for record in predecessor["records"]
            if record["variant"] == "with_skill"
        )
        request = module.strict_json(record["request"])
        candidate_path = predecessor["candidate_paths"][0]
        self.assertEqual(
            module.digest(request["candidate_bundle"][0]),
            predecessor["source_sha256"][candidate_path],
        )

        request["candidate_bundle"][0] = "changed candidate bytes"
        self.sync_executor_request(record, request)

        with self.assertRaisesRegex(
            module.EvidenceError, "schema2 predecessor source binding"
        ):
            module.history_envelope(module.canonical(predecessor) + "\n")

    def test_schema2_predecessor_checks_every_candidate_position_across_repetitions(
        self,
    ):
        for candidate_index in range(len(module.CANDIDATE_PATHS)):
            for repetition in (1, 3):
                with self.subTest(
                    candidate_index=candidate_index, repetition=repetition
                ):
                    predecessor = copy.deepcopy(self.document)
                    record = next(
                        record
                        for record in predecessor["records"]
                        if record["variant"] == "with_skill"
                        and record["repetition"] == repetition
                    )
                    request = module.strict_json(record["request"])
                    request["candidate_bundle"][candidate_index] = (
                        f"changed candidate {candidate_index} repetition {repetition}"
                    )
                    self.sync_executor_request(record, request)

                    with self.assertRaisesRegex(
                        module.EvidenceError,
                        "schema2 predecessor source binding",
                    ):
                        module.history_envelope(module.canonical(predecessor) + "\n")

    def test_schema2_predecessor_candidate_bundle_relations_fail_closed(self):
        cases = []

        nonempty_baseline = copy.deepcopy(self.document)
        baseline_record = next(
            record
            for record in nonempty_baseline["records"]
            if record["variant"] == "without_skill"
        )
        baseline_request = module.strict_json(baseline_record["request"])
        baseline_request["candidate_bundle"] = ["source"]
        self.sync_executor_request(baseline_record, baseline_request)
        cases.append(
            (nonempty_baseline, "schema2 predecessor source binding")
        )

        for bundle in (
            ["source"] * (len(module.CANDIDATE_PATHS) - 1),
            ["source"] * (len(module.CANDIDATE_PATHS) + 1),
        ):
            predecessor = copy.deepcopy(self.document)
            record = next(
                record
                for record in predecessor["records"]
                if record["variant"] == "with_skill"
            )
            request = module.strict_json(record["request"])
            request["candidate_bundle"] = bundle
            self.sync_executor_request(record, request)
            cases.append((predecessor, "schema2 predecessor source binding"))

        duplicate_path = copy.deepcopy(self.document)
        duplicate_path["candidate_paths"][1] = duplicate_path["candidate_paths"][0]
        cases.append((duplicate_path, "candidate paths invalid"))

        unsupported_variant = copy.deepcopy(self.document)
        unsupported_variant["records"][0]["variant"] = "unsupported"
        cases.append((unsupported_variant, "record coordinate invalid"))

        for index, (predecessor, message) in enumerate(cases):
            with self.subTest(case=index), self.assertRaisesRegex(
                module.EvidenceError, message
            ):
                module.history_envelope(module.canonical(predecessor) + "\n")

    def test_repeated_refresh_keeps_old_candidate_sources_bound_to_old_predecessor(
        self,
    ):
        first = copy.deepcopy(self.document)
        module.validate(self.root, document=first)
        first_text = module.canonical(first) + "\n"

        for index, path in enumerate(module.CANDIDATE_PATHS):
            (self.root / path).write_text(f"current source {index}")

        second = copy.deepcopy(self.document)
        second["source_sha256"] = {
            path: module.digest(module.read_source(self.root, path))
            for path in module.source_paths(self.root, [self.case])
        }
        for record in second["records"]:
            request = module.strict_json(
                module.executor_request(self.root, self.case, record["variant"])
            )
            self.sync_executor_request(record, request)
        second["history"] = module.history_envelope(first_text)
        module.validate(self.root, document=second)
        second_text = module.canonical(second) + "\n"

        third = copy.deepcopy(second)
        third["history"] = module.history_envelope(second_text)
        module.validate(self.root, document=third)

        old = module.strict_json(first_text)
        new = module.strict_json(second_text)
        old_request = module.strict_json(
            next(
                record
                for record in old["records"]
                if record["variant"] == "with_skill"
            )["request"]
        )
        new_request = module.strict_json(
            next(
                record
                for record in new["records"]
                if record["variant"] == "with_skill"
            )["request"]
        )
        self.assertEqual(old_request["candidate_bundle"], ["source"] * 3)
        self.assertEqual(
            new_request["candidate_bundle"],
            ["current source 0", "current source 1", "current source 2"],
        )
        self.assertEqual(second["history"]["prior_document"], first_text)
        self.assertEqual(third["history"]["prior_document"], second_text)
        self.assertEqual(
            module.strict_json(third["history"]["prior_document"])["history"][
                "prior_document"
            ],
            first_text,
        )

    def test_unsupported_and_malformed_declared_predecessors_fail_closed(self):
        cases = []
        unsupported = copy.deepcopy(self.document)
        unsupported["schema_version"] = 3
        cases.append((unsupported, "unsupported predecessor schema"))
        undeclared = copy.deepcopy(self.document)
        del undeclared["schema_version"]
        cases.append((undeclared, "predecessor schema version"))
        malformed = copy.deepcopy(self.document)
        malformed["provider_attestation"] = True
        cases.append((malformed, "schema2 predecessor schema"))
        incomplete_sources = copy.deepcopy(self.document)
        del incomplete_sources["source_sha256"][
            incomplete_sources["candidate_paths"][0]
        ]
        cases.append((incomplete_sources, "source inventory incomplete"))

        for predecessor, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(
                module.EvidenceError, message
            ):
                module.history_envelope(module.canonical(predecessor) + "\n")


if __name__ == "__main__":
    unittest.main()
