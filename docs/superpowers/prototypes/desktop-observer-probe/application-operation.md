# Application staging and restoration

This runbook implements [Prepare and review the disposable observer probe](https://github.com/nisavid/provingkit/issues/278) as one operator-run window: create one fixture, protect the installed archive, atomically exchange in the reviewed candidate, run one bounded observer arm, stop it, restore the pristine archive, and verify restored behavior.
LIVE operation requires later authorization.

## Approval boundary

This runbook defines the application phases that consume
[Private probe data contracts](private-data-contracts.md), the normative home
for the selected-fixture projection, selected-executor invocation and result
variants, and cleanup-manifest schema.
[Private input construction](private-input-construction.md) defines how to
construct, validate, canonicalize, and exclusively create conforming bytes;
neither procedure defines alternative fields, states, reasons, or enum values.

[Authorize the disposable Desktop observer probe](https://github.com/nisavid/provingkit/issues/279)
must bind every variable to one exact value and every path variable to one exact
absolute path. The packet must not use `eval`, `source`, untrusted shell
expansion, or paths copied from this committed document:

- `RUN_ID`, beginning with `278-`.
- `PROBE_INSTALL_ROOT`, derived from package ownership.
- `CANDIDATE_ARCHIVE` and `GENERATED_BUILD_RECEIPT`, naming the same build output directory's `candidate.asar` and `build-receipt.json`.
- `PUBLISHED_BUILD_RECEIPT`, naming the reviewed revision's retained `candidate-build.json`.
- `CANDIDATE_SHA256`, `REVIEWED_ARCHIVE_VERIFICATION`, and
  `REVIEWED_ARCHIVE_VERIFICATION_SHA256`. The latter must equal
  `source.archiveVerification.sha256` in the populated private record.
- `PROBE_SYSTEM_STATE_ROOT`, a root-owned `0700` directory prepared only under the later authorization.
- `PROBE_USER_STATE_ROOT`, the existing private output root.
- `PROBE_CONFIG`, a private regular file outside the empty run directory.
- `CLEANUP_MANIFEST`, a private path outside the run directory that does not exist before the run.
- `LINUX_OBSERVATION_FILE`, a private path outside the run directory whose
  basename is exactly `selected-linux-executor-observation.json`.
- `PROBE_LAUNCHER`, its SHA-256 as `PROBE_LAUNCHER_SHA256`, and its reviewed device, inode, owner, group, mode, link count, and size as `PROBE_LAUNCHER_STAT`.
- The reviewed NUL-delimited `PROBE_LAUNCH_ARGV_FILE`, its reconstructed NUL-delimited SHA-256 as `PROBE_LAUNCH_ARGV_SHA256`, and its device, inode, owner, group, mode, link count, and size as `PROBE_LAUNCH_ARGV_STAT`. These are recorded as `launchRoute.launchArgumentFile` in the private record.
- `PROBE_PROFILE`, exactly `default` or the current named-profile token;
  `PROBE_PROFILE_KIND`, exactly `default` or `named`; and `PROBE_HOME`.
- The ordered in-memory `PROBE_LAUNCH_ENV` array reconstructed from the
  private record, and its NUL-delimited `name=value` SHA-256 as
  `PROBE_LAUNCH_ENV_SHA256`.
- `PROBE_CONFIG_DIR`, its existing directory identity as
  `PROBE_CONFIG_DIR_STAT`, `PROBE_LOCK_PATH_PRIMARY`,
  `PROBE_LOCK_PATH_3P`, `PROBE_FLAGS_PATH`, and `PROBE_FLAGS_STATE`.
- `PROBE_EXPECTED_ELECTRON`, `PROBE_EXPECTED_ELECTRON_SHA256`,
  `PROBE_VERSION_FILE`, `PROBE_VERSION_FILE_SHA256`,
  `PROBE_VERSION_FILE_STAT`, `PROBE_EXPECTED_RESOURCES`, and
  `PROBE_EXPECTED_APP_ASAR`.
- `PROBE_NAMED_BINARY_STATE`, exactly `not-applicable`, `absent`, or
  `ready`. Refresh is outside this increment.
- The exact source-derived effective-argv variant or variants recorded under
  `launchRoute.execution.effectiveArgvVariants` in the private record.
- `PROTECTED_ASSET_MANIFEST`, its SHA-256, and the exact main-executable, complete native-asset, and `chrome-sandbox` inventory.
- The current profile, account, organization, Electron user-data root, new local Code task, new empty
  non-Git project directory, any app-created dedicated worktree and its approved
  expected entries, task ID, Code ID, constructed metadata path, approved
  process bindings, and task-restoration expectations.

Any required root preparation is part of the later authorization packet, not a
requirement already completed by this document. If a required root does not
exist at preflight, stop for its separately authorized root-creation step; do
not create a directory chain through unchecked ancestors.

The packet must confirm:

- Package `claude-desktop-extra 2.9939.4-1`.
- Application archive `@ant/desktop 2.9939.4`.
- Electron `44.4.3`.
- Installed target `PROBE_INSTALL_ROOT/resources/app.asar`.
- Pristine SHA-256 `4ac2b896dabf3e871f9cf6d9833d02f9f6ad2a839dae6658edc84bb08341238a`.
- Target: regular `root:root` file, mode `0644`, one link, `54910454` bytes, base ACL only, and no xattrs.
- Resources directory: `root:root`, mode `0755`.
- Main executable: `root:root`, mode `0755`.
- `chrome-sandbox`: `root:root`, mode `4755`.
- The launcher and every ancestor are root-owned and not group- or world-writable.
- The launcher ignores `CLAUDE_APP_ASAR` and loads the selected
  executable-adjacent archive. An absent named-profile executable is not
  created by an ordinary launch; an existing one may be refreshed only when a
  source predicate fires. This procedure prohibits that refresh and stops
  before launch if its no-refresh precondition is not met.

`build-receipt.json` is generated output tied to the proposed archive.
`candidate-build.json` is its published source copy. Both bind source-input
hashes and the candidate archive hash, but neither contains the published Git
revision; approval must bind and review that revision separately. Authorization
and staging require the two receipt files to compare byte for byte. Host
metadata proves installed ownership. UID `65534` observed in the sandbox
namespace does not.

## Normative private contracts

The normative selected-fixture projection and selected-executor invocation,
wrapper, and result variants are defined in
[Private probe data contracts](private-data-contracts.md#normative-private-contracts).
This runbook consumes those contracts; it does not define alternative fields,
states, reasons, or enum values.

## Fixture preparation

Before closing Claude Desktop or staging files, use the current signed-in
profile and a new dedicated empty directory that is not a Git repository or
worktree to create exactly one new top-level local Code task through the normal
new-task UI. Never fork, spawn, import, duplicate, or reuse a task. Resolve and
open the selected directory, record its exact real path, device, inode, UID,
GID, and mode, and require an empty nonrecursive entry list before creation. If
Desktop creates a dedicated worktree, record its identity and require only the
exact app-managed entries approved by the later grant. Do not resolve or invent
a worktree before creation. Stop and return for a decision on any unexpected
shape, activity, or identity change. Send the exact first prompt:

```text
This is a disposable observer fixture. Reply exactly `PROBE_READY`. Do not use tools, inspect files, change settings, or begin other work.
```

Reviewed source constructs the metadata path as
`path.join(Electron app.getPath("userData"), "claude-code-sessions",
currentAccountId, currentOrgId, taskId + ".json")`. Construct the exact path
from that source and the later selected profile, account, organization, and
task values. The exact app-data root remains an authorization binding gap; the
source-defined base is `claude-code-sessions`.
`getSessionFilePath` is an internal source method, not an approved callable UI
or API; do not invoke it. Do not enumerate the constructed path's parent
directory. Record its projected `sessionId`, `cliSessionId`, `cwd`,
`originCwd`, `worktreePath`, `spawnedFrom`, `dispatchParentId`,
`dispatchParentOrigin`, `forkedFromSessionId`, and `lineageDetached`; do not
export the raw metadata or a transcript.

Require matching task and Code IDs and require `cwd` to match the opened
project identity. Record `originCwd` and `worktreePath` as absent, present with
an empty string, or present with a nonempty value. Do not substitute the
project path for an absent or empty value or fabricate a worktree. Bind every
nonempty value to an approved opened-directory identity. Preserve each optional
lineage field's presence. If present, spawn, dispatch-parent, and fork fields
must be null and `lineageDetached` must be false. A non-null relation or true
`lineageDetached` is a stop condition. Absence remains absent and is not
evidence of confirmed nonrelation. Missing or changing required IDs, an
unexpected path, or unexpected activity is also a stop condition; do not
create another fixture or rescope.

Persisted nE metadata does not contain `backend.kind`. Record local creation
from the normal new-local-task UI provenance. Separately, the inspected adapter
source checks the live record for `backend.kind === "local"` with `sshConfig`
and `wslConfig` undefined before bootstrap or getter collection and refuses
unsupported routes. Static inspection of that guard is not live proof that a
particular run passed it.

The selected file provides no global proof that children do not exist or that
no unrelated task shares a repository, project, or worktree. Record
`selectedMetadataRelations` as `no-nonnull-relation-observed`,
`globalChildAbsence` as `not-established-from-selected-metadata`, and
`unrelatedSharingAbsence` as `not-established`. Current exclusive construction
and operator coordination remain cleanup gates, not global-sharing evidence.

Prepare `PROBE_CONFIG` before staging. It must carry the existing schema, exact
fixture and artifact binding, private run directory, and setup limits described
by `probe-procedure.md`. Construct and validate its exact bytes using
`private-input-construction.md`. Do not acquire private identity data before
the later grant.

Record the fixture's expected post-restoration state in the approval packet.
The bound cleanup-manifest path remains absent until the run reaches a terminal
state. If restoration is verified, complete or stop the distinct package-cleanup
phase before creating the manifest. If restoration was not required, create
the manifest without deleting any package path. If restoration is incomplete
or unverified, create the recovery manifest without deleting anything. Record
only identities and resources actually established. An uncertain task,
directory, worktree, file, or package path is retained pending an operational
decision; it is never treated as absent or discarded.

## Protected-asset manifest

`PROTECTED_ASSET_MANIFEST` is an LF-terminated tab-delimited data file with no
header or blank lines. Each row has exactly these eight nonempty columns:

```text
role<TAB>path<TAB>sha256<TAB>uid<TAB>gid<TAB>mode<TAB>links<TAB>size<LF>
```

`role` is exactly `main-executable`, `native-asset`, or `chrome-sandbox`.
`path` is the literal absolute pathname byte sequence: it is not quoted,
escaped, expanded, or normalized. A path containing a tab, LF, or CR is not
representable and must be rejected rather than escaped. `sha256` is 64
lowercase hexadecimal characters. `uid`, `gid`, `links`, and `size` are
canonical unsigned decimal integers; `links` is positive. `mode` is the three-
or four-digit octal spelling returned by `stat -c %a`.

The manifest contains exactly one `main-executable` row, exactly one
`chrome-sandbox` row, and one row for every reviewed native asset, with no
duplicate path or additional row. Its path set must equal the complete
package-derived inventory approved by issue 279. Completeness is established
during review of that inventory; a runtime scan must not invent or enlarge it.
The approved manifest hash binds the reviewed set.

## Manual phase supervision and shell recovery

This remains a manually supervised procedure. The operator, or an autonomous
control surface explicitly covered by the later grant, is the external phase
supervisor. The supervisor runs outside the shell that uses
`set -euo pipefail`; that shell is a supervised child process, not the holder
of recovery state. A shell exit therefore returns control to the supervisor.

The supervised phase boundaries are preflight, staging, exchange, candidate
launch and collection, candidate shutdown and quiescence, restoration and
restored verification, package cleanup, and cleanup-manifest creation. Before
each boundary, record the applicable existing failure-phase token and only the
resource identities, mutations, and absence checks already established. Use
the normative cleanup-manifest status, restoration, and package-cleanup fields;
this phase record does not define another schema.

On any nonzero command result, unexpected shell exit, or failed UI step, the
supervisor must:

1. Record the earliest failure without replacing an earlier `firstFailure`,
   stop the remaining commands in that phase, and stop collection. Do not retry
   a failed prompt, arm, getter, helper invocation, launch, exchange, deletion,
   or retained-file operation.
2. If Desktop may be running, request its normal UI shutdown, verify the
   selected PID has exited where that can be established, and establish current
   profile quiescence before any recovery action. No shell trap can establish
   application quiescence. If the authorized autonomous control surface is
   unavailable, stop and escalate to the human operator.
3. Retain every resource whose current state is known or uncertain. Do not
   reread configuration, output, sample, helper-result, or retained-evidence
   contents merely to reconstruct lost shell state.
4. If candidate exchange did not occur, establish whether the original archive
   bytes are unchanged and whether Desktop availability requires recovery.
   When unchanged bytes are established, perform no archive exchange. If
   Desktop remains closed, use the single restored launch only when covered by
   the later restoration-cycle grant, after the pristine, package, launcher,
   and quiescence checks pass. Record restoration as `not-required` only when
   no application or archive recovery obligation remains. If needed recovery
   is not covered, available, completed, or verified, record `incomplete` with
   status `recovery-required`. A changed or ambiguous archive, or an earlier
   launch with an ambiguous result, stops for a decision and does not
   authorize a retry. If exchange occurred or may have occurred, enter the
   already authorized restoration cycle only after quiescence. Recovery within
   that cycle does not authorize another candidate cycle or any launch or
   restart beyond its single grant.

A recovery shell is a fresh Bash process with `set -euo pipefail` and
`LC_ALL=C`. Before it performs any package mutation, the supervisor must:

1. Verify that the procedure revision is the immutable revision named by the
   grant. Manually repopulate the required variables from the existing
   validated private binding record and authorization packet. Do not use
   `source`, `eval`, shell-generated assignments, or newly acquired private
   data.
2. Repeat the required-variable, `RUN_ID`, absolute-path, component, no-symlink,
   and root-owned-ancestor validations from preflight. Reconstruct exactly
   `TARGET_DIR`, `TARGET`, `STAGE`, `BACKUP_RUN_ROOT`, `BACKUP`,
   `OUTPUT_RUN_ROOT`, and `PRISTINE_SHA256` from their reviewed definitions.
3. Re-enter verbatim from the reviewed revision the definitions of
   `hash_file`, `check_no_xattrs`, `check_root_archive_file`,
   `check_root_owned_directory`, `check_root_owned_ancestors`,
   `check_root_owned_parent_ancestors`,
   `check_reviewed_archive_verification`,
   `validate_protected_asset_manifest`, `check_reviewed_launcher`,
   `load_reviewed_launch_argv`, and
   `validate_reviewed_launch_environment`. Do not execute the rest of
   preflight as a definitions loader.
4. Re-establish `CANDIDATE_SIZE` only after the current candidate archive again
   matches `CANDIDATE_SHA256`. Recheck the current package version and
   ownership, protected-asset manifest and its bound hash, reviewed
   archive-verification record, and the exact target, stage, and backup
   identities applicable to the last verified phase.
5. Reconstruct `PROBE_LAUNCH_ENV` and the exact effective-argv variants
   manually from the existing private record. Repeat every applicable bound
   launcher-routing check below. Do not reacquire an ambient value merely to
   reconstruct lost state.
6. Follow the restoration prechecks and remaining restoration steps from the
   first step not already verified. Never repeat a verified exchange or launch.
   A changed package, upgrade, ownership change, protected-asset change,
   missing archive, uncertain exchange state, identity mismatch, or failed
   restoration command stops recovery. Record `recovery-required`, retain all
   package and private resources, and return for the operational-restoration
   decision.

After a successful restoration exchange, or when unchanged archive bytes are
established but Desktop availability requires recovery, the one restored
launch authorized by the applicable restoration-cycle grant and its route
attestation remain necessary. A failed attestation authorizes shutdown and
restoration only, not another candidate launch. No failure authorizes an extra
launch. Package cleanup remains prohibited until restoration is fully
verified.

## Bound launcher routing

This procedure uses literal launcher `/usr/bin/claude-desktop` with SHA-256
`015f5232d3c2c40f04f5529d44058d3fd0a80cdce0eddf91dc08688f0a8c867e`.
`PROBE_LAUNCH_ARGV_FILE` contains exactly one NUL-terminated argument:
`/usr/bin/claude-desktop`. URI, subcommand, maintenance, deployment-mode,
profile, `--user-data-dir`, AppImage, ASAR, executable-override, and
sandbox-disabling arguments are prohibited.

The launch environment is an ordered in-memory array of exact `name=value`
strings reconstructed manually from the private record. It is never sourced,
evaluated, or inherited implicitly. Its NUL-delimited digest is computed as:

```text
name=value NUL name=value NUL ...
```

Names are bytewise ascending and unique. The array contains `HOME`,
`USER`, `LOGNAME`, `PATH`, and `CLAUDE_PROFILE`. `HOME` equals
`PROBE_HOME`; `CLAUDE_PROFILE` is `default` or the exact current named
profile. `PATH` contains only nonempty absolute components.

Only these additional names may be present:

- `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_DATA_DIRS`,
  `XDG_CACHE_HOME`, `XDG_STATE_HOME`, and `XDG_RUNTIME_DIR`;
- `DISPLAY`, `WAYLAND_DISPLAY`, `XAUTHORITY`, and
  `DBUS_SESSION_BUS_ADDRESS`;
- `XDG_SESSION_TYPE`, `XDG_CURRENT_DESKTOP`, `XDG_SESSION_DESKTOP`,
  `DESKTOP_SESSION`, `XDG_SESSION_CLASS`, `XDG_SEAT`, and `XDG_VTNR`;
- `LANG`, `LANGUAGE`, `LC_ALL`, `LC_ADDRESS`, `LC_COLLATE`,
  `LC_CTYPE`, `LC_IDENTIFICATION`, `LC_MEASUREMENT`, `LC_MESSAGES`,
  `LC_MONETARY`, `LC_NAME`, `LC_NUMERIC`, `LC_PAPER`,
  `LC_TELEPHONE`, and `LC_TIME`;
- `GTK_IM_MODULE`, `QT_IM_MODULE`, `XMODIFIERS`, `GDK_BACKEND`,
  `PULSE_SERVER`, `PIPEWIRE_RUNTIME_DIR`, `SSH_AUTH_SOCK`,
  `GPG_AGENT_INFO`, `GNOME_KEYRING_CONTROL`, `TERM`, `COLORTERM`,
  and `DESKTOP_STARTUP_ID`;
- `CLAUDE_CONFIG_DIR`, `CLAUDE_USE_XWAYLAND`,
  `CLAUDE_GPU_BACKEND`, `CLAUDE_DISABLE_GPU`,
  `CLAUDE_ENABLE_VULKAN`, `CLAUDE_PASSWORD_STORE`,
  `CLAUDE_NATIVE_TITLEBAR`, `CLAUDE_NO_WINDOW_CONTROLS`,
  `CLAUDE_DISABLE_SYSTEMD_SCOPE`, `CLAUDE_KEEP_TTY`, and
  `CLAUDE_LAUNCHER`.

When present, `CLAUDE_LAUNCHER` must equal
`/usr/bin/claude-desktop`. `CLAUDE_ELECTRON`, `CLAUDE_APP_ASAR`,
`CLAUDE_APPIMAGE_PATH`, `CLAUDE_DISABLE_SANDBOX`,
`ELECTRON_FORCE_IS_PACKAGED`, and `PROVINGKIT_OBSERVER_CONFIG` are
prohibited in the base environment. Credential and API-key variables are not
copied into the packet or launch environment.

The later grant permits a name-only inventory of the ambient environment and
reads of values for only the allowed names above. Do not dump the environment.
The presence of an unapproved name that may affect loading, execution,
authentication, or UI routing—including a name beginning `LD_`, `NODE_`, or
`ELECTRON_`, or `GTK_MODULES`, `GTK_PATH`, `GIO_EXTRA_MODULES`,
`QT_PLUGIN_PATH`, or `QT_QPA_PLATFORM_PLUGIN_PATH`—stops for an amended
review without reading that value. If preserving the current account or Code
route requires another variable, stop for that decision rather than silently
discarding or authorizing it.

The selected paths are derived exactly as follows:

- `config_dir` is nonempty `XDG_CONFIG_HOME`, otherwise
  `PROBE_HOME/.config`, followed by `/Claude` for the default profile or
  `/Claude-<profile>` for a named profile.
- `PROBE_LOCK_PATH_PRIMARY` is `config_dir/SingletonLock`;
  `PROBE_LOCK_PATH_3P` is `config_dir-3p/SingletonLock`.
- `PROBE_FLAGS_PATH` is nonempty `XDG_CONFIG_HOME`, otherwise
  `PROBE_HOME/.config`, followed by `/claude-desktop-flags.conf`.
- A named profile inherits a nonempty `CLAUDE_CONFIG_DIR`. Otherwise the
  launcher exports `PROBE_HOME/.claude-<profile>`. The procedure does not
  alter deployment mode or infer an app data root from an absent lock.

`PROBE_CONFIG_DIR` must already exist before either launch. Require the exact
path to be a non-symlink directory owned by the selected Desktop UID and not
group- or world-writable. Open the final component with
`O_DIRECTORY|O_NOFOLLOW`, compare its device, inode, UID, GID, and mode with
`PROBE_CONFIG_DIR_STAT`, and require the path still resolves to that opened
identity. Recheck the same identity immediately before and after both
launches. Do not enumerate the directory beyond the two separately authorized
lock paths.

The named-profile launcher executes `mkdir -p` for this directory. Because
the reviewed route requires the exact directory to exist first, that command
has no authorized creation effect. Absence or identity drift stops before
launch; the procedure does not create, restore, or remove the directory, and
it is not a cleanup resource.

The current launcher may read only the selected profile's
`claude-desktop-extra.jsonc` and `claude-desktop-extra.json` for saved
native-titlebar and window-control diagnostics. Do not read those files for
this route review. Existing app-side configuration effects remain ordinary
profile effects. `CLAUDE_NATIVE_TITLEBAR` and
`CLAUDE_NO_WINDOW_CONTROLS` are the explicit launcher controls; if both equal
`1`, the launcher unsets the latter. Neither adds a Chromium argument.

Before either launch, both exact lock paths must be absent. A lock symlink,
whether active, malformed, or stale, stops for an operating decision. This
increment does not authorize the launcher's stale-lock removal. During
post-launch attestation, the two paths may be read only as described below.

The executable branch is:

- For `default`, `PROBE_NAMED_BINARY_STATE=not-applicable` and the selected
  executable is `/usr/lib/claude-desktop/claude`.
- For named profile state `absent`, require exact absence of
  `PROBE_HOME/.local/lib/claude-desktop/claude-<profile>`. Ordinary launch
  must retain that absence and select `/usr/lib/claude-desktop/claude`.
- For named profile state `ready`, require that exact profile executable to be
  executable and byte-identical to the reviewed canonical executable. Require
  the canonical executable not to be newer, its `resources` link to have the
  exact canonical-resources target, and every existing sibling symlink
  inspected by the launcher's normal predicate to have an existing target.
  The later grant must cover that metadata-only sibling-symlink enumeration.

For `ready`, recheck all no-refresh predicates and the bound sibling-symlink
inventory immediately before each launch and recheck the same identities
afterward. For `absent`, recheck only the exact named executable's absence
before and after launch. If a refresh predicate is true, if a
`.new.<launcher-pid>` staging path appears, or if a profile or sibling asset
changes, stop. Do not refresh, materialize, replace, relink, or substitute the
profile. The preflight gate rejects a launch when the inspected predicate
would refresh. The afterward check detects selected changes, but the
check/launch/check sequence is not atomic and does not guarantee against
same-user interference during its race window. It preserves current-profile
selection and stops on observed drift; it does not prove that every mutation
was prevented.

Legacy `/usr/lib/claude-desktop-bin/claude` fallback is prohibited. For the
selected executable directory `D`, bind `D/version`, `D/resources`, and
`D/resources/app.asar`. Read the version file through one stable descriptor;
require its bound identity and digest, and require its first line to be exactly
`44.4.3`. This prevents the launcher's `--version` fallback execution.
Require the selected `resources/app.asar` to resolve through the reviewed
resource route to the same device and inode as `TARGET`.

For a present flags file, open only `PROBE_FLAGS_PATH` through one stable
descriptor. Compare its before/descriptor/after identity and digest with the
private record. Parse each LF-delimited line, including a final line without
LF, by removing the first `#` and everything after it, ignoring an
all-whitespace remainder, and splitting the remainder on Bash default IFS
without quote parsing or expansion. Compare the resulting ordered tokens
exactly with the private record. For an absent flags file, require exact
absence before and after each launch.

Profile extraction has already completed before these tokens are read. Reject
every positional token and every token that can select another application,
archive, executable, profile, user-data directory, URI, deployment mode,
extension, debugging listener, AppImage, or weaker sandbox. Feature, display,
GPU, password-store, and other behavioral tokens proceed only when the grant
names the exact token and accepts its effect. A token not already classified
by the grant stops the run.

Construct the effective-argv variants manually from the reviewed environment
and ordered flag tokens:

1. Element zero is `PROBE_EXPECTED_ELECTRON`. The first argument is
   `--enable-blink-features=WebBluetooth`.
2. Because AppImage and `CLAUDE_DISABLE_SANDBOX=1` are prohibited, no
   `--no-sandbox` argument is added.
3. With absent `WAYLAND_DISPLAY`, select x11 and add no platform argument.
   With present `WAYLAND_DISPLAY`, select wayland unless
   `CLAUDE_USE_XWAYLAND=1` and nonempty `DISPLAY`, which selects xwayland.
   Xwayland adds `--ozone-platform=x11`. Wayland adds
   `--ozone-platform=wayland`, `--enable-wayland-ime`, and
   `--wayland-text-input-version=3`; its enable-feature list begins with
   `GlobalShortcutsPortal`, and its disable-feature list begins with `Vulkan`
   unless `CLAUDE_ENABLE_VULKAN=1`.
4. Scan flag tokens in order. Split each `--disable-features=` or
   `--enable-features=` value on commas, remove that original token, skip
   empty and exact duplicate feature names, and preserve first occurrence.
   Emit the single joined disable-features argument first when nonempty, then
   the single joined enable-features argument when nonempty.
5. `CLAUDE_GPU_BACKEND=angle-gl` adds `--use-gl=angle` and then
   `--use-angle=gl`. `CLAUDE_DISABLE_GPU=1` or `compositing` adds
   `--disable-gpu-compositing`; `full` adds `--disable-gpu`.
6. A remaining forwarded `--password-store=*` token suppresses detection and
   remains among the forwarded tokens. Otherwise, absent
   `CLAUDE_PASSWORD_STORE` yields exactly two permitted variants: no added
   argument or `--password-store=gnome-libsecret`. Value `auto` adds none;
   any other reviewed value adds one
   `--password-store=<exact-value>` argument. Do not set, clear, or alter this
   variable to force a variant.
7. A named profile appends `--user-data-dir=<config_dir>`.
8. Append all remaining forwarded flag tokens in their original order.

Record exactly one argv variant except for the bounded two-result detector
branch. Each variant is a NUL-delimited array with its own SHA-256. Neither
launcher log text nor a prior process supplies an expected variant. The
launcher exports `ELECTRON_FORCE_IS_PACKAGED=true` and its resolved
`CLAUDE_LAUNCHER`; those exports do not add arguments.

The bindings used by these checks remain later-grant data. A check described
here without a named shell function is a manual route check against those
bindings, not a call to an omitted function.

Immediately before each launch, repeat the package, target, protected-asset,
launcher, one-argument launch-file, clean-environment, exact existing
configuration-directory identity, flags, profile branch, no-refresh, version,
executable, resources, archive, and absent-lock checks.
Any mismatch stops before execution. `systemd-run` or `setsid` wrapping does
not change the expected inner Electron array; runtime disagreement is a failed
attestation, not successful routing.

After launch and before candidate arm creation or restored acceptance, inspect
only the two bound lock paths. Parse the substring after the last `-` in each
present symlink target as a positive decimal PID. Require exactly one unique
PID, owned by the selected Desktop UID and started during this launch. A
missing, malformed, reused, conflicting, or non-unique PID stops the run. Do
not enumerate processes or infer another profile path.

For that PID only, the later grant permits:

- metadata checks of the numeric `/proc` directory and its `stat` start-time
  field before and after attestation;
- one stable-descriptor read of `/proc/<pid>/exe`;
- one read, bounded at 64 KiB, of `/proc/<pid>/cmdline`;
- the opens needed to hash the selected executable and its adjacent
  `resources/app.asar`.

Require the executable target, identity, and SHA-256 to match
`PROBE_EXPECTED_ELECTRON`. Compare the NUL-delimited command line in memory
with the permitted effective-argv variant or variants and accept exactly one
match. Do not retain raw command-line or lock-target bytes. Resolve
`resources/app.asar` from the attested executable directory and require its
stable descriptor to identify `TARGET`, with the candidate digest during the
candidate cycle and pristine digest during the restored cycle. Recheck the
configuration-directory identity, flags state, and applicable named-profile
state after launch.

For the candidate cycle, complete the selected-process, argv, adjacent-archive,
flags, and profile checks before waiting for bootstrap. Once bootstrap is
available and validated, require its PID to equal the attested PID and its
copied-archive digest to equal the candidate digest before creating `arm.json`.
The restored cycle performs no bootstrap read or bootstrap-binding comparison;
it keeps UI and fixture behavior as separate acceptance checks. Attestation
failure authorizes only normal shutdown and the already granted restoration
path.

The per-launch `PROBE_LAUNCH_ENV` and effective-argv arrays, parsed working
copies, `/proc` command-line bytes, and lock-target bytes remain in memory only
and are unset or discarded after comparison. The private record retains the
approved `launchRoute.environment.entries`, their digest, and the effective
argv variants as selected launch configuration and recovery input. Those
allowlisted entries exclude credential and API-key variables; they are not a
full ambient-environment dump or raw process-environment export. This increment
creates no separate runtime-input file and adds no cleanup-manifest role.

## Preflight

Issue 279 schedules one window and two full Desktop shutdown/launch cycles. The
window includes:

- the listed manual package, receipt, asset, launcher, argument, fixture, and
  directory checks;
- two submissions of the exact setup prompt;
- candidate staging and launch;
- getter initiation, asynchronous waiting, and settlement acceptance bounded by
  one 30-second monotonic observation deadline, without a hard-cancellation
  claim for uncancellable or synchronously blocking work;
- candidate shutdown, restoration, restored launch, and restoration checks;
- retained-artifact and cleanup-manifest construction.

The total duration is unmeasured. The operator chooses the window and
contingency and refuses to start if the available window is unsuitable. No
unsupported numerical total is evidence or an accepted deadline.

Coordinate the one current-profile window so no package operation is active or
scheduled to overlap it. Do not change global updater configuration.

```bash
set -euo pipefail
export LC_ALL=C

required=(RUN_ID PROBE_INSTALL_ROOT CANDIDATE_ARCHIVE
  GENERATED_BUILD_RECEIPT PUBLISHED_BUILD_RECEIPT CANDIDATE_SHA256
  REVIEWED_ARCHIVE_VERIFICATION REVIEWED_ARCHIVE_VERIFICATION_SHA256
  PROBE_SYSTEM_STATE_ROOT
  PROBE_USER_STATE_ROOT PROBE_CONFIG CLEANUP_MANIFEST
  PROBE_LAUNCHER PROBE_LAUNCHER_SHA256 PROBE_LAUNCHER_STAT
  LINUX_OBSERVATION_FILE PROBE_LAUNCH_ARGV_FILE PROBE_LAUNCH_ARGV_SHA256 PROBE_LAUNCH_ARGV_STAT
  PROBE_PROFILE PROBE_PROFILE_KIND PROBE_HOME PROBE_LAUNCH_ENV_SHA256
  PROBE_CONFIG_DIR PROBE_CONFIG_DIR_STAT
  PROBE_LOCK_PATH_PRIMARY PROBE_LOCK_PATH_3P
  PROBE_FLAGS_PATH PROBE_FLAGS_STATE PROBE_NAMED_BINARY_STATE
  PROBE_EXPECTED_ELECTRON PROBE_EXPECTED_ELECTRON_SHA256
  PROBE_VERSION_FILE PROBE_VERSION_FILE_SHA256 PROBE_VERSION_FILE_STAT
  PROBE_EXPECTED_RESOURCES PROBE_EXPECTED_APP_ASAR
  PROTECTED_ASSET_MANIFEST PROTECTED_ASSET_MANIFEST_SHA256)
for name in "${required[@]}"; do
  [[ -n "${!name:-}" ]]
done
[[ "$RUN_ID" =~ ^278-[A-Za-z0-9._-]+$ ]]
test "$PROBE_LAUNCHER" = "/usr/bin/claude-desktop"
test "$PROBE_LAUNCHER_SHA256" = \
  "015f5232d3c2c40f04f5529d44058d3fd0a80cdce0eddf91dc08688f0a8c867e"
[[ "$PROBE_PROFILE_KIND" = "default" || "$PROBE_PROFILE_KIND" = "named" ]]
[[ "$PROBE_PROFILE" = "default" || "$PROBE_PROFILE" =~ ^[a-zA-Z0-9_-]+$ ]]
if [[ "$PROBE_PROFILE_KIND" = "default" ]]; then
  test "$PROBE_PROFILE" = "default"
  test "$PROBE_NAMED_BINARY_STATE" = "not-applicable"
else
  test "$PROBE_PROFILE" != "default"
  [[
    "$PROBE_NAMED_BINARY_STATE" = "absent" ||
    "$PROBE_NAMED_BINARY_STATE" = "ready"
  ]]
fi

test -d "$PROBE_CONFIG_DIR"
test ! -L "$PROBE_CONFIG_DIR"
test "$(stat -c '%d:%i:%u:%g:%a' -- "$PROBE_CONFIG_DIR")" = \
  "$PROBE_CONFIG_DIR_STAT"
test "$(stat -c '%u' -- "$PROBE_CONFIG_DIR")" = "$(id -u)"
config_dir_mode=$(stat -c '%a' -- "$PROBE_CONFIG_DIR") || exit 1
(( (8#$config_dir_mode & 0022) == 0 ))

TARGET_DIR="$PROBE_INSTALL_ROOT/resources"
TARGET="$TARGET_DIR/app.asar"
STAGE="$TARGET_DIR/.app.asar.probe-$RUN_ID.exchange"
BACKUP_RUN_ROOT="$PROBE_SYSTEM_STATE_ROOT/$RUN_ID"
BACKUP="$BACKUP_RUN_ROOT/pristine-app.asar"
OUTPUT_RUN_ROOT="$PROBE_USER_STATE_ROOT/$RUN_ID"
PRISTINE_SHA256="4ac2b896dabf3e871f9cf6d9833d02f9f6ad2a839dae6658edc84bb08341238a"

test "${CANDIDATE_ARCHIVE##*/}" = "candidate.asar"
test "${GENERATED_BUILD_RECEIPT##*/}" = "build-receipt.json"
test "${PUBLISHED_BUILD_RECEIPT##*/}" = "candidate-build.json"
test "${CANDIDATE_ARCHIVE%/*}" = "${GENERATED_BUILD_RECEIPT%/*}"

for path in "$PROBE_INSTALL_ROOT" "$CANDIDATE_ARCHIVE" \
  "$GENERATED_BUILD_RECEIPT" "$PUBLISHED_BUILD_RECEIPT" \
  "$REVIEWED_ARCHIVE_VERIFICATION" "$PROBE_SYSTEM_STATE_ROOT" \
  "$PROBE_USER_STATE_ROOT" "$PROBE_CONFIG" "$CLEANUP_MANIFEST" \
  "$LINUX_OBSERVATION_FILE" \
  "$PROBE_LAUNCHER" "$PROBE_LAUNCH_ARGV_FILE" \
  "$PROTECTED_ASSET_MANIFEST"; do
  [[ "$path" = /* && "$path" != *$'\n'* && "$path" != *'/../'* ]]
  cursor="/"
  IFS=/ read -r -a components <<< "${path#/}" || exit 1
  for component in "${components[@]}"; do
    [[ -n "$component" && "$component" != "." && "$component" != ".." ]]
    cursor="${cursor%/}/$component"
    sudo test ! -L "$cursor"
  done
done

check_root_owned_directory() {
  local path="$1" owner mode
  sudo test -d "$path"
  owner=$(sudo stat -c '%u' -- "$path") || return 1
  mode=$(sudo stat -c '%a' -- "$path") || return 1
  test "$owner" = "0"
  (( (8#$mode & 0022) == 0 ))
}

check_root_owned_ancestors() {
  local path="$1" cursor="/" component
  local -a components
  check_root_owned_directory "/"
  IFS=/ read -r -a components <<< "${path#/}" || return 1
  for component in "${components[@]}"; do
    [[ -n "$component" && "$component" != "." && "$component" != ".." ]]
    cursor="${cursor%/}/$component"
    check_root_owned_directory "$cursor"
  done
}

check_root_owned_parent_ancestors() {
  local path="$1" parent
  parent="${path%/*}"
  [[ -n "$parent" ]] || parent="/"
  check_root_owned_ancestors "$parent"
}

check_root_owned_ancestors "$PROBE_INSTALL_ROOT"
check_root_owned_ancestors "$PROBE_SYSTEM_STATE_ROOT"
check_root_owned_parent_ancestors "$PROBE_LAUNCHER"

sudo test -d "$PROBE_SYSTEM_STATE_ROOT"
test "$(sudo stat -c '%u:%g:%a' -- "$PROBE_SYSTEM_STATE_ROOT")" = "0:0:700"
test -d "$PROBE_USER_STATE_ROOT"
test -f "$PROBE_CONFIG"
test ! -L "$PROBE_CONFIG"
test "$(stat -c '%a:%h' -- "$PROBE_CONFIG")" = "600:1"
[[ "$PROBE_CONFIG" != "$OUTPUT_RUN_ROOT"/* ]]
[[ "$CLEANUP_MANIFEST" != "$OUTPUT_RUN_ROOT"/* ]]
[[ "$LINUX_OBSERVATION_FILE" != "$OUTPUT_RUN_ROOT"/* ]]
test "${LINUX_OBSERVATION_FILE##*/}" = \
  "selected-linux-executor-observation.json"
test ! -e "$CLEANUP_MANIFEST"
test ! -L "$CLEANUP_MANIFEST"
test ! -e "$LINUX_OBSERVATION_FILE"
test ! -L "$LINUX_OBSERVATION_FILE"

package_line=$(pacman -Q -- claude-desktop-extra) || exit 1
test "$package_line" = "claude-desktop-extra 2.9939.4-1"
owner_line=$(pacman -Qo -- "$TARGET") || exit 1
test "$owner_line" = \
  "$TARGET is owned by claude-desktop-extra 2.9939.4-1"

hash_file() {
  local output digest marker
  output=$(sudo sha256sum -- "$1") || return 1
  if [[ "$output" == \\* ]]; then
    output="${output:1}"
  fi
  digest="${output:0:64}"
  marker="${output:64:2}"
  [[ "$digest" =~ ^[0-9a-f]{64}$ ]]
  [[ "$marker" = "  " || "$marker" = " *" ]]
  printf '%s' "$digest"
}

check_reviewed_archive_verification() {
  [[ "$REVIEWED_ARCHIVE_VERIFICATION_SHA256" =~ ^[0-9a-f]{64}$ ]]
  test -f "$REVIEWED_ARCHIVE_VERIFICATION"
  test ! -L "$REVIEWED_ARCHIVE_VERIFICATION"
  test "$(stat -c '%h' -- "$REVIEWED_ARCHIVE_VERIFICATION")" = "1"
  test "$(hash_file "$REVIEWED_ARCHIVE_VERIFICATION")" = \
    "$REVIEWED_ARCHIVE_VERIFICATION_SHA256"
}

validate_protected_asset_manifest() {
  local manifest="$1"
  local role path digest uid gid mode links size actual
  local cursor component last_byte
  local main_count=0 native_count=0 sandbox_count=0
  local -a components
  local -A seen_paths=()

  test -f "$manifest"
  test ! -L "$manifest"
  test "$(stat -c '%h' -- "$manifest")" = "1"
  test -s "$manifest"

  last_byte=$(
    tail -c 1 -- "$manifest" |
      od -An -tu1 |
      tr -d ' '
  ) || return 1
  test "$last_byte" = "10"

  awk -F '\t' '
    NF != 8 { exit 1 }
    {
      if (index($0, "\r") != 0) exit 1
      for (field = 1; field <= 8; field += 1) {
        if ($field == "") exit 1
      }
    }
    END {
      if (NR == 0) exit 1
    }
  ' "$manifest" || return 1

  while IFS=$'\t' read -r \
    role path digest uid gid mode links size; do
    case "$role" in
      main-executable)
        ((main_count += 1))
        ;;
      native-asset)
        ((native_count += 1))
        ;;
      chrome-sandbox)
        ((sandbox_count += 1))
        test "${path##*/}" = "chrome-sandbox"
        ;;
      *)
        return 1
        ;;
    esac

    [[ "$path" = /* ]]
    [[ "$path" = "$PROBE_INSTALL_ROOT"/* ]]
    [[ "$path" != *$'\t'* ]]
    [[ "$path" != *$'\n'* ]]
    [[ "$path" != *$'\r'* ]]
    [[ -z "${seen_paths[$path]+x}" ]]
    seen_paths["$path"]=1

    cursor="/"
    IFS=/ read -r -a components <<< "${path#/}" ||
      return 1
    for component in "${components[@]}"; do
      [[
        -n "$component" &&
        "$component" != "." &&
        "$component" != ".."
      ]]
      cursor="${cursor%/}/$component"
      sudo test ! -L "$cursor"
    done

    [[ "$digest" =~ ^[0-9a-f]{64}$ ]]
    [[ "$uid" =~ ^(0|[1-9][0-9]*)$ ]]
    [[ "$gid" =~ ^(0|[1-9][0-9]*)$ ]]
    [[ "$mode" =~ ^[0-7]{3,4}$ ]]
    [[ "$links" =~ ^[1-9][0-9]*$ ]]
    [[ "$size" =~ ^(0|[1-9][0-9]*)$ ]]

    sudo test -f "$path"
    sudo test ! -L "$path"
    actual=$(
      sudo stat -c '%u:%g:%a:%h:%s' -- "$path"
    ) || return 1
    test "$actual" = \
      "$uid:$gid:$mode:$links:$size"
    test "$(hash_file "$path")" = "$digest"
  done < "$manifest"

  test "$main_count" = "1"
  test "$sandbox_count" = "1"
  test "$native_count" -gt 0
}

check_no_xattrs() {
  local output
  output=$(sudo getfattr --absolute-names -d -m- -- "$1") || return 1
  test -z "$output"
}

check_root_archive_file() {
  local path="$1" expected_sha256="$2" expected_size="$3"
  local actual acl

  [[ "$expected_sha256" =~ ^[0-9a-f]{64}$ ]]
  [[ "$expected_size" =~ ^(0|[1-9][0-9]*)$ ]]
  sudo test -f "$path"
  sudo test ! -L "$path"
  actual=$(sudo stat -c '%u:%g:%a:%h:%s' -- "$path") || return 1
  test "$actual" = "0:0:644:1:$expected_size"
  acl=$(sudo getfacl -cp -- "$path") || return 1
  test "$acl" = $'user::rw-\ngroup::r--\nother::r--'
  check_no_xattrs "$path"
  test "$(hash_file "$path")" = "$expected_sha256"
}

check_reviewed_launcher() {
  local actual mode
  check_root_owned_parent_ancestors "$PROBE_LAUNCHER"
  sudo test -f "$PROBE_LAUNCHER"
  sudo test ! -L "$PROBE_LAUNCHER"
  actual=$(sudo stat -c '%d:%i:%u:%g:%a:%h:%s' -- "$PROBE_LAUNCHER") ||
    return 1
  test "$actual" = "$PROBE_LAUNCHER_STAT"
  test "$(sudo stat -c '%u' -- "$PROBE_LAUNCHER")" = "0"
  mode=$(sudo stat -c '%a' -- "$PROBE_LAUNCHER") || return 1
  (( (8#$mode & 0022) == 0 ))
  test "$(hash_file "$PROBE_LAUNCHER")" = "$PROBE_LAUNCHER_SHA256"
}

load_reviewed_launch_argv() {
  local destination_name="$1" argv_fd path_before descriptor_before
  local descriptor_after path_after item hash_output digest marker extra
  local -n destination="$destination_name"

  destination=()
  test -f "$PROBE_LAUNCH_ARGV_FILE"
  test ! -L "$PROBE_LAUNCH_ARGV_FILE"
  path_before=$(stat -c '%d:%i:%u:%g:%a:%h:%s' -- \
    "$PROBE_LAUNCH_ARGV_FILE") || return 1
  test "$path_before" = "$PROBE_LAUNCH_ARGV_STAT"

  exec {argv_fd}<"$PROBE_LAUNCH_ARGV_FILE" || return 1
  descriptor_before=$(stat -Lc '%d:%i:%u:%g:%a:%h:%s' -- \
    "/proc/self/fd/$argv_fd") || {
      exec {argv_fd}<&-
      return 1
    }
  test "$descriptor_before" = "$path_before" || {
    exec {argv_fd}<&-
    return 1
  }

  while true; do
    item=
    if IFS= read -r -d '' item <&"$argv_fd"; then
      destination+=("$item")
      continue
    fi
    test -z "$item" || {
      exec {argv_fd}<&-
      return 1
    }
    break
  done

  descriptor_after=$(stat -Lc '%d:%i:%u:%g:%a:%h:%s' -- \
    "/proc/self/fd/$argv_fd") || {
      exec {argv_fd}<&-
      return 1
    }
  path_after=$(stat -c '%d:%i:%u:%g:%a:%h:%s' -- \
    "$PROBE_LAUNCH_ARGV_FILE") || {
      exec {argv_fd}<&-
      return 1
    }
  exec {argv_fd}<&-

  test ! -L "$PROBE_LAUNCH_ARGV_FILE"
  test "$descriptor_after" = "$descriptor_before"
  test "$path_after" = "$path_before"
  test "${#destination[@]}" = "1"
  test "${destination[0]}" = "$PROBE_LAUNCHER"

  hash_output=$(printf '%s\0' "${destination[@]}" | sha256sum) || return 1
  read -r digest marker extra <<< "$hash_output" || return 1
  test "$marker" = "-"
  test -z "${extra:-}"
  test "$digest" = "$PROBE_LAUNCH_ARGV_SHA256"
}

# BEGIN validate_reviewed_launch_environment
validate_reviewed_launch_environment() {
  local source_name="$1" assignment name value previous=""
  local hash_output digest marker extra component
  local -n source="$source_name"
  local -A seen=()
  local -a path_components

  test "${#source[@]}" -gt 0
  for assignment in "${source[@]}"; do
    [[ "$assignment" == *=* ]]
    name="${assignment%%=*}"
    value="${assignment#*=}"
    [[ "$name" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]
    [[ -z "${seen[$name]+x}" ]]
    if [[ -n "$previous" ]]; then
      [[ "$previous" < "$name" ]]
    fi
    previous="$name"
    seen["$name"]=1

    case "$name" in
      HOME|USER|LOGNAME|PATH|CLAUDE_PROFILE|\
      XDG_CONFIG_HOME|XDG_DATA_HOME|XDG_DATA_DIRS|XDG_CACHE_HOME|\
      XDG_STATE_HOME|XDG_RUNTIME_DIR|DISPLAY|WAYLAND_DISPLAY|\
      XAUTHORITY|DBUS_SESSION_BUS_ADDRESS|XDG_SESSION_TYPE|\
      XDG_CURRENT_DESKTOP|XDG_SESSION_DESKTOP|DESKTOP_SESSION|\
      XDG_SESSION_CLASS|XDG_SEAT|XDG_VTNR|LANG|LANGUAGE|LC_ALL|\
      LC_ADDRESS|LC_COLLATE|LC_CTYPE|LC_IDENTIFICATION|\
      LC_MEASUREMENT|LC_MESSAGES|LC_MONETARY|LC_NAME|LC_NUMERIC|\
      LC_PAPER|LC_TELEPHONE|LC_TIME|GTK_IM_MODULE|QT_IM_MODULE|\
      XMODIFIERS|GDK_BACKEND|PULSE_SERVER|PIPEWIRE_RUNTIME_DIR|\
      SSH_AUTH_SOCK|GPG_AGENT_INFO|GNOME_KEYRING_CONTROL|TERM|\
      COLORTERM|DESKTOP_STARTUP_ID|CLAUDE_CONFIG_DIR|\
      CLAUDE_USE_XWAYLAND|CLAUDE_GPU_BACKEND|CLAUDE_DISABLE_GPU|\
      CLAUDE_ENABLE_VULKAN|CLAUDE_PASSWORD_STORE|\
      CLAUDE_NATIVE_TITLEBAR|CLAUDE_NO_WINDOW_CONTROLS|\
      CLAUDE_DISABLE_SYSTEMD_SCOPE|CLAUDE_KEEP_TTY|CLAUDE_LAUNCHER)
        ;;
      *)
        return 1
        ;;
    esac

    [[ "$value" != *$'\n'* && "$value" != *$'\r'* ]]
    if [[ "$name" = "CLAUDE_LAUNCHER" ]]; then
      test "$value" = "$PROBE_LAUNCHER"
    fi
  done

  for name in HOME USER LOGNAME PATH CLAUDE_PROFILE; do
    [[ -n "${seen[$name]+x}" ]]
  done

  for assignment in "${source[@]}"; do
    name="${assignment%%=*}"
    value="${assignment#*=}"
    case "$name" in
      HOME)
        test "$value" = "$PROBE_HOME"
        [[ "$value" = /* ]]
        ;;
      CLAUDE_PROFILE)
        test "$value" = "$PROBE_PROFILE"
        ;;
      PATH)
        [[
          -n "$value" &&
          "$value" != :* &&
          "$value" != *: &&
          "$value" != *::*
        ]]
        IFS=: read -r -a path_components <<< "$value" || return 1
        test "${#path_components[@]}" -gt 0
        for component in "${path_components[@]}"; do
          [[ -n "$component" && "$component" = /* ]]
        done
        ;;
    esac
  done

  hash_output=$(printf '%s\0' "${source[@]}" | sha256sum) || return 1
  read -r digest marker extra <<< "$hash_output" || return 1
  test "$marker" = "-"
  test -z "${extra:-}"
  test "$digest" = "$PROBE_LAUNCH_ENV_SHA256"
}
# END validate_reviewed_launch_environment

test -d "$TARGET_DIR"
test "$(stat -c '%u:%g:%a' -- "$TARGET_DIR")" = "0:0:755"
test -f "$TARGET"
test ! -L "$TARGET"
test "$(stat -c '%u:%g:%a:%h:%s' -- "$TARGET")" = \
  "0:0:644:1:54910454"
test "$(hash_file "$TARGET")" = "$PRISTINE_SHA256"
target_acl=$(getfacl -cp -- "$TARGET") || exit 1
test "$target_acl" = $'user::rw-\ngroup::r--\nother::r--'
check_no_xattrs "$TARGET"

for file in "$CANDIDATE_ARCHIVE" "$GENERATED_BUILD_RECEIPT" \
  "$PUBLISHED_BUILD_RECEIPT" "$REVIEWED_ARCHIVE_VERIFICATION" \
  "$PROBE_LAUNCH_ARGV_FILE" "$PROTECTED_ASSET_MANIFEST"; do
  test -f "$file"
  test ! -L "$file"
  test "$(stat -c '%h' -- "$file")" = "1"
done

check_reviewed_archive_verification
cmp -s -- "$GENERATED_BUILD_RECEIPT" "$PUBLISHED_BUILD_RECEIPT"
test "$(hash_file "$CANDIDATE_ARCHIVE")" = "$CANDIDATE_SHA256"
CANDIDATE_SIZE=$(stat -c '%s' -- "$CANDIDATE_ARCHIVE") || exit 1
[[ "$CANDIDATE_SIZE" =~ ^(0|[1-9][0-9]*)$ ]]
test "$(hash_file "$PROTECTED_ASSET_MANIFEST")" = \
  "$PROTECTED_ASSET_MANIFEST_SHA256"
validate_protected_asset_manifest \
  "$PROTECTED_ASSET_MANIFEST"
check_reviewed_launcher
PREFLIGHT_LAUNCH_ARGV=()
load_reviewed_launch_argv PREFLIGHT_LAUNCH_ARGV
unset PREFLIGHT_LAUNCH_ARGV

# Populate only from launchRoute.environment in the validated private record.
PROBE_LAUNCH_ENV=()
# The operator inserts the exact reviewed name=value array here as shell data,
# without source, eval, ambient expansion, or an additional environment read.
validate_reviewed_launch_environment PROBE_LAUNCH_ENV
unset PROBE_LAUNCH_ENV

sudo test ! -e "$STAGE"
sudo test ! -L "$STAGE"
sudo test ! -e "$BACKUP_RUN_ROOT"
sudo test ! -L "$BACKUP_RUN_ROOT"
test ! -e "$OUTPUT_RUN_ROOT"
test ! -L "$OUTPUT_RUN_ROOT"
mv --help | grep -q -- '--exchange'
mv --help | grep -q -- '--no-copy'
```

Review the generated and published receipts, their byte-for-byte comparison, the
separately bound published revision, and the archive-verification record.
Confirm that the candidate hash comes from that receipt and that the complete
unchanged-asset inventory matches it. Every later receipt comparison or
archive-evidence check must call
`check_reviewed_archive_verification` again and compare the current record
bytes with `REVIEWED_ARCHIVE_VERIFICATION_SHA256`; an earlier successful
comparison cannot be reused.

At every later point that requires the complete protected-asset check, run
`validate_protected_asset_manifest "$PROTECTED_ASSET_MANIFEST"` again after
rechecking the manifest file's bound SHA-256. Do not evaluate a row as shell
text or use it to construct a command string.

Quit Claude Desktop through its UI. Under the later grant, the exact selected
application PID may be checked against the profile-specific `SingletonLock`;
static review only establishes that the lock contains a PID. Do not infer that
one PID proves every process has exited. If the current profile is not
quiescent, stop. If another Desktop instance uses the shared installed
resources, return for an operating decision. Do not enumerate unrestricted
processes.

```bash
install -d -m 0700 -- "$OUTPUT_RUN_ROOT"
sudo install -d -o 0 -g 0 -m 0700 -- "$BACKUP_RUN_ROOT"
sudo cp --preserve=all --reflink=never -- "$TARGET" "$BACKUP"

check_root_archive_file \
  "$BACKUP" "$PRISTINE_SHA256" "54910454"
sudo cmp -s -- "$TARGET" "$BACKUP"
```

## Atomic candidate exchange

The build receipts must still compare byte for byte immediately before the
candidate is copied into the package-owned staging path.

```bash
check_reviewed_archive_verification
cmp -s -- "$GENERATED_BUILD_RECEIPT" "$PUBLISHED_BUILD_RECEIPT"
test "$(hash_file "$CANDIDATE_ARCHIVE")" = "$CANDIDATE_SHA256"

sudo install -o 0 -g 0 -m 0644 -- "$CANDIDATE_ARCHIVE" "$STAGE"
check_root_archive_file \
  "$STAGE" "$CANDIDATE_SHA256" "$CANDIDATE_SIZE"
sudo sync -f -- "$STAGE"
```

Immediately repeat the package, ownership, target identity, pristine hash, ACL,
xattr, backup, receipt comparison, and protected-asset manifest checks. Then
exchange:

```bash
sudo mv --exchange --no-copy -- "$STAGE" "$TARGET"
sudo sync -f -- "$TARGET_DIR"
test "$(hash_file "$TARGET")" = "$CANDIDATE_SHA256"
test "$(sudo stat -c '%u:%g:%a:%h' -- "$TARGET")" = "0:0:644:1"
test "$(hash_file "$STAGE")" = "$PRISTINE_SHA256"
test "$(sudo stat -c '%u:%g:%a:%h:%s' -- "$STAGE")" = \
  "0:0:644:1:54910454"
sudo cmp -s -- "$STAGE" "$BACKUP"
```

Unknown identities are a stop condition. If the pristine stage is lost, retain
the protected backup and stop; do not use an unreviewed fallback.

## Launch and collection

Immediately before the candidate launch, repeat `pacman -Q`, `pacman -Qo`, the
target candidate identity, the complete protected-asset manifest, and the
receipt comparison. Repeat every applicable check in
[Bound launcher routing](#bound-launcher-routing). Revalidate the root-owned
launcher and its ancestors, then read the argument file once through one stable
descriptor. Reconstruct `PROBE_LAUNCH_ENV` manually from the validated private
record and use only those two validated in-memory arrays.

```bash
package_line=$(pacman -Q -- claude-desktop-extra) || exit 1
test "$package_line" = "claude-desktop-extra 2.9939.4-1"
owner_line=$(pacman -Qo -- "$TARGET") || exit 1
test "$owner_line" = \
  "$TARGET is owned by claude-desktop-extra 2.9939.4-1"
test "$(hash_file "$TARGET")" = "$CANDIDATE_SHA256"
check_reviewed_archive_verification
cmp -s -- "$GENERATED_BUILD_RECEIPT" "$PUBLISHED_BUILD_RECEIPT"

PROBE_LAUNCH_ARGV=()
load_reviewed_launch_argv PROBE_LAUNCH_ARGV
check_reviewed_launcher
PROBE_LAUNCH_ENV=()
# Insert the exact reviewed name=value array from the private record.
validate_reviewed_launch_environment PROBE_LAUNCH_ENV
/usr/bin/env -i "${PROBE_LAUNCH_ENV[@]}" \
  "PROVINGKIT_OBSERVER_CONFIG=$PROBE_CONFIG" \
  "${PROBE_LAUNCH_ARGV[@]}"
unset PROBE_LAUNCH_ARGV PROBE_LAUNCH_ENV
```

Immediately after launch, complete the selected-process, effective-argv,
adjacent-archive, flags, and profile checks. These checks precede the bootstrap
wait, but they do not complete the candidate bootstrap binding. The launcher,
route, and stable-input checks narrow the mutation window; they do not make
script execution atomic. A changed package, launcher, launcher ancestor,
argument-file identity, reconstructed argument or environment digest, flags
state, profile branch, executable, version, resources route, archive identity,
or protected asset is a stop condition.

After candidate launch and before waiting for bootstrap, submit this exact
second prompt on the same recorded fixture:

```text
This is a disposable observer fixture. Reply exactly `PROBE_READY`. Do not use tools, inspect files, change settings, or begin other work.
```

The sidecar writes `bootstrap.json` into the selected private run directory
after binding the existing query. Under the later grant, the executor reads only
that exact file, validates every generated bootstrap value, compares every
binding field with the approved task, Code identity, candidate bytes,
configuration digest, and clock domain, then exclusively creates the matching
`arm.json`. Before creating the arm, compare the validated bootstrap PID with
the already attested process and its copied-archive digest with the candidate
digest. The arm echoes every `BINDING_KEYS` field, including the Linux boot
domain. Follow the exact encoding and file-identity procedure in
`private-input-construction.md`. The three query getters run only after arm
acceptance. Do not start a getter or accept a settlement at or after the
30-second monotonic observation deadline. Clamp every asynchronous wait to the
lesser of its two-second limit and the remaining window. A timed-out or
synchronously blocked getter cannot be forcibly cancelled and can outlive the
deadline; do not treat that possibility as authority for another call or
sample.

The reviewed helper is limited to two metadata checks of the selected numeric
PID path, one owned `O_DIRECTORY | O_NOFOLLOW` descriptor open, seven
descriptor metadata checks, three `stat` opens reading at most 4,096 bytes
each, two `exe` opens, and at most 256 MiB hashed. Every child open uses only a
fixed name beneath the retained descriptor after an immediate identity,
ownership, and freshness recheck. It must not re-resolve a child through the
numeric PID path or read environments, command lines, unrelated processes,
transcripts, or historical peers. Comparing a process report does not establish
the Code query's OS-process association; that remains unknown.

Construct the one authorized helper invocation from
[the normative contract](private-data-contracts.md#normative-private-contracts)
and apply the exact byte procedure in
[private input construction](private-input-construction.md). Invoke the
exported helper at most once and only when an actual usable sample supplies the
sequence and complete accepted binding. Validate its in-memory return against
one normative result variant, construct the normative wrapper, and serialize
only that wrapper into `LINUX_OBSERVATION_FILE`.

If no usable sample exists, the helper is not called. If the helper is not
reached, is deliberately not called, or retained-file creation or validation
fails, do not invoke it again to fill the cleanup manifest. Record the
retained-evidence state and terminal reason defined in
[the cleanup contract](private-data-contracts.md#private-cleanup-manifest-and-retention).
Retain any created
but unvalidated path as an unresolved resource.

A valid retained file is a private regular single-link `0600` file no larger
than 16384 bytes. Record its exact identity and digest in the cleanup manifest.
Do not serialize a caught error, exception text, arbitrary raw object, or fake
binding.

This window permits one arm only. A timeout or failed experiment requires a new
plan and window, not an automatic retry.

After collection ends, whether successfully or unsuccessfully, quit Claude
Desktop through its UI before any restoration check or exchange. Verify that
the exact selected PID has exited where that can be established, then verify
that the current profile is quiescent. One observed PID does not prove that all
activity has ended. If the profile is not quiescent or an unknown or shared
consumer still uses the installed resources, stop for an operating decision.

## Restore and verify

Before reversing, repeat `pacman -Q`, `pacman -Qo`, the complete protected-asset
manifest, and these identity checks:

```bash
check_root_archive_file \
  "$TARGET" "$CANDIDATE_SHA256" "$CANDIDATE_SIZE"
check_root_archive_file "$STAGE" "$PRISTINE_SHA256" "54910454"
check_root_archive_file "$BACKUP" "$PRISTINE_SHA256" "54910454"
sudo cmp -s -- "$STAGE" "$BACKUP"
```

If the package version changed, ownership is unknown, or either archive
identity fails, do not reverse the exchange.

```bash
sudo mv --exchange --no-copy -- "$STAGE" "$TARGET"
sudo sync -f -- "$TARGET_DIR"

test "$(hash_file "$TARGET")" = "$PRISTINE_SHA256"
test "$(sudo stat -c '%u:%g:%a:%h:%s' -- "$TARGET")" = \
  "0:0:644:1:54910454"
restored_acl=$(sudo getfacl -cp -- "$TARGET") || exit 1
test "$restored_acl" = $'user::rw-\ngroup::r--\nother::r--'
check_no_xattrs "$TARGET"
sudo cmp -s -- "$TARGET" "$BACKUP"
test "$(hash_file "$STAGE")" = "$CANDIDATE_SHA256"
```

Repeat the package, ownership, complete-manifest, receipt, and reviewed
archive-verification checks, including a fresh
`check_reviewed_archive_verification` call. Immediately before the restored
launch, recheck the package and pristine target and repeat every applicable
check in [Bound launcher routing](#bound-launcher-routing). Revalidate the
launcher and its root-owned ancestors, reconstruct the argument array through a
newly opened stable descriptor, and reconstruct the clean environment from the
private record. Do not reuse either candidate-launch array.

```bash
package_line=$(pacman -Q -- claude-desktop-extra) || exit 1
test "$package_line" = "claude-desktop-extra 2.9939.4-1"
owner_line=$(pacman -Qo -- "$TARGET") || exit 1
test "$owner_line" = \
  "$TARGET is owned by claude-desktop-extra 2.9939.4-1"
test "$(hash_file "$TARGET")" = "$PRISTINE_SHA256"
check_reviewed_archive_verification

PROBE_LAUNCH_ARGV=()
load_reviewed_launch_argv PROBE_LAUNCH_ARGV
check_reviewed_launcher
PROBE_LAUNCH_ENV=()
# Insert the exact reviewed name=value array from the private record.
validate_reviewed_launch_environment PROBE_LAUNCH_ENV
/usr/bin/env -i "${PROBE_LAUNCH_ENV[@]}" \
  "${PROBE_LAUNCH_ARGV[@]}"
unset PROBE_LAUNCH_ARGV PROBE_LAUNCH_ENV
```

Complete the restored selected-process, effective-argv, and adjacent-archive
attestation before accepting the launch. The restored cycle performs no
bootstrap read or bootstrap-binding comparison. Then verify the selected
profile opens and inspect the same fixture against the recorded restoration
expectations. Restored bytes, protected assets, route attestation, and task
behavior are separate acceptance checks.

## Package cleanup

Package cleanup is a distinct phase before cleanup-manifest creation. It may
remove only `STAGE`, `BACKUP`, and `BACKUP_RUN_ROOT`, and only after restoration
is `verified`. It does not require the issue 281 private-cleanup decision. A
`not-required`, incomplete, or otherwise unverified restoration authorizes no
package deletion. Incomplete restoration also prohibits every private, task,
project, worktree, and manifest deletion.

Immediately before deleting the package staging copy and protected backup,
repeat the exact `STAGE` candidate identity and `BACKUP` pristine identity,
metadata, ACL, xattr, and comparison checks.

```bash
check_root_archive_file \
  "$BACKUP" "$PRISTINE_SHA256" "54910454"
sudo cmp -s -- "$TARGET" "$BACKUP"

check_root_archive_file \
  "$STAGE" "$CANDIDATE_SHA256" "$CANDIDATE_SIZE"
sudo rm -- "$STAGE"
sudo test ! -e "$STAGE"
sudo test ! -L "$STAGE"

check_root_archive_file \
  "$BACKUP" "$PRISTINE_SHA256" "54910454"
sudo cmp -s -- "$TARGET" "$BACKUP"
sudo rm -- "$BACKUP"
sudo test ! -e "$BACKUP"
sudo test ! -L "$BACKUP"

sudo rmdir -- "$BACKUP_RUN_ROOT"
sudo test ! -e "$BACKUP_RUN_ROOT"
sudo test ! -L "$BACKUP_RUN_ROOT"
```

After each command, record only the resource state established by the command
and its absence check. On an identity-precheck mismatch or failure before any
deletion attempt, record a new `package-cleanup` failure through the existing
status rules, preserving `firstFailure` and the top-level earliest stopped
phase, set `packageCleanup.state` to `retained`, and stop without retrying. If
removal was attempted but none was verified, use `failed`; if at least one
removal was verified before failure, use `partial`. Retain every resource
still known or possibly present. Attempt package deletion only after verified
restoration, and remove no other package-owned path.

## Private cleanup manifest and retention

After package cleanup ends, or at terminal stop when package deletion is
prohibited, create the cleanup manifest and apply the retention handling
defined by
[Private probe data contracts](private-data-contracts.md#private-cleanup-manifest-and-retention).
Use only facts established during this run; do not introduce alternative
fields, states, reasons, or enum values.
