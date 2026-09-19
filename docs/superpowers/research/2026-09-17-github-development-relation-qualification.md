# GitHub Development relation qualification

The Issue repository's auto-close setting controlled closure in the live reciprocal cross-repository tests. With that setting disabled, manual and description-derived Development links remained visible in both API directions and in GitHub's UI, while the tested merges left the target Issues open. Adding a manual link to an already-merged PR left an open Issue open under both enabled and disabled settings.

## Scope and evidence

These are observed GitHub.com results from 2026-09-17 using the repository owner/admin account in two newly created private, isolated fixture repositories. They are separate from the selected historical project corpus. All experimental writes were confined to the fixture repositories. The observations qualify native relation operations and setting interaction; they do not qualify a future Mergecraft implementation or historical PR-body publication.

The research input is `docs/superpowers/research/2026-09-17-github-development-relations.md` at `3981ee1bf639a7b5e171b5f80ac9b33f9f891331`. The policy input is [Choose Issue–PR relation maintenance and closure policy](https://github.com/nisavid/provingkit/issues/88#issuecomment-5720983110). Fixture repositories, Issues, PRs, commits, and branches remain retained as private evidence.

The coordinator observed the documented Settings checkbox through authenticated GitHub UI. Phase 1 had both fixture repositories enabled, verified at 20:49:40 UTC. Phase 2 had fixture A disabled and fixture B enabled, verified at 21:03:04 UTC after saving and reloading A. No private settings API was used. The UI settings observation and the native relation result are separate evidence.

Every relation observation read both `PullRequest.closingIssuesReferences` and `Issue.closedByPullRequestsReferences(includeClosedPrs: true)`, with independent all/manual/detected filters. Connections used two-item pages to exercise pagination and consumed every page. The native mutation requests used freshly observed fixture IDs. Each tested write retained its response and before/after state; expected negative results were reconciled through rereads.

## Supported observations

| Case | Observed result |
| --- | --- |
| Add already-merged, default-base PR to open Issue; enabled | Mutation succeeded; Issue remained open immediately and after a subsequent unrelated default-branch merge. Both directions contained one manual edge. |
| Same historical manual add; disabled | Mutation succeeded; Issue remained open, and both directions contained the manual edge. |
| Manual add to draft default-base PR | Succeeded, with manual provenance and no state change. |
| Manual add to draft non-default-base PR | Succeeded, with manual provenance and no state change. |
| Manual add to closed-unmerged non-default-base PR | Succeeded; `includeClosedPrs: true` preserved the issue-side observation. Reopening retained the link. |
| Closed Issue manual addition, removal, and readdition under disabled | All succeeded against a merged PR; the Issue stayed closed, and its independent detected edge stayed present. |
| Two distinct PR IDs added to one Issue | Both manual edges appeared. Removing the same two IDs removed both. |
| Repeated add containing duplicate PR IDs | Succeeded with no duplicate edges or state change. |
| Mixed valid PR IDs and an Issue ID supplied as a PR ID | `NOT_FOUND`; neither valid candidate edge appeared in the following complete reread. |
| Remove description-detected edge | `UNPROCESSABLE`: GitHub required editing the PR body instead. The edge remained. |
| Add an already description-detected edge manually | Successful no-op; manual-only filters stayed empty for that edge, and detected-only filters retained it. A subsequent manual-remove attempt still failed. |
| Remove a batch containing a manual edge and a detected edge | `UNPROCESSABLE`; both remained in the complete reread. This is one observed failure shape, not a general transaction guarantee. |
| Disable after relations already exist | Existing manual and detected relations remained visible in both directions. Closed Issues stayed closed. |
| Create manual and detected relations while disabled | Both appeared in both directions. Commit keywords still produced no containing-PR Development relation. |
| UI with disabled setting | Both Development sidebars showed the tested links after asynchronous page loading settled. Generic sidebar/timeline text still described closure; that text did not establish the actual setting. |

The merge comparisons used separate target Issues for manual links, PR-description keywords, and commit-message keywords. Keyword-bearing original commits reached the target branch through a merge commit, so the commit-only target was not dependent on the PR description.

| PR repository setting | Issue repository setting | Base | Manual target | Description-keyword target | Commit-keyword target |
| --- | --- | --- | --- | --- | --- |
| Enabled | Enabled, same repository | Default | Closed | Closed | Closed |
| Enabled | Enabled, same repository | Non-default | Open | Open; no detected native edge | Open; no native PR edge |
| Disabled | Disabled, same repository | Default | Open | Open | Open |
| Disabled | Enabled, other repository | Default | Closed | Closed | Closed |
| Enabled | Disabled, other repository | Default | Open | Open | Open |

A separate ordinary `Refs` target remained open and had no native closing relation after the enabled default-branch merge. In every commit-only case, the containing PR remained absent from both native Development connections even where the Issue closed.

These reciprocal cross-repository results identify the Issue repository as the controlling setting surface for the tested manual, description-keyword, and commit-keyword paths. Looking up only the PR repository's setting would give the wrong answer in both mixed-setting cases.

## Reproducible qualification procedure

1. Bind the candidate operations, actor, separate private fixture ownership, and retained-evidence disposition. Confirm fixture names are absent before creating them; never adopt an existing repository silently.
2. Load the reviewed platform research. Use `checkpointing-and-publishing-git-work` for task-owned fixture commits and pushes, and `publishing-reviewable-prs` with `writing-reviewable-pr-descriptions` for fixture PR text and readiness. Use explicit `not-required` publication-review mode and an empty specialist list when the simple fixture prose does not need a review loop; make no clean-review claim.
3. Observe the documented repository setting in the UI, record the repository, value, and observation time, and wait for a verified setting phase before its dependent experiment. Keep approval and observed state distinct.
4. Use disjoint Issues for manual, description-keyword, commit-keyword, and ordinary-reference controls. Preserve keyword-bearing commits when testing their arrival at a base. Capture the pushed commit, PR lifecycle, and default/non-default base before mutation.
5. Bind each request to its own immutable request artifact. Read both native connections, with all/manual/detected provenance filters and `includeClosedPrs: true`; paginate fully. Recheck the exact Issue/PR identities before adding or removing. Save typed responses and full after-state, including Issue state. A failed or uncertain write requires observation before any new attempt.
6. Use reciprocal cross-repository fixtures with opposite settings to distinguish the controlling repository. Keep read-only observations separate from writes; parallel readers need independent request artifacts.
7. Retain the fixtures, method, request/response evidence, and dated supported-input matrix. Downstream consumers load this result and its reviewed revision before claiming native behavior. Production reconciliation need not repeat this deliberately thorough qualification read pattern on every edit.

## Limits and downstream qualification

The historical manual-link observations are dated evidence for the tested owner/admin GitHub.com cases, not an indefinite state-preservation warranty. They do not expand the accepted native-link policy or authorize explicit Issue closure. The tested lifecycle/base combinations do not establish every Cartesian combination. Existing closed Issues were not reopened by the tested relation additions.

No independent permission roles, organization restrictions, inaccessible cross-repository actors, GitHub Enterprise deployment, stale authorization, concurrency race at the forge, or post-send network-failure recovery was qualified. The negative batch results do not guarantee atomicity for every server failure. No artificial network interruption was injected, and no ambiguous remote write was retried.

A live two-distinct-PR batch was qualified. The documented maximum of ten PR IDs per add/remove request is separate from total PRs linked to one Issue and from the UI's documented ten-Issues-per-PR control limit. More than ten distinct PRs linked to one Issue was not tested. The separate cardinality result below bounds the observed Issue-per-PR behavior.

Historical closed/merged PR-body ledger edits were not tested. The current installed publisher cannot perform those edits, and this qualification did not bypass it. The implementation work must provide and qualify its historical relation-ledger publication mode through the owning writer/publisher before historical repair consumes that mode. Native-link support here is not that downstream publication qualification.

## Manual cardinality and result handling

The API accepted ten distinct manually linked Issues on one already-merged PR. Adding an eleventh returned `UNPROCESSABLE` with `Pull request exceeds manual reference limit`; the complete subsequent reads showed ten manual edges and no edge on the eleventh Issue. That Issue stayed open. This qualifies an API-enforced manual Issue-per-PR total in this fixture, not merely the documented UI limit. It says nothing about the total number of PRs linked to one Issue, and it does not test a detected-keyword cardinality limit.

The rejected eleventh-link response contained both non-null `data.addCloseIssueReferences` and an `errors` array. A consumer must inspect GraphQL errors and verify the requested post-state; non-null mutation data is insufficient to report success. The body ledgers still need to preserve every verified association when native capacity prevents a link.

The installed publication audit also binds open PR state. Each fixture had a verified canonical publication audit before merge; rerunning it after the authorized merge reported state drift. Independent final checks confirmed the same identities and byte-for-byte authored title/body, with recognized bot tails retained. This is an audit scope limit, not evidence that historical publication has been qualified.
