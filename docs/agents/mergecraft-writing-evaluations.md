# Refresh Mergecraft writing observations

Use `scripts/mergecraft_writing_evals.py` when reviewed Markdown-writer or
Issue–PR relation instruction changes invalidate their supplied-instruction
behavior evidence. The helper freezes the two fixed corpora, runs explicitly
selected coordinates, and assembles response-bound packets for independent
grading. The offline relation projector assembles a new private member-evidence proposal
from explicitly bound originals. The helper does not grade responses or apply
experiments, content locks, or Kit identities.

The preparation, record, and collection interfaces have synthetic executable
tests in `tests/test_mergecraft_writing_evals.py`. A changed execution helper
needs source review and a real provider preflight before its remaining runs.
Synthetic executable tests establish local mechanics only. Record that review
and preflight beside the evaluation; this document does not assert that an
unexecuted candidate helper is a qualified provider route.

For the 33 Codex PR-description applications and their nineteen direct sentinel traces, follow [PR-writing evaluations](mergecraft-pr-writing-evaluations.md), including preparation-time rubric capture and pinned processor reconciliation. The Markdown/relation application procedure remains separate.

## Inputs and scope

Load the [Mergecraft package contract](../../plugins/mergecraft/README.md), the
reviewed instruction source, and each owning corpus policy before preparation.
Use `capturing-agent-procedures` when consuming or changing this method. Keep
source review, model application, native discovery, and publication separate.

The helper prepares exactly these candidate coordinates:

| Corpus | Cases | Repetitions | Executions |
| --- | --- | --- | --- |
| `plugins/mergecraft/skills/writing-github-issue-and-pr-markdown/evals/evals.json` | 8 | 3 | 24 |
| `evals/mergecraft/skills/maintaining-issue-pr-relations/evals.json` | 17 | 3 | 51 |

The executor receives only `prompt`, `fixture`, and `candidate_bundle`.
Expectations and expected output go to `grader-cases.json` and never enter the
request. Paths inside requests are repository-relative. Preparation preserves
source bytes, including fixture newline distinctions, before JSON encoding.

The Markdown bundle contains its skill, authoring contract, review voice, and
Proseweaving entrypoint plus its three routed prose references. Conditional
instructions still determine which policy applies: a format-only task does
not authorize prose rewriting merely because a reference is available.

Each relation bundle adds the relation skill and its two references, publisher
skill, PR writer, body contract, relation ledger, Markdown contract, and change
navigation. It also supplies the case's lifecycle caller and its applicable
continuation/merge references. These cases cover the concrete handoffs and
writing decisions in their fixtures; they do not execute lifecycle helpers,
publication, feedback actuators, review loops, or optional atlas generation.
Revisit the explicit bundle lists when a case or routed procedure changes.

The helper manifest binds every consumed instruction, corpus, fixture, policy,
helper, and executable. Its `candidate_base_commit` identifies preparation
context and `candidate_commit: null` is not the committed evaluated source
required by the ordinary receipt procedure. Keep the helper manifest and receipt
snapshot distinct. Never substitute a new source digest into a retained
execution or grade.

## Prepare and review

Before new receipt-bound observations, the integration owner completes reviewed
source composition and reference projections, then runs:

```sh
python scripts/validate_mergecraft.py "$candidate_checkout" --prepare-content-lock
```

This command checks structure, projections, Atlas correspondence, and runtime
contracts, then writes only the Mergecraft content lock through its guarded
transaction. It permits stale behavior evidence and explicitly reports the
candidate as unqualified. Malformed inputs, stale projections, Atlas drift,
and concurrent source changes still fail. It is a whole-plugin operation and
cannot be combined with `--skill`, `--source-stage`, or another writing mode.
Normal validation and the existing lock writer keep their evidence checks.

The integration owner completes remaining member identity work and commits the
evaluated source, including the reviewed receipt processor. Load the
[ordinary receipt procedure](../behavior-eval-receipts.md), require ready
descriptors for the agreed application and trigger coordinates, and retain its
prepared snapshot before dispatch. Review the prospective recorder's binding
between that snapshot and the helper's actual per-case delivered inputs.
Use the relation receipt commands below to bind the exact preparation before
launch, capture admitted observations, and project independent judgments through
the ordinary producer. A source manifest or successful lock preparation alone
does not supply that binding.

