#!/usr/bin/env python3
"""Prepare offline Proseweaving writer inputs; never invoke a model."""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile
import types

SKILL = "writing-for-people"
SCRIPT = "scripts/prepare_proseweaving_eval.py"
TOOLS = (
    SCRIPT, "scripts/validate_proseweaving.py", "scripts/evidence_transport.py",
    "scripts/agent_plugins_standard.py", "scripts/member_versions.py",
    "scripts/member_source_stage_cli.py",
    "docs/proseweaving-evaluation-preparation.md",
)
BOOTSTRAP_SHA256 = "fa4dc0e5e4c8a8bdf4b55023b5085648122726dc08fb2d0afe16f607ecb8c101"


class PreparationError(ValueError):
    """Preparation or consumer evidence does not satisfy the public contract."""


def _open_directory(path):
    descriptor = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in path.parts[1:]:
            if component == "..":
                raise PreparationError("Lexical parent traversal is unsupported.")
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _read_regular(path):
    import stat
    path = Path(path).absolute()
    parent = _open_directory(path.parent)
    try:
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                             dir_fd=parent)
        with os.fdopen(descriptor, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise PreparationError("Expected a regular input file.")
            return stream.read()
    finally:
        os.close(parent)


def _module(path, content, name):
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(content, str(path), "exec"), module.__dict__)
    return module


def _transport():
    path = Path(__file__).absolute().parent / "evidence_transport.py"
    content = _read_regular(path)
    if hashlib.sha256(content).hexdigest() != BOOTSTRAP_SHA256:
        raise PreparationError("Bootstrap evidence transport identity changed.")
    return _module(path, content, "writer_preparation_transport")


