# Decomposed judgment execution proposal

Compare Jev's direct evidence-relation judgment with four narrower judgments combined by code, alongside the same questions answered by Decisions and ordinary models. The decision is whether this design merits a later workflow trial as an early System One check. This preparation permits no experimental request until the operator accepts the reviewed concrete bindings.

## Inputs and meanings

Use the 24 fresh synthetic cases in [corpus/construction.json](corpus/construction.json), with their complete draft contexts and ordered sources. The [independently adjudicated key](corpus/evaluator/key.json) has six supported, six contradicted, six unsupported-extension, and six unresolved cases. These constructed diagnostic cases share sources within six families; they are not a random sample or a population reliability estimate. The exposed R17–R20 development checks and earlier experiment cases are excluded.

[selected-questions.md](selected-questions.md) controls the question meanings and combination. [questions.json](questions.json) supplies their frozen API text. Direct uses the unchanged four-way question and option descriptions. Decomposed asks interpretability, relevant conflict, incompatible fact, and complete warrant in that order. All four answers are required. The combination uses categorical selections, no confidence threshold, probability fusion, statistical independence assumption, answer repair, or automatic fallback.

Consume `handling-sys1-incidents` and its maintained comparison contract, together with `adopting-jev`. Bind the consumed procedure sources. Use the reviewed `claim_producer.py` from `jev-axi-comparison-producers-2026-10-07`, with draft and source identities at the frozen Git revision. The model input is its complete `inference.json`: assertion, draft context, and ordered sources with neutral IDs and full text. Verify equality with the independently labeled packet before freezing it. Do not use the provenance-bearing Markdown packet as inference. No evaluator label, rationale, source path, Git identity, other answer, or construction note enters requests.

Prepare c25 as a copy of c01 with its first source selected and controlled unavailable. Require producer exit 2, non-ready status, no observed source digest or source file, unavailable quotation assessment, no `inference.json`, and zero semantic slots. This is a fallback control, not an unresolved assertion.

Bind corpus files, original label reports, adjudication, key and grading, selected questions and API text, producer and receipts, inference bytes, runner/preflight/wrapper and transport dependencies, procedure sources, route/rate evidence, and this contract by path, size, and SHA-256. Private bindings identify local paths; public records use repo-relative paths. Review the final source commit and prepared bindings. Changed bytes or material dependencies invalidate affected review.

## Matrix and delivery

| Order | Adapter | Requested model | Effort |
| --- | --- | --- | --- |
| 0 | Jev Choice | `jev-1.13.0` | none |
| 1 | Decisions Choice | `gpt-6-luna` | none |
| 2 | Responses | `gpt-6-luna` | low |
| 3 | Responses | `gpt-6-luna` | medium |
| 4 | Responses | `gpt-6-luna` | high |
| 5 | Responses | `gpt-6.1-sol` | low |

Use claim specification version 3, treatments `direct` then `decomposed`, and case order c01–c25. At ready-case position i, rotate the six conditions by i modulo six. For a condition's original position j, use direct then decomposed if i+j is even, otherwise decomposed then direct. Freeze and independently check all 288 slots. Every ready case uses identical inference bytes across all conditions and treatments.

Run serially, with one fresh request per slot, one repetition, and no retry, additional development call, automatic substitution, or feedback. There are at most 288 request groups, 720 question instances (144 direct plus 576 decomposed), and 144 combinations. Count all questions even when an earlier answer determines the final relation. A request containing four questions is billed and timed once using its returned request-level usage.

Jev sends a named map of one or four Choice questions; Decisions sends an ordered list of one or four Choice questions. Responses sends the same instructions and option meanings and requires either the original single-relation JSON object or one four-field JSON object. Tools are omitted. Jev documents independent questions over shared state; Responses can reason jointly. Preserve that distinction rather than claim identical internal execution. The direct request encoding remains unchanged from the prior comparison. No four-request decomposition fallback is permitted.

The newer Jev 1.14 preview is not substituted for the previously used 1.13 selector. [Provider facts](provider-facts.json) record the public interface and rate evidence checked for this proposal. Documentary support and fake-service tests establish no live access or successful provider execution.

## Routes, limits, and response validity

