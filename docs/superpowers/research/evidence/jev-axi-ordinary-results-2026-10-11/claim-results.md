# Claim-support comparison result

All 60 scheduled requests completed with matching requested and returned model identities. Luna 6 Low, Medium, and High matched the frozen key on all ten supplied cases. This is a supplied-case feasibility result; it does not establish native benefit or whole-workflow economic superiority.

## Cases before aggregates

| Case | Expected | Jev 1.13.0 | Decisions Luna 6 | Luna 6 Low | Luna 6 Medium | Luna 6 High | Sol 6.1 Low |
| --- | --- | --- | --- | --- | --- | --- | --- |
| c01 | unsupported_extension | supported | unresolved | unsupported_extension | unsupported_extension | unsupported_extension | unsupported_extension |
| c04 | supported | supported | unresolved | supported | supported | supported | supported |
| c03 | contradicted | contradicted | unresolved | contradicted | contradicted | contradicted | contradicted |
| c06 | supported | supported | unresolved | supported | supported | supported | supported |
| c05 | unsupported_extension | unsupported_extension | unsupported_extension | unsupported_extension | unsupported_extension | unsupported_extension | unsupported_extension |
| c07 | supported | supported | supported | supported | supported | supported | supported |
| c02 | supported | supported | unsupported_extension | supported | supported | supported | supported |
| c08 | contradicted | contradicted | contradicted | contradicted | contradicted | contradicted | unsupported_extension |
| c09 | unsupported_extension | supported | supported | unsupported_extension | unsupported_extension | unsupported_extension | unsupported_extension |
| c10 | unsupported_extension | supported | unresolved | unsupported_extension | unsupported_extension | unsupported_extension | unsupported_extension |

The local unavailable-source control c11 remained unavailable and had zero semantic requests. It has a producer-fallback outcome, not an unresolved classification.

## Per-condition measurements

| Condition | Matching / 10 | Input tokens | Output tokens | API-rate equivalent, USD | Median request seconds |
| --- | --- | --- | --- | --- | --- |
| Jev 1.13.0 | 7/10 | 28809 | 537 | 0.001209978 | 0.302521 |
| Decisions Luna 6 | 3/10 | 22695 | 0 | 0.0022695 | 0.328503 |
| Luna 6 Low | 10/10 | 22175 | 793 | 0.003167625 | 1.657824 |
| Luna 6 Medium | 10/10 | 22175 | 1218 | 0.003380125 | 1.877322 |
| Luna 6 High | 10/10 | 22175 | 3655 | 0.004598625 | 1.541795 |
| Sol 6.1 Low | 9/10 | 22175 | 237 | 0.0577925 | 1.704416 |

The serialized request phase took 103.010015 seconds. It reported 140,204 input tokens and 6,440 output tokens, including reported reasoning within output. The frozen-rate equivalent for the 60 requests is USD 0.072418353. This is not a verified bill or the full cost of the comparison.

All six conditions had ten valid completed answers and no retries or unattempted slots. The three Luna Responses conditions pass the fixed ten-case feasibility bar. Jev, Decisions, and Sol do not pass that bar. No probability calibration or broader accuracy rate follows from this small fixed set.

Jev supplied native confidence/probabilities and input/output usage; separate cache and reasoning counters were not reported. Decisions and Responses reported those counters. Responses reported cache-write input; the valuation includes that partition at the frozen rate. No token counter is converted into subscription quota.

## Accounting and limits

Runner attempt records remain authoritative and are counted once. The condition views and total are alternative aggregations of the same attempts. Provider charges, effective region where absent, complete root/reviewer token attribution, setup/construction effort, active operator effort, and ordinary authoring costs remain unknown. Research evaluation and future ordinary use are separate. The outer clock continues through final review, correction, and prepared handback; its elapsed span will be recorded at closure.

This comparison did not run an author-consumer task, replace routine review, prevent a native mistake, or change a live hook. A useful next decision needs the reviewed results and the separately accepted publication-coverage comparison.
