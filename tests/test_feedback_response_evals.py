import copy
import importlib.util
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import test_feedback_response_evidence as fixtures


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "feedback_response_evals", ROOT / "scripts/feedback_response_evals.py"
)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
evidence = fixtures.module


class EvaluationMethodTests(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.RetainedEvidenceTests()
        fixture.setUp()
        self.addCleanup(fixture.temporary.cleanup)
        self.root = fixture.root
        for path in evidence.METHOD_PATHS:
            if (ROOT / path).is_file():
                (self.root / path).write_bytes((ROOT / path).read_bytes())
        self.prior = evidence.canonical(fixture.document) + "\n"
        prior_path = self.root / evidence.EVIDENCE
        prior_path.parent.mkdir(parents=True, exist_ok=True)
        prior_path.write_text(self.prior)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.output = self.work / "prepared"
        self.adapter = self.work / "synthetic-adapter.txt"
        self.adapter.write_text("Synthetic protocol fixture. No provider execution.\n")
        self.dispatch = self.work / "dispatch.json"
        self.dispatch.write_text(json.dumps({
            "schema_version": 1,
            "route": "synthetic test fixture; no provider",
            "model": "synthetic-model",
            "reasoning_effort": "synthetic-effort",
            "executor_instructions": "Use the supplied instructions. Use no tools.",
            "grader_instructions": "Grade the exact supplied response against each expectation.",
            "method_files": [{"label": "synthetic adapter", "path": str(self.adapter)}],
        }))

    def test_preparation_separates_executor_inputs_and_preserves_predecessor(self):
        helper.prepare(self.root, self.output, self.dispatch)
        frozen = helper.verify(self.root, self.output)
        packet = helper.packet(self.root, self.output, 4, "with_skill", 1)
        request = evidence.strict_json(packet["packet"]["request"])
        self.assertEqual(set(request), {"prompt", "fixture", "candidate_bundle"})
        self.assertEqual(request["fixture"], ["source"])
        self.assertEqual(len(request["candidate_bundle"]), 8)
        self.assertNotIn("expectations", packet["packet"])
        self.assertEqual(frozen["history"]["prior_document"], self.prior)
        self.assertTrue(all(not row["selected"] for row in frozen["history"]["entries"]))
        control = helper.packet(self.root, self.output, 4, "without_skill", 1)
        self.assertEqual(evidence.strict_json(control["packet"]["request"])["candidate_bundle"], [])

    def observation_files(self, prepared, label, response_text, **overrides):
        packet = prepared["packet"]
        observation = self.work / f"{label}-{packet['variant']}-{packet['repetition']}-{packet['role']}.json"
        observation.write_text(json.dumps({
            "packet_sha256": prepared["sha256"], "session_id": label,
            "model": "synthetic-model", "reasoning_effort": "synthetic-effort",
            "turn_status": "completed", "request": packet["request"],
            "response": response_text, "tool_events": [], **overrides,
        }))
        raw = observation.with_suffix(".raw")
        raw.write_bytes(b"Synthetic raw protocol fixture\r\n")
        return observation, raw

    def supply(self, variant, repetition, role, response_text, expected_state=None, **overrides):
        prepared = helper.packet(self.root, self.output, 4, variant, repetition, role)
        if expected_state is None:
            expected_state = helper.session_state(self.root, self.output)["sha256"]
        label = overrides.get("session_id", f"fresh-{variant}-{repetition}-{role}")
        observation, raw = self.observation_files(prepared, label, response_text, **overrides)
        self.last_admission = helper.record(
            self.root, self.output, 4, variant, repetition, role, observation, raw,
            expected_session_state_sha256=expected_state,
        )
        return observation, raw

    def complete(self, candidate_passed=True):
        for variant in ("with_skill", "without_skill"):
            for repetition in (1, 2, 3):
                self.supply(variant, repetition, "execution", "Retain the exact source.\r\n")
                self.supply(variant, repetition, "grading", json.dumps({"expectations": [{
                    "id": "case-4-expectation-1", "passed": candidate_passed and variant == "with_skill",
                    "evidence": "Synthetic judgment for protocol verification.",
                }]}))

    def test_recording_grading_and_assembly_use_the_owning_schema(self):
        helper.prepare(self.root, self.output, self.dispatch)
        self.complete()
        target = self.work / "result.json"
        helper.assemble(self.root, self.output, target)
        document = evidence.strict_json(target.read_text())
        evidence.validate(self.root, document=document)
        self.assertEqual(document["schema_version"], 2)
        self.assertEqual(len(document["records"]), 6)
        self.assertEqual(document["history"]["prior_document"], self.prior)
        self.assertEqual(document["records"][0]["response"], "Retain the exact source.\r\n")
        grading = evidence.strict_json(document["records"][0]["grading_request"])
        self.assertEqual(grading["response"], "Retain the exact source.\r\n")
        self.assertEqual(grading["expectations"][0]["id"], "case-4-expectation-1")
        self.assertTrue(all(row["execution_session_id"].startswith("fresh-") for row in document["records"]))
        provenance = json.loads(target.with_name(target.name + ".provenance.json").read_bytes())
        self.assertEqual(len(provenance["records"]), 12)
        self.assertEqual(provenance["records"][0]["role"], "execution")
        self.assertEqual(provenance["records"][0]["raw_record_sha256"],
                         hashlib.sha256(b"Synthetic raw protocol fixture\r\n").hexdigest())

    def test_cli_prepares_verifies_reports_state_and_records_without_execution(self):
        command = [sys.executable, "-B", str(ROOT / "scripts/feedback_response_evals.py")]
        prepared = subprocess.run(command + [
            "prepare", "--repo", str(self.root), "--output", str(self.output),
            "--dispatch", str(self.dispatch),
        ], capture_output=True, text=True)
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        self.assertEqual(json.loads(prepared.stdout)["executions"], 6)
        verified = subprocess.run(command + [
            "verify", "--repo", str(self.root), "--evaluation", str(self.output),
        ], capture_output=True, text=True)
        self.assertEqual(verified.returncode, 0, verified.stderr)
        packet_result = subprocess.run(command + [
            "packet", "--repo", str(self.root), "--evaluation", str(self.output),
            "--case", "4", "--variant", "with_skill", "--repetition", "1", "--role", "execution",
        ], capture_output=True, text=True)
        self.assertEqual(packet_result.returncode, 0, packet_result.stderr)
        packet = json.loads(packet_result.stdout)
        state_result = subprocess.run(command + [
            "session-state", "--repo", str(self.root), "--evaluation", str(self.output),
        ], capture_output=True, text=True)
        self.assertEqual(state_result.returncode, 0, state_result.stderr)
        state = json.loads(state_result.stdout)
        observation, raw = self.observation_files(packet, "cli-session", "CLI response.")
        recorded = subprocess.run(command + [
            "record", "--repo", str(self.root), "--evaluation", str(self.output),
            "--case", "4", "--variant", "with_skill", "--repetition", "1", "--role", "execution",
            "--observation", str(observation), "--raw-record", str(raw),
            "--session-state-sha256", state["sha256"],
        ], capture_output=True, text=True)
        self.assertEqual(recorded.returncode, 0, recorded.stderr)
        admitted = json.loads(recorded.stdout)
        self.assertEqual(admitted["session_state_sha256_before"], state["sha256"])
        self.assertNotEqual(admitted["session_state_sha256_after"], state["sha256"])

    def test_current_and_predecessor_consumers_require_boolean_grade_pairs(self):
        control = evidence.strict_json(self.prior)
        control["source_sha256"] = helper.source_snapshot(self.root)["source_sha256"]
        command = [sys.executable, "-B", str(ROOT / "scripts/feedback_response_evals.py")]
        validator = [sys.executable, "-B", str(ROOT / "scripts/validate_feedback_response_evidence.py")]
        for index, (passed, numeric) in enumerate(((True, 1), (False, 0), (True, 1.0), (False, 0.0))):
            for side in ("neither", "projection", "response", "both"):
                with self.subTest(passed=passed, numeric=numeric, side=side):
                    document = copy.deepcopy(control)
                    record = next(row for row in document["records"] if row["variant"] == "without_skill")
                    record["grades"][0]["passed"] = passed
                    response = {"expectations": copy.deepcopy(record["grades"])}
                    if side in ("projection", "both"):
                        record["grades"][0]["passed"] = numeric
                    if side in ("response", "both"):
                        response["expectations"][0]["passed"] = numeric
                    record["grading_response"] = json.dumps(response, indent=2) + "\n"
                    record["grading_response_sha256"] = evidence.digest(record["grading_response"])
                    prior = json.dumps(document, indent=2) + "\n"
                    (self.root / evidence.EVIDENCE).write_text(prior)
                    current = subprocess.run(validator + [str(self.root)], capture_output=True, text=True)
                    output = self.work / f"grade-pair-{index}-{side}"
                    prepared = subprocess.run(command + [
                        "prepare", "--repo", str(self.root), "--output", str(output),
                        "--dispatch", str(self.dispatch),
                    ], capture_output=True, text=True)
                    if side == "neither":
                        self.assertEqual(current.returncode, 0, current.stderr)
                        self.assertEqual(prepared.returncode, 0, prepared.stderr)
                        verified = subprocess.run(command + [
                            "verify", "--repo", str(self.root), "--evaluation", str(output),
                        ], capture_output=True, text=True)
                        self.assertEqual(verified.returncode, 0, verified.stderr)
                        history = helper.verify(self.root, output)["history"]
                        self.assertEqual(history["prior_document"], prior)
                        self.assertTrue(all(row["selected"] is False for row in history["entries"]))
                    else:
                        self.assertNotEqual(current.returncode, 0)
                        self.assertNotEqual(prepared.returncode, 0)
                        self.assertFalse(output.exists())

    def test_retained_session_cannot_be_recorded_as_a_fresh_execution(self):
        helper.prepare(self.root, self.output, self.dispatch)
        with self.assertRaisesRegex(ValueError, "historical session"):
            self.supply("with_skill", 1, "execution", "A new string does not create a new execution.",
                        session_id="with_skill-1")
        retained = self.output / "records/4-with_skill-1-execution"
        self.assertTrue((retained / "rejection.json").is_file())
        self.assertEqual((retained / "raw-record.bin").read_bytes(), b"Synthetic raw protocol fixture\r\n")
        with self.assertRaisesRegex(ValueError, "record"):
            self.supply("with_skill", 1, "execution", "Replacement is not allowed.")

    def test_session_state_is_deterministic_preparation_bound_and_returned_by_record(self):
        helper.prepare(self.root, self.output, self.dispatch)
        first = helper.session_state(self.root, self.output)
        self.assertEqual(first, helper.session_state(self.root, self.output))
        self.assertEqual(first["state"], {
            "schema_version": 1,
            "preparation_sha256": evidence.digest(helper.encoded(helper.verify(self.root, self.output))),
            "historical_session_ids": sorted(helper.historical_sessions(helper.verify(self.root, self.output))),
            "accepted_records": [],
        })
        self.supply("with_skill", 1, "execution", "Response.", expected_state=first["sha256"])
        after = helper.session_state(self.root, self.output)
        self.assertEqual(self.last_admission["session_state_sha256_before"], first["sha256"])
        self.assertEqual(self.last_admission["session_state_sha256_after"], after["sha256"])
        self.assertEqual(len(self.last_admission["record_sha256"]), 64)
        self.assertEqual(after["state"]["accepted_records"][0]["session_id"],
                         "fresh-with_skill-1-execution")

    def test_stale_state_rejects_a_distinct_label_and_retains_the_attempt(self):
        helper.prepare(self.root, self.output, self.dispatch)
        state = helper.session_state(self.root, self.output)["sha256"]
        self.supply("with_skill", 1, "execution", "First.", expected_state=state)
        with self.assertRaisesRegex(ValueError, "stale session state"):
            self.supply("without_skill", 1, "execution", "Second.", expected_state=state)
        retained = self.output / "records/4-without_skill-1-execution"
        self.assertTrue((retained / "rejection.json").is_file())
        self.assertTrue((retained / "raw-record.bin").is_file())
        self.assertFalse((retained / "record.json").exists())
        with self.assertRaisesRegex(ValueError, "record file inventory"):
            helper.session_state(self.root, self.output)

    def test_subprocess_imports_with_one_state_commit_at_most_once(self):
        command = [sys.executable, "-B", str(ROOT / "scripts/feedback_response_evals.py")]
        for same_label in (True, False):
            with self.subTest(same_label=same_label):
                self.output = self.work / f"race-{same_label}"
                helper.prepare(self.root, self.output, self.dispatch)
                state = helper.session_state(self.root, self.output)["sha256"]
                jobs = []
                for variant in ("with_skill", "without_skill"):
                    prepared = helper.packet(self.root, self.output, 4, variant, 1, "execution")
                    label = "raced-session" if same_label else f"raced-{variant}"
                    observation, raw = self.observation_files(prepared, label, "Raced response.")
                    jobs.append(command + [
                        "record", "--repo", str(self.root), "--evaluation", str(self.output),
                        "--case", "4", "--variant", variant, "--repetition", "1", "--role", "execution",
                        "--observation", str(observation), "--raw-record", str(raw),
                        "--session-state-sha256", state,
                    ])
                processes = [subprocess.Popen(job, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                             for job in jobs]
                results = [process.communicate() + (process.returncode,) for process in processes]
                self.assertEqual(sum(returncode == 0 for _, _, returncode in results), 1, results)
                directories = list((self.output / "records").iterdir())
                self.assertEqual(sum((directory / "record.json").is_file() for directory in directories), 1)

    def test_busy_or_crash_left_lock_fails_closed_and_is_preserved(self):
        helper.prepare(self.root, self.output, self.dispatch)
        marker = self.output / helper.LOCK_NAME
        marker.write_bytes(b'{"owner":"synthetic-crash"}\n')
        with self.assertRaisesRegex(ValueError, "lock busy or recovery required"):
            helper.session_state(self.root, self.output)
        self.assertEqual(marker.read_bytes(), b'{"owner":"synthetic-crash"}\n')

    def test_state_rejects_unknown_partial_drifted_malformed_and_aliased_records(self):
        for condition in ("unknown", "partial", "drifted", "malformed", "aliased"):
            with self.subTest(condition=condition):
                self.output = self.work / f"state-{condition}"
                helper.prepare(self.root, self.output, self.dispatch)
                if condition == "unknown":
                    (self.output / "records/unknown").mkdir(parents=True)
                elif condition == "partial":
                    prepared = helper.packet(self.root, self.output, 4, "with_skill", 1, "execution")
                    directory = helper.record_directory(self.output, prepared)
                    directory.mkdir(parents=True)
                    (directory / "packet.json").write_bytes(helper.encoded(prepared))
                elif condition == "aliased":
                    records = self.output / "records"
                    records.mkdir()
                    target = self.work / "alias-target"
                    target.mkdir(exist_ok=True)
                    (records / "4-with_skill-1-execution").symlink_to(target, target_is_directory=True)
                else:
                    self.supply("with_skill", 1, "execution", "Response.")
                    directory = self.output / "records/4-with_skill-1-execution"
                    if condition == "drifted":
                        (directory / "raw-record.bin").write_bytes(b"changed")
                    else:
                        index = json.loads((directory / "record.json").read_bytes())
                        index["unexpected"] = True
                        (directory / "record.json").write_text(json.dumps(index))
                with self.assertRaises(ValueError):
                    helper.session_state(self.root, self.output)

    def test_grading_packet_and_assembly_exclude_a_partial_import(self):
        helper.prepare(self.root, self.output, self.dispatch)
        prepared = helper.packet(self.root, self.output, 4, "with_skill", 1, "execution")
        directory = helper.record_directory(self.output, prepared)
        directory.mkdir(parents=True)
        (directory / "packet.json").write_bytes(helper.encoded(prepared))
        with self.assertRaisesRegex(ValueError, "record file inventory"):
            helper.packet(self.root, self.output, 4, "with_skill", 1, "grading")
        with self.assertRaisesRegex(ValueError, "record file inventory"):
            helper.assemble(self.root, self.output, self.work / "result.json")

    def test_grading_packet_validates_complete_record_inventory(self):
        helper.prepare(self.root, self.output, self.dispatch)
        self.supply("with_skill", 1, "execution", "Observed response.")
        (self.output / "records/unknown").mkdir()
        with self.assertRaisesRegex(ValueError, "unknown coordinate"):
            helper.packet(self.root, self.output, 4, "with_skill", 1, "grading")

    def test_import_rejects_non_utf8_scalar_text_and_accepts_unicode(self):
        for field in ("session_id", "response"):
            with self.subTest(field=field):
                self.output = self.work / f"non-utf8-{field}"
                helper.prepare(self.root, self.output, self.dispatch)
                prepared = helper.packet(self.root, self.output, 4, "with_skill", 1, "execution")
                state = helper.session_state(self.root, self.output)["sha256"]
                label = "\ud800" if field == "session_id" else "ordinary-session"
                response = "\ud800" if field == "response" else "Ordinary response."
                observation, raw = self.observation_files(
                    prepared, f"fixture-{field}", response, session_id=label,
                )
                observation_bytes, raw_bytes = observation.read_bytes(), raw.read_bytes()
                with self.assertRaisesRegex(ValueError, "canonical UTF-8"):
                    helper.record(
                        self.root, self.output, 4, "with_skill", 1, "execution", observation, raw,
                        expected_session_state_sha256=state,
                    )
                retained = self.output / "records/4-with_skill-1-execution"
                self.assertEqual((retained / "observation.json").read_bytes(), observation_bytes)
                self.assertEqual((retained / "raw-record.bin").read_bytes(), raw_bytes)
                self.assertTrue((retained / "rejection.json").is_file())
                self.assertFalse((retained / "record.json").exists())
                with self.assertRaises(ValueError):
                    helper.record(
                        self.root, self.output, 4, "with_skill", 1, "execution", observation, raw,
                        expected_session_state_sha256=state,
                    )
                self.assertEqual((retained / "observation.json").read_bytes(), observation_bytes)
                self.assertEqual((retained / "raw-record.bin").read_bytes(), raw_bytes)

        self.output = self.work / "unicode-scalar"
        helper.prepare(self.root, self.output, self.dispatch)
        response = "R\u00e9sum\u00e9 \U0001f375 \u6f22\u5b57"
        self.supply("with_skill", 1, "execution", response, session_id="session-\u03bc")
        grading = helper.packet(self.root, self.output, 4, "with_skill", 1, "grading")
        self.assertEqual(evidence.strict_json(grading["packet"]["request"])["response"], response)

    def test_current_session_cannot_be_recorded_twice(self):
        helper.prepare(self.root, self.output, self.dispatch)
        self.supply("with_skill", 1, "execution", "First response.",
                    session_id="current-reused-session")
        with self.assertRaisesRegex(ValueError, "current session"):
            self.supply("without_skill", 1, "execution", "Second response.",
                        session_id="current-reused-session")
        duplicate = self.output / "records/4-without_skill-1-execution"
        self.assertFalse((duplicate / "record.json").exists())

    def test_assembly_rejects_undeclared_record_directories(self):
        helper.prepare(self.root, self.output, self.dispatch)
        self.complete()
        (self.output / "records/unplanned-observation").mkdir()
        with self.assertRaisesRegex(ValueError, "record inventory"):
            helper.assemble(self.root, self.output, self.work / "result.json")

    def test_grading_rejects_a_changed_recorded_executor_packet(self):
        helper.prepare(self.root, self.output, self.dispatch)
        self.supply("with_skill", 1, "execution", "Observed response.")
        retained = self.output / "records/4-with_skill-1-execution/packet.json"
        data = json.loads(retained.read_bytes())
        data["packet"]["instructions"] = "Different delivery instructions."
        retained.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "recorded packet"):
            helper.packet(self.root, self.output, 4, "with_skill", 1, "grading")

    def test_preparation_requires_all_delivered_sources(self):
        missing = self.root / "plugins/proseweaving/skills/writing-for-people/references/threaded-conversation.md"
        missing.unlink()
        with self.assertRaisesRegex(ValueError, "missing source"):
            helper.prepare(self.root, self.output, self.dispatch)
        self.assertFalse(self.output.exists())

    def test_source_method_and_runner_changes_stale_preparation(self):
        helper.prepare(self.root, self.output, self.dispatch)
        paths = [
            self.root / "evals/mergecraft/skills/interacting-with-pr-review-feedback/fixtures/example.md",
            self.root / "plugins/mergecraft/references/review-voice.md",
            self.root / "docs/agents/mergecraft-feedback-evaluations.md",
            self.root / "scripts/feedback_response_evals.py",
            self.root / evidence.EVIDENCE,
            self.adapter,
        ]
        for path in paths:
            with self.subTest(path=path.name):
                original = path.read_bytes()
                path.write_bytes(original + b"\nchanged")
                with self.assertRaises(ValueError):
                    helper.verify(self.root, self.output)
                path.write_bytes(original)
                helper.verify(self.root, self.output)
        original_mode = self.adapter.stat().st_mode & 0o777
        self.adapter.chmod(original_mode ^ 0o100)
        with self.assertRaisesRegex(ValueError, "dispatch method drift"):
            helper.verify(self.root, self.output)

    def test_incomplete_and_failed_candidate_batches_cannot_be_assembled(self):
        helper.prepare(self.root, self.output, self.dispatch)
        target = self.work / "result.json"
        with self.assertRaisesRegex(ValueError, "record inventory"):
            helper.assemble(self.root, self.output, target)
        self.complete(candidate_passed=False)
        with self.assertRaisesRegex(ValueError, "candidate threshold"):
            helper.assemble(self.root, self.output, target)
        self.assertFalse(target.exists())
        self.assertFalse(target.with_name(target.name + ".provenance.json").exists())

    def test_import_rejects_mismatched_and_incomplete_observations_but_keeps_bytes(self):
        for index, change in enumerate((
            {"model": "different-model"}, {"reasoning_effort": "different-effort"},
            {"turn_status": "interrupted"}, {"response": ""},
            {"request": "different request"}, {"packet_sha256": "0" * 64},
            {"tool_events": [{"type": "synthetic-observed-action"}]},
        )):
            with self.subTest(change=change):
                self.output = self.work / f"prepared-{index}"
                helper.prepare(self.root, self.output, self.dispatch)
                with self.assertRaises(ValueError):
                    self.supply("with_skill", 1, "execution", "Response.", **change)
                retained = self.output / "records/4-with_skill-1-execution"
                self.assertTrue((retained / "rejection.json").exists())
                self.assertEqual((retained / "raw-record.bin").read_bytes(), b"Synthetic raw protocol fixture\r\n")
                self.assertFalse((retained / "record.json").exists())
                with self.assertRaisesRegex(ValueError, "record file inventory"):
                    helper.session_state(self.root, self.output)

    def test_imported_raw_record_changes_invalidate_its_grade_packet(self):
        helper.prepare(self.root, self.output, self.dispatch)
        self.supply("with_skill", 1, "execution", "Observed response.")
        raw = self.output / "records/4-with_skill-1-execution/raw-record.bin"
        raw.write_bytes(b"different raw observation")
        with self.assertRaisesRegex(ValueError, "record bytes drift"):
            helper.packet(self.root, self.output, 4, "with_skill", 1, "grading")

    def test_context_and_actual_predecessor_remain_exact_excluded_artifacts(self):
        self.prior = (ROOT / evidence.EVIDENCE).read_bytes().decode("utf-8")
        (self.root / evidence.EVIDENCE).write_bytes(self.prior.encode("utf-8"))
        note = self.work / "history-note.txt"
        note.write_bytes(b"Prior request strings changed; response and grade fields did not.\r\n")
        helper.prepare(self.root, self.output, self.dispatch, historical_context=[note])
        self.complete()
        target = self.work / "result.json"
        helper.assemble(self.root, self.output, target)
        document = json.loads(target.read_bytes())
        predecessor = json.loads(document["history"]["prior_document"])
        self.assertEqual(len(predecessor["records"]), 78)
        self.assertEqual(document["history"]["prior_document"].encode("utf-8"), self.prior.encode("utf-8"))
        self.assertEqual((self.root / evidence.EVIDENCE).read_bytes(), self.prior.encode("utf-8"))
        provenance = json.loads(target.with_name(target.name + ".provenance.json").read_bytes())
        context = provenance["historical_context"][0]
        self.assertFalse(context["selected"])
        self.assertEqual(context["document"].encode("utf-8"), note.read_bytes())


if __name__ == "__main__":
    unittest.main()
