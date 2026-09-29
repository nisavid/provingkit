# Prepare one disposable Desktop observation

This procedure prepares a bounded observation of one disposable Claude Desktop
Code task. The authorization ticket must identify the reviewed revision before
offering any live step described here.

## Entry conditions

The executor loads this procedure through `capturing-agent-procedures` and
records its immutable source revision. It must have a positive, scoped grant
from [Authorize the disposable Desktop observer probe](https://github.com/nisavid/provingkit/issues/279).
A closed prerequisite alone is insufficient. The grant must name the candidate,
fixture, data access, setup prompts, application changes, launcher and argument
identities, cleanup terms, and restoration plan.

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

## Application operation

Use the selected installed-archive route during one scheduled window in the
current signed-in profile. Follow
[application staging and restoration](application-operation.md) for the exact
preflight, backup, exchange, launch, and restoration sequence. The route
temporarily replaces the installed archive while preserving the installed
executable, native modules, launcher, and sandbox layout. The later grant must
cover this package-owned-file modification.

Before approving that route, identify a window in which Desktop can be closed
without interrupting unrelated work. Record the user's restoration expectations
for that work. If there is no such window, return to the operating decision; do
not switch to a copied runtime or disable sandboxing during execution.

Keep a verified pristine archive and the package identity outside the
experimental output directory. Build the candidate offline and compare every
member through the independent archive reader. Only the selected manager chunk
and added sidecar may differ. The generated `build-receipt.json` is output tied
to the candidate archive. Retain it in the reviewed source as
`candidate-build.json` only after complete archive verification and manager and
sidecar syntax checks. The generated and retained receipts must compare byte
for byte before authorization and again before staging. Record candidate,
sidecar, manager, and build-input digests from that receipt. No source file from
Desktop is published with this experiment.

Closing Desktop before staging and again before restoration produces two
application restarts in the one scheduled window: the candidate launch and the
restored launch. Installation success, candidate loading, and restored
application behavior are separate observations. The authorization must
acknowledge that existing queries need not survive a restart. Collection is
capped at 30 seconds; total window duration has not been measured. A failed
attempt does not authorize another arm or restart cycle. Routine version changes
do not automatically require another live window, and notification sends do not
each require a restart. Maintained observer installation and upgrade behavior
remain a later adoption decision.

The private packet binds the launcher's digest and owner, group, mode, device,
inode, link count, and size. It also binds the exact NUL-delimited argument-file
identity and reconstructed byte digest. Revalidate the package, protected
assets, root-owned launcher ancestry, launcher, and stable-descriptor argument
read immediately before both launches. Execute only the validated in-memory
argument array. These checks narrow the mutation window but do not make launch
atomic.

## Disposable fixture

Create one disposable Code task named `Desktop observer probe 278` in a
dedicated empty disposable worktree and project, using the current signed-in
profile. Do not select a historical or unrelated task. Record its exact task
identity and Code session identity using only the fixture-specific source
approved by the authorization. Require no parent, child, shared-task,
shared-project, or shared-worktree links. If those identities or isolation
conditions cannot be established, stop before staging.

The selected source is the exact fixture metadata file described in
[the observation-path investigation](../../research/2026-09-29-desktop-observation-paths.md#acquisition-paths).
The grant supplies its complete selected path under the chosen Desktop profile,
account, and organization. Read that file's `sessionId` and `cliSessionId`;
require the former to equal the fixture identity chosen in the app. Do not scan
other sessions or read transcripts to obtain the latter. The file may lag the
running task, so the patched app must independently match both identifiers to
its current selected record and query before bootstrap and arm acceptance.

The setup prompt is:

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

The sidecar is inactive without an explicitly selected configuration. The
configuration names the exact fixture, candidate identities, and a private run
directory. It waits a bounded time for that fixture's existing query. A
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
operator-created arm echoes the binding keys and selects these limits: three
samples, five-second minimum interval, 30-second observation window, and two
seconds per getter. The source accepts only one arm within 60 seconds of
bootstrap. The three calls are `accountInfo()`,
`getContextUsage({detail:"summary"})`, and `listPermissionRules()`, sequentially.
A timeout cannot cancel the original getter; it stops later calls and samples.
Elapsed-time limits use the monotonic clock. Wall timestamps describe the
observations and cannot extend collection authority.

Outputs are `bootstrap.json`, `arm.json`, and at most three numbered sample
files. Each sample is bounded at 16 KiB; the run output is bounded at 64 KiB.
Samples record each getter's availability or fixed failure class and
before/after host snapshots, including named gaps and whether the selected host
values changed. Settled getter failures preserve independent observations; a
timeout records the failing stage and ends collection. Use the strict reader
with the independently checked binding and a maximum age no greater than 30
seconds. Every result remains unqualified. Preserve a failed or missing sample
as such.

Each of the initial and final selected-executor sample acquisitions reads the
nonsecret Linux boot identifier once from the single path
`/proc/sys/kernel/random/boot_id`. It reads no other path to discover a PID.
The boot identifier and `linux-clock-monotonic.v1` bind the sample's monotonic
timestamps to the current boot. Direct calls to `readProbeSample` or
`inspectProbeSample` must pass explicit contemporaneous `now` and
`monotonicNow` values, the expected binding's `monotonicClockId` and
`linuxBootId`, and the approved maximum age. The selected-executor observer
samples both clocks after the boot-ID read, rechecks them after each awaited
sample acquisition, and checks them again after the selected PID's owner
directory check immediately before opening its process files. Either clock
regressing or exceeding the maximum age stops the observation before those
opens. Active-profile or clock uncertainty remains unqualified.

The projection includes provider/source labels, the reported model, permission
rules and directory grants, skipped-settings error count, spawn
account/organization IDs, manager mode and last mode event, selected host
computer-use grants, pending/update markers, retained cwd, and the query-bound
Code process/version report. It excludes prompt/transcript contents, credential
values, environment contents, raw errors, and arbitrary object fields. Rules,
paths, and account identifiers still require explicit fixture-data consent.

Bind app process identity separately from query-reported Code process identity.
The [process-binding investigation](process-binding-evidence.md) identifies the
existing reports and their limits. The live grant must name any selected Linux
process fields and executable read before the executor uses them. Invoke
`observeSelectedLinuxExecutor` with the granted inputs defined by the final
reviewed source. It reads the selected sample itself, requires matching reports
in both host snapshots, checks process ownership before opening process files,
and revalidates sample freshness afterward. Retain its sample evidence with the
result. A selected binary path, version string, or parsed PID does not establish
the full query-to-executable association.

## Restoration, retention, and return

Stop collection and close Desktop before restoring. Recheck the installed
package identity first. If an upgrade intervened, do not overwrite the new
package with the retained older archive; return for a restoration decision.
Otherwise restore the verified pristine archive and verify its bytes and
unchanged native assets.

Remove the probe configuration from the restored launch environment, revalidate
the launcher and arguments, then verify the restored app opens and the agreed
unrelated-work expectations hold. Report disposable fixture loss or changed
task state separately from restored package bytes.

After restored behavior is checked, create the private cleanup manifest defined
by [application staging and restoration](application-operation.md). It binds
the exact source and artifact identities, disposable task and Code IDs,
dedicated project and worktree, configuration, output root, and every emitted
file. Retain raw fixture output and that manifest through the return decision,
accessible only to the user and the authorized execution and decision
workflow.

After the decision approves a redacted summary and names the exact manifest
subset to remove, use only Desktop's normal exact-task deletion UI. Source
inspection shows that managed deletion may cascade to the selected task's
worktree and transcript, so task deletion requires confirmed isolation and a
live confirmation scope matching only the fixture. Do not call internal session
deletion methods or add cleanup instrumentation. If the UI control is absent or
its scope is broader, retain the fixture for an operational decision.

Delete approved user-owned configuration and output files one exact
manifest-listed path at a time after type, identity, ownership, containment,
size, and digest checks. Use `unlink` for files and `rmdir` only for verified
empty owned directories. Do not use globs or recursive removal, delete Desktop
private profile stores or transcripts manually, or alter unrelated worktrees.
Unapproved paths remain retained.

Return a report to
[Decide what the disposable observer probe establishes](https://github.com/nisavid/provingkit/issues/281)
with source/candidate identities, actual actions, getter and binding results,
receiver effects, restoration evidence, cleanup-manifest identity, and
unresolved requirements. Preserve unknowns and carry them as blockers before
the notification interface proceeds.
