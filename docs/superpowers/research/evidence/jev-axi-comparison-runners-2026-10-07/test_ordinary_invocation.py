"""Exercise whole-invocation orchestration through approved synthetic CLI seams."""
import hashlib
import json
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from test_comparison_runner import service, RUNNER

INVOCATION = Path(__file__).with_name('ordinary_invocation.py')

def write(path, value):
    path.write_text(json.dumps(value))
    return hashlib.sha256(path.read_bytes()).hexdigest()

def ref(path, role, identity):
    data = path.read_bytes()
    return dict(role=role, id=identity, path=str(path), bytes=len(data),
                sha256=hashlib.sha256(data).hexdigest())

def claim_fixture(root, base, seconds=60, request_seconds=2):
    order = ['c01', 'c04', 'c03', 'c06', 'c05', 'c07', 'c02', 'c08', 'c09', 'c10', 'c11']
    cases, dependencies = [], [ref(RUNNER, 'runner', 'runner')]
    for case in order:
        path = root / (case + '.md')
        path.write_text('Status: non_ready\n' if case == 'c11' else
                        'Assertion: alpha.\nSource: alpha is recorded.\n')
        item = ref(path, 'inference', case)
        dependencies.append(item)
        cases.append(dict(id=case, status='unavailable' if case == 'c11' else 'ready',
                          input=dict(path=str(path), sha256=item['sha256'])))
    for role in ['contract', 'procedure', 'route', 'price', 'evaluator']:
        path = root / (role + '.json')
        write(path, dict(synthetic_fixture=role))
        dependencies.append(ref(path, role, role))
    corpus, control = root / 'corpus.json', root / 'control.json'
    write(corpus, dict(preparations=[
        dict(case=case, status='non_ready' if case == 'c11' else 'ready',
             exit_code=2 if case == 'c11' else 0) for case in order]))
    write(control, dict(case_id='c11', status='non_ready', quotation_status='unavailable',
                        sources=[dict(status='controlled_unavailable',
                                      availability='controlled_unavailable',
                                      observed_sha256=None, file=None)]))
    dependencies += [ref(corpus, 'corpus', 'manifest'),
                     ref(control, 'corpus', 'c11-packet')]
    rates = dict(input='0.10', cached='0', write='0', output='0')
    conditions = [
        dict(id='jev', adapter='jev', model='fixture-jev', effort=None,
             endpoint=base + '/jev', billing='local_test', auth_env=None, rates=rates),
        dict(id='decisions', adapter='decisions', model='gpt-6-luna', effort=None,
             endpoint=base + '/decisions', billing='local_test', auth_env=None, rates=rates)]
    profiles = [('gpt-6-luna', 'low'), ('gpt-6-luna', 'medium'),
                ('gpt-6-luna', 'high'), ('gpt-6.1-sol', 'low')]
    conditions += [
        dict(id='responses-' + str(index), adapter='responses', model=model, effort=effort,
             endpoint=base + ('/sol' if model == 'gpt-6.1-sol' else '/luna'),
             billing='local_test', auth_env=None, rates=rates)
        for index, (model, effort) in enumerate(profiles)]
    limits = dict(request_seconds=request_seconds, run_seconds=60, input_bytes=65536,
                  request_bytes=131072, response_bytes=1048576, requests_per_cell=1)
    spec, bindings = root / 'spec.json', root / 'bindings.json'
    spec_sha = write(spec, dict(version=1, kind='claim', cases=cases,
                                conditions=conditions, limits=limits))
    bindings_sha = write(bindings, dict(version=1, kind='claim',
                                        invocation_seconds=seconds,
                                        dependencies=dependencies))
    output = root / 'invocation'
    command = [sys.executable, str(INVOCATION), 'start',
               '--spec', str(spec), '--spec-sha256', spec_sha,
               '--bindings', str(bindings), '--bindings-sha256', bindings_sha,
               '--output', str(output), '--local-http']
    return command, output

