"""Exercise assigned local-alpha versions through the member validator CLIs."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
MEMBERS = (
    "rolecasting",
    "tricritical",
    "versionkeeping",
    "mergecraft",
    "artifact-customs",
    "proseweaving",
)


class LocalAlphaMemberVersionTests(unittest.TestCase):
    def fixture(self, destination: Path, version: str) -> None:
        shutil.copytree(
            REPOSITORY,
            destination,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
        )
        subprocess.run(["git", "init", "-q"], cwd=destination, check=True)
        for member in MEMBERS:
            root = destination / "plugins" / member
            for relative in ("plugin.json", ".claude-plugin/plugin.json"):
                path = root / relative
                manifest = json.loads(path.read_text(encoding="utf-8"))
                manifest["version"] = version
                path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            changelog = root / "CHANGELOG.md"
            changelog.write_text(
                changelog.read_text(encoding="utf-8").replace(
                    "# Changelog\n",
                    f"# Changelog\n\n## {version}\n\nLocal alpha fixture.\n",
                    1,
                ),
                encoding="utf-8",
            )

    @staticmethod
    def validate(repository: Path, member: str, *, write: bool = False):
        script = REPOSITORY / "scripts" / f"validate_{member.replace('-', '_')}.py"
        arguments = [sys.executable, str(script)]
        if member in ("rolecasting", "tricritical", "proseweaving"):
            if write:
                arguments.append("--write-content-lock")
            arguments.append(str(repository))
        else:
            arguments.append(str(repository))
            if write:
                arguments.append("--write-content-lock")
        return subprocess.run(arguments, text=True, capture_output=True, check=False)

    def test_all_six_member_validators_accept_an_assigned_alpha(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            self.fixture(repository, "0.1.0-alpha.2")
            for member in MEMBERS:
                with self.subTest(member=member):
                    result = self.validate(repository, member, write=True)
                    self.assertEqual(result.returncode, 0, result.stderr)

    def test_all_six_member_validators_reject_invalid_ordinals(self) -> None:
        diagnostics = {
            "rolecasting": "canonical manifest version drift",
            "tricritical": "canonical manifest version is invalid",
            "versionkeeping": "canonical manifest version drift",
            "mergecraft": "canonical version drift",
            "artifact-customs": "canonical Agent Plugin manifest drift",
            "proseweaving": "canonical manifest version drift",
        }
        for version in ("0.1.0-alpha.02", "0.1.0-alpha.0"):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as directory:
                repository = Path(directory) / "repository"
                self.fixture(repository, version)
                for member in MEMBERS:
                    with self.subTest(member=member):
                        result = self.validate(repository, member)
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn(diagnostics[member], result.stderr)


if __name__ == "__main__":
    unittest.main()
