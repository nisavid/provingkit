"""Shared optional Receipt context bootstrap for standalone member validators."""

from __future__ import annotations

import argparse
from pathlib import Path


def add_context_arguments(
    parser: argparse.ArgumentParser, *, source_stage_help: str | None = None
) -> None:
    parser.add_argument("--source-stage", action="store_true", help=source_stage_help)
    parser.add_argument("--base")
    parser.add_argument("--candidate")
    parser.add_argument("--receipt-root")
    parser.add_argument("--procedure-revision")


def prepare_context_if_requested(
    parser: argparse.ArgumentParser,
    arguments: argparse.Namespace,
    repository: Path,
    *,
    writing: bool = False,
):
    """Load optional Receipt support only for an explicit context request."""
    if not any(
        value is not None
        for value in (
            arguments.base,
            arguments.candidate,
            arguments.receipt_root,
            arguments.procedure_revision,
        )
    ):
        return None
    try:
        from behavior_eval_source_stage import prepare_context
    except ImportError:
        parser.error("Receipt source-stage support is unavailable")
    return prepare_context(parser, arguments, repository, writing=writing)


def check_context_if_requested(context, member: str) -> int:
    """Emit the optional member result after its structural validation passes."""
    from behavior_eval_source_stage import check_context

    return check_context(context, member)
