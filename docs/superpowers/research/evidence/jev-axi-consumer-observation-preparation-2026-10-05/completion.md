# Completion observation: supported records and measurement proposal

Completion reporting can be investigated through retained requests, report text, candidate identities, verification receipts, and the operator’s actual checking actions. The sources provide pieces of that route; they do not establish a complete ordinary observation or reduced effort. I used `research` and explicitly invoked `handling-sys1-incidents` and its comparison contract at Provingkit revision `212939e9ae7dc451f8305bae1d120a483e61e429`. This handback prepares [the contract decision][successor]; it selects no workload, threshold, Jev arm, or experiment authority.

## Available observations and their limits

| Necessary observation | Actual fields or methods | Omission and supported boundary |
| --- | --- | --- |
| Requests and amendments | Codex `ThreadItem.userMessage.content/id/clientId`; `native.run.receive` retains delivered input and full requested histories. `observer.extract` preserves supported role/content records and indices. | Neither a user role nor an optional client ID establishes operator origin. Preserve the delivery chain and ordered amendments. The authoring runner asserts one original user message and one root turn; it cannot accommodate ordinary amendments unchanged. |
| Completion report and boundary meaning | Generated `agentMessage.text/id/phase/questions`; `TurnCompletedNotification.turn.status/error/items/itemsView`. | Optional phase is no completion judgment. A completed turn can yield, pause, or hand off. Pair actual report text with current direction; `itemsView=full` covers available persisted items, not every possible source. |
| Candidate and ownership | `native.git_evidence` records commit/tree/parents, observer matches, final file hashes, and porcelain status. | Its disposable-project enumeration excludes observation/runner directories and rejects symlinks. Ordinary task ownership, dirty-state separation, ignored content, and check-time candidate snapshots need explicit collection. A Git tree alone does not cover uncommitted work. |
| Checks and results | Generated `commandExecution.id/command/cwd/status/aggregatedOutput/exitCode/durationMs`; MCP `arguments/result/error/status`; dynamic-call `arguments/contentItems/success/status`. | Several result/duration fields are nullable. Preserve complete relevant receipts and command/tool identities. Exit code does not establish requirement coverage, passing assertions, or task correctness; relevance is selected and interpreted. |
| Stop’s actual input | `jev-axi` `readTranscript`, `buildObservation`, and `superviseHook` supply first/latest accepted prompt, last five tool outputs, diff, and skip/output branches. | Job/diff/output are bounded to 4,000/20,000/12,000 characters. Intermediate amendments and final assistant text are absent. Unstable transcript parsing skips unknown/malformed records. No extracted structured completion/pause/handoff meaning exists. |
| Baseline and hook provenance | `recordEvent` calls `sessionBase` at the first PostToolUse record; `workDiff` uses its baseline/untracked set. `HookReceipts.receive/reconcile` joins lifecycle starts/ends and compares event counts. | Baseline capture follows the first tool; exclusions and truncation limit coverage. Session state lacks cwd binding. Receipt/capture agreement is aggregate, not an individual invocation join. Removing assessment differs from removing this bookkeeping producer. |
| Consumer checking | No supplied runner records the operator’s searches, rereads, decisions, or active checking time. | A later permitted observer must retain actual actions and decision reasons. Report length or receipt count cannot substitute for effort. |

These are source facts from [the native runner][native], [bounded transcript observer][observer], [receipt reconciler][receipts], and [`jev-axi` observation sources][stop-source] and [Stop dispatch][hook]. The generated Codex 0.160.0 schemas are source availability only: `ItemCompletedNotification.json`, `TurnCompletedNotification.json`, and `ThreadTokenUsageUpdatedNotification.json`; their identities and [selected source excerpts](protocol-source-excerpts.json) accompany this handback.

