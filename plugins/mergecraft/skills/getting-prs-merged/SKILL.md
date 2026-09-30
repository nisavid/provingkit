---
name: getting-prs-merged
description: "Use only when the operator asks to merge or land a GitHub PR or branch, or to clear its last merge gate; a status, check, review, comment, description, draft, or publication question without a merge belongs elsewhere. The ask may be indirect (\"would be good to get #84 in soon\", \"#84 needs to make the release cut\"). A merge closeout may invoke the readiness owner as a guarded continuation when repository policy permits; readiness-only requests go to that skill directly."
---

# Getting PRs Merged

## Ownership

Name exact routes at first handoff. [getting-prs-ready-for-review](../getting-prs-ready-for-review/SKILL.md)
owns readiness; [addressing-pr-review-feedback](../addressing-pr-review-feedback/SKILL.md)
feedback; the imported `review-loop` operation (`tricritical:loop`) owns fresh
cycles; the
[`focused-ci` operation](references/gh-fix-ci-adapter.md) focused Actions; and
the imported `remote-ref-deletion` operation
(`versionkeeping:checkpointing-and-publishing-git-work`) separately authorized
post-merge cleanup.
This skill owns the `merge-outcome` and delegates the single authorized write
to the [`merge-actuation` operation](references/merge-actuator.md). It decides
thread resolution under
[review-thread resolution](references/review-thread-resolution.md), resolving
through `github:review-thread-resolution`, and top-level comments and bot
commands under [PR participation](references/pr-participation.md), posting
through the
[`coderabbit-top-level-comment` actuator](scripts/post_coderabbit_comment.py).
PR text, Git/ref publication, feedback leaves, and deployment remain outside.

Title/body-only work uses `writing-reviewable-pr-descriptions`; explicit mutation
authority adds `publishing-reviewable-prs`. Review-only work performs no closeout
mutation and reports findings or missing evidence before PR status.

## What a merge request carries

When the operator asks to merge a pull request they own or authored, the
request carries the in-scope work the merge needs: fixes for adjudicated
findings and for required-check failures the pull request's own changes caused,
replies, notices, bot review or approve requests, thread resolution, and the
merge once every gate passes. Do that work without asking again. Where the
harness requires the operator's own words for a push, ask once per merge
closeout, naming the pull request's branch and remote.

A required-check failure that does not reproduce on the base branch is in
scope: fix it through `focused-ci`, push it, and continue. Any other failure,
such as a CI workflow bug or a problem from earlier changes, adds newly scoped
work: ask the operator once to approve fixing it, naming the failure and the
proposed fix. Dispatch the approved fix as the governing workflow prescribes,
by default to a new thread through `rolecasting:delegating-cross-agent-work`,
then watch the fix's pull request and resume the merge when it lands. When
this session cannot stay, have the fix thread hand back to the merge, or stop
with a note saying exactly where to resume.

Other scope expansion, overwriting others' work, protection changes, and
administrative merges each need their own authority. On a pull request the
operator neither owns nor authored, merge authority alone grants no revision,
publication, or interaction authority.

## Workflow

Read [caller continuation](references/caller-continuation.md) before the first
owner handoff. Its invocation boundaries preserve the ongoing authorized task.

