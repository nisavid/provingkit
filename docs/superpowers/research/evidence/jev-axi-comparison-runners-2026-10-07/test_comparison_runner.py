"""Exercise comparison preparation and execution through their public CLI."""
import copy
import hashlib
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

RUNNER = Path(__file__).with_name('comparison_runner.py')



@contextmanager
def service(reply, raw_received=None):
    received = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            raw = self.rfile.read(int(self.headers['Content-Length']))
            if raw_received is not None:
                raw_received.append(raw)
            received.append(json.loads(raw))
            value = reply(self.path) if callable(reply) else reply
            if callable(value):
                value(self)
                return
            status, headers = 200, {}
            if isinstance(value, tuple):
                status, headers, value = value
            body = value if isinstance(value, bytes) else json.dumps(value).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            for name, value in headers.items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}/v1/decisions', received
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


class ComparisonCLI(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.input = self.root / 'candidate.txt'
        self.input.write_text('Assertion: alpha.\nSource: alpha is recorded; benefit remains unknown.\n')
        self.spec = {
            'version': 1, 'kind': 'claim',
            'cases': [{'id': 'c01', 'status': 'ready', 'input': {
                'path': str(self.input),
                'sha256': hashlib.sha256(self.input.read_bytes()).hexdigest()}}],
            'conditions': [{'id': 'decisions', 'adapter': 'decisions',
                            'model': 'gpt-6-luna', 'effort': None,
                            'endpoint': 'http://127.0.0.1:1/v1/decisions',
                            'billing': 'local_test', 'auth_env': None,
                            'rates': {'input': '0.10', 'cached': '0',
                                      'write': '0', 'output': '0'}}],
            'limits': {'request_seconds': 2, 'run_seconds': 10,
                       'input_bytes': 65536, 'request_bytes': 131072,
                       'response_bytes': 1048576, 'requests_per_cell': 1}
        }
        self.spec_path = self.root / 'spec.json'
        self.bundle = self.root / 'prepared'

    def cli(self, *args):
        return subprocess.run([sys.executable, str(RUNNER), *map(str, args)],
                              capture_output=True, text=True, timeout=10)

    def prepare(self, *, coverage_mode='diagnostic'):
        if self.spec['kind'] == 'coverage':
            self.spec['mode'] = coverage_mode
        self.spec_path.write_text(json.dumps(self.spec))
        return self.cli('prepare', '--spec', self.spec_path, '--output', self.bundle)

    def run_bundle(self, output):
        return self.cli('run', '--prepared', self.bundle, '--manifest-sha256',
                        hashlib.sha256((self.bundle / 'manifest.json').read_bytes()).hexdigest(),
                        '--output', output, '--local-http')

    def test_prepare_preserves_complete_input_and_freezes_source_identity(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((self.bundle / 'manifest.json').read_text())
        self.assertEqual((self.bundle / manifest['cases'][0]['input']['path']).read_bytes(),
                         self.input.read_bytes())
        self.assertEqual(manifest['cases'][0]['input']['sha256'],
                         self.spec['cases'][0]['input']['sha256'])
        self.assertEqual(manifest['source_spec_sha256'],
                         hashlib.sha256(self.spec_path.read_bytes()).hexdigest())
        self.assertEqual(manifest['schedule'], [{'case': 'c01', 'condition': 'decisions'}])


    def test_changed_input_is_rejected_before_a_prepared_manifest_is_written(self):
        self.input.write_text('changed after selection\n')
        result = self.prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.bundle / 'manifest.json').exists())

    def test_evaluator_fields_cannot_enter_candidate_preparation(self):
        self.spec['cases'][0]['expected_relation'] = 'supported'
        result = self.prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.bundle / 'manifest.json').exists())


    def test_decisions_request_preserves_input_and_records_answer_usage_and_value(self):
        reply = {'model': 'gpt-6-luna', 'answers': [{
            'type': 'choice', 'name': 'claim_relation', 'choice': 'supported',
            'confidence': 0.9, 'probabilities': [
                {'value': 'supported', 'probability': 0.9},
                {'value': 'contradicted', 'probability': 0.04},
                {'value': 'unsupported_extension', 'probability': 0.04},
                {'value': 'unresolved', 'probability': 0.02}]}],
            'usage': {'input_tokens': 123, 'output_tokens': 0}}
        raw_received = []
        with service(reply, raw_received) as (endpoint, received):
            self.spec['conditions'][0]['endpoint'] = endpoint
            self.assertEqual(self.prepare().returncode, 0)
            manifest = self.bundle / 'manifest.json'
            output = self.root / 'run'
            result = self.cli('run', '--prepared', self.bundle, '--manifest-sha256',
                              hashlib.sha256(manifest.read_bytes()).hexdigest(),
                              '--output', output, '--local-http')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]['input'], self.input.read_text())
        self.assertEqual(received[0]['questions'][0]['name'], 'claim_relation')
        attempt = json.loads((output / 'attempt-0000.json').read_text())
        self.assertEqual((output / attempt['request_body']).read_bytes(), raw_received[0])
        self.assertEqual(attempt['payload_sha256'], hashlib.sha256(raw_received[0]).hexdigest())
        self.assertEqual(attempt['relation'], 'supported')
        self.assertEqual(attempt['raw_response'], reply)
        self.assertEqual(attempt['usage'], reply['usage'])
        self.assertEqual(attempt['api_rate_equivalent_usd'], '0.0000123')
        self.assertIsNone(attempt['confirmed_charge_usd'])
        self.assertGreaterEqual(attempt['duration_ms'], 0)
        summary = json.loads((output / 'summary.json').read_text())
        self.assertEqual(summary['slots'][0]['status'], 'completed')


    def test_invalid_answer_is_retained_and_stops_only_its_condition(self):
        good = {'model': 'gpt-6-luna', 'answers': [{
            'type': 'choice', 'name': 'claim_relation', 'choice': 'supported',
            'confidence': 1.0, 'probabilities': [
                {'value': key, 'probability': value} for key, value in [
                    ('supported', 1.0), ('contradicted', 0.0),
                    ('unsupported_extension', 0.0), ('unresolved', 0.0)]]}],
            'usage': {'input_tokens': 10}}
        bad = {'model': 'gpt-6-luna', 'answers': [], 'usage': {'input_tokens': 7}}
        with service(lambda path: bad if path.endswith('/bad') else good) as (endpoint, received):
            self.spec['conditions'][0]['endpoint'] = endpoint + '/bad'
            other = copy.deepcopy(self.spec['conditions'][0])
            other.update(id='other', endpoint=endpoint + '/good')
            self.spec['conditions'].append(other)
            other_case = copy.deepcopy(self.spec['cases'][0]); other_case['id'] = 'c02'
            self.spec['cases'].append(other_case)
            self.assertEqual(self.prepare().returncode, 0)
            manifest = self.bundle / 'manifest.json'; output = self.root / 'run'
            result = self.cli('run', '--prepared', self.bundle, '--manifest-sha256',
                              hashlib.sha256(manifest.read_bytes()).hexdigest(),
                              '--output', output, '--local-http')
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads((output / 'summary.json').read_text())
        statuses = {(s['case'], s['condition']): s['status'] for s in summary['slots']}
        self.assertEqual(statuses, {('c01', 'decisions'): 'invalid_response',
                                   ('c01', 'other'): 'completed',
                                   ('c02', 'decisions'): 'unattempted',
                                   ('c02', 'other'): 'completed'})
        self.assertEqual(len(received), 3)
        first = json.loads((output / 'attempt-0000.json').read_text())
        self.assertEqual(first['raw_response'], bad)
        self.assertEqual(first['api_rate_equivalent_usd'], '0.0000007')


    def test_responses_stream_waits_for_terminal_and_values_token_partitions_once(self):
        response = {'id': 'resp_test', 'model': 'gpt-6-luna', 'status': 'completed',
                    'service_tier': 'default', 'output': [
                        {'type': 'reasoning', 'id': 'rs_1', 'summary': []},
                        {'type': 'message', 'role': 'assistant', 'content': [
                            {'type': 'output_text', 'text': '{"relation":"supported"}'}]}],
                    'usage': {'input_tokens': 1000,
                              'input_tokens_details': {'cached_tokens': 200, 'cache_write_tokens': 100},
                              'output_tokens': 50, 'output_tokens_details': {'reasoning_tokens': 20}}}
        early = {'type': 'response.output_text.delta', 'delta': '{"relation":"contradicted"}'}
        done = {'type': 'response.completed', 'response': response}
        stream = ('data: ' + json.dumps(early) + '\n\n' +
                  'data: ' + json.dumps(done) + '\n\n').encode()
        with service(stream) as (endpoint, received):
            self.spec['conditions'][0].update(adapter='responses', endpoint=endpoint, effort='low',
                rates={'input': '0.10', 'cached': '0.01', 'write': '0.125', 'output': '0.50'})
            self.assertEqual(self.prepare().returncode, 0)
            manifest = self.bundle / 'manifest.json'; output = self.root / 'run'
            result = self.cli('run', '--prepared', self.bundle, '--manifest-sha256',
                              hashlib.sha256(manifest.read_bytes()).hexdigest(),
                              '--output', output, '--local-http')
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = received[0]
        self.assertTrue(payload['stream']); self.assertFalse(payload['store'])
        self.assertEqual(payload['reasoning'], {'effort': 'low'})
        self.assertEqual(payload['input'][0]['content'][0]['text'], self.input.read_text())
        self.assertTrue(payload['text']['format']['strict'])
        attempt = json.loads((output / 'attempt-0000.json').read_text())
        self.assertEqual(attempt['relation'], 'supported')
        self.assertEqual(attempt['api_rate_equivalent_usd'], '0.0001095')
        self.assertEqual(attempt['raw_response'], response)
        self.assertEqual(attempt['raw_events'], [early, done])


    def test_jev_choice_preserves_the_same_question_and_native_distribution(self):
        reply = {'model': 'jev-1.13.0', 'answers': {'claim_relation': {
            'type': 'choice', 'choice': 'unsupported_extension', 'confidence': 0.7,
            'probabilities': {'supported': 0.1, 'contradicted': 0.05,
                              'unsupported_extension': 0.8, 'unresolved': 0.05}}},
            'usage': {'input_tokens': 1000, 'output_tokens': 30}}
        with service(reply) as (endpoint, received):
            self.spec['conditions'][0].update(adapter='jev', model='jev-1.13.0', endpoint=endpoint,
                rates={'input': '0.042', 'cached': '0', 'write': '0', 'output': '0'})
            self.assertEqual(self.prepare().returncode, 0)
            manifest = self.bundle / 'manifest.json'; output = self.root / 'run'
            result = self.cli('run', '--prepared', self.bundle, '--manifest-sha256',
                              hashlib.sha256(manifest.read_bytes()).hexdigest(),
                              '--output', output, '--local-http')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(received[0]['state'], self.input.read_text())
        self.assertEqual(set(received[0]['questions']), {'claim_relation'})
        self.assertEqual(list(received[0]['questions']['claim_relation']['criteria']),
                         ['supported', 'contradicted', 'unsupported_extension', 'unresolved'])
        attempt = json.loads((output / 'attempt-0000.json').read_text())
        self.assertEqual(attempt['relation'], 'unsupported_extension')
        self.assertEqual(attempt['raw_response'], reply)
        self.assertEqual(attempt['api_rate_equivalent_usd'], '0.000042')


    def test_changed_prepared_source_is_refused_without_http_submission(self):
        with service({}) as (endpoint, received):
            self.spec['conditions'][0]['endpoint'] = endpoint
            self.assertEqual(self.prepare().returncode, 0)
            manifest = self.bundle / 'manifest.json'
            data = json.loads(manifest.read_text())
            (self.bundle / data['cases'][0]['input']['path']).write_text('different candidate')
            result = self.cli('run', '--prepared', self.bundle, '--manifest-sha256',
                              hashlib.sha256(manifest.read_bytes()).hexdigest(),
                              '--output', self.root / 'run', '--local-http')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(received, [])


    def test_inconsistent_usage_preserves_the_answer_without_inventing_value(self):
        response = {'model': 'gpt-6-luna', 'status': 'completed', 'output': [
            {'type': 'message', 'role': 'assistant', 'content': [
                {'type': 'output_text', 'text': '{"relation":"supported"}'}]}],
            'usage': {'input_tokens': 100,
                      'input_tokens_details': {'cached_tokens': 101, 'cache_write_tokens': 0},
                      'output_tokens': 10}}
        stream = ('data: ' + json.dumps({'type': 'response.completed', 'response': response}) + '\n\n').encode()
        with service(stream) as (endpoint, received):
            self.spec['conditions'][0].update(adapter='responses', endpoint=endpoint, effort='low',
                rates={'input': '0.10', 'cached': '0.01', 'write': '0.125', 'output': '0.50'})
            self.assertEqual(self.prepare().returncode, 0)
            manifest = self.bundle / 'manifest.json'; output = self.root / 'run'
            result = self.cli('run', '--prepared', self.bundle, '--manifest-sha256',
                              hashlib.sha256(manifest.read_bytes()).hexdigest(),
                              '--output', output, '--local-http')
        self.assertEqual(result.returncode, 0, result.stderr)
        attempt = json.loads((output / 'attempt-0000.json').read_text())
        self.assertEqual(attempt['status'], 'accounting_error')
        self.assertEqual(attempt['relation'], 'supported')
        self.assertEqual(attempt['usage'], response['usage'])
        self.assertIsNone(attempt['api_rate_equivalent_usd'])


    def test_input_only_adapters_refuse_inapplicable_rate_components(self):
        for adapter in ['jev', 'decisions']:
            for component in ['cached', 'write', 'output']:
                with self.subTest(adapter=adapter, component=component):
                    condition = self.spec['conditions'][0]
                    condition.update(adapter=adapter, rates={
                        'input': '0.10', 'cached': '0', 'write': '0', 'output': '0'})
                    condition['rates'][component] = '0.50'
                    self.spec_path.write_text(json.dumps(self.spec))
                    output = self.root / (adapter + '-' + component)
                    result = self.cli('prepare', '--spec', self.spec_path, '--output', output)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(output.exists())

    def test_malformed_response_bytes_survive_as_a_failed_attempt(self):
        raw = b'{"answers": incomplete'
        with service(raw) as (endpoint, received):
            self.spec['conditions'][0]['endpoint'] = endpoint
            self.assertEqual(self.prepare().returncode, 0)
            manifest = self.bundle / 'manifest.json'; output = self.root / 'run'
            result = self.cli('run', '--prepared', self.bundle, '--manifest-sha256',
                              hashlib.sha256(manifest.read_bytes()).hexdigest(),
                              '--output', output, '--local-http')
        self.assertEqual(result.returncode, 0, result.stderr)
        attempt = json.loads((output / 'attempt-0000.json').read_text())
        self.assertEqual(attempt['status'], 'invalid_response')
        self.assertEqual((output / attempt['response_body']).read_bytes(), raw)
        self.assertIsNone(attempt['raw_response'])
        self.assertIsNone(attempt['usage'])
        self.assertIsNone(attempt['api_rate_equivalent_usd'])
        self.assertEqual(len(received), 1)

    def test_stream_failures_and_refusals_retain_their_distinct_outcomes(self):
        usage = {'input_tokens': 12, 'output_tokens': 3,
                 'input_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 0}}
        responses = {
            'provider_failed': {'type': 'response.failed', 'response': {
                'status': 'failed', 'usage': usage, 'error': {'code': 'example'}}},
            'provider_incomplete': {'type': 'response.incomplete', 'response': {
                'status': 'incomplete', 'usage': usage,
                'incomplete_details': {'reason': 'example'}}},
            'refused': {'type': 'response.completed', 'response': {
                'status': 'completed', 'usage': usage, 'output': [{
                    'type': 'message', 'role': 'assistant', 'content': [
                        {'type': 'refusal', 'refusal': 'Cannot answer this fixture.'}]}]}},
            'stream_incomplete': {'type': 'response.output_text.delta',
                                  'delta': '{"relation":"supported"}'},
            'provider_error': {'type': 'error', 'code': 'example', 'message': 'fixture error'}
        }
        for status, event in responses.items():
            with self.subTest(status=status):
                self.bundle = self.root / ('prepared-' + status)
                raw = ('data: ' + json.dumps(event) + '\n\n').encode()
                with service(raw) as (endpoint, received):
                    self.spec['conditions'][0].update(adapter='responses', endpoint=endpoint, effort='low')
                    self.assertEqual(self.prepare().returncode, 0)
                    output = self.root / status
                    result = self.run_bundle(output)
                self.assertEqual(result.returncode, 0, result.stderr)
                attempt = json.loads((output / 'attempt-0000.json').read_text())
                self.assertEqual(attempt['status'], status)
                self.assertEqual(attempt['raw_events'], [event])
                self.assertEqual(attempt['usage'], event.get('response', {}).get('usage'))
                self.assertIsNone(attempt['relation'])
                self.assertEqual(len(received), 1)

    def test_response_cap_preserves_only_the_bounded_prefix_and_reservation(self):
        with service(b'x' * 200) as (endpoint, received):
            self.spec['conditions'][0]['endpoint'] = endpoint
            self.spec['limits']['response_bytes'] = 64
            self.assertEqual(self.prepare().returncode, 0)
            output = self.root / 'run'
            result = self.run_bundle(output)
        self.assertEqual(result.returncode, 0, result.stderr)
        attempt = json.loads((output / 'attempt-0000.json').read_text())
        reservation = json.loads((output / 'request-0000.json').read_text())
        self.assertEqual(attempt['status'], 'response_limit')
        self.assertTrue(attempt['response_truncated'])
        self.assertEqual((output / attempt['response_body']).read_bytes(), b'x' * 64)
        self.assertEqual(reservation['payload_sha256'], attempt['payload_sha256'])
        self.assertEqual(reservation['status'], 'started')
        self.assertIsNone(attempt['usage'])
        self.assertEqual(len(received), 1)

    def test_claim_response_cap_retains_complete_terminal_usage_without_accepting_completion(self):
        usage = {'input_tokens': 100, 'output_tokens': 10,
                 'input_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 0}}
        response = {'model': 'gpt-6-luna', 'status': 'completed', 'usage': usage,
                    'output': [{'type': 'message', 'role': 'assistant', 'content': [
                        {'type': 'output_text', 'text': '{"relation":"supported"}'}]}]}
        event = {'type': 'response.completed', 'response': response}
        prefix = ('data: ' + json.dumps(event) + '\n\n').encode()
        with service(prefix + b'x' * 20) as (endpoint, received):
            self.spec['conditions'][0].update(adapter='responses', endpoint=endpoint, effort='low',
                rates={'input': '0.10', 'cached': '0', 'write': '0', 'output': '0.50'})
            self.spec['limits']['response_bytes'] = len(prefix)
            self.assertEqual(self.prepare().returncode, 0)
            output = self.root / 'run'; result = self.run_bundle(output)
        self.assertEqual(result.returncode, 0, result.stderr)
        attempt = json.loads((output / 'attempt-0000.json').read_text())
        self.assertEqual(attempt['status'], 'response_limit')
        self.assertEqual((output / attempt['response_body']).read_bytes(), prefix)
        self.assertEqual(attempt['raw_events'], [event])
        self.assertEqual(attempt['usage'], usage)
        self.assertIsNone(attempt['relation'])
        self.assertEqual(attempt['api_rate_equivalent_usd'], '0.000015')
        accounting = json.loads((output / 'summary.json').read_text())['request_accounting']
        self.assertEqual(accounting['known_api_rate_equivalent_usd'], '0.000015')
        self.assertEqual(accounting['unvalued_attempts'], 0)

    def test_claim_response_cap_does_not_value_incomplete_or_conflicting_terminal_evidence(self):
        usage = {'input_tokens': 100, 'output_tokens': 10,
                 'input_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 0}}
        terminal = ('data: ' + json.dumps({'type': 'response.completed', 'response': {
            'model': 'gpt-6-luna', 'status': 'completed', 'usage': usage, 'output': []}}) + '\n\n').encode()
        for label, prefix in [('incomplete', terminal[:-2]), ('conflicting', terminal + terminal)]:
            with self.subTest(label=label):
                self.bundle = self.root / ('prepared-' + label)
                with service(prefix + b'x' * 20) as (endpoint, received):
                    self.spec['conditions'][0].update(adapter='responses', endpoint=endpoint, effort='low')
                    self.spec['limits']['response_bytes'] = len(prefix)
                    self.assertEqual(self.prepare().returncode, 0)
                    output = self.root / ('run-' + label); result = self.run_bundle(output)
                self.assertEqual(result.returncode, 0, result.stderr)
                attempt = json.loads((output / 'attempt-0000.json').read_text())
                self.assertEqual(attempt['status'], 'response_limit')
                self.assertIsNone(attempt['usage'])
                self.assertIsNone(attempt['api_rate_equivalent_usd'])

    def test_request_deadline_preserves_partial_body_without_retry(self):
        def slow_body(handler):
            handler.send_response(200)
            handler.send_header('Content-Length', '100')
            handler.end_headers()
            handler.wfile.write(b'partial'); handler.wfile.flush()
            time.sleep(1)
        with service(lambda _: slow_body) as (endpoint, received):
            self.spec['conditions'][0]['endpoint'] = endpoint
            self.spec['limits']['request_seconds'] = 0.25
            self.assertEqual(self.prepare().returncode, 0)
            output = self.root / 'run'
            result = self.run_bundle(output)
        self.assertEqual(result.returncode, 0, result.stderr)
        attempt = json.loads((output / 'attempt-0000.json').read_text())
        self.assertEqual(attempt['status'], 'timeout')
        self.assertEqual((output / attempt['response_body']).read_bytes(), b'partial')
        self.assertTrue(attempt['residual_provider_work_unknown'])
        self.assertEqual(len(received), 1)

    def test_http_errors_are_recorded_and_redirects_are_not_followed(self):
        with service((307, {'Location': '/unexpected'}, b'fixture redirect')) as (endpoint, received):
            self.spec['conditions'][0]['endpoint'] = endpoint
            self.assertEqual(self.prepare().returncode, 0)
            output = self.root / 'run'
            result = self.run_bundle(output)
        self.assertEqual(result.returncode, 0, result.stderr)
        attempt = json.loads((output / 'attempt-0000.json').read_text())
        self.assertEqual(attempt['status'], 'http_error')
        self.assertEqual(attempt['http_status'], 307)
        self.assertEqual((output / attempt['response_body']).read_bytes(), b'fixture redirect')
        self.assertEqual(len(received), 1)

    def test_invalid_token_counts_and_probabilities_are_not_usable_results(self):
        examples = [
            ({'input_tokens': -1}, {'supported': 1.0, 'contradicted': 0,
                'unsupported_extension': 0, 'unresolved': 0}, 'accounting_error'),
            ({'input_tokens': True}, {'supported': 1.0, 'contradicted': 0,
                'unsupported_extension': 0, 'unresolved': 0}, 'accounting_error'),
            ({'input_tokens': 1.5}, {'supported': 1.0, 'contradicted': 0,
                'unsupported_extension': 0, 'unresolved': 0}, 'accounting_error'),
            ({'input_tokens': 10}, {'supported': 1.4, 'contradicted': -0.4,
                'unsupported_extension': 0, 'unresolved': 0}, 'invalid_response'),
        ]
        for index, (usage, probabilities, status) in enumerate(examples):
            with self.subTest(index=index):
                self.bundle = self.root / f'prepared-{index}'
                reply = {'model': 'jev-1.13.0', 'answers': {'claim_relation': {
                    'type': 'choice', 'choice': 'supported', 'confidence': 0.9,
                    'probabilities': probabilities}}, 'usage': usage}
                with service(reply) as (endpoint, received):
                    self.spec['conditions'][0].update(adapter='jev', model='jev-1.13.0', endpoint=endpoint)
                    self.assertEqual(self.prepare().returncode, 0)
                    output = self.root / f'run-{index}'
                    result = self.run_bundle(output)
                self.assertEqual(result.returncode, 0, result.stderr)
                attempt = json.loads((output / 'attempt-0000.json').read_text())
                self.assertEqual(attempt['status'], status)
                self.assertEqual(attempt['raw_response'], reply)
                if status == 'accounting_error':
                    self.assertIsNone(attempt['api_rate_equivalent_usd'])
                    self.assertEqual(attempt['relation'], 'supported')
                else:
                    self.assertIsNone(attempt['relation'])

    def test_preflight_refuses_bad_limits_duplicate_ids_and_oversized_payloads(self):
        original = copy.deepcopy(self.spec)
        changes = ['negative_limit', 'duplicate_case', 'unknown_condition_field', 'input_limit', 'request_limit']
        for change in changes:
            with self.subTest(change=change):
                self.spec = copy.deepcopy(original)
                self.bundle = self.root / change
                if change == 'negative_limit':
                    self.spec['limits']['response_bytes'] = -1
                elif change == 'duplicate_case':
                    self.spec['cases'].append(copy.deepcopy(self.spec['cases'][0]))
                elif change == 'unknown_condition_field':
                    self.spec['conditions'][0]['expected_relation'] = 'supported'
                elif change == 'input_limit':
                    self.spec['limits']['input_bytes'] = 1
                else:
                    self.spec['limits']['request_bytes'] = 1
                result = self.prepare()
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.bundle / 'manifest.json').exists())

    def test_schedule_rotates_conditions_and_keeps_unavailable_control_without_calls(self):
        other = copy.deepcopy(self.spec['conditions'][0]); other['id'] = 'other'
        self.spec['conditions'].append(other)
        for case_id, status in [('c02', 'ready'), ('c03', 'unavailable')]:
            case = copy.deepcopy(self.spec['cases'][0]); case.update(id=case_id, status=status)
            self.spec['cases'].append(case)
        self.assertEqual(self.prepare().returncode, 0)
        manifest = json.loads((self.bundle / 'manifest.json').read_text())
        self.assertEqual(manifest['schedule'], [
            {'case': 'c01', 'condition': 'decisions'}, {'case': 'c01', 'condition': 'other'},
            {'case': 'c02', 'condition': 'other'}, {'case': 'c02', 'condition': 'decisions'}])
        self.assertEqual(manifest['cases'][2]['status'], 'unavailable')

    def test_coverage_schedule_keeps_profile_pairs_and_counterbalances_by_case_ordinal(self):
        self.input.write_text(json.dumps({
            'task': 'Explain the review evidence.', 'ordinary': 'Read s01.',
            'deterministic': 'Review source: s01.',
            'sources': [{'id': 's01', 'path': 'review.md', 'content': 'Reviewed.\n',
                         'sha256': hashlib.sha256(b'Reviewed.\n').hexdigest()}]}))
        self.spec['kind'] = 'coverage'
        self.spec['cases'][0]['input']['sha256'] = hashlib.sha256(self.input.read_bytes()).hexdigest()
        for identity in ['c04', 'c02']:
            case = copy.deepcopy(self.spec['cases'][0]); case['id'] = identity
            self.spec['cases'].append(case)
        self.spec['limits'].update(cell_seconds=8, tool_operations=16,
                                  tool_result_bytes=131072, tool_total_bytes=2097152)
        template = self.spec['conditions'][0]
        self.spec['conditions'] = []
        for identity, effort, arm in [
                ('low_ordinary', 'low', 'ordinary'), ('low_added', 'low', 'deterministic'),
                ('medium_ordinary', 'medium', 'ordinary'), ('medium_added', 'medium', 'deterministic')]:
            condition = copy.deepcopy(template)
            condition.update(id=identity, adapter='responses', effort=effort, arm=arm)
            self.spec['conditions'].append(condition)
        result = self.prepare(coverage_mode='comparison')
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((self.bundle / 'manifest.json').read_text())
        self.assertEqual(manifest['mode'], 'comparison')
        self.assertEqual([(slot['case'], slot['condition']) for slot in manifest['schedule']], [
            ('c01', 'low_ordinary'), ('c01', 'low_added'),
            ('c01', 'medium_added'), ('c01', 'medium_ordinary'),
            ('c04', 'low_added'), ('c04', 'low_ordinary'),
            ('c04', 'medium_ordinary'), ('c04', 'medium_added'),
            ('c02', 'low_added'), ('c02', 'low_ordinary'),
            ('c02', 'medium_ordinary'), ('c02', 'medium_added')])

    def test_coverage_comparison_refuses_missing_or_duplicate_profile_arms(self):
        self.input.write_text(json.dumps({
            'task': 'Explain the review evidence.', 'ordinary': 'Read s01.',
            'deterministic': 'Review source: s01.',
            'sources': [{'id': 's01', 'path': 'review.md', 'content': 'Reviewed.\n',
                         'sha256': hashlib.sha256(b'Reviewed.\n').hexdigest()}]}))
        self.spec['kind'] = 'coverage'
        self.spec['cases'][0]['input']['sha256'] = hashlib.sha256(self.input.read_bytes()).hexdigest()
        self.spec['limits'].update(cell_seconds=8, tool_operations=16,
                                  tool_result_bytes=131072, tool_total_bytes=2097152)
        original = self.spec['conditions'][0]
        original.update(adapter='responses', effort='low', arm='ordinary')
        for label, arms in [('missing', ['ordinary']),
                            ('duplicate', ['ordinary', 'ordinary', 'deterministic'])]:
            with self.subTest(label=label):
                self.spec['conditions'] = [dict(original, id='condition_' + str(n), arm=arm)
                                           for n, arm in enumerate(arms)]
                self.spec_path.write_text(json.dumps(self.spec))
                output = self.root / label
                result = self.cli('prepare', '--spec', self.spec_path, '--output', output)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(output.exists())

    def test_existing_attempt_directory_is_not_reused_or_changed(self):
        with service({}) as (endpoint, received):
            self.spec['conditions'][0]['endpoint'] = endpoint
            self.assertEqual(self.prepare().returncode, 0)
            output = self.root / 'run'; output.mkdir()
            sentinel = output / 'attempt-0000.json'; sentinel.write_bytes(b'previous outcome\n')
            result = self.run_bundle(output)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sentinel.read_bytes(), b'previous outcome\n')
        self.assertEqual(list(output.iterdir()), [sentinel])
        self.assertEqual(received, [])

    def test_local_run_rejects_all_unsupported_endpoints_before_any_request(self):
        with service({}) as (endpoint, received):
            self.spec['conditions'][0]['endpoint'] = endpoint
            self.spec['conditions'].append(dict(self.spec['conditions'][0], id='other',
                                                endpoint='https://example.invalid/v1/decisions'))
            prepared = self.prepare()
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            output = self.root / 'run'; result = self.run_bundle(output)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('loopback endpoint', result.stderr)
        self.assertEqual(received, [])
        self.assertFalse(output.exists())

    def test_global_deadline_accounts_for_all_remaining_slots(self):
        def slow_body(handler):
            handler.send_response(200); handler.send_header('Content-Length', '100')
            handler.end_headers(); handler.wfile.write(b'prefix'); handler.wfile.flush()
            time.sleep(1)
        with service(lambda _: slow_body) as (endpoint, received):
            self.spec['conditions'][0]['endpoint'] = endpoint
            self.spec['limits']['run_seconds'] = 0.2
            other = copy.deepcopy(self.spec['conditions'][0]); other['id'] = 'other'
            self.spec['conditions'].append(other)
            self.assertEqual(self.prepare().returncode, 0)
            output = self.root / 'run'; result = self.run_bundle(output)
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads((output / 'summary.json').read_text())
        self.assertEqual(summary['slots'][0]['status'], 'timeout')
        self.assertEqual(summary['slots'][1]['status'], 'unattempted')
        self.assertEqual(summary['slots'][1]['reason'], 'run_deadline')
        self.assertLessEqual(len(received), 1)

    def test_returned_model_mismatch_keeps_usage_but_stops_the_affected_condition(self):
        response = {'model': 'gpt-6.1-sol', 'status': 'completed', 'output': [
            {'type': 'message', 'role': 'assistant', 'content': [
                {'type': 'output_text', 'text': '{"relation":"supported"}'}]}],
            'usage': {'input_tokens': 100, 'output_tokens': 10,
                      'input_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 0}}}
        raw = ('data: ' + json.dumps({'type': 'response.completed', 'response': response}) + '\n\n').encode()
        with service(raw) as (endpoint, received):
            self.spec['conditions'][0].update(adapter='responses', endpoint=endpoint, effort='low')
            other = copy.deepcopy(self.spec['cases'][0]); other['id'] = 'c02'
            self.spec['cases'].append(other)
            self.assertEqual(self.prepare().returncode, 0)
            output = self.root / 'run'; result = self.run_bundle(output)
        self.assertEqual(result.returncode, 0, result.stderr)
        attempt = json.loads((output / 'attempt-0000.json').read_text())
        self.assertEqual(attempt['status'], 'model_mismatch')
        self.assertEqual(attempt['raw_response'], response)
        self.assertEqual(attempt['usage'], response['usage'])
        self.assertEqual(attempt['returned_model'], 'gpt-6.1-sol')
        self.assertEqual(attempt['requested_model'], 'gpt-6-luna')
        self.assertIsNone(attempt['api_rate_equivalent_usd'])
        self.assertEqual(len(received), 1)
        summary = json.loads((output / 'summary.json').read_text())
        self.assertEqual(summary['slots'][1]['status'], 'unattempted')

    def test_claim_result_with_a_tool_request_is_not_accepted_as_a_final_answer(self):
        response = {'model': 'gpt-6-luna', 'status': 'completed', 'output': [
            {'type': 'function_call', 'call_id': 'call_read', 'name': 'read_source',
             'arguments': '{"source":"s01"}'},
            {'type': 'message', 'role': 'assistant', 'content': [
                {'type': 'output_text', 'text': '{"relation":"supported"}'}]}],
            'usage': {'input_tokens': 100, 'output_tokens': 10,
                      'input_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 0}}}
        raw = ('data: ' + json.dumps({'type': 'response.completed', 'response': response}) + '\n\n').encode()
        with service(raw) as (endpoint, received):
            self.spec['conditions'][0].update(adapter='responses', endpoint=endpoint, effort='low')
            other = copy.deepcopy(self.spec['cases'][0]); other['id'] = 'c02'
            self.spec['cases'].append(other)
            self.assertEqual(self.prepare().returncode, 0)
            output = self.root / 'run'; result = self.run_bundle(output)
        self.assertEqual(result.returncode, 0, result.stderr)
        attempt = json.loads((output / 'attempt-0000.json').read_text())
        self.assertEqual(attempt['status'], 'unexpected_tool_call')
        self.assertIsNone(attempt['relation'])
        self.assertEqual(attempt['raw_response'], response)
        self.assertEqual(attempt['usage'], response['usage'])
        self.assertEqual(len(received), 1)
        summary = json.loads((output / 'summary.json').read_text())
        self.assertEqual(summary['slots'][1]['status'], 'unattempted')

    def test_coverage_refusal_ends_its_cell_without_cancelling_the_next_case(self):
        self.input.write_text(json.dumps({
            'task': 'Explain what the supplied review covers.',
            'ordinary': 'Read the review source.', 'deterministic': 'Review source: s01.',
            'sources': [{'id': 's01', 'path': 'review.md', 'content': 'Reviewed candidate.\n',
                         'sha256': hashlib.sha256(b'Reviewed candidate.\n').hexdigest()}]}))
        self.spec['kind'] = 'coverage'
        self.spec['cases'][0]['input']['sha256'] = hashlib.sha256(self.input.read_bytes()).hexdigest()
        second_packet = {'task': 'Explain what the second review covers.',
                         'ordinary': 'Read the second review source.',
                         'deterministic': 'Second review source: s01.',
                         'sources': [{'id': 's01', 'path': 'second-review.md',
                                      'content': 'Second candidate reviewed.\n',
                                      'sha256': hashlib.sha256(b'Second candidate reviewed.\n').hexdigest()}]}
        second_input = self.root / 'second-candidate.json'
        second_input.write_text(json.dumps(second_packet))
        second = copy.deepcopy(self.spec['cases'][0]); second['id'] = 'c02'
        second['input'] = {'path': str(second_input),
                           'sha256': hashlib.sha256(second_input.read_bytes()).hexdigest()}
        self.spec['cases'].append(second)
        self.spec['limits'].update(cell_seconds=8, tool_operations=16,
                                  tool_result_bytes=131072, tool_total_bytes=2097152)
        usage = {'input_tokens': 100, 'output_tokens': 10,
                 'input_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 0}}
        responses = [
            {'model': 'gpt-6-luna', 'status': 'completed', 'usage': usage, 'output': [
                {'type': 'message', 'role': 'assistant', 'content': [
                    {'type': 'refusal', 'refusal': 'Synthetic refusal.'}]}]},
            {'model': 'gpt-6-luna', 'status': 'completed', 'usage': usage, 'output': [
                {'type': 'message', 'role': 'assistant', 'content': [
                    {'type': 'output_text', 'text': 'The source describes the reviewed candidate [s01].'}]}]}]
        refused_response = copy.deepcopy(responses[0])
        def reply(_):
            return ('data: ' + json.dumps({'type': 'response.completed',
                                          'response': responses.pop(0)}) + '\n\n').encode()
        raw_received = []
        with service(reply, raw_received) as (endpoint, received):
            self.spec['conditions'][0].update(adapter='responses', endpoint=endpoint,
                                               effort='low', arm='ordinary')
            prepared = self.prepare()
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            output = self.root / 'run'; result = self.run_bundle(output)
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads((output / 'summary.json').read_text())
        self.assertEqual(summary['coverage_mode'], 'diagnostic')
        self.assertEqual([(slot['case'], slot['status']) for slot in summary['slots']],
                         [('c01', 'refused'), ('c02', 'completed')])
        self.assertEqual(len(received), 2)
        self.assertEqual(received[0]['input'][0]['content'][0]['text'].split('\n\nSources: ')[0],
                         'Read the review source.')
        self.assertEqual(received[1]['input'][0]['content'][0]['text'].split('\n\nSources: ')[0],
                         second_packet['ordinary'])
        self.assertEqual((output / 'cell-0001' / 'request-0000.body').read_bytes(), raw_received[1])
        self.assertEqual(json.loads((output / 'cell-0001' / 'attempt-0000.json').read_text())['request_body'],
                         'request-0000.body')
        self.assertEqual(summary['slots'][1]['case'], 'c02')
        self.assertEqual(summary['slots'][1]['condition'], 'decisions')
        attempt = json.loads((output / 'cell-0000' / 'attempt-0000.json').read_text())
        self.assertEqual(attempt['raw_response'], refused_response)
        self.assertEqual(attempt['usage'], usage)
        self.assertGreater(attempt['duration_ms'], 0)
        refused = json.loads((output / 'cell-0000' / 'summary.json').read_text())
        self.assertIsNone(refused['answer'])
        self.assertEqual(refused['requests'], 1)

    def test_coverage_incomplete_output_preserves_the_failure_and_continues_with_fresh_cases(self):
        self.input.write_text(json.dumps({
            'task': 'Explain what the supplied review covers.',
            'ordinary': 'Read s01.', 'deterministic': 'Review source: s01.',
            'sources': [{'id': 's01', 'path': 'review.md', 'content': 'Candidate reviewed.\n',
                         'sha256': hashlib.sha256(b'Candidate reviewed.\n').hexdigest()}]}))
        self.spec['kind'] = 'coverage'
        self.spec['cases'][0]['input']['sha256'] = hashlib.sha256(self.input.read_bytes()).hexdigest()
        second = copy.deepcopy(self.spec['cases'][0]); second['id'] = 'c02'
        self.spec['cases'].append(second)
        self.spec['limits'].update(cell_seconds=8, tool_operations=16,
                                  tool_result_bytes=131072, tool_total_bytes=2097152)
        incomplete = {'model': 'gpt-6-luna', 'status': 'incomplete', 'output': [],
                      'incomplete_details': {'reason': 'max_output_tokens'},
                      'usage': {'input_tokens': 100, 'output_tokens': 40}}
        completed = {'model': 'gpt-6-luna', 'status': 'completed', 'output': [
            {'type': 'message', 'role': 'assistant', 'content': [
                {'type': 'output_text', 'text': 'The source reports a reviewed candidate [s01].'}]}]}
        faults = [
            ('provider_incomplete', ('data: ' + json.dumps({'type': 'response.incomplete',
                                                           'response': incomplete}) + '\n\n').encode()),
            ('stream_incomplete', b'data: {"type":"response.created"}\n\n'),
            ('invalid_response', b'not a valid response stream\n\ndata: {malformed}\n\n')]
        final = ('data: ' + json.dumps({'type': 'response.completed', 'response': completed}) + '\n\n').encode()
        for status, raw in faults:
            with self.subTest(status=status):
                responses = [raw, final]
                self.bundle = self.root / ('prepared-' + status)
                with service(lambda _: responses.pop(0)) as (endpoint, received):
                    self.spec['conditions'][0].update(adapter='responses', endpoint=endpoint,
                                                       effort='low', arm='ordinary')
                    prepared = self.prepare()
                    self.assertEqual(prepared.returncode, 0, prepared.stderr)
                    output = self.root / ('run-' + status)
                    result = self.run_bundle(output)
                self.assertEqual(result.returncode, 0, result.stderr)
                summary = json.loads((output / 'summary.json').read_text())
                self.assertEqual([slot['status'] for slot in summary['slots']], [status, 'completed'])
                self.assertEqual(len(received), 2)
                self.assertEqual(received[1]['input'], received[0]['input'])
                first = output / 'cell-0000'
                self.assertEqual((first / 'response-0000.body').read_bytes(), raw)
                cell = json.loads((first / 'summary.json').read_text())
                self.assertEqual(cell['requests'], 1)
                self.assertIsNone(cell['answer'])
                if status == 'provider_incomplete':
                    attempt = json.loads((first / 'attempt-0000.json').read_text())
                    self.assertEqual(attempt['usage'], incomplete['usage'])
                    self.assertEqual(attempt['raw_response'], incomplete)

    def test_coverage_timeout_ends_the_attempt_without_cancelling_a_later_case(self):
        self.input.write_text(json.dumps({
            'task': 'Explain the review evidence.', 'ordinary': 'Read s01.',
            'deterministic': 'Review source: s01.',
            'sources': [{'id': 's01', 'path': 'review.md', 'content': 'Reviewed.\n',
                         'sha256': hashlib.sha256(b'Reviewed.\n').hexdigest()}]}))
        self.spec['kind'] = 'coverage'
        self.spec['cases'][0]['input']['sha256'] = hashlib.sha256(self.input.read_bytes()).hexdigest()
        second = copy.deepcopy(self.spec['cases'][0]); second['id'] = 'c02'
        self.spec['cases'].append(second)
        self.spec['limits'].update(request_seconds=0.4, cell_seconds=8, tool_operations=16,
                                  tool_result_bytes=131072, tool_total_bytes=2097152)
        def slow_body(handler):
            handler.send_response(200); handler.send_header('Content-Length', '100')
            handler.end_headers(); handler.wfile.write(b'partial response'); handler.wfile.flush()
            time.sleep(0.7)
        completed = {'model': 'gpt-6-luna', 'status': 'completed', 'output': [
            {'type': 'message', 'role': 'assistant', 'content': [
                {'type': 'output_text', 'text': 'The review records the candidate [s01].'}]}]}
        replies = [slow_body, ('data: ' + json.dumps({'type': 'response.completed',
                                                     'response': completed}) + '\n\n').encode()]
        with service(lambda _: replies.pop(0)) as (endpoint, received):
            self.spec['conditions'][0].update(adapter='responses', endpoint=endpoint,
                                               effort='low', arm='ordinary')
            prepared = self.prepare()
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            output = self.root / 'run'; result = self.run_bundle(output)
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads((output / 'summary.json').read_text())
        self.assertEqual([slot['status'] for slot in summary['slots']], ['timeout', 'completed'])
        self.assertEqual(len(received), 2)
        self.assertEqual(received[1]['input'], received[0]['input'])
        attempt = json.loads((output / 'cell-0000' / 'attempt-0000.json').read_text())
        self.assertTrue(attempt['residual_provider_work_unknown'])
        self.assertIsNone(attempt['usage'])
        self.assertIsNone(attempt['confirmed_charge_usd'])
        self.assertEqual((output / 'cell-0000' / 'response-0000.body').read_bytes(), b'partial response')

    def test_coverage_response_limit_retains_prefix_and_continues_with_next_case(self):
        self.input.write_text(json.dumps({
            'task': 'Explain the review evidence.', 'ordinary': 'Read s01.',
            'deterministic': 'Review source: s01.',
            'sources': [{'id': 's01', 'path': 'review.md', 'content': 'Reviewed.\n',
                         'sha256': hashlib.sha256(b'Reviewed.\n').hexdigest()}]}))
        self.spec['kind'] = 'coverage'
        self.spec['cases'][0]['input']['sha256'] = hashlib.sha256(self.input.read_bytes()).hexdigest()
        self.spec['cases'].append(dict(self.spec['cases'][0], id='c02'))
        self.spec['limits'].update(response_bytes=1024, cell_seconds=8, tool_operations=16,
                                  tool_result_bytes=131072, tool_total_bytes=2097152)
        usage = {'input_tokens': 100, 'output_tokens': 10,
                 'input_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 0}}
        terminal = {'type': 'response.completed', 'response': {
            'model': 'gpt-6-luna', 'status': 'completed', 'usage': usage, 'output': [
                {'type': 'message', 'role': 'assistant', 'content': [
                    {'type': 'output_text', 'text': 'The source covers the candidate [s01].'}]}]}}
        prefix = ('data: ' + json.dumps(terminal) + '\n\n').encode()
        responses = [prefix + b'x' * 4096, prefix]
        with service(lambda _: responses.pop(0)) as (endpoint, received):
            self.spec['conditions'][0].update(adapter='responses', endpoint=endpoint,
                                               effort='low', arm='ordinary')
            prepared = self.prepare()
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            output = self.root / 'run'; result = self.run_bundle(output)
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads((output / 'summary.json').read_text())
        self.assertEqual([x['status'] for x in summary['slots']], ['response_limit', 'completed'])
        self.assertEqual(len(received), 2)
        attempt = json.loads((output / 'cell-0000' / 'attempt-0000.json').read_text())
        self.assertEqual((output / 'cell-0000' / 'response-0000.body').read_bytes(),
                         (prefix + b'x' * 4096)[:1024])
        self.assertEqual(attempt['status'], 'response_limit')
        self.assertEqual(attempt['raw_events'], [terminal])
        self.assertEqual(attempt['usage'], usage)
        self.assertEqual(attempt['api_rate_equivalent_usd'], '0.00001')
        self.assertEqual(summary['request_accounting']['known_api_rate_equivalent_usd'], '0.00002')

    def test_response_cap_does_not_hide_condition_model_or_accounting_errors(self):
        self.input.write_text(json.dumps({
            'task': 'Explain the review evidence.', 'ordinary': 'Read s01.',
            'deterministic': 'Review source: s01.',
            'sources': [{'id': 's01', 'path': 'review.md', 'content': 'Reviewed.\n',
                         'sha256': hashlib.sha256(b'Reviewed.\n').hexdigest()}]}))
        self.spec['kind'] = 'coverage'
        self.spec['cases'][0]['input']['sha256'] = hashlib.sha256(self.input.read_bytes()).hexdigest()
        self.spec['cases'].append(dict(self.spec['cases'][0], id='c02'))
        self.spec['limits'].update(response_bytes=1024, cell_seconds=8, tool_operations=16,
                                  tool_result_bytes=131072, tool_total_bytes=2097152)
        for expected, model, usage in [
            ('model_mismatch', 'different-model', {'input_tokens': 100, 'output_tokens': 10}),
            ('accounting_error', 'gpt-6-luna', {'input_tokens': -1, 'output_tokens': 10}),
        ]:
            with self.subTest(expected=expected):
                terminal = {'type': 'response.completed', 'response': {
                    'model': model, 'status': 'completed', 'usage': usage, 'output': []}}
                response = ('data: ' + json.dumps(terminal) + '\n\n').encode() + b'x' * 4096
                self.bundle = self.root / ('prepared-' + expected)
                with service(response) as (endpoint, received):
                    self.spec['conditions'][0].update(adapter='responses', endpoint=endpoint,
                                                      effort='low', arm='ordinary')
                    self.assertEqual(self.prepare().returncode, 0)
                    output = self.root / ('run-' + expected)
                    result = self.run_bundle(output)
                self.assertEqual(result.returncode, 0, result.stderr)
                summary = json.loads((output / 'summary.json').read_text())
                self.assertEqual([s['status'] for s in summary['slots']], ['response_limit', 'unattempted'])
                self.assertEqual(len(received), 1)
                attempt = json.loads((output / 'cell-0000' / 'attempt-0000.json').read_text())
                self.assertEqual(attempt['condition_error'], expected)
                self.assertIsNone(attempt['api_rate_equivalent_usd'])

    def test_coverage_request_limit_preserves_prepared_but_unsubmitted_sources(self):
        sources = [
            {'id': 's01', 'path': 'review.md', 'content': 'Candidate reviewed.\n',
             'sha256': hashlib.sha256(b'Candidate reviewed.\n').hexdigest()},
            {'id': 's02', 'path': 'push.md', 'content': 'Push outcome unknown.\n',
             'sha256': hashlib.sha256(b'Push outcome unknown.\n').hexdigest()}]
        self.input.write_text(json.dumps({
            'task': 'Explain the review and publication evidence.',
            'ordinary': 'Read s01 and s02.', 'deterministic': 'Review: s01. Push: s02.',
            'sources': sources}))
        self.spec['kind'] = 'coverage'
        self.spec['cases'][0]['input']['sha256'] = hashlib.sha256(self.input.read_bytes()).hexdigest()
        second = copy.deepcopy(self.spec['cases'][0]); second['id'] = 'c02'
        self.spec['cases'].append(second)
        self.spec['limits'].update(cell_seconds=8, tool_operations=16,
                                  tool_result_bytes=131072, tool_total_bytes=2097152)
        usage = {'input_tokens': 100, 'output_tokens': 10,
                 'input_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 0}}
        response = {'model': 'gpt-6-luna', 'status': 'completed', 'usage': usage,
                    'output': [
                        {'type': 'function_call', 'namespace': 'evidence', 'name': 'read_source',
                         'call_id': 'call_review', 'arguments': '{"source":"s01"}'},
                        {'type': 'function_call', 'namespace': 'evidence', 'name': 'read_source',
                         'call_id': 'call_push', 'arguments': '{"source":"s02"}'}]}
        raw = ('data: ' + json.dumps({'type': 'response.completed', 'response': response}) + '\n\n').encode()
        completed = {'model': 'gpt-6-luna', 'status': 'completed', 'usage': usage, 'output': [
            {'type': 'message', 'role': 'assistant', 'content': [
                {'type': 'output_text', 'text': 'Review and push are separate records [s01, s02].'}]}]}
        replies = [raw, ('data: ' + json.dumps({'type': 'response.completed',
                                              'response': completed}) + '\n\n').encode()]
        with service(lambda _: replies.pop(0)) as (endpoint, received):
            self.spec['conditions'][0].update(adapter='responses', endpoint=endpoint, effort='low', arm='ordinary')
            prepared = self.prepare()
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            output = self.root / 'run'
            result = self.run_bundle(output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(received), 2)
        self.assertEqual(received[1]['input'], received[0]['input'])
        summary = json.loads((output / 'summary.json').read_text())
        self.assertEqual([slot['status'] for slot in summary['slots']],
                         ['resource_incomplete', 'completed'])
        cell_path = output / 'cell-0000'
        cell = json.loads((cell_path / 'summary.json').read_text())
        self.assertEqual(cell['status'], 'resource_incomplete')
        self.assertIsNone(cell['answer'])
        self.assertEqual(cell['tool_operations'], 2)
        self.assertEqual(cell['tool_submission_attempted_bytes'], 0)
        self.assertIsNone(cell['provider_consumed_tool_bytes'])
        tools = json.loads((cell_path / 'tools-0000.json').read_text())
        self.assertEqual([json.loads(item['output']) for item in tools['results']], sources)
        self.assertEqual([item['call_id'] for item in tools['results']], ['call_review', 'call_push'])
        prepared_bytes = sum(len(item['output'].encode()) for item in tools['results'])
        self.assertEqual(cell['tool_prepared_bytes'], prepared_bytes)
        self.assertEqual(tools['prepared_bytes'], prepared_bytes)
        self.assertNotIn('delivered_bytes', tools)
        self.assertEqual(cell['unsubmitted_tool_results'], ['call_review', 'call_push'])
        self.assertEqual(cell['unsubmitted_reason'], 'request_limit')
        attempt = json.loads((cell_path / 'attempt-0000.json').read_text())
        self.assertEqual(attempt['usage'], usage)
        self.assertEqual(attempt['raw_response'], response)
        self.assertGreater(attempt['duration_ms'], 0)
        self.assertFalse((cell_path / 'request-0001.json').exists())

    def test_coverage_unavailable_source_remains_visible_and_identical_in_both_arms(self):
        unavailable = {'id': 's02', 'path': 'verification.json',
                       'unavailable_reason': 'Source bytes are not available in this capture.'}
        self.input.write_text(json.dumps({
            'task': 'Explain what the supplied review evidence supports.',
            'ordinary': 'Inspect the supplied evidence.',
            'deterministic': 'Prepared table: comparison unavailable for verification.json.',
            'sources': [{'id': 's01', 'path': 'review.md', 'content': 'Reviewed.\n',
                         'sha256': hashlib.sha256(b'Reviewed.\n').hexdigest()}, unavailable]}))
        self.spec['kind'] = 'coverage'
        self.spec['cases'][0]['input']['sha256'] = hashlib.sha256(self.input.read_bytes()).hexdigest()
        self.spec['limits'].update(requests_per_cell=5, cell_seconds=8, tool_operations=16,
                                  tool_result_bytes=131072, tool_total_bytes=2097152)
        read = {'model': 'gpt-6-luna', 'status': 'completed', 'output': [
            {'type': 'function_call', 'namespace': 'evidence', 'name': 'read_source',
             'call_id': 'read_manifest', 'arguments': '{"source":"s02"}'}]}
        final = {'model': 'gpt-6-luna', 'status': 'completed', 'output': [
            {'type': 'message', 'role': 'assistant', 'content': [
                {'type': 'output_text', 'text': 'The verification record is unavailable [s02].'}]}]}
        responses = [read, final, read, final]
        with service(lambda _: ('data: ' + json.dumps({'type': 'response.completed',
                                                      'response': responses.pop(0)}) + '\n\n').encode()) as (endpoint, received):
            self.spec['conditions'][0].update(adapter='responses', endpoint=endpoint,
                                               effort='low', arm='ordinary')
            other = copy.deepcopy(self.spec['conditions'][0]); other.update(id='added', arm='deterministic')
            self.spec['conditions'].append(other)
            prepared = self.prepare()
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            output = self.root / 'run'; result = self.run_bundle(output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(received), 4)
        for index in [0, 2]:
            self.assertIn('verification.json', received[index]['input'][0]['content'][0]['text'])
            returned = received[index + 1]['input'][-1]
            self.assertEqual(returned['call_id'], 'read_manifest')
            self.assertEqual(json.loads(returned['output']), unavailable)
        summary = json.loads((output / 'summary.json').read_text())
        self.assertEqual([slot['status'] for slot in summary['slots']], ['completed', 'completed'])
        self.assertEqual(summary['cases'], [{'case': 'c01', 'status': 'ready'}])

    def test_coverage_tool_delivery_limit_counts_replayed_results_before_submission(self):
        content = 'a' * 1000
        self.input.write_text(json.dumps({
            'task': 'Inspect the source and explain its scope.', 'ordinary': 'Read s01.',
            'deterministic': 'Source: s01.',
            'sources': [{'id': 's01', 'path': 'source.md', 'content': content,
                         'sha256': hashlib.sha256(content.encode()).hexdigest()}]}))
        self.spec['kind'] = 'coverage'
        self.spec['cases'][0]['input']['sha256'] = hashlib.sha256(self.input.read_bytes()).hexdigest()
        self.spec['limits'].update(requests_per_cell=5, cell_seconds=8, tool_operations=16,
                                  tool_result_bytes=2000, tool_total_bytes=3000)
        responses = [
            {'model': 'gpt-6-luna', 'status': 'completed', 'output': [
                {'type': 'function_call', 'namespace': 'evidence', 'name': 'read_source',
                 'call_id': 'read_once', 'arguments': '{"source":"s01"}'}]},
            {'model': 'gpt-6-luna', 'status': 'completed', 'output': [
                {'type': 'function_call', 'namespace': 'evidence', 'name': 'read_source',
                 'call_id': 'read_again', 'arguments': '{"source":"s01"}'}]},
            {'model': 'gpt-6-luna', 'status': 'completed', 'output': [
                {'type': 'message', 'role': 'assistant', 'content': [
                    {'type': 'output_text', 'text': 'Finished reading.'}]}]}]
        with service(lambda _: ('data: ' + json.dumps({'type': 'response.completed',
                                                      'response': responses.pop(0)}) + '\n\n').encode()) as (endpoint, received):
            self.spec['conditions'][0].update(adapter='responses', endpoint=endpoint,
                                               effort='low', arm='ordinary')
            prepared = self.prepare()
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            output = self.root / 'run'; result = self.run_bundle(output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(received), 2)
        cell_path = output / 'cell-0000'
        cell = json.loads((cell_path / 'summary.json').read_text())
        self.assertEqual(cell['status'], 'resource_incomplete')
        self.assertEqual(cell['requests'], 2)
        self.assertIsNone(cell['answer'])
        self.assertGreater(cell['tool_prepared_bytes'], 2000)
        self.assertLessEqual(cell['tool_prepared_bytes'], 3000)
        self.assertGreater(cell['tool_submission_attempted_bytes'], 1000)
        self.assertLess(cell['tool_submission_attempted_bytes'], 2000)
        self.assertEqual(cell['unsubmitted_tool_results'], ['read_again'])
        self.assertEqual(cell['unsubmitted_reason'], 'tool_submission_bytes')
        self.assertFalse((cell_path / 'request-0002.json').exists())
        tools = json.loads((cell_path / 'tools-0001.json').read_text())
        self.assertEqual(json.loads(tools['results'][0]['output'])['content'], content)

    def test_coverage_accounting_counts_continuations_and_keeps_unreported_usage_unknown(self):
        self.input.write_text(json.dumps({
            'task': 'Explain the review evidence.', 'ordinary': 'Read s01.',
            'deterministic': 'Review source: s01.',
            'sources': [{'id': 's01', 'path': 'review.md', 'content': 'Reviewed.\n',
                         'sha256': hashlib.sha256(b'Reviewed.\n').hexdigest()}]}))
        self.spec['kind'] = 'coverage'
        self.spec['cases'][0]['input']['sha256'] = hashlib.sha256(self.input.read_bytes()).hexdigest()
        second = copy.deepcopy(self.spec['cases'][0]); second['id'] = 'c02'
        self.spec['cases'].append(second)
        self.spec['limits'].update(requests_per_cell=5, cell_seconds=8, tool_operations=16,
                                  tool_result_bytes=131072, tool_total_bytes=2097152)
        events = [
            {'type': 'response.completed', 'response': {
                'model': 'gpt-6-luna', 'status': 'completed', 'output': [
                    {'type': 'function_call', 'namespace': 'evidence', 'name': 'read_source',
                     'call_id': 'read_review', 'arguments': '{"source":"s01"}'}],
                'usage': {'input_tokens': 100, 'output_tokens': 10,
                          'input_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 0}}}},
            {'type': 'response.completed', 'response': {
                'model': 'gpt-6-luna', 'status': 'completed', 'output': [
                    {'type': 'message', 'role': 'assistant', 'content': [
                        {'type': 'output_text', 'text': 'The candidate was reviewed [s01].'}]}],
                'usage': {'input_tokens': 120, 'output_tokens': 20,
                          'input_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 0}}}},
            {'type': 'response.incomplete', 'response': {
                'model': 'gpt-6-luna', 'status': 'incomplete', 'output': []}}]
        with service(lambda _: ('data: ' + json.dumps(events.pop(0)) + '\n\n').encode()) as (endpoint, received):
            self.spec['conditions'][0].update(adapter='responses', endpoint=endpoint,
                                               effort='low', arm='ordinary', rates={
                'input': '0.10', 'cached': '0.01', 'write': '0.125', 'output': '0.50'})
            prepared = self.prepare()
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            output = self.root / 'run'; result = self.run_bundle(output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(received), 3)
        summary = json.loads((output / 'summary.json').read_text())
        accounting = summary['request_accounting']
        self.assertEqual(accounting['attempts'], 3)
        self.assertEqual(accounting['known_api_rate_equivalent_usd'], '0.000037')
        self.assertEqual(accounting['unvalued_attempts'], 1)
        self.assertIsNone(accounting['api_rate_equivalent_usd'])
        self.assertEqual(accounting['input_tokens'], {'reported_sum': 220, 'unreported_attempts': 1})
        self.assertEqual(accounting['output_tokens'], {'reported_sum': 30, 'unreported_attempts': 1})
        self.assertIsNone(accounting['confirmed_charge_usd'])
        self.assertFalse(accounting['complete_workflow_costs_measured'])
        self.assertEqual([slot['status'] for slot in summary['slots']], ['completed', 'provider_incomplete'])

    def test_coverage_model_mismatch_stops_only_the_affected_condition(self):
        self.input.write_text(json.dumps({
            'task': 'Explain the review evidence.', 'ordinary': 'Read s01.',
            'deterministic': 'Review source: s01.',
            'sources': [{'id': 's01', 'path': 'review.md', 'content': 'Reviewed.\n',
                         'sha256': hashlib.sha256(b'Reviewed.\n').hexdigest()}]}))
        self.spec['kind'] = 'coverage'
        self.spec['cases'][0]['input']['sha256'] = hashlib.sha256(self.input.read_bytes()).hexdigest()
        second = copy.deepcopy(self.spec['cases'][0]); second['id'] = 'c02'
        self.spec['cases'].append(second)
        self.spec['limits'].update(cell_seconds=8, tool_operations=16,
                                  tool_result_bytes=131072, tool_total_bytes=2097152)
        usage = {'input_tokens': 100, 'output_tokens': 10}
        def reply(path):
            response = {'model': 'gpt-6.1-sol' if path.endswith('/wrong') else 'gpt-6-luna',
                        'status': 'completed', 'usage': usage, 'output': [
                {'type': 'message', 'role': 'assistant', 'content': [
                    {'type': 'output_text', 'text': 'Candidate reviewed [s01].'}]}]}
            return ('data: ' + json.dumps({'type': 'response.completed', 'response': response}) + '\n\n').encode()
        with service(reply) as (endpoint, received):
            self.spec['conditions'][0].update(adapter='responses', endpoint=endpoint + '/wrong',
                                               effort='low', arm='ordinary')
            other = copy.deepcopy(self.spec['conditions'][0])
            other.update(id='other', endpoint=endpoint + '/right', arm='deterministic')
            self.spec['conditions'].append(other)
            prepared = self.prepare()
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            output = self.root / 'run'; result = self.run_bundle(output)
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads((output / 'summary.json').read_text())
        self.assertEqual({(slot['case'], slot['condition']): slot['status'] for slot in summary['slots']},
                         {('c01', 'decisions'): 'model_mismatch', ('c01', 'other'): 'completed',
                          ('c02', 'decisions'): 'unattempted', ('c02', 'other'): 'completed'})
        self.assertEqual(len(received), 3)
        attempt = json.loads((output / 'cell-0000' / 'attempt-0000.json').read_text())
        self.assertEqual(attempt['usage'], usage)
        self.assertEqual(attempt['returned_model'], 'gpt-6.1-sol')
        self.assertIsNone(attempt['api_rate_equivalent_usd'])
        self.assertIsNone(json.loads((output / 'cell-0000' / 'summary.json').read_text())['answer'])

    def test_malformed_usage_retains_attempt_and_allows_independent_coverage_work(self):
        self.input.write_text(json.dumps({
            'task': 'Explain the review evidence.', 'ordinary': 'Read s01.',
            'deterministic': 'Review source: s01.',
            'sources': [{'id': 's01', 'path': 'review.md', 'content': 'Reviewed.\n',
                         'sha256': hashlib.sha256(b'Reviewed.\n').hexdigest()}]}))
        self.spec['kind'] = 'coverage'
        self.spec['cases'][0]['input']['sha256'] = hashlib.sha256(self.input.read_bytes()).hexdigest()
        second = copy.deepcopy(self.spec['cases'][0]); second['id'] = 'c02'
        self.spec['cases'].append(second)
        self.spec['limits'].update(cell_seconds=8, tool_operations=16,
                                  tool_result_bytes=131072, tool_total_bytes=2097152)
        usage = {'input_tokens': 100, 'output_tokens': 10}
        def reply(path):
            response = {'model': 'gpt-6-luna', 'status': 'completed',
                        'usage': dict(usage, input_tokens_details=['bad']) if path.endswith('/wrong') else usage, 'output': [
                {'type': 'message', 'role': 'assistant', 'content': [
                    {'type': 'output_text', 'text': 'Candidate reviewed [s01].'}]}]}
            return ('data: ' + json.dumps({'type': 'response.completed', 'response': response}) + '\n\n').encode()
        with service(reply) as (endpoint, received):
            self.spec['conditions'][0].update(adapter='responses', endpoint=endpoint + '/wrong',
                                               effort='low', arm='ordinary')
            other = copy.deepcopy(self.spec['conditions'][0])
            other.update(id='other', endpoint=endpoint + '/right', arm='deterministic')
            self.spec['conditions'].append(other)
            prepared = self.prepare()
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            output = self.root / 'run'; result = self.run_bundle(output)
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads((output / 'summary.json').read_text())
        self.assertEqual({(slot['case'], slot['condition']): slot['status'] for slot in summary['slots']},
                         {('c01', 'decisions'): 'accounting_error', ('c01', 'other'): 'completed',
                          ('c02', 'decisions'): 'unattempted', ('c02', 'other'): 'completed'})
        self.assertEqual(len(received), 3)
        attempt = json.loads((output / 'cell-0000' / 'attempt-0000.json').read_text())
        self.assertEqual(attempt['usage'], dict(usage, input_tokens_details=['bad']))
        self.assertEqual(attempt['returned_model'], 'gpt-6-luna')
        self.assertIsNone(attempt['api_rate_equivalent_usd'])
        self.assertIsNone(json.loads((output / 'cell-0000' / 'summary.json').read_text())['answer'])

    def test_coverage_continuation_preserves_reasoning_phase_and_paired_source_result(self):
        source_text = 'This record covers the commit candidate; the actual pushed range is unknown.\n'
        source = {'id': 's01', 'path': 'record.md', 'content': source_text,
                  'sha256': hashlib.sha256(source_text.encode()).hexdigest()}
        packet = {'task': 'Explain what the review supports and cite its evidence.',
                  'ordinary': 'Candidate record: s01.',
                  'deterministic': 'Candidate record: s01. Prepared relationship: identical.',
                  'sources': [source]}
        self.input.write_text(json.dumps(packet))
        self.spec['kind'] = 'coverage'
        self.spec['cases'][0]['input']['sha256'] = hashlib.sha256(self.input.read_bytes()).hexdigest()
        self.spec['limits'].update(requests_per_cell=5, cell_seconds=8, tool_operations=16,
                                  tool_result_bytes=131072, tool_total_bytes=2097152)
        first_output = [
            {'type': 'reasoning', 'id': 'rs_1', 'summary': [],
             'encrypted_content': 'synthetic-opaque-reasoning', 'status': 'completed'},
            {'type': 'message', 'role': 'assistant', 'phase': 'commentary',
             'content': [{'type': 'output_text', 'text': 'I will read the record.'}],
             'status': 'completed'},
            {'type': 'function_call', 'namespace': 'evidence', 'name': 'read_source',
             'id': 'fc_1', 'call_id': 'call_1', 'arguments': '{"source":"s01"}',
             'status': 'completed'}]
        usage = {'input_tokens': 100, 'input_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 0},
                 'output_tokens': 10}
        responses = [
            {'model': 'gpt-6-luna', 'status': 'completed', 'output': first_output, 'usage': usage},
            {'model': 'gpt-6-luna', 'status': 'completed', 'output': [
                {'type': 'message', 'role': 'assistant', 'phase': 'final_answer',
                 'content': [{'type': 'output_text', 'text': 'The record covers the candidate, not the actual push [s01].'}]}],
             'usage': usage}]
        def reply(_):
            return ('data: ' + json.dumps({'type': 'response.completed', 'response': responses.pop(0)}) + '\n\n').encode()
        raw_received = []
        with service(reply, raw_received) as (endpoint, received):
            self.spec['conditions'][0].update(adapter='responses', endpoint=endpoint, effort='low', arm='ordinary')
            prepared = self.prepare()
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            output = self.root / 'run'; result = self.run_bundle(output)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(received), 2)
        self.assertEqual(received[0]['include'], ['reasoning.encrypted_content'])
        self.assertEqual(received[0]['tools'][0]['name'], 'evidence')
        continuation = received[1]
        expected_history = received[0]['input'] + [
            {key: value for key, value in item.items() if key != 'status'} for item in first_output]
        self.assertEqual(continuation['input'][:-1], expected_history)
        returned = continuation['input'][-1]
        self.assertEqual(returned['type'], 'function_call_output')
        self.assertEqual(returned['call_id'], 'call_1')
        self.assertEqual(json.loads(returned['output']), source)
        self.assertFalse(continuation['store']); self.assertTrue(continuation['stream'])
        self.assertNotIn('previous_response_id', continuation)
        cell = json.loads((output / 'cell-0000' / 'summary.json').read_text())
        self.assertEqual(cell['status'], 'completed')
        self.assertEqual(cell['requests'], 2)
        self.assertEqual(cell['tool_operations'], 1)
        self.assertEqual(cell['answer'], 'The record covers the candidate, not the actual push [s01].')
        for number in range(2):
            attempt = json.loads((output / 'cell-0000' / f'attempt-{number:04d}.json').read_text())
            self.assertEqual(attempt['usage'], usage)
            self.assertEqual((output / 'cell-0000' / attempt['request_body']).read_bytes(), raw_received[number])
            self.assertEqual(attempt['payload_sha256'], hashlib.sha256(raw_received[number]).hexdigest())


if __name__ == '__main__':
    unittest.main()
