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
`source-stage` validation; see the [contributor guide](../CONTRIBUTING.md#prepared-source-stage-containment).
The [release boundary](release-boundary.md#source-checks-and-release-evidence)
explains the additional controls required for release and live qualification.

## What the bridge binds

1. `scripts/amberbridge_compatibility_projection.py` derives the compatibility
   document: the minimal authority contract shared by the public candidate and
   private deployment.
2. `scripts/private_amberbridge_evidence.py` verifies the private registry,
   complete-tree witness, replay summary, isolation evidence, and frozen
   identities.
3. `scripts/run_amberbridge_composed_matrix.py` runs public checks from an
   immutable snapshot and binds their logs to the verified private summary.
4. `scripts/run_amberbridge_production_integration.py` coordinates the later
   release path; the terminal-proof tools,
   `scripts/run_amberbridge_terminal_proof.py` and
   `scripts/combine_amberbridge_terminal_proofs.py`, bind and combine its
   terminal results.

The compatibility document is version 2
(`amberbridge-public-private-compatibility-v2`); its frozen bytes are
`tests/fixtures/amberbridge-v2-compatibility.json`. It binds ordinary
Rolecasting plan and selection ownership, Tricritical's ordinary inputs, and
its conditional witnessed inputs. Evidence for the v1 or v4 compatibility
bytes retained beside that fixture cannot qualify this contract; private and
public projections must match exactly. The private verifier currently pins the
retained v1 document, not the v2 projection. Reconciling that pin with the v2
contract remains outstanding.

A changed candidate, support module, private registry, or evidence artifact
invalidates the corresponding receipt. A passing receipt proves only the
checks and evidence named by its contract.

## Task Witness

Amberbridge does not require Task Witness. Its compatibility document consumes
Rolecasting, Versionkeeping, Tricritical, and Mergecraft's Review Atlas
authority contracts; it does not consume Task Witness provider declarations.
The public release validator, `scripts/validate_public_release.py`, accepts no
Task Witness final-evidence operands.

The private complete-tree witness is an Amberbridge evidence artifact. Its name
does not imply the removed Task Witness implementation or a Task Witness
runtime. Plugin-local provider declarations are retained inert inputs for future
reassessment; they grant no current witnessed-route capability. A future Task
Witness integration must define and qualify a fresh adapter and evidence
contract.

## Maintenance

Edit canonical source first, then verify the affected contract tests and the
public source validator, whose commands are under
[Validate a source checkout](../CONTRIBUTING.md#validate-a-source-checkout).
A pinned entry point carries its normalized source digest in a `SOURCE_SHA256`
constant: the SHA-256 of the script's source with that constant's value
replaced by 64 zeros. Rebind it when you change the script, and regenerate
member content locks only through their owning validator, as
[Generated artifacts](../CONTRIBUTING.md#generated-artifacts) describes. The
private verifier, `scripts/private_amberbridge_evidence.py`, currently pins
the retained v1 compatibility document, including its final newline. Its digest
is distinct from a Python source digest and from the v2 projection digest.

Preserve historical evidence bytes and their original Git identities. The active
Amberbridge private registry, witness, and binding fixtures contain a separate
synthetic Git commit with one inert producer file. Their check names and runtime
fields are test inputs, not observations from a private checkout or host. The
verifier tests accept this internally consistent sample and then reject altered
compatibility bytes and package paths after the outer digests are recomputed.

The deterministic Mergecraft publication fixture lives in
`scripts/mergecraft_control_plane.py`. It is test equipment for Mergecraft and
is outside Amberbridge's release-support closure.
