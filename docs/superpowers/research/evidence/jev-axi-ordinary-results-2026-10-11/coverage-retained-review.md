## Findings

### R1 — P2: The grade for `775d4c208f44` mistakes conditional claim scoping for a question about known map membership

**Scope:** Runtime, grading correctness. This contradicts the current fixed grading contract.

In `outputs.json`, `775d4c208f44` asks:

> “Clarify which of the added review, verification, research-record, and publication-context files are included or deliberately excluded from any claim of coverage. A content-map match alone does not establish semantic coverage.”

`coverage-final-grades.json` instead characterizes this as asking whether `research-record.json` is included despite its presence in the seven-file map. The delivered question concerns the scope of a proposed coverage claim; it does not ask whether that file belongs to the map. Earlier in the same note, the answer explicitly states that the other six listed public inputs match their recorded hashes.

The unchanged key distinguishes map membership from semantic coverage and states that a correct conditional prerequisite is not automatically an unnecessary question or stop. The note places this request under “before claiming full candidate coverage” and offers narrowing the claim to unchanged reviewed inputs. That conditional framing matters.

The answer still omits an evidence-backed discussion of both changed texts, so its existing `final_quality: incomplete` remains supported. But the supplied basis does not establish `next_action: fail` or the recorded `unnecessary_question` event. Removing that unsupported failure would make this cell **incomplete**, not passing.

**Impact:** The reported split would become four passing, six incomplete, and four failing delivered notes, rather than four, five, and five. No condition would pass both cases; this does not produce a qualifying condition or economic winner.

**Smallest correction:** Reassess this next-action dimension and false-steering event against the actual passage, preserving the unchanged key and original answer. Update the cell outcome, condition reconciliation, and report counts if the finding is accepted.

**Proof needed:** Show the revised dimension basis anchored to the actual question and its conditional scope, then verify the resulting sixteen-cell outcome join. No inference rerun is needed.

**Limitation:** This is an independent finding for adjudication, not a mutation or adjudicated grade change.

## Falsification attempts

### Semantic grades

I challenged all sixteen records against the fourteen delivered notes, source projection, and unchanged key.

| Output | Result supported by inspection |
|---|---|
| `121d5ebe4b97` | Pass: nine/seven reconciliation, matching separate review digest, retained review scope, and conditional broader-claim checks are present. Named endpoints and records provide equivalent precise citations. |
| `348e180ed6df` | Pass: seven candidate matches and separate review match are explicit. Further checks are conditional on broader claims. |
| `4064f872412e` | Pass: inventory, seven matches, separate review association, review scope, and next action are grounded. Support-record inspection is conditional on an all-nine claim. |
| `59559f12d144` | Incomplete: seven matches are stated, but the separate review-digest match is omitted. I did not convert that omission into a false assertion. |
| `6e563627efcf` | Fail remains supported: “The clean review did not cover all nine added files” categorically infers exclusion from map absence. Its conditional broader-claim wording does not cure that assertion. |
| `ba2b5d0fbe46` | Failed delivery: no delivered note exists. |
| `c3b5cf9154a3` | Incomplete: it describes recorded hashes but does not deliver the candidate-to-record matching conclusion. |
| `e257a5186400` | Pass: nine additions, seven matching inputs, separate matching review, semantic scope, and operational limits are explicit. |
| `17e8c75a23dd` | Unattempted: no note exists; it remains in the condition denominator. |
| `21ba509d8b44` | Fail: it reports eleven additions against a supplied complete inventory of ten. The added note’s content is also omitted. |
| `436a8a797868` | Incomplete: both changed texts and six matches are discussed with precise citations; a matching separate review digest is not explicitly reconciled. |
| `703fdb3b2396` | Fail remains supported: “previously published packet” asserts publication that the supplied commit identity and comparison do not establish. The later disclaimer about the current candidate does not establish earlier publication. |
| `775d4c208f44` | R1 above: changed-text omissions support incomplete delivery of the requested reconciliation, but the recorded unnecessary-question failure misreads the passage. |
| `85b431d879ca` | Incomplete: it identifies both paths and the separate review match but omits the six-equal relationship conclusion and inspection of both supplied texts. |
| `e3af19992cfe` | Incomplete: the README sentence is discussed; the supplied new note’s content and supporting citation are deferred. |
| `ee0dd9b0fafd` | Fail remains supported: it invents an inventory mismatch between seven Markdown documents and the explicitly supplied seven reviewed inputs, then requests reconciliation of that known distinction. Neither changed text is discussed. |

