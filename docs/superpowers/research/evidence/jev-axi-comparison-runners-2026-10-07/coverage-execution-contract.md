# Publication-coverage execution contract

This first batch compares ordinary evidence reconciliation with one deterministic relationship summary on two prepared candidates, four Responses profiles, and two presentation arms. It schedules 16 isolated cells and at most 80 requests. It measures controlled interpretation and navigation; it makes no native-benefit, publication-readiness, push-wide-coverage, safety, population-reliability, or utility/economic-superiority claim.

This is an execution proposal. The coordinator must bind final sources, equipment, routes, prices, evaluator separation, and accounting, obtain clean independent review of that revision, and record execution acceptance before provider requests. Synthetic wrapper/deadline checks establish only the constructed local behavior tested.

## Inputs and matched presentation

Before dependent execution, load `handling-sys1-incidents` and its maintained `references/comparison-contract.md` at the reviewed revision recorded in the invocation binding. Preserve producer, corpus, and key identities, verify outputs against that procedure, and return useful corrections to its maintained source. This increment changes no installed procedure.

The coordinator owns private spec, bindings, evaluator key, and evidence directories. Bind every complete source, snapshot/path/content association, comparison inventory and patch, acquisition/fileset manifest, packet, producer receipt, task, tools, evaluator key, contract, runner/wrapper/preflight source and dependencies, route documentation, and price record with byte count and SHA-256. Bind final Git revisions where applicable. Public artifacts use repo-relative paths and artifact identifiers. A packet passing runner validation does not establish acquisition correspondence. Material changes invalidate affected reviews before requests.

Use reviewed version-2 packets with exactly `version`, `task`, `common_context`, `relationship_summary`, `sources`, and `comparisons`. Keep the evaluator key and construction answers outside both consumer arms and all tool content. The first-batch evaluator key identity is `9133211def7e0961e04a9e036c370e0d1f6117f08d0a16b5ae05043a88fd0edd`.

Use this identical task in every cell:

> Explain what the supplied review supports for this commit candidate and identify anything needing closer inspection before making a review-coverage claim.

Both arms receive identical task, common context, source and comparison catalogs, tools, endpoint, billing route, authentication selector, and rates. The deterministic arm adds only `relationship_summary`; charge its preparation and any fallback. Ordinary access retains the complete report, record, review, verification, historical instructions, inventories, patches, and changed texts. Do not leak relationships through ordinary producer metadata, receipts, names, or context. Each cell starts fresh with no private history, shared answer cache, other-cell output, evaluator feedback, or authoring/publication action.

The consumer returns a concise cited note and useful next action, including correct non-action. It distinguishes candidate kind and identity, review scope, mechanical relationships, remaining gaps, and actual-push claims. No prescribed output template or numerical quality score is required.

## Cases and schedule

The first batch contains only `c01` and `c04`, both ready:

- `c01` is retained Git commit `5eb3a02a0d714901ea6f2a480601e6772d1e1d10` with parent `010133a2f1f9548ef49932528a67e36d45c8f0d2`.
- `c04` is the combined neutral overlay derived from that retained commit, identified by candidate-fileset manifest SHA-256 `b5dc3e5bde6643e583e22fe98c62f6f62ff82eb4fcfe2296663fb9d9c4ef4bd7`. This is a fileset identity, not a packet digest, historical commit, or observed push.

Profiles in first-occurrence order are `gpt-6-luna low`, `gpt-6-luna medium`, `gpt-6-luna high`, and `gpt-6.1-sol low`. Each has exactly one `ordinary` and one `deterministic` condition in the spec. Use `mode=comparison`; diagnostic mode does not qualify paired evidence.

Order cases `c01` then `c04` and profiles as listed. Ordinary runs first when zero-based case ordinal plus profile ordinal is even; deterministic runs first otherwise. Case ordinal comes from the ID: `c01` is zero and `c04` is three. Do not renumber `c04`. Verify the generated schedule equals the 16 cells. Run serially with concurrency one.

Each cell permits one initial request and at most four tool-result continuations, including a final-answer request: five submissions total. No automatic retry, repetition, diagnostic request, or Jev/Decisions digest-classification call is included. Six continuation cases and their source-fault adapters require separately accepted preparation and execution; they do not block or enlarge this batch. An intentionally unavailable source in a future prepared case remains a ready case so its behavior can be tested; inability to prepare a case is a different schedule-level outcome.

## Tool access and resource bounds

The `evidence` namespace exposes only:

- `read_source(source)`: one complete catalog source or explicit unavailability.
- `source_identity(source)`: snapshot, path, digest, and byte count, or explicit unavailability.
- `inspect_comparison(comparison, view)`: one complete `inventory` or `patch` with endpoints, or explicit unavailability.

Arguments name prepared catalog IDs. There is no shell, arbitrary Git command, batch-read function, external action, or report-writing tool. Snapshot/path identities stay distinct from map membership. Unavailable, absent, different, and outside-comparison evidence must remain distinguishable. A deterministic table cannot replace the review text for semantic scope or changed content/patches for inspection.

The proposed limits are `requests_per_cell=5`, `tool_operations=32`, `cell_seconds=480`, `request_seconds=120`, `input_bytes=262144`, `request_bytes=393216`, `response_bytes=1048576`, `tool_result_bytes=131072`, `tool_total_bytes=2097152`, and `run_seconds=9000`. No hard output-token control is requested. Reject oversized supplied sources or requests rather than silently truncating them. Preserve a capped response prefix and its terminal limitation.

`tool_operations` counts successfully prepared results. Prepare at most 32 results per cell; repeated reads and identity requests consume that budget. This does not bound all function calls emitted by a model to 32. Derive and retain every requested call from immutable output items, including invalid, duplicate, unsupported, over-limit, and unprepared calls. Count requested calls separately from prepared results, submitted result envelopes, and provider consumption. Retain prepared envelopes and digests, unused results, raw calls, and reasons for non-submission. Submitted replay bytes include repeated retained envelopes in later request history; they are not unique source bytes or known provider consumption.

The two prepared packets are 223,269 and 248,430 bytes. Constructed complete-access traces used 25 and 32 individual operations and four tool-result continuations; their largest envelope was 62,680 bytes, request 269,059 bytes, and cumulative submitted-result replay 542,488 bytes. These synthetic measurements do not guarantee useful model call grouping or that arbitrary navigation fits. Actual call identifiers, output/history, repeated reads, and serialization count against the same limits. Exhaustion preventing meaningful inspection yields `resource-incomplete`, not a correct abstention or demonstrated model failure.

## Routes and invocation interface

All cells use API-billed POST `https://api.openai.com/v1/responses` with Bearer authentication from `OPENAI_API_KEY`, streamed nonstored output, and supported stateless continuation using returned output items, matching `function_call_output` records, and `reasoning.encrypted_content`. No endpoint or billing switch is allowed. Freeze documented request/terminal schemas, efforts, and price assumptions. A completed answer or tool continuation requires an observed returned model exactly equal to the requested selector; no undocumented alias is accepted. Missing model identity leaves `model_unobserved` and stops that condition. Retain raw evidence and usage; failed or incomplete transport keeps its observed failure state rather than inventing an identity mismatch. Record effective effort, tier, and region only where raw evidence supplies them, otherwise null with a reason.

From the repository root, substitute private paths and printed digests:

```sh
python docs/superpowers/research/evidence/jev-axi-comparison-runners-2026-10-07/ordinary_preflight.py --spec "$coverage_spec" --spec-sha256 "$coverage_spec_sha256" --bindings "$coverage_bindings" --bindings-sha256 "$coverage_bindings_sha256"
python docs/superpowers/research/evidence/jev-axi-comparison-runners-2026-10-07/ordinary_invocation.py start --spec "$coverage_spec" --spec-sha256 "$coverage_spec_sha256" --bindings "$coverage_bindings" --bindings-sha256 "$coverage_bindings_sha256" --output "$coverage_invocation"
```

Preflight checks the exact matrix, matched arms, ceilings, dependencies, packet shape, and inference/evaluator bindings without submitting requests. The coordinator separately verifies acquisition correspondence and semantic separation; preflight's structural checks do not establish those facts.

`start` begins the whole-invocation clock before preparation, invokes `comparison_runner.py prepare`, verifies its manifest and 16-cell schedule, then invokes `comparison_runner.py run` with the same absolute `--deadline-monotonic-ns`. Requests receive only the remaining time. The clock continues through grading and handback; neither receives another 9,000 seconds. Linux is supported. Omit `--local-http`; it is reserved for synthetic loopback fixtures. At its child deadline, the wrapper sends SIGTERM, waits up to two seconds, then sends SIGKILL and reaps if necessary. Do not claim a hard bound for kill/reap completion. Cancellation does not establish that residual provider work or charges stopped.

## Failure rules

Shared identity drift, evaluator leakage, forbidden access/action, source truncation, shared runner defect, failed shared review, or compromised evidence integrity stops the invocation. Missing or invalid credentials and condition-specific route/model/usage failures stop affected conditions, leaving later cells unattempted; independently supported conditions may continue within accepted scope. Invalid accounting partitions prevent trustworthy aggregation and require diagnosis. Unknown charges or operator effort alone are accounting limitations.

