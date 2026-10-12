# Ordinary-work baseline and accounting contribution

**DONE_WITH_CONCERNS.** This contribution supplies a bounded baseline, ledger, and grading procedure for one prospective observation of the capability-assessment report associated with [issue 548](https://github.com/nisavid/provingkit/issues/548). It supports preparation of the joined observation contract. Collection and execution remain unaccepted.

The observation can establish when adequate claim evidence becomes available, what preparation adds, and whether a useful early checking opportunity remains. It supplies no model hint and measures no intervention effect.

## 1. Workload and admission

The frozen `workload-metadata.json` identifies:

| Binding | Supplied value |
| --- | --- |
| Ordinary task | Capability assessment associated with issue 548 |
| Branch | `ivan/research/peer-portfolio-sys1-548` |
| Verified starting base | `61b99e73ebedf8afb33b28a531daea8089504394` |
| Planned report | `docs/superpowers/research/2026-10-12-system-one-portfolio-capabilities.md` |
| Prospective section | Capability/source/evidence table and accompanying claims about what each mechanism can and cannot prove |
| Historical availability | Report absent at the metadata check; no draft commit or review artifact identified |
| Continuation | Owner proceeds without waiting |
| Study state | Observation unaccepted; content collection unstarted |

These are supplied metadata, not my inspection of the workload. I did not read its worktree or report.

**Proposed admission rule:** immediately before acceptance, obtain a metadata-only confirmation of task identity, report path, current revision, and whether the selected section has completed required final review. Repeat that check immediately before execution. Neither check collects report content.

- If the selected section remains eligible before required final review, admit it prospectively.
- If its eligible window has passed, record `missed_window`, with the observed boundary and its evidence. Stop this invocation.
- If eligibility cannot be established, record `eligibility_unknown`; do not collect retrospectively.
- A task, report, or section substitution requires a revised contract and acceptance.
- Ordinary author judgment alone does **not** close eligibility: an independent check might still arrive before reuse or required review.

Report existence or absence alone cannot establish whether the checking window remains open. The owner must not pause ordinary work to preserve it.

## 2. Ordinary baseline and prospective selection

The baseline is the owner's authorized work: writing the selected report, choosing and reading sources, forming citations and support explanations, revising claims, completing required review, and preparing publication. Existing task instructions and ordinary corrections continue.

Choose the **first material evidence-based assertion** in the prospectively named section after admission. “Material” means a statement about a mechanism's capability or evidentiary limit that could change the section's conclusion. Select without searching for a known defect or injecting one. Preserve its enclosing row or paragraph and its ordinary citations. Retain one assertion and one or two sources.

If the first eligible assertion needs more than two sources, an unavailable source, or inaccessible evidence, record that input limitation. Do not silently choose a more convenient assertion.

Maintain three distinct states:

1. **Evidence adequate:** the bounded supplied context contains the referents and source material needed to examine the assertion.
2. **Producer supported:** identities satisfy the current claim producer's commit/path/digest and draft-coordinate requirements.
3. **Early opportunity available:** evidence readiness precedes identifiable remaining support work, reuse, or required review.

The current producer requires commit objects and complete source blobs. A plain file snapshot can establish observational availability, but it is not a supported producer invocation. Do not create an extra commit to feed the observation. A semantic support judgment is also separate from producer readiness.
Source: `docs/superpowers/research/evidence/jev-axi-comparison-producers-2026-10-07/claim_producer.py`, `validate`, `read_blob`, and `prepare`.

## 3. Proposed collection envelope

The workload/evidence lane must replace unresolved artifact bindings below with exact permitted paths, identities, and acquisition routes before acceptance. No broad history collector is needed.

| Artifact family | Proposed maximum | Purpose |
| --- | --- | --- |
| Selected report | Three captures: initial eligible draft, one natural revision/reuse checkpoint, terminal version; each at most 256 KiB | Preserve assertion, context, citations, and ordinary changes |
| Selected sources | One or two complete files, each at most 128 KiB | Establish evidence available at the first checkpoint |
| Ordinary review and publication records | Four explicitly bound existing artifacts, collectively at most 1 MiB | Findings, candidate association, reconciliation, terminal result |
| Existing task-owned usage/timing export | One bound artifact, at most 256 KiB, if available | Source-reported accounting |
| Observation ledger, bindings, and receipts | Collectively at most 256 KiB | Acquisition and interpretation accounting |

Allow at most **ten workload artifact captures**, **8 MiB total content acquisition**, and **2 MiB retained workload content**. Repeated reads charge the acquisition pool again. Hashing reads and producer reads also charge it; a producer receipt is not a complete physical-I/O counter. Stop before an indivisible read would exceed its limit.

Start after accepted execution admission. End at the first terminal ordinary publication-preparation result, withdrawal, workload mismatch, unavailable required source, exhausted budget, or **30 minutes elapsed wall time**. Record pauses; do not restart the clock. Permit one final bounded reconciliation of already admitted artifacts, within **10 minutes elapsed**, without reopening collection.

Publication preparation is eligible only if it occurs naturally inside the window. A later publication is unobserved. No recurring monitoring, extra handback, forced pause, or automatic continuation is added.

For each capture, preserve artifact identity, exact bytes or admitted excerpt coordinates, digest, acquisition timestamp, and why it was selected. A timestamp establishes observation time unless an existing artifact independently establishes earlier availability.

**Packaging branch:** if an ordinary pre-review commit and pinned sources exist, the accepted contract may permit one deterministic claim-preparation invocation, with its case specification, output, failure, receipt, and cost retained. Otherwise retain an observation-only snapshot envelope and mark the current producer unavailable. No model request is permitted in either branch.

## 4. Event ledger

Use one append-only ledger. Record an explicit terminal state for each planned stage, including unobserved stages.

```text
event_id, parent_event_id, task_id, assertion_id
kind, cost_bucket, purpose, actor
observed_at_utc, source_time, timing_basis
artifact_refs[{path, revision_or_snapshot, sha256, coordinates}]
attempt_id, response_id, cumulative_lineage
state, outcome, evidence_basis
bytes_acquired, tool_operations
elapsed_ms, active_effort_estimate_ms
usage{input, cached_input, output, reasoning, semantics}
valuation{currency, rates_revision, calculation}
actual_cost{amount, attribution_source}
shared_cost_id, consumer_ids
missing_fields, interference, invalidates
```

Use `measured`, `owner_reported`, `estimated`, or `unknown` for each measurement's basis. Null means unknown, not zero. Preserve duplicate occurrences; deduplicate only with supported identities and declared rules.

Useful event kinds are: `admission`, `ordinary_write`, `ordinary_source_access`, `support_explanation`, `assertion_selected`, `input_available`, `package_attempt`, `collection`, `reuse`, `claim_revision`, `review_finding`, `review_revision`, `operator_interruption`, `publication_reconciliation`, `attempt_terminal`, and `observation_terminal`.

A source delivered through a tool is an observed access event, not proof of reading, comprehension, or thought. No event does not prove no work occurred.

## 5. Cost buckets and measurement routes

| Bucket | Include | Measurement route and limit |
| --- | --- | --- |
| Ordinary authoring and evidence work | Writing, ordinary citation selection, source access, explicit support explanations | Existing admitted artifacts and visible task-owned action records; undocumented effort remains unknown |
| Special selection and packaging | Choosing the study assertion, locating identities, coordinates, hashing, case specification, deterministic preparation | Observer ledger and receipts; distinguish ordinary citation production from study-specific binding |
| Collection overhead | Captures, parsing, omission decisions, retention, ledger production, interpretation | Acquired bytes, operations, observer elapsed intervals, supported usage |
| Subsequent reuse and revision | Observed uses of the assertion, source rereads, edits, obsolete products, refresh | Artifact differences and explicit references; inspect only admitted report/records |
| Required review | Review preparation, review attempts, findings, adjudication, revisions, re-review | Existing review artifacts tied to reviewed bytes; retain failures and stale reviews |
| Operator effort | Actual questions, interruptions, recovery, ordinary checking | Existing explicit records; one optional estimate only after actual checking, with reporting burden counted |
| Publication reconciliation | Selecting candidate and records, digest association, changed-text inspection, manual explanation | Ordinary publication artifacts; preserve candidate versus actual publication distinction |
| Research preparation | This preparation, integration, contract review, procedure design | Separate study setup account; never fold into observed ordinary-task cost |
| Unobserved work | Earlier work, omitted actions, unavailable counters, work after stopping | Explicit gap register with scope and effect on conclusions |

A study-specific source reread that itself resolves support belongs to special preparation, even if its output is subsequently useful. Work can have several purposes but one cost-bearing event. An existing ordinary action is not charged twice because the observer also uses its artifact.

Record every available in-scope attempt, including failed, cancelled, skipped, retried, stale, and unused work. A retry has a new identity. Successful output does not erase preceding failure costs. Existing ambient assessments, if exposed by admitted records, remain separate ordinary/ambient events; no added model hint does not establish their absence.

Do not claim complete whole-task totals when only the selected section or part of the window is covered. Provide observed subtotals plus unresolved components.

## 6. Tokens, money, timing, and shared work

**Tokens.** Prefer existing task-owned provider receipts or harness exports with unique attempt/response identities and documented counter semantics. Preserve input, cached input, output, and reasoning breakdowns where reported. Establish whether counters are per-response, cumulative, or cached historical records before summing. For cumulative records, require matching lineage and valid endpoints. Do not subtract incompatible totals.

If the admitted artifacts supply no counters, report `usage_unknown`. Do not inspect private histories or launch requests to recover them. A zero newly added semantic-request count can be known from this contract; total ordinary-task usage cannot thereby be called zero.

**API-equivalent valuation.** Compute only for supported usage using an identified, accepted rate schedule, model/route, currency, effective date, cache treatment, and reasoning-token treatment. Prevent double counting when reasoning is included in output. Distinguish missing usage from missing rates. Freeze the rate source before execution; this preparation performed no price lookup. Valuation is a list-rate equivalent, not a bill.

**Actual cost and quota.** Report attributable actual cost only from an authorized existing billing record with a defensible attribution rule. Subscription price, token counts, and API-equivalent value do not establish marginal billing or quota consumption. Without that evidence, retain both as unknown.

**Timing.** Record acquisition and producer duration from observer monotonic intervals or supported receipts; record ordinary tool duration only where its artifact exposes it. Keep:

- Input-readiness-to-next-use or review intervals.
- Tool/request elapsed duration.
- Observation elapsed window.
- Voluntary active-effort estimates.

None is exact active effort. Do not sum overlapping intervals into whole-task latency. A multi-operation orchestration duration does not identify each operation's duration.

**Shared work.** Give each shared capture or package one `shared_cost_id`. Count it once in combined totals; retain each consumer's additional interpretation cost separately. Standalone attribution may include the complete shared production cost, but standalone totals must not then be added together. Show unresolved allocation explicitly. No amortization or assumed future reuse enters this episode's total.

These rules consume the maintained whole-task method in `.agents/skills/handling-sys1-incidents/references/comparison-contract.md`, especially items 7–8 and its terminal handback requirements.

## 7. Outcomes and narrow decisions

| Observed branch | Supported decision |
| --- | --- |
| Adequate, supported inputs precede explicit remaining support work | Prepare a later reasoning-replacement comparison naming the actions a replacement would remove |
| Author has already expressed a support judgment, but inputs precede reuse/review | Preserve the independent-checking opportunity; investigate added checking separately from replacement |
| Required review later corrects a material overstatement and an earlier adequate checkpoint existed | Supports an earlier error-detection hypothesis; track observed propagation and correction, without claiming prevention |
| Evidence exists early, but no ordinary commit does | Record useful evidence availability and the current reader limitation; snapshot-route development needs separate preparation and review |
| Study-specific preparation performs the proposed replacement work | This placement lacks demonstrated replacement value; independent checking still needs its own benefit hypothesis |
| Ordinary publication performs repeated relationship navigation or reconciliation | Prepare a deterministic delivery comparison retaining the ordinary explanation as its baseline |
| Ordinary work already supplies the needed result and no concrete remaining benefit appears | Retain ordinary handling for this observed scope |
| Source is unavailable, the selected assertion exceeds scope, the window is missed, or costs/events are unknown | Return the precise limitation; no automatic replacement observation |

A useful early checkpoint does not require a baseline mistake. Conversely, a later correction does not establish that Jev would have detected it, arrived in time, or reduced rework.

Do not classify every post-judgment check as redundant. “Redundant replacement” means the hypothesized reasoning work is already performed and no remaining action has been identified for removal. Independent checking is a separate hypothesis whose added costs and possible error-detection benefit remain open.

The controlling qualification is in `docs/superpowers/research/evidence/jev-axi-integration-investigations-2026-10-12/README.md`, “How the two recommendations join” and “The next test I recommend.”

## 8. Comparability and observation interference

This is one passive episode, not paired arms. It cannot establish savings, calibration, causal effect, frequency, economic superiority, or general uselessness.

For a later comparison, retain the same material task outcome, supported evidence boundary, ordinary authoring freedom, required review, and terminal-quality criteria. Compare complete workflows, including preparation, false alarms, consumption, refresh, recovery, and unused outputs. Do not compare a cheap relation call with an ordinary whole task.

Observation may change behavior through awareness, capture requests, packaging, or an optional effort record. Log those exposures and their timing. Keep observer analysis and study packages from the author during this baseline; ordinary necessary corrections must still proceed. Record any correction triggered by observation as interference, rather than attributing its consequences to unassisted ordinary work.

The coverage producer's direct-parent comparison and identity relationships do not establish actual outgoing publication or review sufficiency. Capture the ordinary comparison kind; do not force it into that producer's supported shape.
Source: `docs/superpowers/research/evidence/jev-axi-comparison-producers-2026-10-07/coverage_producer.py`, `prepare`.

## 9. Join requirements and acceptance checklist

The workload/evidence lane must supply exact source bindings, permitted acquisition routes, eligible checkpoint rules, contextual adequacy criteria, artifact-version relationships, and a source-grounded terminal-quality rubric. It must identify how an evaluator distinguishes a supported claim, a bounded limitation, and an overstatement without supplying model hints.

Before execution acceptance, confirm:

- Fresh task eligibility and explicit handling of a missed window.
- Prospective assertion-selection rule and one-or-two-source ceiling.
- Exact allowed artifact paths/routes, byte limits, capture limits, and stopping clock.
- Observation-only snapshots versus supported producer inputs.
- Review/candidate association and publication scope.
- Available counter semantics, rate source, and actual-cost route—or explicit unknowns.
- Failure, unused-work, shared-cost, interference, and gap rules.
- No added semantic request, extra ordinary commit, forced pause, or substitute workload.

**Gradeable completion:** each planned stage has a measured result, bounded negative result, or precise unknown; each reported fact maps to admitted evidence; every acquired artifact and available attempt reconciles to the ledger; budgets and stopping conditions reconcile; every cost bucket is measured, estimated, or unknown; each proposed next decision states its supporting observation and causal limit.

Missing usage may leave economic conclusions incomplete while still permitting an input-timing result. Missing checkpoint order prevents an early-opportunity conclusion. Missing terminal review prevents a final-quality conclusion. An unexplained absent stage makes the handback incomplete.

## 10. Procedure capture and closure

Treat this as a proposed observation-specific accounting procedure, not an installed convention. The coordinator should place the joined, reviewed contract beside its workload binding and require the executing consumer to load that revision before collection. Its handback must record the consumed revision, ledger, gap register, terminal condition, and supported next decision. Broader equipment promotion remains a separate decision.

I used `research` and `capturing-agent-procedures`; this child performed the research delegation without further delegation. I verified the request digest and all ten manifest file hashes and sizes before and after inspection. They matched. The supplied source base is `5be38ce96e36b08d017fc1e2cfb5bcf9ff606d03`; I did not independently inspect Git state.

My effective execution is this native child in the current harness. Harness instructions identify a GPT-6-based agent; permitted evidence supplies no product attestation of the exact deployed model or effort. I therefore make no exact-model attestation. The coordinator reported standing admission `sys1-observation-accounting-preparation-v2-standing` for this preparation; it grants no collection or publication authority.

All lane-owned inspection and preparation are complete. I made no edits, network requests, producer/model launches, subdelegations, workload-content reads, private-history reads, or external actions. No child work remains running. Output preservation, admission closure, independent review, integration, and publication remain with the coordinator.