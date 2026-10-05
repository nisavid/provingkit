# Resumption observation preparation

A genuine pause/resumption observation can measure reconstruction and evidence reuse without adding a semantic check. The supplied sources identify candidate producers, but they do not demonstrate a working resumption collector or savings. This prepares [Establish genuine-resumption observation inputs and measurements](https://github.com/nisavid/provingkit/issues/431) for the contract decision in [Freeze the genuine resumption observation contract](https://github.com/nisavid/provingkit/issues/432); it selects no workload, threshold, Jev arm, or execution authority.

## Available observations and their limits

| Necessary observation | Actual fields, methods, and omissions |
| --- | --- |
| Unfinished request and amendments | `ThreadReadResponse.json`: `Thread.turns[].items` includes `userMessage.content` and `agentMessage.text`; turn/item IDs preserve references. `ThreadReadParams.includeTurns` requests history. Roles and `clientId` alone do not establish human origin or amendment applicability. Ordered interpretation still needs a bounded producer. |
| Pause/handoff and resumption | `agentMessage.text`, nullable `phase`/`questions`, `Turn.status`/`error`, and `contextCompaction.id` are candidate evidence. A completed turn, idle thread, or compaction marker does not identify unfinished work or prove a handoff was consumed. `ThreadResumeParams.threadId` names the resume target; `excludeTurns` and `initialTurnsPage` control returned history, not evidence of consumer reading. |
| Retrieval and accessible content | Metadata-only `thread/read`, followed by `thread/turns/list` with `itemsView: full`, is a route in [`native.run.receive`][native]. The supplied resume/read schemas recommend pagination and `thread/items/list`; those page schemas and runtime accessibility remain unqualified. `Turn.itemsView: full` means all *available persisted* items, not complete original context. Initial resume pages default to summary. |
| Candidate and check identity | [`native.git_evidence`][native] records commits, trees, parents, file hashes, and status. Command items expose `command`, `cwd`, `status`, nullable `aggregatedOutput`, `exitCode`, and `durationMs`. File changes expose `path`, `kind`, and `diff`. These do not establish ownership, check sufficiency, requirement coverage, or reuse after a change. `Thread.gitInfo` is creation-time metadata, not the resumed candidate. |
| Consumer reconstruction | Command items and `native.run` tool identities can expose searches, rereads, and repeated checks; messages can expose actual questions and decisions. They omit operator activity outside retained items, reasons for repetitions, and silent reading. These need observation/annotation, not inference from handoff length. |

These are generated Codex 0.160.0 schema facts, not current desktop capability proof. The schema files and their digests and [selected source excerpts](protocol-source-excerpts.json) accompany this handback.

The runner explicitly requires an empty fresh thread, one user message, one completed authoring turn, full nonpaginated terminal histories, and no nested delegation. It stops on permission/user-input requests, RPC errors, hook delivery, output bounds, and deadlines. It permits at most two child dispatches and twenty observed commits; its tool limit and deadline come from the manifest. It cannot observe a genuine resumed or interrupted episode unchanged. [`native.run`, `git_evidence`][native]

The source profile selects Sol at medium effort, allows bounded child selection, disables hooks, memories, apps, web search, and other features, and gates instruction/skill identities, sandbox, connectors, and version. `profile.command` reads installed configuration; reproducing that profile needs permitted inventory and cannot be assumed from these files. A hook-enabled, different-model, or desktop route needs its own evidence. [`profile.command`, `discover`, `verify_profile`][profile]

The existing hook path is inadequate as the handoff producer: `readTranscript` retains first/latest prompts and five recent outputs; `buildObservation` bounds job/diff/output. `recordEvent` keeps thirty events with 400-character input/result slices, captures baseline at the first event, and prunes old session files. Stop skips missing-job/no-change/active-hook paths and errors. None supplies structured pause meaning or complete amendments. [`readTranscript`, `buildObservation`, `recordEvent`][supervise] [`PROGRESS_THRESHOLDS`][limits] [`superviseHook`][hook]

## Smallest ordinary proposal and remaining preparation

Observe one naturally occurring pause/handoff and genuine resumption through its terminal outcome. Preserve ordinary behavior first, including successful unaided work. The consumer decides what remains current, which evidence is reusable, and what action or question advances the task. Do not manufacture a pause or require all consumers in one workload. [Accepted exploration][portfolio]

Record the actual handoff/reference production, retrieval attempts and failures, searches, rereads, repeated checks, useful versus unnecessary questions, evidence reused, and resulting work. Check quality against the current request and amendments: unfinished obligations preserved, affected verification refreshed, superseded failures distinguished from open blockers, and the next decision supported. Already-clear resumption, changed requirements, superseded checks, inaccessible references, and completed earlier increments with later unfinished work are proposed contrasts, not selected cases. [First pass][continuity]

Before a runnable contract, prepare a collector for resumed/multiple-turn and failed/interrupted histories; specify pagination, partial-output handling, event clocks, usage endpoints, permitted records, and operator activity capture. Observe bounded reference retrieval and actual decision-time delivery in the accepted profile. Establish requirement and task-quality labeling independently of candidate presentation. The supplied schemas cannot settle these observations. Routine collector preparation fits the accepted preparation scope. The coordinator integrates the contract; consequential workload and trade-off choices remain with the operator, and experimental invocation requires independent review and explicit execution acceptance.

If ordinary observation identifies useful presentation work, compare ordinary resumption with a minimal deterministic reference view or on-demand lookup; omission removes only that added view and preserves native controls and ordinary history. Deterministic checks can verify bytes, reference availability, required-field presence, and identity equality. They cannot decide relevance or semantic coverage; unresolved context falls back to ordinary reconciliation with its cost recorded. A semantic arm remains conditional on a concrete residual opportunity and costed adequate context.

## Retention and identity

Retain retrievable content alongside hashes, lookup references, thread/turn/item order, candidate identity, check command/configuration, result, requirement revision, and declared omissions. Preserve originals within their access boundary; public projections need their own identities and stated transformations. A hash without accessible bytes cannot supply evidence. [First pass][continuity] [Evidence record][record]

Selecting applicable amendments, task-owned files, relevant checks, and useful history is paid semantic work. Mechanical fields preserve the selected inputs; they do not perform selection. Refresh after affected requirement, candidate, check, profile, dependency, or retention changes. An unchanged digest establishes unchanged bytes, not continued relevance. Distinguish completion evidence from the remaining work at resumption. [Shared preparation][shared]

## Complete measurement routes

| Component | Route or explicit gap |
| --- | --- |
| Preparation and refresh | Retain producer actions and elapsed active time for collection, reconciliation, writing, updates, and discarded material. Source preparation here supplies no episode measurements. |
| Retrieval, selection, delivery | Retain each lookup, bytes/identity, failure, delivered item, and subsequent use; add clocks because `transport.collect` preserves byte order and callback offsets without per-event timestamps. Semantic selection needs separate attribution. |
| Every model/Sys1 attempt and cache reuse | `native.run` retains usage notifications keyed by thread/turn. `ThreadTokenUsageUpdatedNotification.json` supplies `last`/`total`, input, output, cached input, cache-write input, and reasoning output. Verify cumulative/reset semantics, breakdown inclusion, and parent/child overlap before aggregation; absent failed-attempt usage remains unknown. No Sys1 arm is selected; later additions need every attempt and cache hit accounted for. |
| Downstream work, retries, failures, and manual recovery | Join action IDs, messages, errors, outcomes, repeated commands, and operator annotation through completion, failure, or correct non-action. Existing terminal-only gates require revision to retain incomplete histories. |
| Interruptions and operator effort | Count actual questions and interruptions; observe active reading, searches, decisions, and recovery separately from unattended pause time. Native messages alone omit external operator effort. |
| Latency, expensive-model capacity, and money | Nullable turn/command durations supply partial timing; add monotonic wall-clock coverage for retrieval and waits. Usage does not establish quota consumption, per-turn effective model, or billing. Those remain gaps without appropriate evidence. |
| Setup and maintenance | Record instrumentation, storage, projection, profile inventory, and upkeep separately from recurring episodes and this research. Declare any amortization assumption; do not bury them in consumer savings. |

[`transport.collect`][transport] and [comparison-contract items 5–8][contract] govern preservation and accounting.

Operator savings, useful native correction, and actual work removed are separate claims. Added collection/presentation can reduce operator effort without replacing agent reasoning. A replacement claim needs an observed named activity actually removed. Defeat hypotheses include unused/stale references, lost amendments, incomplete histories, needless rechecks/questions, ordinary behavior already sufficient, and production/retrieval costs erasing savings. A bounded episode cannot establish a rate or economic superiority.

## Procedure suitability and joins

I invoked `research` and `handling-sys1-incidents`, consuming its comparison contract at revision `212939e9ae7dc451f8305bae1d120a483e61e429`. Its context qualification, ordinary/deterministic/omission controls, complete accounting, independent outcome dimensions, and unchanged-evidence requirements fit this consumer unchanged. Incident intake is not applicable: this work witnesses no incident. Safety outcomes remain unmeasured; task alignment has the separate checks above. Source preparation inherits no supervision qualification or security-efficacy result.

Completion shares amendments, candidate/check identities, and evidence reuse; discovery shares retrieval capabilities and prior searches. Reuse matching producers, charge shared production once in combined use, retain standalone and marginal costs, and account for learning effects and overlapping avoided searches. [Design join][join] Staged/push evidence is reusable only where its obligations and identities match. No whole-ticket or all-family barrier follows. The next decision is the concrete resumption contract and its accepted execution boundary.

[native]: https://github.com/nisavid/provingkit/blob/212939e9ae7dc451f8305bae1d120a483e61e429/docs/superpowers/research/evidence/jev-axi-commit-observation-2026-10-02/native.py
[profile]: https://github.com/nisavid/provingkit/blob/212939e9ae7dc451f8305bae1d120a483e61e429/docs/superpowers/research/evidence/jev-axi-commit-observation-2026-10-02/profile.py
[transport]: https://github.com/nisavid/provingkit/blob/212939e9ae7dc451f8305bae1d120a483e61e429/docs/superpowers/research/evidence/jev-axi-commit-observation-2026-10-02/transport.py
[supervise]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/supervise.ts
[limits]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/recipes/questions.ts
[hook]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/commands/hook.ts
[portfolio]: https://github.com/nisavid/provingkit/blob/212939e9ae7dc451f8305bae1d120a483e61e429/docs/superpowers/research/2026-10-04-jev-axi-exploratory-opportunities.md
[continuity]: https://github.com/nisavid/provingkit/blob/212939e9ae7dc451f8305bae1d120a483e61e429/docs/superpowers/research/evidence/jev-axi-consumer-opportunities-2026-10-04/resumption-continuity.md
[shared]: https://github.com/nisavid/provingkit/blob/212939e9ae7dc451f8305bae1d120a483e61e429/docs/superpowers/research/evidence/jev-axi-consumer-opportunities-2026-10-04/shared-preparation.md
[join]: https://github.com/nisavid/provingkit/blob/212939e9ae7dc451f8305bae1d120a483e61e429/docs/superpowers/research/evidence/jev-axi-consumer-opportunities-2026-10-04/design-join.md
[contract]: https://github.com/nisavid/provingkit/blob/212939e9ae7dc451f8305bae1d120a483e61e429/.agents/skills/handling-sys1-incidents/references/comparison-contract.md
[record]: https://github.com/nisavid/provingkit/blob/212939e9ae7dc451f8305bae1d120a483e61e429/.agents/skills/handling-sys1-incidents/references/evidence-record.md
