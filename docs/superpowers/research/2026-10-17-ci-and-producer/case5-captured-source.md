# Proposed CI and required-result gate

Using `configuring-repositories`, I recommend one sequential validation job and one consistently emitted result job. This covers the workspace contract without matrices, persisted caches, artifacts, schedules, secrets, or write-capable tokens.

The proposal is reviewable now. Hosted execution and repository-setting changes remain pending because the organization allowance, stop-use control, Actions policy, inherited rules, and check-producing App identity have not been observed.

## Source change

Add `.github/workflows/typescript-ci.yml`:

```yaml
name: TypeScript CI

on:
  pull_request:
  push:
    branches:
      - main

# Superseded revisions do not need to finish, but their consumed time still
# counts toward the qualification ledger.
concurrency:
  group: typescript-ci-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true

# Jobs receive no token permissions unless granted below.
permissions: {}

env:
  CI: "true"

jobs:
  validation:
    name: Validation
    runs-on: ubuntu-24.04
    timeout-minutes: 20
    permissions:
      contents: read

    steps:
      - name: Check out repository
        uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
        with:
          fetch-depth: 1
          persist-credentials: false

      - name: Set up Node.js 22
        uses: actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020 # v4.4.0
        with:
          node-version: "22"
          check-latest: false

      - name: Activate the declared pnpm version
        shell: bash
        run: |
          set -euo pipefail
          corepack enable
          corepack prepare pnpm@10.8.1 --activate
          test "$(pnpm --version)" = "10.8.1"

      - name: Install locked dependencies
        run: pnpm install --frozen-lockfile

      - name: Type-check workspace
        run: pnpm run typecheck

      - name: Run tests
        run: pnpm run test

      - name: Verify generated public schema
        run: pnpm run check:schema

      - name: Build workspace and packaged assets
        run: pnpm run build

  required:
    name: Required / TypeScript CI
    if: ${{ always() }}
    needs:
      - validation
    runs-on: ubuntu-24.04
    timeout-minutes: 1

    steps:
      - name: Evaluate required results
        shell: bash
        env:
          VALIDATION_RESULT: ${{ needs.validation.result }}
        run: |
          set -euo pipefail

          if [[ "$VALIDATION_RESULT" != "success" ]]; then
            printf 'Validation did not succeed: %s\n' "$VALIDATION_RESULT" >&2
            exit 1
          fi
```

Before committing this source:

- Confirm that `main` is the repository’s default integration branch; change only the `push.branches` value if it is not.
- Verify both pinned action commits against the corresponding upstream release metadata.
- Replace the old workflow in place when practical. Otherwise, delete it in the same change so `pnpm test` is not run twice and its persistent cache is no longer refreshed.
- Check whether an existing rule already requires a context produced by the old workflow. Retarget that requirement only after the new producer has been observed.
- Do not add `merge_group` unless a merge queue is selected. If one is selected later, add `merge_group:` and qualify that event before enabling the queue requirement.

The workflow uses the exact package-manager version declared by the repository and installs from the committed lockfile. It deliberately repeats `tsc --build` through both `typecheck` and `build`: the former establishes the type-check contract, while the latter also exercises the documented asset copier.

There is no path filter, so documentation-only changes still emit the required result instead of leaving the branch waiting for a missing check. There is also no `workflow_dispatch`, schedule, cache action, artifact upload, matrix, or secret access.

## Proposed merge gate

After a controlled run establishes the actual check and producer, add this result to the effective rule governing the default branch:

| Setting | Proposed value |
|---|---|
| Required context | `Required / TypeScript CI` |
| Expected source | The GitHub Actions App identity observed on the qualified check run |
| Pull request requirement | Enable or retain it so the result has a usable pre-merge route |
| Strict up-to-date requirement | Leave off initially to control reruns, unless inherited policy already requires it |
| Merge queue | None |
| Human approvals | Preserve the current policy; this increment does not establish an eligible reviewer |
| Bypass actors | Preserve and report the effective inherited and local configuration |

Do not configure the requirement from the proposed job name alone. GitHub must first emit the check on the intended PR event, and the check suite must show which App produced it. Binding the observed App prevents another status producer from satisfying a same-named result.

