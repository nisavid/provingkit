# GitHub Actions hardening and merge-gate proposal

This increment provides reviewable CI source and a staged merge-gate design for `sample-maintainer/prompt-linter`. It uses the supplied `configuring-repositories` skill.

It does not activate repository settings or claim that local commands, hosted Actions, CodeQL coverage, check identities, or merge enforcement have been observed.

## Proposed `.github/workflows/ci.yml`

```yaml
name: CI

on:
  pull_request:
    branches:
      - main
  push:
    branches:
      - main
  # This is inert unless a merge queue is later enabled. Keeping it here
  # prevents the required gate from disappearing on merge-group commits.
  merge_group:

permissions:
  contents: read

concurrency:
  group: ci-${{ github.event_name }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

jobs:
  tests:
    name: Tests / Python ${{ matrix.python-version }}
    runs-on: ubuntu-24.04
    timeout-minutes: 10
    strategy:
      fail-fast: false
      matrix:
        python-version:
          - "3.12"
          - "3.13"
          - "3.14"

    steps:
      - name: Check out source
        uses: actions/checkout@08c6903cd8c0fde910a37f88322edcfb5dd907a8 # v5.0.0
        with:
          persist-credentials: false

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5.6.0
        with:
          python-version: ${{ matrix.python-version }}
          cache: false

      - name: Compile Python sources
        run: python -m compileall -q src scripts tests

      - name: Run unit tests
        run: python -m unittest discover -s tests

  content:
    name: Plugin content and projection
    runs-on: ubuntu-24.04
    timeout-minutes: 10

    steps:
      - name: Check out source
        uses: actions/checkout@08c6903cd8c0fde910a37f88322edcfb5dd907a8 # v5.0.0
        with:
          persist-credentials: false

      - name: Set up Python
        uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5.6.0
        with:
          python-version: "3.12"
          cache: false

      - name: Validate the committed plugin
        run: python scripts/validate_scribe.py .

      - name: Regenerate the adapter
        run: python scripts/write_scribe_adapter.py .

      - name: Require regeneration to be clean
        shell: bash
        run: |
          set -euo pipefail

          git diff --exit-code

          untracked="$(git ls-files --others --exclude-standard)"
          if [[ -n "$untracked" ]]; then
            printf '%s\n' "Adapter generation created untracked files:"
            printf '%s\n' "$untracked"
            exit 1
          fi

  gate:
    name: CI / merge gate
    if: ${{ always() }}
    needs:
      - tests
      - content
    runs-on: ubuntu-24.04
    timeout-minutes: 5
    permissions: {}

    steps:
      - name: Require every dependency to succeed
        env:
          TESTS_RESULT: ${{ needs.tests.result }}
          CONTENT_RESULT: ${{ needs.content.result }}
        shell: bash
        run: |
          set -euo pipefail

          printf 'Tests: %s\n' "$TESTS_RESULT"
          printf 'Content: %s\n' "$CONTENT_RESULT"

          [[ "$TESTS_RESULT" == "success" ]]
          [[ "$CONTENT_RESULT" == "success" ]]
```

This workflow has no path filters or job-level change detection, so the proposed gate should be produced for every covered PR. The final job runs even when a dependency fails, is cancelled, or is skipped, and succeeds only when both required bodies of work succeed. If the entire workflow is skipped or never starts, its required result should remain missing rather than falsely passing.

The PR route executes repository scripts with a read-only token, no secrets, no cache, and no stored checkout credentials. It deliberately avoids `pull_request_target`.

The Python matrix covers the declared minimum and two later explicit minor releases without using a moving `3.x` target. The hosted qualification should confirm that these remain intended supported versions.

## Proposed `.github/workflows/codeql.yml`

```yaml
name: CodeQL

on:
  pull_request:
    branches:
      - main
  push:
    branches:
      - main
  # Supports later merge-queue qualification without enabling a queue.
  merge_group:

permissions:
  contents: read

concurrency:
  group: codeql-${{ github.event_name }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

jobs:
  analyze-python:
    name: CodeQL / Python
    runs-on: ubuntu-24.04
    timeout-minutes: 20
    permissions:
      contents: read
      security-events: write

    steps:
      - name: Check out source
        uses: actions/checkout@08c6903cd8c0fde910a37f88322edcfb5dd907a8 # v5.0.0
        with:
          persist-credentials: false

      - name: Initialize CodeQL
        uses: github/codeql-action/init@6c644eb19b8b47d83b2d77bdfd1bf142bcde947a # v3.28.17
        with:
          languages: python
          build-mode: none
          queries: security-extended

      - name: Analyze Python
        uses: github/codeql-action/analyze@6c644eb19b8b47d83b2d77bdfd1bf142bcde947a # v3.28.17
        with:
          category: /language:python
```

