# Whole-invocation accounting

Each ordinary comparison retains preparation, request, interpretation, grading, review, correction, fallback, operator, and handback work under one invocation identity. API-rate equivalents, attributable charges, provider-defined subscription usage, elapsed time, and active effort are separate quantities. Missing measurements remain unknown. This increment makes no utility/economic-superiority or native-benefit claim.

## Binding and records

The coordinator owns private specs, bindings, evaluator keys, and ledgers. Public reports use artifact identities and repo-relative paths. Freeze every source, producer receipt, procedure revision, corpus/acquisition/fileset manifest, inference packet, question/task/tools, evaluator key/grading procedure, contract, runner/wrapper/preflight source and dependencies, route record, and price record with byte count and SHA-256. Material changes require fresh affected review before execution. Record execution acceptance separately from preparation, synthetic tests, review, and publication.

The wrapper bindings document has exactly `version`, `kind`, `invocation_seconds`, and `dependencies`. Use version 1, the comparison kind, and an allowance no greater than 9000 seconds. Each dependency has exactly `role`, `id`, `path`, `sha256`, and `bytes`. Required roles are `runner`, `contract`, `procedure`, `corpus`, `route`, `price`, `evaluator`, and `inference`; bind exactly one runner and every case's inference input. Include additional sources/equipment under unique role/ID pairs. Claim corpus bindings include `manifest` and `c11-packet`. Spec, bindings, and prepared manifest have separate identities. Their presence proves no completed execution or semantic separation.

Use invocation ID, manifest digest, runner run ID, neutral case/condition IDs, slot ordinal, and attempt ordinal to join records. Reconcile 60 claim slots or 16 coverage cells and at most 80 coverage attempts. Keep scheduled, reserved, attempted, skipped/unattempted, failed, cancelled, discarded, and unused work distinct. A reserved request without submission is preparation and unused capacity, not a provider attempt or a saving. Retain failed first preparation and every separately authorized later invocation with distinct identities.

The runner writes `run-identity.json` before request work and a `submission-*.json` boundary record immediately before each transport call. That boundary record means submission is uncertain; it does not establish transmission. A returned transport result establishes submission through an attempt or updated reservation, or non-submission through a `not-submitted-*.json` record. An interrupted submitted request without a completed attempt retains unknown usage and residual provider work. Reconcile uncertain reservations separately from observed submissions and unused capacity.

Every submitted attempt binds its slot, case, condition, serialized request digest/size, response evidence digest/size, adapter/source revision, endpoint, provider request ID where observed, requested model/effort, observed returned model/effective effort/tier/region, billing route, terminal status, raw output/events, and raw usage/scope. Exact observed returned-model equality is required for a completed answer or continuation. Missing model identity is `model_unobserved`; failure evidence remains retained. A failed/incomplete transport retains its observed failure state rather than an invented model mismatch. Never accept an undocumented alias.

Derive response byte counts and digests from the retained `request-evidence.json` inventory and its hashed bodies, rather than assuming absent attempt fields were collected. Derive effective effort, tier, and region only from explicit retained raw fields; otherwise record null and a reason. Do not infer them from requested controls or a pricing row. Retain acquisition counters in their documented units: logical producer bytes are neither physical I/O nor model tokens. Time producer completion externally; receipt timing omits completion of receipt writing.

For coverage, enumerate every `function_call` output independently, including malformed, duplicate, unsupported, over-limit, unprepared, and unused calls. `tool_operations` is the count of successfully prepared results, capped at 32 per cell, not all requested calls. Keep prepared envelopes, their digest/size, submission/replay counts and bytes, unused result IDs/reasons, and unknown provider consumption separate. Repeated replay is charged to submitted bytes each time; it does not create another unique source or establish consumption.

The metadata loader accepts at most 1 MiB per specification, bindings, state, or closeout JSON document. Input and response-body allowances are separate. Existing output destinations are refused; a failed attempt remains retained and receives no automatic retry.

## Whole clock and closeout

`ordinary_invocation.py start` starts UTC and an identified monotonic clock before final preparation. Bind its process-clock identity, start/deadline readings, actual runner run ID, preparation interval, request interval, and retained artifacts. The runner receives the same absolute deadline and only the remaining whole allowance. The maximum 9000 seconds includes preflight/preparation, requests, interpretation, grading, review/correction, and handback. Close the request phase before grading; the outer clock continues. No hidden grading-model request is included.

