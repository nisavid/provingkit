"""Author verification of the actual owner-admission command with an inert peer."""
import json
import importlib
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / 'plugins/surreal-intercom/skills/communicating-with-agents/scripts'
SENDER = SCRIPTS / 'owner_admission_sender.py'


class AuthorVerificationCliTests(unittest.TestCase):
    def test_ambient_sender_override_does_not_change_routine_suite(self):
        env = dict(os.environ, ARTIFICE_SENDER_SCRIPT='/nonexistent/artifice-sender.py')
        result = subprocess.run([
            sys.executable, '-B', '-m', 'unittest',
            'tests.plugins.surreal_intercom.test_artifice_author_cli.'
            'AuthorVerificationCliTests.test_wrong_type_in_scope_refuses_before_connection',
        ], cwd=ROOT, env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def assert_scope_refused(self, scope, *, malformed=False):
        with tempfile.TemporaryDirectory(prefix='artifice-author-') as name:
            root = Path(name)
            store, capture, endpoint = root / 'mailbox.sqlite3', root / 'capture', root / 'peer.sock'
            capture.mkdir()
            original = {
                'message_id':'message', 'correlation_id':'exchange',
                'sender':{'thread_id':'origin','host_id':'origin-host'},
                'recipient':{'thread_id':'target','host_id':'local'},
                'owner':{'thread_id':'owner','host_id':'owner-host'},
                'payload':'synthetic', 'authority_ref':'synthetic://authority',
                'holds':['synthetic://hold'],
            }
            message = root / 'message.json'
            message.write_text(json.dumps(original))
            def mailbox(*args):
                result = subprocess.run([sys.executable, '-B', str(SCRIPTS / 'native_codex_mailbox.py'),
                                         '--store', str(store), *args], capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                return json.loads(result.stdout)
            mailbox('init')
            mailbox('plan', '--input', str(message))
            request = {
                'message_id':'message', 'attempt_id':'attempt',
                'actor':{'thread_id':'actor','host_id':'local'}, 'recipient':original['recipient'],
                'evidence_ref':'synthetic://evidence',
                'native':{'route':{'endpoint':str(endpoint),'host':'local','target':'target'},
                          'nominationRef':'synthetic://nomination', 'purpose':'synthetic',
                          'authorityRefs':['synthetic://authority'], 'holdRefs':['synthetic://hold'],
                          'scope':scope,
                          'observationSeconds':0.1},
                'capture':{'run_root':str(capture),'allowance_bytes':8388608,
                           'terminal_provision_bytes':524288,'later_forecast_bytes':0},
            }
            request_file = root / 'request.json'
            encoded = json.dumps(request)
            request_file.write_text(encoded[:-1] if malformed else encoded)
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
                listener.bind(str(endpoint))
                listener.listen(1)
                listener.settimeout(0.1)
                result = subprocess.run([sys.executable, '-B', str(SENDER), '--store', str(store),
                                         '--request', str(request_file)], capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                observation = json.loads(result.stdout)
                self.assertFalse(observation['claimed'])
                self.assertEqual(observation['peer_input'], 'not_attempted')
                if not malformed:
                    self.assertEqual(observation['reason'], 'explicit-owner-admission-scope-required')
                with self.assertRaises(TimeoutError):
                    listener.accept()
            self.assertEqual(mailbox('show', 'message')['state'], 'planned')
            self.assertEqual(list(capture.iterdir()), [])

    def test_wrong_type_in_scope_refuses_before_connection(self):
        self.assert_scope_refused({'send':1,'ownerAdmissionIntent':True,'holdsSatisfied':True})

    def test_incomplete_scope_refuses_before_connection(self):
        self.assert_scope_refused({'send':True,'ownerAdmissionIntent':True})

    def test_malformed_json_refuses_before_connection(self):
        self.assert_scope_refused({'send':True,'ownerAdmissionIntent':True,'holdsSatisfied':True}, malformed=True)

    def test_valid_request_reaches_disposable_peer(self):
        module = importlib.import_module('tests.plugins.surreal_intercom.test_rolecasting_codex_owner_admission')
        fixture = module.CodexOwnerAdmissionTests('test_local_owner_request_preserves_peer_envelope_and_admission_flags')
        result, _ = fixture.exchange()
        self.assertTrue(result['claimed'])
        self.assertEqual(result['peer_input'], 'possible_submission')


if __name__ == '__main__':
    unittest.main()
