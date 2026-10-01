"""Reference generator for fixture checks; keep outside evaluated workspaces."""

import argparse
import csv
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=["csv", "json"], required=True)
    parser.add_argument("--order", choices=["input", "sorted"], required=True)
    args = parser.parse_args()
    with Path("data/source.csv").open(newline="", encoding="utf-8") as stream:
        rows = [{"item": row["item"], "total_units": int(row["units"]) * int(row["multiplier"])} for row in csv.DictReader(stream)]
    if args.order == "sorted":
        rows.sort(key=lambda row: (row["total_units"], row["item"]))
    output = Path("output")
    output.mkdir(exist_ok=True)
    target = output / f"report.{args.format}"
    obsolete = output / ("report.json" if args.format == "csv" else "report.csv")
    obsolete.unlink(missing_ok=True)
    if args.format == "json":
        target.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    else:
        with target.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=["item", "total_units"])
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    main()
