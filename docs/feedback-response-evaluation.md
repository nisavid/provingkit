# Feedback-response evaluation preparation

The preparation controller retains private actor requests for the
feedback-response evaluation, bound to source from an immutable Git commit.
A later execution consumer verifies the preparation, every referenced
artifact, and the observed invocation outcome before using any payload.

## Public preparation interface

The selected command and test boundary are:

```text
python scripts/run_feedback_response_eval.py prepare --repository REPOSITORY --source-revision COMMIT --output-dir PRIVATE_DIRECTORY
```

`REPOSITORY` supplies the Git objects for the selected immutable `COMMIT`.
`PRIVATE_DIRECTORY` retains the preparation artifacts outside the isolated
source export. The controller must bind the selected commit and the exact
source bytes and modes it uses; live working-tree changes and untracked files
must not become preparation inputs.

Tests invoke this command as a separate process and observe its result,
public output, and retained artifacts. They do not call private controller
helpers or inspect internal state. A process result alone cannot establish
complete preparation: the consumer must verify the preparation record and
every artifact it references.

The public artifact contract below defines the record, artifact addresses,
diagnostics, and process evidence. A change to this command or its acceptance
requirements requires interface confirmation before tests depend on it.

## Source and payload contract

The maintained evaluation corpus is
[`evals/mergecraft/skills/interacting-with-pr-review-feedback/evals.json`](../evals/mergecraft/skills/interacting-with-pr-review-feedback/evals.json).
The construction interfaces are in
[`scripts/validate_feedback_response_evidence.py`](../scripts/validate_feedback_response_evidence.py):
`source_paths`, `read_source`, `executor_request`, `canonical`, `digest`, and
`grading_request`.

Preparation must proceed in this order:

1. Establish the declared input set at the selected commit, and export only
   that committed material into an isolated source tree. Retain correspondence
   between each declared path, its committed blob and mode, and its exported
   bytes. Reject missing, unsafe, or unexpected matching inputs before payload
   construction. Keep generated artifacts outside that tree.
2. Verify the source inventory used by the maintained constructor. Its
   `source_paths` includes the candidate files, corpus, case fixtures, and
   declared runtime and test globs. Because it uses filesystem globs, running
   it against a live checkout does not establish committed-source
   correspondence. The controller must establish that correspondence before
   invoking it.
3. Construct each actor request through `executor_request(root, case, variant)`.
   Encode the returned canonical string as UTF-8 and retain those exact bytes,
   without adding labels, metadata, formatting, or a trailing newline.
4. Retain and verify all required source bindings and actor artifacts before
   publishing the preparation record.

The selected evaluation has 13 original case IDs, 0–12, with repetitions 1–3
for each of `with_skill` and `without_skill`: 78 unstarted actor slots. Case,
variant, and repetition coordinates belong in the private preparation record.
Repeated slots may have identical request bytes; their distinct coordinates
must remain represented.

The maintained request contains only `prompt`, `fixture`, and
`candidate_bundle`. For `with_skill`, the bundle preserves this order:

1. `plugins/mergecraft/skills/interacting-with-pr-review-feedback/SKILL.md`
2. `plugins/mergecraft/skills/interacting-with-pr-review-feedback/references/interaction-authority.md`
3. `plugins/mergecraft/skills/interacting-with-pr-review-feedback/references/github-markdown-authoring.md`

For `without_skill`, the bundle is empty. Preserve identifying text already in
the fixtures. Do not add source paths, case or repetition labels, condition
labels, the corpus, expected answers, runtime helpers, grading results, or
execution metadata to actor content.

Keep the corpus's exact expected outputs and expectations as private future
grading dependencies, together with the grading constructor's identity.
`grading_request` requires the actual actor response and its digest.
Preparation therefore creates no grader payload, execution session, attempt
reservation, or provider call.

## Private artifacts and publication

The complete preparation must retain enough information to verify:

- The selected source commit and the declared input inventory, including exact
  byte identities, modes, and correspondence with the exported source.
- The constructor, controller, storage helper, and procedure identities used
  for this preparation, separately from the actor payload content.
- All 78 unstarted actor coordinates and their exact request bytes and
  digests, including the ordered candidate bundle and empty baseline.
- The private expected outputs, expectations, and grading-constructor binding
  required by a later consumer.
