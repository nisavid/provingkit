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

The accepted operating shape is one scheduled window and two full application
shutdown/launch cycles: the candidate cycle and the restored cycle. It also
contains two submissions of the exact setup prompt, the package, receipt,
protected-asset, launcher, argument, fixture, and directory preflight checks,
the archive exchanges, restoration checks, and retained-artifact construction.
Installation success, candidate loading, and restored application behavior are separate observations. The
authorization must acknowledge that existing queries need not survive a
restart. Collection is bounded by preventing getter initiation, clamping
asynchronous waits, and rejecting settlements at or after the 30-second
monotonic observation deadline. Uncancellable or synchronously blocking getter
work can outlive that deadline; the source does not provide hard cancellation.
The operating-window description must not treat the observation deadline as a
hard total-duration bound.

The total operating-window duration has not been measured. Issue 279 must leave
that duration as a scheduling unknown, let the operator choose a suitable
window and contingency for the listed work, and permit refusal to start when
the available window is unsuitable. Do not present a numerical total as
observed evidence or as a deadline accepted by the user. A failed attempt does
not authorize another arm or restart cycle.

The manual phase supervisor defined in `application-operation.md` remains
outside the `set -euo pipefail` shell. A shell exit returns control to that
supervisor, which records the earliest failure, stops collection, establishes
Desktop quiescence, and either resumes the already authorized restoration cycle
from immutable reviewed definitions and the existing private binding record or
reports `recovery-required`. It does not retry failed actuation, reread extra
private evidence, restore across package drift, or add another launch cycle.
When the authorized autonomous control surface is unavailable, the supervisor
returns control to the human operator.

Each launch transfers control once to its own bound transient service in the
selected user's existing systemd manager. The service receives the unchanged
reviewed launcher array through an inner clean environment, discards
application output, survives loss of the invoking shell or terminal, and never
restarts. Both submissions use the fixed description
`Provingkit task 278 Desktop launch control` and
`--expand-environment=no`, preserving the literal inner environment
assignments and launcher arguments. Submission is asynchronous, and
`Type=exec` establishes only execution of the initial command. Its PID is
launcher-control metadata only. The actual application PID still comes
exclusively from the two bound lock paths and must pass the selected-PID route
attestation. A successful unit submission or launcher exit does not establish
application success.

