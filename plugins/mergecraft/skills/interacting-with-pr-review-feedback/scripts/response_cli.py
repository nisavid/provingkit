#!/usr/bin/env python3
"""Public CLI for strict acquisition and one-intent Mergecraft responses."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from github_response_provider import (
    GhJsonTransport,
    InlineReplyAdapter,
    PullRequestConversationAdapter,
    TypedEpochAdapter,
)
from response_runtime import ResponseRuntime


def _json_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain one JSON object")
    return value


def _transport(value: str | None) -> GhJsonTransport:
    if value is None:
        return GhJsonTransport()
    argv = json.loads(value)
    if not isinstance(argv, list) or not all(isinstance(item, str) for item in argv):
        raise ValueError("--gh-command-json must be a JSON string array")
    return GhJsonTransport(argv)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gh-command-json",
        help='Explicit gh-compatible argv prefix; defaults to ["gh"]',
    )
    commands = parser.add_subparsers(dest="command", required=True)
    acquire = commands.add_parser("acquire")
    acquire.add_argument("--repo", required=True)
    acquire.add_argument("--pr", required=True, type=int)
    invoke = commands.add_parser("invoke")
    invoke.add_argument("--state-dir", required=True, type=Path)
    invoke.add_argument("--intent", required=True, type=Path)
    invoke.add_argument("--body-file", required=True, type=Path)
    reconcile = commands.add_parser("reconcile")
    reconcile.add_argument("--state-dir", required=True, type=Path)
    reconcile.add_argument("--intent-key", required=True)
    prepare_replacement = commands.add_parser("prepare-replacement")
    prepare_replacement.add_argument("--state-dir", required=True, type=Path)
    prepare_replacement.add_argument("--intent-key", required=True)
    prepare_replacement.add_argument(
        "--repo", help="fresh current owner/name repository locator"
    )
    outcomes = commands.add_parser("outcomes")
    outcomes.add_argument("--state-dir", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        transport = _transport(args.gh_command_json)
        epoch_adapter = TypedEpochAdapter(transport)
        if args.command == "acquire":
            result = epoch_adapter.acquire(args.repo, args.pr)
        else:
            runtime = ResponseRuntime(
                state_directory=args.state_dir,
                epoch_adapter=epoch_adapter,
                inline_adapter=InlineReplyAdapter(transport),
                conversation_adapter=PullRequestConversationAdapter(transport),
            )
            if args.command == "invoke":
                result = runtime.invoke(
                    _json_object(args.intent), args.body_file.read_bytes()
                )
            elif args.command == "reconcile":
                result = runtime.reconcile(args.intent_key)
            elif args.command == "prepare-replacement":
                result = runtime.prepare_replacement(args.intent_key, args.repo)
            else:
                result = runtime.read_outcomes()
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as error:
        print(f"response runtime: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
