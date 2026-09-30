# Construct the private fixture inputs

This document defines how to construct, validate, canonicalize, and exclusively
create private bytes for one authorized run. The normative selected-fixture
projection, selected-executor invocation and result variants, and
cleanup-manifest schema are in
[private probe data contracts](private-data-contracts.md#normative-private-contracts)
and its
[private cleanup manifest and retention](private-data-contracts.md#private-cleanup-manifest-and-retention)
section. This document must not add alternative fields, states, reasons, or
enum values.

It contains placeholders, not private values or live authority. The
authorization resolution binds the final immutable published revision and the
populated private record. No source-controlled example, placeholder, path,
digest, identifier, or bootstrap value authorizes an application change,
private read, prompt, arm, helper invocation, or cleanup action.

## Bound private record

Before staging, the private record must contain this complete fragment. Replace
each angle-bracket string with one authorized value. Integer zeroes are
placeholders and must be replaced where the field requires a positive integer.
The populated record must contain no angle-bracket placeholder.

```json
{
  "schema": "provingkit.desktop-probe-private-bindings.v1",
  "source": {
    "publishedRevision": "<immutable reviewed Git revision>",
    "generatedBuildReceipt": {
      "path": "<exact absolute build-receipt.json path>",
      "sha256": "<lowercase SHA-256>"
    },
    "publishedBuildReceipt": {
      "path": "<exact absolute candidate-build.json path>",
      "sha256": "<same lowercase SHA-256>"
    },
    "archiveVerification": {
      "path": "<exact absolute reviewed verification-record path>",
      "sha256": "<lowercase SHA-256>"
    },
    "candidateSha256": "<receipt candidate SHA-256>",
    "managerSha256": "<receipt manager SHA-256>",
    "moduleSha256": "<receipt sidecar SHA-256>"
  },
  "launchRoute": {
    "accountId": "<exact current account identity>",
    "organizationId": "<exact current organization identity>",
    "userDataRoot": {
      "path": "<exact absolute Electron userData directory>",
      "stat": "<device:inode:uid:gid:mode>"
    },
    "launcher": {
      "path": "/usr/bin/claude-desktop",
      "sha256": "015f5232d3c2c40f04f5529d44058d3fd0a80cdce0eddf91dc08688f0a8c867e",
      "stat": "<device:inode:uid:gid:mode:links:size>"
    },
    "launchArgumentFile": {
      "path": "<exact absolute PROBE_LAUNCH_ARGV_FILE>",
      "sha256": "<lowercase SHA-256 of its exact NUL-delimited bytes>",
      "stat": "<device:inode:uid:gid:mode:links:size>"
    },
    "profile": {
      "kind": "<default|named>",
      "name": "<default or exact current named profile>",
      "home": "<exact absolute HOME>",
      "configDirectory": "<exact launcher-selected config_dir>",
      "configDirectoryStat": "<device:inode:uid:gid:mode>",
      "claudeConfigDirectory": {
        "state": "<absent|present>",
        "value": "<omit only when absent; preserve an empty or nonempty value exactly>"
      },
      "locks": [
        "<config_dir/SingletonLock>",
        "<config_dir-3p/SingletonLock>"
      ],
      "namedExecutable": {
        "state": "<not-applicable|absent|ready>",
        "path": "<omit only for not-applicable; otherwise exact named executable path>",
        "readyIdentity": "<ready only: device:inode:uid:gid:mode:links:size>",
        "readySha256": "<ready only: reviewed executable SHA-256>"
      }
    },
    "environment": {
      "encoding": "ordered-nul-delimited-name-equals-value",
      "sha256": "<lowercase SHA-256>",
      "entries": [
        {
          "name": "<allowed environment name>",
          "value": "<exact reviewed value>"
        }
      ]
    },
    "shellExecutable": {
      "environmentValue": "<exact permitted absolute SHELL value>",
      "routeContract": "linux-system-shell-v1",
      "resolvedPath": "<exact byte-preserved canonical executable path>",
      "stat": "<device:inode:uid:gid:mode:links:size>",
      "sha256": "<lowercase SHA-256>"
    },
    "kdeSessionVersion": {
      "state": "<absent|present>",
      "value": "<present only: 5|6>",
      "sourceWalletBranch": "<kwalletd5|kwalletd6>"
    },
    "launchControl": {
      "mechanism": "systemd-user-transient-service.v1",
      "candidateUnit": "<exact provingkit-278-...-candidate.service>",
      "restoredUnit": "<exact provingkit-278-...-restored.service>",
      "clientOptions": [
        "--description=Provingkit task 278 Desktop launch control",
        "--expand-environment=no"
      ],
      "workingDirectory": {
        "path": "<exact absolute existing directory>",
        "stat": "<device:inode:uid:gid:mode>"
      },
      "serviceProperties": [
        "Type=exec",
        "RemainAfterExit=yes",
        "Restart=no",
        "KillMode=process",
        "StandardInput=null",
        "StandardOutput=null",
        "StandardError=null"
      ],
      "managerStorageEffect": {
        "runtimeUnitStorage": "XDG_RUNTIME_DIR/systemd/transient",
        "storedLaunchConfiguration": "selected-noncredential-execstart"
      },
      "metadataObservation": {
        "acquisition": "all-properties-for-exact-task-unit",
        "outputProjection": [
          "LoadState",
          "ActiveState",
          "SubState",
          "Result",
          "ExecMainCode",
          "ExecMainStatus",
          "MainPID"
        ]
      },
      "applicationPidSource": "selected-profile-lock-attestation"
    },
    "flags": {
      "state": "<absent|present>",
      "path": "<exact selected claude-desktop-flags.conf path>",
      "sha256": "<present only: lowercase SHA-256>",
      "stat": "<present only: device:inode:uid:gid:mode:links:size>",
      "tokens": ["<present only: exact ordered parsed token>"]
    },
    "execution": {
      "executable": "<exact canonical or ready named-profile executable>",
      "executableSha256": "<reviewed executable SHA-256>",
      "versionFile": {
        "path": "<exact selected executable-adjacent version path>",
        "sha256": "<lowercase SHA-256>",
        "stat": "<device:inode:uid:gid:mode:links:size>",
        "firstLine": "44.4.3"
      },
      "resources": "<exact selected executable-adjacent resources path>",
      "appAsar": "<exact selected executable-adjacent resources/app.asar path>",
      "passwordStoreBranch": "<forwarded|environment-auto|environment-explicit|detector-bounded>",
      "effectiveArgvVariants": [
        {
          "sha256": "<lowercase SHA-256 of the NUL-delimited argv>",
          "argv": ["<exact ordered argument including argv[0]>"]
        }
      ]
    }
  },
  "fixture": {
    "creationRoute": "normal-new-local-task-ui",
    "taskId": "<selected task ID>",
    "codeSessionId": "<selected cliSessionId>",
    "metadataPath": "<exact absolute source-constructed path ending in /<taskId>.json>",
    "projectPath": "<exact absolute real project path>",
    "optionalPathStates": {
      "originCwd": "<absent|empty|exact absolute approved real-directory path>",
      "worktreePath": "<absent|empty|exact absolute approved real-directory path>"
    },
    "worktree": "<absent or exact absolute real app-created worktree path>"
  },
  "paths": {
    "runDirectory": "<exact absolute OUTPUT_RUN_ROOT>",
    "configuration": "<exact absolute PROBE_CONFIG outside runDirectory>",
    "cleanupManifest": "<exact absolute CLEANUP_MANIFEST outside runDirectory>",
    "linuxObservation": "<exact absolute private path outside runDirectory ending in /selected-linux-executor-observation.json>"
  },
  "limits": {
    "setupDeadlineMs": 60000,
    "pollIntervalMs": 100,
    "maxSamples": 3,
    "minIntervalMs": 5000,
    "observationWindowMs": 30000,
    "perGetterTimeoutMs": 2000,
    "linuxObservationMaximumBytes": 16384
  }
}
```

The generated and published receipt bytes and hashes must match. The candidate,
manager, and module values come from that receipt. Do not copy those hashes
from prose. The final published revision is supplied by the authorization
resolution after publication; do not add a future or self-referential commit
hash to the candidate being reviewed.

Bind `REVIEWED_ARCHIVE_VERIFICATION` to
`source.archiveVerification.path` and
`REVIEWED_ARCHIVE_VERIFICATION_SHA256` to
`source.archiveVerification.sha256`. Require the digest to be exactly 64
lowercase hexadecimal characters. Every required archive-evidence check hashes
the current bytes at that path and compares them with the bound digest; neither
value may be independently substituted.

Require `launchRoute.accountId` and `launchRoute.organizationId` to be the
exact nonempty values established by a separately reviewed identity-acquisition
route for the selected current fixture. They must contain no control character
or placeholder and must equal the values used in the selected metadata-path
derivation and later fixture record. The selected metadata-file procedure
consumes these values; it does not acquire them.

Require `launchRoute.userDataRoot.path` to be the exact absolute Electron
`userData` root established by that separately reviewed route for the selected
profile. Open that exact directory without following the final component,
require a same-UID directory that is not group- or world-writable, compare its
device, inode, UID, GID, and mode with `launchRoute.userDataRoot.stat`, and
require the path still names that opened identity. The selected metadata path
must be the exact join of this root, `claude-code-sessions`, the bound account
ID, the bound organization ID, and the bound task filename. Configuration
construction cannot begin until the complete profile, account, organization,
user-data-root, task-ID, and Code-ID prerequisite has been satisfied.

Require `launchRoute.launchArgumentFile` to equal the reviewed
`PROBE_LAUNCH_ARGV_FILE`, `PROBE_LAUNCH_ARGV_SHA256`, and
`PROBE_LAUNCH_ARGV_STAT` bindings. Validate it through the stable-descriptor
procedure in `application-operation.md`: it is a non-symlink regular
single-link file whose exact bytes are one NUL-terminated
`/usr/bin/claude-desktop` argument. No additional read or inferred argv source
may populate this fragment.

## Launch-routing inputs

Construct `launchRoute` only through the bounded observations and derivation in
`application-operation.md`. This is the sole definition of the private
launch-route fragment; other documents consume it rather than restating its
shape.

The later grant permits a name-only inventory of the ambient environment.
Read a value only when that grant explicitly approves the name. Adding
`SHELL` and `KDE_SESSION_VERSION` to the source allowlist does not
retroactively authorize those value reads. Preserve the exact literal
`SHELL`; do not replace it with its resolved path. Preserve absence of
`KDE_SESSION_VERSION`, and preserve a present exact `5` or `6`. Do not dump
the environment, read a credential or API-key value, enumerate a profile
directory except for the narrowly authorized named-profile no-refresh symlink
check, or read the selected profile's JSON or JSONC configuration.

The presence of `CLAUDE_USER_DATA_DIR` is a stop for amended review without
reading its value. It is not an allowed environment entry or evidence for the
active Electron user-data root. `CHROME_DESKTOP` also remains rejected.

Sort environment entries bytewise by `name`, reject duplicate names, and
compute `launchRoute.environment.sha256` over exact `name=value` strings, each
followed by one NUL byte. Preserve present empty values. Validate `HOME`,
`PATH`, `SHELL`, `CLAUDE_PROFILE`, XDG/config states, display/session values,
the optional KDE selector, and every `CLAUDE_` launcher variable against the
procedure. Missing `SHELL` or a required variable outside the allowlist is a
stop for an amended review.

Bind `launchRoute.shellExecutable.environmentValue` to the exact `SHELL`
entry without rewriting it. Set `routeContract` to
`linux-system-shell-v1`. Accept only `/usr/bin/zsh` or `/bin/zsh` with
canonical target `/usr/bin/zsh`, `/usr/bin/bash` or `/bin/bash` with canonical
target `/usr/bin/bash`, and `/usr/bin/sh` or `/bin/sh` with canonical target
`/usr/bin/bash`. Any other literal and canonical pair returns for a separate
decision.

Read canonical and direct symlink targets with the byte-preserving route
check. Require the fixed route's directories to be root-owned and not group-
or world-writable. Require every permitted symlink to be root-owned, reached
through a protected directory, and to have the exact target spelling allowed
by the route contract. Record the byte-preserved canonical target and the
target's device, inode, UID, GID, mode, link count, size, and SHA-256. Do not
record a recursive route digest or prohibited-root list.

For `kdeSessionVersion.state=absent`, omit `value` and record
`sourceWalletBranch=kwalletd5`. For a present `5`, record the same branch. For
a present `6`, record `sourceWalletBranch=kwalletd6`. No other value or branch
is representable. This is a source-selection binding, not evidence that the
site was reached or that wallet access succeeded.

The environment array is reconstructed manually in memory before each launch.
The approved selected entries and their digest remain in the private record as
launch configuration and recovery input; discard only the reconstructed
per-launch array after comparison. Do not create an environment file, write
assignments to a shell script, or use `source` or `eval`. Because this increment
creates no separate environment file, it adds no cleanup-manifest resource or
later deletion step. Reconstruct the shell binding from the existing private
record for every preflight, candidate, restored, or recovery route check; do
not reacquire or derive a replacement `SHELL` value from ambient state.

Require `launchControl.mechanism`, every ordered `clientOptions` value, every
ordered `serviceProperties` value, both `managerStorageEffect` values,
`metadataObservation.acquisition`, and the complete ordered
`metadataObservation.outputProjection` to equal the literals above. The fixed
description must not be replaced with the command, unit name, cycle name, or
private value. Disabled environment expansion is mandatory for both
submissions. The candidate and restored unit names must be distinct, no more
than 200 bytes, match the cycle-specific patterns in
`application-operation.md`, and be absent from the selected user's manager
before their respective one-time submissions. Do not derive a unit name at
runtime or reuse one after failure.

Open `launchControl.workingDirectory.path` without following its final
component. Require an existing directory owned by the selected Desktop UID,
not group- or world-writable, and compare its device, inode, UID, GID, and mode
with `launchControl.workingDirectory.stat` before each launch. The transient
service uses this exact path rather than an inherited shell working directory.

The application command remains an inner `/usr/bin/env -i` followed by the
already validated launcher array. The candidate adds only the authorized
observer-configuration assignment; the restored launch adds none. The outer
`systemd-run` client also receives the reviewed base environment through
`/usr/bin/env -i` solely to select the bound user manager and graphical
session. `--expand-environment=no` prevents systemd-run from expanding dollar
expressions in any inner assignment or launcher argument. Do not treat its
PID, the transient unit's `MainPID`, or launcher exit status as the application
PID. `applicationPidSource` fixes the existing selected-lock attestation as
that source.

The transient service creates manager state and generated runtime unit
configuration under `$XDG_RUNTIME_DIR/systemd/transient`. Its generated
`ExecStart` setting contains the exact selected noncredential environment
assignments, including the literal `SHELL` and present
`KDE_SESSION_VERSION`, the candidate observer-configuration path assignment
when present, and the launcher arguments. This manager-owned runtime file is
not a separately created private-input or cleanup-manifest role, but its
creation, retention, and manager-mediated retirement are operating effects
that the later grant must cover. Do not inspect or delete the file manually.

The property-show client acquires all manager-exposed properties for the exact
addressed unit before printing the requested projection. Permit that
acquisition only for the two exact task-owned unit names and retain only the
seven `metadataObservation.outputProjection` fields in the phase record.
Existing task-unit metadata is separate from private receiver payloads. Do not
enumerate other units or processes, collect application output, or read the
unit journal. After bounded quiescence, retirement uses only the exact unit and
is complete only when its property-show result is
`LoadState=not-found`. If the restored application remains open, retain its
exact manager state and generated configuration until later normal UI shutdown
and that same retirement check. A lost unit or supervisor does not authorize
another submission.

For a present flags file, acquire only its exact path through one stable
descriptor. Record and compare its identity and digest, then apply the
launcher's exact line/comment/default-IFS tokenization. Do not enumerate its
parent. For an absent file, record and recheck only the exact path's absence.

For a default profile, record named-executable state `not-applicable`. For a
named profile with no profile executable, record `absent`; do not create or
materialize it. For an existing named executable, record `ready` only after
the exact no-refresh predicates, byte equality with the canonical executable,
resource-link target, and bounded sibling-symlink inventory pass. Any refresh
predicate returns for a decision and must not be represented as `ready`.

The selected `configDirectory` must already exist before either launch. Open
the exact path with directory and no-follow semantics, require the final path
to be a non-symlink same-UID directory that is not group- or world-writable,
and record its device, inode, UID, GID, and mode as
`configDirectoryStat`. Recheck that identity immediately before and after
each launch without enumerating the directory. The launcher may execute
`mkdir -p` for this path, but the existence precondition makes that operation
a no-op. An absent or changed directory stops before launch; do not create,
replace, repair, or later remove it. This pre-existing profile directory is
not a cleanup-manifest resource.

Derive `effectiveArgvVariants` only from the inspected launcher revision,
reviewed environment, profile branch, and exact flags tokens. Apply the ordered
algorithm in `application-operation.md`. Record one variant unless absent
`CLAUDE_PASSWORD_STORE` and absence of a forwarded password-store token selects
the ordinary detector branch; that branch records exactly the no-added-flag
and `--password-store=gnome-libsecret` variants. Do not run the detector during
construction, alter password-store state, derive argv from logs, or copy a
prior process command line.

Each `argv` begins with the exact selected Electron executable. Compute its
digest over every exact element followed by NUL. Reject an unexpected
positional argument, empty executable, legacy executable, `--no-sandbox`,
unreviewed feature, or route-changing flag.

## Fixture construction and selected metadata

Create a new dedicated empty directory that is not a Git repository or
worktree. Create the task through Desktop's normal new-local-task route. Never
fork, spawn, import, duplicate, or reuse a task.

Before task creation:

1. Resolve the chosen project path to its exact real path. Reject a missing
   component, symlink component, path substitution, or identity mismatch. Do
   not resolve or invent a worktree.
2. Record the project directory's path, device, inode, UID, GID, and mode from
   the opened directory and confirm the path still resolves to that opened
   identity.
3. Inspect only the immediate directory entries. Require an empty list. Do not
   recurse into the directory or inspect unrelated projects, worktrees, tasks,
   or sessions.
4. Record the normal new-local-task UI route and the creation timestamp. Stop
   if another actor may use the selected project directory during the run.

If Desktop creates a dedicated worktree, record its exact identity and inspect
only its immediate entries. Require the exact app-managed entries selected by
the later grant. An unexpected worktree or directory shape returns for a
decision.

Reviewed source constructs the selected manager path as
`path.join(Electron app.getPath("userData"), "claude-code-sessions",
currentAccountId, currentOrgId, taskId + ".json")`. Construct the exact
absolute path only after a separately reviewed acquisition route has
established the exact selected profile, account, organization, Electron
user-data root, task ID, and Code ID. Normal UI availability of that complete
tuple remains unestablished. The selected metadata path cannot establish the
values required to locate itself. The source-defined base is
`claude-code-sessions`. `getSessionFilePath` is an internal source method, not
an approved callable UI or API; never invoke it. Do not enumerate the
containing directory, scan other task files, or read a transcript.

Acquire the selected metadata through one stable descriptor. Starting at the
already bound `userData` directory, check each constructed path component with
`lstat`; reject every symlink component, a component owned by another UID, or a
directory writable by group or other. Do not enumerate any component.

For the final path:

1. `lstat` it and require a regular non-symlink file owned by the selected
   Desktop UID, with one link and a size from 1 through 65536 bytes. Record
   device, inode, UID, GID, mode, link count, size, nanosecond mtime, and
   nanosecond ctime. Do not require mode `0600`: a source-written `0644` file
   inside the private profile is acceptable. Reject group- or world-writable
   mode.
2. Open that exact path once with `O_RDONLY|O_NOFOLLOW`. `fstat` the descriptor
   before reading and require every recorded field to equal the preceding
   `lstat`.
3. Read at most 65537 bytes from the descriptor. Require exactly the recorded
   size followed by EOF; a short read, additional byte, or size above 65536 is
   a stop condition.
4. `fstat` the same descriptor after reading and require device, inode, type,
   UID, GID, mode, link count, size, mtime, and ctime to equal the descriptor's
   pre-read state.
5. `lstat` the final path again, require that it is still a non-symlink, and
   require the same fields to equal the descriptor state. Then close the
   descriptor.
6. Strictly decode only the captured bytes as UTF-8 and parse one JSON object.
   Project only the fields listed below. Do not retain or export the raw bytes,
   the unprojected object, or any additional field.

Repeat this acquisition immediately before staging. The two accepted
projections and their file identities must match. A replacement, mutation,
ownership change, additional link, or projection change is a stop condition.

Project only the source-backed fields in the normative selected-metadata
projection in
[private probe data contracts](private-data-contracts.md#normative-private-contracts).
Require `sessionId` to equal the selected Desktop task ID,
`cliSessionId` to equal the recorded Code ID, and `cwd` to match the already
opened project identity, not only its spelling.

nE uses an empty-string fallback for `originCwd`, while JSON serialization
omits optional properties whose value is undefined. Preserve each optional
path as absent, empty, or its approved nonempty real-directory path. Preserve
each optional lineage field's actual presence. A present spawn,
dispatch-parent, or fork value must be null, and a present
`lineageDetached` value must be false. Any non-null relation, true
`lineageDetached`, missing required field, unexpected path, changed directory
identity, unexpected activity, or metadata change before staging is a stop
condition.

Persisted nE metadata does not serialize `backend.kind`. Record local creation
from the normal new-local-task UI provenance. The inspected adapter guard for
`backend.kind === "local"` with undefined SSH and WSL configuration remains
separate static source evidence, not persisted metadata or live proof.

Record the normative relation-evidence values without substitution:
`selectedMetadataRelations` is `no-nonnull-relation-observed`,
`globalChildAbsence` is `not-established-from-selected-metadata`, and
`unrelatedSharingAbsence` is `not-established`. Exclusive construction,
coordination, and nonrecursive project inspection do not establish global
absence.

## Configuration bytes

The configuration template below contains every accepted key. Its displayed
order has no validation or canonicalization meaning.

```json
{"copiedAsarSha256":"<receipt candidate SHA-256>","getterSetId":"desktop-query.readonly.v1:accountInfo,getContextUsage-summary,listPermissionRules","moduleSha256":"<receipt sidecar SHA-256>","pollIntervalMs":100,"runDirectory":"<exact absolute OUTPUT_RUN_ROOT>","runId":"<exact RUN_ID beginning 278->","schema":"desktop-observer.probe-config.v1","setupDeadlineMs":60000,"targetCodeSessionId":"<exact selected cliSessionId>","targetTaskId":"<exact selected sessionId>"}
```

Construct an in-memory object from the populated private record. Do not perform
text replacement or canonicalization on the displayed template. Validate the
populated object's exact keys, types, ranges, absolute paths, identifier
equality, receipt values, and absence of placeholders. Recursively sort that
object's keys, serialize once with
`JSON.stringify`, and encode with strict UTF-8. The configuration bytes contain
no BOM, indentation, trailing spaces, or final newline.

Compute `configSha256` over those exact bytes. Strictly decode the bytes as
UTF-8, parse them as JSON, repeat the validation and canonical serialization,
and require byte-for-byte equality before creating `PROBE_CONFIG`.
That equality check rejects reordered members, alternate whitespace and number
spellings, escapes that do not match canonical serialization, and duplicate
member names. Parsing collapses duplicate names, so duplicate-bearing input
cannot reproduce its original bytes and needs no separate generalized parser.

Create the exact final path once with
`O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW` and mode `0600`. Write all bytes through
that descriptor, set the descriptor mode to `0600`, sync it, and require a
regular file owned by the selected UID with one link and the exact byte count.
Close it, compare the final path's device and inode with the descriptor
identity, require that the path is not a symlink, and recheck mode, ownership,
link count, size, SHA-256, strict UTF-8 decoding, parsed values, and canonical
bytes. Sync the already validated parent directory. Any pre-existing path,
short write, changed identity, extra link, decoding failure, or mismatch stops
the run. Do not overwrite, truncate, rename over, or repair the path.

The configuration remains outside the initially empty `0700` run directory.
Its existence does not arm the probe.

## Bootstrap validation and arm bytes

Before constructing the arm, acquire only the selected `bootstrap.json` direct
child. Require the approved run-directory identity, a regular same-UID `0600`
file with one link, strict UTF-8 JSON, the bootstrap schema, and only the
documented bootstrap keys. Compare the static binding fields with the private
record and receipt:

- `runId`
- `configSha256`
- `moduleSha256`
- `copiedAsarSha256`
- `targetTaskId`
- `targetCodeSessionId`
- `getterSetId`
- `monotonicClockId`

Require `monotonicClockId` to equal `linux-clock-monotonic.v1`. Validate the
remaining generated fields before accepting them:

- `appStartNonce` is 64 lowercase hexadecimal characters.
- `pid` is a positive safe integer.
- `processStartTicks` is a nonempty decimal string.
- `queryGeneration` is a positive safe integer.
- `linuxBootId` is the lowercase UUID-form Linux boot domain allowed by the
  grant.

Compare the limits with the reviewed source. Revalidate the selected metadata
and fixture-directory identities. Record the accepted bootstrap file identity,
size, SHA-256, and every binding value in the private run record. A mismatch
stops before arm creation.

The arm template contains every `BINDING_KEYS` field, including the Linux boot
domain:

```json
{"appStartNonce":"<bootstrap appStartNonce>","copiedAsarSha256":"<bootstrap copiedAsarSha256>","configSha256":"<bootstrap configSha256>","getterSetId":"<bootstrap getterSetId>","linuxBootId":"<bootstrap linuxBootId>","maxSamples":3,"minIntervalMs":5000,"moduleSha256":"<bootstrap moduleSha256>","monotonicClockId":"<bootstrap monotonicClockId>","observationWindowMs":30000,"perGetterTimeoutMs":2000,"pid":0,"processStartTicks":"<bootstrap processStartTicks>","queryGeneration":0,"runId":"<bootstrap runId>","schema":"desktop-observer.arm.v1","targetCodeSessionId":"<bootstrap targetCodeSessionId>","targetTaskId":"<bootstrap targetTaskId>"}
```

Replace the displayed zeroes for `pid` and `queryGeneration` with the accepted
positive bootstrap integers. Copy every other binding value from the validated
bootstrap object, then compare it again with the private run record. Do not
derive or substitute a binding value from another source.

Recursively sort the populated arm keys, serialize once with `JSON.stringify`,
encode as strict UTF-8, and append exactly one LF byte. Strictly decode, parse,
validate exact keys and values, remove the LF for canonical reserialization,
and require byte equality before creation. Apply the same duplicate rejection
property as configuration validation. Configuration accepts no final LF; arm
acceptance requires exactly one final LF.

Immediately before creation, require the exact run-directory identity and an
inventory containing only `bootstrap.json`. Create `arm.json` directly and
exclusively with `O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW` and mode `0600`. Apply
the same complete-write, descriptor sync, file identity, ownership, link,
mode, size, digest, strict-decoding, and parent-directory sync checks used for
the configuration. After creation, require the exact inventory
`bootstrap.json`, `arm.json`. Never replace or retry an arm.

## Retained Linux-observation artifact

Use the normative invocation, wrapper, and result variants in
[private probe data contracts](private-data-contracts.md#normative-private-contracts).
The exact retained basename is
`selected-linux-executor-observation.json`; its bound absolute path is outside
`OUTPUT_RUN_ROOT`. Its existing parent is a bound private same-owner `0700`
directory, and the result path must not exist before the authorized invocation.

Construct the invocation only from an actual usable selected sample, its
accepted bootstrap binding, the private record, and the selected Desktop UID.
Recursively sort the populated object's keys, serialize once with
`JSON.stringify`, and encode strict UTF-8 without a BOM, indentation, trailing
spaces, or final newline. Strictly decode, parse, revalidate, reserialize, and
require byte-for-byte equality.

In a one-shot Node ES-module evaluation, import only
`observeSelectedLinuxExecutor` from
`selected-executor-linux-identity.mjs`, parse the validated in-memory bytes,
and invoke exactly:

```js
const result =
  await observeSelectedLinuxExecutor(invocation);
```

Invoke it at most once. Do not invoke it when no usable sample supplies an
actual sequence and complete expected binding. Do not place private values in
source control, a shell command line, or a reusable driver, and do not print or
write the raw return.

Validate the return against one normative result variant. Apply the exact
producer-result, field-outcome, host-gap, nullable-report, and
original-sample requirements in
[Retained producer provenance](private-data-contracts.md#retained-producer-provenance).
Validate the summary against the already selected sample in memory. Do not
reread private output to construct or complete it.

No implemented serializer supplies validation. Require the observed partial
result's sample binding and sequence to equal the wrapper and its selected
report to match the selected task, Code ID, query generation, and PID. Require
its `sampleEvidence.result` and all five `fieldOutcomes` entries to match that
same selected sample exactly. Retain an unknown result as explicit evidence;
do not convert it to a missing file or a success.

Construct the normative wrapper in memory, recursively canonicalize that
object, serialize with `JSON.stringify`, encode strict UTF-8, and append
exactly one LF. Reject extra or missing keys, invalid states, arbitrary error
objects, exception text, stacks, command lines, environments, or any raw object
outside the normative variants.

Require the complete file to be from 1 through 16384 bytes. Create the bound
path once with `O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW` and mode `0600`, applying
the configuration file's complete-write, sync, descriptor identity, ownership,
link-count, byte, parse, and digest checks. Do not invoke the helper again to
replace an unknown result or repair a retention failure.

Record a valid artifact through the normative cleanup-manifest variant. If the
helper is not called or retention fails, record the exact absent reason instead.
Retain any possibly created or unvalidated path as an unresolved resource. No
task ID, Code ID, binding, sequence, file identity, or helper result may be
fabricated to complete the manifest.

## Cleanup-manifest bytes

Manually populate one cleanup-manifest object from identities and outcomes
already established by the run. Validate its exact keys, literal enum tokens,
discriminated variants, and compatibility rules against the sole normative
schema in `private-data-contracts.md`. Descriptive placeholder property names
such as `onlyActuallyVerifiedFields` are instructions, not output keys; omit
unknown optional fields.

Recursively sort the populated object's keys, serialize once with
`JSON.stringify`, encode strict UTF-8, and append exactly one LF. Strictly
decode, parse, revalidate, reserialize, and require byte-for-byte equality.
Create only the bound `CLEANUP_MANIFEST` path, using the configuration file's
exclusive-creation, complete-write, sync, descriptor-identity, ownership,
single-link, mode `0600`, digest, and final-path checks. This manual construction
does not define another schema or authorize a reusable cleanup serializer.
