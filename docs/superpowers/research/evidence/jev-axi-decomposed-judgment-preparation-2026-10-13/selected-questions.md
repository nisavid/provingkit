# Selected questions and combination

The proposed treatment asks four categorical questions over one frozen evidence packet and combines their answers without another model call. These questions govern the joined proposal. The independently prepared `question-design.md` remains an unchanged design record; its original incompatibility question is superseded here.

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

> After applying explicit qualifications, retractions, and corrections supplied in the evidence, does a source state a fact incompatible with the designated assertion at its stated scope that has not been resolved or withdrawn? Do not count a contrary claim that the supplied context explicitly resolves as erroneous. A later date, greater confidence, or a different assertion alone does not resolve disagreement. If independent accounts remain in unresolved conflict, answer whether one contains an incompatible fact; the relevant-conflict question handles that conflict. A statement that an event is unestablished is not evidence of an incompatible event. Distinguish a claim that an outcome occurred from a claim that its measurement occurred.

- `yes`: At least one supplied source explicitly states an incompatible fact that remains after the supplied qualifications and resolution.
- `no`: No incompatible fact remains after the supplied qualifications and resolution; lack of warrant alone belongs here.
- `unanswerable`: I cannot determine whether an explicitly incompatible fact remains after the supplied qualifications and resolution.

**complete_warrant**

> Do the supplied sources, taken together with their qualifications and evidential dependencies, warrant every part of the designated assertion at its stated scope? Matching words, a derivative repetition, an observed act without its claimed benefit, or a subjective impression without evidence of the claimed objective effect do not by themselves establish complete warrant.

- `yes`: The supplied evidence warrants the complete assertion at its stated scope.
- `no`: The supplied evidence does not warrant at least part of the assertion at its stated scope.
- `unanswerable`: I cannot determine whether complete warrant exists.

These are the selected research prompts for this proposal, not an approved integration contract. The interpretability and relevant-conflict questions deliberately retain the accepted qualifier “prevent assigning another relation.” Replacing it with “any ambiguity” or “any disagreement” would change the semantics.

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

## Source-based development checks

These constructed source packets check the definitions and combination, not model accuracy. They are exposed development examples, excluded from any unseen evaluation claim. Each assertion has no additional draft context. The quoted text is the complete source text for the example; no external facts are needed.

### Explicit correction

Source A:

> Test report R17: Twelve samples were processed. Zero samples passed the acceptance test.

Source B:

> Correction to test report R17: The line “Zero samples passed the acceptance test” is a transcription error. I checked the acceptance records: all twelve samples passed. I retract the zero-pass statement; the corrected result is twelve passes out of twelve.

Assertion: “All twelve samples in test R17 passed the acceptance test.”

The supplied evidence expressly resolves the earlier contrary statement. Its continued presence in Source A does not make it a remaining incompatible fact. The packet supplies complete warrant at the asserted scope.

### Unresolved independent disagreement

Source A:

> Inspector A's independent observation of test R18: All twelve samples passed the acceptance test.

Source B:

> Inspector B's independent observation of test R18: Zero samples passed the acceptance test. Neither account has been retracted or reconciled.

Assertion: “All twelve samples in test R18 passed the acceptance test.”

The disagreement concerns the asserted event and the packet supplies no resolving basis. An incompatible fact exists in the unresolved account, but the relevant-conflict gate determines the relation.

### Uncontested contradiction

Source A:

> Test report R19: Twelve samples were processed. Zero samples passed the acceptance test.

Assertion: “All twelve samples in test R19 passed the acceptance test.”

The only source explicitly states an incompatible result. There is no conflicting account or supplied correction.

### Missing warrant

Source A:

> Test report R20: Twelve samples were processed. Whether any sample passed the acceptance test has not been established.

Assertion: “All twelve samples in test R20 passed the acceptance test.”

An unestablished result neither warrants the assertion nor states an incompatible result.

### Expected source-based answers

| Development example | Interpretability | Relevant conflict | Incompatible fact | Complete warrant | Combined relation |
| --- | --- | --- | --- | --- | --- |
| Explicit correction | clear | no | no | yes | supported |
| Unresolved independent disagreement | clear | yes | yes | no | unresolved |
| Uncontested contradiction | clear | no | yes | no | contradicted |
| Missing warrant | clear | no | no | no | unsupported_extension |

The independent review must assess these relations from the sources, not assume this table is a gold label. A mere later contrary report without an explicit resolving basis belongs with unresolved disagreement, not the correction example. The rule does not infer source authority from recency or confidence.

Source resolution adds interpretation to the incompatible-fact question. It preserves the accepted meanings but does not prove that this question is simpler for Jev. That complexity and all four questions remain part of the proposed feasibility and cost comparison.
