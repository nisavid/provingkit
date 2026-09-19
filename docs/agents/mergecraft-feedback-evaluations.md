# Refresh Mergecraft feedback observations

Use `scripts/feedback_response_evals.py` to prepare, record, and assemble fresh
supplied-instruction observations for `interacting-with-pr-review-feedback`.
Load this procedure when its delivered instructions, corpus, fixtures, grading
protocol, or recording method changes, or when resuming a prepared batch. Use
`capturing-agent-procedures` when changing or consuming the method.

Ordinary PR replies and response-runtime repairs do not invoke this evaluation
procedure. Markdown-writer and Issue–PR relation evaluations use the
[writing evaluation procedure](mergecraft-writing-evaluations.md). Native skill
discovery and ordinary receipts retain their own methods.

The helper launches no provider. It binds declared inputs and atomically admits
observations from a separately reviewed runner. Its checks establish local
serialization, byte correspondence, and uniqueness of declared session labels;
they do not authenticate a provider, prove containment, or demonstrate native
skill invocation. Instructions supplied as strings support an instruction
application claim.

## Order the source and evidence

The feedback experiment lives inside `plugins/mergecraft`. Its final bytes affect
the member content lock and the later ordinary-receipt source snapshot. The
relation experiment's external-output ordering does not apply here.

1. Complete reviewed composition and establish the feedback source/method
   checkpoint, **F**, through the owning workflow. Resolve all result-bearing
   README edits before F. This method binds the entire README and uses stable
   contract text for feedback; it adds no result claim to that file after runs.
   Record F's exact inventory and the checkpoint identity actually established.
   The helper's byte inventory does not establish a Git commit or ordinary S.
2. Prepare against F, record the actual fresh executions and independent grades,
   and assemble the private schema-2 experiment with its provenance sidecar.
   Keep every evaluated input and method identity unchanged. A later README,
   rubric, source, or method correction requires a new preparation and runs.
3. Have the integration owner apply the reviewed experiment bytes and verify them
   with the owning validator. The experiment is the output of this method and
   is outside its evaluated source inventory. Preserve F, raw records, failed
   attempts, grades, historical context, and the assembled identities.
4. Prepare final member locks and any resulting Kit definition identity changes
   through their owning workflows, then establish the committed ordinary source
   **S** with those final experiment and identity bytes. If identity preparation
   changes any F-bound input, return to step 1; do not omit that dependency.
5. Resolve the selected ordinary descriptor and snapshot at S. Fresh receipt
   observations use that snapshot. Reconciliation of earlier observations uses
   the separate receipt procedure: preserve the original recorded revision or
   explicitly recorded null, supported raw records, delivered inputs, rubric,
   model bases, grading lineage, and discovery limits. S is never backdated onto
   an earlier run. This importer alone establishes no receipt eligibility.

Use `checkpointing-and-publishing-git-work` for any Git checkpoint or publication.
The package's documented `--prepare-content-lock` mode permits stale behavior
evidence only as unqualified source preparation; normal and source-stage checks
still check evidence. It is no exception to a required commit/checkpoint gate.
If the owning policy requires a check that needs fresh results before F can be
committed, return that exact check and ordering conflict to the owner before
choosing an exception. A private byte checkpoint or prepared lock is not a
qualified commit, and this procedure grants no checkpoint-policy override.

## Establish the inputs

1. Load the [package contract](../../plugins/mergecraft/README.md) and identify the
   reviewed source and method revisions. Resolve source composition and rubric
   decisions before preparing. PR #84 consumes qualified PR #114 writing source;
   a held writing copy or a missing `threaded-conversation.md` is an incomplete
   input. The writing owner accepts the case-3 wording, and the feedback owner
   retains its response expectations and thresholds.
2. Check the complete closure enumerated by `source_paths` in
   `scripts/validate_feedback_response_evidence.py`:
   - `CANDIDATE_PATHS` supplies eight ordered instruction files: the feedback
     skill and its interaction-authority, GitHub Markdown, and review-voice
     references, followed by the Proseweaving writing skill and its edit-pass,
     evidence-in-prose, and threaded-conversation references.
   - `PROVENANCE_PATHS` binds five additional inputs: the shared review voice,
     the Markdown writer's review voice and authoring contract, and both
     plugins' topologies. These are provenance inputs, not duplicate delivery.
   - `METHOD_PATHS` binds the validator, helper, both test suites, this procedure,
     and the package README. The existing corpus, scenario fixtures, response
     scripts, feedback-acquisition helper, and both response test/fixture
     collections remain in the closure.
3. Retain the exact predecessor document, every additional excluded experiment,
   and any historical context files. Supply the original `before-final-fix.json`
   and its provenance limitation note as historical context: retained request
   strings were rewritten without fresh responses or grades. An old-source
   correspondence pass does not establish authentic execution. Context files
   stay unselected in the private provenance sidecar.
