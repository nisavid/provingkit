# Inserting the observer into a copied Desktop package

The proposed integration adds one CommonJS observation module to a copied
Desktop archive, connects it to the existing session manager, and exports one
fixture-bound file. This plan locates the actual insertion and lifecycle sites.
The prototype implements the observation and file boundaries with fake inputs;
it does not apply this patch or establish that the modified app will load.

## Inspected inputs

Inspection on 2026-09-29 confirmed `claude-desktop-extra` **2.9939.4-1**,
ASAR manifest `@ant/desktop` **2.9939.4**, and archive SHA-256
`4ac2b896dabf3e871f9cf6d9833d02f9f6ad2a839dae6658edc84bb08341238a`.
The archive matches the reviewed design's baseline.

`insertion-points.json` records the hashes, unique source text, and zero-based
byte positions in `.vite/build/index.chunk-B9SZqsi8.js` and
`.vite/build/index.chunk-DuaKZOPP.js`. `verify-source.mjs` compares extracted
bytes as data. It neither imports Desktop nor connects to an app process.

The published `@anthropic-ai/claude-agent-sdk` **0.3.284** declarations corroborate
the response shapes used here. `sdk.d.ts` SHA-256 is
`048ae2e6c796cc2aa3c423afaad59a08972cb48c271ffcc9847d910ff65f61b2`.
`AccountInfo` has optional provider/source fields; `SDKControlPermissionRulesState`
and `SDKPermissionRuleEntry` specify rules, directory grants, `notInEffect`, and
parse errors. The published `Query` declaration does not expose
`listPermissionRules`, although Desktop calls it. A declaration and matching
client version do not establish executor support.

## Patch placement

1. Add `.vite/build/desktopRuntimeObserver.js` to a **copy** of the archive.
   It would contain the reviewed portable observer, a thin Desktop projection,
   generation/event bookkeeping, and the selected-file writer. Convert the
   portable exports to CommonJS for this module; keep its imports limited to
   Node file/crypto facilities. The inspected manager already loads sibling
   CommonJS files using `require`. The current prototype uses ES modules for its
   Node tests and inline browser demo; no converted app module is shipped here.
2. Add a uniquely named `require("./desktopRuntimeObserver.js")` immediately
   after the manager chunk's `"use strict";` directive. Check for a name collision
   before emitting a patch. No broad renderer IPC or external query endpoint is
   needed for the proposed experiment.
3. At `var sF=new aF(t.By);t._B(sF);`, attach a newly armed observer to `sF`.
   The reviewed probe configuration would supply the exact Desktop task ID,
   expected Code session, app-start identity, output file, sample limit/cadence,
   expiry, and approved projection. No default target, discovery scan, or
   automatic rebind is permitted. Unloaded or parked records remain unavailable.
4. Implement a stable view of only `sF.sessions.get(selectedTaskId)`. The same
   underlying record must return the same view identity; a replacement record
   must return a different view. Map `sessionId` to `taskId`, `cliSessionId` to
   `codeSessionId`, and expose getters for `query`, `inputStream`, generation,
   and the selected host projection. Evaluate the same unavailable predicate
   `pk(record)` used by `readContextUsage`; do not use `isRunning` as a proxy for
   query presence. The prototype's normalized `unavailableReason` represents
   this adapter result.
5. Call `observeReceiver(expectedBinding, bounds)` and export only if the arm
   remains valid. Run one collection at a time. Stop at the arm expiry or an
   identity transition. A bounded wait does not cancel the original getter:
   the probe must bound the number of outstanding requests and measure their
   effects before adopting periodic sampling.

`liveQueryOf` merely returns `this.sessions.get(e)?.query??null`.
`withTemporaryQuery` creates a different query and cannot implement this
adapter. Do not call it, a warm/resume path, a setter, or a prompt to fill a gap.

### Required lifecycle changes

The sidecar generation and event provenance below are **new code**, not existing
Desktop guarantees. Keep them keyed by the selected record and query, rather
than by a reusable PID or task title.

