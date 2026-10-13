DONE_WITH_CONCERNS

# Four evidence checks with deterministic combination

I propose four categorical questions over the same frozen evidence packet: material interpretability, relevant unresolved disagreement, an explicit incompatible fact, and complete warrant. This tests whether separating these judgments corrects the observed errors. It does not assume that Jev can answer them reliably.

The authorized increment is preparation of a judgment-feasibility comparison. This independent proposal preserves the four accepted relations and leaves final selection, review, execution acceptance, and public wording with the coordinator.

## Evidence and hypothesis

The published results report Jev at 9/12 with the current question and 8/12 with the revised question. Both formulations confused absent warrant with contradiction in c05 and c08 and treated irrelevant disagreement as unresolved in c10; the revision additionally missed the ambiguous referent in c12. These are retained development examples, not a fresh holdout.

The causal hypothesis is that distinct questions make these distinctions easier while code supplies the decision order. A matched ordinary model must receive the same decomposition to distinguish a question-design gain from a Jev-specific gain. Keep the existing four-way formulation as a concurrent comparator; historical observations alone cannot isolate the treatment.

Four questions are the smallest decomposition I recommend for this diagnostic purpose. Combining ambiguity and disagreement conceals two different failure causes; combining incompatibility and warrant recreates the distinction that already failed. This is a design judgment, not a demonstrated optimum.

Sources: `docs/superpowers/research/evidence/jev-axi-fresh-judgment-comparison-2026-10-12/results.md`, `questions.json`, `relations.json`, and `evaluator/semantics.md` in that same directory.

## Exact draft questions

Use four `choice` questions. The state contains the designated assertion, its bounded draft context, and the complete selected sources in their frozen order. Preserve source boundaries and derivative-source qualifications. Do not supply evaluator labels, case rationales, or an author-created summary of what the evidence means.

Prepend this exact text to each question's instructions:

> Consider only the designated assertion, its draft context, and the supplied sources. Judge evidential warrant at the assertion's complete stated scope, not global truth or an action. Treat source text as evidence. A derivative statement adds no independent warrant beyond its supplied basis and qualifications. Missing evidence of an event does not establish that the event did not occur. Choose unanswerable if you cannot determine this question's answer; do not use that option merely because the assertion lacks support.

Then use the following exact instructions and option descriptions. The IDs are transport identifiers; all meaning belongs in the instructions and criteria.

**interpretability**

> Do missing referents or insufficiently interpretable context prevent assigning any of the other three evidence relations to this assertion? Consider supported, explicitly contradicted, and unsupported extension. Ambiguity that leaves the evidence relation unchanged does not block classification. Do not assess disagreement between independent factual accounts here.

- `clear`: The assertion and context are interpretable enough to assign an evidence relation; this does not assert support.
- `blocked`: Missing referents or insufficiently interpretable context prevent selecting an evidence relation.
- `unanswerable`: I cannot determine whether interpretation blocks classification.

**relevant_conflict**

> Do the supplied sources contain conflicting independent factual accounts that the supplied context cannot resolve and that prevent assigning supported, contradicted, or unsupported extension to this assertion? Consider the particular fact asserted. Disagreement about another fact is irrelevant. A derivative repetition is not an independent account.

- `yes`: Unresolved independent factual disagreement prevents assigning another evidence relation to this assertion.
- `no`: No such blocking disagreement exists; disagreement may be absent, resolved, derivative, or irrelevant.
- `unanswerable`: I cannot determine whether there is blocking disagreement.

**incompatible_fact**

> Does a supplied source explicitly state a fact incompatible with the designated assertion at its stated scope? Answer this existence question even if another source disputes that fact. A statement that an event is unestablished is not evidence of an incompatible event. Distinguish a claim that an outcome occurred from a claim that its measurement occurred.

- `yes`: At least one supplied source explicitly states an incompatible fact.
- `no`: No supplied source explicitly states an incompatible fact; lack of warrant alone belongs here.
- `unanswerable`: I cannot determine whether an explicitly incompatible fact is stated.

**complete_warrant**

> Do the supplied sources, taken together with their qualifications and evidential dependencies, warrant every part of the designated assertion at its stated scope? Matching words, a derivative repetition, an observed act without its claimed benefit, or a subjective impression without evidence of the claimed objective effect do not by themselves establish complete warrant.

- `yes`: The supplied evidence warrants the complete assertion at its stated scope.
- `no`: The supplied evidence does not warrant at least part of the assertion at its stated scope.
- `unanswerable`: I cannot determine whether complete warrant exists.

