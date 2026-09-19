---
name: getting-prs-ready-for-review
description: Use when the operator explicitly asks only to make a pull request ready for review end to end. A merge-owned readiness invocation may call this skill as its delegated readiness leaf; direct callers must still keep readiness separate from review-only, text-only, publish-only, merge, ship, or closeout outcomes.
---

# Getting PRs Ready For Review

Coordinate one review-readiness outcome. Read repository/operator policy first;
it defines who may publish commits and mark a draft ready.

When invoked within PR closeout, read
[caller continuation](../getting-prs-merged/references/caller-continuation.md)
and return readiness to that caller so it can continue from live state.

For creation with Issue contributions or a material contribution/completion
scope change, use
[Maintain Issue–PR Relations](../maintaining-issue-pr-relations/SKILL.md)
before authoring. Carry its ledger intent into the writer/publisher handoff,
then resume pending reconciliation with the assigned PR identity and verified
publication result. Reuse the caller's stable task ID, observations, and plan;
unchanged ready-only work does not reacquire relations or repository settings.

1. Resolve the exact repository, branch, pushed base/head, exact head repository,
   and existing PR.
2. Stop on unresolved valid blockers, operator decisions, or overlapping source
   ownership. This skill does not perform an independent review or address
   existing review feedback.
3. When scoped changes need a checkpoint or push, call
   the imported `git-ref-push` operation
   (`versionkeeping:checkpointing-and-publishing-git-work`).
4. Select the publisher's explicit `required` or `not-required` mode and sorted
   specialist inventory before invoking `pr-content` or freezing its candidate.
   Preserve an existing selection; changing it requires fresh applicable review.
   Give that selection and the exact pushed change to the `pr-content` operation
   owned by
   [Write Reviewable PR Descriptions](../writing-reviewable-pr-descriptions/SKILL.md).
   Where its independent review gate applies, require the verified bare `clean`
   hand-back for the current candidate, review input, requirements, scopes, and
   evidence dependencies. `not-required` records no witnessed provenance and
   does not waive that review. An unavailable witnessed route blocks `required`.
5. Give the complete validated title/body to the operation-specific publisher
   surface in [Publish Reviewable PRs](../publishing-reviewable-prs/SKILL.md):
   use `pr-creation` for an absent PR or `pr-text-write` for an existing matching
   draft. Carry the same mode and specialist inventory through each publisher
   operation. Create every new PR as a draft; never create a duplicate.
6. Inspect the stored and rendered canonical body. If all readiness gates pass
   and actuation is authorized, refresh the exact identity/preimage and use the
   publisher's guarded `pr-readiness-write` operation.
7. Before reporting readiness, use the publisher's read-only
   `publication-audit` operation and require
   the authoritative latest receipt to verify the exact final live state.

Never invoke raw ready actuation or accept generated forge text as canonical.
Preserve the existing draft/ready state until the final authorized transition.
A mutation timeout requires an exact reread and never a blind retry.

Finish with exact repository/base/head identities, stored text digests,
receipt id/provenance/sequence and audit status, draft/ready state, and any
remaining operator-owned gate.

Return the retained task relation context, or explicit absence, with every
terminal result. Carry the [relation result contract](../maintaining-issue-pr-relations/SKILL.md#procedure):
plan identity, per-pair results, pending handoffs or verified receipts, original
setting observation metadata, read counts, limitations, and unresolved gates.
Preserve that context for the caller to resume pending work without rediscovery
or renewing observation timestamps. Keep relation-publication receipts distinct
from canonical publication evidence.
