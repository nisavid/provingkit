DONE

# SessionStart and Stop source-fact brief

The frozen canonical JSON plan, request, and binding hashes match the dispatch; every listed input matches its SHA-256. Binding: `09d5fb9a5ec82a53097cc44b66a5741bea1af661fb3f9ffde739cc60d4722586`. This is a read-only inventory using the research skill. No source, tests, hooks, provider calls, network, credential inspection, writes, or delegation occurred. Jev is the service; jev-axi constructs observations and selects actions. All upstream anchors below refer to revision `a1fe6190c65b528ad5b85cbe276fd4b68bdeb236`.

## SessionStart: declared context delivery, dependency boundary

The integration declares SessionStart hooks for Claude Code, Codex, and OpenCode to provide jev-axi ambient context. `setup hooks` passes user/project scope to `installSessionStartHooks` imported from `axi-sdk-js`; status delegates to that package too. The source here contains installation/status calls, not the injected payload, runtime input parser, provider behavior, cost, or failure handling. There is no basis in these calls to classify SessionStart as a Jev assessment. [Setup declaration and delegation][meta-start]

The manifest requires `axi-sdk-js ^0.1.12`; the lock resolves 0.1.12. That dependency's implementation is absent from this frozen source directory. The prior catalog report says it inspected dependency source and records configuration observations without comparative benefit qualification; that report does not supply replacement source anchors for the missing implementation. SessionStart's actual payload, consumer acceptance, configuration readiness checks, and runtime/provider cost therefore remain named uncertainties. [Manifest][manifest] [Lock][lock]

## Stop: observation and deterministic action

Stop accepts hook JSON from stdin, literal JSON, or a file through `--input`. It reads `cwd` (fallback process cwd), optional `session_id`, existing `transcript_path`, and `stop_hook_active`. It skips when already continuing from a Stop hook, when no job is extracted, or when no repository changes are available. Otherwise it assesses job, diff, and recent tool output; it does not include the retained event tail or worker questions. Stop requests a 10-second API timeout and zero client retries. [Stop intake][hook-stop]

The transcript reader recognizes selected Claude and Codex JSONL records, skips malformed or unknown lines, ignores prompt text beginning with `<`, and combines the first and latest distinct accepted prompts. Intermediate requests are not retained in the job. Output is the latest five captured tool-result strings, rather than a verification ledger. The reader explicitly describes both transcript formats as unstable. [Transcript extraction][transcript]

The four declared yes/no questions concern complete implementation, tests covering behavior changes, compliance with explicit requirements, and doubt about execution from failures or absent build/test output. The test and verification questions expressly accommodate requests forbidding tests or execution. These are questions put to Jev, not observed proof that work is complete. [Job questions][job-questions]

Scores are rounded before policy. Completion and requirement scores at or below 0.35 select continue. Both at or above 0.70 permit finish unless test sufficiency is at or below 0.35 or needs-verification is at or above 0.70, which select verify. High needs-verification also selects verify when completion is uncertain. Remaining intermediate completion cases select unclear continue. [Assessment and policy][policy] [Thresholds][thresholds]

Finish and unclear assessments produce empty hook output. Clear continue/verify produce a user `systemMessage` warning by default; with `--block`, they produce `decision: block` and a reason directing the agent to finish, verify, or explain completeness. The stop-active guard prevents a second immediate intervention. These JSON shapes express intended harness consumption; this inventory did not observe delivery or continuation. [Output policy][hook-output]

## PostToolUse bookkeeping changes what Stop can judge

The baseline is captured on the first recorded PostToolUse event, after that tool has run, not at SessionStart. Recording stores a stash-created unreferenced commit if available, otherwise HEAD, plus then-existing untracked paths. Stop uses this session baseline when present; without it, diff construction falls back to HEAD and then an ordinary diff. Consequently the source shape does not guarantee a baseline from before the first tool's changes, and missing bookkeeping changes which changes Stop sees. [Baseline and diff][diff] [Session persistence][sessions]

Diff construction includes tracked changes relative to the baseline and eligible new untracked files, excludes credential-file paths, excludes previously untracked paths, and skips unreadable, binary-looking, or over-256-KiB untracked files. Observation construction keeps the first 20,000 diff characters and the last 12,000 output characters, with pattern-based secret redaction. Job text keeps its first 4,000 characters but is not passed through `redactSecrets` in this function. Redaction is a source transformation, not a confidentiality qualification. [Diff filtering][diff] [Observation construction][observation] [Redaction][redaction]

