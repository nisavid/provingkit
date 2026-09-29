# Construct the private fixture inputs

This document fixes the data shapes and creation procedure for one authorized
run. It contains placeholders, not private values or live authority. The
authorization resolution comment binds the final immutable published revision
and the populated private record. No source-controlled example, placeholder,
path, digest, identifier, or bootstrap value authorizes an application change,
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
absolute path from that source and the later selected profile, account,
organization, and task values. The exact app-data root remains a later binding
gap; the source-defined base is `claude-code-sessions`. `getSessionFilePath` is
an internal source method, not an approved callable UI or API; never invoke it.
Do not enumerate the containing directory, scan other task files, or read a
transcript.

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

Project only these source-backed fields from the captured metadata:

```json
{
  "sessionId": "<exact selected task ID>",
  "cliSessionId": "<exact selected Code session ID>",
  "cwd": "<exact selected real directory>",
  "optionalPathStates": {
    "originCwd": "<absent|empty|exact approved absolute real-directory path>",
    "worktreePath": "<absent|empty|exact approved absolute real-directory path>"
  },
  "optionalFieldPresence": {
    "presentNull": ["exact subset of spawnedFrom, dispatchParentId, dispatchParentOrigin, and forkedFromSessionId present with null"],
    "presentFalse": ["lineageDetached only when present with false"],
    "absent": ["every allowed optional field absent from the selected JSON"]
  }
}
```

Require `sessionId` to equal the selected Desktop task ID and `cliSessionId` to
equal the recorded Code ID. Require `cwd` to match the already opened project
identity, not only its spelling. nE uses an empty-string fallback for
`originCwd`, while JSON serialization omits optional properties whose value is
undefined. Record `originCwd` and `worktreePath` as absent, empty, or their
approved nonempty real-directory path. Do not substitute the project path for
an absent or empty value or fabricate a worktree. Preserve whether each
optional lineage field is absent or present. A present spawn,
dispatch-parent, or fork value must be null, and a present `lineageDetached`
value must be false. Any non-null relation or true `lineageDetached` is a stop
condition. Absence remains explicitly absent and must not be converted into
confirmed nonrelation. A missing required field, unexpected path, changed
directory identity, unexpected activity, or metadata change before staging is
also a stop condition.

Persisted nE metadata does not serialize `backend.kind`. Record local creation
from the normal new-local-task UI provenance. Separately, inspected adapter
source checks the live record for `backend.kind === "local"` with `sshConfig`
and `wslConfig` undefined before bootstrap or getter collection and refuses
unsupported routes. This static source fact is not live proof that a particular
run passed the guard.

The selected file establishes only the relations serialized in that file. It
cannot prove a global absence of children or that no other task anywhere shares
a repository, project, or worktree. Record the limits explicitly:

```json
{
  "selectedMetadataRelations": "no-nonnull-relation-observed",
  "globalChildAbsence": "not-established-from-selected-metadata",
  "unrelatedSharingAbsence": "not-established"
}
```

Exclusive construction and current operator coordination are cleanup
preconditions. Neither they nor the nonrecursive project inspection establish
global absence of sharing.

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
and require byte equality before creation.

Immediately before creation, require the exact run-directory identity and an
inventory containing only `bootstrap.json`. Create `arm.json` directly and
exclusively with `O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW` and mode `0600`. Apply
the same complete-write, descriptor sync, file identity, ownership, link,
mode, size, digest, strict-decoding, and parent-directory sync checks used for
the configuration. After creation, require the exact inventory
`bootstrap.json`, `arm.json`. Never replace or retry an arm.

## Retained Linux-observation artifact

The separately invoked selected-executor helper has one retained result file.
Its exact basename is:

```text
selected-linux-executor-observation.json
```

The bound absolute path is outside `OUTPUT_RUN_ROOT`. This preserves the
sampler's exclusive directory inventory. Its existing parent must be a private,
same-owner `0700` directory whose identity is bound before the run. The result
path must not exist before the authorized helper invocation.

The helper invocation is manual but its input is exact. Construct this object
from the accepted bootstrap, private record, and selected sample:

```json
{
  "afterSequence": 0,
  "expectedBinding": "<the exact complete accepted bootstrap binding object>",
  "expectedUid": 0,
  "maximumAgeMs": 30000,
  "runDirectory": "<exact absolute OUTPUT_RUN_ROOT>",
  "sequence": 0
}
```

Replace `sequence` with the selected integer from 1 through 3,
`afterSequence` with exactly `sequence - 1`, and `expectedUid` with the
selected Desktop user's nonnegative integer UID. `expectedBinding` has exactly
the complete binding keys and values already accepted for the arm; it is not
reconstructed from the sample.

Reject extra or missing invocation keys, a noninteger value, a binding
difference, a different run directory, or a placeholder. Recursively sort the
populated object's keys, serialize it once with `JSON.stringify`, and encode it
as strict UTF-8 with no BOM, indentation, trailing spaces, or final newline.
Strictly decode and parse those bytes, repeat the exact validation and
canonical serialization, and require byte-for-byte equality.

In a one-shot Node ES-module evaluation, import only
`observeSelectedLinuxExecutor` from
`selected-executor-linux-identity.mjs`, parse the validated in-memory bytes,
and invoke exactly:

```js
const result =
  await observeSelectedLinuxExecutor(invocation);
```

Invoke it once. Do not place private values in source control, a shell command
line, or a reusable driver, and do not print or write the raw return. Hold the
return in memory, validate it against one documented result variant, construct
the wrapper below, and only then serialize the wrapper to the exclusively
created retained-evidence path.

