# Ordinary behavior-evaluation receipts

Prepare committed evaluation inputs, project local observations into public receipts, and check their coverage and freshness with [the local adapter](../scripts/behavior_eval_receipts.py). Its `prepare`, `produce`, and `check` functions expose the same three stages to repository callers. This is a source-specific procedure for ordinary result data.

## When to load this procedure

Load it when producing a behavior receipt from fresh evaluation artifacts, checking receipts after skill or shared-reference changes, or consuming those results for disclosure or readiness. For example, “Record these three runs,” “Does this reference change invalidate the writing skill’s receipt?” and “Check the behavior evidence for this candidate” enter this procedure.

Static source validation, ordinary pull-request review, publication-review receipts, and deployment qualification use their owning procedures. A request such as “Check Markdown formatting” or “Verify the publication-review receipt” does not enter this procedure. An unchanged candidate still enters when the request is to check behavior evidence; `not-required` is an application outcome, not a discovery exemption.

## Inputs and claim

Use a local Git repository with the relevant committed source and ancestry available, Python, and `jsonschema`. The [schema](../release/behavior-eval-receipt-v1.schema.json) defines the public `evaluation` and `waiver` records and the private `skill`, `snapshot`, `results`, `execution`, `grading`, `triggerObservation`, and `request` inputs under `$defs`. The [policy](../release/behavior-eval-policy.json) requires three runs of every case: each safety expectation passes all three, each quality expectation passes at least two, and every trigger case is correct.

These checks establish consistency of supplied data, coverage arithmetic, and byte binding to Git source. They do not authenticate observations, prove native invocation from authored fields, or supply issuer, privileged-execution, protected-evidence, or security assurance. `attestation` is always `null` and has no operative meaning. Route a requirement for those stronger claims to its owner before expanding this procedure.

The local corpus adapter supports:

- A per-skill object with matching `skill_name` and a nonempty `evals` array. Every case has a unique positive integer `id`, a `fixture_paths` array, and nonempty `expectations` containing unique `id`, nonblank `text`, and explicit `severity` of `safety` or `quality`.
- A nonempty trigger array whose entries contain exactly a unique nonblank `query` and Boolean `should_trigger`. Trigger result IDs are the one-based array positions written as strings.
- Committed regular files with normalized repository-relative paths. Fixture paths resolve under the descriptor’s `fixture_root`, which defaults to the skill directory.

String-only expectations, missing or empty trigger corpora, and other matrix formats are unsupported. Return the unsupported input and required adapter work to its owner. A future matrix adapter must retain every case and distinguish observed invocation from authored selections. Historical output keeps its original input identity; it cannot be rebound to fresh source by adding a new envelope.

## 1. Prepare the evaluated source

Choose an existing full commit identity **S** for the source to evaluate. Complete source and content-lock preparation before selecting S. The later commit **C** that contains the receipt must descend from S and retain the entire evaluated input closure unchanged. The receipt’s `candidate_revision` names S; the check request’s `candidate_revision` names C. Neither field claims that C was executed.

Write one private skill descriptor per skill. This illustrative descriptor uses the supported shape; replace its identities and paths with the actual source:

```json
{
  "plugin": "example",
  "skill": "writing",
  "content_lock": "release/plugin-content-locks/example.json",
  "evals": "plugins/example/skills/writing/evals/evals.json",
  "trigger_evals": "plugins/example/skills/writing/evals/trigger-evals.json",
  "dependencies": [],
  "shared_references": [],
  "closure_complete": true
}
```

Inventory all dependencies the evaluation consumes. Put canonical shared-reference sources in `shared_references`, including sources whose generated projections affect this skill. Put other dependency files in `dependencies`. `closure_complete: true` is the caller’s assertion that this inventory is complete; the helper does not discover omitted dependencies.

The snapshot automatically binds the whole skill directory, the whole declared content lock, the corpora and their listed fixtures, descriptor dependencies and shared references, and the receipt tool, policy, and schema. It records each file’s bytes and executable mode. Whole-lock binding is intentionally conservative: a change elsewhere in that lock also invalidates this skill’s receipt. Source-stage validators, CI, and shared outputs are outside the automatic closure. Keep receipt outputs outside the evaluated closure so recording them does not invalidate their own inputs.

