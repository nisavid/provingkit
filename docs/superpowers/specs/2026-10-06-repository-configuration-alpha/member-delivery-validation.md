# Proposed Mergecraft member-delivery validation

This proposal gives the repository-configuration alpha a source-validation path that checks the changed Mergecraft member and preserves the other five members. It supplies the remaining validation and CI caller decision for [Bind the alpha to maintained source and an installation contract](https://github.com/nisavid/provingkit/issues/375). The source/release owner must accept this context before implementation or member-version reservation.

The [development increment](https://github.com/nisavid/provingkit/commit/e50777edc12c17f5c5f1c4ede245c2a45064476a) is reviewed and published. It passes ordinary source checks with all six development versions at `1.0.0`. The selected delivery route instead changes Mergecraft while preserving five installed versions. The ordinary `validate_provingkit` entrypoint rejects differing versions; its behavior and owning rejection test remain unchanged.

## Validation interface and claim

Maintain the proposed entrypoint in `scripts/validate_member_delivery.py`, with owning tests in `tests/test_validate_member_delivery.py`. It returns a source-and-preservation result for one changed Mergecraft member and a complete six-member catalog. It does not return a whole-Kit Release qualification, installed-state acceptance, or a settings-enforcement result.

The caller supplies three immutable subjects:

| Subject | Required binding |
| --- | --- |
| Development source | Published Git commit containing the reviewed Mergecraft source and its current review/evaluation inputs. |
| Preservation baseline | Installation-owner-accepted record identifying baseline source, all three targets' retained artifacts, complete inventories with file modes, member versions and catalog identities, and the observations establishing acceptance. A source commit alone is insufficient. |
| Delivery source | Clean Git commit containing that Mergecraft amendment and the retained members' governed source, with the proposed member-version binding. |

Supporting inputs identify the reviewed validator revision, maintained projector and projection policy, complete delivery artifacts and raw receipts, and qualification evidence for the imported interfaces actually used. Bind each result to those inputs and their digests. Missing acceptance, identities, artifacts, or required interface evidence produces an incomplete or rejected result and a failing invocation, rather than a passing preservation claim. The installer rechecks baseline freshness before its later write window.

The validator establishes these obligations:

- The delivery has exactly the six declared members, supported member versions, matching canonical and Claude manifests, correct definition-to-content-lock identities, and complete catalogs for Agent Plugins, Claude Code, and Cursor.
- Mergecraft passes its maintained structural and content-lock validation. `--source-stage` alone is insufficient because it skips the lock check. Its source matches the reviewed development amendment apart from explicitly enumerated version-binding changes; any other change requires fresh affected review and evaluation.
- Each retained member matches the accepted baseline by path, bytes, mode, version, and target catalog entry. Comparison covers the complete projected member trees, not only six inspected Skill bodies or a subset of files.
- Every target artifact and raw receipt matches the delivery source, projector, policy, target, and complete inventory. Retain an explicit mode inventory: the current projector's tree digest binds paths and bytes, not modes.
- The required imported interfaces are identified by their actual source/resource closure and current qualification evidence. A file-presence check or matching Skill body does not establish runtime compatibility. The entrypoint verifies the supplied evidence bindings; the source/qualification owner performs the behavior qualification.

Registration, scope, enablement, provider precedence, and recovery preservation remain installer observations. Successful projection does not imply source validation or any of those host results. The validator reports only the checks it actually performed and the external evidence it consumed; ordinary digests are not authenticated attestations.

## Preparation and Actions caller

Prepare the delivery in an isolated checkout after baseline acceptance. Use the maintained projector over that one committed source for all three complete target catalogs. Keep the reviewed development commit, delivery commit, and validator revision distinct. Do not splice independently projected member trees into a marketplace.

Add a proposed manually dispatched Actions workflow at `.github/workflows/mergecraft-member-delivery.yml`, through the normal source review and publication route. Its caller accepts immutable subject and evidence references, invokes the maintained validator revision, and records the resulting bindings and individual check outcomes. Its tests must verify both a passing constructed delivery and failing preservation cases. The CI implementation must settle how the evidence and artifacts are fetched and retained before the workflow is considered runnable; this document does not invent a storage route or receipt producer.

Publish a final delivery commit to a task-owned non-default branch. Do not open it as a pull request into ordinary coordinated Kit source. The current source workflow runs on pull requests and pushes to `main`; publishing a non-default branch does not invoke it. The proposed member workflow supplies the separately named validation result. Ordinary development pull requests and `main` continue running the existing Kit checks without branch exceptions or a mixed-version waiver.

[GitHub requires the manual-dispatch workflow on the default branch](https://github.com/github/docs/blob/main/data/reusables/actions/workflow-dispatch.md). Pin the workflow, validator, and dependency revisions for a candidate run and record what actually ran. Adding the workflow and dispatching it remain later operations. Use GitHub Actions under the applicable cost policy, with no recurring schedule. This workflow is delivery-source validation, distinct from the separately bounded public and private qualification fixtures.

## Owning tests and completion

Construct one valid changed-Mergecraft/five-preserved example and reject each material deviation independently: a retained path, byte, mode, version, or catalog change; missing or extra members; wrong subject identity; absent baseline acceptance; mismatched manifests or locks; missing, incomplete, or stale target receipts; and missing or incompatible imported-interface evidence. Cover version-only binding changes and invalidate review when other Mergecraft bytes change. Keep the ordinary Kit mixed-version rejection test.

Caller tests verify immutable input propagation, the validator actually invoked, result binding, and failure propagation. A member-delivery success must not be reported as an ordinary Kit check or whole-Kit compatibility result. Final source and caller changes receive their owning validation and independent review before publication; constructed tests do not qualify a real baseline or client.

Acceptance of this proposal selects the validation context and caller placement. It reserves no version. The version owner still selects an unused identity and upgrade ordering: the current grammar admits a flat positive alpha ordinal and rejects dotted `alpha.4.1`. The installer still supplies a freshly accepted preservation baseline and Cursor control readiness. The qualification owner still proves actual imports, both live GitHub contexts, and fresh useful invocation in all three clients. Ivan retains the separately required candidate-bound installation approval.

## Evidence and decision

The constraints above are grounded in the reviewed development source's `scripts/validate_provingkit.py`, `tests/test_validate_provingkit.py`, `scripts/member_versions.py`, `scripts/build_release_artifacts.py`, and `.github/workflows/provingkit-source.yml`, together with the [member-validation proposal](https://github.com/nisavid/provingkit/issues/375#issuecomment-6056053768) and the deployment owner's source/installation handoff. The retained alpha.3 identity is historical baseline evidence, not current host acceptance.

The decision is whether the source/release owner accepts this separate maintained member-delivery validation and Actions context while preserving ordinary Kit validation. Artifact/evidence transport and the precise input schema are implementation decisions to settle before a runnable caller exists. No validator, workflow, version assignment, delivery commit, projection, or installation is implemented by this proposal.
