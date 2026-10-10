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

    def test_source_change_during_observation_leaves_compatibility_unestablished(self):
        for side in ('before', 'after'):
            with self.subTest(side=side):
                case = self.root / ('source-change-' + side)
                self.before = case / 'before'
                self.after = case / 'after'
                shutil.copytree(SEED, self.before)
                shutil.copytree(SEED, self.after)
                self.output = case / 'evidence'
                changed = self.before if side == 'before' else self.after
                report = changed / 'bin/inventory-report'
                report.write_text(report.read_text() +
                                  '\nfrom pathlib import Path\n'
                                  'Path("generated-note.txt").write_text("created during comparison\\n")\n')
                result = self.run_comparison()
                self.assertEqual(result.returncode, 2, result.stderr)
                evidence = self.evidence()
                self.assertEqual(evidence['outcome'], 'observation_failed')
                self.assertNotIn('generated-note.txt', evidence['source_identities'][side])
                self.assertEqual(evidence['source_rechecks'][side]['status'], 'changed')
                self.assertIn('generated-note.txt', evidence['source_rechecks'][side]['identity'])
                other = 'after' if side == 'before' else 'before'
                self.assertEqual(evidence['source_rechecks'][other]['status'], 'unchanged')
                for observation in evidence['observations'].values():
                    self.assertFalse(observation['different'])
                    self.assertFalse(observation['observation_failed'])
                    self.assertEqual(observation['before']['records'], observation['after']['records'])

    def test_unreadable_initial_subtree_is_an_observation_failure(self):
        hidden = self.before / 'unreadable'
        hidden.mkdir()
        self.addCleanup(hidden.chmod, 0o700)
        hidden.chmod(0)
        try:
            list(hidden.iterdir())
        except PermissionError:
            pass
        else:
            self.skipTest('This environment can enumerate mode-000 directories')
        result = self.run_comparison()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('source inventory unavailable', result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        self.assertFalse(self.output.exists())

    def test_unreadable_final_subtree_leaves_compatibility_unestablished(self):
        hidden = self.after / 'generated'
        hidden.mkdir()
        self.addCleanup(hidden.chmod, 0o700)
        hidden.chmod(0)
        try:
            list(hidden.iterdir())
        except PermissionError:
            pass
        else:
            self.skipTest('This environment can enumerate mode-000 directories')
        finally:
            hidden.chmod(0o700)
        report = self.after / 'bin/inventory-report'
        report.write_text(report.read_text() +
                          '\nfrom pathlib import Path\n'
                          'if Path("generated").stat().st_mode & 0o700:\n'
                          '    Path("generated/note.txt").write_text("created during comparison\\n")\n'
                          '    Path("generated").chmod(0)\n')
        result = self.run_comparison()
        self.assertEqual(result.returncode, 2, result.stderr)
        evidence = self.evidence()
        self.assertEqual(evidence['outcome'], 'observation_failed')
        self.assertEqual(evidence['source_rechecks']['after']['status'], 'failed')
        self.assertIsNone(evidence['source_rechecks']['after']['identity'])
        self.assertTrue(evidence['source_rechecks']['after']['error'])
        self.assertEqual(evidence['source_rechecks']['before']['status'], 'unchanged')
        for observation in evidence['observations'].values():
            self.assertFalse(observation['different'])
            self.assertFalse(observation['observation_failed'])
            self.assertEqual(observation['before']['records'], observation['after']['records'])

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

    def run_contract(self):
        return subprocess.run(
            [sys.executable, str(CLI), '--before', str(self.before), '--after', str(self.after),
             '--contract-cases', str(ROOT / 'cases'), '--output', str(self.output)],
            capture_output=True, text=True)

    def install_json_report(self, change=''):
        report = self.after / 'bin/inventory-report'
        shutil.copyfile(report, report.with_name('.baseline-report'))
        report.write_text(
            'import argparse, json, subprocess, sys\n'
            'from pathlib import Path\n'
            'parser = argparse.ArgumentParser()\n'
            'parser.add_argument("--format", choices=("text", "json"), default="text")\n'
            'args, rest = parser.parse_known_args()\n'
            'result = subprocess.run([sys.executable, str(Path(__file__).with_name(".baseline-report")), *rest], capture_output=True, text=True)\n'
            'if result.returncode:\n'
            '    sys.stdout.write(result.stdout)\n'
            '    sys.stderr.write(result.stderr)\n'
            '    raise SystemExit(result.returncode)\n'
            'rows = result.stdout.splitlines()\n'
            'rows[1:] = reversed(rows[1:])\n'
            'items = [dict(sku=row.split("\\t")[0], warehouse=row.split("\\t")[1], on_hand=int(row.split("\\t")[2])) for row in rows[1:]]\n'
            'warehouse = rest[rest.index("--warehouse") + 1] if "--warehouse" in rest else None\n'
            'value = dict(schema="inventory-report/v1", warehouse=warehouse, items=items)\n'
            + change +
            '\nprint(json.dumps(value) if args.format == "json" else "\\n".join(rows))\n'
        )

    def test_contract_mode_rejects_wrong_json_schema_after_compatible_defaults(self):
        self.install_json_report('value["schema"] = "wrong"\n')
        result = self.run_contract()
        self.assertEqual(result.returncode, 1, result.stderr)
        evidence = self.evidence()
        self.assertTrue(evidence['observations']['south/default']['matches_contract'])
        self.assertTrue(evidence['observations']['south/json']['different'])
        self.assertEqual(evidence['observations']['south/json']['after']['status'], 'malformed')
        self.assertEqual(evidence['source_rechecks']['after']['status'], 'unchanged')

    def test_contract_mode_accepts_all_cases_and_refactored_reordered_reports(self):
        self.install_json_report()
        result = self.run_contract()
        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = self.evidence()
        self.assertEqual(evidence['mode'], 'amended-inventory-contract/v1')
        for ident in ('unfiltered', 'south', 'empty', 'no-matches'):
            for boundary in ('default', 'text', 'json', 'low-stock', 'archive'):
                self.assertTrue(evidence['observations'][ident + '/' + boundary]['matches_contract'])
            self.assertTrue((self.output / 'cases' / ident / 'input.json').is_file())
        for observation in evidence['observations'].values():
            self.assertTrue(observation['matches_contract'])
        self.assertEqual(evidence['observations']['south/json']['after']['records'],
                         [['A-100', 'South', 0], ['B-200', 'South', 2]])

    def test_contract_mode_rejects_json_warehouse_quantity_and_dropped_zero(self):
        for index, change in enumerate((
                'value["warehouse"] = "Wrong"\n',
                'value["items"] = [item for item in items if item["on_hand"] > 0]\n',
                'if items: items[0]["on_hand"] = True\n',
        )):
            with self.subTest(change=change):
                case = self.root / str(index)
                self.before = case / 'before'
                self.after = case / 'after'
                shutil.copytree(SEED, self.before)
                shutil.copytree(SEED, self.after)
                self.output = case / 'evidence'
                self.install_json_report(change)
                result = self.run_contract()
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertTrue(self.evidence()['observations']['south/json']['different'])

    def test_contract_mode_preserves_rejection_difference_with_consumer_failure(self):
        self.install_json_report()
        report = self.after / 'bin/inventory-report'
        report.write_text(report.read_text().replace(
            'if result.returncode:', 'if result.returncode and args.format != "json":'
        ).replace(
            'rows = result.stdout.splitlines()',
            'rows = result.stdout.splitlines() or ["sku\\twarehouse\\ton_hand"]'
        ))
        (self.after / 'bin/low-stock').write_text('raise SystemExit(7)\n')
        result = self.run_contract()
        self.assertEqual(result.returncode, 2, result.stderr)
        evidence = self.evidence()
        self.assertTrue(evidence['observations']['invalid/quantity-1/json']['different'])
        self.assertTrue(evidence['observations']['south/low-stock']['observation_failed'])

    def test_contract_mode_keeps_source_recheck_and_destination_protection(self):
        self.install_json_report()
        report = self.after / 'bin/inventory-report'
        report.write_text(report.read_text() + '\nPath("new.txt").write_text("changed")\n')
        result = self.run_contract()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(self.evidence()['source_rechecks']['after']['status'], 'changed')
        retained = (self.output / 'summary.json').read_bytes()
        result = self.run_contract()
        self.assertEqual(result.returncode, 2)
        self.assertEqual((self.output / 'summary.json').read_bytes(), retained)
        self.output = self.after / 'evidence'
        result = self.run_contract()
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.output.exists())
