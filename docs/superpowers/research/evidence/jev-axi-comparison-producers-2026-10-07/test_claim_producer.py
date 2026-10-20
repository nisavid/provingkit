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
                                 '--output', str(target)], capture_output=True, text=True, timeout=5)
        return result, target

    def snapshot_case(self):
        draft = ('Opening.\r\n' + self.assertion + ' See [report](source.md).\r\n'
                 'This is only a proposal.\r\n').encode()
        (self.root / 'draft-copy.md').write_bytes(draft)
        (self.root / 'report-copy.md').write_bytes(self.source)
        def entry(path, snapshot, data):
            return {'kind': 'snapshot', 'path': path, 'snapshot': snapshot,
                    'checkpoint': 'saved-draft-01', 'sha256': hashlib.sha256(data).hexdigest()}
        case = self.case()
        case.update(version=2, source_link={'line': 2, 'target': 'source.md'})
        case['draft'] = entry('docs/draft.md', 'draft-copy.md', draft) | {
            'start_line': 1, 'end_line': 3, 'assertion_line': 2}
        case['sources'] = [entry('docs/source.md', 'report-copy.md', self.source)]
        return case, draft

    def test_saved_draft_keeps_qualifications_and_selected_report_without_commit(self):
        case, draft = self.snapshot_case()
        result, target = self.invoke(case)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((target / 'draft.source').read_bytes(), draft)
        self.assertEqual((target / 'source-1.source').read_bytes(), self.source)
        packet = json.loads((target / 'packet.json').read_text())
        self.assertEqual(packet['draft']['checkpoint'], 'saved-draft-01')
        self.assertNotIn('commit', packet['draft'])
        self.assertEqual(packet['source_link'], {'line': 2, 'target': 'source.md',
                                               'status': 'matched', 'source_id': 'source-1'})
        inference = json.loads((target / 'inference.json').read_text())
        self.assertEqual(inference['draft_context'], draft.decode())
        self.assertEqual(inference['assertion'], self.assertion)
        self.assertEqual(inference['sources'], [{'id': 'source-1', 'text': self.source.decode()}])
        receipt = json.loads((target / 'receipt.json').read_text())
        self.assertEqual(receipt['git_blob_bytes_read'], 0)
        self.assertEqual(receipt['snapshot_bytes_read'], len(draft) + len(self.source))
        self.assertEqual(receipt['snapshot_read_attempts'], 2)
        self.assertEqual(receipt['git_commands'], 0)

    def test_snapshot_nonregular_inputs_do_not_become_ready(self):
        for kind in ('symlink', 'parent_symlink', 'directory', 'fifo'):
            with self.subTest(kind=kind):
                case, _ = self.snapshot_case()
                path = self.root / kind
                if kind == 'symlink':
                    path.symlink_to(self.root / 'report-copy.md')
                elif kind == 'parent_symlink':
                    path.symlink_to(self.root, target_is_directory=True)
                elif kind == 'directory':
                    path.mkdir()
                else:
                    import os
                    os.mkfifo(path)
                case['sources'][0]['snapshot'] = kind + ('/report-copy.md' if kind == 'parent_symlink' else '')
                result, target = self.invoke(case, 'nonregular_' + kind)
                self.assertEqual(result.returncode, 2, result.stderr)
                packet = json.loads((target / 'packet.json').read_text())
                self.assertEqual(packet['sources'][0]['status'], 'unsupported')
                self.assertFalse((target / 'inference.json').exists())

    def test_code_and_escaped_links_cannot_supply_report_association(self):
        for variant, line in [
            ('inline_code', self.assertion + ' See `[report](source.md)`.'),
            ('escaped', self.assertion + ' See \\[report](source.md).'),
            ('fenced', '```\n' + self.assertion + ' See [report](source.md).\n```'),
            ('indented', '    ' + self.assertion + ' See [report](source.md).'),
        ]:
            with self.subTest(variant=variant):
                case, _ = self.snapshot_case()
                draft = ('Opening.\n' + line + '\nClosing.\n').encode()
                (self.root / 'draft-copy.md').write_bytes(draft)
                case['draft'].update(sha256=hashlib.sha256(draft).hexdigest(),
                                     end_line=len(draft.splitlines()),
                                     assertion_line=3 if variant == 'fenced' else 2)
                case['source_link']['line'] = case['draft']['assertion_line']
                result, target = self.invoke(case, variant)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(json.loads((target / 'packet.json').read_text())['source_link']['status'], 'unresolved')
                self.assertFalse((target / 'inference.json').exists())

    def test_mixed_indent_code_cannot_supply_report_association(self):
        case, _ = self.snapshot_case()
        draft = (' \t' + self.assertion + ' See [report](source.md).\n').encode()
        (self.root / 'draft-copy.md').write_bytes(draft)
        case['draft'].update(sha256=hashlib.sha256(draft).hexdigest(),
                             start_line=1, end_line=1, assertion_line=1)
        case['source_link']['line'] = 1
        result, target = self.invoke(case)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual((target / 'draft.source').read_bytes(), draft)
        self.assertEqual(json.loads((target / 'packet.json').read_text())['source_link']['status'], 'unresolved')
        self.assertFalse((target / 'inference.json').exists())

    def test_indented_quote_cannot_supply_report_association(self):
        for spaces in (1, 2, 3):
            for indent in (' ', '     '):
                with self.subTest(spaces=spaces, indent=indent):
                    case, _ = self.snapshot_case()
                    draft = (' ' * spaces + '>' + indent + self.assertion + ' See [report](source.md).\n').encode()
                    (self.root / 'draft-copy.md').write_bytes(draft)
                    case['draft'].update(sha256=hashlib.sha256(draft).hexdigest(),
                                         start_line=1, end_line=1, assertion_line=1)
                    case['source_link']['line'] = 1
                    result, target = self.invoke(case, f'quote_{spaces}_{len(indent)}')
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertEqual((target / 'draft.source').read_bytes(), draft)
                    self.assertEqual(json.loads((target / 'packet.json').read_text())['source_link']['status'], 'unresolved')
                    self.assertFalse((target / 'inference.json').exists())

    def test_multiline_inline_code_cannot_supply_report_association(self):
        for delimiter in ('`', '``'):
            with self.subTest(delimiter=delimiter):
                case, _ = self.snapshot_case()
                draft = ('Opening ' + delimiter + 'code\n' + self.assertion
                         + ' See [report](source.md).\nclosing' + delimiter + '.\n').encode()
                (self.root / 'draft-copy.md').write_bytes(draft)
                case['draft']['sha256'] = hashlib.sha256(draft).hexdigest()
                result, target = self.invoke(case, 'multiline_' + str(len(delimiter)))
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual((target / 'draft.source').read_bytes(), draft)
                self.assertEqual((target / 'source-1.source').read_bytes(), self.source)
                self.assertEqual(json.loads((target / 'packet.json').read_text())['source_link']['status'], 'unresolved')
                self.assertFalse((target / 'inference.json').exists())

    def test_prose_links_outside_code_spans_remain_usable(self):
        for name, opening, closing in [
            ('earlier_code', 'Opening `code`.', 'Closing.'),
            ('unmatched', 'Opening `literal.', 'Closing.'),
            ('different_width', 'Opening `literal.', 'Closing ``literal.'),
            ('escaped', 'Opening \\`literal.', 'Closing `literal.'),
            ('new_paragraph', 'Opening `literal.\n', 'Closing `literal.'),
        ]:
            with self.subTest(name=name):
                case, _ = self.snapshot_case()
                draft = (opening + '\n' + self.assertion + ' See [report](source.md).\n'
                         + closing + '\n').encode()
                (self.root / 'draft-copy.md').write_bytes(draft)
                line = len(opening.split('\n')) + 1
                case['draft'].update(sha256=hashlib.sha256(draft).hexdigest(),
                                     end_line=len(draft.splitlines()), assertion_line=line)
                case['source_link']['line'] = line
                result, target = self.invoke(case, name)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads((target / 'inference.json').read_text())['draft_context'], draft.decode())

    def test_report_amendment_keeps_prior_attempt_and_declared_version_relationship(self):
        case, _ = self.snapshot_case()
        result, original = self.invoke(case, 'original')
        self.assertEqual(result.returncode, 0, result.stderr)
        before = {p.name: p.read_bytes() for p in original.iterdir()}
        amended = b'Further observation is required.\n'
        (self.root / 'report-copy.md').write_bytes(amended)
        result, changed = self.invoke(case, 'stale')
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(json.loads((changed / 'packet.json').read_text())['sources'][0]['status'], 'changed')
        self.assertEqual((changed / 'source-1.source').read_bytes(), amended)
        self.assertFalse((changed / 'inference.json').exists())
        source = case['sources'][0]
        prior = {'checkpoint': source['checkpoint'], 'sha256': source['sha256']}
        source.update(checkpoint='amended-report-02', sha256=hashlib.sha256(amended).hexdigest(),
                      supersedes=prior)
        result, successor = self.invoke(case, 'successor')
        self.assertEqual(result.returncode, 0, result.stderr)
        packet = json.loads((successor / 'packet.json').read_text())
        self.assertEqual(packet['sources'][0]['supersedes'], prior)
        self.assertEqual((successor / 'source-1.source').read_bytes(), amended)
        self.assertEqual({p.name: p.read_bytes() for p in original.iterdir()}, before)
        self.assertNotIn('supersedes', (successor / 'inference.json').read_text())

    def test_snapshot_failure_records_preserve_bytes_and_withhold_inference(self):
        for role in ('draft', 'source'):
            for failure in ('missing', 'changed', 'unsupported'):
                with self.subTest(role=role, failure=failure):
                    case, _ = self.snapshot_case()
                    entry = case['draft'] if role == 'draft' else case['sources'][0]
                    path = self.root / entry['snapshot']
                    if failure == 'missing':
                        path.unlink()
                    else:
                        path.write_bytes(b'changed bytes' if failure == 'changed' else b'\xff')
                        if failure == 'unsupported':
                            entry['sha256'] = hashlib.sha256(b'\xff').hexdigest()
                    result, target = self.invoke(case, role + '_' + failure)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    packet = json.loads((target / 'packet.json').read_text())
                    record = packet['draft'] if role == 'draft' else packet['sources'][0]
                    self.assertEqual(record['status'], failure)
                    self.assertFalse((target / 'inference.json').exists())
                    if failure != 'missing':
                        self.assertEqual((target / record['file']).read_bytes(), path.read_bytes())

    def test_snapshot_link_must_select_the_exact_report_in_context(self):
        for variant in ('target', 'origin', 'line', 'outside_context', 'duplicate', 'image'):
            with self.subTest(variant=variant):
                case, draft = self.snapshot_case()
                if variant == 'target': case['source_link']['target'] = 'another.md'
                if variant == 'origin': case['sources'][0]['path'] = 'elsewhere/source.md'
                if variant == 'line': case['source_link']['line'] = 1
                if variant == 'outside_context': case['source_link']['line'] = 4
                if variant in ('duplicate', 'image'):
                    draft = draft.replace(b'[report](source.md)',
                        b'[report](source.md) [again](source.md)' if variant == 'duplicate' else b'![report](source.md)')
                    (self.root / 'draft-copy.md').write_bytes(draft)
                    case['draft']['sha256'] = hashlib.sha256(draft).hexdigest()
                result, target = self.invoke(case, 'link_' + variant)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertFalse((target / 'inference.json').exists())

    def test_snapshot_draft_can_select_an_immutable_committed_report(self):
        case, draft = self.snapshot_case()
        case['sources'][0] = self.case()['sources'][0]
        case['draft']['path'] = 'draft.md'
        result, target = self.invoke(case)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((target / 'draft.source').read_bytes(), draft)
        self.assertEqual((target / 'source-1.source').read_bytes(), self.source)
        packet = json.loads((target / 'packet.json').read_text())
        self.assertEqual(packet['sources'][0]['commit'], self.commit)
        receipt = json.loads((target / 'receipt.json').read_text())
        self.assertEqual(receipt['git_blob_bytes_read'], len(self.source))
        self.assertEqual(receipt['snapshot_bytes_read'], len(draft))
        self.assertEqual(receipt['git_commands'], 3)

    def test_snapshot_result_refuses_reuse_after_inputs_change(self):
        case, _ = self.snapshot_case()
        result, target = self.invoke(case)
        self.assertEqual(result.returncode, 0, result.stderr)
        before = {p.name: p.read_bytes() for p in target.iterdir()}
        (self.root / 'draft-copy.md').write_bytes(b'New draft')
        result, _ = self.invoke(case)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual({p.name: p.read_bytes() for p in target.iterdir()}, before)

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

    def test_ready_inference_contains_only_assertion_context_and_complete_source_text(self):
        result, target = self.invoke(self.case())
        self.assertEqual(result.returncode, 0, result.stderr)
        raw = (target / 'inference.json').read_bytes()
        self.assertEqual(json.loads(raw), {
            'assertion': 'The report says “Unknown costs remain.”',
            'draft_context': 'Opening.\nThe report says “Unknown costs remain.”\nClosing.\n',
            'sources': [{'id': 'source-1', 'text':
                         'Unknown costs remain.\nA separate qualification.\n'}],
        })
        receipt = json.loads((target / 'receipt.json').read_text())
        self.assertEqual(receipt['artifacts']['inference.json'], {
            'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)})

    def test_repeated_assertion_in_context_cannot_produce_inference(self):
        case = self.case()
        repeated = ('Opening.\n' + self.assertion + '\n' + self.assertion + '\n').encode()
        (self.repo / 'draft.md').write_bytes(repeated)
        self.git('add', 'draft.md')
        self.git('-c', 'core.hooksPath=/dev/null', '-c', 'user.name=Test',
                 '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'repeated assertion')
        case['draft'].update(commit=self.git('rev-parse', 'HEAD').decode().strip(),
                             sha256=hashlib.sha256(repeated).hexdigest())
        result, target = self.invoke(case)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(json.loads((target / 'packet.json').read_text())['draft']['status'],
                         'malformed_context')
        self.assertFalse((target / 'inference.json').exists())

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
                self.assertFalse((target / 'inference.json').exists())

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
                self.assertFalse((target / 'inference.json').exists())

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
        self.assertEqual(json.loads((target / 'inference.json').read_text())['sources'], [
            {'id': 'source-1', 'text': self.draft.decode()},
            {'id': 'source-2', 'text': self.source.decode()}])

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
        inference = json.loads((target / 'inference.json').read_bytes())
        self.assertEqual(inference['draft_context'], 'The report says “Café”.\r\n')
        self.assertEqual(inference['sources'], [
            {'id': 'source-1', 'text': 'Cafe\u0301\r\nAnother line.\r\n'}])


if __name__ == '__main__':
    unittest.main()
