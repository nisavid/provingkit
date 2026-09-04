from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts import validate_provingkit

REPOSITORY = Path(__file__).resolve().parents[1]
VALIDATOR = REPOSITORY / "scripts" / "validate_provingkit.py"
SOURCE_WORKFLOW = REPOSITORY / ".github/workflows/provingkit-source.yml"
LEGACY_REPOSITORY_ID = "nisavid" + "/agents"


class ProvingkitRepositoryContractTests(unittest.TestCase):
    def validate(self, repository: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), str(repository)],
            text=True,
            capture_output=True,
            check=False,
        )

    def clone_with_history(self, destination: Path) -> None:
        subprocess.run(
            [
                "git",
                "clone",
                "--quiet",
                "--shared",
                "--no-hardlinks",
                str(REPOSITORY),
                str(destination),
            ],
            text=True,
            capture_output=True,
            check=True,
        )
        for retained_name in (
            "issue-81-history-import",
            "agents-pr-69",
            "pr-11-reviewed-carrier",
        ):
            retained_ref = f"refs/remotes/origin/retained/{retained_name}"
            retained_tip = subprocess.run(
                ["git", "-C", str(REPOSITORY), "rev-parse", retained_ref],
                text=True,
                capture_output=True,
                check=True,
            ).stdout.strip()
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(destination),
                    "update-ref",
                    retained_ref,
                    retained_tip,
                ],
                text=True,
                capture_output=True,
                check=True,
            )
        self.overlay_current_final_main_contract(destination)

    @staticmethod
    def overlay_current_final_main_contract(destination: Path) -> None:
        for relative in (
            ".claude-plugin/marketplace.json",
            "release/provingkit/cutover-provenance-v1.json",
            "release/provingkit/definition-v1.json",
            "release/provingkit/final-main-import-map-v1.tsv",
            "release/provingkit/historical-identity-allowlist-v1.json",
            "release/provingkit/release-manifest-v1.schema.json",
        ):
            shutil.copy2(REPOSITORY / relative, destination / relative)
        shutil.copytree(
            REPOSITORY / "plugins/tidesmith",
            destination / "plugins/tidesmith",
            dirs_exist_ok=True,
        )

    def assert_identity_fixture(
        self,
        content: str,
        *,
        accepted: bool,
        extension: str = "txt",
    ) -> None:
        relative = f"release/provingkit/unexpected-identity.{extension}"
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            self.clone_with_history(repository)
            (repository / relative).write_text(content, encoding="utf-8")

            result = self.validate(repository)

        if accepted:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unallowlisted legacy repository identity", result.stderr)
            self.assertIn(relative, result.stderr)

    def synthetic_release_manifest(self) -> dict[str, object]:
        digest = "sha256:" + ("0" * 64)
        members = []
        for member_id, distribution_kind, content_kind, content_path in (
            (
                "rolecasting",
                "agent-plugin",
                "plugin-content-lock",
                "plugins/rolecasting/content-lock.json",
            ),
            (
                "tricritical",
                "agent-plugin",
                "plugin-content-lock",
                "plugins/tricritical/content-lock.json",
            ),
            (
                "versionkeeping",
                "agent-plugin",
                "plugin-content-lock",
                "release/plugin-content-locks/versionkeeping.json",
            ),
            (
                "mergecraft",
                "agent-plugin",
                "plugin-content-lock",
                "release/plugin-content-locks/mergecraft.json",
            ),
            (
                "artifact-customs",
                "agent-plugin",
                "plugin-content-lock",
                "release/plugin-content-locks/artifact-customs.json",
            ),
            (
                "task-witness",
                "code-only",
                "source-shape-review",
                "release/task-witness/source-shape-review.json",
            ),
            (
                "tidesmith",
                "agent-plugin",
                "plugin-content-lock",
                "plugins/tidesmith/content-lock.json",
            ),
        ):
            members.append(
                {
                    "id": member_id,
                    "distribution_kind": distribution_kind,
                    "version": "1.0.0",
                    "identity_manifests": {
                        "canonical": {
                            "path": f"plugins/{member_id}/plugin.json",
                            "sha256": digest,
                        },
                        "claude": {
                            "path": (f"plugins/{member_id}/.claude-plugin/plugin.json"),
                            "sha256": digest,
                        },
                    },
                    "content_identity": {
                        "kind": content_kind,
                        "path": content_path,
                        "sha256": digest,
                    },
                }
            )
        return {
            "contract": "provingkit-release-manifest-v1",
            "schema_version": 1,
            "immutable": True,
            "definition": {
                "path": "release/provingkit/definition-v1.json",
                "sha256": digest,
            },
            "source": {
                "repository": "https://github.com/nisavid/provingkit",
                "commit_sha1": "0" * 40,
            },
            "members": members,
            "content_identity": {
                "algorithm": "sha256",
                "scope": "canonical-json-without-content-identity",
                "sha256": digest,
            },
        }

    def test_identity_fixture_clone_preserves_required_retained_refs(self) -> None:
        expected = {
            "refs/remotes/origin/retained/issue-81-history-import": (
                "caf9a58769af746fd5b514beff5cb305788f7e1c"
            ),
            "refs/remotes/origin/retained/agents-pr-69": (
                "8edaf590736621352262457752d087bad835555d"
            ),
            "refs/remotes/origin/retained/pr-11-reviewed-carrier": (
                "c566c53db920a6b7048550a4b8f7ee4d3c914003"
            ),
        }
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            self.clone_with_history(repository)
            observed = {
                ref: subprocess.run(
                    ["git", "-C", str(repository), "rev-parse", ref],
                    text=True,
                    capture_output=True,
                    check=True,
                ).stdout.strip()
                for ref in expected
            }

        self.assertEqual(observed, expected)

    @staticmethod
    def refresh_allowlisted_hash(repository: Path, relative: str) -> None:
        allowlist_path = (
            repository / "release/provingkit/historical-identity-allowlist-v1.json"
        )
        allowlist = json.loads(allowlist_path.read_text(encoding="utf-8"))
        for entry in allowlist["entries"]:
            if entry["path"] == relative:
                entry["sha256"] = (
                    "sha256:"
                    + hashlib.sha256((repository / relative).read_bytes()).hexdigest()
                )
                break
        else:
            raise AssertionError(f"missing historical allowlist entry: {relative}")
        allowlist_path.write_text(
            json.dumps(allowlist, indent=2) + "\n", encoding="utf-8"
        )

    def test_source_stage_validator_accepts_the_cutover_candidate(self) -> None:
        result = self.validate(REPOSITORY)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "Provingkit source validation passed\n")

    def test_provingkit_source_job_pins_identity_validation_dependency(self) -> None:
        workflow = yaml.safe_load(SOURCE_WORKFLOW.read_text(encoding="utf-8"))
        commands = {
            step.get("run", "")
            for step in workflow["jobs"]["provingkit-source"]["steps"]
        }
        expected = (
            "python -m pip install --disable-pip-version-check "
            "idna==3.18 jsonschema==4.26.0 PyYAML==6.0.3"
        )

        self.assertIn(expected, commands)
        self.assertIn(
            "python -m pip install idna==3.18 jsonschema==4.26.0 "
            "PyYAML==6.0.3",
            (REPOSITORY / "README.md").read_text(encoding="utf-8"),
        )

    def test_provingkit_source_job_checks_the_trigger_base_to_head_range(self) -> None:
        workflow = yaml.safe_load(SOURCE_WORKFLOW.read_text(encoding="utf-8"))
        steps = workflow["jobs"]["provingkit-source"]["steps"]
        check = next(
            step for step in steps if step.get("name") == "Check base-to-head diff"
        )

        self.assertEqual(
            check["env"],
            {
                "BASE_SHA": (
                    "${{ github.event.pull_request.base.sha || "
                    "github.event.before }}"
                ),
                "HEAD_SHA": (
                    "${{ github.event.pull_request.head.sha || github.sha }}"
                ),
            },
        )
        self.assertEqual(check["run"], 'git diff --check "$BASE_SHA" "$HEAD_SHA"')
        derived_commands = {
            step.get("run", "")
            for step in workflow["jobs"]["derived-locks"]["steps"]
        }
        self.assertIn("git diff --exit-code", derived_commands)

    def test_rolecasting_source_job_installs_its_validation_dependency(self) -> None:
        workflow = yaml.safe_load(SOURCE_WORKFLOW.read_text(encoding="utf-8"))
        commands = {
            step.get("run", "")
            for step in workflow["jobs"]["rolecasting"]["steps"]
        }

        self.assertIn(
            "python -m pip install --disable-pip-version-check PyYAML==6.0.3",
            commands,
        )

    def test_required_jobs_run_current_tricritical_and_projection_contracts(
        self,
    ) -> None:
        workflow = yaml.safe_load(SOURCE_WORKFLOW.read_text(encoding="utf-8"))
        tricritical_commands = {
            line.strip()
            for step in workflow["jobs"]["tricritical"]["steps"]
            for line in step.get("run", "").splitlines()
            if line.strip()
        }
        provingkit_commands = {
            line.strip()
            for step in workflow["jobs"]["provingkit-source"]["steps"]
            for line in step.get("run", "").splitlines()
            if line.strip()
        }
        expected_tricritical = (
            "python -m unittest tests.test_validate_tricritical "
            "tests.test_tricritical_eval_corpus "
            "tests.plugins.test_tricritical_review_evidence"
        )
        expected_projection = (
            "python -m unittest "
            "tests.test_phase7_compatibility_projection."
            "Phase7CompatibilityProjectionTests."
            "test_projection_is_byte_identical_to_frozen_v5_fixture"
        )

        self.assertIn(expected_tricritical, tricritical_commands)
        self.assertIn(expected_projection, provingkit_commands)
        self.assertIn(
            expected_tricritical,
            (REPOSITORY / "README.md").read_text(encoding="utf-8"),
        )

    def test_task_witness_source_job_runs_the_qualification_selector_guard(self) -> None:
        workflow = yaml.safe_load(SOURCE_WORKFLOW.read_text(encoding="utf-8"))
        commands = {
            line.strip()
            for step in workflow["jobs"]["task-witness"]["steps"]
            for line in step.get("run", "").splitlines()
            if line.strip()
        }

        self.assertIn(
            "python -m unittest tests.test_task_witness_qualification.TaskWitnessQualificationTests.test_deployment_common_selector_table_is_closed_and_exact",
            commands,
        )

    def test_tidesmith_source_job_and_derived_lock_are_covered(self) -> None:
        workflow = yaml.safe_load(SOURCE_WORKFLOW.read_text(encoding="utf-8"))
        source_commands = {
            line.strip()
            for step in workflow["jobs"]["tidesmith"]["steps"]
            for line in step.get("run", "").splitlines()
            if line.strip()
        }
        lock_commands = {
            line.strip()
            for step in workflow["jobs"]["derived-locks"]["steps"]
            for line in step.get("run", "").splitlines()
            if line.strip()
        }

        self.assertIn("python -m unittest tests.test_validate_tidesmith", source_commands)
        self.assertIn("python scripts/validate_tidesmith.py .", source_commands)
        self.assertIn(
            "python scripts/validate_tidesmith.py --write-content-lock .",
            lock_commands,
        )

    def test_human_docs_state_the_current_seven_member_source_set(self) -> None:
        for relative in (
            "README.md",
            "CONTRIBUTING.md",
            ".github/pull_request_template.md",
        ):
            with self.subTest(relative=relative):
                content = (REPOSITORY / relative).read_text(encoding="utf-8")
                normalized = " ".join(content.split())
                self.assertIn("seven source members", normalized)
                self.assertIn("six Agent Plugins", normalized)
                self.assertIn("Tidesmith", normalized)
                self.assertIn("Task Witness", normalized)
                self.assertNotIn("six source members carried by this cutover", normalized)
                self.assertNotIn("issue #25 after pull request #11", normalized)

    def test_agent_guidance_describes_member_specific_content_identity_writers(
        self,
    ) -> None:
        guidance = " ".join((REPOSITORY / "AGENTS.md").read_text().split())

        self.assertIn("Use `--write-content-lock` only where", guidance)
        self.assertIn(
            "Rolecasting, Versionkeeping, Mergecraft, and Artifact Customs write "
            "only their content locks",
            guidance,
        )
        self.assertIn(
            "Tricritical also regenerates its per-skill reference projections",
            guidance,
        )
        self.assertIn("Task Witness", guidance)
        self.assertIn("has no mechanical writer", guidance)
        self.assertNotIn(
            "validator owns the plugin's projections and content lock",
            guidance,
        )

    def test_versioned_definition_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            shutil.copytree(
                REPOSITORY,
                repository,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            definition = repository / "release/provingkit/definition-v1.json"
            if definition.exists():
                definition.unlink()

            result = self.validate(repository)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("versioned Provingkit definition is missing", result.stderr)

    def test_definition_requires_the_exact_seven_member_set(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            shutil.copytree(
                REPOSITORY,
                repository,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            definition_path = repository / "release/provingkit/definition-v1.json"
            definition = json.loads(definition_path.read_text(encoding="utf-8"))
            definition["membership"]["members"].pop()
            definition_path.write_text(
                json.dumps(definition, indent=2) + "\n", encoding="utf-8"
            )

            result = self.validate(repository)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("definition membership drift", result.stderr)

    def test_definition_withholds_release_authority_and_instances(self) -> None:
        for field, value in (
            ("release_authority", "granted"),
            ("instances", ["release/provingkit/not-authorized.json"]),
        ):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                repository = Path(directory) / "repository"
                shutil.copytree(
                    REPOSITORY,
                    repository,
                    ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
                )
                definition_path = repository / "release/provingkit/definition-v1.json"
                definition = json.loads(definition_path.read_text(encoding="utf-8"))
                definition["release_manifest"][field] = value
                definition_path.write_text(
                    json.dumps(definition, indent=2) + "\n", encoding="utf-8"
                )

                result = self.validate(repository)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("definition release boundary drift", result.stderr)

    def test_definition_json_rejects_duplicate_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            shutil.copytree(
                REPOSITORY,
                repository,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            definition_path = repository / "release/provingkit/definition-v1.json"
            definition = definition_path.read_text(encoding="utf-8")
            definition_path.write_text(
                definition.replace(
                    '  "schema_version": 1,',
                    '  "schema_version": 1,\n  "schema_version": 1,',
                    1,
                ),
                encoding="utf-8",
            )

            result = self.validate(repository)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("versioned Provingkit definition is unreadable", result.stderr)

    def test_definition_rejects_boolean_schema_versions_and_extra_claims(self) -> None:
        for field, value in (("schema_version", True), ("published", True)):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                repository = Path(directory) / "repository"
                shutil.copytree(
                    REPOSITORY,
                    repository,
                    ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
                )
                definition_path = repository / "release/provingkit/definition-v1.json"
                definition = json.loads(definition_path.read_text(encoding="utf-8"))
                definition[field] = value
                definition_path.write_text(
                    json.dumps(definition, indent=2) + "\n", encoding="utf-8"
                )

                result = self.validate(repository)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("definition membership drift", result.stderr)

    def test_definition_binds_each_member_identity_and_excluded_source(self) -> None:
        definition = json.loads(
            (REPOSITORY / "release/provingkit/definition-v1.json").read_text(
                encoding="utf-8"
            )
        )

        observed = [
            (
                member["id"],
                member["distribution_kind"],
                member["version"],
                member["identity_manifests"]["canonical"],
                member["identity_manifests"]["claude"],
                member["content_identity"]["kind"],
                member["content_identity"]["path"],
            )
            for member in definition["membership"]["members"]
        ]
        self.assertEqual(
            observed,
            [
                (
                    "rolecasting",
                    "agent-plugin",
                    "1.0.0",
                    "plugins/rolecasting/plugin.json",
                    "plugins/rolecasting/.claude-plugin/plugin.json",
                    "plugin-content-lock",
                    "plugins/rolecasting/content-lock.json",
                ),
                (
                    "tricritical",
                    "agent-plugin",
                    "1.0.0",
                    "plugins/tricritical/plugin.json",
                    "plugins/tricritical/.claude-plugin/plugin.json",
                    "plugin-content-lock",
                    "plugins/tricritical/content-lock.json",
                ),
                (
                    "versionkeeping",
                    "agent-plugin",
                    "1.0.0",
                    "plugins/versionkeeping/plugin.json",
                    "plugins/versionkeeping/.claude-plugin/plugin.json",
                    "plugin-content-lock",
                    "release/plugin-content-locks/versionkeeping.json",
                ),
                (
                    "mergecraft",
                    "agent-plugin",
                    "1.0.0",
                    "plugins/mergecraft/plugin.json",
                    "plugins/mergecraft/.claude-plugin/plugin.json",
                    "plugin-content-lock",
                    "release/plugin-content-locks/mergecraft.json",
                ),
                (
                    "artifact-customs",
                    "agent-plugin",
                    "1.0.0",
                    "plugins/artifact-customs/plugin.json",
                    "plugins/artifact-customs/.claude-plugin/plugin.json",
                    "plugin-content-lock",
                    "release/plugin-content-locks/artifact-customs.json",
                ),
                (
                    "task-witness",
                    "code-only",
                    "1.0.0",
                    "plugins/task-witness/plugin.json",
                    "plugins/task-witness/.claude-plugin/plugin.json",
                    "source-shape-review",
                    "release/task-witness/source-shape-review.json",
                ),
                (
                    "tidesmith",
                    "agent-plugin",
                    "1.0.0",
                    "plugins/tidesmith/plugin.json",
                    "plugins/tidesmith/.claude-plugin/plugin.json",
                    "plugin-content-lock",
                    "plugins/tidesmith/content-lock.json",
                ),
            ],
        )
        self.assertEqual(
            definition["excluded_source"],
            {
                "paths": [".scratch", "tooling"],
                "products": [
                    "Base Loadout",
                    "Hindsight",
                    "personal tools",
                    "unrelated experiments",
                ],
            },
        )
        self.assertEqual(
            definition["cutover_provenance"],
            "release/provingkit/cutover-provenance-v1.json",
        )
        self.assertEqual(
            definition["historical_identity_allowlist"],
            "release/provingkit/historical-identity-allowlist-v1.json",
        )

    def test_each_member_keeps_its_own_manifest_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            shutil.copytree(
                REPOSITORY,
                repository,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            manifest_path = repository / "plugins/rolecasting/plugin.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["name"] = "provingkit"
            manifest_path.write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )

            result = self.validate(repository)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("member identity drift", result.stderr)

    def test_claude_manifest_must_match_the_independent_member_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            shutil.copytree(
                REPOSITORY,
                repository,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            manifest_path = (
                repository / "plugins/versionkeeping/.claude-plugin/plugin.json"
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["version"] = "9.0.0"
            manifest_path.write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )

            result = self.validate(repository)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("member identity drift", result.stderr)

    def test_cutover_member_version_rejects_a_coordinated_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            shutil.copytree(
                REPOSITORY,
                repository,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            definition_path = repository / "release/provingkit/definition-v1.json"
            definition = json.loads(definition_path.read_text(encoding="utf-8"))
            definition["membership"]["members"][0]["version"] = "9.9.9"
            definition_path.write_text(
                json.dumps(definition, indent=2) + "\n", encoding="utf-8"
            )
            for relative in (
                "plugins/rolecasting/plugin.json",
                "plugins/rolecasting/.claude-plugin/plugin.json",
            ):
                manifest_path = repository / relative
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["version"] = "9.9.9"
                manifest_path.write_text(
                    json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
                )
            schema_path = (
                repository / "release/provingkit/release-manifest-v1.schema.json"
            )
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            schema["$defs"]["rolecasting"]["properties"]["version"]["const"] = (
                "9.9.9"
            )
            schema_path.write_text(
                json.dumps(schema, indent=2) + "\n", encoding="utf-8"
            )

            result = self.validate(repository)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cutover member version drift", result.stderr)

    def test_member_content_identity_binds_the_exact_review_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            shutil.copytree(
                REPOSITORY,
                repository,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            content_identity_path = repository / "plugins/rolecasting/content-lock.json"
            content_identity_path.write_text(
                content_identity_path.read_text(encoding="utf-8") + "\n",
                encoding="utf-8",
            )

            result = self.validate(repository)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("member content identity drift", result.stderr)

    def test_cutover_provenance_binds_source_history_and_unreleased_scope(
        self,
    ) -> None:
        provenance = json.loads(
            (REPOSITORY / "release/provingkit/cutover-provenance-v1.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(provenance["contract"], "provingkit-cutover-provenance-v1")
        self.assertEqual(
            provenance["source_repository"]["cutover_baseline"],
            {
                "original_commit": "44ee979cdae1d47f2ef3fdc713eaa6f04adf9892",
                "filtered_commit": "7dd8273ecab621be662d27c38706e33f2b48ae34",
            },
        )
        self.assertEqual(
            provenance["source_repository"]["retained_extraction_input"],
            {
                "kind": "pull-request",
                "number": 69,
                "url": "https://github.com/nisavid" + "/agents/pull/69",
                "state": "open-unmerged",
                "production_disposition": "retained-input-not-accepted-behavior",
                "original_head": "02e3c721bdbd922883948bb3af84c5bafd702984",
                "filtered_head": "8edaf590736621352262457752d087bad835555d",
                "destination_ref": "refs/heads/retained/agents-pr-69",
            },
        )
        adopted = provenance["adopted_qualification_history"]
        self.assertEqual(
            [
                (item["platform"], item["source_range"]["commit_count"])
                for item in adopted
            ],
            [("linux", 21), ("macos", 36)],
        )
        self.assertTrue(
            all(
                item["evidence_disposition"]
                == "historical-stale-not-current-qualification"
                for item in adopted
            )
        )
        self.assertEqual(
            provenance["release_resources"],
            {"authority": "not-granted", "created": []},
        )
        self.assertEqual(
            [
                (
                    entry["source_issue"],
                    entry["destination_issue"],
                    entry["state"],
                )
                for entry in provenance["issue_migration"]["entries"]
            ],
            [
                (43, 1, "transferred"),
                (44, 2, "transferred"),
                (45, 3, "transferred"),
                (52, 4, "transferred"),
                (53, 5, "transferred"),
                (56, 6, "transferred"),
                (59, 7, "transferred"),
                (65, 8, "transferred"),
                (79, 9, "transferred"),
                (80, 10, "transferred"),
            ],
        )
        self.assertEqual(provenance["issue_migration"]["state"], "transferred")

    def test_adopted_history_import_map_binds_the_reviewed_replay(self) -> None:
        provenance = json.loads(
            (REPOSITORY / "release/provingkit/cutover-provenance-v1.json").read_text(
                encoding="utf-8"
            )
        )
        import_history = provenance["adopted_history_import"]

        self.assertEqual(
            import_history["retained_ref"],
            {
                "ref": "refs/heads/retained/issue-81-history-import",
                "disposition": "immutable-non-release-history-evidence",
            },
        )
        self.assertEqual(
            import_history["delta_bundle"],
            {
                "contract": "provingkit-adopted-history-delta-bundle-v1",
                "path": "release/provingkit/adopted-history-delta-bundle-v1.json",
                "row_count": 57,
                "sha256": (
                    "sha256:"
                    "c9f5e9a2f9cfee80e943eeb859d4f5b072f98150e7018e474710f709c6e1b9ae"
                ),
                "content_sha256": (
                    "sha256:"
                    "d14da319649492e7ecb64d20a578983cb2cd88e00a5e4d3a1ed7e49a1a526cc5"
                ),
                "source_roots": [
                    {
                        "disposition": (
                            "protected-non-release-source-history-evidence"
                        ),
                        "platform": "linux",
                        "ref": (
                            "refs/heads/ivan/"
                            "task-witness-linux-qualification-harness"
                        ),
                        "repository": "nisavid" + "/agents",
                        "ruleset_id": 22049569,
                        "tip": "a8410babc9e1b0c2a57b9f69db98a495133f6843",
                    },
                    {
                        "disposition": (
                            "protected-non-release-source-history-evidence"
                        ),
                        "platform": "macos",
                        "ref": (
                            "refs/heads/ivan/"
                            "task-witness-macos-qualification-harness"
                        ),
                        "repository": "nisavid" + "/agents",
                        "ruleset_id": 22049569,
                        "tip": "0703e8df26c975a187cb6f36b8dfb21df8bcc6db",
                    },
                ],
            },
        )
        self.assertEqual(
            import_history["final_main_mapping"],
            {
                "completion_gate": "required-before-closing-source-issue-81",
                "contract": "provingkit-final-main-import-map-v1",
                "final_main": {
                    "base_commit": "64060b3d81da21c47487eb6e4da732dbbb4cbd3a",
                    "tip_commit": "7d2cbbb8de045fd1ba381b982674131c6ead6919",
                    "tree": "3e5ec43b24517d01ca32319279f6e7365a0fd351",
                },
                "merge_method": "rebase",
                "path": "release/provingkit/final-main-import-map-v1.tsv",
                "reviewed_carrier": {
                    "commit": "14352d60d765d634c2da0fa9cca54e465f6571f6",
                    "commit_count": 84,
                    "comparison": "ordered-tree-and-message-sequence-equality",
                    "evidence_envelope": {
                        "commit": "c566c53db920a6b7048550a4b8f7ee4d3c914003",
                        "disposition": "protected-non-release-history-evidence",
                        "parents": [
                            "7d2cbbb8de045fd1ba381b982674131c6ead6919",
                            "14352d60d765d634c2da0fa9cca54e465f6571f6",
                        ],
                        "ref": "refs/heads/retained/pr-11-reviewed-carrier",
                        "tree": "3e5ec43b24517d01ca32319279f6e7365a0fd351",
                    },
                    "tree": "3e5ec43b24517d01ca32319279f6e7365a0fd351",
                },
                "row_count": 57,
                "sha256": (
                    "sha256:"
                    "408de1b00688d05e7f2da00411c490d09c37dbacacd0719f6aef5fa2c62a9f5d"
                ),
                "source_pull_request": (
                    "https://github.com/nisavid/provingkit/pull/11"
                ),
                "state": "verified",
            },
        )
        rows = (
            REPOSITORY
            / "release/provingkit/adopted-history-import-map-v1.tsv"
        ).read_text(encoding="ascii").splitlines()
        self.assertEqual(len(rows), 58)
        self.assertEqual(
            rows[0].split("\t"),
            [
                "platform",
                "ordinal",
                "original_commit",
                "filtered_commit",
                "retained_import_commit",
                "full_tree_delta_sha256",
                "projected_tree_delta_sha256",
            ],
        )
        self.assertEqual(
            [(row.split("\t")[0], int(row.split("\t")[1])) for row in rows[1:]],
            [("linux", ordinal) for ordinal in range(1, 22)]
            + [("macos", ordinal) for ordinal in range(1, 37)],
        )

    def test_final_main_import_map_binds_rebase_assigned_commits(self) -> None:
        provenance = json.loads(
            (REPOSITORY / "release/provingkit/cutover-provenance-v1.json").read_text(
                encoding="utf-8"
            )
        )
        mapping = provenance["adopted_history_import"]["final_main_mapping"]

        self.assertEqual(mapping["state"], "verified")
        self.assertEqual(mapping["contract"], "provingkit-final-main-import-map-v1")
        self.assertEqual(
            mapping["path"], "release/provingkit/final-main-import-map-v1.tsv"
        )
        self.assertEqual(mapping["row_count"], 57)
        self.assertEqual(mapping["merge_method"], "rebase")
        self.assertEqual(
            mapping["source_pull_request"],
            "https://github.com/nisavid/provingkit/pull/11",
        )
        self.assertEqual(
            mapping["reviewed_carrier"],
            {
                "commit": "14352d60d765d634c2da0fa9cca54e465f6571f6",
                "commit_count": 84,
                "comparison": "ordered-tree-and-message-sequence-equality",
                "evidence_envelope": {
                    "commit": "c566c53db920a6b7048550a4b8f7ee4d3c914003",
                    "disposition": "protected-non-release-history-evidence",
                    "parents": [
                        "7d2cbbb8de045fd1ba381b982674131c6ead6919",
                        "14352d60d765d634c2da0fa9cca54e465f6571f6",
                    ],
                    "ref": "refs/heads/retained/pr-11-reviewed-carrier",
                    "tree": "3e5ec43b24517d01ca32319279f6e7365a0fd351",
                },
                "tree": "3e5ec43b24517d01ca32319279f6e7365a0fd351",
            },
        )
        self.assertEqual(
            mapping["final_main"],
            {
                "base_commit": "64060b3d81da21c47487eb6e4da732dbbb4cbd3a",
                "tip_commit": "7d2cbbb8de045fd1ba381b982674131c6ead6919",
                "tree": "3e5ec43b24517d01ca32319279f6e7365a0fd351",
            },
        )

        rows = (
            REPOSITORY / "release/provingkit/final-main-import-map-v1.tsv"
        ).read_text(encoding="ascii").splitlines()
        self.assertEqual(len(rows), 58)
        self.assertEqual(
            rows[0].split("\t"),
            [
                "platform",
                "ordinal",
                "retained_import_commit",
                "final_main_commit",
                "full_tree_delta_sha256",
            ],
        )
        self.assertEqual(
            rows[1].split("\t")[:4],
            [
                "linux",
                "1",
                "56af80454bd356097f264bd81f0920234ae17bfc",
                "d79d1699134cfdf3e19895b40fe75da427961b56",
            ],
        )
        self.assertEqual(
            rows[-1].split("\t")[:4],
            [
                "macos",
                "36",
                "604c6e8702c4e3914e862bee58ab35f529866737",
                "d47e9fbe95c5be6f923c91d0751ccdb1af80280b",
            ],
        )

    def test_validator_rejects_an_identical_tree_outside_final_main(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            self.clone_with_history(repository)
            synthetic_carrier = subprocess.run(
                [
                    "git",
                    "-C",
                    str(repository),
                    "-c",
                    "user.name=Provingkit Test",
                    "-c",
                    "user.email=provingkit-test@example.invalid",
                    "commit-tree",
                    "3e5ec43b24517d01ca32319279f6e7365a0fd351",
                    "-p",
                    "64060b3d81da21c47487eb6e4da732dbbb4cbd3a",
                    "-m",
                    "Synthetic reviewed carrier",
                ],
                text=True,
                capture_output=True,
                check=True,
            ).stdout.strip()
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repository),
                    "checkout",
                    "--quiet",
                    "--detach",
                    "--force",
                    synthetic_carrier,
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            self.overlay_current_final_main_contract(repository)

            result = self.validate(repository)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("final main import reachability drift", result.stderr)

    def test_validator_rejects_reordered_reachable_final_main_rows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            self.clone_with_history(repository)

            map_path = (
                repository / "release/provingkit/final-main-import-map-v1.tsv"
            )
            lines = map_path.read_text(encoding="ascii").splitlines()
            rows = [line.split("\t") for line in lines[1:]]
            rows[28][3], rows[29][3] = rows[29][3], rows[28][3]
            map_path.write_text(
                "\n".join([lines[0], *("\t".join(row) for row in rows)]) + "\n",
                encoding="ascii",
            )
            map_sha256 = "sha256:" + hashlib.sha256(map_path.read_bytes()).hexdigest()

            provenance_path = (
                repository / "release/provingkit/cutover-provenance-v1.json"
            )
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
            provenance["adopted_history_import"]["final_main_mapping"][
                "sha256"
            ] = map_sha256
            provenance_path.write_text(
                json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
            )
            provenance_sha256 = (
                "sha256:" + hashlib.sha256(provenance_path.read_bytes()).hexdigest()
            )

            allowlist_path = (
                repository
                / "release/provingkit/historical-identity-allowlist-v1.json"
            )
            allowlist = json.loads(allowlist_path.read_text(encoding="utf-8"))
            provenance_entry = next(
                entry
                for entry in allowlist["entries"]
                if entry["path"]
                == "release/provingkit/cutover-provenance-v1.json"
            )
            provenance_entry["sha256"] = provenance_sha256
            allowlist_path.write_text(
                json.dumps(allowlist, indent=2) + "\n", encoding="utf-8"
            )

            validator_path = Path(directory) / "validate_provingkit.py"
            validator_source = VALIDATOR.read_text(encoding="utf-8")
            current_map_sha256 = (
                "sha256:"
                "408de1b00688d05e7f2da00411c490d09c37dbacacd0719f6aef5fa2c62a9f5d"
            )
            self.assertEqual(validator_source.count(current_map_sha256), 1)
            validator_path.write_text(
                validator_source.replace(current_map_sha256, map_sha256),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(validator_path), str(repository)],
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("final main import reachability drift", result.stderr)

    def test_validator_rejects_rewritten_reviewed_carrier(self) -> None:
        candidates = (
            ("nonexistent", "0" * 40, "reviewed carrier object drift"),
            (
                "wrong-tree",
                "64060b3d81da21c47487eb6e4da732dbbb4cbd3a",
                "reviewed carrier tree drift",
            ),
            ("same-trees-one-message-drift", None, "reviewed carrier history drift"),
        )
        reviewed_carrier = "14352d60d765d634c2da0fa9cca54e465f6571f6"
        reviewed_carrier_envelope = "c566c53db920a6b7048550a4b8f7ee4d3c914003"
        final_main_base = "64060b3d81da21c47487eb6e4da732dbbb4cbd3a"
        final_main_tip = "7d2cbbb8de045fd1ba381b982674131c6ead6919"
        final_main_tree = "3e5ec43b24517d01ca32319279f6e7365a0fd351"
        envelope_message = (
            "chore(provingkit/cutover): retain reviewed carrier evidence\n\n"
            "Join final main to the exact PR #11 reviewed carrier on a frozen "
            "non-release evidence ref. This commit remains outside main and grants "
            "no release authority."
        )
        for label, candidate, expected_error in candidates:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                repository = Path(directory) / "repository"
                self.clone_with_history(repository)
                candidate_commit = candidate
                if candidate_commit is None:
                    carrier_commits = subprocess.run(
                        [
                            "git",
                            "-C",
                            str(repository),
                            "rev-list",
                            "--reverse",
                            f"{final_main_base}..{reviewed_carrier}",
                        ],
                        text=True,
                        capture_output=True,
                        check=True,
                    ).stdout.splitlines()
                    self.assertEqual(len(carrier_commits), 84)
                    previous = final_main_base
                    for ordinal, original in enumerate(carrier_commits, start=1):
                        tree = subprocess.run(
                            [
                                "git",
                                "-C",
                                str(repository),
                                "show",
                                "-s",
                                "--format=%T",
                                original,
                            ],
                            text=True,
                            capture_output=True,
                            check=True,
                        ).stdout.strip()
                        message = subprocess.run(
                            [
                                "git",
                                "-C",
                                str(repository),
                                "show",
                                "-s",
                                "--format=%B",
                                original,
                            ],
                            text=True,
                            capture_output=True,
                            check=True,
                        ).stdout
                        if ordinal == 42:
                            message = message.rstrip() + "\n\nSynthetic message drift\n"
                        candidate_commit = subprocess.run(
                            [
                                "git",
                                "-C",
                                str(repository),
                                "-c",
                                "user.name=Provingkit Test",
                                "-c",
                                "user.email=provingkit-test@example.invalid",
                                "commit-tree",
                                tree,
                                "-p",
                                previous,
                                "-F",
                                "-",
                            ],
                            input=message,
                            text=True,
                            capture_output=True,
                            check=True,
                        ).stdout.strip()
                        previous = candidate_commit

                forged_envelope_content = (
                    f"tree {final_main_tree}\n"
                    f"parent {final_main_tip}\n"
                    f"parent {candidate_commit}\n"
                    "author Ivan D Vasin <ivan@nisavid.io> 1788476307 +0000\n"
                    "committer Ivan D Vasin <ivan@nisavid.io> 1788476307 +0000\n"
                    "\n"
                    f"{envelope_message}\n"
                )
                forged_envelope = subprocess.run(
                    [
                        "git",
                        "-C",
                        str(repository),
                        "hash-object",
                        "-t",
                        "commit",
                        "-w",
                        "--stdin",
                    ],
                    input=forged_envelope_content,
                    text=True,
                    capture_output=True,
                    check=True,
                ).stdout.strip()
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(repository),
                        "update-ref",
                        "refs/remotes/origin/retained/pr-11-reviewed-carrier",
                        forged_envelope,
                        reviewed_carrier_envelope,
                    ],
                    text=True,
                    capture_output=True,
                    check=True,
                )

                provenance_path = (
                    repository / "release/provingkit/cutover-provenance-v1.json"
                )
                provenance = json.loads(
                    provenance_path.read_text(encoding="utf-8")
                )
                carrier_metadata = provenance["adopted_history_import"][
                    "final_main_mapping"
                ]["reviewed_carrier"]
                carrier_metadata["commit"] = candidate_commit
                carrier_metadata["evidence_envelope"]["commit"] = forged_envelope
                carrier_metadata["evidence_envelope"]["parents"][1] = candidate_commit
                provenance_path.write_text(
                    json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
                )
                provenance_sha256 = (
                    "sha256:"
                    + hashlib.sha256(provenance_path.read_bytes()).hexdigest()
                )

                allowlist_path = (
                    repository
                    / "release/provingkit/historical-identity-allowlist-v1.json"
                )
                allowlist = json.loads(
                    allowlist_path.read_text(encoding="utf-8")
                )
                provenance_entry = next(
                    entry
                    for entry in allowlist["entries"]
                    if entry["path"]
                    == "release/provingkit/cutover-provenance-v1.json"
                )
                provenance_entry["sha256"] = provenance_sha256
                allowlist_path.write_text(
                    json.dumps(allowlist, indent=2) + "\n", encoding="utf-8"
                )

                validator_path = Path(directory) / "validate_provingkit.py"
                validator_source = VALIDATOR.read_text(encoding="utf-8")
                self.assertEqual(validator_source.count(reviewed_carrier), 1)
                self.assertEqual(validator_source.count(reviewed_carrier_envelope), 1)
                validator_path.write_text(
                    validator_source.replace(
                        reviewed_carrier, candidate_commit
                    ).replace(
                        reviewed_carrier_envelope, forged_envelope
                    ),
                    encoding="utf-8",
                )
                result = subprocess.run(
                    [sys.executable, str(validator_path), str(repository)],
                    text=True,
                    capture_output=True,
                    check=False,
                )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(expected_error, result.stderr)

    def test_validator_requires_the_reviewed_carrier_retained_ref(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            self.clone_with_history(repository)
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repository),
                    "update-ref",
                    "-d",
                    "refs/remotes/origin/retained/pr-11-reviewed-carrier",
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            result = self.validate(repository)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reviewed carrier ref attestation drift", result.stderr)

    def test_adopted_history_bundle_base64_must_be_canonical(self) -> None:
        self.assertEqual(validate_provingkit._decode_canonical_base64("YQ=="), b"a")
        for encoded in ("YQ", "YR==", "YQ==\n"):
            with self.subTest(encoded=encoded), self.assertRaises(
                validate_provingkit.ValidationError
            ):
                validate_provingkit._decode_canonical_base64(encoded)

    def test_historical_identity_allowlist_binds_the_delta_bundle(self) -> None:
        allowlist = json.loads(
            (
                REPOSITORY
                / "release/provingkit/historical-identity-allowlist-v1.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(len(allowlist["entries"]), 39)
        self.assertIn(
            {
                "disposition": (
                    "protected-non-release-source-history-delta-evidence"
                ),
                "path": (
                    "release/provingkit/adopted-history-delta-bundle-v1.json"
                ),
                "sha256": (
                    "sha256:"
                    "c9f5e9a2f9cfee80e943eeb859d4f5b072f98150e7018e474710f709c6e1b9ae"
                ),
            },
            allowlist["entries"],
        )

    def test_validator_rejects_adopted_history_bundle_file_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            shutil.copytree(
                REPOSITORY,
                repository,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            bundle_path = (
                repository
                / "release/provingkit/adopted-history-delta-bundle-v1.json"
            )
            bundle_path.write_text(
                bundle_path.read_text(encoding="utf-8") + "\n", encoding="utf-8"
            )

            result = self.validate(repository)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("adopted history delta bundle drift", result.stderr)

    def test_validator_rejects_semantic_import_map_drift_with_a_refreshed_hash(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            shutil.copytree(
                REPOSITORY,
                repository,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            map_path = (
                repository
                / "release/provingkit/adopted-history-import-map-v1.tsv"
            )
            rows = map_path.read_text(encoding="ascii").splitlines()
            fields = rows[1].split("\t")
            fields[1] = "2"
            rows[1] = "\t".join(fields)
            map_path.write_text("\n".join(rows) + "\n", encoding="ascii")
            provenance_path = (
                repository / "release/provingkit/cutover-provenance-v1.json"
            )
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
            provenance["adopted_history_import"]["review_map"]["sha256"] = (
                "sha256:" + hashlib.sha256(map_path.read_bytes()).hexdigest()
            )
            provenance_path.write_text(
                json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
            )

            result = self.validate(repository)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("adopted history import map drift", result.stderr)

    def test_validator_rejects_a_different_cutover_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            shutil.copytree(
                REPOSITORY,
                repository,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            provenance_path = (
                repository / "release/provingkit/cutover-provenance-v1.json"
            )
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
            provenance["source_repository"]["cutover_baseline"]["original_commit"] = (
                "0" * 40
            )
            provenance_path.write_text(
                json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
            )

            result = self.validate(repository)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cutover provenance drift", result.stderr)

    def test_validator_locks_compatibility_alias_scopes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            shutil.copytree(
                REPOSITORY,
                repository,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            relative = "release/provingkit/cutover-provenance-v1.json"
            provenance_path = repository / relative
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
            provenance["compatibility_aliases"][0]["scope"] = "active-source"
            provenance_path.write_text(
                json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
            )
            self.refresh_allowlisted_hash(repository, relative)

            result = self.validate(repository)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cutover provenance drift", result.stderr)

    def test_cutover_provenance_inventories_the_repository_id_alias(self) -> None:
        provenance = json.loads(
            (REPOSITORY / "release/provingkit/cutover-provenance-v1.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertIn(
            {
                "canonical": "nisavid/provingkit",
                "kind": "repository-id",
                "legacy": LEGACY_REPOSITORY_ID,
                "scope": "frozen-receipts",
            },
            provenance["compatibility_aliases"],
        )

    def test_validator_locks_the_historical_source_lineage_owner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            shutil.copytree(
                REPOSITORY,
                repository,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            relative = "release/provingkit/cutover-provenance-v1.json"
            provenance_path = repository / relative
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
            provenance["historical_artifacts"] = []
            provenance_path.write_text(
                json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
            )
            self.refresh_allowlisted_hash(repository, relative)

            result = self.validate(repository)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cutover provenance drift", result.stderr)

    def test_issue_migration_ledger_requires_unique_destination_issues(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            shutil.copytree(
                REPOSITORY,
                repository,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            relative = "release/provingkit/cutover-provenance-v1.json"
            provenance_path = repository / relative
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
            for entry in provenance["issue_migration"]["entries"][:2]:
                entry["destination_issue"] = 1
                entry["state"] = "transferred"
            provenance["issue_migration"]["state"] = "partial-native-transfer"
            provenance_path.write_text(
                json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
            )
            self.refresh_allowlisted_hash(repository, relative)

            result = self.validate(repository)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("issue migration ledger drift", result.stderr)

    def test_excluded_products_and_source_roots_cannot_reenter_the_repository(
        self,
    ) -> None:
        for relative in (
            ".scratch/unrelated-experiment.txt",
            "tooling/personal-tool/README.md",
            "plugins/base-loadout/plugin.json",
            "plugins/hindsight/plugin.json",
        ):
            with (
                self.subTest(relative=relative),
                tempfile.TemporaryDirectory() as directory,
            ):
                repository = Path(directory) / "repository"
                shutil.copytree(
                    REPOSITORY,
                    repository,
                    ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
                )
                excluded = repository / relative
                excluded.parent.mkdir(parents=True, exist_ok=True)
                excluded.write_text("excluded\n", encoding="utf-8")

                result = self.validate(repository)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("excluded source present", result.stderr)

    def test_marketplace_is_the_exact_six_agent_plugin_source_projection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            shutil.copytree(
                REPOSITORY,
                repository,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            marketplace_path = repository / ".claude-plugin/marketplace.json"
            marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
            marketplace["plugins"].append(
                {
                    "name": "task-witness",
                    "source": "./plugins/task-witness",
                    "category": "developer-tools",
                }
            )
            marketplace_path.write_text(
                json.dumps(marketplace, indent=2) + "\n", encoding="utf-8"
            )

            result = self.validate(repository)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("marketplace source projection drift", result.stderr)

    def test_unallowlisted_legacy_repository_identity_is_rejected(self) -> None:
        legacy_repository = "https://github.com/nisavid" + "/agents"
        self.assert_identity_fixture(
            f"Unexpected active link: {legacy_repository}\n",
            accepted=False,
        )

    def test_unallowlisted_legacy_repository_identity_variants_are_rejected(
        self,
    ) -> None:
        variants = {
            "percent-encoded": "https://github.com/nisavid/" + "%61gents",
            "percent-encoded-path-separator": (
                "ht" + "tps://github.com/nisavid" + "%2Fagents"
            ),
            "double-percent-encoded": "https://github.com/nisavid/" + "%2561gents",
            "html-entity": "https://github.com/nisavid/" + "&#97;gents",
            "github-case": "https://GitHub.com/NISAVID" + "/AGENTS",
        }
        for variant_name, legacy_repository in variants.items():
            with self.subTest(variant=variant_name):
                self.assert_identity_fixture(
                    f"Unexpected active link: {legacy_repository}\n",
                    accepted=False,
                )

    def test_json_unicode_escape_for_legacy_repository_identity_is_rejected(
        self,
    ) -> None:
        encoded_identity = "https://github.com/nisavid/" + r"\u0061gents"
        self.assert_identity_fixture(
            '{"repository":"' + encoded_identity + '"}\n',
            accepted=False,
            extension="json",
        )

    def test_json_escaped_solidus_for_legacy_repository_identity_is_rejected(
        self,
    ) -> None:
        encoded_identity = "https:" + r"\/\/github.com\/nisavid" + r"\/agents"
        self.assert_identity_fixture(
            '{"repository":"' + encoded_identity + '"}\n',
            accepted=False,
            extension="json",
        )

    def test_github_url_dot_segments_for_legacy_identity_are_rejected(
        self,
    ) -> None:
        variants = {
            "current-directory": "https://github.com/nisavid/" + "./agents",
            "parent-directory": (
                "https://github.com/nisavid/" + "ignored/../agents"
            ),
        }
        for variant_name, legacy_repository in variants.items():
            with self.subTest(variant=variant_name):
                self.assert_identity_fixture(
                    f"Unexpected active link: {legacy_repository}\n",
                    accepted=False,
                )

    def test_github_url_backslash_separators_for_legacy_identity_are_rejected(
        self,
    ) -> None:
        legacy_repository = "https://github.com" + r"\nisavid\agents"
        self.assert_identity_fixture(
            f"Unexpected active link: {legacy_repository}\n",
            accepted=False,
        )

    def test_composed_url_encodings_for_legacy_identity_are_rejected(self) -> None:
        variants = {
            "encoded-separators-and-dot-segment": (
                "ht"
                + "tps://github.com/nisavid/ignored%2F..%2F"
                + "agents\n",
                "txt",
            ),
            "html-dot-segment": (
                "ht"
                + "tps://github.com/nisavid/ignored/&#46;&#46;/"
                + "agents\n",
                "txt",
            ),
            "html-scheme": (
                '<a href="h&#116;'
                + 'tps://github.com/nisavid/ignored/../'
                + 'agents">legacy</a>\n',
                "html",
            ),
            "html-uts46-host": (
                "ht"
                + "tps://g&#105;thub.com/nisavid/ignored/../"
                + "agents\n",
                "html",
            ),
        }
        for variant_name, (content, extension) in variants.items():
            with self.subTest(variant=variant_name):
                self.assert_identity_fixture(
                    content,
                    accepted=False,
                    extension=extension,
                )

    def test_github_special_url_without_scheme_separators_is_rejected(
        self,
    ) -> None:
        raw_identity = "https:" + r"github.com\nisavid\agents"
        json_identity = "https:" + r"github.com\\nisavid\\agents"
        variants = {
            "raw": ("txt", f"Unexpected active link: {raw_identity}\n"),
            "json": ("json", '{"repository":"' + json_identity + '"}\n'),
        }
        for variant_name, (extension, payload) in variants.items():
            with self.subTest(variant=variant_name):
                self.assert_identity_fixture(
                    payload,
                    accepted=False,
                    extension=extension,
                )

    def test_github_url_authority_aliases_for_legacy_identity_are_rejected(
        self,
    ) -> None:
        variants = {
            "userinfo": "https://user@github.com/nisavid/" + "./agents",
            "multiple-userinfo-delimiters": (
                "https://user@domain@github.com/nisavid/" + "./agents"
            ),
            "encoded-userinfo-delimiter": (
                "https://user%40domain@github.com/nisavid/" + "./agents"
            ),
            "encoded-userinfo-slash": (
                "https://user%2Fname@github.com/nisavid/" + "./agents"
            ),
            "empty-port": "https://github.com:/nisavid/" + "./agents",
            "default-port": "https://github.com:443/nisavid/" + "./agents",
            "long-leading-zero-port": (
                "https://github.com:000000443/nisavid/" + "./agents"
            ),
            "trailing-host-dot": "https://github.com./nisavid/" + "./agents",
        }
        for variant_name, legacy_repository in variants.items():
            with self.subTest(variant=variant_name):
                self.assert_identity_fixture(
                    f"Unexpected active link: {legacy_repository}\n",
                    accepted=False,
                )

    def test_json_escaped_url_controls_are_rejected(self) -> None:
        variants = {
            "authority-tab": (
                "https://git" + r"\u0009" + "hub.com/nisavid/" + "./agents"
            ),
            "authority-newline": (
                "https://git" + r"\u000a" + "hub.com/nisavid/" + "./agents"
            ),
            "scheme-short-tab": (
                "ht" + r"\t" + "tps://github.com/nisavid/" + "./agents"
            ),
            "scheme-tab": (
                "ht" + r"\u0009" + "tps://github.com/nisavid/" + "./agents"
            ),
            "scheme-newline": (
                "htt" + r"\u000a" + "ps://github.com/nisavid/" + "./agents"
            ),
        }
        for variant_name, encoded_identity in variants.items():
            with self.subTest(variant=variant_name):
                self.assert_identity_fixture(
                    '{"repository":"' + encoded_identity + '"}\n',
                    accepted=False,
                    extension="json",
                )

    def test_raw_url_scheme_controls_are_rejected(self) -> None:
        variants = {
            "tab": "ht\ttps://github.com/nisavid/ignored/../" + "agents",
            "newline": "ht\ntps://github.com/nisavid/ignored/../" + "agents",
        }
        for variant_name, legacy_repository in variants.items():
            with self.subTest(variant=variant_name):
                self.assert_identity_fixture(
                    legacy_repository + "\n",
                    accepted=False,
                )

    def test_github_unicode_host_aliases_for_legacy_identity_are_rejected(
        self,
    ) -> None:
        variants = {
            "ideographic-full-stop": (
                "ht" + "tps://github。com/nisavid/ignored/../" + "agents"
            ),
            "percent-encoded-ideographic-full-stop": (
                "ht"
                + "tps://github%E3%80%82com/nisavid/ignored/../"
                + "agents"
            ),
            "fullwidth-full-stop": (
                "ht" + "tps://github．com/nisavid/ignored/../" + "agents"
            ),
            "halfwidth-ideographic-full-stop": (
                "ht" + "tps://github｡com/nisavid/ignored/../" + "agents"
            ),
            "fullwidth-host": (
                "ht"
                + "tps://ｇｉｔｈｕｂ．ｃｏｍ/nisavid/ignored/../"
                + "agents"
            ),
        }
        for variant_name, legacy_repository in variants.items():
            with self.subTest(variant=variant_name):
                self.assert_identity_fixture(
                    legacy_repository + "\n",
                    accepted=False,
                )

    def test_whatwg_url_characters_do_not_truncate_legacy_identity_scan(
        self,
    ) -> None:
        variants = {
            "userinfo-space": (
                "ht" + "tps://user name@github.com/nisavid/./" + "agents"
            ),
            "path-space": (
                "ht" + "tps://github.com/nisavid/ /../" + "agents"
            ),
            "path-mid-segment-space": (
                "ht" + "tps://github.com/nisavid/a b/../" + "agents"
            ),
            "path-repeated-spaces": (
                "ht" + "tps://github.com/nisavid/  /../" + "agents"
            ),
            "path-http-scheme": (
                "ht"
                + "tps://github.com/nisavid/http:ignored/../"
                + "agents"
            ),
            "path-nested-scheme": (
                "ht"
                + "tps://github.com/nisavid/ignored/https:/../../"
                + "agents"
            ),
            "path-double-quote": (
                "ht" + "tps://github.com/nisavid/" + '"ignored/../' + "agents"
            ),
            "path-apostrophe": (
                "ht" + "tps://github.com/nisavid/" + "'ignored/../" + "agents"
            ),
            "path-less-than": (
                "ht" + "tps://github.com/nisavid/" + "<ignored/../" + "agents"
            ),
            "path-greater-than": (
                "ht" + "tps://github.com/nisavid/" + ">ignored/../" + "agents"
            ),
            "path-mid-segment-quote": (
                "ht"
                + "tps://github.com/nisavid/ignored"
                + '"nested/child/../../'
                + "agents"
            ),
            "path-repeated-quotes": (
                "ht"
                + "tps://github.com/nisavid/"
                + '"ig"nored/../'
                + "agents"
            ),
            "path-raw-tab": (
                "ht" + "tps://github.com/nisa\tvid/" + "agents"
            ),
            "userinfo-form-feed": (
                "ht" + "tps://user\fname@github.com/nisavid/./" + "agents"
            ),
            "userinfo-vertical-tab": (
                "ht" + "tps://user\vname@github.com/nisavid/./" + "agents"
            ),
            "userinfo-double-quote": (
                "ht" + 'tps://user"name@github.com/nisavid/./' + "agents"
            ),
            "userinfo-apostrophe": (
                "ht" + "tps://user'name@github.com/nisavid/./" + "agents"
            ),
            "userinfo-less-than": (
                "ht" + "tps://user<name@github.com/nisavid/./" + "agents"
            ),
            "userinfo-greater-than": (
                "ht" + "tps://user>name@github.com/nisavid/./" + "agents"
            ),
        }
        for variant_name, legacy_repository in variants.items():
            with self.subTest(variant=variant_name):
                self.assert_identity_fixture(
                    legacy_repository + "\n",
                    accepted=False,
                )

    def test_url_candidate_boundaries_do_not_join_surrounding_prose(self) -> None:
        variants = {
            "same-line": (
                "See ht" + "tps://github.com/nisavid/foo for context /../agents.\n"
            ),
            "next-line": (
                "See ht" + "tps://github.com/nisavid/foo for context\n/../agents.\n"
            ),
        }
        for variant_name, content in variants.items():
            with self.subTest(variant=variant_name):
                self.assert_identity_fixture(content, accepted=True)

    def test_uts46_github_host_aliases_are_rejected(self) -> None:
        variants = {
            "modifier-capital-g": "ᴳithub.com",
            "subscript-i": "gᵢthub.com",
            "enclosed-capital-g": "🄶ithub.com",
        }
        for variant_name, host in variants.items():
            with self.subTest(variant=variant_name):
                self.assert_identity_fixture(
                    "ht" + f"tps://{host}/nisavid/ignored/../" + "agents\n",
                    accepted=False,
                )

    def test_non_uts46_github_hosts_are_not_reinterpreted(self) -> None:
        variants = {
            "mongolian-todo-soft-hyphen": "github\u1806.com",
            "zero-width-non-joiner": "github\u200c.com",
            "zero-width-joiner": "github\u200d.com",
        }
        for variant_name, host in variants.items():
            with self.subTest(variant=variant_name):
                self.assert_identity_fixture(
                    "ht" + f"tps://{host}/nisavid/ignored/../" + "agents\n",
                    accepted=True,
                )

    def test_separate_url_is_not_hidden_by_prior_authority(self) -> None:
        variants = {
            "raw": (
                "ht"
                + "tps://evil.invalid "
                + "ht"
                + "tps://github.com/nisavid/ignored/../"
                + "agents\n"
            ),
            "encoded": (
                "ht"
                + "tps://evil.invalid "
                + "%68%74"
                + "%74%70%73%3A%2F%2Fgithub.com%2Fnisavid%2Fignored%2F"
                + "..%2Fagents\n"
            ),
            "comma-separated": (
                "ht"
                + "tps://evil.invalid,"
                + "ht"
                + "tps://github.com/nisavid/ignored/../"
                + "agents\n"
            ),
            "parenthesis-separated": (
                "ht"
                + "tps://evil.invalid)"
                + "ht"
                + "tps://github.com/nisavid/ignored/../"
                + "agents\n"
            ),
            "comma-separated-encoded": (
                "ht"
                + "tps://evil.invalid,"
                + "%68%74"
                + "%74%70%73%3A%2F%2Fgithub.com%2Fnisavid%2Fignored%2F"
                + "..%2Fagents\n"
            ),
        }
        for variant_name, content in variants.items():
            with self.subTest(variant=variant_name):
                self.assert_identity_fixture(content, accepted=False)

    def test_non_equivalent_url_text_is_not_reinterpreted_as_github_authority(
        self,
    ) -> None:
        variants = {
            "query": (
                "https://evil.invalid?next=@" + "github.com/nisavid/./agents"
            ),
            "fragment": (
                "https://evil.invalid#next=@" + "github.com/nisavid/./agents"
            ),
            "embedded-scheme-prefix": (
                "nothttps://" + "github.com/nisavid/./agents"
            ),
            "multiple-trailing-host-dots": (
                "https://github.com../nisavid/" + "./agents"
            ),
            "out-of-range-port": (
                "https://github.com:99999/nisavid/" + "./agents"
            ),
            "unbounded-port": (
                "https://github.com:"
                + ("9" * 5_000)
                + "/nisavid/"
                + "./agents"
            ),
            "encoded-port-delimiter": (
                "https://github.com%3A443/nisavid/" + "./agents"
            ),
            "encoded-out-of-range-port-delimiter": (
                "https://github.com%3A99999/nisavid/" + "./agents"
            ),
            "encoded-port-digits": (
                "https://github.com:%34%34%33/nisavid/" + "./agents"
            ),
            "encoded-host-userinfo-delimiter": (
                "https://evil%40github.com/nisavid/" + "./agents"
            ),
            "encoded-host-userinfo-suffix": (
                "https://github.com%40evil.invalid/nisavid/" + "./agents"
            ),
            "double-encoded-port-delimiter": (
                "https://github.com%253A443/nisavid/" + "./agents"
            ),
            "double-encoded-host-userinfo-delimiter": (
                "https://evil%2540github.com/nisavid/" + "./agents"
            ),
            "double-encoded-host-path-delimiter": (
                "https://github.com%252Fnisavid/" + "./agents"
            ),
            "double-encoded-host-dot": (
                "ht" + "tps://github%252Ecom/nisavid/" + "./agents"
            ),
            "raw-control-split-scheme-encoded-port": (
                "ht\ttps://github.com:%34%34%33/nisavid/" + "./agents"
            ),
            "json-control-split-scheme-encoded-port": (
                "ht" + r"\u0009" + "tps://github.com:%34%34%33/nisavid/"
                + "./agents"
            ),
        }
        for variant_name, external_url in variants.items():
            with self.subTest(variant=variant_name):
                self.assert_identity_fixture(
                    external_url + "\n",
                    accepted=True,
                )

    def test_encoded_scheme_does_not_decode_percent_authority(self) -> None:
        variants = {
            "json-unicode": (
                '{"repository":"ht'
                + r"\u0074"
                + 'ps://github.com%3A443/nisavid/./agents"}\n',
                "json",
            ),
            "html-entity": (
                "h&#116;tps://github.com%3A443/nisavid/./agents\n",
                "txt",
            ),
        }
        for variant_name, (content, extension) in variants.items():
            with self.subTest(variant=variant_name):
                self.assert_identity_fixture(
                    content,
                    accepted=True,
                    extension=extension,
                )

    def test_json_identity_extraction_handles_edge_cases_without_tracebacks(
        self,
    ) -> None:
        self.assertEqual(
            validate_provingkit._json_string_values(br'"\ud800"'),
            [],
        )
        deeply_nested = b"[" * 10_000 + b"0" + b"]" * 10_000
        self.assertEqual(
            validate_provingkit._json_string_values(deeply_nested),
            [],
        )
        self.assert_identity_fixture(
            '"' + r"\ud800" + '"\n',
            accepted=True,
            extension="json",
        )
        self.assert_identity_fixture(
            "9" * 5_000 + "\n",
            accepted=True,
            extension="json",
        )

    def test_json_surrogate_does_not_hide_later_legacy_identity(self) -> None:
        encoded_host = "".join(
            rf"\u{ord(character):04x}" for character in "ｇｉｔｈｕｂ．ｃｏｍ"
        )
        self.assert_identity_fixture(
            '{"repository":"'
            + r"\ud800"
            + " https://"
            + encoded_host
            + '/nisavid/ignored/../agents"}\n',
            accepted=False,
            extension="json",
        )

    def test_large_json_number_does_not_hide_legacy_identity(self) -> None:
        encoded_host = "".join(
            rf"\u{ord(character):04x}" for character in "ｇｉｔｈｕｂ．ｃｏｍ"
        )
        self.assert_identity_fixture(
            '{"number":'
            + "9" * 5_000
            + ',"repository":"https://'
            + encoded_host
            + '/nisavid/ignored/../agents"}\n',
            accepted=False,
            extension="json",
        )

    def test_path_hard_delimiter_scan_completes_for_large_popped_segment(
        self,
    ) -> None:
        probe = (
            "from scripts import validate_provingkit as validator\n"
            "content = b'https://github.com/nisavid/' + b' ' * 64_000 "
            "+ b'/../agents'\n"
            "paths = validator._canonical_github_url_paths(content)\n"
            "expected = b'nisavid' + b'/agents'\n"
            "assert expected in paths\n"
        )
        result = subprocess.run(
            [sys.executable, "-B", "-c", probe],
            cwd=REPOSITORY,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_excessive_nested_identity_encoding_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            self.clone_with_history(repository)
            pristine = self.validate(repository)
            self.assertEqual(pristine.returncode, 0, pristine.stderr)
            encoded_segment = "%61gents"
            for _ in range(9):
                encoded_segment = encoded_segment.replace("%", "%25")
            unexpected = repository / "release/provingkit/unexpected-identity.txt"
            unexpected.write_text(
                f"Unexpected active link: https://github.com/nisavid/{encoded_segment}\n",
                encoding="utf-8",
            )

            result = self.validate(repository)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("repository identity encoding depth exceeds limit", result.stderr)

    def test_active_legacy_repository_guidance_exemption_requires_exact_block(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            shutil.copytree(
                REPOSITORY,
                repository,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            context_path = repository / "CONTEXT.md"
            expected = (
                "**Base Loadout**:\n"
                f"The portable declaration in `{LEGACY_REPOSITORY_ID}` that selects a "
                "Provingkit release; it is that repository's only Loadout.\n"
                "_Avoid_: Profile, preset"
            )
            self.assertIn(expected, context_path.read_text(encoding="utf-8"))
            context_path.write_text(
                context_path.read_text(encoding="utf-8").replace(
                    expected,
                    expected + " from an unscoped branch",
                ),
                encoding="utf-8",
            )

            result = self.validate(repository)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("active legacy repository guidance scope drift", result.stderr)

    def test_active_legacy_repository_guidance_exemption_rejects_extra_content(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            shutil.copytree(
                REPOSITORY,
                repository,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            context_path = repository / "CONTEXT.md"
            context_path.write_text(
                context_path.read_text(encoding="utf-8")
                + f"\nUnscoped repository: `{LEGACY_REPOSITORY_ID}`.\n",
                encoding="utf-8",
            )

            result = self.validate(repository)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unallowlisted legacy repository identity", result.stderr)
        self.assertIn("CONTEXT.md", result.stderr)

    def test_active_legacy_tracker_reference_exemption_requires_an_exact_url(
        self,
    ) -> None:
        for suffix in ("0", "evil", "/comments", "?query=unexpected"):
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as directory:
                repository = Path(directory) / "repository"
                shutil.copytree(
                    REPOSITORY,
                    repository,
                    ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
                )
                legacy_issue = "https://github.com/nisavid" + "/agents/issues/50"
                refresh_path = (
                    repository
                    / "release/source-skill-disposition/release-refresh-contract.json"
                )
                refresh = json.loads(refresh_path.read_text(encoding="utf-8"))
                self.assertEqual(
                    refresh["workflow"]["source_disposition_owner_issue"],
                    legacy_issue,
                )
                refresh["workflow"]["source_disposition_owner_issue"] = (
                    legacy_issue + suffix
                )
                refresh_path.write_text(
                    json.dumps(refresh, indent=2) + "\n", encoding="utf-8"
                )

                result = self.validate(repository)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("active legacy tracker reference scope drift", result.stderr)

    def test_active_legacy_tracker_reference_exemption_is_field_scoped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            shutil.copytree(
                REPOSITORY,
                repository,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            ledger_path = (
                repository / "release/source-skill-disposition/disposition-ledger.json"
            )
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            legacy_issue = "https://github.com/nisavid" + "/agents/issues/51"
            ledger["dispositions"][0]["rationale"] += f" {legacy_issue}"
            ledger_path.write_text(
                json.dumps(ledger, indent=2) + "\n", encoding="utf-8"
            )

            result = self.validate(repository)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unallowlisted legacy repository identity", result.stderr)
        self.assertIn(
            "release/source-skill-disposition/disposition-ledger.json",
            result.stderr,
        )

    def test_repository_identity_scan_rejects_symbolic_links(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            shutil.copytree(
                REPOSITORY,
                repository,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            (repository / "release/provingkit/source-link").symlink_to(
                repository / "README.md"
            )

            result = self.validate(repository)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("repository identity scan rejects symbolic links", result.stderr)

    def test_cutover_cannot_materialize_a_release_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            shutil.copytree(
                REPOSITORY,
                repository,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            (repository / "release/provingkit/release-manifest-1.0.0.json").write_text(
                "{}\n", encoding="utf-8"
            )

            result = self.validate(repository)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("release manifest instance is not authorized", result.stderr)

    def test_cutover_rejects_a_renamed_release_manifest_outside_release_root(
        self,
    ) -> None:
        for extension, escaped_contract, duplicate_contract in (
            ("json", False, False),
            ("json", True, False),
            ("txt", True, False),
            ("json", False, True),
        ):
            with (
                self.subTest(
                    extension=extension,
                    escaped_contract=escaped_contract,
                    duplicate_contract=duplicate_contract,
                ),
                tempfile.TemporaryDirectory() as directory,
            ):
                repository = Path(directory) / "repository"
                shutil.copytree(
                    REPOSITORY,
                    repository,
                    ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
                )
                unauthorized = repository / f"artifacts/not-a-release-name.{extension}"
                unauthorized.parent.mkdir()
                content = json.dumps(self.synthetic_release_manifest(), indent=2) + "\n"
                if escaped_contract:
                    content = content.replace(
                        "provingkit-release-manifest-v1",
                        "provingkit\\u002drelease-manifest-v1",
                        1,
                    )
                if duplicate_contract:
                    content = content.replace(
                        '  "contract": "provingkit-release-manifest-v1",',
                        '  "contract": "untrusted",\n'
                        '  "contract": "provingkit-release-manifest-v1",',
                        1,
                    )
                unauthorized.write_text(content, encoding="utf-8")

                result = self.validate(repository)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("release manifest instance is not authorized", result.stderr)

    def test_validator_requires_attested_git_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            shutil.copytree(
                REPOSITORY,
                repository,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )

            result = self.validate(repository)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Git history attestation unavailable", result.stderr)

    def test_retained_history_import_ref_rejects_a_descendant_tip(self) -> None:
        expected_tip = "caf9a58769af746fd5b514beff5cb305788f7e1c"
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            self.clone_with_history(repository)
            descendant_tip = subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Provingkit Test",
                    "-c",
                    "user.email=provingkit-test@example.invalid",
                    "commit-tree",
                    f"{expected_tip}^{{tree}}",
                    "-p",
                    expected_tip,
                    "-m",
                    "test descendant",
                ],
                cwd=repository,
                text=True,
                capture_output=True,
                check=True,
            ).stdout.strip()
            subprocess.run(
                [
                    "git",
                    "update-ref",
                    "refs/remotes/origin/retained/issue-81-history-import",
                    descendant_tip,
                ],
                cwd=repository,
                check=True,
            )

            result = self.validate(repository)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("retained history-import ref attestation drift", result.stderr)

    def test_attested_history_preserves_the_unreleased_cutover_boundary(self) -> None:
        retained = "8edaf590736621352262457752d087bad835555d"
        retained_ancestry = subprocess.run(
            ["git", "merge-base", "--is-ancestor", retained, "HEAD"],
            cwd=REPOSITORY,
            check=False,
        )
        self.assertEqual(retained_ancestry.returncode, 1)

        tags = subprocess.run(
            ["git", "tag", "--list"],
            cwd=REPOSITORY,
            text=True,
            capture_output=True,
            check=True,
        ).stdout
        self.assertEqual(tags, "")

        history_paths = subprocess.run(
            [
                "git",
                "log",
                "--format=",
                "--name-only",
                "-z",
                "HEAD",
                retained,
            ],
            cwd=REPOSITORY,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.split("\0")
        prohibited_roots = (
            ".scratch",
            "tooling",
            "base-loadout",
            "hindsight",
            "plugins/base-loadout",
            "plugins/hindsight",
        )
        self.assertFalse(
            any(
                path == root or path.startswith(root + "/")
                for path in history_paths
                for root in prohibited_roots
            )
        )

    def test_historical_qualification_is_outside_default_pytest_discovery(
        self,
    ) -> None:
        configuration = (REPOSITORY / "pytest.ini").read_text(encoding="utf-8")
        self.assertEqual(
            configuration,
            "[pytest]\ntestpaths = tests\nnorecursedirs = qualification/historical\n"
            "pythonpath = .\n",
        )
        if importlib.util.find_spec("pytest") is None:
            self.skipTest("pytest is unavailable")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q"],
            cwd=REPOSITORY,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("tests/test_validate_provingkit.py", result.stdout)
        self.assertNotIn("qualification/historical", result.stdout)

    def test_release_manifest_schema_must_be_valid_draft_2020_12(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            shutil.copytree(
                REPOSITORY,
                repository,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            schema_path = (
                repository / "release/provingkit/release-manifest-v1.schema.json"
            )
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            schema["properties"]["immutable"]["type"] = "not-a-json-type"
            schema_path.write_text(
                json.dumps(schema, indent=2) + "\n", encoding="utf-8"
            )

            result = self.validate(repository)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("release-manifest schema is invalid", result.stderr)

    def test_release_manifest_schema_accepts_only_the_exact_member_contract(
        self,
    ) -> None:
        from jsonschema import Draft202012Validator

        schema = json.loads(
            (
                REPOSITORY / "release/provingkit/release-manifest-v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        validator = Draft202012Validator(schema)
        valid_manifest = self.synthetic_release_manifest()
        invalid_manifest = json.loads(json.dumps(valid_manifest))
        invalid_manifest["members"][0]["id"] = "tricritical"

        self.assertEqual(list(validator.iter_errors(valid_manifest)), [])
        self.assertNotEqual(list(validator.iter_errors(invalid_manifest)), [])

    def test_release_manifest_schema_requires_each_definition_member_version(
        self,
    ) -> None:
        from jsonschema import Draft202012Validator

        schema = json.loads(
            (
                REPOSITORY / "release/provingkit/release-manifest-v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        validator = Draft202012Validator(schema)
        valid_manifest = self.synthetic_release_manifest()

        self.assertEqual(list(validator.iter_errors(valid_manifest)), [])
        for member_index, member in enumerate(valid_manifest["members"]):
            with self.subTest(member=member["id"]):
                invalid_manifest = json.loads(json.dumps(valid_manifest))
                invalid_manifest["members"][member_index]["version"] = "1.0.1"

                self.assertNotEqual(
                    list(validator.iter_errors(invalid_manifest)),
                    [],
                )

    def test_release_boundary_rejects_definition_schema_member_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            shutil.copytree(
                REPOSITORY,
                repository,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            schema_path = (
                repository / "release/provingkit/release-manifest-v1.schema.json"
            )
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            schema["$defs"]["rolecasting"]["properties"]["version"]["const"] = (
                "1.0.1"
            )
            schema_path.write_text(
                json.dumps(schema, indent=2) + "\n", encoding="utf-8"
            )

            result = self.validate(repository)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("release-manifest schema member projection drift", result.stderr)

    def test_release_boundary_binds_closed_member_cardinality_to_definition(
        self,
    ) -> None:
        mutations = (
            ("type", "object"),
            ("minItems", 0),
            ("maxItems", 6),
            ("items", {}),
        )
        for key, value in mutations:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as directory:
                repository = Path(directory) / "repository"
                shutil.copytree(
                    REPOSITORY,
                    repository,
                    ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
                )
                schema_path = (
                    repository / "release/provingkit/release-manifest-v1.schema.json"
                )
                schema = json.loads(schema_path.read_text(encoding="utf-8"))
                schema["properties"]["members"][key] = value
                schema_path.write_text(
                    json.dumps(schema, indent=2) + "\n", encoding="utf-8"
                )

                result = self.validate(repository)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("release-manifest schema member projection drift", result.stderr)

    def test_current_member_manifests_require_the_destination_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            shutil.copytree(
                REPOSITORY,
                repository,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            manifest_path = repository / "plugins/artifact-customs/plugin.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["repository"] = "https://github.com/nisavid" + "/agents"
            manifest_path.write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )

            result = self.validate(repository)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("canonical repository identity drift", result.stderr)


if __name__ == "__main__":
    unittest.main()
