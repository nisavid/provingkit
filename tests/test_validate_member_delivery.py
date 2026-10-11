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