Run commands from the repository root, or insert `--repository PATH` before the subcommand. In these examples, `S` holds the full evaluated commit, `EVAL_PRIVATE` names a task-specific private directory outside the repository, and `RECEIPTS` names the authorized public receipt directory. JSON results go to stdout; the caller chooses their destinations.

```sh
python scripts/behavior_eval_receipts.py prepare \
  --revision "$S" --skill-spec "$EVAL_PRIVATE/spec.json" \
  > "$EVAL_PRIVATE/snapshot.json"
```

Preparation is complete when the returned snapshot matches the intended skill and complete committed inputs at S. Preserve it unchanged with the private run artifacts.

## 2. Record observations

Use the separately authorized evaluation runner to execute every corpus case at repetitions 1, 2, and 3, grade every expectation in each run, and observe every trigger case. The receipt adapter executes no model or harness runs.

Retain the actual local artifacts in the schema’s private envelopes:

| Artifact | Required binding and result |
| --- | --- |
| Executor output | Snapshot digest, case ID, repetition, executor model ID, and response (including an explicitly observed empty string). |
| Grading | The same snapshot and coordinate, grader model ID, exact executor-artifact byte digest, and one Boolean `passed` observation per expectation ID. |
| Trigger observation | Snapshot digest, trigger case ID, executor model ID, `observation_kind: "recorded-invocation"`, and observed Boolean `triggered`. |
| Results manifest | Snapshot digest, executor and grader model IDs, each run’s coordinate and artifact paths, and each trigger’s observation path. |

Artifact paths are relative to the private results manifest’s directory. `snapshot_sha256` uses `document_digest(snapshot)`: SHA-256 of UTF-8 JSON with sorted keys, compact separators, unescaped Unicode, and no trailing newline. Artifact digests cover their exact file bytes.

The runner records observations; the corpus supplies expected behavior and severity. A model’s authored selection of a skill is not a recorded invocation and cannot populate that observation kind. An observed empty response is a completed result that the grader can assess; an absent response field or artifact remains missing. Missing grading or invocation evidence also remains missing. The helper checks envelope consistency, not whether an author truthfully recorded a run or its model identity.

Recording is complete when every required coordinate, expectation, and trigger has its own corresponding artifacts, bound to the preserved snapshot. Keep raw responses, grading files, invocation observations, and the manifest private.

## 3. Produce the public receipt

```sh
python scripts/behavior_eval_receipts.py produce \
  --snapshot "$EVAL_PRIVATE/snapshot.json" \
  --results "$EVAL_PRIVATE/results.json" \
  > "$RECEIPTS/example/writing.json"
```

Create the destination directory beforehand. The producer reads local artifacts, checks their snapshot, coordinate, model, and coverage bindings, and projects expectation results and trigger observations into a receipt. The public record retains hashes of private artifacts and the manifest; it omits their private paths and raw output. Inspect the result before publication. A produced receipt can record failing thresholds; creation alone is not a passing check.

Production is complete when the public record has the intended evaluated revision S, unchanged snapshot, complete results, and private-evidence digests. Preserve the private artifacts under their existing retention arrangements so those hashes remain useful for later inspection.

## 4. Check the candidate

Create a request using `$defs.request`:

- `schema_version` is `1`; `base_revision` is the full comparison commit **B**; `candidate_revision` is the full commit to check, **C**.
- `skills` contains the complete inventory of skill descriptors relevant to the check, including skills affected through shared references. Each descriptor matches the one in its receipt.
- `inventory_complete` is `true`. This is a caller assertion, not verified repository discovery.
- `changed_skills` explicitly lists affected `plugin/skill` IDs known to the caller; use an empty array only when there are no additional known IDs. Every listed ID must occur in `skills`.

The checker unions those explicit IDs with effects derived from the Git diff between B and C: changes under each declared skill directory, its bound paths, and its canonical shared references. Shared-reference coverage therefore depends on the caller supplying every affected skill and its complete closure. The result reports `coverage_basis: "caller-declared-complete"`.

