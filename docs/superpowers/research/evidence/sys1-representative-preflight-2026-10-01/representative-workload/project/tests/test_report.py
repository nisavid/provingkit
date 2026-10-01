"""Check report behavior through the public command."""

import csv
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ReportCommandTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.project = self.root / "application"
        self.project.mkdir()
        shutil.copy2(PROJECT_ROOT / "report.py", self.project / "report.py")
        shutil.copytree(PROJECT_ROOT / "reportlib", self.project / "reportlib",
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(PROJECT_ROOT / "data", self.project / "data")

    def run_report(self):
        return subprocess.run(
            [sys.executable, str(self.project / "report.py")],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )

    def read_report(self):
        with (self.project / "output" / "report.csv").open(
            newline="", encoding="utf-8"
        ) as report:
            return list(csv.reader(report))

    def test_default_report_uses_application_paths_and_source_only(self):
        result = self.run_report()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")
        self.assertEqual(
            self.read_report(),
            [
                ["item", "total_units"],
                ["bravo", "20"],
                ["alpha", "4"],
                ["charlie", "11"],
                ["delta", "4"],
                ["echo", "9"],
            ],
        )
        self.assertFalse((self.root / "output").exists())

    def test_repeated_items_are_combined_in_first_appearance_order(self):
        (self.project / "data" / "source.csv").write_text(
            "item,category,units,multiplier\n"
            "beta,tools,2,3\n"
            "alpha,books,4,2\n"
            "beta,tools,1,5\n",
            encoding="utf-8",
        )
        result = self.run_report()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.read_report(),
            [["item", "total_units"], ["beta", "11"], ["alpha", "8"]],
        )

    def test_invalid_numeric_input_reports_error_without_replacing_report(self):
        output = self.project / "output"
        output.mkdir()
        existing = output / "report.csv"
        existing.write_text("existing report\n", encoding="utf-8")
        (self.project / "data" / "source.csv").write_text(
            "item,category,units,multiplier\n"
            "alpha,books,invalid,2\n",
            encoding="utf-8",
        )
        result = self.run_report()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("must be integers", result.stderr)
        self.assertEqual(existing.read_text(encoding="utf-8"), "existing report\n")


if __name__ == "__main__":
    unittest.main()
