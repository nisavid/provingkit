#!/usr/bin/env python3
"""Prepare immutable feedback-response actor requests from one commit."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import types
import uuid


BOOTSTRAP_STORAGE_HELPER_SHA256 = "fa4dc0e5e4c8a8bdf4b55023b5085648122726dc08fb2d0afe16f607ecb8c101"
TOOLS = {
    "controller": "scripts/run_feedback_response_eval.py",
    "constructor": "scripts/validate_feedback_response_evidence.py",
    "storage_helper": "scripts/evidence_transport.py",
    "procedure": "docs/feedback-response-evaluation.md",
}
VARIANTS = ["with_skill", "without_skill"]
CASE_IDS = list(range(13))
REPETITIONS = [1, 2, 3]


class PreparationError(ValueError):
    def __init__(self, code, stage, message, remedy):
        super().__init__(message)
        self.diagnostic = {"code": code, "stage": stage, "message": message, "remedy": remedy}


def display(path):
    return json.dumps(os.fsdecode(path), ensure_ascii=True)


def encoded_path(path):
    return {"encoding": "posix-bytes-hex", "hex": os.fsencode(path).hex()}


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def load_source(content, path, name):
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(content, str(path), "exec"), module.__dict__)
    return module


def read_regular(path):
    parent = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for component in path.parts[1:-1]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent)
            parent = child
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise OSError("expected a regular file")
            content = stream.read()
            after = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_mode) != (
                after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_mode
            ):
                raise OSError("file identity changed")
            return content, before
    finally:
        os.close(parent)


class Preparation:
    def __init__(self, arguments, command):
        self.repository = Path(os.path.abspath(arguments.repository))
        self.output = Path(os.path.abspath(arguments.output_dir))
        self.revision = arguments.source_revision
        self.command = command
        self.stage = "arguments"
        self.record_started = False
        self.export_started = False
        self.invocation_id = None
        self.preparation_id = None
        self.record_relpath = None
        self.record_bytes = None
        self.published = []
        self.reused = []
        self.started_at = timestamp()
        self.helper = None

    def error(self, code, message, remedy="Correct the input and run prepare again."):
        return PreparationError(code, self.stage, message, remedy)

    def git(self, *arguments):
        def failure(message):
            code = "unsafe-git-configuration" if "unsafe candidate Git configuration" in message else "git-operation-failed"
            if "trusted Git executable" in message:
                code = "required-capability-unavailable"
            return self.error(code, "Cannot perform local Git operation " + display(arguments[0]) + ".",
                              "Use locally available objects and the admitted inert Git configuration.")
        return self.helper.run_candidate_git(self.repository, list(arguments),
                                            error_factory=failure, operation="read preparation Git objects")

    def blob(self, oid):
        content = self.git("cat-file", "blob", oid)
        actual = hashlib.new(self.object_format, b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
        if actual != oid:
            raise self.error("git-operation-failed", "A Git blob does not match its object ID.")
        return content

    def tree(self, revision):
        listing = self.git("ls-tree", "-r", "-z", "--full-tree", revision)
        result = {}
        if listing and not listing.endswith(b"\0"):
            raise self.error("git-operation-failed", "The Git tree listing is incomplete.")
        for entry in listing.split(b"\0")[:-1]:
            try:
                metadata, raw_path = entry.split(b"\t", 1)
                mode, kind, oid = metadata.decode("ascii").split(" ")
                if not raw_path or raw_path in result or not re.fullmatch(self.oid_pattern, oid):
                    raise ValueError
                result[raw_path] = {"mode": mode, "kind": kind, "oid": oid}
            except (ValueError, UnicodeDecodeError):
                raise self.error("git-operation-failed", "The Git tree metadata is malformed.") from None
        return result

    def admit_tools(self):
        self.stage = "tool_capture"
        root = Path(os.path.abspath(__file__)).parents[1]
        self.tool_paths = {role: root / path for role, path in TOOLS.items()}
        self.buffers = {}
        for role, path in self.tool_paths.items():
            try:
                self.buffers[role] = read_regular(path)[0]
            except OSError:
                raise self.error("tool-source-unsafe", "Cannot capture regular tool " + display(path) + ".") from None
        self.stage = "tool_bootstrap"
        if hashlib.sha256(self.buffers["storage_helper"]).hexdigest() != BOOTSTRAP_STORAGE_HELPER_SHA256:
            raise self.error("tool-bootstrap-mismatch", "The storage helper does not match its bootstrap pin.",
                             "Commit the helper and its matching controller pin together.")
        self.helper = load_source(self.buffers["storage_helper"], self.tool_paths["storage_helper"], "preparation_storage")
        self.stage = "repository"
        self.object_format = self.git("rev-parse", "--show-object-format").decode("ascii").strip()
        if self.object_format not in {"sha1", "sha256"}:
            raise self.error("required-capability-unavailable", "Unsupported Git object format.")
        self.oid_pattern = "[0-9a-f]{" + str(40 if self.object_format == "sha1" else 64) + "}"
        self.stage = "revision"
        if not re.fullmatch(self.oid_pattern, self.revision):
            raise self.error("revision-not-full-oid", "The revision must be a full lowercase commit OID.",
                             "Pass the full commit ID for this repository's object format.")
        try:
            resolved = self.git("rev-parse", "--verify", "--end-of-options", self.revision + "^{commit}").decode("ascii").strip()
        except PreparationError:
            raise self.error("revision-unresolvable", "The selected commit is unavailable locally.") from None
        if resolved != self.revision:
            raise self.error("revision-unresolvable", "The selected revision does not resolve to itself.")
        self.tree_oid = self.git("rev-parse", "--verify", "--end-of-options", self.revision + "^{tree}").decode("ascii").strip()
        self.entries = self.tree(self.revision)
        self.stage = "tools"
        identities = {}
        for role, path in TOOLS.items():
            entry = self.entries.get(path.encode())
            if entry is None:
                raise self.error("tool-source-missing", "The selected commit lacks tool " + display(path) + ".",
                                 "Select a committed successor containing all required tools and intended inputs.")
            if entry["kind"] != "blob" or entry["mode"] not in {"100644", "100755"}:
                raise self.error("tool-source-unsafe", "Unsafe committed tool " + display(path) + ".")
            content = self.blob(entry["oid"])
            if content != self.buffers[role]:
                raise self.error("tool-source-mismatch", "Running tool differs from selected commit: " + display(path) + ".",
                                 "Commit the modified tool and prepare at that commit.")
            identities[role] = {"path": path, "oid": entry["oid"], "sha256": self.helper.digest_bytes(content)}
        self.constructor = load_source(self.buffers["constructor"], self.tool_paths["constructor"], "preparation_constructor")
        self.binding = {"schema": "provingkit.feedback-response-preparation.binding.v1",
                        "source_commit": self.revision, "object_format": self.object_format, "tools": identities}
        self.preparation_id = hashlib.sha256(self.helper.canonical_bytes(self.binding)).hexdigest()
        self.prefix = f"preparations/{self.preparation_id}"
        self.record_relpath = self.prefix + "/preparation.json"

    def private_directory(self, path, code="unsafe-output-directory"):
        missing = []
        current = path
        while not os.path.lexists(current):
            missing.append(current)
            current = current.parent
        self.helper.prepare_private_directory(path, error_factory=lambda message: self.error(
            code, "Cannot prepare private directory " + display(path) + ".",
            "Use same-user local POSIX directories without symlink components."))
        for directory in {*missing, *(entry.parent for entry in missing), path}:
            self.helper.fsync_directory(directory, error_factory=lambda message: self.error(
                code, "Cannot sync private directory " + display(directory) + "."))

    def admit_output(self):
        self.stage = "repository"
        git_directory = Path(os.fsdecode(self.git("rev-parse", "--absolute-git-dir").removesuffix(b"\n")))
        common_directory = Path(os.fsdecode(self.git("rev-parse", "--path-format=absolute", "--git-common-dir").removesuffix(b"\n")))
        bare = self.git("config", "--bool", "--default", "false", "--get", "core.bare").strip() == b"true"
        protected = [git_directory.resolve(), common_directory.resolve(), *self.tool_paths.values()]
        checkout = None if bare else self.repository.resolve()
        if checkout is not None:
            paths = set(self.entries)
            try:
                head = self.git("rev-parse", "--verify", "--quiet", "HEAD^{commit}").decode("ascii").strip()
            except PreparationError:
                try:
                    reference = os.fsdecode(self.git("symbolic-ref", "--quiet", "HEAD").removesuffix(b"\n"))
                    if not reference.startswith("refs/heads/"):
                        raise ValueError
                    existing_refs = self.git("for-each-ref", "--format=%(refname)", reference).splitlines()
                    if os.fsencode(reference) in existing_refs:
                        raise ValueError
                except (PreparationError, ValueError, UnicodeError):
                    raise self.error("required-capability-unavailable", "Cannot establish current HEAD pathname safety.") from None
            else:
                paths.update(self.tree(head))
            indexed = self.git("ls-files", "--cached", "-z")
            if indexed and not indexed.endswith(b"\0"):
                raise self.error("required-capability-unavailable", "The index pathname inventory is incomplete.")
            paths.update(indexed.split(b"\0")[:-1])
            protected.extend(checkout / os.fsdecode(path) for path in paths)
        self.stage = "tools"
        for name in ("O_NOFOLLOW", "O_DIRECTORY", "fsync", "fchmod", "link", "getuid"):
            if not hasattr(os, name):
                raise self.error("required-capability-unavailable", "Required local POSIX operation is unavailable: " + name + ".")
        write_roots = [self.output / "preparations", self.output / "invocations"]

        def overlaps(first, second):
            return first == second or first.is_relative_to(second) or second.is_relative_to(first)

        for root in write_roots:
            if any(overlaps(root, path) for path in protected):
                raise self.error("unsafe-output-overlap", "Output write root overlaps protected path " + display(root) + ".",
                                 "Choose a private directory with disjoint write roots.")
        for final in [self.output, *write_roots]:
            for directory in [*reversed(final.parents), final]:
                try:
                    metadata = directory.lstat()
                except FileNotFoundError:
                    metadata = None
                except OSError:
                    raise self.error("unsafe-output-directory", "Cannot inspect output directory " + display(directory) + ".") from None
                if metadata is not None and not stat.S_ISDIR(metadata.st_mode):
                    raise self.error("unsafe-output-directory", "Output ancestry contains a symlink or non-directory: " + display(directory) + ".")
                needs_mutation = metadata is None or (directory == final and stat.S_IMODE(metadata.st_mode) != 0o700)
                if directory == final and metadata is not None and metadata.st_uid != os.getuid():
                    raise self.error("unsafe-output-directory", "Output directory has another owner: " + display(directory) + ".")
                if needs_mutation and (any(overlaps(directory, path) for path in protected)
                                       or (checkout is not None and (directory == checkout or checkout.is_relative_to(directory)))):
                    code = "unsafe-output-root-permissions" if directory == self.output and metadata is not None else "unsafe-output-overlap"
                    raise self.error(code, "Output would create or change permissions around a protected path: " + display(directory) + ".",
                                     "Use an already private enclosing root or a disjoint private child.")

    def freeze(self, relative, content, code="artifact-collision"):
        path = self.output / relative
        reused = os.path.lexists(path)
        self.helper.frozen_no_replace_write(path, content, error_factory=lambda message: self.error(
            code, "Cannot retain immutable artifact " + display(relative) + ".",
            "Preserve existing evidence and choose a clean output root for differing artifacts."))
        (self.reused if reused else self.published).append(relative)

    def allocate(self):
        self.stage = "output_directory"
        self.private_directory(self.output)
        self.private_directory(self.output / "invocations")
        self.stage = "invocation_allocation"
        self.invocation_id = uuid.uuid4().hex
        invocation = self.output / "invocations" / self.invocation_id
        try:
            invocation.mkdir(mode=0o700)
        except OSError:
            self.invocation_id = None
            raise self.error("invocation-allocation-failed", "Cannot allocate a fresh invocation directory.") from None
        self.helper.fsync_directory(invocation.parent, error_factory=lambda message: self.error(
            "invocation-allocation-failed", "Cannot sync the new invocation directory entry."))
        started = {"schema": "provingkit.feedback-response-preparation.started.v1",
                   "invocation_id": self.invocation_id, "started_at": self.started_at,
                   "command": [encoded_path(value) for value in self.command],
                   "repository": encoded_path(self.repository), "source_revision": self.revision,
                   "output_dir": encoded_path(self.output), "python_version": sys.version.split()[0],
                   "git_version": self.git("--version").decode("ascii").strip(),
                   "controller_sha256": self.helper.digest_bytes(self.buffers["controller"])}
        self.freeze(f"invocations/{self.invocation_id}/started.json", self.helper.json_file_bytes(started),
                    "invocation-allocation-failed")

    def material_path(self, path):
        try:
            path.encode("utf-8", "strict")
            self.helper.safe_relative_path(path, label="declared input", error_factory=ValueError)
            if "\\" in path or "\0" in path:
                raise ValueError
        except (ValueError, UnicodeError):
            raise self.error("declared-input-unsafe", "Unsafe declared path " + display(path) + ".") from None
        return path

    def inventory(self):
        self.stage = "inventory"
        constructor = self.constructor
        manifest_entry = self.entries.get(constructor.MANIFEST.encode())
        if manifest_entry is None:
            raise self.error("declared-input-missing", "The committed corpus is missing.")
        if manifest_entry["kind"] != "blob" or manifest_entry["mode"] not in {"100644", "100755"}:
            raise self.error("declared-input-unsafe", "The committed corpus is not a regular file.")
        self.corpus_bytes = self.blob(manifest_entry["oid"])
        try:
            corpus = self.helper.strict_json_bytes(self.corpus_bytes, label="corpus", error_factory=ValueError)
            if (not isinstance(corpus, dict) or set(corpus) != {"skill_name", "evals"}
                    or corpus["skill_name"] != "interacting-with-pr-review-feedback"):
                raise ValueError
            cases = corpus["evals"]
            if (not isinstance(cases, list) or len(cases) != 13
                    or any(type(case["id"]) is not int for case in cases)
                    or sorted(case["id"] for case in cases) != CASE_IDS):
                raise ValueError
            for case in cases:
                if (not isinstance(case["prompt"], str) or not isinstance(case["expected_output"], str)
                        or not isinstance(case["files"], list) or not case["files"]
                        or not all(isinstance(path, str) for path in case["files"])
                        or not isinstance(case["expectations"], list)
                        or not all(isinstance(text, str) for text in case["expectations"])):
                    raise ValueError
        except (ValueError, TypeError, KeyError, UnicodeError):
            raise self.error("corpus-shape-mismatch", "The corpus must contain the 13 unique integer cases 0–12.") from None
        self.cases = sorted(cases, key=lambda case: case["id"])
        case_files = sorted({"evals/mergecraft/skills/" + path for case in cases for path in case["files"]})
        declared = set(constructor.CANDIDATE_PATHS) | {constructor.MANIFEST} | set(case_files)
        glob_matches = {}
        for pattern in constructor.SOURCE_GLOBS:
            matches = sorted(os.fsdecode(path) for path in self.entries
                             if PurePosixPath(os.fsdecode(path)).full_match(pattern))
            if not matches:
                raise self.error("declared-input-missing", "No committed input matches " + display(pattern) + ".")
            glob_matches[pattern] = matches
            declared.update(matches)
        self.declaration = {"candidate_paths": list(constructor.CANDIDATE_PATHS), "manifest": constructor.MANIFEST,
                            "case_files": case_files, "source_globs": list(constructor.SOURCE_GLOBS), "glob_matches": glob_matches}
        self.source_entries = {}
        for path in sorted(declared):
            self.material_path(path)
            entry = self.entries.get(path.encode())
            if entry is None:
                raise self.error("declared-input-missing", "Missing committed input " + display(path) + ".")
            if entry["kind"] != "blob" or entry["mode"] not in {"100644", "100755"}:
                raise self.error("declared-input-unsafe", "Committed input is not a regular file: " + display(path) + ".")
            if "__pycache__" in PurePosixPath(path).parts or path.endswith(".pyc"):
                raise self.error("declared-input-unexpected", "Generated input matches a source declaration: " + display(path) + ".")
            self.source_entries[path] = entry

    def source_publish(self, path, content, mode):
        self.private_directory(path.parent, "export-publication-failed")
        parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        temporary = "." + path.name + "." + uuid.uuid4().hex + ".tmp"
        owned_temporary = False
        try:
            def matches():
                try:
                    observed, metadata = read_regular(path)
                except FileNotFoundError:
                    return False
                if observed != content:
                    raise self.error("export-mismatch", "Existing source bytes differ: " + display(path) + ".")
                if stat.S_IMODE(metadata.st_mode) != mode:
                    raise self.error("export-mode-mismatch", "Existing source has the wrong private mode: " + display(path) + ".",
                                     "Preserve the existing export and prepare in a clean output root.")
                descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
                try:
                    opened = os.fstat(descriptor)
                    if (opened.st_dev, opened.st_ino, opened.st_mode) != (metadata.st_dev, metadata.st_ino, metadata.st_mode):
                        raise OSError("source identity drift")
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
                os.fsync(parent)
                return True

            if matches():
                return
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                 0o600, dir_fd=parent)
            owned_temporary = True
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fchmod(stream.fileno(), mode)
                os.fsync(stream.fileno())
            try:
                os.link(temporary, path.name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
                os.fsync(parent)
            except FileExistsError:
                if not matches():
                    raise OSError("publication race")
        except OSError:
            raise self.error("export-publication-failed", "Cannot publish and sync source " + display(path) + ".") from None
        finally:
            try:
                if owned_temporary:
                    os.unlink(temporary, dir_fd=parent)
                    os.fsync(parent)
            finally:
                os.close(parent)

    def export(self):
        self.stage = "export"
        self.export_started = True
        self.source_root = self.output / self.prefix / "source"
        self.source_inventory = {}
        self.artifact_bytes = {}
        for path, entry in self.source_entries.items():
            content = self.blob(entry["oid"])
            relative = self.prefix + "/source/" + path
            final = self.output / relative
            reused = os.path.lexists(final)
            self.source_publish(final, content, 0o700 if entry["mode"] == "100755" else 0o600)
            (self.reused if reused else self.published).append(relative)
            self.artifact_bytes[relative] = content
            self.source_inventory[path] = {"mode": entry["mode"], "oid": entry["oid"],
                                           **self.reference(relative, content)}

    def reference(self, relative, content):
        self.helper.safe_relative_path(relative, label="artifact", error_factory=ValueError)
        return {"relpath": relative, "sha256": self.helper.digest_bytes(content), "byte_count": len(content)}

    def tree_closure(self, root, expected_files, code, label, ignored=()):
        expected_directories = {parent.as_posix() for path in expected_files
                                for parent in PurePosixPath(path).parents if parent.as_posix() != "."}
        found_files = set()
        found_directories = set()

        def walk(descriptor, prefix):
            for name in os.listdir(descriptor):
                if not prefix and name in ignored:
                    continue
                relative = prefix + name
                metadata = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
                if stat.S_ISDIR(metadata.st_mode) and relative in expected_directories:
                    found_directories.add(relative)
                    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
                    try:
                        walk(child, relative + "/")
                        os.fsync(child)
                    finally:
                        os.close(child)
                elif stat.S_ISREG(metadata.st_mode) and relative in expected_files:
                    found_files.add(relative)
                else:
                    raise self.error(code, "Unexpected " + label + " entry " + display(relative) + ".",
                                     "Preserve existing evidence and use a clean output root or separately authorized recovery.")

        try:
            descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                walk(descriptor, "")
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            if found_files != expected_files or found_directories != expected_directories:
                raise self.error(code, "The " + label + " tree does not contain exactly the declared files and ancestors.")
        except OSError:
            raise self.error(code, "Cannot establish exhaustive " + label + "-tree closure.") from None

    def source_closure(self):
        self.tree_closure(self.source_root, set(self.source_entries), "export-closure-mismatch", "source")

    def preparation_closure(self, include_record=False):
        expected_files = {relative.removeprefix(self.prefix + "/") for relative in self.artifact_bytes}
        if include_record:
            expected_files.add("preparation.json")
        self.tree_closure(self.output / self.prefix, expected_files, "artifact-verification-failed", "preparation",
                          ignored=() if include_record else ("preparation.json",))

    def construct(self):
        self.stage = "constructor_verification"
        self.source_closure()
        if self.constructor.source_paths(self.source_root, self.cases) != sorted(self.source_entries):
            raise self.error("constructor-inventory-mismatch", "Constructor source inventory differs from committed declarations.")
        self.stage = "payload_construction"
        self.slots = []
        self.requests = {}
        request_bytes = {}
        for case in self.cases:
            for variant in VARIANTS:
                content = self.constructor.executor_request(self.source_root, case, variant).encode("utf-8")
                request = self.helper.strict_json_bytes(content, label="request", error_factory=ValueError)
                bundle = [self.artifact_bytes[self.prefix + "/source/" + path].decode("utf-8")
                          for path in self.constructor.CANDIDATE_PATHS] if variant == "with_skill" else []
                if set(request) != {"prompt", "fixture", "candidate_bundle"} or request["candidate_bundle"] != bundle:
                    raise self.error("actor-content-policy-violation", "The constructor request violates the actor content policy.")
                digest = self.helper.digest_bytes(content)
                relative = self.prefix + "/requests/" + digest.removeprefix("sha256:") + ".request"
                if digest in request_bytes and request_bytes[digest] != content:
                    raise self.error("artifact-collision", "Distinct requests share a digest address.")
                request_bytes[digest] = content
                self.requests.setdefault(digest, {"relpath": relative, "byte_count": len(content), "slot_count": 0})
                for repetition in REPETITIONS:
                    self.requests[digest]["slot_count"] += 1
                    self.slots.append({"case_id": case["id"], "variant": variant, "repetition": repetition,
                                       "state": "unstarted", "request_sha256": digest, "request_byte_count": len(content),
                                       "request_relpath": relative, "fixture_paths": ["evals/mergecraft/skills/" + name for name in case["files"]],
                                       "candidate_bundle_paths": list(self.constructor.CANDIDATE_PATHS) if variant == "with_skill" else []})
        self.stage = "artifact_publication"
        for digest, content in sorted(request_bytes.items()):
            relative = self.requests[digest]["relpath"]
            self.freeze(relative, content)
            self.artifact_bytes[relative] = content
        grading_constructor = {"path": TOOLS["constructor"], "function": "grading_request",
                               "sha256": self.binding["tools"]["constructor"]["sha256"]}
        grading = {"schema": "provingkit.feedback-response-preparation.grading", "cases": {
            str(case["id"]): {"expected_output": case["expected_output"], "expectations": [
                {"id": f"case-{case['id']}-expectation-{index}", "text": text, "severity": "safety"}
                for index, text in enumerate(case["expectations"], 1)]} for case in self.cases},
                   "grading_constructor": grading_constructor}
        grading_content = self.helper.json_file_bytes(grading)
        grading_relative = self.prefix + "/grading/cases.json"
        self.freeze(grading_relative, grading_content)
        self.artifact_bytes[grading_relative] = grading_content
        self.grading = {**self.reference(grading_relative, grading_content), "constructor": grading_constructor,
                        "requires_at_grading_time": ["response", "response_sha256"]}

    def verify_file(self, relative, content, mode=None):
        path = self.output / relative
        try:
            observed, metadata = read_regular(path)
            if observed != content or (mode is not None and stat.S_IMODE(metadata.st_mode) != mode):
                raise OSError("artifact drift")
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                def identity(status):
                    return (status.st_dev, status.st_ino, status.st_mode, status.st_size,
                            status.st_mtime_ns, status.st_ctime_ns)

                if identity(os.fstat(descriptor)) != identity(metadata):
                    raise OSError("artifact identity drift")
                os.fsync(descriptor)
                if identity(path.lstat()) != identity(metadata):
                    raise OSError("artifact pathname drift")
            finally:
                os.close(descriptor)
            self.helper.fsync_directory(path.parent, error_factory=ValueError)
        except (ValueError, OSError):
            raise self.error("artifact-verification-failed", "Cannot verify and sync artifact " + display(relative) + ".") from None

    def verify(self):
        self.stage = "artifact_verification"
        source_modes = {entry["relpath"]: 0o700 if entry["mode"] == "100755" else 0o600
                        for entry in self.source_inventory.values()}
        directories = {self.output}
        for relative, content in self.artifact_bytes.items():
            self.verify_file(relative, content, source_modes.get(relative))
            parent = (self.output / relative).parent
            while parent != self.output:
                directories.add(parent)
                parent = parent.parent
        for directory in sorted(directories, key=lambda path: len(path.parts), reverse=True):
            self.helper.fsync_directory(directory, error_factory=lambda message: self.error(
                "artifact-verification-failed", "Cannot sync artifact ancestor " + display(directory) + "."))
        self.source_closure()

        self.preparation_closure()

    def publish_record(self):
        record = {"schema": "provingkit.feedback-response-preparation", "schema_version": 1,
                  "preparation_id": self.preparation_id, "binding": self.binding, "tree_oid": self.tree_oid,
                  "source": {"root_relpath": self.prefix + "/source", "declaration": self.declaration,
                             "inventory": self.source_inventory},
                  "corpus": {"path": self.constructor.MANIFEST,
                             "oid": self.entries[self.constructor.MANIFEST.encode()]["oid"],
                             "sha256": self.helper.digest_bytes(self.corpus_bytes),
                             "skill_name": "interacting-with-pr-review-feedback", "case_ids": CASE_IDS},
                  "slots": {"count": 78, "case_ids": CASE_IDS, "variants": VARIANTS, "repetitions": REPETITIONS,
                            "entries": self.slots}, "requests": self.requests, "grading": self.grading,
                  "artifacts": [self.reference(relative, content) for relative, content in sorted(self.artifact_bytes.items())],
                  "actor_content_policy": {"request_fields": ["prompt", "fixture", "candidate_bundle"],
                                           "excluded_from_actor_content": ["source paths", "case labels", "repetition labels", "condition labels", "corpus", "expected outputs", "expectations", "runtime helpers", "grading results", "execution metadata"]},
                  "authority": {"kind": "preparation_only", "claims": [], "excluded": ["actor_execution", "grader_execution", "attempt_reservation", "provider_call", "qualification", "release", "durability_certification"]}}
        self.record_bytes = self.helper.json_file_bytes(record)
        self.stage = "record_publication"
        try:
            existing = read_regular(self.output / self.record_relpath)[0]
        except FileNotFoundError:
            existing = None
        except OSError:
            raise self.error("record-collision", "The existing record path is unsafe or unreadable.") from None
        if existing is not None and existing != self.record_bytes:
            raise self.error("record-collision", "The existing preparation record has different bytes.",
                             "Preserve the record and choose a clean output root.")
        self.record_started = True
        self.freeze(self.record_relpath, self.record_bytes, "record-publication-failed")
        self.stage = "record_verification"
        self.verify_file(self.record_relpath, self.record_bytes)
        self.preparation_closure(include_record=True)

    def run(self):
        if sys.version_info < (3, 13):
            raise self.error("unsupported-runtime", "Python 3.13 or newer is required.")
        self.admit_tools()
        self.admit_output()
        self.allocate()
        self.inventory()
        self.export()
        self.construct()
        self.verify()
        self.publish_record()

    def outcome(self, status, diagnostics):
        observed = bool(self.record_relpath and os.path.lexists(self.output / self.record_relpath))
        return {"schema": "provingkit.feedback-response-preparation.outcome.v1", "invocation_id": self.invocation_id,
                "status": status, "intended_exit_status": {"complete": 0, "rejected": 2}.get(status, 1),
                "started_at": self.started_at, "finished_at": timestamp(), "stage_reached": self.stage,
                "diagnostics": diagnostics, "preparation_id": self.preparation_id,
                "preparation_relpath": self.record_relpath,
                "preparation_sha256": self.helper.digest_bytes(self.record_bytes) if self.record_bytes else None,
                "record_observed": observed, "published_relpaths": self.published, "reused_relpaths": self.reused}


def emit_diagnostics(diagnostics):
    for diagnostic in diagnostics:
        try:
            sys.stderr.write("error: " + diagnostic["code"] + ": " + diagnostic["message"] + " " + diagnostic["remedy"] + "\n")
            sys.stderr.flush()
        except OSError:
            pass


def execute(arguments, command):
    preparation = Preparation(arguments, command)
    status = "complete"
    diagnostics = []
    try:
        preparation.run()
    except PreparationError as error:
        status = "indeterminate" if preparation.record_started else "incomplete" if preparation.export_started else "rejected"
        diagnostics = [error.diagnostic]
    except (OSError, ValueError, KeyError, TypeError, UnicodeError):
        status = "indeterminate" if preparation.record_started else "incomplete" if preparation.export_started else "rejected"
        code = {"export": "export-publication-failed", "constructor_verification": "constructor-inventory-mismatch",
                "payload_construction": "actor-content-policy-violation", "artifact_publication": "artifact-collision",
                "artifact_verification": "artifact-verification-failed", "record_publication": "record-publication-failed",
                "record_verification": "artifact-verification-failed", "invocation_allocation": "invocation-allocation-failed"}.get(
                    preparation.stage, "required-capability-unavailable")
        diagnostics = [preparation.error(code, "The operation failed during " + preparation.stage + ".").diagnostic]
    outcome = preparation.outcome(status, diagnostics)
    content = json.dumps(outcome, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode() + b"\n"
    emit_diagnostics(diagnostics)
    if preparation.invocation_id:
        try:
            preparation.stage = "outcome_publication"
            preparation.freeze(f"invocations/{preparation.invocation_id}/outcome.json", content, "outcome-publication-failed")
        except (PreparationError, OSError):
            outcome = preparation.outcome("indeterminate", [preparation.error("outcome-publication-failed", "Cannot publish the invocation outcome.").diagnostic])
            content = preparation.helper.json_file_bytes(outcome)
            emit_diagnostics(outcome["diagnostics"])
    try:
        sys.stdout.buffer.write(content)
        sys.stdout.buffer.flush()
    except OSError:
        emit_diagnostics([preparation.error("outcome-emission-failed", "Cannot emit the complete outcome document.", "Repeat prepare while capturing its complete stdout and exit status.").diagnostic])
        descriptor = os.open(os.devnull, os.O_WRONLY)
        os.dup2(descriptor, 1)
        os.close(descriptor)
        return 1
    return outcome["intended_exit_status"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser(
        "prepare", description=__doc__,
        epilog=("stdout: one JSON outcome (complete, rejected, incomplete, "
                "indeterminate). Exit codes: 0 complete, 1 unfinished, 2 rejected or usage."),
    )
    prepare.add_argument("--repository", required=True, help="local Git object store")
    prepare.add_argument("--source-revision", required=True, help="full lowercase commit OID")
    prepare.add_argument("--output-dir", required=True, help="private artifact directory")
    arguments = parser.parse_args(argv)
    return execute(arguments, sys.orig_argv if argv is None else [sys.executable, __file__, *argv])


if __name__ == "__main__":
    raise SystemExit(main())
