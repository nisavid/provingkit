---
title: Receipt correspondence and historical processor compatibility
version: proposal-1
date_created: 2026-09-18
owner: Receipt implementation owner, issue 33
tags: [design, receipts, compatibility]
---

# Receipt correspondence and historical processor compatibility

This contract lets unchanged evaluated inputs qualify after squash or rebase
while preserving what the original Receipt says was observed and processed.
Historical evidence is checked by its matching retained processor; a maintained
public interface then compares the complete evaluated inputs with the actual
landed Candidate.

This is the proposed specification for [issue 135](https://github.com/nisavid/provingkit/issues/135),
under the [accepted strategy](https://github.com/nisavid/provingkit/issues/132#issuecomment-5734437374).
It defines implementation and qualification obligations. It supplies no
implemented interface, compatibility pass, hosted qualification, or activation.

## 1. Purpose and scope

The existing [Receipt owner](https://github.com/nisavid/provingkit/issues/33)
owns the public implementation and maintained procedure. This specification
covers ordinary evidence semantics, selection, correspondence, compatibility,
and results. The [caller and retention design](https://github.com/nisavid/provingkit/issues/136)
owns independent retention, acquisition, delivery, actual-commit identification,
and its required security judgments. The two designs must reconcile their shared
inputs and results before implementation acceptance.

Squash is preferred; rebase is also proposed for support, subject to separate
hosted qualification for each route. Merge commits and direct fast-forward
publication are outside this contract. No current source window, execution
allocation, landing order, or qualified historical result changes here.

## 2. Identities and evidence

| Identity | Meaning |
| --- | --- |
| B | Independently retained original comparison base. Never replaced by a Receipt-only comparison or C's parent. |
| H | Reviewed source head containing the reviewed Receipts. |
| T | Separately observed target immediately before the reviewed landing attempt. Target movement requires a refreshed context. |
| S | Receipt `candidate_revision`: prepared evaluated source, or source reconciled with retained observations. Reconciled S need not be the original execution revision. |
| P | Recorded reconciled processing revision. Prepared Receipts have no separate P field. |
| D | Reviewed procedure revision actually consumed by a producer or dependent execution. Each execution records its own D separately from its processing implementation. |
| C | Actual landed commit obtained by the caller. C is checked, never described as an evaluation execution merely because correspondence passes. |
| V | Published implementation revision of the new correspondence consumer, including its selection and compatibility rules. |
| Historical validation implementation | Retained implementation actually run to validate a Receipt now. It is recorded separately from the original execution and from V. |

A closure is the complete authoritative descriptor and map of repository-relative
paths to committed byte digests and Git modes. It includes source, dependencies,
corpora, mappings, and the processing inputs required by the Receipt's method.
Selection determines which consumers need evidence; closure determines whether
that evidence is still fresh. Delivered inputs describe what an execution
actually received. These are three different sets.

The [compatibility matrix](receipt-processor-compatibility.md) pins P957, P24,
and D079 to full commits, explains their differences, and identifies the limits
of the demonstrated evidence. `schema_version: 1` alone selects no processor.

## 3. Requirements and constraints

- **REQ-01, historical meaning:** Preserve the original Receipt bytes, S, recorded
  P, original execution identities, model evidence bases, failures, grading, and
  adjudication. Historical validation rechecks recorded evidence; it runs no
  models and creates no observations. Changed-rubric evidence retains both prior
  grading and actual adjudication references.
- **REQ-02, historical validation:** Select an explicitly supported historical
  profile and run its retained unchanged public `check` implementation against
  S/S with the Receipt's complete descriptor. Require its selected row and
  aggregate result to pass. This deliberately satisfies the legacy ancestry
  condition at S; it does not claim the legacy checker passed at C.
- **REQ-03, correspondence:** Independently derive the authoritative descriptor
  at C and reconstruct the complete closure at S and C under the registered
  profile's closure rules. Require descriptor equality and exact path, byte,
  and mode correspondence. The reconstructed S snapshot must equal the Receipt
  snapshot. S ancestry at C is not required by this new consumer.
- **REQ-04, selection:** The inventory layer derives complete old/new consumer
  selection for B→C from committed Slate, Rosters, declarations, and mappings.
  It preserves both owners of transferred inputs and reports removed or
  unresolved consumers. Caller-supplied consumer lists cannot narrow it.
- **REQ-05, reviewed inputs:** Derive B→H selection during preparation and B→C
  selection after landing. The final required set must equal the independently
  reviewed Receipt-binding set. An added or removed required consumer requires
  refreshed review and evidence; never discard the difference to obtain a pass.
- **REQ-06, committed evidence:** Read selected Receipts from the Git tree at C,
  verify their raw bytes and modes against the reviewed bindings, and retain
  their committed object identities. Dirty files and arbitrary local Receipt
  paths cannot satisfy this contract.
- **REQ-07, immutable policy:** Preserve complete application/trigger coverage,
  three distinct executions per case, safety 3/3, quality 2/3, required trigger
  results, and stricter consumer-specific criteria. Production of a Receipt is
  not qualification. A pending waiver cannot produce an aggregate pass.
- **REQ-08, provenance:** Require available B, H, T, S, recorded P, historical
  validation implementation, consumed procedure revisions, V, and C, with the
  source identities needed to reproduce each check. Original private artifacts
  remain under their owners' retention contracts; ordinary public validation
  does not claim to reopen or authenticate those originals.
- **REQ-09, observable completion:** Record a machine-readable result bound to
  C outside C's source content. A missing, failed, or incomplete final result
  leaves C qualification-pending. A previous pre-landing success is insufficient.

The original B must remain an ancestor of H and C; T must be an ancestor of C.
For squash, C's first parent must be T. The caller supplies the independently
established landing relation and refreshed target observation for the supported
operation. These structural checks do not establish that a forge performed it.
Issue 136 must define the complete operation-specific check, including rebase
completion and target movement, before a route is activated.

## 4. Public interfaces and data contracts

### Maintained source

| Source | Responsibility |
| --- | --- |
| `scripts/behavior_eval_receipts.py` | Public historical-validation orchestration and per-Receipt closure/correspondence; policy outcomes and lineage remain owned here. |
| `scripts/behavior_eval_inventory.py` | Complete old/new selection, authoritative descriptors, committed Receipt reads, aggregate result, and public caller entrypoint. |
| `scripts/behavior_eval_corpora.py` | Existing normalization and original source coordinates. |
| `docs/behavior-eval-receipts.md` | Reviewed invocation procedure, supported profiles, entry conditions, branches, and result consumption. |

The implementation must expose these public operations; their structured request
and result meanings below are normative. Python representation details may be
settled by the owner without changing those meanings.

```python
# behavior_eval_receipts
input_closure(repository, revision, descriptor, *, profile, method)
check_correspondence(repository, *, candidate_revision, descriptor,
                     receipt_bytes, binding)

# behavior_eval_inventory
check_landed(repository, *, context, landing)
```

`input_closure` returns the full snapshot shape used by the profile, including
the descriptor, revision, and complete path/digest/mode map. `profile` and
`method` are validated closed choices, not flags for omitting inconvenient
inputs. Prepared closures bind processing at S and C. Reconciled closures keep
separate P binding, while explicitly declared processing paths remain source
inputs if the descriptor includes them.

`check_correspondence` owns strict parsing, profile dispatch, matching retained
historical execution, snapshot reconstruction, C correspondence, and per-Receipt
results. It derives the historical descriptor from the validated Receipt and
requires equality with the authoritative C descriptor. A core result declares
`coverage_basis: "per-receipt"`; it is never complete inventory qualification.
The core cannot accept a caller's `historical_pass` Boolean instead of executing
the registered validation path.

`check_landed` owns the ordered aggregate procedure below. Its CLI is:

```sh
python scripts/behavior_eval_inventory.py check-landed \
  --context reviewed-context.json --landing actual-landing.json
```

These are proposed names, not commands available in the consumed draft. The
context and landing files are caller inputs whose independent provenance and
delivery are established by issue 136. A committed copy cannot replace that
independent source. A public test and a production caller must use these same
operations; callers must not access private `_freeze` or copy closure logic
into a CI wrapper.

### Reviewed context

All fields below are required. Unknown fields, duplicate JSON keys, non-finite
numbers, invalid Unicode, abbreviated revisions, invalid paths, and wrong types
are errors. Revisions are full lowercase Git object IDs; every referenced object
must resolve to its stated commit. Hashes are lowercase SHA-256 hex.

| Field | Contract |
| --- | --- |
| `contract` | Literal `provingkit.receipt-correspondence/v1`. |
| `original_base` | B. Independently retained through every refresh. |
| `reviewed_head` | H. |
| `reviewed_target` | T for this attempt. |
| `operation` | `squash` or `rebase`. |
| `consumer_revision` | V approved for this invocation; bind its complete implementation manifest in the issue 136 execution contract. |
| `procedure_revision` | D for this check, distinct from each producer's D. |
| `receipt_root` | Authorized normalized repository-relative directory; outside all selected evaluated closures. |
| `receipts` | Map of `plugin/skill` to the complete binding below. Exact selected set, no wildcard or implicit omissions. |

Each Receipt binding contains `path`, `raw_sha256`, `mode`, `evaluated_revision`,
`method`, `profile`, `processing`, and `producer_procedure_revision`.
The path must equal `<receipt_root>/<plugin>/<skill>.json`; it names a committed
regular blob with mode `100644` or `100755`. `evaluated_revision` is S. `method`
is `prepared` or `reconciled-after-run`; `prepared` is a dispatch label and does
not insert a method or processing field into a historical Receipt that lacks it.
`profile` is exactly `p957` or `p24` in the initial compatibility registry.

For reconciled Receipts, `processing` is the Receipt's recorded processing
object: revision P and the complete path/digest/mode map. For prepared Receipts,
it is `null`; the consumer derives processing binding from the S snapshot and
records that basis in its result. `producer_procedure_revision` comes from the
retained execution handoff, not an inferred equality with P. Missing historical
procedure provenance requires owner resolution; no field is invented to pass.

### Actual landing

The required fields are `contract` (the same literal), `context_sha256`,
`operation`, `reviewed_head`, `target_before`, and `candidate_revision`.
They bind the independently observed operation, H, T, and C to the exact context.
Any mismatch fails before evidence qualification. Issue 136 carries additional
provider observations in its own versioned envelope and translates only a
verified complete observation into these inputs. This interface does not decide
who may supply them or certify their authenticity.

### Ordered check

1. Validate request shape, supported operation, context identity, implementation
   and procedure binding, available revisions, and the B/H/T/C relations.
2. Run authoritative selection B→H and require agreement with the reviewed
   binding set. Run complete B→C selection and require the same set. Keep changed
   paths, causes, unsupported inputs, and diagnostics from both comparisons.
3. Derive each C descriptor from the committed inventory. Reject unresolved
   descriptors, missing/removed consumers, and incomplete coverage.
4. Read each committed Receipt at C. Preserve its raw digest and Git identity
   even if parsing subsequently fails. Match its reviewed binding.
5. Run `check_correspondence` for every selected consumer. Select and execute
   only the registered matching historical profile; require historical pass,
   complete descriptor/snapshot correspondence, and unchanged policy outcomes.
6. Return the full aggregate and all selected results. A failure in one consumer
   cannot hide missing results for another; mark unattempted rows explicitly if
   an operational error prevents completion.

The initial inventory semantics follow the documented P24 ordinary selection
contract, including per-consumer matrix applicability and both-side ownership.
V identifies their implementation. Do not dispatch selection to P957 merely
because a selected Receipt uses P957. The compatibility matrix must test the
effect of the two versions' selection differences. Historical evidence remains
under its own profile; a current descriptor or closure difference requires
fresh evidence or reviewed owner migration rather than relaxed matching.

### Result and failures

The aggregate returns `contract`, `status`, `stage`, `reason_code`, B/H/T/C,
`context_sha256`, V, the check's D, `coverage_basis: "complete-inventory"`, both
comparison results, `selection_complete`, and a row for every selected consumer.
Each row records the committed Receipt path/mode/object ID/raw digest, canonical
Receipt digest when parsing succeeds, S, recorded P or null, original producer D,
profile, actual historical validation implementation and processing binding,
historical outcome, correspondence outcome, and diagnostics. Record unavailable
values as null, never as fabricated identities. Record failed-grade counts and
lineage references without replacing the preserved Receipt.

| Status | Meaning and CLI exit |
| --- | --- |
| `pass` | Complete nonempty selection; every selected historical check and correspondence passes. Exit 0. |
| `not-required` | Both complete original comparisons select no consumers and the binding set is empty. Exit 0; establishes only that this comparison needs no ordinary Receipts. |
| `fail` | A well-formed request has missing, stale, unsupported, incomplete, or failing evidence/context. Exit 1. |
| `error` | Malformed request or unavailable execution machinery prevents a completed check. Exit 2. No qualification. |

Per-row status may also be `waiver-pending` or `not-checked`; neither permits an
aggregate pass. An invalid Receipt is an evidence failure, not a malformed
caller request. An unavailable retained commit is `fail/provenance-missing`;
an unavailable historical runtime is `error/historical-runtime-unavailable`.
An unsupported profile is `fail/processor-unsupported`; never substitute latest.
An operation or profile string with an unsupported value is a well-formed but
unsupported request and fails; a missing field or value of the wrong type is
a malformed request and errors.

Other stable reason codes distinguish `context-mismatch`, `target-moved`,
`operation-unsupported`, `selection-incomplete`, `selection-changed`,
`descriptor-unresolved`, `receipt-missing`, `receipt-changed`, `receipt-malformed`,
`processing-mismatch`, `historical-failed`, `snapshot-mismatch`,
`closure-mismatch`, and `waiver-pending`. Human-readable details retain the
historical diagnostic without pretending it is a newly standardized legacy code.
Changed bytes, paths, and modes must be separately identifiable in diagnostics.

Compact digests use sorted compact UTF-8 JSON, unescaped Unicode, no terminal
newline, and no non-finite numbers. `context_sha256` hashes the entire parsed
context in that encoding. A successful row's `input_identity` hashes exactly
this object, using the indicated values rather than their variable names:

```python
{
    "contract": "provingkit.receipt-inputs/v1",
    "profile": profile,
    "method": method,
    "descriptor": descriptor,
    "inputs": snapshot["inputs"],
    "processing_inputs": processing_inputs,
}
```

`profile` and `method` are the validated binding values; `descriptor` is the
complete authoritative descriptor proven equal to the historical descriptor;
`snapshot["inputs"]` is the complete map proven equal at S and C. For prepared
Receipts, `processing_inputs` is the exact three- or five-file subset of that
map required by the profile and descriptor. For reconciled Receipts it is the
complete validated `receipt["processing"]["inputs"]` map. Each map value is
the original `{"sha256": digest, "mode": mode}` object. No revision, newline,
additional key, or omitted input enters this preimage. Failed rows return null
for `input_identity`. Retain the full objects: digest equality cannot replace
any validation step.

## 5. Executable acceptance criteria

- **AC-01:** Reproduce all 47 prototype scenarios through maintained public
  interfaces. Positive merge/fast-forward fixtures remain historical controls;
  the new caller rejects those unsupported operations. Keep all negative
  coverage, dependency, ownership, mode, mapping, lineage, and threshold cases.
- **AC-02:** On actual rewritten squash/rebase commits, unchanged supported
  evidence passes while S may be absent from C's ancestry. A legacy S→C check
  still fails where expected; historical S/S validation is independently visible.
- **AC-03:** Execute every compatibility row and cross-profile rejection case
  in the companion matrix with the named retained implementations. Preserve
  differences between source-derived expectations and measured outcomes.
- **AC-04:** Add/remove a dependency, skill file, owner, or mapping; change only
  a Git mode; change processing binding; or introduce an unresolved consumer.
  Require the specified failing stage and complete diagnostic selection.
- **AC-05:** Exercise malformed JSON/schema, duplicate keys, wrong skill/S,
  missing case/repetition/expectation/trigger, duplicate execution identity,
  wrong severity, failed thresholds, and missing changed-rubric lineage. Bind
  intentionally malformed bytes in the reviewed context when testing later
  stages so an earlier raw-digest mismatch cannot masquerade as that test.
- **AC-06:** Preserve successful evidence containing allowed quality failures,
  original failed grades before regrading, all original identities, and stricter
  consumer criteria. No evidence rewrite is needed merely for a Git rewrite.
- **AC-07:** A Receipt-only range cannot replace B. Target movement, newly
  selected consumers, wrong actual C, missing context, or changed Receipt bytes
  cannot qualify. Complete empty original selection returns only `not-required`.
- **AC-08:** Read C while dirty worktree files disagree, remove required retained
  objects in a fresh clone, and recover them through issue 136's implemented
  retention route. Observe committed reads, explicit missing-provenance failure,
  and exact recovered identities after ordinary branch deletion.
- **AC-09:** Production callers and tests invoke the same public operations.
  Record the reviewed V and each consumed D. The final result lives outside C;
  missing/failing results stop dependent qualification through implemented callers.

## 6. Test strategy

Use disposable real Git repositories and constructed result envelopes for
structural and compatibility tests; those tests execute no models. Assert
observable status, selected consumers, stage, and reason rather than private
function calls. Run historical profiles separately with their exact processing
files, record runtime dependencies, and test from fresh recovered source.

CI checks evidence only. Actual hosted squash/rebase, delivery failure, retained
object recovery, and final-result consumption are separate integration tests
owned with issue 136. Owner migration tests use retained originals only within
their existing access and execution authority. A constructed record test is
not a new measurement of a skill or proof of original execution.

## 7. Compatibility decision and rationale

I recommend retained matching execution for historical validation in v1. It
keeps the demonstrated unchanged-P24 route, extends it explicitly to P957, and
preserves each processor's negative behavior. The operating cost is maintaining
recoverable historical source and runnable dependencies for both profiles.

A new semantic interpreter would require a different explicit compatibility
decision and equivalence evidence. It must identify itself as new code, not
claim unchanged-P execution. Relabeling a Receipt's P or stripping processing
inputs to make it match is never compatibility. A later reviewed transformation
uses eligible originals, records its actual new P, and preserves prior evidence
and lineage under the owner-migration contract.

The new closure interface is still new code requiring conformance evidence.
Retaining a historical checker does not prove that V reconstructs its closure
correctly. For each supported profile and method, verify the public closure's S
snapshot against the historical snapshot and qualify C comparison with the
positive and negative matrix. The private prototype helper is not the API.

## 8. Dependencies and owner handoffs

| Owner or consumer | Required handoff before dependent execution |
| --- | --- |
| Issue 33 Receipt owner | Implement the public core and inventory operations, explicit profile registry, compatibility tests, and maintained procedure; publish and review one concrete revision. Existing consumed draft remains preserved. |
| Issue 136 caller/retention | Reconcile the context, landing relation, implementation manifest, historical runtime, durable retrieval, external result, and missing-result behavior. Qualify each hosted route and its required security properties separately. The held legacy caller packet is input, not acceptance of this contract. |
| Issue 137 migration | Refresh owners and decide in-place or traceable replacement after both designs. Preserve each consumer's S/P/D/B, originals, failures, populated maps, stricter criteria, and review evidence. |
| Producers and member checkers | Load the new reviewed published procedure before dependent preparation, reconciliation, or checking; record its D separately from actual processing. A member projection of a complete result cannot claim whole-Kit qualification. |
| Issues 28 and 34 | Disclosure and readiness distinguish historical validation, pre-landing checks, and the actual C result. They verify the required result and implementation/procedure identities before relying on it. |
| Issues 10, 17, 19, 111, and 112 | Feedback, editing, review voice, PR writing, and adoption retain their own evidence/criteria and consume the new result when their authorized migration activates it. Existing allocations remain intact. |

Under `capturing-agent-procedures`, issue 33 must place entry conditions,
supported inputs, profile dispatch, ordered checks, recovery branches, and
observable completion in `docs/behavior-eval-receipts.md`, with invocation
pointers from relevant public entrypoints and dependent contracts. Consumers
load and record that reviewed revision before use and feed corrections back to
the same owner. This specification is the capture proposal; it neither installs
a procedure nor replaces D079 for already-consumed work.

## 9. Examples and edge cases

- A P957 reconciled writing Receipt lands by squash. Its S and P stay unchanged.
  Retained P957 validates at S/S; V selects the consumer from B→C and compares the
  complete C closure. It passes only after that profile's implementation and
  compatibility tests have qualified. A P24 runtime cannot stand in for P957.
- A P24 prepared Receipt lands with identical skill text but changed processor
  source at C. Prepared processing is part of its source closure, so it fails
  correspondence. Reconciled processing is separately pinned; whether the same
  path is also a source dependency follows the descriptor, not convenience.
- An unrelated matrix row changes. P24 applicability may leave a consumer
  unselected; if another change selects that consumer, its full matrix bytes
  still participate in freshness. Per-consumer selection does not weaken closure.
- A target move introduces another affected consumer. The existing context
  fails; retain B, refresh T/H and selection, and obtain the required reviewed
  evidence before another landing attempt. After a completed landing, use the
  owning recovery process; this contract grants no automatic revert or waiver.

## 10. Specification and activation validation

Specification acceptance selects the interface and matching-execution mechanism.
It requires owner coordination, a concrete compatibility matrix, clean Standards
and Spec reviews of the same published revision, and recorded operator acceptance.
It does not satisfy executable criteria AC-01–09.

Activation additionally requires the accepted strategy's four complete gates:
maintained-interface behavior; actual hosted-result checks with original B and
fresh target; independently recoverable provenance and explicit compatibility;
and downstream procedure/result consumption with engineering and required
security reviews on the final implementation and evidence dependencies.

## 11. References

- [Consumed procedure D079](https://github.com/nisavid/provingkit/blob/0797623a3d8dfafb600f0cb1009e4f6d4538bb30/docs/behavior-eval-receipts.md).
- [Reviewed prototype and limits](https://github.com/nisavid/provingkit/blob/4131b63e68ffd1a94457a097a5674837f5a20ed3/docs/prototypes/receipt-landing-131/README.md).
- [Accepted strategy and original evidence](https://github.com/nisavid/provingkit/issues/132#issuecomment-5734437374).
- [Processor compatibility and source evidence](receipt-processor-compatibility.md).
