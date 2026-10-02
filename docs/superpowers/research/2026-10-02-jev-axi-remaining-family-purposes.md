# Source facts for the remaining hook purposes

The remaining `jev-axi` hook families contain several different assignment
questions: context delivery, judgment before a tool call, completion review,
staged-change review, commit-message review, and push-range review. Their source
mechanics do not establish that any of them improves a native task or replaces
expensive-model work.

This brief supports [Define purposes and acceptance bars for the remaining
jev-axi hook families](https://github.com/nisavid/provingkit/issues/339).
The [accepted supervision disposition](https://github.com/nisavid/provingkit/issues/338#issuecomment-5959242739)
advances neither tested assessment package. It preserves the added context as
an unqualified research candidate and changes no live configuration. The
earlier note-removal and authorization-workflow decisions retain their scope.

## Evidence and unresolved decisions

Two parallel read-only scouts inspected the audited integration at
`a1fe6190c65b528ad5b85cbe276fd4b68bdeb236`. Their exact returned briefs and
digests are retained for [session/completion behavior](evidence/jev-axi-remaining-family-purposes-2026-10-02/session-completion-source-brief.md)
and [Git hooks](evidence/jev-axi-remaining-family-purposes-2026-10-02/git-hooks-source-brief.md).
The coordinator checked source anchors and separately read PreToolUse,
the dependency behind SessionStart, and the pre-commit diff reviewer. Those
supplements are identified below; they do not retroactively expand what the
scouts inspected.

No hook, test, native workload, installation, or Jev request was run. This is
descriptive source evidence, including the names and routing of security-related
checks; it does not evaluate their security efficacy. The selected research
models and evidence limits are in the [research records](evidence/jev-axi-remaining-family-purposes-2026-10-02/research-records.json).

| Family | Source behavior and immediate consumer | Purpose to settle before comparison |
| --- | --- | --- |
| SessionStart | Runs the CLI's home view to provide command, readiness, usage, cache, and update information to the agent; no Jev assessment in that path | Whether ambient information changes useful tool selection or avoids discovery work enough to justify its recurring context and startup cost |
| PreToolUse | Applies a local routine-call rule, otherwise asks Jev five hazard questions and a damage score, then selects allow, ask, or deny | Which consequential mistakes merit another check beyond ordinary reasoning and native permissions, with matched legitimate actions and adequate intent context |
| Stop | Assesses implementation, requirements, tests, and verification from a bounded job/diff/output snapshot; may warn or block | Whether it catches unfinished requested work the agent would otherwise leave, or can replace a named completion-review step without reducing quality |
| pre-commit | Scans staged additions locally for credential patterns, then assesses chunked diff content for risk, tests, credentials, and leftovers | Separate the consumer of deterministic findings from the consumer of semantic review; identify any actual agent review displaced or additional defect caught |
| commit-msg | Assesses message/diff agreement and subject usefulness; checks convention deterministically after the assessment succeeds | Whether semantic checking adds useful correction or can replace an existing message review; format compliance needs its own deterministic comparison |
| pre-push | Assesses a selected commit range for missing migration notes, sensitive areas, hand-edited generated files, and leftovers | Whether push-time findings change a useful next action beyond earlier reviews, and whether the input actually covers what is pushed |

These are proposed purposes, not accepted assignments, reliability thresholds,
or experiment permission. Ordinary harness behavior, meaningful deterministic
alternatives, and omission remain eligible. A replacement needs an observed
step to remove; an addition needs an observed useful effect. Quiet diagnostic
scores still need a named consumer and demonstrated benefit.

## Coordinator supplements

### SessionStart supplies context rather than an assessment

The local dependency resolves to `axi-sdk-js` 0.1.12. Its `dist/hooks.js`
constructs a SessionStart entry whose command is the resolved executable, with
no command arguments. Its `dist/cli.js` routes an empty argument list to the
registered home handler. The integration registers `homeCommand` in
[`src/cli.ts`](https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/cli.ts#L117-L127).

[`homeCommand`](https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/commands/home.ts)
reads configuration and key availability, usage/cache summaries, command
guidance, and update information. It calls no Jev assessment. The
[`update check`](https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/update.ts)
can contact the npm registry when enabled and its cached check is old; its
configured fetch timeout is one second. No actual startup latency, network
request, context delivery, or downstream tool selection was observed here.
The dependency files' hashes are retained in the
[supplement identities](evidence/jev-axi-remaining-family-purposes-2026-10-02/supplement-source-identities.json).

### PreToolUse asks about location and hazards without current task intent

[`buildSafetyState`](https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/safety.ts#L202-L228)
constructs tool/cwd and command or file/content fields, with bounded local
script excerpts for recognized in-project scripts. It does not add the current
task requests or approval history. The
[`questions`](https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/recipes/questions.ts#L284-L328)
cover irreversible damage, private-data transfer, unreviewed remote code,
weakening controls, outside-project changes, and damage if the action were a
mistake. Those categories alone do not establish whether an action was wanted.

The source's
[`decision and adapter`](https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/safety.ts#L246-L288)
select thresholds and convert asks to denials for Codex. The
[`error policy`](https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/commands/hook.ts#L108-L139)
defaults to deny for API rejection and allow for other assessment errors.
Future evidence must separate input adequacy, classification, integration
policy, native permission handling, and actual action outcomes. Earlier
authorization comparisons do not qualify these broader hazard purposes.

### Pre-commit's shared reviewer has additional scope limits

The scout identified `reviewFiles` as a dependency missing from its frozen
packet. The coordinator read
[`src/commands/diff.ts`](https://github.com/nisavid/jev-axi/blob/a1fe6190c65b528ad5b85cbe276fd4b68bdeb236/src/commands/diff.ts#L103-L174).
It scans locally for strong and possible credential patterns, truncates and
redacts per-file patches, chunks them, and submits per-file questions. Overall
scope and kind questions accompany only the first chunk. The per-file
`behavior` answer is requested but not consumed by this reviewer.

Test filenames and matching filename stems affect whether a needs-test score
becomes a flag. Risk, secrets, and leftovers also become flags. These are
deterministic interpretations of returned answers, not demonstrations of test
coverage or protection. The pre-commit caller returns its clean message when
there are no flagged files or local secret hits; a scope-only concern therefore
does not reach that caller's warning branch. A future comparison must account
for this actual consumption rather than grading every requested score as a
delivered intervention.

## Comparison boundaries to retain

Stop uses bookkeeping captured by PostToolUse, so omitting the recurring
assessment is different from deleting the state on which completion review
depends. Its first/latest request extraction, baseline timing, truncation,
uncertainty, planned pauses, and requested handoffs need explicit treatment.

Git comparisons need legitimate contrasts such as intentional fixtures,
deliberate TODOs, tests outside the source patch, fixup/squash messages,
migration notes outside commit subjects, generated files, and multi-ref or
repeated pushes. Context availability, skips, cache hits, service failures,
and unused answers belong in accounting. A declared check and a delivered
useful result remain separate observations.

The next discussion selects the leading purpose, whether verified replacement
opportunities are in scope, and the initial scope of security-related claims.
The resulting family-specific criteria and runnable comparisons remain to be
accepted. Source findings for independent families can proceed in parallel;
execution waits for their own contracts and shared-resource coordination.
