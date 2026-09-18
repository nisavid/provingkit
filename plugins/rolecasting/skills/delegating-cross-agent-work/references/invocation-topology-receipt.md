# Invocation plans and witnessed receipts

For ordinary same-leader work, Rolecasting freezes
`adapter:rolecasting-invocation-plan` and separately records
`adapter:model-selection-record`. The plan binds who may be dispatched, through
which topology and transport, under what granted authority, and at what minimum
assurance. The selection record binds the selected request and live capability
observations. Neither requires Task Witness or authenticated receipt issuance.

These operational records do not attest the model that actually executed or
the product's enforcement of requested authority. Preserve the native profile's
assurance limits. A consumer requiring stronger evidence must remain blocked;
do not lower its frozen minimum to make an ordinary route eligible.

## Independent dimensions

Every selected execution freezes these independent dimensions:

- **target:** exact product family, named surface, observed version, and
  concrete executor;
- **relationship:** child, peer, or external;
- **ownership:** leader-owned or user-owned;
- **transport:** native-tool, task-api, cli, app-server, or remote-api;
- **assurance:** the consumer assurance minimum and observed product-attested,
  controller-observed, or self-reported evidence.

An app-server transport does not make an execution external. A leader-owned
peer remains leader-controlled despite its independent session. A user-owned
peer requires explicit user authority to create or steer it. Model choice is a
separate record and does not change any topology dimension.

## Frozen plan

Bind one content-addressed plan identity to the immutable candidate identity,
review-input identity, requirements identity or explicit absence, selected
critic and specialist execution identities, and issue time. Record exactly one unique dispatch entry
for every selected execution. Duplicate, omitted,
unselected, or extra entries invalidate the whole plan; the entries form a
closed-world dispatch set.

Every dispatch entry records:

- selected critic or specialist execution identity;
- the exact product family, named surface, observed version, and concrete
  executor;
- the child, peer, or external relationship;
- leader-owned or user-owned ownership;
- native-tool, task-api, cli, app-server, or remote-api transport;
- product-attested, controller-observed, or self-reported assurance and the
  consumer assurance minimum;
- a separately supplied model-selection record identity, plus its authenticated
  receipt identity when the consumer explicitly requires witnessed evidence;
- the same candidate, review-input, and requirements identities as the plan;
- bounded scope and read-only authority;
- return shape, verification, and stop conditions;
- distinct session and context isolation from every other selected execution;
- default-denied subdelegation and external-action authority; and
- for a user-owned task or thread, the exact explicit user authority to create
  or steer it.

Unstated authority is absent. User-owned ownership without explicit user
authority, any execution without enforceable distinct isolation, an
assurance level below the consumer minimum, or any entry that permits
subdelegation or external action is invalid before dispatch.

Requested restrictions and existing invocation authority remain binding even
when the product does not attest enforcement. A live observation of the
selected request is not evidence of effective model execution or effective
authority. Prompt restrictions and worker claims cannot satisfy a consumer's
requirement for enforced restrictions.

## Explicitly witnessed inputs

An explicitly witnessed consumer additionally requires
`adapter:rolecasting-invocation-topology-receipt`. This receipt is
separate from `adapter:model-selection-receipt`; neither may be embedded in or
substituted for the other. Both bind the same frozen plan and exact dispatch.
An ordinary plan or selection record cannot substitute for either authenticated
receipt or become portable execution evidence.

Portable policy may describe a surface before Rolecasting can issue authentic
evidence for it. Issuance requires a real adapter qualification for the exact
family, surface, version, executor, transport, and assurance source. Current
provider registration is validator-only; it does not qualify or attest any
surface.

## Dispatch and change control

The leader verifies the plan and relevant live executor capabilities before
each dispatch, then records the bound entry and result. Dispatch no identity
outside the closed set and use each entry at most once. A target, relationship,
ownership, transport, scope, isolation, authority, assurance minimum,
or selected-execution change is not a fallback under the existing plan:
freeze a new valid plan and renew any required witnessed receipts. Preserve raw
failure evidence. Any selected execution that is absent, failed, timed out,
unusable, or unverified leaves the requested ensemble incomplete.
