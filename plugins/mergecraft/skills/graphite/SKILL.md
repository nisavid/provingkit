---
name: graphite
description: >-
  Use when working with Graphite `gt` stacks: creating or tracking stacked
  branches, navigating or reparenting a stack, restacking, submitting or
  updating stacked PRs, fixing Graphite metadata, or diagnosing stack ancestry
  and publication state.
---

# Graphite Stacks

## Boundary

Graphite owns stack topology, ancestry operations, restacking, submission, and
temporary draft transport only. The imported `git-ref-push` operation
(`versionkeeping:checkpointing-and-publishing-git-work`) owns commit/push safety.
[Publishing Reviewable PRs](../publishing-reviewable-prs/SKILL.md) immediately
owns canonical title/body and readiness repair; its writer owns content.

Do not maintain another PR-body format. `gt submit` is only draft transport;
complete it before invoking
[Publishing Reviewable PRs](../publishing-reviewable-prs/SKILL.md); the
publisher never wraps it. Publication requires verified canonical bodies.
The submit-draft path calls only the publisher's `pr-text-write`,
`pr-readiness-write`, and `publication-audit` operations; it does not inherit
every publisher mode and cannot mint provenance by reconciliation.

## Establish Live State

Before mutation, run `git status --short --branch`, `gt log short`, and `gt trunk`.
Bind branch, parent, order, tracking, PRs, and unrelated changes from live state.

Use `gt` navigation, `track`, `create`/`modify`, `restack`, `move`, and `rename`
when they express the operation. Use raw Git only for an unsupported or
documented recovery path, then restore and verify Graphite tracking.

## Create Or Extend A Stack

Start at the verified parent. Keep branches cohesive; stage task-owned paths,
follow repository policy, run branch checks, then restack and verify ancestry.

When adopting branches created outside Graphite, check out each branch in
bottom-to-top order and run `gt track`, selecting the true parent. A worktree
branch can be tracked without moving or deleting the worktree.

## Submit Or Update PRs

For new Issue-contributing PRs or material contribution/completion scope
changes, use
[Maintain Issue–PR Relations](../maintaining-issue-pr-relations/SKILL.md)
before preparing canonical pairs. Share the stable task ID and observations
across the stack; retain every member's own contribution roles. Carry planned
ledger content through the existing writer and publisher. After draft transport
and immediate canonical repair finish, resume pending relation reconciliation
with the verified PR identities and publication results. An ancestry-only
restack or unchanged resubmission does not reacquire relations or settings.

1. Verify root/base and checks; ensure each remote head will equal the recorded
   local commit, then prepare every canonical pair and bound review-input file.
2. Build a schema-v2 absolute-path JSON request for the exact bottom-to-top stack
   and run
   `scripts/submit_draft_stack.py plan`. Review its content-addressed private
   plan. Git operations use the host-compatible configuration profile by
   default, keeping the host's global/system config, credential providers, and
   normal command path available. Set
   `MERGECRAFT_GIT_CONFIG_PROFILE=hardened` for the explicit closed profile;
   it masks global/system config, uses a fixed trusted command path, disables
   implicit commit/tag/push signing, and rejects executable local/worktree
   configuration (including signing programs). Both profiles reject unsafe
   repository/worktree configuration, unsafe includes, and unsupported remotes
   without printing their values. The
   plan binds the clean worktree, current branch, local base/head OIDs, the exact
   current-to-trunk chain and revisions from validated read-only Graphite
   metadata, Graphite 1.8.6's target repository, and the selected remote's exact
   fetch/push endpoint hashes to the stack's single head repository. It also
   binds the selected Git configuration profile and effective configuration
   digest so a plan cannot be executed under a different profile, along with
   diagnostic Graphite log/trunk hashes, candidate inputs, existing PR
   preimages, and each entry's mandatory `review_mode`, `review_bundle`
   (absolute only for `required`, otherwise null), and sorted explicit
   `selected_specialists`. Stop if the typed mutation inventory differs from
   the reviewed bottom-to-top request, the version or metadata schema is
   unsupported, or either repository binding differs.
3. Run `scripts/submit_draft_stack.py execute` on that unchanged plan. It invokes
   exactly one `gt submit --no-stack --draft --no-edit --no-ai
   --no-interactive`. This submits the reviewed current branch and its exact
   downstack chain without unreviewed descendants; add no branch selector or
   broader stack flag. The script never retries an ambiguous transport, maps
   every branch to one exact PR, and writes a private repair handoff. Stop on any
   partial or mismatched result.
4. Immediately run `scripts/submit_draft_stack.py repair` on the complete
   handoff. It executes only the owned publisher commands, bottom-to-top,
   preserves existing ready state, repairs the temporary Graphite text, and
   audits the authoritative latest receipt for every PR. On a new run or resume,
   an uncheckpointed PR whose latest audit already matches the exact handoff
   target is durably checkpointed before any publisher command is considered;
   stale preimage commands are never replayed after convergence. When transport
   already equals the candidate, repair succeeds only if the latest canonical
   v3 audit already has the exact review mode and publication-candidate digest;
   otherwise it blocks. It never upgrades legacy, reconciled, or not-required
   provenance and never manufactures a no-op transition.
5. Verify stored/rendered bodies, denominator, bases, dependencies, navigation,
   current marker, and the repair receipt. An older matching receipt does not
   verify current publication. Rebuild every Stack/Diff from its pushed
   base/head and use guarded readiness only for intended draft-to-ready changes.

If Graphite is unavailable, use the standalone publisher only for a truly
standalone workflow; otherwise stop.

## Restack And Recovery

Checkpoint/order before restacking; resolve conflicts bottom-up with checks.
After raw rebase restore tracking and verify `gt log short`. After interruption
inspect Git and Graphite. Regenerate navigation/diffs after force-update.

## Destructive Changes

Deleting a branch, discarding commits, moving a subtree, or rewriting a
published stack requires a verified impact inventory and the authority supplied
by the operator and repository policy. Preserve remote work with exact leases.
Never delete a harness-owned worktree as incidental Graphite cleanup.

## Completion

Report the final bottom-to-top stack, each branch and PR URL, base/head SHAs,
validation, submission result, receipt id/provenance/sequence and audit status,
canonical-body verification, and any unresolved Graphite or reviewer-owned
action.

Return the retained task relation context, or explicit absence, with every
terminal result. Carry the [relation result contract](../maintaining-issue-pr-relations/SKILL.md#procedure):
plan identity, per-pair results, pending handoffs or verified receipts, original
setting observation metadata, read counts, limitations, and unresolved gates.
Preserve that context for the caller to resume pending work without rediscovery
or renewing observation timestamps. Keep relation-publication receipts distinct
from canonical publication evidence.
