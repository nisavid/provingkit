"""Accepted member versions for the current source-stage Kit."""

from __future__ import annotations

import re

CUTOVER_MEMBER_VERSION = "1.0.0"
LOCAL_ALPHA_VERSION = re.compile(r"0\.1\.0-alpha\.[1-9][0-9]*\Z")


def is_supported_member_version(value: object) -> bool:
    """Accept the cutover source state or an assigned local alpha ordinal."""

    return isinstance(value, str) and (
        value == CUTOVER_MEMBER_VERSION
        or LOCAL_ALPHA_VERSION.fullmatch(value) is not None
    )
