"""Retain requested report bytes; grade independently after native execution."""

import base64
import csv
import hashlib
import io
import json
from pathlib import Path


def read_file(path):
    """Return bounded task-artifact evidence; output mistakes do not stop the run."""
    if path.is_symlink() or path.parent.is_symlink():
        return None, "symlink"
    if not path.exists():
        return None, "missing"
    if not path.is_file():
        return None, "not a regular file"
    try:
        with path.open("rb") as stream:
            data = stream.read(262145)
    except OSError as error:
        return None, "unreadable (" + type(error).__name__ + ")"
    if len(data) > 262144:
        return data[:262144], "exceeds capture bound (retained prefix only)"
    return data, None


def capture(project):
    project = Path(project)
    sources, reports, errors, raw = {}, {}, {}, {}
    for name in ("data/source.csv", "data/returns.csv", "output/report.csv", "output/report.json"):
        data, error = read_file(project / name)
        is_source = name.startswith("data/")
        if error is not None:
            # One report format being absent is expected. Both absent still fail grading.
            if is_source or error != "missing":
                errors[name] = error
                if data is not None:
                    raw[name] = base64.b64encode(data).decode("ascii")
            if is_source:
                sources[Path(name).name] = None
            continue
        if is_source:
            sources[Path(name).name] = hashlib.sha256(data).hexdigest()
        else:
            try:
                reports[Path(name).name] = data.decode("utf-8")
            except UnicodeError:
                errors[name] = "invalid UTF-8"
                raw[name] = base64.b64encode(data).decode("ascii")
    return {"schema": "sys1-report-artifacts/v1", "source_sha256": sources,
            "reports": reports, "artifact_errors": errors, "invalid_bytes_base64": raw,
            "scope": "Known report files and source data only; CLI behavior, tests, docs, and unrelated-file preservation need separate inspection."}


def grade(snapshot, phase, expected_source_sha256):
    if phase not in (0, 1, 2):
        raise ValueError("unknown report phase")
    expected = [("tools", 27), ("books", 10), ("art", 10)] if phase < 2 else [
        ("art", 10), ("books", 10), ("tools", 27)]
    reports = snapshot["reports"]
    right_format = (set(reports) == ({"report.csv"} if phase == 0 else {"report.json"})
                    and not any(name.startswith("output/")
                                for name in snapshot.get("artifact_errors", {})))
    outcome = False
    try:
        if right_format and phase == 0:
            rows = list(csv.reader(io.StringIO(reports["report.csv"])))
            outcome = (bool(rows) and rows[0] == ["category", "total_units"]
                       and all(len(row) == 2 for row in rows[1:])
                       and [(row[0], int(row[1])) for row in rows[1:]] == expected)
        elif right_format:
            rows = json.loads(reports["report.json"])
            outcome = (isinstance(rows, list) and
                       all(isinstance(row, dict) and set(row) == {"category", "total_units"}
                           and type(row["total_units"]) is int for row in rows) and
                       rows == [{"category": name, "total_units": total} for name, total in expected])
    except (ValueError, TypeError, csv.Error):
        pass
    sources = snapshot["source_sha256"] == expected_source_sha256
    return {"phase": phase, "known_format_and_obsolete_report": right_format,
            "literal_result": outcome, "source_data_unchanged": sources,
            "artifact_errors": snapshot.get("artifact_errors", {}),
            "passed": right_format and outcome and sources and not snapshot.get("artifact_errors")}