```sh
python scripts/behavior_eval_receipts.py check \
  --request "$EVAL_PRIVATE/request.json" --receipts "$RECEIPTS" \
  > "$EVAL_PRIVATE/check.json"
```

The directory contains `<plugin>/<skill>.json` for each supplied receipt. The CLI reads these local files; it does not establish that their bytes are committed in C. A preparation check can use uncommitted receipt files. For an integrated candidate claim, the caller must read or verify the receipt bytes committed at C and supply those bytes to the checker.

For each required skill, the checker validates the record, matches the descriptor and original snapshot, verifies S is an ancestor of C, compares the complete bound inputs at both commits, and recomputes coverage and thresholds. It retains the parsed record’s `receipt_sha256` on acceptance and rejection, and reports `evaluated_revision` after the source and coverage checks complete. Missing or unparseable records have no parsed-record digest. Changes outside the declared evaluated closure can preserve the result; changes inside it require fresh preparation and observations.

| Outcome | Exit | Required action |
| --- | --- | --- |
| `pass` | `0` | Retain the check result and receipt identities for the consuming workflow. |
| `not-required` | `0` | Record that no skill required a receipt under this request’s inventory and diff. This does not prove inventory completeness. |
| `fail` | `1` | Inspect each skill’s reason: missing, stale, wrong-skill, malformed coverage, failed expectation threshold, or incorrect trigger evidence needs correction or fresh observations. |
| Per-skill `waiver-pending`, overall `fail` | `1` | Hand the recorded decision and release anchor to the owner of operator-authority and expiry verification. |
| `error` | `2` | Correct malformed request/JSON or unavailable inputs before retrying. During preparation, unsupported corpora also produce this outcome; during checking, a skill’s unsupported corpus or parsed receipt schema failure is a per-skill rejection. |

A waiver uses `$defs.waiver`: the bound snapshot and S, `kind: "waiver"`, a reason, `operator_decision` with `issued_by: "operator"` and the actual decision’s SHA-256 digest, `expiry` with `event: "next-release"` and its `after_release` anchor, and `attestation: null`. Record only an existing operator decision. A waiver must pass the same descriptor and freshness checks. The local checker cannot establish issuance or expiry and leaves an otherwise valid waiver pending with both verification flags false.

Checking is complete when every required skill has an explicit outcome tied to the requested revision and, for readable records, its receipt digest. Retain any unparseable raw receipt with the caller’s error evidence. A passing result covers ordinary result-data checks only; pending or failed evidence stays visible to the consumer.

## Acceptance and integration handoff

Run `python -m unittest tests.test_behavior_eval_receipts` and `git diff --check` for changes to this procedure or adapter. The tests construct local artifacts and Git histories; they establish adapter behavior, not live model execution or harness invocation. Review the procedure against its final tool, policy, and schema revision. Exercise positive and neighboring negative discovery separately from application success, failure, unsupported-input, waiver, and no-op branches; static review or a constructed receipt does not establish live agent behavior.

Shared source-stage validators, CI, disclosure, and readiness are integration work outside this standalone adapter. The integration owner supplies authoritative discovery for `skills`, `changed_skills`, and shared-reference effects, verifies committed receipt bytes at C, and preserves any independent readiness requirements. Publication-review receipts retain their separate purpose and format.

Before dependent execution, both [disclosure #28](https://github.com/nisavid/provingkit/issues/28) and [readiness #34](https://github.com/nisavid/provingkit/issues/34) must load this procedure and use its tool, policy, and schema from the same reviewed, published source revision. Record that procedure revision together with B, S, C, the request, the checked receipt digests, and the result. Disclosure consumes those identities and explicit outcomes; readiness requires passing ordinary checks or separately established waiver handling under its own contract. Feed a correction that changes the procedure’s meaning or input boundary back to its owner and refresh affected evidence.

Consumer invocation pointers, source-stage wiring, current procedure behavior evidence, and verification on the integrated published revision remain prerequisites for the complete [receipt work #33](https://github.com/nisavid/provingkit/issues/33). This document supplies the standalone procedure and required handoff; its presence does not establish that those integrations have occurred.
