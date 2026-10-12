"""Catalog behavior through its command interface, using invented evidence."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
COMMAND = ROOT / "scripts" / "coordination_catalog.py"


def specimen():
    return {
        "schema_version": 1,
        "snapshot": {
            "revision": "synthetic-first",
            "generated_at": "2026-01-01T00:00:00Z",
            "coverage": "Invented examples; no harness capability established.",
        },
        "decisions": ["https://example.org/decision"],
        "evidence": [{
            "id": "invented-source", "kind": "source",
            "uri": "https://example.org/source/immutable",
            "revision": "invented-revision", "observed_at": "2026-01-01T00:00:00Z",
            "limits": ["Invented source declaration only."],
        }],
        "endpoints": [
            {"id": "caller", "name": "Caller", "host": "Invented host",
             "surface": "terminal", "wave": 1, "evidence": ["invented-source"],
             "limits": ["Unqualified"]},
            {"id": "receiver", "name": "Receiver", "host": "Invented host",
             "surface": "GUI", "wave": 2, "evidence": ["invented-source"],
             "limits": ["Unqualified"]},
        ],
        "fabrics": [{
            "id": "sample-inbox", "name": "Sample inbox", "role": "actuator",
            "status": "discovered", "parent": None, "dependencies": [],
            "crosswalk": ["Invented candidate"], "evidence": ["invented-source"],
            "source_scope": "Invented source only",
            "compatibility": {"status": "unassessed", "scope": "Runtime unknown",
                              "evidence": []},
            "gaps": ["Actual receipt is unproved"], "next_check": "Bind the receiver",
            "effort": {"active_minutes": None, "cost": None},
        }],
        "profiles": [{
            "id": "sample-existing", "fabric": "sample-inbox", "channel": None,
            "population": "existing", "ownership": "User-owned; unverified",
            "relationship": "Independent peer", "target_input": "exact-reference",
            "input_semantics": "Peer-labelled informational input",
            "consent": {"references": [], "limits": ["No live grant"]},
            "continuity": {"idle": "unassessed", "busy": "unassessed", "restart": "unassessed"},
            "assurance": "Source declaration only; not live qualification",
            "claims": [{"operation": "notify", "milestone": "receipt",
                        "stage": "source-assessed", "coverage": "partial",
                        "evidence": ["invented-source"],
                        "limits": ["Submission does not establish receipt"]}],
            "gaps": ["Receiver proof missing"], "next_check": "Inspect an exact target",
        }],
        "channels": [{
            "id": "caller-to-receiver", "source": "caller", "target": "receiver",
            "fabrics": ["sample-inbox"], "profiles": ["sample-existing"],
            "caller_access": "Not established", "target_binding": "Not established",
            "evidence": ["invented-source"], "gaps": ["Access unproved"],
            "next_check": "Prepare an access check",
        }],
    }


class CatalogCommandTests(unittest.TestCase):
    def invoke(self, command, catalog, *extra):
        return self.invoke_text(command, json.dumps(catalog), *extra)

    def invoke_text(self, command, contents, *extra):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(contents, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(COMMAND), command, str(path), *extra],
                capture_output=True, text=True, timeout=10,
            )

    def test_valid_source_catalog_is_accepted_without_qualifying_it(self):
        result = self.invoke("validate", specimen())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("metadata", result.stdout)

    def test_unknown_fabric_reference_has_a_record_diagnostic(self):
        catalog = specimen()
        catalog["profiles"][0]["fabric"] = "missing-fabric"
        result = self.invoke("validate", catalog)
        self.assertEqual(result.returncode, 1)
        self.assertIn("profiles[0].fabric", result.stderr)
        self.assertIn("missing-fabric", result.stderr)

    def test_malformed_record_is_a_diagnostic_instead_of_a_traceback(self):
        for field, invalid in [("consent", []), ("fabric", []), ("claims", [None])]:
            with self.subTest(field=field):
                catalog = specimen()
                catalog["profiles"][0][field] = invalid
                result = self.invoke("validate", catalog)
                self.assertEqual(result.returncode, 1)
                self.assertIn("profiles[0]." + field, result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_duplicate_endpoint_identity_is_rejected(self):
        catalog = specimen()
        catalog["endpoints"][1]["id"] = "caller"
        result = self.invoke("validate", catalog)
        self.assertEqual(result.returncode, 1)
        self.assertIn("duplicate", result.stderr)
        self.assertIn("caller", result.stderr)

    def test_dangling_direction_dependency_and_evidence_are_rejected(self):
        cases = [("channels", "source", "missing-endpoint"),
                 ("fabrics", "dependencies", ["missing-dependency"]),
                 ("endpoints", "evidence", ["missing-evidence"]),
                 ("profiles", "channel", "missing-channel")]
        for collection, field, invalid in cases:
            with self.subTest(collection=collection, field=field):
                catalog = specimen()
                catalog[collection][0][field] = invalid
                result = self.invoke("validate", catalog)
                self.assertEqual(result.returncode, 1)
                self.assertIn(collection + "[0]." + field, result.stderr)

    def test_evidence_requires_a_dated_identity(self):
        for field, invalid in [("observed_at", "2026-01-01"),
                               ("sha256", "not-a-digest"), ("revision", None)]:
            with self.subTest(field=field):
                catalog = specimen()
                evidence = catalog["evidence"][0]
                if invalid is None:
                    del evidence[field]
                else:
                    evidence[field] = invalid
                result = self.invoke("validate", catalog)
                self.assertEqual(result.returncode, 1)
                self.assertIn("evidence[0]", result.stderr)

    def test_contract_vocabulary_rejects_unknown_populations_and_milestones(self):
        for field, invalid in [("population", "user-owned"), ("target_input", "title")]:
            with self.subTest(field=field):
                catalog = specimen()
                catalog["profiles"][0][field] = invalid
                result = self.invoke("validate", catalog)
                self.assertEqual(result.returncode, 1)
                self.assertIn(field, result.stderr)
        catalog = specimen()
        catalog["profiles"][0]["claims"][0]["milestone"] = "fulfilled"
        result = self.invoke("validate", catalog)
        self.assertEqual(result.returncode, 1)
        self.assertIn("milestone", result.stderr)

    def test_qualification_needs_live_evidence_and_its_own_direction(self):
        catalog = specimen()
        profile = catalog["profiles"][0]
        profile["channel"] = "caller-to-receiver"
        profile["claims"][0]["stage"] = "qualified"
        result = self.invoke("validate", catalog)
        self.assertEqual(result.returncode, 1)
        self.assertIn("live", result.stderr)
        catalog["evidence"][0]["kind"] = "live"
        profile["channel"] = None
        result = self.invoke("validate", catalog)
        self.assertEqual(result.returncode, 1)
        self.assertIn("channel", result.stderr)

    def test_metadata_values_have_declared_meanings(self):
        cases = [("evidence", "kind", "attested"), ("fabrics", "role", "full"),
                 ("fabrics", "status", "done"), ("endpoints", "wave", 4),
                 ("endpoints", "id", "Opaque ID")]
        for collection, field, invalid in cases:
            with self.subTest(collection=collection, field=field):
                catalog = specimen()
                catalog[collection][0][field] = invalid
                result = self.invoke("validate", catalog)
                self.assertEqual(result.returncode, 1)
                self.assertIn(field, result.stderr)
        for field, invalid in [("stage", "complete"), ("coverage", "100%"),
                               ("outcome", "success")]:
            with self.subTest(field=field):
                catalog = specimen()
                catalog["profiles"][0]["claims"][0][field] = invalid
                result = self.invoke("validate", catalog)
                self.assertEqual(result.returncode, 1)
                self.assertIn(field, result.stderr)

    def test_existing_target_cannot_claim_its_creation(self):
        catalog = specimen()
        catalog["profiles"][0]["claims"][0].update(operation="create-task", milestone="addressable")
        result = self.invoke("validate", catalog)
        self.assertEqual(result.returncode, 1)
        self.assertIn("existing", result.stderr)
        self.assertIn("creation", result.stderr)

    def test_profile_cannot_transfer_a_bound_claim_to_another_direction(self):
        catalog = specimen()
        reverse = dict(catalog["channels"][0], id="receiver-to-caller", source="receiver", target="caller")
        catalog["channels"].append(reverse)
        catalog["profiles"][0]["channel"] = "caller-to-receiver"
        result = self.invoke("validate", catalog)
        self.assertEqual(result.returncode, 1)
        self.assertIn("receiver-to-caller", result.stderr)
        self.assertIn("bound", result.stderr)

    def test_direction_is_unique_and_excludes_self_pairs(self):
        catalog = specimen()
        catalog["channels"].append(dict(catalog["channels"][0], id="same-direction"))
        result = self.invoke("validate", catalog)
        self.assertEqual(result.returncode, 1)
        self.assertIn("duplicate direction", result.stderr)
        catalog["channels"] = catalog["channels"][:1]
        catalog["channels"][0]["target"] = "caller"
        result = self.invoke("validate", catalog)
        self.assertEqual(result.returncode, 1)
        self.assertIn("self", result.stderr)

    def test_fabric_hierarchy_and_composition_cycles_are_rejected(self):
        for field in ("parent", "dependencies"):
            with self.subTest(field=field):
                catalog = specimen()
                first = catalog["fabrics"][0]
                second = dict(first, id="second-inbox")
                catalog["fabrics"].append(second)
                first[field] = "second-inbox" if field == "parent" else ["second-inbox"]
                second[field] = "sample-inbox" if field == "parent" else ["sample-inbox"]
                result = self.invoke("validate", catalog)
                self.assertEqual(result.returncode, 1)
                self.assertIn("cycle", result.stderr)

    def test_graph_and_matrix_share_directions_without_inheriting_reverse_support(self):
        result = self.invoke("project", specimen())
        self.assertEqual(result.returncode, 0, result.stderr)
        view = json.loads(result.stdout)
        self.assertEqual(view["counts"]["potential_channels"], 2)
        self.assertEqual(view["counts"]["associated_channels"], 1)
        arcs = {(arc["source"], arc["target"]): arc["id"] for arc in view["graph"]["arcs"]}
        for row in view["matrix"]["rows"]:
            for cell in row["cells"]:
                if row["source"] == cell["target"]:
                    self.assertIsNone(cell["channel"])
                else:
                    self.assertEqual(cell["channel"], arcs[(row["source"], cell["target"])])
        reverse = next(channel for channel in view["channels"] if channel["source"] == "receiver")
        self.assertEqual(reverse["fabrics"], [])
        self.assertEqual(reverse["association"], "unassessed")

    def test_view_keeps_mixed_progress_and_populations_separate(self):
        catalog = specimen()
        catalog["evidence"].append(dict(catalog["evidence"][0], id="invented-live", kind="live"))
        controlled = dict(catalog["profiles"][0], id="sample-controlled", population="controlled",
                          channel="caller-to-receiver", target_input="creation-contract")
        controlled["claims"] = [
            {"operation": "create-task", "milestone": "addressable", "stage": "qualified",
             "coverage": "proved", "evidence": ["invented-live"], "limits": ["Invented metadata only"]},
            {"operation": "continue-task", "milestone": "same-task-context", "stage": "prototyped",
             "coverage": "partial", "evidence": ["invented-source"], "outcome": "unknown",
             "limits": ["Unresolved context evidence"]},
        ]
        catalog["profiles"].append(controlled)
        catalog["channels"][0]["profiles"].append("sample-controlled")
        result = self.invoke("project", catalog)
        self.assertEqual(result.returncode, 0, result.stderr)
        profiles = {profile["id"]: profile for profile in json.loads(result.stdout)["profiles"]}
        self.assertEqual(profiles["sample-existing"]["operations"]["create-task"], [])
        operations = profiles["sample-controlled"]["operations"]
        self.assertEqual(operations["create-task"][0]["stage"], "qualified")
        self.assertEqual(operations["continue-task"][0]["outcome"], "unknown")
        self.assertEqual(operations["inspect"], [])

    def test_wave_filter_limits_navigation_and_keeps_supporting_candidates(self):
        result = self.invoke("project", specimen(), "--through-wave", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        view = json.loads(result.stdout)
        self.assertEqual(view["counts"]["endpoints"], 1)
        self.assertEqual(view["counts"]["associated_channels"], 0)
        self.assertEqual(view["graph"]["arcs"], [])
        self.assertEqual([fabric["id"] for fabric in view["fabrics"]], ["sample-inbox"])

    def test_unreadable_json_never_emits_a_partial_projection(self):
        duplicate = json.dumps(specimen()).replace('"schema_version": 1', '"schema_version": 0, "schema_version": 1')
        for contents in ("{", duplicate):
            with self.subTest(contents=contents[:50]):
                result = self.invoke_text("project", contents)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertNotIn("Traceback", result.stderr)
                self.assertIn("intake", result.stderr)

    def test_public_evidence_pointers_and_costs_are_well_formed(self):
        for uri in ("/private/task.json", "file:///private/task.json", "https://user:secret@example.org/source"):
            with self.subTest(uri=uri):
                catalog = specimen()
                catalog["evidence"][0]["uri"] = uri
                result = self.invoke("validate", catalog)
                self.assertEqual(result.returncode, 1)
                self.assertIn("uri", result.stderr)
        for minutes in (-1, float("nan"), float("inf")):
            with self.subTest(minutes=minutes):
                catalog = specimen()
                catalog["fabrics"][0]["effort"]["active_minutes"] = minutes
                result = self.invoke("validate", catalog)
                self.assertEqual(result.returncode, 1)

    def test_linked_profile_names_its_fabric_and_is_visible_on_its_bound_channel(self):
        catalog = specimen()
        catalog["channels"][0]["fabrics"] = []
        result = self.invoke("validate", catalog)
        self.assertEqual(result.returncode, 1)
        self.assertIn("fabric", result.stderr)
        catalog = specimen()
        catalog["profiles"][0]["channel"] = "caller-to-receiver"
        catalog["channels"][0]["profiles"] = []
        result = self.invoke("validate", catalog)
        self.assertEqual(result.returncode, 1)
        self.assertIn("listed", result.stderr)

    def test_claims_and_dispositions_retain_their_evidence_and_limits(self):
        for field in ("evidence", "limits"):
            with self.subTest(field=field):
                catalog = specimen()
                catalog["profiles"][0]["claims"][0][field] = []
                result = self.invoke("validate", catalog)
                self.assertEqual(result.returncode, 1)
                self.assertIn(field, result.stderr)
        catalog = specimen()
        catalog["fabrics"][0]["status"] = "unsuitable"
        catalog["fabrics"][0]["gaps"] = []
        result = self.invoke("validate", catalog)
        self.assertEqual(result.returncode, 1)
        self.assertIn("reason", result.stderr)
        catalog = specimen()
        catalog["fabrics"][0]["compatibility"]["status"] = "incompatible"
        result = self.invoke("validate", catalog)
        self.assertEqual(result.returncode, 1)
        self.assertIn("compatibility", result.stderr)


    def test_oversized_intake_stops_with_a_named_limit(self):
        result = self.invoke_text("project", " " * (8 * 1024 * 1024) + "{}")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("8 MiB", result.stderr)


    def test_invalid_url_syntax_is_a_field_diagnostic(self):
        catalog = specimen()
        catalog["evidence"][0]["uri"] = "https://["
        result = self.invoke("validate", catalog)
        self.assertEqual(result.returncode, 1)
        self.assertIn("evidence[0].uri", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


    def test_nonfinite_json_cannot_make_the_generated_view_unreadable(self):
        catalog = specimen()
        catalog["provenance"] = {"value": float("nan")}
        result = self.invoke("project", catalog)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("intake", result.stderr)


    def test_projection_is_reproducible_and_pins_exact_input_bytes(self):
        compact = json.dumps(specimen())
        first = self.invoke_text("project", compact)
        second = self.invoke_text("project", compact)
        pretty = self.invoke_text("project", json.dumps(specimen(), indent=2))
        for result in (first, second, pretty):
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(first.stdout, second.stdout)
        compact_view = json.loads(first.stdout)
        pretty_view = json.loads(pretty.stdout)
        self.assertEqual(compact_view["graph"], pretty_view["graph"])
        self.assertEqual(compact_view["matrix"], pretty_view["matrix"])
        self.assertNotEqual(compact_view["source_sha256"], pretty_view["source_sha256"])
        self.assertEqual(compact_view["snapshot"]["generated_at"], "2026-01-01T00:00:00Z")

    def test_large_finite_integer_effort_does_not_crash_validation(self):
        catalog = specimen()
        catalog["fabrics"][0]["effort"]["active_minutes"] = 10 ** 400
        result = self.invoke("project", catalog)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["fabrics"][0]["effort"]["active_minutes"], 10 ** 400)

    def test_archived_source_vectors_have_six_declared_symbols(self):
        for vector in ("K", "KKKKKKK", "success"):
            with self.subTest(vector=vector):
                catalog = specimen()
                catalog["profiles"][0]["source_assessment"] = {
                    "vector": vector, "evidence": ["invented-source"],
                    "limits": ["Historical vocabulary only"],
                }
                result = self.invoke("validate", catalog)
                self.assertEqual(result.returncode, 1)
                self.assertIn("source_assessment.vector", result.stderr)

    def test_dated_source_vector_stays_archived_instead_of_a_positive_claim(self):
        catalog = specimen()
        catalog["profiles"][0]["claims"] = []
        catalog["profiles"][0]["source_assessment"] = {
            "vector": "SS–SPS", "evidence": ["invented-source"],
            "limits": ["Historical source declaration only"],
        }
        result = self.invoke("project", catalog)
        self.assertEqual(result.returncode, 0, result.stderr)
        profile = json.loads(result.stdout)["profiles"][0]
        self.assertEqual(profile["source_assessment"]["vector"], "SS–SPS")
        self.assertTrue(all(not claims for claims in profile["operations"].values()))


if __name__ == "__main__":
    unittest.main()
