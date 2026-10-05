# Reported usage can be collected; complete episode accounting remains unqualified

I found a source-defined Codex response-usage record that can explain the retained shape mismatch. It offers a candidate route for bounded response accounting, with separate cumulative counters for reconciliation. I did not reopen the observed source, collect chat data, run a model, or change files. The accepted observation's usage, child costs, billing, quota, and active human effort remain unknown. Sources: [retained result](https://github.com/nisavid/provingkit/blob/19d6fe44277113d2d65c5f06e70e2c5bcecb9f1e/docs/superpowers/research/evidence/jev-axi-passive-observation-2026-10-05/results.md), [result projection](https://github.com/nisavid/provingkit/blob/19d6fe44277113d2d65c5f06e70e2c5bcecb9f1e/docs/superpowers/research/evidence/jev-axi-passive-observation-2026-10-05/observation-result.json), and Codex `TokenUsageRecord` below.

## Evidence boundary

The six frozen input digests matched before and after this read-only assessment. The dispatch's canonical plan, request, and model-selection digests also matched. The owning procedure is [handling-sys1-incidents](https://github.com/nisavid/provingkit/blob/19d6fe44277113d2d65c5f06e70e2c5bcecb9f1e/.agents/skills/handling-sys1-incidents/SKILL.md), with its [comparison contract](https://github.com/nisavid/provingkit/blob/19d6fe44277113d2d65c5f06e70e2c5bcecb9f1e/.agents/skills/handling-sys1-incidents/references/comparison-contract.md), especially whole-task accounting. I used the installed `research` skill's primary-source requirement; this dispatch's explicit prohibition on subdelegation and writes controls its usual delegation and file-output steps.