Choose a new task-owned output directory outside the source checkout. Use the
latest available Claude Code unless the operator specifies another version.
Preparation probes the selected executable with `--version`, requires the
`<major>.<minor>.<patch> (Claude Code)` response, and stops the probe after five
seconds. An unrelated executable, malformed response, failed probe, or timeout
stops preparation before it creates the evaluation directory. Record the
observed version and executable digest in the schema-2 helper manifest; do not
pin routine work to a historical client version. The current command requests
`claude-opus-5` with high effort. The ordinary signed-in client supplies
authentication. Do not copy authentication data into the output directory.

```sh
python scripts/mergecraft_writing_evals.py prepare \
  --repo "$candidate_checkout" --output "$evaluation_directory" \
  --claude "$reviewed_claude_executable"
python scripts/mergecraft_writing_evals.py verify \
  --evaluation "$evaluation_directory" --repo "$candidate_checkout"
```

Preparation refuses an existing directory. Review the source map, both corpus
policies, actual executor requests, separate rubric, executable digest, helper
digest, and exact command shape. Retain the manifest's SHA-256 digest in the
execution plan. Source changes require a newly reviewed freeze; an unfinished
old directory remains evidence of the attempted preparation.

Select a small preflight from the planned coordinates, such as Markdown case 1
repetition 1 and relation case 0 repetition 1. The same prepared requests remain
their real coordinates; do not run an extra specimen and substitute its output.

```sh
python scripts/mergecraft_writing_evals.py run \
  --evaluation "$evaluation_directory" --repo "$candidate_checkout" \
  --manifest-sha256 "$reviewed_manifest_sha256" \
  --run-id markdown/case-01-with-skill-1 \
  --run-id relations/case-00-with-skill-1
```

Inspect actual initialization, model metadata, command, no-task-tool records,
result status, response bytes, and session IDs before selecting the remaining
coordinates. Runtime initialization must report the version frozen at
preparation. A newer client requires a fresh executable binding and preflight;
a version change alone does not require an operator decision. No preflight pass
is implied by a requested model name or a
successful process exit. The helper requires one initialization and result,
the expected client/model metadata, empty reported tools/MCP/skills/plugins,
matching initialization, assistant-event, and result session IDs, and a
successful result without decoding errors, parse errors, or tool calls.
The stream is strict UTF-8 NDJSON: LF delimits records; CRLF is also accepted.
Other Unicode characters, including U+2028 and U+2029 inside JSON strings,
remain response content. JSON string escapes preserve embedded CRLF bytes.
Malformed UTF-8 remains in the raw stdout artifact; the record identifies the
decoding failure, leaves the response artifact empty, and rejects collection.
These are observations of the client protocol, not authentication of
the provider's complete prompt, effective effort, or process containment.

The command follows the retained task-local execution method: a fresh UUID and
empty working directory, stream JSON, no session persistence, explicit empty
setting sources/MCP/tools, disabled hooks/auto-memory/plugins/slash commands,
safe mode, and no Chrome. Host authentication and provider-owned context remain
outside this limited observation. Do not claim an isolated baseline or a
general evaluation gate from these controls.

Each `run` invocation accepts only explicit repeated `--run-id` selections.
It checks the frozen manifest, current source, helper, and executable, then runs
up to three processes concurrently with a 240-second timeout per process.
Run directories are create-only. Already launched, interrupted, failed, or
completed coordinates require inspection; the helper never silently retries
or replaces them. Keep any new attempt in a separately reviewed evaluation
directory and preserve the earlier attempt's disposition.

Creating `STOP_LAUNCHES` in the evaluation directory stops later launches while
already running processes finish. A technically invalid result also stops new
launches. The final summary distinguishes completed and unlaunched coordinates.
A stopped, failed, or partial batch returns nonzero and supplies no semantic
pass. Inspect any incomplete directory before further execution.

