#!/usr/bin/env python3
"""Validate an exact, author-supplied relation-ledger replacement in a PR body."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from change_navigation.bot_body import split_bot_tail
from change_navigation.sensitive_content import contains_suspected_secret


class LedgerValidationError(ValueError):
    """The candidate does not prove the authorized edit; messages contain no input."""


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class LedgerRequest:
    target: dict[str, Any]
    preimage: dict[str, Any]
    title: str
    body: str
    review: dict[str, Any]
    manifest_sha256: str


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise LedgerValidationError(message)


def _keys(value: Any, expected: set[str]) -> None:
    _require(isinstance(value, dict) and set(value) == expected, "manifest has unsupported fields or shape")


def _text(value: Any) -> str:
    _require(isinstance(value, str), "manifest text must be a UTF-8 string")
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise LedgerValidationError("manifest text must be a UTF-8 string") from None
    return value


def _decode(value: bytes) -> str:
    _require(isinstance(value, bytes), "candidate inputs must be literal UTF-8 bytes")
    try:
        return value.decode("utf-8")
    except UnicodeError:
        raise LedgerValidationError("candidate inputs must be literal UTF-8 bytes") from None


def validate_request(
    manifest: dict[str, Any], title_bytes: bytes, body_bytes: bytes, *,
    review_mode: str, selected_specialists: list[str],
) -> LedgerRequest:
    """Prove one half-open UTF-8 span replacement without parsing Markdown."""
    _keys(manifest, {"schema_version", "operation", "target", "preimage", "authorized_span", "candidate", "review"})
    _require(type(manifest["schema_version"]) is int and manifest["schema_version"] == 1,
             "unsupported manifest version")
    _require(manifest["operation"] == "pr-relation-ledger-write", "unsupported manifest operation")
    target, preimage = manifest["target"], manifest["preimage"]
    span, candidate, review = manifest["authorized_span"], manifest["candidate"], manifest["review"]
    _keys(target, {"host", "repository", "repository_id", "entity_id", "number"})
    _keys(preimage, {"title", "body", "state", "is_draft"})
    _keys(span, {"start_utf8", "end_utf8", "replacement"})
    _keys(candidate, {"title_sha256", "body_sha256"})
    _keys(review, {"mode", "selected_specialists"})
    _require(target["host"] == "github.com", "host is outside the qualified platform")
    repository = _text(target["repository"])
    _require(re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+", repository) is not None
             and repository.split("/")[1] not in {".", ".."}, "invalid repository identity")
    for key in ("repository_id", "entity_id"):
        _require(re.fullmatch(r"[A-Za-z0-9_=-]{1,256}", _text(target[key])) is not None,
                 "invalid stable identity")
    _require(type(target["number"]) is int and target["number"] > 0, "invalid PR number")
    _require(preimage["state"] in ("OPEN", "CLOSED", "MERGED")
             and type(preimage["is_draft"]) is bool, "invalid expected PR state")
    title, body = _decode(title_bytes), _decode(body_bytes)
    original_title, original_body = _text(preimage["title"]), _text(preimage["body"])
    replacement = _text(span["replacement"])
    _require(not any(contains_suspected_secret(text) for text in
                     (title, body, original_title, original_body, replacement)),
             "sensitive content blocks relation-ledger publication")
    _require(bool(title) and len(title) <= 256 and len(body) <= 65536, "candidate exceeds PR text limits")
    _require(title == original_title, "relation-ledger edits must preserve the title")
    original = original_body.encode("utf-8")
    start, end = span["start_utf8"], span["end_utf8"]
    _require(type(start) is int and type(end) is int and 0 <= start <= end <= len(original),
             "invalid authorized UTF-8 span")
    try:
        original[:start].decode("utf-8")
        original[end:].decode("utf-8")
    except UnicodeError:
        raise LedgerValidationError("authorized span splits a UTF-8 character") from None
    _require(body_bytes == original[:start] + replacement.encode("utf-8") + original[end:],
             "candidate changes bytes outside the authorized replacement")
    authored_prefix, bot_tail = split_bot_tail(original_body)
    _require(not bot_tail or end <= len(authored_prefix.encode("utf-8")),
             "authorized span overlaps recognized bot content")
    for key, text in (("title_sha256", title), ("body_sha256", body)):
        _require(isinstance(candidate[key], str) and candidate[key] == sha256(text),
                 "candidate digest does not match the literal input")
    _require(review_mode in ("not-required", "required"), "explicit review mode is required")
    _require(isinstance(selected_specialists, list)
             and all(isinstance(name, str) and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,99}", name)
                     for name in selected_specialists), "invalid selected specialists")
    _require(selected_specialists == sorted(set(selected_specialists)),
             "selected specialists must be sorted and unique")
    _require(review == {"mode": review_mode, "selected_specialists": selected_specialists},
             "review choice does not match the manifest")
    _require(review_mode != "not-required" or not selected_specialists,
             "not-required review cannot claim specialist reviews")
    return LedgerRequest(dict(target), dict(preimage), title, body,
                         {"mode": review_mode, "selected_specialists": list(selected_specialists)},
                         sha256(canonical_json(manifest)))


def strict_json(value: str) -> Any:
    def pairs(items):
        result = {}
        for key, item in items:
            _require(key not in result, "JSON contains duplicate fields")
            result[key] = item
        return result

    def constant(_value):
        raise LedgerValidationError("JSON contains a non-finite value")

    try:
        return json.loads(value, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, RecursionError):
        raise LedgerValidationError("invalid JSON input") from None


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--title-file", required=True, type=Path)
    parser.add_argument("--body-file", required=True, type=Path)
    parser.add_argument("--review-mode", required=True, choices=("not-required", "required"))
    parser.add_argument("--selected-specialists", required=True, help="JSON array of sorted specialist names")


def read_inputs(args: argparse.Namespace) -> tuple[dict, bytes, bytes, list[str]]:
    def read(path, maximum):
        _require(path.is_absolute(), "input file paths must be absolute")
        try:
            with path.open("rb") as stream:
                data = stream.read(maximum + 1)
        except OSError:
            raise LedgerValidationError("cannot read an input file") from None
        _require(len(data) <= maximum, "input file exceeds size limit")
        return data

    return (strict_json(_decode(read(args.manifest, 2_000_000))), read(args.title_file, 4096),
            read(args.body_file, 300_000), strict_json(args.selected_specialists))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    args = parser.parse_args(argv)
    try:
        manifest, title, body, specialists = read_inputs(args)
        request = validate_request(manifest, title, body, review_mode=args.review_mode,
                                   selected_specialists=specialists)
    except LedgerValidationError as error:
        print(canonical_json({"schema_version": 1, "operation": "pr-relation-ledger-write",
                              "status": "blocked", "reason": str(error)}))
        return 1
    print(canonical_json({"schema_version": 1, "operation": "pr-relation-ledger-write",
                          "status": "validated", **request.target,
                          "manifest_sha256": request.manifest_sha256,
                          "title_sha256": sha256(request.title), "body_sha256": sha256(request.body)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
