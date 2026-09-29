# Private probe data contracts

This document is the normative home for the selected-fixture projection,
selected-executor invocation and result variants, and cleanup-manifest schema
used by one disposable Desktop observer probe.
[Application staging and restoration](application-operation.md) defines the
phase sequence that consumes these contracts.
[Private input construction](private-input-construction.md) defines how
conforming private bytes are constructed, validated, canonicalized, and
exclusively created; it does not define alternative fields, states, reasons, or
enum values.

## Normative private contracts

The selected metadata projection has exactly this shape:

```json
{
  "sessionId": "exact selected task ID",
  "cliSessionId": "exact selected Code session ID",
  "cwd": "exact selected real directory",
  "optionalPathStates": {
    "originCwd": "absent, empty, or exact approved absolute real-directory path",
    "worktreePath": "absent, empty, or exact approved absolute real-directory path"
  },
  "optionalFieldPresence": {
    "presentNull": ["actual subset of spawnedFrom, dispatchParentId, dispatchParentOrigin, and forkedFromSessionId present with null"],
    "presentFalse": ["lineageDetached only when actually present with false"],
    "absent": ["every allowed optional field actually absent from the selected JSON"]
  }
}
```

Its relation evidence is exactly:

```json
{
  "selectedMetadataRelations": "no-nonnull-relation-observed",
  "globalChildAbsence": "not-established-from-selected-metadata",
  "unrelatedSharingAbsence": "not-established"
}
```

The selected-executor invocation has exactly these keys:

```json
{
  "afterSequence": 0,
  "expectedBinding": "exact complete accepted bootstrap binding object",
  "expectedUid": 0,
  "maximumAgeMs": 30000,
  "runDirectory": "exact absolute OUTPUT_RUN_ROOT",
  "sequence": 0
}
```

`sequence` is an actually selected integer from 1 through 3,
`afterSequence` is exactly `sequence - 1`, and `expectedUid` is the selected
Desktop user's nonnegative integer UID. Construct this object only after a
usable selected sample exists. Do not invent a sequence, binding, task ID, Code
ID, or sample to make the helper callable.

The retained wrapper has exactly these top-level fields:

```json
{
  "schema": "provingkit.desktop-probe-linux-observation.v1",
  "source": {
    "publishedRevision": "immutable reviewed Git revision",
    "publishedBuildReceiptSha256": "lowercase SHA-256",
    "candidateSha256": "receipt candidate SHA-256",
    "moduleSha256": "receipt sidecar SHA-256"
  },
  "run": {
    "runId": "exact RUN_ID",
    "targetTaskId": "exact selected task ID",
    "targetCodeSessionId": "exact selected Code ID"
  },
  "sample": {
    "runDirectory": "exact absolute OUTPUT_RUN_ROOT",
    "sequence": 0,
    "expectedBinding": "exact complete accepted bootstrap binding object"
  },
  "result": "one exact result variant below"
}
```

The two unknown result variants are exactly:

```json
{"state":"unknown","reason":"selected-sample-unavailable-or-changed","qualification":"unqualified","queryToOsAssociation":"unknown"}
```

```json
{"state":"unknown","reason":"linux-identity-unavailable-or-changed","qualification":"unqualified","queryToOsAssociation":"unknown"}
```

`selected-sample-unavailable-or-changed` covers any failure that prevents the
selected sample from remaining valid. This includes failure to acquire the
Linux boot domain before selection, clock expiry or regression during later
process-identity checks, and failure or change during final sample
reacquisition. Without the boot domain the helper cannot validate a selected
sample, so this reason does not claim that the sample file is missing.
`linux-identity-unavailable-or-changed` is reserved for process-directory,
owner, start-time, or executable identity failures after a sample has passed
boot-domain, binding, and freshness selection. Beginning process-identity
acquisition does not reclassify a later sample invalidation as a Linux-identity
failure.

The observed result has exactly this shape:

```json
{
  "state": "observed-partial",
  "qualification": "unqualified",
  "sampleEvidence": {
    "binding": "exact complete revalidated sample binding",
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
    "taskId": "exact selected task ID",
    "cliPid": 0,
    "cliPidAtMs": null,
    "cliReportedVersion": null,
    "currentCodeSessionId": "exact selected Code ID",
    "queryGeneration": 0,
    "historicProvenance": "unknown",
    "queryToOsAssociation": "unknown",
    "reportBasis": "manager-retained-report; not independent OS association"
  },
  "linuxIdentity": {
    "pid": 0,
    "processStartTicks": "observed decimal start ticks",
    "ownerUid": 0,
    "executable": {
      "dev": "decimal device",
      "ino": "decimal inode",
      "size": "decimal size",
      "sha256": "lowercase SHA-256"
    }
  },
  "queryToOsAssociation": "unknown"
}
```

In the producer projection, a missing or null selected fact is preserved as
JSON `null` and recorded as an `unavailable` gap. This includes
`selectedExecutorReport.cliPidAtMs` and
`selectedExecutorReport.cliReportedVersion`. The producer's `complete` or
`partial` result follows the actual projected-field statuses and gap lists; a
null fallback does not erase its gap or establish runtime knowledge.

The helper may still return a valid `observed-partial` result carrying these
nulls. In that result, `cliPidAtMs` is independently either JSON `null` or the
actual nonnegative safe integer reported by the producer, and
`cliReportedVersion` is independently either JSON `null` or the actual
nonempty bounded text reported by the producer. Preserve the producer value
exactly. Do not invent or borrow a value, suppress an existing gap, or reject
or reclassify an otherwise valid partial helper result merely because either
field is null. The producer emits, and the reader requires, every
`UNKNOWN_CLAIMS` value and the unqualified outcome.

## Private cleanup manifest and retention

