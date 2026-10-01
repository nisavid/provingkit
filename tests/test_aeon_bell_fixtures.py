"""Public-interface checks for independent synthetic fixture constructions."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from tests.praxis_fixture import construct

ROOT = Path(__file__).resolve().parents[1]
ENGINE = Path(os.environ.get('AEON_FIXTURE_ENGINE', ROOT / 'plugins/praxis/skills/aeon-bell/scripts/aeon_bell.py'))


class Fixtures(unittest.TestCase):
    def make(self, case):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        return construct(ROOT / 'evals/praxis/fixtures' / (case + '.json'),
                         directory.name, engine=ENGINE)

    def finish(self, fixture):
        reply = fixture.initial
        replies = [reply]
        while reply['status'] != 'complete':
            result = fixture.controller.result(reply)
            reply = fixture.submit(reply, result)
            replies.append(reply)
            self.assertLess(len(replies), 30)
        return replies

    def kinds(self, replies):
        return [r['action']['kind'] for r in replies if r.get('action')]

    def test_empty(self):
        fixture = self.make('empty')
        self.assertEqual(fixture.before['registrations'], [])
        self.assertEqual(fixture.initial['action']['kind'], 'heartbeat_set')
        replies = self.finish(fixture)
        self.assertEqual(self.kinds(replies), ['heartbeat_set'])
        self.assertFalse(replies[-1]['outcome']['printed_anything'])

    def test_cached_closed(self):
        fixture = self.make('cached-closed')
        self.assertFalse(fixture.before['schedule']['gates'][0]['due'])
        self.assertEqual(fixture.before['observations'][0]['observed_at'], '2026-09-17T12:00:00+00:00')
        replies = self.finish(fixture)
        self.assertNotIn('observe', self.kinds(replies))
        self.assertNotIn('send', self.kinds(replies))
        self.assertFalse(replies[-1]['outcome']['printed_anything'])

    def test_cached_open(self):
        fixture = self.make('cached-open')
        self.assertEqual(fixture.before['unresolved_attempts'], [])
        self.assertFalse(fixture.before['schedule']['gates'][0]['due'])
        replies = self.finish(fixture)
        self.assertEqual(self.kinds(replies), ['task_read', 'task_read', 'send', 'emit', 'heartbeat_set'])
        self.assertEqual(fixture.inspect()['registrations'][0]['status'], 'completed')
        self.assertTrue(replies[-1]['outcome']['notice']['acknowledged'])

    def test_due_closed(self):
        fixture = self.make('due-closed')
        self.assertTrue(fixture.before['schedule']['gates'][0]['due'])
        replies = self.finish(fixture)
        self.assertEqual(self.kinds(replies).count('observe'), 1)
        self.assertNotIn('send', self.kinds(replies))
        view = fixture.inspect()
        self.assertEqual(view['observations'][0]['observed_at'], '2026-09-17T13:05:00+00:00')
        self.assertFalse(view['schedule']['gates'][0]['due'])
        self.assertEqual(replies[-1]['outcome']['heartbeat']['target_at'], '2026-09-17T14:35:00+00:00')

    def test_due_open(self):
        fixture = self.make('due-open')
        self.assertEqual(fixture.before['registrations'][0]['expected_open_at'], '2026-09-17T19:05:00+00:00')
        self.assertTrue(fixture.before['schedule']['gates'][0]['due'])
        observe = fixture.submit(fixture.initial, fixture.controller.result(fixture.initial))
        self.assertEqual(observe['action']['kind'], 'observe')
        result = fixture.controller.result(observe)
        argv = observe['action']['arguments']['argv']
        payload = json.loads(Path(argv[argv.index('--output') + 1]).read_text())
        self.assertEqual(payload['observations'][0]['gate_key'], fixture.registrations[0]['gate_key'])
        self.assertEqual(payload['observations'][0]['buckets'][0]['remaining_percent'], 40)
        reserved = fixture.submit(observe, result)
        self.assertEqual(reserved['action']['purpose'], 'pre-send')
        self.assertEqual(fixture.inspect()['attention'][0]['status'], 'reserved')
        final = fixture.finish(reserved)
        self.assertEqual(final['outcome']['wakes'][0]['result'], 'accepted')
        self.assertEqual(fixture.inspect()['registrations'][0]['status'], 'completed')

    def test_held(self):
        fixture = self.make('held')
        self.assertTrue(fixture.prelude_final['outcome']['notice']['acknowledged'])
        self.assertEqual(fixture.before['retry_schedule'][fixture.registrations[0]['gate_key']]['failures'], 1)
        replies = self.finish(fixture)
        self.assertEqual(self.kinds(replies).count('observe'), 1)
        self.assertNotIn('send', self.kinds(replies))
        self.assertNotIn('emit', self.kinds(replies))
        self.assertFalse(replies[-1]['outcome']['printed_anything'])
        self.assertEqual(fixture.inspect()['retry_schedule'][fixture.registrations[0]['gate_key']]['failures'], 2)
        self.assertEqual(replies[-1]['outcome']['heartbeat']['target_at'], '2026-09-17T13:50:00+00:00')

    def test_pending(self):
        fixture = self.make('pending')
        self.assertFalse(fixture.prelude_final['outcome']['notice']['acknowledged'])
        replies = self.finish(fixture)
        notices = [r['action'] for r in replies if r.get('action', {}).get('purpose') == 'notice']
        self.assertEqual(len(notices), 1)
        self.assertTrue(notices[0]['arguments']['replayed'])
        self.assertEqual(notices[0]['arguments']['notice_id'], fixture.setup_notice['arguments']['notice_id'])
        self.assertEqual(notices[0]['arguments']['text'], fixture.setup_notice['arguments']['text'])
        self.assertNotIn('send', self.kinds(replies))
        self.assertTrue(replies[-1]['outcome']['notice']['acknowledged'])

    def test_adapter_failure(self):
        fixture = self.make('adapter-failure')
        replies = self.finish(fixture)
        self.assertEqual(self.kinds(replies).count('observe'), 1)
        self.assertNotIn('send', self.kinds(replies))
        self.assertEqual(fixture.inspect()['observations'], fixture.before['observations'])
        self.assertEqual(fixture.inspect()['retry_schedule'], {})
        self.assertTrue(fixture.inspect()['schedule']['gates'][0]['due'])
        self.assertEqual(replies[-1]['outcome']['heartbeat']['rule'], 'failed-observation-recovery')
        self.assertEqual(replies[-1]['outcome']['heartbeat']['target_at'], '2026-09-17T13:20:00+00:00')
        diagnostics = [r['action']['arguments']['text'] for r in replies if r.get('action', {}).get('purpose') == 'diagnostics']
        self.assertEqual(diagnostics, ['step observe: codex status: synthetic-adapter-failure: synthetic provider unavailable'])

    def test_restart_send(self):
        fixture = self.make('restart-send')
        old = fixture.setup_pending
        self.assertEqual(old['action']['kind'], 'send')
        attempt_id = old['action']['arguments']['attempt_id']
        self.assertGreater(fixture.initial['generation'], old['generation'])
        self.assertNotEqual(fixture.initial['invocation_id'], old['invocation_id'])
        self.assertEqual(fixture.before['attention'][0]['attempt_id'], attempt_id)
        replies = self.finish(fixture)
        self.assertNotIn('send', self.kinds(replies))
        after = fixture.inspect()
        self.assertEqual(after['attention'][0]['attempt_id'], attempt_id)
        self.assertEqual(after['attention'][0]['status'], 'reserved')
        self.assertEqual(after['registrations'][0]['status'], 'reserved')
        self.assertEqual(replies[-1]['outcome']['wakes'], [])

    def test_restart_notice(self):
        fixture = self.make('restart-notice')
        old = fixture.setup_pending
        self.assertEqual(old['action']['purpose'], 'notice')
        self.assertGreater(fixture.initial['generation'], old['generation'])
        self.assertEqual(fixture.initial['action']['purpose'], 'notice')
        self.assertEqual(fixture.initial['action']['arguments']['notice_id'], old['action']['arguments']['notice_id'])
        self.assertEqual(fixture.initial['action']['arguments']['text'], old['action']['arguments']['text'])
        self.assertTrue(fixture.initial['action']['arguments']['replayed'])
        replies = self.finish(fixture)
        self.assertNotIn('send', self.kinds(replies))
        self.assertTrue(replies[-1]['outcome']['notice']['acknowledged'])

    def test_partial_observation(self):
        fixture = self.make('partial-observation')
        self.assertEqual(len({r['gate_key'] for r in fixture.registrations}), 2)
        replies = self.finish(fixture)
        self.assertEqual(self.kinds(replies).count('observe'), 1)
        observation = next(item['constructed_observation'] for item in fixture.transcript if 'constructed_observation' in item)
        self.assertEqual(len(observation['requests']), 2)
        output = json.loads(observation['artifacts'][0]['bytes'])
        report = json.loads(observation['artifacts'][1]['bytes'])
        self.assertEqual(len(output['observations']), 1)
        self.assertEqual([g['outcome'] for g in report['gates']], ['observed', 'error'])
        by_key = {o['gate_key']: o for o in fixture.inspect()['observations']}
        self.assertEqual(by_key[fixture.registrations[0]['gate_key']]['observed_at'], '2026-09-17T13:05:00+00:00')
        self.assertEqual(by_key[fixture.registrations[1]['gate_key']]['observed_at'], '2026-09-17T12:00:00+00:00')
        self.assertEqual(replies[-1]['outcome']['heartbeat']['rule'], 'failed-observation-recovery')
        heartbeat = next(r['action'] for r in replies if r.get('action', {}).get('kind') == 'heartbeat_set')
        self.assertEqual(heartbeat['arguments']['basis']['unanswered_due_gate_keys'], [fixture.registrations[1]['gate_key']])
        self.assertNotIn('send', self.kinds(replies))

    def test_schedule_unavailable(self):
        fixture = self.make('schedule-unavailable')
        self.assertEqual(fixture.initial['action']['kind'], 'heartbeat_set')
        replies = self.finish(fixture)
        self.assertEqual(self.kinds(replies), ['heartbeat_set', 'emit'])
        self.assertEqual(replies[-1]['outcome']['heartbeat']['result'], 'unavailable')
        self.assertEqual(replies[-1]['outcome']['heartbeat']['writes'], 1)
        self.assertIn('synthetic heartbeat control unavailable', replies[-2]['action']['arguments']['text'])

    def test_missing_binding(self):
        fixture = self.make('missing-binding')
        self.assertEqual(fixture.before['observations'], [])
        replies = self.finish(fixture)
        self.assertNotIn('observe', self.kinds(replies))
        self.assertNotIn('send', self.kinds(replies))
        notices = [r['action'] for r in replies if r.get('action', {}).get('purpose') == 'notice']
        self.assertEqual(len(notices), 1)
        self.assertFalse(notices[0]['arguments']['replayed'])
        self.assertIn('new: no-binding gate', notices[0]['arguments']['text'])
        self.assertTrue(replies[-1]['outcome']['notice']['acknowledged'])
        self.assertEqual(replies[-1]['outcome']['heartbeat']['target_at'], '2026-09-17T18:05:00+00:00')
        self.assertEqual(fixture.inspect()['schedule']['reason'], 'configuration-gap')

    def test_missing_binding_repeat(self):
        fixture = self.make('missing-binding-repeat')
        self.assertTrue(fixture.prelude_final['outcome']['notice']['acknowledged'])
        replies = self.finish(fixture)
        self.assertEqual(self.kinds(replies), ['task_read', 'heartbeat_set'])
        self.assertFalse(replies[-1]['outcome']['printed_anything'])
        self.assertIsNone(replies[-1]['outcome']['notice']['notice_id'])
        self.assertEqual(fixture.inspect()['observations'], [])
        self.assertEqual(fixture.inspect()['retry_schedule'], {})
        self.assertEqual(replies[-1]['outcome']['heartbeat']['target_at'], '2026-09-18T00:05:00+00:00')

    def test_shared_gate_single_wake(self):
        fixture = self.make('shared-gate-single-wake')
        self.assertEqual(len(fixture.before['schedule']['gates']), 1)
        self.assertTrue(fixture.before['schedule']['gates'][0]['due'])
        self.assertEqual(len({r['gate_key'] for r in fixture.registrations}), 1)
        self.assertEqual(fixture.before['observations'], [])
        replies = self.finish(fixture)
        self.assertEqual(self.kinds(replies).count('observe'), 1)
        observation = next(item['constructed_observation'] for item in fixture.transcript if 'constructed_observation' in item)
        self.assertEqual(len(observation['requests']), 1)
        self.assertEqual(set(observation['requests'][0]['task_ids']), {'synthetic-task-a', 'synthetic-task-b', 'synthetic-task-c'})
        sends = [r['action'] for r in replies if r.get('action', {}).get('kind') == 'send']
        self.assertEqual(len(sends), 1)
        self.assertEqual(sends[0]['arguments']['task_id'], 'synthetic-task-a')
        read_results = [(i['action']['arguments']['task_id'], i['constructed_result']['status']) for i in fixture.transcript if 'constructed_result' in i and i['action']['kind'] == 'task_read']
        self.assertEqual(read_results, [('synthetic-task-a', 'idle'), ('synthetic-task-b', 'running'), ('synthetic-task-c', 'completed'), ('synthetic-task-a', 'idle')])
        self.assertEqual(len(replies[-1]['outcome']['wakes']), 1)

    def test_paused_expired(self):
        fixture = self.make('paused-expired')
        self.assertEqual(len(fixture.before['registrations']), 2)
        self.assertEqual(fixture.before['registrations'][0]['status'], 'paused')
        self.assertEqual(fixture.before['attention'][0]['status'], 'expired')
        self.assertEqual(fixture.before['observations'][0]['observed_at'], '2026-09-17T12:00:00+00:00')
        replies = self.finish(fixture)
        self.assertNotIn('observe', self.kinds(replies))
        self.assertNotIn('send', self.kinds(replies))
        self.assertEqual(replies[-1]['outcome']['wakes'], [])
        after = fixture.inspect()
        self.assertEqual([r['status'] for r in after['registrations']], ['paused', 'expired'])

    def test_controller_setup_and_control_are_separate(self):
        import subprocess
        import sys
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        driver = Path(__file__).with_name('praxis_fixture.py')
        process = subprocess.run([sys.executable, '-B', str(driver), 'setup', 'due-open',
                                  '--directory', directory.name, '--engine', str(ENGINE)],
                                 capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        entry = json.loads(process.stdout)
        self.assertEqual(set(entry), {'case_id', 'entry_ref', 'initial', 'now', 'engine'})
        self.assertEqual(entry['initial']['action']['kind'], 'task_read')
        reply_path = Path(directory.name) / 'issued-reply.json'
        reply_path.write_text(json.dumps(entry['initial']))
        process = subprocess.run([sys.executable, '-B', str(driver), 'control',
                                  '--directory', directory.name, '--reply', str(reply_path)],
                                 capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout), {'status': 'idle', 'observed_at': '2026-09-17T13:05:00+00:00'})
        self.assertEqual(json.loads(reply_path.read_text()), entry['initial'])
