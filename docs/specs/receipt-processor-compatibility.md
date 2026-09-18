# Historical Receipt processor compatibility

The initial correspondence consumer supports two explicitly identified historical
profiles through retained matching execution. This matrix defines the evidence
needed to qualify them; source inspection and the P24 prototype do not supply
that new implementation's compatibility pass.

This table accompanies the [public interface proposal](receipt-correspondence-interface.md)
for [issue 135](https://github.com/nisavid/provingkit/issues/135).

## Frozen source identities

| Name | Full commit | Role |
| --- | --- | --- |
| P957 / `p957` | `957550119aca20a31a26f4e5f9a3f09a2d6bd148` | Consumed older processing implementation. |
| P24 / `p24` | `24c2d712a0be6a95958713ec80c7e06a89abdc6c` | Consumed later processing implementation. |
| D079 | `0797623a3d8dfafb600f0cb1009e4f6d4538bb30` | Consumed procedure revision. Its five processing files have the same bytes and Git modes as P24. |
| Prototype | `4131b63e68ffd1a94457a097a5674837f5a20ed3` | Local Git fixtures and constructed records using unchanged P24. |

The processing closure is `scripts/behavior_eval_receipts.py`,
`release/behavior-eval-receipt-v1.schema.json`, and
`release/behavior-eval-policy.json`; normalized descriptors also bind
`scripts/behavior_eval_corpora.py` and `scripts/behavior_eval_inventory.py`.
P957→P24 changes core, schema, and inventory. Corpus adapter and policy bytes
are unchanged. All full identities and committed path modes remain significant.

The initial registry maps these names to their exact source, closure manifest,
supported methods/shapes, historical public entrypoint, and qualified runtime.
No prefix, branch name, schema version, or matching threshold selects a profile.
For normalized reconciled Receipts, all five recorded P inputs must match the
registered processing closure. The legacy runtime checks running bytes against
committed P bytes; it records committed modes but does not compare filesystem
modes. The new runner preserves and verifies the registered source manifest.

Prepared Receipts bind processing through S and carry no recorded P. Dispatch
must match the three or five processing inputs frozen at S to an explicit
registered profile and supported descriptor shape. A matching retained runtime
is a new consumer requirement: the historical prepared checker itself did not
enforce running-byte equality. Record the implementation actually used for this
validation without claiming it proves which executable originally produced the
Receipt. Unknown or mixed processing closures fail rather than guessing.

## Method and processor matrix

| Case | Historical semantics to preserve | Required new-consumer behavior | Evidence currently available |
| --- | --- | --- | --- |
| P957 prepared | Processing files belong to the S snapshot; no separate P. Prepared result envelopes bind the snapshot. | Dispatch by frozen S processing inputs; run matching P957 at S/S, reconstruct full prepared closure, compare C including processing paths. | Source-derived. No P957 prototype pass. |
| P24 prepared | Same processing placement. Prepared checking does not itself reject every foreign runtime. | Matching P24 dispatch plus unchanged full prepared closure; explicitly reject mismatched profile inputs before claiming historical validation. | Constructed P24 prepared landing and mismatch controls in the prototype; new public interface remains unimplemented. |
| P957 reconciled | Separate S and P; one uniform runtime-input set plus each case's fixtures, applied to every repetition. | Run unchanged P957 with its recorded processing identity; preserve all original records and lineage; compare reconciled C closure. | Source-derived; consumed historical evidence is retained by its owner, not rerun by this design task. |
| P24 reconciled, uniform | Separate P; omitted `case_runtime_inputs` uses uniform semantics. | Run P24; preserve original delivered input meaning and all processing checks. Same public shape as older evidence does not allow a foreign runtime. | Constructed P24 reconciled and changed-rubric fixtures in the prototype. |
| P24 reconciled, per-case | Optional `reconciliation.case_runtime_inputs`; exact application coordinates, entrypoint in every set, global runtime list is their union; each repetition delivers its case set plus fixtures. | Run P24; preserve coordinate-specific delivery and reject incomplete or inconsistent sets. | Source and source tests; no claim that the 47-case prototype qualified this full feature. |

These rows cover both normalized five-file and direct-core three-file shapes
where the named processor supports them. Whole-inventory qualification still
requires the authoritative inventory descriptor. If a direct-core Receipt's
descriptor is not equal to that descriptor, report the incompatibility; do not
promote caller-declared closure into inventory authority.

## Negative and cross-profile matrix

| Input or attempted shortcut | Required outcome and reason |
| --- | --- |
| Reconciled P957 Receipt executed under P24, or P24 under P957 | Refuse profile/runtime mismatch. The unchanged historical processing check would reject differing running bytes; a wrapper must not relabel P. |
| P24 per-case declaration presented to P957 | Reject unsupported shape; P957's closed schema rejects the added field. Never drop it to restore a uniform shape. |
| Prepared Receipt checked under foreign code with the same schema version | New consumer rejects a nonmatching registered processing closure. Do not claim that this rejection already existed in the prepared checker. |
| Unknown P, mixed processing manifest, missing source, or unavailable historical runtime | Explicit unsupported/mismatch/missing-provenance/error result; no latest-processor fallback. |
| Changed profile name or recorded P while preserving observations | Reject binding or snapshot mismatch; changing metadata is not a reviewed transformation. |
| Missing case/repetition/expectation/trigger, wrong severity, duplicate execution identity | Historical failure with the original coordinate and diagnostic retained. |
| Below-threshold results or a pending waiver | No qualification. Allowed quality failures remain visible when the unchanged aggregate policy passes. |
| Ordinary quality 2/3 succeeds but a required member method demands 3/3 | Ordinary correspondence can pass; member qualification fails. The member/readiness consumer must require the separate C-bound member result. Missing member evidence also blocks that stronger claim. |
| Receipt committed at H differs from the reviewed binding while C matches it | `reviewed-receipt-mismatch`; the maintained entrypoint verifies H bytes, mode, source, method, profile, and processing, separately from its C check. |
| Independently retained original B is not an ancestor of H or C, but both comparisons and evidence are complete | Compare committed trees normally; B ancestry is not an ordinary correspondence prerequisite. |
| Changed rubric without original grading or adjudication | Historical lineage failure. Current grading cannot erase prior failed observations. |
| Prepared processing changes at C | Closure mismatch even when skill text is unchanged. |
| Reconciled processing files change at C, with unchanged recorded P | Check descriptor obligations: P stays independently bound; any processing file explicitly consumed as source still must match. No blanket exclusion. |
| New file under a selected skill, removed dependency, changed executable mode, altered map or content lock | Complete closure mismatch or unresolved descriptor; never compare only paths already listed by the Receipt. |

Execute each row with literal expected outcomes through the maintained public
interface. For legacy rejection claims, additionally run the named unchanged
processor and retain its observed result. Record source-derived expectations
separately from those actual observations.

## Inventory compatibility

P24 changes more than the Receipt schema. Its inventory uses per-consumer matrix
projections for applicability, aggregates runtime-owner aliases and companion
declarations, and recognizes changes to inputs of unresolved runtime owners.
P957 can select a broader set when an unrelated matrix row changes. Current
selection follows V's explicit P24-based contract; historical Receipt processing
follows the Receipt's registered profile. They cannot substitute for each other.

Qualification must cover:

1. An unrelated matrix declaration changes without selecting an otherwise
   unaffected consumer, while a selected consumer still binds the full matrix
   bytes for freshness.
2. Multiple declarations and colon/slash owner aliases retain all applicable
   runtime dependencies and companion declarations.
3. A referenced runtime input changes for an unresolved owner and makes
   selection incomplete, even when its declaring matrix is unchanged.
4. Ownership transfer selects both old and new owners; removal cannot erase
   required old-side coverage; malformed or unsupported changed corpora fail.
5. A P957 Receipt's historical descriptor is compared with the authoritative C
   descriptor under V. A difference is an explicit migration/evidence need,
   never normalized away merely to claim compatibility.

## Evidence ledger and remaining qualification

The committed prototype records 47 constructed landing/check scenarios, four
fresh-clone retention cases, a Receipt-only control, and divergent fast-forward
refusal. It uses unchanged P24 `check` at S/S, then a private `_freeze` call for
extra C comparison. The final prototype had clean Standards and Spec reviews.
Its results are evidence for the behavior being specified, not for new public
source, hosted execution, independent production retention, or P957 support.

The implementation owner must publish a results table for every matrix row with
V, check D, Receipt bytes, S, recorded P or null, actual historical runtime and
manifest, original B, C, expected/observed status, stage, diagnostic, and test
artifact references. Include both successful preserved evidence and every
negative case. New implementation or dependency changes invalidate affected
results and reviews. Runtime reproducibility and retrieval must be qualified
with issue 136 before activation.

No extracted interpreter is selected for v1 historical evaluation. If matching
execution becomes impractical, return a concrete compatibility or migration
proposal to the operator. Preserve the existing evidence while deciding; do not
silently replace the mechanism or rerun models under this specification.

## Immutable source references

- [P24 closure construction](https://github.com/nisavid/provingkit/blob/24c2d712a0be6a95958713ec80c7e06a89abdc6c/scripts/behavior_eval_receipts.py#L142-L203).
- [P24 processing snapshot](https://github.com/nisavid/provingkit/blob/24c2d712a0be6a95958713ec80c7e06a89abdc6c/scripts/behavior_eval_receipts.py#L381-L396).
- [P24 production and evaluation](https://github.com/nisavid/provingkit/blob/24c2d712a0be6a95958713ec80c7e06a89abdc6c/scripts/behavior_eval_receipts.py#L1254-L1335).
- [P957 reconciliation](https://github.com/nisavid/provingkit/blob/957550119aca20a31a26f4e5f9a3f09a2d6bd148/scripts/behavior_eval_receipts.py#L1044-L1105).
- [P24 inventory selection and committed reads](https://github.com/nisavid/provingkit/blob/24c2d712a0be6a95958713ec80c7e06a89abdc6c/scripts/behavior_eval_inventory.py#L696-L831).
- [D079 original evidence and result contract](https://github.com/nisavid/provingkit/blob/0797623a3d8dfafb600f0cb1009e4f6d4538bb30/docs/behavior-eval-receipts.md#L90-L200).
- [P24 per-case source tests](https://github.com/nisavid/provingkit/blob/24c2d712a0be6a95958713ec80c7e06a89abdc6c/tests/test_behavior_eval_receipts.py#L310-L539).
- [Prototype consumer](https://github.com/nisavid/provingkit/blob/4131b63e68ffd1a94457a097a5674837f5a20ed3/docs/prototypes/receipt-landing-131/consumer.py#L73-L103).
- [Prototype measurement](https://github.com/nisavid/provingkit/blob/4131b63e68ffd1a94457a097a5674837f5a20ed3/docs/prototypes/receipt-landing-131/results.json).
