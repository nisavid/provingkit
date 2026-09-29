# Desktop observation paths: file acquisition is concrete, runtime evidence remains open

A standalone reader can acquire explicitly selected Claude Desktop metadata and
candidate Code transcript files. The inspected source establishes how Desktop
writes those files and links its task to a Code session. It does not establish
the external sender's receiver record, its native address binding, or an
external read-only observation of every effective runtime setting. The next
decision is how to obtain those missing observations while preserving the
accepted qualification claim.

This report answers
[Establish automated observation paths for the Desktop reader](https://github.com/nisavid/provingkit/issues/272).
The route remains ChatGPT in Codex mode to an exact, consent-bound, existing
Claude Desktop-hosted Code peer on the same Linux machine. The
[reader-adoption decision](https://github.com/nisavid/provingkit/issues/271#issuecomment-5884146675)
permits source work with graduated compatibility checks. Initial live
qualification, disposable-fixture data access, installation, task creation,
and exact-peer sends retain their separate gates.

## Evidence and provenance

The investigation inspected installed first-party application source and
current Anthropic API documentation on 2026-09-29. It consumed the reproducible
inspection procedure in the
[retained receiver-evidence report](https://github.com/nisavid/provingkit/blob/9ae77ba3f3e62bda941d328b58bce1f3e8aea7ef/docs/superpowers/research/2026-09-28-claude-desktop-receiver-evidence.md).
No private receiver metadata, transcript, credential, or process environment
was read. No Desktop module was imported or executed, and no receiver was
created, resumed, installed, prompted, or sent a message.

**Source-backed** means a producer or consumer was traced in the identified
package bytes. **Proposed** means an acquisition or interpretation design
inferred from that source. **Unresolved** names a missing observation or
contract. None means the live route was qualified.

The inspected package is `claude-desktop-extra` **2.9939.4-1**, with ASAR
manifest `@ant/desktop` **2.9939.4**. The ASAR SHA-256 is
`4ac2b896dabf3e871f9cf6d9833d02f9f6ad2a839dae6658edc84bb08341238a`.
Package inventory identifies source bytes; it does not identify a running
receiver or its Code executor.

Paths in this table are relative to that ASAR. Minified names are locators for
these bytes, not stable interfaces.

| Source | SHA-256 | Relevant locators |
| --- | --- | --- |
| `.vite/build/index.chunk-B9SZqsi8.js` | `bd2144a3653bb843f4b75fe652124a4e478f273b5f6c2e10a2139fa3a9a3152f` | `getStorageDir`, `getSessionFilePath`, `writeSessionToDisk`, `getTranscriptWithoutQueryCrashes`, `sendPeerMessage`, `trackPeerInbound`, `notePeerTurnStarted`, `notePeerReply`, `buildStartSdkOptions`, `spawnAccountOf`, `readRunningModel`, `applyHarnessWorktreeMove` |
| `.vite/build/index.chunk-CKt-cwRV.js` | `dad88ac66fe13f72d0225c49d48e124d238ff643ff96426c4a2020482621e62d` | session serializer `nE`, host tool `Gd` / `get_session`, host `send_message` |
| `.vite/build/index.chunk-CgTwqg58.js` | `20759b644bc90e8797767117697ca26026f8cba7b3d4f30aedf64a461920408d` | `resolveProjectDirForSession`, `probeSessionFile`, `resolveSource`, `loadRawChainEntries`, `fullFromDisk`, `skipMtimeTouch` |
| `.vite/build/index.chunk-vRLpacfH.js` | `ac8acccdebfdd2a165bb5f4d9710b80540b46ce01207f85eae42696a0c7819e1` | bundled Code `crossSessionInbound` schema and SDK session-reader exports |
| `.vite/build/heavyWorkWorker.js` | `77b79b7d48e2587595a33fe85c2bd426a3854b54ecbc8eb23a02a2278b24188e` | `loadRawChain`, `loadFullInner`, `skipMtimeTouch` |

## Acquisition paths

### Selected metadata and transcript bytes

The manager builds a metadata path under its Electron application-data root,
base directory, account ID, and organization ID, ending with the Desktop
session ID and `.json`. `writeSessionToDisk` uses `nE` and normally replaces
the file atomically, with a direct-write fallback for specified filesystem
errors. The persistence queue debounces writes and uses a separate delay for
active sessions. An external process with the required filesystem access can
read an explicitly selected file; its existence does not establish freshness.

`nE` retains `sessionId`, `cliSessionId`, `unarchivedCliSessionId`,
`priorCliSessionIds`, `rewindEdges`, and `transcriptCuts`. The manager's
`system/init` handler validates the Code-reported session ID, saves it as
`cliSessionId`, and records relevant lineage changes. This is a concrete
Desktop-task-to-Code-session relationship. No traced field binds an external
native peer address to that task or proves that its executor is still running.

The transcript resolver searches the Claude configuration directory's
`projects` tree for a JSONL file named after the Code session ID. It probes
conversation rows and may select the largest file when multiple conversation
candidates match. A staged transcript path is another source. A standalone
reader should require a unique, explicitly bound candidate and retain lineage,
rather than inherit that ambiguity-resolving heuristic. Consent must cover the
actual read scope; selecting a task is not permission to read unrelated files
while searching for it.

The app's transcript reader can combine disk rows with an in-memory message
buffer. The standalone file path does not expose that buffer. The internal
reader also has filters, caches, byte ceilings, and read paths that can touch
file modification times. Reimplementing the narrow file acquisition avoids
importing those app readers, but does not manufacture a live flush guarantee.

### Public SDK and app-hosted getters

The documented `getSessionInfo` helper returns metadata such as session ID,
timestamps, summary, working directory, and branch. Its listed fields omit
effective account route, model, and permission mode. The SDK's initialization
event can contain model, permission mode, working directory, and API-key
source; an initialization observation alone does not establish later state.
`accountInfo()` belongs to a live `Query`, whose documented methods also
include runtime settings changes. This inspection did not establish an
external read-only attachment from that API to an existing Desktop-owned
query. No query was created or invoked.
[Agent SDK TypeScript reference](https://code.claude.com/docs/en/agent-sdk/typescript)

Desktop's internal `get_session` host tool calls its in-process manager and
returns metadata, including model and worktree; its permission-mode output is
restricted to self or child sessions. Its registration is an app-hosted tool
for a running Code session. Finding that tool does not provide the standalone
reader with an external endpoint, nor does its output constitute a complete
effective-settings snapshot.

## Delivery and acknowledgment

Desktop's host `send_message` calls its manager's `sendPeerMessage` with a
Desktop origin and generated message ID. That producer stores `peerReceipts`
on the sending Desktop session, calls `sendMessage` with the origin and
`peerMessageId`, and records `peerInbound` on the receiver. The manager builds
a user row with `client_platform: "desktop_app"`; `notePeerTurnStarted`
updates the sender's receipt when the receiver starts that turn. `nE`
persists the corresponding peer state.

The selected external sender is the native Code `SendMessage` exposed through
`claude mcp serve`, as established in the
[sender investigation](https://github.com/nisavid/provingkit/blob/ee76e2a85c6cff97bd2111eefdc41fa6dfd433be/docs/superpowers/research/2026-09-26-claude-inbox-feasibility.md).
The inspected Desktop path does not show that this external call enters the
host producer above or yields those same rows. Desktop `peerInbound`,
`delivered`, `readAt`, and `repliedAt` cannot qualify that route without the
missing link. `notePeerReply` marks eligible receipts for a peer pair; it does
not parse an application-correlated acknowledgment.

Desktop's host sender can report `undelivered` / `no_turn` after a timeout
while expressly allowing later delivery. Its queued and refused states are
also specific to that producer. The bundled Code schema describes
`crossSessionInbound` choices `accept`, `hold`, and `refuse`, including policy
defaults. It does not establish an externally readable durable state record
for the chosen sender. Silence cannot distinguish held, refused, delayed,
lost, or unobserved delivery.

## Effective receiver state

The distinction between stored selections and running values is present in
concrete producers, not merely a hypothetical upgrade concern:

- **Account route:** storage placement uses the manager's account and
  organization. Spawn options separately capture `spawnIdentity` and
  `spawnOrgId` in live state keyed by the input stream. `spawnAccountOf` reads
  that state; refreshes can subsequently update the executor's environment.
  A storage directory does not identify the effective executor route.
- **Model:** the saved selection can be `default`. The manager separately
  tracks `modelConfirmed`, consumes Code initialization reports, and can query
  the running model. A saved selection can lead or differ from a live update.
  No external acquisition of the confirmed value was established.
- **Permissions:** `permissionMode`, `sessionSettings`, and
  `sessionPermissionUpdates` are saved inputs. Spawn combines them with
  settings sources, managed settings, mode constraints, directories, and
  other runtime inputs; later updates can fail or remain pending. Equality of
  stored permission modes does not establish equality of effective permission
  state. This report assesses observability, not permission enforcement.
- **Worktree:** saved `cwd`, `originCwd`, `worktreePath`, and `worktreeLazy`
  describe manager state and initial spawn choices. Runtime worktree events
  can update `harnessCwd`; the serializer does not persist it. App-hosted
  consumers may use `harnessCwd || worktreePath || cwd`, so the saved path is
  not always the current executor path.

## Requirement-to-observation assessment

The access designs below are proposed from source. None has been exercised
against private receiver data or an authorized live fixture.

| Requirement | Concrete acquisition design | Missing fact and smallest settling step |
| --- | --- | --- |
| Native peer address, Desktop task, executor, and transcript lineage | Read the selected Desktop JSON, follow its Code ID and lineage to one selected JSONL file. | External discovery-address and running-process binding remain unresolved. A reviewed disposable-fixture plan must compare discovery, Desktop task identity, Code init identity, and process identity before any send. |
| Receiver-origin external delivery | Read raw rows from the bound transcript and retain origin and message identifiers. | Establish which row the chosen external sender actually produces and when it persists. Requires a reviewed acquisition candidate and an authorized, scoped fixture send; Desktop host receipts alone are insufficient. |
| Explicit correlated acknowledgment | Parse receiver assistant output following the bound delivery; match the interface-defined correlation ID. | Define the acknowledgment grammar and provenance rule, then qualify it on the fixture. Reject echoes, quotations, unrelated output, and pair-level reply flags. Synthetic text matching cannot establish the missing live producer. |
| Bounded wait and freshness | Re-read selected files with identity, size, complete-line, and lineage checks; record the observation interval and coverage limits. | Qualify visibility on the fixture. Debounce, buffering, replacement, truncation, compaction, and retention prevent a negative-completeness claim from a quiet file. Timeout remains unknown. |
| Unknown-send reconciliation | Accept positive records whose receiver, origin, and application ID are established; otherwise retain unknown. | Prove the external record's meaning and identity. A missing record supplies no resend permission. Reconciliation does not require or imply proof that nothing happened. |
| Held and refused outcomes | Use explicit observations from a proven producer for this route. | No external read-only path was established. Decide whether a new observer can expose these states; preserve them as required distinctions where evidenced, and report unknown elsewhere. Existing synthetic failure coverage remains the initial plan; disruptive live failures need a separate decision. |
| Effective account route | Observe a non-secret runtime identity bound to the actual executor. | The inspected identity lives in process state. Choose a concrete external observation method or explicitly revise the claim; any new app-side observer needs its own design, review, and scoped qualification. |
| Effective model | Read a current confirmed executor report, separately from the saved selection. | No external route to the live confirmed value was established. Define the observer before proposing a controlled saved-versus-running comparison. |
| Effective permissions | Observe the specified effective permission fields and the process that uses them. | Define the exact preservation observation and its source. Stored mode alone is insufficient. Controlled settings comparisons, if needed, require their own scoped fixture plan and authority. |
| Current worktree | Observe current runtime cwd / worktree, bound to the same process. | No external route to `harnessCwd` was established. Compare saved and current values across a controlled worktree transition only after an observer and scoped fixture plan exist. |
| Busy context continuity | Record predeclared harmless canaries, task resumption, and later turn-in. | Collect during the existing busy qualification. This remains diagnostic; it does not add a pass/fail threshold. |

## Compatibility by consumed behavior

The previous report inspected Desktop **2.7032.0**, ASAR SHA-256
`6f669e85b82c8cf8a028fe77b6e869baec1f23961d8bec62b38bcbfc498b6d7c`.
No previously extracted chunk was byte identical to a current chunk. Targeted
inspection nevertheless found the same relevant storage, serializer identity,
host messaging, and stored-versus-runtime separation described above. That
supports carrying forward these specific source findings. It does not
establish parser compatibility over all inputs or carry forward live evidence
that was never collected.

The maintained reader should own this dependency inventory:

| Consumed dependency | Inexpensive check and escalation | Evidence affected by a failure |
| --- | --- | --- |
| Metadata layout, serializer, writer, and Desktop-to-Code init mapping | Triage relevant release notes; compare these producers; run fixtures covering required fields, missing values, delayed/direct writes, and lineage changes. Inspect changed paths where the comparison is inconclusive. | Task binding, stored-value reads, and any downstream result using them. |
| Transcript selection, raw rows, filters, retention, and buffering | Compare relevant resolver/producer behavior; exercise duplicate candidates, partial rows, replacement, truncation, compaction, and delayed persistence. | Read coverage and affected record interpretations; parsing success alone restores neither. |
| External discovery and delivery producer, once established | Retain the actual descriptor/row contract and probe its relevant behavior. Escalate to affected live qualification when the source or fixtures cannot settle a changed assumption. | Address binding, delivery, and acknowledgment claims dependent on that producer. |
| Effective-state observers, once selected | Compare their source, process binding, fields, and observation timing; probe changed fields. | Only the affected preservation observations and dependent route qualification. |

**Compatible** means evidence supports the required behavior, including
justified carry-forward. **Unassessed** means the effect of a change is not yet
known; read-only assessment may proceed while dependent conclusions remain
limited. **Incompatible** requires a demonstrated failed assumption and
disables the affected function until repaired or replaced. A new version or
whole-archive digest alone establishes neither incompatibility nor a need to
repeat every live test. Release-note silence alone establishes neither
compatibility nor unchanged internal behavior.

Escalate from release notes and relevant artifact comparison to contract
fixtures, targeted source inspection, and affected live qualification according
to the unresolved assumption. Record what evidence was reused and why.
Compatibility status, completeness of one message observation, and route
qualification are separate: a compatible parser may correctly return unknown
for incomplete evidence, and an initially unqualified route remains so after
source comparison. The accepted synthetic prototype's digest gate is a demo
behavior, not the maintained upgrade policy.

## Decision and downstream work

Keep the notification interface blocked on a decision about the missing
runtime observations. A file reader is now a concrete acquisition design;
another parser demonstration would not establish the absent producers.

The decision has three meaningful directions:

1. **Preserve the accepted claim and design an additional automated runtime
   observer.** I recommend this direction for the next bounded decision.
   First identify how the observer reaches the exact Desktop-owned process
   and obtains non-secret current values. Compare an app-side observation
   with any usable existing control surface; neither is established here.
   Accepting this direction would authorize design work, not installation or
   a live probe. If design cannot name a concrete access path, return that
   result instead of repeating the same static survey.
2. **Revise the preservation or evidence claim.** State which effective
   observations would become stored-value observations or operator-assisted
   evidence, and revise the destination and dependent acceptance criteria
   explicitly. This changes the accepted product behavior and needs Ivan's
   decision.
3. **Hold the route pending an externally observable surface.** Retain the
   report and conditional reader adoption without claiming feasibility or
   proceeding with implementation.

An earlier disposable observability experiment may help settle native-address
binding and external row provenance, but cannot by itself expose a runtime
field for which no reader exists. Such an experiment needs an explicit graph
revision, a reviewed bounded candidate and plan, scoped fixture/data-access
authorization, and exact-peer consent before a send. It is not covered by
the current research or silently moved ahead of the existing live gates.

The native decision blocker must be in place before this research closes.
[Specify the notification interface and qualification evidence](https://github.com/nisavid/provingkit/issues/214)
must distinguish stored, running, and unknown observations;
[Implement the exact-peer notification actuator](https://github.com/nisavid/provingkit/issues/215)
must implement the standalone reader as a separately testable resource;
[Prepare the disposable receiver and preservation observation plan](https://github.com/nisavid/provingkit/issues/218)
must bind every read and observation to the authorized fixture. None may treat
this source report as a receiver qualification pass.

## Reproducible inspection and procedure capture

The retained report owns the source-only inspection method. This investigation
used it against the refreshed archive: record package and ASAR identity;
parse the ASAR header as data; extract the relevant first-party JavaScript;
hash it; trace producers, persistence, and consumers without executing modules
or opening receiver records. Static string presence alone does not establish
a callable API or producer relationship.

For future compatibility assessment, inspect the consumed dependencies in the
table above, record the prior finding and the precise behavior compared, and
retain the unchanged evidence where justified. Keep any newly missing
observation as a blocker with its smallest settling experiment or decision.

[Capture the Rolecasting peer-notification skill and invocation](https://github.com/nisavid/provingkit/issues/216)
must consume this report under `capturing-agent-procedures`, record the source
revision used, and place the settled reader invocation, observation semantics,
compatibility inventory, and unknown-send recovery in maintained Rolecasting
equipment. This report provides research input; it installs no procedure and
does not settle the open runtime-observer design.
