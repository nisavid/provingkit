"""Read the application's source records."""

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Record:
    item: str
    category: str
    units: int
    multiplier: int


def read_records(path: Path) -> list[Record]:
    records = []
    with path.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        required = {"item", "category", "units", "multiplier"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("input must contain item, category, units, and multiplier columns")
        for line, row in enumerate(reader, start=2):
            try:
                records.append(
                    Record(
                        item=row["item"],
                        category=row["category"],
                        units=int(row["units"]),
                        multiplier=int(row["multiplier"]),
                    )
                )
            except (TypeError, ValueError) as error:
                raise ValueError(f"line {line}: units and multiplier must be integers") from error
    return records
