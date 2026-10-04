# Stop preparation: current intent and completion boundaries

Stop source preparation identifies the context needed to investigate unmet current requirements; it does not establish useful correction, a removable review step, or authority to change hooks. The frozen tracker records acceptance of the family purposes and bars in [Define purposes and acceptance bars for the remaining jev-axi hook families](https://github.com/nisavid/provingkit/issues/339#issuecomment-5961665316), despite the earlier draft's proposed-language header. The accepted Stop purpose is to catch unmet current requirements, including required tests or verification, for an agent claiming completion. The later recorded decision settles the bounded commit-message cycle without advancing an assessment and moves preparation to SessionStart/Stop with no live change.

All 21 frozen inputs matched their recorded SHA-256 before and after this research. The plan's canonical JSON hash and request's UTF-8 hash matched their recorded identities. This work used research and the maintained comparison procedure through capturing-agent-procedures. It ran no source, tests, hook, native episode, provider request, or network operation and wrote no files.

## What reaches the current check

At jev-axi revision `a1fe6190c65b528ad5b85cbe276fd4b68bdeb236`, Stop takes an existing transcript path, repository cwd, optional session ID, and stop-active flag. It skips an active Stop continuation, an absent extracted job, or absent repository changes. Its assessment receives only job, diff, and recent tool output. It requests a 10-second provider timeout and zero client retries. Warning is the default; clear continue/verify verdicts can block with `--block`, while finish and unclear verdicts are quiet. These are emitted-output mechanics, not observed native consumption. [Stop intake and output][hook]

The transcript reader retains the first and latest distinct accepted prompt, excluding malformed/unknown records and prompt text beginning with `<`. With multiple prompts it initially bounds each end to 2,000 characters; observation construction then bounds the combined job to 4,000. Intermediate amendments, withdrawals, and clarified referents can therefore be absent. Keeping the latest prompt does not guarantee that it restates every current requirement. Selected Claude/Codex record formats are supported by source parsing; the source explicitly calls those formats unstable. [Transcript extraction][transcript] [Observation construction][observation] [Bounds][questions]

Stop does not extract assistant final text or a structured completion/pause/handoff kind. The captured output is the last five selected tool-result strings, further bounded to the last 12,000 characters. A pause instruction could appear in an accepted prompt, but the current check has no separate observation establishing that a Stop event means the agent claimed completion. A turn ending after a requested bounded handoff and a turn claiming the whole job done require distinct labels grounded in the actual episode. This is an input gap for the accepted purpose, not an observed false warning. [Transcript extraction][transcript] [Stop intake][hook]

The four Jev questions ask whether the diff implements the job, covers behavior changes with same-diff tests or an applicable exception, obeys explicit requirements, and leaves execution in doubt. The last question treats absent build/test output as doubt unless the job forbids execution. Existing tests outside the diff, previously completed checks displaced from the output tail, documentation-only tasks, and task-specific verification beyond builds/tests need observed context before judging sufficiency. Scores answer the supplied questions; they are not a completion certificate. [Declared questions][questions]

## Baseline timing and change coverage

The first recorded PostToolUse event captures the baseline, after that tool has executed. It tries `git stash create`, then HEAD, and stores the then-existing untracked paths. This is not a SessionStart baseline. First-tool tracked edits can enter the stash snapshot, and first-tool new files can enter the excluded untracked set. Those effects follow from the source ordering; this research did not run them. [Baseline][diff] [Recording][sessions]

Stop compares against the stored baseline when available. Without a usable baseline it falls back to HEAD, then a plain diff. With a baseline, committed and uncommitted tracked changes can be included. Previously untracked paths, credential-file paths, unreadable files, binary-looking untracked files, and untracked files larger than 256 KiB are excluded; ignored files are not enumerated. The assessment keeps only the first 20,000 diff characters. Thus no changes, excluded changes, and truncated changes must be distinguished from complete coverage. Session state stores no cwd binding, and the session filename sanitizes and truncates the ID; actual session/repository correspondence also needs observation. [Diff construction][diff] [Session state][sessions] [Bounds][questions]

Baseline-relative context can omit implementations already present before recording, while fallback HEAD context can include unrelated preexisting dirt. Neither boundary alone establishes which current requirements were fulfilled. A later contract needs task-owned change identity and explicit coverage exclusions rather than equating diff absence with completion.

## Ordinary work and the PostToolUse join

No frozen input verifies a distinct completion-review step that Stop removes. A prescribed review is not an observed review, and the commit-message decision's lack of a removable message-review step does not settle completion review. Observe the agent's ordinary requirement reconciliation, checks, completion report, pauses, and handoffs before describing any candidate as a replacement. A check leaving ordinary review in place is an addition. Omission and deterministic checks remain eligible comparators; a deterministic missing-check rule also needs observed current requirements and matching check evidence.

The [retained PostToolUse comparison][comparison] observed eight requests at four retained Codex boundaries. Combined context additions removed one unnecessary proposed note in that sample. No steering was delivered and no native task continued. It explicitly leaves Stop interactions and useful native benefit unqualified. The source facts about truncation remain reusable; those output results cannot be transferred to Stop.

PostToolUse records events and captures the baseline before cadence or missing-job skips. It writes the session file on each event, retains 30 bounded events, prunes old state on first recording, and assesses every tenth event by default. Stop reads its baseline/untracked state, not its worker-event tail. Removing PostToolUse assessment need not mean removing bookkeeping, but removing its invocation would remove this baseline producer. Any proposed variant must join with that owner and identify which retained mechanics and costs remain. No such variant is selected here. [Recording][sessions] [Invocation ordering][hook]

Measure bookkeeping separately from assessment: hook startup, first baseline Git operations, session reads/writes and pruning, transcript scans, Stop diff construction, cache reads/writes, service attempts, logs, delivered interruptions, review/recovery, operator effort, and maintenance. Shared state and service work are charged once with explicit allocation. The client logs historical usage on cache hits with zero recorded assessment milliseconds; summing those tokens as new service consumption or treating that zero as end-to-end latency would be unsupported. Actual billing, constrained capacity, whole-hook latency, and bookkeeping cost remain unknown. [Client accounting][client]

## Minimal passive prerequisites and next consumer

Before proposing a runnable observation contract, establish the permitted bounded capture route and retain:

1. An ordinary task's harness/model/source/dependency/configuration identities, ordered requests and amendments with origin, and current requirement reconciliation at each selected Stop boundary.
2. Actual boundary meaning: completion claim, explicit pause, or bounded handoff; plus available hook fields, transcript records, constructed job/output, skip reason, and missing context.
3. Baseline capture ordering, first relevant tool's changes, session/repository correspondence, tracked/untracked/ignored coverage, and identities of task-owned changes and required check results.
4. Ordinary review/check work and its result, separate from the act of writing the final response; enough evidence to determine whether a named removable step exists.
5. Measurement routes for all recurring work above, including failed/skipped attempts, cache state, enclosing wall duration, operator effort, and unknown components.

Use benign evidence and preserve access/publication limits. Capturing a future episode is a separate decision; this prerequisite list authorizes no episode, Jev request, hook change, or experiment. Completion/unmet requirement, amendment/obsolete requirement, pause/completion, sufficient/missing verification, and full/partial change coverage are proposed case dimensions, not frozen cases or accepted experiments.

[Establish context and baselines for session-start and completion checks](https://github.com/nisavid/provingkit/issues/399) owns this context/baseline preparation. Its next qualification consumer is a bounded Stop passive-observation contract, joined with the PostToolUse bookkeeping owner before a variant or assessment contract. The maintained `handling-sys1-incidents` source at preparation base `b7811223315cd0dc9f644b4679585652267df21e` has SHA-256 `1d28f851542a0c7a11a190772630c941f224de5da7b4a776c3e62bcc6a3769ac`; its comparison contract has SHA-256 `9f876cd27c4bd6fe82d56feabc6e31e05d029d7cac18f9651194218e2e1aa981`. [Maintained procedure][method]

The comparison contract already requires current-intent context before judgment, observed ordinary work, complete accounting, distinct classification/delivery/outcome evidence, and explicit execution acceptance. It fits this prospective consumer unchanged. This preparation is not a newly witnessed incident, so incident-intake steps are not invented. No method correction is supported here; the coordinator must preserve the invocation, revisions, gaps, and prerequisite join when integrating the handback.

[hook]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/commands/hook.ts#L141-L204
[transcript]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/supervise.ts#L134-L184
[observation]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/supervise.ts#L41-L58
[questions]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/recipes/questions.ts#L332-L394
[diff]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/supervise.ts#L91-L132
[sessions]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/supervise.ts#L186-L230
[client]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/client.ts#L214-L290
[comparison]: https://github.com/nisavid/provingkit/blob/b7811223315cd0dc9f644b4679585652267df21e/docs/superpowers/research/2026-10-01-jev-axi-retained-boundary-comparison.md
[method]: https://github.com/nisavid/provingkit/blob/b7811223315cd0dc9f644b4679585652267df21e/.agents/skills/handling-sys1-incidents/references/comparison-contract.md
