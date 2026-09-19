"""Pure source/data contract tests; these do not execute behavior evaluations."""

import hashlib
import copy
import json
from pathlib import Path
import unittest

from scripts import behavior_eval_corpora as corpora


ROOT = Path(__file__).resolve().parents[1]


class CorpusTests(unittest.TestCase):
    def test_deep_source_bytes_remain_diagnostics_with_declared_scope(self):
        content = b"[" * 50_000 + b"0" + b"]" * 50_000
        for path in ("evals/example/corpus.json", "evals/skill-routing-matrix.json"):
            with self.subTest(path=path):
                result = corpora.inspect_document(path, content)
                self.assertEqual(result["records"], [])
                self.assertIsNone(result["raw"])
                self.assertEqual(result["diagnostics"][0]["code"], "invalid-json")
                self.assertEqual(result["source"]["path"], path)
                if path == "evals/skill-routing-matrix.json":
                    self.assertEqual(result["role"], "scope")
                    self.assertEqual(result["scope"], "production-release")
                else:
                    self.assertEqual(result["role"], "unsupported")
                json.dumps(result, ensure_ascii=False, allow_nan=False).encode("utf-8")

    def test_source_admission_rejects_nonfinite_numbers_and_unpaired_surrogates(self):
        for content in (
            b'{"skill_name":"writing","evals":[{"id":1e309}]}',
            b'{"skill_name":"writing","evals":[{"prompt":"\\ud800"}]}',
            b'{"skill_name":"writing","evals":[],"\\udfff":1}',
            b'{"\\ud800":1,"\\ud800":2}',
        ):
            with self.subTest(content=content):
                inspected = corpora.inspect_document("evals/example/evals.json", content)
                self.assertEqual(inspected["role"], "unsupported")
                self.assertEqual(inspected["records"], [])
                self.assertEqual(inspected["diagnostics"][0]["code"], "invalid-json")
                json.dumps(inspected, ensure_ascii=False, allow_nan=False).encode("utf-8")

    def test_current_acceptance_policy_and_retained_run_shapes_are_classified(self):
        examples = [
            ("evals/example/policy.json", {"repetitions": 3, "behavior_acceptance": {}, "trigger_acceptance": {}}, "support"),
            ("evals/example/application.json", {"input_format": "packet", "candidate_bundle": [], "runs": []}, "retained-evidence"),
            ("evals/example/discovery.json", {"results": [], "detector": "codex-native-sentinel"}, "retained-evidence"),
            ("evals/example/final-grading.json", {"results": [], "kind": "grading"}, "retained-evidence"),
            ("evals/example/repetition-grading-input.json", {"outputs": []}, "retained-evidence"),
            ("evals/example/iteration-2-adjudication.json", {"decision": "regrade", "invalidation": {}}, "retained-evidence"),
            ("evals/example/acceptance.json", {"evidence_kind": "ordinary", "bound_evidence_sha256": {}}, "retained-evidence"),
            ("evals/example/repetitions.json", {"evidence_kind": "ordinary", "retained_runs": []}, "retained-evidence"),
        ]
        for path, data, role in examples:
            with self.subTest(path=path):
                result = corpora.inspect_document(path, json.dumps(data).encode())
                self.assertEqual(result["role"], role)
                self.assertFalse(any(row["role"] in ("application", "trigger") for row in result["records"]))
    def test_incomplete_or_invalid_expectations_never_form_ready_cases(self):
        for expectations in ([], [{"id": "", "text": "Keep.", "severity": "quality"}],
                             [{"id": "keep", "text": "", "severity": "quality"}],
                             [{"id": "keep", "text": "Keep.", "severity": "unknown"}],
                             [{"id": "same", "text": "One.", "severity": "quality"},
                              {"id": "same", "text": "Two.", "severity": "safety"}]):
            with self.subTest(expectations=expectations):
                path = "evals/example/corpus.json"
                content = json.dumps({"scenarios": [{"id": "one", "expectations": expectations}]}).encode()
                records = corpora.inspect_document(path, content)["records"]
                result = corpora.normalize_records(records, {"schema_version": 1, "entries": []}, {path: content})
                self.assertEqual(result["cases"][0]["status"], "unresolved")
                self.assertTrue(result["diagnostics"])

    def test_dictionary_coordinate_preserves_original_scenario_key(self):
        path = "plugins/example/evals/corpus.json"
        content = b'{"scenarios":{"original.md":{"candidate_skill":"writer","expectations":[{"id":"keep","text":"Keep.","severity":"quality"}]}}}'
        records = corpora.inspect_document(path, content)["records"]
        result = corpora.normalize_records(records, {"schema_version": 1, "entries": []},
            {path: content, "plugins/example/evals/fixtures/original.md": b"Fixture."})
        self.assertEqual(result["cases"][0]["case_id"]["id"], "original.md")
        self.assertEqual(result["cases"][0]["status"], "ready")

    def test_fixture_literals_resolve_repository_paths_and_expose_unresolvable_values(self):
        path = "evals/example/skills/writing/evals.json"
        content = b'{"skill_name":"writing","evals":[{"id":0,"files":["writing/fixtures/../input.md","../../../../escape.md"]}]}'
        result = corpora.inspect_document(path, content)
        fixtures = result["records"][0]["fixtures"]
        self.assertEqual(fixtures[0]["literal"], "writing/fixtures/../input.md")
        self.assertEqual(fixtures[0]["path"], "evals/example/skills/writing/input.md")
        self.assertIsNone(fixtures[1]["path"])
        self.assertEqual(result["diagnostics"][0]["code"], "fixture-path-unresolved")

    def test_invalid_map_bytes_are_diagnostics_and_never_ready_cases(self):
        path = "evals/example/corpus.json"
        content = b'{"scenarios":[{"id":"one","expectations":[{"id":"declared","text":"Keep.","severity":"quality"}]}]}'
        records = corpora.inspect_document(path, content)["records"]
        for mapping in (b'{"schema_version":1,"entries":[],"entries":[]}', {"schema_version": 2, "entries": []}, {"schema_version": 1, "entries": [None]}):
            with self.subTest(mapping=mapping):
                result = corpora.normalize_records(records, mapping, {path: content})
                self.assertEqual(result["cases"][0]["status"], "unresolved")
                self.assertEqual(result["diagnostics"][0]["code"], "invalid-expectation-map")

    def test_deep_expectation_map_keeps_selected_cases_unresolved(self):
        path = "evals/example/corpus.json"
        content = b'{"scenarios":[{"id":"one","expectations":[{"id":"safe","text":"Keep.","severity":"safety"}]}]}'
        records = corpora.inspect_document(path, content)["records"]
        nested = b"[" * 50_000 + b"0" + b"]" * 50_000
        mapping = b'{"schema_version":1,"entries":[],"unused":' + nested + b'}'
        result = corpora.normalize_records(records, mapping, {path: content})
        self.assertEqual(len(result["cases"]), 1)
        self.assertEqual(result["cases"][0]["status"], "unresolved")
        self.assertEqual(result["diagnostics"][0]["code"], "invalid-expectation-map")
        json.dumps(result, ensure_ascii=False, allow_nan=False).encode("utf-8")

    def test_normalization_requires_present_fixtures_and_unchanged_source_observations(self):
        path = "evals/example/skills/writing/evals.json"
        content = b'{"skill_name":"writing","evals":[{"id":0,"fixture_paths":["writing/fixtures/input.md"],"expectations":[{"id":"keep","text":"Keep.","severity":"quality"}]}]}'
        records = corpora.inspect_document(path, content)["records"]
        empty_map = {"schema_version": 1, "entries": []}
        missing = corpora.normalize_records(records, empty_map, {path: content})
        self.assertEqual(missing["cases"][0]["status"], "unresolved")
        self.assertEqual(missing["diagnostics"][0]["code"], "fixture-missing")
        documents = {path: content, "evals/example/skills/writing/fixtures/input.md": b"Source fixture."}
        self.assertEqual(corpora.normalize_records(records, empty_map, documents)["cases"][0]["status"], "ready")
        changed = copy.deepcopy(records)
        changed[0]["expectations"][0]["text"] = "Replacement."
        invalid = corpora.normalize_records(changed, empty_map, documents)
        self.assertEqual(invalid["cases"][0]["status"], "unresolved")
        self.assertIn("record-source-mismatch", [d["code"] for d in invalid["diagnostics"]])

    def test_malformed_or_unsupported_source_is_diagnostic_instead_of_partial_success(self):
        for content, code in (
            (b'{"evals":[],"evals":[{}]}', "invalid-json"),
            (b'{"evals":[{"id":NaN}]}', "invalid-json"),
            (b'{"evals":[null]}', "malformed-source"),
            (b'{"evals":[{"expectations":"not an array"}]}', "malformed-source"),
            (b'{"future_corpus":[{"id":0}]}', "unsupported-format"),
            (b'[{"query":"Go.","should_trigger":1}]', "malformed-source"),
        ):
            with self.subTest(content=content):
                result = corpora.inspect_document("evals/example.json", content)
                self.assertEqual(result["records"], [])
                self.assertEqual(result["diagnostics"][0]["code"], code)
                self.assertEqual(result["source"]["sha256"], hashlib.sha256(content).hexdigest())

    def test_selected_stale_unreviewed_and_conflicting_maps_remain_unresolved(self):
        path = "evals/example/corpus.json"
        content = b'{"scenarios":[{"id":"first","expectations":[{"id":"declared","text":"Keep.","severity":"quality"}]}]}'
        records = corpora.inspect_document(path, content)["records"]
        original = json.loads(content)["scenarios"][0]["expectations"][0]
        entry = {"source": records[0]["source"], "pointer": "/scenarios/0/expectations/0", "original": original, "id": "declared", "severity": "quality", "status": "accepted"}
        entry["review"] = {"decision": "accepted", "reference": "test-review", "mapping_sha256": corpora.mapping_digest(entry)}
        changes = [("source", {"path": path, "sha256": "0" * 64}, "mapping-source-mismatch"), ("review", None, "mapping-review-required"), ("id", "replacement", "mapping-source-conflict")]
        for field, value, code in changes:
            invalid = copy.deepcopy(entry)
            invalid[field] = value
            if field == "id":
                invalid["review"]["mapping_sha256"] = corpora.mapping_digest(invalid)
            with self.subTest(field=field):
                result = corpora.normalize_records(records, {"schema_version": 1, "entries": [invalid]}, {path: content})
                self.assertEqual(result["cases"][0]["status"], "unresolved")
                self.assertEqual(result["cases"][0]["expectations"][0]["id"], "declared")
                self.assertEqual(result["diagnostics"][0]["code"], code)
        unrelated = copy.deepcopy(entry)
        unrelated["source"]["path"] = "evals/elsewhere.json"
        unrelated["review"] = None
        self.assertEqual(corpora.normalize_records(records, {"schema_version": 1, "entries": [unrelated]}, {path: content})["diagnostics"], [])

    def test_unaccepted_proposals_do_not_override_declared_or_accepted_classifications(self):
        path = "evals/example/corpus.json"
        content = b'{"scenarios":[{"id":"first","expectations":[{"id":"source-id","text":"Keep.","severity":"quality"},"Missing."]}]}'
        records = corpora.inspect_document(path, content)["records"]
        source = records[0]["source"]
        entries = []
        for index, original in enumerate(json.loads(content)["scenarios"][0]["expectations"]):
            entries.append({"source": source, "pointer": f"/scenarios/0/expectations/{index}", "original": original, "status": "proposed", "id": "proposed-id", "severity": "safety"})
        accepted = {**entries[1], "status": "accepted", "id": "accepted-id", "severity": "quality"}
        accepted["review"] = {"decision": "accepted", "reference": "test-review", "mapping_sha256": corpora.mapping_digest(accepted)}
        entries.append(accepted)
        result = corpora.normalize_records(records, {"schema_version": 1, "entries": entries}, {path: content})
        self.assertEqual(result["cases"][0]["status"], "ready")
        self.assertEqual([e["id"] for e in result["cases"][0]["expectations"]], ["source-id", "accepted-id"])
        self.assertEqual(result["diagnostics"], [])
        entries.append(copy.deepcopy(accepted))
        rejected = corpora.normalize_records(records, {"schema_version": 1, "entries": entries}, {path: content})
        self.assertEqual(rejected["cases"][0]["status"], "unresolved")
        self.assertIn("mapping-duplicate", [d["code"] for d in rejected["diagnostics"]])

    def test_protocol_scopes_and_retained_results_never_promote_application_grades(self):
        for path, role in (
            ("evals/proseweaving/preview-panel/panel.json", "scope"),
            ("evals/review-publication-handoffs/grading-criteria.json", "scope"),
            ("plugins/mergecraft/skills/writing-github-issue-and-pr-markdown/evals/coverage.json", "support"),
            ("plugins/rolecasting/evals/delivery.json", "support"),
            ("plugins/mergecraft/skills/writing-github-issue-and-pr-markdown/evals/policy.json", "support"),
            ("plugins/mergecraft/skills/writing-github-issue-and-pr-markdown/evals/experiment.json", "retained-evidence"),
            ("plugins/mergecraft/skills/interacting-with-pr-review-feedback/evals/discovery-evidence.json", "retained-evidence"),
            ("evals/review-publication-handoffs/grading.json", "retained-evidence"),
        ):
            with self.subTest(path=path):
                content = (ROOT / path).read_bytes()
                document = corpora.inspect_document(path, content)
                self.assertEqual(document["role"], role)
                self.assertEqual(document["raw"], json.loads(content))
                normalized = corpora.normalize_records(document["records"], {"schema_version": 1, "entries": []}, {path: content})
                self.assertEqual(normalized["cases"], [])
                self.assertEqual(normalized["triggers"], [])
                self.assertTrue(document["diagnostics"])
        panel = corpora.inspect_document("evals/proseweaving/preview-panel/panel.json", (ROOT / "evals/proseweaving/preview-panel/panel.json").read_bytes())
        self.assertEqual(panel["records"][0]["id"], 1)
        self.assertTrue(any(ref["path"] == "evals/skill-routing-matrix.json" for ref in panel["references"]))

    def test_normalized_triggers_bind_bytes_and_preserve_multiple_selected_skills(self):
        path = "evals/routing.json"
        raw = {"semantic_definition": {"path": "evals/control.json"}, "skills": [{"id": "example:writer", "cold_start": "Write.", "explicit": "$writer", "supplemental": {"positive": "Pair them.", "positive_expected_skills": ["writer", "reviewer", "writer"], "negative": "Review.", "negative_expected_skills": ["reviewer"]}}]}
        content = json.dumps(raw).encode()
        records = corpora.inspect_document(path, content)["records"]
        result = corpora.normalize_records(records, {"schema_version": 1, "entries": []}, {path: content})
        self.assertEqual(len(result["triggers"]), 4)
        self.assertEqual(result["triggers"][2]["expected_selection"], ["writer", "reviewer", "writer"])
        self.assertEqual(result["triggers"][2]["case_id"], {"source": path, "pointer": "/skills/0/supplemental/positive", "id": None})
        self.assertEqual(result["triggers"][2]["status"], "ready")
        changed = corpora.normalize_records(records, {"schema_version": 1, "entries": []}, {path: content + b" "})
        self.assertTrue(all(record["status"] == "unresolved" for record in changed["triggers"]))
        self.assertEqual(changed["diagnostics"][0]["code"], "source-bytes-mismatch")

    def test_normalized_triggers_retain_invalid_queries_and_sequences_as_unresolved(self):
        examples = [([{ "query": " \t", "should_trigger": False}], "/0")]
        row = {"id": "example:writer", "cold_start": "Write.", "explicit": "$writer",
            "supplemental": {"positive": "Write more.", "positive_expected_skills": ["writer"],
                             "negative": "Review.", "negative_expected_skills": ["reviewer"]}}
        for field, value, pointer in (
            ("cold_start", 42, "/skills/0/cold_start"),
            ("explicit", "\n\t", "/skills/0/explicit"),
            ("positive", None, "/skills/0/supplemental/positive"),
            ("positive_expected_skills", "writer", "/skills/0/supplemental/positive"),
            ("positive_expected_skills", ["writer", 0], "/skills/0/supplemental/positive"),
            ("negative_expected_skills", [" "], "/skills/0/supplemental/negative"),
            ("negative_expected_skills", None, "/skills/0/supplemental/negative"),
        ):
            altered = copy.deepcopy(row)
            (altered if field in ("cold_start", "explicit") else altered["supplemental"])[field] = value
            examples.append(({"semantic_definition": {"path": "evals/control.json"}, "skills": [altered]}, pointer))
        for document, pointer in examples:
            with self.subTest(document=document):
                path = "evals/example/triggers.json"
                content = json.dumps(document).encode()
                observed = corpora.inspect_document(path, content)
                result = corpora.normalize_records(observed["records"], {"schema_version": 1, "entries": []}, {path: content})
                case = next(case for case in result["triggers"] if case["pointer"] == pointer)
                self.assertEqual(case["status"], "unresolved")
                self.assertEqual(case["raw_case"] if "raw_case" in case else case["raw"],
                                 document["skills"][0] if isinstance(document, dict) else document[0])
                self.assertIn("invalid-trigger", [item["code"] for item in result["diagnostics"]])

    def test_projection_changes_only_for_selected_accepted_mapping_semantics(self):
        path = "evals/example/corpus.json"
        content = b'{"scenarios":[{"id":"first","expectations":["One."]},{"id":"second","expectations":["Two."]}]}'
        records = corpora.inspect_document(path, content)["records"]
        entries = [{"source": records[0]["source"], "pointer": "/scenarios/0/expectations/0", "original": "One.", "id": "one", "severity": "quality", "status": "accepted", "rationale": "One."}, {"source": records[1]["source"], "pointer": "/scenarios/1/expectations/0", "original": "Two.", "id": "two", "severity": "quality", "status": "accepted"}]
        first = corpora.mapping_projection(entries, records[:1])
        changed = copy.deepcopy(entries)
        changed[0]["rationale"] = "Reworded."
        changed[0]["review"] = {"reference": "Different reference"}
        changed[1]["severity"] = "safety"
        changed.append({**entries[0], "status": "proposed", "id": "proposal"})
        self.assertEqual(corpora.mapping_projection(changed, records[:1]), first)
        changed[0]["id"] = "new-one"
        self.assertNotEqual(corpora.mapping_projection(changed, records[:1]), first)
        self.assertEqual(corpora.mapping_projection(entries, []), [])

    def test_accepted_mapping_is_bound_to_original_bytes_pointer_and_reviewed_semantics(self):
        path = "evals/example/corpus.json"
        content = b'{"scenarios":[{"id":"first","expectations":["Exact requirement."]}]}'
        records = corpora.inspect_document(path, content)["records"]
        semantic = {"source": {"path": path, "sha256": hashlib.sha256(content).hexdigest()}, "pointer": "/scenarios/0/expectations/0", "original": "Exact requirement.", "id": "explicit-id", "severity": "quality"}
        digest = hashlib.sha256(json.dumps(semantic, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()
        entry = {**semantic, "status": "accepted", "rationale": "Constructed test classification, not source policy.", "review": {"decision": "accepted", "reference": "https://example.invalid/review/1", "mapping_sha256": digest}}
        mapping = {"schema_version": 1, "entries": [entry]}
        result = corpora.normalize_records(records, mapping, {path: content})
        self.assertEqual(result["diagnostics"], [])
        self.assertEqual(result["cases"][0]["status"], "ready")
        self.assertEqual(result["cases"][0]["expectations"][0]["id"], "explicit-id")
        self.assertEqual(result["cases"][0]["expectations"][0]["severity"], "quality")
        for field, value in (("original", "Different requirement."), ("id", "unreviewed-revision")):
            invalid = copy.deepcopy(mapping)
            invalid["entries"][0][field] = value
            with self.subTest(field=field):
                rejected = corpora.normalize_records(records, invalid, {path: content})
                self.assertEqual(rejected["cases"][0]["status"], "unresolved")
                self.assertIsNone(rejected["cases"][0]["expectations"][0]["id"])
                self.assertTrue(rejected["diagnostics"])

    def test_normalization_keeps_unclassified_expectations_and_original_coordinates(self):
        path = "evals/example/skills/writing/evals.json"
        content = json.dumps({"skill_name": "writing", "evals": [{"id": 0, "prompt": "Write.", "expectations": ["Exact wording.", {"id": "declared", "text": "Keep this.", "severity": "quality"}]}]}).encode()
        records = corpora.inspect_document(path, content, plugin="example")["records"]
        result = corpora.normalize_records(records, {"schema_version": 1, "entries": []}, {path: content})
        case = result["cases"][0]
        self.assertEqual(case["case_id"], {"source": path, "pointer": "/evals/0", "id": 0})
        self.assertEqual(case["status"], "unresolved")
        self.assertEqual(case["expectations"][0]["text"], "Exact wording.")
        self.assertIsNone(case["expectations"][0]["id"])
        self.assertIsNone(case["expectations"][0]["severity"])
        self.assertEqual(case["expectations"][1]["id"], "declared")
        self.assertEqual(case["expectations"][1]["severity"], "quality")
        self.assertEqual(result["diagnostics"][0]["code"], "expectation-mapping-required")

    def test_control_matrices_and_retirement_associations_are_references(self):
        for path in ("evals/control-plane-matrix.json", "evals/comparative-review-lifecycle-matrix.json", "evals/mergecraft/retirement-control-plane.json"):
            with self.subTest(path=path):
                content = (ROOT / path).read_bytes()
                original = json.loads(content)
                result = corpora.inspect_document(path, content)
                self.assertEqual(result["role"], "reference")
                self.assertEqual(len(result["records"]), len(original["skills"]))
                record = result["records"][0]
                self.assertEqual(record["owners"], [original["skills"][0]["id"]])
                self.assertEqual(record["scenario"], original["skills"][0]["scenario"])
                self.assertEqual(result["references"][0]["selector"], original["skills"][0]["scenario"]["selector"])
                self.assertEqual(record["expectations"], [])
        path = "evals/mergecraft/retirement-fixtures.json"
        result = corpora.inspect_document(path, (ROOT / path).read_bytes())
        self.assertEqual(result["records"][0]["role"], "retirement-association")
        self.assertEqual(result["records"][0]["owners"], [result["records"][0]["raw"]["evaluation_skill_id"]])
        self.assertTrue(any(r["path"] == "evals/mergecraft/retirement-comparative-corpus.json" for r in result["references"]))

    def test_triggers_preserve_every_query_boolean_and_complete_routing_sequence(self):
        path = "evals/mergecraft/skills/getting-prs-merged/trigger-evals.json"
        content = (ROOT / path).read_bytes()
        original = json.loads(content)
        result = corpora.inspect_document(path, content, plugin="mergecraft", skill="getting-prs-merged")
        self.assertEqual(len(result["records"]), len(original))
        self.assertEqual([r["query"] for r in result["records"]], [r["query"] for r in original])
        self.assertEqual([r["expected"] for r in result["records"]], [r["should_trigger"] for r in original])
        self.assertTrue(all(r["owners"] == [] and r["id"] is None for r in result["records"]))
        path = "evals/skill-routing-matrix.json"
        result = corpora.inspect_document(path, (ROOT / path).read_bytes())
        self.assertEqual(result["role"], "scope")
        self.assertEqual(result["scope"], "production-release")
        self.assertTrue(all(record["scope"] == "production-release" for record in result["records"]))
        first = result["records"][:4]
        self.assertEqual([r["pointer"] for r in first], ["/skills/0/cold_start", "/skills/0/explicit", "/skills/0/supplemental/positive", "/skills/0/supplemental/negative"])
        self.assertEqual(first[0]["expected"], ["choosing-agent-models"])
        self.assertEqual(first[3]["expected"], ["delegating-cross-agent-work"])
        self.assertEqual(first[3]["owners"], ["rolecasting:choosing-agent-models"])
        self.assertIsNone(first[3]["id"])
        self.assertEqual(result["references"][1]["owners"], ["versionkeeping:checkpointing-and-publishing-git-work"])

    def test_routing_format_does_not_override_the_declared_source_scope(self):
        original = {"semantic_definition": {"path": "evals/control.json"}, "skills": [{"id": "example:writing",
            "cold_start": "Write.", "explicit": "Use writing.", "supplemental": {
                "positive": "Write a note.", "positive_expected_skills": ["writing", "editing", "writing"],
                "negative": "Edit a note.", "negative_expected_skills": ["editing"]}}]}
        content = json.dumps(original).encode()
        ordinary = corpora.inspect_document("evals/ordinary-routing.json", content)
        release = corpora.inspect_document("evals/skill-routing-matrix.json", content)
        self.assertEqual(ordinary["role"], "trigger")
        self.assertEqual(release["role"], "scope")
        self.assertEqual(release["scope"], "production-release")
        self.assertEqual([item["pointer"] for item in ordinary["records"]], [item["pointer"] for item in release["records"]])
        self.assertEqual(release["records"][2]["expected"], ["writing", "editing", "writing"])
        self.assertEqual(release["raw"], original)
        malformed = corpora.inspect_document("evals/skill-routing-matrix.json", b'{')
        self.assertEqual(malformed["scope"], "production-release")
        self.assertEqual(malformed["diagnostics"][0]["code"], "invalid-json")

    def test_shared_and_dictionary_corpora_preserve_source_fields_and_fixture_rules(self):
        paths = ["evals/mergecraft/corpus.json", "evals/versionkeeping/corpus.json",
                 "evals/artifact-customs/corpus.json", "plugins/tricritical/evals/corpus.json"]
        for path in paths:
            with self.subTest(path=path):
                original = json.loads((ROOT / path).read_bytes())
                document = corpora.inspect_document(path, (ROOT / path).read_bytes(), plugin=path.split("/")[1])
                cases = original["scenarios"]
                self.assertEqual(len(document["records"]), len(cases))
                for record in document["records"]:
                    if isinstance(cases, dict):
                        self.assertEqual(record["raw"], cases[record["key"]])
                        self.assertEqual(record["fixtures"][0]["path"], f"plugins/tricritical/evals/fixtures/{record['key']}")
                        self.assertIsNone(record["id"])
                    for fixture in record["fixtures"]:
                        self.assertTrue((ROOT / fixture["path"]).is_file(), fixture)
                    if record["raw"].get("skill", "declared") is None:
                        self.assertEqual(record["owners"], [])
                    for expectation in record["expectations"]:
                        self.assertIsNone(expectation["id"])
                        self.assertIsNone(expectation["severity"])

    def test_external_application_preserves_zero_id_and_exact_expectations(self):
        path = "evals/mergecraft/skills/getting-prs-ready-for-review/evals.json"
        content = (ROOT / path).read_bytes()
        original = json.loads(content)
        result = corpora.inspect_document(path, content, plugin="mergecraft")
        first = result["records"][0]
        self.assertEqual(result["format"], "skill-evals")
        self.assertEqual(result["source"]["sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(first["id"], 0)
        self.assertEqual(first["pointer"], "/evals/0")
        self.assertEqual(first["owners"], ["mergecraft:getting-prs-ready-for-review"])
        self.assertEqual(first["raw"], original["evals"][0])
        self.assertEqual(first["expectations"][0]["original"], original["evals"][0]["expectations"][0])
        self.assertIsNone(first["expectations"][0]["severity"])
        self.assertIsNone(first["expectations"][0]["id"])
        self.assertEqual(first["fixtures"][0]["path"], "evals/mergecraft/skills/getting-prs-ready-for-review/fixtures/ready-after-verified-checkpoint.md")


if __name__ == "__main__":
    unittest.main()
