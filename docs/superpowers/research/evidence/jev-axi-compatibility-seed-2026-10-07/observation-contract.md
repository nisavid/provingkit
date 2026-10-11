# Observe compatibility work after an amended requirement

This observation records how an ordinary Codex author adds JSON output while preserving existing report consumers after a requirement amendment. It looks for a concrete remaining need for compatibility assistance, a distinct review step that a later candidate could replace, or avoidable reconstruction work. It does not test Jev, choose a classifier, or establish an error rate.

This proposed execution contract joins the collector, final evidence, completion grading, and coordinator accounting. Its private invocation binding supplies exact local paths, source and profile identities, and the prepared manifest. All required bindings and independent reviews must be complete before execution acceptance. This document alone accepts no episode or live change.

## Frozen invocation

The proposal is one episode, one initial task, and at most one amendment. There is no retry, replacement workload, replacement turn, automatic answer to an input request, or second model run prompted by grading. A failed or incomplete attempt remains the result of this invocation.

| Binding | Required value at the join |
| --- | --- |
| Source | Published collector, transport, Git-evidence helper, seed producer, comparator, ledger implementation, and corresponding clean review identities |
| Preparation | New prepared manifest path and SHA-256; exact seed receipt, seed spec, case inputs, delivered requests, implementation-trigger paths, initial Git receipt, and native profile |
| Profile | Reviewed native executable/version, selected author model and effort, applicable instructions and authoring/review resources, omission overlay, capabilities, permission handling, and child-dispatch behavior |
| Native limit | Exact prepared limit, collection-byte ceiling, and shutdown handling. Current source proposes 3,600 seconds, 64 MiB, and two five-second shutdown waits; those values have not been accepted for an episode. |
| Coordinator work window | Proposed 9,000 seconds beginning immediately after actual execution acceptance, before final freshness/admission checks, through preservation, grading, analysis review, and prepared handback; exact accepted value, clock binding, stop rules, and preservation after expiry |
| Evaluation | Exact comparator and cases, this completion-grading procedure, evidence selectors, and final-source retention rules |
| Accounting | Full recurring-preparation-to-handback clock, separately measured acceptance waiting and coordinator work window, event format, model/rate sources where available, scope of observed token counters, and explicit gaps |

The invocation is not ready while a required binding is absent. Refreshing a model/profile or changing a material source invalidates its affected review and prepared identity. Preparation-only metadata calls create no author thread or turn. Proposed durations are contract choices awaiting acceptance, not accepted budgets or demonstrated enforcement.

## Commands and native profile

The private binding assigns every shell variable below to a literal path or digest and records the command bytes. All evidence destinations are new and outside the worker project. Metadata preparation creates no author thread or turn.

```sh
python "$SOURCE/prepare_seed.py" --spec "$SEED_SPEC" --output "$PACKET"
python "$SOURCE/collect_observation.py" prepare --native \
  --native-executable "$CODEX" --native-executable-sha256 "$CODEX_SHA256" \
  --model gpt-6.1-sol --effort medium \
  --seed-package "$PACKET" --seed-receipt-sha256 "$SEED_RECEIPT_SHA256" \
  --implementation inventory_format.py --implementation bin/inventory-report \
  --implementation bin/low-stock --implementation jobs/archive-inventory.py \
  --output "$OBSERVATION"
```

The proposed author is Sol 6.1 Medium. Its exact selector/effort and installed CLI/profile must be supported by the captured metadata before acceptance. The profile retains installed authoring and review resources, including the required review loop, adjudication, and revision resources. It sets no observation-specific two-child cap. Actual permitted dispatch remains governed by the captured native configuration and installed procedures; discovery alone does not prove the review will finish or all child evidence will be visible.