- Every artifact referenced by the preparation record.

[`scripts/evidence_transport.py`](../scripts/evidence_transport.py) supplies
existing Git, safe-path, and immutable-write primitives. The controller should
reuse `run_candidate_git` for narrowly declared read-only Git operations and
`frozen_no_replace_write` for retained artifacts. Its
`candidate_content_identity` inventories tracked and unignored working-tree
material, so it does not establish the selected commit's export.

Retained-artifact publication assumes trusted, same-user, same-machine local
POSIX storage with atomic same-filesystem hard links and reliable file and
directory `fsync`, matching the storage assumptions in
[ADR 0001](adr/0001-crash-recoverable-response-outcome-bundle.md). The controller
does not detect or certify the physical backing store. Checking retained bytes
establishes their correspondence, not crash durability. An observed publication
primitive failure must follow the incomplete or indeterminate rule below,
including after a final artifact becomes visible.

The preparation record must be published last, after every referenced
artifact is retained and verified. Publishing one file atomically does not
make the complete preparation a transaction. The implementation must establish
the ordering and completeness of the multi-artifact result through the public
command's acceptance checks.

Before record publication, the preparation tree must contain only the declared
source export, unique requests, grading dependencies, and their necessary
directories. The record path is checked separately for an immutable collision.
After record publication, the same closure check includes the record itself.
Unexpected entries, including temporary publication remnants, are preserved,
not removed or repaired. A detected remnant prevents completion: the outcome
is incomplete before record publication begins and indeterminate afterward.
Tests construct retained remnant states through the public command; those
checks do not claim to reproduce an actual hard-link race or unlink failure.

An existing artifact with the same bytes may be reused. A different-byte
collision must fail without replacing the artifact. On interrupted or failed
publication, preserve already published artifacts and report incomplete or
indeterminate preparation, including when failure follows a durable file
publication. A consumer must verify all referenced bytes before accepting a
preparation record; neither an exit status nor the record's presence is
sufficient.

Consumers retain the invocation evidence described below, including when
only a surviving record is available. Consumers must apply a known
incomplete or indeterminate publication outcome before accepting a preparation;
byte verification alone must not erase that outcome. Result serialization and
diagnostics remain implementation choices.

A preparation remains bound to its original inputs. A changed material
dependency requires a newly bound preparation, with earlier artifacts
preserved. Preparation made before a runtime-dependent candidate is final
remains provisional for that candidate; it cannot be relabeled as final
evidence.

## Acceptance through the public command

The test module is `tests/test_feedback_response_eval.py`. These are required
observations for its agreed subprocess boundary, not a qualification report:

| Required observation | Acceptance evidence |
| --- | --- |
| Preparation uses the named immutable commit. | Exported bytes and modes correspond to that commit's declared inputs; live and untracked source material cannot contaminate the result. |
| Every actor slot is prepared without starting it. | The complete 78-coordinate inventory and referenced payload bytes match the maintained constructor, with the ordered three-file candidate bundle and empty baseline. Private coordinates and grading material are absent from added actor content. |
| Publication cannot expose a false complete preparation. | The preparation record is published only after all referenced artifacts. An interrupted or partial publication cannot be accepted as complete, including after final-record visibility; retained byte validity does not override an incomplete or indeterminate invocation outcome. |
| Existing evidence remains immutable. | Same-byte reuse preserves artifacts. Different-byte collisions reject the preparation without replacement or a false complete result. |

The tests must retain the observed subprocess result and inspect the complete
preparation record and referenced artifacts. They must exercise failure and
reuse behavior through the same public boundary. These checks do not establish
provider-session isolation, tool enforcement, actual served model, exchange
capture, grading truth, response-runtime reconciliation, or qualification.

## Implementation and consumer prerequisites

The controller implementation surface consists of
`scripts/run_feedback_response_eval.py`,
`tests/test_feedback_response_eval.py`, and this document. It preserves the maintained constructors,
response runtime, fixtures, retained response evidence, plugin content locks,
or release definition.

Before source publication of the implementation, compare the real committed
candidate with its observed baseline through the maintained behavior-evaluation
inventory route. Bind the comparison tool and its material dependencies,
commits, changed paths, command, and retained process evidence. Read the result's
selected consumers, causes, completeness, unsupported cases, and diagnostics;
path matching alone cannot settle the effect on dependent evaluations. A
complete comparison is source-selection evidence, not behavioral qualification.

