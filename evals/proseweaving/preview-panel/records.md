# Preserve the comparison evidence

Issue 71 writes UTF-8 JSON records and raw artifacts in its evidence directory. These are fields to populate from observation, not claims already established by protocol preparation. Use evidence-relative artifact paths and reviewable URLs; keep local paths, account identifiers, and credentials out of published records. Each referenced artifact carries its SHA-256 digest.

## Run manifest

One frozen manifest contains:

- Schema version and unique run ID; start time in UTC; preparation and execution issue URLs; the acceptance/decision pointers that authorize the panel.
- Protocol commit and digests of all files in this directory; preparation source revision; qualified candidate source commit, artifact/archive digest, projection identity, and rollout receipt reference.
- Pinned corpus and fixture identities from `panel.json`, the comparison against candidate bytes, and any reviewed protocol amendment.
- Ordered model/harness panel; requested model selector, expected returned identity if exposed, reasoning effort, fast/thinking mode, sampling controls or explicit `not-exposed`, output/token limits, harness version, common prompt/settings digest, and availability observation time. Freeze all model-affecting settings; never assume two model aliases mean the same service.
- Grader and adjudicator identities and settings under the current model policy; the fixed rubric identity; the randomization seed; the full coordinate schedule and opaque-ID mapping in coordinator-only storage.
- Per route, the reviewed launch recipe, discovery surface, tool-denial mechanism, controllable-context inventory format and opaque/common harness-instruction limits, and activation evidence mechanism. Record unsupported routes explicitly.
- Final expected coordinate count, generation start boundary, and the orchestrator's pre-output manifest reference.

## Attempt record

One record per attempt contains:

- Unique attempt ID; coordinate (track, panel entry, case, route, condition, repetition); prior failed attempt ID for the permitted transport retry; scheduling position and timestamps.
- Manifest reference; protocol/candidate/corpus/prompt/fixture digests; exact raw input artifact; condition-specific invocation prefix/event; actual candidate-bundle file inventory and digests.
- Actual harness and returned model identity; actual settings; session and provider request/response IDs when exposed, with explicit unavailability otherwise. A missing provider ID is not an invented ID; retain the harness session and immutable transcript references needed to distinguish attempts.
- Controllable context inventory and digest, isolated configuration identity, freshness/isolation evidence, tool events, and discovery/activation trace artifacts. Writing `activation_status` is `bundle-delivered`, `failed`, `unverified`, or `not-applicable` for disabled controls. Routing `selection_status` is `selected`, `not-selected`, or `unobservable`, independently of expected pass/fail.
- Outcome: `completed`, `transport-failed`, `refused`, `empty`, `truncated`, or `blocked`; raw response artifact and digest when present; usage/latency when exposed; error evidence without credential data.
- Comparison validity: `valid` or `invalid`, with reasons such as `isolation-unverified`, `rubric-leak`, `baseline-contaminated`, `executor-tool-use`, `input-drift`, `model-drift`, `route-unsupported`, `activation-unverified`, or `activation-failed`. Source plugin loading through a writing-executor tool remains tool use under the pinned delivery contract. Routing probes separately retain their allowed selection/loading events and flag any unrelated tool use.

## Grade record

A blinded record contains the opaque output ID, raw response digest, case ID, rubric and source-expectation digests, grader identity, evidence for each expectation, every factuality failure span and tag, the quality-score vector, derived quality fraction, and pass/fail. Keep the grader's complete raw response with its digest. Validation or arithmetic performed by the coordinator does not replace the original grade.

Adjudication appends the reviewed issue, evidence, decision, adjudicator identity, and resulting score or tag changes; it never overwrites the original grade. The adjudicator receives the same blinded evidence. Freeze the adjudicated scores before joining the coordinator's condition/model map.

## Summary and selection record

Report expected, completed, valid, missing, and excluded coordinates per panel entry and route. Include the reason for every exclusion; observed automatic non-selection stays in the routing denominator and is judged against its case expectation. Report bundle-delivery counts and separate native routing outcomes, factuality failures by tag and arm, quality distributions, and both paired deltas per case.

Record each example's case, group eligibility across all repetitions, panel-order selection, fixed repetition-1 selection, raw artifact references, excerpt byte offsets if used, exact excerpt bytes/digests, and intended README evidence link. Record skipped cases and their reason. Preserve failed and superseded attempts with their original identities so the published subset remains auditable.
