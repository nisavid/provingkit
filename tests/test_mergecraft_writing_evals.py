from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import ClassVar

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts/mergecraft_writing_evals.py"


class WritingEvaluationPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.output = Path(self.temporary.name) / "evaluation"
        self.fixture_client()

    def command(self, *arguments):
        return subprocess.run(
            [sys.executable, "-B", str(HELPER), *map(str, arguments)],
            text=True,
            capture_output=True,
            check=False,
        )

    def prepare(self):
        result = self.command(
            "prepare",
            "--repo",
            ROOT,
            "--output",
            self.output,
            "--claude",
            self.claude,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads((self.output / "manifest.json").read_text())

    def test_prepare_rejects_an_unrelated_executable_reporting_a_version(self):
        result = self.command(
            "prepare",
            "--repo",
            ROOT,
            "--output",
            self.output,
            "--claude",
            sys.executable,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Claude Code", result.stderr)
        self.assertFalse(self.output.exists())

    def test_prepare_bounds_the_version_probe_before_creating_evidence(self):
        self.claude.write_text(
            f"#!{sys.executable}\n"
            "import time\n"
            "time.sleep(6)\n"
            "print('2.1.277 (Claude Code)')\n"
        )
        result = self.command(
            "prepare",
            "--repo",
            ROOT,
            "--output",
            self.output,
            "--claude",
            self.claude,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("timed out", result.stderr)
        self.assertFalse(self.output.exists())

    def test_version_bound_manifest_is_distinct_from_historical_schema(self):
        manifest = self.prepare()
        self.assertEqual(manifest["schema_version"], 2)
        manifest["schema_version"] = 1
        (self.output / "manifest.json").write_text(json.dumps(manifest))
        result = self.command("verify", "--evaluation", self.output, "--repo", ROOT)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("schema", result.stderr)

    def test_prepare_freezes_the_two_suites_and_withholds_grading_fields(self):
        manifest = self.prepare()
        specs = json.loads((self.output / "behavior-specs.json").read_text())
        grades = json.loads((self.output / "grader-cases.json").read_text())
        self.assertEqual(manifest["behavior_counts"], {"markdown": 24, "relations": 51})
        self.assertEqual(len(specs), 75)
        self.assertEqual(len({item["id"] for item in specs}), 75)
        self.assertEqual(len(grades), 75)
        self.assertFalse((self.output / "runs").exists())
        for spec, grade in zip(specs, grades):
            request = json.loads(spec["request"])
            self.assertEqual(set(request), {"prompt", "fixture", "candidate_bundle"})
            self.assertEqual(spec["id"], grade["run_id"])
            self.assertNotIn(str(ROOT), spec["request"])
            self.assertTrue(grade["expectations"])
            bundle = request["candidate_bundle"]
            self.assertIn(
                "plugins/mergecraft/skills/writing-github-issue-and-pr-markdown/references/review-voice.md",
                bundle,
            )
            self.assertIn(
                "plugins/proseweaving/skills/writing-for-people/SKILL.md", bundle
            )
            if spec["suite"] == "relations":
                self.assertIn(
                    "plugins/mergecraft/skills/writing-reviewable-pr-descriptions/references/body-contract.md",
                    bundle,
                )
        verified = self.command("verify", "--evaluation", self.output, "--repo", ROOT)
        self.assertEqual(verified.returncode, 0, verified.stderr)

    def test_execution_retains_exact_bytes_and_refuses_run_directory_reuse(self):
        self.fixture_client()
        self.prepare()
        manifest_hash = hashlib.sha256(
            (self.output / "manifest.json").read_bytes()
        ).hexdigest()
        arguments = (
            "run",
            "--evaluation",
            self.output,
            "--repo",
            ROOT,
            "--manifest-sha256",
            manifest_hash,
            "--run-id",
            "markdown/case-01-with-skill-1",
        )
        result = self.command(*arguments)
        self.assertEqual(result.returncode, 0, result.stderr)
        run = self.output / "runs/markdown/case-01-with-skill-1"
        record = json.loads((run / "record.json").read_text())
        self.assertTrue(record["technically_valid"])
        self.assertEqual((run / "response.txt").read_bytes(), b"synthetic response\n")
        before = {p.name: p.read_bytes() for p in run.iterdir() if p.is_file()}
        repeated = self.command(*arguments)
        self.assertNotEqual(repeated.returncode, 0)
        self.assertEqual(
            before, {p.name: p.read_bytes() for p in run.iterdir() if p.is_file()}
        )

    def fixture_client(
        self,
        success=True,
        assistant_session="matching",
        invalid_utf8=False,
        response="synthetic response\n",
        line_ending="\n",
        version="2.1.277",
        stream_version=None,
    ):
        self.claude = Path(self.temporary.name) / "fixture-client"
        self.claude.write_text(
            f"#!{sys.executable}\n"
            "import json,sys\n"
            "if '--version' in sys.argv:\n"
            f" print({(version + ' (Claude Code)')!r})\n"
            " raise SystemExit(0)\n"
            "session=sys.argv[sys.argv.index('--session-id')+1]\n"
            "request=json.load(sys.stdin)\n"
            "assert set(request)=={'prompt','fixture','candidate_bundle'}\n"
            f"response={response!r}\n"
            "def emit(event):\n"
            " raw=json.dumps(event,ensure_ascii=False).encode('utf-8')\n"
            f" if {invalid_utf8}: raw=raw.replace(b'synthetic response', b'synthetic\\xff response')\n"
            f" sys.stdout.buffer.write(raw+{line_ending.encode()!r})\n"
            "emit({'type':'system','subtype':'init','session_id':session,"
            "'tools':[],'mcp_servers':[],'skills':[],'plugins':[],'slash_commands':[],"
            "'model':'claude-opus-5','permissionMode':'dontAsk',"
            f"'claude_code_version':{(stream_version or version)!r}}})\n"
            "assistant={'type':'assistant','session_id':session,'message':{'model':'claude-opus-5',"
            "'content':[{'type':'text','text':response}]}}\n"
            f"if {assistant_session!r} == 'missing': assistant.pop('session_id')\n"
            f"if {assistant_session!r} == 'different': assistant['session_id']='different-session'\n"
            "emit(assistant)\n"
            f"emit({{'type':'result','subtype':{'success' if success else 'error'!r},'is_error':{not success},"
            "'session_id':session,'result':response})\n"
        )
        self.claude.chmod(0o700)

    def test_new_client_version_is_bound_to_execution_and_collection(self):
        self.fixture_client(version="2.1.999")
        manifest = self.prepare()
        self.assertEqual(manifest["executor"]["claude_code_version"], "2.1.999")
        arguments = [
            "run",
            "--evaluation",
            self.output,
            "--repo",
            ROOT,
            "--manifest-sha256",
            hashlib.sha256((self.output / "manifest.json").read_bytes()).hexdigest(),
        ]
        for repetition in (1, 2, 3):
            arguments += ["--run-id", f"relations/case-00-with-skill-{repetition}"]
        result = self.command(*arguments)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.command(
            "collect",
            "--evaluation",
            self.output,
            "--repo",
            ROOT,
            "--suite",
            "relations",
            "--case",
            "0",
            "--output",
            self.output / "grader.json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_runtime_version_mismatch_is_retained_and_cannot_be_collected(self):
        self.fixture_client(version="2.1.277", stream_version="2.1.278")
        self.prepare()
        arguments = [
            "run",
            "--evaluation",
            self.output,
            "--repo",
            ROOT,
            "--manifest-sha256",
            hashlib.sha256((self.output / "manifest.json").read_bytes()).hexdigest(),
        ]
        for repetition in (1, 2, 3):
            arguments += ["--run-id", f"relations/case-00-with-skill-{repetition}"]
        result = self.command(*arguments)
        self.assertNotEqual(result.returncode, 0)
        run = self.output / "runs/relations/case-00-with-skill-1"
        record = json.loads((run / "record.json").read_text())
        self.assertEqual(record["init"]["claude_code_version"], "2.1.278")
        self.assertFalse(record["technically_valid"])
        self.assertEqual((run / "response.txt").read_bytes(), b"synthetic response\n")
        packet = self.output / "invalid-grader.json"
        collected = self.command(
            "collect",
            "--evaluation",
            self.output,
            "--repo",
            ROOT,
            "--suite",
            "relations",
            "--case",
            "0",
            "--output",
            packet,
        )
        self.assertNotEqual(collected.returncode, 0)
        self.assertIn("execution is technically invalid", collected.stderr)
        self.assertFalse(packet.exists())

    def test_assistant_session_must_match_before_responses_are_collected(self):
        for problem in ("missing", "different"):
            with self.subTest(assistant_session=problem):
                self.output = Path(self.temporary.name) / problem
                self.fixture_client(assistant_session=problem)
                self.prepare()
                manifest_hash = hashlib.sha256(
                    (self.output / "manifest.json").read_bytes()
                ).hexdigest()
                result = self.command(
                    "run",
                    "--evaluation",
                    self.output,
                    "--repo",
                    ROOT,
                    "--manifest-sha256",
                    manifest_hash,
                    "--run-id",
                    "markdown/case-01-with-skill-1",
                    "--run-id",
                    "markdown/case-01-with-skill-2",
                    "--run-id",
                    "markdown/case-01-with-skill-3",
                )
                self.assertNotEqual(result.returncode, 0)
                run = self.output / "runs/markdown/case-01-with-skill-1"
                record = json.loads((run / "record.json").read_text())
                self.assertFalse(record["technically_valid"])
                self.assertEqual(
                    (run / "response.txt").read_bytes(), b"synthetic response\n"
                )
                packet = self.output / "invalid-grader.json"
                collected = self.command(
                    "collect",
                    "--evaluation",
                    self.output,
                    "--repo",
                    ROOT,
                    "--suite",
                    "markdown",
                    "--case",
                    "1",
                    "--output",
                    packet,
                )
                self.assertNotEqual(collected.returncode, 0)
                self.assertIn("execution is technically invalid", collected.stderr)
                self.assertFalse(packet.exists())

    def test_invalid_utf8_is_retained_and_rejected_without_replacement(self):
        self.fixture_client(invalid_utf8=True)
        self.prepare()
        manifest_hash = hashlib.sha256(
            (self.output / "manifest.json").read_bytes()
        ).hexdigest()
        result = self.command(
            "run",
            "--evaluation",
            self.output,
            "--repo",
            ROOT,
            "--manifest-sha256",
            manifest_hash,
            "--run-id",
            "markdown/case-01-with-skill-1",
            "--run-id",
            "markdown/case-01-with-skill-2",
            "--run-id",
            "markdown/case-01-with-skill-3",
        )
        self.assertNotEqual(result.returncode, 0)
        run = self.output / "runs/markdown/case-01-with-skill-1"
        raw = (run / "stdout.jsonl").read_bytes()
        self.assertIn(b"synthetic\xff response", raw)
        record = json.loads((run / "record.json").read_text())
        self.assertFalse(record["technically_valid"])
        self.assertTrue(record["decode_error"])
        self.assertEqual(record["stdout_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual((run / "response.txt").read_bytes(), b"")
        packet = self.output / "invalid-grader.json"
        collected = self.command(
            "collect",
            "--evaluation",
            self.output,
            "--repo",
            ROOT,
            "--suite",
            "markdown",
            "--case",
            "1",
            "--output",
            packet,
        )
        self.assertNotEqual(collected.returncode, 0)
        self.assertIn("execution is technically invalid", collected.stderr)
        self.assertFalse(packet.exists())

    def test_unicode_response_survives_lf_and_crlf_record_framing(self):
        response = "Line\u2028separator\u2029paragraph\r\nLiteral \ufffd\n"
        for ending in ("\n", "\r\n"):
            with self.subTest(line_ending=repr(ending)):
                self.output = Path(self.temporary.name) / (
                    "lf" if ending == "\n" else "crlf"
                )
                self.fixture_client(response=response, line_ending=ending)
                self.prepare()
                manifest_hash = hashlib.sha256(
                    (self.output / "manifest.json").read_bytes()
                ).hexdigest()
                result = self.command(
                    "run",
                    "--evaluation",
                    self.output,
                    "--repo",
                    ROOT,
                    "--manifest-sha256",
                    manifest_hash,
                    "--run-id",
                    "markdown/case-01-with-skill-1",
                    "--run-id",
                    "markdown/case-01-with-skill-2",
                    "--run-id",
                    "markdown/case-01-with-skill-3",
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                run = self.output / "runs/markdown/case-01-with-skill-1"
                raw = (run / "stdout.jsonl").read_bytes()
                self.assertIn("Line\u2028separator\u2029paragraph".encode(), raw)
                self.assertEqual((run / "response.txt").read_bytes(), response.encode())
                packet = self.output / "unicode-grader.json"
                collected = self.command(
                    "collect",
                    "--evaluation",
                    self.output,
                    "--repo",
                    ROOT,
                    "--suite",
                    "markdown",
                    "--case",
                    "1",
                    "--output",
                    packet,
                )
                self.assertEqual(collected.returncode, 0, collected.stderr)
                data = json.loads(packet.read_text())
                self.assertEqual(
                    [r["response"] for r in data["responses"]], [response] * 3
                )

    def test_collect_requires_three_complete_bound_responses(self):
        self.fixture_client()
        self.prepare()
        manifest_hash = hashlib.sha256(
            (self.output / "manifest.json").read_bytes()
        ).hexdigest()
        packet = self.output / "case-1-grader.json"
        collect = (
            "collect",
            "--evaluation",
            self.output,
            "--repo",
            ROOT,
            "--suite",
            "markdown",
            "--case",
            "1",
            "--output",
            packet,
        )
        incomplete = self.command(*collect)
        self.assertNotEqual(incomplete.returncode, 0)
        self.assertFalse(packet.exists())
        arguments = [
            "run",
            "--evaluation",
            self.output,
            "--repo",
            ROOT,
            "--manifest-sha256",
            manifest_hash,
        ]
        for repetition in (1, 2, 3):
            arguments += ["--run-id", f"markdown/case-01-with-skill-{repetition}"]
        self.assertEqual(self.command(*arguments).returncode, 0)
        collected = self.command(*collect)
        self.assertEqual(collected.returncode, 0, collected.stderr)
        data = json.loads(packet.read_text())
        self.assertEqual(len(data["responses"]), 3)
        self.assertEqual(len({r["session_id"] for r in data["responses"]}), 3)
        self.assertTrue(data["expectations"])
        self.assertTrue(
            all(r["response"] == "synthetic response\n" for r in data["responses"])
        )
        response = self.output / "runs/markdown/case-01-with-skill-1/response.txt"
        response.write_text("substituted response")
        rejected = self.command(*collect[:-1], self.output / "tampered-grader.json")
        self.assertNotEqual(rejected.returncode, 0)
        self.assertFalse((self.output / "tampered-grader.json").exists())

    def test_source_drift_prevents_launch_without_changing_frozen_inputs(self):
        self.fixture_client()
        manifest = self.prepare()
        shadow = Path(self.temporary.name) / "changed-source"
        shutil.copytree(self.output / "source", shadow)
        changed = (
            shadow
            / "plugins/mergecraft/skills/writing-reviewable-pr-descriptions/references/body-contract.md"
        )
        changed.write_text("different instructions\n")
        manifest_hash = hashlib.sha256(
            (self.output / "manifest.json").read_bytes()
        ).hexdigest()
        result = self.command(
            "run",
            "--evaluation",
            self.output,
            "--repo",
            shadow,
            "--manifest-sha256",
            manifest_hash,
            "--run-id",
            "relations/case-00-with-skill-1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("current source changed", result.stderr)
        self.assertFalse((self.output / "runs").exists())
        self.assertEqual(
            manifest, json.loads((self.output / "manifest.json").read_text())
        )

    def test_failed_execution_stops_later_launches_and_cannot_be_collected(self):
        self.fixture_client(success=False)
        self.prepare()
        manifest_hash = hashlib.sha256(
            (self.output / "manifest.json").read_bytes()
        ).hexdigest()
        arguments = [
            "run",
            "--evaluation",
            self.output,
            "--repo",
            ROOT,
            "--manifest-sha256",
            manifest_hash,
        ]
        for name in (
            "markdown/case-01-with-skill-1",
            "markdown/case-01-with-skill-2",
            "markdown/case-01-with-skill-3",
            "markdown/case-02-with-skill-1",
        ):
            arguments += ["--run-id", name]
        result = self.command(*arguments)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.output / "runs/markdown/case-02-with-skill-1").exists())
        record = json.loads(
            (self.output / "runs/markdown/case-01-with-skill-1/record.json").read_text()
        )
        self.assertFalse(record["technically_valid"])
        self.assertEqual(record["result"]["subtype"], "error")
        packet = self.output / "invalid-grader.json"
        collected = self.command(
            "collect",
            "--evaluation",
            self.output,
            "--repo",
            ROOT,
            "--suite",
            "markdown",
            "--case",
            "1",
            "--output",
            packet,
        )
        self.assertNotEqual(collected.returncode, 0)
        self.assertFalse(packet.exists())

    def test_stop_file_leaves_selected_runs_unlaunched(self):
        self.fixture_client()
        self.prepare()
        (self.output / "STOP_LAUNCHES").touch()
        manifest_hash = hashlib.sha256(
            (self.output / "manifest.json").read_bytes()
        ).hexdigest()
        result = self.command(
            "run",
            "--evaluation",
            self.output,
            "--repo",
            ROOT,
            "--manifest-sha256",
            manifest_hash,
            "--run-id",
            "markdown/case-01-with-skill-1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.output / "runs").exists())
        self.assertEqual(
            json.loads(result.stdout)["unlaunched"], ["markdown/case-01-with-skill-1"]
        )


class RelationReceiptTests(unittest.TestCase):
    """Constructed histories and observations; no provider or qualification claim."""

    skill = "mergecraft/maintaining-issue-pr-relations"
    source = "evals/mergecraft/skills/maintaining-issue-pr-relations"
    target = "mergecraft-scope-eval:maintaining-issue-pr-relations"
    native_paths: ClassVar[list[str]] = [
        "plugins/mergecraft/skills/maintaining-issue-pr-relations/" + suffix
        for suffix in (
            "SKILL.md",
            "references/relation-contract.md",
            "references/command.md",
        )
    ]

    @staticmethod
    def encoded(value):
        return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()

    @staticmethod
    def sha(raw):
        return hashlib.sha256(raw).hexdigest()

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value if isinstance(value, bytes) else self.encoded(value))
        return path

    def ref(self, path, **extra):
        return {"path": str(path), "sha256": self.sha(path.read_bytes()), **extra}

    def command(self, *args, helper="scripts/mergecraft_writing_evals.py"):
        return subprocess.run(
            [sys.executable, "-B", str(self.repo / helper), *map(str, args)],
            cwd=self.repo,
            capture_output=True,
            text=True,
            check=False,
        )

    def git(self, *args):
        return subprocess.check_output(
            [
                "git",
                "-c",
                "core.hooksPath=/dev/null",
                "-c",
                "commit.gpgsign=false",
                "-c",
                "user.name=Constructed Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                *args,
            ],
            cwd=self.repo,
            text=True,
            stderr=subprocess.PIPE,
        ).strip()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / "source"
        shutil.copytree(
            ROOT, self.repo, ignore=shutil.ignore_patterns(".git", "__pycache__")
        )
        # The accepted mapping stays byte-exact at S. Only the constructed B
        # omits the relation support row, selecting one consumer for the test.
        mapping = self.repo / "release/behavior-eval-input-map.json"
        accepted_mapping = mapping.read_bytes()
        data = json.loads(mapping.read_bytes())
        data["entries"] = [
            e
            for e in data["entries"]
            if (e["source"]["path"], e["pointer"]) != (self.source + "/policy.json", "")
        ]
        self.write(mapping, data)
        self.git("init", "-q")
        self.git("add", ".")
        self.git("commit", "-qm", "test: construct inventory baseline")
        self.base_revision = self.git("rev-parse", "HEAD")
        self.write(mapping, accepted_mapping)
        self.git("add", ".")
        self.git("commit", "-qm", "test: construct unqualified receipt source")
        self.revision = self.git("rev-parse", "HEAD")
        self.descriptor = self.root / "descriptor.json"
        self.snapshot = self.root / "snapshot.json"
        self.refresh_snapshot()
        self.behavior = self.root / "behavior"
        fixture_client = self.root / "constructed-client"
        fixture_client.write_text(
            f"#!{sys.executable}\n"
            "import json,sys\n"
            "if '--version' in sys.argv:\n"
            " print('2.1.273 (Claude Code)')\n"
            " raise SystemExit(0)\n"
            "session=sys.argv[sys.argv.index('--session-id')+1]\n"
            "request=json.load(sys.stdin)\n"
            "response='Constructed application\\u2028response\\r\\n'\n"
            "events=[{'type':'system','subtype':'init','session_id':session,'tools':[],'mcp_servers':[],'skills':[],'plugins':[],'slash_commands':[],'model':'claude-opus-5','permissionMode':'dontAsk','claude_code_version':'2.1.273'},\n"
            "{'type':'assistant','session_id':session,'message':{'model':'claude-opus-5','content':[{'type':'text','text':response}]}},\n"
            "{'type':'result','subtype':'success','is_error':False,'session_id':session,'result':response}]\n"
            "for event in events: print(json.dumps(event,ensure_ascii=False))\n"
        )
        fixture_client.chmod(0o700)
        prepared = self.command(
            "prepare",
            "--repo",
            self.repo,
            "--output",
            self.behavior,
            "--claude",
            fixture_client,
        )
        self.assertEqual(prepared.returncode, 0, prepared.stderr)
        self.prepare_native()
        self.preparations = self.root / "preparations.json"
        self.grader_model = self.write(
            self.root / "grader-model.txt", b"fixture-grader"
        )
        self.write(
            self.preparations,
            {
                "schema_version": 1,
                "behavior": self.ref(self.behavior / "manifest.json"),
                "native": self.ref(self.native / "index.json"),
                "native_method": self.ref(self.method),
                "native_provenance": self.provenance,
                "native_format": self.ref(self.format),
                "native_format_evidence": [
                    self.ref(
                        self.write(
                            self.root / "format-evidence.json",
                            {
                                "claim": "Constructed format metadata; no real runtime qualification."
                            },
                        )
                    )
                ],
                "grader_model": {
                    "id": "fixture-grader",
                    "basis": "configured",
                    "reference": self.ref(self.grader_model, format="utf8", pointer=""),
                },
            },
        )
        self.binding = self.root / "binding.json"

    def refresh_snapshot(self):
        for operation, output in (
            ("descriptor", self.descriptor),
            ("prepare", self.snapshot),
        ):
            result = self.command(
                operation,
                "--revision",
                self.revision,
                "--skill",
                self.skill,
                helper="scripts/behavior_eval_inventory.py",
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            output.write_text(result.stdout)

    def prepare_native(self):
        self.native = self.root / "native-prepared"
        self.native.mkdir()
        self.runner_base = self.root / "native-runs"
        original = self.write(
            self.root / "original-runner.py",
            b"from pathlib import Path\nBASE=Path('/constructed-original')\n",
        )
        runner = self.write(
            self.root / "runner.py",
            f"from pathlib import Path\nBASE=Path({str(self.runner_base)!r})\n".encode(),
        )
        self.method = self.write(
            self.root / "native-method.py",
            b"# Constructed method identity; never executed.\n",
        )
        self.format = self.write(
            self.root / "native-format.md",
            b"Constructed fixture for the reviewed unique call/result/immediate-injection format.\n",
        )
        self.provenance = {"claude_eval_runner_v3.py": self.ref(original)}
        sources = {
            p: self.sha((self.repo / p).read_bytes())
            for p in self.native_paths
            + [self.source + "/trigger-evals.json", self.source + "/policy.json"]
        }
        frozen = self.root / "native-freeze"
        for p in sources:
            self.write(frozen / "source" / p, (self.repo / p).read_bytes())
        manifest = self.write(
            frozen / "manifest.json",
            {
                "schema_version": 1,
                "model_requested": "claude-opus-5",
                "effort_requested": "high",
                "trigger_runs": 13,
                "source_sha256": sources,
                "runner_sha256": self.sha(runner.read_bytes()),
            },
        )
        plugin = self.native / "trigger-plugin"
        self.write(
            plugin / ".claude-plugin/plugin.json",
            {
                "name": "mergecraft-scope-eval",
                "version": "0.0.0",
                "description": "Isolated candidate relation skill discovery evaluation",
            },
        )
        for path in self.native_paths:
            self.write(
                plugin
                / "skills/maintaining-issue-pr-relations"
                / Path(path).relative_to(
                    "plugins/mergecraft/skills/maintaining-issue-pr-relations"
                ),
                (self.repo / path).read_bytes(),
            )
        prefix = "Decide which available skill, if any, is needed for this user request. If a skill applies, invoke it using Skill, then stop without carrying out the task. If none applies, return NO_SKILL. Do not invoke any other tool or perform any task action.\n\nUser request: "
        cases = json.loads(
            (self.repo / self.source / "trigger-evals.json").read_bytes()
        )
        self.native_specs = [
            {
                "id": f"opus-relation-triggers-fixture/case-{i:02d}",
                "kind": "trigger",
                "suite": "relation-triggers",
                "case_id": i,
                "request": prefix + c["query"],
                "plugin_dir": str(plugin),
                "candidate_sha256": {p: sources[p] for p in self.native_paths},
            }
            for i, c in enumerate(cases)
        ]
        self.write(self.native / "trigger-specs.json", self.native_specs)
        self.write(self.native / "trigger-first.json", self.native_specs[:1])
        self.write(self.native / "trigger-rest.json", self.native_specs[1:])
        self.write(
            self.native / "grader-cases.json",
            [
                {
                    "run_id": s["id"],
                    "case_id": i,
                    "expected_should_trigger": c["should_trigger"],
                    "query": c["query"],
                    "required_skill": self.target,
                }
                for i, (s, c) in enumerate(zip(self.native_specs, cases))
            ],
        )
        self.write(
            self.native / "isolation-plan.json",
            {
                "schema_version": 1,
                "stage": "configuration-plan-only",
                "model_executed": False,
                "model_requested": "claude-opus-5",
                "effort_requested": "high",
                "native_source_sha256": {p: sources[p] for p in self.native_paths},
            },
        )
        self.write(
            self.native / "index.json",
            {
                "schema_version": 1,
                "stage": "native-input-construction",
                "model_executed": False,
                "version": "fixture",
                "manifest_sha256": self.sha(manifest.read_bytes()),
                "runner_sha256": self.sha(runner.read_bytes()),
                "source_root": str(frozen / "source"),
                "manifest_path": str(manifest),
                "runner_path": str(runner),
                "runner_base": str(self.runner_base),
                "source_sha256": sources,
                "native_source_sha256": {p: sources[p] for p in self.native_paths},
                "producer_source_sha256": {
                    k: v["sha256"] for k, v in self.provenance.items()
                },
                "adapter_sha256": self.sha(self.method.read_bytes()),
                "native_runs_planned": 13,
                "files_sha256": {
                    str(p.relative_to(self.native)): self.sha(p.read_bytes())
                    for p in self.native.rglob("*")
                    if p.is_file()
                },
                "limitations": ["Constructed unqualified observations only."],
            },
        )

    def bind(self, *, helper="scripts/mergecraft_writing_evals.py"):
        return self.command(
            "receipt-bind",
            "--repo",
            self.repo,
            "--revision",
            self.revision,
            "--descriptor",
            self.descriptor,
            "--snapshot",
            self.snapshot,
            "--preparations",
            self.preparations,
            "--output",
            self.binding,
            helper=helper,
        )

    def copy_receipt_equipment(self, directory):
        for relative in (
            "scripts/mergecraft_writing_evals.py",
            "scripts/behavior_eval_receipts.py",
            "scripts/behavior_eval_inventory.py",
            "scripts/behavior_eval_corpora.py",
            "release/behavior-eval-receipt-v1.schema.json",
        ):
            target = directory / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.repo / relative, target)
        return directory / "scripts/mergecraft_writing_evals.py"

    def test_binding_rejects_alternate_loaded_recorder_bytes_and_git_mode(self):
        original_revision = self.revision
        for change in ("bytes", "mode"):
            with self.subTest(change=change):
                helper = self.copy_receipt_equipment(self.root / f"equipment-{change}")
                if change == "bytes":
                    helper.write_bytes(
                        helper.read_bytes() + b"\n# Alternate recorder revision.\n"
                    )
                else:
                    helper.chmod(0o644)
                behavior = self.root / f"behavior-{change}"
                prepared = self.command(
                    "prepare",
                    "--repo",
                    self.repo,
                    "--output",
                    behavior,
                    "--claude",
                    self.root / "constructed-client",
                    helper=helper,
                )
                self.assertEqual(prepared.returncode, 0, prepared.stderr)
                preparations = json.loads(self.preparations.read_bytes())
                preparations["behavior"] = self.ref(behavior / "manifest.json")
                self.write(self.preparations, preparations)
                self.binding = self.root / f"binding-{change}.json"
                bound = self.bind(helper=helper)
                self.assertNotEqual(bound.returncode, 0)
                self.assertIn("loaded recorder", bound.stderr)
                self.assertFalse(self.binding.exists())
                self.assertEqual(self.git("rev-parse", "HEAD"), original_revision)

    def test_binding_freezes_actual_delivery_and_original_coordinates_before_runs(self):
        result = self.bind()
        self.assertEqual(result.returncode, 0, result.stderr)
        binding = json.loads(self.binding.read_bytes())
        self.assertEqual(binding["source_revision"], self.revision)
        self.assertEqual(len(binding["runs"]), 51)
        self.assertEqual(len(binding["triggers"]), 13)
        self.assertEqual(binding["runs"][0]["case_id"]["id"], 0)
        self.assertIsNone(binding["triggers"][0]["case_id"]["id"])
        delivered = binding["runs"][0]["delivered_source_sha256"]
        self.assertIn(
            "plugins/mergecraft/skills/getting-prs-merged/references/caller-continuation.md",
            delivered,
        )
        self.assertNotIn(
            "plugins/mergecraft/skills/getting-prs-merged/references/merge-actuator.md",
            delivered,
        )
        self.assertFalse((self.behavior / "runs").exists())
        self.assertFalse(self.runner_base.exists())
        self.assertNotEqual(binding["snapshot_sha256"], binding["snapshot"]["sha256"])
        self.assertNotEqual(self.bind().returncode, 0)

    def test_binding_outputs_must_stay_outside_source(self):
        self.binding = self.repo / "private-binding.json"
        result = self.bind()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("receipt output must be outside source", result.stderr)
        self.assertFalse(self.binding.exists())

    def observe_fixture(
        self, *, native_mutation=None, helper="scripts/mergecraft_writing_evals.py"
    ):
        result = self.bind(helper=helper)
        self.assertEqual(result.returncode, 0, result.stderr)
        specs = json.loads((self.behavior / "behavior-specs.json").read_bytes())
        arguments = [
            "run",
            "--evaluation",
            self.behavior,
            "--repo",
            self.repo,
            "--manifest-sha256",
            self.sha((self.behavior / "manifest.json").read_bytes()),
        ]
        for spec in specs:
            if spec["suite"] == "relations":
                arguments += ["--run-id", spec["id"]]
        result = self.command(*arguments)
        self.assertEqual(result.returncode, 0, result.stderr)
        packets = []
        for case in range(17):
            packet = self.root / f"application-packets/{case}.json"
            result = self.command(
                "collect",
                "--evaluation",
                self.behavior,
                "--repo",
                self.repo,
                "--suite",
                "relations",
                "--case",
                case,
                "--output",
                packet,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            packets.append(self.ref(packet))
        self.configuration = self.write(
            self.root / "configuration.json",
            {
                "cli_version": "2.1.273",
                "executable_sha256": self.sha(Path(sys.executable).read_bytes()),
                "finding": "Constructed client metadata; not a real native runtime qualification.",
                "source_excerpts": ["Constructed setting-reader correspondence."],
            },
        )
        index = json.loads((self.native / "index.json").read_bytes())
        collection = self.root / "native-collection"
        source_body = (
            (self.repo / self.native_paths[0])
            .read_text()
            .split("---\n", 2)[2]
            .lstrip("\n")
        )
        isolation_rows = []
        settings = {
            "disableAllHooks": True,
            "autoMemoryEnabled": False,
            "enabledPlugins": {},
            "claudeMdExcludes": ["**"],
        }
        for i, spec in enumerate(self.native_specs):
            directory = self.runner_base / spec["id"]
            session = f"constructed-native-{i}"
            plugin = Path(spec["plugin_dir"])
            init = {
                "type": "system",
                "subtype": "init",
                "session_id": session,
                "tools": ["Skill"],
                "skills": [self.target, "bundled-helper"],
                "mcp_servers": [],
                "permissionMode": "dontAsk",
                "model": "claude-opus-5",
                "claude_code_version": "2.1.273",
                "plugins": [
                    {
                        "name": "mergecraft-scope-eval",
                        "path": str(plugin),
                        "source": "mergecraft-scope-eval@inline",
                        "version": "0.0.0",
                    }
                ],
            }
            content = [{"type": "text", "text": "Constructed selection response."}]
            calls, results, injections = [], [], []
            events = [init]
            if i < 5:
                calls = [
                    {
                        "type": "tool_use",
                        "id": f"call-{i}",
                        "name": "Skill",
                        "input": {"skill": self.target},
                    }
                ]
                events.append(
                    {
                        "type": "assistant",
                        "session_id": session,
                        "message": {"model": "claude-opus-5", "content": calls},
                    }
                )
                results = [
                    {
                        "type": "tool_result",
                        "tool_use_id": f"call-{i}",
                        "content": "Launching skill: " + self.target,
                    }
                ]
                events.append(
                    {
                        "type": "user",
                        "session_id": session,
                        "message": {"content": results},
                        "tool_use_result": {
                            "success": True,
                            "commandName": self.target,
                        },
                    }
                )
                injections = [
                    f"Base directory for this skill: {plugin / 'skills/maintaining-issue-pr-relations'}\n\n{source_body}"
                ]
                events.append(
                    {
                        "type": "user",
                        "session_id": session,
                        "isSynthetic": True,
                        "message": {
                            "content": [{"type": "text", "text": injections[0]}]
                        },
                    }
                )
            events.append(
                {
                    "type": "assistant",
                    "session_id": session,
                    "message": {"model": "claude-opus-5", "content": content},
                }
            )
            events.append(
                {
                    "type": "result",
                    "session_id": session,
                    "subtype": "success",
                    "is_error": False,
                    "result": "Constructed selection response.",
                    "permission_denials": [],
                }
            )
            if i == 0 and native_mutation:
                native_mutation(events)
            stdout = (
                b"\n".join(json.dumps(e, ensure_ascii=False).encode() for e in events)
                + b"\n"
            )
            command = [
                "claude",
                "-p",
                "--verbose",
                "--output-format",
                "stream-json",
                "--no-session-persistence",
                "--session-id",
                session,
                "--model",
                "claude-opus-5",
                "--effort",
                "high",
                "--permission-mode",
                "dontAsk",
                "--setting-sources",
                "",
                "--strict-mcp-config",
                "--mcp-config",
                '{"mcpServers":{}}',
                "--no-chrome",
                "--settings",
                json.dumps(settings, separators=(",", ":")),
                "--restricted",
                "--plugin-dir",
                str(plugin),
                "--tools",
                "Skill",
                "--allowedTools",
                "Skill",
                "--debug-file",
                str(directory / "debug.log"),
            ]
            record = {
                "id": spec["id"],
                "kind": "trigger",
                "session_id": session,
                "started_at": "2026-01-01T00:00:00+00:00",
                "finished_at": "2026-01-01T00:00:01+00:00",
                "model_requested": "claude-opus-5",
                "effort_requested": "high",
                "request_sha256": self.sha(spec["request"].encode()),
                "response": "Constructed selection response.",
                "response_sha256": self.sha(b"Constructed selection response."),
                "stdout_sha256": self.sha(stdout),
                "stderr_sha256": self.sha(b""),
                "exit_code": 0,
                "timed_out": False,
                "init": init,
                "assistant_models": ["claude-opus-5"],
                "tool_calls": calls,
                "result_subtype": "success",
                "result_is_error": False,
                "permission_denials": [],
                "parse_errors": [],
            }
            for name, value in {
                "record.json": record,
                "spec.json": {k: v for k, v in spec.items() if k != "request"},
                "request.txt": spec["request"].encode(),
                "command.json": command,
                "stdout.jsonl": stdout,
                "stderr.txt": b"",
                "debug.log": b"getSkills returning: 0 skill dir commands, 1 plugin skills, 1 bundled skills, 0 builtin plugin skills\n",
            }.items():
                self.write(directory / name, value)
            injection_rows = [
                {
                    "original_text_sha256": self.sha(t.encode()),
                    "source_body_sha256": self.sha(source_body.encode()),
                    "source_body_exact_match": True,
                }
                for t in injections
            ]
            grade = json.loads((self.native / "grader-cases.json").read_bytes())[i]
            packet = {
                "case_id": i,
                "request": spec["request"],
                "request_sha256": record["request_sha256"],
                "candidate_sha256": spec["candidate_sha256"],
                "expectation": grade,
                "response": {
                    k: record[k]
                    for k in (
                        "id",
                        "session_id",
                        "response",
                        "response_sha256",
                        "assistant_models",
                        "effort_requested",
                        "exit_code",
                        "timed_out",
                        "result_is_error",
                        "tool_calls",
                    )
                },
                "init": {
                    k: init[k]
                    for k in (
                        "tools",
                        "skills",
                        "plugins",
                        "mcp_servers",
                        "model",
                        "claude_code_version",
                    )
                },
                "skill_tool_results": results,
                "skill_injections": injections,
                "raw_record_sha256": self.sha((directory / "record.json").read_bytes()),
                "configuration_evidence_sha256": self.sha(
                    self.configuration.read_bytes()
                ),
            }
            self.write(
                collection / f"grading-inputs/triggers/case-{i:02d}.json", packet
            )
            isolation_rows.append(
                {
                    "run_id": spec["id"],
                    "command_sha256": self.sha(
                        (directory / "command.json").read_bytes()
                    ),
                    "debug_sha256": self.sha((directory / "debug.log").read_bytes()),
                    "tools": ["Skill"],
                    "mcp_servers": [],
                    "loaded_plugin_names": ["mergecraft-scope-eval"],
                    "skill_directory_commands": 0,
                    "candidate_plugin_skills": 1,
                    "bundled_runtime_skill_descriptions_retained": True,
                    "bundled_runtime_skills_debug_count": 1,
                    "other_initialized_skill_descriptions": ["bundled-helper"],
                    "claudeMdExcludes": ["**"],
                    "skill_injections": injection_rows,
                }
            )
        self.write(
            collection / "native-isolation-report.json",
            {
                "schema_version": 1,
                "configuration_evidence_sha256": self.sha(
                    self.configuration.read_bytes()
                ),
                "configuration_evidence_cli_version": "2.1.273",
                "configuration_evidence_executable_sha256": self.sha(
                    Path(sys.executable).read_bytes()
                ),
                "managed_policy_contents_captured": False,
                "limitations": ["Constructed only."],
                "runs": isolation_rows,
            },
        )
        self.write(
            collection / "index.json",
            {
                "schema_version": 1,
                "stage": "native-record-collection",
                "model_executed": False,
                "native_records_collected": 13,
                "prepared_index_sha256": self.sha(
                    (self.native / "index.json").read_bytes()
                ),
                "candidate_manifest_sha256": index["manifest_sha256"],
                "configuration_evidence_sha256": self.sha(
                    self.configuration.read_bytes()
                ),
                "adapter_sha256": index["adapter_sha256"],
                "producer_source_sha256": index["producer_source_sha256"],
                "semantic_grades_produced": False,
                "limitations": ["Constructed only."],
                "files_sha256": {
                    str(p.relative_to(collection)): self.sha(p.read_bytes())
                    for p in collection.rglob("*")
                    if p.is_file()
                },
            },
        )
        self.observations = self.write(
            self.root / "observations.json",
            {
                "schema_version": 1,
                "application_packets": packets,
                "native_collection": self.ref(collection / "index.json"),
                "configuration": self.ref(self.configuration),
            },
        )
        self.receipts = self.root / "receipt-artifacts"

    def observe(self, *, helper="scripts/mergecraft_writing_evals.py"):
        return self.command(
            "receipt-observe",
            "--binding",
            self.binding,
            "--binding-sha256",
            self.sha(self.binding.read_bytes()),
            "--observations",
            self.observations,
            "--output",
            self.receipts,
            helper=helper,
        )

    def test_observation_preserves_response_bytes_and_derives_native_booleans(self):
        self.observe_fixture()
        result = self.observe()
        self.assertEqual(result.returncode, 0, result.stderr)
        index = json.loads((self.receipts / "observation-index.json").read_bytes())
        self.assertEqual(len(index["runs"]), 51)
        self.assertEqual(len(index["triggers"]), 13)
        first = json.loads(
            (self.receipts / index["runs"][0]["executor_output"]).read_bytes()
        )
        self.assertEqual(first["response"], "Constructed application\u2028response\r\n")
        triggers = [
            json.loads((self.receipts / row["observation"]).read_bytes())["triggered"]
            for row in index["triggers"]
        ]
        self.assertEqual(triggers, [True] * 5 + [False] * 8)
        lineage = index["triggers"][0]["lineage"]
        self.assertEqual(
            lineage["injection_association"],
            "inferred-from-unique-call-adjacent-result-and-source-body",
        )
        self.assertEqual(lineage["call"]["pointer"], "/1/message/content/0")
        self.assertEqual(lineage["injection"]["pointer"], "/3/message/content/0/text")
        self.assertFalse((self.receipts / "results.json").exists())

    def grade_fixture(self):
        """Literal constructed judgments exercise projection, never semantic grading."""
        descriptor = json.loads(self.descriptor.read_bytes())
        observed = json.loads((self.receipts / "observation-index.json").read_bytes())
        cases = {c["case_id"]["id"]: c for c in descriptor["cases"]}
        references = []
        for row in observed["runs"]:
            case = cases[row["case_id"]["id"]]
            grades = [
                {
                    "text": e["text"],
                    "passed": not (
                        e["id"] == "relation-dependency-only-skip-noncontribution-reads"
                        and row["repetition"] == 1
                    ),
                    "evidence": "Constructed Boolean for a projection test; no response assessment.",
                }
                for e in case["expectations"]
            ]
            original = self.write(
                self.root
                / "original-grades"
                / f"{case['id']}-{row['repetition']}.json",
                {
                    "run_id": row["run_id"],
                    "response_sha256": row["response_sha256"],
                    "grader_task": "constructed-independent-grader",
                    "grader_distinct_from_executor": True,
                    "expectations": grades,
                },
            )
            references.append(
                {
                    "run_id": row["run_id"],
                    "record": self.ref(original),
                    "grader_model": {
                        "id": "fixture-grader",
                        "basis": "configured",
                        "reference": self.ref(
                            self.grader_model, format="utf8", pointer=""
                        ),
                    },
                    "previous_grading": [],
                    "adjudication": None,
                }
            )
        self.grading = self.write(
            self.root / "grading-references.json",
            {"schema_version": 1, "runs": references},
        )
        self.finalized = self.root / "finalized"

    def finalize(self, *, helper="scripts/mergecraft_writing_evals.py"):
        return self.command(
            "receipt-results",
            "--binding",
            self.binding,
            "--binding-sha256",
            self.sha(self.binding.read_bytes()),
            "--observation-index",
            self.receipts / "observation-index.json",
            "--observation-index-sha256",
            self.sha((self.receipts / "observation-index.json").read_bytes()),
            "--grading",
            self.grading,
            "--output",
            self.finalized,
            helper=helper,
        )

    def test_identical_copied_recorder_is_retained_and_later_drift_preserves_outputs(
        self,
    ):
        helper = self.copy_receipt_equipment(self.root / "copied-equipment")
        self.observe_fixture(helper=helper)
        binding_bytes = self.binding.read_bytes()
        binding = json.loads(binding_bytes)
        retained = [row for row in binding["inputs"] if row["path"] == str(helper)]
        self.assertEqual(len(retained), 1)
        self.assertEqual(retained[0]["sha256"], self.sha(helper.read_bytes()))
        self.assertEqual(retained[0]["mode"], helper.stat().st_mode & 0o777)
        original, mode = helper.read_bytes(), helper.stat().st_mode & 0o777
        for change in ("bytes", "mode"):
            with self.subTest(stage="observe", change=change):
                if change == "bytes":
                    helper.write_bytes(original + b"\n# Drift after binding.\n")
                else:
                    helper.chmod(0o644)
                refused = self.observe(helper=helper)
                self.assertNotEqual(refused.returncode, 0)
                self.assertIn(
                    "input digest differs"
                    if change == "bytes"
                    else "retained input mode differs",
                    refused.stderr,
                )
                self.assertFalse(self.receipts.exists())
                self.assertEqual(self.binding.read_bytes(), binding_bytes)
                helper.write_bytes(original)
                helper.chmod(mode)
        observed = self.observe(helper=helper)
        self.assertEqual(observed.returncode, 0, observed.stderr)
        self.grade_fixture()
        finalized = self.finalize(helper=helper)
        self.assertEqual(finalized.returncode, 0, finalized.stderr)
        prior_outputs = {self.binding: binding_bytes}
        for directory in (self.receipts, self.finalized):
            prior_outputs.update(
                {
                    path: path.read_bytes()
                    for path in directory.rglob("*")
                    if path.is_file()
                }
            )
        self.finalized = self.root / "new-results-after-drift"
        helper.write_bytes(original + b"\n# Drift after finalized outputs.\n")
        refused = self.finalize(helper=helper)
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("input digest differs", refused.stderr)
        self.assertFalse(self.finalized.exists())
        for path, raw in prior_outputs.items():
            self.assertEqual(path.read_bytes(), raw)

    def test_final_results_roundtrip_preserves_false_grade_and_member_three_of_three(
        self,
    ):
        self.observe_fixture()
        observed = self.observe()
        self.assertEqual(observed.returncode, 0, observed.stderr)
        self.grade_fixture()
        result = self.finalize()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads((self.finalized / "member-report.json").read_bytes())
        self.assertEqual(
            report["ordinary"],
            {
                "status": "pass",
                "reason": "threshold satisfied",
                "trigger_precision": {"correct": 13, "total": 13},
            },
        )
        self.assertFalse(report["member_passed"])
        self.assertEqual(len(report["expectations"]), 65)
        self.assertEqual(sum(e["passes"] for e in report["expectations"]), 194)
        self.assertEqual(
            [e["id"] for e in report["expectations"] if not e["passed"]],
            ["relation-dependency-only-skip-noncontribution-reads"],
        )
        results = json.loads((self.finalized / "results.json").read_bytes())
        self.assertEqual(len(results["runs"]), 51)
        self.assertEqual(len(results["triggers"]), 13)
        first = results["runs"][0]
        grade = json.loads((self.finalized / first["grading"]).read_bytes())
        self.assertEqual(
            grade["executor_output_sha256"],
            self.sha((self.finalized / first["executor_output"]).read_bytes()),
        )
        lineage = json.loads((self.finalized / "lineage.json").read_bytes())["runs"][0]
        self.assertNotEqual(
            lineage["response_sha256"], lineage["execution_envelope_sha256"]
        )
        self.assertNotEqual(
            lineage["original_grader_sha256"], lineage["grading_envelope_sha256"]
        )
        produced = self.command(
            "produce",
            "--snapshot",
            self.snapshot,
            "--results",
            self.finalized / "results.json",
            helper="scripts/behavior_eval_receipts.py",
        )
        self.assertEqual(produced.returncode, 0, produced.stderr)
        receipt = json.loads(produced.stdout)
        self.assertEqual(
            receipt, json.loads((self.finalized / "receipt.json").read_bytes())
        )
        self.write(self.repo / "test-receipts" / (self.skill + ".json"), receipt)
        self.git("add", "test-receipts")
        self.git("commit", "-qm", "test: contain constructed public receipt")
        checked = self.command(
            "check",
            "--base",
            self.base_revision,
            "--candidate",
            self.git("rev-parse", "HEAD"),
            "--receipt-root",
            "test-receipts",
            helper="scripts/behavior_eval_inventory.py",
        )
        self.assertEqual(checked.returncode, 0, checked.stderr + checked.stdout)
        self.assertEqual(json.loads(checked.stdout)["affected_skills"], [self.skill])
        self.assertEqual(json.loads(checked.stdout)["status"], "pass")
        self.assertNotEqual(self.finalize().returncode, 0)

    def member_fixture(self, *, all_pass=True):
        self.observe_fixture()
        observed = self.observe()
        self.assertEqual(observed.returncode, 0, observed.stderr)
        self.grade_fixture()
        if all_pass:
            references = json.loads(self.grading.read_bytes())
            for row in references["runs"]:
                path = Path(row["record"]["path"])
                record = json.loads(path.read_bytes())
                for judgment in record["expectations"]:
                    judgment["passed"] = True
                self.write(path, record)
                row["record"] = self.ref(path)
            self.write(self.grading, references)
        finalized = self.finalize()
        self.assertEqual(finalized.returncode, 0, finalized.stderr)
        references = []
        for case, expected in enumerate([True] * 5 + [False] * 8):
            spec = self.native_specs[case]
            record = json.loads(
                (self.runner_base / spec["id"] / "record.json").read_bytes()
            )
            original = self.write(
                self.root / "native-grades" / f"{case:02d}.json",
                {
                    "run_id": spec["id"],
                    "response_sha256": record["response_sha256"],
                    "grader_task": "constructed-independent-native-grader",
                    "grader_distinct_from_executor": True,
                    "expected_should_trigger": expected,
                    "actual_skill_calls": [self.target] if expected else [],
                    "passed": True,
                    "evidence": "Literal constructed native grade; no model assessment.",
                },
            )
            references.append({"run_id": spec["id"], "record": self.ref(original)})
        self.native_grades = self.write(
            self.root / "native-grades.json", {"schema_version": 1, "runs": references}
        )
        self.projection = self.write(
            self.root / "projection.json",
            {
                "schema_version": 1,
                "binding": self.ref(self.binding),
                "final_lineage": self.ref(self.finalized / "lineage.json"),
                "native_grading": self.ref(self.native_grades),
                "supplements": [],
                "history": {
                    "experiment": self.ref(self.repo / self.source / "experiment.json"),
                    "grading": self.ref(self.repo / self.source / "grading.json"),
                },
            },
        )
        self.projected = self.root / "member-projection"
        self.member_history_fixture()

    def member_project(self):
        return self.command(
            "member-project",
            "--projection",
            self.projection,
            "--projection-sha256",
            self.sha(self.projection.read_bytes()),
            "--output",
            self.projected,
        )

    def update_projection_reference(self, key, path):
        value = json.loads(self.projection.read_bytes())
        value[key] = self.ref(path)
        self.write(self.projection, value)

    def test_member_project_requires_original_native_grade_coverage(self):
        self.member_fixture()
        grades = json.loads(self.native_grades.read_bytes())
        grades["runs"].pop()
        self.write(self.native_grades, grades)
        self.update_projection_reference("native_grading", self.native_grades)
        rejected = self.member_project()
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("native grading coverage", rejected.stderr)
        self.assertFalse(self.projected.exists())

    def test_member_project_rejects_any_inconsistent_complete_member_report(self):
        self.member_fixture(all_pass=False)
        report_path = self.finalized / "member-report.json"
        lineage_path = self.finalized / "lineage.json"
        original_report = json.loads(report_path.read_bytes())
        original_lineage = json.loads(lineage_path.read_bytes())
        original_grades = {
            row["record"]["path"]: Path(row["record"]["path"]).read_bytes()
            for row in json.loads(self.grading.read_bytes())["runs"]
        }
        variants = (
            (
                "criterion-id",
                lambda report: report["expectations"][0].update(
                    id="unrelated-criterion"
                ),
            ),
            (
                "criterion-severity",
                lambda report: report["expectations"][0].update(severity="quality"),
            ),
            ("schema-version", lambda report: report.update(schema_version=True)),
            ("limits", lambda report: report.update(limits=[])),
            ("extra-field", lambda report: report.update(unbound_claim="unsupported")),
            (
                "passes-type",
                lambda report: report["expectations"][0].update(passes=3.0),
            ),
            (
                "required-passes",
                lambda report: report["expectations"][0].update(required_passes=2),
            ),
            (
                "ordinary-reason",
                lambda report: report["ordinary"].update(
                    reason="not the computed result"
                ),
            ),
        )
        for name, change in variants:
            with self.subTest(field=name):
                report = json.loads(json.dumps(original_report))
                change(report)
                self.write(report_path, report)
                lineage = json.loads(json.dumps(original_lineage))
                lineage["files_sha256"]["member-report.json"] = self.sha(
                    report_path.read_bytes()
                )
                self.write(lineage_path, lineage)
                self.update_projection_reference("final_lineage", lineage_path)
                self.projected = self.root / ("rejected-member-report-" + name)
                result = self.member_project()
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertFalse(self.projected.exists())
                self.assertEqual(
                    original_grades,
                    {path: Path(path).read_bytes() for path in original_grades},
                )

    def member_validate(self):
        for name in ("experiment.json", "grading.json"):
            shutil.copyfile(self.projected / name, self.repo / self.source / name)
        return subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                (
                    "import sys; from pathlib import Path; sys.path.insert(0, 'scripts'); "
                    "from validate_mergecraft import validate_relation_evidence; "
                    "validate_relation_evidence(Path('.'))"
                ),
            ],
            cwd=self.repo,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_member_project_all_pass_preserves_history_and_passes_public_consumers(
        self,
    ):
        self.member_fixture()
        previous = {
            name: (self.repo / self.source / name).read_bytes()
            for name in ("experiment.json", "grading.json")
        }
        result = self.member_project()
        self.assertEqual(result.returncode, 0, result.stderr)
        experiment = json.loads((self.projected / "experiment.json").read_bytes())
        grading = json.loads((self.projected / "grading.json").read_bytes())
        normalization = json.loads((self.projected / "normalization.json").read_bytes())
        old = json.loads(previous["experiment.json"])
        self.assertEqual(experiment["behavior_runs"][:380], old["behavior_runs"])
        self.assertEqual(
            experiment["native_and_trigger_runs"][:78], old["native_and_trigger_runs"]
        )
        self.assertEqual(
            grading["previous_selected_grading"], json.loads(previous["grading.json"])
        )
        inverse = normalization["history_inverse"]["experiment"]
        recovered = json.loads(json.dumps(experiment))
        for key in inverse["remove_keys"]:
            del recovered[key]
        recovered.update(inverse["replace_values"])
        for key, length in inverse["list_lengths"].items():
            del recovered[key][length:]
        for key in inverse["remove_request_keys"]:
            del recovered["requests_by_sha256"][key]
        self.assertEqual(self.encoded(recovered), previous["experiment.json"])
        self.assertEqual(
            self.encoded(grading["previous_selected_grading"]), previous["grading.json"]
        )
        self.assertEqual(len(experiment["behavior_runs"]), 431)
        self.assertEqual(len(experiment["native_and_trigger_runs"]), 91)
        self.assertEqual(len(experiment["current_source_sha256"]), 45)
        self.assertEqual(len(normalization["runs"]), 64)
        self.assertEqual(
            len({row["projected_run_id"] for row in normalization["runs"]}), 64
        )
        selected = experiment["selection"]["behavior_by_case"]["0"]
        self.assertEqual(selected, "relation-" + self.sha(self.binding.read_bytes()))
        self.assertTrue(grading["candidate_passed"])
        self.assertEqual(sum(t["passes"] for t in grading["thresholds"]), 195)
        self.assertEqual(
            experiment["behavior_runs"][380]["response"],
            "Constructed application\u2028response\r\n",
        )
        self.assertEqual(
            grading["runs"][0]["original_run_id"], "relations/case-00-with-skill-1"
        )
        native = experiment["native_and_trigger_runs"][78]
        self.assertEqual(native["init"]["plugins"][0]["path"], "<CANDIDATE_PLUGIN>")
        self.assertEqual(native["invocation"]["argv"][-1], "<LOCAL_DEBUG_FILE>")
        self.assertNotEqual(
            native["skill_injections"][0]["original_text_sha256"],
            native["skill_injections"][0]["retained_text_sha256"],
        )
        consumed = self.member_validate()
        self.assertEqual(consumed.returncode, 0, consumed.stderr)
        produced = self.command(
            "produce",
            "--snapshot",
            self.snapshot,
            "--results",
            self.finalized / "results.json",
            helper="scripts/behavior_eval_receipts.py",
        )
        self.assertEqual(produced.returncode, 0, produced.stderr)
        self.assertEqual(
            json.loads(produced.stdout),
            json.loads((self.finalized / "receipt.json").read_bytes()),
        )
        self.write(
            self.repo / "test-receipts" / (self.skill + ".json"),
            json.loads(produced.stdout),
        )
        self.git("add", self.source, "test-receipts")
        self.git("commit", "-qm", "test: project constructed relation member evidence")
        checked = self.command(
            "check",
            "--base",
            self.base_revision,
            "--candidate",
            self.git("rev-parse", "HEAD"),
            "--receipt-root",
            "test-receipts",
            helper="scripts/behavior_eval_inventory.py",
        )
        self.assertEqual(checked.returncode, 0, checked.stderr + checked.stdout)
        self.assertEqual(json.loads(checked.stdout)["status"], "pass")
        before = {p.name: p.read_bytes() for p in self.projected.iterdir()}
        rejected = self.member_project()
        self.assertNotEqual(rejected.returncode, 0)
        self.assertEqual(
            before, {p.name: p.read_bytes() for p in self.projected.iterdir()}
        )

    def member_history_fixture(self, *, writer_digest_change=None):
        """Constructed originals test retention arithmetic, never semantic validity."""
        inputs = {}
        history_root = self.root / "history"
        if writer_digest_change is not None:
            field, value = writer_digest_change
            suffix = field + ("-missing" if value is None else "-conflicting")
            history_root = self.root / ("history-" + suffix)

        def retained(path, value):
            self.write(path, value)
            ref = self.ref(path)
            inputs[str(path)] = {
                "sha256": ref["sha256"],
                "bytes": path.stat().st_size,
                "mode": format(path.stat().st_mode & 0o777, "04o"),
            }
            return {**ref, **inputs[str(path)]}

        def canonical(value):
            return self.sha(
                json.dumps(
                    value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
                ).encode()
            )

        def batch(
            name,
            completed_count,
            judgments_count,
            false_count,
            supplement_count,
            writer=False,
        ):
            root = history_root / name
            source_map = {}
            for n in range(57 if writer else 32):
                path = root / "source" / f"fixtures/history-{n:02d}.txt"
                ref = retained(path, b"Constructed historical source.\n")
                source_map[f"fixtures/history-{n:02d}.txt"] = ref["sha256"]
            specs, completed, unlaunched, archive_rows, grades = [], [], [], [], []
            for n in range(51):
                case, rep = divmod(n, 3)
                run_id = f"{name}/case-{case:02d}-with-skill-{rep + 1}"
                request = "Constructed historical request " + run_id
                spec = {
                    "id": run_id,
                    "case_id": case,
                    "repetition": rep + 1,
                    "request": request,
                    "fixture_sha256": {},
                    "candidate_sha256": source_map,
                }
                specs.append(spec)
                metadata = {
                    "run_id": run_id,
                    "case_id": case,
                    "repetition": rep + 1,
                    "request_sha256": self.sha(request.encode()),
                    "fixture_sha256": {},
                    "candidate_sha256": source_map,
                    "spec_object_sha256": canonical(spec),
                }
                if n >= completed_count:
                    unlaunched.append({**metadata, "response_record_exists": False})
                    continue
                directory = (root / "runs" if writer else root.parent) / run_id
                response = "Constructed historical response " + run_id
                record = {
                    "id": run_id,
                    "session_id": "historical-" + run_id,
                    "response": response,
                    "response_sha256": self.sha(response.encode()),
                    "request_sha256": self.sha(request.encode()),
                    "exit_code": 0,
                    "result_is_error": False,
                    "timed_out": False,
                    "stdout_sha256": self.sha(b"Constructed stream bytes"),
                    "stderr_sha256": self.sha(b""),
                }
                if writer:
                    record["command_sha256"] = self.sha(
                        self.encoded(["constructed-not-executed"])
                    )
                    record["result"] = {
                        "type": "result",
                        "subtype": "success",
                        "is_error": False,
                        "session_id": record["session_id"],
                        "result": response,
                    }
                    del record["response"]
                    del record["result_is_error"]
                    if n == 0 and writer_digest_change is not None:
                        field, value = writer_digest_change
                        if value is None:
                            del record[field]
                        else:
                            record[field] = value
                record_ref = retained(directory / "record.json", record)
                artifacts = [
                    retained(
                        directory / "spec.json",
                        {k: v for k, v in spec.items() if k != "request"},
                    ),
                    retained(directory / "request.txt", request.encode()),
                ]
                if writer:
                    artifacts += [
                        retained(directory / "response.txt", response.encode()),
                        retained(
                            directory / "stdout.jsonl", b"Constructed stream bytes"
                        ),
                        retained(directory / "stderr.txt", b""),
                        retained(
                            directory / "command.json", ["constructed-not-executed"]
                        ),
                    ]
                completed.append(
                    {
                        **metadata,
                        "record": record_ref,
                        "response_record_exists": True,
                        "response_sha256": self.sha(response.encode()),
                    }
                )
                count = judgments_count // completed_count + (
                    n < judgments_count % completed_count
                )
                grade = {
                    "run_id": run_id,
                    "response_sha256": self.sha(response.encode()),
                    "record_sha256": record_ref["sha256"],
                    "request_sha256": self.sha(request.encode()),
                    "expectations": [
                        {
                            "text": f"Constructed historical criterion {i}",
                            "passed": not (n < false_count and i == 0),
                            "evidence": "Constructed Boolean, not an assessment.",
                        }
                        for i in range(count)
                    ],
                }
                grades.append(grade)
                archive_rows.append(
                    {
                        "original_run_id": run_id,
                        "original_record": record_ref,
                        "artifacts": artifacts,
                        "session_id": record["session_id"],
                        "request_sha256": self.sha(request.encode()),
                        "response_sha256": self.sha(response.encode()),
                    }
                )
            specifications = retained(root / "behavior-specs.json", specs)
            cases = retained(root / "grader-cases.json", [{"constructed": True}])
            manifest_value = {
                "source_sha256": source_map,
                "candidate_commit": None,
                "artifact_sha256": {
                    str(p.relative_to(root)): self.sha(p.read_bytes())
                    for p in root.rglob("*")
                    if p.is_file() and "runs" not in p.relative_to(root).parts
                },
            }
            manifest = retained(root / "manifest.json", manifest_value)
            supplements = [
                {
                    "run_id": grades[n % len(grades)]["run_id"],
                    "response_sha256": grades[n % len(grades)]["response_sha256"],
                    "observation": f"Constructed historical supplement {n}",
                }
                for n in range(supplement_count)
            ]
            grade_value = {
                "source_binding": {
                    "manifest_sha256": manifest["sha256"],
                    "source_sha256": source_map,
                    "behavior_specs_sha256": specifications["sha256"],
                    "grader_cases_sha256": cases["sha256"],
                },
                "runs" if not writer else "results": grades,
                "supplementary_observations": supplements,
            }
            if writer:
                grade_value["input_manifest"] = {"sha256": manifest["sha256"]}
            grade_ref = retained(root / "original-grade.json", grade_value)
            adjudication = retained(
                root / "adjudication.json", {"judgments_unchanged": True}
            )
            batch = {
                "name": name,
                "manifest": manifest,
                "manifest_value": manifest_value,
                "specifications": specifications,
                "grader_cases": cases,
                "completed": completed,
                "unlaunched": unlaunched,
                "completed_count": len(completed),
                "unlaunched_count": len(unlaunched),
                "grades": [{"artifact": grade_ref}],
                "adjudication": adjudication,
                "adjudication_value": {"judgments_unchanged": True},
            }
            if writer:
                dispositions = [
                    {
                        "observation_sha256": canonical(o),
                        "original_observation": o,
                        "run_id": o["run_id"],
                        "original_grade": grade_ref,
                        "response": next(
                            r
                            for row in archive_rows
                            if row["original_run_id"] == o["run_id"]
                            for r in row["artifacts"]
                            if Path(r["path"]).name == "response.txt"
                        ),
                        "determination": "historical_model_inaccuracy",
                    }
                    for o in supplements
                ]
                source = retained(root / "source-map.json", {"constructed": True})
                accepted = retained(
                    root / "supplementary-adjudication.json",
                    {
                        "source_map_sha256": source["sha256"],
                        "observations": dispositions,
                    },
                )
                batch = {
                    "name": name,
                    "source_manifest": manifest,
                    "manifest_value": manifest_value,
                    "grades": [{"artifact": grade_ref}],
                    "accepted_supplementary_adjudication": accepted,
                    "source_map": source,
                    "supplementary_dispositions": [
                        {
                            "observation_sha256": d["observation_sha256"],
                            "run_id": d["run_id"],
                            "determination": d["determination"],
                            "original_grade": grade_ref,
                            "response_sha256": d["response"]["sha256"],
                            "changes_original_grade": False,
                        }
                        for d in dispositions
                    ],
                }
                archive = retained(
                    root / "archive.json",
                    {"archive": str(root), "manifest": manifest, "runs": archive_rows},
                )
                return batch, archive
            return batch

        stopped = [batch("pr84-v1", 37, 145, 2, 14), batch("pr84-v2", 3, 18, 1, 3)]
        writer, archive = batch("writer-diagnostic", 51, 195, 4, 15, writer=True)
        projection = json.loads(self.projection.read_bytes())
        history = projection["history"]
        inventory = retained(
            history_root / "inventory.json",
            {
                "schema_version": 1,
                "inputs": inputs.copy(),
                "current_owning_evidence": {
                    "experiment": history["experiment"],
                    "grading": history["grading"],
                },
                "stopped_history": stopped,
                "writer_composition_diagnostic": writer,
            },
        )
        history.update(inventory=inventory, writer_archive=archive, copies=[])
        self.write(self.projection, projection)
        self.history_inventory = Path(inventory["path"])
        self.history_archive = Path(archive["path"])

    def test_member_project_requires_every_original_writer_artifact_digest(self):
        self.member_fixture(all_pass=False)
        variants = (
            ("command_sha256", "0" * 64),
            ("response_sha256", "0" * 64),
            ("command_sha256", None),
            ("response_sha256", None),
            ("request_sha256", "0" * 64),
            ("stdout_sha256", "0" * 64),
            ("stderr_sha256", "0" * 64),
        )
        for field, value in variants:
            with self.subTest(field=field, value=value):
                self.member_history_fixture(writer_digest_change=(field, value))
                inventory = json.loads(self.history_inventory.read_bytes())
                original_grades = {
                    row["artifact"]["path"]: Path(row["artifact"]["path"]).read_bytes()
                    for row in inventory["writer_composition_diagnostic"]["grades"]
                }
                suffix = field + ("-missing" if value is None else "-conflicting")
                self.projected = self.root / ("rejected-writer-" + suffix)
                result = self.member_project()
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertFalse(self.projected.exists())
                self.assertEqual(
                    original_grades,
                    {path: Path(path).read_bytes() for path in original_grades},
                )

    def test_member_project_retains_later_diagnostics_and_verifies_original_archive(
        self,
    ):
        self.member_fixture()
        result = self.member_project()
        self.assertEqual(result.returncode, 0, result.stderr)
        projected = json.loads((self.projected / "experiment.json").read_bytes())
        history = projected["retained_private_history"]
        self.assertEqual(
            [
                (r["completed"], r["unlaunched"], r["judgments"], r["passed"])
                for r in history["batches"]
            ],
            [(37, 14, 145, 143), (3, 48, 18, 17), (51, 0, 195, 191)],
        )
        self.assertEqual(
            [len(r["supplements"]) for r in history["batches"]], [14, 3, 15]
        )
        self.assertTrue(
            all(r["disposition"] is None for r in history["batches"][0]["supplements"])
        )
        self.assertEqual(
            history["batches"][2]["supplements"][0]["disposition"],
            "historical_model_inaccuracy",
        )
        self.assertEqual(len(projected["behavior_runs"]), 431)
        public = json.dumps(history)
        self.assertNotIn(str(self.root), public)
        self.assertIn("original_run_id", public)
        self.assertIn("original_grade", public)
        self.assertNotIn("Constructed historical response", public)
        archive = json.loads(self.history_archive.read_bytes())
        response = next(
            Path(r["path"])
            for r in archive["runs"][-1]["artifacts"]
            if Path(r["path"]).name == "response.txt"
        )
        response.write_bytes(response.read_bytes() + b" drift")
        self.projected = self.root / "rejected-historical-drift"
        rejected = self.member_project()
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("input digest differs", rejected.stderr)
        self.assertFalse(self.projected.exists())

    def test_member_project_requires_complete_current_supplement_dispositions(self):
        self.member_fixture()
        # Add a literal observation to an original grade before a fresh finalization.
        references = json.loads(self.grading.read_bytes())
        record_path = Path(references["runs"][0]["record"]["path"])
        original = json.loads(record_path.read_bytes())
        finding = {
            "run_id": original["run_id"],
            "response_sha256": original["response_sha256"],
            "observation": "Constructed supplementary observation separate from rubric results.",
        }
        original["supplementary_observations"] = [finding]
        self.write(record_path, original)
        references["runs"][0]["record"] = self.ref(record_path)
        self.write(self.grading, references)
        self.finalized = self.root / "finalized-with-supplement"
        finalized = self.finalize()
        self.assertEqual(finalized.returncode, 0, finalized.stderr)
        self.update_projection_reference(
            "final_lineage", self.finalized / "lineage.json"
        )
        rejected = self.member_project()
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("supplementary disposition coverage", rejected.stderr)
        self.assertFalse(self.projected.exists())
        disposition = self.write(
            self.root / "supplement-disposition.json",
            {
                "observation_sha256": self.sha(
                    json.dumps(
                        finding,
                        sort_keys=True,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ).encode()
                ),
                "run_id": finding["run_id"],
                "response_sha256": finding["response_sha256"],
                "determination": "Constructed owner assessment for this literal test finding.",
                "source_revision": self.revision,
            },
        )
        projection = json.loads(self.projection.read_bytes())
        projection["supplements"] = [
            {
                "observation": self.ref(
                    record_path, pointer="/supplementary_observations/0"
                ),
                "disposition": self.ref(disposition),
            }
        ]
        self.write(self.projection, projection)
        accepted = self.member_project()
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        grading = json.loads((self.projected / "grading.json").read_bytes())
        supplement = grading["supplementary_dispositions"][0]
        self.assertEqual(supplement["original_observation"], finding)
        self.assertEqual(
            supplement["original_disposition"], json.loads(disposition.read_bytes())
        )
        self.assertFalse(supplement["changes_original_grade"])
        self.assertTrue(grading["candidate_passed"])

    def test_member_project_false_quality_and_independent_native_verdict_remain_false(
        self,
    ):
        self.member_fixture(all_pass=False)
        result = self.member_project()
        self.assertEqual(result.returncode, 0, result.stderr)
        grading = json.loads((self.projected / "grading.json").read_bytes())
        self.assertFalse(grading["candidate_passed"])
        self.assertEqual(sum(r["passes"] for r in grading["thresholds"]), 194)
        report = json.loads((self.projected / "verification-report.json").read_bytes())
        self.assertEqual(report["ordinary"]["status"], "pass")
        consumed = self.member_validate()
        self.assertNotEqual(consumed.returncode, 0)
        self.assertIn("failed behavior expectation", consumed.stderr)
        # Restore the immutable historical inputs after the disposable consumer check.
        # Each new command below reads separate original history copies.
        source_history = ROOT / self.source
        for name in ("experiment.json", "grading.json"):
            shutil.copyfile(source_history / name, self.repo / self.source / name)
        references = json.loads(self.grading.read_bytes())
        for index, row in enumerate(references["runs"]):
            original = json.loads(Path(row["record"]["path"]).read_bytes())
            if any(not judgment["passed"] for judgment in original["expectations"]):
                old_reference = row["record"]
                for judgment in original["expectations"]:
                    judgment["passed"] = True
                copy = self.write(
                    self.root / "second-constructed-grades" / f"{index}.json", original
                )
                row["record"] = self.ref(copy)
                row["previous_grading"] = [old_reference]
        second_grading = self.write(
            self.root / "second-grading-references.json", references
        )
        self.grading = second_grading
        self.finalized = self.root / "all-pass-applications-native-false"
        finalized = self.finalize()
        self.assertEqual(finalized.returncode, 0, finalized.stderr)
        self.update_projection_reference(
            "final_lineage", self.finalized / "lineage.json"
        )
        native = json.loads(self.native_grades.read_bytes())
        path = Path(native["runs"][0]["record"]["path"])
        grade = json.loads(path.read_bytes())
        grade["passed"] = False
        grade["evidence"] = (
            "Literal independent false verdict, even with a matching observed selection."
        )
        self.write(path, grade)
        native["runs"][0]["record"] = self.ref(path)
        self.write(self.native_grades, native)
        self.update_projection_reference("native_grading", self.native_grades)
        self.projected = self.root / "native-false-projection"
        result = self.member_project()
        self.assertEqual(result.returncode, 0, result.stderr)
        projected_grading = json.loads((self.projected / "grading.json").read_bytes())
        self.assertFalse(projected_grading["trigger_runs"][0]["passed"])
        self.assertFalse(projected_grading["candidate_passed"])
        self.assertEqual(
            sum(row["passes"] for row in projected_grading["thresholds"]), 195
        )

    def test_member_project_rejects_native_grade_conflicts_and_preserves_existing_outputs(
        self,
    ):
        self.member_fixture()
        original = self.native_grades.read_bytes()
        first_path = Path(json.loads(original)["runs"][0]["record"]["path"])
        first = first_path.read_bytes()
        for name, change in (
            ("duplicate", lambda rows: rows["runs"].__setitem__(-1, rows["runs"][0])),
            ("extra", lambda rows: rows["runs"].append(rows["runs"][0])),
        ):
            with self.subTest(name=name):
                value = json.loads(original)
                change(value)
                self.write(self.native_grades, value)
                self.update_projection_reference("native_grading", self.native_grades)
                result = self.member_project()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("native grading coverage", result.stderr)
                self.assertFalse(self.projected.exists())
        for name, change in (
            ("response", lambda grade: grade.update(response_sha256="0" * 64)),
            (
                "independence",
                lambda grade: grade.update(grader_distinct_from_executor=False),
            ),
            ("calls", lambda grade: grade.update(actual_skill_calls=[])),
            ("Boolean", lambda grade: grade.update(passed=1)),
        ):
            with self.subTest(name=name):
                value = json.loads(first)
                change(value)
                self.write(first_path, value)
                rows = json.loads(original)
                rows["runs"][0]["record"] = self.ref(first_path)
                self.write(self.native_grades, rows)
                self.update_projection_reference("native_grading", self.native_grades)
                result = self.member_project()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("native original grade correspondence", result.stderr)
                self.assertFalse(self.projected.exists())
        self.write(first_path, first)
        self.write(self.native_grades, original)
        self.update_projection_reference("native_grading", self.native_grades)
        self.projected.mkdir()
        sentinel = self.projected / "experiment.json"
        sentinel.write_bytes(b"Existing projection must survive.\n")
        result = self.member_project()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(sentinel.read_bytes(), b"Existing projection must survive.\n")
        self.assertEqual(
            [p.name for p in self.projected.iterdir()], ["experiment.json"]
        )
        self.projected = self.repo / "forbidden-projection"
        result = self.member_project()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.projected.exists())

    def test_member_project_rechecks_source_original_bytes_modes_and_final_envelopes(
        self,
    ):
        self.member_fixture()
        binding = json.loads(self.binding.read_bytes())
        cases = [
            self.repo / self.native_paths[0],
            Path(binding["runs"][0]["directory"]) / "record.json",
            Path(binding["runs"][0]["directory"]) / "spec.json",
            Path(json.loads(self.grading.read_bytes())["runs"][0]["record"]["path"]),
            self.finalized / "execution/00.json",
        ]
        for path in cases:
            with self.subTest(path=path.name):
                original = path.read_bytes()
                path.write_bytes(original + b" ")
                rejected = self.member_project()
                self.assertNotEqual(rejected.returncode, 0)
                self.assertFalse(self.projected.exists())
                path.write_bytes(original)
        helper = self.repo / "scripts/mergecraft_writing_evals.py"
        original = helper.read_bytes()
        helper.write_bytes(original + b"\n# Different loaded equipment.\n")
        rejected = self.member_project()
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("input digest differs", rejected.stderr)
        self.assertIn(str(helper), rejected.stderr)
        helper.write_bytes(original)
        original_mode = helper.stat().st_mode & 0o777
        helper.chmod(0o644)
        rejected = self.member_project()
        self.assertNotEqual(rejected.returncode, 0)
        helper.chmod(original_mode)
        self.assertFalse(self.projected.exists())

    def test_member_project_reports_unknown_public_coordinate_without_rewriting_evidence(
        self,
    ):
        self.member_fixture()
        native = json.loads(self.native_grades.read_bytes())
        path = Path(native["runs"][0]["record"]["path"])
        original = json.loads(path.read_bytes())
        original["evidence"] = (
            "See /tmp/unexpected-private-coordinate/response.txt for my evidence."
        )
        self.write(path, original)
        native["runs"][0]["record"] = self.ref(path)
        self.write(self.native_grades, native)
        self.update_projection_reference("native_grading", self.native_grades)
        rejected = self.member_project()
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("public-coordinate conflict", rejected.stderr)
        self.assertFalse(self.projected.exists())
        self.assertEqual(
            json.loads(path.read_bytes())["evidence"], original["evidence"]
        )

    def test_member_project_rejects_history_session_and_request_collisions(self):
        self.member_fixture()
        projection = json.loads(self.projection.read_bytes())
        inventory = json.loads(self.history_inventory.read_bytes())
        base = json.loads((self.repo / self.source / "experiment.json").read_bytes())
        binding = json.loads(self.binding.read_bytes())
        first = json.loads(
            (Path(binding["runs"][0]["directory"]) / "record.json").read_bytes()
        )
        for kind in ("session", "request"):
            with self.subTest(kind=kind):
                value = json.loads(json.dumps(base))
                if kind == "session":
                    value["behavior_runs"][0]["session_id"] = first["session_id"]
                else:
                    value["requests_by_sha256"][first["request_sha256"]] = (
                        "Conflicting constructed request."
                    )
                previous = self.write(
                    self.root / f"history-{kind}-collision.json", value
                )
                projection["history"]["experiment"] = self.ref(previous)
                inventory["current_owning_evidence"]["experiment"] = self.ref(previous)
                self.write(self.history_inventory, inventory)
                projection["history"]["inventory"] = self.ref(self.history_inventory)
                self.write(self.projection, projection)
                result = self.member_project()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(
                    "projected session reused"
                    if kind == "session"
                    else "projected request digest conflict",
                    result.stderr,
                )
                self.assertFalse(self.projected.exists())

    def rewrite_native_stream(self, mutation):
        directory = self.runner_base / self.native_specs[0]["id"]
        raw = (directory / "stdout.jsonl").read_bytes()
        events = [json.loads(line) for line in raw.split(b"\n") if line]
        mutation(events)
        self.write(
            directory / "stdout.jsonl",
            b"\n".join(self.encoded(e).replace(b"\n", b" ") for e in events) + b"\n",
        )
        record = json.loads((directory / "record.json").read_bytes())
        record["stdout_sha256"] = self.sha((directory / "stdout.jsonl").read_bytes())
        self.write(directory / "record.json", record)
        collection = self.root / "native-collection"
        packet_path = collection / "grading-inputs/triggers/case-00.json"
        packet = json.loads(packet_path.read_bytes())
        packet["raw_record_sha256"] = self.sha((directory / "record.json").read_bytes())
        self.write(packet_path, packet)
        index = json.loads((collection / "index.json").read_bytes())
        index["files_sha256"]["grading-inputs/triggers/case-00.json"] = self.sha(
            packet_path.read_bytes()
        )
        self.write(collection / "index.json", index)
        sidecar = json.loads(self.observations.read_bytes())
        sidecar["native_collection"] = self.ref(collection / "index.json")
        self.write(self.observations, sidecar)

    def test_unsupported_assistant_blocks_cannot_be_counted_as_native_observations(
        self,
    ):
        self.observe_fixture()
        self.rewrite_native_stream(
            lambda events: events[-2]["message"]["content"].append(
                {"type": "future-tool-event"}
            )
        )
        result = self.observe()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsupported native assistant block", result.stderr)
        self.assertFalse(self.receipts.exists())

    def test_binding_refuses_source_equipment_mode_and_preexisting_run_drift(self):
        source = self.repo / self.native_paths[0]
        original, mode = source.read_bytes(), source.stat().st_mode & 0o777
        source.write_bytes(original + b"\n")
        self.assertNotEqual(self.bind().returncode, 0)
        source.write_bytes(original)
        source.chmod(mode | 0o111)
        self.assertNotEqual(self.bind().returncode, 0)
        source.chmod(mode)
        method = self.method.read_bytes()
        self.method.write_bytes(method + b"# changed\n")
        self.assertNotEqual(self.bind().returncode, 0)
        self.method.write_bytes(method)
        destination = self.behavior / "runs/relations/case-00-with-skill-1"
        destination.mkdir(parents=True)
        self.assertNotEqual(self.bind().returncode, 0)
        self.assertFalse(self.binding.exists())

    def test_binding_refuses_actual_delivery_absent_from_snapshot(self):
        mapping = self.repo / "release/behavior-eval-input-map.json"
        mapping.write_text(
            self.git(
                "show", self.base_revision + ":release/behavior-eval-input-map.json"
            )
            + "\n"
        )
        data = json.loads(mapping.read_bytes())
        # Restore equipment dependencies only, leaving actual delivered inputs
        # undeclared. This constructed semantic change is deliberately rejected.
        accepted = json.loads(
            self.git("show", self.revision + ":release/behavior-eval-input-map.json")
        )
        row = next(
            e
            for e in accepted["entries"]
            if e["source"]["path"] == self.source + "/policy.json"
        )
        row["behavior_inputs"] = []
        semantic = {
            k: row[k]
            for k in (
                "source",
                "pointer",
                "owners",
                "role",
                "behavior_inputs",
                "dependencies",
            )
        }
        row["review"] = {
            "decision": "accepted",
            "reference": "fixture:constructed-incomplete-delivery",
            "mapping_sha256": self.sha(
                json.dumps(
                    semantic, sort_keys=True, separators=(",", ":"), ensure_ascii=False
                ).encode()
            ),
        }
        data["entries"].append(row)
        self.write(mapping, data)
        self.git("add", str(mapping))
        self.git("commit", "-qm", "test: construct missing delivered input")
        self.revision = self.git("rev-parse", "HEAD")
        self.refresh_snapshot()
        result = self.bind()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("delivered source missing from snapshot", result.stderr)
        self.assertFalse(self.binding.exists())

    def test_native_failures_and_incomplete_records_remain_uncounted(self):
        self.observe_fixture()
        directory = self.runner_base / self.native_specs[0]["id"]
        collection = self.root / "native-collection"
        retained = {
            p: p.read_bytes()
            for p in (
                directory / "stdout.jsonl",
                directory / "record.json",
                collection / "grading-inputs/triggers/case-00.json",
                collection / "index.json",
                self.observations,
            )
        }
        variants = {
            "missing-completion": lambda e: e.pop(),
            "duplicate-completion": lambda e: e.append(e[-1]),
            "non-target": lambda e: e[1]["message"]["content"][0]["input"].update(
                skill="other:skill"
            ),
            "unmatched-result": lambda e: e[2]["message"]["content"][0].update(
                tool_use_id="other-call"
            ),
            "failed-call": lambda e: e[2]["tool_use_result"].update(success=False),
            "repeated-call": lambda e: e[1]["message"]["content"].append(
                dict(e[1]["message"]["content"][0])
            ),
            "missing-injection": lambda e: e.pop(3),
            "wrong-body": lambda e: e[3]["message"]["content"][0].update(
                text="Base directory for this skill: wrong\n\nwrong"
            ),
            "unknown-event": lambda e: e.insert(-1, {"type": "unknown"}),
            "initialization-only": lambda e: e.__delitem__(slice(1, None)),
        }
        for label, mutation in variants.items():
            with self.subTest(label=label):
                for path, raw in retained.items():
                    path.write_bytes(raw)
                self.rewrite_native_stream(mutation)
                before = (directory / "stdout.jsonl").read_bytes()
                result = self.observe()
                self.assertNotEqual(result.returncode, 0, label)
                self.assertFalse(self.receipts.exists())
                self.assertEqual((directory / "stdout.jsonl").read_bytes(), before)

    def test_observed_informational_events_keep_native_correspondence(self):
        self.observe_fixture()

        def informational(events):
            events.insert(2, {"type": "rate_limit_event"})
            events.insert(-1, {"type": "system", "subtype": "thinking_tokens"})

        self.rewrite_native_stream(informational)
        result = self.observe()
        self.assertEqual(result.returncode, 0, result.stderr)
        index = json.loads((self.receipts / "observation-index.json").read_bytes())
        self.assertEqual(
            index["triggers"][0]["lineage"]["result"]["pointer"], "/3/message/content/0"
        )
        self.assertEqual(
            index["triggers"][0]["lineage"]["injection"]["pointer"],
            "/4/message/content/0/text",
        )

    def test_finalization_refuses_changed_observation_and_invalid_original_grades(self):
        self.observe_fixture()
        self.assertEqual(self.observe().returncode, 0)
        self.grade_fixture()
        source = self.repo / self.native_paths[0]
        original = source.read_bytes()
        source.write_bytes(original + b"\n")
        self.assertNotEqual(self.finalize().returncode, 0)
        source.write_bytes(original)
        execution = self.receipts / "execution/00.json"
        raw = execution.read_bytes()
        execution.write_bytes(raw + b"\n")
        self.assertNotEqual(self.finalize().returncode, 0)
        execution.write_bytes(raw)
        sidecar = json.loads(self.grading.read_bytes())
        grade_path = Path(sidecar["runs"][0]["record"]["path"])
        grade_bytes = grade_path.read_bytes()
        mutations = {
            "wrong-response": lambda g: g.update(response_sha256="0" * 64),
            "non-Boolean": lambda g: g["expectations"][0].update(passed=1),
            "wrong-rubric": lambda g: g["expectations"][0].update(
                text="another criterion"
            ),
            "self-grading": lambda g: g.update(grader_distinct_from_executor=False),
            "missing-grade": lambda g: g["expectations"].pop(),
        }
        for label, mutation in mutations.items():
            with self.subTest(label=label):
                grade = json.loads(grade_bytes)
                mutation(grade)
                self.write(grade_path, grade)
                sidecar["runs"][0]["record"] = self.ref(grade_path)
                self.write(self.grading, sidecar)
                result = self.finalize()
                self.assertNotEqual(result.returncode, 0, label)
                self.assertFalse(self.finalized.exists())
                self.assertEqual(json.loads(grade_path.read_bytes()), grade)


if __name__ == "__main__":
    unittest.main()