| Existing source site in the manager chunk | Proposed change |
| --- | --- |
| `noteQueryInstalled(e,n)` | Increment the record generation on installation; clear retained mode provenance. The inspected cold and warm paths call this method after assigning the query. |
| `teardownQuery(e,r="exited",i)` | Increment generation and invalidate in-flight observation at entry, before close/clearing `query` and `inputStream`. |
| `i.cliSessionId=o` in rewind; `r.cliSessionId=i` in resume; `e.cliSessionId=void 0` in stale-resume clear; `i.cliSessionId=g` in `system/init` | Replace each assignment with an equivalent assignment that also increments generation when the value changes. These are the four direct assignments found in the inspected manager region. Recheck assignment coverage when that region changes. |
| `a&&!x&&b&&this.takeCliPermissionMode(i,b,"cli_init")` | Retain the valid Code mode report, query, time, and generation before calling the existing handler, including a report equal to the manager mode. The init handler already rejects a stale `queryObj`. |
| `if(p&&!m&&f&&f!==o.permissionMode&&o.query===e)` in `system/status` | Capture a mode event when `p&&!m&&f&&o.query===e`, before the narrower changed-value branch. Keep the existing refusal/adoption guards and mutation behavior. |

The observation checks the record, query, input stream, Code ID, app start, and
generation again after asynchronous reads. This catches a replaced query even
if its reply arrives successfully. A generation hook additionally catches a
transition away and back to the original identity. Sidecar loss or exporter
recreation needs a new app-start/exporter identity; sequence reset under an old
identity is not valid continuity. The prototype has no process identity or
transcript lineage producer: the probe plan must bind those independently.

## Concrete projection

The thin app projection is the only place that would know these minified names.
It must leave missing values unknown and export only the approved keys. The
prototype's `record.host` is this normalized projection, not a raw manager
record. All current callers supply synthetic records.

| Prototype input or read | Existing source / proposed mapping | Evidence limit |
| --- | --- | --- |
| `query.accountInfo()` | Captured query; select `apiProvider` and `tokenSource` only | SDK initialization cache; no fresh authenticated route |
| `host.spawnRoute` | `sF.cliOAuthTokenKeeper.spawnAccountOf(record)`; selects `{accountUuid,orgId}` from the input-stream keyed WeakMap | Spawn fact; could differ from a refreshed route |
| `query.getContextUsage({detail:"summary"})` | Same captured query used by `readContextUsage`; select `model` | Timed response; freshness for the next effective model remains unproven |
| `query.listPermissionRules()` | Existing caller in the manager consumes `managedOnly`; prototype also selects declared rule/directory rows | Retains `notInEffect`; counts skipped-settings errors while omitting error text. Does not cover all host grants |
| `host.permissionMode` | `record.permissionMode` | Manager selection; not a fresh executor mode getter |
| `host.modeEvent` | New sidecar populated at the guarded init/status sites above | Last event with generation and time, not a current-mode attestation |
| `host.modeRequestsInFlight` | `record.permissionModeRequestsInFlight?.query === record.query` then its `.count`; otherwise unknown | Existing wrapper is `{query,count}`; a saved number alone loses binding |
| `host.alwaysAllowedReasons` | Selected entries from the manager's `Set` | One host permission store; no exhaustive inventory claim |
| `host.cuAllowedApps`, `host.cuGrantFlags` | Raw `record` values; app rows select `bundleId` and `grantedAt`; flags select `clipboardRead`, `clipboardWrite`, `systemKeyCombos` | Cached host grants |
| `host.effectiveCuAllowedApps`, `host.effectiveCuGrantFlags` | Existing `t.qC(record)` and `t.JC(record)`, exported from the companion chunk's `Kqn`/`Jqn` | Applies source-defined grant expiry for relevant child sessions; other applicable host permission stores remain a gap |
| `host.sessionPermissionUpdates` | Stored update inputs; project only each `type` | A stored request is not proof of application |
| `host.flagScopeSyncPending` | Existing Boolean marker | Covers a held flag-scope push, not every in-flight or failed push; exported pending coverage always remains unknown |
| `host.harnessCwd` | `record.harnessCwd`, also projected by `formatSessionForEvent` | Last manager-observed cwd; not fresh arbitrary executor cwd |