def _identity(path, content):
    return {"path": path, "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(), "mode": "0600"}


def _publish(helper, root, path, content):
    helper.frozen_no_replace_write(root / path, content, error_factory=PreparationError)
    return _identity(path, content)


def _sources(helper, repository, revision):
    descriptor = _open_directory(repository)
    os.close(descriptor)
    if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", revision):
        raise PreparationError("A full lowercase commit OID is required.")

    def git(*arguments):
        return helper.run_candidate_git(
            repository, list(arguments), error_factory=PreparationError,
            operation="offline writer preparation",
        )

    if git("cat-file", "-t", revision).strip() != b"commit":
        raise PreparationError("Source revision must identify a commit.")
    entries = git("ls-tree", "-r", "-z", "--full-tree", revision, "--",
                  "plugins/proseweaving", *TOOLS)
    selected = {}
    for row in entries.split(b"\0"):
        if not row:
            continue
        header, raw_path = row.split(b"\t", 1)
        mode, kind, oid = header.decode("ascii").split()
        path = raw_path.decode("utf-8")
        relative = PurePosixPath(path)
        if (relative.is_absolute() or relative.as_posix() != path
                or ".." in relative.parts
                or any(ord(char) < 32 or ord(char) == 127 for char in path)
                or not (path in TOOLS or path.startswith("plugins/proseweaving/"))
                or mode not in {"100644", "100755"} or kind != "blob"):
            raise PreparationError("Unsupported source path or Git file mode.")
        selected[path] = (mode, git("cat-file", "blob", oid))
    if not set(TOOLS).issubset(selected):
        raise PreparationError("Required method, procedure, or helper is missing.")
    if _read_regular(Path(__file__)) != selected[SCRIPT][1]:
        raise PreparationError("Executing preparer differs from the selected commit.")
    if _read_regular(Path(helper.__file__)) != selected["scripts/evidence_transport.py"][1]:
        raise PreparationError("Executing transport differs from the selected commit.")
    return selected


def _validator(snapshot):
    scripts = snapshot / "scripts"
    names = ["agent_plugins_standard", "member_versions", "member_source_stage_cli"]
    saved = {name: sys.modules.pop(name, None) for name in names}
    old_path = sys.path[:]
    sys.path.insert(0, str(scripts))
    try:
        path = scripts / "validate_proseweaving.py"
        return _module(path, _read_regular(path), "writer_preparation_validator")
    finally:
        sys.path[:] = old_path
        for name in names:
            sys.modules.pop(name, None)
            if saved[name] is not None:
                sys.modules[name] = saved[name]


def _batch(helper, snapshot):
    validator = _validator(snapshot)
    plugin = snapshot / "plugins/proseweaving"
    topology, semantic = validator.inspect_contract(plugin)
    validator.validate_inventory(plugin, semantic)
    validator.validate_portability(plugin)
    validator.validate_content_lock(plugin, semantic)
    _, bodies, _ = validator.validate_skills(plugin, topology)
    bundle = validator.build_candidate_bundle(plugin, topology, SKILL, bodies, semantic)
    corpus = validator.load_json(plugin, f"skills/{SKILL}/evals/evals.json", "writer corpus")
    files = {}
    coordinates = []
    for case in corpus["evals"]:
        number = case["id"]
        fixture = validator.read(plugin, Path("skills") / SKILL / case["fixture_paths"][0])
        actor = validator.build_executor_payload(
            prompt=case["prompt"], fixture=fixture, candidate_bundle=bundle,
        )
        request = f"requests/case-{number:03d}.json"
        files[request] = json.dumps(
            actor, ensure_ascii=False, allow_nan=False, separators=(",", ":"),
        ).encode("utf-8") + b"\n"
        files[f"grading/case-{number:03d}.json"] = helper.json_file_bytes({
            key: case[key] for key in ["expected_output", "expectations"]
        })
        coordinates.extend({
            "case_id": number, "repetition": repetition,
            "request": request, "state": "unstarted",
        } for repetition in [1, 2, 3])
    files["coordinates.json"] = helper.json_file_bytes(coordinates)
    return files, len(coordinates)


def _producer_runtime():
    import yaml
    return {
        "python_version": sys.version,
        "python_executable": str(Path(sys.executable).resolve()),
        "python_sha256": hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
        "pyyaml_version": yaml.__version__,
        "pyyaml_entry_sha256": hashlib.sha256(Path(yaml.__file__).read_bytes()).hexdigest(),
        "hermetic_runtime": False,
    }


def _outcome(status, preparation=None, diagnostics=None):
    return {
        "format": "proseweaving-eval-preparation-outcome-v1",
        "status": status, "preparation": preparation,
        "diagnostics": diagnostics or [],
        "intended_exit_status": 0 if status == "complete" else 2 if status == "rejected" else 1,
    }


def _reserve_output(path):
    parent = _open_directory(path.parent)
    try:
        os.mkdir(path.name, 0o700, dir_fd=parent)
    finally:
        os.close(parent)


def _expected_files(helper, repository, revision, runtime):
    sources = _sources(helper, repository, revision)
    with tempfile.TemporaryDirectory(prefix="proseweaving-preparation-") as temporary:
        snapshot = Path(temporary)
        for path, (_, content) in sources.items():
            _publish(helper, snapshot, path, content)
        files, count = _batch(helper, snapshot)
    source_inventory = []
    for path, (mode, content) in sorted(sources.items()):
        artifact = "source/" + path
        files[artifact] = content
        source_inventory.append({
            "path": path, "git_mode": mode, "artifact": artifact,
            "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(),
        })
    files["source-inventory.json"] = helper.json_file_bytes({
        "format": "proseweaving-eval-source-inventory-v1",
        "source_revision": revision, "files": source_inventory, "runtime": runtime,
    })
    return files, count


def _preparation(revision, files, count):
    return {
        "format": "proseweaving-eval-preparation-v1",
        "state": "prepared-not-executed", "source_revision": revision,
        "skill_name": SKILL, "coordinate_count": count,
        "artifacts": [_identity(path, content) for path, content in sorted(files.items())],
    }


def _verify_files(output, files):
    import stat
    expected_directories = {""}
    for name in files:
        expected_directories.update(
            parent.as_posix() for parent in PurePosixPath(name).parents
            if parent.as_posix() != "."
        )
    seen_files = set()
    seen_directories = set()

    def walk(directory, relative):
        metadata = directory.lstat()
        if (not stat.S_ISDIR(metadata.st_mode)
                or stat.S_IMODE(metadata.st_mode) != 0o700
                or metadata.st_uid != os.getuid()):
            raise PreparationError("Artifact directory is not private, owned and regular.")
        seen_directories.add(relative)
        with os.scandir(directory) as entries:
            for entry in entries:
                name = str(PurePosixPath(relative) / entry.name)
                metadata = entry.stat(follow_symlinks=False)
                if stat.S_ISDIR(metadata.st_mode):
                    walk(Path(entry.path), name)
                elif (stat.S_ISREG(metadata.st_mode)
                      and stat.S_IMODE(metadata.st_mode) == 0o600
                      and metadata.st_uid == os.getuid()):
                    if name not in files or _read_regular(entry.path) != files[name]:
                        raise PreparationError("Unexpected or changed artifact bytes.")
                    seen_files.add(name)
                else:
                    raise PreparationError("Artifact type, ownership or mode changed.")

    walk(output, "")
    if seen_files != set(files) or seen_directories != expected_directories:
        raise PreparationError("Artifact or directory inventory is incomplete or changed.")


def _retained_runtime(helper, output):
    inventory = helper.strict_json_bytes(
        _read_regular(output / "source-inventory.json"),
        label="source inventory", error_factory=PreparationError,
    )
    runtime = inventory.get("runtime") if isinstance(inventory, dict) else None
    keys = {"python_version", "python_executable", "python_sha256",
            "pyyaml_version", "pyyaml_entry_sha256", "hermetic_runtime"}
    if (not isinstance(runtime, dict) or set(runtime) != keys
            or runtime["hermetic_runtime"] is not False):
        raise PreparationError("Producer runtime record has an unsupported shape.")
    for key in keys - {"hermetic_runtime"}:
        value = runtime[key]
        if not isinstance(value, str) or not value or "\0" in value:
            raise PreparationError("Producer runtime identity must contain nonempty strings.")
        if key.endswith("sha256") and not re.fullmatch(r"[0-9a-f]{64}", value):
            raise PreparationError("Producer runtime digest is invalid.")
    if not Path(runtime["python_executable"]).is_absolute():
        raise PreparationError("Producer Python executable identity must be absolute.")
    return runtime


def verify_preparation(output_dir, *, repository, source_revision, stdout, returncode):
    """Accept documented artifacts only against independent source and actual exit."""
    try:
        if type(returncode) is not int or returncode != 0 or not isinstance(stdout, bytes):
            raise PreparationError("No complete successful invocation was observed.")
        helper = _transport()
        output = Path(output_dir).absolute()
        runtime = _retained_runtime(helper, output)
        files, count = _expected_files(
            helper, Path(repository).absolute(), source_revision, runtime,
        )
        prepared = _preparation(source_revision, files, count)
        preparation_bytes = helper.json_file_bytes(prepared)
        files["preparation.json"] = preparation_bytes
        outcome = _outcome("complete", _identity("preparation.json", preparation_bytes))
        outcome_bytes = helper.json_file_bytes(outcome)
        if stdout != outcome_bytes:
            raise PreparationError("Observed stdout does not match the expected complete outcome.")
        files["outcome.json"] = outcome_bytes
        _verify_files(Path(output_dir).absolute(), files)
        return prepared
    except PreparationError:
        raise
    except (ValueError, OSError) as error:
        raise PreparationError(str(error)) from error


def prepare(arguments):
    helper = _transport()
    repository = Path(arguments.repository).absolute()
    files, count = _expected_files(
        helper, repository, arguments.source_revision, _producer_runtime(),
    )
    output = Path(arguments.output_dir).absolute()
    _reserve_output(output)
    try:
        for path, content in sorted(files.items()):
            _publish(helper, output, path, content)
        prepared = _preparation(arguments.source_revision, files, count)
        preparation_bytes = helper.json_file_bytes(prepared)
        record = _publish(helper, output, "preparation.json", preparation_bytes)
        files["preparation.json"] = preparation_bytes
        _verify_files(output, files)
        outcome = _outcome("complete", record)
        content = helper.json_file_bytes(outcome)
        _publish(helper, output, "outcome.json", content)
        files["outcome.json"] = content
        _verify_files(output, files)
        return content, 0
    except (ValueError, OSError) as error:
        outcome = _outcome("incomplete", diagnostics=[str(error)])
        try:
            _publish(helper, output, "outcome.json", helper.json_file_bytes(outcome))
        except (ValueError, OSError):
            outcome = _outcome("indeterminate", diagnostics=[str(error), "Outcome publication uncertain."])
        return helper.json_file_bytes(outcome), 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("prepare")
    command.add_argument("--repository", required=True)
    command.add_argument("--source-revision", required=True)
    command.add_argument("--output-dir", required=True)
    arguments = parser.parse_args()
    try:
        content, result = prepare(arguments)
    except (ValueError, OSError) as error:
        content = json.dumps(
            _outcome("rejected", diagnostics=[str(error)]),
            sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        ).encode("utf-8") + b"\n"
        result = 2
    sys.stdout.buffer.write(content)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
