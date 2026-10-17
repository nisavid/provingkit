from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR = REPOSITORY / "scripts" / "validate_member_delivery.py"


class MemberDeliveryCliTests(unittest.TestCase):
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