## Collect and grade

Every run retains its exact request, command, specification, stdout, stderr,
response file, observation record, and empty working directory under `runs/`.
Keep these private task artifacts intact. Raw streams may contain local paths,
thinking blocks, and operational metadata; do not publish them wholesale.

After all three repetitions of a case finish, collect its packet:

```sh
python scripts/mergecraft_writing_evals.py collect \
  --evaluation "$evaluation_directory" --repo "$candidate_checkout" \
  --suite markdown --case 1 --output "$new_grader_packet"
```

Collection checks the original specification, request, command, stream-derived
observations, response bytes, digests, successful completion, and three distinct
sessions. It refuses incomplete, invalid, substituted, or already-written
outputs. It makes no judgment about response quality.

Give independent graders disjoint completed case packets and the owning policy.
Do not provide earlier grades, other graders' answers, or a desired verdict.
Require every exact expectation's Boolean judgment with response-bound evidence
and coverage accounting. Preserve supplementary inaccuracies separately; a
rubric pass does not mean every generated sentence is correct. Markdown uses
its declared severity thresholds; every relation expectation must pass in all
three repetitions. The 75 responses require 72 Markdown and 195 relation
expectation judgments with the current corpora.

## Record prospective relation receipts

The three `receipt-*` commands are offline recorders for the existing 51 relation
applications and 13 native Boolean probes. They do not launch a model, prepare a
native runner, choose source S, or grade a response. Use the existing reviewed
native preparation and collection method. The ordinary processor must be the
reviewed source committed at S, with the recorder and this procedure declared
as freshness dependencies. Every instruction actually delivered to a case must
also be declared as a behavioral input. A union of all consumed files does not
replace each case's delivery record.

Complete plugin Markdown projections and every member lock write before S. The
ordinary snapshot binds the whole Mergecraft lock; changing it before the
receipt-containing commit C invalidates the receipt. The external relation
`experiment.json` and `grading.json` under
`evals/mergecraft/skills/maintaining-issue-pr-relations/` may be projected later
only while absent from the snapshot closure. These commands require that
absence. Keep all private preparations, original observations, grading sources,
and recorder outputs outside the source checkout. Preserve failed attempts;
outputs are create-only.

### Bind before either relation method runs

Obtain the ready descriptor and snapshot through the supported inventory:

```sh
python scripts/behavior_eval_inventory.py --repository "$candidate_checkout" \
  descriptor --revision "$source_revision" \
  --skill mergecraft/maintaining-issue-pr-relations > "$descriptor"
python scripts/behavior_eval_inventory.py --repository "$candidate_checkout" \
  prepare --revision "$source_revision" \
  --skill mergecraft/maintaining-issue-pr-relations > "$snapshot"
```

Prepare the ordinary helper and native method without executing their runs.
Create a private `preparations.json` with `schema_version: 1` and these fields:

| Field | Required binding |
| --- | --- |
| `behavior` | Original helper `manifest.json` reference. |
| `native` | Original native preparation `index.json` reference. |
| `native_method` | Reviewed private native-method source reference. |
| `native_provenance` | Original source-name-to-reference mapping matching the native index's `producer_source_sha256`, including the original runner. |
| `native_format` | Reviewed native format contract reference. |
| `native_format_evidence` | References to its retained metadata and field-shape reports; no original trace transfer is required. |
| `grader_model` | `{id, basis, reference}`, with the selected model ID, `configured`, `requested`, or `reported` basis, and a reference resolving to that exact ID. |

A private reference contains the absolute `path` and lowercase raw-file `sha256`.
JSON value references may add `format: "json"` and a JSON `pointer`; omitted
values mean the entire JSON document. Text references use `format: "utf8"` and
an empty pointer. Keep these references in private sidecars, outside executor
requests and committed evidence.

```sh
python scripts/mergecraft_writing_evals.py receipt-bind \
  --repo "$candidate_checkout" --revision "$source_revision" \
  --descriptor "$descriptor" --snapshot "$snapshot" \
  --preparations "$preparations" --output "$new_binding"
```