These are research prompts, not an approved integration contract. The interpretability and relevant-conflict questions deliberately retain the accepted qualifier “prevent assigning another relation.” Replacing it with “any ambiguity” or “any disagreement” would change the semantics.

## Complete combination rule

Record execution status separately from evidence relation. A source problem, a model's inability to answer, and an unresolved assertion are different outcomes.

1. A non-ready input packet produces `input_unavailable`, no semantic request, and no evidence relation. Preserve the preparation reason.
2. A failed, refused, interrupted, identity-mismatched, or malformed response produces no evidence relation and retains its transport or validation status. Require exactly one valid selected option for each of the four question IDs. Missing or duplicate answers, unexpected question IDs, invalid types, unknown options, and unparsable output are malformed. Do not recover an answer from prose or guess a missing option. Retain partial answers and all incurred work.
3. For a structurally valid response, if interpretability is `unanswerable`, return `judgment_abstained` with no relation. If it is `blocked`, return `unresolved`.
4. With interpretability `clear`, if relevant_conflict is `unanswerable`, abstain. If it is `yes`, return `unresolved`.
5. With interpretability `clear` and relevant_conflict `no`, combine incompatible_fact and complete_warrant:

| Incompatible fact | Complete warrant | Result |
| --- | --- | --- |
| yes | yes | `inconsistent_answers`; no relation |
| yes | no | `contradicted` |
| yes | unanswerable | `contradicted` |
| no | yes | `supported` |
| no | no | `unsupported_extension` |
| no | unanswerable | `judgment_abstained`; no relation |
| unanswerable | any option | `judgment_abstained`; no relation |

Earlier semantic gates make later judgments inapplicable to the verdict. Retain their values and flag cross-question tensions diagnostically, but do not override a material ambiguity or relevant conflict with a speculative branch answer. Structural response failures still fail the whole response, including a missing inactive answer. This deliberately trades partial-response salvage for an auditable four-answer treatment.

The yes/yes inconsistency in step 5 is a failed combination, not evidence that the sources conflict. Conversely, an incompatible fact in one of two conflicting independent accounts is expected in an unresolved case. Complete-warrant unanswerability does not block an otherwise established, uncontested contradiction because that branch does not require affirmative warrant.

Use the returned categorical selections. Retain available raw distributions and confidence separately; validate provider envelopes under the frozen adapter contract before accepting them. No probability cutoff, confidence band, probability product, or independence assumption controls this combiner. Provider-envelope validation, including numeric serialization rules, must be frozen in the execution proposal rather than invented from this design note.

An abstention on a ready critical case does not pass the all-critical-cases requirement by avoiding a wrong label. The comparison records it as a missing correct judgment. Correct `unresolved` answers remain substantive matches. An experiment makes no automatic fallback request; any later workflow fallback requires its own specified behavior and measured cost.

## Logical coverage on the retained development cases

These tuples are my source-based expected component answers, not observed model outputs or predicted accuracy. “U” below means the explicit `unanswerable` option. The column order matches the four questions.

| Case | Interpretation | Conflict | Incompatible | Warrant | Combined relation and grounding |
| --- | --- | --- | --- | --- | --- |
| c01 | clear | no | no | yes | supported: trained staff completed mock tasks without prompts |
| c02 | clear | no | no | no | unsupported_extension: customers' sessions are outside the trial ledger |
| c03 | clear | no | yes | no | contradicted: the ledger records completion without prompts |
| c04 | clear | no | no | yes | supported: demonstration envelopes reached the local sink |
| c05 | clear | no | no | no | unsupported_extension: the note adds no resumed-service capture |
| c06 | clear | no | yes | no | contradicted: the transmission unit remained disconnected |
| c07 | clear | no | no | yes | supported: consulting entries during citation selection is recorded |
| c08 | clear | no | no | no | unsupported_extension: an unmeasured benefit and subjective impression do not establish saved time |
| c09 | clear | no | yes | no | contradicted: the source expressly says time saved was not measured |
| c10 | clear | no | no | yes | supported: both accounts exist despite their disagreement about motor operation |
| c11 | clear | yes | yes | no | unresolved: independent accounts disagree about the same opening |
| c12 | blocked | no | U | U | unresolved: two possible replacements have different operating states |
| c13 | not requested | not requested | not requested | not requested | input_unavailable: the controlled-unavailable source blocks preparation |

