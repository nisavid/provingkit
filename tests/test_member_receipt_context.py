"""Explicit member Receipt context is checked before source validation."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/validate_proseweaving.py'


class MemberReceiptContextTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repository = Path(self.temporary.name)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Receipt fixture')
        self.git('config', 'user.email', 'receipt@example.invalid')
        self.git('config', 'commit.gpgsign', 'false')
        (self.repository / 'README.md').write_text('constructed source\n')
        procedure = self.repository / 'docs/behavior-eval-receipts.md'
        procedure.parent.mkdir()
        procedure.write_bytes((ROOT / 'docs/behavior-eval-receipts.md').read_bytes())
        self.candidate = self.commit()

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.repository, stderr=subprocess.DEVNULL).decode().strip()

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture')
        return self.git('rev-parse', 'HEAD')

    def invoke(self, *, candidate=None, procedure=None, repository=None):
        return subprocess.run([
            sys.executable, str(SCRIPT), str(repository or self.repository),
            '--source-stage', '--base', self.candidate,
            '--candidate', candidate or self.candidate,
            '--receipt-root', 'release/eval-receipts',
            '--procedure-revision', procedure or self.candidate,
        ], capture_output=True, text=True, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})

    def test_different_checked_out_revision_is_rejected_before_structural_validation(self):
        (self.repository / 'README.md').write_text('another committed source\n')
        self.commit()
        result = self.invoke()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('checkout HEAD does not match candidate', result.stderr)
        self.assertNotIn('validation passed', result.stdout)

    def test_dirty_tracked_candidate_is_rejected_before_structural_validation(self):
        (self.repository / 'README.md').write_text('uncommitted source\n')
        result = self.invoke()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('requires a clean candidate checkout', result.stderr)

    def test_untracked_source_is_rejected_before_structural_validation(self):
        (self.repository / 'new-source.md').write_text('uncommitted source\n')
        result = self.invoke()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('requires a clean candidate checkout', result.stderr)

    def test_subdirectory_cannot_stand_in_for_candidate_root(self):
        result = self.invoke(repository=self.repository / 'docs')
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('repository must be the Git checkout root', result.stderr)

    def test_different_procedure_bytes_are_rejected(self):
        (self.repository / 'docs/behavior-eval-receipts.md').write_text('another procedure\n')
        changed = self.commit()
        result = self.invoke(candidate=changed, procedure=changed)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('procedure revision differs from the running source-stage procedure', result.stderr)

    def test_unavailable_procedure_is_an_input_error(self):
        result = self.invoke(procedure='a' * 40)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertNotIn('Traceback', result.stderr)

    def install_member(self):
        shutil.copytree(ROOT / 'plugins/proseweaving', self.repository / 'plugins/proseweaving')
        definition = self.repository / 'release/provingkit/definition-v1.json'
        definition.parent.mkdir(parents=True)
        definition.write_text(json.dumps({'membership': {'members': [
            {'id': 'proseweaving', 'content_identity': {'path': 'plugins/proseweaving/content-lock.json'}},
        ]}}))
        return self.commit()

    def test_real_member_validation_returns_noop_with_separate_procedure_identity(self):
        procedure = self.candidate
        self.candidate = self.install_member()
        result = self.invoke(procedure=procedure)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['status'], 'not-required')
        self.assertEqual(report['member'], 'proseweaving')
        self.assertEqual(report['checked_skills'], [])
        self.assertEqual(report['source_stage'], {
            'structural_candidate_revision': self.candidate,
            'procedure_revision': procedure,
            'procedure_sha256': hashlib.sha256((ROOT / 'docs/behavior-eval-receipts.md').read_bytes()).hexdigest(),
            'member_qualification': 'not-evaluated',
        })
        self.assertIn('Proseweaving contract validation passed', result.stderr)
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_structural_failure_cannot_emit_a_receipt_pass(self):
        self.install_member()
        (self.repository / 'plugins/proseweaving/content-lock.json').write_text('{}\n')
        self.candidate = self.commit()
        result = self.invoke()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, '')
        self.assertIn('validation failed', result.stderr)

    def test_member_does_not_pass_when_other_roster_is_incomplete(self):
        self.candidate = self.install_member()
        definition = self.repository / 'release/provingkit/definition-v1.json'
        document = json.loads(definition.read_text())
        document['membership']['members'].append({
            'id': 'other', 'content_identity': {'path': 'plugins/other/content-lock.json'},
        })
        definition.write_text(json.dumps(document))
        other = self.repository / 'plugins/other'
        other.mkdir()
        (other / 'topology.json').write_text(json.dumps({'skills': {'missing': {}}}))
        (other / 'content-lock.json').write_text('{}\n')
        result = self.invoke(candidate=self.commit())
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['status'], 'fail')
        self.assertEqual(report['checked_skills'], [])
        self.assertFalse(report['selection_complete'])
        self.assertIn('other/missing', report['affected_skills'])

    def test_malformed_inventory_is_reported_as_an_error_after_structural_success(self):
        self.install_member()
        definition = self.repository / 'release/provingkit/definition-v1.json'
        definition.write_text(json.dumps({'membership': {'members': [{}]}}))
        self.candidate = self.commit()
        result = self.invoke()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'error')
        self.assertNotIn('Traceback', result.stderr)
