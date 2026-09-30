"""Inspect or explicitly select from a supplied Daybreak account catalog."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from daybreak_records import dump_json

CATALOG_SCHEMA = "rolecasting-daybreak-catalog-inspection-v1"
BINDING_LINE = re.compile(r"^\s*-\s+binding:\s*(?P<value>\S.*?)\s*$")
FIELD_LINE = re.compile(r"^\s{2,}(?P<name>[a-z][a-z0-9_]*):\s*(?P<value>\S.*?)\s*$")
REQUIRED_FIELDS = {
    "codex_home",
    "authenticated_account_id",
    "account_classification",
    "authentication_observation",
    "configuration_topology",
    "database_topology",
    "usage_capacity",
    "daybreak_selector",
    "harmless_probe",
    "task_data_authority",
}


class CatalogError(ValueError):
    """A supplied catalog does not contain complete public binding blocks."""


def parse_catalog(content: str) -> list[tuple[str, str]]:
    """Parse every supported Markdown binding block in a catalog document."""
    lines = content.splitlines()
    bindings: list[tuple[str, str]] = []
    fields: dict[str, str] | None = None

    def finish_binding() -> None:
        nonlocal fields
        if fields is None:
            return
        if set(fields) != REQUIRED_FIELDS:
            missing = sorted(REQUIRED_FIELDS - set(fields))
            unknown = sorted(set(fields) - REQUIRED_FIELDS)
            detail = ""
            if missing:
                detail = "missing " + ", ".join(missing)
            if unknown:
                detail += ("; " if detail else "") + "unknown " + ", ".join(unknown)
            raise CatalogError(
                f"binding fields do not match the supported catalog: {detail}"
            )
        account_home = fields["codex_home"]
        home_relative = account_home.startswith("~/")
        relative_home = Path(account_home[2:]) if home_relative else None
        relative_parts = relative_home.parts if relative_home is not None else ()
        if not (
            Path(account_home).is_absolute()
            or (
                home_relative
                and relative_home is not None
                and not relative_home.is_absolute()
                and bool(relative_parts)
                and not {".", ".."}.intersection(relative_parts)
            )
        ):
            raise CatalogError("codex_home must be absolute or use ~/PATH syntax")
        bindings.append((account_home, fields["authenticated_account_id"]))
        fields = None

    position = 0
    while position < len(lines):
        line = lines[position]
        binding_match = BINDING_LINE.fullmatch(line)
        if binding_match is not None:
            finish_binding()
            fields = {}
            position += 1
            continue
        if fields is not None:
            field_match = FIELD_LINE.fullmatch(line)
            if field_match is not None:
                name = field_match.group("name")
                if name in fields:
                    raise CatalogError(f"duplicate binding field: {name}")
                fields[name] = field_match.group("value")
                position += 1
                continue
            if line.startswith((" ", "\t")) and line.strip():
                raise CatalogError("malformed indented binding field")
            finish_binding()
        outside_field = FIELD_LINE.fullmatch(line)
        if line.lstrip().startswith("- binding:") or (
            outside_field is not None and outside_field.group("name") in REQUIRED_FIELDS
        ):
            raise CatalogError("malformed account binding field")
        position += 1
    finish_binding()
    if not bindings:
        raise CatalogError("catalog contains no account bindings")
    return bindings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read only the explicitly supplied catalog; do not access account state "
            "or launch Codex."
        )
    )
    subparsers = parser.add_subparsers(dest="operation", required=True)
    inspect_parser = subparsers.add_parser(
        "inspect",
        description=(
            "Validate the complete supplied Markdown catalog and emit only its "
            "binding count and one-based positions."
        ),
    )
    inspect_parser.add_argument("--catalog", type=Path, required=True)
    select_parser = subparsers.add_parser(
        "select",
        description=(
            "Validate the complete supplied Markdown catalog and emit one explicit "
            "private selection without accessing account state."
        ),
    )
    select_parser.add_argument("--catalog", type=Path, required=True)
    select_parser.add_argument("--position", type=int, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        bindings = parse_catalog(arguments.catalog.read_text(encoding="utf-8"))
    except (CatalogError, OSError, UnicodeDecodeError) as error:
        print(f"daybreak_catalog: {error}", file=sys.stderr)
        return 1

    if arguments.operation == "inspect":
        result = {
            "schema": CATALOG_SCHEMA,
            "binding_count": len(bindings),
            "entries": [
                {"position": position} for position in range(1, len(bindings) + 1)
            ],
        }
        sys.stdout.write(dump_json(result))
        return 0
    if not 1 <= arguments.position <= len(bindings):
        print(
            "daybreak_catalog: position is outside the supplied catalog",
            file=sys.stderr,
        )
        return 1
    account_home, account_id = bindings[arguments.position - 1]
    sys.stdout.write(
        dump_json(
            {
                "schema": "rolecasting-daybreak-account-selection-v1",
                "account_home": account_home,
                "authenticated_account_id": account_id,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
