---
name: handling-sys1-incidents
description: Use when diagnosing an observed Sys1 safety denial, supervision misdirection, repeated intervention after approval, or unexpected service-failure behavior, including comparison design and correction handoff.
---

# Handle Sys1 Incidents

Turn an observed Sys1 intervention into a bounded finding and, when supported,
a correction proposal. Sys1 here means the probabilistic judgment used by an
agent's safety or supervision integration.

Use this procedure for an observed incident. Ordinary tool failures, pending
permission requests, and general Jev adoption use their existing workflows.
Use `adopting-jev` when the work reaches Jev integration design.

## 1. Bound the incident

State the witnessed effect, the intended action or task outcome, and the
question this investigation can answer. Preserve the current authorization and
permission boundaries. Intake does not require retrying a denied action.

Read the owning repository's tracker instructions before finding or changing
tracked work. Locate the existing case, if any, and identify its accountable owner
separately. A case identifier alone leaves ownership unknown. Attach distinct
occurrences to the matching case only within the active task's authority.
Match action identity, intended outcome, and intervention layer, rather than
a similar probability alone. Keep each occurrence's evidence and order.

Finish with a named owner or an explicit ownership gap, a bounded investigation
question, and the work that can continue independently.

## 2. Preserve the available evidence

Use [the evidence record](references/evidence-record.md) for the witness,
retained action, authorization, intent amendments, emitted output, selected
logs, source/runtime identities, effects, and access limits. Record missing
fields as unknown. Request only missing evidence that can change the current
decision; a full transcript is not a default prerequisite.

Keep witness reports, source facts, authored fixtures, model responses, native
observations, and inferences distinguishable. Preserve original evidence; make
any authorized public projection separately and identify its omissions.
Record the procedure revision used by this investigation.

Finish when every claim has an evidence pointer or an explicit uncertainty,
and the proposed evidence use fits its access and publication limits.

## 3. Locate the discrepancy

Compare what was authorized with the exact proposed action. Assess path
location and authorization separately: a target outside the project may be
within the operator's approved scope. Establish that scope before calling a
denial correct or requiring new permission. Then trace the smallest relevant
path: input construction, judgment, policy decision, harness adapter, delivery,
or failure handling. A high score identifies a judgment,
not its cause. Approval for one action may not cover another.

Use `diagnosing-bugs` for the implicated behavior.
State competing explanations and the smallest observation that distinguishes
them. A replay or source reading can explain a path without proving that the
native incident took that path. An attributed recovery claim needs observed
recovery evidence before it can support resolution.

Follow the current action boundary when a tool refuses an operation. Preserve
the exact action and stated reason, reconcile existing authority, and use the
owning escalation route if execution remains unavailable. Do not move the
denied effect to another tool, account, or harness.

Finish with a supported explanation, a testable uncertainty, or a no-change
conclusion whose scope is explicit.

## 4. Compare only what the decision needs

When a comparison can change the correction choice, use
[the comparison contract](references/comparison-contract.md). Freeze the
question, hypotheses, inputs, labels, arms, controls, identities, observations,
and limits before execution. Keep removal and native-only alternatives
eligible; name exactly which intervention each arm retains or omits.

Use `grilling` for consequential unresolved intent or authority choices and
`wayfinder` when the investigation needs a revisable work map. Preserve
settled choices while evidence tests the remaining ones. Use `research` and
independent harnesses where they can distinguish competing explanations.
Select workers and model routes through their owning workflows.

Finish with separate safety and task-alignment results, including unmeasured
outcomes, failures, and evidence limits. No-correction is a valid result.

## 5. Hand off the supported result

Return the conclusion, evidence, uncertainty, and smallest supported
correction to the owning implementation workflow. State its affected behavior,
retained behavior, supported inputs, acceptance checks, and unresolved
decisions. Source changes, replay results, built output, native qualification,
publication, and live adoption each need their own evidence.

Use the existing implementation, review, Git, and publication procedures.
Maintain any reusable procedural correction through
`capturing-agent-procedures`. Connect dependent work to this skill's reviewed
revision and required handback; independent work may continue.

Complete this investigation when its bounded question is answered or its
remaining evidence/decision owner is named, the handback distinguishes observed
results from proposals, and authorized tracking reflects that result. Closing
an intake investigation does not complete an unqualified runtime correction.