The current wrapper applies the deadline to its subprocess jobs: SIGTERM, up to two seconds of grace, then SIGKILL/reap if necessary. Kill/reap completion is not hard bounded, and client cancellation proves neither cessation of provider work nor final charges. Grading and handback occur between `start` and `close`; the coordinator manages the remaining allowance. `close` detects an overrun and records `deadline_exceeded`, rather than granting another allowance or proving a hard execution bound.

Use UTC for correlation and monotonic intervals from the same identified clock for durations. Record start/end, actor, purpose, and evidence for all phases. First-byte latency requires same-clock start/first-byte observations and is distinct from terminal typed-answer completion. Do not sum overlapping parent/child intervals as elapsed time. Report elapsed spans and attributed active work separately. Voluntary approximate operator effort is estimated, includes recording effort, and retains its basis; unreported operator effort is unknown. Record interruption cause, needed operator action, and observed recovery without attributing every pause to the candidate.

After request-phase closure, deterministic grading and evidence review produce immutable grade records and handback evidence. Hash those artifacts and include them in the events document. From the repository root, close with private paths and printed digests:

```sh
python docs/superpowers/research/evidence/jev-axi-comparison-runners-2026-10-07/ordinary_invocation.py close --state "$invocation_state" --state-sha256 "$invocation_state_sha256" --events "$closeout_events" --events-sha256 "$closeout_events_sha256" --output "$invocation_ledger"
```

`start` prints the state path/digest. `close` verifies retained artifacts and ledger evidence, records elapsed span and missing phases, and prints the final ledger path/digest. Its `closed_with_gaps` status is a ledger outcome, not a clean experiment, grading pass, complete-cost assertion, or native-benefit result. A deadline-exceeded handback cannot claim completion within the accepted allowance. Preserve partial results and limitations.

After unsuccessful child exits, `start` binds available stdout/stderr, every retained run file in `request-evidence.json`, and reconciled request/slot identities in `run-recovery.json`. Completed runner attempts remain authoritative for usage and valuation; recovery records do not create a second total. Remaining slots retain an interruption or non-submission reason. Evidence binding continues when the allowance has expired so stopping preserves incurred work; its elapsed time remains inside the reported whole span and can produce a deadline overrun. Unreadable or inconsistent records leave a failed, explicitly unreconciled state. `close` rejects changes to the bound run inventory, including added files.

In the retained evaluator instructions, “after the invocation closes” names closure of the fixed request phase. Grading, independent final result review, correction, and handback occur before whole-invocation `close`, with their immutable artifacts bound through events. This lifecycle interpretation changes no semantic key, grade name, or evaluation dimension.

## Outer event schema

The closeout document has exactly `version` and `events`, with version 1. Each event has exactly `id`, `phase`, `purpose`, `recurrence`, `actor`, `evidence`, and `measurements`. IDs are unique. Every evidence reference has `path`, `sha256`, `bytes`, and an unambiguous `selector` for a field or range.

Allowed phases are `acquisition_selection`, `source_resolution`, `extraction_hashing_rendering`, `preparation`, `request_work`, `interpretation`, `required_review`, `correction`, `fallback`, `source_refresh`, `grading`, `operator_recovery`, `handback`, `setup_research`, `equipment_implementation`, `fixture_construction`, `source_review`, `operator_effort`, `interruptions`, `billing`, and `subscription_usage`. Include observed, explicitly unknown, or not-applicable records for every required component. Wrapper intervals do not replace missing active-effort or cost records.

Purpose is `experiment_setup`, `experiment_evaluation`, or `ordinary_workflow`; recurrence is `one_time`, `per_invocation`, `per_case`, `per_attempt`, or `on_change`. These are independent: repeated grading is evaluation work; required ordinary review remains ordinary workflow work. Research, equipment construction, fixture authoring, source review, and maintenance stay separate from recurring selection, preparation, requests, interpretation, correction/fallback, refresh, review, recovery, and handback. Report observed experimental totals and proposed ordinary-workflow components separately.

