#!/usr/bin/env python3
"""Report incomplete evidence through the member-delivery CLI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()

    try:
        with arguments.request.open("rb"):
            pass
    except OSError:
        check = {
            "id": "request",
            "outcome": "missing",
            "reason": "The request could not be opened.",
        }
    else:
        check = {
            "id": "request_validation",
            "outcome": "missing",
            "reason": "Request validation is unavailable in this revision.",
        }

    report = {
        "outcome": "incomplete",
        "established_claims": [],
        "checks": [check],
    }
    arguments.output.write_text(json.dumps(report, indent=2) + "\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
