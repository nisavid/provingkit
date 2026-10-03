# First commit-message observation attempt

The accepted Codex launch stopped before task delivery. It provides no
commit-writing observation, message-quality result, or verified review step
that a Jev assessment could replace.

The attempt used source commit
`73f0f2f2cfd71c69414bc0f7560d5c98575558d3` and prepared manifest SHA-256
`d52e4a75fa3f444d345c45c5db4b586c5655c1f4b0a854b66700a27e7939e754`.
The [public projection](first-attempt.json) retains the exact RPC error,
observed request sequence, counts, duration, and private artifact identities.
The original records remain intact; the failed fixture is not reused.

## What happened

Codex CLI 0.160.0 rejected `thread/start` with error `-32600`:
`thread/start.historyMode requires experimentalApi capability`.
The controller requested paginated history without declaring that capability
during initialization. It then treated the error response as an empty success
result and reported an instruction-source mismatch. No successful instruction
inventory was available to compare, so the mismatch label is not evidence of
profile drift.

Only initialization, its acknowledgement, model discovery, and thread creation
were sent. There was no `turn/start` request. The retained application files
match the initial fixture, Git status is clean, and no new commit or passive
observer record exists. Installed skill delivery, native permissions, and
authoring behavior remain unqualified.

The controller interval was 0.844029 seconds. No usage events were recorded;
that does not establish zero tokens, money, or quota consumption. Preparation,
metadata discovery, local checks, review, correction, and operator effort are
separate research costs. This attempt supports no economic comparison.

## Review and correction

Independent [outcome](outcome-audit.md) and [accounting](accounting-audit.md)
audits verified all thirteen frozen input identities before and after review.
Both identify the protocol rejection and misleading controller label. Their
filenames and line references refer to the retained private evidence; the
public projection supplies the relevant identities and facts without exposing
the installed profile or raw logs.

The corrected [controller](../jev-axi-commit-observation-2026-10-02/native.py)
declares `experimentalApi` and records RPC errors before interpreting success
fields. Local regressions reproduced both omissions and then passed after the
correction. These synthetic checks exercise the runner boundary; they do not
qualify another native episode.

Another episode requires a fresh fixture, reviewed source, and separate
execution acceptance under the [contract](../jev-axi-commit-observation-2026-10-02/contract.md).
The first attempt remains part of the result for
[Observe native commit-message writing and hook context](https://github.com/nisavid/provingkit/issues/406).
