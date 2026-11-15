#!/usr/bin/env python3
"""Prepare immutable Provingkit snapshot deliveries for one cooperating issuer."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import stat
from pathlib import Path

if __package__:
    from .evidence_transport import run_candidate_git
else:
    from evidence_transport import run_candidate_git

PREPARATION_SCHEMA = "provingkit-snapshot-preparation-v1"
NORMAL = r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
CUT = rf"{NORMAL}-(?:alpha|beta|rc)\.[1-9][0-9]*"
ARTIFACT_REF = "refs/heads/ivan/provingkit-ad-hoc-artifacts"
FILES = {"artifact.tar.gz", "RECEIPT.json", "modes.tsv"}
TARGETS = {"agent-plugins", "claude", "cursor"}


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def decode_json(raw: bytes) -> object:
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate JSON field")
            value[key] = item
        return value
    return json.loads(raw, object_pairs_hook=unique)


def version_key(version: str) -> tuple:
    normal, separator, suffix = version.partition("-")
    if re.fullmatch(NORMAL, normal) is None:
        raise ValueError("unsupported normal version")
    release = tuple(map(int, normal.split(".")))
    if not separator:
        return release, 1, ()
    if not suffix or any(re.fullmatch(r"(?:0|[1-9][0-9]*|[A-Za-z-][A-Za-z0-9-]*)", part)
                         is None for part in suffix.split(".")):
        raise ValueError("unsupported prerelease version")
    return release, 0, tuple((0, int(part)) if part.isdigit() else (1, part)
                            for part in suffix.split("."))


def validate_preparation(record: object) -> dict:
    fields = {"schema", "request_id", "release_unit", "target_release", "preceding_cut",
              "next_named_release", "sequence", "version", "source_commit"}
    if not isinstance(record, dict) or set(record) != fields:
        raise ValueError("snapshot preparation fields differ from the supported contract")
    if record["schema"] != PREPARATION_SCHEMA or record["release_unit"] != "provingkit":
        raise ValueError("unsupported snapshot preparation schema or release unit")
    for field in fields - {"sequence"}:
        if not isinstance(record[field], str) or not record[field]:
            raise ValueError(f"snapshot preparation requires a string {field}")
    target, preceding, successor = (record[key] for key in
                                    ("target_release", "preceding_cut", "next_named_release"))
    if re.fullmatch(NORMAL, target) is None:
        raise ValueError("snapshot target must be a normal release")
    if preceding != target + "-0" and re.fullmatch(CUT, preceding) is None:
        raise ValueError("unsupported preceding cut")
    if not preceding.startswith(target + "-"):
        raise ValueError("preceding cut belongs to another target")
    if successor != target and (re.fullmatch(CUT, successor) is None
                                or not successor.startswith(target + "-")):
        raise ValueError("successor belongs to another target or is unsupported")
    if type(record["sequence"]) is not int or record["sequence"] < 1:
        raise ValueError("snapshot sequence must be a positive integer")
    if record["version"] != f"{preceding}.snapshot.{record['sequence']}":
        raise ValueError("snapshot version differs from its anchor and sequence")
    if not version_key(preceding) < version_key(record["version"]) < version_key(successor):
        raise ValueError("snapshot is outside its named-release interval")
    if re.fullmatch(r"[0-9a-f]{40}", record["source_commit"]) is None:
        raise ValueError("snapshot preparation requires a full source commit")
    identifier(record["request_id"])
    return record


def fields(request: object, expected: set[str]) -> dict:
    if not isinstance(request, dict) or set(request) != expected | {"operation"}:
        raise ValueError("request fields differ from the supported operation")
    for name in expected - {"variants"}:
        if not isinstance(request[name], str) or not request[name]:
            raise ValueError(f"request requires a nonempty string {name}")
    return request


def identifier(value: object) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value) is None:
        raise ValueError("request identifier must be a short portable identifier")
    return value


def preparation(state: dict, request_id: str, source: str, sequence: int) -> dict:
    return validate_preparation({"schema": PREPARATION_SCHEMA, "request_id": request_id,
        "release_unit": "provingkit", "target_release": state["target_release"],
        "preceding_cut": state["preceding_cut"], "next_named_release": state["next_named_release"],
        "sequence": sequence, "version": f"{state['preceding_cut']}.snapshot.{sequence}",
        "source_commit": source})


def ready_publication(state: dict, request: dict) -> dict:
    raw = Path(request["publication_plan"]).read_bytes()
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    if request["reviewed_plan_sha256"] != digest:
        raise ValueError("publication plan differs from its reviewed digest")
    plan = decode_json(raw)
    if not isinstance(plan, dict) or plan.get("status") != "ready":
        raise ValueError("publication plan is not ready")
    destination = plan.get("destination")
    if (not isinstance(destination, dict) or destination.get("ref") != ARTIFACT_REF
            or destination.get("endpoint_fingerprint") != state["endpoint_fingerprint"]):
        raise ValueError("publication plan targets another route or endpoint")
    commit = plan.get("source_sha")
    if not isinstance(commit, str) or re.fullmatch(r"[0-9a-f]{40}", commit) is None:
        raise ValueError("publication plan needs a full publication commit")
    outgoing = plan.get("outgoing_shas")
    if (not isinstance(outgoing, list) or not outgoing
            or any(not isinstance(sha, str) or re.fullmatch(r"[0-9a-f]{40}", sha) is None for sha in outgoing)
            or len(set(outgoing)) != len(outgoing) or commit not in outgoing):
        raise ValueError("publication plan needs its complete outgoing commit set")
    return {"commit": commit, "destination": destination, "plan_sha256": digest, "outgoing_shas": outgoing}


def read_variants(connection: sqlite3.Connection, supplied: object, prepared: dict) -> dict:
    if not isinstance(supplied, dict) or not supplied or not set(supplied) <= TARGETS:
        raise ValueError("variants must name supported projection targets")
    variants = {}
    for target, paths in supplied.items():
        if not isinstance(paths, dict) or set(paths) != FILES:
            raise ValueError("each variant requires its archive, receipt, and mode inventory")
        variants[target] = {}
        data = {}
        for name, path in paths.items():
            if not isinstance(path, str) or not stat.S_ISREG(Path(path).lstat().st_mode):
                raise ValueError("variant inputs must be regular files")
            raw = Path(path).read_bytes()
            data[name] = raw
            digest = hashlib.sha256(raw).hexdigest()
            variants[target][name] = {"bytes": len(raw), "sha256": digest}
            connection.execute("INSERT OR IGNORE INTO artifacts VALUES (?, ?)", (digest, raw))
        receipt = decode_json(data["RECEIPT.json"])
        delivery = {"version": prepared["version"], "request_id": prepared["request_id"],
                    "preparation_sha256": hashlib.sha256(canonical_json(prepared)).hexdigest()}
        if (not isinstance(receipt, dict) or not isinstance(receipt.get("source"), dict)
                or receipt["source"].get("commit") != prepared["source_commit"]
                or receipt.get("target") != target or receipt.get("delivery") != delivery):
            raise ValueError("variant receipt differs from the prepared source or delivery")
    return variants


def verify_transport(repository: str, publication: dict, versions: dict) -> None:
    expected_paths = {}
    for version, identity in versions.items():
        for target, files in identity["variants"].items():
            for name, expected in files.items():
                path = f"ad-hoc/{identity['source_commit']}/{version}/{target}/{name}"
                expected_paths[path] = expected
    # The existing publisher owns computation and revalidation of this reviewed
    # outgoing set. A ref push exposes its reachable history, not just its tip.
    for commit in publication["outgoing_shas"]:
        inventory = run_candidate_git(Path(repository),
            ["ls-tree", "-r", "-z", commit, "--", "ad-hoc"], error_factory=ValueError,
            operation="inspect snapshot publication history", runtime_policy="host-compatible")
        found = set()
        for row in inventory.split(b"\0"):
            if not row:
                continue
            metadata, raw_path = row.split(b"\t", 1)
            path = raw_path.decode("utf-8")
            parts = path.split("/")
            if len(parts) < 3 or re.fullmatch(r"[0-9a-f]{40}", parts[1]) is None or ".snapshot." not in parts[2]:
                continue
            if path not in expected_paths:
                raise ValueError("publication history contains an unrecorded snapshot file or variant")
            if not metadata.startswith((b"100644 blob ", b"100755 blob ")):
                raise ValueError("publication omits a regular retained variant file")
            raw = run_candidate_git(Path(repository), ["show", f"{commit}:{path}"],
                error_factory=ValueError, operation="inspect snapshot transport bytes",
                runtime_policy="host-compatible")
            expected = expected_paths[path]
            if len(raw) != expected["bytes"] or hashlib.sha256(raw).hexdigest() != expected["sha256"]:
                raise ValueError("publication changes retained variant bytes")
            found.add(path)
        if commit == publication["commit"] and found != set(expected_paths):
            raise ValueError("publication omits a regular retained variant file")


def transition(connection: sqlite3.Connection, state: dict | None, request: object) -> tuple[dict, dict]:
    if not isinstance(request, dict):
        raise ValueError("request must be an object")
    operation = request.get("operation")
    if not isinstance(operation, str):
        raise ValueError("operation must be a string")
    if operation == "initialize":
        fields(request, {"custody_owner", "endpoint_fingerprint", "target_release", "preceding_cut", "next_named_release"})
        identifier(request["custody_owner"])
        if not isinstance(request["endpoint_fingerprint"], str) or re.fullmatch(
                r"sha256:[0-9a-f]{64}", request["endpoint_fingerprint"]) is None:
            raise ValueError("a bound publication endpoint fingerprint is required")
        if state is not None:
            raise ValueError("issuance state already exists; initialization cannot replace history")
        state = {"schema": "provingkit-snapshot-state-v1", "custody_owner": request["custody_owner"],
                 "endpoint_fingerprint": request["endpoint_fingerprint"],
                 "target_release": request["target_release"], "preceding_cut": request["preceding_cut"],
                 "next_named_release": request["next_named_release"], "next_sequence": 1,
                 "last_issued": None, "pending": None, "preparations": {}, "deliveries": {},
                 "versions": {}, "target_history": []}
        preparation(state, "interval-check", "0" * 40, 1)
        return state, {"outcome": "initialized", "custody_owner": state["custody_owner"]}
    if state is None:
        raise ValueError("issuance state has not been initialized")
    if operation == "inspect":
        fields(request, set())
        return state, state
    if operation == "prepare":
        fields(request, {"request_id", "source_commit"})
        request_id = identifier(request["request_id"])
        existing = state["preparations"].get(request_id)
        if existing is not None:
            if existing["source_commit"] != request["source_commit"]:
                raise ValueError("request identifier is bound to another source")
            return state, existing
        if request_id in state["deliveries"]:
            raise ValueError("request identifier is already bound to a variant addition")
        if state["preceding_cut"] == state["target_release"]:
            raise ValueError("the normal target is closed; record the next normal target")
        record = preparation(state, request_id, request["source_commit"], state["next_sequence"])
        state["next_sequence"] += 1
        state["preparations"][request_id] = record
        return state, record
    if operation == "advance-cut":
        fields(request, {"preceding_cut", "next_named_release"})
        if state["pending"] is not None:
            raise ValueError("pending exposure prevents a cut transition")
        if request["preceding_cut"] != state["next_named_release"]:
            raise ValueError("cut transition must consume the recorded successor")
        if state["preceding_cut"] == state["target_release"]:
            raise ValueError("the normal target is already closed")
        successor = dict(state, preceding_cut=request["preceding_cut"],
                         next_named_release=request["next_named_release"])
        if successor["preceding_cut"] == state["target_release"]:
            if successor["next_named_release"] != state["target_release"]:
                raise ValueError("normal-release closure must name that normal release")
        else:
            preparation(successor, "interval-check", "0" * 40, state["next_sequence"])
        return successor, {"outcome": "cut-recorded", "preceding_cut": successor["preceding_cut"]}
    if operation == "retarget":
        fields(request, {"target_release", "next_named_release"})
        if state["pending"] is not None or state["preceding_cut"] != state["target_release"]:
            raise ValueError("retargeting requires a closed normal release and no pending exposure")
        target = request["target_release"]
        if version_key(target) <= version_key(state["target_release"]):
            raise ValueError("the next normal target must advance")
        successor = dict(state, target_release=target, preceding_cut=target + "-0",
                         next_named_release=request["next_named_release"], next_sequence=1, last_issued=None)
        preparation(successor, "interval-check", "0" * 40, 1)
        successor["target_history"].append({key: state[key] for key in
            ("target_release", "preceding_cut", "next_named_release", "next_sequence", "last_issued")})
        return successor, {"outcome": "retargeted", "target_release": target}
    if operation in {"issue", "add-variants"}:
        required = {"request_id", "variants", "publication_plan", "reviewed_plan_sha256", "transport_repository"}
        fields(request, required | ({"version", "source_commit"} if operation == "add-variants" else set()))
        request_id = identifier(request["request_id"])
        if operation == "add-variants":
            identity = state["versions"].get(request["version"])
            if identity is None or identity["source_commit"] != request["source_commit"]:
                raise ValueError("variant addition changes the recorded source identity")
            if not any(item["version"] == request["version"] and item["exposure"] == "verified"
                       for item in state["deliveries"].values()):
                raise ValueError("variant addition requires an exposed version")
            if request_id in state["preparations"]:
                raise ValueError("variant addition needs its own request identifier")
            prepared = identity["preparation"]
        else:
            prepared = state["preparations"].get(request_id)
        if prepared is None:
            raise ValueError("issuance requires its original preparation")
        publication = ready_publication(state, request)
        variants = read_variants(connection, request["variants"], prepared)
        existing = state["deliveries"].get(request_id)
        if existing is not None:
            if (existing["operation"] != operation or existing["version"] != prepared["version"]
                    or existing["publication"] != publication or existing["variants"] != variants):
                raise ValueError("retry changes its original publication or variant bytes")
            return state, existing
        if state["pending"] is not None:
            raise ValueError("a pending exposure must be reconciled before another issuance")
        version = prepared["version"]
        if operation == "issue":
            if any(prepared[key] != state[key] for key in ("target_release", "preceding_cut", "next_named_release")):
                raise ValueError("preparation uses a stale named-release interval")
            if state["last_issued"] is not None and version_key(version) <= version_key(state["last_issued"]):
                raise ValueError("snapshot does not exceed the last issued version")
            if version in state["versions"]:
                raise ValueError("issued versions cannot be reassigned")
            state["versions"][version] = {"source_commit": prepared["source_commit"],
                                          "preparation": prepared, "variants": variants, "withdrawn": False}
            state["last_issued"] = version
        else:
            previous = state["versions"][version]["variants"]
            if any(target in previous and files != previous[target] for target, files in variants.items()):
                raise ValueError("variant addition changes existing variant bytes")
            exposed = {target for delivery in state["deliveries"].values()
                       if delivery["version"] == version and delivery["exposure"] == "verified"
                       for target in delivery["variants"]}
            unexposed = set(variants) - exposed
            if not unexposed:
                raise ValueError("variant addition must include a target without verified exposure")
            previous.update(variants)
        required_versions = {}
        for retained_version, identity in state["versions"].items():
            targets = {target for delivery in state["deliveries"].values()
                       if delivery["version"] == retained_version and delivery["exposure"] == "verified"
                       for target in delivery["variants"]}
            if retained_version == version:
                targets.update(variants)
            if targets:
                required_versions[retained_version] = dict(identity, variants={
                    target: identity["variants"][target] for target in targets})
        verify_transport(request["transport_repository"], publication, required_versions)
        record = {"operation": operation, "request_id": request_id, "version": version,
                  "source_commit": prepared["source_commit"], "publication": publication,
                  "variants": variants, "exposure": "pending"}
        if operation == "add-variants":
            record["retry_of"] = sorted(delivery["request_id"] for delivery in state["deliveries"].values()
                if delivery["version"] == version and delivery["exposure"] == "cancelled"
                and set(delivery["variants"]) & unexposed)
        state["pending"] = request_id
        state["deliveries"][request_id] = record
        return state, record
    if operation == "reconcile":
        fields(request, {"request_id", "publication_result"})
        record = state["deliveries"].get(identifier(request["request_id"]))
        if record is None:
            raise ValueError("no original exposure record exists")
        raw = Path(request["publication_result"]).read_bytes()
        result = decode_json(raw)
        publication = record["publication"]
        if (not isinstance(result, dict) or result.get("source_sha") != publication["commit"]
                or result.get("destination") != publication["destination"]
                or type(result.get("push_attempted")) is not bool):
            raise ValueError("result differs from the original publication")
        digest = hashlib.sha256(raw).hexdigest()
        if record["exposure"] != "pending":
            if record.get("result_sha256") != digest:
                raise ValueError("settled exposure cannot be reassigned another result")
            return state, record
        expected = [{"kind": "remote_ref_equals",
                     "endpoint_fingerprint": publication["destination"]["endpoint_fingerprint"],
                     "ref": ARTIFACT_REF, "sha": publication["commit"]}]
        if result["push_attempted"]:
            record["attempt_observed"] = True
        if result.get("status") == "verified":
            if result["push_attempted"] is not True or result.get("reasons") != [] or result.get("postchecks") != expected:
                record["result_sha256"] = digest
                return state, {"outcome": "rejected",
                               "reason": "verified result lacks its required publication postcheck"}
            record["exposure"] = "verified"
        elif result["push_attempted"] is False and result.get("status") == "blocked":
            if record.get("attempt_observed"):
                raise ValueError("a later unattempted result cannot settle an earlier uncertain attempt")
            record["exposure"] = "cancelled"
        record["result_sha256"] = digest
        if record["exposure"] != "pending":
            state["pending"] = None
        return state, record
    if operation in {"withdraw", "redeliver"}:
        fields(request, {"version"} | ({"target", "output"} if operation == "redeliver" else set()))
        identity = state["versions"].get(request["version"])
        if identity is None:
            raise ValueError("unknown issued version")
        if operation == "withdraw":
            identity["withdrawn"] = True
            return state, {"outcome": "withdrawn", "version": request["version"]}
        target = request["target"]
        if not any(item["version"] == request["version"] and target in item["variants"]
                   and item["exposure"] == "verified" for item in state["deliveries"].values()):
            raise ValueError("redelivery requires a verified original exposure of that variant")
        retained = {}
        for name, expected in identity["variants"][target].items():
            row = connection.execute("SELECT data FROM artifacts WHERE sha256=?", (expected["sha256"],)).fetchone()
            if row is None or len(row[0]) != expected["bytes"] or hashlib.sha256(row[0]).hexdigest() != expected["sha256"]:
                raise ValueError("retained variant bytes are unavailable or changed")
            retained[name] = row[0]
        output = Path(request["output"])
        output.mkdir(mode=0o700)
        for name, raw in retained.items():
            (output / name).write_bytes(raw)
        return state, {"outcome": "redelivered", "version": request["version"],
                       "source_commit": identity["source_commit"], "variants": {target: identity["variants"][target]},
                       "withdrawn": identity["withdrawn"]}
    raise ValueError("unsupported issuance operation")


def pinned_state_path(state_path: Path) -> tuple[int, Path]:
    search_flag = getattr(os, "O_PATH", None)
    if search_flag is None:
        search_flag = getattr(os, "O_SEARCH", None)
    if (
        search_flag is None
        or not hasattr(os, "O_DIRECTORY")
        or not hasattr(os, "O_NOFOLLOW")
        or os.open not in os.supports_dir_fd
        or os.stat not in os.supports_dir_fd
    ):
        raise ValueError(
            "safe issuance state requires search-capable no-follow directory operations"
        )
    state_path = Path(os.path.abspath(state_path))
    if state_path == Path(state_path.anchor) or state_path.name in {"", ".", ".."}:
        raise ValueError("issuance state needs a file path below a private directory")

    root = Path(state_path.anchor)
    root_metadata = root.stat()
    first = root / state_path.parts[1]
    try:
        first_metadata = first.lstat()
    except FileNotFoundError:
        first_metadata = None
    if (
        len(state_path.parts) > 2
        and first_metadata is not None
        and stat.S_ISLNK(first_metadata.st_mode)
        and first_metadata.st_uid == root_metadata.st_uid
        and not root_metadata.st_mode & 0o022
    ):
        target = first.readlink()
        if not target.is_absolute():
            target = first.parent / target
        state_path = Path(os.path.abspath(target.joinpath(*state_path.parts[2:])))

    flags = search_flag | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(state_path.anchor, flags)
    try:
        namespace = Path(state_path.anchor)
        for component in state_path.parent.parts[1:]:
            namespace /= component
            child = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
            metadata = os.fstat(descriptor)
            if (metadata.st_uid not in {root_metadata.st_uid, os.geteuid()}
                    or metadata.st_mode & 0o022 and not metadata.st_mode & stat.S_ISVTX):
                raise ValueError(
                    f"issuance state ancestor is writable by other users: {namespace}"
                )
        metadata = os.fstat(descriptor)
        if (not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.geteuid()
                or metadata.st_mode & 0o077):
            raise ValueError("issuance state needs a private owned parent directory")
        for root in (Path("/proc/self/fd"), Path("/dev/fd")):
            pinned_parent = root / str(descriptor)
            try:
                visible = pinned_parent.stat()
            except OSError:
                continue
            if (visible.st_dev, visible.st_ino) == (metadata.st_dev, metadata.st_ino):
                return descriptor, pinned_parent / state_path.name
        raise ValueError("safe issuance state requires descriptor-backed filesystem paths")
    except BaseException:
        os.close(descriptor)
        raise


def perform(state_path: Path, request: object) -> dict:
    descriptor, state_path = pinned_state_path(state_path)
    try:
        try:
            metadata = os.stat(state_path.name, dir_fd=descriptor, follow_symlinks=False)
        except FileNotFoundError:
            metadata = None
        if metadata is not None:
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid():
                raise ValueError("issuance state must be an owned regular file")
        elif not isinstance(request, dict) or request.get("operation") != "initialize":
            raise ValueError("issuance state has not been initialized")
        with sqlite3.connect(state_path, timeout=10, isolation_level=None) as connection:
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY CHECK(id=1), document TEXT NOT NULL)")
            connection.execute("CREATE TABLE IF NOT EXISTS artifacts (sha256 TEXT PRIMARY KEY, data BLOB NOT NULL)")
            row = connection.execute("SELECT document FROM state WHERE id=1").fetchone()
            state = decode_json(row[0].encode()) if row else None
            state, response = transition(connection, state, request)
            connection.execute("INSERT OR REPLACE INTO state VALUES (1, ?)", (canonical_json(state).decode(),))
            connection.execute("COMMIT")
        return response
    finally:
        os.close(descriptor)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    args = parser.parse_args()
    try:
        response = perform(args.state, decode_json(args.request.read_bytes()))
    except (ValueError, OSError, sqlite3.Error) as error:
        print(canonical_json({"outcome": "rejected", "reason": str(error)}).decode(), end="")
        return 1
    print(canonical_json(response).decode(), end="")
    return 1 if response.get("outcome") == "rejected" else 0


if __name__ == "__main__":
    raise SystemExit(main())
