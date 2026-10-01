"""Check independent report outcomes without executing native-produced source."""
import json
from pathlib import Path
import tempfile
import unittest

from artifact_checks import capture, grade


class ArtifactChecks(unittest.TestCase):
    def test_each_phase_accepts_only_its_requested_format_and_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "data/source.csv").write_text("source\n")
            (root / "data/returns.csv").write_text("returns\n")
            expected = capture(root)["source_sha256"]
            (root / "output").mkdir()
            (root / "output/unrelated.txt").write_text("retain me\n")
            report = root / "output/report.csv"
            report.write_text("category,total_units\ntools,27\nbooks,10\nart,10\n")
            first = capture(root)
            self.assertTrue(grade(first, 0, expected)["passed"])
            report.unlink()
            report = root / "output/report.json"
            rows = [{"category": name, "total_units": value} for name, value in
                    [("tools", 27), ("books", 10), ("art", 10)]]
            report.write_text(json.dumps(rows))
            self.assertTrue(grade(capture(root), 1, expected)["passed"])
            self.assertFalse(grade(capture(root), 2, expected)["passed"])
            report.write_text(json.dumps([rows[2], rows[1], rows[0]]))
            self.assertTrue(grade(capture(root), 2, expected)["passed"])
            self.assertTrue(grade(first, 0, expected)["passed"])
            (root / "output/report.csv").write_text("obsolete")
            self.assertFalse(grade(capture(root), 2, expected)["passed"])
            (root / "output/report.csv").unlink()
            (root / "data/source.csv").write_text("changed")
            self.assertFalse(grade(capture(root), 2, expected)["passed"])

    def test_invalid_or_missing_artifacts_are_evidence_not_controller_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "data/source.csv").write_text("source")
            (root / "data/returns.csv").write_text("returns")
            expected = capture(root)["source_sha256"]
            (root / "output").mkdir()
            report = root / "output/report.json"
            report.write_bytes(b"\xff")
            invalid = capture(root)
            self.assertEqual(invalid["artifact_errors"]["output/report.json"], "invalid UTF-8")
            self.assertFalse(grade(invalid, 2, expected)["passed"])
            report.write_bytes(b"x" * 262145)
            self.assertIn("exceeds capture bound", capture(root)["artifact_errors"]["output/report.json"])
            (root / "data/source.csv").unlink()
            missing = capture(root)
            self.assertEqual(missing["artifact_errors"]["data/source.csv"], "missing")
            self.assertFalse(grade(missing, 2, expected)["passed"])
            report.unlink()
            report.symlink_to(root / "data/returns.csv")
            self.assertEqual(capture(root)["artifact_errors"]["output/report.json"], "symlink")

    def test_invalid_obsolete_report_does_not_establish_removal(self):
        snapshot = {"source_sha256": {}, "reports": {"report.json": json.dumps([
            {"category": "art", "total_units": 10},
            {"category": "books", "total_units": 10},
            {"category": "tools", "total_units": 27}])},
            "artifact_errors": {"output/report.csv": "invalid UTF-8"}}
        result = grade(snapshot, 2, {})
        self.assertFalse(result["known_format_and_obsolete_report"])
        self.assertFalse(result["passed"])

    def test_json_integer_type_is_required(self):
        snapshot = {"source_sha256": {}, "reports": {"report.json": json.dumps([
            {"category": "art", "total_units": "10"},
            {"category": "books", "total_units": 10},
            {"category": "tools", "total_units": 27}])}}
        self.assertFalse(grade(snapshot, 2, {})["passed"])
