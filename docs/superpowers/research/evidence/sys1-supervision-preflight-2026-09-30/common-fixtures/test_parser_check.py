"""Check the external parser oracle against reference and faulty programs."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent


class ParserCheckTests(unittest.TestCase):
    def check_program(self, path):
        return subprocess.run(
            [sys.executable, str(ROOT / "check_parser.py"), str(path)],
            capture_output=True, text=True, timeout=15,
        )

    def test_correct_reference_passes_the_literal_cases(self):
        result = self.check_program(ROOT / "reference" / "parser.py")
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertEqual(json.loads(result.stdout), {"accepted": True, "failed": []})

    def test_seed_has_two_independently_repairable_defects(self):
        seed = (ROOT / "task-input" / "parser.py").read_text(encoding="utf-8")
        cases = [
            ("both defects", seed, ["signed", "blank", "combined"]),
            ("sign fixed", seed.replace("abs(int(match[2]))", "int(match[2])"), ["blank", "combined"]),
            ("blanks fixed", seed.replace("        match =", "        if not line:\n            continue\n        match ="), ["signed", "combined"]),
        ]
        for label, source, expected_failures in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory(prefix="sys1-parser-oracle-") as scratch:
                program = Path(scratch) / "parser.py"
                program.write_text(source, encoding="utf-8")
                result = self.check_program(program)
                self.assertEqual(result.returncode, 1, result.stderr or result.stdout)
                self.assertEqual(json.loads(result.stdout), {"accepted": False, "failed": expected_failures})

    def test_rejects_dropped_or_reordered_rows(self):
        reference = (ROOT / "reference" / "parser.py").read_text(encoding="utf-8")
        for replacement in ("return records[:1]", "return sorted(records)"):
            with self.subTest(replacement=replacement), tempfile.TemporaryDirectory(prefix="sys1-parser-oracle-") as scratch:
                program = Path(scratch) / "parser.py"
                program.write_text(reference.replace("return records", replacement), encoding="utf-8")
                result = self.check_program(program)
                self.assertEqual(result.returncode, 1, result.stderr or result.stdout)
                self.assertIn("ordinary", json.loads(result.stdout)["failed"])

    def test_rejects_unrelated_crash_on_malformed_rows(self):
        reference = (ROOT / "reference" / "parser.py").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory(prefix="sys1-parser-oracle-") as scratch:
            program = Path(scratch) / "parser.py"
            program.write_text(reference.replace('raise ValueError("malformed measurement")', 'raise RuntimeError("malformed measurement")'), encoding="utf-8")
            result = self.check_program(program)
            self.assertEqual(result.returncode, 1, result.stderr or result.stdout)
            self.assertEqual(json.loads(result.stdout), {
                "accepted": False,
                "failed": ["malformed-value", "malformed-name", "malformed-delimiter"],
            })


if __name__ == "__main__":
    unittest.main()
