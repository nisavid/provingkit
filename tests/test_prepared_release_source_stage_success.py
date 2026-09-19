from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
EXPECTED_MEMBER_IDENTITIES = {
    "artifact-customs",
    "mergecraft",
    "praxis",
    "rolecasting",
    "proseweaving",
    "tricritical",
    "versionkeeping",
}


class PreparedReleaseSourceStageSuccessTests(unittest.TestCase):
    def run_prepared_source_stage(
        self, repository: Path
    ) -> subprocess.CompletedProcess[str]:
        prepared_python = Path(sys.executable).resolve(strict=True)
        return subprocess.run(
            [
                "/bin/sh",
                str(repository / "scripts/run_prepared_release_validation.sh"),
                "source-stage",
                str(prepared_python),
                str(repository),
            ],
            cwd=repository,
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )

    def test_checked_out_candidate_completes_prepared_source_stage_validation(
        self,
    ) -> None:
        result = self.run_prepared_source_stage(REPOSITORY)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        identities = json.loads(result.stdout)
        self.assertEqual(set(identities), {"plugins", "schema_version"})
        self.assertEqual(identities["schema_version"], 1)
        self.assertIsInstance(identities["plugins"], dict)
        self.assertEqual(set(identities["plugins"]), EXPECTED_MEMBER_IDENTITIES)
        for member in sorted(EXPECTED_MEMBER_IDENTITIES):
            with self.subTest(member=member):
                identity = identities["plugins"][member]
                self.assertEqual(
                    set(identity), {"composite_sha256", "plugin_sha256"}
                )
                for digest in identity.values():
                    self.assertRegex(digest, r"\A[0-9a-f]{64}\Z")

    def test_prepared_source_stage_rejects_malformed_current_definitions(
        self,
    ) -> None:
        mutations = (
            ("corpus shape", "evals/praxis/corpus.json", "corpus-shape"),
            (
                "control-plane selector",
                "evals/control-plane-matrix.json",
                "control-selector",
            ),
            (
                "control-plane inventory",
                "evals/control-plane-matrix.json",
                "control-inventory",
            ),
            (
                "routing count",
                "evals/skill-routing-matrix.json",
                "routing-count",
            ),
            (
                "routing semantic digest",
                "evals/skill-routing-matrix.json",
                "routing-digest",
            ),
        )
        for label, relative, mutation in mutations:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                repository = Path(directory) / "repository"
                shutil.copytree(
                    REPOSITORY,
                    repository,
                    ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
                )
                path = repository / relative
                document = json.loads(path.read_text(encoding="utf-8"))
                if mutation == "corpus-shape":
                    document["scenarios"] = {}
                elif mutation == "control-selector":
                    document["skills"][-1]["scenario"]["selector"] = (
                        "missing-praxis-selector"
                    )
                elif mutation == "control-inventory":
                    document["skills"].pop()
                elif mutation == "routing-count":
                    document["skills"].pop()
                else:
                    document["semantic_definition"]["sha256"] = "0" * 64
                path.write_text(
                    json.dumps(document, indent=2) + "\n", encoding="utf-8"
                )

                result = self.run_prepared_source_stage(repository)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(
                    "definition validation failed",
                    result.stdout + result.stderr,
                )


if __name__ == "__main__":
    unittest.main()