The user manager keeps manager state and generated runtime unit configuration
under `$XDG_RUNTIME_DIR/systemd/transient`, including the exact `ExecStart`
array and its selected noncredential launch configuration. The fixed
description avoids copying the command into the description but does not
remove that `ExecStart` storage. `systemctl show` acquires all
manager-exposed properties for the addressed unit before projecting the named
output fields, so the later grant must cover that acquisition for only the two
exact task-owned units. Printed and retained control metadata remains limited
to the seven fields named in `application-operation.md`; it is separate from
private receiver payloads. The manager state and generated file are retired
only through the exact-unit stop, reset, and `LoadState=not-found` sequence,
never by inspecting or deleting unit files or enumerating units or processes.
The dependency basis is the systemd 261.2
[systemd-run manual](https://github.com/systemd/systemd/blob/v261.2/man/systemd-run.xml),
[systemd.unit manual](https://github.com/systemd/systemd/blob/v261.2/man/systemd.unit.xml),
[property-show implementation](https://github.com/systemd/systemd/blob/v261.2/src/systemctl/systemctl-show.c#L2123-L2171),
and
[transient-setting writer](https://github.com/systemd/systemd/blob/v261.2/src/core/dbus-execute.c#L1678-L1690).

Candidate shutdown and every failed-cycle recovery establish bounded
quiescence through normal UI shutdown, disappearance of the attested PID,
absence of both exact lock paths, and absence of the selected-profile UI before
retiring the exact unit and requiring `LoadState=not-found`. The procedure
does not enumerate processes or manually inspect or remove generated unit
files. If the supervisor, user manager, or exact unit is lost, it performs no
replacement submission: candidate loss may enter only the already authorized
restoration cycle, while loss during unaccepted restored verification leaves
restoration incomplete. An accepted restored application may remain open under
its exact restored unit, with the corresponding manager state and generated
runtime configuration retained, until its later normal UI shutdown and
exact-unit retirement.

Routine version changes do not automatically require another live window, and
notification sends do not each
require a restart. Maintained observer installation and upgrade behavior remain
a later adoption decision.

The private packet binds the launcher's digest and owner, group, mode, device,
inode, link count, and size. It also binds the exact one-argument NUL launch
file path, digest, and identity; the selected account, organization, and
Electron user-data root; the clean launch environment; the current-profile
branch and existing configuration-directory identity; the flags file or
absence; the readable `44.4.3` version file; the executable and
adjacent-resources route; and the exact source-derived effective-argv
variants. It additionally binds the two exact transient-unit names, the fixed
launch-control mechanism, description, disabled environment expansion,
properties, manager-storage effect, exact-unit metadata acquisition and output
projection, and the existing launch-working-directory identity. The ordinary
password-store detector remains active when current state selects it, so that
branch admits only its two source-bounded argv results.

An absent named-profile executable remains absent and uses canonical fallback.
An existing named executable must pass the exact no-refresh checks; otherwise
the run returns for a decision before the launcher can replace it or maintain
shared sibling links. The procedure does not change profiles, force a password
store, authorize stale-lock cleanup, or read the selected profile's diagnostic
configuration.

The selected profile configuration directory must already exist as the bound
same-UID non-symlink directory before both launches. Recheck its identity
before and after each launch. This makes the launcher's `mkdir -p` operation a
no-op; absence or drift returns for a decision and supplies no authority to
create or clean up that directory.

Revalidate the package, protected assets, root-owned launcher ancestry,
launcher, launch file, environment, flags, profile state, no-refresh
predicates, version file, executable, resources route, archive, and absent
locks immediately before both launches. After each launch, attest the one
selected main PID through the two exact lock paths, then compare its executable,
bounded command line, and executable-adjacent archive with the reviewed
bindings. After those candidate checks, validate bootstrap and require its PID
and copied-archive digest to agree before arming. The restored cycle has no
bootstrap comparison. Execute only validated in-memory arrays and discard
their reconstructed copies plus raw lock-target and command-line bytes after
comparison. The private binding record continues to retain the approved
allowlisted selected environment entries and digest as recovery input, not a
full ambient or raw process environment. These checks narrow the mutation
window but do not make launch atomic.

## Disposable fixture

Create one new top-level disposable Code task named
`Desktop observer probe 278` in a new dedicated empty directory that is not a
Git repository or worktree, using the current signed-in profile. Use the normal
new-local-task UI. Never fork, spawn, import, duplicate, or reuse a task. Record
the exact real directory identity and prove pre-creation emptiness through a
nonrecursive inspection. Do not resolve or invent a worktree before creation.
If Desktop creates one, verify its exact identity and require only the expected
app-managed entries selected by the later grant. An unexpected directory or
worktree shape returns for a decision. Do not select a historical or unrelated
task.

Reviewed source constructs the selected metadata path as
`path.join(Electron app.getPath("userData"), "claude-code-sessions",
currentAccountId, currentOrgId, taskId + ".json")`. Construct the absolute path
from that reviewed source and the later selected profile, account,
organization, and task values. The exact app-data root remains a later binding
gap; the source-defined base is `claude-code-sessions`.
`getSessionFilePath` is an internal source method, not an approved callable UI
or API; never invoke it to obtain the path. Read only the constructed selected
file and project `sessionId`, `cliSessionId`, `cwd`, `originCwd`,
`worktreePath`, `spawnedFrom`, `dispatchParentId`,
`dispatchParentOrigin`, `forkedFromSessionId`, and `lineageDetached`. Do not
enumerate other sessions, export the raw metadata file, or read transcripts.

Require `sessionId` to equal the fixture identity chosen in the app,
`cliSessionId` to equal the recorded Code identity, and `cwd` to match the
dedicated project identity. Record `originCwd` and `worktreePath` as absent,
present with an empty string, or present with a nonempty value. Do not replace
an absent or empty value with the project path or invent a worktree. Bind every
nonempty value to an approved opened-directory identity. Preserve whether each
optional lineage field is absent or present. If present, spawn,
dispatch-parent, and fork values must be null and `lineageDetached` must be
false. A non-null relation or true `lineageDetached` stops the run. Absence
remains explicitly absent and must not be converted into confirmed lack of a
relation. Any unexpected path, changed identity, or unexpected activity stops
the run before staging.

Persisted nE metadata does not serialize `backend.kind`. Local classification
rests on the observed normal new-local-task UI provenance and, separately, the
inspected adapter source, which checks the live record for
`backend.kind === "local"` with `sshConfig` and `wslConfig` undefined before
bootstrap or getter collection and refuses unsupported routes. That static
source check is not live proof that a particular run passed the guard and must
not be exported as persisted metadata evidence.

That selected file cannot establish a global absence of children or unrelated
repository, project, or worktree sharing. Absence of unrelated sharing rests on
neither that file nor a nonrecursive project inspection. Exclusive fixture
construction and current operator coordination are cleanup gates, not proof of
global absence. Record `globalChildAbsence` as
`not-established-from-selected-metadata` and
`unrelatedSharingAbsence` as `not-established`. Do not substitute another enum
or convert either value into an absence boolean. Before cleanup, repeat the
selected-metadata checks and coordination check. The file may lag the running
task, so the patched app must independently match both identifiers to its
current selected record and query before bootstrap and arm acceptance.

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
[Private probe data contracts](private-data-contracts.md#normative-private-contracts)
is the normative home for the selected-fixture projection and selected-executor
invocation and result variants.
[Private input construction](private-input-construction.md) supplies their
canonical UTF-8 construction, exclusive creation, selected-metadata acquisition,
and complete bootstrap comparison procedures; it does not define alternative
enum sets.

`observer-probe.mjs` defines the exact configuration and arm schemas. Keep the
configuration outside the initially empty, same-owner `0700` run directory;
configuration and arm files are regular, single-link `0600` files. Set the
candidate and sidecar digests from the reviewed build receipt, the two verified
fixture IDs, a unique run ID, a 60-second setup deadline, and a 100-millisecond
setup poll interval. Supply its absolute configuration path as
`PROVINGKIT_OBSERVER_CONFIG` only for the experimental launch.

The Desktop adapter accepts only the exact canonical configuration encoding
with no final LF and supplies the SHA-256 of those accepted file bytes to the
probe. The probe requires that digest to equal the canonical validated object
before publishing it in the bootstrap. It does not replace the accepted byte
digest with a separately normalized digest. Arm input uses the same canonical
byte comparison but requires exactly one final LF. Reordered, alternate-
whitespace, or duplicate-bearing inputs are rejected before acceptance.

After bootstrap, compare every binding value with the granted fixture, reviewed
bytes, configuration digest, selected clock domain, and private run record.
Validate the generated nonce, PID, process start ticks, query generation, and
Linux boot ID before constructing the arm. The `pid` and `processStartTicks`
fields identify the app. The arm echoes every `BINDING_KEYS` field, including `monotonicClockId` and
`linuxBootId`, and selects these limits: three samples, five-second minimum
interval, 30-second observation window, and two seconds per getter.
Source-controlled values and templates do not authorize or supply a binding.
The source accepts only one arm within 60 seconds of bootstrap. The three calls
are `accountInfo()`, `getContextUsage({detail:"summary"})`, and
`listPermissionRules()`, sequentially. Each getter's wait is limited to the
lesser of two seconds and the time remaining before the absolute monotonic
observation deadline. No getter starts, and no settlement is accepted, at or
after that deadline. A timeout cannot cancel the original getter; it stops later
calls and samples. Synchronously blocking getter work likewise cannot be
forcibly stopped. Elapsed-time limits use the monotonic clock. Wall timestamps
describe the observations and cannot extend collection authority.

Outputs are `bootstrap.json`, `arm.json`, and at most three numbered sample
files. Each sample is bounded at 16 KiB; the run output is bounded at 64 KiB.
Samples record each getter's availability or fixed failure class and
before/after host snapshots, including named gaps and whether the selected host
values changed. Settled getter failures preserve independent observations; a
timeout records the failing stage and ends collection. Use the strict reader
with the independently checked binding and a maximum age no greater than 30
seconds. Every result remains unqualified. Preserve a failed or missing sample
as such.

The collection producer sets `sample.result` to `partial` when at least one
projected field has status `unavailable`, or when an available projected value
contains a nonempty `gaps` list. It sets `complete` only when neither condition
is present. `projectApprovedHost` records missing or null selected facts,
including `selectedExecutorReport.cliPidAtMs` and
`selectedExecutorReport.cliReportedVersion`, as `unavailable` gaps while
preserving JSON `null` as the projected fallback. A null report member is
therefore a valid shape, but it neither establishes runtime knowledge nor
overrides the producer's status or gap evidence.

The helper's retained producer status, field failures, host gaps, nullable
report facts, and relationship to the canonical original sample are governed
by
[Retained producer provenance](private-data-contracts.md#retained-producer-provenance).
Neither producer result state establishes any member of `UNKNOWN_CLAIMS`: the
producer emits those exact unknown values, and the strict reader requires them
and always returns `usable-partial` with qualification `unqualified`.

Each of the initial and final selected-executor sample acquisitions reads the
nonsecret Linux boot identifier once from the single path
`/proc/sys/kernel/random/boot_id`. It reads no other path to discover a PID.
The boot identifier and `linux-clock-monotonic.v1` bind the sample's monotonic
timestamps to the current boot. Direct calls to `readProbeSample` or
`inspectProbeSample` must pass explicit contemporaneous `now` and
`monotonicNow` values, the expected binding's `monotonicClockId` and
`linuxBootId`, and the approved maximum age. The selected-executor observer
samples both clocks after the boot-ID read, rechecks them after each awaited
sample acquisition, and binds the selected PID directory to one owned open
descriptor. It rechecks that descriptor's owner and identity and both clocks
immediately before every `stat` or `exe` open. Child reads use only the fixed
names beneath the retained descriptor and never re-resolve the numeric PID
path. Either clock regressing or exceeding the maximum age stops the
observation before the next child open. Active-profile or clock uncertainty
remains unqualified.

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
in both host snapshots, opens one owned selected-PID directory descriptor,
checks descriptor identity and freshness before every process-file open, and
revalidates the sample afterward. Its process budget is two numeric-path
metadata checks, one directory-descriptor open, seven descriptor metadata
checks, three `stat` opens of at most 4,096 bytes each, two `exe` opens, and at
most 256 MiB hashed. Retain its sample evidence with the result. A selected
binary path, version string, or parsed PID does not establish the full
query-to-executable association.

Validate the one authorized helper return against the normative result variants
in
[private probe data contracts](private-data-contracts.md#normative-private-contracts),
construct the normative wrapper, canonicalize that object, and serialize it by
the procedure in
[private input construction](private-input-construction.md). Apply the exact
retained sample-evidence requirements in
[Retained producer provenance](private-data-contracts.md#retained-producer-provenance).

Invoke the helper at most once and only when an actual usable selected sample
supplies its sequence and complete accepted binding. If no usable sample exists,
the helper is not called. A skipped helper or failed retention uses the exact absent reason
defined by the cleanup manifest and does not authorize another invocation.
No helper invocation occurs during preparation.

## Restoration, retention, and return

Stop collection and close Desktop before restoring. Recheck the installed
package identity first. If an upgrade intervened, do not overwrite the new
package with the retained older archive; return for a restoration decision.
Otherwise restore the verified pristine archive and verify its bytes and
unchanged native assets.

Use the same reviewed clean base environment without the probe configuration,
repeat the complete launcher-route checks, and attest the restored process
before accepting it. Then verify the restored app opens and the agreed
unrelated-work expectations hold. Report route failure, disposable fixture
loss, or changed task state separately from restored package bytes.
If the accepted restored app remains open, the later grant must cover retention
of its exact service, manager state, and generated runtime configuration until
normal UI shutdown, followed by the same bounded retirement and
`LoadState=not-found` check.

After verified restoration, perform the distinct package-cleanup phase from
`application-operation.md`. It may remove only the verified staging archive,
protected backup, and empty backup run root; it does not wait for issue 281.
Record each actual known, uncertain, removed, or absent state, and do not retry
a failed or partial removal. If restoration is `not-required`, incomplete, or
otherwise unverified, delete no package or private resource.

Create the private cleanup manifest after that package-cleanup phase ends, or
at the terminal stop when package deletion is prohibited. Use the exact status,
reason, restoration, package-cleanup, fixture, output, retained-evidence, and
resource-role variants defined by
[private probe data contracts](private-data-contracts.md#private-cleanup-manifest-and-retention).
The schema has no top-level retention field; record retention only in the
nested `restoration.recoveryRecord.retention` and `fixture.retention` fields.
List only files and resources actually established, preserve absent artifacts
explicitly, and never invent a task ID, Code ID, binding, sequence, file
identity, or removal result.

Incomplete or unverified restoration records `recovery-required` /
`restoration-incomplete`, retains the recovery record and every package and
private artifact, and permits no deletion. A possibly created task, directory,
worktree, or file remains unresolved pending an operational decision.

Retain raw fixture output, any valid Linux-observation artifact, unresolved
resources, and the cleanup manifest through the return decision, accessible
only to the user and the authorized execution and decision workflow. Do not
invoke the helper merely to populate a missing retained-evidence entry.

After the decision approves a redacted summary and names the exact manifest
subset to remove, use only Desktop's normal exact-task deletion UI. Source
inspection shows that managed deletion may cascade to the selected task's
worktree and transcript, so task deletion requires confirmed isolation and a
live confirmation scope matching only the fixture. The confirmation must make
the managed scope, including linked tasks and worktree handling, clear enough
to compare with the fixture record. Do not call internal session or family
deletion methods, scan all tasks, or add cleanup instrumentation. If the UI
control is absent, the managed scope cannot be established, or its scope is
broader, retain the fixture for an operational decision.

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
