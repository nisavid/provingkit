# Reconcile a commit candidate with its existing review record

A small deterministic view can expose byte differences using the existing Git objects and verification record. The retained nine-file example does not yet establish that the view helps: the ordinary report already explains its seven recorded content files and two supporting records. I recommend a local comparison of that strong baseline with changed-byte and added-path controls, followed by omission if the view adds no useful information or reduces no reconciliation work. This preparation is ready for a local prototype proposal; execution still needs its own accepted contract.

The consumer is the publishing agent deciding what the existing review record supports for a particular commit candidate and where closer inspection is needed before making a review-coverage claim. The proposed view is an addition to ordinary preparation. It removes no required review, authorizes no publication, and supplies no permission or safety judgment.

## Evidence and supported input

I reconstructed the parent-to-child **commit candidate**, not an observed push:

- Parent: `010133a2f1f9548ef49932528a67e36d45c8f0d2`.
- Child: `5eb3a02a0d714901ea6f2a480601e6772d1e1d10`.
- Manifest: `docs/superpowers/research/evidence/jev-axi-consumer-opportunities-2026-10-04/verification.json`, SHA-256 `ddc15fb627aeca4a00be7d8993ae99403365fe36408287f7d294a46857d3faad`.
- Every path below is relative to `docs/superpowers/research/evidence/jev-axi-consumer-opportunities-2026-10-04/`.

All nine paths are additions in this parent-to-child difference. The seven values in `reviewed_public_inputs` match the child blobs. The following is a worked mechanical output computed from those objects; “absent” means absent from that particular content map.

| Candidate path | Candidate SHA-256 | Comparison with content map |
| --- | --- | --- |
| `README.md` | `e0cf866e2a446e2d5b46554e49a9b3152eef2ceab1df0534767c033b09b46a9f` | Equal |
| `capability-discovery.md` | `ecb2c99227e8c4c16df5c970b4601c998cc582aeca58decd3d9ea89edc5107ea` | Equal |
| `completion-evidence.md` | `e3bfc856cb7937b16808edc9d6da5c876ec4abd1f09dad586f9ac108272c7ef9` | Equal |
| `design-join.md` | `b1ec9ecfe8ffaf61b1cdd77f7ec1c2788148d7c8699b8eb29173bd0e15b4689d` | Equal |
| `research-record.json` | `850c3f8b0ba1cca0772eb68bd519f645a50ad5ba57f6d2601855eb7368edd7c7` | Equal |
| `resumption-continuity.md` | `31dda347a7a929fced73c36c3e5843c29b7897492f86bd63c8ffccbce758114d` | Equal |
| `review.md` | `4cfd2b2b638bcbe93029a77fa65e134f26ff8a69dc6575edc9c8966f6838a913` | Absent |
| `shared-preparation.md` | `d7ff28039ed72a7ddcd7edd20c343d766e762721c246a45ec9c122dabcc16fa7` | Equal |
| `verification.json` | `ddc15fb627aeca4a00be7d8993ae99403365fe36408287f7d294a46857d3faad` | Absent |

The manifest separately contains `review_sha256`, which matches `review.md`. Preserve that as a distinct supporting-record comparison. Moving it into the content map would misstate the map's scope. The manifest does not contain a content-map entry for itself; no recursive self-review or new semantic ledger is needed to display that fact.

The [review][review] reports no actionable findings for the seven-file public candidate and projected tracker texts, covering factual support, scope, accounting, evidence boundaries, links, and prose. The [ordinary push-workflow report][report] already explains the nine/seven distinction. These are retained source/review records. The historical actual pushed refs, destination observations, accepted-push receipt, and full pushed range are unavailable in the supplied evidence. A nine-file commit cannot be relabeled as a nine-file push.

