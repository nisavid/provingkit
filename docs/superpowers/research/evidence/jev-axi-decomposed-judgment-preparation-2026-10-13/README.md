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

The [execution proposal](contract.md) compares the unchanged direct question with the four selected questions on every condition: Jev 1.13, Decisions with Luna 6, Responses with Luna 6 Low/Medium/High, and Responses with Sol 6.1 Low. Each decomposed treatment uses one request containing four questions; the four categorical answers are combined locally. API output formats and the distinction between independent Jev questions and joint Responses output remain explicit.

The [fresh corpus](corpus/README.md) has 24 assertions across six source families, with complete draft context and two sources each. Two isolated labelers agreed on all final relations and components; a separate adjudicator checked the evidence and accepted all cases without correction. The final key has six cases per relation. Those labels prepare grading; they are not candidate-model results. All cases remain critical, including the six accurate assertions. Exposed development examples and previous experiment packets are excluded.

The claim producer now emits a clean inference object separately from provenance. Every condition and treatment receives the same assertion, context, and complete source text. Evaluator labels, rationale, Git identities, paths, and other answers stay outside inference. A controlled-unavailable case remains local and receives no semantic request.

## Equipment and full work

Version 3 of the [comparison runner](../jev-axi-comparison-runners-2026-10-07/README.md) supports the paired schedule, grouped questions, strict answer-set validation, deterministic combination, and separate semantic abstention and operational failure. Local CLI and fake-service checks exercise these behaviors and the full invocation/accounting path. They do not establish provider access or judgment performance.

The proposed matrix has 288 request groups, 720 question instances, and at most 144 combinations. The direct treatment contains 144 questions; decomposition contains 576. Usage and API-rate equivalent are counted once per submitted request, including all questions and source state. No request retry, four-call fallback, or additional development call is proposed.

Count source preparation, transmission, interpretation, combination, grading, review, correction, operator effort, and failed work. Keep research/equipment costs separate from recurring work without assuming amortization. API-rate equivalent, actual charges, subscription usage, active effort, and latency are different quantities. The public [provider facts](provider-facts.json) retain the selected model and current documentary rates; no Pro billing route is assumed for Decisions.

The maintained [comparison procedure](../../../../../.agents/skills/handling-sys1-incidents/references/comparison-contract.md), producer, runner README, and [invocation accounting](../jev-axi-comparison-runners-2026-10-07/invocation-accounting.md) provide the consumer path. This increment changes that local equipment; it does not install a generalized agent procedure or change a live hook.

## Parallel preparation and join

The initial question/evidence and interface/accounting proposals used the same frozen published evidence in separate contexts. Their original reports remain design records; `selected-questions.md` controls the adopted semantics. Fresh evidence construction and independent labeling joined the adapter and accounting work at the execution proposal. `corpus/label-provenance.json` preserves the labeling inputs and original reports.

The final preparation joins the frozen source commit, exact inference packets, evaluator key, questions, schedule, limits, rate evidence, and verification into private execution bindings. Independent review must cover both protocol fidelity and implementation behavior before those bindings are offered for acceptance. A source or evidence change invalidates the affected review. Publication of the preparation is not experiment acceptance.

## What this could establish

A future pass could establish bounded judgment feasibility on the selected supplied evidence and its measured comparison costs. It would not establish calibrated confidence, population reliability, early availability of adequate working-draft evidence, useful author corrections, removed review work, or complete workflow savings. A later workflow test must establish an actual opportunity and compare ordinary work and omission before this becomes a System One assignment.

Current preparation used native assistant analysis and public documentation. No new provider experiment ran. Preparation model tokens, attributable bills, complete active effort, and the initial preparation interval were not fully captured; those costs remain unknown. The full investigation must carry them as setup uncertainty rather than assign them zero cost.