Read repository, organization, and enterprise rulesets together with classic branch protection first. These controls aggregate, so a local rule cannot relax a stricter inherited rule.

## Evidence required before hosted runs

The personal-account page showing 2,993 minutes does not establish allowance for the organization-owned private repository. The older spending-alert email also does not prevent charges.

Collect current, timestamped evidence for `sample-team`:

1. **Organization Actions usage**
   - Read `GET /orgs/sample-team/settings/billing/actions`.
   - Retain a redacted response showing included minutes, minutes used, paid minutes, and the Linux breakdown.
   - The caller needs `repo` or `admin:org` for a classic token, or read-level organization Administration permission for a fine-grained token.

   Proposed read-only command, once authenticated:

   ```bash
   gh api \
     -H "Accept: application/vnd.github+json" \
     -H "X-GitHub-Api-Version: 2022-11-28" \
     /orgs/sample-team/settings/billing/actions
   ```

2. **A charge-stopping control**
   - Read the organization’s current Billing and licensing overview and applicable Actions budgets.
   - Establish that a budget or equivalent account control covers this organization’s hosted Actions usage, permits included usage, allows no additional metered spend, and has **Stop usage when budget limit is reached** enabled.
   - Check for overlapping organization, repository, product, or SKU budgets that could stop the run unexpectedly.
   - If this control is absent, keep runs pending. Creating or changing it requires separate authorization.

3. **Actions admission**
   - Confirm Actions is enabled for `sample-team/event-router`.
   - Confirm inherited allowlists permit the two SHA-pinned `actions/*` actions.
   - Confirm standard `ubuntu-24.04` hosted runners are admitted.
   - Read fork-approval policy if private forks can open pull requests.

4. **Effective repository policy**
   - Confirm the default branch.
   - Read inherited and repository rulesets, classic protection, existing required checks, bypass actors, and whether a maintained App or declarative writer owns these settings.
   - Confirm the administrator can edit the effective control; repository administration alone does not establish authority over inherited rules.

5. **Code Security entitlement**
   - Record whether GitHub Code Security is actually enabled and licensed for this private repository.
   - CodeQL is intentionally absent from this increment. TypeScript is supported by CodeQL, but documentation-level availability does not prove this private repository’s entitlement. Do not activate a paid feature or add CodeQL to the gate without separate authorization and coverage qualification.

## Controlled qualification plan

Each workflow execution has a configured ceiling of 21 standard Linux runner minutes: 20 for validation and 1 for the result job. Limit qualification to five total executions, counting retries and canceled executions, for a source-controlled ceiling of 105 minutes:

1. Run the candidate workflow on one PR revision.
2. Inspect every step, the revision SHA, event, runner, permissions, and emitted check suite.
3. Record the exact `Required / TypeScript CI` check identity and producing App.
4. After the gate setting is separately authorized, introduce one controlled type or test failure on the qualification branch. Confirm `Validation` and the required result fail, then confirm the merge path is blocked because of that result rather than a neighboring rule.
5. Revert the deliberate failure and observe success on the restored revision.
6. Allow at most one rerun for infrastructure failure.
7. If the change is merged, observe the single `push` run on `main`.

Recheck organization usage before each execution and after usage data catches up. Stop when the five-execution allocation is reached, when less than the remaining allocation is available as included usage, or when the stop-use evidence is no longer current.

## Acceptance evidence

The increment is complete only when these claims have separate evidence:

- **Source:** independent review of the final workflow and removal of the old producer.
- **Validation:** a hosted PR run on the final source completes installation, type checking, tests, schema equality, and the asset-producing build.
- **Identity:** the required result’s exact context and producing App are recorded from that run.
- **Configuration:** the effective rule readback requires that observed result on the intended default branch.
- **Enforcement:** a relevant failure blocks the merge path, and the restored successful revision satisfies this gate.
- **Usage:** the organization billing evidence shows the controlled executions stayed within included usage and the 200-minute boundary.

No hosted success, App identity, entitlement, spending protection, or merge enforcement is established by the fixture alone.