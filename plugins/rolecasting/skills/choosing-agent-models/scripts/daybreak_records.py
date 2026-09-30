"""Pure record handling shared by the Daybreak command-line programs."""

from __future__ import annotations

import json

SELECTION_SCHEMA = "rolecasting-daybreak-account-selection-v1"
RATE_LIMIT_REACHED_TYPES = {
    "rate_limit_reached",
    "workspace_owner_credits_depleted",
    "workspace_member_credits_depleted",
    "workspace_owner_usage_limit_reached",
    "workspace_member_usage_limit_reached",
}


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


def load_strict_json(content: str | bytes) -> object:
    """Load one JSON value without duplicate keys or non-finite constants."""
    try:
        return json.loads(
            content,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, RecursionError) as error:
        raise RecordError("JSON input must contain exactly one valid value") from error


def load_selection(content: str) -> dict[str, str]:
    """Load the one strict selection object accepted by the account CLI."""
    try:
        value = load_strict_json(content)
    except RecordError as error:
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


def _capacity_error() -> RecordError:
    return RecordError("capacity response has an invalid type")


def _integer(value: object, *, bits: int, nullable: bool) -> int | None:
    if value is None and nullable:
        return None
    if type(value) is not int:
        raise _capacity_error()
    lower = -(2 ** (bits - 1))
    upper = 2 ** (bits - 1) - 1
    if not lower <= value <= upper:
        raise _capacity_error()
    return value


def allowlisted_window(value: object) -> dict[str, object] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or "usedPercent" not in value:
        raise _capacity_error()
    return {
        "used_percent": _integer(value["usedPercent"], bits=32, nullable=False),
        "resets_at": _integer(value.get("resetsAt"), bits=64, nullable=True),
        "window_duration_minutes": _integer(
            value.get("windowDurationMins"), bits=64, nullable=True
        ),
    }


def allowlisted_capacity(value: object) -> dict[str, object] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise _capacity_error()
    spend_control = value.get("spendControlReached")
    if spend_control is not None and type(spend_control) is not bool:
        raise _capacity_error()
    reached_type = value.get("rateLimitReachedType")
    if reached_type is not None and (
        not isinstance(reached_type, str)
        or reached_type not in RATE_LIMIT_REACHED_TYPES
    ):
        raise _capacity_error()
    return {
        "primary": allowlisted_window(value.get("primary")),
        "secondary": allowlisted_window(value.get("secondary")),
        "spend_control_reached": spend_control,
        "rate_limit_reached_type": reached_type,
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
