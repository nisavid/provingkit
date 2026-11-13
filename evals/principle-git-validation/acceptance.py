"""Assess the first synthetic completion-claim acceptance slice."""

from collections.abc import Mapping
from typing import Any


def assess_completion(record: Mapping[str, Any]) -> dict[str, Any]:
    """Reject claimed completion when an attempted required check has no result.

    Other valid records remain undetermined in this first offline slice.
    Supplied records are observations, not authenticated execution evidence.
    """
    outcomes = []
    reasons = []
    if record["handback"]["completion_claimed"] is True:
        attempts = record["observations"]["attempts"]
        results = record["observations"]["results"]
        for check in record["contract"]["checks"]:
            if check["required"] is not True or check["applicability"] != "applicable":
                continue
            attempt_ids = {
                attempt["attempt_id"]
                for attempt in attempts
                if attempt["check_id"] == check["check_id"]
            }
            if attempt_ids and not any(
                result["attempt_id"] in attempt_ids for result in results
            ):
                outcomes.append({"check_id": check["check_id"], "state": "missing"})
                reasons.append(
                    {"check_id": check["check_id"], "code": "required_check_missing_result"}
                )
    return {
        "completion": "unsupported" if reasons else "undetermined",
        "check_outcomes": outcomes,
        "reasons": reasons,
    }
