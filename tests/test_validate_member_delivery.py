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
    def test_malformed_request_returns_rejected_evidence(self) -> None:
        requests = (
            ("unfinished value", b'{"schema_version":'),
            ("UTF-8 NULs", bytes([0, 91, 0, 93])),
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
