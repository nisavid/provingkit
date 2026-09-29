# Record PR-writing evaluations

Record the eleven PR-description cases as 33 supplied-instruction applications,
retain independent judgments for all 43 whole criteria, and reconcile them with
nineteen direct skill-selection observations. Load this procedure when preparing,
recording, grading, collecting, or reconciling that corpus. Use
`capturing-agent-procedures` when consuming or changing the method.

The [method package](../../scripts/mergecraft_pr_writing_evals/) owns preparation
and correspondence. The [receipt procedure](../behavior-eval-receipts.md), its
processor, schema, policy, and accepted maps own inventory, reconciliation, and
receipt checking. The separate
[Markdown and relation evaluations](mergecraft-writing-evaluations.md) retain
their own method and Claude route.

## Bind the method and committed source

Run commands from a checkout containing this package and the canonical receipt
processor. Python, Git, and `jsonschema` are required. The package verifies the
five processing files against
[the reviewed correspondence](../../scripts/mergecraft_pr_writing_evals/correspondence.json).
Its supported public processing revision **P** is
`e48778f3d733d6c82961b7fed56b9bd43bee5f5f`. A changed processor, client, native
recorder, or prompt constructor requires reviewed correspondence and affected
tests before use. Preserve populated source maps. Missing dependencies stop the
operation.

Before preparation, load the published receipt procedure identified by
`receipt_procedure` in the correspondence file and record its revision and byte
digest as **D**, separately from P. The current D and P name the same commit but
serve different roles: D identifies the consumed instructions; P identifies the
processing implementation.

This binding uses the ordinary inventory preparation, reconciliation, and checking
interfaces. It does not register P as a historical correspondence profile or
activate a landing workflow. Retained `p957` and `p24` profiles keep their original
commits and processing bytes; current processing bytes cannot be labeled as
either profile. Keep earlier adapter contracts and evidence under their original
identities. The final source owner selects the applicable landing procedure.

The source owner supplies committed **S**, the twelve-path source binding, and
the source review. The evaluation coordinator owns preparation, retained private
evidence, independent grading, and dispatch under the existing authorization.
Keep final source selection and launch review with those owners. This procedure
does not select S or create evaluation authorization.

Use the committed corpus, its ten fixtures, accepted expectation/input maps, and
ordinary direct queries. The frozen contract preserves 20 safety criteria
(3/3 required), 23 quality criteria (at least 2/3 required), and three repetitions.
“Safety” here is the corpus's writing-invariant category. Keep every clause in
each original criterion. The Phase 2 matrix, fifteen other selection queries,
and eight native composition cases are outside this receipt.

Create a private runtime-binding JSON file with exactly `path`, `sha256`, and
`version`. `path` is the reviewed local executable's absolute path; its bytes
must match the pinned client digest and version in `correspondence.json`.
Retain that file's raw SHA-256. No installed path is built into this package.
For a launcher-managed installation, select and hash the native Codex executable;
record the launcher and package-manager shim separately. Reobserve the selected
executable before launch. A version or help probe establishes local command
correspondence, not provider qualification.
All output directories below are private, caller-selected, and new.

```sh
python -B -m scripts.mergecraft_pr_writing_evals.inputs \
  --source-root "$source_checkout" --revision "$S" \
  --runtime-binding "$runtime_binding" \
  --runtime-binding-sha256 "$runtime_binding_sha256" \
  --processing-revision "$P" --output "$frozen_inputs"
```

The command derives tasks and grading material from committed source, verifies
the accepted whole-criterion identities and severities, and freezes the direct
query and constructor correspondence. It returns the raw input-manifest digest
and leaves `STOP_LAUNCHES`. It creates no observations. Inspect and retain the
result before preparation.

Using the canonical inventory, obtain a ready descriptor and snapshot for S
and `mergecraft/writing-reviewable-pr-descriptions`; follow the receipt
procedure's `descriptor` and `prepare` commands. The final source binding has
`status: "reviewed-final-pr84-source"`, full `repository_head`, a
`source_review` object containing its retained path and raw `sha256`, and all
twelve `source_sha256` entries named in the method contract. Matching bytes
establish correspondence, not the reviewer's authority. The loaded maintained adapter must also exist at its
canonical paths in S with identical bytes and executable Git modes. That separate
method-source binding covers the complete package without widening the twelve
instruction bindings. Every subsequent operation revalidates it; recording
revalidates it again after the process returns.

