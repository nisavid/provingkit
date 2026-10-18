# Jev's probability contract leaves the numerical tolerance unresolved

The inspected TypeSafe sources describe a normalized Choice distribution but do not establish a numerical acceptance band. The earlier comparison's `0.000001` sum tolerance is therefore a local protocol requirement, not a verified provider guarantee. Its preserved response genuinely sums to `0.99` before client validation. Neither finding changes the original grade or repairs the two categorical ambiguity errors.

This investigation resolves [Establish the Jev probability-output contract before reusing response validation](https://github.com/nisavid/provingkit/issues/609). The remaining provider guarantee is explicitly unresolved. A future protocol must decide how it uses probability diagnostics before freezing validation; no replacement tolerance, normalization, experiment, or behavior assignment is selected here.

## What the original records establish

The attempt, request body, and response body for direct c14 match the [published retention inventory](../jev-axi-decomposed-judgment-results-2026-10-15/retained-evidence.json) in size and SHA-256. Parsed request and response bodies match their fields in the attempt record. The runner from execution commit `edfaccfbb514c7f8261f64edd5f11ad87ea6be7e` is byte-identical to the inspected published source.

| Original record | Bytes | SHA-256 |
| --- | ---: | --- |
| `attempt-0167.json` | 4456 | `0b070ae9b5d6160b01caa3ed83047a76a5ee6e59ba8abc94a54241888a8723a9` |
| `request-0167.body` | 2287 | `dc91caf91714601d9e42a0effd5f53a67e2946815e9b63192e06e4b8cfe47ff8` |
| `response-0167.body` | 261 | `37bc0865b3b67ed3ede9b6f92752dac796ab62a35d4d4ad449e87ceb2d23116b` |

The HTTP response reports `jev-1.14.0`, selects `contradicted`, and supplies probabilities `0.03`, `0.93`, `0.01`, and `0.02`. Their decimal sum is `0.99`; confidence is a separate field, `0.91`. Transport recorded HTTP 200 and an untruncated response. The [runner](../jev-axi-comparison-runners-2026-10-07/comparison_runner.py) uses Python's HTTP client and JSON parser directly, without a Jev SDK or `jev-axi` formatter in this path.

The frozen [contract](../jev-axi-decomposed-judgment-preparation-2026-10-13/contract.md) required finite numeric values in `[0,1]`, exact option coverage, and a sum within `0.000001` of one. `valid_probabilities` applies that rule. The retained output fails the sum condition, so the original `invalid_response` and twenty unattempted Jev slots remain as recorded. Two-decimal values in one response do not establish the provider's rounding algorithm or guaranteed precision.

## What the provider sources establish

Sources were inspected October 17, 2026, America/New_York (October 18 UTC). The current [HTTP reference](https://docs.typesafe.ai/api.md) and [Choice guide](https://docs.typesafe.ai/primitives/choice.md) describe a greatest-probability choice and a distribution over every requested option. The [live OpenAPI schema](https://api.typesafe.ai/openapi.json) describes a total approximately equal to one. The inspected sources specify no maximum sum error, decimal precision, or rounding rule. Machine-readable numeric fields do not supply that missing cross-field constraint.

The provider's [Python SDK schema at an October 14 revision](https://github.com/typesafe-ai/typesafe-sdk-python/blob/f36e68549ceca3191e5791e5f99ea1baa1a258b5/src/typesafe_sdk/_schemas/models.py) also describes approximate normalization. That dated SDK source predates the run; it does not prove which service implementation or deployed documentation governed the October 15 response. No historical deployed-service guarantee was established.

The [Confidence guide](https://docs.typesafe.ai/confidence.md) defines Choice confidence as `(p_max - 1/n) / (1 - 1/n)`. Confidence need not equal the selected probability, and this formula alone establishes no calibration. A three-option HTTP documentation example displays probabilities `0.88`, `0.12`, and `0.0` with confidence `0.81`; applying the formula to those displayed values gives `0.82`. This is an example discrepancy, not an observed service response or evidence for a particular rounding policy.

The current [Models page](https://docs.typesafe.ai/models.md) identifies `jev-1.14.0` as the newest release, while listing `jev-latest` as `jev-1.13.0` and `jev-preview` as `jev-1.14.0`. A future latest-version assessment must verify and pin the intended selector rather than assume the alias identifies the newest release. No new model-list or inference request was made.

## Join and consequence for future work

The discrepancy is in retained HTTP values, so CLI display rounding does not explain this attempt. The primary-source investigation and retained-response inspection were completed independently before this join. Together they support expected option coverage, numeric range, greatest-probability selection, and approximate normalization, but do not determine whether a deviation of `0.01` breaches the service contract.

A future protocol can investigate separate validity of the categorical answer and diagnostic quality of its scores, or establish a numerical requirement for its actual consumer. Either is a new protocol choice requiring its own justification and review. This research selects neither a permissive tolerance nor a stricter one. Preserve original numbers and deviations; do not repair them to satisfy a preferred outcome.

The smallest missing provider fact is a version-applicable statement of quantization, normalization order, maximum sum error, and whether choice and confidence use values before serialization. A published statement could resolve it; contacting the provider requires separate authorization. Further samples could characterize behavior but would not establish a guarantee.

This uncertainty blocks only future reuse of the affected probability-validity rule. [Choosing the next catalog hypothesis](https://github.com/nisavid/provingkit/issues/608) and [compatibility preparation](https://github.com/nisavid/provingkit/issues/471) remain independent. The [completed comparison](../jev-axi-decomposed-judgment-results-2026-10-15/results.md), its expired attempt, and unknown original controller closure remain unchanged. No rerun, regrading, code correction, calibration claim, hook change, or upstream submission occurred.

This follow-up used public documentation research and local retained-evidence inspection. It made no inference request. Native research/review tokens, charges, coordination effort, and operator effort were not measured; they are additional work outside the original comparison's clock.
