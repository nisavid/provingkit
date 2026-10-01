# Native context evidence for the supervision comparison

The four accepted passive episodes establish several Claude Code and Codex hook input shapes. Three reached normal terminal outcomes. The fourth stopped because the controller rejected a Codex Stop hook ID reused in a later turn. Neither harness establishes the complete three-turn PostToolUse context contrast, and none of these episodes establishes a benefit from supervision.

I retained all four attempts, including the failed attempt and its usage. I made no retry, Jev assessment, live-hook change, or upstream submission. The source that ran remains unchanged at [the reviewed preparation checkpoint](https://github.com/nisavid/provingkit/tree/588b54afc3f54940e4d6eaf7271401f9f7b9089d/docs/superpowers/research/evidence/sys1-supervision-preflight-2026-09-30). The operator accepted its [four-episode contract](evidence/sys1-supervision-preflight-2026-09-30/contract.md); the configured deadlines totaled 960 seconds. Actual execution occurred on October 1 UTC, September 30 in the operator's time zone.

## What the episodes establish

| Episode | Ordered turns acknowledged / reconciled | PostToolUse / Stop captures | Supported observation | Remaining limit |
| --- | --- | --- | --- | --- |
| Claude parser | 1 / 1 | 5 / 1 | Native terminal success, Bash call/result pairing, available transcript captures, preserved baseline | No cadence-ten opportunity or established native nonzero command-exit case |
| Claude report | 3 / 3 | 6 / 3 | Same-session CSV, JSON, and sorting instructions; the sorting-turn transcript contains the intermediate JSON amendment | No cadence-ten opportunity, so no actual PostToolUse assessment-input contrast |
| Codex parser | 1 / 1 | 9 / 1 | Native completion, command status/exit/output and patch shapes; a command with exit 1 triggers PostToolUse | No cadence-ten opportunity; inherited skills and a shell temporary-file error affect the profile |
| Codex report | 2 / 1 | 12 / 1 | First turn reconciles; JSON amendment acknowledged; count ten records a current observation containing JSON | Controller aborts at the second Stop start; no second terminal result or sorting delivery |

These are per-property admissions. The passive hook ran the original `jev-axi` event recording, cadence, and baseline mechanics, but omitted assessments and emitted no steering. Native run IDs and observer capture IDs were reconciled by event counts, not joined individually.

At the Claude sorting boundary, the native transcript contains both amendments. The final Stop observation's first/latest projection contains the sorting request and omits the intermediate JSON request. That is observed Stop projection loss. Applying it to a cadence-ten PostToolUse input is still source inference: this episode never reaches ten. The revised README and report files also contain the JSON requirement, so omission from the job field alone does not establish inadequate total context or a wrong judgment. Codex's sole cadence-ten opportunity occurs during the JSON turn, before a sorting request is delivered.

Both parser artifacts remove the same erroneous absolute-value conversion. After inspecting their source, I checked each against the nine independent literal CLI examples; both passed. The read-only report checker accepts Claude's retained sorted JSON and Codex's retained JSON in source order. Both source CSV files remain unchanged. Those report checks inspect artifacts; they do not execute or independently qualify the report generators. The partial Codex result cannot pass the undelivered sorting task.

The [attempt projection](evidence/sys1-supervision-preflight-results-2026-10-01/attempts.json), [artifact checks](evidence/sys1-supervision-preflight-results-2026-10-01/artifact-checks.json), and [original record identities](evidence/sys1-supervision-preflight-results-2026-10-01/retained-record-identities.json) carry the supporting quantities and private-record digests. Raw transcripts remain private because they include inherited host instructions and skill content.

## Preparation defects and profile observations

Codex emits the same Stop hook ID in two different turns. The original controller keyed its receipt table by hook ID across the entire session, so it rejected the second invocation as a duplicate. The retained native stream establishes this implementation defect; it is not evidence of task or supervision failure. A process exit also does not substitute for a native terminal receipt: Claude processes exit 143 after controller termination on completion, while the failed Codex report process exits 0 without the required terminal callback.

A separate candidate correction keys receipts by session, turn, and hook ID. Its new regression failed against the original parser, then passed after the correction; all eight local checks pass. Read-only replay of the retained Codex receipts accepts the second Stop start and still rejects reconciliation because that Stop never completed. The correction therefore does not turn the old failed episode into a pass. The [candidate patch and local checks](evidence/sys1-supervision-preflight-results-2026-10-01/README.md) have not run in a new native episode.

Both Codex episodes report the requested exclusions for general temporary-directory writes. Their heredoc commands nevertheless emit a temporary-file error while the enclosing compound command returns exit 0. Later commands recover using `python -c`. Missing writable shell scratch under that profile is the working explanation, not a proven containment result. A revised preparation needs project-owned temporary space and a direct check before another task run; the native acceptance remains pending.

Codex also receives an inherited skill catalog and reads the installed `tdd` and `diagnosing-bugs` skills. Disabling skill search did not remove those inputs. The contract did not promise Codex read isolation, so these reads are profile dependencies to bind or deliberately change before comparison. Claude reports an empty skill inventory, while its commands see additional profile paths in the sandbox view; those listings do not establish persistent fixture modifications. These observations cannot be credited as supervision effects.

## Research costs

| Episode | Measured launch interval | Reported input | Reported output |
| --- | ---: | --- | ---: |
| Claude parser | 27.703 s | 12 ordinary; 9,286 cache creation; 37,308 cache read | 1,811 |
| Claude report | 43.545 s | 18 ordinary; 11,179 cache creation; 80,913 cache read | 4,202 |
| Codex parser | 58.191 s | 171,262, including 143,744 cached | 1,296 |
| Codex report, censored | 113.722 s | 251,824, including 221,440 cached | 2,990 |

The four launch intervals total **243.161 seconds**. They include launch checks, native work, instrumentation, and shutdown within each invocation. The 38 capture-body intervals total 1.599 seconds and overlap those launch intervals; they exclude hook process startup and native scheduling. Do not add them to elapsed time or treat the episodes as an assessment-arm latency comparison.

Claude report mixes per-turn `usage` and `duration_ms` with cumulative `modelUsage`, `total_cost_usd`, and `duration_api_ms`. I use its final cumulative values once. Codex's latest retained cumulative totals are 172,558 and 254,814 tokens; cached input is already inside input, and reasoning output is already inside output. The censored report still incurs the reported work: its completed first turn reports 143,627 tokens, with another 111,187 reported before interruption.

Claude reports list-basis costs totaling **$0.3077442** for these two sessions. These are native estimates, not actual charges or quota consumption. Codex monetary cost, billed charges, constrained capacity, preparation, review, diagnosis, maintenance, and operator effort remain unmeasured. Failed qualification is research work, not a zero-cost omission. No whole-workflow economic ranking follows from this preflight.

## Join and next work

Independent context/outcome and accounting inspections verified the same eight dispatch inputs and 183 frozen record files before and after inspection. Their [joined disposition](evidence/sys1-supervision-preflight-results-2026-10-01/inspection-reviews.json) admits the input facts above and retains the missing coverage.

[Freeze the first jev-axi catalog comparison contract](https://github.com/nisavid/provingkit/issues/336) remains open. Its full comparison is not yet ready to execute. The next preparation must:

1. Qualify turn-scoped hook receipts, provide usable project-local shell scratch, and bind or deliberately revise the inherited Codex profile.
2. Decide how ordinary developer tasks will provide meaningful native opportunities for the agreed loop/repetition and drift/authorized-change contrasts. These small tasks do not establish the intended cadence coverage. Do not add ceremonial tool calls, force mistakes, lower cadence silently, or count a delivered note as benefit.
3. Freeze only the affected follow-up qualification, with retained failures, complete cost scopes, and independent reviews, before requesting its separate execution acceptance. Reuse supported facts instead of rerunning completed cells merely to obtain a preferred outcome.

The accepted three assessment arms, the conditional deterministic comparator, and the reliability and cost priorities remain unchanged. This result selects no behavior assignment. The maintained `handling-sys1-incidents` procedure remains unchanged at its recorded revision; this report is a consumer of that method, not a new generic procedure.
