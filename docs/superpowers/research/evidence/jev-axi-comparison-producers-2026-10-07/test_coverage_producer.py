import hashlib
import base64
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name('coverage_producer.py')


class CoverageProducerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.git('init', '-q')
        (self.repo / 'outside.md').write_bytes(b'Existing.\n')
        self.parent = self.commit()
        (self.repo / 'a.md').write_bytes(b'Selected.\n')
        (self.repo / 'review.md').write_bytes(b'Review of declared input.\n')
        self.record = {'reviewed_public_inputs': {
            'a.md': hashlib.sha256(b'Selected.\n').hexdigest(),
            'outside.md': hashlib.sha256(b'Existing.\n').hexdigest()},
            'review_sha256': hashlib.sha256(b'Review of declared input.\n').hexdigest()}
        (self.repo / 'verification.json').write_text(json.dumps(self.record))
        self.child = self.commit()
        self.spec = {'version': 1, 'parent': self.parent, 'child': self.child,
                     'sources': [self.reference('review.md'), self.reference('verification.json')],
                     'verification': 1, 'review': 0}

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), '-c', 'core.hooksPath=/dev/null',
                    '-c', 'commit.gpgsign=false', '-c', 'user.name=Fixture',
                    '-c', 'user.email=fixture@example.invalid', *args], stderr=subprocess.PIPE)

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture')
        return self.git('rev-parse', 'HEAD').decode().strip()

    def reference(self, name):
        return {'commit': self.child, 'path': name,
                'sha256': hashlib.sha256((self.repo / name).read_bytes()).hexdigest()}

    def invoke(self, spec=None, name='result'):
        path = self.root / (name + '.json')
        path.write_text(json.dumps(self.spec if spec is None else spec))
        target = self.root / name
        result = subprocess.run([sys.executable, str(SCRIPT), 'prepare-coverage',
                    '--repository', str(self.repo), '--case-spec', str(path), '--output', str(target)],
                    capture_output=True, text=True)
        return result, target

    def test_content_membership_and_review_identity_are_distinct(self):
        result, target = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        packet = json.loads((target / 'packet.json').read_text())
        self.assertTrue(packet['ready'])
        self.assertEqual([(r['path'], r['relationship']) for r in packet['entries']],
                         [('a.md', 'equal'), ('review.md', 'absent'), ('verification.json', 'absent')])
        self.assertEqual(packet['review']['relationship'], 'equal')
        self.assertEqual([r['path'] for r in packet['outside_difference']], ['outside.md'])
        self.assertEqual([r['path'] for r in packet['sources']], ['review.md', 'verification.json'])
        for source in packet['sources']:
            self.assertEqual((target / source['artifact']).read_bytes(), (self.repo / source['path']).read_bytes())
        receipt = json.loads((target / 'receipt.json').read_text())
        for name, digest in receipt['artifacts'].items():
            self.assertEqual(hashlib.sha256((target / name).read_bytes()).hexdigest(), digest)
        self.assertIn('outside.md', (target / 'packet.md').read_text())
        self.assertNotIn(str(self.repo), (target / 'packet.json').read_text())

    def test_neutral_snapshot_records_both_differences(self):
        changed, added = b'Selected.\nMore context.\n', b'# Context\n'
        spec = self.spec | {'overlays': [
            {'path': path, 'mode': '100644', 'base64': base64.b64encode(data).decode()}
            for path, data in [('a.md', changed), ('context.md', added)]]}
        result, target = self.invoke(spec)
        self.assertEqual(result.returncode, 0, result.stderr)
        packet = json.loads((target / 'packet.json').read_text())
        self.assertEqual(packet['candidate']['kind'], 'snapshot')
        self.assertNotIn('commit', packet['candidate'])
        rows = {r['path']: r for r in packet['entries']}
        self.assertEqual(rows['a.md']['relationship'], 'different')
        self.assertEqual(rows['context.md']['relationship'], 'absent')
        self.assertEqual((target / rows['a.md']['artifact']).read_bytes(), changed)
        self.assertEqual((target / rows['context.md']['artifact']).read_bytes(), added)
        self.assertEqual(packet['review']['relationship'], 'equal')
        self.assertNotIn('overlays', packet)

    def test_unavailable_record_never_becomes_absent_membership(self):
        for variant in ['unavailable', 'changed', 'malformed']:
            spec = json.loads(json.dumps(self.spec))
            if variant == 'unavailable': spec['sources'][1]['path'] = 'missing.json'
            if variant == 'changed': spec['sources'][1]['sha256'] = '0' * 64
            if variant == 'malformed': spec['sources'][1]['sha256'] = 'bad'
            result, target = self.invoke(spec, variant)
            self.assertEqual(result.returncode, 2, result.stderr)
            packet = json.loads((target / 'packet.json').read_text())
            self.assertEqual(packet['sources'][1]['status'], variant)
            self.assertTrue(packet['entries'])
            self.assertEqual({r['relationship'] for r in packet['entries']}, {'unavailable'})

    def test_separate_review_mismatch_is_a_ready_relationship(self):
        (self.repo / 'review.md').write_bytes(b'Another review.\n')
        self.child = self.commit()
        self.spec['parent'], self.spec['child'] = self.spec['child'], self.child
        self.spec['sources'][0] = self.reference('review.md')
        result, target = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        packet = json.loads((target / 'packet.json').read_text())
        self.assertEqual(packet['review']['relationship'], 'different')
        self.assertTrue(packet['ready'])

    def test_missing_source_commit_is_unavailable(self):
        self.spec['sources'][1]['commit'] = '0' * 40
        result, target = self.invoke()
        self.assertEqual(result.returncode, 2, result.stderr)
        packet = json.loads((target / 'packet.json').read_text())
        self.assertEqual(packet['sources'][1]['status'], 'unavailable')
        self.assertEqual(packet['sources'][1]['commit'], '0' * 40)
        self.assertEqual([r['path'] for r in packet['entries']],
                         ['a.md', 'review.md', 'verification.json'])
        self.assertEqual({r['relationship'] for r in packet['entries']}, {'unavailable'})

    def test_missing_candidate_blob_keeps_later_entries_and_sources(self):
        blob = self.git('rev-parse', self.child + ':a.md').decode().strip()
        # This disposable repository has loose objects. Remove only the selected
        # candidate blob to exercise a genuinely unavailable Git object.
        (self.repo / '.git' / 'objects' / blob[:2] / blob[2:]).unlink()
        result, target = self.invoke()
        self.assertEqual(result.returncode, 2, result.stderr)
        packet = json.loads((target / 'packet.json').read_text())
        self.assertEqual([r['path'] for r in packet['entries']],
                         ['a.md', 'review.md', 'verification.json'])
        self.assertEqual(packet['entries'][0]['relationship'], 'unavailable')
        self.assertNotIn('artifact', packet['entries'][0])
        self.assertEqual(packet['review']['relationship'], 'equal')
        for row in packet['entries'][1:]:
            self.assertEqual(row['relationship'], 'absent')
            self.assertEqual((target / row['artifact']).read_bytes(), (self.repo / row['path']).read_bytes())
        self.assertEqual([r['path'] for r in packet['outside_difference']], ['outside.md'])

    def test_malformed_map_preserves_the_retrieved_record(self):
        (self.repo / 'verification.json').write_bytes(b'{"reviewed_public_inputs": []}')
        self.child = self.commit()
        self.spec['parent'], self.spec['child'] = self.spec['child'], self.child
        self.spec['sources'][1] = self.reference('verification.json')
        result, target = self.invoke()
        self.assertEqual(result.returncode, 2, result.stderr)
        packet = json.loads((target / 'packet.json').read_text())
        self.assertEqual(packet['sources'][1]['status'], 'available')
        self.assertEqual((target / packet['sources'][1]['artifact']).read_bytes(), b'{"reviewed_public_inputs": []}')

    def test_unsupported_deletion_and_symlink_remain_visible(self):
        (self.repo / 'a.md').unlink()
        (self.repo / 'link.md').symlink_to('outside.md')
        self.child = self.commit()
        self.spec['parent'], self.spec['child'] = self.spec['child'], self.child
        result, target = self.invoke()
        self.assertEqual(result.returncode, 2, result.stderr)
        packet = json.loads((target / 'packet.json').read_text())
        self.assertEqual({r['path'] for r in packet['entries']}, {'a.md', 'link.md'})
        self.assertTrue(all(r['relationship'] == 'unavailable' for r in packet['entries']))

    def test_mode_change_preserves_the_content_relationship(self):
        (self.repo / 'a.md').chmod(0o755)
        self.child = self.commit()
        self.spec['parent'], self.spec['child'] = self.spec['child'], self.child
        result, target = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        row = json.loads((target / 'packet.json').read_text())['entries'][0]
        self.assertEqual((row['before'][0], row['after'][0], row['relationship']), ('100644', '100755', 'equal'))

    def test_existing_result_is_untouched(self):
        target = self.root / 'result'
        target.mkdir()
        (target / 'sentinel').write_bytes(b'Keep.\n')
        result, _ = self.invoke()
        self.assertEqual(result.returncode, 1)
        self.assertEqual([p.name for p in target.iterdir()], ['sentinel'])
        self.assertEqual((target / 'sentinel').read_bytes(), b'Keep.\n')

    def test_invalid_revision_and_overlay_report_nonready(self):
        for variant in ['revision', 'base64', 'path']:
            spec = json.loads(json.dumps(self.spec))
            if variant == 'revision': spec['child'] = 'HEAD'
            elif variant == 'path': spec['sources'][1]['path'] = '../verification.json'
            else: spec['overlays'] = [{'path': 'a.md', 'mode': '100644', 'base64': '%%%'}]
            result, target = self.invoke(spec, variant)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertFalse(json.loads((target / 'packet.json').read_text())['ready'])

    def test_derived_snapshot_cannot_put_a_file_inside_another_file(self):
        spec = self.spec | {'overlays': [{'path': 'a.md/child', 'mode': '100644',
                                         'base64': base64.b64encode(b'child').decode()}]}
        result, target = self.invoke(spec)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse(json.loads((target / 'packet.json').read_text())['ready'])


if __name__ == '__main__':
    unittest.main()
