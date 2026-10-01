import json
import re
import sys


def parse_measurements(text):
    records = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = re.fullmatch(r"([a-z]+)=([+-]?[0-9]+)", line)
        if match is None:
            raise ValueError("malformed measurement")
        records.append((match[1], int(match[2])))
    return records


if __name__ == "__main__":
    try:
        result = parse_measurements(sys.stdin.read())
    except ValueError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps(result))