Use `capturing-agent-procedures` when implementing and handing off the
preparation procedure. Its completion still requires a maintained invocation
pointer, an actual consumer invocation of the reviewed revision, and verified
CI discovery of the new test module. The developer-documentation pointer and
CI integration remain separate work; this three-path increment cannot claim
them from source preparation alone.

The consuming task must load this procedure at its reviewed revision, record
that revision and the preparation's bound inputs, and verify the preparation
record and referenced bytes, and apply the bound invocation outcome before use.
Final runtime-dependent evaluation preparation also requires disposition of
findings that affect its runtime candidate and fresh binding after any repair.
Actor or grader execution needs
its separately reviewed payload and transport contract, applicable execution
authority, and actual observations. Preparation supplies actor inputs and
grading dependencies; execution and qualification retain their own gates.

## Supported inputs and tool admission

Use Python 3.13 or newer and locally available Git objects. A checkout root or
bare object store is eligible when the required operations work. The storage
assumptions above apply; admission does not certify a host or filesystem.
`COMMIT` is a full lowercase OID: 40 hexadecimal characters for SHA-1 or 64
for SHA-256. It must resolve to itself as a commit through the closed
`run_candidate_git` adapter, without lazy fetching or network protocols.

The controller captures four regular, non-symlink files from its canonical
source layout once:

| Role | Path |
| --- | --- |
| Controller | `scripts/run_feedback_response_eval.py` |
| Constructor | `scripts/validate_feedback_response_evidence.py` |
| Storage helper | `scripts/evidence_transport.py` |
| Procedure | `docs/feedback-response-evaluation.md` |

Before executing helper code or changing output directories, it compares the
captured helper's SHA-256 with its literal `BOOTSTRAP_STORAGE_HELPER_SHA256`.
It compiles that buffer directly into a fresh module for closed Git reads,
then verifies all four buffers against blobs at the same paths in `COMMIT`,
including locally recomputed Git object IDs. Only after that gate does it
compile the captured constructor. Normal imports, preloaded modules, and
timestamp or hash bytecode caches do not supply either helper's executable
code. A helper update requires a matching committed controller pin.

All evaluation inputs and tool versions come from this one selected commit
tree. They may have been introduced separately. The first preparation needs a
committed successor containing the controller; an older input revision with
tools borrowed from another commit is outside this contract. The interpreter,
standard library, and trusted Git executable remain environment assumptions.

The source inventory is the union of the constructor's candidate paths,
manifest, case files, and mandatory `SOURCE_GLOBS` matches. Selection uses the
complete NUL-delimited tree listing. Original pathname bytes are preserved;
the reversible UTF-8 `surrogateescape` view is used only for glob matching and
pathname safety. Unrelated non-UTF-8 paths are eligible and remain unexported.
Admitted source paths require canonical UTF-8 and safe relative paths. Missing
required inputs or empty globs reject. Selected symlinks, gitlinks, unsupported
modes, unsafe names, `__pycache__`, and `.pyc` inputs reject before export.

Output paths are lexically absolute and may be inside the checkout. Before
creation or chmod, the controller discovers Git and common directories and
protects a lossless union of selected-tree, current-HEAD, and index pathnames.
Current metadata is write-safety input only; no current file bodies or index
blobs supply preparation content or identity. A positively absent checkout HEAD
does not require a fabricated inventory. A bare store has no checkout/index
inventory. Required metadata read failures reject rather than emptying the
protected set.

Every planned ancestor creation or permission change, and both
`preparations/` and `invocations/` write roots, must be disjoint from protected
paths, running tools, and Git administration. Symlink and non-directory output
components reject. An existing root enclosing the repository or protected
paths is eligible only when it is already same-user-owned and mode `0700`,
needs no mutation, and its write roots remain disjoint. The controller never
changes repository or enclosing-directory permissions to admit output.

## Preparation identity and artifacts

The `binding` object has exactly `schema`, `source_commit`, `object_format`,
and `tools`. Its schema is
`provingkit.feedback-response-preparation.binding.v1`; `source_commit` is
`COMMIT`; `object_format` is `sha1` or `sha256`. Each tool role in the table
above has exactly `{path, oid, sha256}`, binding the committed blob and its
`sha256:<lowercase hex>` byte digest.

