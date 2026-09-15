# Amberbridge

Amberbridge is Provingkit's release-evidence bridge. It binds one public
candidate to a verified, public-safe summary of private deployment evidence,
then composes that summary with public checks into a candidate-specific
receipt.

The name describes the job: **amber** preserves the evidence, and **bridge**
connects the public Kit to its private deployment context. Amberbridge is a
repository capability, not a plugin, agent, release stage number, or source of
mutation authority.

## Current status

Amberbridge's contracts and deterministic tests are present in the source
stage. Its composed, production-integration, and terminal-proof entry points
remain unavailable. Passing source checks does not qualify a host, authorize a
release, or establish live runtime behavior. The prepared wrapper exposes only
`source-stage` validation; see the [human entrypoint](../README.md#prepared-source-stage-containment).

## What the bridge binds

1. `scripts/amberbridge_compatibility_projection.py` derives the minimal
   authority contract shared by the public candidate and private deployment.
2. `scripts/private_amberbridge_evidence.py` verifies the private registry,
   complete-tree witness, replay summary, isolation evidence, and frozen
   identities.
3. `scripts/run_amberbridge_composed_matrix.py` runs public checks from an
   immutable snapshot and binds their logs to the verified private summary.
4. `scripts/run_amberbridge_production_integration.py` coordinates the later
   release path; the terminal-proof tools bind and combine its terminal results.

A changed candidate, support module, private registry, or evidence artifact
invalidates the corresponding receipt. A passing receipt proves only the
checks and evidence named by its contract.

## Task Witness

Amberbridge does not require Task Witness. Its compatibility document consumes
Rolecasting, Versionkeeping, Tricritical, and Review Atlas authority contracts;
it does not consume Task Witness provider declarations. The public release
validator accepts no Task Witness final-evidence operands.

The private complete-tree witness is an Amberbridge evidence artifact. Its name
does not imply the removed Task Witness implementation or a Task Witness
runtime. Plugin-local provider declarations are retained inert inputs for future
reassessment; they grant no current witnessed-route capability. A future Task
Witness integration must define and qualify a fresh adapter and evidence
contract.

## Maintenance

Edit canonical source first, then verify the affected contract tests and the
public source validator. Rebind normalized source digests when changing a
pinned entry point, and regenerate member locks only through their owning
validator. Preserve historical evidence bytes: renamed active fixtures are
separate from their retained provenance inputs.

The deterministic Mergecraft publication fixture lives in
`scripts/mergecraft_control_plane.py`. It is test equipment for Mergecraft and
is outside Amberbridge's release-support closure.
