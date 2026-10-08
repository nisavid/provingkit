import json
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SEED = ROOT / 'seed'
CLI = ROOT / 'compare_behavior.py'


class ComparisonCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.before = self.root / 'before'
        self.after = self.root / 'after'
        shutil.copytree(SEED, self.before)
        shutil.copytree(SEED, self.after)
        self.output = self.root / 'evidence'
        self.input = self.root / 'inventory.json'
        self.input.write_bytes((SEED / 'fixtures/inventory.json').read_bytes())

    def run_comparison(self, *extra):
        return subprocess.run([sys.executable, str(CLI), '--before', str(self.before), '--after', str(self.after), '--input', str(self.input), '--output', str(self.output), *extra], capture_output=True, text=True)

    def evidence(self):
        return json.loads((self.output / 'summary.json').read_text())

    def test_unchanged_behavior_is_compatible_and_retained(self):
        result = self.run_comparison('--warehouse', 'South', '--threshold', '2')
        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = self.evidence()
        self.assertEqual(evidence['outcome'], 'compatible')
        self.assertEqual(set(evidence['observations']), {'report', 'filtered_report', 'low_stock', 'archive'})
        self.assertEqual(evidence['observations']['report']['before']['records'], evidence['observations']['report']['after']['records'])
        self.assertTrue((self.output / 'input.json').is_file())

    def test_relative_paths_are_resolved_from_the_invoking_directory(self):
        result = subprocess.run(
            [sys.executable, str(CLI), '--before', 'before', '--after', 'after',
             '--input', 'inventory.json', '--output', 'evidence'],
            cwd=self.root, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.evidence()['outcome'], 'compatible')

    def test_reordered_rows_and_internal_refactor_are_compatible(self):
        formatter = self.after / 'inventory_format.py'
        formatter.write_text('HEADER = "sku\\twarehouse\\ton_hand\\n"\n\ndef render_text(items):\n    rows = list(items)\n    rows.reverse()\n    return HEADER + "".join("%s\\t%s\\t%s\\n" % (r["sku"], r["warehouse"], r["on_hand"]) for r in rows)\n')
        result = self.run_comparison('--warehouse', 'South')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.evidence()['outcome'], 'compatible')
        self.assertNotEqual(self.evidence()['source_identities']['before'], self.evidence()['source_identities']['after'])

    def test_changed_default_json_is_different_with_malformed_report_evidence(self):
        (self.after / 'bin/inventory-report').write_text('print(\'{"items": []}\')\n')
        result = self.run_comparison()
        self.assertEqual(result.returncode, 2, result.stderr)
        evidence = self.evidence()
        self.assertEqual(evidence['outcome'], 'observation_failed')
        self.assertTrue(evidence['observations']['report']['different'])
        self.assertEqual(evidence['observations']['report']['after']['status'], 'malformed')
        self.assertIn('items', evidence['observations']['report']['after']['stdout'])

    def test_dropped_zero_row_is_different(self):
        formatter = self.after / 'inventory_format.py'
        formatter.write_text(formatter.read_text().replace('for item in items)', 'for item in items if item["on_hand"] > 0)'))
        result = self.run_comparison('--warehouse', 'South')
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(self.evidence()['outcome'], 'different')
        self.assertTrue(self.evidence()['observations']['filtered_report']['different'])

    def test_removing_literal_quotes_from_record_identity_is_different(self):
        self.input.write_text(json.dumps({'items': [{'sku': '"A"', 'warehouse': '"North"', 'on_hand': 0}]}))
        (self.after / 'inventory_format.py').write_text(
            'def render_text(items):\n'
            '    return "sku\\twarehouse\\ton_hand\\nA\\tNorth\\t0\\n"\n'
        )
        result = self.run_comparison()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(self.evidence()['outcome'], 'different')
        self.assertEqual(self.evidence()['observations']['report']['before']['records'], [['"A"', '"North"', 0]])

    def test_command_failure_does_not_establish_compatibility(self):
        (self.after / 'bin/low-stock').write_text('raise SystemExit(7)\n')
        result = self.run_comparison()
        self.assertEqual(result.returncode, 2, result.stderr)
        evidence = self.evidence()
        self.assertEqual(evidence['outcome'], 'observation_failed')
        self.assertEqual(evidence['observations']['low_stock']['after']['exit_code'], 7)
        self.assertTrue(evidence['observations']['low_stock']['observation_failed'])

    def test_invalid_utf8_command_evidence_is_preserved_without_replacement(self):
        (self.after / 'bin/low-stock').write_text(
            'import sys\nsys.stdout.buffer.write(b"\\xff\\x00")\n'
            'sys.stderr.buffer.write(b"\\xfe")\nraise SystemExit(7)\n'
        )
        result = self.run_comparison()
        self.assertEqual(result.returncode, 2, result.stderr)
        observation = self.evidence()['observations']['low_stock']['after']
        self.assertEqual(observation['stdout_hex'], 'ff00')
        self.assertEqual(observation['stderr_hex'], 'fe')
        self.assertEqual(observation['exit_code'], 7)

    def test_difference_and_failure_are_both_retained(self):
        formatter = self.after / 'inventory_format.py'
        formatter.write_text(formatter.read_text().replace('for item in items)', 'for item in items if item["on_hand"] > 0)'))
        (self.after / 'bin/low-stock').write_text('raise SystemExit(7)\n')
        result = self.run_comparison()
        self.assertEqual(result.returncode, 2, result.stderr)
        evidence = self.evidence()
        self.assertEqual(evidence['outcome'], 'observation_failed')
        self.assertTrue(evidence['observations']['report']['different'])
        self.assertTrue(evidence['observations']['low_stock']['observation_failed'])

    def test_existing_output_is_preserved(self):
        self.output.mkdir()
        marker = self.output / 'keep.txt'
        marker.write_text('untouched')
        result = self.run_comparison()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(marker.read_text(), 'untouched')
        self.assertEqual(sorted(path.name for path in self.output.iterdir()), ['keep.txt'])

    def test_output_within_either_source_is_rejected_without_changes(self):
        def snapshot(root):
            return {str(path.relative_to(root)): path.read_bytes()
                    for path in root.rglob('*') if path.is_file()}
        for source in (self.before, self.after):
            with self.subTest(source=source.name):
                original = snapshot(source)
                self.output = source / 'evidence'
                result = self.run_comparison()
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.output.exists())
                self.assertEqual(snapshot(source), original)

    def test_timeout_stops_descendant_before_it_changes_a_file(self):
        marker = self.root / 'late-write'
        child = (
            'import time; from pathlib import Path; time.sleep(6); '
            f'Path({str(marker)!r}).write_text("late")'
        )
        (self.after / 'bin/low-stock').write_text(
            'import subprocess, sys\n'
            f'subprocess.Popen([sys.executable, "-c", {child!r}])\n'
        )
        result = self.run_comparison()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertTrue(self.evidence()['observations']['low_stock']['after']['timed_out'])
        time.sleep(1.2)  # Cross the descendant's planned write time after the CLI returns.
        self.assertFalse(marker.exists(), 'timed-out descendant still performed its write')
