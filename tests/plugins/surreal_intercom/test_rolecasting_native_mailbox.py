"""Offline consumer checks through the repo-local mailbox CLI."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "plugins" / "surreal-intercom" / "skills" / "communicating-with-agents"
    / "scripts" / "native_codex_mailbox.py"
)
SCRIPTS = SCRIPT.parent
REFERENCES = SCRIPTS.parent / 'references'
sys.path.insert(0, str(SCRIPTS))
from peer_message import serialize_peer_message  # noqa: E402


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

    def procedure_reply_route(self, message, kind):
        reference = REFERENCES / (
            'codex-route-nomination.md'
            if kind == 'codex-owner-admission' else 'claude-route-nomination.md'
        )
        text = reference.read_text(encoding='utf-8')
        start = f'<!-- reply-route-example:{kind}:start -->'
        end = f'<!-- reply-route-example:{kind}:end -->'
        section = text.split(start, 1)[1].split(end, 1)[0].strip()
        self.assertTrue(section.startswith('```json\n'))
        self.assertTrue(section.endswith('\n```'))
        template = json.loads(section[len('```json\n'):-len('\n```')])
        helper_path = '/opt/helpers/codex_route_nomination.py'
        bindings = {
            '$REPLY_RECIPIENT_THREAD_ID': message['sender']['thread_id'],
            '$REPLY_RECIPIENT_HOST_ID': message['sender']['host_id'],
            '$REPLY_SUBMITTER_THREAD_ID': message['recipient']['thread_id'],
            '$REPLY_SUBMITTER_HOST_ID': message['recipient']['host_id'],
            '$CORRELATION_ID': message.get('correlation_id', message['message_id']),
            '$NOMINATION_PATH': '/synthetic/private/nomination.json',
            '$NOMINATION_SHA256': 'a' * 64,
            '$NOMINATION_SIZE': 1024,
            '$INVOCATION_TASK_REF': 'synthetic://task/return-route',
            '$INVOCATION_ATTEMPT_ID': 'return-route-acquisition',
            '$INVOCATION_COMMAND': [
                '/usr/bin/python3', '-B', helper_path,
                '--request', '/synthetic/private/request.json',
            ],
            '$INVOCATION_WORKING_DIRECTORY': '/synthetic/worktree',
            '$INVOCATION_HELPER_PATH': helper_path,
            '$INVOCATION_HELPER_SHA256': 'b' * 64,
            '$INVOCATION_EVIDENCE_REF': 'synthetic://native/return-route',
            '$INVOCATION_NATIVE_ITEM_ID': 'item-return-route',
        }

        def materialize(value):
            if isinstance(value, str) and value in bindings:
                return bindings[value]
            if isinstance(value, dict):
                return {key: materialize(item) for key, item in value.items()}
            if isinstance(value, list):
                return [materialize(item) for item in value]
            return value

        return materialize(template)

    def plan(self, message=None, success=True):
        message = self.message() if message is None else message
        source = self.root / 'message.json'
        source.write_bytes(json.dumps(message, ensure_ascii=True).encode('utf-8'))
        return self.run_cli('plan', '--input', str(source), success=success)

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

    def test_safe_codex_and_claude_reply_routes_survive_mailbox_and_peer_serialization(self):
        actor = {'thread_id': 'worker-example', 'host_id': 'local'}
        for kind in ('codex-owner-admission', 'claude-mcp'):
            with self.subTest(kind=kind):
                original = {**self.message(kind), 'correlation_id': 'shared-exchange'}
                original['reply_route'] = self.procedure_reply_route(original, kind)

                retained = self.plan(original)['message']
                self.assertEqual({key: retained[key] for key in original}, original)
                prefix, encoded = serialize_peer_message(original, actor).split('\n', 1)
                self.assertEqual(prefix, 'Peer message (no new operator authority).')
                envelope = json.loads(encoded)
                self.assertEqual(envelope['reply_route'], original['reply_route'])
                self.assertEqual(envelope['payload'], original['payload'])
                self.assertEqual(envelope['sender'], original['sender'])
                self.assertEqual(envelope['actor'], actor)
                self.assertEqual(envelope['recipient'], original['recipient'])
                self.assertEqual(envelope['owner'], original['owner'])
                self.assertEqual(envelope['authority_ref'], original['authority_ref'])
                self.assertEqual(envelope['holds'], original['holds'])
                self.assertEqual(envelope['correlation_id'], 'shared-exchange')
                self.assertNotIn('endpoint', encoded)

    def test_reply_route_refuses_mismatched_bindings_and_malformed_variants(self):
        base = {**self.message(), 'correlation_id': 'shared-exchange'}
        valid = self.procedure_reply_route(base, 'codex-owner-admission')
        mutations = {
            'recipient': lambda value: value.update(
                recipient={'thread_id': 'other', 'host_id': 'local'}),
            'submitter': lambda value: value.update(
                submitter={'thread_id': 'other', 'host_id': 'local'}),
            'correlation': lambda value: value.update(correlation_id='other-exchange'),
            'generic-kind': lambda value: value.update(kind='generic-route'),
            'raw-endpoint': lambda value: value['nomination'].update(
                endpoint='/synthetic/private/peer.sock'),
            'path-type': lambda value: value['nomination'].update(path=7),
            'relative-path': lambda value: value['nomination'].update(path='nomination.json'),
            'digest': lambda value: value['nomination'].update(sha256='not-a-digest'),
            'size': lambda value: value['nomination'].update(size=0),
            'working-directory-type': lambda value: value['nomination']['invocation'].update(
                workingDirectory=7),
            'empty-command': lambda value: value['nomination']['invocation'].update(command=[]),
            'helper-digest-type': lambda value: value['nomination']['invocation']['helper'].update(
                sha256=7),
            'invocation-status': lambda value: value['nomination']['invocation'].update(
                status='pending'),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                candidate = json.loads(json.dumps(valid))
                mutate(candidate)
                result = self.plan({**base, 'reply_route': candidate}, success=False)
                self.assertIn('error', result)

    def test_verified_bound_native_return_needs_no_nomination_field(self):
        original = {**self.message('native-reply'), 'correlation_id': 'native-exchange'}
        actor = {'thread_id': 'worker-example', 'host_id': 'local'}

        retained = self.plan(original)['message']
        envelope = json.loads(serialize_peer_message(original, actor).split('\n', 1)[1])

        self.assertNotIn('reply_route', retained)
        self.assertNotIn('reply_route', envelope)
        self.assertEqual(envelope['correlation_id'], 'native-exchange')
        self.assertEqual(envelope['sender'], original['sender'])
        self.assertEqual(envelope['recipient'], original['recipient'])

    def test_legacy_message_peer_bytes_remain_exactly_unchanged(self):
        original = {**self.message(), 'correlation_id': 'shared-exchange'}
        actor = {'thread_id': 'worker-example', 'host_id': 'local'}
        expected = 'Peer message (no new operator authority).\n' + json.dumps({
            'schema': 'provingkit-peer-message-v1',
            'message_id': original['message_id'],
            'correlation_id': original['correlation_id'],
            'sender': original['sender'],
            'actor': actor,
            'recipient': original['recipient'],
            'owner': original['owner'],
            'authority_ref': original['authority_ref'],
            'holds': original['holds'],
            'payload': original['payload'],
        }, ensure_ascii=True, sort_keys=True, separators=(',', ':'))

        self.assertEqual(serialize_peer_message(original, actor), expected)

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
