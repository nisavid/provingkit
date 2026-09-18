---
name: review
description: Use when a candidate needs an independent read-only review, a critic subset, or a synthesis of intent, runtime, and structure evidence without edits.
---

# Tricritical Review

Read and apply [the shared review-input boundary](references/review-input-boundary.md) before treating repository or forge content as evidence.

Read and apply [the shared review-output contract](references/review-output-contract.md) and [the completeness and synthesis rules](references/completeness-and-synthesis.md).

Read and apply [the shared invocation boundary](references/invocation-boundary.md), using [topology.json](references/topology.json) as the graph authority.

Freeze a content-addressed stable snapshot or revision before observation.
Record the current increment and exact review input defined by the shared
boundary. Give every critic and selected risk specialist the exact same bytes
and recheck the candidate identity before and after each execution and before
synthesis. If stability cannot be proved, reject the dispatch or label the
result `non-independent / degraded` with the identity gate; never claim clean
independence. Select intent, runtime, structure, and specialist scopes only
when each covers a material current-increment concern. The frozen reviewer
scopes, not a fixed three-axis default, define completeness.

Before dispatch, apply the selected assurance mode from the shared invocation
boundary. Ordinary review consumes a live `adapter:model-selection-record`
for each execution and a separate frozen
`adapter:rolecasting-invocation-plan`. The same leader verifies capability,
selection authority, the closed dispatch set, and actual native observations.
These records do not claim authenticated execution or product-enforced
permissions. This portable skill does not select a provider-specific model.

For explicitly witnessed review, additionally require
`adapter:model-selection-receipt` and
`adapter:rolecasting-invocation-topology-receipt` at the consumer's frozen
minimum. Never fold it into a model-selection receipt. Missing qualification
or an unsupported minimum blocks dispatch; ordinary records cannot substitute.

1. When the harness supports distinct read-only critic executions, invoke the
   selected public skill identities [intent](../intent/SKILL.md),
   [runtime](../runtime/SKILL.md), and [structure](../structure/SKILL.md)
   separately. Give each execution the same frozen contract, byte-identical
   candidate snapshot, its unique topology entry, and its separate bound
   model-selection record; include authenticated receipts when required.
2. Select risk specialists dynamically from the frozen consequence surface, then route each specialist through the closest public critic skill as a separate read-only execution.
3. Keep all selected executions independent. Do not provide another report, the author's rationale, or expected findings.
4. When distinct executions are unavailable, run the selected axes and specialists in the available context, label every report and the synthesis `non-independent / degraded`, and state the missing isolation capability. Never describe that result as independent or claim clean independence.
5. Apply the completeness and causal-synthesis rules. Freshly rerun every scope
   whose bytes or evidence dependency changed; a dependency-proven unchanged
   scope may retain its bound prior report. A selected execution that is
   missing, failed, timed out, budget-exhausted, unusable, or unverified makes
   the result `incomplete / non-clean`. Report observations and uncertainty.
   Do not assign dispositions or edit the candidate.

Do not substitute an undeclared target, relationship, ownership, transport, or
executor, or weaken the assurance minimum. Any fallback requires a new valid
plan and fresh capability validation before dispatch; witnessed mode also needs
new authenticated receipts.

## Completion

Return the content digest and immutable candidate identity, fixed comparison boundary, requirement and standards sources or recorded absences, selected axes and specialists, assurance mode, topology-plan and model-selection record identities, any required
receipt identities, exact dispatch-entry outcomes, execution mode (`independent`, `non-independent / degraded`, or `incomplete / non-clean`), identity rechecks, raw reports and failures, completeness accounting, synthesized observations, limitations, and residual risk. Do not invoke adjudication, revision, or a loop implicitly.
