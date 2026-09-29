# Prepare one disposable Desktop observation

This procedure prepares a bounded observation of one disposable Claude Desktop
Code task. The authorization ticket must identify the reviewed revision before
offering any live step described here.

## Entry conditions

The executor loads this procedure through `capturing-agent-procedures` and
records its immutable source revision. It must have a positive, scoped grant
from [Authorize the disposable Desktop observer probe](https://github.com/nisavid/provingkit/issues/279).
A closed prerequisite alone is insufficient. The grant must name the candidate,
fixture, data access, setup prompts, application changes, and restoration plan.

Use the inspected package and archive identities in
[packaging evidence](packaging-evidence.md). Assess a changed dependency through
release notes, byte comparisons, and affected source or synthetic checks.
A changed build is unassessed; demonstrated incompatibility disables the
affected function. Applying this exact patch requires its inspected source
bytes. An assessment that another version is compatible does not make these
replacement anchors apply to it.

The probe investigates getter availability, selected response fields, binding,
observation timing, and receiver effects. Current account/model/cwd semantics,
complete applied permissions, and native address binding remain open. It sends
no notification and supplies no delivery or acknowledgment evidence.

## Proposed application operation

Plan one scheduled window using the current signed-in profile. Follow
[application staging and restoration](application-operation.md) for the exact
preflight, backup, exchange, launch, and restoration sequence. The proposal
temporarily replaces the installed archive while preserving the installed
executable, native modules, launcher, and sandbox layout. The later grant must
cover this package-owned-file modification.

Before approving that route, identify a window in which Desktop can be closed
without interrupting unrelated work. Record the user's restoration expectations
for that work. If there is no such window, return to the operating decision;
do not switch to a copied runtime or disable sandboxing during execution.

Keep a verified pristine archive and the package identity outside the
experimental output directory. Build the candidate offline and compare every
member through the independent archive reader. Only the selected manager chunk
and added sidecar may differ. Record candidate, sidecar, manager, and build-input
digests. No source file from Desktop is published with this experiment.

Closing Desktop before staging and again before restoration requires two
application shutdowns and subsequent launches for this attempt. Installation success,
candidate loading, and restored application behavior are separate observations.
The authorization must acknowledge that existing queries need not survive a
restart. Collection is capped at 30 seconds; total window duration has not been
measured. A failed attempt does not authorize another arm or restart cycle.
Routine version changes do not automatically require another live window, and
notification sends do not each require a restart. Maintained observer
installation and upgrade behavior remain a later adoption decision.

## Disposable fixture proposal

Create one disposable Code task named `Desktop observer probe 278` in an empty
disposable worktree, using the current signed-in profile.
Do not select a historical or unrelated task. Record its exact task identity and
Code session identity using only the fixture-specific source approved by the
authorization. If those identities cannot be established, stop before staging.

The proposed source is the exact fixture metadata file described in
[the observation-path investigation](../../research/2026-09-29-desktop-observation-paths.md#acquisition-paths).
The grant supplies its complete selected path under the chosen Desktop profile,
account, and organization. Read that file's `sessionId` and `cliSessionId`;
require the former to equal the fixture identity chosen in the app. Do not scan
other sessions or read transcripts to obtain the latter. The file may lag the
running task, so the patched app must independently match both identifiers to
its current selected record and query before bootstrap and arm acceptance.

The proposed setup prompt is:

> This is a disposable observer fixture. Reply exactly `PROBE_READY`. Do not use
> tools, inspect files, change settings, or begin other work.

The authorization must explicitly cover two submissions of this text: one to
establish the fixture and its Code identity before staging, and one to establish
its query after the patched app starts. The second submission is a planned setup
action on that exact fixture. It is not an automatic observation fallback. If
the identity changes, stop and return the discrepancy for a decision.

Keep account, model, permissions, grants, and cwd unchanged during this probe.
Any deliberate transition requires its own reviewed proposal and grant. A
missing observation is a result to retain, not a reason to relax permissions.

## Candidate collection contract

The proposed sidecar is inactive without an explicitly selected configuration.
The configuration names the exact fixture, candidate identities, and a private
run directory. It waits a bounded time for that fixture's existing query. A
bootstrap record is inspected before a separate arm file permits collection.

`observer-probe.mjs` defines the exact configuration and arm schemas. Keep the
configuration outside the initially empty, same-owner `0700` run directory;
configuration and arm files are regular, single-link `0600` files. Set the
candidate and sidecar digests from the reviewed build receipt, the two verified
fixture IDs, a unique run ID, a 60-second setup deadline, and a 100-millisecond
setup poll interval. Supply its absolute configuration path as
`PROVINGKIT_OBSERVER_CONFIG` only for the experimental launch.

After bootstrap, compare every binding value to the granted fixture and
reviewed bytes. The `pid` and `processStartTicks` fields identify the app. The
operator-created arm echoes the binding keys and selects these proposed limits:
three samples, five-second minimum interval, 30-second observation window, and
two seconds per getter. The source accepts only one arm within 60 seconds of
bootstrap. The three calls are `accountInfo()`,
`getContextUsage({detail:"summary"})`, and `listPermissionRules()`, sequentially.
A timeout cannot cancel the original getter; it stops later calls and samples.
Elapsed-time limits use the monotonic clock. Wall timestamps describe the
observations and cannot extend collection authority.

Outputs are `bootstrap.json` and at most three numbered sample files. Each
sample is bounded at 16 KiB; the run output is bounded at 64 KiB. Samples record
each getter's availability or fixed failure class and before/after host
snapshots, including named gaps and whether the selected host values changed.
Settled getter failures preserve independent observations; a timeout records
the failing stage and ends collection. Use the strict reader with
the independently checked binding and a maximum age no greater than 30 seconds.
Every result remains unqualified. Preserve a failed or missing sample as such.

The proposed projection includes provider/source labels, the reported model,
permission rules and directory grants, skipped-settings error count, spawn
account/organization IDs, manager mode and last mode event, selected host
computer-use grants, pending/update markers, retained cwd, and the query-bound
Code process/version report. It excludes prompt/transcript contents, credential
values, environment contents, raw errors, and arbitrary object fields. Rules,
paths, and account identifiers still require explicit fixture-data consent.

Bind app process identity separately from query-reported Code process identity.
The [process-binding investigation](process-binding-evidence.md) identifies the
existing reports and their limits. The live grant must name any selected Linux
process fields and executable read before the executor uses them. Invoke
`observeSelectedLinuxExecutor` with the granted `runDirectory`, selected
`sequence`, independently checked `expectedBinding`, `maximumAgeMs`, last
consumed `afterSequence`, and the approved calling user's `expectedUid`. It
reads the selected sample itself, requires matching reports in both host
snapshots, checks process ownership before opening process files, and
revalidates sample freshness afterward. Retain its `sampleEvidence` with the
result. A selected
binary path, version string, or parsed PID does not establish the full
query-to-executable association.

## Restoration and return

Stop collection and close Desktop before restoring. Recheck the installed
package identity first. If an upgrade intervened, do not overwrite the new
package with the retained older archive; return for a restoration decision.
Otherwise restore the verified pristine archive and verify its bytes and
unchanged native assets.

Remove the probe configuration from the next launch, then verify the restored
app opens and the agreed unrelated-work expectations hold. Report disposable
fixture loss or changed task state separately from restored package bytes.

Propose retaining raw fixture outputs in the one private run directory through
the return decision, accessible only to the user and the authorized execution
and decision workflow. After that decision approves a redacted summary and the
evidence to keep, delete the manifest-listed disposable task, empty worktree,
configuration, and raw output. The later authorization must accept or amend
these terms. Do not publish private fixture observations automatically.

Return a report to
[Decide what the disposable observer probe establishes](https://github.com/nisavid/provingkit/issues/281)
with source/candidate identities, actual actions, getter and binding results,
receiver effects, restoration evidence, and unresolved requirements. Preserve
unknowns and carry them as blockers before the notification interface proceeds.