4. Have the owning workflow classify the actual executor, grader, and runner
   review, resolve the route and applicable authority, and approve its complete
   input inventory. Record the resulting dispatch contract below. A route name,
   model declaration, or fixed rubric `safety` label does not settle those gates.
   Existing protected-work model requirements remain with their owner.

The dispatch JSON has exactly these fields; angle-bracket values below are
placeholders, not defaults:

```json
{
  "schema_version": 1,
  "route": "<reviewed route description>",
  "model": "<reviewed model>",
  "reasoning_effort": "<reviewed effort>",
  "executor_instructions": "<exact executor wrapper>",
  "grader_instructions": "<exact independent grader wrapper>",
  "method_files": [
    {"label": "runner", "path": "<absolute path to reviewed runner>"}
  ]
}
```

Use nonempty strings, unique file labels, and actual absolute file paths in the
private dispatch document. The single-file example is sufficient only when it
is the complete reviewed inventory. Include the actual runner/grader executable
identities, wrappers, configuration, transport/response parsers, and every other
file the owning runner review requires. The helper binds their bytes and modes;
it cannot establish inventory completeness from declarations. Both roles use
the same declared model and effort. There is no default or substitution path.

## Prepare and verify

From the candidate repository, choose a new private output directory outside
that repository. Include each additional experiment and each historical context
file through its own repeated option:

```sh
python scripts/feedback_response_evals.py prepare \
  --repo "$candidate_checkout" --output "$evaluation_directory" \
  --dispatch "$reviewed_dispatch" \
  --additional-experiment "$excluded_experiment" \
  --historical-context "$before_final_fix_document" \
  --historical-context "$history_limitation_note"
python scripts/feedback_response_evals.py verify \
  --repo "$candidate_checkout" --evaluation "$evaluation_directory"
```

Omit optional arguments only when there is no corresponding input. Preparation
refuses an existing directory or missing source. Review `preparation.json` and
retain its returned SHA-256 with the source/method revision and runner review.
Check the complete source inventory, delivery order, corpus, expectation policy,
history, and dispatch. Source, mode, predecessor, context, dispatch, or method
changes stale preparation; preserve that directory and prepare a new reviewed
batch. A successful `verify` makes no observations and leaves evidence unchanged.

The current 13 cases and 64 expectations require three repetitions in each of
`with_skill` and `without_skill`: 78 executions, each with an independent grade,
using 156 fresh role sessions. All 192 candidate judgments must pass. Baseline
failures remain comparison results and do not lower that threshold.

## Deliver and record each coordinate

Generate an execution packet for an explicit case, condition, and repetition:

```sh
python scripts/feedback_response_evals.py packet \
  --repo "$candidate_checkout" --evaluation "$evaluation_directory" \
  --case 3 --variant with_skill --repetition 1 --role execution \
  > "$execution_packet"
```

The result is `{"packet": {...}, "sha256": "..."}`. The packet binds the
preparation digest, `case_id`, `variant`, `repetition`, `role`, model, effort,
role instructions, and canonical request string. The execution request contains
only `prompt`, `fixture` as raw strings, and `candidate_bundle` as ordered raw
instruction strings; the control bundle is empty. Expected output and rubric
belong only to grading.

The reviewed runner delivers the packet's exact role instructions and request.
Immediately before launch, obtain and retain the evaluation's current session
state and its SHA-256:

```sh
python scripts/feedback_response_evals.py session-state \
  --repo "$candidate_checkout" --evaluation "$evaluation_directory" \
  > "$execution_session_state"
```

The closed state binds the preparation, sorted historical exclusions, and every
accepted current record's coordinate, session label, packet, observation, and
raw-record identity. Capture the original raw outcome and truthfully normalize
that outcome. Use a fresh session for every role and coordinate. Retain the raw
record before any normalization; a normalized declaration alone cannot show
what the runner sent or received. The normalized JSON has exactly these fields:

```json
{
  "packet_sha256": "<returned packet digest>",
  "session_id": "<observed session label>",
  "model": "<observed model>",
  "reasoning_effort": "<observed effort>",
  "turn_status": "<observed completion status>",
  "request": "<exact canonical request string>",
  "response": "<exact response string>",
  "tool_events": []
}
```

Record actual tool events when present; the empty array depicts an observation
eligible for selection. Missing protocol facts stay missing and make an attempt
ineligible rather than becoming inferred successes. Import the two original files:

```sh
python scripts/feedback_response_evals.py record \
  --repo "$candidate_checkout" --evaluation "$evaluation_directory" \
  --case 3 --variant with_skill --repetition 1 --role execution \
  --observation "$execution_observation" --raw-record "$execution_raw_record" \
  --session-state-sha256 "$execution_session_state_sha256"
python scripts/feedback_response_evals.py packet \
  --repo "$candidate_checkout" --evaluation "$evaluation_directory" \
  --case 3 --variant with_skill --repetition 1 --role grading \
  > "$grading_packet"
```

