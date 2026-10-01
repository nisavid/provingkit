"""Orchestrate the application's default report."""

import argparse
from pathlib import Path
import sys

from .aggregation import item_totals
from .parsing import read_records
from .rendering import write_report


APPLICATION_ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate output/report.csv from data/source.csv.")
    parser.parse_args(argv)
    try:
        records = read_records(APPLICATION_ROOT / "data" / "source.csv")
        totals = item_totals(records)
        write_report(APPLICATION_ROOT / "output" / "report.csv", totals)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"report: {error}", file=sys.stderr)
        return 1
    return 0
