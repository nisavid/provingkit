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

    def oracle(self):
        constructor = types.ModuleType("clean_constructor_oracle")
        content = self.git("show", self.revision + ":" + TOOLS["constructor"])
        self.assertEqual(sha256(content), sha256((ROOT / TOOLS["constructor"]).read_bytes()))
        exec(compile(content, "committed-constructor-oracle", "exec"), constructor.__dict__)
        source = self.directory / "oracle-source"
        source.mkdir(exist_ok=True)
        for relative in self.git("ls-tree", "-r", "--name-only", self.revision).decode().splitlines():
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(self.git("show", self.revision + ":" + relative))
        cases = json.loads((source / MANIFEST).read_bytes())["evals"]
        requests = {(case["id"], variant): constructor.executor_request(source, case, variant).encode()
                    for case in cases for variant in ("with_skill", "without_skill")}
        return constructor, source, cases, requests

    def verify_artifacts(self, record, output=None):
        output = output or self.output
        entries = record["artifacts"]
        self.assertEqual(len(entries), len({entry["relpath"] for entry in entries}))
        for entry in entries:
            content = (output / entry["relpath"]).read_bytes()
            self.assertEqual(sha256(content), entry["sha256"])
            self.assertEqual(len(content), entry["byte_count"])
        for relative, entry in record["source"]["inventory"].items():
            path = output / entry["relpath"]
            self.assertEqual(path.stat().st_mode & 0o777, 0o700 if entry["mode"] == "100755" else 0o600)
            self.assertEqual(path.read_bytes(), self.git("show", self.revision + ":" + relative))

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
        constructor, source, cases, requests = self.oracle()
        self.assertEqual(sorted(record["source"]["inventory"]), constructor.source_paths(source, cases))
        coordinates = [(case_id, variant, repetition) for case_id in range(13)
                       for variant in ("with_skill", "without_skill") for repetition in (1, 2, 3)]
        self.assertEqual(record["slots"]["count"], 78)
        self.assertEqual([(slot["case_id"], slot["variant"], slot["repetition"])
                          for slot in record["slots"]["entries"]], coordinates)
        for slot in record["slots"]["entries"]:
            self.assertEqual(slot["state"], "unstarted")
            expected = requests[slot["case_id"], slot["variant"]]
            self.assertEqual((self.output / slot["request_relpath"]).read_bytes(), expected)
            self.assertEqual(slot["request_sha256"], sha256(expected))
            self.assertEqual(slot["request_byte_count"], len(expected))
            self.assertEqual(slot["candidate_bundle_paths"], CANDIDATES if slot["variant"] == "with_skill" else [])
        self.assertEqual(len(record["requests"]), len(set(requests.values())))
        self.assertEqual(len(record["artifacts"]), len(constructor.source_paths(source, cases)) + len(set(requests.values())) + 1)
        grading_reference = {key: record["grading"][key] for key in ("relpath", "sha256", "byte_count")}
        self.assertIn(grading_reference, record["artifacts"])
        grading = json.loads((self.output / grading_reference["relpath"]).read_bytes())
        self.assertEqual(grading["cases"]["0"], {"expected_output": "Private expected answer 0", "expectations": [
            {"id": "case-0-expectation-1", "text": "Preserve contract 0.", "severity": "safety"}]})
        self.verify_artifacts(record)
        expected_files = {entry["relpath"] for entry in record["artifacts"]} | {outcome["preparation_relpath"]}
        actual_files = {path.relative_to(self.output).as_posix() for path in
                        (self.output / "preparations" / record["preparation_id"]).rglob("*") if path.is_file()}
        self.assertEqual(actual_files, expected_files)
        self.assertEqual(record["authority"]["kind"], "preparation_only")
        self.assertEqual(record["authority"]["claims"], [])

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
                    self.verify_artifacts(record, output)

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

    def verify_independently_derived_inventory(self, record):
        constructor, source, cases, requests = self.oracle()
        paths = constructor.source_paths(source, cases)
        self.assertEqual(sorted(record["source"]["inventory"]), paths)
        expected_requests = {sha256(content): content for content in requests.values()}
        self.assertEqual(set(record["requests"]), set(expected_requests))
        prefix = "preparations/" + record["preparation_id"]
        expected_artifacts = {prefix + "/source/" + path for path in paths}
        expected_artifacts.update(prefix + "/requests/" + digest.removeprefix("sha256:") + ".request"
                                  for digest in expected_requests)
        expected_artifacts.add(prefix + "/grading/cases.json")
        self.assertEqual({entry["relpath"] for entry in record["artifacts"]}, expected_artifacts)
        self.assertEqual(len(record["artifacts"]), len(paths) + len(expected_requests) + 1)
        for slot in record["slots"]["entries"]:
            expected = requests[slot["case_id"], slot["variant"]]
            self.assertEqual((self.output / slot["request_relpath"]).read_bytes(), expected)
            self.assertEqual(slot["request_sha256"], sha256(expected))
            self.assertEqual(slot["request_byte_count"], len(expected))
        self.verify_artifacts(record)

    def verify_changed_inventory_reuse_and_collision(self, result, outcome, record):
        paths = [self.output / entry["relpath"] for entry in record["artifacts"]]
        record_path = self.output / outcome["preparation_relpath"]
        paths.append(record_path)
        identities = {path: (path.stat().st_ino, path.stat().st_mode, path.read_bytes()) for path in paths}
        reused, reused_record = self.completed(self.prepare())
        self.assertEqual(reused_record, record)
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
        self.verify_independently_derived_inventory(record)
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
        self.verify_independently_derived_inventory(record)
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
                _, _, _, requests = self.oracle()
                for slot in record["slots"]["entries"]:
                    self.assertEqual((self.output / slot["request_relpath"]).read_bytes(), requests[slot["case_id"], slot["variant"]])
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
        self.verify_artifacts(bare_record, output)
        self.failure(self.prepare(repository=bare, output=bare / "private"), "rejected", "unsafe-output-overlap")

    def test_checkout_with_unset_optional_bare_config_remains_eligible(self):
        _, control = self.completed(self.prepare())
        self.git("config", "--unset", "core.bare")
        output = self.directory / "unset-bare-output"
        _, record = self.completed(self.prepare(output=output), output)
        self.assertEqual(record, control)
        self.verify_artifacts(record, output)
        self.failure(self.prepare(output=self.repository / ".git/private"), "rejected", "unsafe-output-overlap")

    def test_lossless_source_selection_and_unicode_material(self):
        _, baseline = self.completed(self.prepare())
        unrelated = os.fsdecode(b"unrelated-\xff")
        self.write(unrelated, b"unrelated")
        self.revision = self.commit()
        _, record = self.completed(self.prepare())
        self.assertEqual(set(record["source"]["inventory"]), set(baseline["source"]["inventory"]))
        self.assertEqual(set(record["requests"]), set(baseline["requests"]))
        self.write(f"{SKILL}/scripts/café.py", b"unicode source")
        self.revision = self.commit()
        _, unicode_record = self.completed(self.prepare())
        self.assertIn(f"{SKILL}/scripts/café.py", unicode_record["source"]["inventory"])
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
        self.assertEqual(record["slots"]["count"], 78)
        self.assertEqual(record["slots"]["case_ids"], list(range(13)))
        constructor = types.ModuleType("real_committed_oracle")
        source = subprocess.check_output(["git", "show", real_revision + ":" + TOOLS["constructor"]], cwd=ROOT)
        exec(compile(source, "real-committed-oracle", "exec"), constructor.__dict__)
        oracle = self.directory / "real-oracle"
        oracle.mkdir()
        for relative in record["source"]["inventory"]:
            path = oracle / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(subprocess.check_output(["git", "show", real_revision + ":" + relative], cwd=ROOT))
        cases = {case["id"]: case for case in json.loads((oracle / MANIFEST).read_bytes())["evals"]}
        for slot in record["slots"]["entries"]:
            expected = constructor.executor_request(oracle, cases[slot["case_id"]], slot["variant"]).encode()
            self.assertEqual((self.output / slot["request_relpath"]).read_bytes(), expected)
            self.assertEqual(slot["candidate_bundle_paths"], CANDIDATES if slot["variant"] == "with_skill" else [])

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
            record_path = self.output / outcome["preparation_relpath"]
            record_bytes = record_path.read_bytes()
            self.assertEqual(sha256(record_bytes), outcome["preparation_sha256"])
            record = json.loads(record_bytes)
            identity = hashlib.sha256(canonical(record["binding"])).hexdigest()
            self.assertEqual(identity, record["preparation_id"])
            self.assertEqual(identity, record_path.parent.name)
            self.assertEqual(record["binding"]["source_commit"], self.revision)
            for role, relative in TOOLS.items():
                expected_bytes = self.git("show", self.revision + ":" + relative)
                expected_oid = self.git("rev-parse", self.revision + ":" + relative).decode().strip()
                self.assertEqual(record["binding"]["tools"][role],
                                 {"path": relative, "oid": expected_oid, "sha256": sha256(expected_bytes)})
            for entry in record["artifacts"]:
                relative = PurePosixPath(entry["relpath"])
                self.assertFalse(relative.is_absolute())
                self.assertEqual(relative.as_posix(), entry["relpath"])
                self.assertNotIn("..", relative.parts)
                current = self.output
                for part in relative.parts:
                    current /= part
                    self.assertFalse(current.is_symlink())
            self.verify_artifacts(record)
            source_root = self.output / record["source"]["root_relpath"]
            expected_files = set(record["source"]["inventory"])
            expected_directories = {parent.as_posix() for path in expected_files
                                    for parent in PurePosixPath(path).parents if str(parent) != "."}
            actual_files = set()
            actual_directories = set()
            for directory, directories, files in os.walk(source_root, followlinks=False):
                for name in directories:
                    path = Path(directory) / name
                    self.assertFalse(path.is_symlink())
                    actual_directories.add(path.relative_to(source_root).as_posix())
                for name in files:
                    path = Path(directory) / name
                    self.assertFalse(path.is_symlink())
                    self.assertTrue(path.is_file())
                    actual_files.add(path.relative_to(source_root).as_posix())
            self.assertEqual(actual_files, expected_files)
            self.assertEqual(actual_directories, expected_directories)
            artifacts = {entry["relpath"]: entry for entry in record["artifacts"]}
            for entry in record["source"]["inventory"].values():
                self.assertEqual(artifacts[entry["relpath"]], {key: entry[key] for key in ("relpath", "sha256", "byte_count")})
            for pattern, matches in record["source"]["declaration"]["glob_matches"].items():
                self.assertEqual(matches, sorted(path for path in actual_files if PurePosixPath(path).full_match(pattern)))
            expected_coordinates = [(case_id, variant, repetition) for case_id in range(13)
                                    for variant in ("with_skill", "without_skill") for repetition in (1, 2, 3)]
            self.assertEqual([(slot["case_id"], slot["variant"], slot["repetition"])
                              for slot in record["slots"]["entries"]], expected_coordinates)
            for slot in record["slots"]["entries"]:
                self.assertEqual(slot["state"], "unstarted")
                self.assertEqual(artifacts[slot["request_relpath"]],
                                 {"relpath": slot["request_relpath"], "sha256": slot["request_sha256"],
                                  "byte_count": slot["request_byte_count"]})
            grading = record["grading"]
            self.assertEqual(artifacts[grading["relpath"]], {key: grading[key] for key in ("relpath", "sha256", "byte_count")})
            self.assertEqual(json.loads((self.output / grading["relpath"]).read_bytes())["cases"], {
                str(case["id"]): {"expected_output": case["expected_output"], "expectations": [
                    {"id": f"case-{case['id']}-expectation-{index}", "text": text, "severity": "safety"}
                    for index, text in enumerate(case["expectations"], 1)]} for case in self.cases})
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
        self.verify_artifacts(record)
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
        extra = self.output / record["source"]["root_relpath"] / "extra-empty"
        extra.mkdir()
        self.assertEqual(self.consumer_status(result, invocation_id), "indeterminate")
        extra.rmdir()
        result = self.prepare()
        fresh, _ = self.completed(result)
        self.assertEqual(self.consumer_status(result, fresh["invocation_id"]), "accepted")


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