The authoring profile fixes Sol/medium, disables hooks and several context features, restricts connectors, verifies loaded instructions/skills and sandbox settings, and stops on control requests. Its runner rejects paginated history and unexpected hook delivery; transport retains at most 2 MiB and distinguishes callback-consumed output from an undelivered tail. These bounded methods are useful designs, not an unchanged general completion collector or proof that this desktop surface supplies equivalent records. The private observer also requires a bound session/path, regular non-symlink JSONL, complete trailing newline, and at most 2 MiB; unavailable, oversized, changed, or malformed reads remain explicit. [Profile][profile] [Transport][transport] [Observer][observer]

## Smallest ordinary proposal and remaining preparation

Draft one prospective ordinary task observation through its natural report and the operator’s verification. Retain successful unaided work. A natural task may expose discovery too; no manufactured pause or all-family barrier is needed.

The primary consumer decides whether to accept the report, inspect a gap, or request further verification. Compare ordinary reporting with a deterministic linked-receipt view and omission of that extra view. Mechanical checks can detect missing references or identity mismatch; where applicability or freshness depends on semantic judgment, retain the agent’s selection and rationale. Incomplete inputs should expose the gap and fall back to ordinary inspection.

Count actual searches, rereads, repeated checks, questions, active checking time, and the resulting decision. Separately retain any agent correction and the exact ordinary reconciliation step removed. Without observed removal, preparation is added work. Check final candidate behavior against current accepted requirements, required verification, report accuracy, and unresolved work; keep evaluator labels separate from candidate inputs. Safety efficacy remains unmeasured. [Accepted benefit distinction][portfolio]

Before freezing execution, the successor needs a permitted collection/retrieval route, episode-specific source/model/instruction identities, the workload selection, comparison order and learning controls, operator-action capture, and independent outcome adjudication. Retain the accepted priorities: unnecessary interruptions, then constrained expensive-model capacity; latency and money stay separate. Reliability requirements and remaining trade-offs must be explicit without inventing numerical bars. Easy accurate reports, stale evidence, superseded failures, changed requirements, incomplete claims, and explicit pauses are candidate contrasts, not preselected cases. No Jev arm is selected; a later semantic question needs residual ambiguity and costed adequate context.

## Retention and evidence identity

Retain authorized original bytes with digest, episode/thread/turn/item or attempt identity, source revision, acquisition order/time, and accessibility. Keep public projections separate, documenting omissions. A surviving hash cannot recover lost content. Prove retrieval at the consumer’s decision point, including failures, before relying on a reference. Existing native records and bounded lookup remain alternatives to a new ledger. [Shared preparation][shared]

For each selected claim, retain the originating request/amendment, applicable instruction identity, task-owned candidate identity at check and report time, check command/configuration identity, result bytes, and supersession relation. Refresh affected evidence when requirements, candidate, verification dependencies, or retention/access change. Preserve earlier failures as history while distinguishing later superseding results. Mechanical identities establish correspondence; semantic selection determines applicability, coverage, boundary meaning, and evidential support. The selected requirement/evidence mapping is paid producer work.

## Whole-workflow accounting routes

| Component | Proposed measurement route or explicit gap |
| --- | --- |
| Preparation, refresh, retrieval, selection, recurring context | Producer action records, retained input sizes/identities, enclosing durations, and usage endpoints; distinguish mechanical collection from interpretation. No complete instrument is demonstrated. |
| Every model attempt and downstream work | Retain thread/turn/attempt identities and outcomes. Generated `tokenUsage.total/last` exposes input, cached input, cache-write input, output, reasoning output, and total tokens. Reconcile cumulative endpoints and child scopes before aggregation; failed-attempt coverage is unqualified. |
| Sys1 attempts, cache reuse, discarded/unused assessments | No Sys1 arm is selected. If baseline use exists, retain all requests, failures, skips, cache status, outputs, and delivery. `evaluate` logs successful calls/hits only; hits repeat historical usage with zero assessment milliseconds. Missing records are unknown, not zero. |
| Bookkeeping, checks, retries, failure, recovery | Enclosing monotonic intervals plus tool/process receipts for baseline Git work, session I/O/pruning, scans, diff construction, cache/log I/O, repeated checks, and manual recovery. Individual call durations do not establish whole-workflow wall time. |
| Operator interruptions and effort | Actual action/time records through acceptance, further work, pause, failure, or correct non-action; count questions and attention displaced by notes. Current sources have no such producer. |
| Setup, maintenance, latency, capacity, money | Separate one-time research/setup and maintenance from recurring episodes; state amortization assumptions. Report latency and expensive-model usage separately. Tokens/list-price estimates establish neither quota impact nor billing; those require separately permitted account evidence or remain unknown. |

