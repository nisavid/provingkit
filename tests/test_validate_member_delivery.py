from __future__ import annotations

import json
import hashlib
import copy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR = REPOSITORY / "scripts" / "validate_member_delivery.py"
PREPARED_SCHEMA = REPOSITORY / "tests/fixtures/member_delivery/prepared-admission-schema.json"
COMPLETE_RECORD = REPOSITORY / "tests/fixtures/member_delivery/constructed-complete-record.json"


class NonpassingPreservationCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.prepared = Path(self.temporary.name)
        self.inputs = self.prepared / "inputs"
        self.inputs.mkdir()
        self.records: dict[str, dict[str, object]] = {}
        self.expected_dependencies = {"baseline-statement": "missing"}
        self.add_record("admission-request", b'{"purpose":"constructed example"}\n')
        self.add_record("reviewed-contract", b"Constructed contract bytes.\n")
        self.add_record("prepared-schema", PREPARED_SCHEMA.read_bytes())
        self.response = {
            "schema": "provingkit-host-preservation-admission-prepared-v1",
            "contract_status": "prepared-not-adopted",
            "record_origin": "constructed",
            "reviewed_contract": self.reference("reviewed-contract"),
            "admission_request": self.reference("admission-request"),
            "observed_at": "2026-10-17T05:00:00+00:00",
            "outcome": "missing-evidence",
            "claim": "no-preservation-correspondence",
            "known_records": [self.reference(name) for name in self.records],
            "dependencies": [{
                "dependency": "baseline-statement",
                "state": "missing",
                "reason": "The constructed example has no baseline statement.",
            }],
            "reason": "Baseline evidence is missing.",
        }

    def add_record(self, name: str, content: bytes) -> None:
        (self.inputs / name).write_bytes(content)
        self.records[name] = {
            "path": name,
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }

    def reference(self, name: str) -> dict[str, object]:
        return {"logical_name": name, **{
            key: self.records[name][key] for key in ("bytes", "sha256")
        }}

    def use_complete_response(self) -> None:
        self.response = json.loads(COMPLETE_RECORD.read_text())
        self.response["producer_contract"] = self.reference("reviewed-contract")
        self.response["currentness"]["admission_request"] = self.reference("admission-request")
        for name in ("subject", "baseline"):
            logical_name = name + "-statement"
            self.add_record(logical_name, (json.dumps(self.response[name]["statement"]) + "\n").encode())
            self.response[name]["record"] = self.reference(logical_name)
        self.expected_dependencies = {"original-owner-decision": "unavailable"}

    def test_complete_statement_consistency_does_not_establish_admission(self) -> None:
        self.use_complete_response()

        result, report = self.invoke()

        self.assertEqual((result.returncode, report["outcome"], report["established_claims"]),
                         (2, "incomplete", []), report)

    def test_complete_response_cannot_substitute_a_different_raw_statement(self) -> None:
        for field in ("subject", "baseline"):
            with self.subTest(statement=field):
                self.use_complete_response()
                changed = copy.deepcopy(self.response[field]["statement"])
                if field == "subject":
                    changed["delivery_commit"] = "c" * 40
                else:
                    changed["id"] = "another-constructed-baseline"
                name = field + "-statement"
                self.add_record(name, (json.dumps(changed) + "\n").encode())
                self.response[field]["record"] = self.reference(name)

                result, report = self.invoke()

                self.assertEqual((result.returncode, report["outcome"], report["established_claims"]),
                                 (1, "rejected", []), report)
                self.assertIn(field + " statement", report["checks"][0]["reason"])

    def test_raw_statement_boolean_cannot_replace_a_number(self) -> None:
        self.use_complete_response()
        changed = copy.deepcopy(self.response["subject"]["statement"])
        changed["route_contract"]["bytes"] = True
        self.add_record("subject-statement", (json.dumps(changed) + "\n").encode())
        self.response["subject"]["record"] = self.reference("subject-statement")

        result, report = self.invoke()

        self.assertEqual((result.returncode, report["outcome"], report["established_claims"]),
                         (1, "rejected", []), report)
        self.assertIn("subject statement", report["checks"][0]["reason"])

    def test_unequal_decimal_tokens_cannot_round_to_the_same_statement_value(self) -> None:
        for changed_record in ("raw statement", "response"):
            with self.subTest(record=changed_record):
                self.use_complete_response()
                if changed_record == "raw statement":
                    content = json.dumps(self.response["subject"]["statement"]).encode()
                    content = content.replace(b'"bytes": 1,', b'"bytes": 1.0000000000000001,', 1)
                    self.add_record("subject-statement", content)
                    self.response["subject"]["record"] = self.reference("subject-statement")
                    response_bytes = None
                else:
                    response_bytes = json.dumps(self.response).encode().replace(
                        b'"bytes": 1,', b'"bytes": 1.0000000000000001,', 1,
                    )

                result, report = self.invoke(response_bytes)

                self.assertEqual((result.returncode, report["outcome"], report["established_claims"]),
                                 (1, "rejected", []), report)

    def test_equivalent_decimal_response_values_pass_shape_without_admission(self) -> None:
        self.use_complete_response()
        self.response["subject"]["statement"]["route_contract"]["bytes"] = 1.0

        result, report = self.invoke()

        self.assertEqual((result.returncode, report["outcome"], report["established_claims"]),
                         (2, "incomplete", []), report)

    def test_nonpassing_decimal_byte_counts_remain_nonpassing(self) -> None:
        for record in self.response["known_records"]:
            record["bytes"] = float(record["bytes"])

        result, report = self.invoke()

        self.assertEqual((result.returncode, report["outcome"], report["established_claims"]),
                         (2, "incomplete", []), report)
        self.assertEqual(report["preservation_response"]["outcome"], "missing-evidence")

    def test_statement_numbers_outside_parser_range_are_rejected(self) -> None:
        for changed_record in ("raw statement", "response"):
            with self.subTest(record=changed_record):
                self.use_complete_response()
                if changed_record == "raw statement":
                    content = json.dumps(self.response["subject"]["statement"]).encode().replace(
                        b'"bytes": 1,', b'"bytes": 1e9999999999999999999,', 1,
                    )
                    self.add_record("subject-statement", content)
                    self.response["subject"]["record"] = self.reference("subject-statement")
                    response_bytes = None
                else:
                    response_bytes = json.dumps(self.response).encode().replace(
                        b'"bytes": 1,', b'"bytes": 1e9999999999999999999,', 1,
                    )

                result, report = self.invoke(response_bytes)

                self.assertEqual((result.returncode, report["outcome"], report["established_claims"]),
                                 (1, "rejected", []), report)
                self.assertIn("numeric range", report["checks"][0]["reason"])

    def test_equivalent_statement_formatting_does_not_establish_admission(self) -> None:
        self.use_complete_response()
        equivalent = copy.deepcopy(self.response["subject"]["statement"])
        equivalent["route_contract"]["bytes"] = 1.0
        self.add_record("subject-statement", (json.dumps(equivalent, sort_keys=True, indent=2) + "\n").encode())
        self.response["subject"]["record"] = self.reference("subject-statement")

        result, report = self.invoke()

        self.assertEqual((result.returncode, report["outcome"], report["established_claims"]),
                         (2, "incomplete", []), report)

    def test_complete_references_must_match_the_caller_input_identities(self) -> None:
        for field in ("producer_contract", "admission_request", "subject", "baseline"):
            with self.subTest(reference=field):
                self.use_complete_response()
                if field == "admission_request":
                    reference = self.response["currentness"][field]
                elif field in ("subject", "baseline"):
                    reference = self.response[field]["record"]
                else:
                    reference = self.response[field]
                reference["sha256"] = "0" * 64

                result, report = self.invoke()

                self.assertEqual((result.returncode, report["outcome"], report["established_claims"]),
                                 (1, "rejected", []), report)
                self.assertIn("different", report["checks"][0]["reason"])

    def test_raw_statements_require_strict_json(self) -> None:
        self.use_complete_response()
        original = json.dumps(self.response["subject"]["statement"]).encode()
        duplicate = original.replace(b'"changed_member": "mergecraft"',
                                     b'"changed_member": "mergecraft", "changed_member": "mergecraft"')
        for content in (duplicate, b"NaN", b"\xff", b'{"unfinished":'):
            with self.subTest(content=content):
                self.use_complete_response()
                self.add_record("subject-statement", content)
                self.response["subject"]["record"] = self.reference("subject-statement")

                result, report = self.invoke()

                self.assertEqual((result.returncode, report["outcome"], report["established_claims"]),
                                 (1, "rejected", []), report)
                self.assertIn("raw subject statement must contain valid JSON", report["checks"][0]["reason"])

    def test_missing_statement_stays_named_and_incomplete(self) -> None:
        self.use_complete_response()
        (self.inputs / "subject-statement").unlink()

        result, report = self.invoke()

        self.assertEqual((result.returncode, report["outcome"], report["established_claims"]),
                         (2, "incomplete", []), report)
        self.assertIn("subject-statement", report["checks"][0]["reason"])

    def test_missing_statement_cannot_hide_another_statement_contradiction(self) -> None:
        self.use_complete_response()
        (self.inputs / "subject-statement").unlink()
        self.response["baseline"]["statement"]["id"] = "a-different-statement"

        result, report = self.invoke()

        self.assertEqual((result.returncode, report["outcome"], report["established_claims"]),
                         (1, "rejected", []), report)
        self.assertIn("baseline statement", report["checks"][0]["reason"])

    def invoke(self, response_bytes: bytes | None = None) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
        if response_bytes is None:
            response_bytes = (json.dumps(self.response) + "\n").encode()
        self.add_record("owner-response", response_bytes)
        request = self.prepared / "request.json"
        request.write_text(json.dumps({
            "schema_version": "provingkit-member-delivery-request-v1",
            "preservation": {
                "response": "owner-response",
                "admission_request": "admission-request",
                "reviewed_contract": "reviewed-contract",
                "schema": "prepared-schema",
                "inputs": self.records,
                "expected_dependencies": self.expected_dependencies,
            },
        }))
        output = self.prepared / "result.json"
        result = subprocess.run(
            [sys.executable, "-I", "-B", str(VALIDATOR),
             "--request", str(request), "--inputs", str(self.inputs),
             "--output", str(output)],
            cwd=REPOSITORY, text=True, capture_output=True, check=False, timeout=20,
        )
        self.assertTrue(output.is_file(), result.stderr)
        return result, json.loads(output.read_text())

    def test_bound_missing_evidence_response_stays_nonpassing(self) -> None:
        result, report = self.invoke()

        self.assertEqual(
            (result.returncode, report["outcome"], report["established_claims"]),
            (2, "incomplete", []),
        )
        self.assertEqual(report.get("preservation_response"), {
            "record_origin": "constructed",
            "outcome": "missing-evidence",
            "claim": "no-preservation-correspondence",
            "observed_at": "2026-10-17T05:00:00+00:00",
            "dependencies": self.response["dependencies"],
            "reason": "Baseline evidence is missing.",
        }, report)

    def test_mixed_response_cannot_use_the_unimplemented_complete_branch(self) -> None:
        self.response["claim"] = "correspondence-to-owner-admitted-observation-at-capture"
        del self.response["outcome"]

        result, report = self.invoke()

        self.assertEqual(
            (result.returncode, report["outcome"], report["established_claims"]),
            (1, "rejected", []), report,
        )

    def test_reported_unavailability_remains_data_without_admission(self) -> None:
        self.response["record_origin"] = "owner-reported"
        self.response["outcome"] = "unavailable"
        self.response["dependencies"][0]["state"] = "unavailable"
        self.expected_dependencies = {"baseline-statement": "unavailable"}

        result, report = self.invoke()

        self.assertEqual((result.returncode, report["outcome"], report["established_claims"]),
                         (2, "incomplete", []))
        self.assertEqual(report["preservation_response"]["record_origin"], "owner-reported")
        self.assertEqual(report["preservation_response"]["outcome"], "unavailable")

    def test_changed_input_bytes_are_rejected(self) -> None:
        (self.inputs / "admission-request").write_bytes(b'{"purpose":"different"}\n')

        result, report = self.invoke()

        self.assertEqual((result.returncode, report["outcome"], report["established_claims"]),
                         (1, "rejected", []))
        self.assertIn("Input bytes differ", report["checks"][0]["reason"])

    def test_request_and_contract_bindings_must_match_caller_identities(self) -> None:
        original = copy.deepcopy(self.response)
        for field in ("admission_request", "reviewed_contract"):
            with self.subTest(binding=field):
                self.response = copy.deepcopy(original)
                self.response[field]["sha256"] = "0" * 64
                result, report = self.invoke()
                self.assertEqual((result.returncode, report["outcome"], report["established_claims"]),
                                 (1, "rejected", []))
                self.assertIn("bound to a different", report["checks"][0]["reason"])

    def test_known_records_preserve_the_entire_supplied_identity_set(self) -> None:
        records = self.response["known_records"]
        cases = {
            "omitted known schema": records[:-1],
            "duplicate logical name": records + [records[0]],
            "unknown record": records + [{"logical_name": "unexpected", "bytes": 0, "sha256": "0" * 64}],
            "wrong known hash": [*records[:-1], {**records[-1], "sha256": "0" * 64}],
        }
        for label, known in cases.items():
            with self.subTest(records=label):
                self.response["known_records"] = known
                result, report = self.invoke()
                self.assertEqual((result.returncode, report["outcome"], report["established_claims"]),
                                 (1, "rejected", []))

    def test_malformed_response_bytes_are_rejected_without_claims(self) -> None:
        for content in (b'{"claim":', b'{"claim":null,"claim":null}', b"NaN", b"\xff"):
            with self.subTest(content=content):
                result, report = self.invoke(content)
                self.assertEqual((result.returncode, report["outcome"], report["established_claims"]),
                                 (1, "rejected", []))

    def test_dependency_states_and_declared_outcome_must_agree(self) -> None:
        original = copy.deepcopy(self.response)
        changes = (
            {"outcome": "unavailable"},
            {"dependencies": [{"dependency": "subject-statement", "state": "missing", "reason": "Absent."}]},
            {"dependencies": [*original["dependencies"], {"dependency": "baseline-statement", "state": "unavailable", "reason": "Unavailable."}]},
        )
        for change in changes:
            with self.subTest(change=change):
                self.response = {**original, **change}
                result, report = self.invoke()
                self.assertEqual((result.returncode, report["outcome"], report["established_claims"]),
                                 (1, "rejected", []))

    def test_known_inaccessible_file_stays_named_and_incomplete(self) -> None:
        self.add_record("export", b"Constructed unavailable export.\n")
        self.response["known_records"].append(self.reference("export"))
        (self.inputs / "export").unlink()
        self.response["dependencies"].append({"dependency": "export-records", "state": "unavailable", "reason": "The known export cannot be read."})
        self.expected_dependencies["export-records"] = "unavailable"

        result, report = self.invoke()

        self.assertEqual((result.returncode, report["outcome"], report["established_claims"]),
                         (2, "incomplete", []))
        self.assertEqual(report["preservation_response"]["outcome"], "missing-evidence")
        self.assertIn("export", report["checks"][-1]["reason"])

    def test_timestamp_requires_a_real_date_and_explicit_offset(self) -> None:
        for timestamp in ("2026-02-30T05:00:00Z", "2026-10-17T05:00:00", "2026-10-17 05:00:00Z", "2026-10-17T25:00:00Z"):
            with self.subTest(timestamp=timestamp):
                self.response["observed_at"] = timestamp
                result, report = self.invoke()
                self.assertEqual((result.returncode, report["outcome"], report["established_claims"]),
                                 (1, "rejected", []))

    def test_unresolvable_input_returns_missing_evidence(self) -> None:
        path = self.inputs / "admission-request"
        path.unlink()
        path.symlink_to("admission-request")

        result, report = self.invoke()

        self.assertEqual((result.returncode, report["outcome"], report["established_claims"]),
                         (2, "incomplete", []))
        self.assertTrue(any(check["outcome"] == "missing" and "admission-request" in check["reason"]
                            for check in report["checks"]), report)

    def test_a_different_schema_cannot_redefine_the_supported_response(self) -> None:
        self.add_record("prepared-schema", b'{"type":"object"}\n')
        self.response["known_records"][-1] = self.reference("prepared-schema")

        result, report = self.invoke()

        self.assertEqual((result.returncode, report["outcome"], report["established_claims"]),
                         (1, "rejected", []))
        self.assertIn("not the supported prepared schema", report["checks"][0]["reason"])

    def test_closed_response_shape_rejects_unrelated_acceptance_fields(self) -> None:
        self.response["accepted"] = True

        result, report = self.invoke()

        self.assertEqual((result.returncode, report["outcome"], report["established_claims"]),
                         (1, "rejected", []))

    def test_missing_request_cannot_mask_a_response_shape_contradiction(self) -> None:
        (self.inputs / "admission-request").unlink()
        self.response["accepted"] = True

        result, report = self.invoke()

        self.assertEqual((result.returncode, report["outcome"], report["established_claims"]),
                         (1, "rejected", []), report)

    def test_missing_schema_or_contract_cannot_mask_a_shape_contradiction(self) -> None:
        self.response["accepted"] = True
        for name in ("prepared-schema", "reviewed-contract"):
            with self.subTest(unavailable=name):
                path = self.inputs / name
                original = path.read_bytes()
                path.unlink()
                try:
                    result, report = self.invoke()
                finally:
                    path.write_bytes(original)
                self.assertEqual((result.returncode, report["outcome"], report["established_claims"]),
                                 (1, "rejected", []), report)

    def test_missing_request_cannot_mask_binding_or_dependency_contradictions(self) -> None:
        (self.inputs / "admission-request").unlink()
        original = copy.deepcopy(self.response)
        cases = (
            {"admission_request": {**original["admission_request"], "sha256": "0" * 64}},
            {"dependencies": [{"dependency": "subject-statement", "state": "missing", "reason": "Absent."}]},
        )
        for change in cases:
            with self.subTest(change=change):
                self.response = {**original, **change}
                result, report = self.invoke()
                self.assertEqual((result.returncode, report["outcome"], report["established_claims"]),
                                 (1, "rejected", []), report)

    def test_well_formed_response_with_a_missing_prerequisite_stays_incomplete(self) -> None:
        for name in ("admission-request", "reviewed-contract", "prepared-schema"):
            with self.subTest(unavailable=name):
                path = self.inputs / name
                original = path.read_bytes()
                path.unlink()
                try:
                    result, report = self.invoke()
                finally:
                    path.write_bytes(original)
                self.assertEqual((result.returncode, report["outcome"], report["established_claims"]),
                                 (2, "incomplete", []), report)
                self.assertTrue(any(check["outcome"] == "missing" and name in check["reason"]
                                    for check in report["checks"]), report)