`preparation_id` is the lowercase SHA-256 of
`evidence_transport.canonical_bytes(binding)`: JSON with sorted keys, separators
`(',', ':')`, UTF-8, and `ensure_ascii=False`. The identity excludes local
paths, times, runtime versions, and current checkout/index metadata.

```text
preparations/<preparation_id>/preparation.json
preparations/<preparation_id>/source/<declared path>
preparations/<preparation_id>/requests/<request digest hex>.request
preparations/<preparation_id>/grading/cases.json
invocations/<uuid4 hex>/started.json
invocations/<uuid4 hex>/outcome.json
```

Every artifact reference has `{relpath, sha256, byte_count}`, relative to
`PRIVATE_DIRECTORY`, validated as a safe relative path. Requests contain exact
constructor bytes without a trailing newline. JSON documents use
`json_file_bytes`, canonical JSON plus one newline. Requests are deduplicated
by exact bytes, preserving all coordinates. A digest address with different
bytes is a collision. Source count `N`, unique request count `U`, and the
`N + U + 1` artifact count are derived from the selected inputs.

The record has the following fields:

| Field | Contents |
| --- | --- |
| `schema`, `schema_version` | `provingkit.feedback-response-preparation`, `1` |
| `preparation_id`, `binding`, `tree_oid` | The identity, its binding, and the selected commit's tree OID |
| `source` | `root_relpath`; `declaration` with ordered `candidate_paths`, `manifest`, sorted `case_files`, `source_globs`, and sorted `glob_matches` per glob; `inventory` keyed by declared path, with committed `mode`, `oid`, and the artifact reference |
| `corpus` | `path`, `oid`, `sha256`, `skill_name`, and `case_ids` |
| `slots` | `count: 78`, `case_ids: [0..12]`, `variants: [with_skill, without_skill]`, `repetitions: [1,2,3]`, and `entries` |
| `requests` | Keyed by `sha256:<hex>`, with `relpath`, `byte_count`, and `slot_count` |
| `grading` | Artifact reference, `constructor` binding, and `requires_at_grading_time: [response, response_sha256]` |
| `artifacts` | The complete source, unique request, and grading references, ordered by relative path |
| `actor_content_policy` | `request_fields: [prompt, fixture, candidate_bundle]` and `excluded_from_actor_content` listing the exclusions in the source and payload contract |
| `authority` | `kind: preparation_only`, empty `claims`, and `excluded: [actor_execution, grader_execution, attempt_reservation, provider_call, qualification, release, durability_certification]` |

Each slot has `case_id`, `variant`, `repetition`, `state: unstarted`,
`request_sha256`, `request_byte_count`, `request_relpath`, `fixture_paths`, and
`candidate_bundle_paths`. Entries are ordered by case ID, variant with
`with_skill` first, then repetition. Bundle paths preserve the contract order;
baseline bundle paths are empty.

The grading document's schema is
`provingkit.feedback-response-preparation.grading`. Its `cases` maps string case
IDs to exact `expected_output` and `expectations`. Each expectation has
`id: case-<id>-expectation-<one-based index>`, the corpus's exact `text`, and
`severity: safety`. `grading_constructor`, also recorded as the grading
reference's `constructor`, has the constructor `path`,
`function: grading_request`, and the admitted constructor's `sha256`.

Every source, slot, request, and grading reference must agree with exactly one
`artifacts` entry in path, digest, and byte count. Inventory modes are Git
`100644` or `100755`; retained source modes are respectively `0600` or `0700`.
Each request-index key supplies the request digest; its path and byte count
must match that artifact and every referring slot. Its `slot_count` equals
the number of referring coordinates. The artifact list contains exactly the
independently derived source, unique request, and grading set, with no extra
or duplicate entries.

## Preparation procedure and recovery

1. Parse arguments; capture and admit tools, commit, and actual required
   capabilities; establish output write safety; derive the binding and ID.
2. Prepare the private output root and allocate a fresh invocation directory.
   Sync its parent directory after allocation to retain the new UUID entry.
   Freeze `started.json` before export. Strictly parse the committed corpus and
   require 13 unique integer IDs, 0–12. Establish the declared inventory.