Each measurement has `name`, `value`, `unit`, `status`, and `basis`. Status is `observed`, `derived`, `estimated`, `unknown`, `not_applicable`, or `invalid`. The last three have null values with explicit reasons; non-null values require evidence. Currency uses decimal strings. A template filled with unknowns does not establish measured work.

## Tokens, prices, and charges

Retain complete provider usage and its documented scope. Distinguish per-request from cumulative or unknown counters; sum only distinct non-overlapping scopes. Cumulative deltas need matching session/stream identity, documented reset semantics, and a previous endpoint. The first cumulative observation is not automatically new work; interim stream snapshots are not added to terminal totals.

Preserve total input I, cached input C, cache-write input W, output O, reasoning output R, and provider-specific counters. Negative, Boolean, fractional, inconsistent, or malformed counters are invalid, never clamped. Validate C + W <= I and R <= O where supplied. Reasoning is included in output and is not charged twice. Missing is unknown, explicit zero is zero, and not-applicable needs endpoint evidence. Keep known subtotals with observed/missing/invalid/not-applicable counts; report a complete total only when relevant counters, scope, and prices are known and valid.

Use the frozen Standard short-context USD rates per million tokens from official provider sources retrieved on 2026-10-09, with route documentation rechecked on 2026-10-10:

| Condition | Input | Cached input | Cache-write input | Output |
| --- | --- | --- | --- | --- |
| Jev | 0.042 | No separate charge | No separate charge | Free |
| Decisions `gpt-6-luna` | 0.10 | No separate charge | No separate charge | No charge |
| Responses `gpt-6-luna` | 0.10 | 0.01 | 0.125 | 0.50 |
| Responses `gpt-6.1-sol` | 2.00 | 0.10 | 2.50 | 10.00 |

Sources are [OpenAI pricing](https://developers.openai.com/api/docs/pricing), [Decisions](https://developers.openai.com/api/docs/guides/decisions), and [TypeSafe models](https://docs.typesafe.ai/models). Bind retained source digests, retrieval dates, currency/unit, exact selector, endpoint, context range, Standard tier, and no-region-surcharge assumption. OpenAI short context is at most 272,000 input tokens. Effective tier/region and applicable adjustments remain observed or unknown independently of this declared equivalent. These frozen rates are documentary valuation inputs, not confirmed charges or live inference access.

For Responses, API-rate equivalent is `((I-C-W)*input_rate + C*cached_rate + W*write_rate + O*output_rate)/1000000`. Missing required partitions or applicable rates leave it unknown; omitted cache-write tokens are not zero unless the bound endpoint contract establishes that meaning. Jev/Decisions use `I*input_rate/1000000`; missing output counters do not prevent documented input-only valuation, but remain missing token evidence. Keep any zero-priced output counters.

Record attributable actual charges only from provider billing evidence with identity and time range. Bills including unrelated work do not establish per-attempt charges. Provider-defined subscription records keep their units, scope, window/reset, and concurrent-work limitations. All OpenAI comparison conditions here are API-billed; claim no Pro quota saving or token-to-quota conversion. Unknown money, quota, effective effort, operator effort, and residual provider work remain null with reasons. They are neither free work nor an invented execution gate.

## Reconciliation and handback

Count each observed shared event once. Allocated arm views declare beneficiaries and nonnegative weights summing to one, including unallocated share; allocation is an assumption rather than another observation. Standalone scenarios may duplicate necessary preparation but are not added to actual experimental spending. Do not amortize setup without an accepted reuse assumption.

Retain failures, cancellations, discarded/unused results, unknown usage, and residual provider work. Stopping never erases incurred work. Before handback, reconcile every scheduled slot/cell, reserved request, actual submission, retained body, requested function call, prepared/submitted/unused result, grade, interruption, and ledger entry. Report unused capacity separately. Join runner attempts by identity without copying them into a second total. List accounting gaps and the conclusions each prevents; retain all case-level outcomes before aggregates.

Independent final result review checks the inventory, every grade, accounting joins, and claim limits. Review and correction are evaluation costs. Neither ledger closure, a correct table, nor a known classifier-call value establishes complete-workflow superiority, native benefit, author correction, required-review replacement, or activation. Claim and coverage invocations retain independent acceptance and closeout; neither depends on a compatibility observation.
