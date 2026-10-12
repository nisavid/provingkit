---
name: updating-cross-harness-catalog
description: Reconcile a completed cross-harness research, prototype, selection, implementation, qualification, release, or deployment batch with Provingkit's maintained catalog and generated atlas inputs. Use when integrating a producer batch or preparing its closeout, including batches that make no relevant catalog change.
---

# Update the cross-harness catalog

Make a coherent producer result discoverable through the maintained catalog,
with its actual evidence and outstanding gaps. This procedure integrates
records; the owning workflow supplies review, publication, live authority,
and operator decisions.

## Bind the batch

Load `docs/coordination/README.md`, its format reference, the current catalog,
and the applicable operation decision. Record the reviewed procedure revision
and the immutable producer result being consumed. For producer self-use,
record the candidate digest and establish its checks independently.

Identify affected endpoints, directions, fabrics/subroutes, profiles,
operation milestones, and evidence dependencies. Read governing addenda with
the first inventory. Keep independently existing tasks separate from
controller-created lifecycles, and keep host, wrapper, native task, and turn
identities distinct. Use public specimen identities in the catalog.

Finish this step with a bounded change proposal, or a supported explanation
that the batch changes no catalog record. An unaffected batch still checks
its consumers and records that conclusion in its owning closeout.

## Reconcile the evidence

Update only the affected records against the latest repository state.
Preserve unrelated and concurrent edits; reconcile shared changes through
the map driver. Retain distinct candidates, partial mechanisms, unsuccessful
probes, unsuitable reasons, and the source crosswalk. Link immutable evidence
with its acquisition date, source/build/configuration scope, and limits.

Reconcile every affected fabric against the complete finite producer evidence.
Maintain a source-to-component record in
`provenance.component_dependencies.reconciliation`: identify mandatory
components, alternative combinations, grouping-only relations, or a source
that establishes no additional component requirement. Name the evidence and
scope for each conclusion; an empty dependency list is not its own proof.
For a full seed or comparison batch, cover every fabric; later batches
preserve unrelated reconciliation records and reassess affected dependents.

Put every established mandatory component in the fabric's `dependencies`
and its generated card. If the source establishes a required component class
but not its precise backend or deployment, retain an explicit supporting
component record with its source crosswalk and unresolved binding. For
example, a connector's required selected server is distinct from that server's
optional MCP entrance. Group membership and alternatives create no mandatory
edge. Independent review checks this reconciliation against the producer
evidence; metadata validation cannot discover an omitted source requirement.

State the reached milestone and outstanding observations separately. For
example, queue admission supports submission; receiver evidence is needed
for receipt, and returned output needs the caller's checks before fulfillment.
Sharing receiver-side source findings supplies no caller access or reverse
route. Put an outcome on the affected operation claim inside
`profiles[].claims[]`. For uncertain submission, that claim keeps
`coverage: "unknown"`, `outcome: "unknown"`, the actual evidence kind, and
its limits. The containing profile has no outcome field. Leave reconciliation
and any later replay to the owning workflow. Qualified, released, and deployed records bind their own channel and
supporting evidence. Keep unmeasured effort and cost unknown.

Apply graduated compatibility assessment to the affected behavior. Record
why evidence carries forward, what remains unassessed, or what demonstrated
failure makes a function incompatible. A new version alone settles none of
those questions. Refer consequential changes to the owning decision before
publishing them.

Finish with each changed claim supported by its declared evidence kind and
scope, with missing observations still visible. Independent review decides
whether that evidence actually supports the claim; validation checks metadata.

## Regenerate and review

Update the snapshot revision, generation date, and coverage statement for the
batch. Run the README's validation, projection, and command tests. Compare the
generated graph and matrix: both must refer to the same channel records and
preserve mixed progress. Check the diff for lost candidates, unrelated edits,
private identifiers, and inferred qualifications. Regeneration performs no
new harness observation.

Verify that the reconciliation covers the batch's fabrics and that each
mandatory component appears in both the canonical dependencies and generated
cards, with the same scope and unresolved binding. Include that crosswalk in
the completion evidence; preserve alternatives and grouping separately.

Use the owning independent-review workflow on the final candidate, including
the evidence interpretation and procedure changes where applicable. Resolve
valid findings and rerun affected checks after changes. Completion requires
current clean review and the agreed behavior evidence; synthetic success
establishes the tested source behavior only.

## Publish and connect consumers

Use `checkpointing-and-publishing-git-work` for task-owned commits and
authorized publication. Verify the published revision and the actual generated
bytes. Follow the owning tracker contract to record the result and update
authorized consumer pointers. Name this skill, its reviewed source revision,
invocation condition, and required producer result in consumers. Verify
prerequisites remain acyclic. Return useful procedural corrections to the
source owner and the reusable agent-panel workflow catalog.

Close out with the changed records (or no-change reason), evidence limits,
validation and behavior results, final review, publication status, and verified
consumer pointers. Record installation separately when it is part of the
owning task. This catalog update does not install equipment, qualify a live
route, accept a prototype, or authorize a receiver action.