Retain the returned binding digest before dispatch. Binding checks committed
source, current bytes and modes, loaded processor/schema, both original
manifests, method equipment, exact requests and separate rubrics, and all absent
run destinations. It records each original run ID, ordered delivered files,
repetition, and corpus coordinate. Application case zero stays zero; native
cases without an ID retain null. The snapshot's canonical digest and its raw
file digest remain separate. Metadata never enters a model-visible prompt.

Dispatch only the agreed coordinates with the existing execution methods. A
changed source, executable, preparation, or private method requires a new
reviewed binding before execution; do not attach one to old observations.

### Observe complete records

Collect all 17 application packets using the existing `collect` command and all
13 native records using their original collector. Create private
`observations.json` with `schema_version: 1`, `application_packets` (17 original
packet references), `native_collection` (the original collector index reference),
and `configuration` (its exact configuration reader/schema evidence reference).

```sh
python scripts/mergecraft_writing_evals.py receipt-observe \
  --binding "$binding" --binding-sha256 "$binding_sha256" \
  --observations "$observations" --output "$new_observation_directory"
```

Observation repeats freshness checks, reconstructs application packets from
original records, and preserves native collector admission. A counted native
true requires one successful target Skill call, its ID-matched result, the
immediately following exact candidate-body injection, subsequent assistant
output, and a complete valid stream. The injection carries no call ID; its
association remains explicitly inferred from position and source correspondence.
A counted false requires a complete valid stream with zero calls, results, and
injections. A final answer such as `NO_SKILL` supplies neither Boolean by itself.

Failed, repeated, parallel, non-target, unmatched, incomplete, or unsupported
records remain uncounted and preserved. Return new event shapes to the method
owner; do not relabel them false or allocate a retry. Supported informational
records are `rate_limit_event` without a subtype and `system` with subtype
`thinking_tokens`. Raw JSONL pointers retain physical LF line indices. The
recorder writes 51 closed execution envelopes, 13 closed Boolean envelopes, and
an `observation-index.json` retaining original-artifact lineage. It preserves
response bytes separately from serialized-envelope digests.

### Project independent judgments and check the member requirement

Create private `grading-references.json` with `schema_version: 1` and 51 `runs`.
Each row names the original `run_id`, a `record` reference, `grader_model` in the
same form as preparation, a `previous_grading` reference list, and `adjudication`
(null or an original source reference). The selected original record uses the
existing relation grade shape: `run_id`, `response_sha256`, `grader_task`,
`grader_distinct_from_executor: true`, and ordered `expectations` containing
exact `text`, Boolean `passed`, and response-bound `evidence`. Optional IDs and
severities must match the accepted descriptor. Preserve original supplementary
findings and superseded judgments in their referenced files. Do not author
replacement original grades to satisfy this interface.

```sh
python scripts/mergecraft_writing_evals.py receipt-results \
  --binding "$binding" --binding-sha256 "$binding_sha256" \
  --observation-index "$observation_index" \
  --observation-index-sha256 "$observation_index_sha256" \
  --grading "$grading_references" --output "$new_results_directory"
```

Finalization rechecks source, preparations, observations, and grading sources.
It maps the 195 original Booleans to the 65 accepted criteria, validates closed
grading/results envelopes, and calls the real ordinary producer. It writes
`results.json`, `receipt.json`, `member-report.json`, and private `lineage.json`
alongside exact observation-envelope copies and 51 grading envelopes. Original
response, runner record, grader packet, original grade, execution envelope, and
grading envelope digests remain distinct.

Exit zero means complete valid projection; inspect `member_passed`. False
grades remain false. Ordinary policy allows quality criteria at 2/3, while the
relation method requires every one of its 56 safety and 9 quality criteria at
3/3, plus all 13 correct native observations. The member report checks each
criterion independently. Neither model IDs nor grader task IDs authenticate
execution or grading; their original declared basis is retained.

