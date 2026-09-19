from __future__ import annotations

import ast
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "scripts" / "validate_mergecraft.py"
CONTROL_PLANE_EVALUATOR = REPO_ROOT / "scripts" / "run_control_plane_eval.py"
PLUGIN = Path("plugins/mergecraft")
EVAL_ROOT = Path("evals/mergecraft")
CONTENT_LOCK = Path("release/plugin-content-locks/mergecraft.json")
ATLAS_RELEASE = Path("release/mergecraft")
RETIREMENT_LEDGER = Path("release/mergecraft-retirement-contribution-ledger.json")
MARKDOWN_AUTHORING_SKILL = "writing-github-issue-and-pr-markdown"
MARKDOWN_AUTHORING_SOURCE = Path(
    "skills/writing-github-issue-and-pr-markdown/references/authoring-contract.md"
)
MARKDOWN_AUTHORING_PROJECTIONS = {
    "writing-reviewable-pr-descriptions": Path(
        "references/github-markdown-authoring.md"
    ),
    "interacting-with-pr-review-feedback": Path(
        "references/github-markdown-authoring.md"
    ),
    "getting-prs-merged": Path("references/github-markdown-authoring.md"),
}
AGENT_PLUGIN_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
CANONICAL_IDENTITY_FIELDS = (
    "name",
    "version",
    "description",
    "author",
    "homepage",
    "repository",
    "license",
    "keywords",
)
SPEC = importlib.util.spec_from_file_location("validate_mergecraft", VALIDATOR)
assert SPEC is not None and SPEC.loader is not None
VALIDATE_MERGECRAFT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATE_MERGECRAFT)


class AuthorityGuardRemover(ast.NodeTransformer):
    def __init__(self, field: str) -> None:
        self.field = field
        self.removed = 0

    def visit_Compare(self, node: ast.Compare) -> ast.expr:
        self.generic_visit(node)
        left = node.left
        if (
            isinstance(left, ast.Subscript)
            and isinstance(left.value, ast.Name)
            and left.value.id == "authority"
            and isinstance(left.slice, ast.Constant)
            and left.slice.value == self.field
        ):
            self.removed += 1
            return ast.copy_location(ast.Constant(value=False), node)
        return node


class CheckedInMergecraftReleaseTests(unittest.TestCase):
    def test_checked_in_content_lock_matches_current_plugin_before_test_mutation(
        self,
    ) -> None:
        plugin = VALIDATE_MERGECRAFT.locate_plugin(REPO_ROOT)
        VALIDATE_MERGECRAFT.validate_content_lock(REPO_ROOT, plugin)


class ValidateMergecraftTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary_directory.name) / "repo"
        shutil.copytree(
            REPO_ROOT / PLUGIN,
            self.repo / PLUGIN,
            symlinks=True,
        )
        shutil.copytree(REPO_ROOT / EVAL_ROOT, self.repo / EVAL_ROOT, symlinks=True)
        for skill in ("addressing-pr-review-feedback", "interacting-with-pr-review-feedback"):
            relative = Path("tests/plugins/mergecraft") / skill
            shutil.copytree(REPO_ROOT / relative, self.repo / relative, symlinks=True)
        shutil.copytree(
            REPO_ROOT / ATLAS_RELEASE,
            self.repo / ATLAS_RELEASE,
            symlinks=True,
        )
        (self.repo / RETIREMENT_LEDGER).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / RETIREMENT_LEDGER, self.repo / RETIREMENT_LEDGER)
        for plugin in ("tricritical", "versionkeeping"):
            external = self.repo / "plugins" / plugin
            external.mkdir(parents=True)
            shutil.copy2(REPO_ROOT / "plugins" / plugin / "topology.json", external)
        for relative in (
            Path("plugins/proseweaving/topology.json"),
            *(Path(path) for path in VALIDATE_MERGECRAFT.MARKDOWN_BUNDLE
              if path.startswith("plugins/proseweaving/")),
        ):
            (self.repo / relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO_ROOT / relative, self.repo / relative)
        (self.repo / CONTENT_LOCK).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / CONTENT_LOCK, self.repo / CONTENT_LOCK)
        self.plugin = self.repo / PLUGIN
        self.retirement_ledger = self.repo / RETIREMENT_LEDGER
        VALIDATE_MERGECRAFT.write_content_lock(self.repo, self.plugin)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def run_validator(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), str(self.repo), *extra],
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

    def run_candidate_runtime_probe(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "-I",
                "-B",
                "-c",
                VALIDATE_MERGECRAFT.CANDIDATE_RUNTIME_PROBE,
                str(self.plugin),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )

    def run_comment_acknowledgement_probe(self) -> subprocess.CompletedProcess[str]:
        marker = "    set_states(created)\n    request = {"
        probe, separator, _remainder = (
            VALIDATE_MERGECRAFT.CANDIDATE_RUNTIME_PROBE.partition(marker)
        )
        self.assertEqual(separator, marker)
        return subprocess.run(
            [sys.executable, "-I", "-B", "-c", probe, str(self.plugin)],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )

    def assert_rejected(self, expected: str) -> None:
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(expected, result.stderr)

    def write_json(self, relative: str, value: object) -> None:
        (self.plugin / relative).write_text(
            json.dumps(value, indent=2) + "\n",
            encoding="utf-8",
        )

    def write_ledger(self, value: object) -> None:
        self.retirement_ledger.write_text(
            json.dumps(value, indent=2) + "\n",
            encoding="utf-8",
        )

    def write_eval_json(self, relative: str, value: object) -> None:
        (self.repo / EVAL_ROOT / relative).write_text(
            json.dumps(value, indent=2) + "\n",
            encoding="utf-8",
        )

    def write_atlas_json(self, relative: str, value: object) -> None:
        (self.repo / ATLAS_RELEASE / relative).write_text(
            json.dumps(value, indent=2) + "\n",
            encoding="utf-8",
        )

    def test_accepts_current_public_contract_and_each_skill_quick_check(self) -> None:
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stderr)
        topology = json.loads((self.plugin / "topology.json").read_text())
        for component in topology["skills"]:
            skill = component["name"]
            with self.subTest(skill=skill):
                result = self.run_validator("--skill", skill)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_publication_rejects_missing_relation_evaluation_evidence(self) -> None:
        evidence = self.repo / EVAL_ROOT / "skills/maintaining-issue-pr-relations"
        (evidence / "experiment.json").unlink(missing_ok=True)
        result = self.run_validator("--source-stage")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("relation evaluation evidence", result.stderr)

    def prepare_relation_contract_fixture(self) -> dict:
        """Construct validator inputs from the preparation CLI; execute no model.

        The retained response/grade rows are fixture material only. Rebinding
        them here tests source correspondence, never behavioral qualification.
        """
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(
            ["git", "-C", str(self.repo), "-c", "user.name=Fixture",
             "-c", "user.email=fixture@example.invalid", "-c", "core.hooksPath=/dev/null",
             "commit", "--allow-empty", "-qm", "test: create synthetic preparation source"],
            check=True,
        )
        prepared = self.repo.parent / "prepared"
        fixture_client = self.repo.parent / "fixture-claude"
        fixture_client.write_text(
            f"#!{sys.executable}\n"
            "import sys\n"
            "if sys.argv[1:] != ['--version']:\n"
            "    raise SystemExit('This fixture supports only --version.')\n"
            "print('0.0.0 (Claude Code)')\n"
        )
        fixture_client.chmod(0o755)
        result = subprocess.run(
            [sys.executable, "-B", str(REPO_ROOT / "scripts/mergecraft_writing_evals.py"),
             "prepare", "--repo", str(self.repo), "--output", str(prepared),
             "--claude", str(fixture_client)],
            text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        specs = [row for row in json.loads((prepared / "behavior-specs.json").read_bytes())
                 if row["suite"] == "relations"]
        self.assertEqual(len(specs), 51)
        self.assertFalse((prepared / "runs").exists())
        source = json.loads((prepared / "manifest.json").read_bytes())["source_sha256"]
        folder = self.repo / EVAL_ROOT / "skills/maintaining-issue-pr-relations"
        experiment = json.loads((folder / "experiment.json").read_bytes())
        runs = {row["id"]: row for row in experiment["behavior_runs"]}
        paths = {str(EVAL_ROOT / "skills/maintaining-issue-pr-relations" / name)
                 for name in ("evals.json", "policy.json", "trigger-evals.json")}
        for spec in specs:
            selected = experiment["selection"]["behavior_by_case"][str(spec["case_id"])]
            run = runs[f"{selected}/case-{spec['case_id']:02d}-with-skill-{spec['repetition']}"]
            run["request_sha256"] = spec["request_sha256"]
            run["candidate_sha256"] = spec["candidate_sha256"]
            run["fixture_sha256"] = spec["fixture_sha256"]
            experiment["requests_by_sha256"][spec["request_sha256"]] = spec["request"]
            paths.update(spec["candidate_sha256"])
            paths.update(f"evals/mergecraft/skills/{path}" for path in spec["fixture_sha256"])
        experiment["current_source_sha256"] = {path: source[path] for path in sorted(paths)}
        skill = "plugins/mergecraft/skills/maintaining-issue-pr-relations"
        native_paths = [f"{skill}/{name}" for name in
                        ("SKILL.md", "references/relation-contract.md", "references/command.md")]
        body = (self.repo / native_paths[0]).read_text().split("---\n", 2)[2].lstrip("\n")
        native = experiment["selection"]["trigger_experiment"]
        for run in experiment["native_and_trigger_runs"]:
            if run["id"].startswith(native + "/"):
                run["candidate_sha256"] = {path: source[path] for path in native_paths}
                for injection, call in zip(run["skill_injections"], run["tool_use"]):
                    injection["source_body_sha256"] = hashlib.sha256(body.encode()).hexdigest()
                    text = "Base directory for this skill: <CANDIDATE_SKILL_DIR>\n\n" + body
                    if call["input"].get("args"):
                        text += "\n\nARGUMENTS: " + call["input"]["args"]
                    injection["text"] = text
                    injection["retained_text_sha256"] = hashlib.sha256(text.encode()).hexdigest()
                run["isolation"]["skill_injections"] = [
                    {key: injection[key] for key in
                     ("original_text_sha256", "source_body_sha256", "source_body_exact_match")}
                    for injection in run["skill_injections"]
                ]
        (folder / "experiment.json").write_text(json.dumps(experiment) + "\n")
        return experiment

    def test_relation_contract_accepts_the_prepared_full_instruction_bundle(self) -> None:
        experiment = self.prepare_relation_contract_fixture()
        self.assertIn(
            "plugins/proseweaving/skills/writing-for-people/references/threaded-conversation.md",
            experiment["current_source_sha256"],
        )
        self.assertIn(
            "plugins/mergecraft/skills/getting-prs-merged/references/caller-continuation.md",
            experiment["current_source_sha256"],
        )
        VALIDATE_MERGECRAFT.validate_relation_evidence(self.repo)

    def test_publication_requires_the_full_per_case_relation_bundle(self) -> None:
        original = self.prepare_relation_contract_fixture()
        common = "plugins/proseweaving/skills/writing-for-people/references/threaded-conversation.md"
        routed = "plugins/mergecraft/skills/getting-prs-merged/references/caller-continuation.md"
        for case_id, path, add in ((0, common, False), (0, routed, False), (11, routed, True)):
            with self.subTest(case=case_id, path=path, extra=add):
                experiment = copy.deepcopy(original)
                selected = experiment["selection"]["behavior_by_case"][str(case_id)]
                run_id = f"{selected}/case-{case_id:02d}-with-skill-1"
                run = next(row for row in experiment["behavior_runs"] if row["id"] == run_id)
                request = json.loads(experiment["requests_by_sha256"][run["request_sha256"]])
                if add:
                    self.assertNotIn(path, request["candidate_bundle"])
                    request["candidate_bundle"][path] = (self.repo / path).read_text()
                else:
                    del request["candidate_bundle"][path]
                text = json.dumps(request, ensure_ascii=False, indent=2)
                run["request_sha256"] = hashlib.sha256(text.encode()).hexdigest()
                run["candidate_sha256"] = {
                    name: hashlib.sha256(value.encode()).hexdigest()
                    for name, value in request["candidate_bundle"].items()
                }
                experiment["requests_by_sha256"][run["request_sha256"]] = text
                self.write_eval_json("skills/maintaining-issue-pr-relations/experiment.json", experiment)
                result = self.run_validator("--source-stage")
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn("selected executor inputs", result.stderr)

    def test_publication_binds_all_delivered_relation_reference_sources(self) -> None:
        original = self.prepare_relation_contract_fixture()
        for path in (
            "plugins/proseweaving/skills/writing-for-people/references/threaded-conversation.md",
            "plugins/mergecraft/skills/getting-prs-merged/references/caller-continuation.md",
        ):
            with self.subTest(path=path):
                experiment = copy.deepcopy(original)
                del experiment["current_source_sha256"][path]
                self.write_eval_json("skills/maintaining-issue-pr-relations/experiment.json", experiment)
                result = self.run_validator("--source-stage")
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn("current source binding", result.stderr)

    def test_publication_rejects_malformed_relation_evaluation_without_traceback(self) -> None:
        evidence = self.repo / EVAL_ROOT / "skills/maintaining-issue-pr-relations"
        (evidence / "experiment.json").write_text("[]\n", encoding="utf-8")
        (evidence / "grading.json").write_text("{}\n", encoding="utf-8")
        result = self.run_validator("--source-stage")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("relation evaluation evidence", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_publication_rejects_rebound_hashes_with_stale_relation_executor_inputs(self) -> None:
        relative = "plugins/mergecraft/skills/maintaining-issue-pr-relations/references/command.md"
        source = self.repo / relative
        source.write_text(source.read_text() + "\nAdditional current instruction.\n")
        evidence = self.repo / EVAL_ROOT / "skills/maintaining-issue-pr-relations/experiment.json"
        experiment = json.loads(evidence.read_bytes())
        experiment["current_source_sha256"][relative] = hashlib.sha256(source.read_bytes()).hexdigest()
        evidence.write_text(json.dumps(experiment), encoding="utf-8")
        result = self.run_validator("--source-stage")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("selected executor inputs", result.stderr)

    def test_publication_requires_isolated_relation_runs_and_bound_passing_grades(self) -> None:
        folder = self.repo / EVAL_ROOT / "skills/maintaining-issue-pr-relations"
        original_experiment = self.prepare_relation_contract_fixture()
        original_grading = json.loads((folder / "grading.json").read_bytes())
        VALIDATE_MERGECRAFT.validate_relation_evidence(self.repo)
        selected = original_experiment["selection"]["behavior_by_case"]["0"]
        selected_id = f"{selected}/case-00-with-skill-1"
        diagnostics = {
            "tools exposed": "behavior isolation",
            "parse error": "executor failure",
            "permission denial": "executor failure",
            "failed expectation": "failed behavior expectation",
            "missing grade": "missing selected run/grade",
            "wrong response": "independent grade binding",
            "failed trigger": "trigger grade",
        }
        for change, diagnostic in diagnostics.items():
            with self.subTest(change=change):
                experiment = copy.deepcopy(original_experiment)
                grading = copy.deepcopy(original_grading)
                run = next(row for row in experiment["behavior_runs"] if row["id"] == selected_id)
                grade = next(row for row in grading["runs"] if row["run_id"] == selected_id)
                if change == "tools exposed":
                    run["init"]["tools"] = ["Bash"]
                elif change == "parse error":
                    run["parse_errors"] = ["Malformed stream event"]
                elif change == "permission denial":
                    run["permission_denials"] = [{"tool_name": "Bash"}]
                elif change == "failed expectation":
                    grade["expectations"][0]["passed"] = False
                elif change == "missing grade":
                    grading["runs"].remove(grade)
                elif change == "wrong response":
                    grade["response_sha256"] = "0" * 64
                else:
                    grading["trigger_runs"][0]["passed"] = False
                (folder / "experiment.json").write_text(json.dumps(experiment), encoding="utf-8")
                (folder / "grading.json").write_text(json.dumps(grading), encoding="utf-8")
                result = self.run_validator("--source-stage")
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn(f"relation evaluation evidence: {diagnostic}", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_publication_rejects_inconsistent_selected_relation_model_identity(self) -> None:
        path = self.repo / EVAL_ROOT / "skills/maintaining-issue-pr-relations/experiment.json"
        original = json.loads(path.read_bytes())
        selected = original["selection"]["behavior_by_case"]["0"]
        selected_id = f"{selected}/case-00-with-skill-1"
        baseline = self.run_validator("--source-stage")
        self.assertEqual(baseline.returncode, 0, baseline.stderr)
        for field in ("model_requested", "init.model"):
            with self.subTest(field=field):
                experiment = copy.deepcopy(original)
                run = next(row for row in experiment["behavior_runs"] if row["id"] == selected_id)
                if field == "model_requested":
                    run[field] = "different-executor"
                else:
                    run["init"]["model"] = "different-executor"
                path.write_text(json.dumps(experiment), encoding="utf-8")
                result = self.run_validator("--source-stage")
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn("actual executor identity", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_publication_requires_relation_thresholds_to_match_selected_grades(self) -> None:
        path = self.repo / EVAL_ROOT / "skills/maintaining-issue-pr-relations/grading.json"
        original = json.loads(path.read_bytes())
        for change in ("false summary", "missing summary", "duplicate summary", "weakened requirement"):
            with self.subTest(change=change):
                grading = copy.deepcopy(original)
                if change == "false summary":
                    grading["thresholds"][0].update(passes=0, met=False)
                elif change == "missing summary":
                    grading["thresholds"].pop()
                elif change == "duplicate summary":
                    grading["thresholds"].append(grading["thresholds"][0])
                else:
                    grading["thresholds"][0]["required"] = 1
                path.write_text(json.dumps(grading), encoding="utf-8")
                result = self.run_validator("--source-stage")
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn("relation evaluation evidence", result.stderr)
                self.assertIn("threshold", result.stderr)

    def test_uses_canonical_agent_plugins_v1_manifest_and_discovery(self) -> None:
        canonical = json.loads((self.plugin / "plugin.json").read_text())
        topology = json.loads((self.plugin / "topology.json").read_text())

        self.assertEqual(canonical["$schema"], AGENT_PLUGIN_SCHEMA)
        self.assertEqual(canonical["name"], "mergecraft")
        self.assertEqual(canonical["version"], "1.0.0")
        self.assertEqual(set(canonical["extensions"]), {"com.openai"})
        self.assertEqual(set(canonical["extensions"]["com.openai"]), {"interface"})
        self.assertFalse((self.plugin / ".codex-plugin").exists())
        self.assertEqual(
            sorted(
                path.name
                for path in (self.plugin / "skills").iterdir()
                if path.is_dir() and (path / "SKILL.md").is_file()
            ),
            sorted(component["name"] for component in topology["skills"]),
        )

    def test_markdown_authoring_contract_is_public_and_writer_local(self) -> None:
        topology = json.loads((self.plugin / "topology.json").read_text())
        components = {component["name"]: component for component in topology["skills"]}
        canonical = (self.plugin / MARKDOWN_AUTHORING_SOURCE).read_bytes()

        self.assertIn(MARKDOWN_AUTHORING_SKILL, components)
        self.assertEqual(
            components[MARKDOWN_AUTHORING_SKILL]["references"],
            [
                MARKDOWN_AUTHORING_SOURCE.as_posix(),
                "skills/writing-github-issue-and-pr-markdown/references/review-voice.md",
            ],
        )
        for skill, relative in MARKDOWN_AUTHORING_PROJECTIONS.items():
            with self.subTest(skill=skill):
                installed_root = Path(self.temporary_directory.name) / "installed" / skill
                shutil.copytree(self.plugin / "skills" / skill, installed_root)
                projection = installed_root / relative
                self.assertEqual(projection.read_bytes(), canonical)
                self.assertIn(
                    f"({relative.as_posix()})",
                    (installed_root / "SKILL.md").read_text(encoding="utf-8"),
                )

    def test_response_authoring_contract_requires_portable_writer_edge(self) -> None:
        topology = json.loads((self.plugin / "topology.json").read_text())
        response = next(
            component
            for component in topology["skills"]
            if component["name"] == "interacting-with-pr-review-feedback"
        )
        writer = next(
            operation
            for operation in topology["operations"]
            if operation["semantic_id"] == "github-markdown-content"
        )
        projection = (
            "skills/interacting-with-pr-review-feedback/"
            "references/github-markdown-authoring.md"
        )
        self.assertIn(projection, response["references"])
        self.assertIn("operation:github-markdown-content", response["calls"])
        self.assertIn("interacting-with-pr-review-feedback", writer["callers"])

        response["calls"] = [
            call
            for call in response["calls"]
            if call != "operation:github-markdown-content"
        ]
        writer["callers"] = [
            caller
            for caller in writer["callers"]
            if caller != "interacting-with-pr-review-feedback"
        ]
        self.write_json("topology.json", topology)

        with self.assertRaisesRegex(
            VALIDATE_MERGECRAFT.ContractError,
            "response Markdown authoring operation edge drift",
        ):
            VALIDATE_MERGECRAFT.validate_topology(self.plugin)

    def test_projection_command_updates_review_voice_only(self) -> None:
        canonical = self.plugin / "references/review-voice.md"
        self.assertTrue(canonical.is_file(), "canonical review voice is missing")
        canonical.write_bytes(canonical.read_bytes() + b"\nReview-specific addition.\n")
        projections = {
            self.plugin / "skills" / skill / "references/review-voice.md"
            for skill in (
                "writing-github-issue-and-pr-markdown",
                "interacting-with-pr-review-feedback",
            )
        }
        before = {
            path: (path.read_bytes(), stat.S_IMODE(path.stat().st_mode), path.stat().st_ino)
            for path in self.repo.rglob("*")
            if path.is_file()
        }

        result = self.run_validator("--write-markdown-projections")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            {path for path in self.repo.rglob("*") if path.is_file()}, set(before)
        )
        for path, (content, mode, inode) in before.items():
            with self.subTest(path=path.relative_to(self.repo)):
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), mode)
                if path in projections:
                    self.assertEqual(path.read_bytes(), canonical.read_bytes())
                else:
                    self.assertEqual(path.read_bytes(), content)
                    self.assertEqual(path.stat().st_ino, inode)

    def test_current_projections_need_no_replacement(self) -> None:
        before = {
            path: (path.read_bytes(), path.stat().st_ino)
            for path in self.repo.rglob("*")
            if path.is_file()
        }

        result = self.run_validator("--write-markdown-projections")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            {path: (path.read_bytes(), path.stat().st_ino) for path in before}, before
        )

    def test_external_writing_route_rejects_missing_callable(self) -> None:
        target = self.repo / "plugins/proseweaving/skills/writing-for-people/SKILL.md"
        target.unlink()

        result = self.run_validator("--write-markdown-projections")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("external call does not resolve to a callable skill", result.stderr)

    def test_external_writing_route_requires_owned_capabilities(self) -> None:
        path = self.repo / "plugins/proseweaving/topology.json"
        topology = json.loads(path.read_bytes())
        for capability in (
            "human-facing-register", "evidence-in-prose", "post-draft-edit-pass",
        ):
            with self.subTest(capability=capability):
                changed = copy.deepcopy(topology)
                changed["skills"]["writing-for-people"]["owns"].remove(capability)
                path.write_text(json.dumps(changed), encoding="utf-8")

                result = self.run_validator("--write-markdown-projections")

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("external writing capabilities missing", result.stderr)

    def test_external_writing_route_rejects_symlink_traversal(self) -> None:
        for relative in (
            "proseweaving", "proseweaving/skills",
            "proseweaving/skills/writing-for-people",
            "proseweaving/skills/writing-for-people/SKILL.md",
            "proseweaving/topology.json",
        ):
            with self.subTest(relative=relative):
                path = self.repo / "plugins" / relative
                moved = Path(self.temporary_directory.name) / "external-writing-input"
                path.rename(moved)
                path.symlink_to(moved, target_is_directory=moved.is_dir())
                try:
                    result = self.run_validator("--write-markdown-projections")
                    self.assertNotEqual(result.returncode, 0)
                    self.assertRegex(result.stderr, "symlink|required regular file")
                finally:
                    path.unlink()
                    moved.rename(path)

    def test_external_writing_route_is_declared_by_each_semantic_consumer(self) -> None:
        topology = json.loads((self.plugin / "topology.json").read_bytes())
        consumers = (
            "writing-github-issue-and-pr-markdown",
            "writing-reviewable-pr-descriptions",
            "interacting-with-pr-review-feedback",
        )
        for name in consumers:
            with self.subTest(consumer=name):
                changed = copy.deepcopy(topology)
                consumer = next(row for row in changed["skills"] if row["name"] == name)
                consumer["external_calls"] = []
                self.write_json("topology.json", changed)
                result = self.run_validator("--write-markdown-projections")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("external writing call declaration drift", result.stderr)

    def test_content_lock_command_rejects_stale_review_voice(self) -> None:
        projection = self.plugin / (
            "skills/interacting-with-pr-review-feedback/references/review-voice.md"
        )
        projection.write_bytes(projection.read_bytes() + b"\nStale projection.\n")
        before = {
            path: path.read_bytes() for path in self.repo.rglob("*") if path.is_file()
        }

        result = self.run_validator("--write-content-lock")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("review voice projection drift", result.stderr)
        self.assertEqual({path: path.read_bytes() for path in before}, before)

    def test_source_stage_rejects_markdown_authoring_projection_drift(self) -> None:
        projection = (
            self.plugin
            / "skills/writing-reviewable-pr-descriptions"
            / MARKDOWN_AUTHORING_PROJECTIONS["writing-reviewable-pr-descriptions"]
        )
        projection.write_bytes(projection.read_bytes() + b"\nDrift.\n")

        result = self.run_validator("--source-stage")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("writer-local Markdown authoring projection drift", result.stderr)

    def test_content_lock_command_rejects_stale_markdown_projections(self) -> None:
        projection = (
            self.plugin
            / "skills/writing-reviewable-pr-descriptions"
            / MARKDOWN_AUTHORING_PROJECTIONS["writing-reviewable-pr-descriptions"]
        )
        projection.write_bytes(projection.read_bytes() + b"\nDrift.\n")
        before = {
            path: path.read_bytes()
            for path in self.repo.rglob("*")
            if path.is_file()
        }

        for extra in ((), ("--source-stage",)):
            with self.subTest(extra=extra):
                result = self.run_validator("--write-content-lock", *extra)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn("Markdown authoring projection drift", result.stderr)
                self.assertEqual(
                    {path: path.read_bytes() for path in before}, before
                )

    def test_projection_command_regenerates_only_projections_with_stale_evidence(
        self,
    ) -> None:
        canonical = self.plugin / MARKDOWN_AUTHORING_SOURCE
        canonical.write_bytes(canonical.read_bytes() + b"\nCanonical extension.\n")
        projections = {
            self.plugin / "skills" / skill / relative
            for skill, relative in MARKDOWN_AUTHORING_PROJECTIONS.items()
        }
        next(iter(projections)).chmod(0o640)
        before = {
            path: (path.read_bytes(), stat.S_IMODE(path.stat().st_mode), path.stat().st_ino)
            for path in self.repo.rglob("*")
            if path.is_file()
        }

        result = self.run_validator("--write-markdown-projections")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Mergecraft Markdown authoring projections updated", result.stdout)
        self.assertEqual(
            {path for path in self.repo.rglob("*") if path.is_file()}, set(before)
        )
        for path, (content, mode, inode) in before.items():
            with self.subTest(path=path.relative_to(self.repo)):
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), mode)
                if path in projections:
                    self.assertEqual(path.read_bytes(), canonical.read_bytes())
                else:
                    self.assertEqual(path.read_bytes(), content)
                    self.assertEqual(path.stat().st_ino, inode)

    def test_content_lock_command_preserves_every_plugin_file(self) -> None:
        lock = self.repo / CONTENT_LOCK
        expected_lock = lock.read_bytes()
        lock.write_bytes(b"{}\n")
        before = {
            path: (path.read_bytes(), stat.S_IMODE(path.stat().st_mode), path.stat().st_ino)
            for path in self.plugin.rglob("*")
            if path.is_file()
        }

        result = self.run_validator("--write-content-lock")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(lock.read_bytes(), expected_lock)
        self.assertEqual(
            {
                path: (path.read_bytes(), stat.S_IMODE(path.stat().st_mode), path.stat().st_ino)
                for path in before
            },
            before,
        )

    def test_prepare_content_lock_retains_stale_evidence_and_changes_only_lock(self) -> None:
        for relative in (
            PLUGIN / "skills/writing-github-issue-and-pr-markdown/evals/experiment.json",
            PLUGIN / "skills/interacting-with-pr-review-feedback/evals/response-evidence.json",
            EVAL_ROOT / "skills/maintaining-issue-pr-relations/experiment.json",
        ):
            (self.repo / relative).write_text("{}\n", encoding="utf-8")
        lock = self.repo / CONTENT_LOCK
        lock.write_bytes(b"{}\n")
        lock.chmod(0o640)
        before = {
            path: (path.read_bytes(), stat.S_IMODE(path.stat().st_mode), path.stat().st_ino)
            for path in self.repo.rglob("*") if path.is_file()
        }

        result = self.run_validator("--prepare-content-lock")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "Mergecraft content lock prepared; behavior evidence not checked; candidate unqualified.\n",
        )
        self.assertEqual(result.stderr, "")
        VALIDATE_MERGECRAFT.validate_content_lock(self.repo, self.plugin)
        self.assertEqual({path for path in self.repo.rglob("*") if path.is_file()}, set(before))
        for path, (content, mode, inode) in before.items():
            with self.subTest(path=path.relative_to(self.repo)):
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), mode)
                if path != lock:
                    self.assertEqual((path.read_bytes(), path.stat().st_ino), (content, inode))
        prepared = lock.read_bytes()
        repeated = self.run_validator("--prepare-content-lock")
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        self.assertEqual(lock.read_bytes(), prepared)

    def test_generation_commands_are_mutually_exclusive(self) -> None:
        before = {
            path: (path.read_bytes(), stat.S_IMODE(path.stat().st_mode), path.stat().st_ino)
            for path in self.repo.rglob("*")
            if path.is_file()
        }

        result = self.run_validator(
            "--write-content-lock", "--write-markdown-projections"
        )

        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("not allowed with argument", result.stderr)
        self.assertEqual(
            {
                path: (path.read_bytes(), stat.S_IMODE(path.stat().st_mode), path.stat().st_ino)
                for path in before
            },
            before,
        )

    def test_preparation_argument_conflicts_leave_all_files_unchanged(self) -> None:
        before = {
            path: (path.read_bytes(), stat.S_IMODE(path.stat().st_mode), path.stat().st_ino)
            for path in self.repo.rglob("*") if path.is_file()
        }
        for extra in (
            ("--skill", "getting-prs-merged"),
            ("--source-stage",),
            ("--write-content-lock",),
            ("--write-markdown-projections",),
        ):
            with self.subTest(arguments=extra):
                result = self.run_validator("--prepare-content-lock", *extra)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("--prepare-content-lock", result.stderr)
                self.assertEqual(
                    {path: (path.read_bytes(), stat.S_IMODE(path.stat().st_mode), path.stat().st_ino)
                     for path in self.repo.rglob("*") if path.is_file()},
                    before,
                )

    def test_preparation_rejects_invalid_structure_before_lock_replacement(self) -> None:
        manifest = json.loads((self.plugin / "plugin.json").read_bytes())
        manifest["version"] = "invalid-candidate"
        cases = (
            (PLUGIN / "plugin.json", json.dumps(manifest).encode(), "manifest"),
            (PLUGIN / "skills/writing-github-issue-and-pr-markdown/evals/experiment.json",
             b"{", "contract validation failed"),
            (EVAL_ROOT / "skills/maintaining-issue-pr-relations/experiment.json",
             b"{", "contract validation failed"),
            (PLUGIN / "skills/interacting-with-pr-review-feedback/references/review-voice.md",
             b"Stale projection.\n", "review voice projection drift"),
            (ATLAS_RELEASE / "review-atlas-contract.json", b"{}\n", "atlas canonical contract"),
        )
        lock = self.repo / CONTENT_LOCK
        original_lock = (lock.read_bytes(), stat.S_IMODE(lock.stat().st_mode), lock.stat().st_ino)
        for relative, content, diagnostic in cases:
            with self.subTest(path=relative):
                path = self.repo / relative
                original = path.read_bytes()
                try:
                    path.write_bytes(content)
                    result = self.run_validator("--prepare-content-lock")
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn(diagnostic.lower(), result.stderr.lower())
                    self.assertEqual(
                        (lock.read_bytes(), stat.S_IMODE(lock.stat().st_mode), lock.stat().st_ino),
                        original_lock,
                    )
                finally:
                    path.write_bytes(original)

    def test_preparation_does_not_disable_evidence_checks_in_existing_modes(self) -> None:
        relative = "skills/writing-github-issue-and-pr-markdown/evals/experiment.json"
        evidence = json.loads((self.plugin / relative).read_bytes())
        evidence["current_source_sha256"]["SKILL.md"] = "0" * 64
        self.write_json(relative, evidence)
        lock = self.repo / CONTENT_LOCK
        before = lock.read_bytes()
        for extra in ((), ("--source-stage",), ("--write-content-lock",),
                      ("--source-stage", "--write-content-lock")):
            with self.subTest(arguments=extra):
                result = self.run_validator(*extra)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn("Markdown authoring evidence source binding drift", result.stderr)
                self.assertEqual(lock.read_bytes(), before)

    def test_preparation_rolls_back_lock_after_late_source_change(self) -> None:
        lock = self.repo / CONTENT_LOCK
        lock.write_bytes(b"{}\n")
        lock.chmod(0o640)
        original_lock = lock.read_bytes()
        document = self.plugin / "README.md"
        changed = document.read_bytes() + b"\nConcurrent source change.\n"
        real_replace = os.replace
        changed_once = False

        def replace_then_drift(source: object, destination: object, **kwargs: object) -> None:
            nonlocal changed_once
            real_replace(source, destination, **kwargs)
            if Path(destination).name == lock.name and not changed_once:
                changed_once = True
                document.write_bytes(changed)

        stderr = io.StringIO()
        stdout = io.StringIO()
        with (
            mock.patch.object(os, "replace", side_effect=replace_then_drift),
            mock.patch.object(VALIDATE_MERGECRAFT.sys, "argv",
                              ["validate_mergecraft.py", str(self.repo), "--prepare-content-lock"]),
            contextlib.redirect_stderr(stderr),
            contextlib.redirect_stdout(stdout),
        ):
            result = VALIDATE_MERGECRAFT.main()
        self.assertEqual(result, 1, stderr.getvalue())
        self.assertTrue(changed_once)
        self.assertIn("validated inputs changed", stderr.getvalue())
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(lock.read_bytes(), original_lock)
        self.assertEqual(stat.S_IMODE(lock.stat().st_mode), 0o640)
        self.assertEqual(document.read_bytes(), changed)

    def test_lock_writer_rejects_changed_captured_dependencies(self) -> None:
        lock = self.repo / CONTENT_LOCK
        paths = (
            self.plugin / "README.md",
            self.repo / EVAL_ROOT / "skills/maintaining-issue-pr-relations/evals.json",
            self.repo / ATLAS_RELEASE / "review-atlas-contract.json",
            self.repo / "plugins/versionkeeping/topology.json",
            self.repo / "plugins/proseweaving/topology.json",
            self.repo / "plugins/proseweaving/skills/writing-for-people/SKILL.md",
            self.repo / "plugins/proseweaving/skills/writing-for-people/references/edit-pass.md",
            self.retirement_ledger,
            lock,
        )
        for path in paths:
            with self.subTest(path=path.relative_to(self.repo)):
                original = path.read_bytes()
                original_lock = lock.read_bytes()
                snapshot = VALIDATE_MERGECRAFT.capture_content_lock_write_snapshot(self.repo)
                changed = original + b"\nConcurrent source change.\n"
                try:
                    path.write_bytes(changed)
                    with self.assertRaisesRegex(
                        VALIDATE_MERGECRAFT.ContractError, "validated inputs changed"
                    ):
                        VALIDATE_MERGECRAFT.write_content_lock(self.repo, snapshot=snapshot)
                    self.assertEqual(path.read_bytes(), changed)
                    self.assertEqual(lock.read_bytes(), changed if path == lock else original_lock)
                finally:
                    path.write_bytes(original)

    def test_projection_command_rolls_back_after_late_input_changes(self) -> None:
        canonical = self.plugin / MARKDOWN_AUTHORING_SOURCE
        canonical.write_bytes(canonical.read_bytes() + b"\nCanonical extension.\n")
        lock = self.repo / CONTENT_LOCK
        projections = {
            self.plugin / "skills" / skill / relative
            for skill, relative in MARKDOWN_AUTHORING_PROJECTIONS.items()
        }
        original = {
            path: (path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
            for path in projections
        }
        real_replace = os.replace

        for changed_input in (
            canonical,
            lock,
            self.repo / "plugins/proseweaving/topology.json",
            self.repo / "plugins/proseweaving/skills/writing-for-people/SKILL.md",
        ):
            with self.subTest(changed_input=changed_input.relative_to(self.repo)):
                before_input = changed_input.read_bytes()
                replacements = 0

                def replace_then_drift(
                    source: object, destination: object, **kwargs: object
                ) -> None:
                    nonlocal replacements
                    real_replace(source, destination, **kwargs)
                    if Path(destination).name == "github-markdown-authoring.md":
                        replacements += 1
                        if replacements == len(projections):
                            changed_input.write_bytes(
                                before_input + b"\nConcurrent input change.\n"
                            )

                stderr = io.StringIO()
                with (
                    mock.patch.object(os, "replace", side_effect=replace_then_drift),
                    mock.patch.object(
                        VALIDATE_MERGECRAFT.sys,
                        "argv",
                        [
                            "validate_mergecraft.py",
                            str(self.repo),
                            "--write-markdown-projections",
                        ],
                    ),
                    contextlib.redirect_stderr(stderr),
                ):
                    result = VALIDATE_MERGECRAFT.main()

                self.assertEqual(result, 1, stderr.getvalue())
                self.assertIn("validated inputs changed", stderr.getvalue())
                self.assertEqual(
                    {
                        path: (path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
                        for path in projections
                    },
                    original,
                )
                self.assertEqual(
                    changed_input.read_bytes(),
                    before_input + b"\nConcurrent input change.\n",
                )
                changed_input.write_bytes(before_input)

    def test_markdown_authoring_eval_corpus_has_a_blind_executor_boundary(self) -> None:
        VALIDATE_MERGECRAFT.validate_markdown_authoring_eval_corpus(self.plugin)
        eval_root = self.plugin / "skills" / MARKDOWN_AUTHORING_SKILL / "evals"
        delivery = json.loads((eval_root / "delivery.json").read_text())
        document = json.loads((eval_root / "evals.json").read_text())

        self.assertEqual(
            delivery["executor"]["inputs"],
            ["prompt", "fixture", "candidate_bundle"],
        )
        self.assertNotIn("expected_output", delivery["executor"]["inputs"])
        self.assertNotIn("expectations", delivery["executor"]["inputs"])
        for item in document["evals"]:
            fixture = (
                self.plugin
                / "skills"
                / MARKDOWN_AUTHORING_SKILL
                / item["fixture_paths"][0]
            )
            self.assertTrue(fixture.is_file())
            self.assertFalse(
                any(
                    expectation["text"] in fixture.read_text(encoding="utf-8")
                    for expectation in item["expectations"]
                )
            )

    def test_lock_refresh_rejects_stale_markdown_evidence(self) -> None:
        skill = self.plugin / "skills" / MARKDOWN_AUTHORING_SKILL / "SKILL.md"
        skill.write_bytes(skill.read_bytes() + b"\nChanged authoring instruction.\n")
        lock = self.repo / CONTENT_LOCK
        before = lock.read_bytes()

        result = self.run_validator("--source-stage", "--write-content-lock")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Markdown authoring evidence source binding drift", result.stderr)
        self.assertEqual(lock.read_bytes(), before)

    def test_lock_refresh_rejects_relabelled_markdown_requests(self) -> None:
        prefix = f"skills/{MARKDOWN_AUTHORING_SKILL}"
        skill = self.plugin / prefix / "SKILL.md"
        skill.write_bytes(skill.read_bytes() + b"\nChanged authoring instruction.\n")
        path = self.plugin / prefix / "evals/experiment.json"
        experiment = json.loads(path.read_bytes())
        experiment["current_source_sha256"]["SKILL.md"] = hashlib.sha256(
            skill.read_bytes()
        ).hexdigest()
        experiment["current_delivered_source_sha256"][f"plugins/mergecraft/{prefix}/SKILL.md"] = hashlib.sha256(
            skill.read_bytes()
        ).hexdigest()
        self.write_json(f"{prefix}/evals/experiment.json", experiment)
        before = (self.repo / CONTENT_LOCK).read_bytes()

        result = self.run_validator("--source-stage", "--write-content-lock")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Markdown authoring selected request binding drift", result.stderr)
        self.assertEqual((self.repo / CONTENT_LOCK).read_bytes(), before)

    def test_validator_rejects_contradictory_selected_markdown_threshold(self) -> None:
        relative = f"skills/{MARKDOWN_AUTHORING_SKILL}/evals/grading.json"
        grading = json.loads((self.plugin / relative).read_bytes())
        grading["selected_thresholds"][0]["passes"] = 0
        grading["selected_thresholds"][0]["met"] = True
        self.write_json(relative, grading)
        before = (self.repo / CONTENT_LOCK).read_bytes()

        result = self.run_validator("--source-stage", "--write-content-lock")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Markdown authoring threshold derivation drift", result.stderr)
        self.assertEqual((self.repo / CONTENT_LOCK).read_bytes(), before)

    def test_validator_rejects_inconsistent_markdown_records_without_tracebacks(
        self,
    ) -> None:
        prefix = f"skills/{MARKDOWN_AUTHORING_SKILL}/evals"
        experiment = json.loads((self.plugin / prefix / "experiment.json").read_bytes())
        grading = json.loads((self.plugin / prefix / "grading.json").read_bytes())
        threshold = grading["selected_thresholds"][0]
        selected_id = (
            f"{threshold['experiment']}/case-{threshold['case_id']:02d}"
            f"-{threshold['variant']}-1"
        )

        def current_grade(document: dict) -> dict:
            return next(row for row in document["runs"] if row["run_id"] == selected_id)

        mutations = [
            ("missing source hash", "experiment",
             lambda d: d["current_source_sha256"].pop("SKILL.md")),
            ("changed request", "experiment",
             lambda d: d["requests_by_sha256"].update(
                 {next(iter(d["requests_by_sha256"])): "changed request"})),
            ("changed response", "experiment",
             lambda d: d["behavior_runs"][0].update(response="changed response")),
            ("unbound request", "experiment",
             lambda d: d["behavior_runs"][0].update(request_sha256="0" * 64)),
            ("duplicate run", "experiment",
             lambda d: d["behavior_runs"].append(d["behavior_runs"][0])),
            ("reused session", "experiment",
             lambda d: d["behavior_runs"][1].update(
                 session_id=d["behavior_runs"][0]["session_id"])),
            ("missing variant", "experiment",
             lambda d: d["behavior_runs"][0].pop("variant")),
            ("invalid case", "experiment",
             lambda d: d["behavior_runs"][0].update(case_id=[])),
            ("invalid repetition", "experiment",
             lambda d: d["behavior_runs"][0].update(repetition={})),
            ("missing selected run", "experiment",
             lambda d: d.update(behavior_runs=[
                 r for r in d["behavior_runs"] if r["id"] != selected_id])),
            ("orphan grade", "grading",
             lambda d: d["runs"][0].update(run_id="missing")),
            ("duplicate grade", "grading",
             lambda d: d["runs"].append(d["runs"][0])),
            ("unbound grade response", "grading",
             lambda d: current_grade(d).update(response_sha256="0" * 64)),
            ("stale selected expectation", "grading",
             lambda d: current_grade(d)["expectations"][0].update(text="Previous contract")),
            ("nonboolean judgment", "grading",
             lambda d: current_grade(d)["expectations"][0].update(passed="false")),
            ("invalid severity", "grading",
             lambda d: d["runs"][0]["expectations"][0].update(severity=[])),
            ("missing selected expectation", "grading",
             lambda d: current_grade(d)["expectations"].pop()),
            ("missing selected threshold", "grading",
             lambda d: d["selected_thresholds"].pop()),
            ("duplicate selected threshold", "grading",
             lambda d: d["selected_thresholds"].append(d["selected_thresholds"][0])),
            ("wrong required count", "grading",
             lambda d: d["selected_thresholds"][0].update(required=1)),
            ("wrong candidate result", "grading",
             lambda d: d.update(candidate_passed=not d["candidate_passed"])),
        ]
        before = (self.repo / CONTENT_LOCK).read_bytes()
        for name, target, mutate in mutations:
            with self.subTest(name=name):
                documents = {
                    "experiment": copy.deepcopy(experiment),
                    "grading": copy.deepcopy(grading),
                }
                mutate(documents[target])
                for label, document in documents.items():
                    self.write_json(f"{prefix}/{label}.json", document)

                result = self.run_validator("--source-stage", "--write-content-lock")

                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(
                    result.stderr.startswith("Mergecraft contract validation failed:"),
                    result.stderr,
                )
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual((self.repo / CONTENT_LOCK).read_bytes(), before)

    def test_validator_accepts_a_consistently_recorded_markdown_failure(self) -> None:
        relative = f"skills/{MARKDOWN_AUTHORING_SKILL}/evals/grading.json"
        grading = json.loads((self.plugin / relative).read_bytes())
        threshold = next(
            row for row in grading["selected_thresholds"]
            if row["variant"] == "with-skill" and row["severity"] == "safety"
            and row["passes"] == 3
        )
        run_id = (
            f"{threshold['experiment']}/case-{threshold['case_id']:02d}"
            f"-{threshold['variant']}-1"
        )
        grade = next(row for row in grading["runs"] if row["run_id"] == run_id)
        expectation = next(
            item for item in grade["expectations"]
            if item["id"] == threshold["expectation"]
        )
        expectation["passed"] = False
        expectation["evidence"] = "Constructed independent failure for this regression."
        for rows in (grading["thresholds"], grading["selected_thresholds"]):
            for row in rows:
                if all(
                    row[key] == threshold[key]
                    for key in ("experiment", "variant", "case_id", "expectation")
                ):
                    row.update(passes=2, met=False)
        grading["candidate_passed"] = False
        self.write_json(relative, grading)

        result = self.run_validator("--source-stage")

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_claude_manifest_is_exact_canonical_projection(self) -> None:
        canonical = json.loads((self.plugin / "plugin.json").read_text())
        claude = json.loads(
            (self.plugin / ".claude-plugin" / "plugin.json").read_text()
        )
        self.assertEqual(set(claude), set(CANONICAL_IDENTITY_FIELDS) | {"displayName"})
        self.assertEqual(claude["displayName"], "Mergecraft")
        self.assertEqual(
            {field: claude[field] for field in CANONICAL_IDENTITY_FIELDS},
            {field: canonical[field] for field in CANONICAL_IDENTITY_FIELDS},
        )

    def test_rejects_duplicate_json_at_any_depth(self) -> None:
        path = self.plugin / "plugin.json"
        path.write_text(
            path.read_text().replace(
                '"name": "mergecraft"',
                '"name": "mergecraft", "name": "other"',
            )
        )
        self.assert_rejected("duplicate JSON key")

    def test_rejects_inconsistent_change_navigation_reference_example(self) -> None:
        path = self.plugin / (
            "skills/writing-reviewable-pr-descriptions/references/change-navigation.md"
        )
        path.write_text(
            path.read_text().replace(
                "IMPL: 9 additions, 3 deletions",
                "IMPL: 10 additions, 3 deletions",
                1,
            )
        )
        result = self.run_validator("--source-stage")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("change-navigation reference example", result.stderr)

    def test_rejects_duplicate_or_contradictory_diff_summary_category_badges(
        self,
    ) -> None:
        path = self.plugin / (
            "skills/writing-reviewable-pr-descriptions/references/change-navigation.md"
        )
        original = path.read_text()
        before_diff, diff_section = original.split("## Diff Disclosure", 1)
        duplicate = (
            '<picture><img alt="IMPL: 9 additions, 3 deletions" '
            'src="https://img.shields.io/badge/'
            'IMPL-%2B9%20%E2%88%923-0969DA?style=flat" '
            'height="16"></picture> '
        )
        for metric in (
            duplicate,
            duplicate.replace(
                "9 additions, 3 deletions", "10 additions, 3 deletions"
            ).replace("%2B9%20%E2%88%923", "%2B10%20%E2%88%923"),
        ):
            with self.subTest(metric=metric):
                path.write_text(
                    before_diff
                    + "## Diff Disclosure"
                    + diff_section.replace(
                        '<picture><img alt="TEST: 16 additions, 22 deletions"',
                        metric + '<picture><img alt="TEST: 16 additions, 22 deletions"',
                        1,
                    )
                )
                result = self.run_validator("--source-stage")
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn("summary category badges", result.stderr)

    def test_change_navigation_examples_satisfy_the_production_validator(
        self,
    ) -> None:
        navigation = (
            self.plugin
            / "skills/writing-reviewable-pr-descriptions/references/change-navigation.md"
        ).read_text(encoding="utf-8")

        VALIDATE_MERGECRAFT.validate_change_navigation_reference_example(
            navigation,
            self.plugin,
        )

    def test_change_navigation_example_validation_timeout_is_contextual(self) -> None:
        navigation = (
            self.plugin
            / "skills/writing-reviewable-pr-descriptions/references/change-navigation.md"
        ).read_text(encoding="utf-8")

        with mock.patch.object(
            VALIDATE_MERGECRAFT.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(["python"], 30),
        ):
            with self.assertRaisesRegex(
                VALIDATE_MERGECRAFT.ContractError,
                "production validation timed out",
            ):
                VALIDATE_MERGECRAFT.validate_change_navigation_reference_example(
                    navigation,
                    self.plugin,
                )

    def test_publisher_actuation_fixtures_bind_exact_head_repository(self) -> None:
        fixture = self.repo / EVAL_ROOT / (
            "skills/publishing-reviewable-prs/fixtures/ready-state-only.md"
        )
        fixture.write_text(
            fixture.read_text(encoding="utf-8").replace(
                "- Head repository: `alice/widgets`\n",
                "",
            ),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(
            VALIDATE_MERGECRAFT.ContractError,
            "publisher actuation fixture identity drift",
        ):
            VALIDATE_MERGECRAFT.validate_raw_skill_eval_isolation(self.repo)

    def test_rejects_change_navigation_example_missing_required_category_title(
        self,
    ) -> None:
        path = self.plugin / (
            "skills/writing-reviewable-pr-descriptions/references/change-navigation.md"
        )
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                ' title="Implementation: 32 additions, 4 deletions '
                '(non-test source and configuration)"',
                "",
                1,
            ),
            encoding="utf-8",
        )

        self.assert_rejected("change-navigation reference example")

    def test_rejects_change_navigation_example_with_noncanonical_taxonomy(
        self,
    ) -> None:
        path = self.plugin / (
            "skills/writing-reviewable-pr-descriptions/references/change-navigation.md"
        )
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "TEST means automated verification.",
                "TEST means tests.",
                1,
            ),
            encoding="utf-8",
        )

        self.assert_rejected("change-navigation reference example")

    def test_rejects_change_navigation_example_with_stack_diff_aggregate_drift(
        self,
    ) -> None:
        path = self.plugin / (
            "skills/writing-reviewable-pr-descriptions/references/change-navigation.md"
        )
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "IMPL: 9 additions, 3 deletions",
                "IMPL: 10 additions, 3 deletions",
                1,
            ),
            encoding="utf-8",
        )

        self.assert_rejected("change-navigation reference example")

    def test_resynced_writer_and_publisher_boundaries_are_explicit(self) -> None:
        writer = (
            self.plugin / "skills/writing-reviewable-pr-descriptions/SKILL.md"
        ).read_text(encoding="utf-8")
        navigation = (
            self.plugin
            / "skills/writing-reviewable-pr-descriptions/references/change-navigation.md"
        ).read_text(encoding="utf-8")
        publisher = (
            self.plugin / "skills/publishing-reviewable-prs/SKILL.md"
        ).read_text(encoding="utf-8")
        normalized_writer = " ".join(writer.split())
        normalized_navigation = " ".join(navigation.split())
        normalized_publisher = " ".join(publisher.split())

        for requirement in (
            "standalone validation proves manifest, body, and local Git self-consistency",
            "does not prove the live pull request identity",
            "detects content drift; it does not authenticate the manifest's source",
            "Noncurrent Stack rows remain caller-supplied observations",
            "deterministic body generator, pathname classifier, Stack-discovery adapter, GitHub observer, or GitHub Action",
            "The first-100 presentation is a file-count bound, not a body-size guarantee",
        ):
            self.assertIn(requirement, normalized_writer)
        for requirement in (
            "schema v3 supports only GitHub's confirmed `diff-<sha256(target path)>` anchor convention",
            "stop if GitHub renders another anchor",
        ):
            self.assertIn(requirement, normalized_navigation)
        for requirement in (
            "serializes only cooperating processes that share the same local receipt root",
            "does not serialize another machine, user, bot, automation, or GitHub actor",
            "Classify an unchanged candidate as `no-op` before invoking the updater",
            "not updater success",
        ):
            self.assertIn(requirement, normalized_publisher)

    def test_resynced_writer_and_publisher_evals_are_retained(self) -> None:
        expected = {
            "writing-reviewable-pr-descriptions": {
                "chat-only-draft.md",
                "command-envelope-stack.md",
                "config-loader-precedence.md",
                "documentation-flag-correction.md",
                "preview-server-port-selection.md",
                "provider-plugin-framework.md",
                "change-summary-and-supporting-evidence.md",
                "publication-with-legacy-chat-framing.md",
                "personal-investigation-section.md",
                "publication-and-review-reply.md",
            },
            "publishing-reviewable-prs": {
                "body-only-preservation.md",
                "chat-only-draft-near-miss.md",
                "existing-pr-text-update.md",
                "new-draft-pr.md",
                "read-only-inspection-near-miss.md",
                "ready-state-only.md",
            },
        }
        for skill, fixtures in expected.items():
            root = self.repo / EVAL_ROOT / "skills" / skill
            with self.subTest(skill=skill):
                self.assertTrue((root / "evals.json").is_file())
                self.assertTrue((root / "trigger-evals.json").is_file())
                self.assertEqual(
                    {path.name for path in (root / "fixtures").glob("*.md")},
                    fixtures,
                )

    def test_accepts_distinct_writer_cases_sharing_a_fixture(self) -> None:
        VALIDATE_MERGECRAFT.validate_raw_skill_eval_isolation(self.repo)

    def test_rejects_changed_shared_writer_case_name_or_fixture(self) -> None:
        relative = "skills/writing-reviewable-pr-descriptions/evals.json"
        original = json.loads((self.repo / EVAL_ROOT / relative).read_text())
        for field, replacement, diagnostic in (
            ("name", "change-summary-and-supporting-evidence", "item schema drift"),
            (
                "files",
                ["writing-reviewable-pr-descriptions/fixtures/chat-only-draft.md"],
                "fixture binding drift",
            ),
        ):
            with self.subTest(field=field):
                changed = copy.deepcopy(original)
                changed["evals"][10][field] = replacement
                self.write_eval_json(relative, changed)
                with self.assertRaisesRegex(
                    VALIDATE_MERGECRAFT.ContractError, diagnostic
                ):
                    VALIDATE_MERGECRAFT.validate_raw_skill_eval_isolation(self.repo)

    def test_rejects_writer_publisher_trigger_complement_drift(self) -> None:
        relative = (
            "skills/writing-reviewable-pr-descriptions/trigger-evals.json"
        )
        document = json.loads((self.repo / EVAL_ROOT / relative).read_text())
        chat_only = next(
            item
            for item in document
            if item["query"]
            == "Draft a better pull request title and body here in chat. "
            "Do not change GitHub."
        )
        chat_only["should_trigger"] = False
        self.write_eval_json(relative, document)

        self.assert_rejected("writer/publisher trigger complement drift")

    def test_rejects_nonboolean_trigger_eval_result(self) -> None:
        relative = "skills/publishing-reviewable-prs/trigger-evals.json"
        document = json.loads((self.repo / EVAL_ROOT / relative).read_text())
        document[0]["should_trigger"] = 1
        self.write_eval_json(relative, document)

        self.assert_rejected(
            "trigger eval schema drift: publishing-reviewable-prs"
        )

    def test_rejects_non_finite_json_at_any_boundary(self) -> None:
        path = self.plugin / "plugin.json"
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant):
                path.write_text(
                    (REPO_ROOT / PLUGIN / "plugin.json")
                    .read_text()
                    .replace('"version":', f'"probe": {constant}, "version":', 1)
                )
                self.assert_rejected("non-finite JSON value")

    def test_rejects_exponent_overflow_json_at_any_boundary(self) -> None:
        path = self.plugin / "plugin.json"
        path.write_text(
            (REPO_ROOT / PLUGIN / "plugin.json")
            .read_text()
            .replace('"version":', '"probe": 1e999, "version":', 1)
        )
        self.assert_rejected("non-finite JSON value")

    def test_rejects_duplicate_yaml_key(self) -> None:
        path = self.plugin / "skills/graphite/agents/openai.yaml"
        path.write_text(path.read_text() + "\ninterface: {}\n")
        self.assert_rejected("duplicate YAML key")

    def test_rejects_non_finite_yaml_value(self) -> None:
        path = self.plugin / "skills/graphite/agents/openai.yaml"
        path.write_text(path.read_text() + "\nprobe: .nan\n")
        self.assert_rejected("non-finite YAML value")

    def test_rejects_manifest_projection_version_drift(self) -> None:
        path = self.plugin / ".claude-plugin/plugin.json"
        value = json.loads(path.read_text())
        value["version"] = "1.0.1"
        self.write_json(".claude-plugin/plugin.json", value)
        self.assert_rejected("Claude manifest projection drift: version")

    def test_rejects_unnamespaced_codex_prompt(self) -> None:
        path = self.plugin / "skills/graphite/agents/openai.yaml"
        path.write_text(path.read_text().replace("$mergecraft:graphite", "$graphite"))
        self.assert_rejected("namespaced Codex prompt")

    def test_rejects_missing_or_extra_public_skill(self) -> None:
        shutil.rmtree(self.plugin / "skills/graphite")
        self.assert_rejected("public skill inventory")

    def test_rejects_runtime_or_test_inventory_drift(self) -> None:
        path = self.plugin / "skills/graphite/extra.py"
        path.write_text("pass\n")
        self.assert_rejected("skill file inventory")

    def test_rejects_symlink_and_special_entry(self) -> None:
        link = self.plugin / "skills/graphite/linked.md"
        link.symlink_to("SKILL.md")
        self.assert_rejected("symlink")
        link.unlink()
        fifo = self.plugin / "skills/graphite/special"
        os.mkfifo(fifo)
        self.addCleanup(lambda: fifo.unlink(missing_ok=True))
        self.assertTrue(stat.S_ISFIFO(fifo.lstat().st_mode))
        self.assert_rejected("special entry")

    def test_rejects_topology_edge_or_owner_reversal(self) -> None:
        path = self.plugin / "topology.json"
        value = json.loads(path.read_text())
        next(
            component
            for component in value["skills"]
            if component["name"] == "writing-reviewable-pr-descriptions"
        )["calls"] = ["publishing-reviewable-prs"]
        self.write_json("topology.json", value)
        self.assert_rejected("forbidden reverse call")

        shutil.copy2(REPO_ROOT / PLUGIN / "topology.json", path)
        value = json.loads(path.read_text())
        operation = next(
            item for item in value["operations"] if item["semantic_id"] == "pr-creation"
        )
        operation["owner"] = "versionkeeping:checkpointing-and-publishing-git-work"
        self.write_json("topology.json", value)
        self.assert_rejected("operation owner drift")

    def test_rejects_merge_coordinator_self_actuation(self) -> None:
        path = self.plugin / "topology.json"
        value = json.loads(path.read_text())
        merge = next(
            component
            for component in value["skills"]
            if component["name"] == "getting-prs-merged"
        )
        merge["calls"] = [
            "operation:merge-actuation" if call == "internal:merge-actuator" else call
            for call in merge["calls"]
        ]
        operation = next(
            item
            for item in value["operations"]
            if item["semantic_id"] == "merge-actuation"
        )
        operation.update(
            {
                "owner": "getting-prs-merged",
                "implementation": "skills/getting-prs-merged/SKILL.md",
                "disposition": "public-skill",
            }
        )
        self.write_json("topology.json", value)
        self.assert_rejected("self-actuator ownership cycle")

    def test_operation_registry_rejects_missing_duplicate_unresolved_and_drift(
        self,
    ) -> None:
        path = self.plugin / "topology.json"

        value = json.loads(path.read_text())
        value["operations"] = [
            item for item in value["operations"] if item["semantic_id"] != "pr-creation"
        ]
        self.write_json("topology.json", value)
        self.assert_rejected("GitHub operation alias coverage drift")

        shutil.copy2(REPO_ROOT / PLUGIN / "topology.json", path)
        value = json.loads(path.read_text())
        value["operations"].append(copy.deepcopy(value["operations"][0]))
        self.write_json("topology.json", value)
        self.assert_rejected("duplicate operation export")

        shutil.copy2(REPO_ROOT / PLUGIN / "topology.json", path)
        value = json.loads(path.read_text())
        remote = next(
            item
            for item in value["operations"]
            if item["semantic_id"] == "remote-ref-deletion"
        )
        remote["owner"] = remote["import"] = "missing:owner"
        self.write_json("topology.json", value)
        self.assert_rejected("unresolved operation import")

        shutil.copy2(REPO_ROOT / PLUGIN / "topology.json", path)
        value = json.loads(path.read_text())
        publisher = next(
            item
            for item in value["skills"]
            if item["name"] == "publishing-reviewable-prs"
        )
        publisher["operations"].remove("pr-creation")
        self.write_json("topology.json", value)
        self.assert_rejected("public operation owner is not declared")

        shutil.copy2(REPO_ROOT / PLUGIN / "topology.json", path)
        value = json.loads(path.read_text())
        operation = next(
            item for item in value["operations"] if item["semantic_id"] == "pr-creation"
        )
        operation["github_aliases"] = ["pr-text-write"]
        self.write_json("topology.json", value)
        self.assert_rejected("GitHub operation alias collision")

        shutil.copy2(REPO_ROOT / PLUGIN / "topology.json", path)
        value = json.loads(path.read_text())
        operation = next(
            item for item in value["operations"] if item["semantic_id"] == "pr-creation"
        )
        operation["callers"] = []
        self.write_json("topology.json", value)
        self.assert_rejected("operation caller drift")

    def test_rejects_caller_callee_contract_drift(self) -> None:
        path = self.plugin / "topology.json"
        value = json.loads(path.read_text())
        publisher = next(
            component
            for component in value["skills"]
            if component["name"] == "publishing-reviewable-prs"
        )
        del publisher["contract"]["authority"]
        self.write_json("topology.json", value)
        self.assert_rejected("caller/callee contract drift")

    def test_rejects_nested_merge_loop_or_invalid_terminal_handoff(self) -> None:
        path = self.plugin / "topology.json"
        value = json.loads(path.read_text())
        merge = next(
            component
            for component in value["skills"]
            if component["name"] == "getting-prs-merged"
        )
        merge["calls"].append("tricritical:loop")
        self.write_json("topology.json", value)
        self.assert_rejected("nested loop ownership")

        shutil.copy2(REPO_ROOT / PLUGIN / "topology.json", path)
        value = json.loads(path.read_text())
        handoff = next(
            component
            for component in value["skills"]
            if component["name"] == "getting-prs-merged"
        )["contract"]["terminal_handoffs"][0]
        handoff["owner"] = "internal:merge-actuator"
        self.write_json("topology.json", value)
        self.assert_rejected("terminal handoff drift")

    def test_absent_pr_continues_through_readiness_operation_before_merge(
        self,
    ) -> None:
        topology = json.loads((self.plugin / "topology.json").read_text())
        merge = next(
            component
            for component in topology["skills"]
            if component["name"] == "getting-prs-merged"
        )
        self.assertIn("operation:readiness-outcome", merge["calls"])
        self.assertIn("readiness-handoff", merge["contract"]["terminal_statuses"])
        handoff = next(
            item
            for item in merge["contract"]["terminal_handoffs"]
            if item["owner"] == "getting-prs-ready-for-review"
        )
        self.assertEqual(
            handoff["trigger"],
            "readiness-authority-unavailable-or-outcome-blocked-ambiguous-or-unsafe",
        )
        fixture = (
            self.repo
            / EVAL_ROOT
            / "skills/getting-prs-merged/fixtures/new-branch-publish-and-closeout.md"
        ).read_text()
        self.assertIn("invokes `readiness-outcome`", fixture)
        self.assertIn("readiness coordinator owns", fixture)
        self.assertIn("fresh `getting-prs-merged`", fixture)

    def test_coordinator_handoffs_preserve_authorized_caller_continuation(self) -> None:
        topology = json.loads((self.plugin / "topology.json").read_text())
        skills = {item["name"]: item for item in topology["skills"]}
        outcome_coordinators = {
            "resuming-reviewed-prs",
            "addressing-pr-review-feedback",
            "getting-prs-ready-for-review",
            "getting-prs-merged",
        }
        for name in outcome_coordinators:
            with self.subTest(name=name):
                called = {
                    next(
                        operation["owner"]
                        for operation in topology["operations"]
                        if operation["semantic_id"]
                        == call.removeprefix("operation:")
                    )
                    for call in skills[name]["calls"]
                    if call.startswith("operation:")
                }
                allowed = (
                    {"getting-prs-ready-for-review", "addressing-pr-review-feedback"}
                    if name == "getting-prs-merged"
                    else set()
                )
                self.assertTrue((called & outcome_coordinators) <= allowed)

        resume = skills["resuming-reviewed-prs"]
        self.assertEqual(
            {item["owner"] for item in resume["contract"]["terminal_handoffs"]},
            {
                "addressing-pr-review-feedback",
                "maintaining-issue-pr-relations",
                "getting-prs-ready-for-review",
                "getting-prs-merged",
                "operation:focused-ci",
                "versionkeeping:resolving-merge-conflicts",
            },
        )
        merge = skills["getting-prs-merged"]
        self.assertIn("operation:feedback-acquisition", merge["calls"])
        self.assertIn("operation:readiness-outcome", merge["calls"])
        self.assertIn(
            "addressing-pr-review-feedback",
            {item["owner"] for item in merge["contract"]["terminal_handoffs"]},
        )
        feedback_acquisition = next(
            item
            for item in topology["operations"]
            if item["semantic_id"] == "feedback-acquisition"
        )
        self.assertEqual(feedback_acquisition["access"], "read")
        self.assertEqual(
            feedback_acquisition["callers"],
            ["addressing-pr-review-feedback", "getting-prs-merged"],
        )

        resume_evals = json.loads(
            (
                self.repo / EVAL_ROOT / "skills/resuming-reviewed-prs/evals.json"
            ).read_text()
        )
        by_name = {item["name"]: item for item in resume_evals["evals"]}
        for name in ("feedback-terminal-handoff", "readiness-terminal-handoff"):
            with self.subTest(eval=name):
                expected = by_name[name]["expected_output"]
                self.assertIn("exactly one terminal handoff", expected)
                self.assertIn("ends its invocation", expected)
                self.assertIn("continues the authorized task", expected)

    def test_rejects_missing_merge_feedback_continuation(self) -> None:
        topology = json.loads((self.plugin / "topology.json").read_text())
        merge = next(
            item for item in topology["skills"] if item["name"] == "getting-prs-merged"
        )
        feedback = next(
            item for item in topology["operations"]
            if item["semantic_id"] == "feedback-outcome"
        )
        merge["calls"].remove("operation:feedback-outcome")
        feedback["callers"].remove("getting-prs-merged")
        self.write_json("topology.json", topology)

        with self.assertRaisesRegex(
            VALIDATE_MERGECRAFT.ContractError,
            "merge feedback continuation drift",
        ):
            VALIDATE_MERGECRAFT.validate_topology(self.plugin)

    def test_rejects_unconditional_readiness_handoff(self) -> None:
        topology = json.loads((self.plugin / "topology.json").read_text())
        merge = next(
            item for item in topology["skills"] if item["name"] == "getting-prs-merged"
        )
        handoff = next(
            item for item in merge["contract"]["terminal_handoffs"]
            if item["owner"] == "getting-prs-ready-for-review"
        )
        handoff["trigger"] = "pr-absent-or-not-review-ready"
        self.write_json("topology.json", topology)

        with self.assertRaisesRegex(
            VALIDATE_MERGECRAFT.ContractError,
            "merge readiness terminal handoff drift",
        ):
            VALIDATE_MERGECRAFT.validate_topology(self.plugin)

    def test_handoff_consumers_require_the_shared_continuation_reference(self) -> None:
        readers = {
            "getting-prs-merged/SKILL.md": "references/caller-continuation.md",
            "addressing-pr-review-feedback/SKILL.md": "../getting-prs-merged/references/caller-continuation.md",
            "resuming-reviewed-prs/SKILL.md": "../getting-prs-merged/references/caller-continuation.md",
            "getting-prs-ready-for-review/SKILL.md": "../getting-prs-merged/references/caller-continuation.md",
            "getting-prs-merged/references/gh-fix-ci-adapter.md": "caller-continuation.md",
        }
        for relative, target in readers.items():
            with self.subTest(reader=relative):
                path = self.plugin / "skills" / relative
                original = path.read_text()
                path.write_text(original.replace(
                    f"[caller continuation]({target})", "caller continuation"
                ))
                try:
                    with self.assertRaisesRegex(
                        VALIDATE_MERGECRAFT.ContractError,
                        "caller continuation pointer drift",
                    ):
                        VALIDATE_MERGECRAFT.validate_links_and_call_projection(self.plugin)
                finally:
                    path.write_text(original)

    def test_merge_feedback_continuation_keeps_only_a_gated_terminal_handoff(
        self,
    ) -> None:
        VALIDATE_MERGECRAFT.validate_topology(self.plugin)
        topology = json.loads((self.plugin / "topology.json").read_text())
        skills = {item["name"]: item for item in topology["skills"]}
        merge = skills["getting-prs-merged"]
        self.assertIn("operation:feedback-outcome", merge["calls"])
        self.assertEqual(
            skills["addressing-pr-review-feedback"]["contract"]["terminal_statuses"],
            ["snapshot", "addressed", "blocked"],
        )

        self.assertEqual(
            [
                item for item in merge["contract"]["terminal_handoffs"]
                if item["owner"] == "addressing-pr-review-feedback"
            ],
            [{
                "trigger": "feedback-authority-unavailable-or-feedback-outcome-blocked-or-snapshot",
                "owner": "addressing-pr-review-feedback",
                "resume": "fresh-getting-prs-merged-invocation-after-feedback-gate-clears",
            }],
        )

    def test_merge_accepts_prior_feedback_outcome_for_revalidation(self) -> None:
        topology = json.loads((self.plugin / "topology.json").read_text())
        skills = {item["name"]: item for item in topology["skills"]}
        self.assertIn(
            "verified-feedback-outcome",
            skills["addressing-pr-review-feedback"]["contract"]["outputs"],
        )
        self.assertIn(
            "prior-feedback-outcome-or-explicit-absence",
            skills["getting-prs-merged"]["contract"]["inputs"],
        )

    def test_rejects_missing_prior_feedback_outcome_input(self) -> None:
        topology = json.loads((self.plugin / "topology.json").read_text())
        merge = next(
            item for item in topology["skills"] if item["name"] == "getting-prs-merged"
        )
        merge["contract"]["inputs"].remove("prior-feedback-outcome-or-explicit-absence")
        self.write_json("topology.json", topology)

        with self.assertRaisesRegex(
            VALIDATE_MERGECRAFT.ContractError,
            "merge prior feedback outcome input drift",
        ):
            VALIDATE_MERGECRAFT.validate_topology(self.plugin)

    def test_rejects_merge_owned_feedback_adjudication_or_revision(self) -> None:
        original = json.loads((self.plugin / "topology.json").read_text())
        for semantic_id in ("finding-adjudication", "source-revision"):
            with self.subTest(operation=semantic_id):
                topology = copy.deepcopy(original)
                merge = next(
                    item for item in topology["skills"]
                    if item["name"] == "getting-prs-merged"
                )
                merge["calls"].append(f"operation:{semantic_id}")
                operation = next(
                    item for item in topology["operations"]
                    if item["semantic_id"] == semantic_id
                )
                operation["callers"] = sorted([*operation["callers"], merge["name"]])
                self.write_json("topology.json", topology)

                with self.assertRaisesRegex(
                    VALIDATE_MERGECRAFT.ContractError,
                    "merge feedback adjudication ownership drift",
                ):
                    VALIDATE_MERGECRAFT.validate_topology(self.plugin)

    def test_rejects_feedback_continuation_owner_or_authority_drift(self) -> None:
        original = json.loads((self.plugin / "topology.json").read_text())
        for drift in ("owner", "operation-authority", "contract-authority"):
            with self.subTest(drift=drift):
                topology = copy.deepcopy(original)
                skills = {item["name"]: item for item in topology["skills"]}
                feedback = skills["addressing-pr-review-feedback"]
                operation = next(
                    item for item in topology["operations"]
                    if item["semantic_id"] == "feedback-outcome"
                )
                if drift == "owner":
                    owner = skills["getting-prs-ready-for-review"]
                    feedback["operations"].remove("feedback-outcome")
                    owner["operations"].append("feedback-outcome")
                    operation["owner"] = owner["name"]
                    operation["implementation"] = owner["entrypoint"]
                    operation["callers"] = ["getting-prs-merged", owner["name"]]
                elif drift == "operation-authority":
                    operation["authority"] = "merge authority authorizes source edits"
                else:
                    feedback["contract"]["authority"] = "merge authority authorizes source edits"
                self.write_json("topology.json", topology)

                with self.assertRaisesRegex(
                    VALIDATE_MERGECRAFT.ContractError,
                    "feedback outcome ownership or authority drift",
                ):
                    VALIDATE_MERGECRAFT.validate_topology(self.plugin)

    def test_rejects_feedback_continuation_result_or_mode_drift(self) -> None:
        original = json.loads((self.plugin / "topology.json").read_text())
        for field, value in (
            ("terminal_statuses", ["snapshot", "clean", "blocked"]),
            ("terminal_statuses", ["addressed", "blocked"]),
            ("modes", ["address"]),
        ):
            with self.subTest(field=field, value=value):
                topology = copy.deepcopy(original)
                feedback = next(
                    item for item in topology["skills"]
                    if item["name"] == "addressing-pr-review-feedback"
                )
                feedback["contract"][field] = value
                self.write_json("topology.json", topology)

                with self.assertRaisesRegex(
                    VALIDATE_MERGECRAFT.ContractError,
                    "feedback outcome mode or result drift",
                ):
                    VALIDATE_MERGECRAFT.validate_topology(self.plugin)

    def test_rejects_unconditional_or_snapshot_omitting_feedback_handoff(self) -> None:
        original = json.loads((self.plugin / "topology.json").read_text())
        for trigger in (
            "current-actionable-feedback-or-requested-changes",
            "feedback-authority-unavailable-or-feedback-outcome-blocked",
        ):
            with self.subTest(trigger=trigger):
                topology = copy.deepcopy(original)
                merge = next(
                    item for item in topology["skills"]
                    if item["name"] == "getting-prs-merged"
                )
                handoff = next(
                    item for item in merge["contract"]["terminal_handoffs"]
                    if item["owner"] == "addressing-pr-review-feedback"
                )
                handoff["trigger"] = trigger
                self.write_json("topology.json", topology)

                with self.assertRaisesRegex(
                    VALIDATE_MERGECRAFT.ContractError,
                    "merge feedback terminal handoff drift",
                ):
                    VALIDATE_MERGECRAFT.validate_topology(self.plugin)

    def test_rejects_feedback_reverse_call_into_merge(self) -> None:
        topology = json.loads((self.plugin / "topology.json").read_text())
        feedback = next(
            item for item in topology["skills"]
            if item["name"] == "addressing-pr-review-feedback"
        )
        feedback["calls"].append("operation:merge-outcome")
        operation = next(
            item for item in topology["operations"]
            if item["semantic_id"] == "merge-outcome"
        )
        operation["callers"].insert(0, feedback["name"])
        self.write_json("topology.json", topology)

        with self.assertRaisesRegex(
            VALIDATE_MERGECRAFT.ContractError,
            "outcome coordinator call edge",
        ):
            VALIDATE_MERGECRAFT.validate_topology(self.plugin)

    def test_rejects_other_operations_owned_by_readiness_coordinator(self) -> None:
        topology = json.loads((self.plugin / "topology.json").read_text())
        skills = {item["name"]: item for item in topology["skills"]}
        other_operation = copy.deepcopy(next(
            item for item in topology["operations"]
            if item["semantic_id"] == "readiness-outcome"
        ))
        other_operation["semantic_id"] = "other-readiness-outcome"
        topology["operations"].append(other_operation)
        skills["getting-prs-ready-for-review"]["operations"].append(
            "other-readiness-outcome"
        )
        skills["getting-prs-merged"]["calls"].append(
            "operation:other-readiness-outcome"
        )
        self.write_json("topology.json", topology)
        with self.assertRaisesRegex(
            VALIDATE_MERGECRAFT.ContractError,
            "outcome coordinator call edge",
        ):
            VALIDATE_MERGECRAFT.validate_topology(self.plugin)

    def test_rejects_outcome_coordinator_call_edge_and_feedback_handoff_drift(
        self,
    ) -> None:
        path = self.plugin / "topology.json"
        topology = json.loads(path.read_text())
        readiness = next(
            item
            for item in topology["skills"]
            if item["name"] == "getting-prs-ready-for-review"
        )
        readiness["calls"].append("operation:feedback-outcome")
        self.write_json("topology.json", topology)
        with self.assertRaisesRegex(
            VALIDATE_MERGECRAFT.ContractError,
            "outcome coordinator call edge",
        ):
            VALIDATE_MERGECRAFT.validate_topology(self.plugin)

        shutil.copy2(REPO_ROOT / PLUGIN / "topology.json", path)
        topology = json.loads(path.read_text())
        merge = next(
            item for item in topology["skills"] if item["name"] == "getting-prs-merged"
        )
        merge["calls"].remove("operation:feedback-acquisition")
        acquisition = next(
            item
            for item in topology["operations"]
            if item["semantic_id"] == "feedback-acquisition"
        )
        acquisition["callers"].remove("getting-prs-merged")
        self.write_json("topology.json", topology)
        with self.assertRaisesRegex(
            VALIDATE_MERGECRAFT.ContractError,
            "merge feedback terminal handoff drift",
        ):
            VALIDATE_MERGECRAFT.validate_topology(self.plugin)

    def test_resume_routes_conflict_ci_and_status_without_merge_authority(
        self,
    ) -> None:
        topology = json.loads((self.plugin / "topology.json").read_text())
        resume = next(
            item
            for item in topology["skills"]
            if item["name"] == "resuming-reviewed-prs"
        )
        handoffs = resume["contract"]["terminal_handoffs"]
        self.assertEqual(
            [(item["trigger"], item["owner"]) for item in handoffs[:2]],
            [
                (
                    "active-git-conflict-operation",
                    "versionkeeping:resolving-merge-conflicts",
                ),
                ("failed-required-github-actions", "operation:focused-ci"),
            ],
        )
        self.assertIn("status-only", resume["contract"]["modes"])
        self.assertIn("reported", resume["contract"]["terminal_statuses"])
        self.assertEqual(resume["calls"], ["operation:publication-audit"])

        skill = (self.plugin / "skills/resuming-reviewed-prs/SKILL.md").read_text()
        self.assertIn("status-only request", skill)
        self.assertIn("active conflict", skill)
        self.assertIn("failed required GitHub Actions", skill)
        self.assertIn("without merge authority", skill)

        evals = json.loads(
            (
                self.repo / EVAL_ROOT / "skills/resuming-reviewed-prs/evals.json"
            ).read_text()
        )
        by_name = {item["name"]: item for item in evals["evals"]}
        self.assertIn("active-conflict-terminal-handoff", by_name)
        self.assertIn("required-actions-terminal-handoff", by_name)
        self.assertIn("status-only-read-only", by_name)

    def test_routing_corpus_separates_pr_ship_from_issue_and_release_publication(
        self,
    ) -> None:
        corpus = json.loads((self.repo / EVAL_ROOT / "corpus.json").read_text())
        scenarios = {item["id"]: item for item in corpus["scenarios"]}
        self.assertIn(
            "getting-prs-merged", scenarios["pr-ship-positive-route"]["must_include"]
        )
        for scenario_id in (
            "issue-edit-negative-route",
            "non-pr-publication-negative-route",
        ):
            self.assertIn(
                "publishing-reviewable-prs", scenarios[scenario_id]["must_not_include"]
            )
            self.assertIn(
                "getting-prs-merged", scenarios[scenario_id]["must_not_include"]
            )

    def test_rejects_merge_handoff_prose_drift_through_content_identity(self) -> None:
        path = self.plugin / "skills/getting-prs-merged/SKILL.md"
        path.write_text(
            path.read_text().replace(
                "terminate this invocation with an exact handoff to\n"
                "   `tricritical:loop`",
                "for every merge request.",
            )
        )
        self.assert_rejected("relation evaluation evidence: current source binding")

    def test_invalid_write_candidate_preserves_existing_content_lock_bytes(
        self,
    ) -> None:
        lock_path = self.repo / CONTENT_LOCK
        original_lock = lock_path.read_bytes()
        manifest_path = self.plugin / "plugin.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["version"] = "invalid-candidate"
        manifest_path.write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )

        result = self.run_validator("--write-content-lock")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("manifest", result.stderr.lower())
        self.assertEqual(lock_path.read_bytes(), original_lock)

    def test_write_content_lock_rejects_symlinked_release_ancestor_without_external_changes(
        self,
    ) -> None:
        release = self.repo / "release"
        external_release = self.repo.parent / "outside-release"
        release.rename(external_release)
        try:
            release.symlink_to(external_release, target_is_directory=True)
        except OSError as error:
            self.skipTest(f"symlink creation is unavailable: {error}")
        external_lock = external_release / "plugin-content-locks/mergecraft.json"
        external_lock.write_bytes(b"outside sentinel\n")
        original_entries = tuple(sorted(external_lock.parent.iterdir()))

        result = self.run_validator("--source-stage", "--write-content-lock")

        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual(external_lock.read_bytes(), b"outside sentinel\n")
        self.assertEqual(
            tuple(sorted(external_lock.parent.iterdir())),
            original_entries,
        )

    def test_write_content_lock_accepts_relative_repository_root(self) -> None:
        lock_path = self.repo / CONTENT_LOCK
        expected_lock = lock_path.read_bytes()
        lock_path.write_text("{}\n", encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                str(VALIDATOR),
                ".",
                "--write-content-lock",
            ],
            cwd=self.repo,
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Mergecraft semantic content lock updated", result.stdout)
        self.assertEqual(lock_path.read_bytes(), expected_lock)

    def test_unknown_repository_user_uses_contract_error_surface(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(VALIDATOR),
                "~mergecraft-path-regression-user-2f74c3db2e5b4b8cb6d0",
            ],
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertNotIn("Traceback (most recent call last)", result.stderr)
        self.assertTrue(
            result.stderr.startswith("Mergecraft contract validation failed: "),
            result.stderr,
        )
        self.assertEqual(len(result.stderr.splitlines()), 1, result.stderr)

    def test_detected_late_refresh_failure_restores_content_lock_bytes(
        self,
    ) -> None:
        lock_path = self.repo / CONTENT_LOCK
        original_lock = lock_path.read_bytes()
        document = self.plugin / "README.md"
        document.write_text(
            document.read_text(encoding="utf-8") + "\nValid semantic change.\n",
            encoding="utf-8",
        )
        real_replace = os.replace

        def replace_then_drift(
            source: object,
            destination: object,
            **kwargs: object,
        ) -> None:
            real_replace(source, destination, **kwargs)
            if Path(destination).name == lock_path.name:
                document.write_text(
                    document.read_text(encoding="utf-8")
                    + "\nConcurrent semantic change.\n",
                    encoding="utf-8",
                )

        stderr = io.StringIO()
        with (
            mock.patch.object(
                os,
                "replace",
                side_effect=replace_then_drift,
            ),
            mock.patch.object(
                VALIDATE_MERGECRAFT.sys,
                "argv",
                [
                    "validate_mergecraft.py",
                    str(self.repo),
                    "--write-content-lock",
                ],
            ),
            contextlib.redirect_stderr(stderr),
        ):
            result = VALIDATE_MERGECRAFT.main()

        self.assertNotEqual(result, 0)
        self.assertIn("validated inputs changed", stderr.getvalue())
        self.assertEqual(lock_path.read_bytes(), original_lock)

    def test_github_operation_inventory_is_complete_and_collision_free(self) -> None:
        topology = json.loads((self.plugin / "topology.json").read_text())
        operations = {
            alias: (item["access"], item["owner"])
            for item in topology["operations"]
            for alias in item["github_aliases"]
        }
        self.assertEqual(
            len(operations),
            sum(len(item["github_aliases"]) for item in topology["operations"]),
        )
        required = {
            "pr-create",
            "issue-pr-relation-read",
            "issue-body-write",
            "issue-pr-development-write",
            "pr-relation-ledger-write",
            "repository-orientation",
            "pr-orientation",
            "issue-orientation",
            "repository-summary",
            "pr-summary",
            "issue-summary",
            "patch-inspection",
            "top-level-comment-read",
            "top-level-comment-write",
            "feedback-conversation-response-write",
            "review-comment-read",
            "review-reply-write",
            "labels-read",
            "labels-write",
            "reactions-read",
            "reactions-write",
            "review-submit-comment",
            "review-submit-approve",
            "review-submit-request-changes",
            "review-thread-resolution",
            "check-inspection",
            "check-rerun",
            "bot-review-request",
            "pr-text-read",
            "pr-text-write",
            "pr-readiness-read",
            "pr-readiness-write",
            "merge-inspection",
            "merge-write",
        }
        self.assertEqual(set(operations), required)
        self.assertEqual(
            operations["pr-text-write"],
            ("write", "publishing-reviewable-prs"),
        )
        for alias in (
            "pr-text-read",
            "issue-pr-relation-read",
            "pr-readiness-read",
            "check-inspection",
            "merge-inspection",
        ):
            self.assertEqual(operations[alias][0], "read")
        for alias in (
            "pr-text-write",
            "issue-body-write",
            "issue-pr-development-write",
            "pr-relation-ledger-write",
            "pr-readiness-write",
            "check-rerun",
            "feedback-conversation-response-write",
            "merge-write",
        ):
            self.assertEqual(operations[alias][0], "write")
        self.assertEqual(
            next(
                item["import"]
                for item in topology["operations"]
                if item["semantic_id"] == "git-ref-push"
            ),
            "versionkeeping:checkpointing-and-publishing-git-work",
        )
        remote = next(
            item
            for item in topology["operations"]
            if item["semantic_id"] == "remote-ref-deletion"
        )
        self.assertEqual(remote["import"], remote["owner"])
        self.assertEqual(remote["access"], "write")

    def test_operation_calls_are_mode_specific_and_recovery_routes_are_complete(
        self,
    ) -> None:
        topology = json.loads((self.plugin / "topology.json").read_text())
        skills = {item["name"]: item for item in topology["skills"]}
        operations = {item["semantic_id"]: item for item in topology["operations"]}

        self.assertEqual(
            skills["resuming-reviewed-prs"]["calls"],
            ["operation:publication-audit"],
        )
        merge_publication_calls = {
            call
            for call in skills["getting-prs-merged"]["calls"]
            if operations[call.removeprefix("operation:")]["owner"]
            == "publishing-reviewable-prs"
        }
        self.assertEqual(
            merge_publication_calls,
            {"operation:publication-audit"},
        )
        self.assertEqual(
            operations["feedback-acquisition"]["callers"],
            ["addressing-pr-review-feedback", "getting-prs-merged"],
        )
        self.assertEqual(operations["feedback-acquisition"]["access"], "read")

        graphite_modes = set(skills["graphite"]["contract"]["modes"])
        self.assertEqual(
            graphite_modes,
            {
                "create",
                "track",
                "navigate",
                "reparent",
                "metadata-repair",
                "diagnose",
                "restack",
                "submit-draft",
            },
        )
        cleanup = next(
            item
            for item in skills["getting-prs-merged"]["contract"]["terminal_handoffs"]
            if item["owner"] == "operation:remote-ref-deletion"
        )
        self.assertEqual(
            cleanup["trigger"],
            "verified-merge-and-authorized-remote-ref-deletion",
        )

        for skill in skills.values():
            self.assertTrue(
                all(call.startswith("operation:") for call in skill["calls"]),
                skill["name"],
            )

    def test_rejects_alias_access_drift_and_callee_wide_fanout(self) -> None:
        topology = json.loads((self.plugin / "topology.json").read_text())
        text_read = next(
            item
            for item in topology["operations"]
            if item["semantic_id"] == "pr-text-read"
        )
        text_read["access"] = "write"
        self.write_json("topology.json", topology)
        self.assert_rejected("GitHub operation access drift")

        topology = json.loads((REPO_ROOT / PLUGIN / "topology.json").read_text())
        graphite = next(
            item for item in topology["skills"] if item["name"] == "graphite"
        )
        graphite["calls"].append("publishing-reviewable-prs")
        self.write_json("topology.json", topology)
        self.assert_rejected("callee-wide operation fanout")

    def test_rejects_merge_eval_grader_answer_leak(self) -> None:
        path = (
            self.repo
            / EVAL_ROOT
            / "skills/getting-prs-merged/fixtures/stalled-external-review.md"
        )
        path.write_text(path.read_text() + "\nExpected behavior: merge now.\n")
        self.assert_rejected("merge eval grader answer leaked into fixture")

    def test_rejects_raw_leaf_eval_grader_answer_leak(self) -> None:
        path = (
            self.repo
            / EVAL_ROOT
            / "skills/interacting-with-pr-review-feedback/fixtures/"
            / "authorized-reply-and-resolution-boundary.md"
        )
        path.write_text(path.read_text() + "\nExpected behavior: resolve it.\n")

        with self.assertRaisesRegex(
            VALIDATE_MERGECRAFT.ContractError,
            "raw eval grader answer leaked into fixture",
        ):
            VALIDATE_MERGECRAFT.validate_raw_skill_eval_isolation(self.repo)

    def test_rejects_writer_forge_terminal_boundary_regression(self) -> None:
        path = self.plugin / "skills/writing-reviewable-pr-descriptions/SKILL.md"
        path.write_text(
            path.read_text().replace(
                "Do not mutate the forge or verify stored/rendered state",
                "Publish and verify the stored state",
            )
        )
        self.assert_rejected("writer content-only terminal boundary drift")

    def test_rejects_writer_independent_review_gate_regression(self) -> None:
        path = self.plugin / "skills/writing-reviewable-pr-descriptions/SKILL.md"
        path.write_text(
            path.read_text().replace("bare `clean`", "unverified clean")
        )
        self.assert_rejected("writer independent review gate drift")

    def test_rejects_pr_text_secret_blocker_regression(self) -> None:
        path = (
            self.plugin
            / "skills/writing-reviewable-pr-descriptions/references/body-contract.md"
        )
        path.write_text(
            path.read_text().replace(
                "Never quote, echo, preserve, or republish it",
                "preserve the live value",
            )
        )
        self.assert_rejected("PR text secret blocker drift")

    def test_rejects_feedback_snapshot_mode_regression(self) -> None:
        path = self.plugin / "skills/addressing-pr-review-feedback/SKILL.md"
        path.write_text(path.read_text().replace("stop before step 2", "continue"))
        self.assert_rejected("feedback snapshot mode drift")

    def test_rejects_gh_fix_ci_adapter_broadening(self) -> None:
        path = self.plugin / "skills/getting-prs-merged/references/gh-fix-ci-adapter.md"
        path.write_text(path.read_text().replace("merge actuation", "merge handling"))
        self.assert_rejected("gh-fix-ci adapter authority drift")

    def test_rejects_merge_actuator_broadening(self) -> None:
        path = self.plugin / "skills/getting-prs-merged/references/merge-actuator.md"
        path.write_text(
            path.read_text().replace(
                "execute at most once",
                "execute repeatedly",
            )
        )
        self.assert_rejected("merge actuator authority drift")

    def test_rejects_retired_review_orchestration_route(self) -> None:
        path = self.plugin / "skills/resuming-reviewed-prs/SKILL.md"
        path.write_text(path.read_text() + "\nCall pr-review-orchestration.\n")
        self.assert_rejected("retired route")

    def test_rejects_publisher_text_scope_behavior_drift(self) -> None:
        path = (
            self.plugin
            / "skills/publishing-reviewable-prs/scripts/update_reviewable_pr.py"
        )
        path.write_text(
            path.read_text()
            + "\nupdate_text = lambda **kwargs: {'accepted': True}\n"
        )
        self.assert_rejected("candidate runtime behavior")

    def test_rejects_boolean_topology_schema_version(self) -> None:
        path = self.plugin / "topology.json"
        value = json.loads(path.read_text())
        value["schema_version"] = True
        self.write_json("topology.json", value)
        self.assert_rejected("topology identity drift")

    def test_rejects_readme_projection_drift(self) -> None:
        path = self.plugin / "README.md"
        path.write_text(
            path.read_text().replace(
                "| graphite | Graphite topology",
                "| stack-tool | Graphite topology",
            )
        )
        self.assert_rejected("README skill projection")

    def test_rejects_broken_relative_skill_link(self) -> None:
        path = self.plugin / "skills/graphite/SKILL.md"
        path.write_text(
            path.read_text().replace("../publishing-reviewable-prs", "../missing")
        )
        self.assert_rejected("Agent Skill resource is missing")

    def test_rejects_private_or_personal_content(self) -> None:
        path = self.plugin / "skills/graphite/SKILL.md"
        path.write_text(path.read_text() + "\n/Users/ivan/private\n")
        self.assert_rejected("portability leak")

        path.write_text(
            (REPO_ROOT / PLUGIN / "skills/graphite/SKILL.md").read_text()
            + "\nUse the ivan/ branch prefix.\n"
        )
        self.assert_rejected("portability leak")

    def test_rejects_retired_route_fill_or_compatibility_shim(self) -> None:
        path = self.plugin / "skills/graphite/SKILL.md"
        path.write_text(path.read_text() + "\nUse resolving-workflow-ownership.\n")
        self.assert_rejected("retired route")

        path.write_text(
            (REPO_ROOT / PLUGIN / "skills/graphite/SKILL.md").read_text()
            + "\nRun gh pr create --fill.\n"
        )
        self.assert_rejected("generic generated-text route")

        shim = self.plugin / "skills/getting-prs-merged/scripts/trigger_eval_core.py"
        shim.parent.mkdir(exist_ok=True)
        shim.write_text("pass\n")
        self.assert_rejected("compatibility shim")

    def test_accepts_current_reviewed_atlas_prose(self) -> None:
        VALIDATE_MERGECRAFT.validate_atlas_split(self.repo, self.plugin)

    def test_atlas_evidence_is_repository_owned_and_byte_preserved(self) -> None:
        runtime_references = (
            self.plugin / "skills/writing-reviewable-pr-descriptions/references"
        )
        self.assertFalse((runtime_references / "review-atlas-contract.json").exists())
        self.assertFalse(
            (runtime_references / "review-atlas-contribution-ledger.json").exists()
        )
        topology = json.loads((self.plugin / "topology.json").read_text())
        writer = next(
            component
            for component in topology["skills"]
            if component["name"] == "writing-reviewable-pr-descriptions"
        )
        self.assertNotIn(
            "skills/writing-reviewable-pr-descriptions/references/"
            "review-atlas-contract.json",
            writer["references"],
        )
        self.assertNotIn(
            "skills/writing-reviewable-pr-descriptions/references/"
            "review-atlas-contribution-ledger.json",
            writer["references"],
        )
        # These literals intentionally bind the reviewed release evidence bytes.
        # Review each changed artifact against its owning sources before updating them.
        expected_digests = {
            "review-atlas-contract.json": (
                "c1a56a67d33813303bd1e9e20ec4b9cc6b19cb00c262bd7efe382559d334415c"
            ),
            "review-atlas-contribution-ledger.json": (
                "5804803a8abb18e26c2b7700670d036aadf6d44cab2b0457f7b8a69e1a9e0046"
            ),
        }
        self.assertEqual(
            {
                path.name: VALIDATE_MERGECRAFT.hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()
                for path in (self.repo / ATLAS_RELEASE).iterdir()
            },
            expected_digests,
        )

    def test_rejects_atlas_ledger_gap_or_private_overlay_leak(self) -> None:
        path = self.repo / ATLAS_RELEASE / "review-atlas-contribution-ledger.json"
        value = json.loads(path.read_text())
        value["contributions"][0]["source_headings"] = []
        self.write_atlas_json(
            "review-atlas-contribution-ledger.json",
            value,
        )
        self.assert_rejected("atlas contribution mapping")

        shutil.copy2(
            REPO_ROOT / ATLAS_RELEASE / "review-atlas-contribution-ledger.json",
            path,
        )
        atlas = (
            self.plugin / "skills/writing-reviewable-pr-descriptions/"
            "review-atlas-reference-design.md"
        )
        atlas.write_text(atlas.read_text() + "\nprivate attachment URL\n")
        self.assert_rejected("private atlas detail")

    def test_rejects_synced_atlas_contribution_mapping_swap(self) -> None:
        ledger_relative = "review-atlas-contribution-ledger.json"
        canonical_relative = "review-atlas-contract.json"
        ledger = json.loads((self.repo / ATLAS_RELEASE / ledger_relative).read_text())
        canonical = json.loads(
            (self.repo / ATLAS_RELEASE / canonical_relative).read_text()
        )
        ledger["contributions"][2]["destination_anchor"] = "architecture"
        ledger["contributions"][3]["destination_anchor"] = "design-principles"
        canonical["contribution_ledger"] = ledger
        self.write_atlas_json(ledger_relative, ledger)
        self.write_atlas_json(canonical_relative, canonical)
        self.assert_rejected("atlas contribution mapping drift")

    def test_rejects_self_updated_atlas_prose_digest_for_changed_bytes(self) -> None:
        writer_relative = "skills/writing-reviewable-pr-descriptions/SKILL.md"
        canonical_relative = "review-atlas-contract.json"
        writer = self.plugin / writer_relative
        writer.write_text(
            writer.read_text() + "\nOverlay policy outranks public policy.\n"
        )
        canonical = json.loads(
            (self.repo / ATLAS_RELEASE / canonical_relative).read_text()
        )
        canonical["prose_sha256"]["writer"] = VALIDATE_MERGECRAFT.hashlib.sha256(
            writer.read_bytes()
        ).hexdigest()
        self.write_atlas_json(canonical_relative, canonical)
        result = self.run_validator("--source-stage")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("atlas public prose bytes drift", result.stderr)

    def test_rejects_missing_concrete_atlas_visual_budget(self) -> None:
        path = (
            self.plugin
            / "skills"
            / "writing-reviewable-pr-descriptions"
            / "review-atlas-reference-design.md"
        )
        path.write_text(
            path.read_text().replace(
                "at least 16 CSS pixels between\n  centerlines", ""
            )
        )
        self.assert_rejected("atlas visual budget missing")

    def test_rejects_atlas_writer_firewall_or_body_preservation_drift(self) -> None:
        writer = self.plugin / "skills/writing-reviewable-pr-descriptions/SKILL.md"
        original = writer.read_text()
        weakened = original.replace(
            (
                "Keep atlas source,\ntests, docs, manifests, and generated assets "
                "outside application repositories."
            ),
            "Keep atlas assets available.",
        )
        self.assertNotEqual(weakened, original)
        writer.write_text(weakened)
        self.assert_rejected("atlas writer contract drift")

        shutil.copy2(
            REPO_ROOT / PLUGIN / "skills/writing-reviewable-pr-descriptions/SKILL.md",
            writer,
        )
        body_contract = (
            self.plugin
            / "skills/writing-reviewable-pr-descriptions/references/body-contract.md"
        )
        body_contract.write_text(
            body_contract.read_text().replace(
                "Preserve an unauthorized existing field byte-for-byte.",
                "Preserve fields.",
            )
        )
        self.assert_rejected("atlas body preservation contract drift")

    def test_atlas_extension_contract_is_portable_and_additive(self) -> None:
        path = (
            self.plugin / "skills/writing-reviewable-pr-descriptions/references/"
            "review-atlas-extension.json"
        )
        extension = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(extension["schema_version"], 1)
        self.assertEqual(
            extension["default_overlay_path"],
            "~/.config/mergecraft/review-atlas-overlay.md",
        )
        self.assertEqual(extension["absence"], "continue-public-core")
        self.assertEqual(extension["precedence"], "public-core")
        self.assertEqual(
            set(extension["allowed_authority"]),
            {"instance-data", "stricter-local-policy"},
        )
        self.assertIn("public-contract-redefinition", extension["forbidden_authority"])
        extension["precedence"] = "private-overlay"
        self.write_json(
            "skills/writing-reviewable-pr-descriptions/references/"
            "review-atlas-extension.json",
            extension,
        )
        self.assert_rejected("atlas extension contract drift")

    def test_rejects_boolean_or_float_atlas_ledger_integers(self) -> None:
        relative = "review-atlas-contribution-ledger.json"
        path = self.repo / ATLAS_RELEASE / relative
        original = json.loads(path.read_text())
        for field, malformed in (
            ("schema_version", True),
            ("schema_version", 1.0),
            ("source_line_count", 399.0),
        ):
            with self.subTest(field=field, malformed=malformed):
                ledger = json.loads(json.dumps(original))
                ledger[field] = malformed
                self.write_atlas_json(relative, ledger)
                self.assert_rejected("atlas ledger schema drift")

    def test_rejects_behavior_corpus_coverage_drift(self) -> None:
        path = self.repo / EVAL_ROOT / "corpus.json"
        value = json.loads(path.read_text())
        value["scenarios"] = value["scenarios"][:-1]
        self.write_eval_json("corpus.json", value)
        self.assert_rejected("behavior corpus")

    def test_rejects_boolean_and_float_behavior_corpus_versions(self) -> None:
        path = self.repo / EVAL_ROOT / "corpus.json"
        original = json.loads(path.read_text())
        for malformed in (True, 1.0):
            with self.subTest(malformed=malformed):
                corpus = json.loads(json.dumps(original))
                corpus["version"] = malformed
                self.write_eval_json("corpus.json", corpus)
                self.assert_rejected("behavior corpus schema drift")

    def test_rejects_publisher_parser_behavior_drift(self) -> None:
        state = (
            self.plugin
            / "skills/publishing-reviewable-prs/scripts/reviewable_pr_state.py"
        )
        state.write_text(
            state.read_text()
            + "\nstrict_json = lambda output, source: {'accepted': True}\n"
        )
        self.assert_rejected("candidate runtime behavior")

    def test_rejects_reconciliation_behavior_drift(self) -> None:
        audit = (
            self.plugin
            / "skills/publishing-reviewable-prs/scripts/audit_reviewable_pr.py"
        )
        audit.write_text(audit.read_text() + "\nreconcile = lambda **kwargs: None\n")
        self.assert_rejected("candidate runtime behavior")

    def test_rejects_effective_unknown_ambiguity_probe_regression(self) -> None:
        helper = (
            self.plugin
            / "skills/interacting-with-pr-review-feedback/scripts"
            / "response_identity_lifecycle.py"
        )
        source = helper.read_text(encoding="utf-8")
        changed = source.replace(
            'if len(group["intent_ids"]) > 1:',
            'if False:',
            1,
        )
        self.assertNotEqual(changed, source)
        helper.write_text(changed, encoding="utf-8")

        probe = self.run_candidate_runtime_probe()
        self.assertNotEqual(probe.returncode, 0)
        self.assertIn("C6-S1 ambiguity guard", probe.stderr)
        self.assertNotIn("trusted ssh executable is unavailable", probe.stderr)

        result = self.run_validator("--source-stage")

        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("candidate runtime behavior drift", result.stderr)

    def test_rejects_cross_intent_lifecycle_probe_regression(self) -> None:
        helper = (
            self.plugin
            / "skills/interacting-with-pr-review-feedback/scripts"
            / "response_identity_lifecycle.py"
        )
        source = helper.read_text(encoding="utf-8")
        changed = source.replace(
            'if self._roles(identity) - {intent_id}:',
            'if False:',
            1,
        )
        self.assertNotEqual(changed, source)
        helper.write_text(changed, encoding="utf-8")

        probe = self.run_candidate_runtime_probe()
        self.assertNotEqual(probe.returncode, 0)
        self.assertIn("C6-S2 cross-intent lifecycle guard", probe.stderr)
        self.assertNotIn("trusted ssh executable is unavailable", probe.stderr)

        result = self.run_validator("--source-stage")

        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("candidate runtime behavior drift", result.stderr)

    def test_rejects_stable_source_owner_probe_regression(self) -> None:
        helper = (
            self.plugin
            / "skills/interacting-with-pr-review-feedback/scripts"
            / "response_source_owner.py"
        )
        source = helper.read_text(encoding="utf-8")
        changed = source.replace(
            '"repository_identity": repository,',
            '"repository_identity": copy.deepcopy(legacy_repository),',
            1,
        )
        self.assertNotEqual(changed, source)
        helper.write_text(changed, encoding="utf-8")

        probe = self.run_candidate_runtime_probe()
        self.assertNotEqual(probe.returncode, 0)
        self.assertIn("S7-S1 stable owner rename guard", probe.stderr)
        self.assertNotIn("trusted ssh executable is unavailable", probe.stderr)

        result = self.run_validator("--source-stage")

        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("candidate runtime behavior drift", result.stderr)

    def test_rejects_required_review_authority_behavior_drift(self) -> None:
        required_review = (
            self.plugin
            / "skills/publishing-reviewable-prs/scripts/required_review.py"
        )
        required_review.write_text(
            required_review.read_text()
            + "\nvalidate_required_review = lambda **kwargs: None\n"
        )
        self.assert_rejected("candidate runtime behavior")

    def assert_removed_authority_guard_rejected(self, field: str) -> None:
        required_review = (
            self.plugin
            / "skills/publishing-reviewable-prs/scripts/required_review.py"
        )
        tree = ast.parse(required_review.read_text(encoding="utf-8"))
        remover = AuthorityGuardRemover(field)
        tree = remover.visit(tree)
        self.assertEqual(remover.removed, 1)
        required_review.write_text(
            ast.unparse(ast.fix_missing_locations(tree)) + "\n",
            encoding="utf-8",
        )

        result = self.run_validator("--source-stage")

        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("candidate runtime behavior", result.stderr)

    def test_source_stage_rejects_removed_required_review_access_guard(self) -> None:
        self.assert_removed_authority_guard_rejected("access")

    def test_source_stage_rejects_removed_required_review_subdelegation_guard(
        self,
    ) -> None:
        self.assert_removed_authority_guard_rejected("subdelegation")

    def test_source_stage_rejects_removed_required_review_external_action_guard(
        self,
    ) -> None:
        self.assert_removed_authority_guard_rejected("external_action")

    def test_rejects_create_lifecycle_behavior_drift(self) -> None:
        create = (
            self.plugin
            / "skills/publishing-reviewable-prs/scripts/create_reviewable_pr.py"
        )
        create.write_text(
            create.read_text() + "\npublish = lambda **kwargs: {'accepted': True}\n"
        )
        self.assert_rejected("candidate runtime behavior")

    def test_rejects_receipt_audit_behavior_drift(self) -> None:
        receipts = (
            self.plugin
            / "skills/publishing-reviewable-prs/scripts/publication_receipts.py"
        )
        receipts.write_text(
            receipts.read_text()
            + "\naudit_publication = lambda **kwargs: {'accepted': True}\n"
        )
        self.assert_rejected("candidate runtime behavior")

    def test_rejects_graphite_scope_and_authority_behavior_drift(self) -> None:
        graphite = self.plugin / "skills/graphite/scripts/submit_draft_stack.py"
        graphite.write_text(
            graphite.read_text() + "\nbuild_plan = lambda request: {'accepted': True}\n"
        )
        self.assert_rejected("candidate runtime behavior")

    def test_rejects_comment_publication_behavior_drift(self) -> None:
        comment = (
            self.plugin
            / "skills/getting-prs-merged/scripts/post_coderabbit_comment.py"
        )
        comment.write_text(
            comment.read_text() + "\npost_comment = lambda **kwargs: {'accepted': True}\n"
        )
        self.assert_rejected("candidate runtime behavior")

    def test_accepts_closed_comment_acknowledgement_runtime_contract(self) -> None:
        probe = self.run_comment_acknowledgement_probe()

        self.assertEqual(probe.returncode, 0, probe.stderr)

    def test_rejects_comment_acknowledgement_digest_drift(self) -> None:
        comment = (
            self.plugin
            / "skills/getting-prs-merged/scripts/post_coderabbit_comment.py"
        )
        comment.write_text(
            comment.read_text(encoding="utf-8")
            + "\n_original_post_comment = post_comment\n"
            + "def post_comment(**kwargs):\n"
            + "    receipt = _original_post_comment(**kwargs)\n"
            + "    receipt['body_sha256'] = '0' * 64\n"
            + "    return receipt\n",
            encoding="utf-8",
        )

        probe = self.run_comment_acknowledgement_probe()

        self.assertNotEqual(probe.returncode, 0)

    def test_rejects_comment_acknowledgement_provider_field_disclosure(self) -> None:
        comment = (
            self.plugin
            / "skills/getting-prs-merged/scripts/post_coderabbit_comment.py"
        )
        comment.write_text(
            comment.read_text(encoding="utf-8")
            + "\n_original_post_comment = post_comment\n"
            + "def post_comment(**kwargs):\n"
            + "    receipt = _original_post_comment(**kwargs)\n"
            + "    receipt['user']['provider_debug'] = 'arbitrary provider field'\n"
            + "    return receipt\n",
            encoding="utf-8",
        )

        probe = self.run_comment_acknowledgement_probe()

        self.assertNotEqual(probe.returncode, 0)

    def test_rejects_publisher_exact_identity_behavior_drift(self) -> None:
        state = (
            self.plugin
            / "skills/publishing-reviewable-prs/scripts/reviewable_pr_state.py"
        )
        state.write_text(
            state.read_text()
            + "\nidentity_matches = lambda stored, expected: True\n"
        )
        self.assert_rejected("candidate runtime behavior")

    def test_rejects_feedback_parser_behavior_drift(self) -> None:
        state = (
            self.plugin
            / "skills/addressing-pr-review-feedback/scripts/review_feedback_state.py"
        )
        state.write_text(
            state.read_text()
            + "\nstrict_json = lambda content, source: {'accepted': True}\n"
        )
        self.assert_rejected("candidate runtime behavior")

    def test_rejects_feedback_state_behavior_drift(self) -> None:
        state = (
            self.plugin
            / "skills/addressing-pr-review-feedback/scripts/review_feedback_state.py"
        )
        state.write_text(
            state.read_text() + "\nstate_from_pages = lambda *args, **kwargs: {}\n"
        )
        self.assert_rejected("candidate runtime behavior")

    def test_rejects_review_input_parser_behavior_drift(self) -> None:
        parser = self.plugin / (
            "skills/writing-reviewable-pr-descriptions/scripts/"
            "change_navigation/review_input.py"
        )
        parser.write_text(
            parser.read_text() + "\nload_review_input = lambda path: object()\n"
        )
        self.assert_rejected("candidate runtime behavior")

    def test_rejects_semantic_drift_not_named_by_phrase_checks(self) -> None:
        path = self.plugin / "README.md"
        path.write_text(
            path.read_text() + "\nPublication may skip final verification.\n"
        )
        self.assert_rejected("semantic content lock mismatch")

    def test_rejects_retirement_ledger_missing_or_duplicate_contribution(self) -> None:
        path = self.retirement_ledger
        original = json.loads(path.read_text())

        missing = copy.deepcopy(original)
        missing["contributions"].pop()
        self.write_ledger(missing)
        self.assert_rejected("retirement contribution coverage drift")

        duplicate = copy.deepcopy(original)
        duplicate["contributions"].append(copy.deepcopy(duplicate["contributions"][0]))
        self.write_ledger(duplicate)
        self.assert_rejected("retirement contribution schema drift")

    def test_rejects_retirement_ledger_unmapped_fixture_or_owner(self) -> None:
        path = self.retirement_ledger
        original = json.loads(path.read_text())

        unmapped_fixture = copy.deepcopy(original)
        unmapped_fixture["contributions"][0]["fixture"] = "missing-fixture"
        self.write_ledger(unmapped_fixture)
        self.assert_rejected("retirement contribution schema drift")

        unmapped_owner = copy.deepcopy(original)
        unmapped_owner["contributions"][0]["destination_owner"] = "unmapped-owner"
        self.write_ledger(unmapped_owner)
        self.assert_rejected("retirement contribution schema drift")

    def test_rejects_retirement_fixture_assertion_polarity_or_evaluation_drift(
        self,
    ) -> None:
        corpus_path = self.repo / EVAL_ROOT / "retirement-comparative-corpus.json"
        corpus = json.loads(corpus_path.read_text())
        (
            corpus["scenarios"][0]["must_include"],
            corpus["scenarios"][0]["must_not_include"],
        ) = (
            corpus["scenarios"][0]["must_not_include"],
            corpus["scenarios"][0]["must_include"],
        )
        self.write_eval_json("retirement-comparative-corpus.json", corpus)
        self.assert_rejected("retirement fixture assertion polarity drift")

        shutil.copy2(
            REPO_ROOT / EVAL_ROOT / "retirement-comparative-corpus.json", corpus_path
        )
        fixtures_path = self.repo / EVAL_ROOT / "retirement-fixtures.json"
        fixtures = json.loads(fixtures_path.read_text())
        fixtures["fixtures"][0]["topology_operations"] = ["missing-operation"]
        self.write_eval_json("retirement-fixtures.json", fixtures)
        self.assert_rejected("retirement fixture coverage drift")

    def test_retirement_control_plane_definition_validates_without_a_provider(
        self,
    ) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(CONTROL_PLANE_EVALUATOR),
                "--repo",
                str(REPO_ROOT),
                "--definition",
                str(REPO_ROOT / EVAL_ROOT / "retirement-control-plane.json"),
                "validate-definition",
            ],
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"skills": 17', result.stdout)

    def test_rejects_retirement_destination_owner_missing_from_bundle(self) -> None:
        definition_path = self.repo / EVAL_ROOT / "retirement-control-plane.json"
        original = json.loads(definition_path.read_text())
        mutations = (
            (
                "ordinary-tool",
                lambda skills: skills["mergecraft:resuming-reviewed-prs"][
                    "comparison"
                ].update(owner="wrong-ordinary-owner"),
            ),
            (
                "feedback-acquisition",
                lambda skills: skills[
                    "mergecraft:addressing-pr-review-feedback"
                ].update(
                    companions=[
                        "tricritical:adjudicate",
                        "tricritical:revise",
                        "versionkeeping:checkpointing-and-publishing-git-work",
                    ]
                ),
            ),
            (
                "checkpointing",
                lambda skills: skills["mergecraft:getting-prs-ready-for-review"].update(
                    companions=[
                        "mergecraft:writing-reviewable-pr-descriptions",
                        "mergecraft:publishing-reviewable-prs",
                    ]
                ),
            ),
            (
                "retained-specialist",
                lambda skills: skills["mergecraft:getting-prs-merged"][
                    "comparison"
                ].update(owner="github:other-specialist"),
            ),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                definition = copy.deepcopy(original)
                skills = {skill["id"]: skill for skill in definition["skills"]}
                mutate(skills)
                self.write_eval_json("retirement-control-plane.json", definition)
                self.assert_rejected(
                    "retirement destination owner is absent from evaluated bundle"
                )

    def test_rejects_feedback_leaf_as_the_acquisition_target(self) -> None:
        fixtures_path = self.repo / EVAL_ROOT / "retirement-fixtures.json"
        fixtures = json.loads(fixtures_path.read_text())
        fixtures["fixtures"][1]["evaluation_skill_id"] = (
            "mergecraft:interacting-with-pr-review-feedback"
        )
        self.write_eval_json("retirement-fixtures.json", fixtures)
        self.assert_rejected("retirement fixture coverage drift")


class MarkdownEvidenceRefreshTests(unittest.TestCase):
    """Exercise the owning evidence validator without unrelated runtime probes."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        for relative in (
            PLUGIN / "skills" / MARKDOWN_AUTHORING_SKILL,
            Path("plugins/proseweaving/skills/writing-for-people"),
        ):
            shutil.copytree(REPO_ROOT / relative, self.repo / relative)
        self.plugin = self.repo / PLUGIN
        self.evals = self.plugin / "skills" / MARKDOWN_AUTHORING_SKILL / "evals"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def validate(self) -> None:
        VALIDATE_MERGECRAFT.validate_markdown_authoring_evidence(self.plugin)

    def test_current_full_bundle_and_historical_controls_validate(self) -> None:
        self.validate()

    def test_selected_current_runs_require_successful_tool_free_execution(self) -> None:
        path = self.evals / "experiment.json"
        original = path.read_bytes()
        for field, value in (
            ("technically_valid", False), ("exit_code", 1),
            ("exit_code", False), ("timed_out", True),
            ("result_subtype", "error_during_execution"),
            ("result_is_error", True),
            ("tool_use", [{"type": "tool_use", "name": "Bash"}]),
        ):
            with self.subTest(field=field, value=value):
                data = json.loads(original)
                run = next(r for r in data["behavior_runs"]
                           if r["id"] == "markdown/case-01-with-skill-1")
                run[field] = value
                path.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaisesRegex(
                    VALIDATE_MERGECRAFT.ContractError, "current execution validity drift"
                ):
                    self.validate()
        path.write_bytes(original)

    def test_selected_current_protocol_matches_the_recorded_application_method(self) -> None:
        path = self.evals / "experiment.json"
        original = path.read_bytes()
        mutations = (
            ("launch_error", "Synthetic launch failure"),
            ("decode_error", {"start": 0}), ("parse_errors", ["invalid"]),
            ("stream_valid", False), ("assistant_session_ids", ["other-session"]),
            ("assistant_session_ids", []), ("result_session_id", "other-session"),
            ("result_permission_denials", [{"tool": "Bash"}]),
            ("model_requested", "different-model"), ("effort_requested", "low"),
            ("assistant_models", ["different-model"]),
            ("system_prompt_sha256", "0" * 64),
            ("init.session_id", "other-session"),
            ("init.model", "different-model"), ("init.permissionMode", "default"),
            ("init.claude_code_version", "2.1.263"),
            *((f"init.{key}", ["unexpected"])
              for key in ("tools", "mcp_servers", "skills", "plugins", "slash_commands")),
        )
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                data = json.loads(original)
                run = next(r for r in data["behavior_runs"]
                           if r["id"] == "markdown/case-01-with-skill-1")
                if field.startswith("init."):
                    run["init"][field.removeprefix("init.")] = value
                else:
                    run[field] = value
                path.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaisesRegex(
                    VALIDATE_MERGECRAFT.ContractError, "current execution validity drift"
                ):
                    self.validate()
        for field in ("technically_valid", "exit_code", "timed_out", "launch_error",
                      "decode_error", "parse_errors", "stream_valid", "init",
                      "assistant_session_ids", "result_session_id",
                      "result_permission_denials", "result_is_error", "tool_use"):
            with self.subTest(missing=field):
                data = json.loads(original)
                run = next(r for r in data["behavior_runs"]
                           if r["id"] == "markdown/case-01-with-skill-1")
                del run[field]
                path.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaisesRegex(
                    VALIDATE_MERGECRAFT.ContractError, "current execution validity drift"
                ):
                    self.validate()
        path.write_bytes(original)

    def test_current_grade_requires_the_runs_original_record_digest(self) -> None:
        path = self.evals / "grading.json"
        original = path.read_bytes()
        for value in ("0" * 64, "malformed", None):
            with self.subTest(source_record_sha256=value):
                data = json.loads(original)
                grade = next(r for r in data["runs"]
                             if r["run_id"] == "markdown/case-01-with-skill-1")
                if value is None:
                    del grade["source_record_sha256"]
                else:
                    grade["source_record_sha256"] = value
                path.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaisesRegex(
                    VALIDATE_MERGECRAFT.ContractError, "current grade original record binding drift"
                ):
                    self.validate()
        path.write_bytes(original)
        experiment_path = self.evals / "experiment.json"
        experiment = json.loads(experiment_path.read_bytes())
        run = next(r for r in experiment["behavior_runs"]
                   if r["id"] == "markdown/case-01-with-skill-1")
        run["source_record_sha256"] = "malformed"
        experiment_path.write_text(json.dumps(experiment), encoding="utf-8")
        data = json.loads(original)
        grade = next(r for r in data["runs"] if r["run_id"] == run["id"])
        grade["source_record_sha256"] = "malformed"
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(
            VALIDATE_MERGECRAFT.ContractError, "current grade original record binding drift"
        ):
            self.validate()

    def test_supplemental_findings_and_dispositions_bind_one_to_one_to_current_responses(self) -> None:
        path = self.evals / "grading.json"
        original = path.read_bytes()
        normal_path = self.evals / "normalization.json"
        original_normal = normal_path.read_bytes()
        mutations = (
            ("missing findings", lambda r: r.update(supplemental_findings=[])),
            ("missing dispositions", lambda r: r.update(supplemental_dispositions=[])),
            ("wrong response", lambda r: r["supplemental_findings"][0].update(response_sha256="0" * 64)),
            ("wrong disposition key", lambda r: r["supplemental_dispositions"][0].update(finding_key="unrelated")),
            ("wrong case", lambda r: r["supplemental_findings"][0].update(case_id=1)),
            ("wrong repetition", lambda r: r["supplemental_dispositions"][0].update(repetition=2)),
            ("duplicate finding", lambda r: r["supplemental_findings"].append(r["supplemental_findings"][0])),
            ("duplicate disposition", lambda r: r["supplemental_dispositions"].append(r["supplemental_dispositions"][0])),
            ("unknown run", lambda r: r["supplemental_findings"][0].update(run_id="missing/case-01-with-skill-1")),
            ("changed rubric claim", lambda r: r["supplemental_dispositions"][0].update(changes_original_grade=True)),
            ("wrong origin", lambda r: r["supplemental_dispositions"][0].update(origin="other-grading.json")),
        )
        for name, mutate in mutations:
            with self.subTest(mutation=name):
                data = json.loads(original)
                refresh = data["application_refresh"]
                mutate(refresh)
                path.write_text(json.dumps(data), encoding="utf-8")
                # Recompute the declared projection so this tests correspondence,
                # independently of the separate exact-retention digest check.
                normal = json.loads(original_normal)
                normal["supplemental_projection_sha256"] = {
                    key: hashlib.sha256(json.dumps(refresh[key], sort_keys=True,
                                                 separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
                    for key in ("supplemental_findings", "supplemental_dispositions")
                }
                normal_path.write_text(json.dumps(normal), encoding="utf-8")
                with self.assertRaisesRegex(
                    VALIDATE_MERGECRAFT.ContractError, "supplemental.*drift"
                ):
                    self.validate()
        path.write_bytes(original)
        normal_path.write_bytes(original_normal)

    def test_original_supplemental_text_and_provenance_are_retained(self) -> None:
        path = self.evals / "grading.json"
        original = path.read_bytes()
        mutations = (
            ("remove both lists", lambda r: r.update(supplemental_findings=[], supplemental_dispositions=[])),
            ("rewrite finding", lambda r: r["supplemental_findings"][0].update(finding="Rewritten finding")),
            ("rewrite disposition", lambda r: r["supplemental_dispositions"][0].update(followup="Rewritten disposition")),
            ("wrong grading source", lambda r: r.update(original_grader_artifact_sha256="0" * 64)),
            ("wrong adjudication source", lambda r: r.update(adjudication_source_sha256="0" * 64)),
            ("wrong retention source", lambda r: r.update(retention_review_sha256="0" * 64)),
        )
        for name, mutate in mutations:
            with self.subTest(mutation=name):
                data = json.loads(original)
                mutate(data["application_refresh"])
                path.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaisesRegex(
                    VALIDATE_MERGECRAFT.ContractError, "supplemental.*drift"
                ):
                    self.validate()
        path.write_bytes(original)
        data = json.loads(original)
        del data["application_refresh"]
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(
            VALIDATE_MERGECRAFT.ContractError, "supplemental.*drift"
        ):
            self.validate()

    def test_historical_configuration_cannot_be_relabelled(self) -> None:
        path = self.evals / "experiment.json"
        data = json.loads(path.read_bytes())
        data["experiments"][0]["model"] = "replacement-model"
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(
            VALIDATE_MERGECRAFT.ContractError, "historical retention drift"
        ):
            self.validate()


    def test_every_delivered_dependency_invalidates_the_current_observations(self) -> None:
        # This literal inventory is the approved seven-file delivery contract.
        markdown = "plugins/mergecraft/skills/writing-github-issue-and-pr-markdown"
        prose = "plugins/proseweaving/skills/writing-for-people"
        paths = [
            f"{markdown}/SKILL.md", f"{markdown}/references/authoring-contract.md",
            f"{markdown}/references/review-voice.md", f"{prose}/SKILL.md",
            f"{prose}/references/edit-pass.md",
            f"{prose}/references/evidence-in-prose.md",
            f"{prose}/references/threaded-conversation.md",
        ]
        for relative in paths:
            with self.subTest(dependency=relative):
                path = self.repo / relative
                original = path.read_bytes()
                path.write_bytes(original + b"\nChanged delivery.\n")
                with self.assertRaisesRegex(
                    VALIDATE_MERGECRAFT.ContractError, "source binding drift"
                ):
                    self.validate()
                path.write_bytes(original)

    def test_relabelled_external_dependency_does_not_refresh_old_requests(self) -> None:
        relative = "plugins/proseweaving/skills/writing-for-people/references/edit-pass.md"
        source = self.repo / relative
        source.write_bytes(source.read_bytes() + b"\nNew instruction.\n")
        path = self.evals / "experiment.json"
        data = json.loads(path.read_bytes())
        data["current_delivered_source_sha256"][relative] = hashlib.sha256(
            source.read_bytes()
        ).hexdigest()
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(
            VALIDATE_MERGECRAFT.ContractError, "selected request binding drift"
        ):
            self.validate()

    def test_current_request_must_deliver_the_complete_bundle(self) -> None:
        path = self.evals / "experiment.json"
        data = json.loads(path.read_bytes())
        run = next(r for r in data["behavior_runs"] if r["id"] == "markdown/case-01-with-skill-1")
        request = json.loads(data["requests_by_sha256"][run["request_sha256"]])
        omitted = "plugins/proseweaving/skills/writing-for-people/references/edit-pass.md"
        del request["candidate_bundle"][omitted]
        value = json.dumps(request, indent=2, ensure_ascii=False)
        digest = hashlib.sha256(value.encode()).hexdigest()
        data["requests_by_sha256"][digest] = value
        run["request_sha256"] = digest
        del run["candidate_sha256"][omitted]
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(
            VALIDATE_MERGECRAFT.ContractError, "selected request binding drift"
        ):
            self.validate()

    def test_historical_judgments_and_native_records_remain_immutable(self) -> None:
        for filename, mutate in (
            ("grading.json", lambda d: d["runs"][0]["expectations"][0].update(evidence="Rewritten history")),
            ("experiment.json", lambda d: d["native_and_trigger_runs"].pop()),
        ):
            with self.subTest(artifact=filename):
                path = self.evals / filename
                original = path.read_bytes()
                data = json.loads(original)
                mutate(data)
                path.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaisesRegex(
                    VALIDATE_MERGECRAFT.ContractError, "historical retention drift"
                ):
                    self.validate()
                path.write_bytes(original)

    def test_historical_controls_cannot_be_selected_as_current_application(self) -> None:
        path = self.evals / "grading.json"
        data = json.loads(path.read_bytes())
        data["selected_thresholds"].extend(data["historical_control_thresholds"])
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(
            VALIDATE_MERGECRAFT.ContractError, "selected case coverage drift"
        ):
            self.validate()

    def test_current_failure_is_retained_without_lowering_its_threshold(self) -> None:
        path = self.evals / "grading.json"
        data = json.loads(path.read_bytes())
        criterion = next(r for r in data["selected_thresholds"] if r["severity"] == "safety")
        run_id = f"markdown/case-{criterion['case_id']:02d}-with-skill-1"
        run = next(r for r in data["runs"] if r["run_id"] == run_id)
        expectation = next(e for e in run["expectations"] if e["id"] == criterion["expectation"])
        expectation.update(passed=False, evidence="Synthetic failure for validator regression.")
        for rows in (data["thresholds"], data["selected_thresholds"]):
            for row in rows:
                if row["experiment"] == "markdown" and row["case_id"] == criterion["case_id"] and row["expectation"] == criterion["expectation"]:
                    row.update(passes=2, met=False)
        data["candidate_passed"] = False
        path.write_text(json.dumps(data), encoding="utf-8")
        self.validate()
        for rows in (data["thresholds"], data["selected_thresholds"]):
            for row in rows:
                if row["experiment"] == "markdown" and row["case_id"] == criterion["case_id"] and row["expectation"] == criterion["expectation"]:
                    row.update(required=2, met=True)
        data["candidate_passed"] = True
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(
            VALIDATE_MERGECRAFT.ContractError, "threshold derivation drift"
        ):
            self.validate()


if __name__ == "__main__":
    unittest.main()
