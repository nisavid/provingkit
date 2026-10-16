"""Constructed record shapes; no semantic admission or live host observation."""

import copy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]


class HostPreservationAdmissionShapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(
            (ROOT / "release/host-preservation-admission/record.schema.json").read_text()
        )
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(
            cls.schema, format_checker=FormatChecker()
        )
        cls.fixture = json.loads(
            (ROOT / "tests/fixtures/host_preservation_admission/constructed-record.json")
            .read_text()
        )

    def setUp(self):
        self.record = copy.deepcopy(self.fixture)

    def test_constructed_record_is_representable(self):
        self.validator.validate(self.record)
        self.assertEqual(self.record["record_origin"], "constructed")

    def test_prepared_identity_cannot_claim_operational_adoption(self):
        for status in ("proposal-not-adopted", "adopted", "accepted"):
            with self.subTest(status=status):
                self.record["contract_status"] = status
                self.assertFalse(self.validator.is_valid(self.record))

    def test_missing_member_and_unknown_root_field_are_rejected(self):
        members = self.record["baseline"]["statement"]["member_states"]
        for member in tuple(members):
            with self.subTest(member=member):
                changed = copy.deepcopy(self.record)
                del changed["baseline"]["statement"]["member_states"][member]
                self.assertFalse(self.validator.is_valid(changed))
        self.record["admit_this_candidate"] = True
        self.assertFalse(self.validator.is_valid(self.record))

    def test_unavailable_cursor_coverage_is_representable(self):
        baseline = self.record["baseline"]["statement"]
        unavailable = {"state": "unavailable", "reason": "Constructed missing observation"}
        baseline["clients"]["cursor"]["evidence"] = unavailable
        for member in baseline["member_states"].values():
            member["projected_state"]["cursor"] = unavailable
        self.validator.validate(self.record)
        # Shape acceptance must remain separate from required coverage checks.

    def test_cursor_execution_scope_is_rejected(self):
        self.record["baseline"]["statement"]["clients"]["cursor"]["route_scope"] = (
            "preservation-and-proposed-execution"
        )
        self.assertFalse(self.validator.is_valid(self.record))

    def test_noncurrent_observations_are_representable(self):
        for status in ("withdrawn", "superseded", "unknown"):
            with self.subTest(status=status):
                self.record["currentness"].update(
                    status=status, observed_head=None, reason="Constructed branch"
                )
                self.validator.validate(self.record)

    def test_wrong_observation_time_type_and_bad_digest_are_rejected(self):
        self.record["currentness"]["observed_at"] = 42
        self.assertFalse(self.validator.is_valid(self.record))
        self.record = copy.deepcopy(self.fixture)
        self.record["baseline"]["record"]["sha256"] = "not-a-digest"
        self.assertFalse(self.validator.is_valid(self.record))

    def test_export_paths_cannot_escape_relative_input_map(self):
        for path in ("../EXPORT.json", "/EXPORT.json", "exports/../EXPORT.json", "a\\b"):
            with self.subTest(path=path):
                self.record["exports"][0]["relative_path"] = path
                self.assertFalse(self.validator.is_valid(self.record))

    def test_public_branch_does_not_accept_an_unbound_packet(self):
        self.validator.validate(self.record)
        self.record["public_transfer"] = {"status": "proposed-exact-packet"}
        self.assertFalse(self.validator.is_valid(self.record))

    def test_schema_does_not_claim_to_check_cross_record_correspondence(self):
        # Well-shaped unequal digests require the separately implemented semantic check.
        self.record["owner_decision"]["baseline_record_sha256"] = "b" * 64
        self.validator.validate(self.record)
        self.assertNotEqual(
            self.record["owner_decision"]["baseline_record_sha256"],
            self.record["baseline"]["record"]["sha256"],
        )

    def nonpassing_response(self, dependencies, outcome="missing-evidence"):
        return {
            "schema": self.fixture["schema"],
            "contract_status": "prepared-not-adopted",
            "record_origin": "constructed",
            "reviewed_contract": copy.deepcopy(self.fixture["producer_contract"]),
            "admission_request": copy.deepcopy(
                self.fixture["currentness"]["admission_request"]
            ),
            "observed_at": "2026-01-01T00:00:00Z",
            "outcome": outcome,
            "claim": "no-preservation-correspondence",
            "known_records": [],
            "dependencies": [
                {
                    "dependency": dependency,
                    "state": "missing" if outcome == "missing-evidence" else "unavailable",
                    "reason": "Constructed case: no observed file identity",
                }
                for dependency in dependencies
            ],
            "reason": "Required owner evidence could not be obtained",
        }

    def test_unknown_owner_evidence_has_a_nonpassing_response(self):
        for dependencies in (
            ["decision-source"],
            ["original-owner-decision"],
            ["decision-source", "original-owner-decision"],
        ):
            with self.subTest(dependencies=dependencies):
                response = self.nonpassing_response(dependencies)
                self.validator.validate(response)
                self.assertNotIn("owner_decision", response)
                self.assertNotIn("currentness", response)
                self.assertEqual(
                    response["admission_request"],
                    self.fixture["currentness"]["admission_request"],
                )

    def test_unavailable_identity_keeps_only_known_records(self):
        response = self.nonpassing_response(["decision-source"], "unavailable")
        response["known_records"] = [copy.deepcopy(self.fixture["baseline"]["record"])]
        self.validator.validate(response)

    def test_nonpassing_response_requires_request_contract_and_explanation(self):
        response = self.nonpassing_response(["decision-source"])
        for field in ("admission_request", "reviewed_contract", "outcome", "reason", "dependencies"):
            with self.subTest(field=field):
                incomplete = copy.deepcopy(response)
                del incomplete[field]
                self.assertFalse(self.validator.is_valid(incomplete))
        response["dependencies"] = []
        self.assertFalse(self.validator.is_valid(response))

    def test_nonpassing_response_cannot_claim_correspondence_or_mix_branches(self):
        for field, value in (
            ("outcome", "matches-admitted-observation-at-capture"),
            ("claim", "correspondence-to-owner-admitted-observation-at-capture"),
            ("owner_decision", self.fixture["owner_decision"]),
        ):
            with self.subTest(field=field):
                response = self.nonpassing_response(["original-owner-decision"])
                response[field] = value
                self.assertFalse(self.validator.is_valid(response))
        ambiguous = copy.deepcopy(self.fixture)
        ambiguous.update(self.nonpassing_response(["decision-source"]))
        self.assertFalse(self.validator.is_valid(ambiguous))


if __name__ == "__main__":
    unittest.main()
