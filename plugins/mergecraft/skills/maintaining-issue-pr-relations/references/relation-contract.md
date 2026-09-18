# Issue–PR Relation Contract

Apply the [accepted relation policy](https://github.com/nisavid/provingkit/issues/88#issuecomment-5720983110)
within the [2026-09-17 GitHub.com qualification](https://github.com/nisavid/provingkit/blob/6cc33a584589125fe06bd9ac8f381aa8005efcba/docs/superpowers/research/2026-09-17-github-development-relation-qualification.md).

## Qualify The Contribution

Bind the Issue contract to concrete PR work and record the supporting source.
Use a role such as implementation, partial implementation, research,
qualification, or follow-up when it explains the contribution. A dependency,
background citation, shared topic, or incidental mention remains a reference
unless the work itself advances that Issue's scope.

For example, a PR that implements one backend for an Issue requesting three
backends is a partial implementation. A PR that merely depends on that Issue's
eventual result is not a contribution. Research can contribute when the Issue
requires the decision or evidence that the PR supplies.

Keep historically supported contributions when an Issue's scope changes. Name
the earlier role and bind evidence for the earlier contract; do not imply that
the PR satisfies today's scope or gates. If that contract is only inferred,
leave the association ambiguous. Existing native relations are evidence of an
association, not automatic semantic truth or permission to remove them.

Choose semantic intent separately from native effects:

- `ensure`: retain the evidenced contribution in both ledgers and plan the
  native association permitted by closure policy and capacity.
- `unlink-native`: remove authorized native closing intent while retaining the
  evidenced contribution in both ledgers. A closure-policy limitation does not
  erase contribution history.
- `withdraw`: remove a mistaken or no-longer-applicable association, binding
  the corrective evidence and separately authorized body spans. Superseded
  work, a historical role, or changed Issue status alone is not withdrawal
  evidence.

Use stable repository-qualified entity URLs in each body's ledger. Link to the
PR from the Issue and to the Issue from the PR. Keep annotations short and
specific; omit copied titles, open/closed state, and merge status. Preserve
every supported pair, even when native capacity or closure policy prevents a
native link. Before exposing a private cross-repository peer, bind the allowed
disclosure boundary; an authorized local read is not publication authority.

## Native Links And Closure

GitHub Development links may participate in Issue closure. The **Issue
repository's** auto-close setting controls the tested cross-repository paths.
Setting policy, observation, and authority to change a setting are separate.
The observation field `auto_close:false` means disabled; `auto_close:true` means
enabled.

| Proposed native addition | Required evidence |
| --- | --- |
| Partial contribution | A usable observation that Issue auto-close is disabled. |
| Complete contribution, enabled or unknown setting | Evidence that the triggering merge satisfies the Issue's completion gates. |
| Complete contribution, disabled setting | Verified contribution and ordinary mutation authority; no automatic closure claim. |

When a partial native link is unsafe or unavailable, keep both body entries and
report the native limitation. A known complete fix needs no setting lookup
solely to establish link safety. Historical manual additions were observed to
leave Issue state unchanged, but that dated behavior does not expand this
policy. Relation repair contains no explicit Issue close/reopen operation.

With auto-close disabled, completion remains an explicit Issue-workflow step.
After verified merge, carry any candidate Issue completions back to the ongoing
task. Its Issue owner checks the Issue's own current gates and closes it only
within the task's existing authority, then verifies the resulting state. A
deployment, acceptance, or additional-PR gate keeps the Issue open. Partial
contributions and historical relation repair do not create closure work merely
because a PR is merged.

Offer disabling auto-close only when a useful native link is actually blocked
and there is no settled decision to keep it enabled. Ask once when that choice
is unknown; require the repository's authorized maintainer to approve any
setting change. Respect a decision to keep it enabled; do not repeatedly ask.
Without setting-change authority, continue under enabled-mode limits. Prepare
a maintainer handoff only if wanted. An
approval is not an observation: any separately authorized setting change must
be verified before dependent links proceed. Installation changes no settings
and contacts no maintainers.

## Setting Observation Lifetime

Key records by forge host and stable **Issue repository ID**; retain the current
routing name separately. Store the observed boolean, evidence source, original
observation time, and cache provenance separately from policy and permissions.
Generic sidebar or timeline closure wording is not a setting observation. The
qualified surface is the authenticated repository Settings UI. Observe the
persisted checkbox state after reload; a save acknowledgment alone or its
absence does not establish the value. If unavailable, record the unavailable
attempt and use enabled-mode limits.

Reuse the selected observation throughout the whole agent task, including
resumes. Cross-task expiry does not expire an already selected task observation.
Any later dependent action in the same task, including its first native write,
reuses that selection unless an explicit invalidation occurs. Merely needing
the value later is not an invalidation. The helper owns cache selection and
expiry; callers consume its result instead of recalculating freshness.
For a new task, use a persistent 30-day TTL from the original observation by
default, with configurable TTL or explicit no-expiry. A cache hit never renews
the observation timestamp.

Only when a proposed effect needs the setting, acquire a missing or expired
observation once per repository for that task and share it across the batch.
Record unavailable attempts too. Explicit refresh, a newly observed setting
change, or contradictory behavior invalidates the affected cached state and
plans; reacquire before continuing a dependent effect. Do not poll, refresh on
every resume, or claim a cached value is newly verified. Report it as last
observed and retain the possibility of an unobserved later change.

An unavailable attempt is memoized for its task. It is not a confirmed value
for another task's persistent cache; a later task may request the setting once
when it needs it.

## Preserve Text And Publication Ownership

The generic Issue Markdown writer receives the complete current body, exact
authorized ledger span, contribution entries, and retain/replace dispositions.
It returns complete candidate bytes, preserving line endings and the terminal
newline. The Issue-body actuator consumes those bytes opaquely. A missing clear
span returns to the writer; it does not justify a new Markdown parser.

When normal PR creation or text publication is already pending, include ledger
intent in that writer/publisher handoff. After that owner verifies publication,
observe the resulting PR and build a fresh relation plan. Supply the writer's
unchanged-body decision for its already-correct ledger, so that plan requires
no second PR edit. Keep the canonical receipt in the lifecycle context;
`publication_results` accepts only the separate ledger publisher's receipts.

A standalone ledger edit goes through the existing PR writer and the
publisher's `pr-relation-ledger-write` operation. Bind forge, repository and PR IDs,
number/URL, exact live title/body digests and state, authorized UTF-8 byte span
and its preimage, replacement bytes, and complete writer-owned candidate body.
Historical ledger-only mode needs neither a surviving branch nor reconstructed
Diff navigation. It preserves title/state and all other authored content and
yields a relation-publication receipt, not readiness or canonical-navigation
evidence. A lifecycle caller requiring canonical publication evidence must
establish it through the normal owner after any body change.

For a standalone ledger edit, the caller performs publication after this
procedure returns the handoff, then resumes reconciliation with its bound
ledger-publication result. Verify live identity, body,
title, and state against that result before dependent effects. Never infer
success merely from a publisher status string or invoke the publisher again
from inside reconciliation. A changed preimage requires a fresh plan and new
authorization for its effects.

## Native Provenance, Capacity, And Recovery

Observe complete required `closingIssuesReferences` and
`closedByPullRequestsReferences(includeClosedPrs: true)` connections, preserving
all/manual/detected provenance and pagination evidence. Reuse complete,
compatible supplied observations; acquire only the missing connections needed
by the plan. A description-detected edge remains detected after a no-op manual
add. Removing that edge requires the owning PR content handoff. Commit closing
keywords can close an Issue without creating a containing-PR Development edge;
absence of a native edge does not settle merge consequences.

If a detected reference lies outside the authorized ledger span, return a
separately scoped PR-content handoff instead of widening the ledger edit.
Commit-message changes belong to the Git owner. Report those unresolved merge
consequences without pretending a manual-native removal repaired them.

The live GitHub.com qualification observed a cap of ten manually linked Issues
per PR and an input limit of ten PR IDs per native mutation. These are distinct
limits. Preserve existing valid links and require explicit selection when new
additions exceed remaining capacity; retain all body entries and report each
omitted native link. No total PRs-per-Issue cap or detected-link cap was
qualified. Do not silently evict existing links or select an arbitrary ten.

Bind explicit add/remove effects to qualified pairs and authority. Reject wrong
entity kinds or IDs, incomplete required pagination, stale affected preimages,
and unbound effects. Inspect GraphQL errors even when mutation data is non-null;
then reread the requested post-state. Preserve unrelated native edges.

Report each verified, failed, partial, or unknown effect. A timeout after a
possible mutation requires observation before any further attempt. Replan only
remaining authorized work against that observation; do not replay a whole batch
or promise transactionality across bodies, links, or repositories.

## Evidence Boundary

The platform qualification covers dated owner/admin GitHub.com cases, including
manual links on selected draft, open, closed, and merged PRs; disabled-setting
visibility; reciprocal cross-repository closure behavior; and cardinality and
provenance failures. It does not qualify every lifecycle/base combination,
permission role, organization restriction, inaccessible peer, GitHub Enterprise
deployment, concurrent race, or post-send network failure.

Keep unsupported cases explicit and obtain the evidence needed for their next
effect. Native-link qualification does not qualify historical body publication;
that route uses its own publisher evidence. Separate local command verification
from live platform behavior and state exactly what each receipt covers.
