"""Public PR-writing evaluation seams; all observations are synthetic."""

import json
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.mergecraft_pr_writing_evals import receipt_artifacts as adapter
from scripts.mergecraft_pr_writing_evals import run_application as recorder
from scripts.mergecraft_pr_writing_evals.binding import load_processor
from scripts.mergecraft_pr_writing_evals.prepare_application import prepare
from scripts.mergecraft_pr_writing_evals.run_application import record_attempt
from tests.mergecraft_pr_writing_evals.support import (
    ROOT,
    SourceFixture,
    read,
    reference,
    retained_value,
    sha,
    synthetic_execute,
    synthetic_grade,
    write,
)

REPOSITORY = Path(__file__).resolve().parents[1]


class ProcessorBindingTests(unittest.TestCase):
    def test_changed_processor_is_rejected_before_import(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)
            for relative in (
                "scripts/behavior_eval_receipts.py",
                "scripts/behavior_eval_inventory.py",
                "scripts/behavior_eval_corpora.py",
                "release/behavior-eval-receipt-v1.schema.json",
                "release/behavior-eval-policy.json",
            ):
                target = source / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(REPOSITORY / relative, target)
            with (source / "scripts/behavior_eval_inventory.py").open("ab") as stream:
                stream.write(b"\n# Unreviewed processor change.\n")
            with self.assertRaisesRegex(ValueError, "reviewed processor differs"):
                load_processor(source)


