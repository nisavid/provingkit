"""Accepted member versions for the current source-stage Kit."""

from __future__ import annotations

import re

TRUNK_MEMBER_VERSION = "0.1.0-trunk"
LOCAL_ALPHA_VERSION = re.compile(r"0\.1\.0-alpha\.[1-9][0-9]*\Z")


def is_supported_member_version(value: object) -> bool:
    """Accept the next-normal-release source marker or an assigned alpha cut."""

    return isinstance(value, str) and (
        value == TRUNK_MEMBER_VERSION
        or LOCAL_ALPHA_VERSION.fullmatch(value) is not None
    )