| Field | Available fact | Interpretation or missing premise |
| --- | --- | --- |
| Candidate identity and changed paths | Exact parent, child, nine additions, and child blob bytes | Actual outgoing publication range absent |
| Content-record membership | Seven explicit path/digest entries; two paths absent | Absence does not establish a missing required review or an exemption |
| Byte relationship | Seven equal digests; separately matching review digest | Equality does not establish completeness, dependency freshness, or present applicability |
| Review result and scope | Recorded clean result and named review focuses | No blanket conclusion that every outgoing object or dependency is covered |
| Manifest `base` | Equals the reconstructed parent | Its field name alone does not encode a complete publication or review-dependency contract |
| Runtime and benefit | Manifest explicitly records both as unqualified | No runtime qualification, savings, or publication-readiness result follows |
| Operational checks | The report identifies source requirements and unavailable execution evidence | Missing records are not proof that required checks failed or were omitted |

The later [publication observation][publication] ended before its later successful push and left operator effort unmeasured. The [resumption study][resumption] supports retrieval and reuse of a saved review choice without measured avoidable reconstruction. Neither supplies a hidden benefit estimate for this view.

## Candidate inputs and worked outputs

The retained case is the original commit candidate above. The next two cases are **authored controls**, calculated in memory from its bytes. They are not additional historical commits or native push observations.

Mechanical producer fixtures preserve the parent/child identities, original blobs, exact overlay instructions, and expected relationships. Construction instructions and expected outputs stay in evaluator state. Consumer packets contain the resulting candidate identities and blobs, the unchanged manifest and review, the ordinary report with its historical identity visible, and ordinary task instructions. All arms receive access to the same underlying sources. The explicit test language in the two overlays below makes them suitable for mechanical checks only; the consumer comparison uses the neutral variants defined afterward.

**Changed recorded bytes.** Append exactly the following UTF-8 string to the original `README.md`, preserving every original byte:

```json
"\nAuthored publication-coverage control: this line is outside the recorded content.\n"
```

The result is 8,470 bytes, SHA-256 `801bd15603e59fcf52416684be43007dad6cc7bdcc571691f134a778c7074a5d`. The original is 8,387 bytes. This intentionally harmless edit tests whether changed identity causes precise inspection rather than an invented defect.

The view would return:

```text
scope: authored overlay of the retained commit candidate
content-map equal: 6
content-map different: 1
content-map absent: 2
README.md:
  recorded: e0cf866e2a446e2d5b46554e49a9b3152eef2ceab1df0534767c033b09b46a9f
  candidate: 801bd15603e59fcf52416684be43007dad6cc7bdcc571691f134a778c7074a5d
  relationship: different
review.md:
  content-map relationship: absent
  separate review_sha256 relationship: equal
verification.json:
  content-map relationship: absent
review applicability: not determined by this view
```

**Additional candidate document.** Retain the original nine files and add `additional-publication-note.md` in the same directory, with exactly these 92 UTF-8 bytes:

```json
"# Additional publication note\n\nThis authored file is outside the supplied content manifest.\n"
```

Its SHA-256 is `98c65687f86e6c7f6def1b9c4f0f6f01f946fabfa87c6676cc62b8b7e6fc4816`. The output becomes seven equal entries, zero different entries, and three absent paths, explicitly naming the added document alongside the two supporting records. The same “absent” relationship is correct for all three; their roles and applicable review requirements can differ.

A combined overlay would yield six equal entries, one different entry, and three absent paths. It can test that the changed README does not distract the consumer from the extra document. Do not supply these counts or explanations as candidate answers.

**Neutral consumer controls.** Append the following text to the original README for the changed-content consumer case:

```json
"\nThe evidence records the declared scope of each source review.\n"
```

The resulting file is 8451 bytes, SHA-256 `685f67222930e50531b64b96fc07a43823a1a784f2d92ac3e19782866010f343`. For the added-path consumer case, retain the nine original files and add `publication-context.md` with these bytes:

```json
"# Review context\n\nThis note describes the public research materials considered for publication.\n"
```

The added file is 96 bytes, SHA-256 `eb018e9da4189250105634a5f4ca41893d077f655e2012f2969e9224bac5ec1a`. These are newly authored variants, separate from the mechanical examples above. Their relationship counts are the same: six equal, one different, and two absent for the README variant; seven equal and three absent for the added-path variant; six equal, one different, and three absent for their combination. Those counts, construction instructions, provenance labels, and intended findings stay outside consumer packets. A later producer must materialize and freeze the resulting candidate objects before execution; these in-memory constructions are preparation evidence only.

