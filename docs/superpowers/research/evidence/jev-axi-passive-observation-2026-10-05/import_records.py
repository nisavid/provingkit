"""Import explicitly selected local evidence; never launch or steer a task."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import time

MAX_MANIFEST = 1024 * 1024
MAX_BYTES = 8 * 1024 * 1024
MAX_SOURCES = 128
MAX_RECORDS = 10000


def read_selection(path):
    if not path.is_file():
        raise ValueError("manifest must be a regular file")
    with path.open("rb") as stream:
        raw = stream.read(MAX_MANIFEST + 1)
    if len(raw) > MAX_MANIFEST:
        raise ValueError("manifest exceeds 1 MiB")
    manifest = json.loads(raw)
    if not isinstance(manifest, dict) or type(manifest.get("version")) is not int or manifest["version"] != 1:
        raise ValueError("version must be 1")
    for name in ("episode", "purpose"):
        if not isinstance(manifest.get(name), str) or not manifest[name].strip():
            raise ValueError(f"{name} must be a nonempty string")
    sources = manifest.get("sources")
    if not isinstance(sources, list) or not 1 <= len(sources) <= MAX_SOURCES:
        raise ValueError("select 1 through 128 sources")
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("source must be an object")
        for name in ("label", "path"):
            if not isinstance(source.get(name), str) or not source[name].strip():
                raise ValueError(f"source {name} must be a nonempty string")
        for name in ("start", "length"):
            if type(source.get(name)) is not int or source[name] < 0:
                raise ValueError(f"source {name} must be a nonnegative integer")
        if source.get("format") not in ("bytes", "jsonl"):
            raise ValueError("source format must be bytes or jsonl")
        if not isinstance(source.get("sha256"), str) or not re.fullmatch("[0-9a-f]{64}", source["sha256"]):
            raise ValueError("source sha256 must be a lowercase SHA-256 digest")
    if sum(s["length"] for s in sources) > MAX_BYTES:
        raise ValueError("selected spans exceed 8 MiB")
    return raw, manifest


def main():
    started = time.perf_counter()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        raw, manifest = read_selection(args.manifest)
    except (OSError, ValueError, RecursionError) as error:
        print(f"invalid selection: {error}", file=sys.stderr)
        return 1
    try:
        args.output.mkdir()
    except OSError as error:
        print(f"cannot create new result: {error}", file=sys.stderr)
        return 1
    imports = []
    index = []
    seen = {}
    partial = False
    receipt = {"status": "incomplete", "imports": imports,
               "episode": manifest["episode"], "work_scope": "import only",
               "index_limit_reached": False,
               "selection_sha256": hashlib.sha256(raw).hexdigest()}
    try:
        (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        (args.output / "selection.json").write_bytes(raw)
        for number, source in enumerate(manifest["sources"]):
            source_path = Path(source["path"])
            if not source_path.is_absolute():
                source_path = args.manifest.parent / source_path
            if not source_path.is_file():
                raise ValueError("selected source is missing or is not a regular file")
            with source_path.open("rb") as stream:
                stream.seek(source["start"])
                data = stream.read(source["length"])
            if len(data) != source["length"]:
                raise ValueError("selected span is missing bytes")
            digest = hashlib.sha256(data).hexdigest()
            if digest != source["sha256"]:
                raise ValueError("selected span digest changed")
            filename = f"{number:04d}.source"
            (args.output / filename).write_bytes(data)
            imports.append({"label": source["label"], "file": filename,
                            "sha256": digest, "bytes": len(data)})
            if source["format"] == "jsonl":
                offset = source["start"]
                for line in io.BytesIO(data):
                    if len(index) == MAX_RECORDS:
                        receipt["index_limit_reached"] = True
                        partial = True
                        break
                    line_digest = hashlib.sha256(line).hexdigest()
                    row = {"file": filename, "start": offset, "bytes": len(line),
                           "keys": None, "parse_status": "parsed",
                           "sha256": line_digest,
                           "duplicate_of": seen.get(line_digest)}
                    if not line.endswith(b"\n"):
                        row["parse_status"] = "unterminated"
                    else:
                        try:
                            value = json.loads(line)
                            row["keys"] = sorted(value) if isinstance(value, dict) else None
                        except (ValueError, UnicodeError, RecursionError):
                            row["parse_status"] = "malformed"
                    partial |= row["parse_status"] != "parsed"
                    seen.setdefault(line_digest, len(index))
                    index.append(row)
                    offset += len(line)
        (args.output / "index.json").write_text(json.dumps(index, indent=2) + "\n")
        receipt["status"] = "partial" if partial else "complete"
    except (OSError, ValueError, OverflowError) as error:
        receipt["error"] = str(error)
    receipt["elapsed_seconds"] = time.perf_counter() - started
    try:
        (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    except OSError as error:
        print(f"cannot finish result: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"status": receipt["status"], "imports": len(imports)}))
    return {"complete": 0, "incomplete": 1, "partial": 2}[receipt["status"]]


if __name__ == "__main__":
    sys.exit(main())
