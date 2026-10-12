"""Retain both question identities through whole-invocation accounting."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_comparison_runner import service
from test_ordinary_invocation import claim_fixture, write, ref
from test_question_treatments import CURRENT_QUESTION


def paired_fixture(root, endpoint):
    command, output = claim_fixture(root, endpoint, seconds=90)
    spec_path, bindings_path = root / 'spec.json', root / 'bindings.json'
    spec = json.loads(spec_path.read_text())
    bindings = json.loads(bindings_path.read_text())
    cases = []
    dependencies = [x for x in bindings['dependencies'] if x['role'] not in {'inference', 'corpus'}]
    for n in range(1, 14):
        case = f'c{n:02d}'
        path = root / f'new-{case}.md'
        path.write_text('Status: non_ready\n' if n == 13 else 'Assertion: alpha.\nSource: alpha.\n')
        item = ref(path, 'inference', case)
        dependencies.append(item)
        cases.append(dict(id=case, status='unavailable' if n == 13 else 'ready',
                          input=dict(path=str(path), sha256=item['sha256'])))
    corpus, control = root / 'new-corpus.json', root / 'new-control.json'
    write(corpus, dict(preparations=[dict(case=c['id'], status='non_ready' if c['id'] == 'c13' else 'ready',
                                        exit_code=2 if c['id'] == 'c13' else 0) for c in cases]))
    write(control, dict(case_id='c13', status='non_ready', quotation_status='unavailable',
                       sources=[dict(status='controlled_unavailable', availability='controlled_unavailable',
                                     observed_sha256=None, file=None)]))
    dependencies += [ref(corpus, 'corpus', 'manifest'), ref(control, 'corpus', 'c13-packet')]
    spec.update(version=2, cases=cases, treatments=[
        dict(id='current', question=CURRENT_QUESTION),
        dict(id='revised', question='Assess the assertion using the supplied evidence.')])
    bindings['dependencies'] = dependencies
    command[command.index('--spec-sha256') + 1] = write(spec_path, spec)
    command[command.index('--bindings-sha256') + 1] = write(bindings_path, bindings)
    return command, output


class TreatmentInvocationCLI(unittest.TestCase):
    def test_paired_run_reconciles_all_requests_and_zero_call_control(self):
        def reply(path):
            labels = ['supported', 'contradicted', 'unsupported_extension', 'unresolved']
            usage = {'input_tokens': 10, 'output_tokens': 1,
                     'input_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 0},
                     'output_tokens_details': {'reasoning_tokens': 0}}
            if path in {'/jev', '/decisions'}:
                answer = dict(type='choice', name='claim_relation', choice='supported', confidence=1,
                              probabilities={k: int(k == 'supported') for k in labels})
                if path == '/decisions':
                    answer['probabilities'] = [dict(value=k, probability=v)
                                               for k, v in answer['probabilities'].items()]
                return dict(model='fixture-jev' if path == '/jev' else 'gpt-6-luna',
                            answers={'claim_relation': answer} if path == '/jev' else [answer], usage=usage)
            response = dict(model='gpt-6.1-sol' if path == '/sol' else 'gpt-6-luna',
                            status='completed', usage=usage, output=[dict(type='message', role='assistant',
                            content=[dict(type='output_text', text='{"relation":"supported"}')])])
            return ('data: ' + json.dumps(dict(type='response.completed', response=response)) + '\n\n').encode()

        with tempfile.TemporaryDirectory() as temporary, service(reply) as (endpoint, received):
            root = Path(temporary)
            command, output = paired_fixture(root, endpoint.rsplit('/', 2)[0])
            result = subprocess.run(command, capture_output=True, text=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(len(received), 144)
            state = json.loads((output / 'state.json').read_text())
            self.assertEqual(state['status'], 'awaiting_closeout')
            summary = json.loads((output / 'run/summary.json').read_text())
            self.assertEqual(len(summary['slots']), 144)
            self.assertEqual({s['treatment'] for s in summary['slots']}, {'current', 'revised'})
            self.assertFalse(any(s['case'] == 'c13' for s in summary['slots']))
            self.assertEqual(summary['request_accounting']['attempts'], 144)
            self.assertEqual(summary['request_accounting']['input_tokens']['reported_sum'], 1440)
            recovery = json.loads((output / 'run-recovery.json').read_text())
            self.assertEqual(recovery['slots'], summary['slots'])
            self.assertEqual(recovery['request_accounting']['observed_attempts'], 144)


if __name__ == '__main__':
    unittest.main()
