"""Offline consumer checks through the repo-local mailbox CLI."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "plugins" / "rolecasting" / "skills" / "delegating-cross-agent-work"
    / "scripts" / "native_codex_mailbox.py"
)


class CaptureMailboxTests(unittest.TestCase):

    def test_planned_message_survives_replacement_with_original_content(self):
        original = {'message_id': 'delivery-1', 'sender': {'thread_id': 'dispatch-example', 'host_id': 'local'}, 'recipient': {'thread_id': 'worker-example', 'host_id': 'local'}, 'owner': {'thread_id': 'foreman-example', 'host_id': 'local'}, 'payload': '[delivery-1] Intake only.\r\nKeep é and café unchanged.\n', 'authority_ref': 'synthetic://grant/intake-only', 'holds': ['No operational transfer.', 'Publication remains held.']}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            store = root / 'mailbox.sqlite3'
            source = root / 'message.json'
            source.write_bytes(json.dumps(original).encode('utf-8'))

            def invoke(*args):
                result = subprocess.run([sys.executable, str(SCRIPT), '--store', str(store), *args], capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                return json.loads(result.stdout)
            self.assertEqual(invoke('init'), {'initialized': True})
            self.assertTrue(invoke('plan', '--input', str(source))['created'])
            recovered = invoke('show', 'delivery-1')
            self.assertEqual(recovered, {**original, 'state': 'planned', 'attempts': []})


class NativeCodexMailboxTests(unittest.TestCase):

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.store = self.root / 'mailbox.sqlite3'
        self.run_cli('init')

    def command(self, *arguments):
        if arguments and arguments[0] == 'claim' and ('--actor-thread-id' not in arguments):
            arguments = (*arguments, '--actor-thread-id', 'dispatch-example', '--actor-host-id', 'local')
        return [sys.executable, str(SCRIPT), '--store', str(self.store), *arguments]

    def run_cli(self, *arguments, success=True):
        result = subprocess.run(self.command(*arguments), capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0 if success else 2, result.stderr)
        return json.loads(result.stdout if success else result.stderr)

    def message(self, message_id='delivery-1'):
        return {'message_id': message_id, 'sender': {'thread_id': 'dispatch-example', 'host_id': 'local'}, 'recipient': {'thread_id': 'worker-example', 'host_id': 'local'}, 'owner': {'thread_id': 'foreman-example', 'host_id': 'local'}, 'payload': '[' + message_id + '] Intake only.\r\nKeep é and café unchanged.\n', 'authority_ref': 'synthetic://grant/intake-only', 'holds': ['No operational transfer.', 'Publication remains held.']}

    def plan(self, message=None):
        message = self.message() if message is None else message
        source = self.root / 'message.json'
        source.write_bytes(json.dumps(message, ensure_ascii=True).encode('utf-8'))
        return self.run_cli('plan', '--input', str(source))

    def observe(self, message_id, attempt_id, kind, detail='synthetic observation', success=True):
        source = self.root / 'observation.txt'
        source.write_bytes(detail.encode('utf-8'))
        return self.run_cli('observe', message_id, attempt_id, kind, '--evidence-ref', 'synthetic://evidence/' + kind, '--detail-file', str(source), success=success)

    def test_correlated_delivery_keeps_submission_receipt_handling_and_completion_separate(self):
        original = self.message()
        self.assertEqual(self.plan(original)['message']['state'], 'planned')
        claimed = self.run_cli('claim', 'delivery-1', 'attempt-1')
        self.assertTrue(claimed['claimed'])
        self.assertEqual(claimed['message']['state'], 'unknown')
        submitted = self.observe('delivery-1', 'attempt-1', 'submitted')
        self.assertEqual(submitted['state'], 'submitted')
        self.assertFalse(submitted['attempts'][0]['received'])
        self.assertFalse(submitted['attempts'][0]['handled'])
        self.assertFalse(submitted['attempts'][0]['completed'])
        detail = 'Synthetic receiver worker-example saw delivery-1 / attempt-1.\r\n'
        received = self.observe('delivery-1', 'attempt-1', 'received', detail)
        self.assertEqual(received['state'], 'received')
        self.assertEqual(received['attempts'][0]['observations'][-1]['detail'], detail)
        self.assertFalse(received['attempts'][0]['handled'])
        self.assertFalse(received['attempts'][0]['completed'])
        handled = self.observe('delivery-1', 'attempt-1', 'handled')
        self.assertEqual(handled['state'], 'handled')
        self.assertEqual([item['message_id'] for item in self.run_cli('pending')], ['delivery-1'])
        completed = self.observe('delivery-1', 'attempt-1', 'completed')
        self.assertEqual(completed['state'], 'completed')
        self.assertEqual(completed['payload'], original['payload'])
        self.assertEqual(completed['authority_ref'], original['authority_ref'])
        self.assertEqual(self.run_cli('pending'), [])

    def test_idle_steer_refusal_stays_pending_without_a_new_claim(self):
        self.plan()
        self.run_cli('claim', 'delivery-1', 'attempt-idle')
        refused = self.observe('delivery-1', 'attempt-idle', 'refused', 'Synthetic idle-steer refusal; no active turn was observed.')
        self.assertEqual(refused['state'], 'refused')
        self.assertFalse(refused['attempts'][0]['received'])
        duplicate = self.run_cli('claim', 'delivery-1', 'attempt-retry')
        self.assertFalse(duplicate['claimed'])
        self.assertEqual(duplicate['message']['attempts'][0]['attempt_id'], 'attempt-idle')
        pending = self.run_cli('pending')
        self.assertEqual([item['state'] for item in pending], ['refused'])
        self.assertEqual(pending[0]['holds'], self.message()['holds'])

    def test_uncertain_result_reconciles_without_replay_and_late_events_do_not_erase_receipt(self):
        self.plan()
        self.run_cli('claim', 'delivery-1', 'attempt-lost')
        self.observe('delivery-1', 'attempt-lost', 'unknown', 'Synthetic lost sending response.')
        self.assertFalse(self.run_cli('claim', 'delivery-1', 'attempt-lost')['claimed'])
        received = self.observe('delivery-1', 'attempt-lost', 'received', 'Synthetic native history correlates delivery-1 / attempt-lost.')
        self.assertEqual(received['state'], 'received')
        later = self.observe('delivery-1', 'attempt-lost', 'unknown', 'Later bounded read is inconclusive.')
        self.assertEqual(later['state'], 'received')
        self.assertEqual(later['attempts'][0]['submission'], 'unknown')
        self.assertTrue(later['attempts'][0]['received'])
        self.assertFalse(later['attempts'][0]['completed'])
        self.assertEqual(len(later['attempts'][0]['observations']), 3)

    def test_duplicate_capture_is_idempotent_and_conflicting_bindings_are_rejected(self):
        original = self.message()
        self.assertTrue(self.plan(original)['created'])
        self.assertFalse(self.plan(original)['created'])
        self.assertTrue(self.run_cli('claim', 'delivery-1', 'attempt-1')['claimed'])
        self.assertFalse(self.run_cli('claim', 'delivery-1', 'attempt-2')['claimed'])
        source = self.root / 'conflict.json'
        for field, changed in (('payload', 'Different work.'), ('authority_ref', 'synthetic://other-grant'), ('holds', []), ('owner', {'thread_id': 'replacement-example', 'host_id': 'local'})):
            source.write_bytes(json.dumps({**original, field: changed}).encode('utf-8'))
            self.assertIn('error', self.run_cli('plan', '--input', str(source), success=False))
        self.plan(self.message('other-message'))
        self.assertIn('error', self.run_cli('claim', 'other-message', 'attempt-1', success=False))
        retained = self.run_cli('show', 'delivery-1')
        self.assertEqual({key: retained[key] for key in original}, original)
        self.assertEqual(len(retained['attempts']), 1)

    def test_replacement_actor_is_bound_without_rewriting_original_message(self):
        original = self.message()
        self.plan(original)
        claimed = self.run_cli('claim', 'delivery-1', 'replacement-attempt', '--actor-thread-id', 'replacement-example', '--actor-host-id', 'replacement-host')
        self.assertTrue(claimed['claimed'])
        self.assertEqual(claimed['message']['attempts'][0]['actor'], {'thread_id': 'replacement-example', 'host_id': 'replacement-host'})
        self.assertIsNone(claimed['message']['attempts'][0]['reconciliation'])
        self.assertEqual({key: claimed['message'][key] for key in original}, original)
        self.assertIn('error', self.run_cli('claim', 'delivery-1', 'replacement-attempt', success=False))
        retained = self.run_cli('show', 'delivery-1')
        self.assertEqual(retained, claimed['message'])

    def test_later_attempt_binds_nondelivery_evidence_and_owning_task_decision(self):
        self.plan()
        self.run_cli('claim', 'delivery-1', 'attempt-idle')
        self.observe('delivery-1', 'attempt-idle', 'refused', 'Synthetic idle-steer refusal.')
        continuation = ('--after-attempt', 'attempt-idle', '--decision-ref', 'synthetic://owning-task/continue')
        self.assertFalse(self.run_cli('claim', 'delivery-1', 'attempt-next', *continuation)['claimed'])
        reconciled = self.observe('delivery-1', 'attempt-idle', 'not_delivered', 'Synthetic conclusive native evidence establishes nondelivery.')
        self.assertFalse(self.run_cli('claim', 'delivery-1', 'attempt-next')['claimed'])
        self.assertIn('error', self.run_cli('claim', 'delivery-1', 'attempt-next', '--after-attempt', 'attempt-idle', success=False))
        claimed = self.run_cli('claim', 'delivery-1', 'attempt-next', *continuation, '--actor-thread-id', 'replacement-example', '--actor-host-id', 'local')
        self.assertTrue(claimed['claimed'])
        attempts = claimed['message']['attempts']
        self.assertEqual([attempt['attempt_id'] for attempt in attempts], ['attempt-idle', 'attempt-next'])
        self.assertEqual(attempts[0], reconciled['attempts'][0])
        self.assertEqual(attempts[1]['actor'], {'thread_id': 'replacement-example', 'host_id': 'local'})
        self.assertEqual(attempts[1]['reconciliation'], {'after_attempt': 'attempt-idle', 'nondelivery_ref': 'synthetic://evidence/not_delivered', 'decision_ref': 'synthetic://owning-task/continue'})
        self.assertEqual(claimed['message']['state'], 'unknown')
        self.assertFalse(self.run_cli('claim', 'delivery-1', 'attempt-next', *continuation, '--actor-thread-id', 'replacement-example', '--actor-host-id', 'local')['claimed'])
        self.assertFalse(self.run_cli('claim', 'delivery-1', 'attempt-third', *continuation)['claimed'])
        self.observe('delivery-1', 'attempt-idle', 'unknown', 'Later evidence reopens uncertainty.')
        self.observe('delivery-1', 'attempt-next', 'not_delivered', 'Synthetic second-attempt nondelivery.')
        self.assertFalse(self.run_cli('claim', 'delivery-1', 'attempt-third', '--after-attempt', 'attempt-next', '--decision-ref', 'synthetic://owning-task/another-continuation')['claimed'])
        self.assertEqual(len(self.run_cli('show', 'delivery-1')['attempts']), 2)

    def test_unknown_effects_and_conflicting_receipt_block_later_attempts(self):
        self.plan()
        self.run_cli('claim', 'delivery-1', 'attempt-lost')
        continuation = ('--after-attempt', 'attempt-lost', '--decision-ref', 'synthetic://owning-task/continue')
        self.observe('delivery-1', 'attempt-lost', 'unknown', 'Synthetic lost response.')
        self.assertFalse(self.run_cli('claim', 'delivery-1', 'attempt-fresh', *continuation)['claimed'])
        self.observe('delivery-1', 'attempt-lost', 'not_delivered', 'Synthetic nondelivery conclusion.')
        self.observe('delivery-1', 'attempt-lost', 'unknown', 'New evidence leaves effects uncertain.')
        self.assertFalse(self.run_cli('claim', 'delivery-1', 'attempt-fresh', *continuation)['claimed'])
        self.observe('delivery-1', 'attempt-lost', 'received', 'Synthetic correlated receiver evidence.')
        retained = self.observe('delivery-1', 'attempt-lost', 'not_delivered', 'Conflicting supplied conclusion.')
        self.assertFalse(self.run_cli('claim', 'delivery-1', 'attempt-fresh', *continuation)['claimed'])
        self.assertEqual(retained['state'], 'received')
        self.assertEqual(len(retained['attempts']), 1)
        self.assertEqual([item['kind'] for item in retained['attempts'][0]['observations']], ['unknown', 'not_delivered', 'unknown', 'received', 'not_delivered'])

    def test_replacement_intake_preserves_unsubmitted_uncertain_refused_and_handled_obligations(self):
        for name in ('planned', 'unknown', 'refused', 'handled', 'completed'):
            self.plan(self.message(name))
            if name != 'planned':
                self.run_cli('claim', name, 'attempt-' + name)
            if name in ('refused', 'handled', 'completed'):
                self.observe(name, 'attempt-' + name, name)
        pending = self.run_cli('pending')
        self.assertEqual([item['message_id'] for item in pending], ['handled', 'planned', 'refused', 'unknown'])
        for retained in pending:
            original = self.message(retained['message_id'])
            self.assertEqual(retained['state'], retained['message_id'])
            self.assertEqual({key: retained[key] for key in original}, original)
        handled = self.run_cli('show', 'handled')['attempts'][0]
        self.assertTrue(handled['handled'])
        self.assertFalse(handled['received'])

    def test_observation_cannot_be_attached_to_a_different_message_or_attempt(self):
        self.plan()
        self.plan(self.message('other-message'))
        self.run_cli('claim', 'delivery-1', 'attempt-1')
        self.assertIn('error', self.observe('other-message', 'attempt-1', 'completed', success=False))
        self.assertIn('error', self.observe('delivery-1', 'wrong-attempt', 'received', success=False))
        self.assertEqual(self.run_cli('show', 'delivery-1')['state'], 'unknown')
        self.assertEqual(self.run_cli('show', 'other-message')['state'], 'planned')

    def test_concurrent_claimers_get_one_submission_claim(self):
        self.plan()
        processes = [subprocess.Popen(self.command('claim', 'delivery-1', attempt), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for attempt in ('attempt-a', 'attempt-b')]
        try:
            results = []
            for process in processes:
                stdout, stderr = process.communicate(timeout=10)
                self.assertEqual(process.returncode, 0, stderr)
                results.append(json.loads(stdout))
            self.assertEqual(sorted((result['claimed'] for result in results)), [False, True])
            self.assertEqual(len(self.run_cli('show', 'delivery-1')['attempts']), 1)
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                process.communicate()

    def test_replacement_read_never_initializes_a_missing_store(self):
        missing = self.root / 'wrong-store.sqlite3'
        result = subprocess.run([sys.executable, str(SCRIPT), '--store', str(missing), 'pending'], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertIn('error', json.loads(result.stderr))
        self.assertFalse(missing.exists())
        self.assertIn('error', self.run_cli('init', success=False))


if __name__ == "__main__":
    unittest.main()
