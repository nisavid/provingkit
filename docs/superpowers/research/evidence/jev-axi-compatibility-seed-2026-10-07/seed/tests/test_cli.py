import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_cli(name, *args):
    return subprocess.run([sys.executable, str(ROOT / name), *map(str, args)], text=True, capture_output=True)


class CliTests(unittest.TestCase):
    def test_report_prints_all_records_in_tab_separated_form(self):
        result = run_cli("bin/inventory-report", "--input", ROOT / "fixtures/inventory.json")
        self.assertEqual((result.returncode, result.stderr), (0, ""))
        self.assertEqual(result.stdout.splitlines()[0], "sku\twarehouse\ton_hand")
        self.assertEqual(set(result.stdout.splitlines()[1:]), {"A-100\tNorth\t4", "A-100\tSouth\t0", "B-200\tSouth\t2"})

    def test_report_filters_warehouse_and_preserves_zero(self):
        result = run_cli("bin/inventory-report", "--input", ROOT / "fixtures/inventory.json", "--warehouse", "South")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.splitlines()[0], "sku\twarehouse\ton_hand")
        self.assertEqual(set(result.stdout.splitlines()[1:]), {"A-100\tSouth\t0", "B-200\tSouth\t2"})

    def test_no_match_and_empty_inventory_have_only_header(self):
        for path, args in [(ROOT / "fixtures/inventory.json", ("--warehouse", "West")), (ROOT / "fixtures/empty-inventory.json", ())]:
            with self.subTest(path=path, args=args):
                result = run_cli("bin/inventory-report", "--input", path, *args)
                self.assertEqual((result.returncode, result.stdout), (0, "sku\twarehouse\ton_hand\n"))

    def test_invalid_records_fail_with_diagnostic(self):
        bad_items = [
            [{"sku": "", "warehouse": "North", "on_hand": 1}],
            [{"sku": "A-100", "warehouse": "", "on_hand": 1}],
            [{"sku": "A-100", "warehouse": "North", "on_hand": -1}],
            [{"sku": "A-100", "warehouse": "North", "on_hand": True}],
            [{"sku": "A-100", "warehouse": "North", "on_hand": 1}, {"sku": "A-100", "warehouse": "North", "on_hand": 2}],
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "inventory.json"
            for items in bad_items:
                with self.subTest(items=items):
                    path.write_text(json.dumps({"items": items}))
                    result = run_cli("bin/inventory-report", "--input", path)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("error:", result.stderr)
                    self.assertEqual(result.stdout, "")

    def test_low_stock_includes_zero_and_threshold_quantity(self):
        result = run_cli("bin/low-stock", "--input", ROOT / "fixtures/inventory.json", "--threshold", "2")
        self.assertEqual((result.returncode, result.stderr), (0, ""))
        self.assertEqual(result.stdout.splitlines()[0], "sku\twarehouse\ton_hand")
        self.assertEqual(set(result.stdout.splitlines()[1:]), {"A-100\tSouth\t0", "B-200\tSouth\t2"})

    def test_archive_writes_every_record_to_selected_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "archive.tsv"
            result = run_cli("jobs/archive-inventory.py", "--input", ROOT / "fixtures/inventory.json", "--output", output)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))
            rows = output.read_text().splitlines()
            self.assertEqual(rows[0], "sku\twarehouse\ton_hand")
            self.assertEqual(set(rows[1:]), {"A-100\tNorth\t4", "A-100\tSouth\t0", "B-200\tSouth\t2"})

    def test_archive_rejects_a_report_that_is_not_tab_separated_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            seed = Path(directory) / "seed"
            shutil.copytree(ROOT, seed)
            report = seed / "bin/inventory-report"
            report.write_text('print(\'{"items": []}\')\n')
            output = Path(directory) / "archive.tsv"
            result = subprocess.run(
                [sys.executable, str(seed / "jobs/archive-inventory.py"),
                 "--input", str(seed / "fixtures/inventory.json"), "--output", str(output)],
                text=True, capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("error:", result.stderr)
            self.assertFalse(output.exists())

    def test_invalid_arguments_and_malformed_json_return_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory:
            bad = Path(directory) / "bad.json"
            bad.write_text("{broken")
            commands = [
                ("bin/inventory-report", ("--input", bad)),
                ("bin/inventory-report", ("--input", ROOT / "fixtures/inventory.json", "--unknown")),
                ("bin/low-stock", ("--input", bad)),
                ("bin/low-stock", ("--input", ROOT / "fixtures/inventory.json", "--threshold", "-1")),
                ("jobs/archive-inventory.py", ("--input", bad, "--output", Path(directory) / "archive.tsv")),
            ]
            for name, args in commands:
                with self.subTest(name=name, args=args):
                    result = run_cli(name, *args)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("error:", result.stderr)
                    self.assertEqual(result.stdout, "")
