# Ordinary behavior-evaluation receipts

Produce and check behavior-evaluation receipts for the committed Provingkit Slate with [the inventory adapter](../scripts/behavior_eval_inventory.py) and [the receipt core](../scripts/behavior_eval_receipts.py). The inventory derives affected skills and their current cases; the core binds observations to source and checks coverage. Use preparation before new runs, reconciliation for eligible retained observations, and a check of receipt bytes committed in the candidate.

## When to load this procedure

Load it when recording behavior evaluations, reconciling retained run or discovery artifacts, checking evidence after skill or shared-input changes, or consuming those results for disclosure or readiness. “Record these three runs,” “Can these original runs support the current source?” and “Check behavior evidence for this candidate” enter this procedure.

Static source validation, ordinary pull-request review, publication-review receipts, and deployment qualification use their owning procedures. “Check Markdown formatting” and “Verify the publication-review receipt” do not enter this procedure. An unchanged candidate still enters when behavior evidence is requested: `not-required` is a check outcome, not a discovery exemption.

## Inputs and claim

Use a local Git repository with the required commits and ancestry available, Python, and `jsonschema`. JSON must contain finite numbers and UTF-8 scalar text. The [schema](../release/behavior-eval-receipt-v1.schema.json) defines public receipts and private inputs, including `snapshot`, `results`, `reconciliationResults`, `routingSequence`, and `request`. For the cases required by the ordinary inventory, the [policy](../release/behavior-eval-policy.json) requires three runs per application case: every safety expectation passes all three, every quality expectation passes at least two, and every required Boolean or ordered-routing trigger is correct. Support for a corpus format does not itself make that corpus an ordinary evaluation requirement.

These are ordinary data checks: source coverage, supplied-artifact consistency, threshold arithmetic, and byte binding. They do not authenticate observations or review decisions, establish native invocation from authored fields, or supply issuer, privileged-execution, protected-evidence, or security assurance. `attestation: null` is inert. Return a requirement for stronger claims to its owner before expanding this procedure.

Keep four commit identities distinct:

| Identity | Meaning |
| --- | --- |
| B | Comparison base used to decide which skills require receipts. |
| S | Committed source evaluated after preparation, or matched to retained observations during reconciliation. The receipt calls this `candidate_revision`. |
| C | Candidate containing the public receipts; the check calls this `candidate_revision`. S must be its ancestor and all bound source inputs must remain unchanged. C is not claimed to have been executed. |
| P | Committed processing implementation used for reconciliation, recorded separately from S and original execution revisions. |

Complete canonical source and content-lock preparation before selecting S. Keep public receipts outside the evaluated input closure. Run commands from the repository root, or put `--repository PATH` before the subcommand. `SKILL` is a `plugin/skill` ID, `EVAL_PRIVATE` is a private artifact directory outside the repository, and `RECEIPTS` is an authorized repository-relative receipt directory. All commands emit JSON on stdout; create destinations before redirecting output.

## 1. Resolve the committed inventory

```sh
python scripts/behavior_eval_inventory.py discover --revision "$S" \
  > "$EVAL_PRIVATE/inventory.json"
python scripts/behavior_eval_inventory.py normalize --revision "$S" --skill "$SKILL" \
  > "$EVAL_PRIVATE/normalized.json"
python scripts/behavior_eval_inventory.py descriptor --revision "$S" --skill "$SKILL" \
  > "$EVAL_PRIVATE/descriptor.json"
```

The authoritative repository inventory starts at [the Kit definition](../release/provingkit/definition-v1.json): its Slate selects plugins, and each plugin's topology declares its Roster. Discovery compares each Roster with committed `skills/*/SKILL.md` entrypoints. An outside-Slate directory does not become a member through filesystem presence. Missing or extra entrypoints remain diagnostics. `discover` returning zero establishes Roster completeness only; inspect diagnostics and require the selected descriptor's `status: "ready"` before producing evidence.

[Corpus normalization](../scripts/behavior_eval_corpora.py) retains original coordinates as `{source, pointer, id}`. A case with ID `0` at `/evals/0` keeps ID `0`; a string ID stays a string. When an ID is absent, its dictionary key supplies the identity if available; otherwise it remains `null`. JSON pointers locate source records; they are not invented expectation IDs. Ordinary normalization retains every owned current application and trigger case required in this scope, resolves external fixtures and referenced scenarios, and preserves complete ordered `expected_selection` arrays when selected. Inspection retains source coordinates, roles, and scope even for records outside ordinary coverage. Current corpora and supporting inputs remain distinct from reference-only material and retained run/grading evidence. A retained grade is not a current case or a newly observed result.

