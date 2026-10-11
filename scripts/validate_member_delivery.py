#!/usr/bin/env python3
"""Report request errors and incomplete member-delivery validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


class InvalidJsonConstant(ValueError):
    """A numeric token outside JSON syntax appeared in the request."""


def reject_json_constant(value: str) -> None:
    raise InvalidJsonConstant(value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    outcome = "incomplete"
    exit_status = 2

    try:
        with arguments.request.open("r", encoding="utf-8") as request:
            json.load(request, parse_constant=reject_json_constant)
    except OSError:
        check = {
            "id": "request",
            "outcome": "missing",
            "reason": "The request could not be opened.",
        }
    except (json.JSONDecodeError, InvalidJsonConstant):
        check = {
            "id": "request_content",
            "outcome": "invalid",
            "reason": "The request must contain valid JSON.",
        }
        outcome = "rejected"
        exit_status = 1
    else:
        check = {
            "id": "request_validation",
            "outcome": "missing",
            "reason": "Request validation is unavailable in this revision.",
        }

    report = {
        "outcome": outcome,
        "established_claims": [],
        "checks": [check],
    }
    arguments.output.write_text(json.dumps(report, indent=2) + "\n")
    return exit_status


if __name__ == "__main__":
    raise SystemExit(main())