```sh
python -B -m scripts.mergecraft_pr_writing_evals.prepare_application \
  --source-root "$source_checkout" \
  --binding "$source_binding" --binding-sha256 "$source_binding_sha256" \
  --inputs "$frozen_inputs" --input-manifest-sha256 "$input_manifest_sha256" \
  --receipt-snapshot "$snapshot" \
  --receipt-snapshot-file-sha256 "$snapshot_file_sha256" \
  --receipt-snapshot-sha256 "$snapshot_document_sha256" \
  --receipt-descriptor "$descriptor" --receipt-descriptor-sha256 "$descriptor_sha256" \
  --output "$run_directory"
```

The snapshot document digest is the processor's sorted, compact UTF-8 JSON
digest without a final newline. Its raw file digest and the runner manifest's
raw digest are separate identities. Preparation requires committed bytes and
modes; a matching dirty overlay cannot substitute for S. It copies the frozen
inputs into `method-inputs/` and leaves the new run's launch hold in place.

Review the complete snapshot, source binding, eleven requests, withheld rubrics,
runtime binding, delivery table, and helper digests. Each provider request has
exactly `prompt`, `fixture`, and `candidate_bundle`, with the original prefix,
serialization, and newline join. No rubric or receipt metadata is delivered.
The union of supplied instruction paths is eight; the source closure remains
twelve. Case 10 delivers only its three Mergecraft paths. That omission is an
input variant, not a claim about the host's installed equipment.

## Record and grade selected coordinates

The coordinator removes the run's launch hold only after the applicable source,
method, and payload reviews. Run only selected coordinates under the existing
authorization. Case 0/repetition 1 and case 10/repetition 1 are preflights and
count among the 33. Keep at most three concurrent clients and the 180-second
timeout. Failed or interrupted attempts remain create-only evidence for owner
disposition; the method provides no automatic scheduling or retry.

```sh
python -B -m scripts.mergecraft_pr_writing_evals.run_application \
  --root "$run_directory" --manifest-sha256 "$manifest_sha256" \
  --case 0 --repetition 1

python -B -m scripts.mergecraft_pr_writing_evals.receipt_artifacts \
  --root "$run_directory" --manifest-sha256 "$manifest_sha256" \
  project-execution --case 0 --repetition 1
```

The recorder opens binary streams before execution and retains them before
decoding. It preserves LF framing, Unicode, CRLF inside responses, and original
message joining. Invalid UTF-8, malformed or ambiguous JSON, non-finite numbers,
task-tool events, timeout, launch failure, nonzero exit, and incomplete or empty
responses cannot qualify. The original execution record is written at ordinary
completion, including ordinary failure; projection cannot invent a missing
record after interruption.

Execution projection re-observes the raw streams, command, launch metadata,
response bytes, and original session identity. It creates the processor's
closed execution envelope and separate original-file correspondence without
rewriting either. The model and effort are requested configuration;
served-model identity and ambient provider context remain opaque.

Give an independent grader the execution envelope and response, actual request,
case's `grading-contract.json`, preparation-time
`receipt/grading-rubrics.json`, accepted IDs/severities, and owning policy.
Withhold prior grades and desired verdicts. Grade every clause in every complete
criterion. Record supplementary inaccuracies separately, including an explicit
empty list when none were observed.

Retain the rich grade and grader configuration inside the run directory. The
grade contains `snapshot_sha256`, original `case_id`, `repetition`, `model_id`,
`executor_output_sha256`, `response_sha256`, `expectations`, and
`supplemental_observations`. Each expectation has its accepted `id`, Boolean
`passed`, and concrete nonempty `evidence`. The executor digest covers the exact
execution-envelope file. Configuration contains `model_id`, a descriptive
`basis`, and explicit `model_basis` of `configured`, `requested`, or `reported`,
matching the actual metadata. Preserve other original configuration fields.

```sh
python -B -m scripts.mergecraft_pr_writing_evals.receipt_artifacts \
  --root "$run_directory" --manifest-sha256 "$manifest_sha256" \
  project-grading --case 0 --repetition 1 \
  --grade "$grade" --grade-sha256 "$grade_sha256" \
  --grader-configuration "$grader_configuration" \
  --grader-configuration-sha256 "$grader_configuration_sha256"
```

False judgments remain false. The rich grade, configuration, and supplementary
observations remain intact beside the closed grading envelope. Metadata
correspondence does not establish that semantic grading occurred. Fresh grades
have no prior-grade or adjudication lineage; existing lineage stops assembly
for a reviewed adapter decision instead of being discarded.

## Reconcile and check the receipt