The collector starts a direct app-server process with per-invocation overrides. It disables `hooks`, `plugin_hooks`, `memories`, `apps`, `shell_snapshot`, `browser_use`, `computer_use`, and `image_generation`; keeps plugins and multi-agent support enabled; disables web search and configured MCP servers plus the two plugin-provided servers identified in source; and provides the disposable project as the trusted task root. Its shell environment has no inherited variables and sets LANG, LC_ALL, PATH, and a project-local TMPDIR. The profile and executable identities include the concrete settings and resources used.

The cooperative `AGENTS.override.md` omits Jev and `jev-axi` while retaining other standing instructions. It does not establish adversarial containment. Thread and turn requests explicitly select the author model/effort, project cwd and runtime roots, empty environments, `on-request` approvals reviewed by the user, and workspace-write tools with no network or implicit temporary-directory roots. Returned thread model, effort, and roots must match; relevant settings notifications are checked when received. Unrelated provider/tier metadata and an absent settings notification do not introduce a new gate. These request/response checks do not establish native enforcement.

After actual execution acceptance and coordinator admission, invoke once:

```sh
python "$SOURCE/collect_observation.py" run \
  --manifest "$OBSERVATION/manifest.json" \
  --expected-sha256 "$MANIFEST_SHA256" --accept-native
```

This single call owns task delivery, the automatic once-only amendment, process shutdown, final source retention, and final Git capture. The coordinator must not send a second amendment or repeat capture by treating the accounting phases as extra actions. Retain the call's stdout, stderr, exit status, and duration. Internal phase timing comes only from supported retained records; an indivisible outer call does not establish separate observed durations for each internal phase.

## Preparation and ordinary work

Start the outer UTC/monotonic record before the recurring copy and profile preparation for this episode. Earlier equipment development and creation of the reusable seed are research construction costs, recorded separately with their original evidence or an explicit unknown; they are not assigned zero cost or silently included in a later measured interval.

Prepare the declared seed and the exact two requests. The agent receives the seed, its README and ordinary tests, the omission overlay approved by the profile join, and applicable installed authoring instructions. Keep constructed candidates, their labels, the comparison script, grading notes, final oracle, and observation records outside the worker project.

Initialize that copied project as a fresh local Git repository after the overlay is present and before native metadata discovery. The supplied Git helper constructs the baseline with recorded Git plumbing: `init --initial-branch=compatibility-observation`, `add --force --all -- .`, `write-tree`, `var GIT_AUTHOR_IDENT`, `var GIT_COMMITTER_IDENT`, `commit-tree`, and `update-ref`. It retains the seed commit's raw metadata and verifies root, branch, tracked paths, status, remotes, and regular-file inventory. Bind its executable identity and command records. Effective Git identities come from the recorded Git environment/configuration; do not override them or attribute baseline preparation to the author.

The seed commit is not an ordinary `git commit` invocation. These records do not establish that ordinary commit hooks or author review ran; hook configuration, signing behavior, and any unobserved external effects remain unknown unless separately supported by retained evidence. The helper observes empty remote output and clean status for its baseline. It rejects an existing Git metadata path, unsupported nonregular source entries, or a baseline mismatch; failed preparation is retained and no task is delivered.

The helper's regular-file inventory excludes `.git`, `__pycache__`, `*.pyc`, and `*.pyo`. Its baseline tracked-path check compares Git's tracked list with that inventory. State correspondence only for that declared inventory and retained command scope. Each recorded Git command has a proposed ten-second collection timeout; this is neither a hard whole-workflow deadline nor evidence that any command ran in this observation.

Immediately before thread/task delivery, verify the bound baseline commit, intended branch, observed absence of remotes, initially clean working tree, seed modes/content, and profile identity. The supplied Git preflight also verifies the Git executable identity and baseline regular-file inventory. Metadata discovery may produce files; an unexpected dirty tree is a concrete preparation mismatch to resolve before proposing a fresh accepted package. Do not quietly discard or ignore those files to obtain a clean result.