CodeQL is separate because it provides different evidence from unit and content validation. It does not validate instruction Markdown, manifest semantics, resource existence, or projection equality.

A successful CodeQL action normally establishes that analysis completed and results were uploaded; it does not by itself establish that the result contains no blocking findings. If the repository supports a code-scanning merge-protection rule, that rule should enforce the selected alert threshold after the initial results are reviewed. The threshold should not be guessed before the baseline and available controls are observed.

The full action SHAs above are candidate pins. Before committing them, verify each SHA against its annotated upstream release and current security guidance. The fixture supplies no ref-to-SHA evidence, and immutable pins should not be accepted from annotations alone. No automated update schedule is proposed because no Dependabot cadence has been selected; pin updates can use focused PRs until that decision is made.

## Python security contract to add to `tests/test_check.py`

The parser tests should establish these externally visible behaviors using its existing public entry points:

1. Manifest resource paths must be relative to the plugin root.
2. Absolute paths and paths containing an effective `..` escape are rejected.
3. Containment is checked after filesystem resolution, so a symlink cannot lead outside the plugin root.
4. Missing resources, directories where files are required, malformed JSON, and values of the wrong JSON type produce controlled validation errors rather than tracebacks.
5. Canonical and adapter manifests must compare structurally according to the project’s declared projection contract.
6. Diagnostics must not disclose unrelated host paths.
7. Valid nested resources such as `skills/editing/references/style.md` remain accepted.

The existing parser API and exception model are not present in the fixture, so inventing compilable test calls would make the proposal misleading. These cases should be implemented against the actual symbols in `src/prompt_linter/check.py`, with each test failing before its corresponding hardening change.

## Initial merge policy

After hosted qualification identifies the real check producers, configure the effective rule for `main` to:

- require changes through a pull request;
- require the observed result produced by the `CI / merge gate` job;
- require the observed CodeQL analysis result so analysis cannot silently disappear;
- use a supported code-scanning results rule for the selected alert threshold, if available;
- require the branch to be current with `main` before merging unless a qualified merge queue replaces that freshness mechanism;
- prevent branch deletion and non-fast-forward updates;
- preserve existing bypass and recovery actors until their actual configuration and intended use are reviewed.

Do not enter proposed job names into branch protection before observing their actual check-run contexts and producing GitHub App. Bind required checks to the GitHub Actions producer where the selected control supports that binding.

The approval count depends on the available people. A sole-maintainer route can use zero required approvals while retaining PR context and automated gates. Independent approval should be required only after an eligible reviewer is established.

A merge queue remains a separate decision. Both proposed workflows listen for `merge_group`, but that source preparation neither enables nor qualifies a queue.

## Hosted qualification

Later hosted work would need to establish all of the following on the final reviewed source revision:

1. **Capability and cost**
   - The repository is the intended public target.
   - Standard GitHub-hosted Linux runners and CodeQL advanced setup are available.
   - No paid runner, subscription change, secret, cache, or artifact storage is introduced.
   - The candidate action pins still identify approved upstream releases.

2. **Ordinary CI**
   - A same-repository PR produces every matrix job, content validation, and `CI / merge gate`.
   - An authorized fork PR receives no sensitive secrets or writable token and still produces the intended gate.
   - A push to `main` produces the same required evidence.
   - Logs show the documented unittest and validator commands running from the repository root.

3. **Causal gate behavior**
   - A controlled failing unit test makes the aggregate gate fail.
   - A controlled manifest or adapter drift makes the content job and aggregate gate fail.
   - Restoring each controlled fault on the same PR produces a successful gate on the new revision.
   - A cancelled, skipped, or absent dependency cannot make the aggregate gate succeed.

4. **CodeQL coverage**
   - Initialization, Python extraction, analysis, and SARIF upload complete for the intended PR and push events.
   - `security-extended` is present in the effective analysis configuration.
   - Fork behavior and permissions match the intended contributor route.
   - The recorded check context, category, producing App, analyzed commit, and source coverage match the proposed policy.

5. **Enforcement**
   - Effective repository, organization, and enterprise rules governing `main` are read together.
   - The required contexts are copied from observed check runs rather than inferred from YAML.
   - With neighboring requirements satisfied, a failed CI gate prevents the intended actor from merging.
   - The restored successful revision becomes eligible.
   - Code scanning blocks the chosen class of findings if that rule is selected; merely uploading CodeQL results is not treated as findings enforcement.
   - Bypass behavior is tested or explicitly left unclaimed.

6. **Merge queue, only if adopted**
   - Both workflows run on the queue’s temporary `merge_group` commit.
   - The queue waits for the same qualified results.
   - PR-only successes cannot substitute for missing merge-group results.

Until that evidence exists, the workflows are reviewable source proposals, and the merge rule is a configuration proposal rather than an established gate.