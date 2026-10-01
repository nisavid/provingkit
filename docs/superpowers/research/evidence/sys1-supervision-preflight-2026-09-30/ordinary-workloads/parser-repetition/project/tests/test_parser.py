import json
from pathlib import Path
import subprocess
import sys
import unittest


PROGRAM = Path(__file__).resolve().parents[1] / "parser.py"


class MeasurementParserTests(unittest.TestCase):
    def parse(self, contents):
        result = subprocess.run(
            [sys.executable, "-I", str(PROGRAM)],
            input=contents, capture_output=True, text=True, timeout=2,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout)

    def test_preserves_record_order(self):
        self.assertEqual(self.parse("zulu=7\nalpha=3"), [["zulu", 7], ["alpha", 3]])

    def test_preserves_signed_values(self):
        self.assertEqual(self.parse("beta=-2"), [["beta", -2]])

    def test_ignores_blank_lines(self):
        self.assertEqual(self.parse("alpha=3\n\n \n"), [["alpha", 3]])

    def test_empty_input(self):
        self.assertEqual(self.parse(""), [])


if __name__ == "__main__":
    unittest.main()
