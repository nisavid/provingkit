# Mergecraft member-delivery validation design

This design gives the repository-configuration alpha a source-validation path that checks the changed Mergecraft member and preserves the other five members. The source/release owner accepts the separate validation context and manual Actions caller for implementation design in [Bind the alpha to maintained source and an installation contract](https://github.com/nisavid/provingkit/issues/375). Evidence admission and transport, member-version selection, and the installation baseline remain to be settled before the caller is runnable.

The [development increment](https://github.com/nisavid/provingkit/commit/e50777edc12c17f5c5f1c4ede245c2a45064476a) is reviewed and published. It passes ordinary source checks with all six development versions at `1.0.0`. The selected delivery route instead changes Mergecraft while preserving five installed versions. The ordinary `validate_provingkit` entrypoint rejects differing versions; its behavior and owning rejection test remain unchanged.

## Validation interface and claim

Maintain the proposed entrypoint in `scripts/validate_member_delivery.py`, with owning tests in `tests/test_validate_member_delivery.py`. It returns a source-and-preservation result for one changed Mergecraft member and a complete six-member catalog. It does not return a whole-Kit Release qualification, installed-state acceptance, or a settings-enforcement result.

The caller supplies three immutable subjects:

| Subject | Required binding |
| --- | --- |
| Development source | Published Git commit containing the reviewed Mergecraft source and its current review/evaluation inputs. |
| Preservation baseline | Installation-owner-accepted record identifying baseline source, all three targets' retained artifacts, complete inventories with file and directory modes and allowed links, member versions and catalog identities, and the observations establishing acceptance. A source commit alone is insufficient. |
| Delivery source | Clean Git commit containing that Mergecraft amendment and the retained members' governed source, with the proposed member-version binding. |

Supporting inputs identify the reviewed validator revision, maintained projector and projection policy, Codex local-view producer revision, complete canonical and consumed delivery artifacts and raw receipts, and qualification evidence for the imported interfaces actually used. Bind each result to those inputs and their digests. Missing acceptance, identities, artifacts, or required interface evidence produces an incomplete or rejected result and a failing invocation, rather than a passing preservation claim. The installer rechecks baseline freshness before its later write window.

The evidence schema must identify the accepting observation and decision, its admission and freshness rules, and its transport and retention. A caller-supplied `accepted: true` does not establish installer acceptance. Keep private host observations outside public Actions payloads. Bind the validator and projector code and dependency closure actually executed separately from the delivery subject; a receipt's source or builder field alone does not establish which code ran.

The validator establishes these obligations:

- The delivery has exactly the six declared members, supported member versions, matching canonical and Claude manifests, correct definition-to-content-lock identities, and complete catalogs for the actual Codex, Claude Code, and Cursor variants consumed by the installation route.
- Mergecraft passes its maintained structural and content-lock validation. `--source-stage` alone is insufficient because it skips the lock check. Its source matches the reviewed development amendment apart from explicitly enumerated version-binding changes, including the definition-to-release-schema member projection; any other change requires fresh affected review and evaluation.
- Each retained member matches the accepted baseline by path, bytes, mode, version, and target catalog entry. Comparison covers the complete projected member trees and shared catalog fields, not only six inspected Skill bodies or a subset of files.
- Every target artifact and raw receipt matches the delivery source, projector, policy, client, installable variant, and complete inventory. Codex's `provingkit-local` route binds `agent-plugins-local` and its raw receipt explicitly; canonical `agent-plugins` has a separate catalog identity and cannot substitute for it. Retain complete file and directory modes and allowed links: the current projector's tree digest binds paths and bytes, not modes.
- The required imported interfaces are identified by their actual source/resource closure and current qualification evidence. A file-presence check or matching Skill body does not establish runtime compatibility. The entrypoint verifies the supplied evidence bindings; the source/qualification owner performs the behavior qualification.

Artifact link handling follows the maintained producer and consumer policies. The canonical projector rejects symbolic links; the [root-receipt contract](../../../release-artifact-projection.md#receipt-and-mode-preservation) requires a regular root receipt and permits hard links. Recording native host links does not broaden the shipped artifact format.

Registration, scope, enablement, provider precedence, and recovery preservation remain installer observations. Retain complete native logical records, including duplicate, disabled, shadowed, unresolved, and pathless rows, unknown fields, and missing/null/false distinctions. Keep client-managed cache extras and volatile bookkeeping separate from shipped artifacts. Successful projection does not imply source validation or any of those host results. The validator reports only the checks it actually performed and the external evidence it consumed; ordinary digests are not authenticated attestations.

## Preparation and Actions caller

Prepare the delivery in an isolated checkout after baseline acceptance. Use the maintained Provingkit projector over that one committed source for the canonical `agent-plugins`, `claude`, and `cursor` catalogs. Keep the reviewed development commit, delivery commit, and validator revision distinct. Do not splice independently projected member trees into a marketplace.

Codex's local variant comes from the [maintained installer procedure](https://github.com/nisavid/dotfiles/blob/3feb1c44317338dcc8b63fce38d6db58f592abba/docs/agent-equipment/provingkit-installations.md), after verification of the canonical Agent Plugins artifact. Its fixed view changes the catalog name to `provingkit-local`, preserves member payloads and modes, and produces a `provingkit-local-marketplace-projection-v1` root receipt bound to the exact canonical parent receipt. That derived receipt is distinct from the ordinary artifact receipt. Bind the local producer's revision and resulting view/receipt alongside the parent artifact; `build_release_artifacts.py` does not emit an `agent-plugins-local` target. The later caller must settle retrieval and use of this maintained producer's evidence with its owner; this design declares no new public installer interface.

Add a proposed manually dispatched Actions workflow at `.github/workflows/mergecraft-member-delivery.yml`, through the normal source review and publication route. Its caller accepts immutable subject and evidence references, invokes the maintained validator revision, and records the resulting bindings and individual check outcomes. Its tests must verify both a passing constructed delivery and failing preservation cases. The CI implementation must settle how the evidence and artifacts are fetched and retained before the workflow is considered runnable; this document does not invent a storage route or receipt producer.

Publish a final delivery commit to a task-owned non-default branch. Do not open it as a pull request into ordinary coordinated Kit source. The current source workflow runs on pull requests and pushes to `main`; publishing a non-default branch does not invoke it. The proposed member workflow supplies the separately named validation result. Ordinary development pull requests and `main` continue running the existing Kit checks without branch exceptions or a mixed-version waiver.

[GitHub requires the manual-dispatch workflow on the default branch](https://github.com/github/docs/blob/main/data/reusables/actions/workflow-dispatch.md). Pin the workflow, validator, and dependency revisions for a candidate run and record what actually ran. Adding the workflow and dispatching it remain later operations. Use GitHub Actions under the applicable cost policy, with no recurring schedule. This workflow is delivery-source validation, distinct from the separately bounded public and private qualification fixtures.

## Owning tests and completion

Construct one valid changed-Mergecraft/five-preserved example and reject each material deviation independently: a change to a retained path, bytes, file or directory mode, permitted link, version, or catalog entry; missing or extra members; wrong subject identity; absent baseline acceptance; mismatched manifests or locks; missing, incomplete, or stale target receipts; a receipt for the wrong target variant; and missing or incompatible imported-interface evidence. Cover version-only binding changes and invalidate review when other Mergecraft bytes change. Keep the ordinary Kit mixed-version rejection test.

Caller tests verify immutable input propagation, the validator actually invoked, result binding, and failure propagation. A member-delivery success must not be reported as an ordinary Kit check or whole-Kit compatibility result. Final source and caller changes receive their owning validation and independent review before publication; constructed tests do not qualify a real baseline or client.

The accepted context and caller placement reserve no version. The version owner still selects an unused identity and upgrade ordering: the current grammar admits a flat positive alpha ordinal and rejects dotted `alpha.4.1`. Reconcile the accepted baseline and existing reservations with the next coordinated Kit preview, then verify actual client update ordering. The installer still supplies a freshly accepted preservation baseline and Cursor control readiness. The qualification owner still proves actual imports, both live GitHub contexts, and fresh useful invocation in all three clients. Ivan retains the separately required candidate-bound installation approval.

## Evidence and decision

The constraints above are grounded in the reviewed development source's `scripts/validate_provingkit.py`, `tests/test_validate_provingkit.py`, `scripts/member_versions.py`, `scripts/build_release_artifacts.py`, and `.github/workflows/provingkit-source.yml`, together with the [member-validation proposal](https://github.com/nisavid/provingkit/issues/375#issuecomment-6056053768) and the deployment owner's source/installation handoff. The retained alpha.3 identity is historical baseline evidence, not current host acceptance.

The source/release decision accepts this separate maintained member-delivery validation and Actions context while preserving ordinary Kit validation. Artifact/evidence transport and the precise input schema are implementation decisions to settle before a runnable caller exists. No validator, workflow, version assignment, delivery commit, projection, or installation is implemented by this design document.
