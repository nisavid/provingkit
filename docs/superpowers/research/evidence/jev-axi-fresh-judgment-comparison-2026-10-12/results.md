# Longer question wording did not correct Jev's evidence-scope errors

The fresh comparison does not support advancing either tested Jev question as an adequate correction. Jev matched the frozen labels on nine of twelve cases with the current question and eight with the revised question. All four Responses conditions matched every case with both questions. This is a result about isolated judgments on supplied synthetic evidence; an early check in an agent workflow remains unqualified.

One accepted invocation ran all 144 serialized requests on 2026-10-13, without retries, failures, refusals, or unattempted semantic slots. Every returned model identity matched its requested selector. The unavailable-source control made no semantic request. The reviewed [contract](contract.md), [questions](questions.json), [cases](construction.json), and [frozen key](evaluator/key.json) remained unchanged. Request execution used source commit `c9ce60ecb85f9a35771509f7ae386f9a2c6c8af7`; the inference source blobs were already pinned at its ancestor `bbc4d9d562d13578bf2081510a63089faa357393`.

## Case outcomes

[results.json](results.json) retains all 144 slot outcomes and 72 paired transitions before its aggregates. Each condition/question denominator is twelve: four supported assertions, three unsupported extensions, three contradictions, and two unresolved assertions. The cases share six source documents and are not twelve independent samples from ordinary work.

| Condition | Current question | Revised question | Median request seconds, current / revised | API-rate equivalent for twelve requests, current / revised |
| --- | ---: | ---: | ---: | ---: |
| Jev 1.13.0 | 9/12 | 8/12 | 0.276 / 0.276 | $0.000441084 / $0.000499548 |
| Decisions / Luna 6 | 7/12 | 8/12 | 0.276 / 0.267 | $0.0006885 / $0.0008157 |
| Luna 6 Low | 12/12 | 12/12 | 1.411 / 1.539 | $0.0010296 / $0.0011933 |
| Luna 6 Medium | 12/12 | 12/12 | 1.588 / 1.487 | $0.0011321 / $0.0012733 |
| Luna 6 High | 12/12 | 12/12 | 1.827 / 1.823 | $0.0012701 / $0.0014173 |
| Sol 6.1 Low | 12/12 | 12/12 | 2.199 / 2.120 | $0.014852 / $0.017796 |

The revised Jev question preserved its three earlier mistakes and added one. It called the ambiguous “replacement was operating” assertion supported even though the sources describe two possible replacements with different states. The current question correctly left that assertion unresolved. Both Jev formulations also:

- called an unwarranted claim about resumed relay delivery contradicted, although the sources establish only rehearsal delivery and no incompatible resumed-service event;
- called an unmeasured time-saving claim contradicted, although missing measurement does not establish that no time was saved; and
- called the assertion that two inspectors supplied accounts unresolved, although their disagreement about operation does not dispute that the accounts exist.

Decisions improved one answer: the revised question recognized the recorded act of consulting bibliography entries. It still missed two explicit contradictions, the existence-of-accounts assertion, and the ambiguous replacement assertion. That last case changed from one wrong category to another. Each Responses condition returned twelve matching answers under each formulation. There is no observed quality gain from the longer question for those conditions.

The paired record contains 63 unchanged correct pairs, seven unchanged incorrect pairs, one correct-to-incorrect transition (Jev), and one incorrect-to-correct transition (Decisions). There are no incomplete pairs. These are single observations per slot; the comparison neither estimates population error rates nor establishes run-to-run reliability or probability calibration. Jev and Decisions probability outputs are retained without selecting a confidence threshold. Responses answers are not assigned invented equivalent probabilities.

## Work and cost

The fixed request phase lasted 198.042 seconds, including the serialized runner's work. Final preflight took 0.036 seconds and preparation took 0.114 seconds under the same outer invocation clock. Credential resolution took 0.994 seconds before that clock and is retained separately as preparation overhead. Individual request medians above are observed elapsed request times, including transport; they are not isolated model compute times.

The provider records report 92,614 input tokens and 8,180 output tokens. Of the output, 5,375 tokens are reported as reasoning and are already included in output totals. No cache-read or cache-write tokens were reported by the OpenAI requests; those partitions and the reasoning breakdown are absent on the 24 Jev requests. Missing breakdowns remain unknown. All 144 requests have a calculable value under the frozen endpoint-specific rates: **$0.042408532 in total**. This is an API-rate equivalent, not observed billing. The table uses the contract's Standard short-context rates and no-region-surcharge assumption; effective tier, region, and effort remain separately observed or unknown in the records.

The request ledger is only part of the work. Corpus production retained 13 internal receipt intervals totaling 139.454 milliseconds and 7,869 logical Git-blob bytes read, including repeated reads. Those intervals begin inside the producer and end before the receipt is written; they exclude CLI/process setup and receipt-writing completion. Complete producer wall time is unknown. The recorded preparation included two design passes, two label passes, six critics, three adjudications, and 83 local checks with a runner-reported duration of 100.9 seconds. Coordinator and native-review token counts, attributable bills, complete preparation/review active time, and operator effort remain unknown. The contract keeps grading, result review, correction, and handback under the original 9,000-second accounting window and requires the private closeout to bind their final records. None of this establishes a saving in subscription capacity or complete workflow cost.

[results.json](results.json) includes per-request raw usage, returned model, requested effort, explicit effective fields where present, timing, probability-bearing responses, and frozen-rate valuation. [retained-evidence.json](retained-evidence.json) identifies the original local request records by relative name, bytes, and digest; it excludes machine-local paths. The private request and response bodies remain unchanged. [preparation-accounting.json](preparation-accounting.json) preserves setup quantities and gaps separately from request costs. These projections contain synthetic workload and result data, not credentials or chat histories.

## Consequence for System One integration

Under the agreed all-critical-cases bar, neither Jev formulation nor either Decisions formulation passes this set. The revised Jev formulation is not an adequate correction. The passing Responses controls show that the supplied evidence can support the intended distinctions with these model configurations; they do not show that an ordinary author would perform this review or that replacing it would remove work.

A useful next design question is whether to decompose the four-way verdict into narrower Jev judgments, then combine them with deterministic logic, or to set aside this Jev behavior for now. Any decomposed proposal must preserve ambiguous referents and the distinction between absent warrant and an incompatible fact, account for every question and combination step, and retain the successful ordinary-model controls and omission. The current result does not select that successor, authorize another experiment, or justify a live hook. Working-draft delivery and complete workflow benefit remain separate unanswered questions.
