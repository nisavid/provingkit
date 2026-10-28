# Feedback-response evaluation preparation

The preparation controller retains private actor requests for the
feedback-response evaluation, bound to source from an immutable Git commit.
It prepares no model execution or grading result. A later execution consumer
must verify the complete preparation and its observed invocation outcome before
using any payload.

This procedure owns preparation only. Passing subprocess tests establish the
preparation contract; they do not qualify the feedback-response runtime or
refresh its retained behavioral evidence.

## Public preparation interface

The selected command and test boundary are:

```text
python scripts/run_feedback_response_eval.py prepare --repository REPOSITORY --source-revision COMMIT --output-dir PRIVATE_DIRECTORY
```

`REPOSITORY` supplies the Git objects for the selected immutable `COMMIT`,
expressed as its complete lowercase hexadecimal commit object ID.
`PRIVATE_DIRECTORY` retains the preparation artifacts outside the isolated
source export. The controller must bind the selected commit and the exact
source bytes and modes it uses; live working-tree changes and untracked files
must not become preparation inputs.

Tests will invoke this command as a separate process and observe its result,
public output, and retained artifacts. They will not call private controller
helpers or inspect internal state. A process result alone cannot establish
complete preparation: the consumer must verify the preparation record and
every artifact it references.

The schema and process contract below are the public consumer boundary. Changes
to that boundary require review together with its subprocess acceptance tests.

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
   construction. The controller enumerates the committed tree, reads its corpus,
   selects its declared paths, and verifies every archived file against its Git
   blob ID and executable mode. Archive attributes that omit or rewrite an input
   fail this comparison. Keep generated artifacts outside that tree.
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

The controller and its maintained constructor, storage helper, and this
procedure are processing inputs from the running checkout. Their exact bytes
are retained separately from evaluated source; they are not represented as
files from the selected commit. Preparation fails if these observed processing
bytes change before publication. This uses trusted local Python and assumes no
concurrent processing-source edits; byte identities are not code attestation.

### Record and invocation schema

`PRIVATE_DIRECTORY/preparation.json` is canonical JSON followed by one newline.
Its schema-version-1 fields are:

| Field | Meaning |
| --- | --- |
| `kind` | `feedback-response-preparation` |
| `preparation_id` | Lowercase SHA-256 of canonical record JSON with this field omitted |
| `source` | Selected `commit`, `tree`, and `files`; each file binds its original `path`, `git_blob_id`, `git_mode`, and retained `artifact` |
| `processing.files` | Original processing paths and their retained byte references |
| `candidate_paths` | The maintained ordered three-file candidate bundle |
| `slots` | Exactly 78 `{case_id, variant, repetition, state: unstarted, request}` rows |
| `grading_dependencies` | A retained artifact containing each original expected output and the maintained safety expectations; it is not a grader request |

Each artifact reference has exactly `path`, `byte_count`, and `sha256`, with a
strictly relative `artifacts/HEX_DIGEST` path. SHA-256 covers exact bytes without
a prefix. Identical content shares an artifact while slot coordinates remain
distinct. Actor artifacts contain exactly the maintained canonical request,
without a terminal newline. Retained files have mode `0600`; original executable
modes are source metadata, not permissions granted to retained artifacts.

Each invocation reserves `invocations/UUID/started.json` before publishing any
payload. After all referenced artifacts are retained and verified, it publishes
the preparation record and rechecks the bytes. Only then does it publish
`invocations/UUID/complete.json`. These invocation files do not become actor
content or part of the preparation ID.

The command prints one JSON invocation result on stdout. Its fields are
`schema_version: 1`, `kind: feedback-response-preparation-invocation`,
`invocation_id`, `status`, `preparation_id`, and `record`. `record` is the same
three-field byte reference pointing to `preparation.json`; it and
`preparation_id` are null if construction did not finish. A failure also has a
`reason`. Exit zero and `status: complete` mean publication and all checks
completed for that invocation; exit one means `incomplete` before the record
publication boundary, or `indeterminate` once that boundary may have been
crossed. Argument errors retain argparse's exit-two diagnostic.

