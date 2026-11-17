"""Complete, create-only capture publication on a test-owned filesystem.

Exercise CaptureWriter's public write methods with filesystem fault injection;
no host, transport, account, or process observations are acquired.
"""

import hashlib
import importlib.util
import os
import stat
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = (Path(__file__).resolve().parents[3] /
          "plugins/surreal-intercom/skills/communicating-with-agents/scripts/codex_capture.py")
spec = importlib.util.spec_from_file_location("capture_publication_subject", SCRIPT)
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)


class CapturePublicationTests(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name).resolve()
        self.settings = {"run_root": str(self.root), "allowance_bytes": 8388608,
                         "terminal_provision_bytes": capture.TERMINAL,
                         "later_forecast_bytes": 0}
        self.writer = capture.CaptureWriter(self.settings)

    def test_restrictive_umask_preserves_readable_exact_owner_permissions(self):
        # The fixture root exists before changing the process-local umask.
        for method, expected in (("write", b"complete"),
                                 ("write_json", b'{"status":"complete"}')):
            with self.subTest(method=method):
                final = self.root / method
                previous = os.umask(0o477)
                try:
                    if method == "write":
                        self.writer.write(final, b"complete")
                    else:
                        self.writer.write_json(final, {"status": "complete"})
                finally:
                    os.umask(previous)
                self.assertEqual(stat.S_IMODE(final.stat().st_mode), 0o600)
                self.assertEqual(final.read_bytes(), expected)

    def test_permission_failure_never_publishes_and_cleans_own_staging(self):
        final = self.root / "record"
        with patch.object(capture.os, "fchmod", side_effect=OSError("synthetic permission failure")):
            with self.assertRaisesRegex(OSError, "synthetic permission failure"):
                self.writer.write(final, b"complete")
        self.assertFalse(final.exists())
        self.assertEqual(list(self.root.iterdir()), [])
        self.assertEqual(self.writer.new_bytes, 0)
        self.assertEqual(self.writer.terminal_bytes, 0)

    def test_sync_failure_never_exposes_failed_json_as_final(self):
        final = self.root / "record.json"
        with patch.object(capture.os, "fsync", side_effect=OSError("synthetic sync failure")):
            with self.assertRaisesRegex(OSError, "synthetic sync failure"):
                self.writer.write_json(final, {"status": "complete"})
        self.assertFalse(final.exists(), "failed capture must not advertise final bytes")
        self.assertEqual(list(self.root.iterdir()), [])

    def test_partial_write_failure_stays_unpublished_and_counts_written_bytes(self):
        final = self.root / "record"
        real_write = capture.os.write
        calls = 0

        def fail_after_prefix(fd, data):
            nonlocal calls
            calls += 1
            if calls == 1:
                return real_write(fd, data[:3])
            raise OSError("synthetic write failure")

        with patch.object(capture.os, "write", side_effect=fail_after_prefix):
            with self.assertRaisesRegex(OSError, "synthetic write failure"):
                self.writer.write(final, b"complete")
        self.assertFalse(final.exists())
        self.assertEqual(list(self.root.iterdir()), [])
        self.assertEqual(self.writer.new_bytes, 3)
        self.assertEqual(self.writer.terminal_bytes, 0)
        capture.CaptureWriter(self.settings).write(final, b"retry complete")
        self.assertEqual(final.read_bytes(), b"retry complete")

    def test_short_writes_publish_all_bytes(self):
        final = self.root / "record"
        real_write = capture.os.write
        with patch.object(capture.os, "write", side_effect=lambda fd, data: real_write(fd, data[:2])):
            self.writer.write(final, b"complete")
        self.assertEqual(final.read_bytes(), b"complete")
        self.assertEqual(list(self.root.iterdir()), [final])
        self.assertEqual(self.writer.new_bytes, 8)

    def test_zero_progress_refuses_without_final(self):
        final = self.root / "record"
        with patch.object(capture.os, "write", return_value=0):
            with self.assertRaisesRegex(capture.StorageRefusal, "capture-write-incomplete"):
                self.writer.write(final, b"complete")
        self.assertFalse(final.exists())
        self.assertEqual(list(self.root.iterdir()), [])
        self.assertEqual(self.writer.new_bytes, 0)

    def test_interrupted_staging_is_cleaned_without_removing_other_files(self):
        retained = self.root / ".codex-capture-other.tmp"
        retained.write_bytes(b"unrelated staging")
        final = self.root / "record"
        with patch.object(capture.os, "fsync", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.writer.write(final, b"complete")
        self.assertFalse(final.exists())
        self.assertEqual(list(self.root.iterdir()), [retained])
        self.assertEqual(retained.read_bytes(), b"unrelated staging")
        capture.CaptureWriter(self.settings).write(final, b"retry")
        self.assertEqual(final.read_bytes(), b"retry")
        self.assertEqual(retained.read_bytes(), b"unrelated staging")

    def test_existing_final_is_preserved(self):
        final = self.root / "record"
        final.write_bytes(b"retained")
        with self.assertRaises(FileExistsError):
            self.writer.write(final, b"new complete bytes")
        self.assertEqual(final.read_bytes(), b"retained")
        self.assertEqual(list(self.root.iterdir()), [final])

    def test_final_created_during_staging_is_preserved(self):
        final = self.root / "record"
        real_sync = capture.os.fsync

        def concurrent_final(fd):
            final.write_bytes(b"concurrent complete bytes")
            real_sync(fd)

        with patch.object(capture.os, "fsync", side_effect=concurrent_final):
            with self.assertRaises(FileExistsError):
                self.writer.write(final, b"complete")
        self.assertEqual(final.read_bytes(), b"concurrent complete bytes")
        self.assertEqual(list(self.root.iterdir()), [final])

    def test_publication_failure_removes_only_own_staging(self):
        final = self.root / "record"
        with patch.object(capture.os, "link", side_effect=OSError("synthetic publication failure")):
            with self.assertRaisesRegex(OSError, "synthetic publication failure"):
                self.writer.write(final, b"complete")
        self.assertFalse(final.exists())
        self.assertEqual(list(self.root.iterdir()), [])
        self.assertEqual(self.writer.new_bytes, 8)

    def test_final_is_absent_until_bytes_are_synced(self):
        final = self.root / "record"
        real_sync = capture.os.fsync

        def inspect_before_sync(fd):
            self.assertFalse(final.exists())
            real_sync(fd)

        with patch.object(capture.os, "fsync", side_effect=inspect_before_sync):
            self.writer.write(final, b"complete")
        self.assertEqual(final.read_bytes(), b"complete")

    def test_empty_capture_publishes_complete_empty_bytes(self):
        final = self.root / "record"
        self.writer.write(final, b"")
        self.assertEqual(final.read_bytes(), b"")
        self.assertEqual(list(self.root.iterdir()), [final])
        self.assertEqual(self.writer.new_bytes, 0)

    def test_json_digest_names_complete_bytes(self):
        final = self.root / "nested" / "record.json"
        digest = self.writer.write_json(final, {"status": "complete"})
        expected = b'{"status":"complete"}'
        self.assertEqual(final.read_bytes(), expected)
        self.assertEqual(digest, hashlib.sha256(expected).hexdigest())

    def test_failed_terminal_write_preserves_accounting_and_remaining_provision(self):
        with patch.object(capture.os, "fsync", side_effect=OSError("synthetic sync failure")):
            with self.assertRaises(OSError):
                self.writer.write(self.root / "stdout", b"prefix", terminal=True)
        self.assertEqual(self.writer.new_bytes, 6)
        self.assertEqual(self.writer.terminal_bytes, 6)
        self.assertFalse((self.root / "stdout").exists())
        self.writer.write(self.root / "stderr", b"diagnostic", terminal=True)
        self.assertEqual(self.writer.new_bytes, 16)
        self.assertEqual(self.writer.terminal_bytes, 16)
        self.assertEqual((self.root / "stderr").read_bytes(), b"diagnostic")
        self.assertEqual(self.writer.observations[-1]["terminalAfterBytes"], capture.TERMINAL - 16)

    def test_nonterminal_allowance_still_reserves_terminal_bytes(self):
        settings = dict(self.settings, allowance_bytes=capture.TERMINAL + 8)
        writer = capture.CaptureWriter(settings)
        writer.write(self.root / "record", b"complete")
        with self.assertRaisesRegex(capture.StorageRefusal, "run-storage-limit"):
            writer.write(self.root / "overflow", b"x")
        writer.write(self.root / "stderr", b"diagnostic", terminal=True)
        self.assertFalse((self.root / "overflow").exists())
        self.assertEqual((self.root / "stderr").read_bytes(), b"diagnostic")


if __name__ == "__main__":
    unittest.main()
