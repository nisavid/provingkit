#!/usr/bin/env python3
import argparse
import csv
import io
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Archive the full tab-separated inventory report")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = Path(__file__).resolve().parents[1] / "bin/inventory-report"
    result = subprocess.run([sys.executable, str(report), "--input", str(args.input)], capture_output=True, text=True)
    if result.returncode:
        sys.stderr.write(result.stderr)
        return result.returncode
    try:
        rows = list(csv.reader(io.StringIO(result.stdout), delimiter="\t", quoting=csv.QUOTE_NONE))
        if not rows or rows[0] != ["sku", "warehouse", "on_hand"]:
            raise ValueError("expected tab-separated inventory header")
        if any(len(row) != 3 for row in rows[1:]):
            raise ValueError("expected three fields per inventory record")
        archive = io.StringIO()
        csv.writer(archive, delimiter="\t", lineterminator="\n", quoting=csv.QUOTE_NONE, quotechar=None).writerows(rows)
        args.output.write_text(archive.getvalue(), encoding="utf-8")
    except (OSError, ValueError, csv.Error) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
