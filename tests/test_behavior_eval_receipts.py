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
            "scripts/behavior_eval_corpora.py",
            "scripts/behavior_eval_inventory.py",
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

    def test_input_closure_exposes_the_accepted_profile_and_method_seam(self):
        prepared = receipts.input_closure(
            self.repo,
            self.candidate,
            self.spec,
            profile="p24",
            method="prepared",
        )
        reconciled = receipts.input_closure(
            self.repo,
            self.candidate,
            self.spec,
            profile="p24",
            method="reconciled-after-run",
        )

        self.assertEqual(prepared["candidate_revision"], self.candidate)
        self.assertEqual(prepared["skill"], self.spec)
        self.assertEqual(
            set(prepared["inputs"]),
            {
                self.prefix + "/SKILL.md",
                self.prefix + "/evals/fixtures/case.md",
                self.prefix + "/evals/evals.json",
                self.prefix + "/evals/trigger-evals.json",
                "release/plugin-content-locks/example.json",
                "release/behavior-eval-policy.json",
                "release/behavior-eval-receipt-v1.schema.json",
                "scripts/behavior_eval_receipts.py",
            },
        )
        self.assertEqual(
            set(reconciled["inputs"]),
            {
                self.prefix + "/SKILL.md",
                self.prefix + "/evals/fixtures/case.md",
                self.prefix + "/evals/evals.json",
                self.prefix + "/evals/trigger-evals.json",
                "release/plugin-content-locks/example.json",
            },
        )
        self.assertEqual(prepared["skill"], reconciled["skill"])

    def test_input_closure_rejects_unknown_profile_or_method(self):
        for keyword, value in (("profile", "p1"), ("method", "prepared-before-run")):
            with self.subTest(keyword=keyword):
                arguments = {"profile": "p24", "method": "prepared"}
                arguments[keyword] = value
                with self.assertRaisesRegex(receipts.ReceiptError, keyword):
                    receipts.input_closure(
                        self.repo,
                        self.candidate,
                        self.spec,
                        **arguments,
                    )

    def test_input_closure_rejects_a_non_object_descriptor(self):
        with self.assertRaisesRegex(receipts.ReceiptError, "schema mismatch"):
            receipts.input_closure(
                self.repo,
                self.candidate,
                [],
                profile="p24",
                method="prepared",
            )

    def test_check_correspondence_rejects_unregistered_prepared_processing(self):
        snapshot = receipts.input_closure(
            self.repo,
            self.candidate,
            self.spec,
            profile="p24",
            method="prepared",
        )
        results = self.results(snapshot)
        receipt = receipts.produce(self.repo, snapshot, results)
        raw = receipts.canonical_bytes(receipt)
        binding = {
            "path": "receipts/example/writing.json",
            "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "mode": "100644",
            "evaluated_revision": self.candidate,
            "method": "prepared",
            "profile": "p24",
            "processing": None,
            "producer_procedure_revision": self.candidate,
        }
        self.write("unrelated.txt", "The landing changed an unrelated file.\n")
        landed = self.commit("land receipt change")

        result = receipts.check_correspondence(
            self.repo,
            candidate_revision=landed,
            descriptor=self.spec,
            receipt_bytes=raw,
            binding=binding,
        )

        self.assertEqual(result["status"], "fail")
        self.assertIsNone(result["input_identity"])

    def test_check_correspondence_retains_malformed_receipt_identity(self):
        raw = b'{"broken":'
        binding = {"path": "receipts/example/writing.json", "raw_sha256": hashlib.sha256(raw).hexdigest(),
                   "mode": "100644", "evaluated_revision": self.candidate, "method": "prepared",
                   "profile": "p24", "processing": None, "producer_procedure_revision": self.candidate}
        result = receipts.check_correspondence(self.repo, candidate_revision=self.candidate,
            descriptor=self.spec, receipt_bytes=raw, binding=binding)
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["reason_code"], "receipt-malformed")
        self.assertEqual(result["receipt_raw_sha256"], "cbdf3b1f91ae32fe1ea292ac6cccf19222f97929f531523f0d15d885052c00c4")
        self.assertIsNone(result["receipt_sha256"])
        self.assertIsNone(result["input_identity"])

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

    def retained_results(self, case_runtime_inputs=None):
        """Construct original records without an execution-time receipt snapshot."""
        corpus = json.loads((self.repo / self.spec["evals"]).read_text())
        corpus_hash = hashlib.sha256((self.repo / self.spec["evals"]).read_bytes()).hexdigest()
        runtime = self.prefix + "/SKILL.md"
        original = {"runs": [], "triggers": []}
        for case in corpus["evals"]:
            case_id = str(case["id"])
            paths = (case_runtime_inputs[case_id] if case_runtime_inputs is not None else [runtime])
            paths = paths + [self.prefix + "/" + path for path in case["fixture_paths"]]
            for repetition in (1, 2, 3):
                original["runs"].append({
                    "case_id": case_id, "repetition": repetition,
                    "revision": self.candidate, "corpus_sha256": corpus_hash,
                    "native_agent": f"constructed-executor-{case_id}-{repetition}",
                    "inputs": {path: (self.repo / path).read_text() for path in paths},
                    "prompt": case["prompt"], "response": "Constructed retained response.\n",
                    "executor_model": "test-executor-1", "grader_model": "test-grader-1",
                    "original_expectations": case["expectations"],
                    "graded_response": "Constructed retained response.\n",
                    "rubric": case["expectations"], "grades": [
                        {"id": "facts", "passed": True},
                        {"id": "useful", "passed": repetition != 3}],
                })
        for index, item in enumerate(json.loads((self.repo / self.spec["trigger_evals"]).read_text())):
            original["triggers"].append({
                "query": item["query"], "entrypoint": (self.repo / runtime).read_text(),
                "model": "test-executor-1", "body_loaded": item["should_trigger"],
                "sentinel": "PROBE_SENTINEL", "negative_response": "NO_SKILL",
                "response": "PROBE_SENTINEL" if item["should_trigger"] else "NO_SKILL",
                "tool_action_count": 1 if item["should_trigger"] else 0, "returncode": 0,
            })
        artifact = self.private / "retained.json"
        artifact.write_text(json.dumps(original))
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()

        def ref(pointer):
            return {"path": "retained.json", "sha256": digest, "format": "json", "pointer": pointer}

        def binding(pointer):
            return {"representation": "utf8", "value": ref(pointer)}

        runs = []
        for index, run in enumerate(original["runs"]):
            pointer = f"/runs/{index}"
            runs.append({
                "case_id": run["case_id"], "repetition": run["repetition"], "execution_record": ref(pointer),
                "original_revision": ref(pointer + "/revision"),
                "original_corpus_sha256": ref(pointer + "/corpus_sha256"),
                "inputs": {path: binding(pointer + "/inputs/" + path.replace("/", "~1")) for path in run["inputs"]},
                "prompt": ref(pointer + "/prompt"), "response": ref(pointer + "/response"),
                "executor_model": {"basis": "configured", "value": ref(pointer + "/executor_model")},
                "grader_model": {"basis": "configured", "value": ref(pointer + "/grader_model")},
                "grading_record": ref(pointer + "/grades"),
                "graded_response": binding(pointer + "/graded_response"),
                "original_expectations": ref(pointer + "/original_expectations"),
                "rubric": {"representation": "expectations", "value": ref(pointer + "/rubric")},
                "grades": ref(pointer + "/grades"), "previous_grading": [], "adjudication": None,
            })
        triggers = []
        for index in range(2):
            pointer = f"/triggers/{index}"
            trigger = {"case_id": str(index + 1), "observation_kind": "recorded-sentinel-body-load",
                "record": ref(pointer), "model": {"basis": "configured", "value": ref(pointer + "/model")},
                "query": ref(pointer + "/query"), "entrypoint": binding(pointer + "/entrypoint"),
                "limits": ["Constructed body-load surrogate; no native invocation claim."]}
            trigger.update({key: ref(pointer + "/" + key) for key in (
                "body_loaded", "sentinel", "negative_response", "response", "tool_action_count", "returncode")})
            triggers.append(trigger)
        result = {"schema_version": 1, "method": "reconciled-after-run",
            "executor_model_id": "test-executor-1", "grader_model_id": "test-grader-1",
            "runtime_inputs": [runtime], "runtime_inputs_complete": True,
            "runs": runs, "triggers": triggers}
        if case_runtime_inputs is not None:
            result["runtime_inputs"] = sorted({path for paths in case_runtime_inputs.values() for path in paths})
            result["case_runtime_inputs"] = [
                {"case_id": case_id, "runtime_inputs": paths}
                for case_id, paths in case_runtime_inputs.items()
            ]
        path = self.private / "reconciliation.json"
        path.write_text(json.dumps(result))
        return path

    def claude_session_results(self):
        """Reference original-shaped CLI records, separate from responses."""
        path = self.retained_results()
        manifest = json.loads(path.read_text())
        original = json.loads((self.private / "retained.json").read_text())
        for index, run in enumerate(manifest["runs"]):
            response = original["runs"][index]["response"]
            case_id = int(run["case_id"])
            repetition = run["repetition"]
            record = {
                "run_id": f"case-{case_id:02d}-rep-{repetition}",
                "source_revision": self.candidate,
                "session_id": f"constructed-claude-session-{index}",
                "status": "verified-transport",
                "returncode": 0,
                "observed_model": "test-executor-1",
                "response_id": f"constructed-response-{index}",
                "response_sha256": hashlib.sha256(response.encode()).hexdigest(),
                "input_sha256": "a" * 64,
                "stdout_sha256": "b" * 64,
                "stderr_sha256": "c" * 64,
            }
            artifact = self.private / f"claude-record-{index}.json"
            artifact.write_text(json.dumps(record))
            run["execution_record"] = {
                "path": artifact.name,
                "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                "format": "json", "pointer": "",
            }
        path.write_text(json.dumps(manifest))
        return path

    def test_reconciliation_accepts_original_claude_session_records(self):
        receipt = receipts.reconcile(self.repo, self.candidate, self.spec,
                                     self.claude_session_results(), self.candidate)
        self.assertEqual([run["reconciliation"]["execution_identity"]["basis"]
                          for run in receipt["runs"]], ["recorded-claude-session"] * 3)
        result = receipts.check(self.repo, self.request(), {"example/writing": receipt})
        self.assertEqual(result["status"], "pass")

    def change_claude_record(self, path, index, changes):
        manifest = json.loads(path.read_text())
        reference = manifest["runs"][index]["execution_record"]
        artifact = self.private / reference["path"]
        record = json.loads(artifact.read_text())
        for key, value in changes.items():
            if value is None:
                record.pop(key, None)
            else:
                record[key] = value
        artifact.write_text(json.dumps(record))
        reference["sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
        path.write_text(json.dumps(manifest))

    def test_reconciliation_rejects_invalid_claude_session_records(self):
        changes = {
            "missing-session": ({"session_id": None}, "identity is unavailable"),
            "blank-session": ({"session_id": " "}, "identity is unavailable"),
            "failed-status": ({"status": "incomplete"}, "verified transport"),
            "failed-exit": ({"returncode": 1}, "verified transport"),
            "boolean-exit": ({"returncode": False}, "verified transport"),
            "wrong-response": ({"response_sha256": "0" * 64}, "response digest differs"),
            "wrong-coordinate": ({"run_id": "case-02-rep-1"}, "coordinate differs"),
            "wrong-case-alias": ({"case_id": "2"}, "case differs"),
            "wrong-repetition-alias": ({"repetition": 2}, "repetition differs"),
            "wrong-source": ({"source_revision": self.base}, "source revision differs"),
            "wrong-model": ({"observed_model": "another-model"}, "observed model differs"),
            "conflicting-native-agent": ({"native_agent": "different-session"}, "identifiers disagree"),
            "conflicting-thread": ({"execution": {"completed": True, "returncode": 0,
                "thread_ids": ["different-session"],
                "response_sha256": hashlib.sha256(b"Constructed retained response.\n").hexdigest()}},
                "identifiers disagree"),
            "conflicting-response-text": ({"response": "Another response."}, "response differs"),
        }
        for name, (change, message) in changes.items():
            with self.subTest(name=name):
                path = self.claude_session_results()
                self.change_claude_record(path, 0, change)
                with self.assertRaisesRegex(receipts.ReceiptError, message):
                    receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)

    def test_reconciliation_rejects_reused_claude_session(self):
        path = self.claude_session_results()
        first = json.loads((self.private / "claude-record-0.json").read_text())
        self.change_claude_record(path, 1, {"session_id": first["session_id"]})
        with self.assertRaisesRegex(receipts.ReceiptError, "one original execution"):
            receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)

    def test_public_check_rejects_reused_claude_session_identity(self):
        receipt = receipts.reconcile(self.repo, self.candidate, self.spec,
                                     self.claude_session_results(), self.candidate)
        receipt["runs"][1]["reconciliation"]["execution_identity"] = copy.deepcopy(
            receipt["runs"][0]["reconciliation"]["execution_identity"])
        result = receipts.check(self.repo, self.request(), {"example/writing": receipt})
        self.assertEqual(result["status"], "fail")
        self.assertIn("original execution", result["skills"][0]["reason"])

    def test_reconciliation_schema_accepts_optional_case_runtime_inputs(self):
        manifest = json.loads(self.retained_results().read_text())
        manifest["case_runtime_inputs"] = [
            {"case_id": "1", "runtime_inputs": [self.prefix + "/SKILL.md"]}
        ]
        receipts.validate(manifest, "reconciliationResults")

    def test_reconciliation_schema_rejects_authored_selection(self):
        manifest = json.loads(self.retained_results().read_text())
        receipts.validate(manifest, "reconciliationResults")
        manifest["triggers"][0]["observation_kind"] = "authored-selection"
        with self.assertRaisesRegex(receipts.ReceiptError, "schema mismatch"):
            receipts.validate(manifest, "reconciliationResults")

    def heterogeneous_retained_results(self):
        """Construct two source-coordinate cases with distinct delivered references."""
        corpus_path = self.spec["evals"]
        document = json.loads((self.repo / corpus_path).read_text())
        first = document["evals"][0]
        first["id"] = 0
        second = {**copy.deepcopy(first), "id": 1, "prompt": "Write the second answer.",
                  "fixture_paths": ["evals/fixtures/second.md"]}
        document["evals"].append(second)
        self.write(corpus_path, document)
        self.write(self.prefix + "/evals/fixtures/second.md", "Second answer facts.\n")
        self.write(self.prefix + "/references/first.md", "Reference for the first case.\n")
        self.write(self.prefix + "/references/second.md", "Reference for the second case.\n")
        self.candidate = self.commit("two cases with different runtime references")
        manifest_path = self.retained_results({
            "0": [self.prefix + "/SKILL.md", self.prefix + "/references/first.md"],
            "1": [self.prefix + "/SKILL.md", self.prefix + "/references/second.md"],
        })
        manifest = json.loads(manifest_path.read_text())
        self.spec.update(corpus_format="provingkit-v1", case_selection=[
            {"source": corpus_path, "pointer": "/evals/0"},
            {"source": corpus_path, "pointer": "/evals/1"},
            {"source": self.spec["trigger_evals"], "pointer": "/0"},
            {"source": self.spec["trigger_evals"], "pointer": "/1"}])
        for item in manifest["runs"] + manifest["case_runtime_inputs"]:
            index = int(item["case_id"])
            item["case_id"] = {"source": corpus_path, "pointer": f"/evals/{index}", "id": index}
        for index, trigger in enumerate(manifest["triggers"]):
            trigger["case_id"] = {"source": self.spec["trigger_evals"], "pointer": f"/{index}", "id": None}
        manifest_path.write_text(json.dumps(manifest))
        return manifest_path

    def test_reconciliation_accepts_three_runs_for_each_distinct_case_runtime_set(self):
        path = self.heterogeneous_retained_results()
        manifest = json.loads(path.read_text())
        original = (self.private / "retained.json").read_bytes()
        receipt = receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)
        self.assertEqual(receipt["reconciliation"]["case_runtime_inputs"], manifest["case_runtime_inputs"])
        self.assertEqual((self.private / "retained.json").read_bytes(), original)
        self.assertEqual(len(receipt["runs"]), 6)
        for index, run in enumerate(receipt["runs"]):
            reference = "first" if index < 3 else "second"
            fixture = "case" if index < 3 else "second"
            self.assertEqual(set(run["reconciliation"]["inputs"]), {
                self.prefix + "/SKILL.md", self.prefix + f"/references/{reference}.md",
                self.prefix + f"/evals/fixtures/{fixture}.md"})
            binding = manifest["runs"][index]["inputs"][self.prefix + f"/references/{reference}.md"]["value"]
            self.assertIn({key: binding[key] for key in ("sha256", "format", "pointer")},
                          run["reconciliation"]["evidence"])
        self.assertEqual([item["triggered"] for item in receipt["triggers"]], [True, False])
        self.assertEqual([item["observation_kind"] for item in receipt["triggers"]],
                         ["recorded-sentinel-body-load", "recorded-sentinel-body-load"])
        self.assertEqual(receipts.check(self.repo, self.request(), {"example/writing": receipt})["status"], "pass")

    def test_reconciliation_rejects_incomplete_or_ambiguous_case_runtime_coordinates(self):
        path = self.heterogeneous_retained_results()
        original = json.loads(path.read_text())
        for change in ("missing", "duplicate", "unknown", "wrong-pointer", "wrong-id", "id-type", "string-id"):
            with self.subTest(change=change):
                manifest = copy.deepcopy(original)
                table = manifest["case_runtime_inputs"]
                if change == "missing":
                    table.pop()
                elif change == "duplicate":
                    duplicate = copy.deepcopy(table[0])
                    duplicate["runtime_inputs"].reverse()
                    table.append(duplicate)
                elif change == "unknown":
                    unknown = copy.deepcopy(table[0])
                    unknown["case_id"]["pointer"] = "/evals/unknown"
                    table.append(unknown)
                elif change == "wrong-pointer":
                    table[0]["case_id"]["pointer"] = "/evals/1"
                elif change == "wrong-id":
                    table[0]["case_id"]["id"] = 1
                elif change == "id-type":
                    table[0]["case_id"]["id"] = "0"
                else:
                    table[0]["case_id"] = "0"
                path.write_text(json.dumps(manifest))
                with self.assertRaisesRegex(receipts.ReceiptError, "case runtime input coverage"):
                    receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)

    def test_case_runtime_sets_require_entrypoint_bound_sources_and_exact_union(self):
        path = self.heterogeneous_retained_results()
        original = json.loads(path.read_text())
        entrypoint = self.prefix + "/SKILL.md"
        first_reference = self.prefix + "/references/first.md"
        for change in ("missing-entrypoint", "outside-snapshot", "union-missing", "union-extra"):
            with self.subTest(change=change):
                manifest = copy.deepcopy(original)
                paths = manifest["case_runtime_inputs"][0]["runtime_inputs"]
                if change == "missing-entrypoint":
                    paths.remove(entrypoint)
                    for run in manifest["runs"][:3]:
                        del run["inputs"][entrypoint]
                elif change == "outside-snapshot":
                    paths.remove(first_reference)
                    paths.append("unbound.md")
                    for run in manifest["runs"][:3]:
                        run["inputs"]["unbound.md"] = run["inputs"].pop(first_reference)
                elif change == "union-missing":
                    manifest["runtime_inputs"].remove(first_reference)
                else:
                    manifest["runtime_inputs"].append(self.prefix + "/evals/fixtures/case.md")
                path.write_text(json.dumps(manifest))
                message = "runtime input union" if change.startswith("union-") else "declared case runtime inputs"
                with self.assertRaisesRegex(receipts.ReceiptError, message):
                    receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)

    def test_case_runtime_schema_requires_nonempty_unique_paths_and_honest_completeness(self):
        path = self.heterogeneous_retained_results()
        manifest = json.loads(path.read_text())
        receipt = receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)
        for public in (False, True):
            for change in ("empty-table", "empty-paths", "duplicate-path", "unknown-property",
                           "missing-paths", "absolute-path", "parent-path", "false-completeness"):
                with self.subTest(public=public, change=change):
                    document = copy.deepcopy(receipt if public else manifest)
                    declaration = document["reconciliation"] if public else document
                    table = declaration["case_runtime_inputs"]
                    if change == "empty-table":
                        table.clear()
                    elif change == "empty-paths":
                        table[0]["runtime_inputs"].clear()
                    elif change == "duplicate-path":
                        table[0]["runtime_inputs"].append(table[0]["runtime_inputs"][0])
                    elif change == "unknown-property":
                        table[0]["authenticated"] = True
                    elif change == "missing-paths":
                        del table[0]["runtime_inputs"]
                    elif change == "absolute-path":
                        table[0]["runtime_inputs"][0] = "/outside.md"
                    elif change == "parent-path":
                        table[0]["runtime_inputs"][0] = "../outside.md"
                    else:
                        declaration["runtime_inputs_complete"] = False
                    with self.assertRaisesRegex(receipts.ReceiptError, "schema mismatch"):
                        receipts.validate(document, None if public else "reconciliationResults")

    def test_absent_case_runtime_table_keeps_uniform_delivery_and_public_shape(self):
        path = self.retained_results()
        original = json.loads(path.read_text())
        receipt = receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)
        self.assertEqual(receipt["reconciliation"], {
            "runtime_inputs": [self.prefix + "/SKILL.md"], "runtime_inputs_complete": True})
        self.assertEqual(receipts.check(self.repo, self.request(), {"example/writing": receipt})["status"], "pass")
        for change in ("missing", "extra"):
            with self.subTest(change=change):
                manifest = copy.deepcopy(original)
                inputs = manifest["runs"][1]["inputs"]
                if change == "missing":
                    del inputs[self.prefix + "/SKILL.md"]
                else:
                    inputs[self.spec["evals"]] = manifest["runs"][1]["graded_response"]
                path.write_text(json.dumps(manifest))
                with self.assertRaisesRegex(receipts.ReceiptError, "delivered input coverage"):
                    receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)
                changed = copy.deepcopy(receipt)
                public_inputs = changed["runs"][1]["reconciliation"]["inputs"]
                if change == "missing":
                    del public_inputs[self.prefix + "/SKILL.md"]
                else:
                    public_inputs[self.spec["evals"]] = changed["snapshot"]["inputs"][self.spec["evals"]]["sha256"]
                result = receipts.check(self.repo, self.request(), {"example/writing": changed})
                self.assertEqual(result["status"], "fail")
                self.assertIn("delivered input", result["skills"][0]["reason"])

    def test_each_case_repetition_requires_its_declared_inputs_fixtures_and_current_bytes(self):
        path = self.heterogeneous_retained_results()
        original = json.loads(path.read_text())
        first_reference = self.prefix + "/references/first.md"
        second_reference = self.prefix + "/references/second.md"
        fixture = self.prefix + "/evals/fixtures/second.md"
        for change in ("missing-runtime", "missing-fixture", "extra", "wrong-case", "runtime-bytes", "fixture-bytes"):
            with self.subTest(change=change):
                manifest = copy.deepcopy(original)
                run = manifest["runs"][4]
                inputs = run["inputs"]
                if change == "missing-runtime":
                    del inputs[second_reference]
                elif change == "missing-fixture":
                    del inputs[fixture]
                elif change == "extra":
                    inputs[first_reference] = manifest["runs"][0]["inputs"][first_reference]
                elif change == "wrong-case":
                    del inputs[second_reference]
                    inputs[first_reference] = manifest["runs"][0]["inputs"][first_reference]
                elif change == "runtime-bytes":
                    inputs[second_reference] = run["graded_response"]
                else:
                    inputs[fixture] = manifest["runs"][0]["inputs"][self.prefix + "/evals/fixtures/case.md"]
                path.write_text(json.dumps(manifest))
                message = "historical delivered input" if change.endswith("-bytes") else "delivered input coverage"
                with self.assertRaisesRegex(receipts.ReceiptError, message):
                    receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)

    def test_public_check_rejects_case_declaration_and_delivery_tampering(self):
        path = self.heterogeneous_retained_results()
        original = receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)
        first_reference = self.prefix + "/references/first.md"
        second_reference = self.prefix + "/references/second.md"
        for change in ("missing-case", "duplicate-case", "unknown-case", "missing-entrypoint", "outside-snapshot",
                       "union", "wrong-case", "dropped-table", "missing-runtime", "missing-fixture", "extra", "changed-bytes"):
            with self.subTest(change=change):
                receipt = copy.deepcopy(original)
                declaration = receipt["reconciliation"]
                table = declaration["case_runtime_inputs"]
                inputs = receipt["runs"][4]["reconciliation"]["inputs"]
                message = "delivered input"
                if change == "missing-case":
                    table.pop()
                    message = "case runtime input coverage"
                elif change == "duplicate-case":
                    duplicate = copy.deepcopy(table[0])
                    duplicate["runtime_inputs"].reverse()
                    table.append(duplicate)
                    message = "case runtime input coverage"
                elif change == "unknown-case":
                    table[0]["case_id"]["pointer"] = "/evals/unknown"
                    message = "case runtime input coverage"
                elif change == "missing-entrypoint":
                    table[0]["runtime_inputs"].remove(self.prefix + "/SKILL.md")
                    message = "declared case runtime inputs"
                elif change == "outside-snapshot":
                    table[0]["runtime_inputs"].append("unbound.md")
                    message = "declared case runtime inputs"
                elif change == "union":
                    declaration["runtime_inputs"].remove(first_reference)
                    message = "runtime input union"
                elif change == "wrong-case":
                    table[0]["runtime_inputs"], table[1]["runtime_inputs"] = (
                        table[1]["runtime_inputs"], table[0]["runtime_inputs"])
                elif change == "dropped-table":
                    del declaration["case_runtime_inputs"]
                elif change == "missing-runtime":
                    del inputs[second_reference]
                elif change == "missing-fixture":
                    del inputs[self.prefix + "/evals/fixtures/second.md"]
                elif change == "extra":
                    inputs[first_reference] = receipt["snapshot"]["inputs"][first_reference]["sha256"]
                else:
                    inputs[second_reference] = "0" * 64
                result = receipts.check(self.repo, self.request(), {"example/writing": receipt})
                self.assertEqual(result["status"], "fail")
                self.assertIn(message, result["skills"][0]["reason"])

    def test_case_delivery_omission_preserves_full_source_byte_and_mode_freshness(self):
        path = self.heterogeneous_retained_results()
        receipt = receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)
        reference = self.prefix + "/references/first.md"
        self.assertIn(reference, receipt["snapshot"]["inputs"])
        self.assertNotIn(reference, receipt["runs"][3]["reconciliation"]["inputs"])
        original = (self.repo / reference).read_bytes()
        for change in ("bytes", "mode"):
            with self.subTest(change=change):
                (self.repo / reference).write_bytes(original if change == "mode" else b"Changed reference.\n")
                (self.repo / reference).chmod(0o755 if change == "mode" else 0o644)
                later = self.commit("changed omitted case dependency " + change)
                result = receipts.check(self.repo, self.request(later), {"example/writing": receipt})
                self.assertEqual(result["status"], "fail")
                self.assertIn("stale evaluated input closure", result["skills"][0]["reason"])

    def test_prepared_producer_rejects_sentinel_body_load_observation_kind(self):
        snapshot = receipts.prepare(self.repo, self.candidate, self.spec)
        path = self.results(snapshot)
        observation_path = self.private / "trigger-1.json"
        observation = json.loads(observation_path.read_text())
        observation["observation_kind"] = "recorded-sentinel-body-load"
        observation_path.write_text(json.dumps(observation))
        with self.assertRaisesRegex(receipts.ReceiptError, "triggerObservation schema mismatch"):
            receipts.produce(self.repo, snapshot, path)

    def test_reconciliation_keeps_historical_source_separate_from_processor(self):
        processor = self.candidate
        self.git("rm", receipts.TOOL_PATH, receipts.POLICY_PATH, receipts.SCHEMA_PATH)
        self.candidate = self.commit("historical source without processor")
        with self.assertRaises(receipts.ReceiptError):
            receipts.prepare(self.repo, self.candidate, self.spec)
        path = self.retained_results()
        original = (self.private / "retained.json").read_bytes()
        receipt = receipts.reconcile(self.repo, self.candidate, self.spec, path, processor)
        self.assertEqual(receipt["method"], "reconciled-after-run")
        self.assertEqual(receipt["processing"]["revision"], processor)
        self.assertNotIn(receipts.TOOL_PATH, receipt["snapshot"]["inputs"])
        self.assertEqual((self.private / "retained.json").read_bytes(), original)
        self.assertNotIn("snapshot_sha256", original.decode())
        self.assertEqual(receipts.check(self.repo, self.request(), {"example/writing": receipt})["status"], "pass")
        self.assertFalse(receipt["runs"][2]["expectations"][1]["passed"])
        self.assertEqual(receipt["triggers"][0]["observation_kind"], "recorded-sentinel-body-load")

    def test_reconciliation_rejects_changed_inputs_missing_models_and_reused_execution(self):
        path = self.retained_results()
        original = json.loads(path.read_text())
        for change, message in (("input", "input"), ("model", "model"), ("reused", "execution")):
            with self.subTest(change=change):
                manifest = copy.deepcopy(original)
                if change == "input":
                    manifest["runs"][0]["inputs"][self.prefix + "/SKILL.md"] = manifest["runs"][0]["graded_response"]
                elif change == "model":
                    manifest["runs"][0]["grader_model"]["value"] = manifest["runs"][0]["prompt"]
                else:
                    manifest["runs"][1]["execution_record"] = manifest["runs"][0]["execution_record"]
                path.write_text(json.dumps(manifest))
                with self.assertRaisesRegex(receipts.ReceiptError, message):
                    receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)

    def test_reconciliation_does_not_count_fields_of_one_execution_as_three_runs(self):
        path = self.retained_results()
        manifest = json.loads(path.read_text())
        first = manifest["runs"][0]
        manifest["runs"] = []
        for repetition, pointer in enumerate(("/runs/0", "/runs/0/prompt", "/runs/0/response"), 1):
            run = copy.deepcopy(first)
            run["repetition"] = repetition
            run["execution_record"]["pointer"] = pointer
            manifest["runs"].append(run)
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(receipts.ReceiptError, "execution"):
            receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)

    def test_reconciliation_rejects_copied_execution_identity_across_record_shapes(self):
        path = self.retained_results()
        artifact = self.private / "retained.json"
        original = json.loads(artifact.read_text())
        for different_shape in (False, True, "conflicting-alias"):
            with self.subTest(different_shape=different_shape):
                document = copy.deepcopy(original)
                first, second = document["runs"][:2]
                second["native_agent"] = first["native_agent"]
                if different_shape:
                    second["execution"] = {"completed": True, "returncode": 0,
                        "thread_ids": ["different-thread" if different_shape == "conflicting-alias" else first["native_agent"]],
                        "response_sha256": hashlib.sha256(second["response"].encode()).hexdigest()}
                artifact.write_text(json.dumps(document))
                manifest = json.loads(path.read_text())
                digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
                def refresh(value):
                    if isinstance(value, dict):
                        if value.get("path") == artifact.name:
                            value["sha256"] = digest
                        for item in value.values(): refresh(item)
                    elif isinstance(value, list):
                        for item in value: refresh(item)
                refresh(manifest)
                path.write_text(json.dumps(manifest))
                with self.assertRaisesRegex(receipts.ReceiptError, "original execution"):
                    receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)

    def test_public_reconciliation_rejects_reused_execution_identity(self):
        receipt = receipts.reconcile(self.repo, self.candidate, self.spec, self.retained_results(), self.candidate)
        first, second = receipt["runs"][:2]
        second["reconciliation"]["execution_identity"] = copy.deepcopy(first["reconciliation"]["execution_identity"])
        second["reconciliation"]["execution_identity"]["basis"] = "recorded-thread"
        result = receipts.check(self.repo, self.request(), {"example/writing": receipt})
        self.assertEqual(result["status"], "fail")
        self.assertIn("original execution", result["skills"][0]["reason"])

    def test_reconciliation_rejects_authored_selection_and_mismatched_grade_response(self):
        path = self.retained_results()
        original = json.loads(path.read_text())
        authored = copy.deepcopy(original)
        authored["triggers"][0]["observation_kind"] = "authored-selection"
        path.write_text(json.dumps(authored))
        with self.assertRaisesRegex(receipts.ReceiptError, "schema mismatch"):
            receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)
        wrong_response = copy.deepcopy(original)
        wrong_response["runs"][0]["graded_response"]["value"] = wrong_response["runs"][0]["prompt"]
        path.write_text(json.dumps(wrong_response))
        with self.assertRaisesRegex(receipts.ReceiptError, "response"):
            receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)

    def test_reconciled_public_record_rejects_unknown_coordinate_and_false_sentinel(self):
        receipt = receipts.reconcile(self.repo, self.candidate, self.spec, self.retained_results(), self.candidate)
        bad_coordinate = copy.deepcopy(receipt)
        bad_coordinate["runs"][0]["case_id"] = "unknown"
        result = receipts.check(self.repo, self.request(), {"example/writing": bad_coordinate})
        self.assertEqual(result["status"], "fail")
        self.assertIn("coverage", result["skills"][0]["reason"])
        forged = copy.deepcopy(receipt)
        forged["triggers"][0]["reconciliation"]["body_loaded"] = False
        result = receipts.check(self.repo, self.request(), {"example/writing": forged})
        self.assertEqual(result["status"], "fail")
        self.assertIn("boundary", result["skills"][0]["reason"])

    def test_retained_reference_preserves_jsonl_line_coordinates(self):
        path = self.private / "trace.jsonl"
        path.write_text('{"first":1}\n\n{"second":2}\n')
        evidence = receipts._RetainedEvidence(self.private)
        reference = {"path": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                     "format": "jsonl", "pointer": "/2/second"}
        self.assertEqual(evidence.value(reference), 2)

    def test_normalized_corpus_preserves_zero_and_full_ordered_routing_sequence(self):
        path = self.spec["evals"]
        document = json.loads((self.repo / path).read_text())
        document["evals"][0]["id"] = 0
        self.write(path, document)
        routing = "evals/routing.json"
        self.write(routing, {"semantic_definition": {"path": "evals/control.json"}, "skills": [{
            "id": "example:writing", "cold_start": "Write.", "explicit": "$writing",
            "supplemental": {"positive": "Write and edit.", "positive_expected_skills": ["writing", "editing", "writing"],
                "negative": "Edit only.", "negative_expected_skills": ["editing"]}}]})
        revision = self.commit("zero identity and routing")
        spec = {**self.spec, "corpus_format": "provingkit-v1", "case_selection": [
            {"source": path, "pointer": "/evals/0"},
            {"source": routing, "pointer": "/skills/0/supplemental/positive"},
            {"source": routing, "pointer": "/skills/0/supplemental/negative"}]}
        cases, triggers, fixtures = receipts.corpus(self.repo, {"candidate_revision": revision, "skill": spec})
        coordinate = {"source": path, "pointer": "/evals/0", "id": 0}
        self.assertIn(receipts.coordinate_key(coordinate), cases)
        self.assertEqual(list(triggers.values()), [["writing", "editing", "writing"], ["editing"]])
        self.assertEqual(fixtures, {self.prefix + "/evals/fixtures/case.md"})

    def normalized_retained_results(self):
        """Use original document coordinates throughout the public workflow."""
        path = self.spec["evals"]
        document = json.loads((self.repo / path).read_text())
        document["evals"][0]["id"] = 0
        self.write(path, document)
        self.candidate = self.commit("original zero case identity")
        manifest_path = self.retained_results()
        manifest = json.loads(manifest_path.read_text())
        self.spec.update(corpus_format="provingkit-v1", case_selection=[
            {"source": path, "pointer": "/evals/0"},
            {"source": self.spec["trigger_evals"], "pointer": "/0"},
            {"source": self.spec["trigger_evals"], "pointer": "/1"}])
        for run in manifest["runs"]:
            run["case_id"] = {"source": path, "pointer": "/evals/0", "id": 0}
        for index, trigger in enumerate(manifest["triggers"]):
            trigger["case_id"] = {"source": self.spec["trigger_evals"], "pointer": f"/{index}", "id": None}
        manifest_path.write_text(json.dumps(manifest))
        return manifest_path

    def test_normalized_reconciliation_retains_zero_identity_and_processor_dependencies(self):
        path = self.normalized_retained_results()
        receipt = receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)
        self.assertEqual(receipt["runs"][0]["case_id"]["id"], 0)
        self.assertEqual(receipts.check(self.repo, self.request(), {"example/writing": receipt})["status"], "pass")
        self.assertIn("scripts/behavior_eval_inventory.py", receipt["processing"]["inputs"])
        self.assertIn("scripts/behavior_eval_corpora.py", receipt["processing"]["inputs"])
        self.write(self.spec["content_lock"], {"whole-lock": "another skill changed"})
        self.candidate = self.commit("whole lock freshness changed")
        result = receipts.check(self.repo, self.request(), {"example/writing": receipt})
        self.assertEqual(result["status"], "fail")
        self.assertIn("stale evaluated input closure", result["skills"][0]["reason"])

    def routing_results(self):
        """Construct a whole supplied catalog and raw sequential native reads."""
        for name in ("writing", "editing"):
            self.write(f"plugins/example/skills/{name}/SKILL.md",
                f"---\nname: {name}\ndescription: Use when {name}.\n---\nReal instructions.\n")
        self.write("plugins/example/topology.json", {"skills": {"writing": {}, "editing": {}}})
        self.write("release/provingkit/definition-v1.json", {"membership": {"members": [
            {"id": "example", "content_identity": {"path": self.spec["content_lock"]}}]}})
        routing = "evals/routing.json"
        self.write(routing, {"semantic_definition": {"path": "evals/control.json"}, "skills": [{
            "id": "example:writing", "cold_start": "Write.", "explicit": "$writing",
            "supplemental": {"positive": "Write, edit, then write.",
                "positive_expected_skills": ["writing", "editing", "writing"],
                "negative": "Edit.", "negative_expected_skills": ["editing"]}}]})
        path = self.normalized_retained_results()
        self.spec["case_selection"].append({"source": routing, "pointer": "/skills/0/supplemental/positive"})
        self.spec["dependencies"] += ["release/provingkit/definition-v1.json", "plugins/example/topology.json",
            "plugins/example/skills/editing/SKILL.md"]
        offered, markers, members, body_refs = [], [], [], {}
        for name in ("editing", "writing"):
            source_path = f"plugins/example/skills/{name}/SKILL.md"
            body_path = f"/tmp/constructed-routing/{name}/SKILL.md"
            token = name.upper() + "_TOKEN"
            body = token + "\n"
            args = {"cmd": "/usr/bin/cat -- " + body_path, "shell": "/bin/sh", "login": False,
                    "tty": False, "max_output_tokens": 1024}
            call = "text(await tools.exec_command(" + json.dumps(args) + "));"
            offered.append({"name": name, "description": f"Use when {name}.", "body_path": body_path, "read_call": call})
            markers.append({"name": name, "skill_id": "example:" + name, "token": token,
                "absolute_body_path": body_path, "allowed_tool": "functions.exec", "allowed_read_javascript": call,
                "body": {"path": name + ".md", "sha256": hashlib.sha256(body.encode()).hexdigest(), "bytes": len(body)}})
            members.append({"id": "example:" + name, "name": name, "description": f"Use when {name}.",
                "source_path": source_path, "source_sha256": hashlib.sha256((self.repo / source_path).read_bytes()).hexdigest()})
            (self.private / (name + ".md")).write_text(body)
            body_refs[name] = {"path": name + ".md", "sha256": hashlib.sha256(body.encode()).hexdigest(),
                               "format": "utf8", "pointer": ""}
        query = "Write, edit, then write."
        offered_text = json.dumps(offered, indent=2) + "\n"
        protocol = "Choose from the supplied catalog and record every selected body read.\n"
        message = protocol + "\nRequest:\n" + query + "\n\nAvailable skill catalog:\n" + offered_text
        final = '{"tokens":["WRITING_TOKEN","EDITING_TOKEN","WRITING_TOKEN"]}'
        trace = [{"type": "session_meta", "payload": {"id": "constructed-session"}},
            {"type": "turn_context", "payload": {"turn_id": "turn-1", "model": "test-executor-1"}},
            {"type": "event_msg", "payload": {"type": "task_started", "turn_id": "turn-1"}}]
        for index, name in enumerate(("writing", "editing", "writing")):
            entry = next(row for row in offered if row["name"] == name)
            command = "/usr/bin/cat -- " + entry["body_path"]
            body = name.upper() + "_TOKEN\n"
            trace += [
                {"type": "response_item", "payload": {"type": "custom_tool_call", "name": "exec",
                    "call_id": f"read-{index}", "input": entry["read_call"]}},
                {"type": "event_msg", "payload": {"type": "item_completed", "turn_id": "turn-1",
                    "item": {"type": "CommandExecution", "id": f"command-{index}",
                        "command": ["/bin/sh", "-c", command], "parsed_cmd": [{"type": "read", "cmd": command}],
                        "status": "completed", "exit_code": 0, "stdout": body, "stderr": "", "aggregated_output": body}}},
                {"type": "response_item", "payload": {"type": "custom_tool_call_output", "call_id": f"read-{index}",
                    "output": [{"type": "input_text", "text": "Script completed\nOutput:\n"},
                        {"type": "input_text", "text": json.dumps({"exit_code": 0, "output": body})}]}}]
        trace += [{"type": "response_item", "payload": {"type": "message", "role": "assistant", "channel": "final",
                "content": [{"type": "output_text", "text": final}]}},
            {"type": "event_msg", "payload": {"type": "task_complete", "turn_id": "turn-1",
                "last_agent_message": final, "started_at": 1, "completed_at": 2}}]
        document = {"query": query, "model": "test-executor-1", "source_catalog": {"revision": self.candidate,
                "tree": self.git("rev-parse", "HEAD^{tree}"), "entries": members},
            "offered_catalog": offered_text, "marker_map": markers, "protocol": protocol,
            "executor_message": message, "trace": trace,
            "dispatch": {"call_id": "spawn-1", "arguments": {"task_name": "constructed_route", "fork_turns": "none", "message": message}},
            "spawn": {"call_id": "spawn-1", "agent_thread_id": "constructed-session", "agent_path": "/root/constructed_route"}}
        artifact = self.private / "routing.json"
        artifact.write_text(json.dumps(document))
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        def ref(pointer):
            return {"path": artifact.name, "sha256": digest, "format": "json", "pointer": pointer}
        manifest = json.loads(path.read_text())
        manifest["triggers"].append({"case_id": {"source": routing, "pointer": "/skills/0/supplemental/positive", "id": None},
            "observation_kind": "recorded-sentinel-sequence", "record": ref(""),
            "model": {"basis": "configured", "value": ref("/model")}, "query": ref("/query"),
            "limits": ["Supplied-catalog body-load surrogate; ambient context and complete provider inputs are not verified."],
            "sequence": {**{key: ref("/" + key) for key in ("source_catalog", "offered_catalog", "marker_map",
                "protocol", "executor_message", "trace", "dispatch", "spawn")}, "bodies": body_refs, "prompt_basis": "frozen-dispatch-argument"}})
        path.write_text(json.dumps(manifest))
        return path

    def test_catalog_routing_derives_complete_order_and_duplicate_reads_from_native_events(self):
        path = self.routing_results()
        receipt = receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)
        trigger = receipt["triggers"][-1]
        self.assertEqual(trigger["observed_selection"], ["writing", "editing", "writing"])
        self.assertEqual(trigger["reconciliation"]["source_binding"], "supplied-catalog-body-load")
        self.assertEqual(len(trigger["reconciliation"]["catalog"]["members"]), 2)
        self.assertEqual(receipts.check(self.repo, self.request(), {"example/writing": receipt})["status"], "pass")

    def test_routing_public_check_rejects_rewritten_sequence_or_incomplete_catalog(self):
        path = self.routing_results()
        original = receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)
        for change in ("sequence", "catalog", "read", "dispatch"):
            with self.subTest(change=change):
                receipt = copy.deepcopy(original)
                trigger = receipt["triggers"][-1]
                if change == "sequence":
                    trigger["observed_selection"] = ["writing"]
                elif change == "catalog":
                    trigger["reconciliation"]["catalog"]["members"].pop()
                elif change == "read":
                    trigger["reconciliation"]["catalog"]["reads"][1]["body_sha256"] = "0" * 64
                else:
                    trigger["reconciliation"]["catalog"]["dispatch"]["record"]["sha256"] = "0" * 64
                result = receipts.check(self.repo, self.request(), {"example/writing": receipt})
                self.assertEqual(result["status"], "fail")
                self.assertIn("routing", result["skills"][0]["reason"])

    def rewrite_routing_artifact(self, manifest_path, document):
        artifact = self.private / "routing.json"
        artifact.write_text(json.dumps(document))
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        manifest = json.loads(manifest_path.read_text())
        def refresh(value):
            if isinstance(value, dict):
                if value.get("path") == artifact.name:
                    value["sha256"] = digest
                for item in value.values(): refresh(item)
            elif isinstance(value, list):
                for item in value: refresh(item)
        refresh(manifest)
        manifest_path.write_text(json.dumps(manifest))

    def test_routing_rejects_off_catalog_tools_and_incomplete_or_mismatched_raw_records(self):
        path = self.routing_results()
        original = json.loads((self.private / "routing.json").read_text())
        for change in ("unpaired", "parallel", "body", "outer", "tokens", "catalog", "completion", "tool-event", "web-call", "uncompleted-start"):
            with self.subTest(change=change):
                document = copy.deepcopy(original)
                events = document["trace"]
                if change == "unpaired":
                    events[5]["payload"]["call_id"] = "another-call"
                elif change == "parallel":
                    events.insert(4, copy.deepcopy(events[6]))
                elif change == "body":
                    events[4]["payload"]["item"]["stdout"] = "DIFFERENT\n"
                elif change == "outer":
                    events[5]["payload"]["output"][1]["text"] = json.dumps({"exit_code": 0, "output": "DIFFERENT\n"})
                elif change == "tokens":
                    events[-2]["payload"]["content"][0]["text"] = '{"tokens":[]}'
                    events[-1]["payload"]["last_agent_message"] = '{"tokens":[]}'
                elif change == "catalog":
                    catalog = json.loads(document["offered_catalog"])
                    catalog.pop()
                    document["offered_catalog"] = json.dumps(catalog)
                elif change == "completion":
                    events[-1]["payload"]["error"] = {"message": "interrupted"}
                elif change == "tool-event":
                    events.insert(4, {"type": "event_msg", "payload": {"type": "item_completed",
                        "turn_id": "turn-1", "item": {"type": "McpToolCall", "id": "unaccounted"}}})
                elif change == "web-call":
                    events.insert(4, {"type": "response_item", "payload": {"type": "web_search_call"}})
                else:
                    events.insert(4, {"type": "event_msg", "payload": {"type": "item_started",
                        "turn_id": "turn-1", "item": {"type": "CommandExecution", "id": "uncompleted"}}})
                self.rewrite_routing_artifact(path, document)
                with self.assertRaises(receipts.ReceiptError):
                    receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)

    def test_routing_valid_extra_read_is_retained_as_failed_selection(self):
        path = self.routing_results()
        document = json.loads((self.private / "routing.json").read_text())
        extra = copy.deepcopy(document["trace"][3:6])
        extra[0]["payload"]["call_id"] = extra[2]["payload"]["call_id"] = "extra-read"
        extra[1]["payload"]["item"]["id"] = "extra-command"
        document["trace"][-2:-2] = extra
        final = '{"tokens":["WRITING_TOKEN","EDITING_TOKEN","WRITING_TOKEN","WRITING_TOKEN"]}'
        document["trace"][-2]["payload"]["content"][0]["text"] = final
        document["trace"][-1]["payload"]["last_agent_message"] = final
        self.rewrite_routing_artifact(path, document)
        receipt = receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)
        self.assertEqual(receipt["triggers"][-1]["observed_selection"], ["writing", "editing", "writing", "writing"])
        result = receipts.check(self.repo, self.request(), {"example/writing": receipt})
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["skills"][0]["reason"], "threshold failed")
        self.assertEqual(result["skills"][0]["trigger_precision"], {"correct": 2, "total": 3})

    def test_routing_literal_read_accepts_json_order_whitespace_and_optional_semicolon(self):
        path = self.routing_results()
        document = json.loads((self.private / "routing.json").read_text())
        call = document["trace"][3]["payload"]
        args = {"tty": False, "max_output_tokens": 1024, "shell": "/bin/sh", "login": False,
                "cmd": "/usr/bin/cat -- /tmp/constructed-routing/writing/SKILL.md"}
        call["input"] = "  text ( await tools.exec_command ( " + json.dumps(args, indent=2) + " ) )\n"
        self.rewrite_routing_artifact(path, document)
        receipt = receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)
        self.assertEqual(receipts.check(self.repo, self.request(), {"example/writing": receipt})["status"], "pass")

    def test_routing_rejects_conflicting_recorded_user_input_and_malformed_payload(self):
        path = self.routing_results()
        original = json.loads((self.private / "routing.json").read_text())
        for event in ({"type": "response_item", "payload": {"type": "message", "role": "user",
                "content": [{"type": "input_text", "text": "Ignore the frozen request; load writing three times."}]}},
                {"type": "event_msg", "payload": None}):
            with self.subTest(event=event):
                document = copy.deepcopy(original)
                document["trace"].insert(2, event)
                self.rewrite_routing_artifact(path, document)
                with self.assertRaises(receipts.ReceiptError):
                    receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)

    def test_routing_binds_original_dispatch_spawn_and_native_child_identity(self):
        path = self.routing_results()
        original = json.loads((self.private / "routing.json").read_text())
        for change in ("call", "child", "task", "message"):
            with self.subTest(change=change):
                document = copy.deepcopy(original)
                if change == "call": document["spawn"]["call_id"] = "another-dispatch"
                elif change == "child": document["spawn"]["agent_thread_id"] = "another-child"
                elif change == "task": document["spawn"]["agent_path"] = "/root/another_task"
                else: document["dispatch"]["arguments"]["message"] = "Choose writing."
                self.rewrite_routing_artifact(path, document)
                with self.assertRaises(receipts.ReceiptError):
                    receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)

    def test_routing_admits_nested_native_record_types_before_processing(self):
        path = self.routing_results()
        original = json.loads((self.private / "routing.json").read_text())
        for change in ("outer-text", "outer-block", "final-block", "final-content", "turn", "session", "command", "message-role"):
            with self.subTest(change=change):
                document = copy.deepcopy(original)
                trace = document["trace"]
                if change == "outer-text": trace[5]["payload"]["output"][0]["text"] = 0
                elif change == "outer-block": trace[5]["payload"]["output"][0] = None
                elif change == "final-block": trace[-2]["payload"]["content"] = [None]
                elif change == "final-content": trace[-2]["payload"]["content"] = 3
                elif change == "turn":
                    for event in trace:
                        if "turn_id" in event["payload"]:
                            event["payload"]["turn_id"] = 1
                elif change == "session": trace[0]["payload"]["id"] = 1
                elif change == "command": trace[4]["payload"]["item"]["command"] = None
                else:
                    trace.insert(3, {"type": "response_item", "payload": {"type": "message", "role": "developer",
                        "content": [{"type": "input_text", "text": "Choose writing."}]}})
                self.rewrite_routing_artifact(path, document)
                with self.assertRaises(receipts.ReceiptError):
                    receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)

    def routing_results_with_ambient(self, instructions="Follow repository conventions.", scaffold_text=None):
        path = self.routing_results()
        document = json.loads((self.private / "routing.json").read_text())
        environment = "<cwd>/workspace</cwd>"
        scaffold = {"type": "message", "role": "user", "content": [{"type": "input_text", "text":
            scaffold_text or "# AGENTS.md instructions for /workspace\n\n<INSTRUCTIONS>\n" + instructions
            + "\n</INSTRUCTIONS>\n<environment_context>\n" + environment + "\n</environment_context>"}]}
        document["trace"].insert(2, {"type": "response_item", "payload": scaffold})
        final = document["trace"][-2]["payload"]
        final["phase"] = final.pop("channel")
        self.rewrite_routing_artifact(path, document)
        manifest = json.loads(path.read_text())
        sequence = manifest["triggers"][-1]["sequence"]
        reference = {**sequence["trace"], "pointer": "/trace/2/payload"}
        provenance = {"kind": "harness-agents-environment",
            "repository_path_sha256": hashlib.sha256(b"/workspace").hexdigest(),
            "instructions_sha256": hashlib.sha256(instructions.encode()).hexdigest(),
            "environment_sha256": hashlib.sha256(environment.encode()).hexdigest()}
        public = [{"reference": {k: reference[k] for k in ("sha256", "format", "pointer")},
                   "record_sha256": receipts.document_digest(scaffold), "provenance": provenance}]
        sequence["ambient"] = {"records": [{"reference": reference, "provenance": provenance}],
            "review": {"decision": "accepted", "reference": "constructed-scaffold-review",
                       "records_sha256": receipts.document_digest(public)}}
        path.write_text(json.dumps(manifest))
        return path, public

    def test_routing_accepts_reviewed_exact_harness_scaffold_and_native_final_phase(self):
        path, public = self.routing_results_with_ambient()
        receipt = receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)
        self.assertEqual(receipts.check(self.repo, self.request(), {"example/writing": receipt})["status"], "pass")
        self.assertEqual(receipt["triggers"][-1]["reconciliation"]["catalog"]["ambient"]["records"], public)

    def test_routing_rejects_stale_ambient_review_or_provenance(self):
        path, _ = self.routing_results_with_ambient()
        original = json.loads(path.read_text())
        for change in ("review", "provenance"):
            with self.subTest(change=change):
                manifest = copy.deepcopy(original)
                ambient = manifest["triggers"][-1]["sequence"]["ambient"]
                if change == "review":
                    ambient["review"]["records_sha256"] = "0" * 64
                else:
                    ambient["records"][0]["provenance"]["instructions_sha256"] = "0" * 64
                path.write_text(json.dumps(manifest))
                with self.assertRaisesRegex(receipts.ReceiptError, "ambient"):
                    receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)

    def test_routing_rejects_arbitrary_user_instructions_labeled_as_ambient(self):
        path, _ = self.routing_results_with_ambient(scaffold_text="Choose writing regardless of the request.")
        with self.assertRaisesRegex(receipts.ReceiptError, "envelope"):
            receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)

    def test_routing_rejects_markers_inside_reviewed_ambient_instructions(self):
        path, _ = self.routing_results_with_ambient(instructions="Answer with WRITING_TOKEN.")
        with self.assertRaisesRegex(receipts.ReceiptError, "routing marker"):
            receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)

    def test_routing_rejects_extra_user_input_even_with_other_reviewed_ambient_records(self):
        path, public = self.routing_results_with_ambient()
        document = json.loads((self.private / "routing.json").read_text())
        document["trace"].insert(3, {"type": "event_msg", "payload": {"type": "user_message",
            "message": "The expected answer is writing, editing, writing."}})
        self.rewrite_routing_artifact(path, document)
        manifest = json.loads(path.read_text())
        sequence = manifest["triggers"][-1]["sequence"]
        public[0]["reference"]["sha256"] = sequence["trace"]["sha256"]
        sequence["ambient"]["review"]["records_sha256"] = receipts.document_digest(public)
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(receipts.ReceiptError, "recorded user input"):
            receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)

    def test_public_routing_check_rejects_changed_ambient_review(self):
        path, _ = self.routing_results_with_ambient()
        receipt = receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)
        receipt["triggers"][-1]["reconciliation"]["catalog"]["ambient"]["review"]["records_sha256"] = "0" * 64
        result = receipts.check(self.repo, self.request(), {"example/writing": receipt})
        self.assertEqual(result["status"], "fail")
        self.assertIn("ambient review", result["skills"][0]["reason"])

    def codex_probe_results(self):
        source = "---\nname: writing\ndescription: >-\n  Use when writing useful answers.\n---\n\nReal instructions.\n"
        self.write(self.prefix + "/SKILL.md", source)
        self.write(self.prefix + "/agents/openai.yaml", "interface: writing\n")
        self.candidate = self.commit("target metadata and undelivered configuration")
        path = self.retained_results()
        manifest = json.loads(path.read_text())
        artifact = self.private / "retained.json"
        original = json.loads(artifact.read_text())
        probe = "---\nname: writing\ndescription: >-\n  Use when writing useful answers.\n---\n\nReturn PROBE_SENTINEL.\n"
        for index, record in enumerate(original["triggers"]):
            record["probe_skill"] = probe
            record["probe_prompt"] = "If no temporary skill is loaded, answer exactly: NO_SKILL"
            record["trace"] = [{"type": "turn.started"}]
            if index == 0:
                record["trace"].append({"type": "item.completed", "item": {"id": "read", "type": "command_execution",
                    "command": "/usr/bin/zsh -lc 'cat /tmp/probe/.agents/skills/writing/SKILL.md'",
                    "aggregated_output": probe, "exit_code": 0, "status": "completed"}})
            record["trace"] += [{"type": "item.completed", "item": {"id": "final", "type": "agent_message",
                "text": record["response"]}}, {"type": "turn.completed"}]
        artifact.write_text(json.dumps(original))
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        def refresh(value):
            if isinstance(value, dict):
                if value.get("path") == artifact.name:
                    value["sha256"] = digest
                for item in value.values(): refresh(item)
            elif isinstance(value, list):
                for item in value: refresh(item)
        refresh(manifest)
        for index, trigger in enumerate(manifest["triggers"]):
            for key in ("entrypoint", "body_loaded", "response", "negative_response", "tool_action_count"):
                trigger.pop(key)
            for key in ("trace", "probe_skill", "probe_prompt"):
                trigger[key] = {"path": artifact.name, "sha256": digest, "format": "json", "pointer": f"/triggers/{index}/{key}"}
        path.write_text(json.dumps(manifest))
        return path

    def rewrite_retained_artifact(self, path, document):
        artifact = self.private / "retained.json"
        artifact.write_text(json.dumps(document))
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        manifest = json.loads(path.read_text())
        def refresh(value):
            if isinstance(value, dict):
                if value.get("path") == artifact.name:
                    value["sha256"] = digest
                for item in value.values(): refresh(item)
            elif isinstance(value, list):
                for item in value: refresh(item)
        refresh(manifest)
        path.write_text(json.dumps(manifest))

    def test_codex_probe_trace_derives_observation_and_binds_only_target_metadata(self):
        path = self.codex_probe_results()
        document = json.loads((self.private / "retained.json").read_text())
        document["triggers"][0]["trace"].insert(1, {"type": "item.completed", "item": {
            "id": "commentary", "type": "agent_message", "text": "I will read the matching skill."}})
        self.rewrite_retained_artifact(path, document)
        receipt = receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)
        self.assertEqual(receipts.check(self.repo, self.request(), {"example/writing": receipt})["status"], "pass")
        self.assertEqual(receipt["triggers"][0]["reconciliation"]["source_binding"], "name-and-description")
        self.assertTrue(receipt["triggers"][0]["reconciliation"]["body_loaded"])
        self.assertEqual(receipt["triggers"][1]["reconciliation"]["tool_action_count"], 0)

    def test_codex_probe_rejects_printed_text_wrong_body_paths_and_invalid_event_order(self):
        path = self.codex_probe_results()
        original = json.loads((self.private / "retained.json").read_text())
        for change in ("printf", "other-skill", "shell-action", "early-completion", "read-after-answer", "reused-command", "null-item"):
            with self.subTest(change=change):
                document = copy.deepcopy(original)
                trace = document["triggers"][0]["trace"]
                if change == "printf": trace[1]["item"]["command"] = "printf %s probe-text"
                elif change == "other-skill": trace[1]["item"]["command"] = "/usr/bin/zsh -lc 'cat /tmp/probe/.agents/skills/editing/SKILL.md'"
                elif change == "shell-action": trace[1]["item"]["command"] += "; echo hidden"
                elif change == "early-completion": trace.insert(1, trace.pop())
                elif change == "read-after-answer": trace[1], trace[2] = trace[2], trace[1]
                elif change == "reused-command": trace.insert(2, copy.deepcopy(trace[1]))
                else: trace[1]["item"] = None
                self.rewrite_retained_artifact(path, document)
                with self.assertRaises(receipts.ReceiptError):
                    receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)

    def test_codex_probe_keeps_recorded_symbolic_projection_distinct_from_raw_trace(self):
        path = self.codex_probe_results()
        document = json.loads((self.private / "retained.json").read_text())
        record = document["triggers"][0]
        record["trace"][1]["item"]["command"] = "/usr/bin/zsh -lc 'cat <probe-root>/.agents/skills/writing/SKILL.md'"
        self.rewrite_retained_artifact(path, document)
        with self.assertRaisesRegex(receipts.ReceiptError, "projection provenance"):
            receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)
        record["trace_path_normalization"] = "The public projection replaces the recorded temporary root with <probe-root>."
        record["original_transcript_sha256"] = "1" * 64
        self.rewrite_retained_artifact(path, document)
        receipt = receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)
        self.assertEqual(receipt["triggers"][0]["reconciliation"]["trace_projection"],
                         {"kind": "symbolic-paths", "original_trace_sha256": "1" * 64})
        self.assertEqual(receipts.check(self.repo, self.request(), {"example/writing": receipt})["status"], "pass")
        record["original_transcript_sha256"] = "unavailable"
        self.rewrite_retained_artifact(path, document)
        with self.assertRaisesRegex(receipts.ReceiptError, "original trace identity"):
            receipts.reconcile(self.repo, self.candidate, self.spec, path, self.candidate)

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
