"""Accepted member versions for the current source-stage Kit."""

from __future__ import annotations

import re

LOCAL_ALPHA_VERSION = re.compile(r"0\.1\.0-alpha\.[1-9][0-9]*\Z")


def is_supported_member_version(value: object) -> bool:
    """Accept an assigned pre-v1 alpha ordinal for current source."""

    return isinstance(value, str) and LOCAL_ALPHA_VERSION.fullmatch(value) is not None
