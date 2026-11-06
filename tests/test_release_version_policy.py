from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.member_versions import is_supported_member_version


class CurrentMemberVersionPolicyTests(unittest.TestCase):
    def test_current_source_rejects_unreleased_v1_metadata(self) -> None:
        self.assertFalse(is_supported_member_version("1.0.0"))

    def test_six_current_identity_manifests_use_assigned_alpha5(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        observed = {}
        for member in ("rolecasting", "tricritical", "versionkeeping", "mergecraft", "artifact-customs", "proseweaving"):
            root = repository / "plugins" / member
            canonical = json.loads((root / "plugin.json").read_text())
            adapter = json.loads((root / ".claude-plugin/plugin.json").read_text())
            observed[member] = (canonical["version"], adapter["version"])
        self.assertEqual(observed, {
            "rolecasting": ("0.1.0-alpha.6", "0.1.0-alpha.6"),
            "tricritical": ("0.1.0-alpha.6", "0.1.0-alpha.6"),
            "versionkeeping": ("0.1.0-alpha.6", "0.1.0-alpha.6"),
            "mergecraft": ("0.1.0-alpha.6", "0.1.0-alpha.6"),
            "artifact-customs": ("0.1.0-alpha.6", "0.1.0-alpha.6"),
            "proseweaving": ("0.1.0-alpha.6", "0.1.0-alpha.6"),
        })

    def test_assigned_alpha_is_valid_in_member_release_schema(self) -> None:
        from jsonschema import Draft202012Validator

        repository = Path(__file__).resolve().parents[1]
        schema = json.loads((repository / "release/provingkit/release-manifest-v1.schema.json").read_text())
        member_schema = {"$ref": "#/$defs/rolecasting", "$defs": schema["$defs"]}
        # Format-only digests in an in-memory schema example, not a release receipt.
        example = {
            "id": "rolecasting",
            "distribution_kind": "agent-plugin",
            "version": "0.1.0-alpha.6",
            "identity_manifests": {
                "canonical": {"path": "plugins/rolecasting/plugin.json", "sha256": "sha256:" + "a" * 64},
                "claude": {"path": "plugins/rolecasting/.claude-plugin/plugin.json", "sha256": "sha256:" + "b" * 64},
            },
            "content_identity": {
                "kind": "plugin-content-lock",
                "path": "plugins/rolecasting/content-lock.json",
                "sha256": "sha256:" + "c" * 64,
            },
        }
        errors = [error.message for error in Draft202012Validator(member_schema).iter_errors(example)]
        self.assertEqual(errors, [])
