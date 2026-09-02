from __future__ import annotations

import json
import hashlib
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


class ProvingkitRepositoryContractTests(unittest.TestCase):
    def validate(self, repository: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), str(repository)],
            text=True,
            capture_output=True,
            check=False,
        )

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

    def test_definition_requires_the_exact_six_member_set(self) -> None:
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
                "state": "pending-rebase-merge",
                "completion_gate": "required-before-closing-source-issue-81",
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
        self.assertEqual(len(allowlist["entries"]), 32)
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

    def test_marketplace_is_the_exact_five_member_source_projection(self) -> None:
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
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            shutil.copytree(
                REPOSITORY,
                repository,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            legacy_repository = "https://github.com/nisavid" + "/agents"
            readme = repository / "README.md"
            readme.write_text(
                readme.read_text(encoding="utf-8")
                + f"\nUnexpected active link: {legacy_repository}\n",
                encoding="utf-8",
            )

            result = self.validate(repository)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unallowlisted legacy repository identity", result.stderr)

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
            "[pytest]\ntestpaths = tests\nnorecursedirs = qualification/historical\n",
        )
        if shutil.which("pytest") is None:
            self.skipTest("pytest is unavailable")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q"],
            cwd=REPOSITORY,
            text=True,
            capture_output=True,
            check=False,
        )
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