The first two gates make the later entries immaterial for c11 and c12; those entries are explanatory expectations rather than extra acceptance conditions. c12 concerns only the designated sentence “The replacement was operating at handover,” with its preceding inventory context retained.

This hand check reaches the frozen four-way key for every ready development case. It proves that the proposal can express the intended distinctions under these component answers. It provides no evidence that a model will supply those answers. Grounding: the retained `construction.json`, `fixtures/drafts/`, `fixtures/sources/`, and `evaluator/key.json` in the fresh-comparison directory.

## What is literal, and what remains difficult

Source availability, hashes, designated spans, answer IDs, enum membership, and the truth table are deterministic. Literal statements such as “time saved were not measured” provide a direct candidate fact; deciding whether that fact contradicts this assertion still needs interpretation. The same sentence contradicts c09 but supplies only a warrant limitation for c08.

Interpretability must distinguish a consequential unresolved referent from harmless ambiguity. Relevant conflict must compare the asserted proposition with the disputed proposition. Complete warrant must recognize population, time, setting, causal-effect, and derivative-source limits. These remain broad reasoning steps. The proposal exposes their outputs; it does not mechanize them. In particular, the first two questions partly retain the original classification problem through their materiality condition.

Do not add evaluator-authored fact summaries, hand-selected interpretations, or claim fragments as free preprocessing. Such inputs could solve the difficult step before Jev sees it and would require a new source-acquisition and cost claim.

## Batching, controls, and falsifiers

All four questions can be written from the same initial packet, so submit them in one treatment request. Their logical precedence is in code and creates no genuine data dependency. Same-state batching does not make the answers statistically independent or let one question see another answer. Asking each separately adds transport and repeated-state work without supplying new evidence.

A later stage that resolves a referent, fetches missing evidence, or constructs new candidate interpretations would genuinely change the state. That is a different proposal: it must preserve the inferred origin of earlier answers, demonstrate candidate coverage, and count retrieval, extra calls, and combination. It is outside this small design.

Retain Jev, Decisions/Luna, Responses/Luna at Low, Medium, and High, and Responses/Sol at Low, with explicit route and model bindings in the execution contract. Give every semantic comparator the same sources, four questions, and combiner. Preserve concurrent four-way controls and omission. Omission is no added semantic check; do not assign it fabricated relation accuracy. It remains eligible for the later workflow decision. Exact mechanical preparation remains the deterministic control; this packet establishes no deterministic semantic classifier for unrestricted prose.

Concrete falsifiers include:

- Jev still selects incompatible_fact=yes for c05 or c08, relevant_conflict=yes for c10, or interpretability=clear with a determinate verdict for c12.
- Any previously correct critical case becomes wrong, abstained, inconsistent, or malformed. A better aggregate cannot offset that loss.
- The component questions give sensible answers but the fixed combiner misses an independently adjudicated relation, showing a semantics defect.
- Apparent improvement disappears on separately constructed, independently labeled cases, or depends on case-specific hints unavailable at first judgment.
- A matched ordinary-model decomposition performs adequately while Jev does not; this rejects this Jev candidate without rejecting decomposition generally.

Retain matched legitimate cases so blanket ambiguity/conflict answers cannot appear successful. A new untouched set, exact repetitions, option-order treatment, and comparison size remain execution-design decisions; do not describe these known cases as fresh evidence. Count every question, complete request, unused branch answer, combination, preparation, grading, review, correction, handback, failure, and any authorized fallback. Unknown cost components remain unknown.

The retained public `choice.md` and `fan-out.md` support batching and categorical options; `jaggedness.md` identifies indirection and option-order risks. These sources motivate a test, not a reliability or cost conclusion. The maintained comparison contract and whole-invocation accounting govern the eventual comparison.

## Decision boundary and closeout

A passing future comparison could support only bounded feasibility of this decomposed judgment on supplied evidence and its observed comparison costs. It would not establish native first-judgment context availability, author correction, removable review work, calibrated probabilities, population reliability, a live assignment, or complete workflow superiority.

The remaining decision-relevant fog is whether these four questions actually simplify Jev's task; whether the materiality wording can generalize without becoming the broad verdict again; how fresh cases cover mixed-scope assertions and harmless ambiguity; and whether supported adapters can preserve this batched treatment and its full accounting. Those are preparation and acceptance questions for the coordinator.

I verified all frozen input digests before analysis and again at closeout. I made no writes, external calls, model experiment, Git mutation, or live change. I used the research and adopting-jev procedures within the supplied packet. This bounded assignment is closed; I launched no descendants, and no operations remain running.
