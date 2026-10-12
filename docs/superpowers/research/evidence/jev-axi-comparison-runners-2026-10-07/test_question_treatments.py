"""Observe matched question treatments through the runner CLI and fake HTTP."""
import copy
import json
import unittest
import test_comparison_runner as fixtures
from test_comparison_runner import service


class QuestionTreatmentsCLI(unittest.TestCase):
    setUp = fixtures.ComparisonCLI.setUp
    cli = fixtures.ComparisonCLI.cli
    prepare = fixtures.ComparisonCLI.prepare
    run_bundle = fixtures.ComparisonCLI.run_bundle

    def paired_fixture(self, endpoint):
        self.spec['conditions'][0]['endpoint'] = endpoint
        self.bundle = self.root / 'paired'
        self.spec['version'] = 2
        self.spec['treatments'] = [
            {'id': 'current', 'question': CURRENT_QUESTION},
            {'id': 'revised', 'question': 'Which relation does the whole assertion warrant?'}]
        self.spec['cases'].append(dict(copy.deepcopy(self.spec['cases'][0]), id='c02'))
        self.spec['cases'].append(dict(copy.deepcopy(self.spec['cases'][0]),
                                       id='c03', status='unavailable'))
        base = self.spec['conditions'][0]
        self.spec['conditions'] = [
            dict(base, id='jev', adapter='jev', model='fixture-jev', endpoint=endpoint + '/jev'),
            dict(base, id='decisions', endpoint=endpoint + '/decisions'),
            dict(base, id='luna', adapter='responses', effort='low', endpoint=endpoint + '/luna')]

    def test_failed_request_stops_both_treatments_for_that_model(self):
        with service((500, {}, {'error': 'synthetic'})) as (endpoint, received):
            self.paired_fixture(endpoint)
            self.assertEqual(self.prepare().returncode, 0)
            output = self.root / 'failed'
            result = self.run_bundle(output)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(received), 3)
        summary = json.loads((output / 'summary.json').read_text())
        self.assertEqual([(s['condition'], s['treatment']) for s in summary['slots']
                          if s['status'] != 'unattempted'],
                         [('jev', 'current'), ('decisions', 'revised'), ('luna', 'current')])
        for slot in summary['slots']:
            if slot['status'] == 'unattempted':
                self.assertEqual(slot['reason'], 'condition_stopped')
        preserved = {p.name: p.read_bytes() for p in output.iterdir() if p.is_file()}
        self.assertNotEqual(self.run_bundle(output).returncode, 0)
        self.assertEqual(preserved, {p.name: p.read_bytes() for p in output.iterdir() if p.is_file()})

    def test_invalid_or_oversized_treatment_refuses_before_creating_preparation(self):
        with service({}) as (endpoint, received):
            self.paired_fixture(endpoint)
            treatments = copy.deepcopy(self.spec['treatments'])
            variants = [
                [dict(treatments[0], question='Changed baseline'), treatments[1]],
                [treatments[0], dict(treatments[1], question='')],
                [treatments[0], dict(treatments[1], question='x' * 131072)],
                [treatments[0], dict(treatments[1], id='current')]]
            for variant in variants:
                with self.subTest(questions=[len(t['question']) for t in variant]):
                    self.spec['treatments'] = variant
                    result = self.prepare()
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(self.bundle.exists())
            self.assertEqual(received, [])

    def test_pairs_deliver_only_the_selected_question_and_retain_matched_evidence(self):
        labels = ['supported', 'contradicted', 'unsupported_extension', 'unresolved']
        usage = {'input_tokens': 10, 'output_tokens': 1,
                 'input_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 0},
                 'output_tokens_details': {'reasoning_tokens': 0}}

        def reply(path):
            if path.endswith(('/jev', '/decisions')):
                answer = dict(type='choice', name='claim_relation', choice='supported',
                              confidence=1, probabilities={key: int(key == 'supported') for key in labels})
                if path.endswith('/decisions'):
                    answer['probabilities'] = [dict(value=k, probability=v)
                                               for k, v in answer['probabilities'].items()]
                return dict(model='fixture-jev' if path.endswith('/jev') else 'gpt-6-luna',
                            answers={'claim_relation': answer} if path.endswith('/jev') else [answer],
                            usage=usage)
            response = dict(model='gpt-6-luna', status='completed', usage=usage, output=[
                dict(type='message', role='assistant', content=[
                    dict(type='output_text', text='{"relation":"supported"}')])])
            return ('data: ' + json.dumps(dict(type='response.completed', response=response)) + '\n\n').encode()

        with service(reply) as (endpoint, received):
            self.paired_fixture(endpoint)
            prepared = self.prepare()
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            result = self.run_bundle(self.root / 'result')
            self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads((self.root / 'result/summary.json').read_text())
        self.assertEqual([(s['case'], s['condition'], s['treatment']) for s in summary['slots']], [
            ('c01', 'jev', 'current'), ('c01', 'jev', 'revised'),
            ('c01', 'decisions', 'revised'), ('c01', 'decisions', 'current'),
            ('c01', 'luna', 'current'), ('c01', 'luna', 'revised'),
            ('c02', 'decisions', 'current'), ('c02', 'decisions', 'revised'),
            ('c02', 'luna', 'revised'), ('c02', 'luna', 'current'),
            ('c02', 'jev', 'revised'), ('c02', 'jev', 'current')])
        self.assertEqual(len(received), 12)
        questions = {t['id']: t['question'] for t in self.spec['treatments']}
        for index, (slot, payload) in enumerate(zip(summary['slots'], received)):
            self.assertEqual(slot['status'], 'completed')
            attempt = json.loads((self.root / f'result/attempt-{index:04d}.json').read_text())
            self.assertEqual(attempt['treatment'], slot['treatment'])
            self.assertEqual(attempt['request'], payload)
            if slot['condition'] == 'jev':
                question = payload['questions']['claim_relation']
                self.assertEqual(list(question['criteria']), labels)
                instruction, state = question['instructions'], payload['state']
            elif slot['condition'] == 'decisions':
                question = payload['questions'][0]
                self.assertEqual([c['value'] for c in question['choices']], labels)
                instruction, state = question['instructions'], payload['input']
            else:
                instruction = payload['instructions'].split('\nsupported:', 1)[0]
                state = payload['input'][0]['content'][0]['text']
            self.assertEqual(instruction, questions[slot['treatment']])
            self.assertEqual(state, self.input.read_text())
        self.assertEqual(summary['request_accounting']['attempts'], 12)
        self.assertEqual(summary['request_accounting']['input_tokens']['reported_sum'], 120)


CURRENT_QUESTION = (
    'Considering only the supplied sources, what relation does the designated assertion '
    'have to their evidence? Respect the assertion\'s scope and any explicit qualifications '
    'in the supplied evidence. Do not decide global truth or recommend an action.\n\n'
    'Assess evidential warrant, including when the assertion says that reports establish '
    'a fact: a derivative assertion adds no independent warrant beyond its supplied '
    'cited basis and qualifications. A statement that a fact is unestablished limits '
    'warrant; it does not, by itself, establish an incompatible event or state of affairs. '
    'Conflicting independent factual accounts that the supplied context cannot resolve '
    'remain `unresolved`.')


if __name__ == '__main__':
    unittest.main()