def close_command(state_ref, events, events_sha, output):
    return [sys.executable, str(INVOCATION), 'close',
            '--state', state_ref['path'], '--state-sha256', state_ref['sha256'],
            '--events', str(events), '--events-sha256', events_sha,
            '--output', str(output)]

@contextmanager
def interrupted_service():
    received, lock = [], threading.Lock()
    second_seen, release = threading.Event(), threading.Event()
    prefix = b'{"model":"gpt-6-luna","answers":'
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_POST(self):
            body = self.rfile.read(int(self.headers['Content-Length']))
            with lock:
                received.append(dict(path=self.path, body=body))
                ordinal = len(received)
            if ordinal == 1:
                relations = ['supported', 'contradicted', 'unsupported_extension', 'unresolved']
                answer = dict(type='choice', name='claim_relation', choice='supported',
                              confidence=1,
                              probabilities={key: int(key == 'supported') for key in relations})
                data = json.dumps(dict(model='fixture-jev',
                                       answers={'claim_relation': answer},
                                       usage={'input_tokens': 10})).encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                self.wfile.flush()
            else:
                self.send_response(200)
                self.send_header('Content-Length', str(len(prefix) + 1024))
                self.end_headers()
                self.wfile.write(prefix)
                self.wfile.flush()
                second_seen.set()
                release.wait(15)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.daemon_threads = True
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield (f'http://127.0.0.1:{server.server_port}',
               received, second_seen, prefix)
    finally:
        release.set()
        server.shutdown()
        server.server_close()
        worker.join()

