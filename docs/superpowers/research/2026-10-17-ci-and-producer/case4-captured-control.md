# GitHub Actions hardening and merge-gate proposal

This proposal adds read-only validation, reproducible projection checks, pinned actions, CodeQL analysis, and one stable aggregate gate. It uses the `security-best-practices` review lens.

The proposal is local source only. It does not claim that GitHub accepted the workflows, that any check ran, or that branch protection blocked a merge.

## Current increment

**Outcome**

- Validate the Python code and instruction plugin on pull requests, default-branch pushes, and future merge-queue commits.
- Detect manifest, resource, and generated-adapter drift.
- Analyze Python with CodeQL’s default and `security-extended` queries.
- Prevent moving action references and common high-risk workflow permissions.
- Expose one aggregate CI result for the eventual merge gate.

**Supported inputs**

- Python 3.12, the project’s stated minimum.
- The documented `unittest`, validation, and adapter-writer commands.
- Standard GitHub-hosted Linux runners.
- No project dependency downloads, cache, artifacts, deployment credentials, or scheduled runs.

**Acceptance evidence**

The source is ready for review when the following files have been reviewed together. Completion still requires the hosted qualification described below.

---

## 1. `.github/workflows/ci.yml`

Replace the existing CI workflow rather than leaving the write-enabled workflow active alongside this one.

```yaml
name: CI

on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main
  # This event is dormant until a merge queue is enabled. Keeping it here
  # prevents a later queue from bypassing the required workflow.
  merge_group:
    types:
      - checks_requested

concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

defaults:
  run:
    shell: bash

jobs:
  unit:
    name: Unit tests (Python 3.12)
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - name: Check out the repository
        uses: actions/checkout@08c6903cd8c0fde910a37f88322edcfb5dd907a8
        with:
          persist-credentials: false

      - name: Set up Python 3.12
        uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065
        with:
          python-version: "3.12"

      - name: Run unit tests
        run: python -m unittest discover -s tests

  content:
    name: Plugin content and projection
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - name: Check out the repository
        uses: actions/checkout@08c6903cd8c0fde910a37f88322edcfb5dd907a8
        with:
          persist-credentials: false

      - name: Set up Python 3.12
        uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065
        with:
          python-version: "3.12"

      - name: Validate the canonical plugin and adapter
        run: python scripts/validate_scribe.py .

      - name: Verify that the committed adapter is reproducible
        run: |
          python scripts/write_scribe_adapter.py .

          dirty="$(git status --porcelain=v1 --untracked-files=all)"
          if [[ -n "$dirty" ]]; then
            printf '%s\n' \
              "Adapter regeneration changed the checkout." \
              "Run 'python scripts/write_scribe_adapter.py .' and commit the result." \
              "$dirty"
            git --no-pager diff -- \
              plugins/scribe/.claude-plugin/plugin.json || true
            exit 1
          fi

  workflow-policy:
    name: Workflow policy
    runs-on: ubuntu-latest
    timeout-minutes: 5

    steps:
      - name: Check out the repository
        uses: actions/checkout@08c6903cd8c0fde910a37f88322edcfb5dd907a8
        with:
          persist-credentials: false

      - name: Set up Python 3.12
        uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065
        with:
          python-version: "3.12"

      - name: Check workflow policy
        run: python scripts/check_workflow_policy.py .

  codeql:
    name: CodeQL (Python)
    runs-on: ubuntu-latest
    timeout-minutes: 20

    permissions:
      contents: read
      security-events: write

    steps:
      - name: Check out the repository
        uses: actions/checkout@08c6903cd8c0fde910a37f88322edcfb5dd907a8
        with:
          persist-credentials: false

      - name: Initialize CodeQL
        uses: github/codeql-action/init@5cf07d8b700b67e235fbb65cbc84f69c0cf10464
        with:
          languages: python
          build-mode: none
          config: |
            queries:
              - uses: security-extended

      - name: Analyze Python
        uses: github/codeql-action/analyze@5cf07d8b700b67e235fbb65cbc84f69c0cf10464
        with:
          category: /language:python

  required:
    name: Required
    if: ${{ always() }}
    needs:
      - unit
      - content
      - workflow-policy
      - codeql
    runs-on: ubuntu-latest
    timeout-minutes: 5
    permissions: {}

    env:
      UNIT_RESULT: ${{ needs.unit.result }}
      CONTENT_RESULT: ${{ needs.content.result }}
      POLICY_RESULT: ${{ needs.workflow-policy.result }}
      CODEQL_RESULT: ${{ needs.codeql.result }}

    steps:
      - name: Require every CI job to succeed
        run: |
          for result in \
            "$UNIT_RESULT" \
            "$CONTENT_RESULT" \
            "$POLICY_RESULT" \
            "$CODEQL_RESULT"
          do
            if [[ "$result" != "success" ]]; then
              printf 'A required CI job ended with result: %s\n' "$result"
              exit 1
            fi
          done
```

