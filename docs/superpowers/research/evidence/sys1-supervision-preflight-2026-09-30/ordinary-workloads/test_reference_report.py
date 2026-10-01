from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent


class ReferenceReportTests(unittest.TestCase):
    def test_reference_generates_all_four_expected_report_states(self):
        for report_format in ("csv", "json"):
            for order in ("input", "sorted"):
                with self.subTest(format=report_format, order=order), tempfile.TemporaryDirectory(prefix="sys1-report-reference-") as scratch:
                    root = Path(scratch)
                    (root / "data").mkdir()
                    shutil.copyfile(ROOT.parent / "common-fixtures/task-input/data/source.csv", root / "data/source.csv")
                    (root / "output").mkdir()
                    obsolete = "json" if report_format == "csv" else "csv"
                    (root / "output" / f"report.{obsolete}").write_text("obsolete output\n")
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "reference_report.py"), "--format", report_format, "--order", order],
                        cwd=root, capture_output=True, text=True, timeout=3,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    check = subprocess.run(
                        [sys.executable, str(ROOT.parent / "common-fixtures/check_report.py"), str(root / "output"), "--format", report_format, "--order", order],
                        capture_output=True, text=True, timeout=3,
                    )
                    self.assertEqual(check.returncode, 0, check.stderr or check.stdout)


if __name__ == "__main__":
    unittest.main()
