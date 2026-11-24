# Appointment configuration and scoped overrides

Resolve the selection for the actual work from the recipient's applicable
appointment configuration, operator decisions, and any active scoped override.
The appointment configuration is the recipient's persistent selection, resolved
from applicable role and harness defaults and explicitly adopted domain or
appointment exceptions. A scoped override supplies a bounded change for a
particular recipient and task; it does not replace the appointment
configuration. Resolve model, effort, and Ultracode independently. An override
of effort owns neither the model nor the toggle. A field the override omits is
unchanged, not reset.

## Resolve authority and applicability

Honor current explicit operator choices and applicable task requirements before
using defaults or a previously approved selection profile. A selection profile
records a reviewed selection and its conditions; approval does not authorize new
work, data transfer, or a settings operation. Reuse it without a routine approval
question when its recipient, task scope, conditions, authority, and declared end
still match. Use the cheapest reliable match against those recorded facts. When
they do not match, abstain from that selection profile: use an otherwise eligible
authorized default, or return the concrete unresolved requirement through the
existing owner. Do not invent a registry, inference service, or a new review for
every message. Capability, security, effort, and account/resource gates still
apply.

## Retain the override record

Retain the recipient, governing task and selection profile or decision
reference, conditions, changed fields and their prior applicable selection,
application observation, declared end, and application/restoration owner through
existing task, selection, handoff, and verification records. Distinguish a
proposed choice, an issued request, an acknowledged operation, and observed
effective or persistent state. An acknowledgment does not prove the latter
states. Use an existing record's notes or a referenced task artifact; do not add
unrecognized fields to a strict adapter or infer a new schema.

## Apply at the actual task boundary

Prepare a queued task's selection without reconfiguring current work. Apply
only the authorized fields when a supported operation carries the actual task
or its authorized execution continuation. Selection alone grants no actuation
or additional work. Preserve unrelated recipient fields and later operator
choices. An ordinary peer message in an accepted assignment uses the existing
[message boundary](capability-probes-and-fallbacks.md#distinguish-messages-from-execution-assignments).
It does not become a settings operation because a selection profile exists.

Before application, establish the current recipient and applicable appointment
configuration, active task scope, field ownership, authority, supported
controls, and any pending operation. Pass the resolved task selection under the
[field rules](capability-probes-and-fallbacks.md#pass-every-supported-selection-field)
and [Ultracode binding](capability-probes-and-fallbacks.md#bind-claude-ultracode);
never omit a field to simulate preservation or copy a sender or global default
into a missing binding. If a required control or binding is unavailable, retain
the unresolved operation and use the existing capability or authority
disposition. Do not silently change the selection profile or invent success.

## Continue and recover

On continuation or reentry, recover the appointment configuration, active
override, its end condition, pending operations, and accepted owner before
choosing settings. An applicable override continues for its declared scope; a
new message, context compaction, restart, or handover alone neither ends it nor
makes it permanent. Recheck changed applicability, authority, or capability
through the existing continuation gates. Do not replace still-valid task fields
with role defaults merely because the execution is a continuation.

When the task changes, determine whether its override still applies before any
new execution. For overlapping scopes, establish the accepted precedence and
which scope currently owns each field. A newer task label alone does not settle
that question. Reconcile conflicting or unknown ownership, current state, and
uncertain operations before another conflicting write. Keep unrelated eligible
work independent. Do not blindly replay an unobserved application or restoration.

## End and restore owned fields

At the declared end, restore only fields still owned by the ending override,
using the current appointment configuration and operator decisions. A saved
prior selection explains the change; it is not a whole-recipient rollback
snapshot. Preserve later authorized changes, including a later decision that
happens to select the same value. A matching value alone does not prove
continued ownership. Resolve overlapping scopes and pending outcomes before
restoring their fields.

Use a supported, authorized operation and verify the observations required by
the consumer before calling restoration complete. If the operation is unavailable
or its effect is uncertain, retain the pending restoration, its evidence limits,
and accountable owner. Handover transfers this obligation only to an accepting
owner; until then the existing owner retains it. After a restart, recover that
same obligation rather than declaring success or losing it with the old context.
