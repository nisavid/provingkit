"""Preserve recognized bot-owned pull-request body suffixes."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterator


# These markers are emitted as complete trailing blocks by the hosted review
# integrations. Keep the match deliberately narrow so authored HTML comments
# or ordinary prose cannot silently become bot-owned.
_BOT_TAIL_START = re.compile(
    r"(?:\A|(?<=[\r\n]))<!--[ \t]*(?P<marker>"
    r"This is an auto-generated comment:[ \t]*(?P<name>[^>\r\n]+?)"
    r"|review_stack_entry_start"
    r"|tips_start"
    r"|walkthrough_start"
    r"|final_review_risk_start"
    r"|pre_merge_checks_walkthrough_start"
    r"|poem_footer_start"
    r")[ \t]*-->[ \t]*(?=[\r\n]|\Z)"
)
_TRUSTED_DYNAMIC_NAMES = {
    "release notes by coderabbit.ai",
    "review in progress by coderabbit.ai",
    "summarize by coderabbit.ai",
}
_FIXED_END_MARKERS = {
    "review_stack_entry_start": "<!-- review_stack_entry_end -->",
    "tips_start": "<!-- tips_end -->",
    "walkthrough_start": "<!-- walkthrough_end -->",
    "final_review_risk_start": "<!-- final_review_risk_end -->",
    "pre_merge_checks_walkthrough_start": ("<!-- pre_merge_checks_walkthrough_end -->"),
    "poem_footer_start": "<!-- poem_footer_end -->",
}


def _end_marker(match: re.Match[str]) -> str:
    name = match.group("name")
    if name is not None:
        return f"<!-- end of auto-generated comment: {name.strip()} -->"
    return _FIXED_END_MARKERS[match.group("marker").strip()]


def _trusted_dynamic_marker(match: re.Match[str]) -> bool:
    name = match.group("name")
    return name is None or name.strip() in _TRUSTED_DYNAMIC_NAMES


class BotBodyError(ValueError):
    """The observed body cannot reproduce the sealed authored prefix."""


def _trim_separator(body: str, prefix_end: int) -> int:
    while body[:prefix_end].endswith("\r\n\r\n"):
        prefix_end -= 2
    while body[:prefix_end].endswith("\n\n"):
        prefix_end -= 1
    while body[:prefix_end].endswith("\r\r"):
        prefix_end -= 1
    return prefix_end


def _tail_starts(body: str) -> Iterator[int]:
    # The first full-line closer ends its block. Never pair an opener with a
    # later block's closer across intervening authored content.
    valid_starts: set[int] = set()
    following_openers: dict[str, int] = {}
    for first in reversed(list(_BOT_TAIL_START.finditer(body))):
        if not _trusted_dynamic_marker(first):
            continue
        end_marker = _end_marker(first)
        following_opener = following_openers.get(end_marker)
        following_openers[end_marker] = first.start()
        closers = re.compile(
            r"(?:\A|(?<=[\r\n]))"
            + re.escape(end_marker)
            + r"[ \t]*(?=[\r\n]|\Z)"
        )
        closer = closers.search(body, first.end())
        if closer is None or (
            following_opener is not None and following_opener < closer.start()
        ):
            continue
        next_start = closer.end()
        while body[next_start : next_start + 1] in {"\r", "\n"}:
            next_start += 1
        if next_start == len(body) or next_start in valid_starts:
            valid_starts.add(first.start())
    yield from sorted(valid_starts)


def split_bot_tail(body: str, *, expected_sha256: str | None = None) -> tuple[str, str]:
    """Resolve a bot boundary using a sealed authored digest when available.

    A marker cannot reveal which preceding newlines belonged to the author.
    Only the sealed digest selects that boundary for publication or audit. The
    unsealed form is for initial discovery, before an author seals a baseline.
    """

    def matches(prefix: str) -> bool:
        return hashlib.sha256(prefix.encode("utf-8")).hexdigest() == expected_sha256

    if expected_sha256 is not None and matches(body):
        return body, ""
    for start in _tail_starts(body):
        if expected_sha256 is None:
            prefix_end = _trim_separator(body, start)
            return body[:prefix_end], body[prefix_end:]
        prefix_end = start
        while True:
            if matches(body[:prefix_end]):
                return body[:prefix_end], body[prefix_end:]
            if prefix_end == 0 or body[prefix_end - 1] not in "\r\n":
                break
            prefix_end -= 1
    if expected_sha256 is not None:
        raise BotBodyError("authored PR body differs from its sealed digest")
    return body, ""


def authored_body(body: str, *, expected_sha256: str | None = None) -> str:
    """Return the body bytes owned by the PR author."""

    return split_bot_tail(body, expected_sha256=expected_sha256)[0]


def merge_bot_tail(
    authored: str, live: str, *, expected_live_sha256: str | None = None
) -> str:
    """Apply authored bytes while retaining the latest live bot suffix."""

    authored_prefix = (
        authored if expected_live_sha256 is not None else authored_body(authored)
    )
    _, live_tail = split_bot_tail(live, expected_sha256=expected_live_sha256)
    if live_tail:
        trailing = authored_prefix[len(authored_prefix.rstrip("\r\n")) :]
        leading = live_tail[: len(live_tail) - len(live_tail.lstrip("\r\n"))]
        line_breaks = len(re.findall(r"\r\n|\r|\n", trailing + leading))
        separator = "\n" * max(0, 2 - line_breaks) if authored_prefix else ""
        return authored_prefix + separator + live_tail
    return authored_prefix
