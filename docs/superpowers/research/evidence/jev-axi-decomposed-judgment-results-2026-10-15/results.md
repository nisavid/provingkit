# Narrower judgments did not resolve the observed Jev ambiguity errors

Jev 1.14 returned the same two incorrect answers with the direct question and the four-question decomposition before a separate response-validity failure stopped its condition. Both treatments treated an ambiguous referent as settled and reported the statement as supported. The decomposed package therefore fails the agreed critical-case bar on observed answers alone; the incomplete remaining cases do not erase those failures. This result supports no deployment of either package as an early System One check.

The single accepted invocation ran on October 15, 2026, using source commit `edfaccfbb514c7f8261f64edd5f11ad87ea6be7e`. It submitted 268 of 288 scheduled requests, containing 670 of 720 scheduled question instances, with no retries or substitutions. All 268 responses reported the requested model identity. Of those, 267 were operationally valid. The controlled-unavailable input made no request. The [contract](../jev-axi-decomposed-judgment-preparation-2026-10-13/contract.md), [question meanings](../jev-axi-decomposed-judgment-preparation-2026-10-13/selected-questions.md), [corpus](../jev-axi-decomposed-judgment-preparation-2026-10-13/corpus/construction.json), and [adjudicated key](../jev-axi-decomposed-judgment-preparation-2026-10-13/corpus/evaluator/key.json) remained fixed. Historical Jev 1.13 results remain version-specific; these different cases are not a controlled version comparison.

## Case outcomes

[results.json](results.json) presents every slot and paired transition before aggregates, including component disagreements, four material-reference cases, two independent-conflict cases, and six source-family groups. There are six cases in each final category. These constructed cases share evidence within families and are not independent population samples.

Each pair below is **direct / decomposed**. “Match” means the returned relation equals the expected relation. “Invalid” and “unattempted” are operational outcomes and supply no usable semantic judgment. The four Responses conditions are individually retained in the JSON; the last column names every exception to their matching pairs.

| Case | Expected relation | Jev 1.14 | Decisions | Responses conditions |
| --- | --- | --- | --- | --- |
| c01 | unresolved | supported / supported | unsupported_extension / unsupported_extension | all match |
| c02 | unresolved | match / match | match / match | all match |
| c03 | unsupported_extension | match / match | match / match | all match |
| c04 | contradicted | match / match | match / match | all match |
| c05 | supported | match / match | match / match | all match |
| c06 | contradicted | match / match | match / match | all match |
| c07 | contradicted | match / match | match / match | all match |
| c08 | contradicted | match / match | match / match | all match |
| c09 | unsupported_extension | match / match | match / match | all match |
| c10 | unsupported_extension | match / match | match / contradicted | all match |
| c11 | unsupported_extension | match / match | match / match | all match |
| c12 | unresolved | supported / supported | unsupported_extension / contradicted | all match |
| c13 | supported | match / match | match / match | all match |
| c14 | contradicted | invalid / match | match / match | all match |
| c15 | supported | unattempted / unattempted | unresolved / contradicted | all match |
| c16 | unsupported_extension | unattempted / unattempted | match / match | all match |
| c17 | supported | unattempted / unattempted | match / match | all match |
| c18 | unresolved | unattempted / unattempted | supported / unsupported_extension | all match |
| c19 | supported | unattempted / unattempted | match / match | all match |
| c20 | unsupported_extension | unattempted / unattempted | match / match | all match |
| c21 | unresolved | unattempted / unattempted | match / match | all match |
| c22 | contradicted | unattempted / unattempted | unsupported_extension / unsupported_extension | all match |
| c23 | unresolved | unattempted / unattempted | unsupported_extension / unsupported_extension | Luna 6 Low decomposed: unsupported_extension; others match |
| c24 | supported | unattempted / unattempted | match / unsupported_extension | all match |

Both Jev treatments missed c01 and c12. In c01, “the screening” could refer to different screenings with different image observations. In c12, “the new pear” could refer to different trees with different flowering observations. The decomposed answer called each referent clear and its statement fully warranted. All 13 Jev pairs with usable judgments on both sides retained their direct result: eleven correct and two incorrect. No wrong-to-right transition was observed.

At c14, the direct Jev response selected `contradicted`, but its probabilities were 0.03, 0.93, 0.01, and 0.02, summing to 0.99. The contract requires a sum within 0.000001 of one. The runner therefore recorded `invalid_response`, retained the raw choice and usage, and skipped the remaining ten cases in both Jev treatments. The c14 decomposed response had already completed correctly. The one-count difference between treatments is consequently a validity difference, not a repaired semantic error. No normalization or answer salvage was applied. The cause of the distribution discrepancy is unestablished; this observation does not distinguish rounding from another provider behavior.

