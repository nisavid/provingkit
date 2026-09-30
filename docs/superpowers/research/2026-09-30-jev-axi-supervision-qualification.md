# Context, accounting, and method for the supervision comparison

The first `jev-axi` supervision comparison has an accepted purpose and reliability bar, a reusable comparison method, and identifiable observation routes. Its context and accounting still need qualification at the native PostToolUse boundary before judgment trials. The retained evidence supports specific hook mechanics and candidate observation routes; it does not demonstrate useful loop detection, off-track correction, or diagnostic value.

This report joins [Establish real context and cost accounting for the selected jev-axi comparisons](https://github.com/nisavid/provingkit/issues/334) and [Qualify the reusable method for catalog-wide behavior-assignment comparisons](https://github.com/nisavid/provingkit/issues/335). I applied their shared [accepted supervision scope](https://github.com/nisavid/provingkit/issues/333#issuecomment-5904778399): all agreed critical cases must pass, with no added false steering, redundant stops, unnecessary questions, or task-quality loss on matched legitimate work. Additions need useful native task effects; replacements must remove model work; diagnostic-only scores need demonstrated value to a named consumer. Complete costs and unknowns remain visible under the existing interruption and constrained-model-capacity priorities.

## Inspected identities and evidence limits

I inspected Provingkit `2e468ce7860d510365c787bfece844d10d77907b` and `jev-axi` [`a1fe6190c65b528ad5b85cbe276fd4b68bdeb236`](https://github.com/nisavid/jev-axi/tree/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236). Both trees were clean before this report. The integration's hook, supervision, question, safety, and client source files match the earlier native candidate `ed5e7c94248d2a639d471b6cbd427ba08abef773`. This permits source-mechanics reuse, not extension of the older native observations to new tasks.

Read-only version queries on September 30 returned Claude Code 2.1.284 and Codex CLI 0.159.0. Those match the earlier context/accounting probes' CLI versions. No model session, hook, fixture, or live configuration change was run for this investigation. No current installed-hook configuration was inspected. Jev is the assessment service; `jev-axi` owns the input preparation, questions, policy, hook output, and local bookkeeping discussed here.

The two research workers inspected context and accounting independently. I investigated method ownership and joined their findings against the primary source. Reported source behavior, retained native observations, injected judgments, and proposed measurement routes remain separate below. Investigation and review costs were not measured and are not treated as zero.

## Context available at judgment

[`superviseHook`](https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/commands/hook.ts#L144) records a PostToolUse event before checking assessment cadence. Missing session identity, a nonassessment cadence, or an empty job skips assessment. The default is every ten recorded calls. An assessed PostToolUse invocation sends a job and bounded tool events, with a six-second timeout and zero SDK retries. It does not send the full conversation, a diff, or the transcript's separately extracted recent output.

[`readTranscript`](https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/supervise.ts#L148) selects only the first and latest recognized user prompts. It excludes prompts beginning with `<`, assistant referents, and intermediate amendments from the resulting job. Malformed and unknown lines are skipped. Claude and Codex have separate recognized record forms; source support for a form is not proof that every current native record is covered.

The job is capped at 4,000 characters. [`recordEvent`](https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/supervise.ts#L207) retains thirty events, each with the first 400 input characters and last 400 result characters. Events have no timestamp, turn identifier, or explicit outcome classification. [`buildObservation`](https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/supervise.ts#L45) redacts event excerpts when preparing assessment state; the local event record precedes that redaction, and the job itself does not pass through the redaction function. Any later candidate must define its permitted data boundary before sending real task material.

| Judgment requirement | Available input and qualification gap |
| --- | --- |
| Current task and accumulated amendments | First/latest prompts can omit intermediate requirements; existing native records establish nonempty jobs, not complete intent. |
| Referent behind an answer such as “that approach” | The current job excludes assistant turns. A separate PreToolUse probe observed referents; that route is not yet qualified for PostToolUse. |
| Legitimate iteration versus an unproductive loop | Tool excerpts may show repeated operations but omit changing causes, verification results, or the reason for repetition. Classification accuracy is unmeasured. |
| Missing input and questions already answered | Selected prompts and excerpts provide partial evidence. Earlier missing-input outcomes do not establish a complete question/answer-state reader. |
| Actual tool outcomes and governing instructions | Serialized response excerpts supply no dedicated outcome or instruction schema. Candidate receipt of relevant instructions needs observation. |
| Session binding, freshness, and unavailable context | The integration uses a transcript path and session-keyed state. General resumed, compacted, malformed, or unavailable-context behavior remains unqualified. |

These omissions explain an input boundary. They do not prove that a particular score was wrong. A context-supplied candidate needs an observed way to obtain the task facts its criterion requires before the judgment; an evaluator-authored summary cannot supply that qualification.

## Assessment and Stop interactions

PostToolUse sends all four [`PROGRESS_WORKER` questions](https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/recipes/questions.ts#L358) in one evaluation. `meaningful_progress` is recorded but does not select a verdict. [`decideProgress`](https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/supervise.ts#L60) gives `needs_human` precedence over stuck and off-track scores. Quiet escalation can therefore suppress steering; that score is not purely diagnostic in the current policy. Steering emits context asking the agent to reconsider the original request and ignore an incorrect note. Continue and escalation emit no note.

The first recorded PostToolUse event captures a Git baseline and existing untracked files **after the first completed tool action**, before cadence and missing-job skips. Stop uses that stored baseline and otherwise falls back to a HEAD-based diff. Removing the entire hook changes this input to Stop; removing only assessment does not necessarily do so. Stop separately assesses job, diff, and recent transcript output, rather than worker events. See [`sessionBase` and `workDiff`](https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/supervise.ts#L107) and the [Stop branch](https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/commands/hook.ts#L178).

The protocol must distinguish removing a question, a score's policy effect, an emitted note, an assessment call, and the whole hook. It must also preserve or explicitly vary Stop's baseline. Shared context and assessment costs are counted once, not credited independently to every question.

## What the native records support

The built-correction records for [Claude supplied input](evidence/sys1-built-2026-09-28/claude-supplied.json), [Claude missing input](evidence/sys1-built-2026-09-28/claude-missing.json), [Codex supplied input](evidence/sys1-built-2026-09-28/codex-01580-supplied.json), and [Codex missing input](evidence/sys1-built-2026-09-28/codex-01580-missing.json) retain Claude Code 2.1.283 and Codex 0.158.0 requests with nonempty jobs, worker-question identities, injected high `needs_human` scores, quiet escalation, native outputs, and bounded task effects. They do not retain full assessment state or transcripts in their public projections. The Codex missing-input observation required offline reanalysis after a rollout-flush warning. These are mechanics and delivered-instruction observations, not loop/off-track accuracy or task-benefit comparisons.

The [Claude alpha](2026-09-28-sys1-claude-alpha.md) observed one real `continue` assessment on 2.1.284. Other hooks errored, and the original file-effects check failed before the separately approved reapplication. Its accepted scope remains intact; it does not qualify diagnostic or steering benefit.

The [context/accounting probes](2026-09-29-sys1-context-and-accounting-source-read.md) observed ordered user turns and an assistant referent in fresh Claude 2.1.284 and Codex 0.159.0 sessions at **PreToolUse** file boundaries. Their reader, counter reconciliation, and retained records are useful starting evidence. The archival reader is not a qualified runnable PostToolUse adapter. Matching CLI version numbers do not close that gap.

## Complete-task accounting boundary

| Required observation | Available route and limit |
| --- | --- |
| Every invocation, assessment, skip, failure, and delivery | Current hook logs follow successful assessments. Missing session, cadence skips, missing jobs, and caught failures can return without a verdict record. Best-effort decision logs lack session/turn/attempt identifiers. Instrument and join these events; silence alone is ambiguous. |
| Provider attempts and cache reuse | `evaluate` logs successful results and cache hits; thrown calls can escape before usage recording. An archival fetch observer can retain individual attempts, but does not cover failures before fetch, process termination, or native delivery. Its PostToolUse use needs qualification. |
| Context and state preparation | Account for retrieval, parsing, selection, redaction, packing, session-file work, and baseline Git commands. Earlier parse timings do not include all these stages. |
| Native model work through terminal outcome | Earlier Claude result/cumulative reconciliation and Codex thread/turn counter reconciliation establish reported-usage routes. They do not prove complete usage, quota debit, or billing. Include continuation, failure, recovery, and correct non-action. |
| Time | Preserve preparation, judgment, hook, and episode intervals with their boundaries. Hook work overlaps episode elapsed time; do not add it twice. Instrumentation also costs time. |
| Useful correction, false steering, questions, and task quality | Retain emitted output, native receipt, subsequent actions, requirements/amendments, final artifacts, verification, and terminal outcome. Apply the accepted task rubric; a changed next action or plausible note is not benefit. |
| Diagnostic value | The stats command exposes summaries and reasons but supplies no demonstrated consumer benefit. A named diagnostic task needs evidence of use and benefit, with collection/maintenance costs. |
| Operator, setup, and maintenance effort | Record these separately from recurring episode work. Synthetic controller messages do not measure human effort; unknown past or future effort stays unknown. |
| Money and constrained capacity | Ledger categories and configured-price estimates are not invoices or attributable quota measurements. Keep reported tokens, prices, money, and capacity distinct. |

Primary source: [`evaluate`](https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/client.ts#L214), [`usage`](https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/usage.ts#L11), and [`superviseStats`](https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/commands/stats.ts#L127). Retained instrumentation and its limits: [provider observer](evidence/sys1-whole-workflow-2026-09-29/sources/source/provider_ledger.mjs.txt), [native accounting](evidence/sys1-whole-workflow-2026-09-29/sources/source/accounting.py.txt), and [whole-workflow results](2026-09-29-sys1-whole-workflow-comparison.md).

Parallel trials need separate session state, caches, logs, and attempt records. The cache key includes model/state/questions, not arm or episode identity; hits retain historical usage. Session-state updates are read-modify-write operations. Separate local roots cannot establish independent provider quotas, native prompt caches, queueing, or host load. The protocol must reserve or serialize shared resources and report residual interference rather than treating concurrent latency as a clean comparison.

## Maintained method and consumer path

The canonical method is [handling-sys1-incidents](../../../.agents/skills/handling-sys1-incidents/SKILL.md), especially its [comparison contract](../../../.agents/skills/handling-sys1-incidents/references/comparison-contract.md). Repository `AGENTS.md` names that owner and requires matching Claude projections. I verified byte equality for the skill and both references. Their SHA-256 values match the [retained downstream invocation](evidence/sys1-method-2026-09-29/downstream-invocation.json):

| Source | SHA-256 |
| --- | --- |
| `SKILL.md` | `1d28f851542a0c7a11a190772630c941f224de5da7b4a776c3e62bcc6a3769ac` |
| `references/evidence-record.md` | `08923f4920817c839a159e3b6003da6b07fde7df68ad1872927dff59de8bdb9a` |
| `references/comparison-contract.md` | `9f876cd27c4bd6fe82d56feabc6e31e05d029d7cac18f9651194218e2e1aa981` |

On the inspected branch, the skill and comparison contract last changed in `8e1e170ab9437849a48e21d230e92dc9dcbf15a3`; the evidence reference last changed in `698aa24f6775e0930753ed359e9812433a0583e0`. The older report records the pre-merge reviewed revision; matching bytes preserve that evidence without equating the commit identities.

The installed `adopting-jev` skill is skills-manager-owned from `shiftynick/jev-axi`, with bytes matching [`skills/adopting-jev/SKILL.md`](https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/skills/adopting-jev/SKILL.md). It supplies Jev fit and integration guidance. Its mutable prices, model names, and benchmark claims were not revalidated here and are not used as current measurements. Live documentation must be checked before integration design or numerical claims.

The comparison contract already covers replacement versus addition, omission and deterministic alternatives, actual context before judgment, native outcomes, complete costs, and purpose-specific requirements from the owning decision. This cohort can explicitly invoke it unchanged as an intake aid, supplying the accepted supervision and diagnostic criteria at the protocol join. That use does not establish automatic discovery for every proactive catalog task or reliable autonomous adjudication. The [method evaluation](2026-09-29-sys1-whole-workflow-method.md) retains consumer compliance limits, including unproven amortization handling.

The next consumer must load these exact method bytes, the accepted scope, and this context/accounting boundary. It must reconcile [the evaluation-scoping owner](https://github.com/nisavid/provingkit/issues/251) before freezing model/profile choices. No new generic constructor, installed convention, or method source edit is justified by the present evidence.

## Required join before trials

The runnable contract must settle workloads and critical cases, exact interventions and fallbacks, diagnostic consumers, task rubrics and effect thresholds, source/build/model/profile identities, cadence, Stop treatment, order, and resource scheduling. It must obtain native PostToolUse context and measurement qualification before admitting a judgment trial, preserving failed and skipped qualification attempts.

The resulting claim can concern observed quality, interventions, corrections, diagnostic benefit, reported counters, and elapsed costs in frozen cells. Complete accounting gaps restrict economic claims; constructed cases do not establish population reliability. The [remaining-family purpose decision](https://github.com/nisavid/provingkit/issues/339) stays independent unless a concrete shared behavior changes this cohort. No live rollout or upstream submission follows from this investigation.
