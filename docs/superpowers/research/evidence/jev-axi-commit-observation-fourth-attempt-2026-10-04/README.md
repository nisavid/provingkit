# Commit-message observation: one completed task, one runtime evidence gap

Codex implemented the report-sorting task, ran six passing CLI tests, and created
one local commit. The passive hook captured the message and staged change that
became that commit. The controller nevertheless returned `native-incomplete`
because no turn-settings notification was recorded. Task and Git observations
remain separate from complete runtime qualification.

This fourth accepted invocation used the unchanged runner at
`cd83ef70e4585e4a82724634118fac31f88b1689` and manifest SHA-256
`0594b2e364548bb18369468f59324df5b7b6e4d54b1abd5a0f84a593bc3ee676`.
The three earlier attempts remain recorded: [protocol negotiation](../jev-axi-commit-observation-attempt-2026-10-03/),
[plugin-server configuration](../jev-axi-commit-observation-second-attempt-2026-10-03/),
and [prepared-profile drift](../jev-axi-commit-observation-third-attempt-2026-10-03/).
No automatic retry followed this result.

## Retained result

The local fixture commit is `8c3726d2b373a82fef266e98beb874b7e4da13ab`, with
message `feat: add item report sorting modes`. The [raw message](message.bin),
[compressed staged patch](staged.patch.gz), and [observer record](record.json) retain the hook's
inputs. The index tree and parent match the final commit; the staged patch equals
the committed change when using the same diff prefixes. Message content matches
after trailing newlines are removed. The observation equipment is unchanged and
the final working tree is clean.

The change adds `--sort input|item|total`, preserves input order by default,
orders totals descending with ascending name ties, and rejects invalid values
before replacing a report. The retained native trace records six passing tests
after the commit, including existing input behavior and the added sort cases.
The [published seed](../sys1-representative-preflight-2026-10-01/representative-workload/project/)
and retained patch make the application change inspectable without the private
native trace. The gzip file decompresses to the exact recorded patch bytes;
compression preserves Git diff context-line whitespace without treating it as
new documentation whitespace.

The message accurately summarizes the material change. The README has one minor
ambiguity: its total-sort example is followed by sample CSV in default input
order without labeling that order. This remains part of the observed task
quality; the fixture has not been repaired after measurement.

The trace includes whole-diff inspection, tests, staging, one message supplied
to `git commit -m`, and post-commit verification. These are observations of the
workflow, not proof that internal message review was absent. Message accuracy,
task quality, and any separately replaceable review work are assessed in the
independent [outcome audit](outcome-audit.md). That audit found no separate
message-review operation that a replacement could demonstrably remove.

## Runtime and accounting limits

Startup matched the prepared instructions and 179 skills. All twelve connector
entries reported disabled states and zero tools before task delivery. The
recorded task text matches the accepted prompt. The turn completed successfully,
and a full, unpaginated history was retained. The controller's additional
requirement for a recorded effective turn-settings notification was unmet;
startup settings and requested turn settings do not replace that missing
observation. The original failure status remains intact. Stderr also retains
MCP startup and authentication warnings, including a transport authentication
error at shutdown. Disabled thread tools do not establish an absence of ambient
connector startup or network activity; those costs remain unmeasured.

The launch interval was 125.470495 seconds; the native turn reports 124.348
seconds. There were 25 distinct tool items and no child dispatches or permission
requests. The process exited zero. All 492,702 stdout bytes were consumed by the
callback, with no undelivered stdout; 20,542 stderr bytes bring the combined
received output to 513,244 bytes, below the 2 MiB bound.

Eleven usage events were retained. The final reported cumulative fields are
350,760 input tokens, 311,296 cached input tokens, 3,092 output tokens, 72 reasoning
output tokens, and 353,852 total tokens, with zero cache-write input tokens.
These are the endpoint's fields, not quantities to add together or convert to
money or quota. The [accounting audit](accounting-audit.md) reconciles those
observations. Setup, metadata discovery, earlier failures, correction work,
reviews, and operator interruptions remain separate research costs. No isolated
message-review cost or whole-workflow savings follows from this episode.

The [structured projection](observation.json) records hashes and scoped facts;
raw profiles and native logs remain private. The passive observer performs no Jev assessment. This result selects no added
or replacement assessment and changes no live hook. The next
comparison decision belongs to [Freeze the commit-message agreement comparison contract](https://github.com/nisavid/provingkit/issues/402).