PostToolUse requires a session ID and records tool name, serialized input, and serialized response before the cadence/job checks. It retains 30 events, each with the first 400 input characters and last 400 result characters. Default assessment cadence is every tenth tool; `--every` overrides it. Assessment needs an extracted job and uses a six-second timeout with zero retries. Worker questions ask about progress, repetition, unrelated work, and human-only blockers. Meaningful-progress scores do not affect verdict selection. A needs-human score at or above 0.70 precedes stuck/off-track steering; escalation is logged quietly, so it can suppress a steering note. [PostToolUse intake][hook-stop] [Persistence][sessions] [Worker questions][worker-questions] [Policy][policy]

The installed supervision pair has no matcher, declares Stop timeout 20 seconds and PostToolUse timeout 15 seconds, and targets Claude/Codex settings. PostToolUse steering emits additional context; continue/escalate are quiet. All successful non-explain verdicts are best-effort logged to `stats/supervise.jsonl`; `--explain` suppresses that verdict log, but PostToolUse still records its session event. Parse/input failures occur before the advisory catch; assessment, transcript, Git, or persistence exceptions inside it return empty output, optionally exposing a skip reason in explain mode. [Installation][installation] [Intake and catch][hook-stop] [Logging and output][hook-output]

## Configuration, cost, and evidence limits

Assessment shares `evaluate`: cached observations can return without a provider request; live calls use TypeSafeClient's `systemOne` with state, questions, and model. Default cache TTL is 24 hours, disabled by `JEV_AXI_NO_CACHE=1` or nonpositive configured TTL; keys include model, state, and questions. Recorded alias changes invalidate older model results. Default model is `jev-latest`, overridden by explicit model, environment, or configuration. API-key precedence is environment, nearest searched dotenv, then configuration. These are source paths; actual configuration, keys, availability, billing, quota, and end-to-end hook latency were not inspected. [Client/cache][client] [Live request][live] [Configuration][config]

The frozen report `docs/superpowers/research/2026-10-01-jev-axi-retained-boundary-comparison.md` (SHA-256 `d2e0afdfe416bf94b5bae71b7e62d45ba3ac829d4829d2ba851d2645ea025c46`) concerns four PostToolUse boundaries and eight Jev requests: it observed proposed output, delivered no steering, and continued no native task. It explicitly excludes Stop interactions, other supervision purposes, and whole-workflow economic ranking. It supplies no SessionStart/Stop acceptance claim.

Minimum source-grounded case dimensions are: valid/missing/changed transcript formats; amended requests omitted between first/latest prompts; first-tool changes versus later changes; missing/stale session bookkeeping; committed changes, preexisting dirt, excluded untracked files, and truncation; clear unfinished/unverified versus complete/uncertain work; threshold-adjacent rounded scores; stop-active replay; API/cache/configuration failures; malformed intake; warning versus blocking delivery; and PostToolUse cadence, quiet escalation, and event persistence. These are candidate case dimensions, not chosen acceptance requirements.

The consequential open decisions are which SessionStart context effect and Stop completion effect should be assigned, what useful result must beat ordinary agent work and omission, and what interruption/blocking and complete workflow costs are acceptable. Those decisions remain with the operator. Missing SDK source and native delivery evidence must be supplied if those behaviors enter the claim.

[meta-start]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/commands/meta.ts#L219-L250
[manifest]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/package.json#L49-L53
[lock]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/pnpm-lock.yaml#L14-L19
[hook-stop]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/commands/hook.ts#L141-L189
[transcript]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/supervise.ts#L134-L184
[job-questions]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/recipes/questions.ts#L332-L356
[policy]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/supervise.ts#L60-L87
[thresholds]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/recipes/questions.ts#L379-L394
[hook-output]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/commands/hook.ts#L190-L204
[diff]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/supervise.ts#L91-L132
[sessions]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/supervise.ts#L186-L230
[observation]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/supervise.ts#L41-L58
[redaction]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/safety.ts#L35-L47
[worker-questions]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/recipes/questions.ts#L358-L377
[installation]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/commands/hook.ts#L209-L247
[client]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/client.ts#L94-L146
[live]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/client.ts#L214-L290
[config]: https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/config.ts#L28-L167
