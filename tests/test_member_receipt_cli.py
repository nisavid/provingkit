from __future__ import annotations

import hashlib
import json
import os
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
    "artifact_customs",
    "proseweaving",
)


def copy_repository(destination: Path, *, receipt_support: bool = True) -> None:
    for directory in (
        "plugins",
        "evals",
        "release",
        "scripts",
        "tests",
        "docs",
        ".claude-plugin",
    ):
        patterns = ["__pycache__"]
        if directory == "scripts" and not receipt_support:
            patterns.append("behavior_eval_*")
        shutil.copytree(
            REPOSITORY / directory,
            destination / directory,
            symlinks=True,
            ignore=shutil.ignore_patterns(*patterns),
        )


def tree_state(root: Path) -> dict[str, tuple[int, int, str]]:
    state = {}
    for path in root.rglob("*"):
        metadata = path.lstat()
        if path.is_symlink():
            identity = os.readlink(path)
        elif path.is_file():
            identity = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            identity = "directory"
        state[str(path.relative_to(root))] = (
            metadata.st_mode,
            metadata.st_mtime_ns,
            identity,
        )
    return state


class MemberReceiptCliTests(unittest.TestCase):
    def test_explicit_context_requires_available_receipt_support(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scripts = root / "scripts"
            shutil.copytree(
                REPOSITORY / "scripts",
                scripts,
                ignore=shutil.ignore_patterns("behavior_eval_*", "__pycache__"),
            )
            repository = root / "repository"
            repository.mkdir()
            environment = os.environ.copy()
            environment.pop("PYTHONPATH", None)
            for member in MEMBERS:
                with self.subTest(member=member):
                    result = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(scripts / f"validate_{member}.py"),
                            str(repository),
                            "--source-stage",
                            "--base",
                            "base",
                            "--candidate",
                            "candidate",
                            "--receipt-root",
                            "release/eval-receipts",
                            "--procedure-revision",
                            "procedure",
                        ],
                        cwd=temporary,
                        env=environment,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn(
                        "Receipt source-stage support is unavailable", result.stderr
                    )
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertEqual(result.stdout, "")
                    self.assertEqual(list(repository.iterdir()), [])

    def test_legacy_writers_need_no_receipt_support(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary) / "repository"
            copy_repository(repository, receipt_support=False)
            environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
            environment.pop("PYTHONPATH", None)
            subprocess.run(
                ["git", "init", "-q", str(repository)],
                env=environment,
                capture_output=True,
                check=True,
            )
            writers = [(member, "--write-content-lock") for member in MEMBERS]
            writers.append(("mergecraft", "--write-markdown-projections"))
            for member, writing in writers:
                with self.subTest(member=member, writing=writing):
                    result = subprocess.run(
                        [
                            sys.executable,
                            "-B",
                            str(repository / "scripts" / f"validate_{member}.py"),
                            writing,
                            str(repository),
                        ],
                        cwd=repository,
                        env=environment,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("updated", result.stdout)

    def test_explicit_route_preserves_member_result_and_output_channels(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary) / "repository"
            copy_repository(repository)
            environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

            def git(*arguments: str) -> str:
                return subprocess.check_output(
                    [
                        "git",
                        "-c",
                        "core.hooksPath=/dev/null",
                        "-c",
                        "commit.gpgsign=false",
                        *arguments,
                    ],
                    cwd=repository,
                    env=environment,
                    stderr=subprocess.DEVNULL,
                    text=True,
                ).strip()

            git("init", "-q")
            git("config", "user.name", "Receipt fixture")
            git("config", "user.email", "receipt@example.invalid")
            git("add", ".")
            git("commit", "-qm", "fixture")
            candidate = git("rev-parse", "HEAD")
            for member in MEMBERS:
                with self.subTest(member=member):
                    arguments = [
                        sys.executable,
                        "-B",
                        str(REPOSITORY / "scripts" / f"validate_{member}.py"),
                        str(repository),
                        "--source-stage",
                        "--base",
                        candidate,
                        "--candidate",
                        candidate,
                        "--receipt-root",
                        "release/eval-receipts",
                        "--procedure-revision",
                        candidate,
                    ]
                    if member == "mergecraft":
                        arguments.extend(["--skill", "publishing-reviewable-prs"])
                    result = subprocess.run(
                        arguments,
                        env=environment,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    receipt = json.loads(result.stdout)
                    self.assertEqual(receipt["status"], "not-required")
                    self.assertEqual(
                        receipt["source_stage"]["structural_candidate_revision"],
                        candidate,
                    )
                    self.assertEqual(
                        receipt["source_stage"]["procedure_revision"], candidate
                    )
                    self.assertEqual(
                        receipt["source_stage"]["member_qualification"],
                        "not-evaluated",
                    )
                    self.assertIn(
                        "validation passed"
                        if member != "artifact_customs"
                        else "contract passed",
                        result.stderr,
                    )
                    self.assertEqual(git("status", "--porcelain"), "")

            # --skill is a structural CLI option. A different changed skill in
            # that member still needs its Receipt and must fail without one.
            changed_skill = "mergecraft/getting-prs-merged"
            adapter = repository / (
                "plugins/mergecraft/skills/getting-prs-merged/agents/openai.yaml"
            )
            adapter.write_bytes(adapter.read_bytes() + b"\n")
            git("add", str(adapter.relative_to(repository)))
            git("commit", "-qm", "change another member skill")
            changed = git("rev-parse", "HEAD")
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(REPOSITORY / "scripts" / "validate_mergecraft.py"),
                    str(repository),
                    "--source-stage",
                    "--skill",
                    "publishing-reviewable-prs",
                    "--base",
                    candidate,
                    "--candidate",
                    changed,
                    "--receipt-root",
                    "release/eval-receipts",
                    "--procedure-revision",
                    candidate,
                ],
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 1, result.stderr)
            receipt = json.loads(result.stdout)
            self.assertEqual(receipt["status"], "fail")
            self.assertEqual(receipt["member"], "mergecraft")
            self.assertIn(changed_skill, receipt["checked_skills"])
            self.assertIn("quick validation passed", result.stderr)
            self.assertEqual(git("status", "--porcelain"), "")

    def test_receipt_context_and_unknown_options_cannot_write(self) -> None:
        context = [
            "--source-stage",
            "--base",
            "base",
            "--candidate",
            "candidate",
            "--receipt-root",
            "release/eval-receipts",
            "--procedure-revision",
            "procedure",
        ]
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary) / "repository"
            copy_repository(repository)
            before = tree_state(repository)
            for member in MEMBERS:
                for writing in (
                    "--write-content-lock",
                    "--write-markdown-projections",
                    "--prepare-content-lock",
                ):
                    with self.subTest(member=member, writing=writing):
                        result = subprocess.run(
                            [
                                sys.executable,
                                "-B",
                                str(REPOSITORY / "scripts" / f"validate_{member}.py"),
                                writing,
                                str(repository),
                                *context,
                            ],
                            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                        self.assertEqual(result.returncode, 2, result.stderr)
                        self.assertIn("error:", result.stderr)
                        self.assertEqual(result.stdout, "")
                        self.assertEqual(tree_state(repository), before)

    def test_partial_receipt_context_is_a_usage_error_before_validation(self) -> None:
        context = (
            ("--base", "base"),
            ("--candidate", "candidate"),
            ("--receipt-root", "release/eval-receipts"),
            ("--procedure-revision", "procedure"),
        )
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary) / "empty-repository"
            repository.mkdir()
            sentinel = repository / "unchanged"
            sentinel.write_text("No validation or writes before context admission.\n")
            before = sentinel.stat()
            for member in MEMBERS:
                for missing in range(len(context) + 1):
                    arguments = [
                        word
                        for index, pair in enumerate(context)
                        if index != missing
                        for word in pair
                    ]
                    if missing < len(context):
                        arguments.append("--source-stage")
                    with self.subTest(member=member, missing=missing):
                        result = subprocess.run(
                            [
                                sys.executable,
                                "-B",
                                str(REPOSITORY / "scripts" / f"validate_{member}.py"),
                                str(repository),
                                *arguments,
                            ],
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                        self.assertEqual(result.returncode, 2, result.stderr)
                        self.assertIn("error:", result.stderr)
                        self.assertNotIn("unrecognized arguments", result.stderr)
                        self.assertEqual(result.stdout, "")
            self.assertEqual(list(repository.iterdir()), [sentinel])
            self.assertEqual(sentinel.stat().st_mtime_ns, before.st_mtime_ns)

    def test_structural_source_stage_needs_no_receipt_support(self) -> None:
        # A copied CLI distribution lacks the optional Receipt modules. Its
        # public structural routes must still validate the real member sources.
        with tempfile.TemporaryDirectory() as temporary:
            scripts = Path(temporary) / "scripts"
            shutil.copytree(
                REPOSITORY / "scripts",
                scripts,
                ignore=shutil.ignore_patterns("behavior_eval_*", "__pycache__"),
            )
            environment = os.environ.copy()
            environment.pop("PYTHONPATH", None)
            for member in MEMBERS:
                with self.subTest(member=member):
                    command = [
                        sys.executable,
                        "-B",
                        str(scripts / f"validate_{member}.py"),
                        str(REPOSITORY),
                    ]
                    ordinary = subprocess.run(
                        command,
                        cwd=temporary,
                        env=environment,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    source = subprocess.run(
                        [*command, "--source-stage"],
                        cwd=temporary,
                        env=environment,
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    self.assertEqual(ordinary.returncode, 0, ordinary.stderr)
                    self.assertEqual(source.returncode, 0, source.stderr)
                    expected = ordinary.stdout
                    if member == "artifact_customs":
                        expected = expected.replace("release-stage", "source-stage")
                    self.assertEqual(source.stdout, expected)


if __name__ == "__main__":
    unittest.main()
