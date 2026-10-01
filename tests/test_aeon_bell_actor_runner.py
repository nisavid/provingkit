"""Separate-process tests of the synthetic structured monitor procedure."""
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'tests/praxis_actor_runner.js'
FIXTURE = ROOT / 'tests/praxis_fixture.py'


class ActorRunner(unittest.TestCase):
    def run_cli(self, command, *args):
        process = subprocess.run([*command, *map(str, args)], capture_output=True,
                                 text=True, timeout=30)
        self.assertEqual(process.returncode, 0, process.stderr)
        return json.loads(process.stdout)

    def make(self, case):
        parent = tempfile.TemporaryDirectory(prefix='praxis-actor-')
        self.addCleanup(parent.cleanup)
        directory = Path(parent.name) / 'run'
        result = self.run_cli(['node', str(RUNNER)], 'setup', case,
                             '--directory', directory)
        self.assertEqual(result['status'], 'ready')
        self.assertNotIn('entry_ref', result)
        return directory

    def advance(self, directory, classification=None):
        args = ['advance', '--directory', directory]
        if classification is not None:
            args += ['--classification', json.dumps(classification)]
        result = self.run_cli(['node', str(directory / 'tests/praxis_actor_runner.js')], *args)
        self.assertEqual(set(result), {'status', 'view'})
        self.assertTrue({'entry_ref', 'continuation', 'arguments', 'actual_result',
                         'result_json', 'engine_reply', 'engine_request'}.isdisjoint(result['view']))
        return result

    def test_raw_fixture_deferred_entry(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            entry = self.run_cli([sys.executable, '-B', str(FIXTURE)], 'setup', 'empty',
                                 '--directory', directory, '--defer-enter')
            self.assertIsNone(entry['initial'])
            transcript = json.loads((directory / 'setup-transcript.json').read_text())
            self.assertFalse(any(event.get('command', {}).get('argv', [])[:2] ==
                                 ['monitor', 'enter'] for event in transcript))

    def events(self, directory):
        return [json.loads(line) for line in (directory / 'events.jsonl').read_text().splitlines()]

    def effects(self, directory):
        return [e for e in self.events(directory) if e['type'] in ('engine', 'control')]

    def test_empty_setup_defers_and_terminal_repeat_has_no_effects(self):
        directory = self.make('empty')
        entry = json.loads((directory / 'entry.json').read_text())
        self.assertIsNone(entry['initial'])
        result = self.advance(directory)
        self.assertEqual(result['status'], 'complete')
        effects = self.effects(directory)
        self.assertEqual([e['kind'] for e in effects if e['type'] == 'control'], ['heartbeat_set'])
        enters = [e for e in effects if e['type'] == 'engine' and e['argv'][3] == 'enter']
        self.assertEqual(len(enters), 1)
        self.assertEqual(enters[0]['reply']['generation'], 1)
        self.assertEqual(self.advance(directory), result)
        self.assertEqual(self.effects(directory), effects)

    def classify(self, result):
        # This synthetic caller belongs to tests, never the actor runner.
        view = result['view']
        summary = view['native_result_summary']
        if view['action_kind'] == 'task_read':
            choice = summary['task_status']
            if choice == 'idle':
                self.assertIs(summary['episode_matches'], True)
                self.assertIn(view['expected_episode'], summary['episode_context'])
        elif view['action_kind'] == 'send':
            choice = summary['transport_status']
            self.assertIn('synthetic', summary['evidence_summary'])
        else:
            self.fail('No public semantic classification for this action')
        self.assertIn(choice, view['allowed_choices'])
        return {'decision_id': view['decision_id'], 'choice': choice}

    def finish(self, directory, result=None):
        result = result or self.advance(directory)
        for _ in range(32):
            if result['status'] != 'needs_classification':
                self.assertEqual(result['status'], 'complete', result)
                return result
            result = self.advance(directory, self.classify(result))
        self.fail('Synthetic caller exceeded 32 decisions')

    def test_cached_open_requires_explicit_classification_and_preserves_native_result(self):
        directory = self.make('cached-open')
        result = self.advance(directory)
        self.assertEqual(result['status'], 'needs_classification')
        self.assertEqual(result['view']['action_kind'], 'task_read')
        control = [e for e in self.events(directory) if e['type'] == 'control'][-1]
        self.assertEqual(control['outcome']['actual_result'],
                         json.loads(control['controller_outcome']['stdout']))
        self.assertEqual(control['outcome']['actual_result'],
                         {'status': 'idle', 'observed_at': '2026-09-17T12:05:00+00:00'})
        effects = self.effects(directory)
        waiting = self.advance(directory)
        self.assertEqual(waiting['status'], 'needs_classification')
        self.assertEqual(self.effects(directory), effects)
        self.finish(directory, result)
        kinds = [e['kind'] for e in self.effects(directory) if e['type'] == 'control']
        self.assertEqual(kinds, ['task_read', 'task_read', 'send', 'emit', 'heartbeat_set'])
        self.assertNotIn('observe', kinds)
        entered = [e for e in self.effects(directory) if e['type'] == 'engine' and e['argv'][3] == 'enter']
        self.assertEqual(len(entered), 1)

    def test_shared_fresh_query_and_one_idle_send(self):
        directory = self.make('shared-gate-single-wake')
        self.finish(directory)
        controls = [e for e in self.events(directory) if e['type'] == 'control']
        self.assertEqual([e['kind'] for e in controls].count('observe'), 1)
        observation = next(e for e in controls if e['kind'] == 'observe')
        records = observation['controller_record']['artifact_records']
        requests = records[0]['constructed_observation']['requests']
        self.assertEqual(len(requests), 1)
        self.assertEqual(set(requests[0]['task_ids']),
                         {'synthetic-task-a', 'synthetic-task-b', 'synthetic-task-c'})
        sends = [e for e in controls if e['kind'] == 'send']
        self.assertEqual(len(sends), 1)
        self.assertEqual(sends[0]['input']['task_id'], 'synthetic-task-a')
        reads = [(e['input']['task_id'], e['outcome']['summary']['task_status'])
                 for e in controls if e['kind'] == 'task_read']
        self.assertEqual(reads, [('synthetic-task-a', 'idle'), ('synthetic-task-b', 'running'),
                                ('synthetic-task-c', 'completed'), ('synthetic-task-a', 'idle')])

    def test_classification_rejects_free_fields_stale_ids_and_unlisted_choices_without_effects(self):
        directory = self.make('cached-open')
        first = self.advance(directory)
        valid = self.classify(first)
        effects = self.effects(directory)
        invalids = [{**valid, 'observed_at': 'actor-authored'},
                    {**valid, 'decision_id': 'decision-stale'},
                    {**valid, 'choice': 'wake'},
                    {'choice': valid['choice']}, None]
        for invalid in invalids:
            with self.subTest(classification=invalid):
                result = self.advance(directory, invalid)
                self.assertEqual(result['status'], 'needs_classification')
                self.assertEqual(result['view']['decision_id'], first['view']['decision_id'])
                self.assertEqual(self.effects(directory), effects)
        next_read = self.advance(directory, valid)
        self.assertNotEqual(next_read['view']['decision_id'], valid['decision_id'])
        effects = self.effects(directory)
        rejected = self.advance(directory, valid)
        self.assertEqual(rejected['view']['decision_id'], next_read['view']['decision_id'])
        self.assertEqual(self.effects(directory), effects)
        self.finish(directory, next_read)

    def test_unavailable_heartbeat_is_recorded_without_real_setter(self):
        directory = self.make('schedule-unavailable')
        self.finish(directory)
        controls = [e for e in self.events(directory) if e['type'] == 'control']
        self.assertEqual([e['kind'] for e in controls], ['heartbeat_set', 'emit'])
        self.assertEqual(controls[0]['outcome']['actual_result'],
                         {'disposition': 'unavailable', 'reason': 'synthetic heartbeat control unavailable'})
        final = [e['reply'] for e in self.events(directory) if e['type'] == 'engine'][-1]
        self.assertEqual(final['outcome']['heartbeat']['result'], 'unavailable')
        self.assertEqual(final['outcome']['heartbeat']['writes'], 1)

    def test_interrupted_recipe_send_reservation_is_preserved_without_replay(self):
        directory = self.make('restart-send')
        before = json.loads((directory / 'before.json').read_text())
        attempt = before['attention'][0]['attempt_id']
        self.finish(directory)
        controls = [e for e in self.events(directory) if e['type'] == 'control']
        self.assertNotIn('send', [e['kind'] for e in controls])
        after = self.inspect(directory)
        self.assertEqual(after['attention'][0]['attempt_id'], attempt)
        self.assertEqual(after['attention'][0]['status'], 'reserved')
        self.assertEqual(after['registrations'][0]['status'], 'reserved')
        events = self.events(directory)
        prelude = [e['event']['command'] for e in events if e['type'] == 'setup_event'
                   and e['event'].get('command', {}).get('argv', [])[:2] == ['monitor', 'enter']]
        self.assertEqual(len(prelude), 1)
        enters = [e for e in events if e['type'] == 'engine' and e['argv'][3] == 'enter']
        self.assertEqual(len(enters), 1)
        self.assertEqual(enters[0]['reply']['generation'], 2)


    def inspect(self, directory):
        config = json.loads((directory / 'runner-config.json').read_text())
        return self.run_cli(['python3', '-B', str(directory / 'plugins/praxis/skills/aeon-bell/scripts/aeon_bell.py')],
                            'inspect', '--store', directory / 'synthetic-store',
                            '--now', config['logical_now'])

    def test_verified_source_drift_stops_before_enter(self):
        directory = self.make('empty')
        helper = directory / 'plugins/praxis/skills/aeon-bell/scripts/monitor_binding.js'
        helper.write_bytes(helper.read_bytes() + b'\n')
        before = self.events(directory)
        process = subprocess.run(['node', str(RUNNER), 'advance', '--directory', str(directory)],
                                 capture_output=True, text=True, timeout=30)
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(process.stdout, '')
        self.assertIn('source identity mismatch', process.stderr)
        self.assertEqual(self.events(directory), before)

    def test_controller_failure_retains_raw_transport_and_stops_without_retry(self):
        directory = self.make('due-open')
        control_path = directory / 'control-state.json'
        control = json.loads(control_path.read_text())
        # The synthetic native channel loses its registration context. Its
        # observation controller cannot answer the later issued query.
        control['registrations'] = []
        control_path.write_text(json.dumps(control) + "\n")
        read = self.advance(directory)
        self.assertEqual(read['status'], 'needs_classification')
        result = self.advance(directory, {'decision_id': read['view']['decision_id'], 'choice': 'unknown'})
        self.assertEqual(result['status'], 'unresolved')
        transports = [e for e in self.events(directory) if e['type'] == 'controller_transport']
        failed = transports[-1]
        self.assertEqual(failed['kind'], 'observe')
        self.assertEqual(failed['outcome']['kind'], 'completed')
        self.assertEqual(failed['outcome']['exit_code'], 1)
        self.assertIn('StopIteration', failed['outcome']['stderr'])
        self.assertEqual(failed['outcome']['stdout'], '')
        effects = self.effects(directory)
        self.assertEqual(self.advance(directory), result)
        self.assertEqual(self.effects(directory), effects)
        self.assertEqual([e for e in self.events(directory) if e['type'] == 'controller_transport'], transports)

    def test_all16_constructed_completions(self):
        cases = sorted(path.stem for path in (ROOT / 'evals/praxis/fixtures').glob('*.json'))
        self.assertEqual(len(cases), 16)
        for case in cases:
            with self.subTest(case=case):
                directory = self.make(case)
                result = self.finish(directory)
                effects = self.effects(directory)
                self.assertEqual(self.advance(directory), result)
                self.assertEqual(self.effects(directory), effects)
                after = self.inspect(directory)
                events = self.events(directory)
                engine_events = [e for e in events if e['type'] == 'engine']
                self.assertTrue(all(e['argv'][:3] == ['python3', 'scripts/aeon_bell.py', 'monitor']
                                    and e['argv'][3] in ('enter', 'continue') for e in engine_events))
                self.assertEqual(sum(e['argv'][3] == 'enter' for e in engine_events), 1)
                if os.environ.get('AEON_ACTOR_TRACE_DIR'):
                    retained = Path(os.environ['AEON_ACTOR_TRACE_DIR']) / case
                    retained.mkdir(parents=True, exist_ok=True)
                    for name in ('events.jsonl', 'setup-transcript.json', 'control-transcript.jsonl',
                                 'runner-config.json', 'binding-state.json', 'entry.json', 'before.json'):
                        source = directory / name
                        if source.exists():
                            shutil.copyfile(source, retained / name)
                    (retained / 'after.json').write_text(json.dumps(after, indent=2) + '\n')
                    (retained / 'completion.json').write_text(json.dumps(result, indent=2) + '\n')

    def test_episode_relation_mismatch_cannot_classify_idle(self):
        directory = self.make('cached-open')
        control_path = directory / 'control-state.json'
        control = json.loads(control_path.read_text())
        control['registrations'][0]['episode'] = 'another-synthetic-wait'
        control_path.write_text(json.dumps(control) + '\n')
        result = self.advance(directory)
        self.assertEqual(result['status'], 'needs_classification')
        summary = result['view']['native_result_summary']
        self.assertEqual(summary['task_status'], 'idle')
        self.assertIs(summary['episode_matches'], False)
        self.assertIn('another-synthetic-wait', summary['episode_context'])
        effects = self.effects(directory)
        rejected = self.advance(directory, {'decision_id': result['view']['decision_id'], 'choice': 'idle'})
        self.assertEqual(rejected['status'], 'needs_classification')
        self.assertEqual(self.effects(directory), effects)
        truthful = {'decision_id': result['view']['decision_id'], 'choice': 'unknown'}
        self.finish(directory, self.advance(directory, truthful))
        self.assertNotIn('send', [e['kind'] for e in self.effects(directory) if e['type'] == 'control'])