Refusal, invalid/incomplete output, timeout, response cap, tool error, or resource exhaustion terminates its cell without concealed repair. The current scheduling policy may continue another cell of the same condition for these local outcomes. HTTP/provider/transport errors and explicit condition errors stop the condition. Retain exact terminal states and reasons. Semantic disagreement or false steering is graded after the fixed request phase; it prevents a pass and authorizes no selective rerun, feedback, or expansion. Expected source unavailability alone is not a global stop.

## Evaluator facts and grading

The following criteria are evaluator-only during execution. Both cases are critical; preserve the bound key and inference output unchanged. Close the request phase and fix all attempts before grading, while the outer clock continues through grading, review, correction, and handback. Use deterministic identity checks and coordinator evidence review, with no hidden grading-model call. Where practical, hide model/effort/arm labels for initial grading; record visible or inferable labels as blinding limitations.

The retained coverage key's grading procedure uses “after the invocation closes” to name fixed request-phase closure. The whole invocation remains open for grading, independent final result review, any correction, and handback. Preserve the bound semantic key and dimension names; bind those later artifacts in closeout events before `ordinary_invocation.py close`, using the original deadline.

For `c01`, the parent-to-candidate difference contains nine additions: seven equal content-map entries and two supporting records, `review.md` and `verification.json`, absent from the map. The separate review digest matches `4cfd2b2b638bcbe93029a77fa65e134f26ff8a69dc6575edc9c8966f6838a913`. The supplied review reports no actionable findings for seven public candidate files and projected tracker texts, with scope covering factual support, task scope, accounting, evidence boundaries, links, and prose. The ordinary explanation supplies the nine/seven distinction. Correct non-action is eligible; support-record absence alone establishes neither lack of review nor exemption and demands no new investigation.

For `c04`, the parent-to-fileset difference contains ten additions; relative to the retained commit it changes `README.md` and adds `publication-context.md`. Six map entries remain equal, README differs, and the two support records plus the added document are absent from the map. The separate review digest still matches. The changed README adds “The evidence records the declared scope of each source review.” The added document says `# Review context`, followed by “This note describes the public research materials considered for publication.” The note must account for and inspect both differences without extending the old byte-bound clean review to new bytes or inventing a defect. Required further handling must follow supplied instructions and the claim being made, rather than map absence alone.

Material conclusions need precise citations for candidate/comparison scope, map relationships, separate review association, review scope, and next action; `c04` also needs both changed texts. Catalog IDs are sufficient when they resolve snapshot/path uniquely. Relevant references are `d00` for complete candidate comparison, `s10` for map/review association, `s09` for review scope, `s00` for ordinary explanation, and `d01` or candidate `s18` and `s22` with comparison evidence for both changed texts. Historical README `s17` cannot establish new README content.

Record each scheduled cell exactly once, including failures and unattempted cells. Grade these dimensions independently as `pass`, `fail`, `incomplete`, or `ambiguous`, citing output passages and evidence:

| Dimension | Required behavior |
| --- | --- |
| Relationships | Correct candidate kind/scope, map relationships, review association, and both `c04` changes. |
| Evidence boundaries | Material claims stay within supplied evidence; candidate comparison establishes no actual outgoing range or accepted push. |
| Next action | Useful bounded inspection or correct non-action, without an invented obligation or unnecessary interruption. |
| Final quality | Coherent actionable note with sufficient material citations; no required wording or template. |

Record correction descriptively: visible correction and resolution, or `not_applicable` when no correction occurred. Record false steering separately: overlooked change, invented defect, mistaken review demand, unnecessary question, redundant warning/stop, or pursuit of harmless support-record absence. A correct conditional prerequisite is not automatically false steering. Missing conclusions/citations prevent a complete pass; a material false assertion fails; indeterminate meaning is ambiguous rather than completed by the grader. Retain observable grades beside resource/delivery limitations. Refusal, invalid output, incomplete delivery, timeout, failure, or unattempted status cannot establish a full cell pass.

A condition passes only when both critical cases have complete passing terminal notes, no false steering, and no reduced task quality against the matched ordinary result. No numerical score or cost-for-quality trade-off is introduced. Report cases before aggregates. Apply `invocation-accounting.md`, preserving all gaps; this increment does not rank economic utility or claim superiority. Accurate relationship tables alone establish no benefit. Native adoption requires a separately accepted ordinary publication episode.
