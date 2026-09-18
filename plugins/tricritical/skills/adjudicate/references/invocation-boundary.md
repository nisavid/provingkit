# Invocation boundary

Treat `topology.json` as the sole graph authority. Invoke or delegate public skills only through the current skill's declared outgoing edges and the frozen contract. Undeclared delegation or invocation is forbidden. Dynamic risk specialists are isolated execution roles routed through `review`'s declared critic edges; they do not add public skills or reverse edges.

## Select assurance before dispatch

Ordinary review is the default. It uses the same leader's live plan, capability
observations, native worker results, and verification. It does not require Task
Witness, a registered issuer, or a retained terminal bundle. Select witnessed
review when the caller or applicable policy explicitly requires authenticated
evidence. Freeze that choice and the consumer assurance minimum before dispatch;
unavailable witnessed evidence blocks rather than falling back to ordinary.

Topology `requires` entries are adapter-supplied capability inputs, not public
skill calls. `conditional_requires.witnessed` adds authenticated inputs only
for that mode. Both modes preserve the same review completeness, original
mutation authority, candidate freshness, and verification requirements.

## Ordinary adapter inputs

`adapter:model-selection-record` binds each execution role to its target
product family, surface, version, and executor; exact supported model and effort
or an appropriate inherited fixed-model binding; fresh live catalog or tool
schema observations; and existing selection authority. It proves available
selection and the requested configuration, not which model actually executed.
The portable skill consumes this record without copying provider-specific policy.
Missing, stale, unsupported, or role-mismatched capability evidence blocks.

The separate Rolecasting-defined `adapter:rolecasting-invocation-plan` binds
candidate, review-input, and requirements identities to a closed-world dispatch
set with exactly one unique dispatch entry per selected critic or specialist.
Each entry records:

- target product family, surface, version, and executor;
- child, peer, or external relationship; leader-owned or user-owned ownership;
  and transport;
- identical immutable inputs, bounded scope, and a separate model-selection record;
- return and verification contract, stop conditions, and distinct isolation;
- authorized read-only authority, default-denied subdelegation and external action,
  and explicit user authority for user-owned work; and
- consumer assurance minimum and observed product-attested, controller-observed,
  or self-reported assurance for each dimension.

The leader observes separate worker contexts, launch, completion, and results
through the native control surface, checks the unchanged inputs, and verifies
report usability. Worker prose cannot supply those observations. Read-only
assignments and model requests remain instructions and selection records;
they do not prove product enforcement or the effective model. Ordinary review
may use this cooperative route when those stronger facts are outside the
consumer's claim and governing policy permits it. Preserve that limit in the
hand-back; do not upgrade self-reported dimensions. A consumer that needs
stronger assurance must receive it or stop before dispatch.

Reject the whole plan for a missing, duplicated, extra, stale, unauthorized,
insufficiently isolated, or cross-bound entry, or assurance below a frozen
minimum. A changed target, relationship, ownership, transport, executor, scope,
authority, isolation, or assurance minimum requires a new valid plan and fresh
capability validation. A selected execution that is missing, failed, timed out,
budget-exhausted, unusable, or unverified keeps the review `incomplete / non-clean`.

## Witnessed adapter inputs

`adapter:model-selection-receipt` and the separate
`adapter:rolecasting-invocation-topology-receipt` require qualified authenticated
issuance for the selected route. They add evidence to the ordinary plan and
selection record; neither can stand in for the other. Validate their binding
and the consumer's minimum before dispatch. Rolecasting's native operational
record is not a portable receipt. Its validator-only registration does not
supply a producer or issuer, and a local controller transcript does not create
one. Keep the retained terminal-evidence validator and its registered producer
chain as the owner of authenticated terminal projections.

## Consume the hand-back

The live caller consumes the actual review or loop result, bound to the final
candidate, review input, requirements, selected scopes and their dependencies,
raw reports, completed dispatch observations, and declared verification.
A bare `clean` loop hand-back proves complete independent review and successful
verification under the selected assurance mode. Absence of portable attestation
alone does not degrade ordinary review. A worker's `DONE`, a copied `clean`
label, or successful verification without complete review is insufficient.
Every other loop terminal remains non-clean for a caller requiring bare `clean`.

Recheck the bindings before a dependent action. Changed candidate bytes,
requirements, scope, or evidence dependencies invalidate the affected review;
rerun those scopes and verification through their owners. If the same leader's
original observations are no longer available, perform fresh ordinary review
or consume separately qualified retained evidence satisfying the caller's
minimum. Saved prose and digest matches alone do not recover live provenance.
A hand-back establishes review status only. Publication, readiness, merge,
deployment, and any other mutation retain their own authority and gates.
