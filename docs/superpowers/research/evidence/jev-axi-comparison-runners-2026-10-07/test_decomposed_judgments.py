"""Observe direct and decomposed judgments through the CLI and fake HTTP."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
import test_comparison_runner as fixtures
from test_comparison_runner import service


QUESTIONS = json.loads((Path(__file__).parents[1] /
    'jev-axi-decomposed-judgment-preparation-2026-10-13/questions.json').read_text())


class DecomposedJudgmentsCLI(unittest.TestCase):
    setUp = fixtures.ComparisonCLI.setUp
    cli = fixtures.ComparisonCLI.cli
    prepare = fixtures.ComparisonCLI.prepare
    run_bundle = fixtures.ComparisonCLI.run_bundle

    def fixture(self, endpoint):
        self.input.write_text(json.dumps({
            'assertion': 'Alpha was measured.', 'draft_context': 'Alpha was measured.\n',
            'sources': [{'id': 'source-1', 'text': 'No measurement was made.\n'}]}))
        self.spec['cases'][0]['input']['sha256'] = hashlib.sha256(self.input.read_bytes()).hexdigest()
        self.spec['version'] = 3
        self.spec['treatments'] = [
            {'id': 'direct', 'questions': [dict(id='claim_relation', **QUESTIONS['direct'])]},
            {'id': 'decomposed', 'questions': [dict(id=q['id'], instructions=q['instructions'],
                options={o['id']: o['description'] for o in q['options']})
                for q in QUESTIONS['decomposed']]}]
        base = self.spec['conditions'][0]
        self.spec['conditions'] = [
            dict(base, id='jev', adapter='jev', model='fixture-jev', endpoint=endpoint + '/jev'),
            dict(base, id='decisions', endpoint=endpoint + '/decisions'),
            dict(base, id='luna', adapter='responses', effort='low', endpoint=endpoint + '/luna')]

    def test_preparation_binds_two_treatments_and_same_clean_input(self):
        with service({}) as (endpoint, received):
            self.fixture(endpoint)
            self.spec['cases'].append(dict(copy.deepcopy(self.spec['cases'][0]),
                                           id='c02', status='unavailable'))
            result = self.prepare()
            self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((self.bundle / 'manifest.json').read_text())
        self.assertEqual(manifest['schedule'], [
            {'case': 'c01', 'condition': 'jev', 'treatment': 'direct'},
            {'case': 'c01', 'condition': 'jev', 'treatment': 'decomposed'},
            {'case': 'c01', 'condition': 'decisions', 'treatment': 'decomposed'},
            {'case': 'c01', 'condition': 'decisions', 'treatment': 'direct'},
            {'case': 'c01', 'condition': 'luna', 'treatment': 'direct'},
            {'case': 'c01', 'condition': 'luna', 'treatment': 'decomposed'}])
        self.assertEqual(manifest['treatments'], self.spec['treatments'])
        self.assertEqual((self.bundle / 'input-000.txt').read_bytes(), self.input.read_bytes())
        self.assertEqual(received, [])

    def response(self, path, payload, values):
        usage = {'input_tokens': 10, 'output_tokens': 1,
                 'input_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 0},
                 'output_tokens_details': {'reasoning_tokens': 0}}
        if path.endswith('/luna'):
            keys = payload['text']['format']['schema']['required']
            answer = ({'relation': 'contradicted'} if keys == ['relation'] else values)
            response = dict(model='gpt-6-luna', status='completed', usage=usage, output=[
                dict(type='message', role='assistant', content=[
                    dict(type='output_text', text=json.dumps(answer))])])
            return ('data: ' + json.dumps(dict(type='response.completed', response=response)) + '\n\n').encode()
        questions = payload['questions']
        if isinstance(questions, dict):
            questions = [dict(name=k, options=v['criteria']) for k, v in questions.items()]
        else:
            questions = [dict(name=q['name'], options=[o['value'] for o in q['choices']])
                         for q in questions]
        answers = []
        for question in questions:
            name = question['name']
            choice = 'contradicted' if name == 'claim_relation' else values[name]
            probabilities = {key: int(key == choice) for key in question['options']}
            if path.endswith('/decisions'):
                probabilities = [dict(value=k, probability=v) for k, v in probabilities.items()]
            answers.append(dict(type='choice', name=name, choice=choice, confidence=1,
                                probabilities=probabilities))
        return dict(model='fixture-jev' if path.endswith('/jev') else 'gpt-6-luna', usage=usage,
                    answers={a['name']: a for a in answers} if path.endswith('/jev') else answers)

    def test_four_judgments_share_one_request_and_combination_preserves_request_cost(self):
        values = dict(interpretability='clear', relevant_conflict='no',
                      incompatible_fact='yes', complete_warrant='no')
        def reply(path):
            return self.response(path, received[-1], values)
        with service(reply) as (endpoint, received):
            self.fixture(endpoint)
            self.assertEqual(self.prepare().returncode, 0)
            output = self.root / 'result'
            result = self.run_bundle(output)
            self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads((output / 'summary.json').read_text())
        self.assertEqual(len(received), 6)
        for index, (slot, payload) in enumerate(zip(summary['slots'], received)):
            self.assertEqual(slot['status'], 'completed')
            attempt = json.loads((output / f'attempt-{index:04d}.json').read_text())
            self.assertEqual(attempt['relation'], 'contradicted')
            self.assertEqual(attempt['judgment_status'], 'classified')
            self.assertEqual(attempt['question_count'], 4 if slot['treatment'] == 'decomposed' else 1)
            if slot['treatment'] == 'decomposed':
                self.assertEqual(attempt['component_answers'], values)
                self.assertGreaterEqual(attempt['combination_duration_ms'], 0)
            else:
                self.assertIsNone(attempt['component_answers'])
                self.assertIsNone(attempt['combination_duration_ms'])
            if slot['condition'] == 'jev':
                self.assertEqual(payload['state'], self.input.read_text())
                questions = [dict(id=k, instructions=q['instructions'], options=q['criteria'])
                             for k, q in payload['questions'].items()]
            elif slot['condition'] == 'decisions':
                self.assertEqual(payload['input'], self.input.read_text())
                questions = [dict(id=q['name'], instructions=q['instructions'],
                    options={o['value']: o['description'] for o in q['choices']}) for q in payload['questions']]
            else:
                self.assertEqual(payload['input'][0]['content'][0]['text'], self.input.read_text())
                if slot['treatment'] == 'direct':
                    self.assertEqual(payload['instructions'], QUESTIONS['direct']['instructions'] + '\n' +
                        '\n'.join(key + ': ' + value for key, value in QUESTIONS['direct']['options'].items()))
                    self.assertEqual(payload['text']['format']['name'], 'claim_relation')
                else:
                    self.assertEqual(payload['text']['format']['schema']['required'], list(values))
                continue
            expected = next(t['questions'] for t in self.spec['treatments'] if t['id'] == slot['treatment'])
            self.assertEqual(questions, expected)
        self.assertEqual(summary['request_accounting']['attempts'], 6)
        self.assertEqual(summary['request_accounting']['input_tokens']['reported_sum'], 60)
        self.assertEqual(summary['judgment_accounting'], {
            'scheduled_request_groups': 6, 'scheduled_questions': 15,
            'submitted_request_groups': 6, 'submitted_questions': 15,
            'combinations': 3})

    def test_duplicate_envelope_keys_cannot_supply_a_judgment(self):
        original = copy.deepcopy(self.spec)
        for adapter in ('jev', 'decisions', 'responses'):
            with self.subTest(adapter=adapter):
                self.spec = copy.deepcopy(original)
                def reply(path):
                    value = self.response(path, received[-1], dict(interpretability='clear',
                        relevant_conflict='no', incompatible_fact='yes', complete_warrant='no'))
                    if isinstance(value, bytes):
                        return value.replace(b'"response":', b'"response":null,"response":', 1)
                    raw = json.dumps(value).encode()
                    return raw.replace(b'"answers":', b'"answers":null,"answers":', 1)
                with service(reply) as (endpoint, received):
                    self.fixture(endpoint)
                    self.bundle = self.root / adapter
                    self.spec['conditions'] = [c for c in self.spec['conditions'] if c['adapter'] == adapter]
                    self.assertEqual(self.prepare().returncode, 0)
                    output = self.root / (adapter + '-result')
                    result = self.run_bundle(output)
                    self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(len(received), 1)
                attempt = json.loads((output / 'attempt-0000.json').read_text())
                self.assertEqual(attempt['status'], 'invalid_response')
                self.assertIsNone(attempt['relation'])
                self.assertIsNone(attempt['component_answers'])
                self.assertTrue((output / attempt['response_body']).read_bytes())

    def test_ready_input_requires_clean_complete_evidence_fields(self):
        with service({}) as (endpoint, received):
            self.fixture(endpoint)
            packet = json.loads(self.input.read_text())
            variants = [dict(packet, expected_relation='contradicted'),
                        dict(packet, draft_context='No designated assertion.'),
                        dict(packet, draft_context='Alpha was measured. Alpha was measured.'),
                        dict(packet, sources=[]),
                        dict(packet, sources=[dict(packet['sources'][0], commit='label-hint')]),
                        dict(packet, sources=[dict(packet['sources'][0], id='contradicted')])]
            for index, value in enumerate(variants):
                with self.subTest(value=value):
                    self.bundle = self.root / f'invalid-{index}'
                    self.input.write_text(json.dumps(value))
                    self.spec['cases'][0]['input']['sha256'] = hashlib.sha256(self.input.read_bytes()).hexdigest()
                    result = self.prepare()
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(self.bundle.exists())
            self.assertEqual(received, [])

    def test_combination_precedence_keeps_abstentions_and_inconsistency_without_stopping(self):
        examples = [
            (['blocked', 'yes', 'yes', 'yes'], 'unresolved', 'classified'),
            (['unanswerable', 'no', 'no', 'yes'], None, 'judgment_abstained'),
            (['clear', 'yes', 'yes', 'yes'], 'unresolved', 'classified'),
            (['clear', 'unanswerable', 'yes', 'no'], None, 'judgment_abstained'),
            (['clear', 'no', 'unanswerable', 'yes'], None, 'judgment_abstained'),
            (['clear', 'no', 'yes', 'yes'], None, 'inconsistent_answers'),
            (['clear', 'no', 'yes', 'no'], 'contradicted', 'classified'),
            (['clear', 'no', 'yes', 'unanswerable'], 'contradicted', 'classified'),
            (['clear', 'no', 'no', 'unanswerable'], None, 'judgment_abstained'),
            (['clear', 'no', 'no', 'yes'], 'supported', 'classified'),
            (['clear', 'no', 'no', 'no'], 'unsupported_extension', 'classified'),
            (['blocked', 'unanswerable', 'unanswerable', 'unanswerable'], 'unresolved', 'classified')]
        values = iter(examples)
        def reply(path):
            payload = received[-1]
            components = (next(values)[0] if len(payload['questions']) == 4 else
                          ['clear', 'no', 'yes', 'no'])
            return self.response(path, payload, dict(zip(
                ['interpretability', 'relevant_conflict', 'incompatible_fact', 'complete_warrant'], components)))
        with service(reply) as (endpoint, received):
            self.fixture(endpoint)
            self.spec['conditions'] = [self.spec['conditions'][1]]
            self.spec['cases'] = [dict(copy.deepcopy(self.spec['cases'][0]), id=f'c{i:02d}')
                                  for i in range(1, len(examples) + 1)]
            self.assertEqual(self.prepare().returncode, 0)
            output = self.root / 'result'
            result = self.run_bundle(output)
            self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads((output / 'summary.json').read_text())
        self.assertEqual(len(received), 24)
        self.assertTrue(all(s['status'] == 'completed' for s in summary['slots']))
        observed = []
        for index, slot in enumerate(summary['slots']):
            if slot['treatment'] == 'decomposed':
                attempt = json.loads((output / f'attempt-{index:04d}.json').read_text())
                observed.append((list(attempt['component_answers'].values()),
                                 attempt['relation'], attempt['judgment_status']))
        self.assertEqual(observed, examples)
        self.assertEqual(summary['judgment_accounting']['combinations'], 12)

    def test_incomplete_or_refused_answer_never_combines_even_when_first_answer_blocks(self):
        original = copy.deepcopy(self.spec)
        for variant in ('missing', 'refusal', 'extra', 'duplicate_name', 'bad_probability', 'wrong_type'):
            with self.subTest(variant=variant):
                self.spec = copy.deepcopy(original)
                def reply(path):
                    payload = received[-1]
                    response = self.response(path, payload, dict(interpretability='blocked',
                        relevant_conflict='no', incompatible_fact='no', complete_warrant='no'))
                    if len(payload['questions']) == 4:
                        answers = response['answers']
                        if variant == 'missing': answers.pop()
                        if variant == 'refusal': answers[-1] = dict(type='refusal', name='complete_warrant')
                        if variant == 'extra': answers.append(dict(answers[-1], name='extra'))
                        if variant == 'duplicate_name': answers[-1]['name'] = 'interpretability'
                        if variant == 'bad_probability': answers[-1]['probabilities'][0]['probability'] = True
                        if variant == 'wrong_type': answers[-1]['type'] = 'score'
                    return response
                with service(reply) as (endpoint, received):
                    self.fixture(endpoint)
                    self.spec['conditions'] = [self.spec['conditions'][1]]
                    self.spec['cases'].append(dict(copy.deepcopy(self.spec['cases'][0]), id='c02'))
                    self.bundle = self.root / variant
                    self.assertEqual(self.prepare().returncode, 0)
                    output = self.root / (variant + '-result')
                    result = self.run_bundle(output)
                    self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(len(received), 2)
                attempt = json.loads((output / 'attempt-0001.json').read_text())
                self.assertEqual(attempt['status'], 'refused' if variant == 'refusal' else 'invalid_response')
                self.assertIsNone(attempt['relation'])
                self.assertIsNone(attempt['component_answers'])
                self.assertIsNone(attempt['combination_duration_ms'])
                self.assertTrue(attempt['raw_response']['answers'])
                summary = json.loads((output / 'summary.json').read_text())
                self.assertTrue(all(s['status'] == 'unattempted' for s in summary['slots'][2:]))


if __name__ == '__main__':
    unittest.main()