The aggregate job deliberately uses `always()`. Without it, an upstream failure could skip the aggregate check, and GitHub may treat a skipped required check differently from an explicit failure.

There are no path filters. Every pull request should produce the gate, including documentation-only changes and changes to the gate itself.

---

## 2. `scripts/check_workflow_policy.py`

This dependency-free lexical check prevents moving action tags, `pull_request_target`, persisted checkout credentials, and repository-mutating permissions. It does not replace YAML validation or action-source review.

```python
#!/usr/bin/env python3

"""Enforce the repository's minimum GitHub Actions security policy."""

from __future__ import annotations

import re
import sys
from pathlib import Path

_FULL_ACTION_SHA = re.compile(r"^[0-9a-f]{40}$")
_FULL_IMAGE_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_WRITE_PERMISSION = re.compile(
    r"^(?:"
    r"actions|attestations|checks|contents|deployments|discussions|"
    r"id-token|issues|models|packages|pages|pull-requests|statuses"
    r")\s*:\s*write$"
)


def _logical_line(raw_line: str) -> str:
    line = raw_line.strip()
    if not line or line.startswith("#"):
        return ""

    line = line.split(" #", 1)[0].rstrip()
    if line.startswith("- "):
        line = line[2:].lstrip()
    return line


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def find_violations(root: Path) -> list[str]:
    workflow_directory = root / ".github" / "workflows"
    workflow_paths = sorted(
        {
            *workflow_directory.glob("*.yml"),
            *workflow_directory.glob("*.yaml"),
        }
    )

    if not workflow_paths:
        return [".github/workflows: no workflow files found"]

    violations: list[str] = []

    for path in workflow_paths:
        relative_path = path.relative_to(root)

        for line_number, raw_line in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            line = _logical_line(raw_line)
            if not line:
                continue

            location = f"{relative_path}:{line_number}"

            if "pull_request_target" in line:
                violations.append(
                    f"{location}: pull_request_target is not permitted"
                )

            if line == "permissions: write-all":
                violations.append(
                    f"{location}: permissions: write-all is not permitted"
                )

            if _FORBIDDEN_WRITE_PERMISSION.fullmatch(line):
                violations.append(
                    f"{location}: repository-mutating write permission is not permitted"
                )

            if re.fullmatch(r"persist-credentials\s*:\s*true", line):
                violations.append(
                    f"{location}: checkout credentials must not be persisted"
                )

            if not line.startswith("uses:"):
                continue

            value = _unquote(line.partition(":")[2].strip())

            if value.startswith("./"):
                continue

            if value.startswith("docker://"):
                _, separator, digest = value.rpartition("@sha256:")
                if not separator or not _FULL_IMAGE_DIGEST.fullmatch(digest):
                    violations.append(
                        f"{location}: Docker actions must use a full sha256 digest"
                    )
                continue

            _, separator, revision = value.rpartition("@")
            if not separator or not _FULL_ACTION_SHA.fullmatch(revision):
                violations.append(
                    f"{location}: remote actions must use a full lowercase commit SHA"
                )

    return violations


def main(argv: list[str]) -> int:
    root = Path(argv[1] if len(argv) > 1 else ".").resolve()
    violations = find_violations(root)

    if violations:
        print("GitHub Actions policy violations:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1

    print("GitHub Actions policy passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

---

## 3. `tests/test_workflow_policy.py`

```python
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.check_workflow_policy import find_violations


class WorkflowPolicyTests(unittest.TestCase):
    def scan(self, workflow: str) -> list[str]:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            workflow_directory = root / ".github" / "workflows"
            workflow_directory.mkdir(parents=True)
            (workflow_directory / "ci.yml").write_text(
                workflow,
                encoding="utf-8",
            )
            return find_violations(root)

    def test_accepts_pinned_and_local_actions(self) -> None:
        revision = "a" * 40
        workflow = f"""
on:
  pull_request:
permissions:
  contents: read
jobs:
  test:
    steps:
      - uses: actions/checkout@{revision}
        with:
          persist-credentials: false
      - uses: ./.github/actions/local
"""
        self.assertEqual([], self.scan(workflow))

    def test_rejects_moving_action_reference(self) -> None:
        violations = self.scan(
            """
jobs:
  test:
    steps:
      - uses: actions/checkout@v5
"""
        )
        self.assertTrue(
            any("full lowercase commit SHA" in item for item in violations)
        )

    def test_rejects_privileged_pull_request_workflow(self) -> None:
        violations = self.scan(
            """
on:
  pull_request_target:
permissions:
  contents: write
"""
        )
        self.assertTrue(
            any("pull_request_target" in item for item in violations)
        )
        self.assertTrue(
            any("write permission" in item for item in violations)
        )

    def test_rejects_persisted_checkout_credentials(self) -> None:
        violations = self.scan(
            """
jobs:
  test:
    steps:
      - uses: ./local-action
        with:
          persist-credentials: true
"""
        )
        self.assertTrue(
            any("must not be persisted" in item for item in violations)
        )