These routes apply [the comparison contract’s complete accounting requirements][method]; [`client.evaluate`][client] supplies only partial service accounting.

The benefit hypothesis is defeated or narrowed if receipts are inaccessible or stale, mapping duplicates ordinary review, operator reconstruction persists, producer/refresh cost offsets savings, extra questions or misleading confidence appear, required work is missed, or learning/order effects explain the difference. An easy unaided success remains informative. An incomplete selected sample supports no population rate.

## Method suitability and joins

The comparison contract fits unchanged: context before judgment, ordinary/deterministic/omission alternatives, terminal outcomes, separate task alignment and safety results, and complete costs. Prospective ordinary preparation supplies no incident to invent and inherits no supervision qualification.

Join completion and continuity on current intent, candidate/check identities, supersession, and retrieval; join discovery on locating usable verification at use time. [Staged/push preparation][staged] offers matching review/obligation references only where scope and candidate identities agree; hook scores are not executed verification or completed obligations. Charge shared production once for combined use, preserve standalone and marginal costs, and count overlapping savings and learning once. These are conditional fact joins, not whole-ticket blockers. The remaining decision is the successor’s concrete observation contract and its separately accepted execution.

[successor]: https://github.com/nisavid/provingkit/issues/430
[native]: https://github.com/nisavid/provingkit/blob/212939e9ae7dc451f8305bae1d120a483e61e429/docs/superpowers/research/evidence/jev-axi-commit-observation-2026-10-02/native.py
[observer]: https://github.com/nisavid/provingkit/blob/212939e9ae7dc451f8305bae1d120a483e61e429/docs/superpowers/research/evidence/sys1-representative-preflight-2026-10-01/native-supervision/observer.py
[receipts]: https://github.com/nisavid/provingkit/blob/212939e9ae7dc451f8305bae1d120a483e61e429/docs/superpowers/research/evidence/sys1-representative-preflight-2026-10-01/native-supervision/hook_receipts.py
[stop-source]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/supervise.ts#L41-L230
[profile]: https://github.com/nisavid/provingkit/blob/212939e9ae7dc451f8305bae1d120a483e61e429/docs/superpowers/research/evidence/jev-axi-commit-observation-2026-10-02/profile.py
[transport]: https://github.com/nisavid/provingkit/blob/212939e9ae7dc451f8305bae1d120a483e61e429/docs/superpowers/research/evidence/jev-axi-commit-observation-2026-10-02/transport.py
[hook]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/commands/hook.ts#L141-L204
[portfolio]: https://github.com/nisavid/provingkit/blob/212939e9ae7dc451f8305bae1d120a483e61e429/docs/superpowers/research/2026-10-04-jev-axi-exploratory-opportunities.md
[shared]: https://github.com/nisavid/provingkit/blob/212939e9ae7dc451f8305bae1d120a483e61e429/docs/superpowers/research/evidence/jev-axi-consumer-opportunities-2026-10-04/shared-preparation.md
[method]: https://github.com/nisavid/provingkit/blob/212939e9ae7dc451f8305bae1d120a483e61e429/.agents/skills/handling-sys1-incidents/references/comparison-contract.md
[client]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/client.ts#L214-L290
[staged]: https://github.com/nisavid/provingkit/blob/212939e9ae7dc451f8305bae1d120a483e61e429/docs/superpowers/research/evidence/jev-axi-staged-push-preparation-2026-10-04/README.md