class OrdinaryInvocationCLI(unittest.TestCase):
    def test_start_and_close_preserve_manifest_and_accounting_gaps(self):
        relations = ['supported', 'contradicted', 'unsupported_extension', 'unresolved']
        usage = {'input_tokens': 10, 'output_tokens': 1,
                 'input_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 0},
                 'output_tokens_details': {'reasoning_tokens': 0}}
        def reply(path):
            if path in {'/jev', '/decisions'}:
                choice = dict(type='choice', name='claim_relation', choice='supported',
                              confidence=1, probabilities={key: int(key == 'supported')
                                                           for key in relations})
                if path == '/decisions':
                    choice['probabilities'] = [dict(value=key, probability=value)
                                               for key, value in choice['probabilities'].items()]
                answers = {'claim_relation': choice} if path == '/jev' else [choice]
                return dict(model='fixture-jev' if path == '/jev' else 'gpt-6-luna',
                            answers=answers, usage=usage)
            model = 'gpt-6.1-sol' if path == '/sol' else 'gpt-6-luna'
            response = dict(model=model, status='completed', usage=usage, output=[
                dict(type='message', role='assistant', content=[
                    dict(type='output_text', text='{"relation":"supported"}')])])
            return ('data: ' + json.dumps(dict(type='response.completed', response=response))
                    + '\n\n').encode()
        with tempfile.TemporaryDirectory() as temporary, service(reply) as (endpoint, received):
            root = Path(temporary)
            base = endpoint.rsplit('/', 2)[0]
            order = ['c01', 'c04', 'c03', 'c06', 'c05', 'c07', 'c02', 'c08', 'c09', 'c10', 'c11']
            cases, dependencies = [], [ref(RUNNER, 'runner', 'runner')]
            for case in order:
                path = root / (case + '.md')
                path.write_text('Status: non_ready\n' if case == 'c11' else
                                'Assertion: alpha.\nSource: alpha is recorded.\n')
                item = ref(path, 'inference', case)
                dependencies.append(item)
                cases.append(dict(id=case, status='unavailable' if case == 'c11' else 'ready',
                                  input=dict(path=str(path), sha256=item['sha256'])))
            for role in ['contract', 'procedure', 'route', 'price', 'evaluator']:
                path = root / (role + '.json')
                write(path, dict(synthetic_fixture=role))
                dependencies.append(ref(path, role, role))
            manifest_path, control_path = root / 'corpus.json', root / 'control.json'
            write(manifest_path, dict(preparations=[
                dict(case=case, status='non_ready' if case == 'c11' else 'ready',
                     exit_code=2 if case == 'c11' else 0) for case in order]))
            write(control_path, dict(case_id='c11', status='non_ready', quotation_status='unavailable',
                                     sources=[dict(status='controlled_unavailable',
                                                   availability='controlled_unavailable',
                                                   observed_sha256=None, file=None)]))
            dependencies += [ref(manifest_path, 'corpus', 'manifest'),
                             ref(control_path, 'corpus', 'c11-packet')]
            rates = dict(input='0.10', cached='0', write='0', output='0')
            conditions = [
                dict(id='jev', adapter='jev', model='fixture-jev', effort=None,
                     endpoint=base + '/jev', billing='local_test', auth_env=None, rates=rates),
                dict(id='decisions', adapter='decisions', model='gpt-6-luna', effort=None,
                     endpoint=base + '/decisions', billing='local_test', auth_env=None, rates=rates)]
            profiles = [('gpt-6-luna', 'low'), ('gpt-6-luna', 'medium'),
                        ('gpt-6-luna', 'high'), ('gpt-6.1-sol', 'low')]
            conditions += [dict(id='responses-' + str(index), adapter='responses',
                                model=model, effort=effort,
                                endpoint=base + ('/sol' if model == 'gpt-6.1-sol' else '/luna'),
                                billing='local_test', auth_env=None, rates=rates)
                           for index, (model, effort) in enumerate(profiles)]
            limits = dict(request_seconds=2, run_seconds=60, input_bytes=65536,
                          request_bytes=131072, response_bytes=1048576, requests_per_cell=1)
            spec_path, bindings_path = root / 'spec.json', root / 'bindings.json'
            spec_sha = write(spec_path, dict(version=1, kind='claim', cases=cases,
                                            conditions=conditions, limits=limits))
            binding_sha = write(bindings_path, dict(version=1, kind='claim',
                invocation_seconds=60, dependencies=dependencies))
            output = root / 'invocation'
            started = subprocess.run([sys.executable, str(INVOCATION), 'start',
                '--spec', str(spec_path), '--spec-sha256', spec_sha,
                '--bindings', str(bindings_path), '--bindings-sha256', binding_sha,
                '--output', str(output), '--local-http'],
                capture_output=True, text=True, timeout=70)
            self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
            self.assertEqual(len(received), 60)
            prepared = output / 'prepared' / 'manifest.json'
            manifest = json.loads(prepared.read_text())
            self.assertEqual(manifest['limits'], limits)
            self.assertEqual(manifest['source_spec_sha256'], spec_sha)
            state_ref = json.loads(started.stdout)['state']
            state = json.loads(Path(state_ref['path']).read_text())
            self.assertEqual(state['status'], 'awaiting_closeout')
            self.assertEqual(state['deadline_monotonic_ns'],
                             state['started_monotonic_ns'] + 60_000_000_000)
            events_path = root / 'events.json'
            summary = json.loads((output / 'run' / 'summary.json').read_text())
            self.assertEqual(len(summary['slots']), 60)
            self.assertTrue(all(slot['status'] == 'completed' for slot in summary['slots']))
            grading_start = time.monotonic_ns()
            grades = root / 'grades.json'
            grading_end = time.monotonic_ns()
            grades_sha = write(grades, dict(
                synthetic_fixture=True, started_monotonic_ns=grading_start,
                finished_monotonic_ns=grading_end,
                slots=[dict(case=slot['case'], condition=slot['condition'], grade='matching')
                       for slot in summary['slots']]))
            review_start = time.monotonic_ns()
            review = root / 'review.json'
            review_end = time.monotonic_ns()
            review_sha = write(review, dict(
                synthetic_fixture=True, reviewed_grades_sha256=grades_sha,
                started_monotonic_ns=review_start, finished_monotonic_ns=review_end,
                scope='constructed ordering trace, not independent result qualification'))
            events = []
            for phase, path, sha, beginning, ending in [
                    ('grading', grades, grades_sha, grading_start, grading_end),
                    ('required_review', review, review_sha, review_start, review_end)]:
                evidence = dict(path=str(path), sha256=sha,
                                bytes=len(path.read_bytes()), selector='$')
                events.append(dict(
                    id=phase, phase=phase, purpose='experiment_evaluation',
                    recurrence='per_invocation', actor='synthetic_fixture',
                    evidence=[evidence],
                    measurements=[dict(
                        name='elapsed', value=ending - beginning, unit='ns', status='derived',
                        basis='finished_monotonic_ns minus started_monotonic_ns')]))
            events_sha = write(events_path, dict(version=1, events=events))
            closed = subprocess.run([sys.executable, str(INVOCATION), 'close',
                '--state', state_ref['path'], '--state-sha256', state_ref['sha256'],
                '--events', str(events_path), '--events-sha256', events_sha,
                '--output', str(root / 'ledger.json')],
                capture_output=True, text=True, timeout=10)
            self.assertEqual(closed.returncode, 0, closed.stdout + closed.stderr)
            ledger = json.loads((root / 'ledger.json').read_text())
            self.assertEqual(ledger['status'], 'closed_with_gaps')
            self.assertNotIn('grading', ledger['missing_phase_measurements'])
            self.assertNotIn('required_review', ledger['missing_phase_measurements'])
            self.assertIn('billing', ledger['missing_phase_measurements'])
            self.assertGreaterEqual(grading_start, state['checkpoint_monotonic_ns'])
            self.assertGreaterEqual(review_start, grading_end)
            self.assertGreaterEqual(ledger['finished_monotonic_ns'], review_end)
            self.assertLessEqual(ledger['finished_monotonic_ns'], state['deadline_monotonic_ns'])
            self.assertEqual(ledger['closeout_events'], events)
            self.assertEqual(hashlib.sha256(prepared.read_bytes()).hexdigest(),
                             state['artifacts']['prepared_manifest']['sha256'])
            self.assertEqual(ledger['runner_run_id'],
                             json.loads((output / 'run' / 'summary.json').read_text())['run_id'])

    def test_interrupted_submission_retains_completed_partial_and_remaining_work(self):
        with tempfile.TemporaryDirectory() as temporary, interrupted_service() as service_state:
            root = Path(temporary)
            base, received, second_seen, prefix = service_state
            command, output = claim_fixture(root, base, request_seconds=20)
            process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True)
            try:
                self.assertTrue(second_seen.wait(10), 'server did not observe the second request')
                partial = output / 'run' / 'response-0001.body'
                wait_until = time.monotonic() + 5
                while time.monotonic() < wait_until:
                    if partial.exists() and partial.read_bytes() == prefix:
                        break
                    time.sleep(0.01)
                self.assertTrue(partial.exists())
                self.assertEqual(partial.read_bytes(), prefix)
                process.send_signal(signal.SIGINT)
                stdout, stderr = process.communicate(timeout=10)
            finally:
                if process.poll() is None:
                    process.send_signal(signal.SIGINT)
                    process.communicate(timeout=10)
            self.assertEqual(process.returncode, 2, stdout + stderr)
            self.assertEqual([item['path'] for item in received], ['/jev', '/decisions'])
            state_ref = json.loads(stdout)['state']
            state = json.loads(Path(state_ref['path']).read_text())
            self.assertEqual(state['status'], 'failed')
            self.assertEqual(state['reason'], 'operator_interruption')
            recovery_ref = state['artifacts']['request_recovery']
            recovery = json.loads(Path(recovery_ref['path']).read_text())
            self.assertEqual(state['runner_run_id'], recovery['run_id'])
            self.assertEqual(len(recovery['slots']), 60)
            self.assertEqual(recovery['slots'][0]['status'], 'completed')
            self.assertEqual(recovery['slots'][1]['status'], 'submission_uncertain')
            self.assertTrue(all(
                slot['status'] == 'unattempted' and slot['reason'] == 'operator_interruption'
                for slot in recovery['slots'][2:]))
            accounting = recovery['request_accounting']
            self.assertEqual(accounting['reserved_requests'], 2)
            self.assertEqual(accounting['observed_attempts'], 1)
            self.assertEqual(accounting['observed_submissions_without_attempt'], 0)
            self.assertEqual(accounting['submission_uncertain_reservations'], 1)
            self.assertEqual(accounting['not_submitted_reservations'], 0)
            uncertain = recovery['requests'][1]
            self.assertIsNone(uncertain['submission_started'])
            self.assertIsNone(uncertain['usage'])
            self.assertTrue(uncertain['residual_provider_work_unknown'])
            completed = json.loads((output / 'run' / 'attempt-0000.json').read_text())
            self.assertEqual(completed['relation'], 'supported')
            self.assertEqual(completed['status'], 'completed')
            inventory_ref = state['artifacts']['request_evidence']
            inventory = json.loads(Path(inventory_ref['path']).read_text())
            retained = {Path(item['path']).name for item in inventory}
            self.assertTrue({
                'run-identity.json', 'attempt-0000.json', 'response-0000.body',
                'request-0001.json', 'request-0001.body', 'response-0001.body',
                'submission-0001.json'} <= retained)
            for stream in ['stdout', 'stderr']:
                item = state['artifacts']['run_cli'][stream]
                data = Path(item['path']).read_bytes()
                self.assertEqual(len(data), item['bytes'])
                self.assertEqual(hashlib.sha256(data).hexdigest(), item['sha256'])
            events = root / 'events.json'
            events_sha = write(events, dict(version=1, events=[]))
            ledger = root / 'ledger.json'
            closed = subprocess.run(close_command(state_ref, events, events_sha, ledger),
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(closed.returncode, 2, closed.stdout + closed.stderr)
            self.assertEqual(json.loads(ledger.read_text())['status'], 'closed_failed')
            partial.write_bytes(prefix + b'changed')
            rejected_ledger = root / 'rejected-ledger.json'
            rejected = subprocess.run(
                close_command(state_ref, events, events_sha, rejected_ledger),
                capture_output=True, text=True, timeout=10)
            self.assertEqual(rejected.returncode, 2)
            self.assertEqual(json.loads(rejected.stdout)['status'], 'refused')
            self.assertFalse(rejected_ledger.exists())

    def test_expired_whole_allowance_submits_no_request(self):
        def reply(path):
            return b'{}'
        with tempfile.TemporaryDirectory() as temporary, service(reply) as (endpoint, received):
            root = Path(temporary)
            base = endpoint.rsplit('/', 2)[0]
            command, output = claim_fixture(root, base, seconds=0.000000001)
            started = subprocess.run(command, capture_output=True, text=True, timeout=10)
            self.assertEqual(started.returncode, 2, started.stdout + started.stderr)
            state_ref = json.loads(started.stdout)['state']
            state = json.loads(Path(state_ref['path']).read_text())
            self.assertIn('admission', state['artifacts'])
            self.assertEqual(state['status'], 'failed')
            self.assertEqual(state['reason'], 'whole-invocation deadline exhausted')
            self.assertEqual(received, [])
            self.assertFalse((output / 'run').exists())
            events = root / 'events.json'
            events_sha = write(events, dict(version=1, events=[]))
            ledger = root / 'ledger.json'
            closed = subprocess.run(close_command(state_ref, events, events_sha, ledger),
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(closed.returncode, 2, closed.stdout + closed.stderr)
            self.assertEqual(json.loads(ledger.read_text())['status'], 'deadline_exceeded')

if __name__ == '__main__':
    unittest.main()
