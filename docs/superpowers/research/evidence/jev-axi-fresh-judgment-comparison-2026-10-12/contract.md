# Fresh judgment execution contract

Compare the current evidence-relation question with one ordered formulation on twelve fresh synthetic cases. The decision is whether a wording correction merits further development as an early System One check. This proposal permits no experiment until the operator accepts the concrete reviewed bindings.

## Inputs and claims

Use `construction.json`, complete fixture sources and drafts, `questions.json`, and the unchanged ordered meanings in `relations.json`. These sources cover accurate concise assertions, misleading scope extensions, contrary facts, conflicting accounts, and an ambiguous referent. They are diagnostic examples constructed after earlier errors, with explicit lexical cues and shared source bundles. They are not a random sample or a population reliability estimate.

The current question is byte-identical to the earlier comparison. The revised question asks the same single categorical judgment through an explicit decision sequence; it is longer, not a smaller evidence packet. It adds no intermediate provider request, source selection, answer repair, action recommendation, confidence threshold, or checking hint to a native author. Both formulations are tested on every model condition. If the sequence changes the meanings rather than their presentation, resolve that finding before execution.

Consume `handling-sys1-incidents` and its maintained comparison contract, and apply `adopting-jev` as recorded in [design application](design-application.md). Bind those source identities and the materially consumed Jev references listed there. Reuse `claim_producer.py` from the comparison-producers evidence directory. For each construction entry, bind its draft and ordered sources to the reviewed Git revision, preserving their hashes and full enclosing context. Supply the resulting complete `packet.md` to inference. Keep producer metadata, this contract, evaluator files, condition names, and other answers out of requests. All twelve ready cases use identical state bytes across conditions and treatments.

Keep `c13`, a copy of c01 with its sole source controlled unavailable, in the spec as unavailable. Verify producer exit 2, non-ready status, no observed digest or source file, unavailable quotation assessment, and zero semantic slots. It yields a separate fallback result, not an `unresolved` grade.

Bind all inputs, producer receipts, corpus manifest, evaluator key and grading, question/options, runner and wrapper source, dependency records, route and price evidence, and this contract by path, byte count, and SHA-256. Public paths are repo-relative. Private binding files record local execution paths. Review the final source commit and bindings; changed bytes or material dependencies invalidate affected review.

## Matrix

| Order | Adapter | Requested model | Effort |
| --- | --- | --- | --- |
| 0 | Jev Choice | `jev-1.13.0` | none |
| 1 | Decisions Choice | `gpt-6-luna` | none |
| 2 | Responses | `gpt-6-luna` | low |
| 3 | Responses | `gpt-6-luna` | medium |
| 4 | Responses | `gpt-6-luna` | high |
| 5 | Responses | `gpt-6.1-sol` | low |

Use claim spec version 2, with treatments `current` and `revised` in that order and case order c01 through c13. For each ready case at zero-based position i, rotate condition order by i modulo six. For each condition's original index j, request current then revised if i+j is even, otherwise revised then current. Verify the exact 144-slot schedule. Each slot gets one fresh independent request. The counterbalance reduces a fixed first-question ordering confound; one run cannot eliminate service or temporal variation.

Run serially with concurrency one, no retries, diagnostic requests, evaluator feedback, additional questions, or automatic substitution. Keep the four option keys and descriptions in their existing order across all requests. Jev and Decisions receive one Choice named `claim_relation`; Responses receives the same question and meanings and returns only the required JSON relation. Their different API output formats remain explicit.

## Routes and limits

Use the existing reviewed transports on Linux: Jev at `https://api.typesafe.ai/v1/systemone` with `TYPESAFE_API_KEY`, Decisions at `https://api.openai.com/v1/decisions`, and Responses at `https://api.openai.com/v1/responses` with `OPENAI_API_KEY`. Credentials remain runtime environment-backed. OpenAI uses the selected API key; no Pro-subscription route is assumed. No endpoint, provider, or billing switch is allowed.

The limits are request 120 seconds, whole invocation 9,000 seconds, input 65,536 bytes, serialized request 131,072 bytes, retained response 1,048,576 bytes, and one request per slot. Recheck request size before sending; never truncate sources. There is no hard output-token setting. The time and response limits do not impose a monetary ceiling or prove provider cancellation. All 144 requests may not fit the whole deadline; preserve incomplete results without a retry.

Use the existing `ordinary_preflight.py` and `ordinary_invocation.py` from `jev-axi-comparison-runners-2026-10-07` with the frozen spec and bindings and their SHA-256 arguments. Preflight submits zero requests. `start` begins the one outer clock before final preparation, creates and checks the prepared manifest, and passes the same absolute deadline to the runner. The clock includes grading, independent final result review, correction, and handback. Do not restart it for requests or closeout. Omit the test-only `--local-http` flag. The wrapper terminates a child at the deadline, escalates after two seconds, and reaps it; reap completion is not hard bounded.

A successful answer requires observed model identity equal to the requested selector, strict valid terminal output, and valid usage accounting. Preserve requested and observed effort/tier/region separately; unobserved effective values stay unknown. Jev/Decisions probabilities must satisfy the existing finite range and sum validation, but select no confidence threshold. Responses has no native option distribution. Retain raw bounded evidence, every attempted request, and all failures.

## Failure, grading, and decision

Identity drift, incorrect producer outcomes, evaluator leakage, source truncation, or a shared integrity failure stops all requests. A condition-specific failure stops every remaining slot for that condition across both treatments; other conditions may continue. A failure consumes its slot. Missing credentials leave that condition unattempted. Semantic disagreement is graded after the request phase and never adapts the schedule. Preserve timeouts, refusals, malformed output, route errors, model mismatches, and accounting failures distinctly.

Follow `evaluator/grading.md` and its frozen key. Grade each scheduled slot exactly once and show paired transitions before aggregates. Each condition/treatment combination must pass all twelve cases to meet the initial categorical feasibility bar. Do not exchange a new false intervention for an apparent gain without returning that trade-off to the operator. This is preparation toward a useful native check, not qualification of an integration: even perfect supplied-case results establish neither improved final authoring nor removed review work, operator savings, or whole-workflow economic superiority. Omission and deterministic organization remain eligible.

## Accounting and closeout

Apply `jev-axi-comparison-runners-2026-10-07/invocation-accounting.md`. Record the existing transport's input, output, cache-read, cache-write, and reasoning usage without double-counting reasoning already included in output; unknown fields remain unknown. Record returned usage and observed timing per attempt, requested-versus-observed model facts, normalized usage, API-equivalent value under `provider-facts.json`, available actual charges separately, and failed-attempt uncertainty. Do not call API-equivalent value an invoice or subscription quota consumption.

Count additional question tokens and complete preparation costs: fixture construction, independent labeling, sources, equipment changes, reviews, grading, corrections, operator interruptions, and handback. Separate one-time research/equipment work from any hypothetical recurring check. Unmeasured native-agent tokens, effort, billing, or timing remain unknown rather than zero. Collect whole invocation and per-stage UTC/monotonic intervals; total provider latency alone is not total work.

Close the fixed request phase before grading. Complete grading and independent result review, bind their artifacts and corrections in the closeout ledger, then run wrapper `close` under the original deadline. An overrun makes the timing claim incomplete. Ledger closure alone proves neither grading nor complete accounting. Publish a result with missing measurements alongside observations and no claim that supplied-case accuracy is an integration decision.
