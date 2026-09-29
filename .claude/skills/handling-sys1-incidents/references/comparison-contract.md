# Comparison Contract

Read this when an experiment could change the selected correction. Freeze:

1. **Decision:** the current question, authorized outcome, and distinct plausible
   answers, including no correction.
2. **Hypotheses:** each predicted observation and what would count against it.
3. **Inputs and labels:** fixed incident-derived or synthetic cases, intended
   behavior, label source, missing information, and any intent amendments.
4. **Arms and controls:** current behavior, plausible narrower/replacement
   behavior, and removal or native-only controls where relevant. Specify the
   exact intervention omitted; removing a supervision note differs from
   removing a safety veto.
5. **Identities and execution:** source/build, harness/model, prompt/configuration,
   dependencies, order, repetitions, record preservation, and supported route.
6. **Observations:** emitted output, judgments, delivered context, tool actions,
   effects, actual questions, errors, and skipped paths needed for the claim.
7. **Acceptance and limits:** separate safety and task-alignment criteria,
   comparison fairness, untested boundaries, and the decision after results.

Keep native controls and action permissions under their existing owners.
An arm that needs a changed permission or live configuration waits for that
specific authority. Synthetic fixtures should exercise the relevant path
without executing the real incident's consequential action.

Record both outcome dimensions explicitly:

| Dimension | Examples of observable outcomes |
| --- | --- |
| Safety | An action outside the supplied authorization is withheld; an authorized action is incorrectly stopped; result unmeasured |
| Task alignment | Supplied choices permit progress; a missing choice prompts a question before the dependent result; amended intent is followed; result unmeasured |

Observe task alignment independently of the safety result. Count withheld
output separately from a useful request for missing input. A quiet hook may
have skipped assessment; require the request, recorded verdict, and native
delivery evidence when claiming quiet handling of a judgment.

Preserve failed and skipped attempts. An attempt's failure may require a new
runner or input before retrying, with a distinct record. Changed candidate or
evidence dependencies invalidate the affected review and qualification.
Injected judgments test the integration around those judgments, not model
accuracy. One episode per cell supports a bounded observation, not a rate or
general equivalence claim.

After the run, reconcile observations with the frozen hypotheses and criteria.
Return the best-supported conclusion and limits. If the evidence does not
choose an arm, name the smallest discriminating follow-up or the consequential
decision that remains open.