**Equal bytes with a missing premise.** Use the unchanged retained case and ask whether all required reviews are current and complete for an unspecified actual push. The correct mechanical table remains unchanged. The view has no supported answer to the broader question because the actual range and complete obligation/dependency evidence are absent.

**Unavailable comparison.** Supply the same candidate with an unavailable manifest, malformed digest, or unavailable blob as separately identified authored variants. Display the affected relationship as unavailable with its reason, never as equal, different, or absent-by-default. A record that could not be read has not established absent membership.

## Minimum producer and ordinary alternatives

The producer needs only an explicit comparison range, its Git blobs, and an explicitly supplied verification record. For this preparation those inputs exist. It does not discover “the latest relevant review,” infer the intended push, construct requirements, or decide whether reviews satisfy policy.

1. Resolve the caller-supplied parent and child and enumerate their full path difference. Keep the comparison kind visible. Reading the existing Git objects suffices for the retained case.
2. Read the supplied manifest as data, validate the expected map and digest shapes, and retain its source identity. A different record schema is unsupported until mapped explicitly.
3. Read child blobs and compute SHA-256. Compare exact paths and bytes; include content-map entries outside the candidate difference in a separate inventory rather than dropping them silently.
4. Render equal, different, absent, or unavailable relationships with source links. Display `review_sha256` as its existing separate association. Keep recorded scope/result text adjacent without converting it to a new verdict.
5. Refresh the comparison when candidate or record bytes change. The consumer interprets the specific differences using ordinary instructions and review evidence.

A prototype can use read-only Git extraction plus a small parser and table renderer. This is a feasibility sketch, not an implementation performed here. It initially supports this explicit commit range and manifest schema. Ref sets, new branches, deletions, renames, submodules, inaccessible objects, and partial/truncated acquisition require explicit support or an unavailable result; they are not silently qualified by the nine-file example. An actual pre-push integration would additionally need a verified producer of every intended ref update and its corresponding range.

| Arm | What the consumer sees and does | Work charged |
| --- | --- | --- |
| Ordinary publication preparation | Existing report, source links, manifest, review, Git difference, and normal instructions; free to use ordinary Git/hash tools or improve the ordinary report | Actual retrieval, any manual reconciliation or report refresh, interpretation, required review, and corrections |
| Deterministic addition | The same preparation plus the proposed relationship table and specific source links | Producer setup and maintenance, per-case reads/hashing/rendering, consumption, interpretation, refresh, required review, and corrections |
| Omit the addition | Ordinary preparation with no new producer or recurring table | Ordinary costs remain; no fictional saving from removing a required step |

There is no established publication-coverage view to remove, so omission and the ordinary arm coincide on behavior here. Keep both choices explicit rather than manufacture a weaker baseline. In particular, a concise current ordinary report may already deliver everything the table offers; measure its preparation cost rather than forbid that report.

Jev, the service, is not needed for exact path membership or digest comparison. The jev-axi integration has separate input, delivery, and coverage limits; this proposed producer is not evidence that its existing push payload is complete. A semantic question about obligations would require additional supported facts and a separate design. No Jev arm is assigned here, and no service price, cookbook confidence threshold, or model-performance assumption enters this comparison.

## Feasible comparison and evaluator-only grading

A later local trial can give a publishing agent the concrete task: “Explain what the supplied review supports for this commit candidate and identify anything needing closer inspection before making a review-coverage claim.” It would use disposable, read-only candidate packets and return a reconciliation note, with no push. Freeze the runner, model, instructions, exact packet bytes, output presentation, available tools, order, repetitions, and measurement route before execution.

Use fresh isolated agent contexts for each arm/case, with the same allowed sources and task. Separate the evaluator key below from packets and record prompts plus delivered outputs. Alternate or randomize arm order when sharing constrained execution resources. A human comparison requires distinct matched cases or an explicit carry-over limitation; repeatedly showing the same nine files teaches the answer.