Supported source forms include per-skill evals, scenario lists and dictionaries, Boolean trigger arrays, routing matrices, and scenario references used by control-plane or retirement matrices. Unknown formats, malformed reference or dependency declarations, missing fixtures, unresolved owners, and missing expectation IDs or severities remain diagnostics in their source scope. Missing application or trigger coverage is unresolved; there is no absent-trigger exemption. Selected unresolved inputs block preparation and checking instead of disappearing from coverage.

The canonical [skill-routing matrix](../evals/skill-routing-matrix.json) belongs to the separate [Phase 2 production-release routing tier](../evals/README.md#phase-2-observable-routing). Its document and records carry `scope: "production-release"`; ordinary inventory excludes its cases by default. This boundary also governs scenario ownership, runtime dependencies, and expectation-mapping applicability across supported source formats. Current direct Boolean probes remain required. Matrix parsing or sequence support does not add the production matrix to their denominator, and separate-tier diagnostics remain visible without automatically blocking unrelated ordinary coverage.

Use the committed [input map](../release/behavior-eval-input-map.json) for reviewed ownership, role, and dependency declarations, and the [expectation map](../release/behavior-eval-expectation-map.json) for reviewed expectation IDs and `safety`/`quality` severities. Accepted entries bind the original source digest and pointer, their semantic fields, and an accepted review reference with the matching semantic digest. Expectation mappings also retain the exact original value and cannot override an explicit source ID or severity. Byte/digest checks establish correspondence, not the reviewer's authority.

An explicitly accepted `current-corpus` input mapping can adopt a production-matrix coordinate for its declared consumers. An empty pointer selects the document's cases; a nonempty pointer must match an original application or trigger coordinate. Unmatched container pointers remain unresolved. Preserve the adopted records' original coordinates and complete expected sequences. Adopted records become ordinary requirements for those consumers and inherit their document-wide and original-owner references. This adoption does not automatically require the matrix for other consumers or replace their direct probes. Use `discover` for full source and scope inspection, and `normalize` or `descriptor` for a particular consumer's ordinary requirements.

```sh
python scripts/behavior_eval_inventory.py proposals --revision "$S" --skill "$SKILL" \
  > "$EVAL_PRIVATE/unresolved.json"
```

`proposals` returns original unresolved values and existing proposed entries for review. It neither writes mappings nor chooses owners, IDs, severities, or acceptance decisions. A proposed entry does not resolve a case. Return consequential mapping decisions to their owner, commit accepted declarations through the owning workflow, then choose S and normalize again.

The generated descriptor accounts for the skill subtree, required corpora and fixtures, topology resources, local linked resources, shared canonical sources and their projections, and declared supporting inputs. When its ordinary requirements include ordered routing, it also binds the complete Slate catalog's definition, topologies, and skill entrypoints. The snapshot binds the full skill directory, whole content lock, selected corpora, mappings, and descriptor inputs by bytes and executable mode. Whole-lock binding is deliberately conservative. Preparation also binds the tool, corpus and inventory adapters, policy, and schema at S; reconciliation records those processing files at P instead.

This full freshness closure is broader than the inputs that select a skill for evaluation, and broader than what a runner actually delivered. For example, a skill's `agents/openai.yaml` can be bound source without being a delivered runtime input. Source-stage validation and downstream readiness remain separate requirements.

## 2. Prepare and produce new observations

```sh
python scripts/behavior_eval_inventory.py prepare --revision "$S" --skill "$SKILL" \
  > "$EVAL_PRIVATE/snapshot.json"
```

Preserve the returned snapshot unchanged. Use a separately authorized runner to execute every application case at repetitions 1, 2, and 3, grade every expectation, and observe every trigger. These adapters execute no evaluations themselves. Store private artifacts using the schema's envelopes:

| Artifact | Required correspondence |
| --- | --- |
| Executor output | Snapshot digest, original case coordinate, repetition, executor model ID, and actual response. An explicitly observed empty response is valid data. |
| Grading | Same snapshot and coordinate, grader model ID, exact executor-artifact byte digest, and a Boolean `passed` observation for each expectation ID. |
| Trigger observation | Same snapshot, trigger coordinate, executor model ID, and recorded Boolean invocation or complete recorded invocation sequence, as required by the corpus. |
| Results manifest | Same snapshot and model IDs, every run coordinate and artifact path, and every trigger observation path. |

Paths resolve from the private results manifest. `snapshot_sha256` is `document_digest(snapshot)`: SHA-256 of sorted, compact UTF-8 JSON with unescaped Unicode and no trailing newline. Artifact hashes cover exact bytes. An authored skill selection cannot populate a recorded-invocation field. Missing responses, grades, or observations remain missing; envelope consistency does not prove that a run occurred or a model identity was truthful.

```sh
python scripts/behavior_eval_receipts.py produce \
  --snapshot "$EVAL_PRIVATE/snapshot.json" --results "$EVAL_PRIVATE/results.json" \
  > "$RECEIPTS/$SKILL.json"
```

Production checks all required coordinates and projects results into a public receipt, retaining private-artifact hashes while omitting their paths and raw outputs. Completion requires the intended S, unchanged snapshot, complete results, and retained private artifacts. A produced receipt may record failed thresholds; proceed to candidate checking before treating it as passing.

## 3. Reconcile retained observations

Use this route when original artifacts can establish correspondence after execution. It does not backdate a snapshot or create new runs.

1. Resolve the complete current inventory at S. Select P containing the processing implementation; its committed tool, corpus adapter, inventory adapter, policy, and schema must match the running files. Processing files need not have existed when the original evaluations ran. A processing-only change requires reprocessing, not relabeling the old receipt.
2. Write a private `$defs.reconciliationResults` manifest with `method: "reconciled-after-run"`. Use read-only `$defs.evidenceReference` values: relative artifact `path`, exact byte `sha256`, `format` (`utf8`, `json`, or `jsonl`), and `pointer`. An empty pointer selects the whole artifact and is required for UTF-8 text. JSONL pointers use **physical zero-based line indices, including blank lines**; blanks occupy null entries. `/2/payload/response` addresses the third physical line, not the third nonblank record. Preserve original bytes and references rather than authoring replacement observations.
3. Supply three distinct original executions per current application case. Each `execution_record` must be a supported original run object, not an arbitrary field or a newly authored identity. Its `execution` envelope must record successful completion, exactly one `thread_ids` value, and the matching response digest; the alternative supported form records `native_agent`. Every present recognized identifier is checked: when both forms appear, `native_agent` must equal the single recorded thread ID. Both forms must bind the actual response through the record's `response` or `response_sha256`, with every present response field agreeing. Recorded case and repetition fields must also agree. Different references to the same execution cannot supply multiple cases or repetitions. The public `execution_identity` retains its `recorded-thread` or `recorded-native-agent` basis and identity hash.
4. Retain the recorded original revision or explicitly recorded `null`, original corpus digest, actual prompt and response, and delivered runtime and fixture bindings. Declare the complete delivered runtime inputs using the [uniform or per-case form below](#runtime-input-declarations). Every repetition must supply exactly its case's declared runtime set plus every required case fixture, retaining original evidence references. Delivered bytes and prompt must match current source exactly.
5. Preserve executor and grader identities with their original `configured`, `requested`, or `reported` evidence basis. Configuration evidence does not establish which model served a request. Reference actual Boolean grades bound to the unchanged response and current rubric or corpus digest. Keep original expectations and grades; a rubric correction requires `previous_grading` and actual `adjudication` evidence with the later grading and model basis. Regrading one response remains one execution. Keep failures in the lineage and use actual final grades.
6. Supply the corresponding discovery evidence below. Missing records, changed delivered inputs, incomplete routing catalogs, and unsupported trace formats remain explicit gaps. Do not manufacture missing observations or substitute authored selections.

```sh
python scripts/behavior_eval_inventory.py reconcile \
  --revision "$S" --processing-revision "$P" --skill "$SKILL" \
  --results "$EVAL_PRIVATE/reconciliation.json" \
  > "$RECEIPTS/$SKILL.json"
```

The public receipt records the reconciliation method, original execution and grading lineage, model bases, observation limits, S, and P. References preserve hashes, formats, and pointers while omitting private artifact paths and response text. Inspect public coordinates for unintended private details. Retain originals unchanged, then check the candidate. Successful production alone proves neither passing thresholds nor a new evaluation.

### Runtime input declarations

When every application case receives the same runtime inputs, declare that unique, nonempty path list in `runtime_inputs`. It must include the target skill's `SKILL.md`, and every path must belong to the complete source snapshot. Omitting `case_runtime_inputs` preserves this uniform contract and leaves the optional table out of the public receipt.

When delivered runtime inputs differ by case, add `case_runtime_inputs` to the private reconciliation manifest. It is an array of `{case_id, runtime_inputs}` rows, using the same authoritative `caseCoordinate` values as the application runs. Include every current application case exactly once, with no missing, duplicate, or unknown coordinates. Each row must contain a unique, nonempty runtime path list that includes the target skill's `SKILL.md` and belongs to the complete source snapshot. The global `runtime_inputs` list must equal the exact union of those lists. For example, if one case receives the skill and a shared reference while another receives only the skill, declare those two sets separately and keep both paths in the global list.

In either form, `runtime_inputs_complete: true` is the caller's assertion that the global list and every case's declared runtime set are complete. Reconciliation and public checking enforce the same declarations and exact input coverage for all three repetitions; they do not independently authenticate delivery. The public receipt's `reconciliation.case_runtime_inputs` retains the table when present. This optional field uses schema version 1 and requires a supporting P; earlier processors reject it.

Keep the full committed source closure even when a case omits a reference. Whole-source bytes and executable modes, including inputs omitted by one or every case, still participate in S-to-C freshness checks. A delivery declaration does not narrow that closure or change prompt, execution, model, grading, or discovery provenance.

### Boolean discovery

`recorded-invocation` references an original Boolean invocation observation. `recorded-sentinel-body-load` records a bounded probe surrogate. Its trace form retains `record`, `model`, `query`, and `limits`, plus retained `trace`, `probe_skill`, `probe_prompt`, `sentinel`, and `returncode` references. The adapter matches the probe's name and description to current skill metadata, then requires one started and completed turn. A positive permits exactly one successful `cat` read of the named `.agents/skills/<name>/SKILL.md`, parsed through a supported absolute shell with `-c` or `-lc`, returning the exact probe bytes. It rejects repeated or concurrent reads, mismatched read starts and completions, responses during an unfinished read, and events after turn completion. CLI message records have no final phase: preliminary messages may precede the read, but a terminal response must follow every read and precede turn completion. The command is parsed as data and is never executed by reconciliation.

A positive requires the recorded body load, exact sentinel response, and successful completion. A negative requires no body load, the exact negative response prescribed by the original probe prompt, no tool actions, and successful completion. Preserve that original prompt even when the negative trace contains no read. This correspondence covers the probe's name and description, not execution of the current skill body or native invocation. It cannot satisfy an ordered-routing case.

A retained public trace projection may replace its original probe-root path with the literal `<probe-root>`. This is the only supported symbolic root and requires the original run record's nonempty `trace_path_normalization` and valid `original_transcript_sha256`. Preserve those original declarations and projected bytes; do not reconstruct a raw trace or relabel a projection as raw evidence. Artifact references hash the supplied projection, while public reconciliation separately retains `trace_projection: {kind: "symbolic-paths", original_trace_sha256}`. The original-trace digest records retained provenance; reconciliation neither reopens that raw trace nor authenticates the projection's correspondence to it. This allowance does not relax the literal command and read requirements of the complete-catalog sequence route.

### When complete ordered routing is required

Enter this branch only when the ordinary descriptor requires an ordered case, including an explicitly adopted production-matrix coordinate. Use `recorded-invocation-sequence` only for an original observed sequence retaining every selection in order. For supplied-catalog marker probes, use `recorded-sentinel-sequence` and `$defs.routingSequence`. These ordinary checks do not substitute for the separate production-release routing gate. Inspect canonical metadata with:

```sh
python scripts/behavior_eval_inventory.py catalog --revision "$S" \
  > "$EVAL_PRIVATE/canonical-catalog.json"
```

The command returns an inspection view with `members` and `source_identities`. Reconciliation's `source_catalog` instead references the original `revision`, `tree`, and `entries` envelope; each entry retains `id` as `plugin:skill`, `name`, `description`, `source_path`, and `source_sha256`. Do not substitute a newly generated inspection view for retained evidence.

The catalog must cover the complete committed Slate and every Roster member, with unique unqualified skill names. Retain original references for:

- `source_catalog`, including its original revision, Git tree, and every member's identity, name, description, entrypoint path, and digest;
- the exact `offered_catalog` JSON string, `marker_map`, and `bodies` for **every** catalog member, including unselected skills;
- the frozen `protocol`, original `query`, complete `executor_message`, raw native `trace`, and original `dispatch` and `spawn` records;
- `record`, model evidence, and limits, with `prompt_basis: "frozen-dispatch-argument"`.

The retained source catalog must match the canonical catalog rebuilt from its original commit, whose complete source identities must also match S's bound inputs. Each offered name and description must match that catalog. Each unique marker body is its unique token followed by a newline; its path, byte count, digest, and literal read command must match the marker map and offered catalog. Use the precise supported literal `functions.exec`/`exec_command` read shape in the core; unsupported wrappers or incomplete evidence require adapter work, not inferred reads.

The frozen executor message must equal `protocol + "\nRequest:\n" + query + "\n\nAvailable skill catalog:\n" + offered_catalog`, preserving the exact offered JSON text. The original dispatch's `arguments.message` must equal that message, `fork_turns` must be `"none"`, and `task_name` must match the spawned agent path. Dispatch and spawn must share a `call_id`; the spawn's `agent_thread_id` must match the native trace's single session identity. One native routing session cannot supply multiple observations.

Recorded user inputs must equal the frozen message or belong to the exact reviewed ambient set described below. Arbitrary additional instructions, conflicting messages, and inputs after completion are rejected. If the recorder omits or encrypts provider-input plaintext, dispatch-to-child correspondence does not recover it. Keep `prompt_basis: "frozen-dispatch-argument"` and record that limit; neither absence of conflicting plaintext nor `fork_turns: "none"` proves a complete provider request, installed-skill discovery, native skill invocation, or runtime isolation.

The adapter validates nested native record types, identities, command arguments, and message blocks before interpreting state or identity correspondence. It then derives the sequence: each allowed sequential tool call must match its completed command, exact marker output, successful exit, and corresponding outer tool result. It requires one identified session and completed turn with matching configured model, and one final response after all reads. Native `phase: "final"` and `channel: "final"` are supported; if both appear, both must be `"final"`. Malformed records and unmatched, concurrent, failing, or unsupported calls reject the evidence. Preserve duplicates and extra reads in their original order; never filter to the expected skill. The final `{"tokens": [...]}` response must agree with the derived reads and serves only as corroboration.

Compare the full observed sequence with the full expected sequence. Expected `["writer"]` with observed `["writer", "writer"]` fails. A neighboring negative may expect another skill; preserve that selection. Expected `[]` passes only with no reads and the corresponding empty-token response in a successful turn.

The public `routingCatalog` retains canonical source identities, every member's metadata/body/token hashes, complete read identities and order, hashes of the prompt, offered catalog, marker map, and trace, and dispatch/spawn references with hashed call, task, child-session, and turn identities. Checking rebuilds the canonical catalog, matches it to the source snapshot, and checks public reads, session uniqueness, and retained evidence references. It does not reopen private traces or authenticate their origin.

### Reviewed ambient context for routing

Optional `sequence.ambient` permits only exact recorded harness envelopes: an AGENTS instruction heading followed by `<INSTRUCTIONS>` and `<environment_context>`, or `<environment_context>` alone. Each `records` entry supplies an original `reference` to the user-message payload in the same trace bytes and format, plus `provenance`. Use `kind: "harness-agents-environment"` with `repository_path_sha256`, `instructions_sha256`, and `environment_sha256`, or `kind: "harness-environment"` with `environment_sha256`. The adapter derives these hashes from the supported envelope and requires agreement; the record digest also binds the complete payload. Every listed payload must occur exactly once, and literal routing markers in it are rejected.

Before accepting this allowance, review the exact ambient content for expected-selection leakage, answer hints, or instructions that alter the probe's routing task. The mechanical marker check cannot make that semantic decision. Record the existing review as `review: {decision: "accepted", reference, records_sha256}`. The digest is `document_digest` of the ordered public records array: each item has `reference` containing only `sha256`, `format`, and `pointer`; `record_sha256` containing `document_digest` of the original user-message payload; and `provenance`. It is not the digest of the private manifest or a blanket approval of an AGENTS filename.

Unsupported user-message shapes remain rejected. Changed content needs a new review; a missing or unaccepted review cannot be replaced by relabeling the input as ambient. The public catalog retains the reviewed records, provenance, and review binding for subsequent consistency checks. This allowance establishes neither authenticated harness provenance nor review authority, and does not remove the provider-input limits above.

## 4. Check committed receipts at C

Through the owning Git workflow, record receipts at `$RECEIPTS/<plugin>/<skill>.json` and select C. First inspect applicability, then run the check:

```sh
python scripts/behavior_eval_inventory.py compare --base "$B" --candidate "$C" \
  > "$EVAL_PRIVATE/comparison.json"
python scripts/behavior_eval_inventory.py check \
  --base "$B" --candidate "$C" --receipt-root "$RECEIPTS" \
  > "$EVAL_PRIVATE/check.json"
```

Applicability compares committed B and C and selects both old and new consumers of changed ordinary behavioral inputs: skill subtrees, required corpora and fixtures, shared sources, topology consumption, and operative ownership or expectation mappings. Mapping selection is per owner. A changed accepted owner, corpus adoption, or rubric selects its affected consumers; changes only to proposals, rationale, or review metadata do not. Removed or renamed skills, changed unsupported ordinary corpora, and changed ordinary inputs with unresolved owners produce explicit unsupported coverage. Separate production-tier diagnostics remain visible and do not independently add ordinary consumers. Descriptors for selected skills use C's current inventory, without forcing deleted historical files into its closure.

Scenario matrices compare each consumer's own declarations and runtime dependencies, plus the entrypoints, companion edges, and runtime dependencies of its transitive companions. Every admitted row contributes its companion declarations; runtime owner aliases contribute all their inputs. Adding an unrelated row leaves existing consumers unselected. Changing a scenario, transferring ownership, removing a consumed row, or changing a companion's consumed runtime selects the affected old and new consumers. `discover` exposes these per-consumer values in `matrix_consumption` while preserving original records and coordinates. A skill that also consumes the whole matrix through a linked resource, topology declaration, reviewed behavioral input, reference, or runtime dependency retains whole-file applicability. This comparison does not remove matrix-derived ownership or runtime inputs, and unresolved declarations remain diagnostics. An unknown runtime owner prevents complete ordinary coverage when its declaring matrix or any declared runtime input changes, including directory additions, removals, bytes, or modes. Unrelated changes do not activate that diagnostic as a coverage blocker.

`compare` returns a compact decision record: full `base_revision` and `candidate_revision`, `changed_paths`, `affected_skills`, `causes`, `selection_complete`, `unsupported`, and status. Its `inventory_diagnostics` preserves global and per-skill diagnostics by side, adding the consumer's `skill` to each per-skill diagnostic. The `inventory_summary` contains each side's revision, Roster-completeness flag, and skill, document, and unresolved-record counts. It does not embed full discovery inventories. Invoke `discover` explicitly at B or C when source records or complete ownership details are needed; `check` carries the same compact diagnostics and summary alongside receipt outcomes.

Freshness then compares the selected receipt's full S-to-C binding. Whole scenario matrices, mapping files, content locks, and supporting dependencies remain freshness inputs even where they do not independently select a skill. Matrix projections change comparison granularity only: descriptors and snapshots still bind the complete consumed matrix bytes. Processing files also bind S to C for prepared receipts; reconciliation verifies them separately at P. For example, an external behavioral fixture change selects its consumers; a proposal-only map edit does not, but it can stale an already selected receipt through the whole map's digest. Untouched unresolved corpora may remain outside a no-op check; no-op does not establish their support or freshness.

The inventory checker reads actual regular Git blobs at `C:$RECEIPTS/<plugin>/<skill>.json`, not working-directory copies, and records their path, mode, blob identity, and byte digest. It passes C as both revisions to the core with each inventory-selected skill explicit, so the core's broader file-level selection cannot widen the per-owner comparison. The result records this coverage basis and retains selection causes, diagnostics, and unsupported inputs.

For every selected skill, require a ready current descriptor, matching receipt and snapshot, S ancestry, unchanged full source closure, complete coverage, and passing thresholds. Reconciliation also checks P against committed and running processing files and checks public correspondence and lineage. Stale processing requires reconciliation again. Changed delivered prompts, runtime bytes, or fixtures require eligible observations for those changed inputs.

The core records `receipt_raw_sha256` before parsing and canonical `receipt_sha256` when serialization succeeds, on acceptance or rejection. Malformed bytes retain their raw identity; missing or unreadable files have neither. `evaluated_revision` names S after source and coverage checks complete, not an original historical execution revision.

| Outcome | Exit | Required action |
| --- | --- | --- |
| `pass` | 0 | Retain the committed receipt identities, selected coverage, and result for the consumer. |
| `not-required` | 0 | Record that the complete comparison selected no skill. Do not infer universal corpus support or receipt freshness. |
| `fail` | 1 | Preserve all rejected or unsupported coverage. Resolve missing evidence, mappings, adapter support, stale bindings, or actual failed expectations before claiming a pass. |
| Per-skill `waiver-pending`, overall `fail` | 1 | Hand the existing operator decision and release anchor to the owner of authority and expiry verification. |
| `error` | 2 | Correct malformed or unavailable inputs. Preparation and reconciliation also use this exit for unresolved selected inventories or invalid evidence. |

`normalize`, `descriptor`, and `proposals` return 1 for unresolved results; `compare` returns 1 for unsupported selection. Inspect their JSON, not just process success. A waiver uses `$defs.waiver`: bound S and snapshot, reason, existing operator-decision digest, `expiry.event: "next-release"` with its `after_release` anchor, and `attestation: null`. It must satisfy descriptor and freshness checks. The local checker leaves issuance and expiry verification false; no threshold or authority requirement is waived by recording it.

## Direct core callers

The core API remains available as `prepare`, `produce`, `reconcile`, and `check`; the inventory exposes `discover`, `normalize`, `canonical_catalog`, `descriptor`, `proposals`, `compare`, `prepare`, `reconcile`, and `check`. Python callers may use these same seams.

For a deliberately caller-scoped check, core CLI `prepare` takes `--revision S --skill-spec spec.json`; `reconcile` additionally takes `--processing-revision P --results reconciliation.json`; `check` takes `--request request.json --receipts DIRECTORY`. Its descriptor requires `behavior_inputs`, `dependencies`, `shared_references`, and `closure_complete: true`; its request supplies B, C, `skills`, explicit `changed_skills`, and `inventory_complete: true`. These completeness fields are caller assertions, not independently discovered coverage.

List every external fixture, directly consumed behavioral resource, and applicable ownership map in `behavior_inputs`; put canonical shared sources in `shared_references` and other freshness inputs in `dependencies`. A supported external fixture absent from `behavior_inputs` is rejected even if listed as a dependency. The core unions explicit changed IDs with its local Git diff effects, enforces every explicit ID, and selects before parsing corpora. Include both old and new consumers when ownership changes, while keeping descriptors current at C. Its legacy corpus form remains limited to positive integer case IDs with structured expectations and nonempty explicit Boolean trigger arrays; inventory-generated `provingkit-v1` descriptors provide normalized coordinates and matrix coverage.

The direct CLI reads mutable local receipt files and reports `coverage_basis: "caller-declared-complete"`. It is useful before committing, but does not establish committed receipt bytes at C or authoritative inventory coverage. Python callers supplying raw bytes retain raw and canonical digests; callers supplying JSON values have only canonical identities. Use the inventory check for the committed-Slate claim above.

## Acceptance and consumer handoff

For adapter changes, run `python -m unittest tests.test_behavior_eval_receipts tests.test_behavior_eval_corpora tests.test_behavior_eval_inventory` and `git diff --check`. Tests construct artifacts and Git histories; they establish adapter behavior, not live evaluations or discovery. Review this procedure against the final implementation, schema, policy, and maps. Exercise positive and neighboring negative discovery separately from application success, failure, unsupported-input, waiver, and no-op branches. A constructed receipt or static review does not establish live procedure behavior.

Before dependent execution, [disclosure #28](https://github.com/nisavid/provingkit/issues/28) and [readiness #34](https://github.com/nisavid/provingkit/issues/34) must load this procedure and invoke the inventory check using the same reviewed, published procedure and implementation revision. Retain that revision, B, S, C, comparison and check outputs, committed receipt identities, explicit failures or gaps, and any independently established waiver disposition. For reconciliation, also retain P, original artifact references and execution revisions, grading/adjudication lineage, model bases, and discovery limits. Disclosure consumes these identities and outcomes; readiness preserves its independent requirements and cannot treat `waiver-pending` as passing.

Consumer invocation pointers, source-stage validators, CI wiring, live procedure evidence, and verification on the integrated published revision remain owned by the integrating workflow. Feed a correction affecting meaning or coverage back to this procedure's owner and refresh affected evidence. This standalone inventory and receipt procedure does not establish consumer completion, publication, or completion of [receipt work #33](https://github.com/nisavid/provingkit/issues/33).
