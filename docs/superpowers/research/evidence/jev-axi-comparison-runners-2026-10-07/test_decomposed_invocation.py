"""Observe the complete decomposed schedule through the invocation CLI."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_comparison_runner import service
from test_ordinary_invocation import claim_fixture, write, ref
import test_decomposed_judgments as judgments


def decomposed_fixture(root, endpoint):
    command, output = claim_fixture(root, endpoint, seconds=90)
    spec_path, bindings_path = root / 'spec.json', root / 'bindings.json'
    spec, bindings = json.loads(spec_path.read_text()), json.loads(bindings_path.read_text())
    dependencies = [x for x in bindings['dependencies'] if x['role'] not in {'inference', 'corpus'}]
    cases = []
    for n in range(1, 26):
        case = f'c{n:02d}'
        path = root / f'new-{case}.json'
        write(path, {'status': 'non_ready'} if n == 25 else {
            'assertion': 'Alpha was measured.', 'draft_context': 'Alpha was measured.\n',
            'sources': [{'id': 'source-1', 'text': 'No measurement was made.\n'}]})
        item = ref(path, 'inference', case)
        dependencies.append(item)
        cases.append(dict(id=case, status='unavailable' if n == 25 else 'ready',
                          input=dict(path=str(path), sha256=item['sha256'])))
    corpus, control = root / 'new-corpus.json', root / 'new-control.json'
    write(corpus, dict(preparations=[dict(case=c['id'], status='non_ready' if c['id'] == 'c25' else 'ready',
                                        exit_code=2 if c['id'] == 'c25' else 0) for c in cases]))
    write(control, dict(case_id='c25', status='non_ready', quotation_status='unavailable',
                       sources=[dict(status='controlled_unavailable', availability='controlled_unavailable',
                                     observed_sha256=None, file=None)]))
    dependencies += [ref(corpus, 'corpus', 'manifest'), ref(control, 'corpus', 'c25-packet')]
    spec.update(version=3, cases=cases, treatments=[
        dict(id='direct', questions=[dict(id='claim_relation', **judgments.QUESTIONS['direct'])]),
        dict(id='decomposed', questions=[dict(id=q['id'], instructions=q['instructions'],
            options={o['id']: o['description'] for o in q['options']}) for q in judgments.QUESTIONS['decomposed']])])
    bindings['dependencies'] = dependencies
    command[command.index('--spec-sha256') + 1] = write(spec_path, spec)
    command[command.index('--bindings-sha256') + 1] = write(bindings_path, bindings)
    return command, output


class DecomposedInvocationCLI(unittest.TestCase):
    def test_all_288_groups_reconcile_without_multiplying_usage_by_question_count(self):
        def reply(path):
            value = judgments.DecomposedJudgmentsCLI.response(self, '/luna' if path == '/sol' else path,
                received[-1], dict(interpretability='clear', relevant_conflict='no',
                                  incompatible_fact='yes', complete_warrant='no'))
            return value.replace(b'gpt-6-luna', b'gpt-6.1-sol') if path == '/sol' else value
        with tempfile.TemporaryDirectory() as temporary, service(reply) as (endpoint, received):
            root = Path(temporary)
            command, output = decomposed_fixture(root, endpoint.rsplit('/', 2)[0])
            result = subprocess.run(command, capture_output=True, text=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(len(received), 288)
            state = json.loads((output / 'state.json').read_text())
            self.assertEqual(state['status'], 'awaiting_closeout')
            summary = json.loads((output / 'run/summary.json').read_text())
            self.assertEqual(len(summary['slots']), 288)
            self.assertFalse(any(s['case'] == 'c25' for s in summary['slots']))
            self.assertEqual(summary['request_accounting']['input_tokens']['reported_sum'], 2880)
            self.assertEqual(summary['judgment_accounting'], dict(
                scheduled_request_groups=288, scheduled_questions=720,
                submitted_request_groups=288, submitted_questions=720, combinations=144))
            recovery = json.loads((output / 'run-recovery.json').read_text())
            self.assertEqual(recovery['slots'], summary['slots'])
            self.assertEqual(recovery['request_accounting']['observed_attempts'], 288)


if __name__ == '__main__':
    unittest.main()
