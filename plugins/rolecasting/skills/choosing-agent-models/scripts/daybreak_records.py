"""Pure record handling shared by the Daybreak command-line programs."""

from __future__ import annotations

import json

SELECTION_SCHEMA = "rolecasting-daybreak-account-selection-v1"


class RecordError(ValueError):
    """A public Daybreak record is malformed."""


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise RecordError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise RecordError(f"non-finite JSON value: {value}")


def load_selection(content: str) -> dict[str, str]:
    """Load the one strict selection object accepted by the account CLI."""
    try:
        value = json.loads(
            content,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as error:
        raise RecordError("selection must be exactly one JSON value") from error
    required = {"schema", "account_home", "authenticated_account_id"}
    if not isinstance(value, dict) or set(value) != required:
        raise RecordError("selection fields do not match the v1 contract")
    if value["schema"] != SELECTION_SCHEMA:
        raise RecordError("selection schema is unsupported")
    for field in ("account_home", "authenticated_account_id"):
        if not isinstance(value[field], str) or not value[field]:
            raise RecordError(f"selection {field} must be a nonempty string")
    return value


def split_selector(selector: str) -> tuple[str, str]:
    model, separator, effort = selector.rpartition("/")
    if (
        not separator
        or not model
        or not effort
        or any(character.isspace() for character in selector)
    ):
        raise RecordError("model must be an exact MODEL/EFFORT selector")
    return model, effort


def allowlisted_window(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    fields = {
        "used_percent": value.get("usedPercent"),
        "resets_at": value.get("resetsAt"),
        "window_duration_minutes": value.get("windowDurationMins"),
    }
    return fields


def allowlisted_capacity(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return {
        "primary": allowlisted_window(value.get("primary")),
        "secondary": allowlisted_window(value.get("secondary")),
        "spend_control_reached": value.get("spendControlReached"),
        "rate_limit_reached_type": value.get("rateLimitReachedType"),
    }


def dump_json(value: object) -> str:
    """Return one deterministic JSON document terminated by a newline."""
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    )