class PreparationTests(unittest.TestCase):
    def test_freeze_uses_committed_whole_criteria_and_exact_case_10_variant(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = SourceFixture(Path(temporary))
            frozen = fixture.freeze()
            plan = read(frozen / "input-manifest.json")
            self.assertEqual(
                (plan["case_count"], plan["fixture_count"], plan["criteria_count"]),
                (11, 10, 43),
            )
            self.assertEqual(len(plan["run_coordinates"]), 33)
            self.assertEqual(plan["processing_identity_kind"], "constructed-test")
            self.assertNotEqual(
                plan["processing_revision"], plan["published_processor_revision"]
            )
            self.assertFalse(
                any("proseweaving" in p for p in plan["case_instruction_paths"]["10"])
            )
            self.assertEqual(len(plan["case_instruction_paths"]["9"]), 8)
            self.assertTrue((frozen / "STOP_LAUNCHES").exists())
            policy = read(frozen / "withheld/expectation-policy.json")
            self.assertEqual(sum(len(c["expectations"]) for c in policy["cases"]), 43)
            self.assertEqual(
                policy["cases"][0]["expectations"][0]["expectation_text"],
                "Explains the exact user-visible correction and preserves the still-current issue link without inventing broader impact.",
            )
            self.assertEqual(
                read(frozen / "native-reference/frozen-direct-queries.json"),
                read(
                    fixture.source
                    / "evals/mergecraft/skills/writing-reviewable-pr-descriptions/trigger-evals.json"
                ),
            )
            gold = read(
                Path(__file__).parent
                / "mergecraft_pr_writing_evals/request-digests.json"
            )
            rows = read(frozen / "native-reference/selection-contract.json")["rows"]
            self.assertEqual(
                {row["id"]: sha(row["probe_prompt"].encode()) for row in rows},
                gold["direct_selection_prompts"],
            )
            with self.assertRaises(FileExistsError):
                fixture.freeze()


class ApplicationPreparationTests(unittest.TestCase):
    def test_prepare_preserves_original_requests_and_blocks_launch(self):
        from scripts.mergecraft_pr_writing_evals import run_application

        with tempfile.TemporaryDirectory() as temporary:
            fixture = SourceFixture(Path(temporary))
            output = Path(temporary) / "prepared"
            prepared = fixture.prepare(output)
            manifest = read(output / "manifest.json")
            gold = read(
                Path(__file__).parent
                / "mergecraft_pr_writing_evals/request-digests.json"
            )
            for number, expected in gold["cases"].items():
                case = output / f"eval-{number}/with_skill"
                self.assertEqual(
                    sha((case / "request.json").read_bytes()), expected["request"]
                )
                self.assertEqual(
                    sha((case / "prompt.txt").read_bytes()), expected["prompt"]
                )
                self.assertEqual(
                    list(read(case / "request.json")),
                    ["prompt", "fixture", "candidate_bundle"],
                )
            self.assertEqual(len(manifest["source_sha256"]), 12)
            self.assertEqual(len(manifest["delivery"]["runtime_inputs"]), 8)
            self.assertEqual(
                manifest["receipt"]["processor_revision"], fixture.processing_revision
            )
            with self.assertRaisesRegex(ValueError, "launch review is pending"):
                run_application.execute(output, prepared["manifest_sha256"], 0, 1)
            self.assertFalse((output / "eval-0/with_skill/repetition-1").exists())


class ReceiptRoundtripTests(unittest.TestCase):
    def test_real_processor_reconciles_complete_corpus_and_checks_committed_receipt(
        self,
    ):
        from scripts.mergecraft_pr_writing_evals import receipt_artifacts as adapter
        from tests.mergecraft_pr_writing_evals.reconciliation import (
            ReconciliationFixture,
        )
        from tests.mergecraft_pr_writing_evals.support import SKILL, write

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = ReconciliationFixture(root)
            output = root / "application"
            digest = fixture.applications(output, failures=[(0, 1, 1)])
            native = root / "native"
            native_digest = fixture.discovery(native)
            result = adapter.assemble_reconciliation(
                output, digest, native, native_digest, output / "reconciliation.json"
            )
            _core, inventory, contract = adapter.processor()
            receipt = inventory.reconcile(
                fixture.source,
                fixture.revision,
                SKILL,
                output / "reconciliation.json",
                fixture.processing_revision,
            )
            self.assertEqual((len(receipt["runs"]), len(receipt["triggers"])), (33, 19))
            self.assertEqual(sum(len(r["expectations"]) for r in receipt["runs"]), 129)
            self.assertEqual(
                sum(
                    not e["passed"] for r in receipt["runs"] for e in r["expectations"]
                ),
                1,
            )
            self.assertNotEqual(
                fixture.processing_revision, contract["published_processor_revision"]
            )
            self.assertEqual(
                result["processor_validation"]["thresholds"]["status"], "pass"
            )
            write(fixture.source / "receipts" / (SKILL + ".json"), receipt)
            containing = fixture.commit("Constructed receipt C; no evaluation evidence")
            comparison = inventory.compare(fixture.source, fixture.baseline, containing)
            checked = inventory.check(
                fixture.source, fixture.baseline, containing, "receipts"
            )
            self.assertEqual(checked["status"], "pass", checked)
            self.assertEqual(checked["affected_skills"], [SKILL])
            self.assertEqual(comparison["affected_skills"], [SKILL])
            member = inventory.check_member(
                fixture.source, fixture.baseline, containing, "receipts", "mergecraft"
            )
            self.assertEqual(member["status"], "pass", member)
            self.assertEqual(member["checked_skills"], [SKILL])
            self.assertEqual(member["coverage_basis"]["receipt_scope"], "selected-member")
            self.assertFalse(result["public_receipt_ready"])


class RecordingTests(unittest.TestCase):
    def test_timeout_preserves_partial_raw_output_and_cannot_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary) / "attempt-1"
            stdout = b'{"type":"item.completed","item":{"type":"agent_message","text":"partial"}}\n'
            stderr = b"before timeout\n"
            command = [
                sys.executable,
                "-c",
                f"import os, time; os.write(1, {stdout!r}); os.write(2, {stderr!r}); time.sleep(30)",
            ]
            result = record_attempt(run, command, b"public task", {}, {}, timeout=1)
            self.assertFalse(result["valid_application"])
            self.assertTrue(result["timed_out"])
            self.assertEqual(result["returncode"], 124)
            self.assertEqual((run / "transcript.jsonl").read_bytes(), stdout)
            self.assertEqual((run / "stderr.log").read_bytes(), stderr)

    def test_observed_task_tool_event_rejects_otherwise_completed_response(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary) / "attempt-1"
            stdout = b'{"type":"item.completed","item":{"type":"command_execution","command":"synthetic"}}\n{"type":"item.completed","item":{"type":"agent_message","text":"answer"}}\n{"type":"turn.completed"}\n'
            result = record_attempt(
                run,
                [sys.executable, "-c", f"import os; os.write(1, {stdout!r})"],
                b"public task",
                {},
                {},
                timeout=1,
            )
            self.assertFalse(result["valid_application"])
            self.assertEqual(len(result["tool_items"]), 1)
            self.assertEqual((run / "response.txt").read_bytes(), b"answer")

    def test_malformed_event_and_unpaired_surrogate_retain_failed_result(self):
        for stdout in (
            b"[]\n",
            b'{"type":"item.completed","item":{"type":"agent_message","text":"\\ud800"}}\n{"type":"turn.completed"}\n',
        ):
            with (
                self.subTest(stdout=stdout),
                tempfile.TemporaryDirectory() as temporary,
            ):
                run = Path(temporary) / "attempt-1"
                result = record_attempt(
                    run,
                    [sys.executable, "-c", f"import os; os.write(1, {stdout!r})"],
                    b"public task",
                    {},
                    {},
                    timeout=1,
                )
                self.assertFalse(result["valid_application"])
                self.assertTrue(result["protocol_errors"])
                self.assertEqual((run / "transcript.jsonl").read_bytes(), stdout)
                self.assertTrue((run / "result.json").exists())

    def test_unicode_line_separators_round_trip_with_lf_and_crlf_records(self):
        answer = "Keep the paragraph separator:\u2029then the line separator:\u2028and a real\r\nline break."
        for newline in ("\n", "\r\n"):
            with (
                self.subTest(newline=newline),
                tempfile.TemporaryDirectory() as temporary,
            ):
                run = Path(temporary) / "attempt-1"
                events = [
                    {"type": "thread.started", "thread_id": "synthetic-thread"},
                    {
                        "type": "item.completed",
                        "item": {"type": "agent_message", "text": answer},
                    },
                    {"type": "turn.completed", "usage": {}},
                ]
                stdout = (
                    newline.join(json.dumps(e, ensure_ascii=False) for e in events)
                    + newline
                ).encode()
                command = [sys.executable, "-c", f"import os; os.write(1, {stdout!r})"]
                result = record_attempt(
                    run,
                    command,
                    b"public task",
                    {"case": 0, "repetition": 1},
                    {},
                    timeout=1,
                )
                self.assertTrue(result["valid_application"])
                self.assertEqual((run / "response.txt").read_bytes(), answer.encode())
                self.assertEqual((run / "transcript.jsonl").read_bytes(), stdout)

    def test_invalid_utf8_retains_exact_streams_and_rejects_collection(self):
        for stream in ("stdout", "stderr"):
            with (
                self.subTest(stream=stream),
                tempfile.TemporaryDirectory() as temporary,
            ):
                run = Path(temporary) / "attempt-1"
                valid = b'{"type":"item.completed","item":{"type":"agent_message","text":"answer"}}\n{"type":"turn.completed"}\n'
                stdout = valid + (b"\xff" if stream == "stdout" else b"")
                stderr = b"\xff" if stream == "stderr" else b""
                command = [
                    sys.executable,
                    "-c",
                    f"import os; os.write(1, {stdout!r}); os.write(2, {stderr!r})",
                ]
                result = record_attempt(
                    run,
                    command,
                    b"public task",
                    {"case": 0, "repetition": 1},
                    {},
                    timeout=1,
                )
                self.assertFalse(result["valid_application"])
                self.assertEqual(result["encoding_errors"][0]["stream"], stream)
                self.assertEqual((run / "transcript.jsonl").read_bytes(), stdout)
                self.assertEqual((run / "stderr.log").read_bytes(), stderr)
                self.assertEqual(json.loads((run / "result.json").read_bytes()), result)

    def test_launch_failure_retains_attempt_and_empty_raw_streams(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = root / "attempt-1"
            result = record_attempt(
                run,
                [str(root / "missing-client")],
                b"public task",
                {"case": 10, "repetition": 1},
                {"test": "synthetic"},
                timeout=1,
            )
            self.assertFalse(result["valid_application"])
            self.assertIsNotNone(result["launch_error"])
            self.assertEqual((run / "transcript.jsonl").read_bytes(), b"")
            self.assertEqual((run / "stderr.log").read_bytes(), b"")
            self.assertEqual(json.loads((run / "result.json").read_bytes()), result)
            before = {p.name: p.read_bytes() for p in run.iterdir()}
            with self.assertRaises(FileExistsError):
                record_attempt(
                    run, [str(root / "missing-client")], b"other", {}, {}, timeout=1
                )
            self.assertEqual({p.name: p.read_bytes() for p in run.iterdir()}, before)


class ReceiptArtifactTests(unittest.TestCase):
    def test_collection_rejects_one_recorded_session_used_for_two_coordinates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = SourceFixture(root)
            output = root / "prepared"
            prepared = fixture.prepare(output)
            digest = prepared["manifest_sha256"]
            (output / "STOP_LAUNCHES").unlink()
            for number in (0, 1):
                synthetic_execute(
                    output, digest, number=number, thread_id="same-synthetic-session"
                )
                projection = adapter.project_execution(output, digest, number, 1)
                grade, config = synthetic_grade(output, projection, number)
                adapter.project_grading(
                    output,
                    digest,
                    number,
                    1,
                    grade,
                    sha(grade.read_bytes()),
                    config,
                    sha(config.read_bytes()),
                )
            with self.assertRaisesRegex(ValueError, "one original session"):
                adapter.collect_applications(
                    output, digest, output / "duplicate-session-index.json"
                )

    def test_projection_requires_a_nonempty_original_session_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = SourceFixture(root)
            output = root / "prepared"
            prepared = fixture.prepare(output)
            (output / "STOP_LAUNCHES").unlink()
            synthetic_execute(output, prepared["manifest_sha256"], thread_id="")
            with self.assertRaisesRegex(ValueError, "session identity"):
                adapter.project_execution(output, prepared["manifest_sha256"], 0, 1)
            self.assertFalse((output / "receipt/executions").exists())

    def test_recorder_retains_original_execution_and_case_specific_delivery(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = SourceFixture(root)
            output = root / "prepared"
            prepared = fixture.prepare(output)
            (output / "STOP_LAUNCHES").unlink()
            result = synthetic_execute(output, prepared["manifest_sha256"], number=10)
            run = output / "eval-10/with_skill/repetition-1/attempt-1"
            original = json.loads((run / "execution-record.json").read_bytes())
            self.assertEqual(original["execution"], result)
            self.assertEqual(original["case"], 10)
            self.assertEqual(original["repetition"], 1)
            self.assertEqual(original["source_revision"], fixture.revision)
            self.assertEqual(len(original["runtime_inputs"]), 3)
            self.assertEqual(len(original["inputs"]), 4)
            self.assertFalse(any("proseweaving" in p for p in original["inputs"]))
            projected = adapter.project_execution(
                output, prepared["manifest_sha256"], 10, 1
            )
            correspondence = json.loads(
                (output / projected["correspondence"]).read_bytes()
            )
            self.assertEqual(correspondence["input_evidence"], original["inputs"])
            self.assertEqual(
                correspondence["execution_record_sha256"],
                sha((run / "execution-record.json").read_bytes()),
            )
            request_path = output / "eval-10/with_skill/request.json"
            request_before = request_path.read_bytes()
            changed = json.loads(request_before)
            changed["candidate_bundle"][
                "plugins/proseweaving/skills/writing-for-people/SKILL.md"
            ] = "Not supplied in this case"
            write(request_path, changed)
            with self.assertRaisesRegex(ValueError, "prepared input differs"):
                adapter.project_execution(output, prepared["manifest_sha256"], 10, 1)

    def test_technical_failure_and_changed_raw_response_cannot_become_envelopes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = SourceFixture(root)
            output = root / "prepared"
            prepared = fixture.prepare(output)
            digest = prepared["manifest_sha256"]
            (output / "STOP_LAUNCHES").unlink()
            synthetic_execute(output, digest, code=1)
            with self.assertRaisesRegex(ValueError, "application record is invalid"):
                adapter.project_execution(output, digest, 0, 1)
            synthetic_execute(output, digest, number=1)
            response = output / "eval-1/with_skill/repetition-1/attempt-1/response.txt"
            response.write_bytes(response.read_bytes() + b"changed")
            with self.assertRaisesRegex(ValueError, "response differs from raw"):
                adapter.project_execution(output, digest, 1, 1)
            self.assertFalse((output / "receipt/executions").exists())

    def test_grader_rejects_changed_identity_coverage_and_nonboolean_judgments(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = SourceFixture(root)
            output = root / "prepared"
            prepared = fixture.prepare(output)
            digest = prepared["manifest_sha256"]
            (output / "STOP_LAUNCHES").unlink()
            synthetic_execute(output, digest)
            projection = adapter.project_execution(output, digest, 0, 1)
            grade, config = synthetic_grade(output, projection)
            original = grade.read_bytes()
            mutations = [
                lambda v: v.update(repetition=2),
                lambda v: v.update(snapshot_sha256="0" * 64),
                lambda v: v.update(model_id="other-grader"),
                lambda v: v["expectations"].pop(),
                lambda v: v["expectations"][0].update(id=v["expectations"][1]["id"]),
                lambda v: v["expectations"][0].update(passed=1),
                lambda v: v["expectations"][0].update(evidence=""),
            ]
            for index, mutation in enumerate(mutations):
                with self.subTest(mutation=index):
                    changed = json.loads(original)
                    mutation(changed)
                    write(grade, changed)
                    with self.assertRaises(ValueError):
                        adapter.project_grading(
                            output,
                            digest,
                            0,
                            1,
                            grade,
                            sha(grade.read_bytes()),
                            config,
                            sha(config.read_bytes()),
                        )
            self.assertFalse((output / "receipt/gradings").exists())

    def test_cli_exposes_application_only_commands(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "scripts.mergecraft_pr_writing_evals.receipt_artifacts",
                "--help",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0)
        self.assertIn("collect-applications", completed.stdout)
        self.assertNotIn("assemble-results", completed.stdout)

    def test_index_requires_all_33_records_and_retains_failed_grades_without_receipt_claim(
        self,
    ):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = SourceFixture(root)
            output = root / "prepared"
            prepared = fixture.prepare(output)
            manifest_hash = prepared["manifest_sha256"]
            index = output / "receipt/applications-index.json"
            with self.assertRaises(FileNotFoundError):
                adapter.collect_applications(output, manifest_hash, index)
            self.assertFalse(index.exists())
            (output / "STOP_LAUNCHES").unlink()
            for repetition in (1, 2, 3):
                for number in range(11):
                    synthetic_execute(output, manifest_hash, number, repetition)
                    projected = adapter.project_execution(
                        output, manifest_hash, number, repetition
                    )
                    grade, config = synthetic_grade(
                        output,
                        projected,
                        number,
                        repetition,
                        passed=(number, repetition) != (0, 1),
                    )
                    adapter.project_grading(
                        output,
                        manifest_hash,
                        number,
                        repetition,
                        grade,
                        sha(grade.read_bytes()),
                        config,
                        sha(config.read_bytes()),
                    )
            result = adapter.collect_applications(output, manifest_hash, index)
            self.assertEqual(result["application_runs"], 33)
            self.assertEqual(result["judgment_count"], 129)
            self.assertEqual(result["negative_judgment_count"], 4)
            self.assertFalse(result["public_receipt_ready"])
            self.assertEqual(
                result["status"],
                "applications-complete-discovery-and-reconciliation-pending",
            )
            self.assertEqual(len(json.loads(index.read_bytes())["runs"]), 33)
            self.assertFalse((output / "receipt/results.json").exists())
            with self.assertRaises(FileExistsError):
                adapter.collect_applications(output, manifest_hash, index)
            first_thread = "synthetic-0-1"
            second_run = output / "eval-1/with_skill/repetition-1/attempt-1"
            changed_stream = (
                (second_run / "transcript.jsonl")
                .read_bytes()
                .replace(b"synthetic-1-1", first_thread.encode())
            )
            (second_run / "transcript.jsonl").write_bytes(changed_stream)
            with self.assertRaisesRegex(ValueError, "raw streams"):
                adapter.collect_applications(
                    output, manifest_hash, output / "copied-session-index.json"
                )
            (second_run / "transcript.jsonl").write_bytes(
                changed_stream.replace(first_thread.encode(), b"synthetic-1-1")
            )
            extra = output / "eval-0/with_skill/repetition-1/attempt-2"
            extra.mkdir()
            with self.assertRaisesRegex(ValueError, "unplanned attempt"):
                adapter.collect_applications(
                    output, manifest_hash, output / "extra-index.json"
                )
            extra.rmdir()
            grade = output / "grading-inputs/case-0/repetition-1.json"
            modified = json.loads(grade.read_bytes())
            modified["supplemental_observations"] = []
            write(grade, modified)
            with self.assertRaisesRegex(ValueError, "grading input differs"):
                adapter.collect_applications(
                    output, manifest_hash, output / "altered-index.json"
                )

    def test_grade_hashes_envelope_not_response_and_preserves_false_judgments(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = SourceFixture(root)
            output = root / "prepared"
            prepared = fixture.prepare(output)
            (output / "STOP_LAUNCHES").unlink()
            synthetic_execute(output, prepared["manifest_sha256"])
            projection = adapter.project_execution(
                output, prepared["manifest_sha256"], 0, 1
            )
            grade_path, config_path = synthetic_grade(output, projection, passed=False)
            original = grade_path.read_bytes()
            incorrect = json.loads(original)
            incorrect["executor_output_sha256"] = incorrect["response_sha256"]
            write(grade_path, incorrect)
            with self.assertRaisesRegex(ValueError, "executor output"):
                adapter.project_grading(
                    output,
                    prepared["manifest_sha256"],
                    0,
                    1,
                    grade_path,
                    sha(grade_path.read_bytes()),
                    config_path,
                    sha(config_path.read_bytes()),
                )
            grade_path.write_bytes(original)
            projected = adapter.project_grading(
                output,
                prepared["manifest_sha256"],
                0,
                1,
                grade_path,
                sha(original),
                config_path,
                sha(config_path.read_bytes()),
            )
            envelope = json.loads((output / projected["grading"]).read_bytes())
            self.assertTrue(all(e["passed"] is False for e in envelope["expectations"]))
            self.assertEqual(
                envelope["executor_output_sha256"], projection["executor_output_sha256"]
            )
            self.assertNotIn("supplemental_observations", envelope)
            self.assertEqual(grade_path.read_bytes(), original)
            with self.assertRaises(FileExistsError):
                adapter.project_grading(
                    output,
                    prepared["manifest_sha256"],
                    0,
                    1,
                    grade_path,
                    sha(original),
                    config_path,
                    sha(config_path.read_bytes()),
                )

    def test_actual_record_projects_exact_response_and_stays_create_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = SourceFixture(root)
            output = root / "prepared"
            prepared = fixture.prepare(output)
            (output / "STOP_LAUNCHES").unlink()
            response = "Exact Unicode:\u2028\u2029\ufffd\r\nand newline.\n"
            result = synthetic_execute(
                output, prepared["manifest_sha256"], response=response
            )
            self.assertTrue(result["valid_application"])
            command = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "scripts.mergecraft_pr_writing_evals.receipt_artifacts",
                    "--root",
                    str(output),
                    "--manifest-sha256",
                    prepared["manifest_sha256"],
                    "project-execution",
                    "--case",
                    "0",
                    "--repetition",
                    "1",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(command.returncode, 0, command.stderr + command.stdout)
            projected = json.loads(command.stdout)
            envelope = json.loads((output / projected["executor_output"]).read_bytes())
            self.assertEqual(envelope["response"].encode(), response.encode())
            self.assertEqual(envelope["case_id"]["id"], 0)
            self.assertEqual(envelope["model_id"], "gpt-6-astra")
            self.assertEqual(
                set(envelope),
                {"snapshot_sha256", "case_id", "repetition", "model_id", "response"},
            )
            self.assertEqual(
                projected["executor_output_sha256"],
                sha((output / projected["executor_output"]).read_bytes()),
            )
            with self.assertRaises(FileExistsError):
                adapter.project_execution(output, prepared["manifest_sha256"], 0, 1)


class ProtocolAndPlanTests(unittest.TestCase):
    def test_finite_events_and_unicode_response_project_with_lf_and_crlf(self):
        response = "Exact\u2028\u2029\ufffd\r\ntext; NaN and Infinity are ordinary string content."
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = SourceFixture(root)
            output = root / "prepared"
            prepared = fixture.prepare(output)
            digest = prepared["manifest_sha256"]
            manifest = json.loads((output / "manifest.json").read_bytes())
            (output / "STOP_LAUNCHES").unlink()
            actual_run = subprocess.run
            for number, newline in enumerate((b"\n", b"\r\n")):
                with self.subTest(newline=newline):
                    events = [
                        {
                            "type": "thread.started",
                            "thread_id": f"synthetic-unicode-{number}",
                            "extra": {"nested": [1.25, 1e308, {"text": "value"}]},
                        },
                        {
                            "type": "item.completed",
                            "item": {"type": "agent_message", "text": response},
                        },
                        {"type": "turn.completed", "usage": {}},
                    ]
                    stdout = (
                        newline.join(
                            json.dumps(event, ensure_ascii=False).encode()
                            for event in events
                        )
                        + newline
                    )

                    def boundary(command, emitted=stdout, **kwargs):
                        if command[0] == manifest["client_binding"]["path"]:
                            kwargs["stdout"].write(emitted)
                            kwargs["stderr"].write(b"")
                            return subprocess.CompletedProcess(command, 0)
                        self.assertEqual(command[0], "git")
                        return actual_run(command, **kwargs)

                    with patch("subprocess.run", side_effect=boundary):
                        result = recorder.execute(output, digest, number, 1)
                    self.assertTrue(result["valid_application"])
                    projection = adapter.project_execution(output, digest, number, 1)
                    envelope = json.loads(
                        (output / projection["executor_output"]).read_bytes()
                    )
                    self.assertEqual(envelope["response"].encode(), response.encode())
                    run = output / f"eval-{number}/with_skill/repetition-1/attempt-1"
                    self.assertEqual(
                        (run / "response.txt").read_bytes(), response.encode()
                    )
                    self.assertEqual((run / "transcript.jsonl").read_bytes(), stdout)

    def test_plan_binds_current_recorder_and_runs_one_held_synthetic_coordinate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = SourceFixture(root)
            output = root / "prepared"
            prepared = fixture.prepare(output)
            manifest = json.loads((output / "manifest.json").read_bytes())
            self.assertEqual(len(manifest["run_coordinates"]), 33)
            self.assertEqual(
                manifest["method_sha256"][
                    "scripts/mergecraft_pr_writing_evals/run_application.py"
                ],
                sha(
                    (
                        ROOT / "scripts/mergecraft_pr_writing_evals/run_application.py"
                    ).read_bytes()
                ),
            )
            command = [
                "scripts.mergecraft_pr_writing_evals.run_application",
                "--root",
                str(output),
                "--manifest-sha256",
                prepared["manifest_sha256"],
                "--case",
                "0",
                "--repetition",
                "1",
            ]
            stdout = (
                b'{"type":"thread.started","thread_id":"synthetic-plan"}\n'
                b'{"type":"item.completed","item":{"type":"agent_message","text":"Planned synthetic answer"}}\n'
                b'{"type":"turn.completed"}\n'
            )
            actual_run = subprocess.run
            process_calls = []

            def boundary(argv, **kwargs):
                if argv[0] == manifest["client_binding"]["path"]:
                    process_calls.append(argv)
                    self.assertEqual(
                        kwargs["input"],
                        (output / "eval-0/with_skill/prompt.txt").read_bytes(),
                    )
                    kwargs["stdout"].write(stdout)
                    kwargs["stderr"].write(b"")
                    return subprocess.CompletedProcess(argv, 0)
                self.assertEqual(argv[0], "git")
                return actual_run(argv, **kwargs)

            def invoke():
                with (
                    patch("subprocess.run", side_effect=boundary),
                    patch.object(sys, "argv", command),
                ):
                    runpy.run_module(command[0], run_name="__main__")

            with self.assertRaisesRegex(
                ValueError, "final source or launch review is pending"
            ):
                invoke()
            self.assertEqual(process_calls, [])
            run = output / "eval-0/with_skill/repetition-1/attempt-1"
            self.assertFalse(run.exists())
            (output / "STOP_LAUNCHES").unlink()
            with self.assertRaises(SystemExit) as completed:
                invoke()
            self.assertEqual(completed.exception.code, 0)
            self.assertEqual(len(process_calls), 1)
            original = json.loads((run / "execution-record.json").read_bytes())
            self.assertEqual((original["case"], original["repetition"]), (0, 1))
            self.assertTrue(original["execution"]["valid_application"])
            self.assertEqual((run / "transcript.jsonl").read_bytes(), stdout)
            before = {p.name: p.read_bytes() for p in run.iterdir()}
            with self.assertRaises(FileExistsError):
                invoke()
            self.assertEqual(len(process_calls), 1)
            self.assertEqual({p.name: p.read_bytes() for p in run.iterdir()}, before)

    def test_ambiguous_and_nonfinite_events_retain_raw_failure_and_block_projection(
        self,
    ):
        duplicate_message = (
            b'{"type":"thread.started","thread_id":"synthetic-duplicate"}\n'
            b'{"type":"item.completed","item":{"type":"agent_message",'
            b'"text":"earlier value","text":"later value"}}\n'
            b'{"type":"turn.completed"}\n'
        )
        nonfinite_event = (
            b'{"type":"thread.started","thread_id":"synthetic-nonfinite","extra":NaN}\n'
            b'{"type":"item.completed","item":{"type":"agent_message","text":"Synthetic answer"}}\n'
            b'{"type":"turn.completed"}\n'
        )
        tail = (
            b'{"type":"item.completed","item":{"type":"agent_message","text":"answer"}}\n'
            b'{"type":"turn.completed"}\n'
        )
        streams = [
            ("duplicate-message", duplicate_message, "duplicate"),
            ("nonfinite-event", nonfinite_event, "non-finite"),
            (
                "duplicate-event-key",
                b'{"type":"other","type":"thread.started","thread_id":"synthetic"}\n'
                + tail,
                "duplicate",
            ),
            (
                "duplicate-nested-key",
                b'{"type":"thread.started","thread_id":"synthetic","extra":{"nested":[{"value":1,"value":2}]}}\n'
                + tail,
                "duplicate",
            ),
        ]
        for token in (b"Infinity", b"-Infinity", b"1e9999", b"-1e9999"):
            streams.append(
                (
                    token.decode(),
                    b'{"type":"thread.started","thread_id":"synthetic","extra":{"nested":['
                    + token
                    + b"]}}\n"
                    + tail,
                    "non-finite",
                )
            )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = SourceFixture(root)
            output = root / "prepared"
            prepared = fixture.prepare(output)
            digest = prepared["manifest_sha256"]
            manifest = json.loads((output / "manifest.json").read_bytes())
            (output / "STOP_LAUNCHES").unlink()
            actual_run = subprocess.run
            stderr = b"Synthetic public diagnostic\n"
            for number, (label, stdout, error) in enumerate(streams):
                with self.subTest(case=label):

                    def boundary(command, emitted=stdout, **kwargs):
                        if command[0] == manifest["client_binding"]["path"]:
                            kwargs["stdout"].write(emitted)
                            kwargs["stderr"].write(stderr)
                            return subprocess.CompletedProcess(command, 0)
                        self.assertEqual(command[0], "git")
                        return actual_run(command, **kwargs)

                    with patch("subprocess.run", side_effect=boundary):
                        result = recorder.execute(output, digest, number, 1)
                    run = output / f"eval-{number}/with_skill/repetition-1/attempt-1"
                    self.assertFalse(result["valid_application"])
                    self.assertEqual((run / "transcript.jsonl").read_bytes(), stdout)
                    self.assertEqual((run / "stderr.log").read_bytes(), stderr)
                    self.assertTrue(
                        any(error in e["error"] for e in result["protocol_errors"])
                    )
                    self.assertTrue(result["unparsed_transcript_lines"])
                    original = json.loads((run / "execution-record.json").read_bytes())
                    self.assertEqual(original["execution"], result)
                    self.assertEqual(
                        json.loads((run / "result.json").read_bytes()), result
                    )
                    before = {p.name: p.read_bytes() for p in run.iterdir()}
                    with self.assertRaisesRegex(
                        ValueError, "application record is invalid"
                    ):
                        adapter.project_execution(output, digest, number, 1)
                    self.assertFalse((output / "receipt/executions").exists())
                    self.assertEqual(
                        {p.name: p.read_bytes() for p in run.iterdir()}, before
                    )


class PreparationRubricTests(unittest.TestCase):
    def test_preparation_freezes_normalized_accepted_rubric_for_graders_only(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = SourceFixture(Path(directory))
            output = Path(directory) / "application"
            result = fixture.prepare(output)
            manifest = adapter.verify_manifest(output, result["manifest_sha256"])
            rubric = adapter.read(output / "receipt/grading-rubrics.json")
            self.assertEqual(
                rubric["acceptance_reference"],
                "https://github.com/nisavid/provingkit/issues/111#issuecomment-5729835933",
            )
            self.assertEqual(len(rubric["cases"]), 11)
            self.assertEqual(sum(len(c["expectations"]) for c in rubric["cases"]), 43)
            descriptor = adapter.read(output / "receipt/descriptor.json")
            self.assertEqual(
                rubric["cases"],
                [
                    {
                        "case_id": c["case_id"],
                        "expectations": [
                            {k: e[k] for k in ("id", "text", "severity")}
                            for e in c["expectations"]
                        ],
                    }
                    for c in descriptor["cases"]
                ],
            )
            self.assertIn("receipt/grading-rubrics.json", manifest["artifact_sha256"])
            for n in range(11):
                request = adapter.read(output / f"eval-{n}/with_skill/request.json")
                self.assertEqual(
                    list(request), ["prompt", "fixture", "candidate_bundle"]
                )
                self.assertNotIn("grading-rubrics", json.dumps(request))

    def test_preparation_rejects_changed_direct_query_before_any_dispatch(self):
        from tests.mergecraft_pr_writing_evals.reconciliation import (
            TRIGGERS,
            ReconciliationFixture,
        )
        from tests.mergecraft_pr_writing_evals.support import SKILL, write

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = ReconciliationFixture(root)
            queries = adapter.read(fixture.source / TRIGGERS)
            queries[0]["query"] += " Changed."
            write(fixture.source / TRIGGERS, queries)
            fixture.revision = fixture.commit("Synthetic changed query rejection")
            _core, inventory, _ = adapter.processor()
            fixture.descriptor = inventory.descriptor(
                fixture.source, fixture.revision, SKILL
            )
            fixture.snapshot = inventory.prepare(
                fixture.source, fixture.revision, SKILL
            )
            write(fixture.snapshot_path, fixture.snapshot)
            write(fixture.descriptor_path, fixture.descriptor)
            fixture.binding["repository_head"] = fixture.revision
            write(fixture.binding_path, fixture.binding)
            with self.assertRaisesRegex(ValueError, "direct queries differ"):
                fixture.prepare(root / "must-not-create")
            self.assertFalse((root / "must-not-create").exists())


class FullReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests.mergecraft_pr_writing_evals.reconciliation import (
            ReconciliationFixture,
        )

        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.fixture = ReconciliationFixture(cls.root)
        cls.output = cls.root / "application"
        cls.fixture.freeze()
        policy = adapter.read(cls.fixture.inputs / "withheld/expectation-policy.json")
        cls.quality = next(
            (c["case_id"], i)
            for c in policy["cases"]
            for i, e in enumerate(c["expectations"])
            if e["severity"] == "quality"
        )
        cls.safety = next(
            (c["case_id"], i)
            for c in policy["cases"]
            for i, e in enumerate(c["expectations"])
            if e["severity"] == "safety"
        )
        cls.digest = cls.fixture.applications(
            cls.output, failures=[(cls.quality[0], 1, cls.quality[1])]
        )
        cls.freeze = cls.root / "native"
        cls.discovery_digest = cls.fixture.discovery(cls.freeze)
        cls.result = adapter.assemble_reconciliation(
            cls.output,
            cls.digest,
            cls.freeze,
            cls.discovery_digest,
            cls.output / "reconciliation.json",
        )
        cls.results = adapter.read(cls.output / "reconciliation.json")
        cls.core, cls.inventory, _ = adapter.processor()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def produce(self, results, label):
        from tests.mergecraft_pr_writing_evals.support import SKILL, write

        path = self.output / f"synthetic-{label}.json"
        write(path, results)
        return self.inventory.reconcile(
            self.fixture.source,
            self.fixture.revision,
            SKILL,
            path,
            self.fixture.processing_revision,
        )

    def test_actual_processor_checker_roundtrip_false_retention_and_identity_distinctions(
        self,
    ):
        from tests.mergecraft_pr_writing_evals.support import SKILL, write

        receipt = self.produce(self.results, "roundtrip")
        self.assertEqual((len(receipt["runs"]), len(receipt["triggers"])), (33, 19))
        self.assertEqual(sum(len(r["expectations"]) for r in receipt["runs"]), 129)
        self.assertEqual(
            sum(not e["passed"] for r in receipt["runs"] for e in r["expectations"]), 1
        )
        self.assertNotEqual(
            self.core.document_digest(receipt["snapshot"]),
            self.core.document_digest(self.fixture.snapshot),
        )
        self.assertTrue(
            all(
                t["observation_kind"] == "recorded-sentinel-body-load"
                for t in receipt["triggers"]
            )
        )
        self.assertEqual(
            len(self.results["case_runtime_inputs"][10]["runtime_inputs"]), 3
        )
        self.assertFalse(
            any(
                "proseweaving" in p
                for p in self.results["case_runtime_inputs"][10]["runtime_inputs"]
            )
        )
        self.assertEqual(len(self.fixture.binding["source_sha256"]), 12)
        self.assertEqual(len(self.results["runtime_inputs"]), 8)
        for row in self.results["runs"]:
            grade = retained_value(self.output, row["grading_record"])
            self.assertTrue(grade["supplemental_observations"])
            self.assertNotEqual(
                grade["executor_output_sha256"], grade["response_sha256"]
            )
        write(self.fixture.source / "receipts" / (SKILL + ".json"), receipt)
        containing = self.fixture.commit("Synthetic containing C; never publish")
        try:
            checked = self.inventory.check(
                self.fixture.source, self.fixture.baseline, containing, "receipts"
            )
            self.assertEqual(checked["status"], "pass", checked)
            self.assertEqual(checked["affected_skills"], [SKILL])
        finally:
            self.fixture.git("checkout", "--quiet", "--detach", self.fixture.revision)
        self.assertFalse(self.result["public_receipt_ready"])
        provenance = adapter.read(self.output / "receipt-source/provenance.json")
        for name, binding in provenance["copies"].items():
            self.assertEqual(
                (self.freeze / name).read_bytes(),
                (self.output / binding["destination"]).read_bytes(),
            )
        with self.assertRaises(FileExistsError):
            adapter.assemble_reconciliation(
                self.output,
                self.digest,
                self.freeze,
                self.discovery_digest,
                self.output / "reconciliation.json",
            )

    def test_processor_rejects_coverage_delivery_and_rubric_mismatches(self):
        import copy

        mutations = {
            "duplicate-runtime-row": lambda r: r["case_runtime_inputs"].append(
                copy.deepcopy(r["case_runtime_inputs"][0])
            ),
            "missing-runtime-row": lambda r: r["case_runtime_inputs"].pop(),
            "unknown-runtime-row": lambda r: r["case_runtime_inputs"][0][
                "case_id"
            ].update(id=999),
            "wrong-union": lambda r: r["runtime_inputs"].pop(),
            "case10-provider-invented": lambda r: r["case_runtime_inputs"][10][
                "runtime_inputs"
            ].append(next(p for p in r["runtime_inputs"] if "proseweaving" in p)),
            "missing-fixture": lambda r: r["runs"][0]["inputs"].pop(
                next(p for p in r["runs"][0]["inputs"] if p.startswith("evals/"))
            ),
            "delivered-value-mismatch": lambda r: r["runs"][0]["inputs"][
                next(iter(r["runs"][0]["inputs"]))
            ]["value"].update(pointer="/prompt"),
            "wrong-rubric": lambda r: r["runs"][0]["rubric"]["value"].update(
                pointer="/cases/1/expectations"
            ),
            "missing-trigger": lambda r: r["triggers"].pop(),
            "duplicate-trigger": lambda r: r["triggers"].append(
                copy.deepcopy(r["triggers"][0])
            ),
            "wrong-query": lambda r: r["triggers"][0]["query"].update(
                pointer="/effort"
            ),
            "wrong-trigger-model": lambda r: r["triggers"][0]["model"]["value"].update(
                pointer="/11"
            ),
            "wrong-graded-response": lambda r: r["runs"][0]["graded_response"][
                "value"
            ].update(pointer="/executor_output_sha256"),
        }
        for label, change in mutations.items():
            with self.subTest(label=label):
                result = copy.deepcopy(self.results)
                change(result)
                with self.assertRaises((ValueError, KeyError)):
                    self.produce(result, label)

    def test_processor_rejects_bad_trace_and_missing_negative_boundary(self):
        import copy

        from tests.mergecraft_pr_writing_evals.support import write

        for label in (
            "extra-read",
            "unsupported-action",
            "bad-json",
            "missing-negative-prompt",
        ):
            result = copy.deepcopy(self.results)
            trigger = result["triggers"][0]
            if label == "missing-negative-prompt":
                path = self.output / "synthetic-prompt.txt"
                write(path, b"No supported negative boundary.")
                trigger["probe_prompt"] = adapter.evidence_reference(
                    self.output, path.name, format="utf8"
                )
            else:
                path = self.output / f"synthetic-{label}.jsonl"
                events = [
                    self.core.read_json(line)
                    for line in (self.output / trigger["trace"]["path"])
                    .read_text()
                    .split("\n")
                    if line.strip()
                ]
                if label == "extra-read":
                    events.insert(3, copy.deepcopy(events[2]))
                if label == "unsupported-action":
                    events[2]["item"]["type"] = "mcp_tool_call"
                write(
                    path,
                    b"{bad}\n"
                    if label == "bad-json"
                    else b"".join((json.dumps(e) + "\n").encode() for e in events),
                )
                trigger["trace"] = adapter.evidence_reference(
                    self.output, path.name, format="jsonl"
                )
            with self.subTest(label=label), self.assertRaises(ValueError):
                self.produce(result, label)

    def check_containing_receipt(self, receipt, expected):
        from tests.mergecraft_pr_writing_evals.support import SKILL, write

        write(self.fixture.source / "receipts" / (SKILL + ".json"), receipt)
        containing = self.fixture.commit("Synthetic threshold checker; never publish")
        try:
            checked = self.inventory.check(
                self.fixture.source, self.fixture.baseline, containing, "receipts"
            )
            self.assertEqual(checked["status"], expected, checked)
            self.assertEqual(checked["affected_skills"], [SKILL])
        finally:
            self.fixture.git("checkout", "--quiet", "--detach", self.fixture.revision)

    def test_inexact_normalized_rubrics_reject_without_replacing_originals(self):
        import copy

        from tests.mergecraft_pr_writing_evals.support import write

        for label in ("legacy-id", "extra-field"):
            result = copy.deepcopy(self.results)
            original = retained_value(
                self.output, result["runs"][0]["original_expectations"]
            )
            if label == "legacy-id":
                original[0]["id"] = "0.1"
            else:
                original[0]["normalization_metadata"] = True
            path = self.output / ("synthetic-rubric-" + label + ".json")
            write(path, original)
            ref = adapter.evidence_reference(self.output, path.name)
            result["runs"][0]["original_expectations"] = ref
            result["runs"][0]["rubric"]["value"] = ref
            with self.subTest(label=label), self.assertRaises(ValueError):
                self.produce(result, "rubric-" + label)

    def test_failed_trace_assembly_keeps_originals_and_failure_capsule(self):
        from tests.mergecraft_pr_writing_evals.support import write

        freeze = self.root / "native-unsupported"
        digest = self.fixture.discovery(freeze)
        run = freeze / "selection-runs/writing-reviewable-pr-descriptions-00"
        events = [
            self.core.read_json(line)
            for line in (run / "stdout.jsonl").read_text().split("\n")
            if line.strip()
        ]
        events[2]["item"]["type"] = "mcp_tool_call"
        write(
            run / "stdout.jsonl",
            b"".join((json.dumps(e) + "\n").encode() for e in events),
        )
        record = adapter.read(run / "record.json")
        record["events"] = events
        record["tool_events"] = [events[2]]
        record["artifact_sha256"]["stdout.jsonl"] = adapter.sha(
            (run / "stdout.jsonl").read_bytes()
        )
        write(run / "record.json", record)
        original = (run / "stdout.jsonl").read_bytes()
        kept = self.output / "retained-valid-source"
        (self.output / "receipt-source").rename(kept)
        target = self.output / "invalid-reconciliation.json"
        try:
            with self.assertRaises(ValueError):
                adapter.assemble_reconciliation(
                    self.output, self.digest, freeze, digest, target
                )
            self.assertTrue(target.exists())
            provenance = adapter.read(self.output / "receipt-source/provenance.json")
            self.assertEqual(provenance["processor_validation"]["status"], "invalid")
            self.assertEqual((run / "stdout.jsonl").read_bytes(), original)
            copied = (
                self.output
                / "receipt-source/discovery/selection-runs/writing-reviewable-pr-descriptions-00/stdout.jsonl"
            )
            self.assertEqual(copied.read_bytes(), original)
            with self.assertRaises(FileExistsError):
                adapter.assemble_reconciliation(
                    self.output, self.digest, freeze, digest, target
                )
        finally:
            (self.output / "receipt-source").rename(
                self.output / "retained-invalid-source"
            )
            kept.rename(self.output / "receipt-source")

    def test_false_safety_quality_and_selection_outcomes_remain_threshold_failures(
        self,
    ):
        import copy

        from tests.mergecraft_pr_writing_evals.support import write

        for label, (number, expectation), repetition in [
            ("safety", self.safety, 1),
            ("quality-second", self.quality, 2),
        ]:
            result = copy.deepcopy(self.results)
            row = next(
                r
                for r in result["runs"]
                if r["case_id"]["id"] == number and r["repetition"] == repetition
            )
            grade = retained_value(self.output, row["grading_record"])
            grade["expectations"][expectation]["passed"] = False
            path = self.output / f"synthetic-false-{label}.json"
            write(path, grade)
            row["grading_record"] = adapter.evidence_reference(self.output, path.name)
            row["grades"] = adapter.evidence_reference(
                self.output, path.name, "/expectations"
            )
            receipt = self.produce(result, "failed-" + label)
            self.assertEqual(
                self.core.evaluate(self.fixture.source, receipt)["status"], "fail"
            )
            self.assertTrue(
                any(not e["passed"] for r in receipt["runs"] for e in r["expectations"])
            )
            self.check_containing_receipt(receipt, "fail")
        # Assemble a complete but wrong direct selection; never discard it on its authored expected-match flag.
        freeze = self.root / "native-wrong"
        digest = self.fixture.discovery(freeze, wrong_selection=0)
        copied, rows = adapter.discovery_copies(
            freeze,
            digest,
            {**adapter.read(self.output / "manifest.json"), "_root": str(self.output)},
        )
        result = copy.deepcopy(self.results)
        trigger = result["triggers"][0]
        _, prefix, probe = rows[0]
        for key, name, format, pointer in [
            ("record", "record.json", "json", ""),
            ("trace", "stdout.jsonl", "jsonl", ""),
            ("probe_skill", probe, "utf8", ""),
            ("probe_prompt", "prompt.txt", "utf8", ""),
            ("sentinel", "case.json", "json", "/marker"),
            ("returncode", "record.json", "json", "/exit_code"),
            ("query", "query.json", "json", "/query"),
        ]:
            path = "synthetic-wrong/" + prefix + "/" + name
            write(self.output / path, copied[prefix + "/" + name])
            trigger[key] = adapter.evidence_reference(
                self.output, path, pointer, format
            )
        receipt = self.produce(result, "wrong-selection")
        self.check_containing_receipt(receipt, "fail")
        self.assertFalse(receipt["triggers"][0]["triggered"])
        self.assertEqual(
            self.core.evaluate(self.fixture.source, receipt)["status"], "fail"
        )

    def test_native_technical_and_source_mismatches_reject_without_rewriting_records(
        self,
    ):
        import copy

        from tests.mergecraft_pr_writing_evals.support import write

        record = (
            self.freeze
            / "selection-runs/writing-reviewable-pr-descriptions-00/record.json"
        )
        original = record.read_bytes()
        native = adapter.read(self.freeze / "manifest.json")
        for label, change in [
            ("technical", lambda r: r.update(technically_valid=False)),
            ("timeout", lambda r: r.update(timed_out=True)),
            ("returncode", lambda r: r.update(exit_code=1)),
            ("raw-observation", lambda r: r.update(messages=["invented"])),
        ]:
            value = adapter.read(record)
            change(value)
            write(record, value)
            try:
                with self.subTest(label=label), self.assertRaises(ValueError):
                    adapter.discovery_copies(
                        self.freeze,
                        self.discovery_digest,
                        {
                            **adapter.read(self.output / "manifest.json"),
                            "_root": str(self.output),
                        },
                    )
            finally:
                record.write_bytes(original)
        # The recorded construction and recorder identities are separate from source identity.
        manifest_path = self.freeze / "manifest.json"
        original_manifest = manifest_path.read_bytes()
        for field in ("helper_sha256", "selection_runner_sha256"):
            changed = copy.deepcopy(native)
            changed[field][next(iter(changed[field]))] = "0" * 64
            write(manifest_path, changed)
            try:
                with self.subTest(field=field), self.assertRaises(ValueError):
                    adapter.discovery_copies(
                        self.freeze,
                        adapter.sha(manifest_path.read_bytes()),
                        {
                            **adapter.read(self.output / "manifest.json"),
                            "_root": str(self.output),
                        },
                    )
            finally:
                manifest_path.write_bytes(original_manifest)
        manifest_path = self.freeze / "manifest.json"
        raw = manifest_path.read_bytes()
        value = copy.deepcopy(native)
        value["source_sha256"][next(iter(value["source_sha256"]))] = "0" * 64
        write(manifest_path, value)
        try:
            with self.assertRaisesRegex(ValueError, "source differs"):
                adapter.discovery_copies(
                    self.freeze,
                    adapter.sha(manifest_path.read_bytes()),
                    {
                        **adapter.read(self.output / "manifest.json"),
                        "_root": str(self.output),
                    },
                )
        finally:
            manifest_path.write_bytes(raw)


class PreparationRegressionTests(unittest.TestCase):
    def test_delivery_table_keeps_case_10_omission_and_exact_global_union(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = SourceFixture(Path(temporary))
            output = Path(temporary) / "prepared"
            fixture.prepare(output)
            manifest = json.loads((output / "manifest.json").read_bytes())
            delivery = manifest["delivery"]
            by_case = {
                row["case_id"]["id"]: row["runtime_inputs"]
                for row in delivery["case_runtime_inputs"]
            }
            self.assertEqual(len(by_case), 11)
            self.assertEqual(len(by_case[10]), 3)
            self.assertEqual(len(by_case[9]), 8)
            self.assertFalse(any("proseweaving" in p for p in by_case[10]))
            self.assertEqual(
                set(delivery["runtime_inputs"]),
                set().union(*map(set, by_case.values())),
            )
            self.assertEqual(len(delivery["runtime_inputs"]), 8)
            metadata = json.loads((output / "eval-10/eval_metadata.json").read_bytes())
            self.assertEqual(len(metadata["input_evidence"]), 4)
            self.assertEqual(
                set(metadata["input_evidence"]),
                set(by_case[10])
                | {
                    "evals/mergecraft/skills/writing-reviewable-pr-descriptions/fixtures/change-summary-and-supporting-evidence.md"
                },
            )
            original = (output / "manifest.json").read_bytes()
            for mutate in (
                lambda value: value["delivery"]["runtime_inputs"].pop(),
                lambda value: value["delivery"]["case_runtime_inputs"].pop(),
                lambda value: value["delivery"]["case_runtime_inputs"][-1][
                    "runtime_inputs"
                ].append("invented-input"),
            ):
                from scripts.mergecraft_pr_writing_evals.receipt_artifacts import (
                    verify_manifest,
                )

                changed = json.loads(original)
                mutate(changed)
                write(output / "manifest.json", changed)
                with self.assertRaisesRegex(ValueError, "delivery table or union"):
                    verify_manifest(
                        output, sha((output / "manifest.json").read_bytes())
                    )
            (output / "manifest.json").write_bytes(original)

    def test_dirty_bytes_modes_and_snapshot_digest_substitution_stop_before_preparation(
        self,
    ):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = SourceFixture(root)
            path = (
                fixture.source
                / "plugins/mergecraft/skills/writing-reviewable-pr-descriptions/SKILL.md"
            )
            original = path.read_bytes()
            path.write_bytes(original + b"uncommitted")
            with self.assertRaisesRegex(ValueError, "working input differs"):
                fixture.prepare(root / "dirty-bytes")
            path.write_bytes(original)
            path.chmod(0o755)
            with self.assertRaisesRegex(ValueError, "working input differs"):
                fixture.prepare(root / "dirty-mode")
            path.chmod(0o644)
            with self.assertRaisesRegex(ValueError, "snapshot document digest"):
                prepare(
                    fixture.source,
                    fixture.binding_path,
                    sha(fixture.binding_path.read_bytes()),
                    sha((fixture.inputs / "input-manifest.json").read_bytes()),
                    root / "wrong-hash",
                    inputs=fixture.inputs,
                    receipt_snapshot=fixture.snapshot_path,
                    receipt_snapshot_file_sha256=sha(
                        fixture.snapshot_path.read_bytes()
                    ),
                    receipt_snapshot_sha256=sha(fixture.snapshot_path.read_bytes()),
                    receipt_descriptor=fixture.descriptor_path,
                    receipt_descriptor_sha256=sha(fixture.descriptor_path.read_bytes()),
                )
            self.assertFalse(
                any(
                    (root / name).exists()
                    for name in ("dirty-bytes", "dirty-mode", "wrong-hash")
                )
            )

    def test_source_that_integrates_a_changed_processor_needs_an_explicit_review(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = SourceFixture(root)
            path = fixture.source / "scripts/behavior_eval_inventory.py"
            path.write_bytes(
                path.read_bytes()
                + b"\n# Synthetic pending successor, never auto-adopt.\n"
            )
            revision = fixture.commit("Synthetic processor difference")
            fixture.revision = revision
            _, inventory = reference()
            fixture.binding["repository_head"] = revision
            write(fixture.binding_path, fixture.binding)
            fixture.descriptor = inventory.descriptor(
                fixture.source,
                revision,
                "mergecraft/writing-reviewable-pr-descriptions",
            )
            fixture.snapshot = inventory.prepare(
                fixture.source,
                revision,
                "mergecraft/writing-reviewable-pr-descriptions",
            )
            write(fixture.descriptor_path, fixture.descriptor)
            write(fixture.snapshot_path, fixture.snapshot)
            with self.assertRaisesRegex(ValueError, "integrated processor differs"):
                fixture.prepare(root / "changed-processor")
            self.assertFalse((root / "changed-processor").exists())

    def test_committed_source_snapshot_and_descriptor_bind_without_changing_payload(
        self,
    ):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = SourceFixture(Path(temporary))
            output = Path(temporary) / "prepared"
            result = fixture.prepare(output)
            self.assertEqual(result["runs"], 33)
            self.assertTrue((output / "STOP_LAUNCHES").exists())
            manifest = json.loads((output / "manifest.json").read_bytes())
            self.assertEqual(manifest["receipt"]["source_revision"], fixture.revision)
            self.assertEqual(
                (output / "receipt/snapshot.json").read_bytes(),
                fixture.snapshot_path.read_bytes(),
            )
            request = json.loads(
                (output / "eval-10/with_skill/request.json").read_bytes()
            )
            self.assertEqual(list(request), ["prompt", "fixture", "candidate_bundle"])
            self.assertEqual(len(request["candidate_bundle"]), 3)
            self.assertEqual(
                manifest["coordinates"][0]["receipt_case_id"],
                {
                    "source": "evals/mergecraft/skills/writing-reviewable-pr-descriptions/evals.json",
                    "pointer": "/evals/0",
                    "id": 0,
                },
            )
            with self.assertRaisesRegex(ValueError, "launch review is pending"):
                synthetic_execute(output, result["manifest_sha256"])
            self.assertFalse((output / "eval-0/with_skill/repetition-1").exists())


class MaintainedSourceBindingTests(unittest.TestCase):
    def test_copied_changed_adapter_bytes_or_executable_mode_cannot_claim_same_source(
        self,
    ):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = SourceFixture(root)
            copied = root / "copied-checkout"
            for relative in [
                *read(
                    REPOSITORY
                    / "scripts/mergecraft_pr_writing_evals/correspondence.json"
                )["processor_files"],
                *[
                    str(p.relative_to(REPOSITORY))
                    for p in (
                        REPOSITORY / "scripts/mergecraft_pr_writing_evals"
                    ).iterdir()
                    if p.suffix in (".py", ".json")
                ],
            ]:
                target = copied / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(REPOSITORY / relative, target)
            helper = copied / "scripts/mergecraft_pr_writing_evals/inputs.py"
            original = helper.read_bytes()
            program = (
                "from pathlib import Path; import sys; "
                "from scripts.mergecraft_pr_writing_evals.inputs import freeze_inputs; "
                "freeze_inputs(Path(sys.argv[1]),sys.argv[2],Path(sys.argv[3]),sys.argv[4],"
                "sys.argv[5],Path(sys.argv[6]),identity_kind='constructed-test')"
            )
            for label in ("bytes", "mode"):
                with self.subTest(label=label):
                    helper.write_bytes(
                        original + b"\n# Unreviewed copied helper.\n"
                        if label == "bytes"
                        else original
                    )
                    helper.chmod(0o755 if label == "mode" else 0o644)
                    output = root / ("refused-" + label)
                    completed = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            "-c",
                            program,
                            str(fixture.source),
                            fixture.revision,
                            str(fixture.runtime),
                            sha(fixture.runtime.read_bytes()),
                            fixture.processing_revision,
                            str(output),
                        ],
                        cwd=copied,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertNotEqual(completed.returncode, 0, completed.stdout)
                    self.assertIn("committed adapter differs", completed.stderr)
                    self.assertFalse(output.exists())


class AdaptationRejectionTests(unittest.TestCase):
    def test_newly_accepted_but_different_whole_criterion_mapping_stops(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = SourceFixture(Path(temporary))
            _core, inventory = reference()
            path = fixture.source / inventory.EXPECTATION_MAP
            mapping = read(path)
            mapping["entries"][0]["severity"] = "quality"
            mapping["entries"][0]["review"]["mapping_sha256"] = (
                inventory.corpora.mapping_digest(mapping["entries"][0])
            )
            write(path, mapping)
            fixture.revision = fixture.commit("Constructed different accepted mapping")
            with self.assertRaisesRegex(ValueError, "whole accepted criteria differ"):
                fixture.freeze()
            self.assertFalse(fixture.inputs.exists())

    def test_pending_source_review_stops_before_preparation_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            fixture = SourceFixture(Path(temporary))
            fixture.freeze()
            fixture.binding["status"] = "source-review-pending"
            write(fixture.binding_path, fixture.binding)
            output = Path(temporary) / "not-prepared"
            with self.assertRaisesRegex(
                ValueError, "reviewed final PR84 source is pending"
            ):
                fixture.prepare(output)
            self.assertFalse(output.exists())

    def test_post_process_method_drift_retains_raw_attempt_without_inventing_record(
        self,
    ):
        from scripts.mergecraft_pr_writing_evals.run_application import execute

        with tempfile.TemporaryDirectory() as temporary:
            fixture = SourceFixture(Path(temporary))
            output = Path(temporary) / "prepared"
            digest = fixture.prepare(output)["manifest_sha256"]
            (output / "STOP_LAUNCHES").unlink()
            helper = fixture.source / "scripts/mergecraft_pr_writing_evals/inputs.py"
            raw = (
                b'{"type":"thread.started","thread_id":"synthetic-drift"}\n'
                b'{"type":"item.completed","item":{"type":"agent_message","text":"Synthetic answer"}}\n'
                b'{"type":"turn.completed"}\n'
            )
            actual_run = subprocess.run

            def boundary(command, **kwargs):
                if command[0] == sys.executable:
                    kwargs["stdout"].write(raw)
                    helper.chmod(0o755)
                    return subprocess.CompletedProcess(command, 0)
                self.assertEqual(command[0], "git")
                return actual_run(command, **kwargs)

            with (
                patch("subprocess.run", side_effect=boundary),
                self.assertRaisesRegex(ValueError, "working adapter differs"),
            ):
                execute(output, digest, 0, 1)
            attempt = output / "eval-0/with_skill/repetition-1/attempt-1"
            self.assertEqual((attempt / "transcript.jsonl").read_bytes(), raw)
            self.assertTrue((attempt / "result.json").exists())
            self.assertFalse((attempt / "execution-record.json").exists())
            helper.chmod(0o644)
            with self.assertRaises(FileNotFoundError):
                adapter.project_execution(output, digest, 0, 1)
            self.assertFalse((attempt / "execution-record.json").exists())


class PublishedRuntimeBindingTests(unittest.TestCase):
    def test_reviewed_runtime_metadata_matches_the_published_route(self):
        from scripts.mergecraft_pr_writing_evals.inputs import validate_plan

        with tempfile.TemporaryDirectory() as temporary:
            fixture = SourceFixture(Path(temporary))
            plan = read(fixture.freeze() / "input-manifest.json")
            plan["processing_revision"] = plan["published_processor_revision"]
            plan["processing_identity_kind"] = "published"
            plan["client_binding"] = {
                "path": str(Path(temporary) / "reviewed-executable-not-launched"),
                "sha256": "d2752c52353401f7f6efbfcea68796f4f7a3d3e4769f5d1da53fa49d4856b72f",
                "version": "0.159.0",
            }
            validate_plan(plan)
            predecessor = {
                **plan,
                "processing_revision": "24c2d712a0be6a95958713ec80c7e06a89abdc6c",
            }
            with self.assertRaisesRegex(ValueError, "processing identity differs"):
                validate_plan(predecessor)
            previous_client = {
                **plan,
                "client_binding": {
                    **plan["client_binding"],
                    "sha256": "0753dfe1d8b87a52436deb13eb1c549661ef4c84fee2c5aa688385eebeccb761",
                    "version": "0.155.1",
                },
            }
            with self.assertRaisesRegex(ValueError, "changed client needs reviewed"):
                validate_plan(previous_client)
            plan["client_binding"]["sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "changed client needs reviewed"):
                validate_plan(plan)


if __name__ == "__main__":
    unittest.main()
