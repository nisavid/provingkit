"""Immutable source discovery and affected consumers; no model executions."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts import behavior_eval_inventory as inventory


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Inventory Tests")
        self.git("config", "user.email", "inventory@example.invalid")
        self.write("release/provingkit/definition-v1.json", {
            "membership": {"members": [{"id": "example", "content_identity": {
                "path": "release/plugin-content-locks/example.json"}}]}})
        self.write("release/plugin-content-locks/example.json", {})
        self.write("plugins/example/topology.json", {"skills": {
            "writing": {"calls": []}, "editing": {"calls": []}}})
        for skill in ("writing", "editing"):
            self.write(f"plugins/example/skills/{skill}/SKILL.md", f"Do {skill}.\n")
        self.base = self.commit("base")

    def git(self, *args):
        return subprocess.check_output([
            "git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
            *args], cwd=self.repo, text=True).strip()

    def write(self, path, value):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(value if isinstance(value, str) else json.dumps(value) + "\n")

    def commit(self, message):
        self.git("add", "--all")
        self.git("commit", "-qm", message)
        return self.git("rev-parse", "HEAD")

    def current_corpus(self):
        for name in ("writing", "editing"):
            self.write(f"plugins/example/skills/{name}/SKILL.md",
                       f"---\nname: {name}\ndescription: Use for {name}.\n---\nDo {name}.\n")
        self.write("plugins/example/skills/writing/evals/evals.json", {
            "skill_name": "writing", "evals": [{"id": 0, "prompt": "Write the answer.",
                "fixture_paths": [], "expectations": [
                    {"id": "keep", "text": "Keep the supplied meaning.", "severity": "quality"}]}]})
        self.write("plugins/example/skills/writing/evals/trigger-evals.json", [
            {"query": "Write the answer.", "should_trigger": True},
            {"query": "What time is it?", "should_trigger": False}])
        for path in (inventory.INPUT_MAP, inventory.EXPECTATION_MAP):
            self.write(path, {"schema_version": 1, "entries": []})

    def processing_sources(self):
        source = Path(__file__).resolve().parents[1]
        for path in ("release/behavior-eval-policy.json", "release/behavior-eval-receipt-v1.schema.json",
                     "scripts/behavior_eval_receipts.py", "scripts/behavior_eval_corpora.py",
                     "scripts/behavior_eval_inventory.py"):
            self.write(path, (source / path).read_text())

    def ordinary_corpora_with_phase_two_source(self):
        self.current_corpus()
        self.processing_sources()
        writing = json.loads((self.repo / "plugins/example/skills/writing/evals/evals.json").read_text())
        writing["skill_name"] = "editing"
        self.write("plugins/example/skills/editing/evals/evals.json", writing)
        self.write("plugins/example/skills/editing/evals/trigger-evals.json", [
            {"query": "Edit the note.", "should_trigger": True},
            {"query": "What time is it?", "should_trigger": False}])
        base = self.commit("ordinary corpora")
        self.write("evals/control.json", {"skills": []})
        document = {"semantic_definition": {"path": "evals/control.json", "sha256": hashlib.sha256(
            (self.repo / "evals/control.json").read_bytes()).hexdigest()}, "skills": [
                {"id": "example:" + name, "cold_start": "Select " + name,
                 "explicit": "Use " + name, "supplemental": {"positive": "Try " + name,
                    "positive_expected_skills": [name], "negative": "Use the neighboring skill.",
                    "negative_expected_skills": ["editing" if name == "writing" else "writing"]}}
                for name in ("writing", "editing")]}
        self.write("evals/skill-routing-matrix.json", document)
        return base, document

    def test_phase_two_scope_preserves_records_without_ordinary_denominator_or_selection(self):
        base, document = self.ordinary_corpora_with_phase_two_source()
        document["semantic_definition"]["sha256"] = "0" * 64
        document["skills"].append({"id": "future:unknown", "cold_start": "Future request.", "explicit": "Future skill."})
        self.write("evals/skill-routing-matrix.json", document)
        candidate = self.commit("separate production routing inventory")
        discovered = inventory.discover(self.repo, candidate)
        matrix = discovered["documents"]["evals/skill-routing-matrix.json"]
        self.assertEqual(matrix["raw"], document)
        self.assertEqual(matrix["scope"], "production-release")
        self.assertEqual(len(matrix["records"]), 10)
        for name in ("writing", "editing"):
            described = inventory.descriptor(self.repo, candidate, "example/" + name)
            self.assertEqual(described["status"], "ready", described["diagnostics"])
            self.assertEqual(len(described["cases"]), 1)
            self.assertEqual(len(described["triggers"]), 2)
            self.assertTrue(all("should_trigger" in trigger for trigger in described["triggers"]))
            self.assertTrue(all(row["source"] != "evals/skill-routing-matrix.json"
                                for row in described["descriptor"]["case_selection"]))
        compared = inventory.compare(self.repo, base, candidate)
        self.assertEqual(compared["status"], "complete", compared)
        self.assertEqual(compared["affected_skills"], [])
        self.assertTrue(any(row["code"] == "unknown-owner" and row.get("scope") == "production-release"
                            for row in compared["inventory_diagnostics"]["candidate"]))
        self.assertEqual(inventory.check(self.repo, base, candidate, "release/receipts")["status"], "not-required")

    def test_check_landed_accepts_a_complete_context_with_no_selected_consumers(self):
        self.write("README.md", "An unrelated landing change.\n")
        candidate = self.commit("unrelated landing change")
        context = {
            "contract": "provingkit.receipt-correspondence/v1",
            "original_base": self.base,
            "reviewed_head": self.base,
            "reviewed_target": self.base,
            "operation": "rebase",
            "consumer_revision": self.base,
            "procedure_revision": self.base,
            "receipt_root": "release/receipts",
            "receipts": {},
        }
        landing = {
            "contract": "provingkit.receipt-correspondence/v1",
            "context_sha256": inventory.core.document_digest(context),
            "operation": "rebase",
            "reviewed_head": self.base,
            "target_before": self.base,
            "candidate_revision": candidate,
        }

        result = inventory.check_landed(self.repo, context=context, landing=landing)

        self.assertEqual(result["status"], "not-required")
        self.assertEqual(result["coverage_basis"], "complete-inventory")
        self.assertEqual(result["selection_complete"], True)

    def test_check_landed_does_not_allow_the_reviewed_binding_set_to_narrow_selection(self):
        self.write("plugins/example/skills/writing/SKILL.md", "A changed writing skill.\n")
        reviewed = self.commit("reviewed skill change")
        self.write("README.md", "An unrelated landing change.\n")
        candidate = self.commit("land reviewed change")
        context = {
            "contract": "provingkit.receipt-correspondence/v1",
            "original_base": self.base,
            "reviewed_head": reviewed,
            "reviewed_target": self.base,
            "operation": "rebase",
            "consumer_revision": self.base,
            "procedure_revision": self.base,
            "receipt_root": "release/receipts",
            "receipts": {},
        }
        landing = {
            "contract": "provingkit.receipt-correspondence/v1",
            "context_sha256": inventory.core.document_digest(context),
            "operation": "rebase",
            "reviewed_head": reviewed,
            "target_before": self.base,
            "candidate_revision": candidate,
        }

        result = inventory.check_landed(self.repo, context=context, landing=landing)

        self.assertEqual(result["status"], "fail")
        self.assertFalse(result["selection_complete"])
        self.assertEqual(result["reason_code"], "selection-mismatch")

    def test_reviewed_consumer_adoption_requires_its_phase_two_coordinate_without_changing_neighbors(self):
        _, document = self.ordinary_corpora_with_phase_two_source()
        base = self.commit("retained separate routing scope")
        path = "evals/skill-routing-matrix.json"
        semantic = {"source": {"path": path, "sha256": hashlib.sha256((self.repo / path).read_bytes()).hexdigest()},
            "pointer": "/skills/0/cold_start", "owners": ["example/writing"], "role": "current-corpus",
            "behavior_inputs": [], "dependencies": []}
        entry = {**semantic, "status": "accepted", "review": {"decision": "accepted", "reference": "constructed-scope-adoption",
            "mapping_sha256": inventory.core.document_digest(semantic)}}
        self.write(inventory.INPUT_MAP, {"schema_version": 1, "entries": [entry]})
        adopted = self.commit("explicit ordinary consumer requirement")
        writer = inventory.descriptor(self.repo, adopted, "example/writing")
        editor = inventory.descriptor(self.repo, adopted, "example/editing")
        self.assertEqual(writer["status"], "ready", writer["diagnostics"])
        self.assertEqual(len(writer["triggers"]), 3)
        self.assertEqual(len(editor["triggers"]), 2)
        self.assertIn({"source": path, "pointer": "/skills/0/cold_start"}, writer["descriptor"]["case_selection"])
        self.assertEqual(inventory.compare(self.repo, base, adopted)["affected_skills"], ["example/writing"])
        with self.assertRaisesRegex(inventory.core.ReceiptError, "trigger coverage"):
            self.prepared_receipt(adopted)
        self.write(inventory.INPUT_MAP, {"schema_version": 1, "entries": []})
        removed = self.commit("remove explicit ordinary requirement")
        self.assertEqual(inventory.compare(self.repo, adopted, removed)["affected_skills"], ["example/writing"])
        self.assertEqual(len(inventory.descriptor(self.repo, removed, "example/writing")["triggers"]), 2)

    def test_production_scope_precedes_scenario_ownership_and_runtime_effects(self):
        self.ordinary_corpora_with_phase_two_source()
        source = "plugins/example/skills/editing/evals/evals.json"
        case = json.loads((self.repo / source).read_text())
        case["evals"][0]["name"] = "editor-case"
        self.write(source, case)
        base = self.commit("ordinary corpora and separate routing source")
        path = "evals/skill-routing-matrix.json"
        self.write(path, {"skills": [{"id": "example:writing", "companions": ["example:missing"],
            "scenario": {"kind": "skill-evals", "source": source, "selector": "editor-case", "id": 0}}],
            "runtime_dependencies": {"example:writing": ["support/missing-runtime.md"]}})
        candidate = self.commit("separate production scenario source")
        observed = inventory.discover(self.repo, candidate)
        writer = observed["skills"]["example/writing"]
        self.assertNotIn(path, writer["behavior_inputs"])
        self.assertNotIn(source, writer["behavior_inputs"])
        self.assertFalse(writer["diagnostics"])
        described = inventory.descriptor(self.repo, candidate, "example/writing")
        self.assertEqual(described["status"], "ready", described["diagnostics"])
        self.assertEqual(len(described["cases"]), 1)
        self.assertEqual(observed["documents"][path]["scope"], "production-release")
        self.assertEqual(len(observed["documents"][path]["records"]), 1)
        compared = inventory.compare(self.repo, base, candidate)
        self.assertEqual(compared["status"], "complete", compared)
        self.assertEqual(compared["affected_skills"], [])
        retained = [row for row in compared["inventory_diagnostics"]["candidate"]
                    if row["code"] in ("runtime-input-missing", "companion-unresolved")]
        self.assertEqual(len(retained), 2)
        self.assertTrue(all(row["scope"] == "production-release" and row["ordinary_owners"] == [] for row in retained))

    def test_production_expectation_mappings_do_not_select_ordinary_consumers(self):
        self.ordinary_corpora_with_phase_two_source()
        path = "evals/skill-routing-matrix.json"
        self.write(path, {"skill_name": "example:writing", "evals": [
            {"id": "release", "prompt": "Release case.", "expectations": ["Release expectation."]}]})
        base = self.commit("separate production application source")
        entry = {"source": {"path": path, "sha256": hashlib.sha256((self.repo / path).read_bytes()).hexdigest()},
            "pointer": "/evals/0/expectations/0", "original": "Release expectation.",
            "id": "release-check", "severity": "safety", "status": "accepted"}
        entry["review"] = {"decision": "accepted", "reference": "constructed-release-expectation",
            "mapping_sha256": inventory.corpora.mapping_digest(entry)}
        self.write(inventory.EXPECTATION_MAP, {"schema_version": 1, "entries": [entry]})
        candidate = self.commit("review production expectation")
        described = inventory.descriptor(self.repo, candidate, "example/writing")
        self.assertEqual(described["status"], "ready", described["diagnostics"])
        self.assertEqual(len(described["cases"]), 1)
        compared = inventory.compare(self.repo, base, candidate)
        self.assertEqual(compared["affected_skills"], [])
        self.assertEqual(compared["status"], "complete", compared)

    def test_malformed_source_links_are_diagnostics_in_their_declared_scope(self):
        self.ordinary_corpora_with_phase_two_source()
        scenario = {"skills": [{"id": "example:writing", "companions": [], "scenario": {
            "kind": "skill-evals", "source": "plugins/example/skills/writing/evals/evals.json", "selector": 0}}],
            "runtime_dependencies": {}}
        routing = {"semantic_definition": {"path": "evals/control.json"}, "skills": [
            {"id": "example:writing", "cold_start": "Write.", "explicit": "$writing"}]}
        malformed = []
        for value in ({}, {"path": []}, {"path": None}, {"path": 3}, {"path": ""}):
            malformed.append({**routing, "semantic_definition": value})
        for value in ([], None, 3, "runtime", {"example:writing": None},
                      {"example:writing": 3}, {"example:writing": [3]}, {"example:writing": [""]}):
            malformed.append({**scenario, "runtime_dependencies": value})
        for field, value in (("id", 3), ("id", None), ("id", ""), ("companions", None),
                             ("companions", 3), ("companions", [3]), ("companions", [""])):
            malformed.append({**scenario, "skills": [{**scenario["skills"][0], field: value}]})
        for field, value in (("source", []), ("source", None), ("kind", []), ("kind", None)):
            malformed.append({**scenario, "skills": [{**scenario["skills"][0], "scenario": {
                **scenario["skills"][0]["scenario"], field: value}}]})
        base = self.commit("ordinary source and separate routing")
        for path, expected in (("evals/ordinary-malformed.json", "unsupported"),
                               ("evals/skill-routing-matrix.json", "complete")):
            for index, document in enumerate(malformed):
                with self.subTest(path=path, shape=index):
                    self.write(path, document)
                    candidate = self.commit("malformed source declaration")
                    compared = inventory.compare(self.repo, base, candidate)
                    self.assertEqual(compared["status"], expected, compared)
                    observed = inventory.discover(self.repo, candidate)["documents"][path]
                    self.assertEqual(observed["raw"], document)
                    self.assertIn("malformed-source", [row["code"] for row in observed["diagnostics"]])
                    if expected == "complete":
                        self.assertEqual(compared["affected_skills"], [])
                        self.assertTrue(all(row["scope"] == "production-release" for row in observed["diagnostics"]))
                        described = inventory.descriptor(self.repo, candidate, "example/writing")
                        self.assertEqual(described["status"], "ready", described["diagnostics"])
            (self.repo / path).unlink()
            self.commit("remove malformed source")

    def test_prepare_freezes_the_authoritative_normalized_descriptor(self):
        self.current_corpus()
        self.processing_sources()
        revision = self.commit("prepared source")
        snapshot = inventory.prepare(self.repo, revision, "example/writing")
        self.assertEqual(snapshot["candidate_revision"], revision)
        self.assertEqual(snapshot["skill"], inventory.descriptor(self.repo, revision, "example/writing")["descriptor"])
        self.assertIn(inventory.INPUT_MAP, snapshot["inputs"])
        self.assertIn(inventory.EXPECTATION_MAP, snapshot["inputs"])
        self.assertIn('"id":0', next(iter(inventory.core.corpus(self.repo, snapshot)[0])))

    def test_nonregular_phase_two_source_keeps_its_separate_scope(self):
        base, _ = self.ordinary_corpora_with_phase_two_source()
        path = "evals/skill-routing-matrix.json"
        (self.repo / path).unlink()
        (self.repo / path).symlink_to("control.json")
        candidate = self.commit("nonregular separate routing source")
        observed = inventory.discover(self.repo, candidate)
        self.assertEqual(observed["documents"][path]["scope"], "production-release")
        compared = inventory.compare(self.repo, base, candidate)
        self.assertEqual(compared["status"], "complete", compared)
        self.assertEqual(compared["affected_skills"], [])
        self.assertTrue(any(row["code"] == "corpus-unavailable" and row["scope"] == "production-release"
                            for row in compared["inventory_diagnostics"]["candidate"]))
        self.assertEqual(inventory.check(self.repo, base, candidate, "release/receipts")["status"], "not-required")

    def test_adopted_consumer_inherits_document_and_original_owner_references(self):
        _, document = self.ordinary_corpora_with_phase_two_source()
        path = "evals/skill-routing-matrix.json"
        document["skills"] = [document["skills"][1]]
        document["semantic_definition"]["path"] = "evals/missing-semantic.json"
        document["existing_trigger_sources"] = [
            {"path": "evals/missing-editing.json", "skill": "example:editing"},
            {"path": "evals/unrelated-writing.json", "skill": "example:writing"}]
        self.write(path, document)
        semantic = {"source": {"path": path, "sha256": hashlib.sha256((self.repo / path).read_bytes()).hexdigest()},
            "pointer": "/skills/0/cold_start", "owners": ["example/writing"], "role": "current-corpus",
            "behavior_inputs": [], "dependencies": []}
        self.write(inventory.INPUT_MAP, {"schema_version": 1, "entries": [{**semantic, "status": "accepted",
            "review": {"decision": "accepted", "reference": "constructed-adoption",
                "mapping_sha256": inventory.core.document_digest(semantic)}}]})
        candidate = self.commit("cross-consumer routing adoption")
        described = inventory.descriptor(self.repo, candidate, "example/writing")
        self.assertEqual(described["status"], "unresolved", described)
        observed = inventory.discover(self.repo, candidate)["skills"]["example/writing"]
        unavailable = {row["path"] for row in observed["diagnostics"] if row["code"] == "input-unavailable"}
        self.assertEqual(unavailable, {"evals/missing-semantic.json", "evals/missing-editing.json"})
        self.assertNotIn("evals/unrelated-writing.json", observed["behavior_inputs"])
        self.assertEqual(inventory.descriptor(self.repo, candidate, "example/editing")["status"], "ready")

    def test_current_corpus_mapping_must_select_an_original_case_coordinate(self):
        self.ordinary_corpora_with_phase_two_source()
        path = "evals/skill-routing-matrix.json"
        semantic = {"source": {"path": path, "sha256": hashlib.sha256((self.repo / path).read_bytes()).hexdigest()},
            "pointer": "/skills/0", "owners": ["example/writing"], "role": "current-corpus",
            "behavior_inputs": [], "dependencies": []}
        self.write(inventory.INPUT_MAP, {"schema_version": 1, "entries": [{**semantic, "status": "accepted",
            "review": {"decision": "accepted", "reference": "constructed-adoption",
                "mapping_sha256": inventory.core.document_digest(semantic)}}]})
        candidate = self.commit("unmatched ordinary requirement")
        described = inventory.descriptor(self.repo, candidate, "example/writing")
        self.assertEqual(described["status"], "unresolved", described)
        self.assertTrue(any(row["code"] == "corpus-coordinate-unresolved" and row["pointer"] == "/skills/0"
                            for row in described["diagnostics"]))
        self.assertEqual(inventory.descriptor(self.repo, candidate, "example/editing")["status"], "ready")

    def test_compact_comparison_preserves_consumer_diagnostics_by_side(self):
        self.current_corpus()
        base = self.commit("ordinary inputs")
        self.write("plugins/example/skills/writing/SKILL.md", "Read [required](missing.md).\n")
        candidate = self.commit("missing declared behavior input")
        compared = inventory.compare(self.repo, base, candidate)
        expected = [{**row, "skill": "example/writing"} for row in
                    inventory.discover(self.repo, candidate)["skills"]["example/writing"]["diagnostics"]]
        self.assertTrue(expected)
        self.assertEqual(compared["affected_skills"], ["example/writing"])
        self.assertEqual(compared["inventory_diagnostics"]["candidate"], expected)
        self.assertEqual(compared["inventory_diagnostics"]["base"], [])
        checked = inventory.check(self.repo, base, candidate, "release/receipts")
        self.assertEqual(checked["status"], "fail")
        self.assertEqual(checked["inventory_diagnostics"], compared["inventory_diagnostics"])

    def prepared_receipt(self, revision):
        snapshot = inventory.prepare(self.repo, revision, "example/writing")
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        private = Path(temporary.name)
        coordinate = {"source": "plugins/example/skills/writing/evals/evals.json", "pointer": "/evals/0", "id": 0}
        snapshot_hash = inventory.core.document_digest(snapshot)
        runs = []
        for repetition in (1, 2, 3):
            output = json.dumps({"snapshot_sha256": snapshot_hash, "case_id": coordinate,
                "repetition": repetition, "model_id": "test-executor", "response": "Constructed answer."}).encode()
            (private / f"output-{repetition}.json").write_bytes(output)
            (private / f"grade-{repetition}.json").write_text(json.dumps({
                "snapshot_sha256": snapshot_hash, "case_id": coordinate, "repetition": repetition,
                "model_id": "test-grader", "executor_output_sha256": hashlib.sha256(output).hexdigest(),
                "expectations": [{"id": "keep", "passed": repetition != 3}]}))
            runs.append({"case_id": coordinate, "repetition": repetition,
                         "executor_output": f"output-{repetition}.json", "grading": f"grade-{repetition}.json"})
        triggers = []
        for index, triggered in enumerate((True, False)):
            trigger = {"source": "plugins/example/skills/writing/evals/trigger-evals.json", "pointer": f"/{index}", "id": None}
            (private / f"trigger-{index}.json").write_text(json.dumps({
                "snapshot_sha256": snapshot_hash, "case_id": trigger, "model_id": "test-executor",
                "observation_kind": "recorded-invocation", "triggered": triggered}))
            triggers.append({"case_id": trigger, "observation": f"trigger-{index}.json"})
        results = private / "results.json"
        results.write_text(json.dumps({"schema_version": 1, "snapshot_sha256": snapshot_hash,
            "executor_model_id": "test-executor", "grader_model_id": "test-grader", "runs": runs, "triggers": triggers}))
        return inventory.core.produce(self.repo, snapshot, results)

    def test_committed_check_reads_containing_commit_bytes_and_reports_both_receipt_identities(self):
        self.current_corpus()
        self.processing_sources()
        base = self.commit("initial corpus")
        self.write("plugins/example/skills/writing/SKILL.md", "Write accurately.\n")
        source = self.commit("evaluated behavior")
        receipt = self.prepared_receipt(source)
        path = "release/receipts/example/writing.json"
        raw = json.dumps(receipt, indent=4) + "\n"
        self.write(path, raw)
        containing = self.commit("receipt containing commit")
        self.write(path, "Uncommitted invalid replacement.")
        result = inventory.check(self.repo, base, containing, "release/receipts")
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(result["affected_skills"], ["example/writing"])
        row = result["skills"][0]
        self.assertEqual(row["evaluated_revision"], source)
        self.assertEqual(row["receipt_raw_sha256"], hashlib.sha256(raw.encode()).hexdigest())
        self.assertEqual(row["receipt_sha256"], inventory.core.document_digest(receipt))
        self.assertEqual(row["receipt_source"]["path"], path)
        missing = inventory.check(self.repo, base, source, "release/receipts")
        self.assertEqual(missing["status"], "fail")
        self.assertIn("committed regular input is unavailable", missing["skills"][0]["reason"])

    def test_reconcile_uses_all_authoritative_coordinates_and_preserves_original_records(self):
        self.current_corpus()
        self.processing_sources()
        source = self.commit("retained source")
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        private = Path(temporary.name)
        corpus_path = "plugins/example/skills/writing/evals/evals.json"
        trigger_path = "plugins/example/skills/writing/evals/trigger-evals.json"
        runtime = "plugins/example/skills/writing/SKILL.md"
        case = json.loads((self.repo / corpus_path).read_text())["evals"][0]
        queries = json.loads((self.repo / trigger_path).read_text())
        original = {"runs": [{"revision": source, "corpus": hashlib.sha256((self.repo / corpus_path).read_bytes()).hexdigest(),
            "native_agent": f"constructed-execution-{repetition}", "case_id": 0, "repetition": repetition,
            "prompt": case["prompt"], "runtime": (self.repo / runtime).read_text(), "response": "Original answer.",
            "executor": "test-executor", "grader": "test-grader", "rubric": case["expectations"],
            "grades": [{"id": "keep", "passed": repetition != 3}]} for repetition in (1, 2, 3)],
            "triggers": [{"query": row["query"], "triggered": row["should_trigger"],
                "entrypoint": (self.repo / runtime).read_text(), "model": "test-executor"} for row in queries]}
        raw = json.dumps(original).encode()
        (private / "original.json").write_bytes(raw)
        def reference(pointer):
            return {"path": "original.json", "sha256": hashlib.sha256(raw).hexdigest(), "format": "json", "pointer": pointer}
        runs = []
        for index in range(3):
            prefix = f"/runs/{index}"
            runs.append({"case_id": {"source": corpus_path, "pointer": "/evals/0", "id": 0}, "repetition": index+1,
                "execution_record": reference(prefix), "original_revision": reference(prefix+"/revision"),
                "original_corpus_sha256": reference(prefix+"/corpus"), "prompt": reference(prefix+"/prompt"),
                "response": reference(prefix+"/response"), "grading_record": reference(prefix+"/grades"),
                "original_expectations": reference(prefix+"/rubric"), "grades": reference(prefix+"/grades"),
                "inputs": {runtime: {"representation": "utf8", "value": reference(prefix+"/runtime")}},
                "executor_model": {"basis": "configured", "value": reference(prefix+"/executor")},
                "grader_model": {"basis": "configured", "value": reference(prefix+"/grader")},
                "graded_response": {"representation": "utf8", "value": reference(prefix+"/response")},
                "rubric": {"representation": "expectations", "value": reference(prefix+"/rubric")},
                "previous_grading": [], "adjudication": None})
        triggers = [{"case_id": {"source": trigger_path, "pointer": f"/{index}", "id": None},
            "observation_kind": "recorded-invocation", "record": reference(f"/triggers/{index}"),
            "model": {"basis": "configured", "value": reference(f"/triggers/{index}/model")},
            "query": reference(f"/triggers/{index}/query"), "triggered": reference(f"/triggers/{index}/triggered"),
            "entrypoint": {"representation": "utf8", "value": reference(f"/triggers/{index}/entrypoint")},
            "limits": ["Constructed local records."]} for index in range(2)]
        results = private / "results.json"
        results.write_text(json.dumps({"schema_version": 1, "method": "reconciled-after-run",
            "executor_model_id": "test-executor", "grader_model_id": "test-grader", "runtime_inputs": [runtime],
            "runtime_inputs_complete": True, "runs": runs, "triggers": triggers}))
        receipt = inventory.reconcile(self.repo, source, "example/writing", results, source)
        self.assertEqual(receipt["method"], "reconciled-after-run")
        self.assertEqual(receipt["runs"][0]["case_id"]["id"], 0)
        self.assertIsNone(receipt["triggers"][0]["case_id"]["id"])
        self.assertEqual(receipt["runs"][2]["expectations"], [{"id": "keep", "severity": "quality", "passed": False}])
        self.assertEqual((private / "original.json").read_bytes(), raw)

    def test_new_mapping_to_unknown_consumer_fails_even_when_corpus_bytes_are_unchanged(self):
        self.write("evals/example/shared.json", {"cases": [{"id": "shared"}]})
        self.write("evals/example/shared.md", "Shared input.\n")
        base = self.commit("unowned original input")
        self.write(inventory.INPUT_MAP, {"schema_version": 1,
            "entries": [self.accepted_input(["example/missing"])]})
        candidate = self.commit("unknown proposed consumer accepted")
        result = inventory.check(self.repo, base, candidate, "release/receipts")
        self.assertEqual(result["status"], "fail")
        self.assertFalse(result["selection_complete"])
        self.assertIn("unknown-owner", [row["code"] for row in result["unsupported"]])

    def test_cli_exposes_authoritative_descriptor_preparation_and_committed_check(self):
        self.current_corpus()
        self.processing_sources()
        revision = self.commit("CLI source")
        script = Path(inventory.__file__)
        def invoke(*args):
            return subprocess.run([sys.executable, str(script), "--repository", str(self.repo), *args],
                                  capture_output=True, text=True)
        described = invoke("descriptor", "--revision", revision, "--skill", "example/writing")
        self.assertEqual(described.returncode, 0, described.stderr)
        self.assertEqual(json.loads(described.stdout)["status"], "ready")
        prepared = invoke("prepare", "--revision", revision, "--skill", "example/writing")
        self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
        self.assertEqual(json.loads(prepared.stdout)["skill"]["corpus_format"], "provingkit-v1")
        checked = invoke("check", "--base", revision, "--candidate", revision, "--receipt-root", "release/receipts")
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        self.assertEqual(json.loads(checked.stdout)["status"], "not-required")
        invalid = invoke("check", "--base", revision, "--candidate", revision, "--receipt-root", "release/../receipts")
        self.assertEqual(invalid.returncode, 2)
        self.assertIn("normalized repository-relative path", json.loads(invalid.stdout)["message"])

    def test_map_metadata_and_proposals_remain_noop_even_when_declared_as_an_input(self):
        self.current_corpus()
        self.write("evals/example/shared.json", {"scenarios": [{"id": "shared", "prompt": "Write.",
            "expectations": [{"id": "keep", "text": "Keep.", "severity": "quality"}]}]})
        entry = self.accepted_input(["example/writing"])
        entry["pointer"] = "/scenarios/0"
        entry["behavior_inputs"] = [inventory.INPUT_MAP]
        entry["review"]["mapping_sha256"] = inventory.core.document_digest({
            key: entry[key] for key in inventory.INPUT_MAPPING_FIELDS})
        self.write(inventory.INPUT_MAP, {"schema_version": 1, "entries": [entry]})
        base = self.commit("operative owner decision")
        entry["rationale"] = "Only the explanation changed."
        proposal = {**entry, "owners": ["example/editing"], "status": "proposed"}
        self.write(inventory.INPUT_MAP, {"schema_version": 1, "entries": [entry, proposal]})
        candidate = self.commit("metadata and unaccepted proposal")
        result = inventory.check(self.repo, base, candidate, "release/receipts")
        self.assertEqual(result["status"], "not-required", result)
        self.assertEqual(result["affected_skills"], [])

    def test_catalog_rejects_duplicate_names_and_incomplete_rosters(self):
        self.current_corpus()
        self.write("release/provingkit/definition-v1.json", {"membership": {"members": [
            {"id": plugin, "content_identity": {"path": "release/plugin-content-locks/example.json"}}
            for plugin in ("example", "second")]}})
        self.write("plugins/second/topology.json", {"skills": {"writing": {}}})
        self.write("plugins/second/skills/writing/SKILL.md", "---\nname: writing\ndescription: Another writer.\n---\nWrite.\n")
        duplicate = self.commit("ambiguous unqualified name")
        with self.assertRaisesRegex(inventory.InventoryError, "duplicate unqualified"):
            inventory.canonical_catalog(self.repo, duplicate)
        self.git("rm", "plugins/second/skills/writing/SKILL.md")
        incomplete = self.commit("missing declared entrypoint")
        with self.assertRaisesRegex(inventory.InventoryError, "complete committed roster"):
            inventory.canonical_catalog(self.repo, incomplete)

    def test_committed_check_rejects_a_receipt_symlink(self):
        self.current_corpus()
        base = self.commit("source")
        self.write("plugins/example/skills/writing/SKILL.md", "Changed behavior.\n")
        target = self.repo / "release/receipts/example/writing.json"
        target.parent.mkdir(parents=True)
        target.symlink_to("elsewhere.json")
        candidate = self.commit("nonregular receipt")
        result = inventory.check(self.repo, base, candidate, "release/receipts")
        self.assertEqual(result["status"], "fail")
        self.assertIn("committed regular input is unavailable", result["skills"][0]["reason"])

    def test_descriptor_does_not_report_ready_for_application_without_a_prompt(self):
        self.current_corpus()
        path = "plugins/example/skills/writing/evals/evals.json"
        corpus = json.loads((self.repo / path).read_text())
        del corpus["evals"][0]["prompt"]
        self.write(path, corpus)
        revision = self.commit("missing application prompt")
        result = inventory.descriptor(self.repo, revision, "example/writing")
        self.assertEqual(result["status"], "unresolved")
        self.assertIsNone(result["descriptor"])
        self.assertIn("unsupported-selected-corpus", [row["code"] for row in result["diagnostics"]])

    def test_malformed_scalar_source_cli_returns_json_diagnostics_before_preparation(self):
        self.current_corpus()
        path = self.repo / "plugins/example/skills/writing/evals/evals.json"
        original = path.read_bytes().rstrip()
        for value in (b'"\\ud800"', b'1e309'):
            with self.subTest(value=value):
                path.write_bytes(original[:-1] + b',"retained_metadata":' + value + b'}\n')
                revision = self.commit("malformed scalar source")
                for command, expected_code in (("normalize", 1), ("descriptor", 1), ("prepare", 2)):
                    with self.subTest(command=command):
                        completed = subprocess.run([sys.executable, str(Path(inventory.__file__)),
                            "--repository", str(self.repo), command, "--revision", revision,
                            "--skill", "example/writing"], capture_output=True, text=True)
                        self.assertEqual(completed.returncode, expected_code, completed.stdout + completed.stderr)
                        result = json.loads(completed.stdout)
                        self.assertIn("invalid-json", json.dumps(result))
                        self.assertNotIn("Traceback", completed.stderr)

    def test_missing_routing_values_cannot_disappear_behind_valid_direct_triggers(self):
        self.current_corpus()
        self.write("evals/control.json", {"skills": []})
        control_hash = hashlib.sha256((self.repo / "evals/control.json").read_bytes()).hexdigest()
        for missing in ("explicit", "positive_expected_skills", "negative_expected_skills"):
            with self.subTest(missing=missing):
                row = {"id": "example:writing", "cold_start": "Write.", "explicit": "$writing",
                    "supplemental": {"positive": "Write more.", "positive_expected_skills": ["writing"],
                                     "negative": "Edit.", "negative_expected_skills": ["editing"]}}
                del (row if missing == "explicit" else row["supplemental"])[missing]
                self.write("evals/routing.json", {"semantic_definition": {"path": "evals/control.json", "sha256": control_hash},
                                                 "skills": [row]})
                revision = self.commit("incomplete routing source")
                result = inventory.descriptor(self.repo, revision, "example/writing")
                self.assertEqual(result["status"], "unresolved", result)
                self.assertIsNone(result["descriptor"])
                self.assertIn("invalid-trigger", [item["code"] for item in result["diagnostics"]])

    def test_invalid_routing_container_or_owner_cannot_remove_required_matrix_coverage(self):
        self.current_corpus()
        self.write("evals/control.json", {"skills": []})
        control_hash = hashlib.sha256((self.repo / "evals/control.json").read_bytes()).hexdigest()
        for change in ({"supplemental": False}, {"id": None}, {"id": "example: "}):
            with self.subTest(change=change):
                row = {"id": "example:writing", "cold_start": "Write.", "explicit": "$writing", **change}
                self.write("evals/routing.json", {"semantic_definition": {"path": "evals/control.json", "sha256": control_hash},
                                                 "skills": [row]})
                revision = self.commit("invalid routing container or owner")
                result = inventory.descriptor(self.repo, revision, "example/writing")
                self.assertEqual(result["status"], "unresolved")
                self.assertIsNone(result["descriptor"])

    def test_descriptor_preserves_every_owned_case_and_external_fixture(self):
        self.current_corpus()
        self.write("evals/example/shared.json", {"scenarios": [{"id": "shared", "skill": "writing",
            "prompt": "Edit this.", "fixture_path": "fixtures/input.md", "expectations": [
                {"id": "keep", "text": "Keep the supplied meaning.", "severity": "quality"}]}]})
        self.write("evals/example/fixtures/input.md", "Original fixture.\n")
        revision = self.commit("complete current corpus")
        result = inventory.descriptor(self.repo, revision, "example/writing")
        self.assertEqual(result["status"], "ready", result["diagnostics"])
        spec = result["descriptor"]
        self.assertEqual(spec["corpus_format"], "provingkit-v1")
        self.assertEqual({(r["source"], r["pointer"]) for r in spec["case_selection"]}, {
            ("plugins/example/skills/writing/evals/evals.json", "/evals/0"),
            ("evals/example/shared.json", "/scenarios/0"),
            ("plugins/example/skills/writing/evals/trigger-evals.json", "/0"),
            ("plugins/example/skills/writing/evals/trigger-evals.json", "/1")})
        self.assertEqual([c["case_id"]["id"] for c in result["cases"]], ["shared", 0])
        self.assertIn("evals/example/fixtures/input.md", spec["behavior_inputs"])
        self.assertEqual(spec["expectation_map"], inventory.EXPECTATION_MAP)
        self.assertTrue({inventory.INPUT_MAP, inventory.EXPECTATION_MAP} <= set(spec["dependencies"]))
        self.assertTrue({inventory.INPUT_MAP, inventory.EXPECTATION_MAP}.isdisjoint(spec["behavior_inputs"]))

    def test_routing_descriptor_binds_full_catalog_without_selecting_unrelated_entrypoints(self):
        self.current_corpus()
        self.write("evals/control.json", {"skills": []})
        self.write("evals/routing.json", {"semantic_definition": {"path": "evals/control.json", "sha256":
            hashlib.sha256((self.repo / "evals/control.json").read_bytes()).hexdigest()}, "skills": [{"id": "example:writing",
            "cold_start": "Write.", "explicit": "$writing", "supplemental": {
                "positive": "Write more.", "positive_expected_skills": ["writing", "editing"],
                "negative": "Edit.", "negative_expected_skills": ["editing"]}}]})
        base = self.commit("routing corpus")
        catalog = inventory.canonical_catalog(self.repo, base)
        self.assertEqual(catalog["members"][0], {
            "skill": "example/editing", "name": "editing", "description": "Use for editing.",
            "entrypoint": {"path": "plugins/example/skills/editing/SKILL.md", "sha256":
                hashlib.sha256((self.repo / "plugins/example/skills/editing/SKILL.md").read_bytes()).hexdigest()}})
        result = inventory.descriptor(self.repo, base, "example/writing")
        self.assertEqual(result["status"], "ready", result["diagnostics"])
        self.assertEqual(len(result["triggers"]), 6)
        positive = next(r for r in result["triggers"] if r["case_id"]["pointer"] == "/skills/0/supplemental/positive")
        self.assertEqual(positive["expected_selection"], ["writing", "editing"])
        self.assertTrue(set(catalog["source_identities"]) <= set(result["descriptor"]["dependencies"]))
        self.write("plugins/example/skills/editing/SKILL.md", "---\nname: editing\ndescription: Edit carefully.\n---\nEdit.\n")
        candidate = self.commit("unrelated catalog member changes")
        self.assertEqual(inventory.compare(self.repo, base, candidate)["affected_skills"], ["example/editing"])

    def test_roster_is_discovered_from_committed_slate_and_topology(self):
        self.write("plugins/example/skills/local-only/SKILL.md", "Uncommitted.\n")
        observed = inventory.discover(self.repo, self.base)
        self.assertEqual(sorted(observed["skills"]), ["example/editing", "example/writing"])
        self.assertTrue(observed["roster_complete"])
        self.assertEqual(observed["revision"], self.base)

    def test_comparison_selects_owned_source_and_keeps_tools_freshness_only(self):
        self.write("scripts/behavior_eval_receipts.py", "# receipt tool change\n")
        tooling = self.commit("tooling")
        self.assertEqual(inventory.compare(self.repo, self.base, tooling)["affected_skills"], [])
        self.write("plugins/example/skills/writing/SKILL.md", "Write accurately.\n")
        candidate = self.commit("behavior")
        result = inventory.compare(self.repo, self.base, candidate)
        self.assertEqual(result["affected_skills"], ["example/writing"])
        self.assertEqual(result["causes"]["example/writing"][0]["path"],
                         "plugins/example/skills/writing/SKILL.md")

    def accepted_input(self, owners):
        source = "evals/example/shared.json"
        semantic = {
            "source": {"path": source, "sha256": hashlib.sha256(
                (self.repo / source).read_bytes()).hexdigest()},
            "pointer": "/cases/0", "owners": owners, "role": "current-corpus",
            "behavior_inputs": ["evals/example/shared.md"], "dependencies": [],
        }
        return {**semantic, "status": "accepted", "rationale": "Constructed owner decision.",
                "review": {"decision": "accepted", "reference": "https://example.invalid/review/1",
                           "mapping_sha256": hashlib.sha256(json.dumps(
                               semantic, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=False).encode()).hexdigest()}}

    def test_mapping_metadata_is_not_behavior_and_owner_change_selects_both_sides(self):
        self.write("evals/example/shared.json", {"cases": [{"id": "shared"}]})
        self.write("evals/example/shared.md", "A shared fixture.\n")
        entry = self.accepted_input(["example/writing"])
        self.write("release/behavior-eval-input-map.json", {"schema_version": 1, "entries": [entry]})
        base = self.commit("owned input")
        entry["rationale"] = "Same operative decision, clarified explanation."
        self.write("release/behavior-eval-input-map.json", {"schema_version": 1, "entries": [entry]})
        metadata = self.commit("metadata")
        self.assertEqual(inventory.compare(self.repo, base, metadata)["affected_skills"], [])
        self.write("release/behavior-eval-input-map.json", {
            "schema_version": 1, "entries": [self.accepted_input(["example/editing"])]})
        changed = self.commit("changed owner")
        self.assertEqual(inventory.compare(self.repo, base, changed)["affected_skills"],
                         ["example/editing", "example/writing"])
        checked = inventory.check(self.repo, base, changed, "release/receipts")
        self.assertEqual([row["skill"] for row in checked["skills"]], ["example/editing", "example/writing"])

    def test_shared_behavioral_resource_selects_every_declared_consumer(self):
        self.write("plugins/example/references/style.md", "Use plain language.\n")
        for skill in ("writing", "editing"):
            self.write(f"plugins/example/skills/{skill}/SKILL.md",
                       "Read [the style contract](../../references/style.md).\n")
        base = self.commit("shared reference")
        self.write("plugins/example/references/style.md", "State the outcome first.\n")
        candidate = self.commit("changed shared reference")
        result = inventory.compare(self.repo, base, candidate)
        self.assertEqual(result["affected_skills"], ["example/editing", "example/writing"])

    def test_compare_cli_keeps_large_retained_artifacts_in_explicit_discovery(self):
        path = "evals/example/grading.json"
        retained = {"results": [{"response": "Retained response. " * 100000}]}
        self.write(path, retained)
        original = (self.repo / path).read_bytes()
        base = self.commit("large retained result")
        self.write("plugins/example/skills/writing/SKILL.md", "Write accurately.\n")
        candidate = self.commit("writer changes")
        process = subprocess.run([sys.executable, str(Path(inventory.__file__)),
            "--repository", str(self.repo), "compare", "--base", base,
            "--candidate", candidate], capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertLess(len(process.stdout.encode()), 16000)
        compared = json.loads(process.stdout)
        self.assertEqual((compared["base_revision"], compared["candidate_revision"]), (base, candidate))
        self.assertEqual(compared["affected_skills"], ["example/writing"])
        self.assertNotIn("base", compared)
        self.assertNotIn("candidate", compared)
        for side, revision in (("base", base), ("candidate", candidate)):
            self.assertEqual(compared["inventory_summary"][side], {"revision": revision,
                "roster_complete": True, "skill_count": 2, "document_count": 1, "unresolved_record_count": 0})
            self.assertEqual(compared["inventory_diagnostics"][side][0]["code"], "scope-only")
        discovered = inventory.discover(self.repo, candidate)
        self.assertEqual(discovered["documents"][path]["raw"], retained)
        self.assertEqual((self.repo / path).read_bytes(), original)

    def test_comparison_retains_production_scope_diagnostics_without_ordinary_selection(self):
        path = "evals/skill-routing-matrix.json"
        self.write(path, {"semantic_definition": {"path": "evals/missing-control.json", "sha256": "a" * 64},
            "skills": [{"id": "example:retired", "cold_start": "Retired query.", "explicit": "$retired"}]})
        candidate = self.commit("separate production routing source")
        compared = inventory.compare(self.repo, self.base, candidate)
        self.assertEqual(compared["status"], "complete", compared["unsupported"])
        self.assertTrue(compared["selection_complete"])
        self.assertEqual(compared["affected_skills"], [])
        self.assertEqual(compared["unsupported"], [])
        diagnostics = compared["inventory_diagnostics"]["candidate"]
        self.assertEqual({row["code"] for row in diagnostics}, {"scope-only", "reference-missing", "unknown-owner"})
        self.assertTrue(all(row["scope"] == "production-release" for row in diagnostics))
        checked = inventory.check(self.repo, self.base, candidate, "release/receipts")
        self.assertEqual(checked["status"], "not-required")
        self.assertEqual(checked["inventory_diagnostics"], compared["inventory_diagnostics"])
        self.assertEqual(checked["inventory_summary"], compared["inventory_summary"])

    def test_compact_comparison_preserves_selection_and_unresolved_coverage_diagnostics(self):
        self.current_corpus()
        self.write("evals/example/grading.json", {"results": []})
        base = self.commit("current and retained sources")
        self.write("evals/example/unknown.json", {"skill_name": "missing", "evals": [
            {"id": 0, "prompt": "Unknown owner.", "expectations": []}]})
        self.write("evals/unowned.json", {"scenarios": [{"id": "unowned", "expectations": []}]})
        self.write("evals/unsupported.json", {"unknown_format": True})
        entrypoint = "plugins/example/skills/writing/SKILL.md"
        self.write(entrypoint, "Write accurately.\n")
        candidate = self.commit("changed writer and unresolved ordinary sources")
        compared = inventory.compare(self.repo, base, candidate)
        self.assertEqual(compared["status"], "unsupported")
        self.assertFalse(compared["selection_complete"])
        self.assertEqual(compared["affected_skills"], ["example/writing"])
        self.assertEqual(compared["causes"], {"example/writing": [
            {"path": entrypoint, "side": "base", "kind": "behavioral-input"},
            {"path": entrypoint, "side": "candidate", "kind": "behavioral-input"}]})
        self.assertEqual({row["code"] for row in compared["unsupported"]},
                         {"unknown-owner", "unresolved-owner", "unsupported-corpus"})
        self.assertEqual({row["code"] for row in compared["inventory_diagnostics"]["candidate"]},
                         {"scope-only", "unsupported-format", "unknown-owner", "unresolved-owner"})
        self.assertEqual(compared["inventory_summary"]["candidate"]["unresolved_record_count"], 2)
        for side, revision in (("base", base), ("candidate", candidate)):
            observed = inventory.discover(self.repo, revision)
            for row in observed["diagnostics"]:
                self.assertIn(row, compared["inventory_diagnostics"][side])
            for key, skill in observed["skills"].items():
                for row in skill["diagnostics"]:
                    self.assertIn({**row, "skill": key}, compared["inventory_diagnostics"][side])
        process = subprocess.run([sys.executable, str(Path(inventory.__file__)),
            "--repository", str(self.repo), "check", "--base", base, "--candidate", candidate,
            "--receipt-root", "release/receipts"], capture_output=True, text=True)
        self.assertEqual(process.returncode, 1, process.stderr)
        checked = json.loads(process.stdout)
        self.assertEqual(checked["status"], "fail")
        for field in ("base_revision", "candidate_revision", "changed_paths", "affected_skills", "causes",
                      "selection_complete", "unsupported", "inventory_diagnostics", "inventory_summary"):
            self.assertEqual(checked[field], compared[field], field)
        self.assertEqual(checked["skills"][0]["skill"], "example/writing")
        self.assertIn("unresolved-owner", [row["code"] for row in checked["skills"][0]["diagnostics"]])

    def test_external_corpus_fixture_is_selected_without_reading_worktree_bytes(self):
        corpus = "evals/example/skills/writing/evals.json"
        fixture = "evals/example/skills/writing/fixtures/input.md"
        self.write(corpus, {"skill_name": "writing", "evals": [{"id": 0,
            "files": ["writing/fixtures/input.md"], "expectations": ["Keep its meaning."]}]})
        self.write(fixture, "Before.\n")
        base = self.commit("external corpus")
        self.write(fixture, "After.\n")
        candidate = self.commit("changed fixture")
        self.write(corpus, "invalid uncommitted JSON")
        result = inventory.compare(self.repo, base, candidate)
        self.assertEqual(result["affected_skills"], ["example/writing"])
        self.assertIn(fixture, inventory.discover(self.repo, candidate)["skills"]["example/writing"]["behavior_inputs"])

    def test_removed_skill_is_an_explicit_unsupported_consumer(self):
        self.git("rm", "plugins/example/skills/writing/SKILL.md")
        self.write("plugins/example/topology.json", {"skills": {"editing": {"calls": []}}})
        candidate = self.commit("retired skill")
        result = inventory.compare(self.repo, self.base, candidate)
        self.assertIn("example/writing", result["affected_skills"])
        self.assertEqual(result["unsupported"], [{"code": "removed-or-renamed-skill",
                                                 "skill": "example/writing"}])
        self.assertEqual(result["status"], "unsupported")
        checked = inventory.check(self.repo, self.base, candidate, "release/receipts")
        self.assertEqual(checked["status"], "fail")
        self.assertEqual(checked["skills"][0]["diagnostics"][0]["code"], "unknown-skill")

    def test_current_projection_consumers_include_their_canonical_source(self):
        repository = Path(__file__).resolve().parents[1]
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repository, text=True).strip()
        observed = inventory.discover(repository, revision)
        self.assertIn("plugins/mergecraft/skills/writing-github-issue-and-pr-markdown/references/authoring-contract.md",
                      observed["skills"]["mergecraft/writing-reviewable-pr-descriptions"]["shared_references"])
        self.assertIn("plugins/tricritical/references/review-input-boundary.md",
                      observed["skills"]["tricritical/intent"]["shared_references"])
        self.assertIn("plugins/artifact-customs/references/component-policy-contract.md",
                      observed["skills"]["artifact-customs/adopting-third-party-components"]["shared_references"])

    def test_normalization_reports_unclassified_cases_with_original_zero_identity(self):
        path = "evals/example/skills/writing/evals.json"
        self.write(path, {"skill_name": "writing", "evals": [
            {"id": 0, "files": [], "expectations": ["Keep its meaning."]}]})
        self.write("evals/example/skills/writing/trigger-evals.json", [
            {"query": "Write this.", "should_trigger": True}])
        revision = self.commit("unclassified corpus")
        result = inventory.normalize(self.repo, revision, "example/writing")
        self.assertEqual(result["status"], "unresolved")
        self.assertEqual(result["cases"][0]["case_id"],
                         {"source": path, "pointer": "/evals/0", "id": 0})
        self.assertIsNone(result["cases"][0]["expectations"][0]["severity"])
        self.assertEqual(result["triggers"][0]["query"], "Write this.")

    def test_mapping_review_metadata_does_not_select_but_invalidates_selected_coverage(self):
        self.write("evals/example/shared.json", {"scenarios": [{"id": "shared",
            "expectations": [{"id": "keep", "text": "Keep.", "severity": "quality"}]}]})
        self.write("evals/example/shared.md", "Shared fixture.\n")
        entry = self.accepted_input(["example/writing"])
        entry["pointer"] = "/scenarios/0"
        entry["review"]["mapping_sha256"] = inventory.core.document_digest({
            key: entry[key] for key in inventory.INPUT_MAPPING_FIELDS})
        self.write(inventory.INPUT_MAP, {"schema_version": 1, "entries": [entry]})
        base = self.commit("reviewed mapping")
        entry["review"]["mapping_sha256"] = "0" * 64
        self.write(inventory.INPUT_MAP, {"schema_version": 1, "entries": [entry]})
        candidate = self.commit("invalid review metadata")
        result = inventory.compare(self.repo, base, candidate)
        self.assertEqual(result["affected_skills"], [])
        normalized = inventory.normalize(self.repo, candidate, "example/writing")
        self.assertEqual(normalized["status"], "unresolved")
        self.assertIn("invalid-input-mapping", [d["code"] for d in normalized["diagnostics"]])

    def test_accepted_owner_mapping_selects_original_case_and_preserves_fixture_bytes(self):
        self.write("evals/example/shared.json", {"scenarios": [{"id": "shared",
            "fixture_path": "shared.md", "expectations": [
                {"id": "keep", "text": "Keep.", "severity": "quality"}]}]})
        self.write("evals/example/shared.md", "Shared fixture.\n")
        entry = self.accepted_input(["example/writing"])
        entry["pointer"] = "/scenarios/0"
        entry["review"]["mapping_sha256"] = inventory.core.document_digest({
            key: entry[key] for key in inventory.INPUT_MAPPING_FIELDS})
        self.write(inventory.INPUT_MAP, {"schema_version": 1, "entries": [entry]})
        self.write("evals/example/skills/writing/trigger-evals.json", [
            {"query": "Write.", "should_trigger": True}])
        revision = self.commit("reviewed source owner")
        result = inventory.normalize(self.repo, revision, "example/writing")
        self.assertEqual(result["status"], "ready", result["diagnostics"])
        self.assertEqual(result["cases"][0]["case_id"], {
            "source": "evals/example/shared.json", "pointer": "/scenarios/0", "id": "shared"})

    def test_unowned_changed_corpus_is_explicitly_incomplete_and_tools_remain_noop(self):
        self.write("evals/example/shared.json", {"scenarios": [{"id": "unowned"}]})
        base = self.commit("unresolved owner")
        self.write("scripts/behavior_eval_receipts.py", "# tool update\n")
        tooling = self.commit("tool only")
        self.assertTrue(inventory.compare(self.repo, base, tooling)["selection_complete"])
        self.write("evals/example/shared.json", {"scenarios": [{"id": "unowned", "prompt": "Changed."}]})
        candidate = self.commit("unknown consumer")
        result = inventory.compare(self.repo, tooling, candidate)
        self.assertFalse(result["selection_complete"])
        self.assertEqual(result["status"], "unsupported")
        self.assertIn("unresolved-owner", [x["code"] for x in result["unsupported"]])

    def test_topology_consumption_change_selects_only_changed_skill(self):
        self.write("plugins/example/topology.json", {"skills": {
            "writing": {"calls": ["editing"]}, "editing": {"calls": []}}})
        candidate = self.commit("new consumption")
        result = inventory.compare(self.repo, self.base, candidate)
        self.assertEqual(result["affected_skills"], ["example/writing"])

    def test_matrix_reference_resolves_only_selected_original_scenario_owner(self):
        self.write("evals/example/corpus.json", {"scenarios": [
            {"id": "selected", "expectations": ["Keep."]},
            {"id": "unresolved", "expectations": ["Other."]}]})
        self.write("evals/control-plane-matrix.json", {"skills": [{
            "id": "example:writing", "scenario": {"source": "evals/example/corpus.json",
                "kind": "simple-corpus", "selector": "selected", "id": "selected"}}]})
        revision = self.commit("declared scenario consumption")
        result = inventory.discover(self.repo, revision)
        applications = [r for r in result["skills"]["example/writing"]["records"] if r["role"] == "application"]
        self.assertEqual([r["id"] for r in applications], ["selected"])
        self.assertEqual([r["id"] for r in result["unresolved_records"]], ["unresolved"])

    def test_expectation_map_changes_only_its_operative_consumer(self):
        entries = []
        for skill in ("writing", "editing"):
            path = f"evals/example/skills/{skill}/evals.json"
            self.write(path, {"skill_name": skill, "evals": [{"id": 0, "expectations": ["Keep."]}]})
            entry = {"source": {"path": path, "sha256": hashlib.sha256((self.repo / path).read_bytes()).hexdigest()},
                "pointer": "/evals/0/expectations/0", "original": "Keep.", "id": "keep",
                "severity": "quality", "status": "accepted"}
            entry["review"] = {"decision": "accepted", "reference": "test-review",
                "mapping_sha256": inventory.corpora.mapping_digest(entry)}
            entries.append(entry)
        self.write(inventory.EXPECTATION_MAP, {"schema_version": 1, "entries": entries})
        base = self.commit("two reviewed classifications")
        entries[0]["rationale"] = "Clarified only."
        self.write(inventory.EXPECTATION_MAP, {"schema_version": 1, "entries": entries[::-1]})
        metadata = self.commit("reordered metadata")
        self.assertEqual(inventory.compare(self.repo, base, metadata)["affected_skills"], [])
        entries[0]["severity"] = "safety"
        entries[0]["review"]["mapping_sha256"] = inventory.corpora.mapping_digest(entries[0])
        self.write(inventory.EXPECTATION_MAP, {"schema_version": 1, "entries": entries})
        changed = self.commit("changed one classification")
        self.assertEqual(inventory.compare(self.repo, metadata, changed)["affected_skills"], ["example/writing"])

    def test_changed_unsupported_corpus_is_explicit_and_retained_probe_is_not_current(self):
        self.write("evals/example/new-format.json", {"future": [{"id": 0}]})
        self.write("evals/review-publication-handoffs/probe-1.json", [{"case": "historical", "action": "Hold."}])
        candidate = self.commit("unsupported corpus and retained result")
        result = inventory.compare(self.repo, self.base, candidate)
        self.assertFalse(result["selection_complete"])
        self.assertEqual([u["path"] for u in result["unsupported"] if u["code"] == "unsupported-corpus"],
                         ["evals/example/new-format.json"])

    def test_stale_routing_reference_is_reported_without_boolean_projection(self):
        self.write("evals/control.json", {"note": "A definition."})
        self.write("evals/routing.json", {"semantic_definition": {"path": "evals/control.json", "sha256": "0" * 64},
            "skills": [{"id": "example:writing", "cold_start": "Write.", "explicit": "$writing"}]})
        revision = self.commit("stale routing binding")
        result = inventory.discover(self.repo, revision)
        self.assertIn("reference-digest-mismatch", [d["code"] for d in result["skills"]["example/writing"]["diagnostics"]])

    def test_selected_malformed_corpus_cannot_hide_behind_other_supported_cases(self):
        self.write("plugins/example/skills/writing/evals/evals.json", {"skill_name": "writing", "evals": [
            {"id": 0, "expectations": [{"id": "keep", "text": "Keep.", "severity": "quality"}]}]})
        self.write("plugins/example/skills/writing/evals/trigger-evals.json", [
            {"query": "Write.", "should_trigger": True}])
        self.write("evals/example/skills/writing/evals.json", "{malformed")
        revision = self.commit("partial supported coverage")
        result = inventory.normalize(self.repo, revision, "example/writing")
        self.assertEqual(result["status"], "unresolved")
        self.assertIn("invalid-json", [item["code"] for item in result["diagnostics"]])
        self.write("scripts/tool.py", "# Only a tool change.\n")
        candidate = self.commit("unselected malformed source")
        comparison = inventory.compare(self.repo, revision, candidate)
        self.assertEqual(comparison["affected_skills"], [])
        self.assertTrue(comparison["selection_complete"])
        self.assertEqual(inventory.check(self.repo, revision, candidate, "release/receipts")["status"], "not-required")
        self.write("plugins/example/skills/writing/SKILL.md", "Changed writing behavior.\n")
        selected = self.commit("selected malformed consumer")
        checked = inventory.check(self.repo, candidate, selected, "release/receipts")
        self.assertEqual(checked["status"], "fail")
        self.assertIn("invalid-json", [row["code"] for row in checked["skills"][0]["diagnostics"]])

    def test_unknown_declared_owner_is_retained_and_changed_coverage_is_incomplete(self):
        self.write("evals/example/corpus.json", {"scenarios": [
            {"id": "unknown", "skill": "missing", "expectations": ["Keep."]}]})
        candidate = self.commit("unknown declared consumer")
        discovered = inventory.discover(self.repo, candidate)
        self.assertEqual(discovered["unresolved_records"][0]["owners"], ["example/missing"])
        self.assertIn("unknown-owner", [item["code"] for item in discovered["diagnostics"]])
        compared = inventory.compare(self.repo, self.base, candidate)
        self.assertFalse(compared["selection_complete"])
        self.assertIn("unresolved-owner", [item["code"] for item in compared["unsupported"]])

    def test_missing_shared_resource_and_nonregular_fixture_are_explicit_inputs(self):
        self.write("plugins/example/skills/writing/SKILL.md", "Read [style](../../references/missing.md).\n")
        self.write("evals/example/skills/writing/evals.json", {"skill_name": "writing", "evals": [
            {"id": 0, "files": ["writing/fixtures/input.md"], "expectations": ["Keep."]}]})
        fixture = self.repo / "evals/example/skills/writing/fixtures/input.md"
        fixture.parent.mkdir(parents=True)
        fixture.symlink_to("missing.md")
        candidate = self.commit("unavailable inputs")
        result = inventory.discover(self.repo, candidate)["skills"]["example/writing"]
        self.assertIn("plugins/example/references/missing.md", result["behavior_inputs"])
        unavailable = {item["path"] for item in result["diagnostics"] if item["code"] == "input-unavailable"}
        self.assertEqual(unavailable, {"plugins/example/references/missing.md", "evals/example/skills/writing/fixtures/input.md"})
        self.assertIn("plugins/example/skills/writing/SKILL.md", result["source_identities"])
        self.assertEqual(result["source_identities"]["plugins/example/skills/writing/SKILL.md"]["mode"], "100644")
        self.assertEqual(inventory.normalize(self.repo, candidate, "example/writing")["status"], "unresolved")

    def test_canonical_projection_drift_is_reported_for_its_consumer(self):
        self.write("release/provingkit/definition-v1.json", {"membership": {"members": [
            {"id": "artifact-customs", "content_identity": {"path": "release/plugin-content-locks/example.json"}}]}})
        self.write("plugins/artifact-customs/topology.json", {"skills": {"adopting": {}}})
        self.write("plugins/artifact-customs/skills/adopting/SKILL.md", "Adopt.\n")
        self.write("scripts/validate_artifact_customs.py", "SKILL_REFERENCES = {'adopting': ['contract.md']}\n")
        self.write("plugins/artifact-customs/references/contract.md", "Canonical.\n")
        self.write("plugins/artifact-customs/skills/adopting/references/contract.md", "Different.\n")
        revision = self.commit("drifted projection")
        result = inventory.discover(self.repo, revision)["skills"]["artifact-customs/adopting"]
        self.assertIn("projection-bytes-mismatch", [item["code"] for item in result["diagnostics"]])
        self.assertIn("plugins/artifact-customs/references/contract.md", result["source_identities"])

    def test_current_support_is_bound_as_freshness_without_selecting_behavior(self):
        support = "plugins/example/evals/delivery.json"
        self.write(support, {"executor": {"inputs": ["fixture"]}, "grader": {"inputs": ["response"]}})
        base = self.commit("delivery support")
        observed = inventory.discover(self.repo, base)["skills"]["example/writing"]
        self.assertIn(support, observed["dependencies"])
        self.assertIn(support, observed["source_identities"])
        self.assertNotIn(support, observed["behavior_inputs"])
        self.write(support, {"executor": {"inputs": ["fixture", "candidate"]}, "grader": {"inputs": ["response"]}})
        candidate = self.commit("support-only change")
        self.assertEqual(inventory.compare(self.repo, base, candidate)["affected_skills"], [])

    def test_refreshed_support_mapping_hash_and_dependencies_do_not_select_behavior(self):
        self.current_corpus()
        support = "plugins/example/evals/delivery.json"
        self.write(support, {"executor": {"inputs": ["fixture"]}, "grader": {"inputs": ["response"]}})
        self.write("support/runner-v1.txt", "Runner configuration.\n")
        def mapping(dependency):
            semantic = {"source": {"path": support, "sha256": hashlib.sha256((self.repo / support).read_bytes()).hexdigest()},
                "pointer": "", "owners": ["example/writing"], "role": "current-support",
                "behavior_inputs": [], "dependencies": [dependency]}
            return {**semantic, "status": "accepted", "review": {"decision": "accepted", "reference": "test-review",
                "mapping_sha256": inventory.core.document_digest(semantic)}}
        self.write(inventory.INPUT_MAP, {"schema_version": 1, "entries": [mapping("support/runner-v1.txt")]})
        base = self.commit("reviewed support mapping")
        self.write(support, {"executor": {"inputs": ["fixture", "candidate"]}, "grader": {"inputs": ["response"]}})
        self.write("support/runner-v2.txt", "Updated runner configuration.\n")
        self.write(inventory.INPUT_MAP, {"schema_version": 1, "entries": [mapping("support/runner-v2.txt")]})
        candidate = self.commit("support and reviewed binding refresh")
        result = inventory.compare(self.repo, base, candidate)
        self.assertEqual(result["status"], "complete", result["unsupported"])
        self.assertEqual(result["affected_skills"], [])
        selected = inventory.discover(self.repo, candidate)["skills"]["example/writing"]
        self.assertIn(support, selected["dependencies"])
        self.assertIn("support/runner-v2.txt", selected["dependencies"])
        self.assertFalse(selected["diagnostics"])

    def test_mapping_classification_changes_select_actual_old_and_new_corpus_consumers(self):
        self.current_corpus()
        base = self.commit("implicit writing corpus ownership")
        corpus = "plugins/example/skills/writing/evals/evals.json"
        semantic = {"source": {"path": corpus, "sha256": hashlib.sha256((self.repo / corpus).read_bytes()).hexdigest()},
            "pointer": "/evals/0", "owners": ["example/editing"], "role": "reference-only",
            "behavior_inputs": [], "dependencies": []}
        def write_mapping():
            self.write(inventory.INPUT_MAP, {"schema_version": 1, "entries": [{**semantic, "status": "accepted",
                "review": {"decision": "accepted", "reference": "test-review",
                           "mapping_sha256": inventory.core.document_digest(semantic)}}]})
        for role in ("reference-only", "retained-evidence", "current-support"):
            with self.subTest(role=role):
                semantic["role"] = role
                write_mapping()
                suppressed = self.commit("classify existing corpus as " + role)
                result = inventory.compare(self.repo, base, suppressed)
                self.assertEqual(result["affected_skills"], ["example/writing"])
                self.assertFalse(any(row["role"] == "application" for row in
                    inventory.discover(self.repo, suppressed)["skills"]["example/editing"]["records"]))
        semantic["role"] = "current-corpus"
        write_mapping()
        transferred = self.commit("current corpus consumed by editing")
        self.assertEqual(inventory.compare(self.repo, base, transferred)["affected_skills"],
                         ["example/editing", "example/writing"])
        self.assertEqual(inventory.compare(self.repo, suppressed, transferred)["affected_skills"], ["example/editing"])

    def test_support_mappings_preserve_real_behavior_owners_without_source_path_fanout(self):
        self.current_corpus()
        self.write("support/runner-v1.json", {"runner": "first"})
        self.write("behavior/style.md", "Write plainly.\n")
        def mapping(source, owner):
            semantic = {"source": {"path": source, "sha256": hashlib.sha256((self.repo / source).read_bytes()).hexdigest()},
                "pointer": "", "owners": [owner], "role": "current-support",
                "behavior_inputs": ["behavior/style.md"], "dependencies": []}
            self.write(inventory.INPUT_MAP, {"schema_version": 1, "entries": [{**semantic, "status": "accepted",
                "review": {"decision": "accepted", "reference": "test-review",
                           "mapping_sha256": inventory.core.document_digest(semantic)}}]})
        mapping("support/runner-v1.json", "example/writing")
        base = self.commit("behavior resource consumed by writer")
        mapping("support/runner-v1.json", "example/editing")
        transferred = self.commit("behavior resource consumed by editor")
        self.assertEqual(inventory.compare(self.repo, base, transferred)["affected_skills"],
                         ["example/editing", "example/writing"])
        self.write("support/runner-v2.json", {"runner": "second"})
        mapping("support/runner-v2.json", "example/editing")
        refreshed = self.commit("replace support source without changing behavior consumption")
        result = inventory.compare(self.repo, transferred, refreshed)
        self.assertEqual(result["affected_skills"], [])
        self.assertIn("support/runner-v2.json", inventory.discover(self.repo, refreshed)["skills"]["example/editing"]["dependencies"])

    def test_appended_matrix_row_selects_only_its_consumer(self):
        corpus = "evals/example/corpus.json"
        matrix = "evals/control-plane-matrix.json"
        self.write(corpus, {"scenarios": [
            {"id": "write", "skill": "writing", "expectations": ["Write."]},
            {"id": "edit", "skill": "editing", "expectations": ["Edit."]}]})
        rows = [{"id": "example:writing", "entrypoint": "plugins/example/skills/writing/SKILL.md", "companions": [],
                 "scenario": {"kind": "simple-corpus", "source": corpus, "selector": "write", "id": "write"}}]
        self.write(matrix, {"skills": rows, "runtime_dependencies": {}})
        base = self.commit("writer scenario consumption")
        rows.append({"id": "example:editing", "entrypoint": "plugins/example/skills/editing/SKILL.md", "companions": [],
                     "scenario": {"kind": "simple-corpus", "source": corpus, "selector": "edit", "id": "edit"}})
        self.write(matrix, {"skills": rows, "runtime_dependencies": {}})
        candidate = self.commit("append independent editor scenario")
        compared = inventory.compare(self.repo, base, candidate)
        self.assertEqual(compared["affected_skills"], ["example/editing"])
        self.assertEqual(compared["status"], "complete")
        self.assertTrue(compared["selection_complete"])
        for revision in (base, candidate):
            writer = inventory.discover(self.repo, revision)["skills"]["example/writing"]
            self.assertIn(matrix, writer["source_identities"])

    def test_direct_whole_matrix_resource_still_selects_its_consumer(self):
        matrix = "evals/control-plane-matrix.json"
        corpus = "evals/example/corpus.json"
        self.write("plugins/example/skills/writing/SKILL.md",
                   "Read [the full matrix](../../../../evals/control-plane-matrix.json).\n")
        self.write(corpus, {"scenarios": [
            {"id": "writing", "skill": "writing", "expectations": ["Write."]},
            {"id": "editing", "skill": "editing", "expectations": ["Edit."]}]})
        rows = [{"id": "example:" + name, "entrypoint": f"plugins/example/skills/{name}/SKILL.md", "companions": [],
                 "scenario": {"kind": "simple-corpus", "source": corpus, "selector": name, "id": name}}
                for name in ("writing", "editing")]
        self.write(matrix, {"skills": rows[:1]})
        base = self.commit("writer also reads complete matrix")
        self.write(matrix, {"skills": rows})
        candidate = self.commit("append editor to directly consumed matrix")
        self.assertEqual(inventory.compare(self.repo, base, candidate)["affected_skills"],
                         ["example/editing", "example/writing"])

    def test_declared_whole_matrix_runtime_input_keeps_file_applicability(self):
        matrix = "evals/control-plane-matrix.json"
        corpus = "evals/example/corpus.json"
        self.write(corpus, {"scenarios": [
            {"id": "writing", "skill": "writing", "expectations": ["Write."]},
            {"id": "editing", "skill": "editing", "expectations": ["Edit."]}]})
        rows = [{"id": "example:" + name, "entrypoint": f"plugins/example/skills/{name}/SKILL.md", "companions": [],
                 "scenario": {"kind": "simple-corpus", "source": corpus, "selector": name, "id": name}}
                for name in ("writing", "editing")]
        runtime = {"example:writing": [matrix]}
        self.write(matrix, {"skills": rows[:1], "runtime_dependencies": runtime})
        base = self.commit("writer runtime reads complete matrix")
        self.write(matrix, {"skills": rows, "runtime_dependencies": runtime})
        candidate = self.commit("append editor to runtime matrix")
        self.assertEqual(inventory.compare(self.repo, base, candidate)["affected_skills"],
                         ["example/editing", "example/writing"])

    def test_matrix_companion_changes_select_transitive_consumers(self):
        matrix = "evals/control-plane-matrix.json"
        corpus = "evals/example/corpus.json"
        names = ("writing", "editing", "reading")
        self.write("plugins/example/topology.json", {"skills": {name: {"calls": []} for name in names}})
        self.write("plugins/example/skills/reading/SKILL.md", "Read.\n")
        self.write(corpus, {"scenarios": [{"id": name, "skill": name, "expectations": [name]} for name in names]})
        rows = [{"id": "example:" + name, "entrypoint": f"plugins/example/skills/{name}/SKILL.md",
                 "companions": ["example:editing"] if name == "writing" else [],
                 "scenario": {"kind": "simple-corpus", "source": corpus, "selector": name, "id": name}}
                for name in names]
        self.write(matrix, {"skills": rows, "runtime_dependencies": {}})
        base = self.commit("writer consumes editor")
        rows[1]["companions"] = ["example:reading"]
        self.write(matrix, {"skills": rows, "runtime_dependencies": {}})
        candidate = self.commit("editor also consumes reader")
        self.assertEqual(inventory.compare(self.repo, base, candidate)["affected_skills"],
                         ["example/editing", "example/writing"])
        writer = inventory.discover(self.repo, candidate)["skills"]["example/writing"]
        self.assertIn("plugins/example/skills/reading/SKILL.md", writer["behavior_inputs"])
        self.assertEqual(inventory.compare(self.repo, candidate, base)["affected_skills"],
                         ["example/editing", "example/writing"])

    def test_matrix_scenario_owner_and_removal_changes_select_old_and_new_consumers(self):
        matrix = "evals/control-plane-matrix.json"
        corpus = "evals/example/corpus.json"
        self.write(corpus, {"scenarios": [
            {"id": "first", "skill": "writing", "expectations": ["First."]},
            {"id": "second", "skill": "writing", "expectations": ["Second."]}]})
        row = {"id": "example:writing", "entrypoint": "plugins/example/skills/writing/SKILL.md", "companions": [],
               "scenario": {"kind": "simple-corpus", "source": corpus, "selector": "first", "id": "first"}}
        self.write(matrix, {"skills": [row]})
        base = self.commit("first writer scenario")
        changes = [
            ([{**row, "scenario": {**row["scenario"], "selector": "second", "id": "second"}}], ["example/writing"]),
            ([{**row, "id": "example:editing", "entrypoint": "plugins/example/skills/editing/SKILL.md"}],
             ["example/editing", "example/writing"]),
            ([], ["example/writing"]),
        ]
        for rows, owners in changes:
            with self.subTest(rows=rows):
                self.write(matrix, {"skills": rows})
                candidate = self.commit("change matrix consumption")
                self.assertEqual(inventory.compare(self.repo, base, candidate)["affected_skills"], owners)
                self.assertEqual(inventory.compare(self.repo, candidate, base)["affected_skills"], owners)
        self.git("rm", matrix)
        removed = self.commit("remove matrix source")
        self.assertEqual(inventory.compare(self.repo, base, removed)["affected_skills"], ["example/writing"])

    def test_matrix_runtime_changes_select_direct_and_transitive_consumers(self):
        matrix = "evals/control-plane-matrix.json"
        corpus = "evals/example/corpus.json"
        names = ("writing", "editing", "reading")
        self.write("plugins/example/topology.json", {"skills": {name: {"calls": []} for name in names}})
        self.write("plugins/example/skills/reading/SKILL.md", "Read.\n")
        self.write(corpus, {"scenarios": [{"id": name, "skill": name, "expectations": [name]} for name in names]})
        rows = [{"id": "example:" + name, "entrypoint": f"plugins/example/skills/{name}/SKILL.md",
                 "companions": ["example:" + names[index + 1]] if index < 2 else [],
                 "scenario": {"kind": "simple-corpus", "source": corpus, "selector": name, "id": name}}
                for index, name in enumerate(names)]
        for path in ("runtime/old.md", "runtime/new.md"):
            self.write(path, "Runtime input.\n")
        self.write(matrix, {"skills": rows, "runtime_dependencies": {"example:reading": ["runtime/old.md"]}})
        base = self.commit("transitive reader runtime")
        self.write(matrix, {"skills": rows, "runtime_dependencies": {"example:reading": ["runtime/new.md"]}})
        candidate = self.commit("change transitive runtime declaration")
        expected = ["example/editing", "example/reading", "example/writing"]
        self.assertEqual(inventory.compare(self.repo, base, candidate)["affected_skills"], expected)
        self.assertEqual(inventory.compare(self.repo, candidate, base)["affected_skills"], expected)
        observed = inventory.discover(self.repo, candidate)
        for name in names:
            self.assertIn("runtime/new.md", observed["skills"]["example/" + name]["behavior_inputs"])
            self.assertNotIn("runtime/old.md", observed["skills"]["example/" + name]["behavior_inputs"])
        self.write("runtime/new.md", "Changed runtime bytes.\n")
        changed_bytes = self.commit("change transitive runtime bytes")
        self.assertEqual(inventory.compare(self.repo, candidate, changed_bytes)["affected_skills"], expected)

    def test_runtime_owner_aliases_preserve_direct_and_transitive_consumption(self):
        matrix = "evals/control-plane-matrix.json"
        corpus = "evals/example/corpus.json"
        names = ("writing", "editing")
        self.write(corpus, {"scenarios": [{"id": name, "skill": name, "expectations": [name]} for name in names]})
        rows = [{"id": "example:" + name, "companions": ["example:editing"] if name == "writing" else [],
                 "scenario": {"kind": "simple-corpus", "source": corpus, "selector": name}} for name in names]
        for path in ("runtime/shared.md", "runtime/old.md", "runtime/new.md"):
            self.write(path, "Runtime input.\n")
        runtime = {"example:editing": ["runtime/shared.md"], "example/editing": ["runtime/old.md"]}
        self.write(matrix, {"skills": rows, "runtime_dependencies": runtime})
        base = self.commit("runtime owner aliases with separate inputs")
        runtime["example/editing"] = ["runtime/new.md"]
        self.write(matrix, {"skills": rows, "runtime_dependencies": runtime})
        candidate = self.commit("change slash-form runtime owner input")
        expected = ["example/editing", "example/writing"]
        self.assertEqual(inventory.compare(self.repo, base, candidate)["affected_skills"], expected)
        self.assertEqual(inventory.compare(self.repo, candidate, base)["affected_skills"], expected)
        for skill in inventory.discover(self.repo, candidate)["skills"].values():
            self.assertIn("runtime/shared.md", skill["behavior_inputs"])
            self.assertIn("runtime/new.md", skill["behavior_inputs"])
            self.assertNotIn("runtime/old.md", skill["behavior_inputs"])

    def test_runtime_only_matrix_consumer_keeps_full_source_binding(self):
        matrix = "evals/control-plane-matrix.json"
        corpus = "evals/example/corpus.json"
        self.write(corpus, {"scenarios": [{"id": "edit", "skill": "editing", "expectations": ["Edit."]}]})
        row = {"id": "example:editing", "scenario": {
            "kind": "simple-corpus", "source": corpus, "selector": "edit"}}
        self.write("runtime/writing.md", "Runtime input.\n")
        runtime = {"example/writing": ["runtime/writing.md"]}
        self.write(matrix, {"skills": [row], "runtime_dependencies": runtime})
        base = self.commit("writer runtime declared outside scenario rows")
        writer = inventory.discover(self.repo, base)["skills"]["example/writing"]
        self.assertIn(matrix, writer["behavior_inputs"])
        self.assertIn(matrix, writer["source_identities"])
        row["entrypoint"] = "plugins/example/skills/editing/SKILL.md"
        self.write(matrix, {"skills": [row], "runtime_dependencies": runtime})
        candidate = self.commit("independent editor declaration change")
        self.assertEqual(inventory.compare(self.repo, base, candidate)["affected_skills"], ["example/editing"])
        self.assertNotEqual(writer["source_identities"][matrix],
                            inventory.discover(self.repo, candidate)["skills"]["example/writing"]["source_identities"][matrix])

    def test_unknown_runtime_only_owner_prevents_complete_matrix_selection(self):
        matrix = "evals/control-plane-matrix.json"
        corpus = "evals/example/corpus.json"
        self.write(corpus, {"scenarios": [{"id": "write", "skill": "writing", "expectations": ["Write."]}]})
        rows = [{"id": "example:writing", "scenario": {
            "kind": "simple-corpus", "source": corpus, "selector": "write"}}]
        self.write("runtime/new.md", "Runtime input.\n")
        self.write(matrix, {"skills": rows})
        base = self.commit("known matrix consumers")
        self.write(matrix, {"skills": rows, "runtime_dependencies": {"unknown:owner": ["runtime/new.md"]}})
        candidate = self.commit("runtime declaration without a roster owner")
        for before, after in ((base, candidate), (candidate, base)):
            compared = inventory.compare(self.repo, before, after)
            self.assertEqual(compared["status"], "unsupported")
            self.assertFalse(compared["selection_complete"])
            self.assertEqual(compared["affected_skills"], [])
            unknown = [row for row in compared["unsupported"] if row["code"] == "unknown-owner"]
            self.assertEqual(len(unknown), 1)
            self.assertEqual(unknown[0]["owners"], ["unknown/owner"])
            self.assertEqual(unknown[0]["source"]["path"], matrix)
        discovered = inventory.discover(self.repo, candidate)
        self.assertTrue(any(row["code"] == "unknown-owner" and row["scope"] == "ordinary"
                            for row in discovered["diagnostics"]))

    def test_unknown_runtime_owner_covers_changes_to_its_declared_dependencies(self):
        matrix = "evals/control-plane-matrix.json"
        dependency = "runtime/unknown/input.md"
        self.write(matrix, {"skills": [], "runtime_dependencies": {"unknown:owner": ["runtime/unknown"]}})
        for change in ("bytes", "mode", "remove", "add"):
            with self.subTest(change=change):
                self.write(dependency, "Original runtime.\n")
                (self.repo / dependency).chmod(0o644)
                base = self.commit("unknown owner with a declared runtime directory " + change)
                changed_path = dependency
                if change == "bytes":
                    self.write(dependency, "Changed runtime.\n")
                elif change == "mode":
                    (self.repo / dependency).chmod(0o755)
                elif change == "remove":
                    (self.repo / dependency).unlink()
                else:
                    changed_path = "runtime/unknown/added.md"
                    self.write(changed_path, "Added runtime.\n")
                candidate = self.commit("change unknown owner's runtime " + change)
                self.assertEqual(inventory.compare(self.repo, base, candidate)["changed_paths"], [changed_path])
                for before, after in ((base, candidate), (candidate, base)):
                    compared = inventory.compare(self.repo, before, after)
                    self.assertEqual(compared["status"], "unsupported")
                    self.assertFalse(compared["selection_complete"])
                    self.assertEqual(compared["affected_skills"], [])
                    self.assertTrue(any(row["code"] == "unknown-owner" for row in compared["unsupported"]))
                    self.assertEqual(inventory.check(self.repo, before, after, "release/receipts")["status"], "fail")
        base = self.git("rev-parse", "HEAD")
        self.write("runtime/unrelated.md", "Unrelated runtime.\n")
        candidate = self.commit("change outside the unresolved dependency")
        self.assertEqual(inventory.check(self.repo, base, candidate, "release/receipts")["status"], "not-required")

    def test_unknown_production_runtime_owner_remains_outside_ordinary_selection(self):
        matrix = "evals/skill-routing-matrix.json"
        dependency = "runtime/production.md"
        self.write(matrix, {"skills": [], "runtime_dependencies": {"unknown:owner": [dependency]}})
        self.write(dependency, "Production runtime.\n")
        base = self.commit("separate production runtime with unknown owner")
        self.write(dependency, "Changed production runtime.\n")
        candidate = self.commit("change separate production runtime")
        checked = inventory.check(self.repo, base, candidate, "release/receipts")
        self.assertEqual(checked["status"], "not-required")
        self.assertTrue(any(row["code"] == "unknown-owner" and row["scope"] == "production-release"
                            for row in checked["inventory_diagnostics"]["candidate"]))

    def test_multiple_matrix_rows_preserve_all_transitive_companions(self):
        matrix = "evals/control-plane-matrix.json"
        corpus = "evals/example/corpus.json"
        names = ("writing", "editing", "reading")
        self.write("plugins/example/topology.json", {"skills": {name: {"calls": []} for name in names}})
        self.write("plugins/example/skills/reading/SKILL.md", "Read.\n")
        self.write(corpus, {"scenarios": [{"id": name, "skill": name, "expectations": [name]} for name in names]})
        rows = [{"id": "example:" + name, "companions": ["example:editing"] if name == "writing" else [],
                 "scenario": {"kind": "simple-corpus", "source": corpus, "selector": name}} for name in names]
        rows.append({**rows[1], "id": "example/editing"})
        self.write(matrix, {"skills": rows})
        base = self.commit("multiple editor declarations")
        rows[1]["companions"] = ["example:reading"]
        self.write(matrix, {"skills": rows})
        candidate = self.commit("first editor declaration adds a companion")
        expected = ["example/editing", "example/writing"]
        for before, after in ((base, candidate), (candidate, base)):
            compared = inventory.compare(self.repo, before, after)
            self.assertEqual(compared["affected_skills"], expected)
            self.assertEqual(compared["status"], "complete", compared["unsupported"])
        discovered = inventory.discover(self.repo, candidate)
        for name in ("writing", "editing"):
            self.assertIn("plugins/example/skills/reading/SKILL.md", discovered["skills"]["example/" + name]["behavior_inputs"])
        self.assertEqual(discovered["documents"][matrix]["raw"]["skills"], rows)

    def test_matrix_projection_keeps_full_source_freshness_in_descriptors_and_receipts(self):
        self.current_corpus()
        self.processing_sources()
        matrix = "evals/control-plane-matrix.json"
        corpus = "plugins/example/skills/writing/evals/evals.json"
        rows = [{"id": "example:writing", "entrypoint": "plugins/example/skills/writing/SKILL.md", "companions": [],
                 "scenario": {"kind": "simple-corpus", "source": corpus, "selector": 0, "id": 0}}]
        self.write(matrix, {"skills": rows})
        base = self.commit("prepared writer with matrix source")
        original = inventory.descriptor(self.repo, base, "example/writing")
        self.assertEqual(original["status"], "ready", original["diagnostics"])
        receipt = self.prepared_receipt(base)
        self.assertEqual(receipt["snapshot"]["inputs"][matrix]["sha256"],
                         hashlib.sha256((self.repo / matrix).read_bytes()).hexdigest())
        rows.append({**rows[0], "id": "example:editing", "entrypoint": "plugins/example/skills/editing/SKILL.md"})
        self.write(matrix, {"skills": rows})
        candidate = self.commit("independent editor matrix row")
        self.assertEqual(inventory.compare(self.repo, base, candidate)["affected_skills"], ["example/editing"])
        current = inventory.descriptor(self.repo, candidate, "example/writing")
        self.assertEqual(current["status"], "ready", current["diagnostics"])
        self.assertEqual(current["descriptor"], original["descriptor"])
        self.assertIn(matrix, current["descriptor"]["behavior_inputs"])
        checked = inventory.core.check(self.repo, {"schema_version": 1,
            "base_revision": candidate, "candidate_revision": candidate,
            "skills": [current["descriptor"]], "changed_skills": ["example/writing"], "inventory_complete": True},
            {"example/writing": json.dumps(receipt).encode()})
        self.assertEqual(checked["skills"][0]["status"], "fail")
        self.assertIn("stale evaluated input closure", checked["skills"][0]["reason"])

    def test_matrix_consumption_uses_observed_contextual_owner_coordinates(self):
        matrix = "evals/example/matrix.json"
        corpus = "evals/example/corpus.json"
        self.write(corpus, {"scenarios": [{"id": name, "skill": name, "expectations": [name]}
                                          for name in ("writing", "editing")]})
        rows = [
            {"id": "writing", "companions": ["example:editing"],
             "scenario": {"kind": "simple-corpus", "source": corpus, "selector": "writing"}},
            {"id": "example:editing", "companions": [],
             "scenario": {"kind": "simple-corpus", "source": corpus, "selector": "editing"}},
        ]
        for path in ("runtime/old.md", "runtime/new.md"):
            self.write(path, "Runtime input.\n")
        self.write(matrix, {"skills": rows, "runtime_dependencies": {"example:editing": ["runtime/old.md"]}})
        base = self.commit("matrix with contextual writer owner")
        self.write(matrix, {"skills": rows, "runtime_dependencies": {"example:editing": ["runtime/new.md"]}})
        candidate = self.commit("contextual owner's companion runtime changes")
        compared = inventory.compare(self.repo, base, candidate)
        self.assertEqual(compared["affected_skills"], ["example/editing", "example/writing"])
        writer = inventory.discover(self.repo, candidate)["skills"]["example/writing"]
        self.assertIn("runtime/new.md", writer["behavior_inputs"])
        reference = next(record for record in writer["records"] if record["role"] == "scenario-reference")
        self.assertEqual(reference["id"], "writing")
        self.assertEqual(reference["pointer"], "/skills/0")

    def test_matrix_projection_keeps_unresolved_and_malformed_consumption_visible(self):
        self.current_corpus()
        matrix = "evals/control-plane-matrix.json"
        row = {"id": "example:writing", "companions": [], "scenario": {
            "kind": "simple-corpus", "source": "plugins/example/skills/writing/evals/evals.json", "selector": 0}}
        self.write(matrix, {"skills": [row]})
        base = self.commit("resolved scenario reference")
        row["scenario"]["selector"] = "absent"
        row["companions"] = ["example:absent"]
        self.write(matrix, {"skills": [row], "runtime_dependencies": {"example:writing": ["runtime/absent.md"]}})
        candidate = self.commit("unresolved scenario runtime and companion")
        compared = inventory.compare(self.repo, base, candidate)
        self.assertEqual(compared["affected_skills"], ["example/writing"])
        expected = {"scenario-selector-unresolved", "runtime-input-missing", "companion-unresolved"}
        self.assertTrue(expected <= {row["code"] for row in compared["inventory_diagnostics"]["candidate"]})
        described = inventory.descriptor(self.repo, candidate, "example/writing")
        self.assertEqual(described["status"], "unresolved")
        self.assertTrue(expected <= {row["code"] for row in described["diagnostics"]})
        checked = inventory.check(self.repo, base, candidate, "release/receipts")
        self.assertEqual(checked["status"], "fail")
        self.assertEqual(checked["skills"][0]["diagnostics"], described["diagnostics"])
        self.write(matrix, {"skills": [row], "runtime_dependencies": False})
        malformed = self.commit("malformed runtime declaration")
        compared = inventory.compare(self.repo, base, malformed)
        self.assertEqual(compared["status"], "unsupported")
        self.assertEqual(compared["affected_skills"], ["example/writing"])
        self.assertIn("unsupported-corpus", [row["code"] for row in compared["unsupported"]])

    def test_declared_matrix_companions_supply_transitive_behavior_inputs(self):
        self.write("plugins/example/references/edit.md", "Edit carefully.\n")
        self.write("plugins/example/skills/editing/SKILL.md", "Read [edit](../../references/edit.md).\n")
        self.write("evals/example/corpus.json", {"scenarios": [
            {"id": "write", "expectations": ["Write."]}, {"id": "edit", "expectations": ["Edit."]}]})
        declarations = [
            {"id": "example:writing", "entrypoint": "plugins/example/skills/writing/SKILL.md", "companions": ["example:editing"],
             "scenario": {"kind": "simple-corpus", "source": "evals/example/corpus.json", "selector": "write", "id": "write"}},
            {"id": "example:editing", "entrypoint": "plugins/example/skills/editing/SKILL.md", "companions": [],
             "scenario": {"kind": "simple-corpus", "source": "evals/example/corpus.json", "selector": "edit", "id": "edit"}}]
        self.write("evals/control-plane-matrix.json", {"skills": declarations, "runtime_dependencies": {}})
        base = self.commit("declared composed inputs")
        discovered = inventory.discover(self.repo, base)["skills"]["example/writing"]
        self.assertIn("plugins/example/skills/editing/SKILL.md", discovered["behavior_inputs"])
        self.assertIn("plugins/example/references/edit.md", discovered["behavior_inputs"])
        self.assertEqual([record["id"] for record in discovered["records"] if record["role"] == "application"], ["write"])
        self.write("plugins/example/references/edit.md", "Edit precisely.\n")
        candidate = self.commit("companion behavior changed")
        self.assertEqual(inventory.compare(self.repo, base, candidate)["affected_skills"], ["example/editing", "example/writing"])

    def test_cli_exposes_immutable_discovery_comparison_and_unresolved_review_queue(self):
        path = "evals/example/skills/writing/evals.json"
        self.write(path, {"skill_name": "writing", "evals": [{"id": 0, "expectations": ["Original requirement."]}]})
        candidate = self.commit("unclassified application")
        script = Path(__file__).resolve().parents[1] / "scripts/behavior_eval_inventory.py"
        def run(*args):
            process = subprocess.run(["python", str(script), "--repository", str(self.repo), *args], capture_output=True, text=True)
            return process.returncode, json.loads(process.stdout)
        code, discovered = run("discover", "--revision", candidate)
        self.assertEqual(code, 0)
        self.assertEqual(discovered["revision"], candidate)
        code, compared = run("compare", "--base", self.base, "--candidate", candidate)
        self.assertEqual(code, 0)
        self.assertEqual(compared["affected_skills"], ["example/writing"])
        code, normalized = run("normalize", "--revision", candidate, "--skill", "example/writing")
        self.assertEqual(code, 1)
        self.assertEqual(normalized["status"], "unresolved")
        code, queue = run("proposals", "--revision", candidate, "--skill", "example/writing")
        self.assertEqual(code, 1)
        self.assertEqual(queue["expectations"][0]["original"], "Original requirement.")
        self.assertIsNone(queue["expectations"][0]["id"])
        self.assertIsNone(queue["expectations"][0]["severity"])
        self.assertEqual(queue["proposed_entries"], [])
        self.assertFalse((self.repo / inventory.EXPECTATION_MAP).exists())

    def test_nonregular_corpus_is_diagnostic_and_unselected_comparison_stays_noop(self):
        target = self.repo / "evals/example/skills/writing/evals.json"
        target.parent.mkdir(parents=True)
        target.symlink_to("elsewhere.json")
        base = self.commit("nonregular corpus")
        observed = inventory.discover(self.repo, base)
        self.assertIn("corpus-unavailable", [row["code"] for row in observed["skills"]["example/writing"]["diagnostics"]])
        self.write("scripts/tool.py", "# Tool only.\n")
        candidate = self.commit("unselected tool update")
        self.assertEqual(inventory.compare(self.repo, base, candidate)["status"], "complete")

    def test_runner_documented_uppercase_placeholders_are_not_missing_resources(self):
        self.write("plugins/example/skills/writing/SKILL.md", "Read [contract](../../references/contract.md).\n")
        self.write("plugins/example/references/contract.md", "Example: `[files](FILES_URL)`. Read [real](real.md).\n")
        candidate = self.commit("link placeholder")
        observed = inventory.discover(self.repo, candidate)["skills"]["example/writing"]
        self.assertNotIn("plugins/example/references/FILES_URL", observed["behavior_inputs"])
        self.assertEqual([item["path"] for item in observed["diagnostics"] if item["code"] == "input-unavailable"], ["plugins/example/references/real.md"])

    def test_missing_local_resource_is_not_omitted_from_closure(self):
        self.write("plugins/example/skills/writing/SKILL.md", "Read [required](references/missing.md).\n")
        candidate = self.commit("missing local dependency")
        result = inventory.discover(self.repo, candidate)["skills"]["example/writing"]
        self.assertIn("plugins/example/skills/writing/references/missing.md", result["behavior_inputs"])
        self.assertIn("input-unavailable", [item["code"] for item in result["diagnostics"]])

    def test_topology_declared_external_resources_and_missing_paths_are_consumed(self):
        self.write("plugins/example/topology.json", {"skills": {
            "writing": {"references": ["references/shared.md"], "scripts": ["scripts/missing.py"]}, "editing": {}}})
        self.write("plugins/example/references/shared.md", "Shared behavior.\n")
        base = self.commit("explicit topology inputs")
        observed = inventory.discover(self.repo, base)["skills"]["example/writing"]
        self.assertIn("plugins/example/references/shared.md", observed["behavior_inputs"])
        self.assertIn("plugins/example/scripts/missing.py", observed["behavior_inputs"])
        self.assertIn("input-unavailable", [item["code"] for item in observed["diagnostics"]])
        self.write("plugins/example/references/shared.md", "Changed behavior.\n")
        candidate = self.commit("changed declared input")
        self.assertEqual(inventory.compare(self.repo, base, candidate)["affected_skills"], ["example/writing"])

    def test_unknown_matrix_consumer_cannot_report_complete_selection(self):
        self.write("evals/example/corpus.json", {"scenarios": [{"id": "case", "skill": "writing", "expectations": ["Write."]}]})
        base = self.commit("owned source")
        self.write("evals/control-plane-matrix.json", {"skills": [{"id": "example:missing",
            "scenario": {"source": "evals/example/corpus.json", "kind": "simple-corpus", "selector": "case", "id": "case"}}]})
        candidate = self.commit("unknown matrix owner")
        result = inventory.compare(self.repo, base, candidate)
        self.assertFalse(result["selection_complete"])
        self.assertIn("unknown-owner", [item["code"] for item in result["unsupported"]])

    def test_nonregular_referenced_definition_is_a_selected_diagnostic(self):
        target = self.repo / "evals/control.json"
        target.parent.mkdir(parents=True)
        target.symlink_to("elsewhere.json")
        self.write("evals/routing.json", {"semantic_definition": {"path": "evals/control.json", "sha256": "0" * 64},
            "skills": [{"id": "example:writing", "cold_start": "Write.", "explicit": "$writing"}]})
        revision = self.commit("nonregular declared reference")
        result = inventory.discover(self.repo, revision)["skills"]["example/writing"]
        self.assertIn("reference-unavailable", [item["code"] for item in result["diagnostics"]])

    def test_projection_mapping_change_selects_its_old_and_new_consumer(self):
        self.write("release/provingkit/definition-v1.json", {"membership": {"members": [
            {"id": "artifact-customs", "content_identity": {"path": "release/plugin-content-locks/example.json"}}]}})
        self.write("plugins/artifact-customs/topology.json", {"skills": {"adopting": {}, "maintaining": {}}})
        for skill in ("adopting", "maintaining"):
            self.write(f"plugins/artifact-customs/skills/{skill}/SKILL.md", "Use the declared references.\n")
            self.write(f"plugins/artifact-customs/skills/{skill}/references/contract.md", "Contract.\n")
        self.write("plugins/artifact-customs/references/contract.md", "Contract.\n")
        self.write("scripts/validate_artifact_customs.py", "SKILL_REFERENCES = {'adopting': ['contract.md']}\n")
        base = self.commit("original projection consumer")
        self.write("scripts/validate_artifact_customs.py", "SKILL_REFERENCES = {'maintaining': ['contract.md']}\n")
        candidate = self.commit("new projection consumer")
        self.assertEqual(inventory.compare(self.repo, base, candidate)["affected_skills"],
                         ["artifact-customs/adopting", "artifact-customs/maintaining"])


if __name__ == "__main__":
    unittest.main()
