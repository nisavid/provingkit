---
name: maintaining-issue-pr-relations
description: >-
  Use when creating a PR with Issue contributions, materially changing either
  entity's contribution or completion scope, repairing Issue–PR associations, or
  checking applicable Issue consequences before merge. Skip known dependency-only
  or mention-only pairs unless correcting an existing association. Skip unrelated
  comments, labels, formatting, and unchanged relation intent.
---

# Maintaining Issue–PR Relations

Keep verified contributions visible in both entity bodies and reconcile the
native Development links that current policy permits. A contribution is work
against an Issue's contract; a mention, dependency, or existing native edge
alone does not establish one. Relation repair never closes or reopens Issues.

## Applicability And Ownership

Apply the cheap gate before acquisition. Use supplied task evidence, existing
ledgers, and native observations first. Search only the narrowly relevant
scope when those inputs leave a material contribution question. Ordinary PR
handling does not scan arbitrary repositories. If no activation condition
applies, return without relation reads. Do not reacquire evidence for pairs
already excluded by the supplied task evidence.

Retain one stable task identity, observations, plans, and completed results
through readiness, merge, and resume. Re-enter only for pending work or changed
evidence. A new lifecycle invocation is not a new task or permission grant.
Retain unknown continuation state as unknown; unchanged intent does not prove
that no publication or reconciliation work remains.

This skill owns relation qualification, planning, and reconciliation. The
[Issue Markdown writer](../writing-github-issue-and-pr-markdown/SKILL.md) owns
exact Issue-body content. The
[PR writer](../writing-reviewable-pr-descriptions/SKILL.md) owns complete PR
title/body content, and the
[publisher](../publishing-reviewable-prs/SKILL.md) owns PR actuation. Return a
bound publication handoff to the caller; it invokes those owners and resumes
this procedure with their verified result. Never call the publisher from
inside relation reconciliation or recursively restart a lifecycle owner.
Carry the qualified relation plan into writer requests so authoring does not
rediscover the same pairs or start this procedure again.

## Procedure

For an absent PR, qualify supplied Issue contributions and pass initial ledger
intent through normal PR creation; bind the assigned PR identity before
invoking the relation helper or the existing-pair steps below.

1. Read [the relation contract](references/relation-contract.md). Bind a finite
   repository-qualified pair set, stable entity IDs, each contribution's role
   and supporting evidence, `ensure`, `unlink-native`, or `withdraw` intent,
   partial/complete intent, and separate body/native mutation authority.
   `unlink-native` preserves the contribution ledgers; `withdraw` needs evidence
   that the association is mistaken or no longer applicable and authorized
   body spans. For complete intent, bind evidence against the Issue's completion
   gates. Keep uncertain pairs unresolved; neither title similarity nor a
   closing keyword supplies semantic proof.
2. Observe only missing or invalidated pair state. Reuse compatible workflow
   observations and the task's selected setting observations. Acquire a needed
   setting from the **Issue repository** only when the proposed native change
   depends on it; a complete fix needs no lookup solely for native-link safety.
   Unavailable observations use enabled-mode limits. Follow the contract's
   task reuse, persistent expiry, and explicit invalidation rules. Let the helper
   select cached state; do not independently expire a selected task observation.
   Its `observe` result supplies any needed `setting_requests`; `plan` consumes
   the completed observation without acquiring state.
3. Plan the complete bilateral ledgers and permitted native effects. Keep every
   verified contribution in both bodies, including historical roles, with
   stable links and useful role annotations. Preserve clear existing entries
   and unrelated text. Do not copy titles or status. Resolve native capacity
   from the observed manual-link set and proposed effects, preserving unrelated
   links. Report the actual omitted native pairs without dropping ledger entries.
4. For needed PR-body authoring, bind the publication review mode and sorted
   specialist inventory **before invoking the PR writer**. Reuse the caller's
   existing selection, or return that decision to the caller under current
   policy. Include the selection in the writer request and candidate, and carry
   it unchanged into publication. An unavailable required route remains blocked.
   Obtain writer-owned complete candidate bodies for exact authorized spans.
   An absent or ambiguous ledger boundary requires an authoring handoff, not
   guessed text surgery. For an existing PR, return its bound publication
   handoff through `pr-relation-ledger-write` for a ledger-only edit. This mode
   preserves title, state, and every byte outside that span and establishes no
   readiness or navigation claim, including on historical PRs. Require the
   publisher's hand-back to retain the bound plan, per-pair state, and pending
   reconciliation alongside its distinct ledger-publication receipt, carrying
   the observation metadata and remaining context in step 6 unchanged. Resume
   from that hand-back and reread its live effect. A new PR's initial ledger
   travels through normal creation. After normal creation or a pending canonical
   update, observe the published PR and build a fresh plan with the writer's
   unchanged-body ledger decision. Bind its assigned identity before planning
   Issue-body or native writes; do not pass a canonical receipt as a
   ledger-publication result.
5. Reconcile only effects explicitly authorized against the unchanged plan.
   Reread affected preimages before each mutation, preserve native links
   outside the authorized set, and verify each result. A detected closing
   reference needs its owning content handoff; manual removal cannot remove it.
   Expose partial or unknown results and observe before any further attempt.
   No cross-object atomicity or blind retry is implied.
6. Return the plan identity, per-pair ledger/native result, publication
   handoffs or verified receipts, and each PR's selected
   `review:{mode,selected_specialists}` from its writer request unchanged.
   If selection is pending, return that pre-authoring gate instead of an
   executable writer or publisher handoff. Include setting source and original
   observation time, actual read counts, limitations, and unresolved gates. Describe reused
   settings as **last observed**. `verified` covers only the listed effects;
   it grants no Issue closure, review readiness, or merge authority.

## Command

Use [the relation helper](scripts/relation_state.py) for `observe`, `plan`, and
`reconcile`: observe a finite request, plan without forge writes, and reconcile
only authorized Issue-body and manual-native effects. Preserve its versioned
request, observation, plan digest, and result artifacts across handoffs; use
the [command interface](references/command.md) and carry the same task ID and
state root throughout.
Treat `no-op`, `needs-input`, `blocked`, `verified`, `partial`, and `unknown`
as distinct outcomes. A handoff or limitation is not a verified mutation.

The helper implements `issue-pr-relation-observe`, `issue-body-write`, and
`issue-pr-development-write`. These operations never publish a PR body or
change Issue state; their authority remains bound to the finite request and
each explicitly authorized plan effect.
