# Controlled TypeScript CI proposal

This adds a manually dispatched workspace check and one stable required-result gate without schedules, persistent caches, artifacts, or automatic executions. I’m applying `capturing-agent-procedures` to keep the later admission, run, and gate-enablement steps repeatable.

No workflow was run, and no repository, organization, billing, or ruleset setting was changed.

## Proposed workflow

Replace the old push-only workflow rather than leaving both enabled:

```yaml
# .github/workflows/ci.yml
name: Controlled CI

on:
  workflow_dispatch:
    inputs:
      expected_sha:
        description: Full commit SHA authorized for this run
        required: true
        type: string

permissions:
  contents: read

concurrency:
  group: controlled-ci
  cancel-in-progress: true

env:
  CI: "true"
  COREPACK_ENABLE_DOWNLOAD_PROMPT: "0"

jobs:
  workspace:
    name: CI / workspace checks
    runs-on: ubuntu-24.04
    timeout-minutes: 20

    steps:
      - name: Confirm authorized revision
        env:
          EXPECTED_SHA: ${{ inputs.expected_sha }}
        run: |
          if [[ ! "$EXPECTED_SHA" =~ ^[0-9a-f]{40}$ ]]; then
            echo "::error::expected_sha must be a full lowercase commit SHA"
            exit 1
          fi

          if [[ "$EXPECTED_SHA" != "$GITHUB_SHA" ]]; then
            echo "::error::Dispatched SHA does not match the authorized SHA"
            printf 'authorized=%s\ndispatched=%s\n' "$EXPECTED_SHA" "$GITHUB_SHA"
            exit 1
          fi

      - name: Check out the authorized revision
        uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
        with:
          ref: ${{ github.sha }}
          persist-credentials: false

      - name: Set up Node.js 22
        uses: actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020 # v4.4.0
        with:
          node-version: "22"

      - name: Activate the declared pnpm version
        run: |
          corepack enable
          corepack prepare pnpm@10.8.1 --activate
          test "$(pnpm --version)" = "10.8.1"

      - name: Install the locked dependency graph
        run: pnpm install --frozen-lockfile

      - name: Check the generated public schema
        run: pnpm run check:schema

      - name: Type-check the workspace
        run: pnpm run typecheck

      - name: Run tests
        run: pnpm run test

      - name: Build packages and copy documented assets
        run: pnpm run build

  required:
    name: CI / required
    if: ${{ always() }}
    needs:
      - workspace
    runs-on: ubuntu-24.04
    timeout-minutes: 1

    steps:
      - name: Require every workspace check to pass
        env:
          WORKSPACE_RESULT: ${{ needs.workspace.result }}
        run: |
          if [[ "$WORKSPACE_RESULT" != "success" ]]; then
            echo "::error::Workspace checks concluded: $WORKSPACE_RESULT"
            exit 1
          fi
```

Before merging this source, independently compare both 40-character action hashes with the named releases in the official `actions/checkout` and `actions/setup-node` repositories. This exercise did not fetch their upstream refs.

Any future required job must be added to `required.needs` and checked by the gate. Otherwise, that job would not affect `CI / required`.

## Why dispatch remains manual

Automatic `pull_request` or `push` triggers cannot enforce a lifetime allowance of 200 minutes. Repository source can cap each job, but it cannot cap the number of dispatches or reruns.

This workflow reserves at most:

- 20 minutes for workspace checks
- 1 minute for the gate
- **21 standard Linux minutes per started attempt**

Authorize one initial attempt and, if needed, one retry: **42 minutes maximum**. Count canceled and rerun attempts against that reservation. Do not enable automatic triggers under the present authorization.

If the spending boundary later changes, the event block can be extended with `pull_request`. Add `merge_group: { types: [checks_requested] }` only if a merge queue is actually selected.

## Account evidence required before a hosted run

The personal balance of 2,993 minutes does not establish the private organization repository’s allowance. The older spending-alert email is also not current admission evidence.

| Evidence | Acceptance condition |
|---|---|
| Organization Actions billing summary | A current response for `sample-team` shows at least 42 uncommitted included minutes for the planned attempt and retry. Record the retrieval time, included minutes, total minutes used, paid minutes used, and Linux breakdown. |
| No-paid-use control | An existing applicable organization, enterprise, or repository budget/spending control must block paid Actions usage after included usage is exhausted. If the current configuration permits billed overflow, do not run; changing it is outside this authorization. |
| Competing organization usage | Confirm that other organization workflows will not consume the reserved included minutes during the controlled window. Recheck before a retry. |
| Actions admission | Confirm that GitHub Actions and standard GitHub-hosted Linux runners are allowed for this private repository and that organization policy admits the two pinned GitHub-owned actions. |
| Default branch and inherited rules | Record the actual default branch and all inherited organization or enterprise rulesets, required checks, bypasses, and expected check sources before proposing a repository rule change. |
| Existing workflow | Confirm the old push workflow is removed or disabled so the controlled change cannot trigger both workflows. |
| Source provenance | Verify the immutable action hashes and confirm that public npm registry access is permitted. No registry credential should be needed because all dependencies are public. |

The supplied official endpoint can provide the organization usage summary:

```bash
gh api /orgs/sample-team/settings/billing/actions
```

It requires suitable organization billing visibility: a classic token with `repo` or `admin:org`, or a fine-grained token with read access to organization Administration. Do not store or paste the token into workflow source or evidence.

The baseline does not use CodeQL, dependency review, or another GitHub Code Security feature. Code Security entitlement is therefore not a prerequisite for this run. Confirm entitlement and its billing effect before adding those checks; do not activate an entitlement as part of this work.

## Controlled-run procedure

1. Review the workflow and remove the old workflow.
2. Obtain the account evidence above.
3. Start a minute ledger at zero. Reserve 21 minutes for the attempt before dispatching it.
4. Dispatch `Controlled CI` for the intended branch and provide its full head SHA as `expected_sha`.
5. Accept only a run whose `github.sha`, checked-out revision, and supplied SHA match.
6. Record the run ID, attempt number, conclusion, billed-minute delta, and cumulative reserved minutes.
7. Permit at most one retry under this proposal. Recheck the organization balance first and reserve another 21 minutes.
8. Stop if the cumulative reservation would exceed 200 minutes, the paid-use block is absent, or account evidence has become stale.

GitHub’s supplied billing documentation says reruns count toward usage and billing is rounded to whole minutes, so a retry is a new ledger entry rather than a continuation of the first attempt.

## Required-result rule

Configure the rule only after a controlled run has produced the check. No current check run or producing App identity was supplied.

From the successful commit, collect the gate’s producer:

```bash
SHA="<successful-full-sha>"

gh api \
  -H "Accept: application/vnd.github+json" \
  "/repos/sample-team/event-router/commits/$SHA/check-runs" \
  --jq '
    .check_runs[]
    | select(.name == "CI / required")
    | {
        name,
        status,
        conclusion,
        head_sha,
        app: (.app | {id, slug, name})
      }
  '
```

Then propose, for the actual default branch:

- Require exactly `CI / required`.
- Bind it to the observed GitHub Actions App identity where the ruleset supports an expected source.
- Do not require `CI / workspace checks` separately; the gate owns that dependency.
- Do not alter inherited checks, bypass actors, strict-update behavior, or merge-queue settings without first reviewing the inherited rule details.
- Confirm on a non-protected test branch that a manual dispatch for the latest PR head is recognized as the required check before applying the rule to the default branch.

The next authorized action is account evidence collection. A hosted dispatch or required-check mutation should wait until that evidence establishes included capacity, no paid overflow, Actions admission, and the inherited rule shape.