The source supports a concrete counterexample to a complete permission claim:
`addDirectories` records an update and returns while
`pushFlagPermissionScope(...).catch(...)` can fail separately. The marker can
also remain true while MCP servers are unknown. The observer cannot infer
success, absence of pending work, or a failure history from a false marker.
Adding complete pending/failed bookkeeping would be another reviewed source
change. This prototype exposes that gap instead of inventing such bookkeeping.

Computer-use app grants have timestamped rows, not strings. Their effective
getters can remove expired grants. The companion source also contains Chrome
permission mode/domain handling; this prototype does not project it or claim
that the selected host stores exhaust permission configuration. The probe must
inventory applicable stores before any completeness conclusion.

## Export, packaging, and restoration

The proposed transport is a single selected file. The synthetic writer creates
an exclusive temporary file beside it with mode `0600`, writes complete JSON,
then renames it over the selected file. Its test reads the replacement through
the same `inspectEnvelope` function as the demo. This demonstrates ordinary
replacement, not crash durability, hostile-path resistance, producer
authentication, or protection against a different writer using that filename.
Those properties and approved fixture-data retention belong in the probe's
reviewed access and operational plan.

The packaging mechanism is an offline ASAR rebuild: retain the pristine archive
and package identity, extract to a private staging tree, add the module, apply
exact reviewed replacements in the manager chunk, rebuild the archive while
preserving unpacked assets, and compare its member manifest with the baseline.
Only the added module and patched manager should differ in this proposal.
The actual packer version/command, archive integrity metadata, distribution
checks, and package-update behavior have not been checked; the probe-plan task
must establish them and produce the exact patch and rebuilt candidate before
requesting installation. This source plan is not an executable installer.

Loading the changed main-process chunk requires restarting Desktop. A restart
can interrupt tasks and does not establish that an existing receiver query will
survive. The first probe therefore needs a separately authorized disposable
fixture and a reviewed installation sequence. Native-module paths, unpacked
assets, and the package launcher must be retained or validated in a staging
launch. No such launch has occurred here.

Restoration means putting back the verified pristine archive/package, removing
the experimental export and arm configuration under their agreed retention
rules, restarting, and verifying the restored artifact and application behavior.
Restoring bytes alone does not prove that task state was restored. The probe
plan must name that check and any expected disposable-task loss. Package updates
may overwrite the patch; never reapply a stale offset patch automatically.

## Compatibility and ownership

Assess the consumed behavior separately: query selection/lifecycle, each
getter, host grant inventory/projection, mode-event capture, export, and reader.
A changed build is unassessed. Start with release notes, artifact comparisons,
and synthetic contract checks, then inspect changed producers and repeat only
the affected live checks where cheaper evidence leaves uncertainty. Carry
prior evidence forward when justified. Demonstrated failure disables that
function; missing evidence in a sample remains unknown even for a compatible
dependency. Initial live qualification remains outstanding in every case.

Propose maintaining the app adapter and patch in the repository that owns the
Desktop package/build integration. Its location and permission to edit it need
that repository's policy and task scope. Keep the stable external reader and
focused notification procedure in Rolecasting after adoption. This directory
is retained experimental evidence, not an installed skill or approved adapter.

The next consumer is [Prepare and review the disposable observer probe](https://github.com/nisavid/provingkit/issues/278).
It must consume this published candidate, settle the packaging and arm details,
and name the exact remaining observations: getter support/effects, current
account/model/mode/cwd semantics, full permission coverage, process and native
address binding. It must carry unresolved requirements into the probe's return
decision. A no-send probe can establish none of the external delivery or
correlated acknowledgment contract.
