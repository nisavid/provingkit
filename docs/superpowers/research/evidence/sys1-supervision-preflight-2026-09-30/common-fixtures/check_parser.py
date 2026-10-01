"""Check a parser's CLI against literal examples without importing its source."""

import argparse
import json
from pathlib import Path
import subprocess
import sys


CASES = [
    ("ordinary", "zulu=7\nalpha=3", [["zulu", 7], ["alpha", 3]]),
    ("signed", "beta=-2", [["beta", -2]]),
    ("blank", "alpha=3\n\n \n", [["alpha", 3]]),
    ("combined", "\n beta=-2 \n\nalpha=3\n", [["beta", -2], ["alpha", 3]]),
    ("repeated", "alpha=3\nalpha=4", [["alpha", 3], ["alpha", 4]]),
    ("empty", "", []),
    ("malformed-value", "alpha=three", None),
    ("malformed-name", "=2", None),
    ("malformed-delimiter", "alpha=2=3", None),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("program", type=Path)
    args = parser.parse_args()
    program = args.program.resolve(strict=True)
    failed = []
    for name, text, expected in CASES:
        try:
            result = subprocess.run(
                [sys.executable, "-I", str(program)],
                cwd=program.parent, input=text, capture_output=True,
                text=True, timeout=1,
            )
            if expected is None:
                passed = result.returncode == 1 and not result.stdout and result.stderr == "malformed measurement\n"
            else:
                passed = result.returncode == 0 and not result.stderr and json.loads(result.stdout) == expected
        except (OSError, ValueError, subprocess.TimeoutExpired):
            passed = False
        if not passed:
            failed.append(name)
    print(json.dumps({"accepted": not failed, "failed": failed}))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