I tested whether concise wording or alternative citations could rescue the incomplete notes. The omissions above concern material conclusions, not a required template, digest recital, or preferred prose. I also tested whether every conditional prerequisite should count as false steering; the key does not permit that rule, which produces R1.

The source projection supports the case facts: nine additions and seven equal map entries for the retained commit; ten additions, six equal entries, the changed README, and the new three-line note for the constructed fileset. Both retain the separate matching review digest. The two changed texts supply no inherent defect, runtime qualification, or publication outcome.

### Failure, schedule, and denominator

The schedule and reconciliation retain sixteen cells: fourteen completed, one transport error, and one unattempted cell. Attempt indices are consecutive within each attempted cell, with no retry records.

The failed continuation in slot 2 records `SSLError`, no HTTP status, no provider request ID, an empty response body, unknown usage, and unknown residual provider work. Its ten prepared tool results appear in that submission attempt, which establishes attempted replay, not transmission or provider consumption. Slot 11 remains unattempted because that condition stopped. The report does not treat the partial condition as a saving.

### Tools and replay accounting

I read every projected call and attempt record and reconciled the per-cell counts:

- 234 requested calls and 234 prepared results.
- No projected unprepared call or unused prepared result.
- Prepared serialized envelopes total **2,203,428 bytes**.
- Submission-attempt replay totals **3,600,072 bytes**.

The submission indices account for repeated history envelopes. The failed submission’s replay remains included. Neither total establishes unique source bytes or provider-consumed bytes, and the report preserves that distinction.

### Token, value, and timing arithmetic

The condition subtotals reconcile to:

- Input: **952,802**.
- Cached input: **417,087**.
- Cache-write input: **535,586**.
- Remaining input: **129**.
- Output: **42,209**, including **28,680** reasoning tokens.
- Known API-rate equivalent: **USD 0.382253650**.

The inspected partitions satisfy cached plus cache-write input not exceeding input, and reasoning not exceeding output. The stated valuation uses reasoning once through output. The failed attempt remains unvalued; actual charges and the complete request value remain unknown.

The request-phase monotonic difference is **419.971958044 seconds**, consistent with the report’s rounded figure. Cell durations include navigation and continuations. The original outer start and deadline remain unchanged; the supplied state is still `awaiting_closeout`, so these artifacts do not establish completed outer closeout.

### Supplemental native-client usage

The four supplemental values reproduce from each session’s last cumulative counters and the frozen requested Sol 6.1 rates:

| Session | Conditional API-rate equivalent, USD |
|---|---:|
| Claim review | 1.0951400 |
| First coverage review | 0.0245252 |
| Second coverage review | 1.8770236 |
| Grade adjudication | 0.5181860 |
| **Sum** | **3.5148748** |

All four records explicitly report zero cache-write input; reasoning is included in output. These are native-client-reported cumulative observations, not independently reconciled provider receipts. I did not subtract the first nonzero observation or add interim cumulative snapshots. Effective model, billing, quota, complete root-workflow attribution, and this current review’s usage remain outside those values.

## Identity, completeness, and limits

I completed consecutive bounded reads of all **15 enumerated evidence files, totaling 489,714 bytes**, with matching before/after SHA-256 hashes. I also completely read and hashed the request, refreshed selection, refreshed plan, input manifest, Runtime skill, and its four required textual references. No response was truncated.

Verified principal identities:

- Request: `ff297198841a6206e6549561356b5fc745764388cba700dc22c61cc018d65366`
- Refreshed selection: `bf23e06ec7230d39c794d51fdf838a54d740f0b8524c991698765e2b691dd875`
- Refreshed plan: `112a97052616a0d4ee851c08351e95e9714b8471e7544b683edab76f19226276`
- Input: `43423eefd81bdcde228b3deb06e80252a57b562dc4b7e3c4f1ed0b44636d87e4`
- Candidate report: `26d229da88e335220955b60b87f016576b901fcef086dd1388cc6ea148b7689e`
- Final grades: `2d32af9077b8e89316e30e1303143fd8bf7ea758e465689c213d1c59e11543d8`
- Fixed key: `9133211def7e0961e04a9e036c370e0d1f6117f08d0a16b5ae05043a88fd0edd`

This is a complete independent audit of the supplied result-review projection. I did not execute source, tests, or a grading experiment; inspect private session history or raw request bodies; access embedded paths; use network; mutate files; subdelegate; adjudicate; or look for `topology.json`. Only the declared review-to-runtime edge was applied.

The projection’s omitted raw material prevents a full raw-request, transport, acquisition, evaluator-isolation, or billing audit. The native launch observations and effective executor configuration remain the coordinator’s verification responsibility.
