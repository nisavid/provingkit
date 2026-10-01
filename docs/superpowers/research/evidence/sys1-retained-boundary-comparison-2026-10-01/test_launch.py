import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

SPEC = importlib.util.spec_from_file_location('boundary_launch', Path(__file__).with_name('launch.py'))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class DeadlineTests(unittest.TestCase):
    def test_deadline_preserves_started_unknown_and_leaves_the_rest_unattempted(self):
        with tempfile.TemporaryDirectory() as scratch:
            out = Path(scratch) / 'run'
            child = ('from pathlib import Path; import time; '
                     "p=Path('attempts'); p.mkdir(); "
                     "(p/'B10-start.json').write_text('{}'); time.sleep(30)")
            started = time.monotonic()
            result = MODULE.supervise([sys.executable, '-c', child], out,
                                      started + 0.4)
            self.assertEqual(result['status'], 'deadline')
            self.assertGreaterEqual(result['timing']['supervision_seconds'], 0.3)
            self.assertGreaterEqual(result['timing']['termination_seconds'], 0)
            self.assertGreaterEqual(result['timing']['reconciliation_seconds'], 0)
            self.assertAlmostEqual(result['timing']['elapsed_through_reconciliation_seconds'],
                                   sum(result['timing'][key] for key in (
                                       'initialization_seconds', 'supervision_seconds',
                                       'termination_seconds', 'reconciliation_seconds')), places=6)
            self.assertLess(time.monotonic() - started, 3)
            self.assertEqual(result['cells'][0]['status'], 'unknown_after_start')
            self.assertEqual(sum(c['status'] == 'unattempted' for c in result['cells']), 7)
            self.assertEqual((out / 'attempts/B10-start.json').read_text(), '{}')
            before = (out / 'launcher.json').read_bytes()
            with self.assertRaises(FileExistsError):
                MODULE.supervise([sys.executable, '-c', 'raise SystemExit(0)'], out,
                                 time.monotonic() + 2)
            self.assertEqual((out / 'launcher.json').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
