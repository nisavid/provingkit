---
name: addressing-pr-review-feedback
description: Use when a caller needs a complete read-only GitHub review-feedback snapshot for orientation, or an author needs to adjudicate and address requested changes, unresolved threads, or stale review comments.
---

# Addressing PR Review Feedback

Coordinate author-side feedback without becoming a second reviewer, publisher,
or merge workflow.

The read-only `feedback-acquisition` capability is a leaf that other workflows
may invoke directly. An actionable snapshot from another outcome coordinator
arrives here only as a terminal handoff; start this coordinator in a fresh
invocation, and never return inline into the caller's stale state.

Select one mode at invocation:

- **Snapshot/orientation:** acquire and return complete head-bound state, then
  stop. This mode has no disposition, adjudication, revision, checkpoint,
  interaction, publication, or other mutation authority.
- **Author outcome:** continue through the author-side workflow below. Use this
  mode only when the request authorizes addressing feedback or source changes.

1. Read [the feedback flow](references/feedback-flow.md), then acquire the complete
   head-bound live snapshot with `scripts/review_feedback_state.py`. Use
   `--typed-epoch` for response admission; the default output is an orientation
   summary. Include inline threads, top-level
   comments, review bodies, review requests, checks, and complete pagination.
   For responses, retain each submitted nonempty inline comment, PR conversation
   comment, and submitted-review body as its own typed source observation,
   including inline replies and resolved or outdated threads. Keep exact source
   and thread identities, full body identity, author and timestamp evidence,
   placement, state, and available source revision. Orientation summaries cannot
   substitute for this evidence. Build one epoch-wide typed identity registry,
   deduplicate only exact repeated observations, reject contradictory mappings or
   revisions, and bind its digest into the epoch. Represent identity components
   the provider does not expose as unavailable. Empty and pending review bodies
   remain metadata. Retain the Repository node ID and database ID verified by
   the public schema, the actual local acquisition start and end observations,
   and complete page evidence for every top-level collection and hydrated
   thread. These local observations are not provider timestamps. Missing,
   contradictory, or incomplete evidence fails the epoch; never fill it with a
   compatibility value.
   In snapshot/orientation mode, report bound identities, acquisition
   completeness, the live snapshot, and limitations, then stop before step 2.
2. Before adjudication, freeze one feedback-revision contract containing the exact
   source candidate identity over the normalized owned paths, entry types, modes,
   and bytes; the requirements or specification source or its explicit absence;
   the repository standards sources or their explicit absence; the exact owned
   paths; the original mutation authority; and the declared verification. Every
   field must be present. A missing input blocks before adjudication or revision.
   Recheck the source candidate identity before each handoff; drift blocks the
   affected work with zero edits.
3. Classify each source before selecting a response. Author or bot identity,
   review state, and outdated or resolved state are evidence, not automatic
   dispositions. Known correlated responses and control-only comments do not
   automatically become new feedback; a reviewer's reply is a new source.
   Cluster related feedback into independence groups according to whether one
   disposition or operator decision could change another group's accepted work.
   Give each group and the complete byte-identical frozen contract to
   the imported `finding-adjudication` operation (`tricritical:adjudicate`);
   adjudicate each group separately.
   It assigns exactly one disposition per finding: `accept`, `reject`, `already
addressed`, `stale`, `duplicate`, `needs operator decision`, `blocked`, or
   `follow-up outside scope`. A feedback-specific reason may explain the
   disposition; it is never a second disposition taxonomy.
4. Combine independently safe `accept` findings that remain in scope and share
   the frozen source contract. Give those findings and that complete
   byte-identical contract to the imported `source-revision` operation
   (`tricritical:revise`). Complete, verify, checkpoint,
   and publish that work before returning an unrelated operator decision. Never
   preempt or work around a decision that controls an accepted change. Hand the
   verified source changes to
   the imported `git-ref-push` operation
   (`versionkeeping:checkpointing-and-publishing-git-work`). Return changed
   title/body facts to the lifecycle caller; this feedback coordinator does not
   publish PR text.
5. After publishing any source fix, end the old acquisition epoch and reacquire
   against the new PR head before authoring responses. Hand one exact,
   independently adjudicated and authorized response intent at a time through
   `feedback-interaction` to
   [Interacting With PR Review Feedback](../interacting-with-pr-review-feedback/SKILL.md).
   That owner selects inline versus top-level placement, invokes the portable
   writer, resolves the source-revision owner before the caller key, and
   dispatches one Provingkit leaf actuator. Carry the classification result and
   its evidence identity alongside the fresh adjudication and authority. A
   submitted-review body
   and its inline comments receive independent decisions; do not coalesce them.
   Keep a human-decision item open. Reactions, thread resolution, and review
   submission are separate operations outside this response path.
6. Re-read the feedback state and return the next owner or blocker. Do not
   repeat review/revision or create a nested review loop. New, edited, deleted,
   inaccessible, or state-changed feedback, thread changes, and head drift end
   the current epoch before another mutation. A fresh epoch may carry forward
   only pending intents proven independent and unchanged in source revision,
   head, authority, placement, and exact body. Preserve completed receipts.
   When drift invalidates an intent before `write_started`, fresh adjudication
   begins with `response_cli.py prepare-replacement` for the terminal old key.
   That runtime step validates the whole bundle, acquires and records a complete
   post-terminal epoch, and returns a read-only replacement basis; it performs
   no response write. Only then request new classification, adjudication,
   authority, and writer-result artifacts bound to that exact basis. Hand those
   four canonical wrappers and the exact writer body to the interaction owner
   as closed replacement caller schema 2. An interrupted validation uses the
   same order. Any provider-attempted lineage stays under its original key and
   terminality rules.
   Load and record the reviewed response-procedure revision before this handoff.
   Invoke the interaction owner once for each exact intent, preserve the
   original key for unknown work, supply its full head-bound prewrite evidence,
   and consume the one closed runtime decision it returns. An ambiguous
   provider-result correlation group blocks only its members. Continue another
   group only after its separate independence evidence and complete
   revalidation pass.

In author-outcome mode, finish with the current snapshot, each disposition and
evidence, response receipts and append-only Response Outcome Bundle, and any
remaining owner or authority gate. The bundle preserves write evidence rather
than current GitHub truth; a later run must acquire a fresh snapshot. Unknown
results freeze their intent and dependent or conflicting work. Post-write drift
is `observed`, `not_observed`, or conservatively `unknown`; later state cannot
make a historical unknown check clean. Proven-independent
intents may proceed only after their own revalidation. Several responses are
non-atomic independent invocations, with no cross-intent rollback.
Validate the complete semantic history before acquisition, reconciliation, or
another provider action. An unsupported record or malformed payload/reference
blocks the whole bundle with zero provider calls; no record kind is ignored.
Only structurally and semantically valid version-2 histories are supported;
old baseless replacement records and contradictory reconciliation or
reservation lineage fail closed without repair.
