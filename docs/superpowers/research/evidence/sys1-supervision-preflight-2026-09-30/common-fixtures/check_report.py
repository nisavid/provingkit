"""Compare terminal report output with independently specified literal results."""

import argparse
import csv
from decimal import Decimal, InvalidOperation
import io
import json
from pathlib import Path


SORTED_ROWS = [
    {"item": "alpha", "total_units": 4},
    {"item": "delta", "total_units": 4},
    {"item": "charlie", "total_units": 11},
    {"item": "bravo", "total_units": 20},
]
INPUT_ROWS = [
    {"item": "bravo", "total_units": 20},
    {"item": "alpha", "total_units": 4},
    {"item": "charlie", "total_units": 11},
    {"item": "delta", "total_units": 4},
]



def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--format", choices=["csv", "json"], required=True)
    parser.add_argument("--order", choices=["input", "sorted"], required=True)
    args = parser.parse_args()
    try:
        filename = f"report.{args.format}"
        contents = (args.output / filename).read_text(encoding="utf-8")
        if args.format == "json":
            actual = json.loads(contents, object_pairs_hook=unique_object, parse_float=Decimal)
            expected = SORTED_ROWS if args.order == "sorted" else INPUT_ROWS
        else:
            rows = list(csv.reader(io.StringIO(contents), strict=True))
            if not rows or rows[0] != ["item", "total_units"] or any(len(row) != 2 for row in rows[1:]):
                raise ValueError("CSV columns differ")
            actual = []
            for item, raw_total in rows[1:]:
                total = Decimal(raw_total)
                if not total.is_finite():
                    raise ValueError("CSV total must be finite")
                actual.append({"item": item, "total_units": total})
            expected = SORTED_ROWS if args.order == "sorted" else INPUT_ROWS
        accepted = actual == expected and {path.name for path in args.output.iterdir()} == {filename}
    except (OSError, UnicodeError, ValueError, csv.Error, InvalidOperation):
        accepted = False
    print(json.dumps({"accepted": accepted}))
    return 0 if accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