Decisions changed two correct answers to incorrect ones and repaired none. Decomposition changed c10 from an unwarranted dishwasher-proof claim to a contradiction, and c24 from a supported pronunciation observation to an unsupported extension. Both Decisions treatments also missed all four material-reference cases. Luna 6 Low decomposition introduced one error on c23, failing to preserve the ambiguity in “the change” and “task duration.” Its direct question matched all cases. Luna 6 Medium, Luna 6 High, and Sol 6.1 Low matched all cases in both treatments. Neither treatment produced a semantic abstention or inconsistent combination.

## Quality and measured request cost

The acceptance denominator remains 24 per condition/treatment. Every critical case must pass; an average cannot compensate for an error or missing answer. Jev has only fourteen attempted cases per treatment, so its totals must not be read as a complete 24-case comparison. Each table cell lists direct / decomposed.

| Condition | Matching / 24 | Incorrect judgments | Invalid / unattempted, direct; decomposed | Median request seconds | API-rate equivalent, USD |
| --- | --- | --- | --- | --- | --- |
| Jev 1.14.0 | 11 / 12 | 2 / 2 | 1 / 10; 0 / 10 | 0.240 / 0.239 | 0.000504588 / 0.000997920 |
| Decisions / Luna 6 | 18 / 16 | 6 / 8 | 0 / 0; 0 / 0 | 0.275 / 0.287 | 0.0014115 / 0.0037515 |
| Luna 6 Low | 24 / 23 | 0 / 1 | 0 / 0; 0 / 0 | 1.358 / 1.509 | 0.0022237 / 0.005085575 |
| Luna 6 Medium | 24 / 24 | 0 / 0 | 0 / 0; 0 / 0 | 1.420 / 1.791 | 0.0023972 / 0.007051075 |
| Luna 6 High | 24 / 24 | 0 / 0 | 0 / 0; 0 / 0 | 1.582 / 2.471 | 0.0025677 / 0.009031075 |
| Sol 6.1 Low | 24 / 24 | 0 / 0 | 0 / 0; 0 / 0 | 1.537 / 1.996 | 0.030464 / 0.0897215 |

Both Jev treatments and both Decisions treatments fail the supplied-case bar. Direct Responses passes at all four selected configurations; decomposed Responses passes at Medium, High, and Sol 6.1 Low. Those passing conditions show feasibility on supplied evidence, not useful integration or removal of ordinary authoring work. The additional questions demonstrate no quality gain on completed pairs and increase the recorded API-rate value in every condition. These cost comparisons use observed workloads, including the shorter Jev workload; they are not a complete economic ranking of substitutable workflows.

The request phase lasted 477.418 seconds. Preflight and final preparation took 0.007 and 0.114 seconds under the same outer clock. Credential resolution took 1.043 seconds before that clock. The 134 local combinations totaled 0.317 milliseconds; that narrow interval excludes request parsing, source preparation, and coordination. Grouped request usage was counted once, not multiplied by four. Retained serialized request and response bodies total 1,348,030 and 5,340,298 bytes respectively.

All 268 attempts have valuatable usage under the frozen rates, including the invalid Jev response. The total API-rate equivalent is **$0.155207333**, not an observed invoice. Provider records report 263,588 input tokens and 30,403 output tokens; 22,161 reported reasoning tokens are already included in output. OpenAI records report zero cached-read tokens and 124,428 cache-write tokens. Those cache and reasoning partitions are missing on the 28 Jev attempts. Requested effort, returned model, and explicit effective effort, tier, and region fields are kept separately. Missing effective values remain unknown.

[Preparation accounting](preparation-accounting.json) retains both incurred producer preparations: 25 invocations before the model amendment and 25 after it. Their internal intervals total 338.444 and 315.031 milliseconds, with 22,791 logical Git-blob bytes read in each preparation. These intervals exclude process setup and receipt completion; logical reads are not physical I/O or model tokens. The unchanged source passed 23 producer and 90 runner checks. The superseded incomplete amendment review remains recorded alongside the completed review and adjudication. Complete corpus-authoring, preparation, coordination, and review effort, attributable native tokens, actual provider charges, and operator active effort remain unknown. The original 9,000-second invocation allowance includes grading, result review, corrections, and handback; the retained closeout binds their final records. This experiment does not measure subscription-capacity savings or complete workflow value.

[Retained evidence](retained-evidence.json) identifies the original local records by relative name, size, and digest. Public results preserve synthetic outputs and usage; they contain no credentials or chat histories. Original request and response bytes are retained unchanged.

## Consequence for System One integration

This particular decomposition did not resolve the observed Jev ambiguity failures. Relaxing the probability-sum check could change operational coverage in a separately accepted protocol, but it would not correct those already observed categorical errors. The distribution discrepancy deserves a separate contract diagnosis before reusing that validity rule; it does not authorize repairing this run or repeating it.

The next decision is whether there is a distinct, testable ambiguity-handling design worth preparing or whether to move this behavior aside and investigate another catalog opportunity. More questions alone are not a supported correction. A future candidate still needs early access to adequate evidence, critical-case reliability, and measured native or operator benefit at acceptable whole-workflow cost. The passing ordinary-model conditions remain comparators. No hook change, behavior assignment, calibration claim, or new experiment follows from this result.