The integration owner reviews the public receipt and the separate member
report, retains private lineage, and runs the ordinary receipt procedure through
C. The public producer can independently reproduce the receipt from the prepared
snapshot and `results.json`; the inventory checker then reads the receipt
committed at C and checks S-to-C freshness. Only reviewed public projections go
into source. Local synthetic tests establish these mechanics, not actual S,
provider behavior, native runtime qualification, or a semantic pass.

## Retain historical evidence narrowly

Assess retained observations separately, before integration:

- Preserve every completed evaluation's original manifest, helper bytes,
  client version, commands, records, and source bindings. This helper accepts
  schema-2 manifests only. Reinspect a schema-1 evaluation with its retained
  original helper and source, then record a separate correspondence decision
  for any current consumer. Do not rewrite its manifest or method digest to
  make it pass the new helper. A newly reviewed method does not imply that
  historical runs used it.

- Markdown no-skill controls may remain historical observations only when
  their exact task, fixtures, empty bundle, original configuration claim,
  response bindings, and rubric still hold. Preserve original IDs, timestamps,
  model/client versions, and grades. Different client versions do not support
  a contemporaneous configuration-matched or causal comparison.
- The 13 relation-native observations bind the relation skill, its two supplied
  references, trigger corpus/policy, recorded plugin identity, and actual
  selection configuration. Retain them only when that narrower source and
  configuration claim remains unchanged. Preserve original Skill calls,
  injections, IDs, grades, and limitations. They do not prove current host
  installation discovery or a new native execution. Preserve the generated
  plugin manifest separately; a newly computed digest is not a launch-time
  binding when the original run did not record one.
- Generic Markdown native observations remain historical when their source
  changed. The fresh behavior executions do not refresh them.

The integration owner publishes only reviewed normalized records. Preserve
exact request/response values and raw-file digests while omitting private paths,
thinking blocks, and unrelated telemetry. Record every normalization explicitly.
Keep original failed and superseded evidence rather than editing it to pass.
Reconcile incomplete writes before retrying an integrator.

Completion requires current independent grades, reviewed supplementary
dispositions, complete coverage, truthful retention decisions, and the owning
validators. Content-lock and Kit-identity preparation, integration, commits,
publication, and installation remain their existing owners' steps. Preserve the
receipt snapshot's source and whole-lock bindings through the receipt-containing
candidate; return any necessary input change to the integration owner before
claiming the observations remain current. This helper
does not implement the unavailable schema-v2 evaluation gate or qualify the
separate feedback-response corpus.

## Project completed relation member evidence

Use `member-project` after the reviewed recorder has completed `receipt-bind`,
`receipt-observe`, and `receipt-results` for the same committed source S. This
command joins their original artifacts into a proposed external member pair.
It does not run an executor, grade a response, modify Git, or apply the pair.
The helper and this procedure must already be reviewed and bound at preparation;
changing either requires a new preparation before any counted observations.

Keep the relation experiment and grading outputs outside S's receipt closure.
Complete any bound plugin Markdown evidence and content-lock preparation before
S. The projector rechecks the loaded helper's bytes and mode, the original
preparation, committed source, descriptor, snapshot, observation inventory,
final lineage, and every retained input. It reproduces the ordinary receipt
with the source-bound processor and compares the retained receipt and complete
member report. The report must match the bound schema, ordered criteria and
severities, original grade counts and verdicts, computed ordinary result, and
bound limits, including their JSON types.

Create a private UTF-8 JSON projection sidecar with these fields:

| Field | Required value |
| --- | --- |
| `schema_version` | `1` |
| `binding` | Exact original preparation-binding file reference. |
| `final_lineage` | Exact `receipt-results` output `lineage.json` reference. This retains the observation index, original application grades, model basis, prior grading, adjudication, and closed result envelopes. |
| `native_grading` | Reference to the independent native grading index described below. |
| `supplements` | Complete current finding/disposition pairs; use `[]` only when the original grade artifacts contain none. |
| `history` | Historical-retention packet described below. |