The start and complete files contain this result with `status: started` and
`status: complete`, respectively. An observed publication failure attempts to
retain `failed.json` without replacing anything. That extra diagnostic cannot
be promised when storage itself fails. A surviving start without a complete
result, a failure marker, or contradictory invocation history blocks reuse;
use a new private directory. A known failed or unavailable actual subprocess
outcome still takes precedence over a visible complete file.

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

An existing artifact with the same bytes may be reused. A different-byte
collision must fail without replacing the artifact. On interrupted or failed
publication, preserve already published artifacts and report incomplete or
indeterminate preparation, including when failure follows a durable file
publication. A consumer must verify all referenced bytes before accepting a
preparation record; neither an exit status nor the record's presence is
sufficient.

The caller must retain the actual subprocess return code and exact stdout and
stderr bytes outside the prepared artifacts, paired with the invocation ID in
stdout. The producer's completion file cannot attest its own process outcome.
Accept only a captured zero exit and complete result whose record digest and
preparation ID match the retained record. A nonzero, missing, interrupted, or
contradictory capture leaves that invocation incomplete or indeterminate even
if every referenced byte is present. Preserve known failures; byte verification
or a later reuse must not erase them.

After checking that outcome, the consumer checks every reference's safe path,
size, and digest, the record's preparation ID, all source Git blob/mode
correspondences, processing identities, and all 78 original coordinates. It
reconstructs the source tree from retained inputs and verifies the complete
`source_paths` inventory, exact `executor_request` bytes, ordered candidate
bundle, empty baseline, and private grading dependencies. A consumer running
different construction code must establish the correspondence independently;
the presence of a preparation record is not that verification.

A preparation remains bound to its original inputs. A changed material
dependency requires a newly bound preparation, with earlier artifacts
preserved. Preparation made before a runtime-dependent candidate is final
remains provisional for that candidate; it cannot be relabeled as final
evidence.

## Acceptance through the public command

Run the public subprocess acceptance tests with:

```sh
python -m unittest tests.test_feedback_response_eval
```

`tests/test_feedback_response_eval.py` exercises these observations:

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

The preparation implementation consists of
`scripts/run_feedback_response_eval.py`,
`tests/test_feedback_response_eval.py`, and this document. It does not change the maintained constructors,
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
CI discovery of the new test module. The existing Mergecraft CI entrypoint `tests.test_feedback_response_evidence`
loads `tests.test_feedback_response_eval` through the standard unittest
`load_tests` hook; the workflow and its permissions are unchanged. This supplies discovery
configuration, not an observed CI run. A developer-documentation invocation
pointer and actual consumer invocation remain separate work. That skill was unavailable in the
implementation environment; no execution of its workflow or completion of
these separate steps is claimed.

The consuming task must load this procedure at its reviewed revision, record
that revision and the preparation's bound inputs, and verify the preparation
record and referenced bytes, and apply the bound invocation outcome before use.
Final runtime-dependent evaluation preparation also requires disposition of
findings that affect its runtime candidate and fresh binding after any repair.
Actor or grader execution needs its separately reviewed payload and transport
contract, applicable execution authority, and actual observations. Preparation
supplies none of those execution or qualification results.

## Remaining execution contract

A future transport must accept only a verified preparation plus its actual
successful invocation capture. For each unstarted coordinate it must create a
fresh isolated actor session with tools denied by the harness, deliver only the
exact actor request, and retain the raw request, response, session/model/effort
observations, completion status, and complete tool-event trace. Declaring no
tool events is not proof that the harness denied tools.

Only a completed actor response can supply `grading_request`; the independent
grader receives that exact constructor output and a separately reviewed strict
JSON response contract. It also requires a fresh session, denied tools, exact
exchange capture, and observed completion. The consumer must retain every
failed or interrupted execution and grading attempt rather than relabel it as
a fresh success. Only actual observations can supply the 78 execution and 78
grading records required by `validate_feedback_response_evidence.py`.

This increment exposes no execution or grading subcommand. Neither `gh` nor
`codex` was on the initial development `PATH`; later investigation located the
executables at `/workspace/tooling/gh/gh_2.103.2_linux_amd64/bin/gh` and
`/opt/codex/bin/codex`. Finding those binaries does not establish a model
transport with verified tool denial. No such transport was invoked or
qualified. Recheck capabilities when implementing that separate transport
rather than infer them from a CLI name or filesystem sandbox option.