if __name__ == "__main__":
    unittest.main()
```

Before activation, inspect every existing file under `.github/workflows/`. The policy check should fail if the legacy workflow still contains moving tags or `contents: write`.

---

## 4. Protect the gate sources

A minimal `.github/CODEOWNERS` addition is:

```text
/.github/workflows/                   @sample-maintainer
/.github/CODEOWNERS                   @sample-maintainer
/scripts/check_workflow_policy.py     @sample-maintainer
/scripts/validate_scribe.py           @sample-maintainer
/scripts/write_scribe_adapter.py      @sample-maintainer
/tests/test_workflow_policy.py        @sample-maintainer
```

Confirm that `@sample-maintainer` resolves to an eligible reviewer before committing this file. Then require code-owner approval in the repository rules. CODEOWNERS alone does not enforce approval.

## Merge-gate configuration

After the first qualified pull-request run, configure a ruleset or branch protection for `main`:

1. Require pull requests.
2. Require at least one approval and code-owner approval.
3. Dismiss stale approvals after new commits.
4. Require conversations to be resolved.
5. Require the observed aggregate `Required` check from the GitHub Actions app.
6. Require the branch to be up to date before merging.
7. Block branch deletion and force pushes.
8. Remove or tightly limit bypass actors.
9. Keep direct pushes to `main` disabled.

Do not enter a guessed status-check name. GitHub must first produce the check so its exact context and app identity can be recorded.

The aggregate job proves that CodeQL completed successfully; it does **not** prove that CodeQL found no alerts. If the repository’s available rules support code-scanning merge protection, separately require CodeQL results at an agreed severity threshold. Select that threshold only after reviewing the initial alert baseline.

## Hosted qualification

A maintainer-controlled qualification pull request should establish all of the following before the gate is treated as dependable:

- All action SHAs resolve to the intended official repositories and reviewed releases.
- The workflow parses and runs on the available `ubuntu-latest` image.
- The documented tests run successfully under Python 3.12 without project dependency downloads.
- Plugin validation is read-only.
- Adapter regeneration leaves a clean checkout for current canonical content.
- A deliberately stale adapter makes `Plugin content and projection` fail.
- A deliberately failing unit test makes the aggregate gate fail.
- A temporary moving action tag makes `Workflow policy` fail.
- CodeQL initializes, analyzes Python, uploads results, and uses the `security-extended` suite.
- A same-repository PR and, if accepted, a fork-originated PR both receive usable CodeQL results without exposing credentials.
- GitHub reports the exact check context and producer identity intended for the ruleset.
- A cancelled or failed prerequisite makes `Required` fail rather than pass or disappear.
- Removing or renaming the required job leaves the pull request blocked.
- A temporary, never-merged CodeQL-positive qualification change proves whether native code-scanning protection blocks the merge at the selected threshold.
- If merge queue is later enabled, a trial merge group receives the same required gate before the queue becomes mandatory.

Keep merge queue disabled until that last case succeeds. The `merge_group` trigger can remain in the workflow meanwhile.

## Deferred decisions

- **Coverage:** Do not invent a coverage threshold before a baseline exists. A later proposal can add `coverage.py`, a pinned installation mechanism, and a ratcheted threshold after hosted measurement.
- **Additional Python versions:** Python 3.12 is the only explicit project constraint in the fixture. Add exact newer versions after maintainers select the supported test set.
- **Scheduled CodeQL:** No schedule is proposed.
- **Automated action updates:** The pinned SHAs require reviewed maintenance. Add Dependabot only after choosing an update schedule and review policy.
- **Artifacts and caches:** Neither is needed for these dependency-free checks.

The CodeQL shape follows GitHub’s advanced-setup documentation for Python `build-mode: none`, inline configuration, `security-extended`, and an explicit analysis category. GitHub’s Python documentation also supports the checkout/setup/test workflow structure, while this project retains its dependency-free `unittest` command.