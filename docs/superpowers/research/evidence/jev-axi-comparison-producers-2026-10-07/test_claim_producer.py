import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name('claim_producer.py')


class ClaimProducerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.git('init', '-q')
        self.assertion = 'The report says “Unknown costs remain.”'
        self.draft = ('Opening.\n' + self.assertion + '\nClosing.\n').encode()
        self.source = b'Unknown costs remain.\nA separate qualification.\n'
        for name, data in [('draft.md', self.draft), ('source.md', self.source)]:
            (self.repo / name).write_bytes(data)
        self.git('add', '.')
        self.git('-c', 'core.hooksPath=/dev/null', '-c', 'user.name=Test',
                 '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'fixture')
        self.commit = self.git('rev-parse', 'HEAD').decode().strip()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), '-c', 'core.autocrlf=false',
                                        '-c', 'core.attributesFile=/dev/null', *args], stderr=subprocess.PIPE)

    def case(self):
        def entry(path, data):
            return {'commit': self.commit, 'path': path,
                    'sha256': hashlib.sha256(data).hexdigest()}
        return {'version': 1, 'case_id': 'case_01', 'assertion': self.assertion,
                'quotation': 'Unknown costs remain.',
                'draft': entry('draft.md', self.draft) | {'start_line': 1, 'end_line': 3, 'assertion_line': 2},
                'sources': [entry('source.md', self.source)]}

    def invoke(self, case, name='result'):
        spec = self.root / (name + '.json')
        spec.write_text(json.dumps(case))
        target = self.root / name
        result = subprocess.run([sys.executable, str(SCRIPT), 'prepare-claim',
                                 '--repository', str(self.repo), '--case-spec', str(spec),
                                 '--output', str(target)], capture_output=True, text=True)
        return result, target

    def test_preserves_complete_sources_and_ready_packet(self):
        result, target = self.invoke(self.case())
        self.assertEqual(result.returncode, 0, result.stderr)
        packet = json.loads((target / 'packet.json').read_text())
        receipt = json.loads((target / 'receipt.json').read_text())
        self.assertEqual(packet['status'], 'ready')
        self.assertEqual(packet['assertion'], self.assertion)
        self.assertEqual(packet['quotation_status'], 'matched')
        self.assertEqual((target / 'draft.source').read_bytes(), self.draft)
        self.assertEqual((target / 'source-1.source').read_bytes(), self.source)
        self.assertIn('0002 | A separate qualification.', (target / 'packet.md').read_text())
        self.assertEqual(receipt['git_blob_bytes_read'], len(self.draft) + len(self.source))
        self.assertNotIn(str(self.repo), (target / 'packet.json').read_text())

    def test_changed_source_is_preserved_without_ready_judgment(self):
        case = self.case()
        case['sources'][0]['sha256'] = '0' * 64
        result, target = self.invoke(case)
        self.assertEqual(result.returncode, 2, result.stderr)
        packet = json.loads((target / 'packet.json').read_text())
        self.assertEqual(packet['status'], 'non_ready')
        self.assertEqual(packet['sources'][0]['status'], 'changed')
        self.assertEqual(packet['quotation_status'], 'unavailable')
        self.assertEqual((target / 'source-1.source').read_bytes(), self.source)

    def test_controlled_unavailability_is_distinct_from_missing(self):
        for state in ['controlled_unavailable', 'missing']:
            with self.subTest(state=state):
                case = self.case()
                if state == 'missing':
                    case['sources'][0]['path'] = 'absent.md'
                else:
                    case['sources'][0]['availability'] = state
                result, target = self.invoke(case, state)
                self.assertEqual(result.returncode, 2, result.stderr)
                packet = json.loads((target / 'packet.json').read_text())
                self.assertEqual(packet['status'], 'non_ready')
                self.assertEqual(packet['sources'][0]['status'], state)
                self.assertEqual(packet['quotation_status'], 'unavailable')
                self.assertFalse((target / 'source-1.source').exists())

    def test_invalid_or_evaluator_bearing_specs_deliver_no_candidate_sources(self):
        for variant in ['key', 'revision', 'path', 'version', 'range', 'quote', 'assertion']:
            with self.subTest(variant=variant):
                case = self.case()
                if variant == 'key': case['expected_relation'] = 'supported'
                if variant == 'revision': case['sources'][0]['commit'] = 'HEAD'
                if variant == 'path': case['sources'][0]['path'] = '../source.md'
                if variant == 'version': case['version'] = True
                if variant == 'range': case['draft']['end_line'] = 100
                if variant == 'quote': case['quotation'] = 'Not in the assertion'
                if variant == 'assertion': case['assertion'] = 'A different assertion'
                result, target = self.invoke(case, variant)
                self.assertEqual(result.returncode, 2, result.stderr)
                packet = json.loads((target / 'packet.json').read_text())
                self.assertEqual(packet['status'], 'non_ready')
                self.assertTrue((target / 'receipt.json').exists())
                self.assertNotIn('expected_relation', (target / 'packet.json').read_text())

    def test_existing_result_is_untouched(self):
        target = self.root / 'result'
        target.mkdir()
        (target / 'sentinel').write_bytes(b'Keep these bytes.\n')
        result, _ = self.invoke(self.case())
        self.assertEqual(result.returncode, 2)
        self.assertEqual([p.name for p in target.iterdir()], ['sentinel'])
        self.assertEqual((target / 'sentinel').read_bytes(), b'Keep these bytes.\n')

    def test_missing_or_unsupported_draft_keeps_its_acquisition_status(self):
        (self.repo / 'binary').write_bytes(b'\xff')
        self.git('add', '.')
        self.git('-c', 'core.hooksPath=/dev/null', '-c', 'user.name=Test',
                 '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'binary draft')
        revision = self.git('rev-parse', 'HEAD').decode().strip()
        for path, expected in [('missing.md', 'missing'), ('binary', 'unsupported')]:
            case = self.case()
            case['draft'].update(commit=revision, path=path,
                                 sha256=hashlib.sha256(b'\xff').hexdigest())
            result, target = self.invoke(case, expected)
            self.assertEqual(result.returncode, 2, result.stderr)
            packet = json.loads((target / 'packet.json').read_text())
            self.assertEqual(packet['draft']['status'], expected)
            self.assertEqual(packet['status'], 'non_ready')
            self.assertEqual(packet['context'], '')
            self.assertEqual((target / 'source-1.source').read_bytes(), self.source)
            if expected == 'unsupported':
                self.assertEqual((target / 'draft.source').read_bytes(), b'\xff')

    def test_nonregular_and_nontext_sources_are_not_ready(self):
        (self.repo / 'link.md').symlink_to('source.md')
        (self.repo / 'binary').write_bytes(b'\xff')
        self.git('add', '.')
        self.git('-c', 'core.hooksPath=/dev/null', '-c', 'user.name=Test',
                 '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'variants')
        revision = self.git('rev-parse', 'HEAD').decode().strip()
        for path, data in [('link.md', b'source.md'), ('binary', b'\xff')]:
            case = self.case()
            case['sources'][0] = {'commit': revision, 'path': path,
                                   'sha256': hashlib.sha256(data).hexdigest()}
            result, target = self.invoke(case, path)
            self.assertEqual(result.returncode, 2, result.stderr)
            packet = json.loads((target / 'packet.json').read_text())
            self.assertEqual(packet['sources'][0]['status'], 'unsupported')

    def test_source_order_preserves_raw_bytes(self):
        case = self.case()
        case['sources'] = [case['draft'] | {}, case['sources'][0]]
        for key in ['start_line', 'end_line', 'assertion_line']:
            del case['sources'][0][key]
        result, target = self.invoke(case)
        self.assertEqual(result.returncode, 0, result.stderr)
        packet = json.loads((target / 'packet.json').read_text())
        self.assertEqual([s['path'] for s in packet['sources']], ['draft.md', 'source.md'])
        self.assertEqual((target / 'source-1.source').read_bytes(), self.draft)
        self.assertEqual((target / 'source-2.source').read_bytes(), self.source)

    def test_literal_quote_only_normalizes_line_endings(self):
        self.assertion = 'The report says “Café”.'
        self.draft = (self.assertion + '\r\n').encode()
        self.source = 'Cafe\u0301\r\nAnother line.\r\n'.encode()
        (self.repo / 'draft.md').write_bytes(self.draft)
        (self.repo / 'source.md').write_bytes(self.source)
        self.git('add', '.')
        self.git('-c', 'core.hooksPath=/dev/null', '-c', 'user.name=Test',
                 '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'unicode')
        self.commit = self.git('rev-parse', 'HEAD').decode().strip()
        case = self.case()
        case['quotation'] = 'Café'
        case['draft'].update(start_line=1, end_line=1, assertion_line=1)
        result, target = self.invoke(case)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((target / 'packet.json').read_text())['quotation_status'], 'unmatched')
        self.assertEqual((target / 'source-1.source').read_bytes(), self.source)


if __name__ == '__main__':
    unittest.main()