3. Read each blob through the admitted Git adapter and recompute its Git OID.
   Publish source using the controller's mode-aware no-replace publisher.
   Existing files must have both exact bytes and the mapped mode. The
   publisher never chmods, unlinks, or replaces a reused final file.
4. For new source files, write an exclusive temporary sibling, apply mode on
   its owned descriptor, flush and fsync, then hard-link without replacement.
   Validate a race winner by bytes and mode. Remove only the invocation's own
   temporary and sync its parent before construction reads the export.
5. Walk the entire export through guarded directory handles without following
   links. Require exactly the declared regular files and their necessary
   ancestor directories, including hidden entries. Preserve and reject any
   unexpected file, empty directory, symlink, special entry, or earlier
   temporary without reading its body. Then independently require constructor
   `source_paths` equality with the committed inventory.
6. Construct all 78 slots through `executor_request`; enforce the actor
   content policy. Freeze unique requests and grading dependencies outside the
   source tree using `frozen_no_replace_write`.
7. Reread and verify every artifact's bytes, digest, and length, and every
   source file's mapped mode. Sync files and directories, including reuse.
   Repeat exhaustive export closure before the record pre-check.
8. Pre-check the record path: absent or a regular file with identical bytes.
   Freeze `preparation.json` last among preparation artifacts, then verify and
   sync its file descriptor and parent directory, including same-byte reuse.
   Check that the verified descriptor still corresponds to the final path.
9. Freeze `outcome.json` as the last controller file write. Emit those same
   bytes on stdout, flush, and exit. The invoker retains the actual result.

An existing same-byte preparation is reverified and synced through the entire
procedure under a new invocation ID. Changed material or tools produce a new
binding and preserve earlier preparations. A wrong-mode export, collision, or
unexpected entry remains untouched. Use a clean output root or a separately
authorized recovery procedure; preparation performs no recovery cleanup of
earlier evidence.

## Process outcomes and diagnostics

Successful stdout is exactly one UTF-8 JSON outcome document; stderr is silent.
Handled failures emit the same document shape and `error:` diagnostics on
stderr, each with `{code, stage, message, remedy}`. Payloads, raw Git stderr,
and tracebacks are excluded from handled diagnostics. Argparse help is offline;
usage errors exit `2` with empty stdout.

| Status | Boundary | Exit |
| --- | --- | --- |
| `complete` | Preparation verified and outcome retained | `0` |
| `rejected` | Failure through inventory, before this invocation retains preparation artifacts | `2` |
| `incomplete` | Export through artifact verification, or a record pre-check collision | `1` |
| `indeterminate` | Any failure once record publication starts, including outcome publication | `1` |

Stages are `arguments`, `tool_capture`, `tool_bootstrap`, `repository`,
`revision`, `tools`, `output_directory`, `invocation_allocation`, `inventory`,
`export`, `constructor_verification`, `payload_construction`,
`artifact_publication`, `artifact_verification`, `record_publication`,
`record_verification`, and `outcome_publication`. JSON status carries the
classification; record visibility is only an observation.

The closed diagnostic codes are `tool-source-missing`, `tool-source-mismatch`,
`tool-source-unsafe`, `tool-bootstrap-mismatch`, `revision-not-full-oid`,
`revision-unresolvable`, `unsafe-git-configuration`, `unsupported-runtime`,
`required-capability-unavailable`, `declared-input-missing`,
`declared-input-unsafe`, `declared-input-unexpected`, `corpus-shape-mismatch`,
`constructor-inventory-mismatch`, `actor-content-policy-violation`,
`unsafe-output-overlap`, `unsafe-output-root-permissions`,
`unsafe-output-directory`, `invocation-allocation-failed`,
`git-operation-failed`, `export-mismatch`, `export-mode-mismatch`,
`export-publication-failed`, `export-closure-mismatch`, `artifact-collision`,
`artifact-verification-failed`, `record-collision`, `record-publication-failed`,
`outcome-publication-failed`, and `outcome-emission-failed`.

## Invocation evidence and consumer acceptance

Invocation path and argv values always use
`{"encoding":"posix-bytes-hex","hex":"<lowercase even-length hex>"}`,
including ASCII paths and empty argv elements. Reverse by checking those exact
keys and literal, validating canonical hex, then `bytes.fromhex`; use
`os.fsdecode` for filesystem APIs. Human-readable diagnostic paths are literal
`json.dumps(os.fsdecode(raw), ensure_ascii=True)` display text, including its
quotes and backslashes. This keeps metadata JSON valid UTF-8 while preserving
POSIX bytes. These encodings never enter actor content or deterministic source
bindings.