Retain actual execution acceptance as a separate event bound to the exact contract and prepared manifest. Start the proposed 9,000-second coordinator work window immediately after that acceptance, before final freshness/admission checks. Full elapsed accounting still starts before recurring preparation and includes measured acceptance waiting. Waiting for acceptance alone cannot expire a work window that has not started. Acceptance does not waive a freshness mismatch, required review, or failed admission.

Deliver the exact first request: add the JSON shape `inventory-report/v1`, initially make JSON the default, share the inventory-collection path between formats, preserve input/filter/exit behavior, update tests and documentation, complete required checks and review, and make a local task commit. No publication is requested.

After the first completed tool item for which a declared seed implementation path differs from its initial bytes, send the exact amendment once to the active thread and expected turn: JSON becomes opt-in; omitted `--format` must preserve existing callers, including `bin/low-stock` and `jobs/archive-inventory.py`. Test-only and documentation-only changes do not trigger it. Record the tool identity, changed-path hashes, event time, outgoing bytes, response, and actual returned turn ID. Do not inspect whether the implementation is wrong before sending the amendment.

At each supported root-turn tool start and completion event, retain a complete regular-file inventory with paths, content hashes, sizes, and modes. Use the same exclusions as final-source capture. Bind each inventory to the original event and tool item, including its command and output when supplied. Record the scan's start, finish, and elapsed duration as collection work. A failed scan retains its partial entries and error, with no complete inventory identity. These scans do not alter the amendment trigger.

RPC acceptance establishes server acceptance, not comprehension. A rejected steer, missing trigger, completed-turn race, input request, failed profile check, native deadline, or failed capture is retained without manufacturing the missing opportunity. A completed author turn does not establish task completion.

## Terminal capture

Keep the final native outcome even if later Git or source capture fails. Once the author process has stopped, collect the following without changing the candidate:

1. The existing wire and ordered receipt records, including delivered requests, amendment acceptance or failure, tool events, input requests, final reports, and usage observations through the actual retained boundary.
2. The independent `final-source/` tree and `final-source.json` already produced by the collector. Preserve modes, added and removed files, and capture gaps. Its existing exclusions and non-atomic nature remain explicit.
3. The supplied helper's final Git receipt and underlying command records: repository root, HEAD, named/detached/unavailable branch observation, baseline reachability, raw commit metadata/messages since the seed, raw status, cumulative committed paths and binary patch from seed to HEAD, staged patch, unstaged patch, untracked paths, and remote output. Retain argv, any recorded stdin, exit statuses, stdout/stderr bytes, timestamps, and command failures. A missing repository or commit is evidence, not permission to repair the worker result.

The helper records regular-file inventories before and after read-only Git capture. It reports `matched-at-recorded-boundaries` only when both equal the complete supplied final-source inventory; otherwise correspondence is unverified and capture is incomplete. This does not establish continuous stability between reads or atomic Git/source correspondence. Retain both observations and their times; do not choose whichever snapshot produces the most favorable grade. Failures, a changed Git executable, and unsupported source entries remain capture gaps.

Raw commit metadata and the cumulative seed-to-HEAD patch do not reveal every intermediate commit's diff. Grade the final committed task change relative to the seed and the retained final working-tree/index state. Whether every intermediate commit excluded unrelated changes remains unverified without additional retained evidence; this draft adds no such collection.

Preserve every failed preparation/attempt directory. A later attempt requires a new directory and separate acceptance. Do not overwrite the earlier result.

## Behavioral evaluation

Run the frozen comparator only after the author stops and final-source capture is complete. Use the clean prepared packet's `seed/` as `--before`, the independently retained `attempt/final-source/` as `--after`, and the bound packet `cases/` as `--contract-cases`. Write to a new grading directory outside both trees:

```sh
python compare_behavior.py --before "$PACKET/seed" --after "$OBSERVATION/attempt/final-source" --contract-cases "$PACKET/cases" --output "$GRADING/behavior"
```

