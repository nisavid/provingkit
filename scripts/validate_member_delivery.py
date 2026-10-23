#!/usr/bin/env python3
"""Report request errors and incomplete member-delivery validation."""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal, DecimalException
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from member_delivery_preservation import validate_nonpassing

class InvalidJsonConstant(ValueError):
    """A numeric token outside JSON syntax appeared in the request."""


class DuplicateJsonKey(ValueError):
    """An object contains the same decoded key more than once."""


def reject_json_constant(value: str) -> None:
    raise InvalidJsonConstant(value)


def unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonKey(key)
        result[key] = value
    return result


def decode_json(raw: bytes) -> object:
    return json.loads(raw.decode("utf-8"), parse_constant=reject_json_constant,
                      object_pairs_hook=unique_json_object, parse_float=Decimal)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    outcome = "incomplete"
    exit_status = 2

    try:
        request = decode_json(arguments.request.read_bytes())
    except OSError:
        check = {
            "id": "request",
            "outcome": "missing",
            "reason": "The request could not be opened.",
        }
    except RecursionError:
        check = {
            "id": "request_content",
            "outcome": "invalid",
            "reason": "The request exceeds the JSON parser nesting limit.",
        }
        outcome = "rejected"
        exit_status = 1
    except (
        json.JSONDecodeError,
        InvalidJsonConstant,
        DuplicateJsonKey,
        UnicodeDecodeError,
    ):
        check = {
            "id": "request_content",
            "outcome": "invalid",
            "reason": "The request must contain valid JSON.",
        }
        outcome = "rejected"
        exit_status = 1
    except (DecimalException, ValueError):
        check = {
            "id": "request_content",
            "outcome": "invalid",
            "reason": "The request exceeds the supported JSON numeric range.",
        }
        outcome = "rejected"
        exit_status = 1
    else:
        preservation = validate_nonpassing(request, arguments.inputs, decode_json)
        if preservation is not None:
            arguments.output.write_text(json.dumps(preservation, indent=2) + "\n")
            return 1 if preservation["outcome"] == "rejected" else 2
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
