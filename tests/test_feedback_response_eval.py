import copy
import hashlib
import importlib.util
import json
import marshal
import os
from pathlib import Path, PurePosixPath
import subprocess
import struct
import sys
import tempfile
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_feedback_response_eval.py"
TOOLS = {
    "controller": "scripts/run_feedback_response_eval.py",
    "constructor": "scripts/validate_feedback_response_evidence.py",
    "storage_helper": "scripts/evidence_transport.py",
    "procedure": "docs/feedback-response-evaluation.md",
}
SKILL = "plugins/mergecraft/skills/interacting-with-pr-review-feedback"
MANIFEST = "evals/mergecraft/skills/interacting-with-pr-review-feedback/evals.json"
CANDIDATES = [
    f"{SKILL}/SKILL.md",
    f"{SKILL}/references/interaction-authority.md",
    f"{SKILL}/references/github-markdown-authoring.md",
]


def sha256(content):
    return "sha256:" + hashlib.sha256(content).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def path_bytes(value):
    return {"encoding": "posix-bytes-hex", "hex": os.fsencode(value).hex()}


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.repository = self.directory / "repository"
        self.repository.mkdir()
        self.output = self.directory / "private"
        self.git("init", "-q")
        self.git("config", "user.name", "Fixture Author")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        for path in TOOLS.values():
            self.write(path, (ROOT / path).read_bytes())
        for index, path in enumerate(CANDIDATES):
            self.write(path, f"Candidate {index}: café\n".encode())
        self.cases = [
            {"id": case_id, "prompt": f"Respond to feedback {case_id}.",
             "files": [f"interacting-with-pr-review-feedback/fixtures/case-{case_id}.md"],
             "expected_output": f"Private expected answer {case_id}",
             "expectations": [f"Preserve contract {case_id}."]}
            for case_id in range(13)
        ]
        for case in self.cases:
            self.write("evals/mergecraft/skills/" + case["files"][0],
                       f"Original fixture {case['id']}\n".encode())
        self.write(MANIFEST, canonical({"skill_name": "interacting-with-pr-review-feedback", "evals": self.cases}))
        self.runtime = f"{SKILL}/scripts/runtime.py"
        self.write(self.runtime, b"runtime source\n")
        (self.repository / self.runtime).chmod(0o755)
        for path in [
            "tests/plugins/mergecraft/interacting-with-pr-review-feedback/test_runtime.py",
            "tests/plugins/mergecraft/interacting-with-pr-review-feedback/fixtures/runtime.json",
            "plugins/mergecraft/skills/addressing-pr-review-feedback/scripts/review_feedback_state.py",
            "tests/plugins/mergecraft/addressing-pr-review-feedback/test_state.py",
            "tests/plugins/mergecraft/addressing-pr-review-feedback/fixtures/state.json",
        ]:
            self.write(path, b"support source\n")
        self.revision = self.commit()

    def git(self, *arguments):
        result = subprocess.run(["git", *arguments], cwd=self.repository, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def write(self, relative, content):
        path = self.repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def commit(self):
        self.git("add", "--all")
        self.git("-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixture")
        return self.git("rev-parse", "HEAD").decode().strip()

    def prepare(self, *, output=None, revision=None, repository=None, sink=None, script=None):
        output = output if output is not None else self.output
        repository = repository if repository is not None else self.repository
        arguments = [sys.executable, "-B", str(script or self.repository / TOOLS["controller"]),
                     "prepare", "--repository", os.fspath(repository),
                     "--source-revision", revision if revision is not None else self.revision,
                     "--output-dir", os.fspath(output)]
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        environment.pop("PYTHONPYCACHEPREFIX", None)
        result = subprocess.run(arguments, env=environment, stdout=sink or subprocess.PIPE,
                                stderr=subprocess.PIPE, cwd=self.directory, timeout=60)
        evidence = {"argv": [path_bytes(value) for value in arguments],
                    "returncode": result.returncode,
                    "stdout_sha256": sha256(result.stdout) if result.stdout is not None else None,
                    "stdout_byte_count": len(result.stdout) if result.stdout is not None else None,
                    "stderr_sha256": sha256(result.stderr), "stderr_byte_count": len(result.stderr),
                    "observed_by": "unittest subprocess invoker"}
        if sink is not None:
            evidence["stdout_capture"] = "unavailable"
            evidence["sink"] = "caller-supplied non-captured sink"
        evidence_directory = self.directory / f"process-{len(list(self.directory.glob('process-*')))}"
        evidence_directory.mkdir()
        (evidence_directory / "process-result.json").write_bytes(canonical(evidence) + b"\n")
        (evidence_directory / "stderr").write_bytes(result.stderr)
        if result.stdout is not None:
            (evidence_directory / "stdout").write_bytes(result.stdout)
        return result

    def verify_preparation(self, record, output=None, repository=None, revision=None, complete=True):
        output = output or self.output
        repository = repository or self.repository
        revision = revision or self.revision
        self.assertFalse(output.is_symlink())

        def git(*arguments):
            return subprocess.check_output(["git", *arguments], cwd=repository)

        committed = {}
        for raw_entry in git("ls-tree", "-r", "-z", "--full-tree", revision).split(b"\0"):
            if raw_entry:
                metadata, raw_path = raw_entry.split(b"\t", 1)
                mode, kind, oid = metadata.decode("ascii").split(" ")
                committed[os.fsdecode(raw_path)] = (mode, kind, oid)

        def blob(relative):
            mode, kind, oid = committed[relative]
            self.assertEqual(kind, "blob")
            self.assertIn(mode, ("100644", "100755"))
            return git("cat-file", "blob", oid)

        def reference(relative, content):
            return {"relpath": relative, "sha256": sha256(content), "byte_count": len(content)}

        tools = {role: {"path": path, "oid": committed[path][2], "sha256": sha256(blob(path))}
                 for role, path in TOOLS.items()}
        binding = {"schema": "provingkit.feedback-response-preparation.binding.v1", "source_commit": revision,
                   "object_format": git("rev-parse", "--show-object-format").decode().strip(), "tools": tools}
        preparation_id = hashlib.sha256(canonical(binding)).hexdigest()
        prefix = "preparations/" + preparation_id
        constructor = types.ModuleType("independent_committed_constructor")
        exec(compile(blob(TOOLS["constructor"]), "independent-committed-constructor", "exec"), constructor.__dict__)
        self.assertEqual(list(constructor.CANDIDATE_PATHS), CANDIDATES)
        self.assertEqual(constructor.MANIFEST, MANIFEST)
        corpus_bytes = blob(MANIFEST)
        corpus = json.loads(corpus_bytes)
        cases = sorted(corpus["evals"], key=lambda case: case["id"])
        self.assertEqual([case["id"] for case in cases], list(range(13)))
        self.assertTrue(all(type(case["id"]) is int for case in cases))
        case_files = sorted({"evals/mergecraft/skills/" + name for case in cases for name in case["files"]})
        glob_matches = {pattern: sorted(path for path in committed if PurePosixPath(path).full_match(pattern))
                        for pattern in constructor.SOURCE_GLOBS}
        self.assertTrue(all(glob_matches.values()))
        declared = set(CANDIDATES) | {MANIFEST} | set(case_files)
        for matches in glob_matches.values():
            declared.update(matches)
        material = {}
        for relative in sorted(declared):
            path = PurePosixPath(relative)
            relative.encode("utf-8", "strict")
            self.assertFalse(path.is_absolute())
            self.assertEqual(path.as_posix(), relative)
            self.assertNotIn("..", path.parts)
            self.assertNotIn("\\", relative)
            self.assertNotIn("__pycache__", path.parts)
            self.assertNotEqual(path.suffix, ".pyc")
            material[relative] = blob(relative)
        artifact_bytes = {prefix + "/source/" + path: content for path, content in material.items()}
        source_inventory = {path: {"mode": committed[path][0], "oid": committed[path][2],
                                   **reference(prefix + "/source/" + path, content)}
                            for path, content in material.items()}
        slots = []
        requests = {}
        with tempfile.TemporaryDirectory(dir=self.directory) as directory:
            oracle = Path(directory)
            for relative, content in material.items():
                path = oracle / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            self.assertEqual(constructor.source_paths(oracle, cases), sorted(declared))
            for case in cases:
                for variant in ("with_skill", "without_skill"):
                    content = constructor.executor_request(oracle, case, variant).encode("utf-8")
                    digest = sha256(content)
                    relative = prefix + "/requests/" + digest.removeprefix("sha256:") + ".request"
                    if relative in artifact_bytes:
                        self.assertEqual(artifact_bytes[relative], content)
                    artifact_bytes[relative] = content
                    request = requests.setdefault(digest, {"relpath": relative, "byte_count": len(content), "slot_count": 0})
                    for repetition in (1, 2, 3):
                        request["slot_count"] += 1
                        slots.append({"case_id": case["id"], "variant": variant, "repetition": repetition,
                                      "state": "unstarted", "request_sha256": digest, "request_byte_count": len(content),
                                      "request_relpath": relative,
                                      "fixture_paths": ["evals/mergecraft/skills/" + name for name in case["files"]],
                                      "candidate_bundle_paths": CANDIDATES if variant == "with_skill" else []})
        grading_constructor = {"path": TOOLS["constructor"], "function": "grading_request",
                               "sha256": tools["constructor"]["sha256"]}
        grading_document = {"schema": "provingkit.feedback-response-preparation.grading", "cases": {
            str(case["id"]): {"expected_output": case["expected_output"], "expectations": [
                {"id": f"case-{case['id']}-expectation-{index}", "text": text, "severity": "safety"}
                for index, text in enumerate(case["expectations"], 1)]} for case in cases},
                            "grading_constructor": grading_constructor}
        grading_bytes = canonical(grading_document) + b"\n"
        grading_relative = prefix + "/grading/cases.json"
        artifact_bytes[grading_relative] = grading_bytes
        expected = {"schema": "provingkit.feedback-response-preparation", "schema_version": 1,
                    "preparation_id": preparation_id, "binding": binding,
                    "tree_oid": git("rev-parse", revision + "^{tree}").decode().strip(),
                    "source": {"root_relpath": prefix + "/source", "declaration": {
                        "candidate_paths": CANDIDATES, "manifest": MANIFEST, "case_files": case_files,
                        "source_globs": list(constructor.SOURCE_GLOBS), "glob_matches": glob_matches}, "inventory": source_inventory},
                    "corpus": {"path": MANIFEST, "oid": committed[MANIFEST][2], "sha256": sha256(corpus_bytes),
                               "skill_name": corpus["skill_name"], "case_ids": list(range(13))},
                    "slots": {"count": 78, "case_ids": list(range(13)), "variants": ["with_skill", "without_skill"],
                              "repetitions": [1, 2, 3], "entries": slots}, "requests": requests,
                    "grading": {**reference(grading_relative, grading_bytes), "constructor": grading_constructor,
                                "requires_at_grading_time": ["response", "response_sha256"]},
                    "artifacts": [reference(path, content) for path, content in sorted(artifact_bytes.items())],
                    "actor_content_policy": {"request_fields": ["prompt", "fixture", "candidate_bundle"],
                                             "excluded_from_actor_content": ["source paths", "case labels", "repetition labels", "condition labels", "corpus", "expected outputs", "expectations", "runtime helpers", "grading results", "execution metadata"]},
                    "authority": {"kind": "preparation_only", "claims": [], "excluded": ["actor_execution", "grader_execution", "attempt_reservation", "provider_call", "qualification", "release", "durability_certification"]}}
        self.assertEqual(canonical(record), canonical(expected))
        for relative, content in artifact_bytes.items():
            path = output
            for part in PurePosixPath(relative).parts:
                path /= part
                self.assertFalse(path.is_symlink())
            self.assertTrue(path.is_file())
            self.assertEqual(path.read_bytes(), content)
        for entry in source_inventory.values():
            self.assertEqual((output / entry["relpath"]).stat().st_mode & 0o777,
                             0o700 if entry["mode"] == "100755" else 0o600)
        if complete:
            record_relative = prefix + "/preparation.json"
            record_path = output / record_relative
            self.assertFalse(record_path.is_symlink())
            self.assertTrue(record_path.is_file())
            self.assertEqual(record_path.read_bytes(), canonical(expected) + b"\n")
            expected_files = set(artifact_bytes) | {record_relative}
            expected_directories = {parent.as_posix() for path in expected_files for parent in PurePosixPath(path).parents
                                    if parent.as_posix().startswith(prefix + "/")}
            actual_files, actual_directories = set(), set()
            for directory, directories, files in os.walk(output / prefix, followlinks=False):
                for name in directories:
                    path = Path(directory) / name
                    self.assertFalse(path.is_symlink())
                    actual_directories.add(path.relative_to(output).as_posix())
                for name in files:
                    path = Path(directory) / name
                    self.assertFalse(path.is_symlink())
                    self.assertTrue(path.is_file())
                    actual_files.add(path.relative_to(output).as_posix())
            self.assertEqual(actual_files, expected_files)
            self.assertEqual(actual_directories, expected_directories)

    def test_source_metadata_verification_rejects_oid_and_mode_only_drift(self):
        _, record = self.completed(self.prepare())
        self.verify_preparation(record)
        changed_oid = copy.deepcopy(record)
        changed_oid["source"]["inventory"][self.runtime]["oid"] = "0" * 40
        with self.assertRaises(AssertionError):
            self.verify_preparation(changed_oid)
        changed_mode = copy.deepcopy(record)
        changed_mode["source"]["inventory"][self.runtime]["mode"] = "100644"
        exported = self.output / record["source"]["inventory"][self.runtime]["relpath"]
        exported.chmod(0o600)
        with self.assertRaises(AssertionError):
            self.verify_preparation(changed_mode)

    def test_baseline_prepares_every_coordinate_and_verifiable_artifact(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, b"")
        outcome = json.loads(result.stdout)
        self.assertEqual(outcome["status"], "complete")
        invocation = self.output / "invocations" / outcome["invocation_id"]
        self.assertEqual((invocation / "outcome.json").read_bytes(), result.stdout)
        self.assertLessEqual((invocation / "started.json").stat().st_mtime_ns,
                             (invocation / "outcome.json").stat().st_mtime_ns)
        record_bytes = (self.output / outcome["preparation_relpath"]).read_bytes()
        self.assertEqual(sha256(record_bytes), outcome["preparation_sha256"])
        record = json.loads(record_bytes)
        self.assertEqual(hashlib.sha256(canonical(record["binding"])).hexdigest(), record["preparation_id"])
        self.assertEqual(record["binding"]["source_commit"], self.revision)
        self.assertEqual(record["tree_oid"], self.git("rev-parse", self.revision + "^{tree}").decode().strip())
        self.verify_preparation(record)

    def completed(self, result, output=None):
        self.assertEqual(result.returncode, 0, result.stderr)
        outcome = json.loads(result.stdout)
        self.assertEqual(outcome["status"], "complete")
        return outcome, json.loads(((output or self.output) / outcome["preparation_relpath"]).read_bytes())

    def failure(self, result, status, code):
        self.assertEqual(result.returncode, 2 if status == "rejected" else 1, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["status"], status)
        self.assertIn(code, [entry["code"] for entry in document["diagnostics"]])
        self.assertNotIn(b"Traceback", result.stderr)
        return document

    def test_reuse_preserves_files_and_rejects_same_bytes_in_wrong_mode(self):
        first, record = self.completed(self.prepare())
        paths = [self.output / entry["relpath"] for entry in record["artifacts"]] + [self.output / first["preparation_relpath"]]
        identities = {path: (path.stat().st_ino, path.stat().st_mode, path.read_bytes()) for path in paths}
        second, second_record = self.completed(self.prepare())
        self.assertEqual(record, second_record)
        self.verify_preparation(second_record)
        self.assertTrue({entry["relpath"] for entry in record["artifacts"]} <= set(second["reused_relpaths"]))
        self.assertEqual({path: (path.stat().st_ino, path.stat().st_mode, path.read_bytes()) for path in paths}, identities)
        target = self.output / record["source"]["inventory"][self.runtime]["relpath"]
        target.chmod(0o600)
        before = (target.stat().st_ino, target.stat().st_mtime_ns, target.read_bytes())
        self.failure(self.prepare(), "incomplete", "export-mode-mismatch")
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        self.assertEqual((target.stat().st_ino, target.stat().st_mtime_ns, target.read_bytes()), before)
        self.assertEqual((self.output / first["preparation_relpath"]).read_bytes(), canonical(record) + b"\n")

    def test_unexpected_export_entries_are_preserved_and_prevent_completion(self):
        outcome, record = self.completed(self.prepare())
        sentinel = self.directory / "sentinel"
        sentinel.write_bytes(b"untouched")
        sibling = "plugins/mergecraft/skills/addressing-pr-review-feedback/scripts/earlier-publication.tmp"
        for kind in ("temporary", "empty-directory", "symlink"):
            with self.subTest(kind=kind):
                output = self.directory / kind
                target = output / "preparations" / record["preparation_id"] / "source" / sibling
                target.parent.mkdir(parents=True)
                if kind == "temporary":
                    target.write_bytes(b"support")
                    target.chmod(0o600)
                elif kind == "empty-directory":
                    target.mkdir()
                else:
                    target.symlink_to(sentinel)
                self.failure(self.prepare(output=output), "incomplete", "export-closure-mismatch")
                self.assertFalse((output / outcome["preparation_relpath"]).exists())
                self.assertEqual(sentinel.read_bytes(), b"untouched")
                if kind == "temporary":
                    self.assertEqual(target.read_bytes(), b"support")
                    self.assertEqual(target.stat().st_mode & 0o777, 0o600)
                elif kind == "empty-directory":
                    self.assertTrue(target.is_dir())
                else:
                    self.assertTrue(target.is_symlink())

    def test_preparation_publication_remnants_are_preserved_and_prevent_completion(self):
        outcome, record = self.completed(self.prepare())
        for index, relative in enumerate(("requests/.earlier-request.tmp", "grading/.earlier-grading.tmp", ".earlier-record.tmp")):
            for reuse in (False, True):
                with self.subTest(relative=relative, reuse=reuse):
                    output = self.directory / f"publication-remnant-{index}-{reuse}"
                    record_path = output / outcome["preparation_relpath"]
                    if reuse:
                        self.completed(self.prepare(output=output), output)
                        original_record = record_path.read_bytes()
                    target = output / "preparations" / record["preparation_id"] / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(b"interruption-compatible retained bytes")
                    before = (target.stat().st_ino, target.stat().st_mode, target.stat().st_mtime_ns)
                    self.failure(self.prepare(output=output), "incomplete", "artifact-verification-failed")
                    if reuse:
                        self.assertEqual(record_path.read_bytes(), original_record)
                    else:
                        self.assertFalse(record_path.exists())
                    self.assertEqual(target.read_bytes(), b"interruption-compatible retained bytes")
                    self.assertEqual((target.stat().st_ino, target.stat().st_mode, target.stat().st_mtime_ns), before)
                    self.verify_preparation(record, output, complete=False)

    def test_output_safety_checks_selected_head_and_index_paths_before_mutation(self):
        private = self.repository / "private"
        private.mkdir(mode=0o700)
        invocations = private / "invocations"
        invocations.mkdir(mode=0o755)
        sentinel = invocations / "sentinel"
        sentinel.write_bytes(b"current checkout only")
        self.git("add", "private/invocations/sentinel")
        before_index = self.git("ls-files", "--stage", "-z")
        self.failure(self.prepare(output=private), "rejected", "unsafe-output-overlap")
        self.assertEqual(before_index, self.git("ls-files", "--stage", "-z"))
        self.assertEqual(invocations.stat().st_mode & 0o777, 0o755)
        self.assertEqual(sentinel.read_bytes(), b"current checkout only")
        self.commit()
        self.git("rm", "--cached", "private/invocations/sentinel")
        self.failure(self.prepare(output=private), "rejected", "unsafe-output-overlap")
        self.assertEqual(invocations.stat().st_mode & 0o777, 0o755)
        self.assertEqual(sentinel.read_bytes(), b"current checkout only")

    def test_safe_roots_and_unsafe_roots_preserve_existing_state(self):
        self.completed(self.prepare(output=self.repository / "safe-private"), self.repository / "safe-private")
        self.repository.chmod(0o755)
        self.failure(self.prepare(output=self.repository), "rejected", "unsafe-output-root-permissions")
        self.assertEqual(self.repository.stat().st_mode & 0o777, 0o755)
        self.failure(self.prepare(output=self.repository / ".git" / "private"), "rejected", "unsafe-output-overlap")
        self.assertFalse((self.repository / ".git/private").exists())
        sentinel = self.directory / "sentinel-dir"
        sentinel.mkdir(mode=0o755)
        link = self.directory / "link"
        link.symlink_to(sentinel, target_is_directory=True)
        self.failure(self.prepare(output=link / "private"), "rejected", "unsafe-output-directory")
        self.assertEqual(list(sentinel.iterdir()), [])
        self.assertEqual(sentinel.stat().st_mode & 0o777, 0o755)
        self.repository.chmod(0o700)
        self.completed(self.prepare(output=self.repository), self.repository)

    def test_collisions_preserve_artifacts_and_record_and_report_incomplete(self):
        first_result = self.prepare()
        outcome, record = self.completed(first_result)
        record_path = self.output / outcome["preparation_relpath"]
        original_record = record_path.read_bytes()
        request = self.output / next(iter(record["requests"].values()))["relpath"]
        original_request = request.read_bytes()
        request.write_bytes(b"existing differing request")
        before = request.stat().st_mtime_ns
        self.failure(self.prepare(), "incomplete", "artifact-collision")
        self.assertEqual(request.read_bytes(), b"existing differing request")
        self.assertEqual(request.stat().st_mtime_ns, before)
        self.assertEqual(record_path.read_bytes(), original_record)
        self.assertEqual(self.consumer_status(first_result, outcome["invocation_id"]), "indeterminate")
        request.write_bytes(original_request)
        record_path.write_bytes(b"existing differing record")
        self.failure(self.prepare(), "incomplete", "record-collision")
        self.assertEqual(record_path.read_bytes(), b"existing differing record")
        for kind in ("record", "grading"):
            with self.subTest(kind=kind):
                output = self.directory / (kind + "-collision")
                relative = outcome["preparation_relpath"] if kind == "record" else record["grading"]["relpath"]
                target = output / relative
                target.mkdir(parents=True)
                self.failure(self.prepare(output=output), "incomplete", "record-collision" if kind == "record" else "artifact-collision")
                self.assertTrue(target.is_dir())
                self.assertFalse(any(target.iterdir()))
                if kind == "record":
                    self.verify_preparation(record, output, complete=False)

    def test_revision_and_declared_input_admission(self):
        for revision in (self.revision[:12], "HEAD", "fixture-tag"):
            with self.subTest(revision=revision):
                self.failure(self.prepare(revision=revision), "rejected", "revision-not-full-oid")
                self.assertFalse((self.output / "preparations").exists())
        path = self.repository / self.runtime
        path.unlink()
        path.symlink_to("other.py")
        self.revision = self.commit()
        self.failure(self.prepare(), "rejected", "declared-input-unsafe")
        path.unlink()
        self.revision = self.commit()
        self.failure(self.prepare(), "rejected", "declared-input-missing")
        self.write(self.runtime, b"runtime restored")
        self.write("tests/plugins/mergecraft/addressing-pr-review-feedback/fixtures/__pycache__/x.pyc", b"cached")
        self.revision = self.commit()
        self.failure(self.prepare(), "rejected", "declared-input-unexpected")

    def test_tool_and_corpus_admission_uses_one_commit(self):
        procedure = self.repository / TOOLS["procedure"]
        content = procedure.read_bytes()
        procedure.unlink()
        self.revision = self.commit()
        procedure.write_bytes(content)
        self.failure(self.prepare(), "rejected", "tool-source-missing")
        self.write(MANIFEST, canonical({"skill_name": "interacting-with-pr-review-feedback", "evals": self.cases[:12]}))
        self.revision = self.commit()
        self.failure(self.prepare(), "rejected", "corpus-shape-mismatch")

    def test_working_tree_and_untracked_content_cannot_supply_inputs(self):
        original = (self.repository / CANDIDATES[0]).read_bytes()
        self.write(CANDIDATES[0], b"uncommitted material")
        untracked = f"{SKILL}/scripts/untracked.py"
        self.write(untracked, b"untracked material")
        constructor = self.repository / TOOLS["constructor"]
        constructor_bytes = constructor.read_bytes()
        constructor.write_bytes(constructor_bytes + b"\n")
        self.failure(self.prepare(), "rejected", "tool-source-mismatch")
        constructor.write_bytes(constructor_bytes)
        outcome, record = self.completed(self.prepare())
        self.assertNotIn(untracked, record["source"]["inventory"])
        self.assertEqual((self.output / record["source"]["inventory"][CANDIDATES[0]]["relpath"]).read_bytes(), original)
        self.assertTrue(outcome["record_observed"])

    def verify_changed_inventory_reuse_and_collision(self, result, outcome, record):
        paths = [self.output / entry["relpath"] for entry in record["artifacts"]]
        record_path = self.output / outcome["preparation_relpath"]
        paths.append(record_path)
        identities = {path: (path.stat().st_ino, path.stat().st_mode, path.read_bytes()) for path in paths}
        reused, reused_record = self.completed(self.prepare())
        self.assertEqual(reused_record, record)
        self.verify_preparation(reused_record)
        self.assertTrue({entry["relpath"] for entry in record["artifacts"]} <= set(reused["reused_relpaths"]))
        self.assertEqual({path: (path.stat().st_ino, path.stat().st_mode, path.read_bytes()) for path in paths}, identities)
        target = self.output / next(iter(record["requests"].values()))["relpath"]
        record_bytes = record_path.read_bytes()
        target.write_bytes(b"conflicting changed-inventory request")
        modified_at = target.stat().st_mtime_ns
        self.failure(self.prepare(), "incomplete", "artifact-collision")
        self.assertEqual(target.read_bytes(), b"conflicting changed-inventory request")
        self.assertEqual(target.stat().st_mtime_ns, modified_at)
        self.assertEqual(record_path.read_bytes(), record_bytes)
        self.assertEqual(self.consumer_status(result, outcome["invocation_id"]), "indeterminate")

    def test_added_glob_match_grows_the_complete_derived_inventory(self):
        _, baseline = self.completed(self.prepare())
        self.write(f"{SKILL}/scripts/additional.py", b"additional source")
        self.revision = self.commit()
        result = self.prepare()
        outcome, record = self.completed(result)
        self.assertEqual(len(record["source"]["inventory"]), len(baseline["source"]["inventory"]) + 1)
        self.assertEqual(set(record["requests"]), set(baseline["requests"]))
        self.verify_preparation(record)
        self.verify_changed_inventory_reuse_and_collision(result, outcome, record)

    def test_identical_requests_preserve_all_coordinates_with_one_artifact_per_byte_string(self):
        for case in self.cases:
            case["prompt"] = "Shared prompt."
            case["files"] = self.cases[0]["files"]
        self.write(MANIFEST, canonical({"skill_name": "interacting-with-pr-review-feedback", "evals": self.cases}))
        self.revision = self.commit()
        result = self.prepare()
        outcome, record = self.completed(result)
        self.assertEqual(len(record["requests"]), 2)
        self.assertEqual([entry["slot_count"] for entry in record["requests"].values()], [39, 39])
        self.assertEqual(len(record["slots"]["entries"]), 78)
        self.verify_preparation(record)
        self.verify_changed_inventory_reuse_and_collision(result, outcome, record)

    def test_captured_source_excludes_timestamp_and_unchecked_hash_caches(self):
        marker = self.directory / "cached-code-ran"
        for cache_kind in ("timestamp", "unchecked-hash"):
            with self.subTest(cache_kind=cache_kind):
                for role in ("constructor", "storage_helper"):
                    source = self.repository / TOOLS[role]
                    content = source.read_bytes()
                    code = compile(f"from pathlib import Path\nPath({str(marker)!r}).write_text('ran')\nraise RuntimeError('cached marker')\n", str(source), "exec")
                    if cache_kind == "timestamp":
                        header = importlib.util.MAGIC_NUMBER + struct.pack("<III", 0, int(source.stat().st_mtime), len(content))
                    else:
                        header = importlib.util.MAGIC_NUMBER + struct.pack("<I", 1) + importlib.util.source_hash(content)
                    cache = source.parent / "__pycache__" / f"{source.stem}.{sys.implementation.cache_tag}.pyc"
                    cache.parent.mkdir(exist_ok=True)
                    cache.write_bytes(header + marshal.dumps(code))
                _, record = self.completed(self.prepare())
                self.verify_preparation(record)
                self.assertFalse(marker.exists())
        helper = self.repository / TOOLS["storage_helper"]
        helper.write_bytes(f"from pathlib import Path\nPath({str(marker)!r}).write_text('ran')\n".encode() + helper.read_bytes())
        self.failure(self.prepare(), "rejected", "tool-bootstrap-mismatch")
        self.assertFalse(marker.exists())

    def test_bare_store_has_the_same_material_identity(self):
        _, checkout_record = self.completed(self.prepare())
        bare = self.directory / "bare.git"
        self.git("clone", "--bare", "--quiet", str(self.repository), str(bare))
        output = self.directory / "bare-output"
        _, bare_record = self.completed(self.prepare(repository=bare, output=output), output)
        self.assertEqual(checkout_record, bare_record)
        self.verify_preparation(bare_record, output)
        self.failure(self.prepare(repository=bare, output=bare / "private"), "rejected", "unsafe-output-overlap")

    def test_checkout_with_unset_optional_bare_config_remains_eligible(self):
        _, control = self.completed(self.prepare())
        self.git("config", "--unset", "core.bare")
        output = self.directory / "unset-bare-output"
        _, record = self.completed(self.prepare(output=output), output)
        self.assertEqual(record, control)
        self.verify_preparation(record, output)
        self.failure(self.prepare(output=self.repository / ".git/private"), "rejected", "unsafe-output-overlap")

    def test_unborn_head_names_are_lossless_and_metadata_failures_reject(self):
        _, control = self.completed(self.prepare())
        original_index = self.git("ls-files", "--stage", "-z")
        for index, branch in enumerate(("unborn", "café", os.fsdecode(b"unborn-\xff"))):
            with self.subTest(branch=branch):
                self.git("symbolic-ref", "HEAD", "refs/heads/" + branch)
                head_bytes = (self.repository / ".git/HEAD").read_bytes()
                output = self.directory / f"unborn-output-{index}"
                _, record = self.completed(self.prepare(output=output), output)
                self.assertEqual(record, control)
                self.verify_preparation(record, output)
                self.assertEqual((self.repository / ".git/HEAD").read_bytes(), head_bytes)
                self.assertEqual(self.git("ls-files", "--stage", "-z"), original_index)
        (self.repository / ".git/HEAD").write_bytes(b"invalid HEAD metadata\n")
        rejected_output = self.directory / "invalid-head-output"
        result = self.prepare(output=rejected_output)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "rejected")
        self.assertFalse(rejected_output.exists())

    def test_unborn_head_is_distinct_from_prefix_neighbors_and_present_invalid_targets(self):
        _, control = self.completed(self.prepare())
        for index, branch in enumerate(("unborn-parent", "café-parent", os.fsdecode(b"unborn-parent-\xff"))):
            with self.subTest(branch=branch):
                self.git("branch", branch + "/child", self.revision)
                self.git("symbolic-ref", "HEAD", "refs/heads/" + branch)
                output = self.directory / f"prefix-output-{index}"
                _, record = self.completed(self.prepare(output=output), output)
                self.assertEqual(record, control)
                self.verify_preparation(record, output)
        blob_oid = self.git("rev-parse", self.revision + ":" + CANDIDATES[0]).strip()
        target = self.repository / ".git/refs/heads/present-invalid"
        target.write_bytes(blob_oid + b"\n")
        self.git("symbolic-ref", "HEAD", "refs/heads/present-invalid")
        rejected_output = self.directory / "present-invalid-output"
        self.failure(self.prepare(output=rejected_output), "rejected", "required-capability-unavailable")
        self.assertFalse(rejected_output.exists())
        self.assertEqual(target.read_bytes(), blob_oid + b"\n")

    def test_lossless_source_selection_and_unicode_material(self):
        _, baseline = self.completed(self.prepare())
        unrelated = os.fsdecode(b"unrelated-\xff")
        self.write(unrelated, b"unrelated")
        self.revision = self.commit()
        _, record = self.completed(self.prepare())
        self.assertEqual(set(record["source"]["inventory"]), set(baseline["source"]["inventory"]))
        self.assertEqual(set(record["requests"]), set(baseline["requests"]))
        self.verify_preparation(record)
        self.write(f"{SKILL}/scripts/café.py", b"unicode source")
        self.revision = self.commit()
        _, unicode_record = self.completed(self.prepare())
        self.assertIn(f"{SKILL}/scripts/café.py", unicode_record["source"]["inventory"])
        self.verify_preparation(unicode_record)
        self.write(f"{SKILL}/scripts/" + os.fsdecode(b"bad-\xff.py"), b"selected invalid encoding")
        self.revision = self.commit()
        self.failure(self.prepare(), "rejected", "declared-input-unsafe")

    def test_byte_named_output_and_invocation_metadata_round_trip(self):
        _, baseline = self.completed(self.prepare())
        for name in ("unicode-é", os.fsdecode(b"private-\xff")):
            with self.subTest(name=name):
                output = self.directory / name
                outcome, record = self.completed(self.prepare(output=output), output)
                self.assertEqual(record, baseline)
                started = json.loads((output / "invocations" / outcome["invocation_id"] / "started.json").read_bytes())
                self.assertEqual(started["output_dir"], path_bytes(output))
                self.assertEqual(started["repository"], path_bytes(self.repository))
                self.assertIn(path_bytes("-B"), started["command"])
                self.assertEqual(started["command"][-1], path_bytes(output))
        unsafe = self.directory / os.fsdecode(b"unsafe-\xfe")
        sentinel = self.directory / "byte-sentinel"
        sentinel.mkdir()
        unsafe.symlink_to(sentinel, target_is_directory=True)
        rejected = self.failure(self.prepare(output=unsafe), "rejected", "unsafe-output-directory")
        self.assertIn(json.dumps(os.fspath(unsafe), ensure_ascii=True), rejected["diagnostics"][0]["message"])

    def test_raw_paths_in_current_head_index_and_selected_tree_protect_output(self):
        private = self.repository / "private"
        private.mkdir(mode=0o700)
        invocations = private / "invocations"
        invocations.mkdir(mode=0o755)
        relative = "private/invocations/" + os.fsdecode(b"sentinel-\xff")
        self.write(relative, b"raw tracked sentinel")
        self.git("add", "--all")
        self.failure(self.prepare(output=private), "rejected", "unsafe-output-overlap")
        self.commit()
        self.failure(self.prepare(output=private), "rejected", "unsafe-output-overlap")
        self.git("rm", "--cached", "--", relative)
        self.failure(self.prepare(output=private), "rejected", "unsafe-output-overlap")
        self.assertEqual(invocations.stat().st_mode & 0o777, 0o755)
        self.assertEqual((self.repository / relative).read_bytes(), b"raw tracked sentinel")
        isolated = self.repository / "selected-private"
        isolated.mkdir(mode=0o700)
        preparations = isolated / "preparations"
        preparations.mkdir(mode=0o755)
        other = "selected-private/preparations/" + os.fsdecode(b"selected-\xff")
        self.write(other, b"selected raw sentinel")
        self.revision = self.commit()
        before_head = self.git("rev-parse", "HEAD")
        before_index = self.git("ls-files", "--stage", "-z")
        self.failure(self.prepare(output=isolated), "rejected", "unsafe-output-overlap")
        self.assertEqual(self.git("rev-parse", "HEAD"), before_head)
        self.assertEqual(self.git("ls-files", "--stage", "-z"), before_index)
        self.assertEqual(preparations.stat().st_mode & 0o777, 0o755)
        self.assertEqual((self.repository / other).read_bytes(), b"selected raw sentinel")
        self.assertFalse((isolated / "invocations").exists())

    def test_real_committed_corpus_uses_the_bound_constructor(self):
        real_revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
        required = [*TOOLS.values(), *CANDIDATES, MANIFEST]
        for path in required:
            exists = subprocess.run(["git", "cat-file", "-e", real_revision + ":" + path], cwd=ROOT, capture_output=True)
            if exists.returncode != 0:
                self.skipTest("required declared path absent from repository HEAD: " + path)
        result = self.prepare(repository=ROOT, revision=real_revision, script=SCRIPT)
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads((self.output / json.loads(result.stdout)["preparation_relpath"]).read_bytes())
        self.verify_preparation(record, repository=ROOT, revision=real_revision)

    def consumer_status(self, result, invocation_id):
        try:
            invocation = self.output / "invocations" / invocation_id
            started_bytes = (invocation / "started.json").read_bytes()
            outcome_bytes = (invocation / "outcome.json").read_bytes()
            started = json.loads(started_bytes)
            outcome = json.loads(outcome_bytes)
            self.assertIsNotNone(result)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, outcome_bytes)
            self.assertEqual(started["invocation_id"], invocation_id)
            self.assertEqual(outcome["status"], "complete")
            self.assertEqual(started["schema"], "provingkit.feedback-response-preparation.started.v1")
            self.assertEqual(outcome["schema"], "provingkit.feedback-response-preparation.outcome.v1")
            preparation_id = outcome["preparation_id"]
            self.assertEqual(len(preparation_id), 64)
            self.assertTrue(all(character in "0123456789abcdef" for character in preparation_id))
            self.assertEqual(outcome["preparation_relpath"], "preparations/" + preparation_id + "/preparation.json")
            record_path = self.output
            for part in PurePosixPath(outcome["preparation_relpath"]).parts:
                record_path /= part
                self.assertFalse(record_path.is_symlink())
            self.assertTrue(record_path.is_file())
            record_bytes = record_path.read_bytes()
            self.assertEqual(sha256(record_bytes), outcome["preparation_sha256"])
            record = json.loads(record_bytes)
            self.verify_preparation(record)
            self.assertEqual(outcome["invocation_id"], invocation_id)
            self.assertEqual(outcome["intended_exit_status"], 0)
            self.assertIs(outcome["record_observed"], True)
            self.assertEqual(outcome["preparation_id"], record["preparation_id"])
            self.assertEqual(outcome["preparation_relpath"], "preparations/" + record["preparation_id"] + "/preparation.json")
            self.assertEqual(started["source_revision"], self.revision)
            self.assertEqual(started["controller_sha256"], record["binding"]["tools"]["controller"]["sha256"])
            self.assertEqual(started["output_dir"], path_bytes(self.output))
            self.assertEqual(started["repository"], path_bytes(self.repository))
            retained = {"procedure_revision": self.revision, "invocation_id": invocation_id,
                        "started_sha256": sha256(started_bytes), "outcome_sha256": sha256(outcome_bytes),
                        "process_result": {"returncode": result.returncode, "stdout_sha256": sha256(result.stdout)}}
            (self.directory / "consumer-acceptance.json").write_bytes(canonical(retained) + b"\n")
            return "accepted"
        except (AssertionError, OSError, ValueError, TypeError, KeyError):
            return "indeterminate"

    def test_late_emission_failure_cannot_be_accepted_by_consumer(self):
        reader, writer = os.pipe()
        os.close(reader)
        try:
            failed = self.prepare(sink=writer)
        finally:
            os.close(writer)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIsNone(failed.stdout)
        self.assertIn(b"outcome-emission-failed", failed.stderr)
        invocation = next((self.output / "invocations").iterdir())
        outcome = json.loads((invocation / "outcome.json").read_bytes())
        self.assertEqual(outcome["status"], "complete")
        self.assertEqual(outcome["intended_exit_status"], 0)
        record = json.loads((self.output / outcome["preparation_relpath"]).read_bytes())
        self.verify_preparation(record)
        self.assertEqual(self.consumer_status(failed, outcome["invocation_id"]), "indeterminate")
        result = self.prepare()
        ordinary, _ = self.completed(result)
        self.assertEqual(self.consumer_status(result, ordinary["invocation_id"]), "accepted")
        self.assertTrue(invocation.exists())

    def test_consumer_requires_outcome_process_and_complete_current_artifacts(self):
        result = self.prepare()
        outcome, record = self.completed(result)
        invocation_id = outcome["invocation_id"]
        self.assertEqual(self.consumer_status(result, invocation_id), "accepted")
        self.assertEqual(self.consumer_status(None, invocation_id), "indeterminate")
        outcome_path = self.output / "invocations" / invocation_id / "outcome.json"
        content = outcome_path.read_bytes()
        outcome_path.unlink()
        self.assertEqual(self.consumer_status(result, invocation_id), "indeterminate")
        outcome_path.write_bytes(content)
        prefix = self.output / "preparations" / record["preparation_id"]
        for parent in (prefix / "source", prefix / "requests", prefix / "grading", prefix):
            with self.subTest(parent=parent):
                extra = parent / "extra-empty"
                extra.mkdir()
                self.assertEqual(self.consumer_status(result, invocation_id), "indeterminate")
                extra.rmdir()
        result = self.prepare()
        fresh, _ = self.completed(result)
        self.assertEqual(self.consumer_status(result, fresh["invocation_id"]), "accepted")

    def test_constructed_consistent_envelopes_cannot_hide_broken_preparation_references(self):
        observed = self.prepare()
        outcome, record = self.completed(observed)
        invocation_id = outcome["invocation_id"]
        self.assertEqual(self.consumer_status(observed, invocation_id), "accepted")
        record_path = self.output / outcome["preparation_relpath"]
        outcome_path = self.output / "invocations" / invocation_id / "outcome.json"
        original_record = record_path.read_bytes()
        original_outcome = outcome_path.read_bytes()
        retained_process = {path: path.read_bytes() for path in self.directory.glob("process-*/*")}
        digest = next(iter(record["requests"]))
        corruptions = [
            (("requests", digest, "byte_count"), record["requests"][digest]["byte_count"] + 1),
            (("requests", digest, "slot_count"), record["requests"][digest]["slot_count"] + 1),
            (("requests", digest, "relpath"), record["grading"]["relpath"]),
            (("requests",), {}),
            (("slots", "entries", 0, "fixture_paths"), []),
            (("slots", "entries", 0, "candidate_bundle_paths"), []),
            (("slots", "entries", 0, "request_byte_count"), 0),
            (("slots", "entries", 0, "state"), "started"),
            (("slots", "count"), 77),
            (("grading", "constructor", "sha256"), "sha256:" + "0" * 64),
            (("grading", "requires_at_grading_time"), []),
            (("source", "declaration", "case_files"), []),
            (("source", "inventory"), {}),
            (("artifacts",), record["artifacts"][:-1]),
            (("artifacts",), record["artifacts"] + [record["artifacts"][0]]),
            (("binding", "tools", "constructor", "oid"), "0" * 40),
            (("tree_oid",), "0" * 40),
            (("corpus", "sha256"), "sha256:" + "0" * 64),
            (("authority", "claims"), ["actor_execution"]),
        ]
        try:
            for path, replacement in corruptions:
                with self.subTest(path=path):
                    changed = copy.deepcopy(record)
                    parent = changed
                    for key in path[:-1]:
                        parent = parent[key]
                    parent[path[-1]] = replacement
                    constructed_record = canonical(changed) + b"\n"
                    record_path.write_bytes(constructed_record)
                    constructed_outcome = {**outcome, "preparation_sha256": sha256(constructed_record)}
                    constructed_stdout = canonical(constructed_outcome) + b"\n"
                    outcome_path.write_bytes(constructed_stdout)
                    constructed_process = subprocess.CompletedProcess(
                        observed.args, observed.returncode, constructed_stdout, observed.stderr,
                    )
                    with self.assertRaises(AssertionError):
                        self.verify_preparation(changed)
                    self.assertEqual(self.consumer_status(constructed_process, invocation_id), "indeterminate")
        finally:
            record_path.write_bytes(original_record)
            outcome_path.write_bytes(original_outcome)
        self.assertEqual({path: path.read_bytes() for path in retained_process}, retained_process)
        self.assertEqual(observed.stdout, original_outcome)
        self.assertEqual(self.consumer_status(observed, invocation_id), "accepted")


class CommandTests(unittest.TestCase):
    def test_help_and_usage_are_available_without_repository_access(self):
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        with tempfile.TemporaryDirectory() as directory:
            help_result = subprocess.run(
                [sys.executable, "-B", str(SCRIPT), "prepare", "--help"],
                cwd=directory, env=environment, capture_output=True,
            )
            self.assertEqual(help_result.returncode, 0, help_result.stderr)
            self.assertIn(b"--source-revision", help_result.stdout)
            self.assertIn(b"indeterminate", help_result.stdout)
            usage_result = subprocess.run(
                [sys.executable, "-B", str(SCRIPT), "prepare"],
                cwd=directory, env=environment, capture_output=True,
            )
            self.assertEqual(usage_result.returncode, 2)
            self.assertEqual(usage_result.stdout, b"")
            self.assertNotIn(b"Traceback", usage_result.stderr)


if __name__ == "__main__":
    unittest.main()