The concrete contract substitutes the bound paths and source identities. Do not use the live Git project as either comparator source: the comparator's source inventory traverses `.git`, and subsequent author activity would also break the captured-candidate comparison.

The oracle covers default and explicit text output, consumer compatibility, JSON schema and records, filtering, empty and zero-stock results, supported identities, and invalid inputs. Record its commands, raw results, return code, source rechecks, and summary. `compatible`, `different`, and `observation_failed` remain distinct. A successful oracle result says nothing by itself about documentation, developer tests, independent review, sharing the implementation, or the local commit.

The amended requirement is the grading target only for the intended amended-work observation when the amendment RPC was accepted. If delivery was rejected or never occurred, label that an observation/delivery gap. Any run of the amended oracle in that case is a diagnostic counterfactual; it cannot establish that the author violated a requirement it was not shown. Retain the first-request outcome separately where evidence permits.

## Completion grading

Complete one assessment over the captured candidate, using [the completion template](completion-grading-template.json). Every requirement receives `satisfied`, `unsatisfied`, `unverified`, or `not_applicable`, with exact evidence selectors and a short explanation. `not_applicable` needs a reason grounded in the delivered requirements; capture failure is not such a reason.

| Required work | What establishes it | What does not |
| --- | --- | --- |
| Final report and consumer behavior | Frozen oracle observations against the captured candidate, with their source rechecks | A completed native turn or an author's summary |
| Shared collection path | Semantic source inspection showing that text and JSON consume the same inventory-selection/validation result; internal names/layout may change | Matching output alone or existence of a helper with an appealing name |
| Documentation | Captured user guidance accurately describes the preserved default, opt-in JSON, supported filter/schema, and relevant command examples | A changed README filename or a statement that docs were updated |
| Developer tests | Captured changed/added tests cover the requested behavior, and retained tool evidence establishes execution of the required repository test command on the applicable final candidate | The research oracle, test-file existence, or an uncorroborated author claim |
| Required independent review | Underlying critic/adjudicator/required loop results and their candidate identities, with no unresolved valid findings and a clean current pass under the bound installed procedure | A root message saying “review passed”, a child-completed notification alone, or review of a superseded candidate |
| Task-only final local commit | Final Git evidence establishes the final task change relative to the seed, with intended final changes committed and unrelated final changes excluded | A seed commit, a commit message alone, clean status without a post-seed commit, or a claim about every intermediate commit inferred from a cumulative patch |
| No publication requested | Retained observed commands and baseline/final remote information, stated only for their observation scope | An absolute guarantee that no unobserved external action occurred |

Use native event ranges for test commands/results and review reports already delivered through the author stream. Additional child-history or artifact collection is not implicit in this draft. If the existing stream omits the required report or binding, mark review unverified. Do not rebuild a purported review from the author's prose. If additional collection is necessary for the contract's purpose, prepare and bind that collection before requesting acceptance.

For each required author test, match its original command and successful result to the same thread, turn, and tool item. Require complete start and completion inventories that both equal the complete final-source inventory before recording correspondence at those boundaries. A later edit to any included file or mode invalidates the earlier match; a later qualifying test may restore it. A missing start event, failed inventory, unmatched item, or absent command/result leaves correspondence unverified. Inspect test adequacy separately. Equal inventories describe non-atomic reads made when the collector receives events: they do not establish continuous stability, exact execution-time filesystem state, or the absence of intervening changes and reversions. Keep any event-delivery or concurrent-edit uncertainty explicit rather than promoting a match to stronger proof. Source correspondence also does not establish independent review.

Grade final quality separately from opportunity. A defect found and fixed by the ordinary author is not a missed final obligation. Record its timing and the work spent correcting it. That may justify a hypothesis about earlier assistance, but it does not demonstrate savings. A distinct message or review step counts as a replacement opportunity only if the retained evidence identifies the actual work and its inputs; do not infer it from a skill name.

Keep native/task outcome, collection completeness, candidate correspondence, behavioral result, completion grading, and accounting state separate. Local checks establish only their exercised synthetic boundaries; the actual native observation remains unqualified until run and inspected.

