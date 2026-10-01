"""Write the CSV item report."""

import csv
from collections.abc import Iterable
from pathlib import Path


def write_report(path: Path, totals: Iterable[tuple[str, int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as report:
        writer = csv.writer(report)
        writer.writerow(["item", "total_units"])
        writer.writerows(totals)