Use the existing Linux transports: Jev at `https://api.typesafe.ai/v1/systemone` with runtime `TYPESAFE_API_KEY`; Decisions and Responses at their respective `https://api.openai.com/v1/decisions` and `/v1/responses` endpoints with runtime `OPENAI_API_KEY`. OpenAI uses the selected API key. No documented Pro route has been established for Decisions; no provider or billing-route substitution is permitted.

Limits are 120 seconds per request, 9,000 seconds for the whole invocation, 65,536 input bytes, 131,072 serialized request bytes, 1,048,576 retained response bytes, and one request per slot. Never truncate sources. There is no hard output-token or money cap. These time and retained-response limits do not prove provider cancellation or guarantee that all 288 slots fit the allowance.

Use `ordinary_preflight.py` and `ordinary_invocation.py` with the frozen spec/binding hashes. Preflight sends no request. `start` creates the one outer clock before final preparation, binds the prepared manifest, and passes the remaining absolute deadline to the runner. Omit the test-only `--local-http` flag. Grading, independent result review, correction, and handback stay inside that same allowance. The wrapper terminates an overdue child, escalates after two seconds, and reaps it; final reap time is not hard bounded.

A usable answer requires successful transport, exact observed requested-model identity, a valid terminal envelope, and valid usage accounting. Preserve requested and observed effort, tier, and region separately; unreported effective values remain unknown. Reject duplicate JSON keys, missing/extra/reordered Decisions names, wrong types, unknown options, and refused or incomplete answer sets. Jev map order is immaterial; its names must match exactly. Require all four structurally valid answers even when an earlier semantic gate would decide the relation. Preserve partial/raw evidence without repairing it.

For Jev and Decisions, confidence and option probabilities must be finite numeric values in [0,1], excluding Booleans. Require precisely the supplied option set and a probability sum within absolute tolerance 0.000001 of one. Do not clamp, renormalize, choose an argmax, or apply a confidence threshold. Responses requires exactly the selected output keys and values. The supplied categorical choices feed the frozen combination.

## Failure and decision

Shared source drift, wrong preparation outcomes, evaluator leakage, truncation, or integrity failure stops requests. A condition-specific operational failure stops that condition's remaining slots across both treatments; other conditions may continue. Missing credentials leave that condition unattempted. Every failure consumes its slot and retains incurred or uncertain work.

A structurally valid `unanswerable` or inconsistent combination is a semantic outcome. It produces no final relation, fails that critical case, and does not stop later slots. Correct `unresolved` remains a substantive match. Do not adapt questions, sources, schedule, or key to observed answers during the run.

Apply [grading.md](corpus/evaluator/grading.md). All 24 critical cases must pass for a condition/treatment to meet the bounded feasibility bar, including all six accurate concise assertions. Report every paired outcome, category and family counts, component diagnostics, and incomplete pairs before aggregates. A better average cannot compensate for a new false intervention. Return any proposed relaxation as a trade-off.

Omission and deterministic evidence preparation remain references with no semantic request or claimed accuracy. This isolated comparison does not demonstrate improved authoring, removed review work, operator savings, calibration, or whole-workflow superiority. Even a complete pass only supports considering a later native comparison where evidence is available early enough to help. It authorizes no hook change or new `jev-axi` behavior assignment.

## Accounting and closeout

Apply the runner's [whole-invocation accounting](../jev-axi-comparison-runners-2026-10-07/invocation-accounting.md). Record request groups, question instances, bytes, available input/output/cache/reasoning tokens, API-equivalent value under the frozen rates, observed timing, and available actual charges separately. Never multiply request usage by four or double-count reasoning already included in output. Unknown effective billing terms or counters remain unknown; API-rate value is not an invoice or subscription-quota measurement.

Count source preparation, complete state transmission, parsing, combination, grading, independent review, corrections, failures, and handback. Record the local combination interval separately. Carry corpus construction, independent labels and adjudication, equipment changes, and protocol reviews as research/setup work, with measured and unmeasured components explicit. Separate those costs from a hypothetical recurring check without assuming free amortization. Operator interruptions and unreported active effort are not zero.

Close the fixed request phase before grading. Bind grades, independent result review, corrections, and handback evidence into the original invocation ledger before `close`. A deadline overrun or missing measurements remains a limitation. Ledger closure alone proves no grading pass, complete cost accounting, or useful integration.