## Whole-invocation accounting

The outer record remains open after native execution. It closes only after terminal capture, grading, required independent analysis review, and the ordinary prepared handback, including failures and any operator recovery. Full elapsed time runs from recurring preparation to that close. Known acceptance waiting is separately measured within it; unobserved waiting is unknown. Earlier recurring preparation and waiting remain in full elapsed/cost totals even though they precede the coordinator work window.

The proposed coordinator work window begins immediately after actual execution acceptance and expires 9,000 seconds later. The collector's proposed 3,600-second native process limit, collection ceiling, and two five-second shutdown waits are separately bound. Coordinator admission verifies freshness, clock continuity, and that the complete configured native allowance plus declared shutdown waits fits in the remaining work window. Admission does not guarantee that grading or handback finishes before expiry.

At coordinator-window expiry, start no discretionary new work, comparison, retry, or substitute episode. Retain the current process outcome and complete minimum necessary preservation and assessment of work already incurred; record later intervals and work-window overrun. Expiry does not waive required review, answer an input request, renew authorization, or authorize a retry or replacement. The record/coordinator stop rules do not establish collector preemption or hard whole-workflow enforcement.

Each phase records a unique ID, purpose, recurrence, actor, source/artifact references, UTC and monotonic start/end where observed, and measurements with `observed`, `derived`, `estimated`, `unknown`, `not_applicable`, or `invalid` status. Shared work is allocated once; overlapping intervals are not added to obtain elapsed time. Clock/boot mismatch invalidates affected durations rather than subtracting unrelated counters. Use the measurement statuses in [the accounting command plan](accounting-command-plan.md); do not call the ordinary provider runner's slot-specific lifecycle for this native observation.

Record recurring copy/Git/profile preparation; acceptance waiting; final freshness/admission checks; native author work; observable child/reviewer work; test and correction work; amendment collection/delivery; shutdown/capture; behavioral evaluation; completion grading; independent analysis review; operator effort/interruptions/recovery; and handback. Record equipment construction separately. A voluntary operator record remains optional, and missing effort remains unknown.

Index the retained tool-inventory scan durations as observation overhead within the native interval. Do not add them again to whole elapsed time. The surrounding collector and record-write work remains part of that outer interval; scan durations alone do not measure all collection overhead.

Retain root and observed other-thread token counters exactly as reported, including cache/reasoning partitions where present. Verify their cumulative scope before deriving a root delta. Do not sum root and child counters without evidence of inclusion and overlap, and do not infer complete child usage from the events received. Report equivalent API value only for counters whose model/rate/partition mapping is supported; otherwise record a reason for null value. Actual charges and subscription capacity usage remain separate, with no token-to-quota conversion. This single observation cannot establish economic superiority.

The [accounting command plan](accounting-command-plan.md) defines coordinator-owned records and their producer. Bind and review its final inputs before execution acceptance. It does not add collector interfaces or automated whole-workflow preemption.

## Handback and next decision

Report delivery validity, native outcome, final capture correspondence and completeness, behavioral outcome, each completion obligation, observable ordinary corrections/review work, full elapsed time, acceptance waiting, work-window timing/overrun, and accounting gaps before any aggregate conclusion. Preserve successful ordinary behavior and absent opportunities as valid findings.

If the evidence identifies a material missed requirement, avoidable operator reconstruction, or a verified review step, propose the smallest later comparison that could discriminate ordinary reasoning, a meaningful deterministic aid, omission, and a narrow semantic judgment. Otherwise retain the absence of a demonstrated opportunity without claiming general uselessness. No outcome of this observation authorizes a live hook change or an upstream submission.

Consume the maintained `handling-sys1-incidents` comparison contract at its frozen revision. Any useful reusable correction must return to that maintained procedure only after it is demonstrated and reviewed; this draft creates no new installed convention.
