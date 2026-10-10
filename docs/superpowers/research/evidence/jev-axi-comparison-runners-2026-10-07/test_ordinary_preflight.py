"""Exercise ordinary preflight through its public CLI and the controlled HTTP seam."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from test_comparison_runner import service

PREFLIGHT = Path(__file__).with_name('ordinary_preflight.py')

class OrdinaryPreflightCLI(unittest.TestCase):
    def test_wrong_claim_matrix_refuses_before_any_request(self):
        with tempfile.TemporaryDirectory() as temporary, service({}) as (endpoint, received):
            root = Path(temporary)
            candidate = root / 'candidate.txt'
            candidate.write_text('Assertion: alpha.\nSource: alpha is recorded.\n')
            spec = {
                'version': 1, 'kind': 'claim',
                'cases': [{'id': 'c01', 'status': 'ready', 'input': {
                    'path': str(candidate),
                    'sha256': hashlib.sha256(candidate.read_bytes()).hexdigest()}}],
                'conditions': [{'id': 'decisions', 'adapter': 'decisions',
                    'model': 'gpt-6-luna', 'effort': None, 'endpoint': endpoint,
                    'billing': 'local_test', 'auth_env': None,
                    'rates': {'input': '0.10', 'cached': '0', 'write': '0', 'output': '0'}}],
                'limits': {'request_seconds': 2, 'run_seconds': 10, 'input_bytes': 65536,
                    'request_bytes': 131072, 'response_bytes': 1048576, 'requests_per_cell': 1}}
            spec_path, bindings_path = root / 'spec.json', root / 'bindings.json'
            spec_path.write_text(json.dumps(spec))
            bindings_path.write_text('{}')
            result = subprocess.run([
                sys.executable, str(PREFLIGHT), '--spec', str(spec_path),
                '--spec-sha256', hashlib.sha256(spec_path.read_bytes()).hexdigest(),
                '--bindings', str(bindings_path),
                '--bindings-sha256', hashlib.sha256(bindings_path.read_bytes()).hexdigest()],
                capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 2, result.stderr)
            refusal = json.loads(result.stdout)
            self.assertEqual(refusal['reason'], 'claim case matrix differs')
            self.assertEqual(refusal['requests_submitted'], 0)
            self.assertEqual(received, [])
            self.assertFalse((root / 'prepared').exists())
            self.assertFalse((root / 'run').exists())

if __name__ == '__main__':
    unittest.main()