A file reference has `path` and lowercase `sha256` of its exact original bytes.
References to individual JSON values also use an explicit JSON `pointer`.
JSON references default to the whole document. Keep these storage coordinates
private; public lineage retains the artifact digest and pointer. Raw response,
runner record, grader artifact, serialized envelope, and normalized projection
have distinct digests. A matching digest establishes correspondence at this
layer; it does not authenticate an executor or establish semantic correctness.

The native grading index has `schema_version: 1` and exactly thirteen `runs`,
each with its original `run_id` and a `record` reference. Each original record
contains `run_id`, `response_sha256`, nonempty `grader_task`,
`grader_distinct_from_executor: true`, Boolean `expected_should_trigger`,
`actual_skill_calls`, Boolean `passed`, and nonempty `evidence`. The grader task
must differ from every selected executor session. Match the expected Boolean to
the bound trigger corpus and actual calls to the retained native observations.
An independent false verdict remains false even when the observed selection
matches the expected Boolean. Do not replace independent grading with the
recorder's derived invocation Boolean.

Current original grader files may contain `supplementary_observations` lists.
For each finding, supply one `supplements` entry with `observation` and
`disposition` references. The observation pointer names its actual position in
the original grader file, not a copied list. Each finding contains original
`run_id` and `response_sha256`. Its disposition contains those same fields,
`observation_sha256`, nonempty `determination`, and `source_revision` identifying
the source assessed. Hash the observation as UTF-8 JSON with sorted keys,
compact separators, and unescaped Unicode. The projector requires exact
coverage and preserves both original objects. A later-source determination
never changes an earlier rubric Boolean; unresolved owner policy remains with
the integration owner. Other current supplementary container names require a
reviewed correspondence before projection.

The `history` object contains `experiment` and `grading` references to the
previous public pair, `inventory` for the retained-history inventory,
`writer_archive` for the complete writer diagnostic archive receipt, and
`copies`. A copy entry has `original_path` and a `copy` file reference with the
same original byte digest. This explicitly handles a mutable status locator
whose captured preimage is retained elsewhere. It does not rebind the historical
identity to the locator's current contents. Unused, conflicting, or changed
copy declarations stop projection.

The supported inventory retains the preceding 380 application and 78 native
objects, including technical failures and incomplete wrapper observations. Its
`inputs` map binds consulted paths to `sha256`, byte count, and mode;
`current_owning_evidence` binds the public pair. `stopped_history` carries the
two original manifests, specifications, grader cases, completed/unlaunched
inventories, original grader files, and adjudications. Recheck the original
source files, requests, specifications, responses, and literal grades: the
stopped batches remain 37 completed/14 unlaunched with 143/145 judgments, and
3 completed/48 unlaunched with 17/18 judgments. Their fourteen and three
supplements retain unresolved individual dispositions. Duplicate preflight and
final copies of identical judgments count once and retain both source identities.

The inventory's `writer_composition_diagnostic` binds its original manifest,
grader artifacts, supplementary adjudication, and source map. `writer_archive`
identifies the full archive, its manifest, and all 51 original records. Each
run lists `original_run_id`, `session_id`, `original_record`, request/response
digests, and six artifact references: specification, request, response, stdout,
stderr, and command. Every original writer record must contain request,
response, command, stdout, and stderr digests that match those exact artifact
bytes. Verify the files against the frozen preparation and the two original
grader formats; the transferred subset of fourteen responses is insufficient. Retain 191/195 literal judgments and fifteen supplementary
source assessments separately. Existing raw grader strings in the public pair
remain exact; later raw originals stay private, with public original IDs,
source/grade identities, counts, and limitations. This command does not expand
publication to later raw trace records.

Invoke the projector with the sidecar's recorded byte digest:

```sh
python scripts/mergecraft_writing_evals.py member-project \
  --projection "$projection" \
  --projection-sha256 "$projection_sha256" \
  --output "$private/member-projection"
```

The output must be a new directory outside the source checkout. All required
input checks finish before the proposed pair is written. Existing or partial
output is preserved and rejected. The directory contains:

- `experiment.json`: unchanged existing history plus 51 selected application
  projections and thirteen selected native projections, with the exact 45-path
  current-source map read from S.
