# Test whether explicit evidence completion improves publication reconciliation

The retained failures justify testing how evidence becomes a usable conclusion. They do not justify rejecting Jev, selecting Luna, or adding a confidence threshold. My recommended next diagnostic is a fresh publication-coverage comparison that holds the evidence and semantic task constant while separating deterministic reconciliation from the consumer’s interpretation and final-note completion. It should proceed only if the joined workflow investigation identifies reconciliation work that remains useful at that checkpoint.

The concerns are evidence limits: this investigation can compare reconstructed actual claim requests, coverage outputs, final grades, and requested tool operations. The supplied coverage projection does not contain the complete original request bodies or function-result bodies. It therefore cannot establish exactly how much delivered evidence the provider processed or attribute omissions to a particular prompt phrase.

## Evidence boundary and maintained method

The frozen request, SHA-256 `911ef28781a4472a2ff75b8e7d984061afff13d367b7eb83c186b87268b622c5`, and all 17 manifest inputs matched before inspection and again at handback. The owning source revision is `6d885174b919802c3550c7d591aad3f94d39601a`.

I used `research`, `adopting-jev`, and `capturing-agent-procedures` within the bounded assignment. No provider reasoning was inspected. No files were changed, tests or provider calls run, browsing performed, or other investigator’s report read.