The frozen [selection procedure](https://github.com/nisavid/provingkit/blob/19d6fe44277113d2d65c5f06e70e2c5bcecb9f1e/docs/superpowers/research/evidence/jev-axi-passive-observation-2026-10-05/selection-and-accounting.md), step 5, admits usage under `event_msg`. The result reports top-level `token_usage_record` instead and says counters were not interpreted. That establishes a procedure/source mismatch, not the fields or completeness of the actual records. The source definitions below are pinned reference implementations; no build or source-version match to the observed desktop harness was established.

## Record shapes and collection surfaces

| Input | Source-defined route | Coverage and qualification limit |
| --- | --- | --- |
| Codex response usage | At OpenAI Codex revision `687a119f0fcaace47e1f1abcc77cec6c813fd6da`, [`TokenUsageRecord`](https://github.com/openai/codex/blob/687a119f0fcaace47e1f1abcc77cec6c813fd6da/codex-rs/protocol/src/protocol.rs#L2262-L2273) has thread, turn, session, root-turn, and response identities, `usage`, `turn_token_usage`, and `thread_token_usage`. | The definition calls it best-effort usage for a completed response. Actual retained records were not read or mapped to this revision. |
| Counter semantics | [`SessionState::record_token_usage`](https://github.com/openai/codex/blob/687a119f0fcaace47e1f1abcc77cec6c813fd6da/codex-rs/core/src/state/session.rs#L215-L250) copies supplied response usage, adds it to the latest matching turn counter, and adds it to the latest thread counter. | Response usage and cumulative snapshots overlap. Sum unique response usage, or take qualified cumulative differences; never add both. |
| Persistence and missing usage | [`Session::record_observed_response_completed`](https://github.com/openai/codex/blob/687a119f0fcaace47e1f1abcc77cec6c813fd6da/codex-rs/core/src/session/mod.rs#L4764-L4795) emits a raw completion event, returns when usage is absent, and otherwise persists `RolloutItem::TokenUsageRecord`. | Completion without usage has no usage record on this path. This is not a ledger of every attempted request or failed stream. |
| Existing app-server stream | [`ThreadTokenUsageUpdatedNotification`](https://github.com/openai/codex/blob/687a119f0fcaace47e1f1abcc77cec6c813fd6da/codex-rs/app-server-protocol/schema/json/v2/ThreadTokenUsageUpdatedNotification.json) requires thread/turn identity and `tokenUsage.total`/`last`. | It provides counters, not response identity or model attribution. Availability on the observed desktop transport remains unqualified; do not start a new server to manufacture this surface. |
| Exact upstream completion metadata | [App-server `ServerNotification`](https://github.com/openai/codex/blob/687a119f0fcaace47e1f1abcc77cec6c813fd6da/codex-rs/app-server-protocol/src/protocol/common.rs#L1956-L1959) marks `rawResponse/completed` internal-only. | A source definition does not grant the public client this route. Treat it as unavailable unless the owning client exposes and qualifies it. |
| Desktop summaries and completion waits | Current exposed contracts `mcp__codex_app__read_thread` and `mcp__codex_app__wait_threads` describe summaries/status, optional truncated outputs, and cursor-based completion results. | Neither contract promises a complete usage or attempt ledger. Snapshot correspondence cannot substitute for absent original accounting records. These tools were not called. |
| Model assignment and children | [Rolecasting `_NATIVE_MAXIMUM`](https://github.com/nisavid/provingkit/blob/19d6fe44277113d2d65c5f06e70e2c5bcecb9f1e/plugins/rolecasting/skills/delegating-cross-agent-work/scripts/native_codex.py) rates model and authority self-reported, while topology and execution result are controller-observed. | Requested selection and acknowledged child identity do not attest effective model execution or child token coverage. |
| Account limits | Current exposed `mcp__codex_app__get_usage_limits` contract offers account-shared used percentages, window lengths, reset times, and limit buckets; null/missing means unavailable. | A future authorized snapshot could describe account state. It cannot isolate this episode amid other account use. No limit tool was called; an attributable quota-debit or billing surface was not established. |

The pinned [`TokenUsageInfo`](https://github.com/openai/codex/blob/687a119f0fcaace47e1f1abcc77cec6c813fd6da/codex-rs/protocol/src/protocol.rs#L2275-L2339) accumulator also permits synthetic context-window fills. Separately, [`recompute_token_usage`](https://github.com/openai/codex/blob/687a119f0fcaace47e1f1abcc77cec6c813fd6da/codex-rs/core/src/session/mod.rs#L4846-L4877) can put an estimate in `last_token_usage`. These counter surfaces require provenance classification before arithmetic. [Resume/fork restoration](https://github.com/openai/codex/blob/687a119f0fcaace47e1f1abcc77cec6c813fd6da/codex-rs/core/src/session/mod.rs#L1599-L1628) restores prior usage records; a new process or physical file does not prove a zero baseline.

For possible ambient Jev calls through `jev-axi`, pinned revision `ed5e7c94248d2a639d471b6cbd427ba08abef773` supplies another source route. [`evaluate`](https://github.com/nisavid/jev-axi/blob/ed5e7c94248d2a639d471b6cbd427ba08abef773/src/client.ts#L214-L290) records cache hits with prior usage and zero milliseconds, records successful live calls afterward, and throws before that success record on error. [`UsageEntry`, `recordUsage`, and `readUsage`](https://github.com/nisavid/jev-axi/blob/ed5e7c94248d2a639d471b6cbd427ba08abef773/src/usage.ts#L11-L77) lack episode/response/retry identities, tolerate write failures, and skip corrupt lines. [`totals` and `estimateCost`](https://github.com/nisavid/jev-axi/blob/ed5e7c94248d2a639d471b6cbd427ba08abef773/src/usage.ts#L91-L138) are ledger categories and configured-price arithmetic. They do not prove invoices, saved provider work, or quota savings. No `jev-axi` ledger or configuration was read.

## Proposed bounded collection and checks

These are preparation checks for a separately accepted observation, not an executed collector or authorization to inspect more chats. They follow [selection-and-accounting.md](https://github.com/nisavid/provingkit/blob/19d6fe44277113d2d65c5f06e70e2c5bcecb9f1e/docs/superpowers/research/evidence/jev-axi-passive-observation-2026-10-05/selection-and-accounting.md) and the [comparison contract](https://github.com/nisavid/provingkit/blob/19d6fe44277113d2d65c5f06e70e2c5bcecb9f1e/.agents/skills/handling-sys1-incidents/references/comparison-contract.md).

1. Bind the producer revision, supported wrapper, episode, root turn, permitted threads, and start/end boundaries before collection. Preserve the existing complete-line, identity, byte, and span bounds. Admit top-level usage only after matching the producer contract; unfamiliar or incomplete fields remain gaps.
2. Retain raw response usage and cumulative fields separately. Preserve every occurrence with source offset/digest. Reconcile repeated response identities only with explicit matching identities and counters; conflicting duplicates remain unresolved. Do not sum event mirrors, repeated snapshots, inherited fork history, and response records as independent usage.
3. Check cumulative differences within the same counter lineage against unique response usage, field by field. A mid-turn start needs a proven preceding baseline. Missing endpoints, resets, synthetic estimates, compaction, or inherited history invalidate an unqualified difference. Do not clamp discrepancies to zero.
4. Preserve raw input, cache, output, reasoning, and total counters with their source semantics. Verify which are subsets before aggregation. Provider cache counts and `jev-axi` application-cache reuse need separate categories; a cached answer carrying old usage is not another provider attempt.
5. Join permitted children by controller-observed launch identity plus source thread/session/root-turn identities. Keep one bounded source contract per included child. Parent source absence proves no child coverage; shared root-turn identity does not prove the child inventory complete. Missing or inaccessible children remain unknown.
6. Retain visible attempt starts, response identities, terminal failures, cancellations, retries, and recoveries independently of success usage. A failed attempt may have unknown provider usage even when its failure is visible. Count the attempt and retain the gap; neither success-only ledgers nor completion counters can establish zero failed-attempt cost.
7. Keep requested, source-reported, and attested model identities distinct. Report unattributed usage without assigning it to the selected model. Delivery of a result or a cache hit is insufficient execution attestation.
8. Measure acquisition/import elapsed time, coordinator work, worker work, and operator effort separately. One orchestration-call duration cannot time nested operations independently. Shared acquisition is counted once in combined use; standalone and marginal work stay separate. Never infer active effort from elapsed time or silence.

| Required cost component | Bounded route or explicit gap |
| --- | --- |
| Research/setup, maintenance, preparation, and refresh | Source/review identities plus relevant coordinator actions and separately labeled timing or estimates. Untimed work remains unknown. |
| Retrieval, parsing, selection, packing, and reconciliation | Bound read traffic, selected spans, importer timing, and relevant collection calls. Reasoning and manual interpretation need direct measurement or explicit estimates. |
| Worker, child, and ambient model attempts | Qualified usage records plus attempt/terminal identities and permitted child sources. Failed, skipped, unreported, or unjoined work remains unknown. |
| Downstream checks, retrieval, retry, interruption, and recovery | Relevant visible call/results and ordinary outcomes, including failure. Off-record work and nested timings remain gaps. |
| Operator checking, clarification, or genuine resumption | Voluntary record of ordinary work, if it occurred, with uncertainty and logging burden. No manufactured exercise; absence remains unknown. |
| Measurement overhead | Acquisition, import, validation, interpretation, and any voluntary-record burden. Preparation and this research are costs even when not timed. |
| Money and quota | No attributable episode route established. Account snapshots and configured-price estimates may be separate descriptive measures, never substitutes. |

Sources for this table: [measurement routes and gaps](https://github.com/nisavid/provingkit/blob/19d6fe44277113d2d65c5f06e70e2c5bcecb9f1e/docs/superpowers/research/evidence/jev-axi-passive-observation-2026-10-05/selection-and-accounting.md#measurement-routes-and-gaps) and [comparison contract, item 7](https://github.com/nisavid/provingkit/blob/19d6fe44277113d2d65c5f06e70e2c5bcecb9f1e/.agents/skills/handling-sys1-incidents/references/comparison-contract.md).

## What is measured in the retained observation

The [result projection](https://github.com/nisavid/provingkit/blob/19d6fe44277113d2d65c5f06e70e2c5bcecb9f1e/docs/superpowers/research/evidence/jev-axi-passive-observation-2026-10-05/observation-result.json) reports three snapshots; 1,048,576 boundary-scan bytes, 8,388,608 antecedent bytes, and 245,526 appended bytes; and 10,973 selected bytes. Their sum is 9,682,710 bytes of read traffic, not distinct source coverage. Importer elapsed time is 0.010993350995704532 seconds and excludes startup/shutdown and final receipt serialization. The 194.571095-second admission-to-source gap is elapsed collection delay, not active work.

The [retained result](https://github.com/nisavid/provingkit/blob/19d6fe44277113d2d65c5f06e70e2c5bcecb9f1e/docs/superpowers/research/evidence/jev-axi-passive-observation-2026-10-05/results.md) distinguishes the successful once-only import from a subsequent coordinator validation failure and recovery. Recovery effort, setup/review work, coordinator active effort, operator effort, and agent/child usage are unknown. The projection reports no observation-induced worker message, extra worker run, Jev request, live change, or automatic retry; that does not establish absence of ambient work outside the retained selection.

## Source identities and verification

Frozen inputs, with SHA-256 verified twice:

| Source | SHA-256 |
| --- | --- |
| Observation `results.md` | `fe8ba1db19faec90fff908a4d55357f2d4706a638d9a7604f3e018db6a301358` |
| Observation `observation-result.json` | `89bc6388a5ab9da00652f13372bf162cc61baf41ea3b9a8d7127866ad127ae5d` |
| Observation `selection-and-accounting.md` | `f980694ac85b7fc2d2df23b89b8f6c4b93ad7ee6d5e31248f3e7751105e97196` |
| Observation `observation-contract.md` | `269f53d977e5faee870659049edf28d8bdeb3d6f8dca942d2dff450c793f3206` |
| `handling-sys1-incidents/SKILL.md` | `1d28f851542a0c7a11a190772630c941f224de5da7b4a776c3e62bcc6a3769ac` |
| Its `references/comparison-contract.md` | `9f876cd27c4bd6fe82d56feabc6e31e05d029d7cac18f9651194218e2e1aa981` |

The first four sources share directory `docs/superpowers/research/evidence/jev-axi-passive-observation-2026-10-05/`; the skill sources are under `.agents/skills/`. Additional inspected material:

| Source identity | SHA-256 or version boundary |
| --- | --- |
| `CONTEXT.md` | `7e9dac9fe2bdf9eec0e2cea0f7d3a23c042cbc53de3818b3aa6fced9ee085901` |
| `docs/superpowers/research/2026-09-29-sys1-context-and-accounting-source-read.md` | `34b3868de324ac70e372592eff5ac00e33a092299cc4a70ef56766d4532f538b` |
| Archival observer `docs/superpowers/research/evidence/sys1-context-2026-09-29/sources/r3-observer.py.txt` | `27df0b9daa9a1bbbfe5ea545d03fa0c0a90e08bd7e378d21942ece1c2b6b1729`; inspected as source, never executed |
| Rolecasting `native_codex.py` | `ee1b54ae187f3c5ef8f086668802079d72519e0ffeac31b82619e82e8d062e65` |
| Rolecasting `dispatch_adapter.py` | `dbf7199ce070cd0c8bd3df84c934a5b4eb58c0d3bbe0346389794808f21ae736` |
| Installed `research/SKILL.md` | `985569f15739c713d6784887c3d186d4ef9ac85bec5ad9c068d25bf0739928e4` |
| Exposed desktop tool contracts named above | Inspected definitions on 2026-10-05; tool version unreported; no runtime accounting qualification |

The two Rolecasting scripts share `plugins/rolecasting/skills/delegating-cross-agent-work/scripts/`. Public source bytes were fetched in memory at the immutable revisions cited above:

| Public source | SHA-256 |
| --- | --- |
| Codex `codex-rs/protocol/src/protocol.rs` | `d3d3d384da91b2824c10091de4331a2bc26ec5474887ed0aef1e3f3c4ae110f4` |
| Codex `codex-rs/core/src/state/session.rs` | `3dedb51926cd6d341c667daa0152d7e36d487e97119c2c0e2dcaab7a93df7e44` |
| Codex `codex-rs/core/src/session/mod.rs` | `aa75ddc17c151ef8bde8f0a66f016b65fb8044f83cca934ab4bfb4fb6c35c28f` |
| Codex notification schema cited above | `aba4f6c7e4a19b2b842c08ee793b57000c07dafd57b922ad0d8e7c76609108c2` |
| Codex `codex-rs/app-server-protocol/src/protocol/common.rs` | `d0cca691d21ffe282d3ca3d8ca9eaee8afe9aab058b04a3d4ef579f72a6918c7` |
| Codex `codex-rs/core/src/rollout.rs` | `1aa136709f80968ee68f4430efcffd6442a2837c34c7c7c78cc43bd83e738bf3` |
| Codex `codex-rs/rollout/src/recorder.rs` | `3a12d4f9813ceede9e6f616d4b669ba1b4af4c03d5e89c0f4a1c30704f53933d` |
| Codex `codex-rs/protocol/src/models.rs` | `916a595e136f4d7e32ce259f50678ffe818af2ea6a92f54d8628f57bfd4d43e7` |
| Codex `codex-rs/protocol/src/response_usage.rs` | `d3f05c8a7845b965f1a2910080d5a9c00c7e05dd2f7be73146829bab82053dfb` |
| Codex `codex-rs/core/src/client_common.rs` | `0125e520f71798e6c31a1d0147934c0d90288ab9cc4bfce6e8374ac587f2b43a` |
| `jev-axi` `src/client.ts` | `7fe1684556ccbcb1661b7abd9e95ebfad27fe1310e8e86e0abd3f422a5bccdbe` |
| `jev-axi` `src/usage.ts` | `2f498e615e6276d9a1c244b873dce4011fdc599f71a6fc315fe6a0aee5c7e2c8` |

Pinned repository directory listings were used only to locate source files. Guessed older recorder, core, and rollout paths returned HTTP errors; I did not treat them as source evidence. No observed-session history, private retained preview index, credentials, or live configuration was inspected.

## Remaining decisions

A next proposal needs a source/build match for its supported usage wrapper, a permitted child inventory and bounded child sources if whole-workflow coverage is claimed, and an episode boundary with complete baselines and terminal outcomes. The coordinator must decide which setup, maintenance, ambient, and shared work belongs to each reported scope and which required measures may remain unknown. The comparison contract requires the owning decision's reliability requirements and cost priorities before choosing a workflow; this assessment supplies neither a winner nor economic or security effectiveness claims. Source-supported preparation can continue, while observation execution and the separate Daybreak-held research retain their existing authority.
