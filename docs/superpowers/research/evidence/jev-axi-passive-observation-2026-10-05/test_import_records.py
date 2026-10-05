"""Exercise the importer only through its CLI and evidence package."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CLI = Path(__file__).with_name("import_records.py")

class ImportRecordsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = self.root / "selection.json"
        self.output = self.root / "evidence"

    def source(self, name, data, start=0, length=None, format="bytes"):
        path = self.root / name
        path.write_bytes(data)
        selected = data[start:] if length is None else data[start:start + length]
        return {"label": name, "path": str(path), "start": start,
                "length": len(selected), "sha256": hashlib.sha256(selected).hexdigest(),
                "format": format}

    def run_import(self, sources, **extra):
        self.manifest.write_text(json.dumps({"version": 1, "episode": "synthetic checking",
            "purpose": "import explicit evidence", "sources": sources, **extra}))
        return subprocess.run([sys.executable, str(CLI), str(self.manifest), str(self.output)],
                              capture_output=True, text=True, timeout=5)

    def receipt(self):
        return json.loads((self.output / "receipt.json").read_text())

    def test_preserves_selected_bytes_in_declared_order(self):
        first = self.source("later.txt", b"skip\nchosen\nrest", 5, 7)
        second = self.source("earlier.txt", b"first")
        result = self.run_import([first, second])
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = self.receipt()
        self.assertEqual(receipt["status"], "complete")
        self.assertEqual([i["label"] for i in receipt["imports"]], ["later.txt", "earlier.txt"])
        self.assertEqual([(self.output / i["file"]).read_bytes() for i in receipt["imports"]],
                         [b"chosen\n", b"first"])
        self.assertEqual((self.output / "selection.json").read_bytes(), self.manifest.read_bytes())
        self.assertEqual((self.root / "later.txt").read_bytes(), b"skip\nchosen\nrest")

    def test_changed_source_is_refused_and_attempt_is_retained(self):
        source = self.source("changed.txt", b"original")
        (self.root / "changed.txt").write_bytes(b"amended!")
        result = self.run_import([source])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.receipt()["status"], "incomplete")
        self.assertIn("digest", self.receipt()["error"])
        self.assertEqual(self.receipt()["imports"], [])
        self.assertEqual((self.output / "selection.json").read_bytes(), self.manifest.read_bytes())

    def test_partial_and_malformed_records_remain_inspectable(self):
        raw = b'{"type":"event","unknown":{"value":7}}\nnot json\n{"unfinished":'
        result = self.run_import([self.source("events.jsonl", raw, format="jsonl")])
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(self.receipt()["status"], "partial")
        self.assertEqual((self.output / "0000.source").read_bytes(), raw)
        index = json.loads((self.output / "index.json").read_text())
        self.assertEqual([r["parse_status"] for r in index],
                         ["parsed", "malformed", "unterminated"])
        self.assertEqual(index[0]["keys"], ["type", "unknown"])
        self.assertEqual(index[0]["start"], 0)
        self.assertIsNone(index[1]["keys"])
        self.assertIsNone(index[2]["keys"])

    def test_duplicate_occurrences_and_separate_spans_keep_their_positions(self):
        raw = b'{"type":"check"}\n{"type":"report"}\n'
        check = self.source("trace.jsonl", raw, 0, 17, "jsonl")
        report = dict(check, start=17, length=18,
                      sha256=hashlib.sha256(b'{"type":"report"}\n').hexdigest())
        result = self.run_import([report, check, check])
        self.assertEqual(result.returncode, 0, result.stderr)
        index = json.loads((self.output / "index.json").read_text())
        self.assertEqual([r["start"] for r in index], [17, 0, 0])
        self.assertEqual([r["duplicate_of"] for r in index], [None, None, 1])
        self.assertEqual([r["file"] for r in index],
                         ["0000.source", "0001.source", "0002.source"])
        self.assertEqual(len(self.receipt()["imports"]), 3)

    def test_existing_result_is_refused_without_changing_any_bytes(self):
        source = self.source("original.txt", b"first result")
        self.assertEqual(self.run_import([source]).returncode, 0)
        before = {f.name: f.read_bytes() for f in self.output.iterdir()}
        result = self.run_import([self.source("new.txt", b"different")])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual({f.name: f.read_bytes() for f in self.output.iterdir()}, before)

    def test_missing_source_retains_prior_imports_without_claiming_completion(self):
        first = self.source("present.txt", b"known")
        missing = self.source("missing.txt", b"gone")
        (self.root / "missing.txt").unlink()
        result = self.run_import([first, missing])
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.receipt()["status"], "incomplete")
        self.assertEqual(len(self.receipt()["imports"]), 1)
        self.assertEqual((self.output / "0000.source").read_bytes(), b"known")
        before = (self.output / "receipt.json").read_bytes()
        self.assertNotEqual(self.run_import([first]).returncode, 0)
        self.assertEqual((self.output / "receipt.json").read_bytes(), before)

    def test_invalid_or_excessive_selection_is_rejected_before_creating_result(self):
        source = self.source("bounded.txt", b"small")
        for change in ({"length": -1}, {"start": True}, {"length": 8388609},
                       {"format": "automatic"}, {"sha256": "not a digest"}):
            with self.subTest(change=change):
                result = self.run_import([dict(source, **change)])
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertFalse(self.output.exists())
                self.assertIn("invalid selection", result.stderr)

    def test_unknown_and_estimated_costs_are_preserved_without_inferred_totals(self):
        costs = {"operator_seconds": None, "selection_seconds": 12,
                 "selection_kind": "estimate", "quota": "unknown"}
        result = self.run_import([self.source("note.txt", b"selected")], costs=costs)
        self.assertEqual(result.returncode, 0, result.stderr)
        copied = json.loads((self.output / "selection.json").read_text())
        self.assertEqual(copied["costs"], costs)
        receipt = self.receipt()
        self.assertEqual(receipt["work_scope"], "import only")
        self.assertGreaterEqual(receipt["elapsed_seconds"], 0)
        self.assertNotIn("task_cost", receipt)
        self.assertEqual(receipt["selection_sha256"], hashlib.sha256(self.manifest.read_bytes()).hexdigest())

    def test_index_limit_preserves_source_and_marks_partial_index(self):
        raw = b'{}\n' * 10001
        result = self.run_import([self.source("many.jsonl", raw, format="jsonl")])
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual((self.output / "0000.source").read_bytes(), raw)
        self.assertTrue(self.receipt()["index_limit_reached"])
        self.assertEqual(len(json.loads((self.output / "index.json").read_text())), 10000)

    def test_jsonl_records_are_delimited_only_by_line_feed(self):
        raw = b'{"value":\r7}\n'
        result = self.run_import([self.source("newline.jsonl", raw, format="jsonl")])
        self.assertEqual(result.returncode, 0, result.stderr)
        index = json.loads((self.output / "index.json").read_text())
        self.assertEqual(len(index), 1)
        self.assertEqual(index[0]["keys"], ["value"])
        self.assertEqual(index[0]["bytes"], 13)

    def test_deep_manifest_is_rejected_without_creating_result(self):
        self.manifest.write_text('{"extra":' + '[' * 2000 + '0' + ']' * 2000 + '}')
        result = subprocess.run([sys.executable, str(CLI), str(self.manifest), str(self.output)],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid selection", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse(self.output.exists())

if __name__ == "__main__":
    unittest.main()
