"""Consumer checks for the version-1 preparation CLI."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

CLI = Path(__file__).with_name('prepare_seed.py')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def identity(entries):
    canonical = json.dumps(entries, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    return digest(canonical)


class PreparationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.seed = self.root / 'source'
        (self.seed / 'bin').mkdir(parents=True)
        (self.seed / 'tests').mkdir()
        self.files = {'bin/report': b'#!/bin/sh\necho ordinary\n', 'tests/test_report.py': b'assert True\n'}
        for name, data in self.files.items():
            path = self.seed / name
            path.write_bytes(data)
            if name == 'bin/report':
                path.chmod(0o755)
        self.requests = self.root / 'request.txt'
        self.requests.write_bytes(b'Add JSON output\n')
        self.case = self.root / 'case.json'
        self.case.write_bytes(b'{"input":"empty"}\n')
        self.spec = {
            'version': 1,
            'seed': self.directory_spec('source', self.files),
            'requests': [{'path': 'request.txt', 'sha256': digest(self.requests.read_bytes())}],
            'observation_cases': [{'id': 'empty', 'path': 'case.json', 'sha256': digest(self.case.read_bytes())}],
            'constructed_candidates': [],
        }
        self.spec_path = self.root / 'spec.json'
        self.output = self.root / 'packet'

    def directory_spec(self, path, files):
        entries = []
        for name, data in sorted(files.items()):
            mode = ((self.root / path / name).stat().st_mode & 0o111) != 0
            entries.append({'path': name, 'sha256': digest(data), 'executable': mode})
        return {'path': path, 'files': entries, 'identity': identity(entries)}

    def run_cli(self):
        self.spec_path.write_bytes(json.dumps(self.spec).encode())
        return subprocess.run([sys.executable, str(CLI), '--spec', str(self.spec_path), '--output', str(self.output)], capture_output=True, text=True)

    def test_preserves_seed_requests_cases_and_manifest_bindings(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        for name, data in self.files.items():
            self.assertEqual((self.output / 'seed' / name).read_bytes(), data)
        self.assertEqual((self.output / 'requests' / '0000').read_bytes(), self.requests.read_bytes())
        self.assertEqual((self.output / 'cases' / 'empty').read_bytes(), self.case.read_bytes())
        receipt = json.loads((self.output / 'receipt.json').read_bytes())
        self.assertEqual(receipt['spec_sha256'], digest(self.spec_path.read_bytes()))
        self.assertEqual(receipt['seed']['identity'], self.spec['seed']['identity'])
        self.assertEqual(receipt['requests'][0]['sha256'], digest(self.requests.read_bytes()))
        self.assertEqual(receipt['observation_cases'][0]['sha256'], digest(self.case.read_bytes()))
        self.assertEqual(receipt['status'], 'ready')
        self.assertEqual(receipt['seed']['files'][0]['sha256'], digest(self.files['bin/report']))
        self.assertTrue((self.output / 'seed' / 'bin/report').stat().st_mode & 0o111)
        self.assertEqual(receipt['logical_bytes_read'], len(self.spec_path.read_bytes()) + sum(map(len, self.files.values())) + len(self.requests.read_bytes()) + len(self.case.read_bytes()))

    def test_changed_or_missing_input_refuses_ready_package(self):
        self.requests.write_bytes(b'changed')
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())
        self.requests.unlink()
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())

    def test_package_retains_the_exact_preparation_spec(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.output / 'spec.json').read_bytes(), self.spec_path.read_bytes())

    def test_receipt_records_preparation_duration(self):
        started = time.monotonic()
        result = self.run_cli()
        elapsed = time.monotonic() - started
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads((self.output / 'receipt.json').read_bytes())
        self.assertGreater(receipt['preparation_elapsed_seconds'], 0)
        self.assertLessEqual(receipt['preparation_elapsed_seconds'], elapsed)

    def test_constructed_candidate_is_separate(self):
        candidate = self.root / 'variant'
        candidate.mkdir()
        (candidate / 'change.py').write_bytes(b'constructed bytes\n')
        self.spec['constructed_candidates'] = [{'id': 'candidate_1', 'source': self.directory_spec('variant', {'change.py': b'constructed bytes\n'})}]
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.output / 'constructed_candidates' / 'candidate_1' / 'change.py').read_bytes(), b'constructed bytes\n')
        self.assertFalse((self.output / 'seed' / 'change.py').exists())
        receipt = json.loads((self.output / 'receipt.json').read_bytes())
        self.assertEqual(receipt['constructed_candidates'][0]['identity'], self.spec['constructed_candidates'][0]['source']['identity'])

    def test_existing_output_is_unchanged(self):
        self.output.mkdir()
        marker = self.output / 'keep'
        marker.write_bytes(b'original')
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(self.output.iterdir()), [marker])
        self.assertEqual(marker.read_bytes(), b'original')

    def test_output_inside_selected_source_is_refused(self):
        self.output = self.seed / 'packet'
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
