# Representative native context for the supervision comparison

The two accepted passive episodes establish four Codex cadence-ten observations across successive requirements, but neither completes the representative workload. Claude stops at its first unavailable transcript capture. Codex completes the CSV and JSON requests, then reaches the accepted tool-count bound during sorting. These results qualify specific context and accounting observations; they establish no benefit from supervision.

I ran each episode once under the [accepted execution contract](https://github.com/nisavid/provingkit/blob/36df3997e04fb803aa314cf965fcbdb1a60257e8/docs/superpowers/research/evidence/sys1-representative-preflight-2026-10-01/contract.md). I retained both failures and made no retry, Jev assessment, steering emission, live-hook change, or upstream submission. The executed source remains unchanged at that commit. The [earlier four attempts](2026-10-01-jev-axi-passive-native-preflight.md) remain separate evidence and costs.

## Observations admitted

| Episode | Requests acknowledged / completed | Hook captures | Result and limit |
| --- | --- | --- | --- |
| Claude Code 2.1.284, requested Opus 5.5 at medium effort | 1 / 0 | One unavailable PostToolUse record; no captured context | Missing native transcript; no cadence or artifact result |
| Codex CLI 0.159.0, requested GPT-6.1-Sol at medium effort | 3 / 2 | 41 PostToolUse and two Stop, all captured | Cadence counts 10, 20, 30, and 40; first two artifact checks pass; sorting incomplete |

Model names and efforts describe requested settings and native reports, not independently attested provider execution. The [attempt projection](evidence/sys1-representative-preflight-results-2026-10-01/attempts.json) preserves versions, manifest identities, receipt counts, failure reasons, and measurement boundaries.

Codex's cadence-ten observation belongs to the first request; counts 20 and 30 occur after the JSON amendment; count 40 follows the sorting amendment. At count 40, the hook-time transcript includes all three task requests. The current `jev-axi` job field contains the first and latest requests and omits the separate intermediate request. That is an observed projection difference, not evidence of inadequate total input: the latest request explicitly retains JSON, and the event history contains JSON work. No classifier was asked to judge either input. The current event window keeps at most 30 events, with each input and result truncated to 400 characters.

The hook-time transcript can also lag the just-finished tool. At count 40, the extracted latest tool result still represents the preceding failing test, while the raw hook response contains the current passing result. Six native test executions report exit 1 followed by edits and successful executions. Native command items expose status and exit code; the Bash hook response carries combined text without a separate exit-code field. A proposed context-supplied arm must account for those timing and representation differences.

The saved CSV and JSON reports contain the expected category totals: tools 27, books 10, and art 10, in first-appearance order. The read-only artifact grader also finds only the required known report format and unchanged source CSV bytes at those completed turns. These checks inspect retained artifacts, not independent executions of the report generator or full validation of its CLI, documentation, tests, or unrelated-file preservation. No third-turn snapshot or completed sorting result exists. See [artifact snapshots and checks](evidence/sys1-representative-preflight-results-2026-10-01/artifact-checks.json).

Native test failures followed by fixes appear during legitimate development. They do not establish unproductive repetition or obsolete-requirement drift. Neither episode supplies a demonstrated intervention opportunity against those failure cases, and passive capture itself cannot establish steering benefit.

## Launch and measurement limits

I launched Claude inside the coordinator's outer tool sandbox, where its normal session store was read-only. Its first passive hook could not read a native transcript, and the controller stopped the attempt. Retained read-only filesystem checks show both clients' session stores were read-only under that outer sandbox and writable from the host. This supports the launch diagnosis; it does not substitute for a successful Claude capture. The failure belongs to experiment orchestration, not a Jev classification.

The still-unlaunched Codex episode used host process access for its ordinary session writes while preserving the frozen internal workspace-write sandbox, temporary-directory exclusions, settings, source, and bounds. It passed two Stop boundaries and reached the third request. The same Stop hook identifier appears in distinct turns, and the revised turn-scoped receipt handling accepts both. Those Stop captures preserve the baseline and before/after bookkeeping state. That launch correction supplies no containment claim and does not repair the failed Claude attempt.

The Codex profile inventory binds 123 listed skill entrypoints. Its observed `tdd` read matches the recorded bytes; this does not bind transitive references, every ambient instruction, or changing catalog metadata. A heredoc still reports read-only temporary-file creation despite the configured project-local `TMPDIR`, `TMP`, and `TEMP`. A later `python -c` command succeeds. The retained evidence does not establish the effective temporary path or environment that caused the failure, so native heredoc compatibility remains unqualified.

Sorting reaches a reported 17-test pass before another edit adds two tests. The final source has 19 tests without completed verification, its README lacks `--sort`, and its retained report remains unsorted. Those are unfinished obligations at interruption, not demonstrated requirement drift.

Codex stopped when the controller observed the 41st counted native item start. The accepted bound is an observation-and-stop guard at 40, not a hard preemption guarantee. The retained stream contains 41 distinct command-execution or file-change starts and 40 completed records of those types. It also contains 41 PostToolUse records; those identities are not interchangeable. One hook's tool identifier lacks a matching completed counted item. The failure was the tool-count bound, not the 480-second deadline.

The two completed-turn hook reconciliations establish aggregate event-count agreement. They do not join each native hook identity to an observer file. The third turn has no completed-turn reconciliation. The post-termination transcript is retained for accounting and later inspection; it cannot retroactively become input available at an earlier hook.

## Research costs

| Episode | Launcher interval | Latest retained reported input | Latest retained reported output |
| --- | ---: | --- | ---: |
| Claude, failed capture | 7.504 s | 2 ordinary; 6,121 cache creation; 0 cache read | 17 |
| Codex, interrupted during sorting | 461.661 s | 889,177, including 831,488 cached | 12,426, including 1,064 reasoning |

Claude's numbers come from one delivered assistant-message fragment. No terminal usage or monetary result was received. Codex's retained transcript contains 24 unique response-usage records, totaling 901,603 reported tokens. The first two turns account for 302,804 and 389,909; the incomplete third accounts for 208,890. These agree with the final retained cumulative counter. That counter includes 54,603 tokens absent from the controller's final delivered update of 847,000. Neither record guarantees that all provider work was reported. The [usage projection](evidence/sys1-representative-preflight-results-2026-10-01/reported-usage.json) keeps the delivered and post-termination scopes separate.

The two launch intervals total **469.166 seconds**. The span between the first launch and second termination is **702.425 seconds**, including an intervening **233.259 seconds** whose diagnosis, waiting, and operator-work shares were not measured. Launch intervals include local validation, native work, instrumentation, and shutdown. They are not complete research-workflow time.

Recorded hook-body intervals total 0.000612 seconds for Claude and 1.773762 seconds for Codex. Codex's native hook-completion durations total 4.483 seconds. These measurements have different, overlapping scopes; neither measures marginal instrumentation overhead. Add none of them to launcher elapsed or to one another. Cached input is already inside Codex input, reasoning is already inside output, and Claude's nested cache-creation fields repeat the same quantity.

Actual billing, attributable quota consumption, preparation and review model work, operator effort, diagnosis, maintenance, and concurrent-account effects remain unmeasured. The earlier attempts also remain part of the research cost. No economic ranking or complete cost-per-success follows from this batch.

## Comparison-contract join

The [retained-record inventory](evidence/sys1-representative-preflight-results-2026-10-01/retained-record-identities.json) binds 159 private original files. Public projections omit raw transcripts, inherited instructions, account information, and host paths. Digests preserve identity; they do not make private evidence publicly inspectable.

[Freeze the first jev-axi catalog comparison contract](https://github.com/nisavid/provingkit/issues/336) remains open. Codex now supplies actual cadence observations spanning the three requests, while Claude's representative capture and Codex's final task outcome remain gaps. No retained example demonstrates a native loop or requirement drift that supervision could usefully correct.

The next decision concerns the comparison's evidentiary scope and which missing observation would justify further native work. A future launch must also address or explicitly retain the unsuccessful shell-temporary behavior in its profile. More workload or higher bounds cannot by themselves create a valid benefit case. A narrower false-steering or context comparison would need its claim stated explicitly; it would not satisfy the accepted requirement for useful native intervention. Any further episode requires a reviewed contract and separate execution acceptance.

The accepted three assessment arms, conditional deterministic comparator, reliability bar, and cost priorities remain unchanged. The maintained `handling-sys1-incidents` procedure is consumed unchanged at `a999943377c1c3d0f83fa96163730eaf4756a878`. These experiment-specific observations add no installed convention or behavior assignment.
