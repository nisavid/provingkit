#!/usr/bin/env python3
"""Embed the measured comparison in one standalone, offline HTML replay."""

import json
from pathlib import Path

from fixtures import sha

root = Path(__file__).resolve().parent
raw = (root / "results.json").read_bytes()
report = json.loads(raw)
rows = []
for row in report["scenarios"]:
    rows.append({key: row[key] for key in ("name", "operation", "original_base", "evaluated_source",
                                         "target_before", "landed_commit", "observations")})
for row in report["retention"]:
    observation = row["observation"]
    rows.append({"name": row["name"], "operation": "fresh clone", "original_base": observation["base_revision"],
                 "evaluated_source": None, "target_before": None, "landed_commit": observation["candidate_revision"],
                 "observations": {"correspondence": observation},
                 "source_available": row["evaluated_source_available"]})
data = json.dumps(rows, separators=(",", ":")).replace("<", "\\u003c")
template = (root / "demo.html.in").read_text()
(root / "index.html").write_text(template.replace("__MEASURED_ROWS__", data).replace("__RESULTS_SHA256__", sha(raw)))