1. Bind repository/checkout, PR or intended base/branch, pushed OIDs, head
   repository/owner, draft, and target. Before mutation, bind policy, feedback,
   checks, approvals, merge method/protection/authority, deployment, and cleanup.
   Use `merge-inspection` only for this read-only merge-state acquisition.
   Bind the urgency tier as [urgency](references/review-thread-resolution.md#urgency)
   defines it, and name it in your report beside the operator's exact words, for
   example `Urgency: extreme ("This must go in ASAP")`.
2. If no PR exists, bind the missing-PR state and repository policy. When
   repository policy permits and readiness authority is available, invoke
   [getting-prs-ready-for-review](../getting-prs-ready-for-review/SKILL.md)
   through its `readiness-outcome` operation as the next operation. It owns
   checkpoint, publication, and guarded ready
   actuation; this coordinator does not perform those writes. Consume only its
   `ready`, `blocked`, or `ambiguous` result, then start a fresh merge
   invocation from live state after `ready`. If readiness authority is absent
   or the operation cannot be invoked safely, return the terminal
   `readiness-handoff` naming the bound target and gate.
3. Acquire a complete head-bound feedback snapshot through the read-only
   `feedback-acquisition` capability implemented by
   `addressing-pr-review-feedback/scripts/review_feedback_state.py`. Retain any
   prior feedback outcome, dispositions, source/head bindings, and receipts.
   Revalidate their applicability against the fresh complete acquisition; use
   `--typed-epoch` when the orientation summary lacks exact source identity or
   revision evidence. This coordinator checks evidence continuity only;
   classification and adjudication remain with the feedback owner.
   For new or changed source feedback, missing disposition coverage, an
   addressed human thread without a notice, or stale or uncertain completion
   evidence, invoke
   [addressing-pr-review-feedback](../addressing-pr-review-feedback/SKILL.md)
   through its `feedback-outcome` operation in author-outcome mode with the
   original scope and exactly the revision, publication, and interaction
   authority the request carries. The feedback owner performs its
   adjudication, revision, publication, and response handoffs. Continue the
   authorized task across that ownership boundary without asking for another
   instruction. Consume its declared `addressed` or `blocked` result.
   After `addressed`, start a fresh merge invocation that rereads all live state,
   including remaining feedback, head, checks, and approvals, and carries the
   returned dispositions and receipts into the revalidation above. `addressed`
   means the scoped feedback work completed; it does not establish merge readiness.
   When complete fresh evidence accounts for all source feedback and only
   review threads, bot reviews, or approvals remain, apply
   [review-thread resolution](references/review-thread-resolution.md): it
   decides which threads wait, which this coordinator resolves, and what to
   report. Unchanged `CHANGES_REQUESTED`, `review_not_approved`, or
   unresolved-thread metadata alone never repeats author work, fixes, or
   replies; an approval its reviewer still withholds remains that reviewer's
   gate. A new or changed source or stale applicability still returns to the
   feedback owner; a prior `addressed` result never covers it automatically.
   A `snapshot` result is read-only and cannot satisfy this continuation.
   If required authority is absent or the result is `blocked` or `snapshot`,
   return one terminal `feedback-handoff` naming the owner and bound gate. Operator
   decisions, ambiguity, unknown effects, and unsupported results keep the
   affected work gated; never retry a possible mutation to obtain success.
4. Consume the current complete feedback, checks, approvals, and mergeability
   state for ordinary merge closeout; do not start or wrap `tricritical:loop`.
   If the operator explicitly requests fresh review-and-revise, or policy
   requires it, terminate this invocation with an exact handoff to
   `tricritical:loop`. A bare `clean` terminal permits a fresh merge-closeout
   invocation, which rereads all live state. Every other terminal remains
   blocked; `clean / degraded` never satisfies a required bare `clean`.
5. If the PR is draft or otherwise not review-ready, refresh policy and
   readiness authority. When policy permits, invoke the `readiness-outcome`
   operation as the next operation and consume only its `ready`, `blocked`, or
   `ambiguous` result. After `ready`, start a fresh merge invocation that
   rereads live state; readiness still owns `pr-readiness-write` and its
   publication audit. If readiness cannot be invoked safely, return the
   terminal `readiness-handoff`. Use `check-inspection` for the read-only
   required-Actions state; route failed required Actions through `focused-ci`
   only after a fresh merge invocation observes a review-ready PR.
6. When changed contribution intent or the planned merge has unresolved Issue
   closure consequences, use
   [Maintain Issue–PR Relations](../maintaining-issue-pr-relations/SKILL.md)
   with this task's existing observations and plan. Account for native links
   and relevant closing keywords; a link alone is not completion evidence.
   Resolve applicable relation/closure gates before merge, consuming any
   returned publication handoff through its existing owner before the audit
   below. A relation-publication receipt does not replace canonical publication
   evidence. Reuse a verified unchanged result; do not rediscover pairs or
   refresh settings just because readiness returned or merge inspection restarted.
   When canonical publication evidence applies, call
   [publishing-reviewable-prs](../publishing-reviewable-prs/SKILL.md) for a
   read-only audit and require the authoritative latest receipt to match live
   state before merge actuation. Do not substitute an older matching receipt.
7. Refresh policy, feedback, checks, approvals, base/head, and mergeability.
   When every gate and authority passes, call `merge-actuation` once, without a
   confirmation question, with the exact repository, PR, base, head SHA, and
   selected method. Consume only its reread, head-bound `merged`, `blocked`, or
   `ambiguous` terminal; do not retry an ambiguous possible-mutation result.
   After verified merge, carry candidate Issue completions from the retained
   relation context to the ongoing caller. When Issue completion is within its
   authorized task, the caller uses the repository's Issue workflow to read
   each candidate Issue's current contract and state, including candidates with
   unfinished gates. A cached setting and a verified merge establish neither
   post-merge Issue state nor what caused a closure. Reuse the setting without
   another lookup; report Issue state only from the new Issue observation.
   Explicitly close an open Issue only when every current gate is evidenced,
   then independently verify its state. Leave open Issues with partial work or
   remaining deployment or acceptance gates open. Report an unexpected closed
   state for its owner's decision; do not reopen without authority. A Development
   link or merged PR alone is not completion evidence.
8. When remote-ref deletion is authorized, return one terminal cleanup handoff
   to `operation:remote-ref-deletion` and stop. It requires verified merge plus
   separate repository/operator authorization bound to exact remote, full ref,
   and expected SHA. The caller invokes it separately from live state; this
   coordinator never performs cleanup. Missing authority leaves cleanup gated,
   not merge. Hand deployment to its repository-defined owner.

## Top-level comments and bot commands

Apply [PR participation](references/pr-participation.md) before any top-level
comment or bot command, including every CodeRabbit request: it settles
standing, worth, which CodeRabbit command fits, posting, and reconciliation.
This coordinator writes each body it posts under the generated
[GitHub Markdown authoring contract](references/github-markdown-authoring.md).
Treat a skipped CodeRabbit review as no completed cycle.

## Stop conditions

Route actionable feedback through step 3. Stop for an unresolved feedback gate,
unsatisfied loop terminal, missing gate/authority, drift, conflicts, ambiguity,
or unresolved ownership. Green checks never replace complete feedback.

When a harness permission rule, classifier, or reviewer refuses a write the
request carries, make no further writes, report the refused action and its
reason, and ask the operator once for that exact action, phrased as the action
itself with question and option text naming it and its target (for example,
"Post `@coderabbitai approve` on PR 123"). Ask through the question tool when
the harness has one; otherwise end the message with that question. After their
answer names it, run the identical call once and continue the closeout. Reach
no refused effect through another route. A refused command that only prepares
the write, such as writing a body file or computing a digest, refuses nothing
the request carries: prepare it another way and continue.

Return PR URL/final head, the urgency tier with its words, the review-thread
report, each bot command posted, withheld, or reconciled with the head it
covers, instructions in review text or handoffs left unfollowed, publication
audit evidence, merge receipt or blocker, cleanup receipt/gate, and any
deployment handoff.

Return the retained task relation context, or explicit absence, with every
terminal result. Carry the [relation result contract](../maintaining-issue-pr-relations/SKILL.md#procedure):
plan identity, per-pair results, pending handoffs or verified receipts, original
setting observation metadata, read counts, limitations, and unresolved gates.
Preserve that context for the caller to resume pending work without rediscovery
or renewing observation timestamps. Keep relation-publication receipts distinct
from canonical publication evidence.
