# Collection routes for current intent, verification, and usage

Bounded history paging and per-response usage are concrete source-defined candidates for the next passive observation. Neither is yet qualified on the observed desktop service. Check-time file identities and off-record operator actions cannot be recovered from a completion summary alone. This report resolves source research for [Establish collection routes for intent, verification, and usage](https://github.com/nisavid/provingkit/issues/435); it authorizes no further collection.

The independent [intent and evidence report](intent-and-evidence.md) and [accounting report](usage-and-accounting.md) preserve the first passes before this join. The accounting copy corrects integration attribution and resolves repository links. The [research record](research-record.json) retains their original hashes and declared edits. Both consume the maintained [comparison procedure](../../../../../.agents/skills/handling-sys1-incidents/references/comparison-contract.md) unchanged.

## Supported routes and remaining gaps

| Input | Candidate route | What remains unqualified |
| --- | --- | --- |
| Requests and amendments | Bound chat-summary pages or persisted turn/item pages; select relevant user messages and referents | Coverage of initiating intent and all relevant changes, origin, truncation, and temporal consistency |
| Candidate and verification | Existing contemporaneous artifact identities joined to command inputs, outputs, and result occurrences | A later file read cannot establish the bytes checked earlier; missing original bindings remain unavailable |
| Agent and operator decisions | Relevant visible actions and an optional voluntary record of ordinary checking or resumption | Delivery is not consumption; off-record actions, active effort, and absent events remain unknown |
| Response usage | Source-matched `TokenUsageRecord.usage`, reconciled with turn/thread cumulative counters | Producer/build match, duplicates, missing usage, failed attempts, counter lineage, and child coverage |
| Estimated thread cost | Source-defined `account/usage/read` with a thread ID | A callable route on the owning service, billing-route availability, episode/child coverage, and estimate accuracy |
| Billing and quota | No attributable episode route established | Thread estimates and account-wide limits do not establish invoices or episode quota debit |

These routes come from the two reports, the [current tool contracts](tool-contracts.json), and the coordinator's [local protocol projection](protocol-source-excerpts.json). The tool contracts expose summary reads and completion waits, not complete original history or a usage ledger. They were inspected without calling them on a chat.

## What the current protocol adds

The coordinator ran schema generation with `codex-cli 0.160.0`; it exited successfully with a read-only PATH-alias warning. This generated definitions without starting an app-server session, reading a chat, or making a model request. The projection records full-source hashes, selected definitions, and omissions. It is not a self-contained schema or evidence that the desktop's running service implements the same version.

`thread/turns/list` accepts a page size, sort direction, and item view; the default item view is `summary`. `thread/items/list` can filter one turn, accepts a continuation cursor or an exclusive item anchor, and exposes optional producer timestamps with each item. Both responses define continuation cursors. These definitions make bounded paging a specific preparation candidate, beyond the older projection's mention of the methods. A page size alone does not bound response bytes, and no consistent-snapshot guarantee was established. A future collector must retain updates, duplicates, missing timestamps, and truncation rather than infer an immutable history.

`account/usage/read` accepts an optional thread ID. Its response describes estimated thread usage when the billing route is available, including estimated credits, optional estimated dollars, and groups with optional model, effort, and token fields. This is more specific than the exposed account-limit tool, but no callable desktop route or runtime result was obtained. It does not remove the need for per-response attribution or demonstrate actual billing.

The accounting report's pinned public Codex source separately defines best-effort usage for completed responses and cumulative turn/thread counters. The coordinator fetched and matched the five core Codex and `jev-axi` source files supporting accumulation, missing-usage persistence, resume/fork restoration, estimates, cache reuse, and success-only ledger limits. This confirms those source claims, not their match to the earlier observed installation. Requested models, source-reported models, and execution attestation remain separate.

## Join before another contract

Prefer an existing supported paging route if its read behavior can be established without resuming or changing the worker. Otherwise retain a specifically bounded local source selection. For either route, establish the workload, relevant antecedents, source/build identity, byte and page bounds, candidate/check joins, response-usage semantics, permitted children, and terminal condition before execution. A missing historical artifact or unrecorded check-time identity is an unavailable input, not a reason to rerun the worker under a passive observation.

Local preparation can exercise pagination, byte ceilings, partial pages, changed items, duplicate occurrences, missing amendments, check-to-candidate joins, cumulative baselines, failed attempts, and inherited child history with synthetic data. Those checks would qualify collection mechanics only. A later accepted observation must establish delivery and supported data on its actual route; it can retain narrower findings when some measures remain unknown. This report implements no collector and adds no standing approval requirement beyond the already reserved acceptance of each concrete experiment.

Completion, discovery, resumption, staged claim checking, and publication-obligation checking may reuse matching records. Share acquisition and candidate identities where they actually match; retain each consumer's decision and marginal effort. Count shared work once and keep standalone cost visible. This join does not block independent staged/push preparation or relax the consequential-action research's Daybreak hold.

Research, source acquisition, schema generation, review, selection, and integration are preparation costs. Their model usage, active effort, money, and quota were not measured here. The prior observation's unknown costs remain unknown. No new observation, Jev assessment, live change, behavior assignment, or saving is established by this packet.