The consumer comparison uses the retained case, neutral changed-content and added-path variants and their combination, the broader-question case, and unavailable-input cases. The explicitly labeled overlays above remain mechanical producer tests. Its authored results can qualify mechanics and expose a usability hypothesis. They cannot demonstrate that ordinary native work makes the planted mistake or that the addition prevents one. If the local result is promising, a separately accepted ordinary publication-preparation task is the next benefit test, preserving required reviews and native controls.

The evaluator's answer key follows. It is a grading resource, not candidate context:

| Case | Useful consumer result | False steering to count |
| --- | --- | --- |
| Retained candidate | Cite the seven matching content records, distinguish the two supporting records and separate review hash, preserve the commit/push boundary | Treat either support file as necessarily unreviewed or exempt; declare push-wide coverage |
| Changed README | Identify the exact changed file and inspect its supplied added line; avoid carrying the old byte-bound review statement onto new bytes | Invent a defect, demand broad unrelated rereview, or claim equality proves current review |
| Added document | Identify the extra path and determine applicable handling from supplied ordinary instructions | Automatically declare missing mandatory review solely from map absence |
| Combined overlay | Account for both authored differences and both supporting records without losing either difference | Correctly flag one difference while overlooking the other |
| Equal bytes, broader question | Keep the mechanical result and explicitly limit the broader claim | Certify completeness/currentness or ask the operator to repeat facts already supplied |
| Unavailable comparison | Preserve uncertainty, name the affected input, and fall back to ordinary inspection when available | Turn parse/read failure into a clean result, omit the affected path, or cause an unnecessary stop |

A useful result may be correct non-action: the historical report already answers the question. Grade factual relationships, evidence-boundary accuracy, useful next action, final note quality, and any real correction separately. Count unnecessary questions, duplicate warnings, redundant stops, mistaken review demands, and consumer time spent chasing harmless record absences. Required review remains required in every arm.

The accepted bar is that every agreed critical case passes within the supported claim, with no added false steering, redundant stops, unnecessary questions, or reduction in final task quality. A cheaper but less reliable arm does not win by an invented trade-off. These cases establish no population rate.

Safety and task alignment remain separate: this read-only local comparison leaves safety efficacy unmeasured; it can measure accurate reconciliation, successful progress, and false steering. Preserving permissions is not a new safety result.

## Benefit hypotheses, costs, and decisions

The positive hypothesis is that the deterministic view exposes a consequential change sooner or reduces actual reconciliation work after paying for its producer. For example, it may direct the consumer to the changed README and extra document without manually reconstructing the seven-entry association. Whether that saves work or changes the final note remains unmeasured.

The defeat test is the unchanged case with the existing explanation plainly available. If the consumer reaches the same correct result with equal or less complete effort under ordinary preparation, the view has shown no marginal benefit there. If the same holds across the authored contrasts, omit this addition for the supported scope. Mere reformatting, an accurate table, or a planted discrepancy found by every arm is not evidence of incremental prevention.

A second defeat is increased friction: repeated flags on the two supporting files produce unnecessary rereview, questions, or stops. Narrow the presentation or reject it. Another honest outcome is uncertainty: successful mechanics with mixed timing or incomplete accounting supports neither an economic winner nor native benefit.

| Cost or observation | Measurement route for a later accepted trial | Current status |
| --- | --- | --- |
| One-time preparation and maintenance | Record packet/producer design, implementation, review, and schema-change effort separately | Unmeasured |
| Recurring preparation, retrieval, selection, hashing, and rendering | Time and preserve each producer invocation and ordinary retrieval path; include bytes and failures | Unmeasured |
| Refresh and repeated checking | Record changed inputs, invalidated outputs, reruns, and consumer rereads | Unmeasured |
| Every model or Sys1 attempt | Retain attempt identities, usage, errors, skipped/unused output, retries, and cache attribution | No experimental attempts; research use is separate and unaggregated |
| Downstream agent work | Record source inspections, interpretation, corrections, required review, and terminal note | Unmeasured |
| Operator attention and recovery | Record actual questions, interventions, verification actions, and manual recovery; do not infer effort from count alone | Unmeasured |
| Latency | Measure from available candidate inputs through the final usable note, including failures and recovery | Unmeasured |
| Constrained model capacity | Preserve supported per-attempt usage and verify cumulative/cache endpoints before aggregation | Unknown |
| Money and quota | Use attributable provider/account evidence only within separately accepted access; otherwise report unknown | Unknown |
| Shared production | Count shared retrieval once in combined work, retaining standalone and marginal costs; disclose amortization assumptions | No measured allocation |