The artifact binds its source, run, selected sample, and complete expected
binding even when the helper returns an unknown result:

```json
{
  "schema": "provingkit.desktop-probe-linux-observation.v1",
  "source": {
    "publishedRevision": "<immutable reviewed Git revision>",
    "publishedBuildReceiptSha256": "<lowercase SHA-256>",
    "candidateSha256": "<receipt candidate SHA-256>",
    "moduleSha256": "<receipt sidecar SHA-256>"
  },
  "run": {
    "runId": "<exact RUN_ID>",
    "targetTaskId": "<exact selected task ID>",
    "targetCodeSessionId": "<exact selected Code ID>"
  },
  "sample": {
    "runDirectory": "<exact absolute OUTPUT_RUN_ROOT>",
    "sequence": 0,
    "expectedBinding": {
      "runId": "<binding runId>",
      "configSha256": "<binding configSha256>",
      "moduleSha256": "<binding moduleSha256>",
      "copiedAsarSha256": "<binding copiedAsarSha256>",
      "appStartNonce": "<binding appStartNonce>",
      "pid": 0,
      "processStartTicks": "<binding processStartTicks>",
      "targetTaskId": "<binding targetTaskId>",
      "targetCodeSessionId": "<binding targetCodeSessionId>",
      "queryGeneration": 0,
      "getterSetId": "<binding getterSetId>",
      "monotonicClockId": "linux-clock-monotonic.v1",
      "linuxBootId": "<binding linuxBootId>"
    }
  },
  "result": "<one exact normalized helper result described below>"
}
```

Replace the sample sequence with the authorized integer from 1 through 3 and
the integer binding placeholders with the accepted bootstrap values. The
serializer accepts only one of these exact helper-result variants.

An unavailable or changed sample is:

```json
{"state":"unknown","reason":"selected-sample-unavailable-or-changed","qualification":"unqualified","queryToOsAssociation":"unknown"}
```

An unavailable or changed Linux identity is:

```json
{"state":"unknown","reason":"linux-identity-unavailable-or-changed","qualification":"unqualified","queryToOsAssociation":"unknown"}
```

`selected-sample-unavailable-or-changed` also covers failure to acquire the
Linux boot domain before sample selection. Without that domain the helper
cannot validate a selected sample, so this reason does not claim that the
sample file is missing. `linux-identity-unavailable-or-changed` applies only
after a sample has passed boot-domain, binding, and freshness selection and
process-identity acquisition has begun.

A successful partial observation must have exactly this shape:

```json
{
  "state": "observed-partial",
  "qualification": "unqualified",
  "sampleEvidence": {
    "binding": {
      "runId": "<binding runId>",
      "configSha256": "<binding configSha256>",
      "moduleSha256": "<binding moduleSha256>",
      "copiedAsarSha256": "<binding copiedAsarSha256>",
      "appStartNonce": "<binding appStartNonce>",
      "pid": 0,
      "processStartTicks": "<binding processStartTicks>",
      "targetTaskId": "<binding targetTaskId>",
      "targetCodeSessionId": "<binding targetCodeSessionId>",
      "queryGeneration": 0,
      "getterSetId": "<binding getterSetId>",
      "monotonicClockId": "linux-clock-monotonic.v1",
      "linuxBootId": "<binding linuxBootId>"
    },
    "sequence": 0,
    "observedAt": 0,
    "observedAtMonotonicMs": 0,
    "collection": {
      "startedAt": 0,
      "endedAt": 0,
      "startedAtMonotonicMs": 0,
      "endedAtMonotonicMs": 0
    }
  },
  "selectedReport": {
    "taskId": "<selected task ID>",
    "cliPid": 0,
    "cliPidAtMs": 0,
    "cliReportedVersion": "<reported version>",
    "currentCodeSessionId": "<selected Code ID>",
    "queryGeneration": 0,
    "historicProvenance": "unknown",
    "queryToOsAssociation": "unknown",
    "reportBasis": "manager-retained-report; not independent OS association"
  },
  "linuxIdentity": {
    "pid": 0,
    "processStartTicks": "<observed decimal start ticks>",
    "ownerUid": 0,
    "executable": {
      "dev": "<decimal device>",
      "ino": "<decimal inode>",
      "size": "<decimal size>",
      "sha256": "<lowercase SHA-256>"
    }
  },
  "queryToOsAssociation": "unknown"
}
```

No implemented serializer supplies validation. Before serialization, reject
extra or missing keys, invalid states, arbitrary error objects, exception text,
stacks, command lines, environments, and any raw object not listed above.
Require the successful result's sample binding and sequence to equal the
wrapper and its selected report to match the selected task, Code ID, query
generation, and PID. Retain an unknown result as explicit evidence; do not
convert it to a missing file or a success.

Construct the complete populated wrapper object, recursively canonicalize that
object rather than the displayed template text, and serialize it with
`JSON.stringify`, encode it as strict UTF-8, and append exactly one LF. Require
the complete file to be between 1 and 16384 bytes. Create the bound path once
with `O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW` and mode `0600`, using the same
complete-write, sync, identity, ownership, link-count, byte, parse, and digest
checks as the arm. Do not invoke the helper again to replace a failed result.

Record the artifact's exact path, role, type, device, inode, UID, GID, mode,
link count, size, and SHA-256 in the cleanup manifest. Retain it through issue
281. Deletion requires issue 281 to name its exact manifest entry and requires
the same absolute-path, no-symlink, identity, ownership, mode, one-link, size,
and digest checks used for other private files. Unlink only that exact path,
then verify both that it does not exist and that it is not a symlink.