- `grading.json`: all 195 literal application judgments, thirteen independent
  native grades, separate supplementary dispositions, and the complete previous
  selected grading document. Each of the 65 criteria must pass all three times.
- `normalization.json`: one-to-one run/grade lineage, explicit metadata
  replacements and their separate original/retained hashes, and an inverse that
  reconstructs both preceding public JSON files byte for byte.
- `verification-report.json`: private input locations, digests, modes, output
  digests, source revision, ordinary result, and correspondence limitations.

Fresh application IDs use `relation-<full-binding-sha256>/case-XX-with-skill-N`;
native IDs use `relation-native-<full-binding-sha256>/case-XX`. Preserve original
IDs alongside the projected IDs and reject any run or session collision.
Application coordinates and delivered-file maps come from the checked
specifications; process facts come from `record.json`, including its nested
`result`. Response text comes from exact UTF-8 `response.txt` bytes and must
match the collected packet and execution envelope. The fixed with-skill method
supplies the member's `variant` field.

Normalize only the checked native plugin path, command plugin/debug arguments,
and injected skill-directory prefix to `<CANDIDATE_PLUGIN>`,
`<LOCAL_DEBUG_FILE>`, and `<CANDIDATE_SKILL_DIR>`. Keep the injected source body,
requests, responses, grade criteria, rationale, and evidence exact. Unexpected
local-coordinate text stops ordinary projection; resolve its concrete field
with the method owner instead of broadly replacing text. These checks provide
no confidentiality assurance. Metadata-value digests use the helper's UTF-8,
two-space-indented JSON encoding with unescaped Unicode and a terminal LF;
retained invocation and injection digests retain the member validator's own
compact-JSON and UTF-8-string conventions.

A complete false judgment produces diagnostic `candidate_passed: false`.
Ordinary quality policy can pass at two of three while this member requires
three of three; a 194/195 projection must remain nonpassing. Preserve the
proposed files and original evidence for adjudication. The owner reviews the
concrete public projections, then separately authorizes their application and
runs the member validator and final committed receipt check. A synthetic
public-command/member-validator/processor roundtrip establishes mechanics only,
not current evaluation qualification or authority to choose S, execute models,
write a lock, commit, or publish.

## Export relation observations for a changed commit identity

The reviewed recorder stores `reconciliation_execution` in each original
application record when execution completes. It retains the scalar case ID,
repetition, exact response digest, completion status, process return code, and
session identity observed in the matched original initialization and result.
Preparation also retains the accepted rubrics. These fields must exist before
counted execution; preserve older records unchanged when they lack this shape.

After `receipt-results`, use the same sidecar and source-bound helper as
`member-project` to export a private reconciliation capsule:

```sh
python scripts/mergecraft_writing_evals.py receipt-reconciliation \
  --projection "$projection" \
  --projection-sha256 "$projection_sha256" \
  --output "$private/relation-reconciliation"
```

The create-only output directory must be outside the retained source checkout.
The exporter repeats the full member projection checks and writes
`reconciliation.json`, `provenance.json`, the member projections under `member/`,
and exact original artifact copies under `originals/`. Each reference binds the
whole artifact digest and the selected JSON pointer. The provenance records the
original locations and modes separately from the private copies. Retain the
complete capsule: it includes original streams, requests, responses, grading,
prior judgments, adjudications, and independent native grades.

For each of the 51 applications, the declaration connects the original recorded
execution to its source revision, corpus, request, delivered runtime and fixture
bytes, response, preparation-time rubric, and grades. The thirteen native entries
remain recorded invocations with the original query and entrypoint. Their
projected invocation Booleans do not replace independent native grading.

After the owner identifies the actual landed source Q and supported processing
revision P, consume this declaration through the `reconcile` command in
[the ordinary Receipt procedure](../behavior-eval-receipts.md). It checks the
original delivered inputs against Q and creates a new Receipt bound to Q.
Preserve the earlier S Receipt and all originals. Commit the new Receipt only
in the separate receipt-containing successor allowed by that procedure, then
run the selected member's source-stage check with the supported procedure
revision. This export does not select Q or P, invoke a provider, publish source,
or activate the separate retained-receipt caller.

