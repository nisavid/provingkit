# GitHub controls that work together

Use this guide when assessing or changing GitHub merge and branch controls. Start from the repository's policy and the user's intended workflow. Recommend defaults by their consequences; honor another informed configuration when it is supported and consistent with actual policy. A different preference is not a blocker. Identify the specific incompatible rule, unavailable capability, or concrete active harm when a requested result cannot safely work.

GitHub documentation was checked on 2026-10-08. Recheck feature availability and semantics when making a live change; these links own the product facts.

## Read the effective policy

Observe the target branch, repository owner and visibility, plan, authenticated actor, and permissions. Read applicable repository, organization, and enterprise rulesets, their targets, enforcement state, and bypass actors, together with classic branch protection. Multiple rulesets aggregate, including with the applicable classic protection rule; a more permissive local edit cannot cancel a stricter inherited requirement. Only one classic branch-protection rule applies at a time. Distinguish a visible rule from one this actor can edit. [Rule layering and availability](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets).

Determine whether the intended contributor, automation, and recovery actors can use the resulting route. Classic protection normally exempts administrators unless configured otherwise; ruleset bypass has its own actor and mode choices. Organization-only actor controls and plan-dependent features cannot be assumed for a personal or private repository. A permission or plan limitation calls for a supported alternative or a scoped handoff, not an automatic upgrade, paid-feature activation, or unrelated bypass change. [Classic protection permissions](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches), [ruleset bypass options](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository).

## Choose PR and review requirements for the people available

PRs provide a place for checks and review; required human approvals add an independent reviewer dependency. A sole maintainer can reasonably choose PRs with zero required approvals while retaining useful checks. A collaborating team can reasonably require an available independent reviewer, or choose zero approvals for its workflow. Direct updates may also be a supported, explicitly chosen route under repository policy. Explain the tradeoff and preserve the user's choice rather than assigning a universal approval count.

Check additional review constraints independently of that count:

- `CODEOWNERS` assigns review responsibility; enforcement requires the corresponding review rule. Use the file from the PR's base branch. Named users need write access; a named team must be visible and itself have write access. Resolve invalid entries and verify who can actually satisfy the rule. [Code owner eligibility and branch selection](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners).
- Dismissing stale approvals requires new review after qualifying changes. Requiring approval of the latest reviewable push requires an eligible approver other than its pusher. These choices affect update/rebase and bot workflows; they can strand work when no qualifying reviewer exists. Decide the usable reviewer or authorized exception route before enforcing them. [Review-rule consequences](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets).

## Bind required checks to working producers

Discover check names from actual runs or statuses on relevant commits, including matrix-generated names and their producing GitHub App where selectable. Workflow names, proposed job names, and an installed app are insufficient evidence that the required context is emitted. Prefer unambiguous names across workflows. Select the expected app when that matches the intended trust boundary; explain an informed choice to accept any source. [Required check sources](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).

Trace each selected check through its producer, event, target branches, paths, job conditions, dependencies, and expected commit. A required check must be reported on the relevant latest commit; an earlier success does not satisfy a new revision. Whole workflows skipped by path/branch filters or skip directives can leave checks pending, while skipped jobs can report success. Neither a missing context nor a skipped test demonstrates the test passed. [Required-check troubleshooting](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks), [skip semantics](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/skip-workflow-runs).

Where selective jobs are useful, consider a small consistently emitted gate that fails when a relevant dependency failed or was unexpectedly absent, and explicitly handles changes for which work is unnecessary. Observe its actual outputs before requiring it. Rename, delete, or retarget a producer and its consuming protection together; otherwise the branch may wait forever for an obsolete context.

## Align integration and history

Strict up-to-date checks test a branch that includes the current base, at the cost of rebuilds after other changes land. Loose checks reduce reruns but permit changes that were not tested together. Choose according to integration risk, throughput, and available CI capacity. [Strict and loose checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).

A merge queue tests integration with the current base and earlier queued work. Verify availability and event coverage before requiring it: Actions producers need `merge_group`, and external CI needs to report on the queue's temporary commits. PR-only successes cannot satisfy queue checks. [Merge queue CI requirements](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue).

Align allowed repository merge methods, the chosen queue strategy if any, and history rules. Linear history excludes merge commits and requires squash or rebase to be allowed. Squash can keep one logical change together; rebase can retain useful individual commits; merge commits can preserve branch structure when policy permits. These are choices, not universal settings. [Linear history and merge-method compatibility](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets).

## Reobserve after a change

Treat an assessment as tied to the observed repository settings and workflow/source revision. Changes to branch targets, inherited rules, bypass actors, permissions, review settings, check identities/events, queue configuration, or merge methods invalidate affected conclusions. Refresh those observations before applying a dependent plan.

After an authorized edit, read back the selected settings and effective rules, then inspect the downstream behavior that matters: the intended actor's merge eligibility, available reviewer route, actual checks on the relevant revision/event, and queue behavior if selected. Report separately what was configured, what was observed working, and what remains unverified. Preserve unrelated settings and concurrent work; a green settings response alone does not prove the merge path works.
