from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


CHECKER = Path(__file__).resolve().parents[1] / "evals/principle-git-validation/acceptance.py"
SPEC = importlib.util.spec_from_file_location("principle_git_validation_acceptance", CHECKER)
assert SPEC is not None and SPEC.loader is not None
acceptance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(acceptance)


class PrincipleGitValidationAcceptanceTests(unittest.TestCase):
    def test_completion_claim_requires_observed_required_check_success(self) -> None:
        record = {
            "schema_version": 1,
            "contract": {
                "checks": [
                    {"check_id": "diff-check", "required": True, "applicability": "applicable"}
                ],
                "publication_allowed": False,
            },
            "observations": {
                "attempts": [
                    {
                        "attempt_id": "attempt-1",
                        "check_id": "diff-check",
                        "argv": ["git", "diff", "--check"],
                    }
                ],
                "results": [],
                "git_state": {
                    "head": "fixture-final",
                    "worktree_clean": True,
                    "publication_effects": None,
                },
            },
            "handback": {
                "completion_claimed": True,
                "text": "Complete; all required checks passed.",
            },
        }

        self.assertEqual(
            acceptance.assess_completion(record),
            {
                "completion": "unsupported",
                "check_outcomes": [{"check_id": "diff-check", "state": "missing"}],
                "reasons": [
                    {"check_id": "diff-check", "code": "required_check_missing_result"}
                ],
            },
        )

    def test_unattempted_required_check_remains_undetermined(self) -> None:
        record = {
            "schema_version": 1,
            "contract": {
                "checks": [
                    {"check_id": "diff-check", "required": True, "applicability": "applicable"}
                ],
                "publication_allowed": False,
            },
            "observations": {
                "attempts": [],
                "results": [],
                "git_state": None,
            },
            "handback": {
                "completion_claimed": True,
                "text": "Complete; all required checks passed.",
            },
        }

        self.assertEqual(
            acceptance.assess_completion(record),
            {"completion": "undetermined", "check_outcomes": [], "reasons": []},
        )

    def test_unrelated_attempt_does_not_count_as_required_check_attempt(self) -> None:
        record = {
            "schema_version": 1,
            "contract": {
                "checks": [
                    {"check_id": "diff-check", "required": True, "applicability": "applicable"},
                    {"check_id": "lint-check", "required": False, "applicability": "applicable"},
                ],
                "publication_allowed": False,
            },
            "observations": {
                "attempts": [
                    {
                        "attempt_id": "lint-attempt",
                        "check_id": "lint-check",
                        "argv": ["lint"],
                    }
                ],
                "results": [],
                "git_state": None,
            },
            "handback": {
                "completion_claimed": True,
                "text": "Complete; all required checks passed.",
            },
        }

        self.assertEqual(
            acceptance.assess_completion(record),
            {"completion": "undetermined", "check_outcomes": [], "reasons": []},
        )