class MemberDeliveryCliTests(unittest.TestCase):
    def test_request_integer_beyond_enabled_digit_limit_returns_rejected_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            prepared = Path(temporary)
            inputs = prepared / "inputs"
            inputs.mkdir()
            request = prepared / "request.json"
            request.write_bytes(b'{"schema_version":' + b"9" * 641 + b"}")
            output = prepared / "result.json"

            result = subprocess.run(
                [sys.executable, "-I", "-B", "-X", "int_max_str_digits=640", str(VALIDATOR),
                 "--request", str(request), "--inputs", str(inputs), "--output", str(output)],
                cwd=REPOSITORY, text=True, capture_output=True, check=False, timeout=20,
            )

            self.assertTrue(output.is_file(), result.stderr)
            report = json.loads(output.read_text())
            self.assertEqual((result.returncode, report["outcome"], report["established_claims"]),
                             (1, "rejected", []), report)
            self.assertEqual(report["checks"], [{
                "id": "request_content", "outcome": "invalid",
                "reason": "The request exceeds the supported JSON numeric range.",
            }])

    def test_request_number_outside_parser_range_returns_rejected_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            prepared = Path(temporary)
            inputs = prepared / "inputs"
            inputs.mkdir()
            request = prepared / "request.json"
            request.write_bytes(b'{"schema_version":1e9999999999999999999}')
            output = prepared / "result.json"

            result = subprocess.run(
                [sys.executable, "-I", "-B", str(VALIDATOR),
                 "--request", str(request), "--inputs", str(inputs), "--output", str(output)],
                cwd=REPOSITORY, text=True, capture_output=True, check=False, timeout=20,
            )

            self.assertTrue(output.is_file(), result.stderr)
            report = json.loads(output.read_text())
            self.assertEqual((result.returncode, report["outcome"], report["established_claims"]),
                             (1, "rejected", []), report)
            self.assertEqual(report["checks"], [{
                "id": "request_content", "outcome": "invalid",
                "reason": "The request exceeds the supported JSON numeric range.",
            }])

    def test_request_beyond_parser_nesting_limit_returns_rejected_evidence(self) -> None:
        requests = (
            ("closed deep arrays", b"[" * 100_000 + b"0" + b"]" * 100_000),
            ("unclosed deep arrays", b"[" * 100_000),
        )
        for label, content in requests:
            with self.subTest(request=label), tempfile.TemporaryDirectory() as temporary:
                prepared = Path(temporary)
                inputs = prepared / "inputs"
                inputs.mkdir()
                request = prepared / "request.json"
                request.write_bytes(content)
                output = prepared / "result.json"

                result = subprocess.run(
                    [
                        sys.executable,
                        "-I",
                        "-B",
                        str(VALIDATOR),
                        "--request",
                        str(request),
                        "--inputs",
                        str(inputs),
                        "--output",
                        str(output),
                    ],
                    cwd=REPOSITORY,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=20,
                )

                self.assertTrue(output.is_file(), result.stderr)
                report = json.loads(output.read_text())
                self.assertEqual(
                    (result.returncode, report["outcome"], report["established_claims"]),
                    (1, "rejected", []),
                )
                self.assertEqual(
                    report["checks"],
                    [{
                        "id": "request_content",
                        "outcome": "invalid",
                        "reason": "The request exceeds the JSON parser nesting limit.",
                    }],
                )

    def test_malformed_request_returns_rejected_evidence(self) -> None:
        requests = (
            ("unfinished value", b'{"schema_version":'),
            ("UTF-8 NULs", bytes([0, 91, 0, 93])),
            ("invalid UTF-8 octet", bytes([255])),
            ("NaN token", b"NaN"),
            ("positive infinity token", b"Infinity"),
            ("negative infinity token", b"-Infinity"),
            ("unclosed deep arrays", b"[" * 2048),
            ("unclosed arrays at byte boundary", b"[" * 4096),
        )
        for label, content in requests:
            with self.subTest(request=label), tempfile.TemporaryDirectory() as temporary:
                prepared = Path(temporary)
                inputs = prepared / "inputs"
                inputs.mkdir()
                request = prepared / "request.json"
                request.write_bytes(content)
                output = prepared / "result.json"

                result = subprocess.run(
                    [
                        sys.executable,
                        "-I",
                        "-B",
                        str(VALIDATOR),
                        "--request",
                        str(request),
                        "--inputs",
                        str(inputs),
                        "--output",
                        str(output),
                    ],
                    cwd=REPOSITORY,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=20,
                )

                self.assertTrue(output.is_file(), result.stderr)
                report = json.loads(output.read_text())
                self.assertEqual(
                    (
                        result.returncode,
                        report["outcome"],
                        report["established_claims"],
                    ),
                    (1, "rejected", []),
                )
                self.assertEqual(
                    (report["checks"][0]["id"], report["checks"][0]["outcome"]),
                    ("request_content", "invalid"),
                )
                self.assertTrue(report["checks"][0]["reason"])

    def test_duplicate_request_keys_return_rejected_evidence(self) -> None:
        requests = (
            ("root object", b'{"member":"mergecraft","member":"other"}'),
            ("nested object", b'{"evidence":{"sha256":"first","sha256":"second"}}'),
            ("identical values", b'{"member":"mergecraft","member":"mergecraft"}'),
            ("null first value", b'{"member":null,"member":"mergecraft"}'),
            ("false first value", b'{"member":false,"member":"mergecraft"}'),
            ("zero first value", b'{"member":0,"member":"mergecraft"}'),
            ("escaped equivalent key", br'{"member":"mergecraft","memb\u0065r":"other"}'),
        )
        for label, content in requests:
            with self.subTest(request=label), tempfile.TemporaryDirectory() as temporary:
                prepared = Path(temporary)
                inputs = prepared / "inputs"
                inputs.mkdir()
                request = prepared / "request.json"
                request.write_bytes(content)
                output = prepared / "result.json"

                result = subprocess.run(
                    [
                        sys.executable,
                        "-I",
                        "-B",
                        str(VALIDATOR),
                        "--request",
                        str(request),
                        "--inputs",
                        str(inputs),
                        "--output",
                        str(output),
                    ],
                    cwd=REPOSITORY,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=20,
                )

                self.assertTrue(output.is_file(), result.stderr)
                report = json.loads(output.read_text())
                self.assertEqual(
                    (result.returncode, report["outcome"], report["established_claims"]),
                    (1, "rejected", []),
                )
                self.assertEqual(
                    (report["checks"][0]["id"], report["checks"][0]["outcome"]),
                    ("request_content", "invalid"),
                )
                self.assertTrue(report["checks"][0]["reason"])

    def test_valid_json_keeps_validation_incomplete(self) -> None:
        requests = (
            (
                "independent object scopes",
                b'{"id":null,"items":[{"id":false},{"id":0}],'
                b'"left":{"id":""},"right":{"id":[]}}',
            ),
            (
                "UTF-8 text and escaped key",
                '{"text":"café 雪","memb\\u0065r":"mergecraft"}'.encode("utf-8"),
            ),
        )
        for label, content in requests:
            with self.subTest(request=label), tempfile.TemporaryDirectory() as temporary:
                prepared = Path(temporary)
                inputs = prepared / "inputs"
                inputs.mkdir()
                request = prepared / "request.json"
                request.write_bytes(content)
                output = prepared / "result.json"

                result = subprocess.run(
                    [
                        sys.executable,
                        "-I",
                        "-B",
                        str(VALIDATOR),
                        "--request",
                        str(request),
                        "--inputs",
                        str(inputs),
                        "--output",
                        str(output),
                    ],
                    cwd=REPOSITORY,
                    text=True,
                    capture_output=True,
                    check=False,
                    timeout=20,
                )

                self.assertTrue(output.is_file(), result.stderr)
                report = json.loads(output.read_text())
                self.assertEqual(
                    (result.returncode, report["outcome"], report["established_claims"]),
                    (2, "incomplete", []),
                )
                self.assertEqual(
                    (report["checks"][0]["id"], report["checks"][0]["outcome"]),
                    ("request_validation", "missing"),
                )
                self.assertTrue(report["checks"][0]["reason"])

    def test_missing_request_returns_incomplete_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            prepared = Path(temporary)
            inputs = prepared / "inputs"
            inputs.mkdir()
            output = prepared / "result.json"

            result = subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-B",
                    str(VALIDATOR),
                    "--request",
                    str(prepared / "missing.json"),
                    "--inputs",
                    str(inputs),
                    "--output",
                    str(output),
                ],
                cwd=REPOSITORY,
                text=True,
                capture_output=True,
                check=False,
                timeout=20,
            )

            self.assertTrue(output.is_file(), result.stderr)
            report = json.loads(output.read_text())
            self.assertEqual(
                (result.returncode, report["outcome"], report["established_claims"]),
                (2, "incomplete", []),
            )


if __name__ == "__main__":
    unittest.main()
