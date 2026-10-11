## Findings

No high-conviction runtime finding in the frozen result-review boundary. All 60 categorical grades, their accounting joins, and the report’s measurements agree with the retained audit projection and frozen grading contract. No correction is required.

This is a clean runtime review of the supplied result artifacts. It does not mean every comparison condition passes: Jev matches 7/10, Decisions matches 3/10, the three Luna Responses conditions each match 10/10, and Sol matches 9/10.

I verified the request SHA-256 `860fadf042c5275ba4615f99f9e9a66a0484864083345e65d2a34b55eeda8b30` and governing input SHA-256 `c15d942a47ae3f59fdd2771203377d6401c16ee44738eea04a5d44903a53c5fc`. I read all 13 enumerated evidence files completely, including every grade and audit row. Their hashes before and after reading matched their declared identities. I also read the runtime skill and its required textual references, excluding the forbidden topology file.

## Falsification attempts

- **Dropped or duplicated slots could inflate feasibility.** I reconciled `summary.json`, `grades.json`, and all rows of `attempt-audit.jsonl`. They contain slots 0000–0059 under run `0717f357617f425c97fc258c82b32b81`, with one attempt of index zero per slot. Each condition has ten completed attempts. The case order and cyclic condition rotation match the contract. No failed or unattempted slot is removed from a denominator.

- **A wrong answer could be relabeled or counted as invalid rather than nonmatching.** I checked all 60 retained relations against `key.json` and the report’s case table. Jev’s nonmatches are c01, c09, and c10. Decisions’ nonmatches are c01, c04, c03, c06, c02, c09, and c10. Sol’s sole nonmatch is c08. The three Luna Responses conditions match every case. Those are exactly the recorded grades and aggregate counts. The grading source preserves a valid wrong relation as nonmatching and requires ten matching terminal answers for a feasibility pass.

- **Transport success or a requested selector could conceal an unusable answer or different model.** Every audit row retains matching requested and returned model identities, received transport, HTTP 200, completed attempt status, no condition error, no truncation, and no expired deadline. All 40 Responses terminal projections additionally retain completed status, null error and incomplete details, and one completed assistant message containing a single JSON object with only the valid `relation` property. Their terminal message values agree with the graded relations.

- **Choice confidence or probabilities could be malformed or silently replaced.** All 20 native Choice answers retain their selected option, confidence, and four probabilities. The confidences and probabilities are finite and within [0, 1]; each distribution sums to one within the contractual tolerance. The selected answers agree with the graded relations. Decisions’ c05 distribution has a tie between supported and unsupported_extension, but its retained choice is unsupported_extension; the contract imposes no unique-maximum requirement or confidence threshold. The report makes no calibration claim.

- **Missing counters, overlapping scopes, or reasoning could create a false low cost.** Every audit row declares per-request usage. The condition joins count distinct attempts once. The input totals independently reconcile to `28,809 + 22,695 + 4 × 22,175 = 140,204`; output totals reconcile to `537 + 0 + 793 + 1,218 + 3,655 + 237 = 6,440`. Responses cache-write input totals 22,145 per condition, or 88,580 overall; cached input is explicitly zero. Reported reasoning totals 5,290 and remains included in output. Each supplied partition satisfies `C + W ≤ I` and `R ≤ O`. Jev’s ten missing cache and reasoning observations remain missing rather than becoming observed zeros.

- **Valuation could ignore cache writes or charge reasoning twice.** Applying the frozen accounting formula gives the report’s six equivalents:

  | Condition | Independently checked USD equivalent |
  | --- | ---: |
  | Jev | 0.001209978 |
  | Decisions | 0.0022695 |
  | Luna Low | 0.003167625 |
  | Luna Medium | 0.003380125 |
  | Luna High | 0.004598625 |
  | Sol Low | 0.0577925 |
  | Total | 0.072418353 |

  For each Responses condition, uncached, non-write input is 30 tokens; the remaining 22,145 input tokens receive the cache-write rate. Output receives its rate once. The report correctly distinguishes these equivalents from confirmed charges and complete comparison cost.

- **First-byte latency or overlapping intervals could be presented as completion time.** I checked the per-attempt durations against the retained monotonic readings and the condition timing joins. The six reported medians match terminal request durations, rounded to six decimal seconds. The runner interval is 103.010014559 seconds, supporting the reported 103.010015 seconds. The wrapper’s encompassing request-work interval is separately retained; it is not added to the runner duration.

- **Grading could receive a new allowance or occur before request closure.** The runner and outer state retain the same absolute deadline, `19448354778969`. Grading begins after the request phase ends and uses the same recorded clock identity. The original 9,000-second allowance starts at `2026-10-11T21:18:27.708960Z` and expires at `2026-10-11T23:48:27.708960Z`. The report says the outer clock continues through review and handback; it does not claim completed whole-invocation closeout.

- **The unavailable control or narrow sample could support a stronger claim.** c11 remains unavailable in the summary, has no scheduled slot or audit attempt, and receives the separate producer-fallback outcome in the grades and report. The report preserves the fixed-set feasibility limit and explicitly disclaims native benefit, whole-workflow economic superiority, calibration, broader accuracy, author correction, review replacement, and live activation.

The projection intentionally omits repeated request objects, stream events, full raw responses, and encrypted reasoning content. I therefore did not independently re-audit request construction, evaluator separation, the original raw inventory, packet/receipt semantics, or the coordinator’s reported verification of 136 dependencies. The controlled-unavailable receipt itself is outside the enumerated files; this review confirms the retained control outcome and absence of semantic attempts. Provider billing, complete outer accounting, and final deadline compliance remain unverified here and are appropriately unresolved in the report.

I made no writes, ran no source or tests, made no provider requests, accessed no credentials or private history, and performed no subdelegation or topology lookup.
