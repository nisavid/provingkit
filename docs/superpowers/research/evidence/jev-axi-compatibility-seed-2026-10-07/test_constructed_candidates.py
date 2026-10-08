"""Observed CLI behavior of the supplied comparison fixtures, not native failures."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent


class ConstructedCandidateTests(unittest.TestCase):
    def candidate(self, name):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        target = Path(temporary.name) / 'candidate'
        shutil.copytree(ROOT / 'seed', target)
        result = subprocess.run(['git', 'apply', str(ROOT / 'constructed' / f'{name}.patch')],
                                cwd=target, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return target

    def report(self, target, *args):
        return subprocess.run([sys.executable, str(target / 'bin/inventory-report'),
                               '--input', str(target / 'fixtures/inventory.json'), *args],
                              cwd=target, capture_output=True, text=True)

    def test_c01_preserves_default_and_adds_json_with_complete_identity(self):
        target = self.candidate('c01')
        ordinary = self.report(target)
        self.assertEqual(ordinary.returncode, 0, ordinary.stderr)
        self.assertEqual(ordinary.stdout, 'sku\twarehouse\ton_hand\nA-100\tNorth\t4\nA-100\tSouth\t0\nB-200\tSouth\t2\n')
        structured = self.report(target, '--format', 'json')
        self.assertEqual(structured.returncode, 0, structured.stderr)
        self.assertEqual(json.loads(structured.stdout), {
            'schema': 'inventory-report/v1', 'warehouse': None,
            'items': [{'sku': 'A-100', 'warehouse': 'North', 'on_hand': 4},
                      {'sku': 'A-100', 'warehouse': 'South', 'on_hand': 0},
                      {'sku': 'B-200', 'warehouse': 'South', 'on_hand': 2}],
        })

    def test_c02_changes_default_and_breaks_the_existing_low_stock_consumer(self):
        target = self.candidate('c02')
        report = self.report(target)
        self.assertEqual(report.returncode, 0, report.stderr)
        self.assertEqual(json.loads(report.stdout)['schema'], 'inventory-report/v1')
        consumer = subprocess.run([sys.executable, str(target / 'bin/low-stock'),
                                   '--input', str(target / 'fixtures/inventory.json')],
                                  cwd=target, capture_output=True, text=True)
        self.assertEqual(consumer.returncode, 0, consumer.stderr)
        self.assertEqual([r['on_hand'] for r in json.loads(consumer.stdout)['items']], [4, 0, 2])

    def test_c03_drops_zero_stock_from_both_renderers(self):
        target = self.candidate('c03')
        text = self.report(target)
        self.assertEqual(text.returncode, 0, text.stderr)
        self.assertEqual(text.stdout, 'sku\twarehouse\ton_hand\nA-100\tNorth\t4\nB-200\tSouth\t2\n')
        structured = self.report(target, '--format', 'json')
        self.assertEqual(structured.returncode, 0, structured.stderr)
        self.assertEqual([r['on_hand'] for r in json.loads(structured.stdout)['items']], [4, 2])

    def test_c04_moves_formatting_and_reorders_rows_without_losing_records(self):
        target = self.candidate('c04')
        text = self.report(target, '--warehouse', 'South')
        self.assertEqual(text.returncode, 0, text.stderr)
        self.assertEqual(text.stdout, 'sku\twarehouse\ton_hand\nB-200\tSouth\t2\nA-100\tSouth\t0\n')
        structured = self.report(target, '--format', 'json', '--warehouse', 'Missing')
        self.assertEqual(structured.returncode, 0, structured.stderr)
        self.assertEqual(json.loads(structured.stdout), {
            'schema': 'inventory-report/v1', 'warehouse': 'Missing', 'items': [],
        })


if __name__ == '__main__':
    unittest.main()
