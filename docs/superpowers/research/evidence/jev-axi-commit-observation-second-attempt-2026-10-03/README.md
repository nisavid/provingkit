# Commit-message observation: connector mismatch

The second accepted launch created an idle Codex thread and passed the prepared
instruction-source and skill-inventory checks. It stopped before task delivery
because two plugin servers remained connected. Commit-writing behavior and a
separately replaceable review step are still unobserved.

The attempt used source `9c813973f721f14923ee9ca73be387a5c819356d` and manifest
SHA-256 `0db25cdfcc4c1c7232b3996425b34382fbeef27a23fa159e5943c230df7cd110`.
The [public projection](second-attempt.json) records the observed connector
identities, counts, timing, and retained private artifact identities.
Independent [outcome](outcome-audit.md) and [accounting](accounting-audit.md)
audits verified all seventeen frozen inputs. The original fixture and logs
remain intact alongside the [first attempt](../jev-axi-commit-observation-attempt-2026-10-03/).

## Observed boundary

The thread reported the requested startup permissions and the prepared global
instruction source. Skill discovery matched all 179 entries. These observations
do not establish turn-time permissions, skill invocation, or model behavior.

Ten MCP servers reported disabled states and no tools. `cua_repl`, identified
as belonging to `unified-computer-use@openai-bundled`, reported three tools;
`fork-ops`, identified as belonging to `fork-ops@fork-ops`, reported fourteen.
Both reported connected states. The runner's connector guard refused the
profile before sending `turn/start`. Its configured-server overrides had not
covered these plugin-provided servers.

No task prompt, new commit, observer record, or usage event was recorded. The
application-file hashes were unchanged and Git status was clean. The controller
interval was 1.264549 seconds. The 141,089 received bytes comprise 138,468 stdout
bytes and 2,621 stderr bytes; all stdout was callback-consumed, with no
undelivered stdout. Plugin startup occurred, and its costs remain unmeasured.
No usage event does not establish zero provider usage, cost, or network activity.

## Preparation correction

The [profile](../jev-axi-commit-observation-2026-10-02/profile.py) supplies
per-plugin server policies for the two observed servers while leaving their
plugins enabled. The bindings
cover this installed profile; a different active server still prevents task
delivery.

Preparation also queries the MCP tool inventory without creating a thread.
A [retained preparation failure](metadata-preparation-failure.json) exposed a
second distinction: that query returned empty tools but unavailable runtime
states. The initial check mislabeled those unavailable states as active
connections. The corrected check requires no exposed tools and records that
thread-runtime disablement remains unqualified. The native runner still
requires explicit disabled states from its actual thread before task delivery.

Local regressions reproduced the plugin-server omission and unavailable-status
case before the fixes. The corrected preparation completed with empty tools
and unchanged skill identities. This is metadata evidence, not a third native
authoring episode or a behavior-assignment result. A fresh source-bound manifest
and separate execution acceptance are required for another episode under the
[contract](../jev-axi-commit-observation-2026-10-02/contract.md).