Collect only after all 33 valid attempts and 129 complete judgments exist:

```sh
python -B -m scripts.mergecraft_pr_writing_evals.receipt_artifacts \
  --root "$run_directory" --manifest-sha256 "$manifest_sha256" \
  collect-applications --output "$new_application_index"
```

Collection requires distinct original sessions and exact planned coordinates,
retains negative counts, and leaves `public_receipt_ready: false`. It is an
application index, not the processor's results input or a passing receipt.

Complete the separately reviewed native selection method against S's exact
writer entrypoint and query source. Its manifest must bind the helper and
constructor identities in the method contract. Retain original commands,
queries, probes, traces, responses, and records. The assembler selects exactly
the nineteen direct queries, checks their source and technical correspondence,
and copies original bytes into the application capsule. A technically complete
wrong selection remains a threshold failure. Unsupported or incomplete traces
remain errors.

```sh
python -B -m scripts.mergecraft_pr_writing_evals.receipt_artifacts \
  --root "$run_directory" --manifest-sha256 "$manifest_sha256" \
  assemble-reconciliation --discovery-freeze "$native_directory" \
  --discovery-manifest-sha256 "$native_manifest_sha256" \
  --output "$run_directory/reconciliation.json"

python -B scripts/behavior_eval_inventory.py --repository "$source_checkout" \
  reconcile --revision "$S" --processing-revision "$P" \
  --skill mergecraft/writing-reviewable-pr-descriptions \
  --results "$run_directory/reconciliation.json"
```

Assembly calls the actual pinned processor. If that call rejects the input,
retain the new capsule and its failure provenance. It remains create-only.
Threshold failures remain inspectable results, and assembly never claims public
receipt readiness. Capture the separate producer's stdout create-only as the
proposed public receipt and retain stderr/exit separately. Inspect its public
projection for private paths, raw responses, operational streams, and unsupported
served-model claims before the owning publication route acts.

After publication at containing commit **C**, run the same processor's `compare`
and `check` against comparison base **B** and C, with the committed receipt root.
Cover every selected consumer. Keep B, evaluated S, containing C, processing P,
original execution revisions, and both snapshot digests distinct. The prepared
snapshot and reconciliation snapshot can differ. Likewise, the rich grade's
executor digest identifies its envelope, while the reconciled public run's
executor digest identifies the response.

For the normal Mergecraft source-stage route, invoke the complete member validator
at clean C using the separately recorded procedure D:

```sh
python -B scripts/validate_mergecraft.py "$source_checkout" --source-stage \
  --base "$B" --candidate "$C" --receipt-root "$RECEIPTS" \
  --procedure-revision "$D"
```

The running five-file processor must match P, and the running receipt procedure
must match D. Structural validation and the full member's selected receipts must
pass. The PR-writing adapter qualifies only its own receipt; it does not replace
other selected skills' evidence or the stricter relation-member requirements.
Preserve the existing original P/D/S identities when adopting this method for
new preparation. Historical correspondence and landing activation remain with
their owning procedures.

## Verify changes and integration

```sh
python -B -m unittest tests.test_mergecraft_pr_writing_evals -v
ruff check --no-cache scripts/mergecraft_pr_writing_evals \
  tests/test_mergecraft_pr_writing_evals.py tests/mergecraft_pr_writing_evals
ruff format --no-cache --check scripts/mergecraft_pr_writing_evals \
  tests/test_mergecraft_pr_writing_evals.py tests/mergecraft_pr_writing_evals
git diff --check
```

Tests consume the canonical processor, corpus, fixtures, and accepted expectation
map from their own checkout. A synthetic input map declares the twelve paths in
the small test repository. They create disposable Git histories and an explicitly constructed
processing commit from the pinned bytes. That commit is not public P. Local
synthetic process responses and judgments exercise all real coordinates without
providers or historical object-store access; they are mechanical evidence only.

A method-only patch on a branch lacking the processor or accepted source inputs
is an integration input. It cannot run the combined suite alone. Integrate the
dependency through its existing source owner, preserve its accepted maps, and
run the owning suite on that composition. Before dispatch, the integrating owner
must repeat the mechanical roundtrip against the eventual committed source
closure and actual public P, then obtain current independent review of the
method and source. A constructed test identity cannot replace that check.

Retain the procedure revision, source and processing identities, raw manifests,
comparison/check output, and any failures with the consumer's evidence. Feed
correspondence changes back to the owning processor or native method rather
than substituting implementations locally. This procedure establishes no
isolation, authenticity, installation, release, or causal baseline claim.
