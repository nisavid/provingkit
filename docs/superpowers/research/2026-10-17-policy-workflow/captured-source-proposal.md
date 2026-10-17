I used the supplied `configuring-repositories` skill. The smallest safe increment is faster, token-free pull-request feedback while retaining the required independent approval.

## Practical constraints

- `POLICY.md` requires one approval from a write collaborator other than the author. The maintainer cannot set required approvals to zero without an authorized policy amendment.
- Two eligible collaborators exist, so the current requirement has a usable reviewer path.
- The proposed `pull_request_target` workflow is unsafe. It checks out contributor-controlled code and then runs `npm ci`, dependency lifecycle hooks, and a repository script while `RELEASE_TOKEN` and a write-capable `GITHUB_TOKEN` are available. That is the documented “pwn request” pattern.
- Approving a fork workflow run does not make its scripts or dependencies trusted.
- Release validation and publishing should not be part of untrusted fork CI. Publishing also remains outside the supplied authority.
- The fixture does not identify the command for the token-free unit-test subset or the project’s supported Node version. Those must be bound to the actual manifest before this source is committed.

## Proposed contribution path

1. Keep one required approving review on `main`.
2. Run the token-free unit subset on `pull_request`, with read-only permissions and no secrets.
3. Cancel superseded runs so contributors receive current feedback sooner without spending time on obsolete revisions.
4. Keep publishing in a separate trusted workflow that executes only reviewed code. Do not pass `RELEASE_TOKEN` to installation or ordinary validation steps.
5. Require the new PR check only after an actual fork run proves that it emits a stable result on every covered change.

### `.github/workflows/pr-validation.yml`

```yaml
name: PR validation

on:
  pull_request:
    branches:
      - main

permissions:
  contents: read

concurrency:
  group: pr-validation-${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  unit:
    name: Token-free unit tests
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      # Keep the repository's supported Node setup here if one already exists.
      # Pin third-party actions to repository-approved full commit SHAs when
      # those pins are available.
      - name: Check out the pull request merge revision
        uses: actions/checkout@v4
        with:
          persist-credentials: false

      - name: Install dependencies
        run: npm ci

      - name: Run token-free unit tests
        run: npm run test:unit
```

`test:unit` is the proposed stable CI entry point. Its `package.json` value should delegate to the existing token-free subset; the fixture does not supply that command, so inventing its implementation would be unsafe.

No `RELEASE_TOKEN` should appear in this workflow. Although contributor-controlled lifecycle hooks and tests still execute, they run in GitHub’s restricted `pull_request` context rather than a privileged context.

## Trusted-release boundary

The existing release operation should remain separate unless its trigger and authorization are explicitly settled. Its source should satisfy this contract:

```yaml
# Trusted release workflow contract, not an authorized publishing change:
#
# - Trigger only from reviewed code on main or an approved release reference.
# - Use an environment such as "release" if the repository uses protected
#   deployment environments.
# - Set top-level permissions to `contents: read` unless publishing requires
#   a narrowly identified additional permission.
# - Run installation and token-free validation without RELEASE_TOKEN.
# - Expose RELEASE_TOKEN only to the final trusted publishing step.
# - Never download, check out, or execute fork code or fork-produced artifacts.
```

For example, the secret boundary around the final step should look like this once the repository’s real trusted publish command is confirmed:

```yaml
- name: Install dependencies
  run: npm ci

- name: Validate reviewed release source
  run: npm run validate-release

- name: Publish
  run: npm run <confirmed-trusted-publish-script>
  env:
    RELEASE_TOKEN: ${{ secrets.RELEASE_TOKEN }}
```

The placeholder must not be committed as written. The publishing trigger, command, environment protection, and required token permissions need an authorized release decision.

## Settings proposal

Leave the `main` review rule at one required approval. To reduce waiting without weakening it:

- route review requests promptly to either eligible collaborator;
- make the token-free unit result visible before human review;
- cancel stale CI revisions;
- consider requiring `Token-free unit tests` only after observing its exact emitted check name and fork coverage.

Reducing approvals to zero remains a policy proposal for the platform owner, not a repository setting the acting maintainer can apply.

## Acceptance evidence for a later authorized implementation

- A fork pull request runs the unit subset without receiving repository secrets.
- The checkout uses the pull-request merge revision and does not persist credentials.
- A failing unit test produces a failing check on the current PR revision.
- A superseding push cancels the obsolete run and starts a new one.
- `main` still rejects a change without one eligible non-author approval.
- No release or registry publication occurs from the PR workflow.
- Any later release workflow runs reviewed source and exposes the release token only to its publishing step.

This proposal is based on the supplied source and GitHub’s documented `pull_request_target` risk guidance; it has not been applied or exercised against a live repository.