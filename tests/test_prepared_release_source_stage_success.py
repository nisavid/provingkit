from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
PREPARED_RELEASE_ENTRYPOINT = (
    REPOSITORY / "scripts" / "run_prepared_release_validation.sh"
)
EXPECTED_MEMBER_IDENTITIES = {
    "artifact-customs",
    "mergecraft",
    "rolecasting",
    "task-witness",
    "tricritical",
    "versionkeeping",
}


class PreparedReleaseSourceStageSuccessTests(unittest.TestCase):
    def test_checked_out_candidate_completes_prepared_source_stage_validation(
        self,
    ) -> None:
        prepared_python = Path(sys.executable).resolve(strict=True)
        result = subprocess.run(
            [
                "/bin/sh",
                str(PREPARED_RELEASE_ENTRYPOINT),
                "source-stage",
                str(prepared_python),
                str(REPOSITORY),
            ],
            cwd=REPOSITORY,
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )

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


if __name__ == "__main__":
    unittest.main()
