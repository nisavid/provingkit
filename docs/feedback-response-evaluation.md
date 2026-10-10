# Feedback-response evaluation preparation

The preparation controller will retain private actor requests for the
feedback-response evaluation, bound to source from an immutable Git commit.
It will let a later execution consumer verify the complete preparation before
using any payload.

This is the initialization specification for that controller. The requirements
and acceptance checks below describe intended behavior. They do not report an
implemented command, a completed preparation, or behavioral qualification.
Implementation follows independent review of this specification, Ivan's assent,
and its documentation merge.

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

Tests will invoke this command as a separate process and observe its result,
public output, and retained artifacts. They will not call private controller
helpers or inspect internal state. A process result alone cannot establish
complete preparation: the consumer must verify the manifest and every artifact
it references.

The public artifact contract below specifies the information and byte
relationships that must be retained. The implementation proposal must settle
the public manifest locator and serialized schema, referenced-artifact
addressing, and process result and diagnostic contract before tests depend on
them. Resolve those choices through this same reviewed contract. A change to
the selected command or its acceptance requirements must return for interface
confirmation before tests are written.

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
   publishing the preparation manifest.

The selected evaluation has 13 original case IDs, 0–12, with repetitions 1–3
for each of `with_skill` and `without_skill`: 78 unstarted actor slots. Case,
variant, and repetition coordinates belong in the private manifest. Repeated
slots may have identical request bytes; their distinct coordinates must remain
represented.

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
- Every artifact referenced by the preparation manifest.

[`scripts/evidence_transport.py`](../scripts/evidence_transport.py) supplies
existing Git, safe-path, and immutable-write primitives. The controller should
reuse `run_candidate_git` for narrowly declared read-only Git operations and
`frozen_no_replace_write` for retained artifacts. Its
`candidate_content_identity` inventories tracked and unignored working-tree
material, so it does not establish the selected commit's export.

The preparation manifest must be published last, after every referenced
artifact is retained and verified. Publishing one file atomically does not
make the complete preparation a transaction. The implementation must establish
the ordering and completeness of the multi-artifact result through the public
command's acceptance checks.

An existing artifact with the same bytes may be reused. A different-byte
collision must fail without replacing the artifact. On interrupted or failed
publication, preserve already published artifacts and report incomplete or
indeterminate preparation, including when failure follows a durable file
publication. A consumer must verify all referenced bytes before accepting a
manifest; neither an exit status nor the manifest's presence is sufficient.

A preparation remains bound to its original inputs. A changed material
dependency requires a newly bound preparation, with earlier artifacts
preserved. Preparation made before a runtime-dependent candidate is final
remains provisional for that candidate; it cannot be relabeled as final
evidence.

## Acceptance through the public command

The later test module is `tests/test_feedback_response_eval.py`. These are
required observations for its agreed subprocess boundary, not test results:

| Required observation | Acceptance evidence |
| --- | --- |
| Preparation uses the named immutable commit. | Exported bytes and modes correspond to that commit's declared inputs; live and untracked source material cannot contaminate the result. |
| Every actor slot is prepared without starting it. | The complete 78-coordinate inventory and referenced payload bytes match the maintained constructor, with the ordered three-file candidate bundle and empty baseline. Private coordinates and grading material are absent from added actor content. |
| Publication cannot expose a false complete preparation. | The manifest is published only after all referenced artifacts. An interrupted or partial publication cannot be accepted as complete. |
| Existing evidence remains immutable. | Same-byte reuse preserves artifacts. Different-byte collisions reject the preparation without replacement or a false complete result. |

The tests must retain the observed subprocess result and inspect the complete
manifest and referenced artifacts. They must exercise failure and reuse
behavior through the same public boundary. These checks do not establish
provider-session isolation, tool enforcement, actual served model, exchange
capture, grading truth, response-runtime reconciliation, or qualification.

## Implementation and consumer prerequisites

The reserved implementation surface consists of
`scripts/run_feedback_response_eval.py`,
`tests/test_feedback_response_eval.py`, and this document. Initialization
changes this document only. It does not change the maintained constructors,
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
that revision and the preparation's bound inputs, and verify the manifest and
referenced bytes before use. Final runtime-dependent evaluation preparation
also requires disposition of findings that affect its runtime candidate and
fresh binding after any repair. Actor or grader execution needs its separately
reviewed payload and transport contract, applicable execution authority, and
actual observations. This initialization supplies none of those execution or
qualification results.