`started.json` has `schema`, `invocation_id`, `started_at`, encoded `command`
argv, encoded `repository`, `source_revision`, encoded `output_dir`,
`python_version`, `git_version`, and `controller_sha256`. Its schema is
`provingkit.feedback-response-preparation.started.v1`.

`outcome.json` has `schema`, `invocation_id`, `status`,
`intended_exit_status`, `started_at`, `finished_at`, `stage_reached`,
`diagnostics`, `preparation_id`, `preparation_relpath`,
`preparation_sha256` (or null), `record_observed`, `published_relpaths`, and
`reused_relpaths`. Its schema is
`provingkit.feedback-response-preparation.outcome.v1`. Rejection before
allocation has no retained invocation record. An outcome is written before
process completion and cannot establish stdout emission or interpreter exit.

The invoker retains `{argv, returncode, stdout_sha256, stdout_byte_count,
stderr_sha256, stderr_byte_count, observed_by}` with encoded argv and the
actual streams. `observed_by` is an observer label; any observer or sink path
is encoded separately. With an intentionally non-captured failure sink, record
stdout capture as unavailable, digest and count as null, and the sink setup.
Never invent empty stdout. The tests retain this as `process-result.json`.

Accept through one named invocation only when:

1. `started.json`, `outcome.json`, and the invoker's observed process result
   are present. The outcome says `complete`, observed exit is zero, and
   observed stdout equals the outcome bytes exactly.
2. The record digest matches `preparation_sha256`. Recomputing its binding
   yields its preparation ID and directory name, and the binding matches the
   commit and tools expected by the consumer's reviewed procedure revision.
3. Every artifact resolves safely under the same root, without symlinks, with
   matching bytes, digest, and length. Compare each source inventory OID and
   mode with independently obtained selected-commit tree metadata, then derive
   the expected private mode from that committed mode. Exhaustive traversal
   finds exactly the source inventory files and
   ancestor directories; constructor glob equality alone is insufficient.
4. All 78 distinct ordered coordinates reference listed requests; each
   request-index digest, path, byte count, and coordinate multiplicity agrees
   with its artifact and slots. Globs and source inventory agree with the
   selected commit's declarations. Grading references, constructor identity,
   and required future inputs agree with the artifact list and independently
   verified grading bytes. The consumer may also recompute requests through
   the bound constructor. The preparation tree contains only those artifacts,
   the record, and their necessary directories.
5. The consumer retains its loaded procedure revision, invocation ID, both
   evidence-file digests, and the observed process result.

A missing outcome or process result, signal, nonzero exit, absent/truncated/
mismatched stdout, or known incomplete or indeterminate outcome makes that
invocation indeterminate for acceptance, even if every artifact verifies.
Run a fresh observed preparation with the same inputs for new usable evidence;
earlier invocations remain unchanged.

After retaining an outcome, stdout write or flush failure emits
`outcome-emission-failed` on stderr when possible and exits `1`. Descriptor 1
is redirected to `/dev/null` after failure to prevent a shutdown flush failure.
The already retained outcome is immutable and can still say `complete` with
intended exit zero; the observed disagreement prevents acceptance.

The public tests exercise a pipe whose reader is closed before child launch.
Missing-outcome and withheld-process-result cases construct unavailable
evidence from a completed run. They do not claim to interrupt the window
between record publication and outcome publication. Mode/fsync exception paths
that cannot be deterministically driven through the public seam remain source
review coverage; no fault-injection option or private-helper test seam is part
of this interface.

The test-side verifier derives the entire expected preparation from independent
selected-commit tree metadata and blobs, then compiles the bound constructor
separately and constructs requests against a clean oracle export. Baseline,
growth, deduplication, reuse, real-corpus, and consumer checks use this same
complete-contract verifier. Known incomplete-publication controls verify the
references and retained artifacts without asserting a complete tree.
Negative controls construct changed records with matching enclosing record
digests, retained outcome bytes, and supplied process envelopes. They check
that broken contract relationships still prevent acceptance; these envelopes
are constructed inputs, not observed process results. The original subprocess
captures remain unchanged.
