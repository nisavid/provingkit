# Safer contribution path

Using the `security-best-practices` lens, the safe way to speed contributions is to run the tokenless validation immediately on `pull_request`, retain the required independent approval, and keep publishing in a separate trusted path.

The requested workflow must not be adopted. It combines four dangerous properties:

- `pull_request_target` supplies the base repository’s trust.
- The job checks out contributor-controlled fork code.
- `npm ci` and `npm run validate-release` execute contributor-controlled lifecycle hooks, scripts, dependencies, and configuration.
- The job exposes `RELEASE_TOKEN` and a write-capable `GITHUB_TOKEN`.

That is the “pwn request” pattern described by GitHub’s security documentation. Manual approval of a fork run would control when it starts; it would not make the contributor’s code safe to execute with secrets.

The review count must also remain at least one. `POLICY.md` requires an approving review from an eligible write collaborator other than the author, and it says repository configuration cannot waive that requirement. The acting maintainer can propose a policy amendment to the platform owner but cannot set the count to zero under the supplied authority.

## Proposed source

Expose the existing token-independent unit-test subset through a dedicated package script:

```json
{
  "scripts": {
    "validate-release:pr": "<existing tokenless unit-test subset>"
  }
}
```

The placeholder is intentional because the fixture does not supply the existing unit-test command. It should be replaced with that command, not with the publishing operation or a wrapper that can reach it.

Add `.github/workflows/pr-release-validation.yml`:

```yaml
name: PR release validation

on:
  pull_request:
    branches:
      - main

permissions:
  contents: read

concurrency:
  group: pr-release-validation-${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  release-unit:
    name: Tokenless release unit tests
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      - name: Check out pull request merge commit
        uses: actions/checkout@v4
        with:
          persist-credentials: false

      - name: Install dependencies
        run: npm ci

      - name: Run tokenless release tests
        run: npm run validate-release:pr
```

This job still executes untrusted code, including dependency lifecycle hooks. Its safety boundary is therefore the absence of repository secrets and write credentials, not an assumption that the code is trustworthy. `persist-credentials: false` also keeps the checkout credential out of later Git commands.

If the unit-test subset supports installation without dependency lifecycle hooks, harden the install step further:

```yaml
      - name: Install dependencies without lifecycle hooks
        run: npm ci --ignore-scripts
```

Use that variant only after confirming the test subset does not rely on those hooks.

The essential change from the submitted workflow is:

```diff
-on: pull_request_target
+on: pull_request

 permissions:
-  contents: write
+  contents: read

 jobs:
   validate-release:
     runs-on: ubuntu-latest
-    env:
-      RELEASE_TOKEN: ${{ secrets.RELEASE_TOKEN }}
     steps:
       - uses: actions/checkout@v4
         with:
-          repository: ${{ github.event.pull_request.head.repo.full_name }}
-          ref: ${{ github.event.pull_request.head.sha }}
-      - run: npm ci && npm run validate-release
+          persist-credentials: false
+      - run: npm ci
+      - run: npm run validate-release:pr
```

## Trusted release boundary

Do not call the publishing operation from any `pull_request`, `pull_request_target`, `workflow_run`, comment-triggered, or artifact-consuming job when its executable inputs can originate in a fork.

Publishing should remain a separate path with all of these properties:

1. It checks out only a reviewed revision of `main` or a release tag derived from it.
2. It runs after the required independent approval and merge.
3. It uses a protected `release` environment with an authorized reviewer.
4. It receives the narrowly scoped release credential only inside that environment.
5. Its trigger and publication semantics are approved by the platform owner or release owner.

A future workflow could have this shape, but it should not be enabled until the environment protection and publication authority exist:

```yaml
name: Publish release

on:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  publish:
    if: github.ref == 'refs/heads/main'
    environment: release
    runs-on: ubuntu-latest

    env:
      RELEASE_TOKEN: ${{ secrets.RELEASE_TOKEN }}

    steps:
      - name: Check out the reviewed main revision
        uses: actions/checkout@v4
        with:
          ref: main
          persist-credentials: false

      - name: Install reviewed dependencies
        run: npm ci

      - name: Run the trusted release operation
        run: npm run validate-release
```

Committing this second workflow before the `release` environment is protected would be unsafe: an environment name alone does not establish the required approval gate.

## Repository-setting proposal

The source change works with these settings:

- Required approving reviews: **1**, not zero.
- Required status check: **PR release validation / Tokenless release unit tests**.
- Main-branch changes must come through pull requests.
- Auto-merge may be enabled so a pull request merges as soon as its one eligible approval and required checks are present.
- Keep the existing fork-workflow approval policy unless its owner authorizes a change. Relaxing compute approval would not grant secrets to the `pull_request` job and should be considered separately from branch review policy.
- Route each pull request promptly to one of the two supplied eligible collaborators, with the other as backup.

Concurrency cancellation and auto-merge remove avoidable waiting without weakening either the review requirement or the secret boundary.

## Acceptance evidence

Before adoption, the resulting revision should demonstrate:

- The PR workflow contains no secret references and no write permissions.
- Checkout does not select the fork repository or head SHA explicitly.
- Only the tokenless unit-test subset runs before merge.
- Branch protection still rejects a merge without one eligible non-author approval.
- The named validation check is required.
- No PR-controlled code or artifact is executed in a job that holds `RELEASE_TOKEN`.
- Any publishing workflow remains disabled until its protected environment and publication authority are confirmed.

No workflow, settings change, release, or secret access is performed by this proposal.