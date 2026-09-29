# Sys1 approval-recovery evidence

Inspect the bounded recovery comparison through its [report](../../2026-09-29-sys1-approval-recovery-results.md), [contract](../../2026-09-29-sys1-approval-recovery-contract.md), and retained records below.

| Record | What it establishes |
| --- | --- |
| [Policy results](policy/results.jsonl) and [summary](policy/summary.json) | 288 constructed policy/adapter cases with fixed diagnostic answers. No native effects. |
| [Built-hook checks](built-policy/summary.json) | Four complete hook CLI calls; one reached the offline judgment transport. |
| [Native selection](recovery-native-selection.json) | Six distinct mechanisms and 22 selected cases per harness, frozen before trials. |
| [Claude summary](recovery-claude-summary.json) and [episodes](claude/) | 22 episodes, 33 user turns, 19 proposals, ten denials, and nine completed files. |
| [Codex summary](recovery-codex-summary.json) and [episodes](codex/) | 22 selected episodes, 31 user turns, 18 proposals, six denials, and 12 completed files. Four selected episodes use separate model-free reanalysis; three additional model attempts remain unqualified. |
| [Codex observer amendment](recovery-codex-r6-amendment.json) | Prospective observer and path-spelling corrections, with earlier records preserved. |
| [Source texts](sources/) | Inspection-only projections of the runners, observers, hooks, and constructed checks. Original source hashes accompany each projection. |
| [Projection inventory](projection.json) | Selected original records and SHA-256 values, projected file hashes, and selection descriptions. |

Paths identifying this host are replaced with `<NATIVE_FIXTURES>`, `<PROVINGKIT>`, `<JEV_BUILD>`, `<RESEARCH_SCRATCH>`, `<HOME>`, or `<CLAUDE_TRANSCRIPT>`. Claude streams retain synthetic user messages, visible assistant text and tool calls, effective initialization fields, and final results. Other events and reasoning are omitted. Four omitted native permission-denied events duplicate denial text retained in tool results.

Codex packets retain synthetic prompts, hook receipts, selected native history and tool outputs, effective permission metadata, diagnostics, and fresh-reader evidence. They omit reasoning, unrelated inherited instructions, and account or connector identity. A projection digest is not an original-record digest. The source texts have not been executed after path replacement and do not provide a portable reproduction package.

The experiments used fixed retained scores and an exact-message authorization oracle. They measured recovery and task behavior; no unauthorized proposal reached a native intervention. They establish neither classifier accuracy nor added safety value. The original failed observations, their later reanalysis where available, and unreached continuations remain distinct.

Jev-derived material retains the adjacent [MIT license](../sys1-2026-09-26/JEV-LICENSE.txt). Fixtures are retained as local research records; no live hook configuration or upstream submission is part of this evidence publication.