Inspect both results. Ordinary quality policy may pass at two of three while
this member requires all 195 judgments and thirteen independent native grades
to pass. The capsule retains `candidate_passed: false` when that stricter
contract fails; a successful export or ordinary Receipt cannot clear it.
Reconcile with the complete supported method bound before the observations.
A changed method or original artifact requires a new preparation or an explicit
owner-reviewed correspondence, never a rewritten historical record.

## Normalize completed Markdown application evidence

Before projecting receipt-bound observations, the integration owner checks every
planned output against the receipt snapshot. Changes to bound experiments,
grades, or content-lock inputs invalidate that snapshot; return the conflict
before writing or claiming current receipt coverage. This normalization method
does not supply an exception to the receipt's source-binding contract.

After independent grading and owner adjudication, append current Markdown runs
to the skill's `evals/experiment.json` and exact judgments to `evals/grading.json`.
Use the frozen outputs of this document's `prepare`, `run`, and `collect`
invocations; normalization does not execute the provider or refresh source.
Verify each request, response, raw record, and grader-packet digest before
projection. Keep `prompt`, fixture contents, all delivered instruction strings,
and responses exact. Retain each judgment's original criterion, severity,
Boolean result, rationale, quotes, and response binding, including supplemental
inaccuracies and their separate owner dispositions.

Bind the current seven-file delivery to the repository-relative `MARKDOWN_BUNDLE`
in `scripts/mergecraft_writing_evals.py`. Record its current file digests in
`current_delivered_source_sha256`; keep the skill-relative fixture, corpus,
policy, delivery, and trigger identities in `current_source_sha256`. The owning
validator reconstructs every selected request from that complete closure.
Instruction drift invalidates the affected observations even if somebody
updates a declared digest without a new execution.

Admit selected current runs only when their retained process and protocol facts
show successful completion: exit zero, no timeout or launch/decode/parse error,
a valid stream, the requested model and effort, matching initialization and
assistant/result sessions, the recorded client configuration, and no task-tool
calls or permission denials. Retain these observations from the original
records; do not infer them from a successful grade. Bind each current grade to
the same original record digest as its run. These checks apply to the current
application method, without relabeling historical controls or diagnostics.

Match every supplementary finding to one owner disposition by run and
classification, with the same case, repetition, and response digest. Keep their
text and provenance separate from rubric judgments. The normalization map
records SHA-256 digests of both original supplementary lists serialized as
UTF-8 JSON with sorted keys, compact separators, and unescaped Unicode. Check
those projections and the original grading/adjudication source pointers so
omitting both lists does not erase the recorded limitations.

Select current with-skill thresholds separately from
`historical_control_thresholds`. The latter retain their original run IDs,
configuration, response, and grade. Validate their unchanged tasks, fixtures,
empty bundles, and arithmetic without presenting them as a contemporaneous
matched comparison. Keep old native records historical; application evidence
does not refresh native discovery. Compute every threshold from the original
individual judgments and owning policy, including a failing candidate result
when the recorded observations require it.

Preserve all original experiment entries, request mappings, runs, grades, and
thresholds. `evals/normalization.json` declares public projection omissions,
source-artifact digests, and an inverse for both preceding public JSON files:
remove newly added fields, restore replaced metadata, truncate only appended
list tails, and remove newly added request keys. Serialize the reconstructed
objects with the recorded insertion order, UTF-8, two-space indentation,
unescaped Unicode, and a terminal LF; both digests must equal the originals.
This preserves their original bytes while making new selected evidence usable.

Publish only selected protocol facts and original-file digests. Keep private
locations, reasoning blocks, credentials, and operational streams in the
retained private artifacts. The validator checks history reconstruction,
current full-bundle correspondence, coverage, grades, and threshold arithmetic.
Run its focused `MarkdownEvidenceRefreshTests` and the package's owning checks;
independent review and existing content-lock/publication owners then decide the
integration. A pending unrelated evidence gate remains pending.
