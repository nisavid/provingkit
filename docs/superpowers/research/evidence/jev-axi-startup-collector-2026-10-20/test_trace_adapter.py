"""Literal input/output checks for the trace projection CLI."""

import json
from pathlib import Path
import subprocess
import sys
import unittest


ADAPTER = Path(__file__).with_name("trace_adapter.py")


class TraceAdapterTests(unittest.TestCase):
    def adapt(self, raw, *arguments):
        result = subprocess.run(
            [sys.executable, str(ADAPTER), "--root-pid", "71", *arguments],
            input=raw, capture_output=True, timeout=5,
        )
        return result, [json.loads(line) for line in result.stdout.splitlines()]

    def test_openat_preserves_observed_path_and_error_without_inventing_resolution(self):
        result, records = self.adapt(
            b'openat(7, "config", O_RDONLY) = -1 ENOENT (No such file or directory)\n'
            b'+++ exited with 1 +++\n'
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        operation = next(r for r in records if r["kind"] == "operation")
        self.assertEqual(operation["name"], "openat")
        self.assertEqual(operation["operands"]["path"],
                         {"state": "known", "hex": "636f6e666967", "complete": True})
        self.assertEqual(operation["operands"]["dirfd"], {"state": "known", "value": "7"})
        self.assertEqual(operation["result"], {"state": "error", "value": "-1", "errno": "ENOENT"})
        self.assertEqual(operation["interpretation"], "observed_operands_only")
        self.assertNotIn(b"No such file", result.stdout)
        self.assertEqual(records[-1]["status"], "complete")
        self.assertEqual(records[-1]["descendant_closure"], "unknown")

    def test_quoted_bytes_are_preserved_without_unicode_or_argument_splitting(self):
        for literal, expected in [(br'"\x66\x66\xff"', "6666ff"),
                                  (b'"a, b"', "612c2062"),
                                  (br'"a\n\"\\\377"', "610a225cff")]:
            with self.subTest(literal=literal):
                result, records = self.adapt(b'open(' + literal + b', O_RDONLY) = 3\n+++ exited with 0 +++\n')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(records[1]["operands"]["path"]["hex"], expected)

    def test_bounds_keep_a_complete_terminal_and_only_the_accepted_prefix(self):
        cases = [
            (b"x" * 20000, (), "raw_line_limit", 8192, 16384),
            (b'open("a", O_RDONLY) = 3\n' * 4, ("--max-records", "3"), "record_limit", 4194304, 3),
            (b'open("' + b"a" * 2000 + b'", O_RDONLY) = 3\n', (), "normalized_record_limit", 4194304, 16384),
        ]
        for raw, args, reason, byte_limit, record_limit in cases:
            with self.subTest(reason=reason):
                result, records = self.adapt(raw, *args)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(records[-1]["kind"], "terminal")
                self.assertEqual(records[-1]["reason"], reason)
                self.assertLessEqual(len(result.stdout), byte_limit)
                self.assertLessEqual(len(records), record_limit)
                self.assertTrue(all(len(line) + 1 <= 4096 for line in result.stdout.splitlines()))
                self.assertEqual(records[-1]["normalized_bytes_emitted_before_terminal"],
                                 sum(len(line) + 1 for line in result.stdout.splitlines()[:-1]))

    def test_unfinished_calls_require_matching_identity_and_completion(self):
        raw = (b'[pid 71] openat(7, "config", O_RDONLY <unfinished ...>\n'
               b'[pid 71] <... openat resumed>) = 3\n'
               b'[pid 71] +++ exited with 0 +++\n')
        result, records = self.adapt(raw)
        self.assertEqual(result.returncode, 0, result.stderr)
        operations = [r for r in records if r["kind"] == "operation"]
        self.assertEqual([r["phase"] for r in operations], ["begin", "end"])
        self.assertEqual(operations[0]["call"], operations[1]["call"])
        self.assertEqual(operations[1]["source_receipts"], [1, 2])
        self.assertEqual(operations[1]["operands"]["path"]["hex"], "636f6e666967")
        for bad in [raw.splitlines(keepends=True)[0],
                    raw.replace(b'<... openat resumed>', b'<... open resumed>'),
                    raw.replace(b'[pid 71] <...', b'[pid 72] <...')]:
            with self.subTest(bad=bad):
                result, records = self.adapt(bad)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(records[-1]["status"], "incomplete")

    def test_structured_openat2_keeps_input_fields_and_refuses_unprojected_extensions(self):
        raw = b'openat2(AT_FDCWD, "config", {flags=O_RDONLY|O_CLOEXEC, resolve=RESOLVE_BENEATH}, 24) = 3\n+++ exited with 0 +++\n'
        result, records = self.adapt(raw)
        self.assertEqual(result.returncode, 0, result.stderr)
        args = records[1]["operands"]
        self.assertEqual(args["how"]["flags"]["symbols"], ["O_RDONLY", "O_CLOEXEC"])
        self.assertEqual(args["how"]["resolve"]["symbols"], ["RESOLVE_BENEATH"])
        self.assertEqual(args["size"], {"state": "known", "value": "24"})
        result, records = self.adapt(raw.replace(b'resolve=RESOLVE_BENEATH', b'resolve=RESOLVE_BENEATH, extra=7'))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(records[-1]["reason"], "unsupported_structure")


if __name__ == "__main__":
    unittest.main()