Apply the [accepted purposes and priorities][acceptance]: unnecessary interruptions first, then constrained expensive-model capacity; report latency and money separately. Report each case before aggregates and keep failed or abandoned runs. Token counts alone do not establish billing or quota. If benefit and complete costs do not decide the choice, return the specific unresolved trade-off rather than invent a numerical threshold.

Stop this preparation at the worked examples and feasible design. Do not collect private history or another native observation merely to finish it. Defer a local trial until its concrete execution contract is accepted. Stop or narrow a producer that needs a comprehensive semantic ledger, guessed record selection, or unsupported push-range acquisition. Candidate or material evidence changes invalidate affected review.

The smallest open decision is whether to authorize the local comparison of the ordinary report against this deterministic addition, using the stated cases and full producer costs. No missing factual premise prevents that local prototype. A later push-wide claim would first need observed actual ref/range inputs; native benefit would need observed useful effect in an ordinary task.

## Source identities and procedure handoff

This preparation consumed the frozen repository revision `7f16d22c5794787ce7db346087d5d38b57bd6ccd`. The [joined opportunity report][join] governs the correction from “observed outgoing range” to commit candidate. The original review and manifest remain pinned to the historical child above.

The maintained consumer procedure is `handling-sys1-incidents`, especially `.agents/skills/handling-sys1-incidents/references/comparison-contract.md`, SHA-256 `9f876cd27c4bd6fe82d56feabc6e31e05d029d7cac18f9651194218e2e1aa981`. I used `capturing-agent-procedures` for this unchanged-procedure handoff, `adopting-jev` for the deterministic/semantic distinction, and `checkpointing-and-publishing-git-work` in its read-only mode. The research skill's further-delegation step was excluded by the bounded assignment.

The next contract author must load that maintained procedure before execution, consume this artifact's exact reviewed revision, freeze cases and evaluator separation, and return case-level outcomes with whole-workflow costs and evidence limits. This research proposal adds no installed convention. Its publication and independent review remain with the coordinator.

All eleven dispatched input hashes matched before and after this work. The canonical plan and exact request hashes matched the dispatch. The owning checkout remained clean at the frozen revision, with seven local commits ahead of its tracking ref. I read public repository evidence and Git objects, computed the displayed hashes and authored-overlay bytes in memory, and performed no writes, experiments, Jev calls, private-history collection, external action, or subdelegation.

[join]: https://github.com/nisavid/provingkit/blob/7f16d22c5794787ce7db346087d5d38b57bd6ccd/docs/superpowers/research/evidence/jev-axi-opportunity-join-2026-10-07/README.md
[report]: https://github.com/nisavid/provingkit/blob/7f16d22c5794787ce7db346087d5d38b57bd6ccd/docs/superpowers/research/evidence/jev-axi-workflow-opportunities-2026-10-05/push-workflow.md
[review]: https://github.com/nisavid/provingkit/blob/5eb3a02a0d714901ea6f2a480601e6772d1e1d10/docs/superpowers/research/evidence/jev-axi-consumer-opportunities-2026-10-04/review.md
[publication]: https://github.com/nisavid/provingkit/blob/7f16d22c5794787ce7db346087d5d38b57bd6ccd/docs/superpowers/research/evidence/jev-axi-publication-observation-2026-10-05/results.md
[resumption]: https://github.com/nisavid/provingkit/blob/7f16d22c5794787ce7db346087d5d38b57bd6ccd/docs/superpowers/research/evidence/jev-axi-resumption-study-2026-10-06/results.md
[acceptance]: https://github.com/nisavid/provingkit/blob/7f16d22c5794787ce7db346087d5d38b57bd6ccd/docs/superpowers/research/2026-10-02-jev-axi-remaining-family-acceptance.md