The consumed maintained procedure is `.agents/skills/handling-sys1-incidents/references/comparison-contract.md`, SHA-256 `9f876cd27c4bd6fe82d56feabc6e31e05d029d7cac18f9651194218e2e1aa981`, at the bound source revision. The supplied [capability-assessment record](https://github.com/nisavid/provingkit/issues/548) also identifies the maintained comparison method at revision `8e1e170ab9437849a48e21d230e92dc9dcbf15a3`.

Its requirements remain controlling: compare complete workflows, preserve failed and skipped attempts, qualify context before judgment, and treat an assessment added to continuing ordinary judgment as an addition. A diagnostic success establishes neither population reliability nor native benefit. See the comparison contract, lines 12–54 and 77–100.

## Claim errors concern evidentiary scope, despite equivalent supplied text

I recursively expanded the losslessly interned text in retained `claim-evidence.json`. For every one of the ten cases, all six routes contained byte-identical evidence text. Jev and Decisions had identical question wording and outcome definitions. Responses placed that same question and definitions in its instructions and requested a structured relation answer.

The actual question already tells candidates that derivative assertions add no independent warrant, and that an unestablished event is not an incompatible event. Adding those sentences again would not be a new correction. The routes nevertheless differ in their API representation, instruction placement, model, and available effort configuration; this is not an isolated test of underlying model identity. See `docs/superpowers/research/evidence/jev-axi-comparison-runners-2026-10-07/comparison_runner.py`, `QUESTION`, `RELATIONS`, and `payload_for`, lines 18–34 and 415–430.

Jev’s three nonmatching answers are:

| Case | Supplied assertion and decisive evidence | Actual Jev answer |
| --- | --- | --- |
| c01 | “The retained publication involved nine outgoing files.” The supplied push report, line 7, identifies a nine-file **commit candidate** and explicitly leaves the actual pushed range unavailable. | `supported`; confidence 0.77; supported probability 0.83 |
| c09 | “The reports establish that the actual publication had nine outgoing files.” A supplied derivative report repeats the publication framing; its supplied underlying push report retains the candidate/push qualification. | `supported`; confidence 0.88; supported probability 0.91 |
| c10 | “The complete actual pushed range contained exactly seven files.” The supplied verification record lists seven reviewed inputs and a separate review digest; it does not identify the actual pushed range. | `supported`; confidence 0.79; supported probability 0.84 |

The accepted relation for all three is `unsupported_extension`. These are received, valid, completed semantic answers, not transport failures or malformed responses. The evidence does not show that a nine-file or seven-file push never happened.

The error pattern is narrower than a general inability to detect unsupported extension. Jev correctly classified c05’s claim that retrieving a saved review choice avoided reconstruction work as `unsupported_extension`. Its source explicitly establishes retrieval and later use while leaving avoidable reconstruction unestablished. Jev also correctly classified c02’s bounded nine-file candidate/seven-reviewed-input statement as supported. The publication/push-scope examples therefore identify a candidate failure surface; they do not establish its cause.

A matched successful control is c07: the assertion accurately quotes the publication study’s statement that costs and savings remain unknown. Every route returned `supported`. Jev returned confidence/probability 1.0; Decisions returned confidence 0.32 and supported probability 0.49. Successful typed delivery and at least one correct relation are possible through both routes.

These findings add request-level grounding to the already-known outcome matrix in `docs/superpowers/research/evidence/jev-axi-ordinary-results-2026-10-11/claim-results.md`, lines 7–20 and 35–43. The accepted case definitions and author outcomes remain those in `docs/superpowers/research/evidence/jev-axi-comparison-preparation-2026-10-07/semantic-support.md`, lines 61–96.

### Decisions’ unresolved answers are classifications, not missing delivery

Decisions returned `unresolved` on c01, c03, c04, c06, and c10. These were valid completed choice answers. In this key, `unresolved` means that missing referents, conflicting sources, or insufficiently interpretable context prevent another relation; it is not a generic confidence fallback.

For example, c03 and c04 use the same publication-results source. That source expressly puts publication outside the observation. c03 claims publication occurred during the interval and is contradicted; c04 says the documents were published afterward and is supported. Decisions returned unresolved on both, with unresolved probabilities 0.50 and 0.53. The request records establish that the distinguishing evidence was supplied. They cannot establish whether the cause was category interpretation, route behavior, salience, or another model behavior.

Decisions correctly classified c05, c07, and c08; it incorrectly classified c02 as unsupported extension and c09 as supported. Keeping Decisions eligible means testing a specific question or delivery change, rather than counting its unresolved answers as either successful abstentions or provider failures.

### The probabilities do not establish an intervention threshold

Jev’s correct unsupported-extension answer on c05 has confidence 0.48, below all three wrong supported answers. Decisions’ wrong supported answer on c09 has confidence 0.48, above each of its three correct answers: 0.15, 0.32, and 0.47.

Thus, these observations do not support a simple claim that higher confidence separates correct from incorrect answers while retaining every correct case. A gate could suppress some answers, but it would introduce abstentions and fallback work whose usefulness and cost are unmeasured. Choosing its threshold from these ten known cases would neither calibrate it nor preserve the accepted bar by itself.

The runner validates probability shape and sums; that is distinct from calibration. See `comparison_runner.py`, `valid_probabilities`, lines 542–557, and `claim-results.md`, lines 35–37.

## Coverage errors persist beyond supplying a relationship summary

Coverage already had deterministic `relationship_summary` presentation. The runner adds that field for the deterministic arm while preserving access to sources and comparisons. The producer separately computes content-map relationships and the review-digest relationship. See `comparison_runner.py`, `payload_for`, lines 373–413, and `docs/superpowers/research/evidence/jev-axi-comparison-producers-2026-10-07/coverage_producer.py`, lines 132–179.

The retained outputs expose different failure types:

| Output | Observation | Consequence |
| --- | --- | --- |
| `6e563627efcf`, Luna Low deterministic, retained candidate | Says the clean review “did not cover all nine added files” and requires review of supporting records because they are absent from the seven-input map. | A semantic overstatement and mistaken review demand despite deterministic presentation. |
| `21ba509d8b44`, Luna Low ordinary, constructed fileset | Reports eleven additions where the complete inventory has ten and calls the fileset a whole commit candidate. It discusses the README sentence but omits the new note’s content. | Wrong assertions plus incomplete interpretation. |
| `775d4c208f44`, Luna High deterministic, constructed fileset | Reconciles six equal inputs, the changed README, ten additions, and the separate review match, but does not discuss either changed text. Its trace requests both comparisons’ patches. | Retrieval activity does not establish a delivered material conclusion. |
| `e3af19992cfe`, Luna High ordinary, constructed fileset | Discusses the README addition but defers the new publication-context note for inspection or scope handling despite requesting its source and the patches. | More navigation can coexist with an incomplete final note. |
| `436a8a797868`, Sol Low ordinary, constructed fileset | Discusses both changed texts with citations but omits the separately matching review-digest conclusion. | Substantive interpretation can coexist with incomplete mechanical reconciliation. |
| `703fdb3b2396`, Sol Low deterministic, constructed fileset | Reconciles both texts and the separate review match but calls the retained commit a “previously published packet.” | A publication assertion exceeds the supplied commit evidence. |

The function traces establish requested operations, prepared results, and attempted submission. They do not establish attention, comprehension, or internal reasoning. In particular, it would be wrong to describe the omissions above simply as “the model never read the evidence.”

A successful coverage control is `121d5ebe4b97`, Sol Low ordinary on the retained candidate. It reports nine additions, seven matching reviewed-input hashes, and the separately matching review digest while preserving source-review and push boundaries. It uses six tool operations. This establishes a successful bounded reconciliation without the added summary; it does not establish that six operations are generally sufficient or cheapest.

The final result remains four passing notes, six incomplete notes, four failing notes, one failed delivery, and one unattempted cell. No condition passes both critical cases. See `docs/superpowers/research/evidence/jev-axi-ordinary-results-2026-10-11/coverage-results.md`, lines 7–30.

### Preserve the grading corrections

Two corrections matter to interpretation:

- `703fdb3b2396` changed from pass to fail because “previously published packet” asserts publication absent from the supplied evidence. The unchanged key was applied to an overlooked assertion.
- `775d4c208f44` had an incorrectly attributed unnecessary-question finding removed. Its conditional full-coverage scoping is not the recorded false steering. It remains incomplete because it omits discussion of both changed texts.

A proposal should not “fix” the second output by prohibiting legitimate scope qualification. Nor should it rescue the first by treating a retained commit as publication evidence. See `coverage-results.md`, lines 24–26, and retained `coverage-final-v3-grades.json`, `prior_revision_provenance` and `revision_provenance`.

The SSL failure in `ba2b5d0fbe46` is separate: there is no delivered answer, no recorded HTTP response, and unknown failed-attempt usage. Its later condition cell, `17e8c75a23dd`, was unattempted. Neither supports a semantic judgment. See `coverage-results.md`, lines 30–40.

## Competing explanations and discriminating observations

| Explanation | What the retained evidence supports or limits | Observation that would count against it |
| --- | --- | --- |
| Claim question or categories cause confusion | Decisions often selects unresolved. The actual question already contains the relevant warrant qualifications. There is no genuine conflicting-source control in the retained claim matrix. | A fresh, equivalent staged question still makes the same errors while supported, contradicted, and genuine-conflict controls work. |
| Evidence roles or salience cause publication-scope errors | c01 repeats the assertion in draft context; c09 includes a derivative assertion as a source. c10 fails without that derivative report, so derivative corroboration alone cannot explain all three. | Explicitly identifying draft versus source roles and directing attention to the qualifying passage fails to change fresh scope contrasts. |
| Route or model behavior dominates | Identical submitted evidence produces different answers; Decisions and Responses also differ despite their shared requested Luna model name. | The differences disappear under equivalent fresh question/context variants. That would weaken a stable route-level explanation, without proving its mechanism. |
| Coverage omissions concern final-answer completion | Correct relationships or retrieved texts are sometimes missing from otherwise useful notes. | Required evidence-linked fields still produce omissions or unsupported conclusions after complete evidence is supplied. |
| Coverage evidence navigation or task breadth causes omissions | Traces contain extensive retrieval; some successful notes use fewer operations. | Supplying the exact changed texts directly leaves omissions unchanged; or completion improves without changing retrieval. |
| Grading explains the apparent coverage failures | Two grading judgments changed, but the unchanged final key still leaves no passing condition. | Independent application of the frozen key finds further material grading errors. Existing evidence does not establish them. |

These are hypotheses about observable behavior. None requires an inference about a model’s internal thought process.

## Recommended fresh test

I recommend a **coverage completion ablation**, conditional on the workflow join finding a real unresolved reconciliation decision.

Use one fresh public packet and two frozen cases: its unchanged reviewed candidate and a neutral combined variant with changed reviewed text plus an added document. Preserve the accepted distinction between content-map membership, separate review association, changed-text interpretation, and publication evidence. Do not reuse the retained packet as independent confirmation.

Use two ordinary profiles that succeeded on the retained unchanged case, provisionally Sol 6.1 Low and Luna 6 High. This is a controlled diagnostic choice, not a profile selection. Freeze three presentations:

1. **Current presentation:** existing relationship summary, source access, and free-form reconciliation note.
2. **Completion structure:** the same inputs and access, with required fields for the separate review association and each changed text’s cited interpretation. Deterministic facts appear from the verified producer rather than being regenerated in prose.
3. **Direct changed-text delivery:** the same completion structure, with the complete changed texts and their identities supplied before judgment.

That is twelve fresh cells before any repetitions. Keep contexts independent and freeze order, request limits, labels, and grading before execution. Retain every failure and skipped cell. Independent evaluators should grade the delivered note against source bytes, including the unchanged-case control for unnecessary review demands.

The stage change is substantive: it tests explicit completion and removes model regeneration of exact mechanical facts. It does **not** merely supply `relationship_summary` again. Structural checks may detect a missing field or invalid citation, but cannot declare a semantic interpretation correct.

Interpret the outcomes narrowly:

- Improvement from presentation 1 to 2 supports a completion or assembly explanation.
- Additional improvement from 2 to 3 supports an evidence-access or navigation explanation.
- Persistent semantic errors in 3 count against both as sufficient remedies and favor narrowing the semantic task or retaining ordinary handling.
- Unnecessary intervention on the unchanged control defeats the candidate under the accepted no-false-steering bar.
- Equivalent correct results with equal or less ordinary work favor omission.
- A diagnostic pass permits further preparation; it does not qualify adoption or replace the original critical-case requirements.

Before execution, include the complete actual coverage payload and function-result identities in the evidence contract. That closes this investigation’s main attribution gap.

If the workflow join instead finds a genuine early claim-correction opportunity, the smaller alternative is a fresh publication-scope contrast comparing the current four-way question with staged questions mapped back to the **same four accepted relations**. Keep Jev, Decisions, Luna, and Sol eligible; include supported, contradicted, and genuine conflicting-source controls. Hold evidence constant first. A later salience comparison needs its own hypothesis so question design and evidence selection are not changed together.

## What would change the integration decision

The diagnostic can establish whether a narrower stage produces a complete, evidence-bounded answer on fresh cases. An eventual useful integration additionally needs a prospective author or publisher checkpoint showing that the answer arrives before ordinary work has settled the decision and changes a correction, rereading decision, or reconciliation effort.

If preparing the inputs already resolves the question, omit the semantic addition. If deterministic rendering supplies the useful result, retain that independently. Jev remains eligible for a narrow typed relation question; it is not assigned exact hashing, file-count reconciliation, or generation of the complete coverage note. Decisions remains eligible for a newly specified relation design.

Required review remains in every workflow. Native benefit requires observed author/publisher use and terminal quality, not merely production of a note. These distinctions follow `semantic-support.md`, lines 98–130, `publication-coverage.md`, lines 107–160, and the [integration decision](https://github.com/nisavid/provingkit/issues/448).

## Costs and missing measurements

The known claim request equivalent is USD 0.072418353 across 60 completed requests. The known coverage request equivalent is USD 0.382253650 across 43 usage-bearing attempts; failed-submission usage is unknown. These frozen-rate equivalents are not verified bills or complete-workflow costs.

Coverage records 234 requested/prepared function calls, 2,203,428 prepared serialized-result bytes, and 3,600,072 submission-attempted replay bytes. Replayed bytes are not unique source bytes or known provider consumption. See `claim-results.md`, lines 24–41, and `coverage-results.md`, lines 32–42.

| Component | Present status and required next measurement |
| --- | --- |
| Setup, question design, producer work, review, and maintenance | Whole effort unknown; record separately from episodes. |
| Claim/path selection, retrieval, preparation, rendering, and refresh | Native cost unknown; retain source reads, bytes, time, invalidations, and whether preparation already answers the question. |
| Model/service attempts, caches, retries, failures, skips, and unused outputs | Preserve every attempt and available counters; failed usage remains unknown. |
| Consumer interpretation, edits, rereads, and downstream rework | Native benefit unknown; preserve decisions and revisions through final required review. |
| Operator interruptions and recovery | Active effort unknown; record actual questions, interventions, and recovery time. |
| Latency | Retained request/cell timings exist; end-to-end usable-result latency remains unmeasured. |
| Constrained model capacity | Verify attribution and cumulative/cache boundaries; tokens do not establish subscription quota savings. |
| Money | Known request-rate equivalents exist; attributable billing and complete costs remain unknown. |
| Shared preparation and amortization | Count shared work once, retain standalone and marginal costs, and declare any reuse assumption before claiming savings. |

Unnecessary interruptions remain the first accepted cost priority, followed by constrained expensive-model capacity; latency and money stay separate. No new success rate, confidence threshold, or acceptable-cost trade-off is proposed.

## Retained evidence identities

Claim records belong to run `0717f357617f425c97fc258c82b32b81`. Each suffix below completes its original attempt ID:

| Case/route | Attempt suffix | Original-record SHA-256 |
| --- | --- | --- |
| c01 Jev | `slot-0000/attempt-0000` | `5e96c4bf3049ee4f307dc146a229307e90b672496735b9836f9ff51b28359795` |
| c05 Jev | `slot-0026/attempt-0000` | `a683efc45981558f385e0586d9c0bf83b170f89f36279a2bea399724e0ce9361` |
| c07 Jev | `slot-0031/attempt-0000` | `1c29013587e9ce5c26bd4a500d3fc832024a186cca152d07c14ee2473cbfc158` |
| c07 Decisions | `slot-0032/attempt-0000` | `a8b9bd0817573fef6faa641f5e94f04310740e8922958a3141c012deccd396ec` |
| c09 Jev | `slot-0052/attempt-0000` | `a3ee5aedfa2e7ad6009fee2ff16ec409854c79dede992c22368c47536b0254ca` |
| c09 Decisions | `slot-0053/attempt-0000` | `9b7e2aa265f9c10c2684c8f6b33b153e7c7c2a2be0a6a7c30fcca7214e9ec8f4` |
| c10 Jev | `slot-0057/attempt-0000` | `735b44cdb41efdd54ceb0fb50ef999672a8087d13b914b0054d9cf7ff4bd7818` |

The retained claim projection is `claim-evidence.json`, SHA-256 `de0a402f310251f5ca982a4a87745577bb53a2a04e49c691534abe2a42086696`; its grades are `claim-grades.json`, SHA-256 `43aed38a1b3d2d1756b841659965fb5a757bbffe533c8d6b60ec34b1e285da7f`.

Coverage records belong to run `204973ddb827410fad143394b9b49f57`. Output IDs identify records in `coverage-opaque-outputs.json`, SHA-256 `4b6f6f638f8b60d0ae6d592fd7a1f019270e4f1f0b56162c08b08aa43442ac79`; `coverage-output-mapping.json`, SHA-256 `616f8a5082321cda7329fe16db3600838624661aca179465daf1ffa7716b130e`, preserves the original cell IDs and summary hashes. Final grades are `coverage-final-v3-grades.json`, SHA-256 `1e6ac9202807fd4b22d978146552d7dce9d46f60106517d21143e1ff9fa76ba4`.

The next contract author should load the maintained comparison procedure, consume these frozen observations, and choose the diagnostic whose consumer opportunity survives the workflow join. No procedure edit, experiment, or integration assignment was executed here.
