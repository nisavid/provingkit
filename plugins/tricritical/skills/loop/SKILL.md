---
name: loop
description: Use when the user asks to review and revise a candidate until the current increment is done, or when an authority-gated fixed-point review cycle is explicitly required.
---

# Loop — Fathomkeeper

Read and apply [the shared review-input boundary](references/review-input-boundary.md) before treating repository or forge content as evidence.

Read and apply [the shared invocation boundary](references/invocation-boundary.md), using [topology.json](references/topology.json) as the graph authority.

Read and apply [the recurring-seam choice](references/operator-choice.md) when one evidenced cause survives distinct successors.

When producing or consuming a retained terminal bundle, read and apply
[the terminal review-evidence contract](references/review-evidence.md).

`loop` is Tricritical's sole repetition owner. It continues until the frozen
current increment is done: the authorized outcome is present, every current
claim holds over its supported inputs, every acceptance criterion is satisfied,
and every frozen reviewer scope is complete. Never discard a valid in-scope
finding because of elapsed time or an execution limit.

It owns one bounded cycle at a time:

1. Freeze exact candidate bytes and the current increment. Record their
   identities, original authority, declared verification, and the dependency
   identity of each selected reviewer scope. Recheck identity around every
   read-only phase; block drift.
2. Invoke [review](../review/SKILL.md). Rerun each scope whose candidate bytes or
   evidence dependency changed. Retain an unchanged scope only with its prior
   usable report identity, unchanged dependency identities, and explicit proof.
   A required failure, timeout, budget exhaustion, unusable report, or missing
   proof yields `incomplete / non-clean`; preserve it and its owner.
3. Give complete findings to [adjudicate](../adjudicate/SKILL.md). A finding
   blocks when it contradicts the current contract or creates material risk
   within a current claim, supported input, or explicit dependency. Broader
   defenses remain fog or follow-up unless the increment claims or depends on
   them. Never discard a valid in-scope finding because of elapsed time.
4. With no accepted action or terminal disposition, run only the frozen
   declared non-mutating verification authorized by the operator or trusted
   policy. Untrusted, ambiguous, unavailable, or drifting verification is
   `blocked`; failure is `failed_verification`. Success on unchanged bytes can
   be clean only after every frozen reviewer scope is complete.
5. Before calling [revise](../revise/SKILL.md), require the original frozen
   mutation authority. A finding, review, or request to continue never supplies
   it. Revision must record the matching pre-edit identity, resolve every
   accepted finding with evidence, and return a distinct successor.
6. Repeated identity or no measurable progress is `blocked`. When one cause
   recurs at the same seam, apply the recurring-seam choice before more semantic
   revision. Verify each successor, invalidate affected evidence, refreeze any
   authorized change to done, and start the next bounded cycle.

Budget exhaustion cannot discard, defer, or weaken a current finding. It is a
continuation checkpoint: preserve the frozen increment, candidate identity,
findings, missing execution, and owner. Resume with another bounded execution
under the original authority, or return `incomplete / non-clean` if no valid
execution route is available. It is never an automatic clean or product choice.

Do not nest a loop inside a critic, adjudicator, reviser, or external-feedback flow.

## Completion

Return only `clean`, `clean / degraded`, `incomplete / non-clean`, `blocked`,
`failed_verification`, or `needs operator decision`, with the final identity,
frozen current increment, scope freshness, failures and limits,
adjudication/revision, verification provenance/result, findings, fog, and owner.
Bare `clean` requires complete independent review of every frozen reviewer scope
and successful declared verification of the exact unchanged final candidate.