Raw output remains private through
[Decide what the observer probe establishes](https://github.com/nisavid/provingkit/issues/281).
At the terminal stop, exclusively create and validate `CLEANUP_MANIFEST` as a
private regular, single-link `0600` file unless its creation or validation
fails. It is an inventory and recovery record, not an executable cleanup
script.

Use schema `provingkit.desktop-probe-cleanup.v2`. The top-level shape shown
below has no `retention` field. Retention is recorded only in the nested
`restoration.recoveryRecord.retention` and `fixture.retention` fields:

```json
{
  "schema": "provingkit.desktop-probe-cleanup.v2",
  "createdAt": "RFC-3339 timestamp",
  "runId": "exact RUN_ID",
  "status": "one exact status variant below",
  "restoration": "one exact restoration variant below",
  "packageCleanup": "one exact package-cleanup variant below",
  "source": {
    "publishedRevision": "exact reviewed Git revision"
  },
  "artifacts": {
    "candidateSha256": "receipt value",
    "managerSha256": "receipt value",
    "sidecarSha256": "receipt value",
    "generatedBuildReceiptSha256": "SHA-256 of build-receipt.json",
    "publishedBuildReceiptSha256": "same SHA-256",
    "archiveVerificationSha256": "exact REVIEWED_ARCHIVE_VERIFICATION_SHA256"
  },
  "fixture": "one exact fixture variant below",
  "configuration": "one exact configuration variant below",
  "output": "one exact output variant below",
  "retainedEvidence": "one exact retained-evidence variant below",
  "unresolvedResources": []
}
```

`status` is one of these three discriminated variants.

A completed run is exactly:

```json
{
  "state": "completed",
  "reason": "completed",
  "phase": "complete",
  "firstFailure": {
    "state": "absent"
  },
  "laterFailures": []
}
```

A stopped run has `state` `stopped`, `reason` `phase-failed`, and `phase` equal
to the earliest failed phase. Its `firstFailure` has `state` `present`,
`reason` `phase-failed`, and the same phase. Each `laterFailures` entry has
`reason` `phase-failed` and its actual later phase, in occurrence order.

A run with incomplete or unverified restoration has `state`
`recovery-required`, `reason` `restoration-incomplete`, and `phase`
`restoration`. If restoration was the first failure, `firstFailure` has
`state` `present`, `reason` `restoration-incomplete`, and phase `restoration`.
If another phase failed first, `firstFailure` retains `reason` `phase-failed`
and that earlier phase, while `laterFailures` contains an entry with reason
`restoration-incomplete` and phase `restoration`. Any failure after that entry
uses reason `phase-failed` and its actual phase.

The literal failure-phase tokens are `preflight`, `staging`, `exchange`,
`setup`, `fixture-creation`, `fixture-query`, `configuration-creation`,
`configuration-validation`, `output-root-creation`,
`output-root-validation`, `candidate-launch`, `bootstrap`, `arm`, `sample`,
`helper-invocation`, `helper-result-validation`,
`retained-evidence-creation`, `retained-evidence-validation`, `restoration`,
`package-cleanup`, `cleanup-manifest-creation`, and
`cleanup-manifest-validation`. `complete` is valid only for a completed run.
`restoration-incomplete` is valid only for phase `restoration`; every other
failure uses `phase-failed`.

`firstFailure` preserves the earliest terminal failure. `laterFailures` lists
only later failures and remains empty when none occurred. Restoration has
outcome priority, but it does not replace an earlier `firstFailure`. An absent
helper, retention failure, package-cleanup failure, or manifest failure also
does not replace an earlier failure.

Failure to acquire or validate the host boot UUID during setup is phase
`setup`. A missing, malformed, or mismatched boot UUID in a bootstrap, arm, or
sample record is assigned to the corresponding `bootstrap`, `arm`, or
`sample` phase. This classification does not change the established metadata
or Linux observation schemas.

When no candidate exchange occurred and unchanged archive bytes are
established, perform no archive exchange. If no application or archive
recovery obligation remains, restoration is
`{state:not-required,recoveryRecord:{state:absent}}`. If Desktop availability
requires recovery, the single restored launch may proceed only under the later
restoration-cycle grant and after the required checks; after complete
restoration checks pass, state is `verified`. If required recovery is not
covered, available, completed, or verified, state is `incomplete` and status
is `recovery-required`; deletion remains prohibited. A changed or ambiguous
archive, or an earlier launch with an ambiguous result, requires a decision
and prohibits retry.

The `not-required` variant is:

```json
{
  "state": "not-required",
  "recoveryRecord": {
    "state": "absent"
  }
}
```

After the complete restoration checks pass, restoration is:

```json
{
  "state": "verified",
  "verifiedAt": "RFC-3339 timestamp",
  "recoveryRecord": {
    "state": "absent"
  }
}
```

If restoration cannot be completed or verified, restoration is:

```json
{
  "state": "incomplete",
  "recoveryRecord": {
    "state": "required",
    "lastVerifiedStep": "literal last verified restoration step",
    "knownPackageArtifacts": [],
    "retention": "all-package-and-private-artifacts",
    "nextDecision": "operational-restoration"
  }
}
```

Each `knownPackageArtifacts` entry has role exactly `target`, `stage`, or
`backup`; an exact known path; existence state exactly `known` or `uncertain`;
and an optional `knownIdentity` object containing only fields already verified.
Omit `knownIdentity` when no identity field was established. List only paths
that are known to exist or whose continued existence is uncertain. Do not
infer a digest, identity, or absence.

`packageCleanup` contains exactly three resource entries keyed `stage`,
`backup`, and `backupRunRoot`. Their matching literal roles are `stage`,
`backup`, and `backup-run-root`. Each entry uses exactly one resource-state
schema:

- `absent`: `role` and `state`; valid only when absence was established without
  deletion.
- `known`: `role`, `state`, exact `path`, and optional nonempty
  `knownIdentity`; valid only when existence was established.
- `uncertain`: `role`, `state`, exact `path`, optional nonempty
  `knownIdentity`, and disposition `retain-pending-operational-decision`.
- `removed`: `role`, `state`, exact `path`, and `removedAt`; valid only after
  the authorized deletion and both absence checks succeeded.

Its top-level state is exactly one of:

- `not-required`: all three resources are `absent`, and no removal was
  attempted.
- `retained`: no resource is `removed`, at least one is `known` or `uncertain`,
  and package deletion was not attempted.
- `failed`: removal was attempted, no resource is `removed`, and at least one
  resource remains `known` or `uncertain`.
- `partial`: at least one resource is `removed`, and at least one remains
  `known` or `uncertain`.
- `completed`: all three resources are `removed`.

A `removed` resource and the states `failed`, `partial`, or `completed` are
valid only with restoration `verified`. `backup-run-root` may be `removed` only
after `backup` is `removed`; the approved sequence also requires `stage`
removal first. Restoration `incomplete` requires package-cleanup state
`retained` or `not-required` and prohibits every deletion. A package resource
in state `known` or `uncertain` is retained from this authoritative package
inventory and is not duplicated in `unresolvedResources`.

An established fixture uses this variant:

```json
{
  "state": "established",
  "profile": "exact selected profile identity",
  "accountId": "exact selected account identity",
  "organizationId": "exact selected organization identity",
  "taskId": "exact disposable task identity",
  "codeId": "exact Code session identity",
  "metadataPath": "exact absolute selected metadata path",
  "creationProvenance": {
    "route": "normal-new-local-task-ui",
    "createdAt": "RFC-3339 timestamp",
    "preCreationInspection": "nonrecursive-empty",
    "unexpectedActivity": "none-observed"
  },
  "selectedMetadata": {
    "sessionId": "exact taskId",
    "cliSessionId": "exact codeId",
    "cwd": "exact real directory path",
    "optionalPathStates": {
      "originCwd": "absent, empty, or exact approved real-directory path",
      "worktreePath": "absent, empty, or exact approved real-directory path"
    },
    "optionalFieldPresence": {
      "presentNull": [
        "exact subset of spawnedFrom, dispatchParentId, dispatchParentOrigin, and forkedFromSessionId present with null"
      ],
      "presentFalse": [
        "lineageDetached only when present with false"
      ],
      "absent": [
        "every allowed optional field absent from the selected JSON"
      ]
    }
  },
  "relationEvidence": {
    "selectedMetadataRelations": "no-nonnull-relation-observed",
    "globalChildAbsence": "not-established-from-selected-metadata",
    "unrelatedSharingAbsence": "not-established",
    "operatorCoordinationAt": "RFC-3339 timestamp"
  },
  "project": {
    "path": "exact absolute dedicated project path",
    "device": "decimal device",
    "inode": "decimal inode",
    "uid": "decimal owner",
    "gid": "decimal group",
    "mode": "octal mode",
    "dedicated": true,
    "emptyAtFixtureCreation": true
  },
  "worktree": {
    "state": "absent"
  }
}
```

If Desktop created a verified worktree, replace only the `worktree` object
with:

```json
{
  "state": "present",
  "path": "exact absolute app-created worktree path",
  "device": "decimal device",
  "inode": "decimal inode",
  "uid": "decimal owner",
  "gid": "decimal group",
  "mode": "octal mode",
  "creation": "app-created",
  "dedication": "dedicated",
  "validatedEntries": ["actual approved nonrecursive entries"]
}
```

For each optional metadata path, write exactly `absent`, `empty`, or its
approved nonempty real-directory path. Do not add a path or worktree identity
for an absent or empty field. The lineage presence arrays contain only fields
actually present with the stated value; absent fields belong only in
`absent`.

Before the complete fixture identity is established, `fixture.state` is
exactly `not-created`, `partial`, or `uncertain`. All three variants contain
`createdResources`, `uncertainResources`, `selectedMetadata`, and `retention`.

The valid combinations are:

- `not-created`: both resource arrays are empty; `selectedMetadata` is
  `{"state":"absent","reason":"not-acquired"}`; retention is `none`.
- `partial`: `createdResources` is nonempty, `uncertainResources` is empty,
  selected metadata is one of the incomplete variants below, and retention is
  `through-issue-281`.
- `uncertain`: `uncertainResources` is nonempty, `createdResources` contains
  any independently established resources, selected metadata is one of the
  incomplete variants below, and retention is
  `pending-operational-decision`.

The literal incomplete selected-metadata variants are:

```json
{"state":"absent","reason":"not-acquired"}
```

```json
{"state":"absent","reason":"query-failed"}
```

```json
{
  "state": "unvalidated",
  "knownIdentity": {
    "onlyActuallyEstablishedFields": "actual values"
  },
  "reason": "query-unvalidated"
}
```

Omit `knownIdentity` fields that were not established. Do not emit the
descriptive property shown above as a literal property name.

Each `createdResources` entry has exactly one literal role:
`project-directory`, `desktop-task`, or `app-created-worktree`.
A `project-directory` or `app-created-worktree` entry contains its exact path
and only established directory-identity fields. A `desktop-task` entry contains
its exact established task identifier and only other identifiers actually
established.

Each `uncertainResources` entry uses one of the same three role tokens, a
`knownIdentity` object containing only known path, identifier, or identity
fields, and disposition `retain-pending-operational-decision`. Do not fabricate
a task ID, Code ID, metadata path, selected projection, project path, or
worktree path. An uncertain resource is never moved to `createdResources`,
declared absent, or deleted merely to complete the manifest.

Configuration is absent only when absence was established:

```json
{
  "state": "absent"
}
```

A configuration that passed the accepted identity checks is:

```json
{
  "state": "present",
  "path": "exact absolute PROBE_CONFIG",
  "type": "regular-file",
  "device": "decimal device",
  "inode": "decimal inode",
  "uid": "decimal owner",
  "gid": "decimal group",
  "mode": "0600",
  "links": 1,
  "size": "decimal bytes",
  "sha256": "lowercase SHA-256"
}
```

If configuration creation may have left a path that did not pass validation,
use:

```json
{
  "state": "unvalidated",
  "path": "exact known path",
  "knownIdentity": {
    "onlyActuallyVerifiedFields": "actual values"
  },
  "disposition": "retain-pending-operational-decision"
}
```

Add that path to `unresolvedResources`. Do not declare the configuration
absent merely because creation or validation failed.

Output is:

```json
{
  "root": {
    "state": "absent"
  },
  "artifactStates": {
    "bootstrap": "absent",
    "arm": "absent",
    "samples": "absent"
  },
  "emittedFiles": []
}
```

Use an absent root only when absence was established. A root that passed the
accepted identity checks is:

```json
{
  "state": "present",
  "path": "exact absolute OUTPUT_RUN_ROOT",
  "type": "directory",
  "device": "decimal device",
  "inode": "decimal inode",
  "uid": "decimal owner",
  "gid": "decimal group",
  "mode": "0700"
}
```

If output-root creation may have left a path that did not pass validation,
use:

```json
{
  "state": "unvalidated",
  "path": "exact known path",
  "knownIdentity": {
    "onlyActuallyVerifiedFields": "actual values"
  },
  "disposition": "retain-pending-operational-decision"
}
```

Add that path to `unresolvedResources`. Each artifact state is exactly
`absent`, `present-validated`, or `present-unvalidated`. Use `absent` only when
absence was established. `emittedFiles` contains only files that actually
exist and passed the identity checks. Its literal role tokens are `bootstrap`, `arm`, `sample-1`, `sample-2`,
and `sample-3`:

```json
{
  "role": "sample-1",
  "path": "exact absolute direct child of OUTPUT_RUN_ROOT",
  "type": "regular-file",
  "device": "decimal device",
  "inode": "decimal inode",
  "uid": "decimal owner",
  "gid": "decimal group",
  "mode": "0600",
  "links": 1,
  "size": "decimal bytes",
  "sha256": "lowercase SHA-256"
}
```

A created or possibly created output path that did not pass validation is not
fabricated into `emittedFiles`. Record only its known identifiers in
`unresolvedResources` and retain it.

Retained evidence is absent when no valid retained file was established. Its
`reason` is exactly one of `not-reached`, `no-usable-selected-sample`,
`helper-not-called`, `helper-invocation-failed`,
`helper-result-unvalidated`, `retention-creation-failed`, or
`retention-validation-failed`:

```json
{
  "state": "absent",
  "reason": "not-reached"
}
```

A retained file that passed the accepted identity checks uses:

```json
{
  "state": "present",
  "files": [
    {
      "role": "selected-linux-executor-observation",
      "purpose": "strictly serialized selected-executor helper return",
      "path": "exact absolute LINUX_OBSERVATION_FILE outside OUTPUT_RUN_ROOT",
      "type": "regular-file",
      "device": "decimal device",
      "inode": "decimal inode",
      "uid": "decimal owner",
      "gid": "decimal group",
      "mode": "0600",
      "links": 1,
      "size": "decimal bytes from 1 through 16384",
      "sha256": "lowercase SHA-256"
    }
  ]
}
```

Use `no-usable-selected-sample` when no sample can truthfully supply the
binding and sequence. Use `helper-not-called` only when a usable sample existed
but the authorized helper invocation did not occur. Use
`helper-invocation-failed` when the helper invocation threw or otherwise
failed to return. Use `helper-result-unvalidated` when it returned a value
that could not be validated under the unchanged Linux observation schema.
Use `retention-creation-failed` or `retention-validation-failed` when the
corresponding file operation did not establish a valid retained file. Do not
call the helper again for any of these states. A possibly created or invalid
retained path belongs in `unresolvedResources` and remains retained.

Every file array contains only actual files. Empty arrays remain empty; they
never contain placeholders, patterns, ranges, or expected future files.

`unresolvedResources` records every unresolved non-package resource. Its
literal role tokens are `project-directory`, `desktop-task`,
`app-created-worktree`, `configuration`, `output-root`, `bootstrap`, `arm`,
`sample-1`, `sample-2`, `sample-3`,
`selected-linux-executor-observation`, and `cleanup-manifest`. Each entry has
the selected role, a `knownIdentity` object containing only actual known paths,
identifiers, or identity fields, and disposition
`retain-pending-operational-decision`. Omit unknown fields; do not add an
unknown path, identifier, digest, or identity merely to make an entry look
complete. Package resources use only the normative `packageCleanup` inventory
and are not duplicated here.

Do not read private configuration, output, helper results, or retained evidence
solely to populate missing manifest fields. Use only identities already
established by the authorized run.

If cleanup-manifest creation or validation fails, retain every resource that
still exists and return the failure without retrying, repairing the path, or
creating a replacement elsewhere. Package resources already verified as
removed during the earlier authorized package-cleanup phase remain recorded as
`removed`; a manifest failure does not undo or repeat that phase. A possibly
created or invalid manifest path is retained using only its known path or
identity. The terminal report uses the same status schema even though no valid
manifest exists.

No failed setup, query, creation, launch, sampling, helper, retention,
restoration, package-cleanup, or manifest operation is retried to fill the
manifest. Manifest recording does not authorize another UI action, helper
invocation, candidate launch, private-data read, external request, deletion, or
other live effect.

Private evidence, task, project, worktree, configuration, output, retained
evidence, and cleanup-manifest deletion requires an exclusively created,
validated manifest and the later issue 281 decision. This gate does not apply
to the narrowly authorized package-cleanup phase after verified restoration.
Issue 281 may approve private deletion only after restoration is `verified` or
`not-required`, no applicable private resource remains unresolved, and it
names the reviewed cleanup manifest and SHA-256, the exact task identity when
known, and the exact roles or paths to remove. Anything unnamed or uncertain
remains retained.

The later authorized cleanup input is a manually populated private packet for
this run. This section does not authorize implementing or running a general
cleanup tool.

Source inspection found that `LocalSessions.delete(sessionId)` delegates to
`manager.deleteSession` with `userInitiated: true`, and manager teardown may
cascade to linked tasks, associated worktrees, and transcripts. Do not call
either internal method, invoke a private API, or add cleanup instrumentation.
Before deletion, reread only the exact selected metadata path and revalidate its
task and Code IDs, `cwd`, optional-path states, and spawn, dispatch-parent,
fork, and `lineageDetached` values when present. Preserve absent and empty
fields exactly, and stop on a non-null relation or true `lineageDetached`.
Reconfirm exclusive fixture construction, current operator coordination,
dedicated directory identities, and absence of unexpected activity. Do not
claim global child or sharing absence from that one file, scan all tasks, or
invoke an internal family or cleanup API.

Use only Desktop's normal task-deletion UI. Proceed only when the live UI shows
the selected disposable fixture and its confirmation establishes the managed
removal scope, including any linked-task and worktree effect, as matching the
recorded fixture. UI labels and controls are not assumed by this runbook. If
the control is absent, the selected identity cannot be confirmed, the managed
scope cannot be established, or the confirmation indicates broader scope,
retain the fixture and return for an operational decision. The approved cleanup
accepts managed removal of that task's own transcript and dedicated worktree.
If any broader side effect is shown or observed, stop without continuing file
cleanup and report it.

After the exact UI deletion, confirm through the selected task route that the
task is absent and compare the recorded fixture directory identities and
explicitly coordinated unrelated work with their recorded expectations. This
is not a global absence-of-change claim. Do not manually delete Desktop private
profile stores, task metadata, transcripts, other worktrees, or any
application-managed residual path.

Remove an approved user-owned configuration or output file only with this
manual checklist:

1. Copy its exact path and expected type, device, inode, UID, GID, mode, link
   count, size, and SHA-256 from the reviewed manifest into the executor's
   checklist as literal data. Do not evaluate the manifest as shell.
2. Require an absolute path without a newline, `.` or `..` component, and
   verify every existing component is not a symlink.
3. For an output file, require the exact output-root prefix and a nonempty
   remainder containing no slash, so the file is a direct child. For the
   configuration, require exact equality with the manifest's configuration
   path and require that it is outside the output root.
4. Compare `lstat`, owner, group, mode, link count, size, and SHA-256 with the
   manifest. Require a regular file and one link. A mismatch retains the file.
5. Run `unlink -- "$EXACT_APPROVED_PATH"` for that one path. Verify both
   `test ! -e "$EXACT_APPROVED_PATH"` and
   `test ! -L "$EXACT_APPROVED_PATH"` afterward.

Process approved output files one at a time in manifest order. Do not use a
glob, brace expansion, recursive removal, or inferred numbered range. After the
approved files are removed, compare the output root's device, inode, owner,
group, and mode with the manifest. Check exact emptiness with a bounded
one-level listing whose failure is handled. Use `rmdir -- "$OUTPUT_RUN_ROOT"`
only when it is empty, then verify the exact path is absent. An unexpected or
unapproved entry remains in place and returns for a decision.

Process an approved retained-evidence file as its own manifest entry. Require
exact equality with `LINUX_OBSERVATION_FILE`, require that it is outside the
output root and has the fixed basename
`selected-linux-executor-observation.json`, and repeat its type, identity,
ownership, mode, link-count, size, SHA-256, absolute-path, and no-symlink
checks. Run `unlink -- "$LINUX_OBSERVATION_FILE"` only when issue 281 names
that exact entry. Verify both `test ! -e "$LINUX_OBSERVATION_FILE"` and
`test ! -L "$LINUX_OBSERVATION_FILE"` afterward. A mismatch retains the file.

If an established fixture's exact manifest-listed project remains after the UI
operation, compare its device, inode, owner, group, and mode with the manifest,
confirm it is still dedicated to the deleted fixture, and verify it is empty.
Apply the same checks to a worktree only when the established fixture records
its state as `present`. A partial or uncertain fixture supplies no cleanup
authority for a task, project, or worktree; retain every such resource pending
an operational decision. Only then may
`rmdir -- "$EXACT_DIRECTORY"` remove that one directory. Do not unlink
directory contents to make it empty. A missing recorded directory is an
accepted managed effect; a nonempty, changed, shared, or differently owned
directory is retained.

The cleanup manifest itself remains private decision evidence unless issue 281
separately binds its exact path, external hash and file identity, and approves
unlinking it last. No glob, broad recursive removal, permanent instrumentation,
maintained observer deployment, periodic commitment, or expanded qualification
is authorized.