The grading packet derives its request from the recorded execution, including
the exact response and its digest, expected output, and fixed expectation list.
Give it to an independent fresh grader session without prior grades or a desired
verdict. The grader returns one JSON object whose sole key is `expectations`.
Its value is an array with one object per supplied expectation in order: `id`,
Boolean `passed`, and nonempty `evidence`.
Keep that exact response in its observation and import it with the same `record`
command using `--role grading`, the grading observation/raw-record paths, and the
session-state SHA retained immediately before the grading launch.

Only a successful `record` return is local admission. Retain `record_sha256` and
both returned session-state identities, then emit the runner's completed outcome.
The runner owns this import; its caller must not import the coordinate again or
maintain a second session registry.

Under one evaluation-scoped lock, `record` reverifies preparation and complete
record state, reserves the coordinate, retains the submitted observation, raw
record, and packet, then checks the launch-time state identity and session label.
A stale state, historical or current label reuse, malformed observation, or
empty supplied raw record writes `rejection.json`, creates no `record.json`, and
leaves that coordinate unavailable. Subsequent state reads fail closed for owner
handoff. Missing or unreadable observation or raw-record input files fail before
reservation and leave the coordinate unchanged. Failed, rejected, interrupted,
or terminal-output attempts create no retry authority. Preserve the attempt and
return any recovery or selection proposal to the method owner.

The same nonblocking lock covers state reads, grading-packet construction, and
assembly. A busy or crash-left marker fails closed and remains owner-recoverable;
never delete it by age or infer liveness. Unknown, rejected, partial, drifted,
malformed, or aliased record paths also fail closed. Distinct serial imports must
refresh state immediately before each launch. Repeat the protocol for all planned
coordinates under the unchanged preparation.

## Assemble and hand off

```sh
python scripts/feedback_response_evals.py assemble \
  --repo "$candidate_checkout" --evaluation "$evaluation_directory" \
  --output "$private_evidence"
```

Assembly requires all 78 execution/grade pairs, current prepared inputs, and the
validator's closed schema-2 record, history, and threshold checks. Selected
observations require distinct nonempty session labels, matching declared model
and effort, completed nonempty responses, no tool events, and exact request,
response, and grade bindings. A malformed, incomplete, drifted, or failing
candidate remains unqualified. Keep its artifacts and findings; changing a
grade or replacing a failed observation does not repair it.

Keep the new evidence and its `.provenance.json` sidecar outside the repository.
The sidecar retains preparation/evidence digests, each role's packet, normalized
observation and raw-record digests, and historical context. Preserve
the evaluation directory, including each imported record's byte bindings and
raw outcome, with it for review. Publish only through the owning integration
workflow after its disclosure review.

The existing history envelope retains exact predecessor/additional-document
bytes, their digests, exclusions, and recorded availability. It accepts the
closed schema-1 predecessor and closed schema-2 predecessor, carries normalized
history forward, and excludes formerly selected records. Unsupported schemas,
malformed documents, and duplicate/orphan historical grading coordinates fail.
Neither request equality nor a historical pass makes retained executions or
grades selectable. This is retention of declared documents, not a census of
all model activity.

Before accepting a method revision, run its focused suites:

```sh
python -m unittest discover -s tests -p 'test_feedback_response_evidence.py'
python -m unittest discover -s tests -p 'test_feedback_response_evals.py'
```

Synthetic tests establish local preparation, state identity, serialized import,
drift, rejection retention, grading exclusion, and assembly behavior. These
checks assume cooperative local processes and detect later filesystem tampering;
they do not contain a hostile same-account writer or prove provider independence.
Exercise discovery with refresh/resume requests and
neighboring ordinary-reply/runtime-repair requests; exercise successful, failed,
and unchanged-input branches. Record unavailable application evidence as a
missing gate. Method review and local tests supply neither fresh model
observations nor a qualified launch route.

PR #84 and the later #10 consumer load this same reviewed procedure revision
before dependent work and report the source/method bindings, current evidence,
and missing gates. The broader #10 repair and global #33 rollout are not
prerequisites for this narrow evaluation. If a consumer requires an ordinary
receipt, its owner establishes committed source S, receipt schema, descriptor,
maps, and processor bindings through the
[receipt procedure](../behavior-eval-receipts.md).

Completion requires clean reviews on the final method revision, truthful fresh
observations of the final source, complete independent grades, exact retained
history, and passing owning validation. Integration, content locks, receipts,
publication, and installation remain their owners' steps. Report each pending
gate explicitly; a private prepared or assembled artifact does not complete it.
