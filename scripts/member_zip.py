#!/usr/bin/env python3
"""Derive and verify member ZIPs from frozen complete-slate snapshot evidence.

Success establishes local derivative integrity, not issuance authenticity or exposure.
"""

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
from contextlib import contextmanager
import stat
import re
import sys
import tarfile
import zipfile
import zlib


EPOCH = (1980, 1, 1, 0, 0, 0)
SLATE = {"rolecasting", "tricritical", "versionkeeping", "mergecraft",
         "artifact-customs", "proseweaving", "surreal-intercom"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def safe_relative(name):
    return (isinstance(name, str) and bool(name) and not any(c in name for c in ("\\", ":", "\0"))
            and all(component not in ("", ".", "..") for component in name.split("/")))


def decode(raw, label):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def nonfinite(value):
        raise ValueError(f"non-finite JSON number: {value}")

    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)
    except (ValueError, UnicodeError) as error:
        raise ValueError(f"{label}: {error}") from error


def check_output_directory(descriptor, *, immediate):
    metadata = os.fstat(descriptor)
    if immediate:
        if metadata.st_uid != os.geteuid() or metadata.st_mode & 0o077:
            raise ValueError("output parent must be owned by the current user and private to that user")
    elif metadata.st_mode & 0o022 and not metadata.st_mode & stat.S_ISVTX:
        raise ValueError("output ancestor must exclude non-sticky shared writes")


