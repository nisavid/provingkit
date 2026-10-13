# Testing narrower Jev evidence judgments

This proposal tests whether four narrower Jev judgments, combined by code, can distinguish a statement that lacks support from one the evidence contradicts. It also separates consequential ambiguity from disagreement that does not affect the statement. The next integration decision is whether this design deserves a workflow trial; no new Jev behavior is assigned by this preparation.

The [accepted preparation](https://github.com/nisavid/provingkit/issues/590#issuecomment-6156301327) is tracked in [#599](https://github.com/nisavid/provingkit/issues/599), under [catalog map #331](https://github.com/nisavid/provingkit/issues/331). It calls for a reviewed proposal. A runnable experiment needs a further frozen contract and separate execution acceptance. Live changes and submissions to the upstream `jev-axi` repository retain their existing approval boundaries.

## Proposed judgment

The [previous comparison](../jev-axi-fresh-judgment-comparison-2026-10-12/results.md) found that neither four-way Jev question passed the selected cases. Both confused missing support with contradiction and treated irrelevant disagreement as unresolved; the revised question additionally missed an ambiguous reference. The retained cases can guide design, but cannot become an unseen evaluation set again.

I propose the four categorical questions and complete combination rule in [selected-questions.md](selected-questions.md):

| Question | What it separates | Example of the distinction |
| --- | --- | --- |
| Interpretability | A reference that prevents judgment from ambiguity that leaves the answer unchanged | Two possible replacements have different operating states; “the replacement worked” does not identify which one. |
| Relevant conflict | Unresolved independent disagreement about the assertion from disagreement about something else | Two accounts disagree about operation, but both support “there are two accounts.” |
| Incompatible fact | Contrary evidence that remains after explicit corrections from missing warrant | “Time savings were not measured” contradicts a claim of measurement, but does not establish that no time was saved. |
| Complete warrant | Evidence for the entire assertion from an extension beyond its scope | A successful trial with staff does not establish success for customers. |

All four receive the same assertion, draft context, and complete selected sources. No evaluator-written interpretation is added to the inference packet. Their categorical answers feed code; probabilities are retained when available but do not determine a threshold or get multiplied together.

The combination distinguishes operational failure, model abstention, and a substantive `unresolved` verdict. It rejects malformed answer sets. Material ambiguity and relevant conflict take precedence; otherwise explicit incompatible evidence yields `contradicted`, complete warrant yields `supported`, and neither yields `unsupported_extension`. Simultaneous affirmative incompatibility and complete warrant, after those earlier gates have cleared, produces `inconsistent_answers` with no relation. The detailed table specifies the unanswerable branches. A missing correct judgment on a ready critical case fails the bar. Explicit corrections and retractions are applied before judging incompatibility; a superseded contrary statement cannot by itself reject a supported assertion. The selected design includes four source-based development checks for this distinction and the other verdicts.

This is a hypothesis about a more useful division of work between Jev and code. It does not establish that the questions are easy. In particular, the first two still ask whether ambiguity or disagreement prevents another classification. Complete warrant also remains a semantic judgment. If these questions merely relocate the original difficulty, decomposition has failed its purpose even if its outputs are easier to inspect.

## Matched comparison and fresh evidence

The [workload proposal](workload-design.md) recommends six fresh source families, with four assertions per family: supported, unsupported extension, contradicted, and unresolved. The six contrasts cover participant/setting scope, observed versus operational events, activity versus benefit, accounts versus their reported facts, referential completeness, and independent versus derivative evidence. That gives 24 proposed primary cases, not 24 independent samples. Case construction and independent label adjudication have not occurred.

Retain the same six conditions: Jev, Decisions with Luna, Responses Luna 6 Low/Medium/High, and Responses Sol 6.1 Low. Each gets a concurrent direct four-way question and the same proposed decomposition over equivalent substantive evidence. Use the previous current four-way wording as the proposed direct control; it is a historical baseline, not a selected best prompt. Freeze the exact text and transport encoding before construction and evaluation.

Jev can receive these same-state questions together. An ordinary model returning a vector may reason jointly, whereas the documented Jev interface evaluates questions independently. Decisions support for the proposed multi-answer encoding remains to be verified. If it needs separate calls, preserve them and count the repeated state. No endpoint is silently removed, and differences in grouping cannot be attributed solely to better question design. A grouping control is needed if that causal claim matters.

Omission remains an eligible integration choice. It has no classification accuracy here; ordinary authoring and review would need a later workflow comparison. Deterministic preparation checks source identities and packet validity. It does not decide semantic support from matching words.

Freeze the questions and combination before authoring the fresh families. Independent evaluators label complete candidate-visible packets before model outputs are available, rejecting cases without a defensible label. Keep construction directions, family identities, labels, and rationales out of model inputs. Include paraphrases, harmless ambiguity, and lexical overlap that does not establish support. Repetitions, dependent wording/source-order variants, option order, and the final critical-case schedule remain decisions for contract preparation; they are not hidden in the proposed 24-case count. Unblinded cases become development evidence for any later revision.

Every selected critical case and matched supported assertion must pass. An improved average cannot compensate for a new false downgrade, abstention, invalid response, or missed ambiguity. Report paired outcomes and family-level patterns before aggregate counts. A direct and decomposed pass shows no quality advantage from decomposition on those cases. A Jev failure with an ordinary-model pass rejects this Jev design at that boundary, while leaving other designs and omission available.

## Full work and supported equipment

With 24 primary cases, six conditions, two treatments, and one repetition, the proposal has 288 treatment cells. That would be 288 requests only if every endpoint used one request per treatment. Four separate decomposition requests for Decisions would increase the total to 360 requests. These figures exclude any additional scheduled development cases, variants, repetitions, or controls; they are planning examples, not an accepted run size or spending estimate.

Count all questions, including branch answers not used by the combiner, and retain every actual submission or uncertain submission. Include source preparation, repeated transmitted state, parsing, combination, grading, independent review, corrections, operator effort, and failed work. Separate setup/on-change work from recurring work without assuming free amortization. Report tokens, API-rate equivalent value, attributable bills, provider-defined subscription usage, active effort, and latency separately. Missing counters and unobserved work stay unknown.

The existing [claim producer](../jev-axi-comparison-producers-2026-10-07/README.md) supports an assertion in draft context with one or two ordered complete UTF-8 sources bound to immutable Git identities. That is the proposed input boundary. Expanding it or substituting a summary requires a separate change to the preparation contract. The maintained [comparison procedure](../../../../../.agents/skills/handling-sys1-incidents/references/comparison-contract.md) and [invocation accounting](../jev-axi-comparison-runners-2026-10-07/invocation-accounting.md) remain the consumer path.

No generalized runner or combiner implementation is supplied here. Existing fixed-formulation equipment cannot be assumed to support four answers, treatment-aware joins, or these request counts. Supported endpoint encodings, response validity, failure handling, current routes and rates, and final accounting bindings must be verified before an execution proposal is ready.

## Parallel preparation and join

The two independent proposals were prepared from the same frozen published evidence without seeing one another's handbacks. Their original Markdown bytes are preserved here as design records, not controlling protocol text. The selected questions and combination are in `selected-questions.md`; [independent-inputs.json](independent-inputs.json) records their lengths and hashes. The coordinator verified the originals and their input pins. Requested model selections and cooperative read-only instructions do not attest which effective models executed or prove enforced permissions.

The next preparation can split along these dependencies:

1. **Question and evidence lane:** resolve any semantic review findings, freeze the question set and combination, then construct fresh families and obtain independent labels. Preserve rejected construction and its cost. No model evaluation begins during this lane.
2. **Interface and accounting lane:** inspect supported encodings for all six conditions and the existing runner, propose the smallest adapter/combiner changes, and identify the necessary local test interfaces. This can proceed independently of the fresh case contents, using synthetic placeholders.
3. **Coordinator join:** bind the final questions, labels, encodings, schedule, quality bar, local verification, price records, limits, and complete accounting into one reviewed execution contract. Changes that affect semantics or evidence invalidate the corresponding review; changed transport must be checked against the intended treatment.

This checkpoint selects a concrete design proposal while leaving experiment-size and interface facts explicit. Local implementation and any new test interface follow their normal requirements. No experimental request, native workload trial, credential repair, or live hook change is part of this checkpoint.

## What this could establish

A future pass could establish bounded judgment feasibility on the selected supplied evidence and its measured comparison costs. It would not establish calibrated confidence, population reliability, early availability of adequate working-draft evidence, useful author corrections, removed review work, or complete workflow savings. A later workflow test must establish an actual opportunity and compare ordinary work and omission before this becomes a System One assignment.

Current preparation used native assistant analysis and public documentation. No new provider experiment ran. Preparation model tokens, attributable bills, complete active effort, and the initial preparation interval were not fully captured; those costs remain unknown. The full investigation must carry them as setup uncertainty rather than assign them zero cost.
