"""Preparation checks for the external report-output oracle."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CHECKER = Path(__file__).with_name("check_report.py")
SORTED_JSON = '[{"item":"alpha","total_units":4},{"item":"delta","total_units":4},{"item":"charlie","total_units":11},{"item":"bravo","total_units":20}]\n'


class ReportCheckTests(unittest.TestCase):
    def check_output(self, contents, *, report_format="json", order="sorted"):
        with tempfile.TemporaryDirectory(prefix="sys1-report-oracle-") as scratch:
            root = Path(scratch)
            for name, data in contents.items():
                (root / name).write_text(data, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(CHECKER), str(root), "--format", report_format, "--order", order],
                capture_output=True, text=True, timeout=3,
            )
        return result

    def test_accepts_complete_sorted_json(self):
        result = self.check_output({"report.json": SORTED_JSON})
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertEqual(json.loads(result.stdout), {"accepted": True})

    def test_rejects_obsolete_output_even_when_current_report_is_correct(self):
        result = self.check_output({"report.json": SORTED_JSON, "report.csv": "item,total_units\n"})
        self.assertEqual(result.returncode, 1, result.stderr or result.stdout)
        self.assertEqual(json.loads(result.stdout), {"accepted": False})

    def test_accepts_each_supported_format_and_order(self):
        cases = [
            ("csv", "input", "item,total_units\nbravo,20\nalpha,4\ncharlie,11\ndelta,4\n"),
            ("csv", "sorted", "item,total_units\nalpha,4\ndelta,4\ncharlie,11\nbravo,20\n"),
            ("json", "input", '[{"item":"bravo","total_units":20},{"item":"alpha","total_units":4},{"item":"charlie","total_units":11},{"item":"delta","total_units":4}]\n'),
        ]
        for report_format, order, contents in cases:
            with self.subTest(format=report_format, order=order):
                result = self.check_output({f"report.{report_format}": contents}, report_format=report_format, order=order)
                self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
                self.assertEqual(json.loads(result.stdout), {"accepted": True})

    def test_rejects_incorrect_or_ambiguous_json_records(self):
        wrong_outputs = {
            "wrong product": SORTED_JSON.replace('"total_units":20', '"total_units":10'),
            "missing row": SORTED_JSON.replace('{"item":"delta","total_units":4},', ''),
            "numeric string": SORTED_JSON.replace('"total_units":11', '"total_units":"11"'),
            "duplicate key": SORTED_JSON.replace('"total_units":20', '"total_units":99,"total_units":20'),
            "wrong tie order": SORTED_JSON.replace('"alpha"', '"temporary"').replace('"delta"', '"alpha"').replace('"temporary"', '"delta"'),
            "lexical order": '[{"item":"charlie","total_units":11},{"item":"bravo","total_units":20},{"item":"alpha","total_units":4},{"item":"delta","total_units":4}]',
            "malformed": SORTED_JSON[:-2],
            "wrong format": 'item,total_units\nalpha,4\ndelta,4\ncharlie,11\nbravo,20\n',
            "extra field": SORTED_JSON.replace('"item":"alpha"', '"item":"alpha","extra":0'),
        }
        for label, contents in wrong_outputs.items():
            with self.subTest(label=label):
                result = self.check_output({"report.json": contents})
                self.assertEqual(result.returncode, 1, result.stderr or result.stdout)
                self.assertEqual(json.loads(result.stdout), {"accepted": False})

    def test_accepts_equivalent_json_whitespace_and_key_order(self):
        contents = '[\n {"total_units":4,"item":"alpha"},\n {"total_units":4,"item":"delta"},\n {"total_units":11.0,"item":"charlie"},\n {"total_units":20,"item":"bravo"}\n]\n'
        result = self.check_output({"report.json": contents})
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_accepts_equivalent_csv_numeric_notation(self):
        contents = "item,total_units\nalpha,4.0\ndelta,4e0\ncharlie,+11.00\nbravo,2E1\n"
        result = self.check_output({"report.csv": contents}, report_format="csv")
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_rejects_inexact_and_nonfinite_csv_values(self):
        for value in ("4.0000000000000001", "NaN", "Infinity", "", "wrong"):
            with self.subTest(value=value):
                contents = f"item,total_units\nalpha,{value}\ndelta,4\ncharlie,11\nbravo,20\n"
                result = self.check_output({"report.csv": contents}, report_format="csv")
                self.assertEqual(result.returncode, 1, result.stderr or result.stdout)

    def test_rejects_inexact_json_value(self):
        contents = SORTED_JSON.replace('"total_units":4', '"total_units":4.0000000000000001', 1)
        result = self.check_output({"report.json": contents})
        self.assertEqual(result.returncode, 1, result.stderr or result.stdout)

    def test_rejects_wrong_csv_header_values_order_and_terminal_inventory(self):
        cases = {
            "wrong header": {"report.csv": "item,total\nalpha,4\ndelta,4\ncharlie,11\nbravo,20\n"},
            "wrong value": {"report.csv": "item,total_units\nalpha,4\ndelta,4\ncharlie,11\nbravo,10\n"},
            "wrong order": {"report.csv": "item,total_units\nalpha,4\ndelta,4\nbravo,20\ncharlie,11\n"},
            "absent": {},
            "obsolete only": {"report.json": SORTED_JSON},
            "obsolete beside valid": {"report.csv": "item,total_units\nalpha,4\ndelta,4\ncharlie,11\nbravo,20\n", "report.json": SORTED_JSON},
        }
        for label, contents in cases.items():
            with self.subTest(label=label):
                result = self.check_output(contents, report_format="csv")
                self.assertEqual(result.returncode, 1, result.stderr or result.stdout)
                self.assertEqual(json.loads(result.stdout), {"accepted": False})


if __name__ == "__main__":
    unittest.main()