@contextmanager
def parent_descriptor(path, *, for_output=False):
    """Walk actual directories without link hops; never extract archive paths."""
    if (not all(hasattr(os, name) for name in ("O_NOFOLLOW", "O_DIRECTORY", "O_NONBLOCK"))
            or os.open not in os.supports_dir_fd or os.mkdir not in os.supports_dir_fd):
        raise ValueError("no-follow descriptor-relative filesystem operations are required")
    path = Path(path).absolute()
    directory_flags = getattr(os, "O_PATH", os.O_RDONLY) | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open(path.anchor, directory_flags)
    try:
        components = path.parts[1:-1]
        if for_output:
            check_output_directory(descriptor, immediate=not components)
        for index, component in enumerate(components):
            following = os.open(component, directory_flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = following
            if for_output:
                check_output_directory(descriptor, immediate=index == len(components) - 1)
        yield descriptor, path.name
    finally:
        os.close(descriptor)


def regular_bytes(path):
    with parent_descriptor(path) as (parent, name):
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(descriptor, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError("input evidence must be a regular file")
            return stream.read()


def write_fresh(output, files):
    with parent_descriptor(output, for_output=True) as (parent, name):
        os.mkdir(name, 0o700, dir_fd=parent)
        directory = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        try:
            for filename, data in files.items():
                descriptor = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                     0o600, dir_fd=directory)
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(data)
        finally:
            os.close(directory)


def output_inventory(output):
    with parent_descriptor(Path(output) / "unused", for_output=True) as (parent, _):
        directory = os.open(".", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        try:
            return set(os.listdir(directory))
        finally:
            os.close(directory)


def check_request(request):
    if (not isinstance(request, dict)
            or set(request) != {"schema", "target", "member", "identity", "parent", "issuer_result"}
            or request["schema"] != "provingkit-member-zip-request-v1"
            or request["target"] not in ("agent-plugins", "claude")
            or not safe_relative(request["member"]) or "/" in request["member"]
            or request["member"] not in SLATE):
        raise ValueError("request fields, schema, target, or member are unsupported")
    identity = request["identity"]
    fields = {"source_commit", "projector_revision", "version", "request_id", "preparation_sha256",
              "policy_sha256", "plugin_slate", "issuer_request_id"}
    if (not isinstance(identity, dict) or set(identity) != fields
            or not all(isinstance(identity[key], str) for key in fields - {"plugin_slate"})):
        raise ValueError("request identity fields or types differ")
    for key, length in (("source_commit", 40), ("projector_revision", 40),
                        ("preparation_sha256", 64), ("policy_sha256", 64)):
        if re.fullmatch(r"[0-9a-f]{" + str(length) + "}", identity[key]) is None:
            raise ValueError(f"request identity requires a full lowercase {key}")
    number = r"(?:0|[1-9][0-9]*)"
    normal = number + r"\." + number + r"\." + number
    if (re.fullmatch(normal + r"-(?:0|(?:alpha|beta|rc)\.[1-9][0-9]*)\.snapshot\.[1-9][0-9]*",
                     identity["version"]) is None
            or any(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", identity[key]) is None
                   for key in ("request_id", "issuer_request_id"))):
        raise ValueError("request snapshot version or issuer request identifier is unsupported")
    slate = identity["plugin_slate"]
    if (not isinstance(slate, list) or not all(isinstance(member, str) for member in slate)
            or len(slate) != len(SLATE) or set(slate) != SLATE):
        raise ValueError("request requires the complete unique seven-member slate")
    parent = request["parent"]
    if not isinstance(parent, dict) or set(parent) != {"archive", "receipt", "modes"}:
        raise ValueError("request requires the three original parent evidence files")
    for label, row in {**parent, "issuer_result": request["issuer_result"]}.items():
        if (not isinstance(row, dict) or set(row) != {"path", "sha256"}
                or not isinstance(row["path"], str) or not row["path"] or "\0" in row["path"]
                or not isinstance(row["sha256"], str)
                or re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is None):
            raise ValueError(f"request parent path or digest is invalid: {label}")


def check_issuer_result(request, raw):
    evidence = request["issuer_result"]
    issuer_raw = regular_bytes(evidence["path"])
    if sha(issuer_raw) != evidence["sha256"]:
        raise ValueError("issuer result digest differs")
    issuer = decode(issuer_raw, "issuer result")
    identity = request["identity"]
    if (not isinstance(issuer, dict) or issuer.get("operation") not in ("issue", "add-variants")
            or issuer.get("request_id") != identity["issuer_request_id"]
            or issuer.get("version") != identity["version"]
            or issuer.get("source_commit") != identity["source_commit"]
            or issuer.get("exposure") not in ("pending", "verified", "cancelled")
            or not isinstance(issuer.get("publication"), dict)
            or not isinstance(issuer.get("variants"), dict)):
        raise ValueError("issuer result identity differs from the selected snapshot")
    same_request = issuer["request_id"] == identity["request_id"]
    if (issuer["operation"] == "issue") != same_request:
        raise ValueError("issuer result request pairing differs from its operation and preparation")
    variant = issuer["variants"].get(request["target"])
    names = {"archive": "artifact.tar.gz", "receipt": "RECEIPT.json", "modes": "modes.tsv"}
    expected = {filename: {"bytes": len(raw[label]), "sha256": sha(raw[label])}
                for label, filename in names.items()}
    if (not isinstance(variant, dict) or variant != expected
            or not all(isinstance(row, dict) and type(row.get("bytes")) is int for row in variant.values())):
        raise ValueError("issuer result variant differs from the three original parent files")
    return issuer_raw


def check_files(raw, entries):
    if ("RECEIPT.json" not in entries or entries["RECEIPT.json"][2] != "file"
            or entries["RECEIPT.json"][1] != raw["receipt"]):
        raise ValueError("parent original receipt bytes differ")
    receipt = decode(raw["receipt"], "parent receipt")
    inventory = receipt.get("files") if isinstance(receipt, dict) else None
    if not isinstance(inventory, list):
        raise ValueError("parent receipt inventory is not a list")
    framed = bytearray(b"provingkit-tree-v1\0")
    expected_inventory = []
    modes = {}
    for name in sorted(entries, key=PurePosixPath):
        mode, data, kind = entries[name]
        if kind != "file" or name == "RECEIPT.json":
            continue
        name_bytes = name.encode()
        framed.extend(len(name_bytes).to_bytes(8, "big") + name_bytes)
        framed.extend(len(data).to_bytes(8, "big") + data)
        expected_inventory.append({"path": name, "sha256": sha(data)})
        modes[name] = stat.S_IMODE(mode)
    if inventory != expected_inventory or receipt.get("artifact_sha256") != sha(framed):
        raise ValueError("parent receipt file inventory, bytes, or tree digest differs")
    rows = csv.DictReader(io.StringIO(raw["modes"].decode("utf-8"), newline=""), delimiter="\t", strict=True)
    if (not rows.fieldnames or len(set(rows.fieldnames)) != len(rows.fieldnames)
            or not {"path", "mode"}.issubset(rows.fieldnames)):
        raise ValueError("parent mode inventory header differs")
    recorded_modes = {}
    for row in rows:
        path, mode = row.get("path"), row.get("mode")
        if (None in row or not safe_relative(path) or path in recorded_modes
                or not isinstance(mode, str) or re.fullmatch(r"[0-7]{1,4}", mode) is None):
            raise ValueError("parent mode inventory path, duplicate, or mode differs")
        recorded_modes[path] = int(mode, 8)
    if recorded_modes != modes:
        raise ValueError("parent mode inventory differs from archive file modes")
    return receipt


def check_identity(request, receipt, entries):
    identity = request["identity"]
    source = receipt.get("source", {})
    delivery = {key: identity[key] for key in ("version", "request_id", "preparation_sha256")}
    if (receipt.get("schema") != "provingkit-artifact-receipt-v1"
            or not isinstance(source, dict) or source.get("commit") != identity["source_commit"]
            or source.get("repository") != "https://github.com/nisavid/provingkit"
            or source.get("preview_label") != "preview-" + identity["source_commit"][:12]
            or source.get("channel") not in ("main", "preview", "release")
            or receipt.get("builder") != {"name": "provingkit-artifact-projector-v1",
                                           "revision": identity["projector_revision"]}
            or receipt.get("target") != request["target"]
            or receipt.get("policy_sha256") != identity["policy_sha256"]
            or receipt.get("plugin_slate") != identity["plugin_slate"]
            or receipt.get("delivery") != delivery):
        raise ValueError("parent receipt identity differs from the selected snapshot")

    def document(path):
        if path not in entries or entries[path][2] != "file":
            raise ValueError(f"parent manifest/catalog identity file is missing: {path}")
        value = decode(entries[path][1], "parent manifest/catalog identity")
        if not isinstance(value, dict):
            raise ValueError(f"parent manifest/catalog identity is not an object: {path}")
        return value

    for member in identity["plugin_slate"]:
        paths = [f"plugins/{member}/plugin.json"]
        adapter_root = f"plugins/{member}/.claude-plugin"
        if request["target"] == "claude":
            paths.append(adapter_root + "/plugin.json")
        elif any(path == adapter_root or path.startswith(adapter_root + "/") for path in entries):
            raise ValueError("parent Agent Plugins identity contains a Claude adapter")
        for path in paths:
            manifest = document(path)
            if manifest.get("name") != member or manifest.get("version") != identity["version"]:
                raise ValueError(f"parent stamped manifest identity differs: {path}")
    catalog_path = (".agents/plugins/marketplace.json" if request["target"] == "agent-plugins"
                    else ".claude-plugin/marketplace.json")
    catalog = document(catalog_path)
    members = catalog.get("plugins")
    if (catalog.get("name") != "provingkit" or not isinstance(members, list)
            or not all(isinstance(row, dict) for row in members)
            or [row.get("name") for row in members] != identity["plugin_slate"]):
        raise ValueError("parent catalog complete-slate identity differs")
    for row in members:
        path = f"./plugins/{row['name']}"
        expected_source = {"source": "local", "path": path} if request["target"] == "agent-plugins" else path
        if (row.get("source") != expected_source
                or (request["target"] == "claude" and row.get("version") != identity["version"])):
            raise ValueError("parent catalog member identity differs")


def selected_parent(request):
    parent = request["parent"]
    raw = {label: regular_bytes(row["path"]) for label, row in parent.items()}
    for label, data in raw.items():
        if sha(data) != parent[label]["sha256"]:
            raise ValueError(f"parent digest differs: {label}")
    prefix = f"plugins/{request['member']}/"
    entries = {}
    expected_root = (f"provingkit-ad-hoc-{request['identity']['source_commit']}-"
                     f"{request['identity']['version']}-{request['target']}")
    with tarfile.open(fileobj=io.BytesIO(raw["archive"]), mode="r:gz") as archive:
        for entry in archive:
            name = entry.name.removesuffix("/") if entry.isdir() else entry.name
            if (not safe_relative(name) or name.split("/", 1)[0] != expected_root
                    or not (entry.isdir() or entry.type in (tarfile.REGTYPE, tarfile.AREGTYPE))
                    or entry.sparse is not None or not 0 <= entry.mode <= 0o7777
                    or (entry.isdir() and entry.size != 0)):
                raise ValueError(f"parent archive path, kind, or mode differs: {entry.name!r}")
            relative = name[len(expected_root):].removeprefix("/")
            if relative in entries or (not entries and (relative or not entry.isdir())):
                raise ValueError("parent archive repeats an entry or lacks its initial root directory")
            kind = "directory" if entry.isdir() else "file"
            data = b"" if entry.isdir() else archive.extractfile(entry).read()
            mode = (stat.S_IFDIR if entry.isdir() else stat.S_IFREG) | entry.mode
            entries[relative] = (mode, data, kind)
    for relative in entries:
        if relative:
            parent_path = str(PurePosixPath(relative).parent)
            parent_path = "" if parent_path == "." else parent_path
            if parent_path not in entries or entries[parent_path][2] != "directory":
                raise ValueError(f"parent archive directory evidence is missing: {relative}")
    if prefix[:-1] not in entries or entries[prefix[:-1]][2] != "directory":
        raise ValueError("parent archive lacks the selected member directory")
    receipt = check_files(raw, entries)
    check_identity(request, receipt, entries)
    raw["issuer_result"] = check_issuer_result(request, raw)
    root_mode = stat.S_IMODE(entries[prefix[:-1]][0])
    selected = {name[len(prefix):]: row for name, row in entries.items() if name.startswith(prefix)}
    return raw, selected, root_mode


def zip_bytes(selected):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, (mode, data, kind) in sorted(selected.items()):
            info = zipfile.ZipInfo(name + ("/" if kind == "directory" else ""), EPOCH)
            info.create_system = 3
            info.external_attr = (mode << 16) | (0x10 if kind == "directory" else 0)
            archive.writestr(info, data, compress_type=zipfile.ZIP_STORED if kind == "directory"
                            else zipfile.ZIP_DEFLATED, compresslevel=9)
    return stream.getvalue()


def product(request, raw, selected, root_mode):
    version = request["identity"]["version"]
    suffix = "-claude" if request["target"] == "claude" else ""
    name = f"provingkit-{request['member']}-{version}{suffix}.zip"
    archive = zip_bytes(selected)
    sidecar = f"{sha(archive)}  {name}\n".encode()
    record = {
        "schema": "provingkit-member-zip-derivative-v1", "target": request["target"],
        "member": request["member"], "identity": request["identity"],
        "parent": {label: {"sha256": sha(raw[label]), "bytes": len(raw[label])}
                   for label in ("archive", "receipt", "modes")},
        "issuer_result": {"sha256": sha(raw["issuer_result"]), "bytes": len(raw["issuer_result"]),
                          **{key: decode(raw["issuer_result"], "issuer result")[key]
                             for key in ("operation", "request_id", "exposure")}},
        "member_root": {"path": f"plugins/{request['member']}", "mode": f"{root_mode:04o}"},
        "recipe": {"name": "member_zip.py", "sha256": sha(regular_bytes(__file__)),
                   "runtime": {"python": sys.version.split()[0], "zlib": zlib.ZLIB_RUNTIME_VERSION}},
        "entries": [{"path": path + ("/" if kind == "directory" else ""),
                     "projection_path": f"plugins/{request['member']}/{path}",
                     "kind": kind, "mode": f"{stat.S_IMODE(mode):04o}", "bytes": len(data),
                     "sha256": None if kind == "directory" else sha(data)}
                    for path, (mode, data, kind) in sorted(selected.items())],
        "zip": {"name": name, "sha256": sha(archive), "bytes": len(archive)},
        "sidecar": {"name": name + ".sha256", "sha256": sha(sidecar), "bytes": len(sidecar)},
    }
    return name, archive, sidecar, canonical(record)


def verify_zip(raw, selected):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        expected = [name + ("/" if row[2] == "directory" else "")
                    for name, row in sorted(selected.items())]
        if archive.namelist() != expected or archive.comment or archive.testzip() is not None:
            raise ValueError("ZIP inventory, comment, or CRC differs")
        for entry, (_, (mode, data, kind)) in zip(archive.infolist(), sorted(selected.items())):
            if (entry.is_dir() != (kind == "directory") or entry.create_system != 3
                    or entry.external_attr != ((mode << 16) | (0x10 if kind == "directory" else 0))
                    or entry.compress_type != (zipfile.ZIP_STORED if kind == "directory"
                                               else zipfile.ZIP_DEFLATED)
                    or entry.date_time != EPOCH or archive.read(entry) != data
                    or entry.extra or entry.comment):
                raise ValueError(f"ZIP entry differs: {entry.filename}")
    if raw != zip_bytes(selected):
        raise ValueError("ZIP canonical encoding differs")


def verify(request, output, record_pin):
    with parent_descriptor(output, for_output=True):
        pass
    raw, selected, root_mode = selected_parent(request)
    name, expected_zip, expected_sidecar, expected_record = product(request, raw, selected, root_mode)
    record = regular_bytes(output / "DERIVATIVE.json")
    if not record_pin or record_pin != sha(record):
        raise ValueError("derivative record digest differs or is missing")
    if record != expected_record:
        raise ValueError("derivative record differs from original parent selection or recipe")
    archive = regular_bytes(output / name)
    verify_zip(archive, selected)
    if archive != expected_zip or regular_bytes(output / (name + ".sha256")) != expected_sidecar:
        raise ValueError("ZIP digest or sidecar differs")
    if output_inventory(output) != {name, name + ".sha256", "DERIVATIVE.json"}:
        raise ValueError("derivative output inventory differs")
    return {"status": "verified", "scope": "local-derivative-integrity", "record_sha256": sha(record),
            "issuer_exposure": decode(raw["issuer_result"], "issuer result")["exposure"]}


def derive(request, output):
    raw, selected, root_mode = selected_parent(request)
    name, archive, sidecar, record_bytes = product(request, raw, selected, root_mode)
    write_fresh(output, {name: archive, name + ".sha256": sidecar, "DERIVATIVE.json": record_bytes})
    return verify(request, output, sha(record_bytes))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("derive", "verify"))
    parser.add_argument("--request", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--record-sha256")
    args = parser.parse_args()
    try:
        request = decode(regular_bytes(args.request), "request")
        check_request(request)
        result = (derive(request, Path(args.output)) if args.operation == "derive" else
                  verify(request, Path(args.output), args.record_sha256))
    except (ValueError, OSError, KeyError, csv.Error, tarfile.TarError, zipfile.BadZipFile,
            zlib.error, RuntimeError, EOFError) as error:
        print(json.dumps({"status": "rejected", "reason": str(error)}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
