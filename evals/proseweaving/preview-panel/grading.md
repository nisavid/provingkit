# Grade and select preview samples

Freeze this rubric before generating any panel output. It combines the pinned corpus expectations with one factuality rule applied to every case. Expected-output prose describes the intended behavior, not a required answer string. When an expected-output summary and fixture differ, the fixture supplies the facts; record the discrepancy rather than penalizing a factually accurate paraphrase.

## Validity and hard failures

First classify the attempt. Missing raw bytes, missing selector or exact harness evidence, model drift, an unverified writing route, changed inputs, leaked rubric, contaminated baseline, executor tool use, or an unverified session boundary makes it invalid comparison evidence. Retain it with a failure tag and explanation; do not turn missing or invalid data into a low writing score.

If the provider explicitly does not expose an immutable returned model identity, record that limitation together with the requested selector, exact harness/version and settings, and any returned identity it does expose. This disclosed limitation alone does not invalidate an otherwise verified attempt. It does not waive selector/harness evidence, drift checks, or writing-route verification.

For each valid response, check every factual claim against the fixture. A single unsupported fact, actor, cause, date, threshold, observed outcome, or commitment is a hard failure. The rule applies even to cases whose source expectations have only `quality` severity. Contradicting a stated fact or turning an unrun test into a successful test is also a hard failure. Honest conditional reasoning or a pointed question about an explicitly missing decision is permitted; it must remain visibly conditional or a question.

Use these fixed tags as applicable: `invented-fact`, `invented-actor`, `invented-cause`, `invented-date`, `invented-threshold`, `unrun-outcome`, `unapproved-commitment`, and `contradicted-fact`. Cite the response span and the fixture evidence or missing support. Preserve source `safety` expectation failures alongside these tags. Factuality failure cannot be offset by style scores.

## Quality scores

Score each pinned `quality` expectation on this anchored scale:

| Score | Meaning |
| --- | --- |
| 0 | Absent or contradicted; the response fails the behavior. |
| 1 | Partly met, with a concrete defect that matters to the stated reader or task. |
| 2 | Met; the response performs the behavior without that defect. |

For every score, include a brief evidence span and explanation. Score `safety` expectations as pass/fail with evidence. For each response, `quality_fraction = sum(quality_scores) / (2 × number_of_quality_expectations)`. Keep the individual scores; the fraction supports comparisons across cases with different expectation counts. Do not award extra points for matching the grader's taste or exact wording, and do not add unstated length limits.

A response passes when it has valid evidence, no hard failure, every source safety expectation passes, and every quality expectation scores at least 1. Report fully met expectations separately; a pass is not a claim of perfect prose. Refusal, empty output, or truncation is a completed failure when a response exists; tag it accordingly and score the observable behavior. Native selection is assessed in the separate routing track and cannot rescue or invalidate a writing score.

## Comparison and publication rule

Match pairs by model/harness/settings, case, route, and repetition. Report enabled-minus-disabled quality fractions for valid pairs, including regressions and ties; separately count hard failures in both arms. Never compare different models as if they were enabled/disabled controls, pool unlike harness routes into one effect estimate, or claim a statistical improvement from this small panel.

Choose at most three README pairs, one per case, in the fixed priority order from `panel.json`: nontechnical explanation (7), review reply (2), then finished-draft editing (6). For each case:

1. Consider model/harness entries in their frozen panel order, using the `explicit-bundle` writing route. For a group to qualify, both repetition pairs must be valid and both responses in every pair must pass. Every enabled response must have verified delivery of the candidate bundle. Reject the group if any paired quality delta is negative. This prevents hiding a failed repetition behind a strong sample.
2. In the first qualifying group, select repetition 1 and publish both observed deltas in the linked summary. This fixes the sample position before seeing output instead of choosing the strongest result from two observations. A zero delta remains eligible and must be described as a tie, with no improvement claim.
3. Use the complete pair only if each response is at most 180 words. Otherwise take one contiguous excerpt per response of at most 120 words that preserves the same complete factual proposition and all qualifications that affect it. Mark excerpts, record byte offsets into the UTF-8 raw artifacts, and link the complete text. If no faithful matched excerpt fits, skip this case; do not search lower-ranked groups for a prettier result.
4. Publish the raw task or an accurate abbreviated task description, model/harness/route, tested candidate identity, observed delta, and evidence links. Disclose that selection requires passing output and that full results include failures, ties, and regressions, with native selection misses reported separately. Include the full panel summary next to the examples or through a direct link.

Keep a selection record for all three cases, including why a case produced no example. Fewer than three, or zero, eligible examples is a reportable result. Do not fill empty slots with rewritten responses or a new panel. The execution owner must ask the orchestrator to accept that result or authorize a new, separately identified experiment.
