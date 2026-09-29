# Claude Desktop receiver evidence: internal reader candidate, qualification open

A reader of Claude Desktop's task metadata and Code transcripts is a plausible
automated evidence path for the first notification route. The inspected source
contains the task-to-transcript mapping and stored settings, but this research
does not establish a complete receiver-origin delivery record, correlated
acknowledgment, or preservation snapshot for the selected external sender.
Keep implementation behind a decision on a bounded internal-reader prototype
and the unresolved evidence requirements.

This report resolves the investigation in
[Verify automated receiver evidence for Claude Desktop](https://github.com/nisavid/provingkit/issues/262).
The accepted direction remains ChatGPT in Codex mode to one existing,
consent-bound Claude Desktop-hosted Code peer on the same Linux machine.
[The receiver-evidence decision](https://github.com/nisavid/provingkit/issues/249#issuecomment-5881568334)
permits evaluating internal formats; adopting them requires a separate operator
decision. The notification contract and later live-fixture gates remain in force.

## Evidence boundary

The investigation used current Anthropic documentation and static inspection of
installed Desktop application code on 2026-09-28 in America/New_York
(2026-09-29 UTC). It made no peer send, model prompt, task creation or resume,
installation, or permission change. No private receiver transcript or task
metadata was opened. Source extraction read the archive into scratch files;
it did not import or execute Desktop modules.

In this report, **documented** means stated by Anthropic; **observed** means
directly inspected package bytes or source behavior; **inferred** means a
candidate design suggested by that evidence; **unresolved** means the required
runtime or identity evidence is absent. An observed function is not an observed
successful live read. No disposable receiver was selected, so the installed
package is not bound to a running receiver's app, executor, account, or settings.

## Documented surfaces

Desktop documents session listing, transcript reading, messaging, and replies
through Claude inside another Code-tab session. That surface sees Desktop-run
Code sessions and defaults to the 20 most recently active, unarchived sessions.
Its busy receiver waits until current work finishes. I found no externally
callable read-only Desktop endpoint in that documentation.
[Work across sessions](https://code.claude.com/docs/en/desktop#work-across-sessions)

The TypeScript Agent SDK documents `listSessions`, `getSessionInfo`, and
`getSessionMessages`. The last reads user and assistant messages from a past
session by ID, with directory, limit, and offset options. Returned messages
include their session ID, UUID, and payload. Session metadata includes timestamps,
working directory, and branch, but its documented fields omit account route,
model, and permission mode. The reference does not establish a live freshness
guarantee or the binding from an exact Desktop task to these APIs.
[Session inspection](https://code.claude.com/docs/en/agent-sdk/typescript#getsessionmessages),
[session metadata](https://code.claude.com/docs/en/agent-sdk/typescript#getsessioninfo)

The SDK's custom `sessionStore` interface does not provide a pre-existing
Desktop observer. Its documented `getSessionMessages` behavior returns the
post-compaction chain; earlier entries may be replaced by a summary. Reading
the full raw store requires `store.load(key)`, whose adapter and key would still
need to be supplied.
[Session storage](https://code.claude.com/docs/en/agent-sdk/session-storage#getsessionmessages-returns-the-post-compaction-chain)

The CLI session guide distinguishes Desktop's history and warns that raw JSONL
entry formats are internal and can change on any release. Thus a documented
SDK function does not make Desktop discovery, raw receipt interpretation, or
concurrent-read completeness a documented contract.
[History scope and transcript format](https://code.claude.com/docs/en/sessions#where-transcripts-are-stored)

[The prior sender investigation](https://github.com/nisavid/provingkit/blob/ee76e2a85c6cff97bd2111eefdc41fa6dfd433be/docs/superpowers/research/2026-09-26-claude-inbox-feasibility.md)
observed `ListAgents` and `SendMessage` through `claude mcp serve` in Code
2.1.280 and 2.1.283. Those are retained sender findings, not fresh receiver
qualification. Desktop's own session messaging and native Code peer messaging
must be assessed separately.

## Installed source findings

The primary local source is `claude-desktop-extra` package `2.7032.0-3`.
Its ASAR manifest identifies `@ant/desktop` version `2.7032.0`. The archive
SHA-256 is `6f669e85b82c8cf8a028fe77b6e869baec1f23961d8bec62b38bcbfc498b6d7c`.
Installed ChatGPT was `26.924.50649-1`; that inventory does not identify the
eventual sender or receiver's running builds.

The following paths are relative to the Desktop ASAR archive. Minified symbol
names are locators for these pinned bytes, not stable APIs.

| Source | SHA-256 | Relevant locators |
| --- | --- | --- |
| `.vite/build/index.chunk-B-iwB3_n.js` | `f3e09ead3db6775d6cef294e00673d2321d5e40151599c84e379ae727d0de755` | `getStorageDir`, `getSessionFilePath`, `writeSessionToDisk`, `getTranscriptWithoutQueryCrashes`, `sendPeerMessage`, `trackPeerInbound`, `notePeerTurnStarted`, `notePeerReply` |
| `.vite/build/index.chunk-C0vuTD4w.js` | `eeef75af54f1f9c8cef5f2886b26e4eb0fb61373cd627594e8a1a175dd88ebc8` | serializer `cE`, exported as `ht` |
| `.vite/build/index.chunk-m7G27Wrl.js` | `c3f2efde76bdcc1db6fda9776fbb1965ae6d615b8aaa4014bea43c02d04c6613` | `resolveProjectDirForSession`, `resolveSource`, `fullFromDisk`, `loadRawChain`, `skipMtimeTouch` |
| `.vite/build/index.chunk-BYymhkVO.js` | `df92d64ef2ef7d4aac15df9e3ab8450a68e69bb0311a63a02738c2c4cb37f305` | SDK exports `getSessionMessages`, `getSessionInfo`, `listSessions`; readers `ege`, `qAe`, `w1`, `Qhe`, `S1` |

### Task identity and preservation fields

**Observed:** the Code session manager writes per-session JSON under an
account-and-organization directory inside its application data root.
`writeSessionToDisk` calls serializer `cE`, which includes Desktop `sessionId`,
`cliSessionId`, `cwd`, `originCwd`, `worktreePath`, `model`, `permissionMode`,
`sessionSettings`, `sessionPermissionUpdates`, and lineage fields such as
`priorCliSessionIds` and `transcriptCuts`. Transcript lookup uses
`cliSessionId` or `unarchivedCliSessionId` and a corresponding JSONL file.

**Inferred:** these records could bind an explicitly selected Desktop task to
its Code transcript and provide stored model, permission, and worktree
observations. A title match or newest-file heuristic would not establish the
consented peer. Native sender addresses still need a verified mapping to that
same task; the contract does not newly require a full UUID from the operator.

**Unresolved:** stored choices need not equal effective running settings.
The account-and-organization storage directory is not proof of the executor's
account route. The source separately tracks spawn account identity in live
process state. Complete effective permissions can also depend on settings
beyond `permissionMode`. No before/after evidence establishes these fields
for a receiver here.

### Delivery records and explicit acknowledgment

**Observed:** Desktop's `sendPeerMessage` keeps `peerReceipts` on its sending
session and `peerInbound` on its receiver. Both appear in the serializer.
`trackPeerInbound` requires a peer origin and a Desktop `peerMessageId`.
`notePeerTurnStarted` removes the pending inbound entry and updates the sender's
receipt. `notePeerReply` marks eligible prior receipts for a peer pair; it does
not parse an explicit acknowledgment carrying the application's correlation ID.

These records describe Desktop's own session messaging. The inspected path
does not establish that an external native `SendMessage` call produces those
same receipts. A stored `delivered`, `readAt`, or `repliedAt` field therefore
cannot qualify the chosen route by itself. The receiver's explicit correlated
acknowledgment must be found and distinguished from echoed notification text,
quoted text, and unrelated assistant output.

**Observed:** the embedded SDK reader filters its message chain. In these
bytes, `Qhe` excludes metadata, sidechain, and team entries and defaults to
excluding system entries. Some queued attachments are converted to user rows.
`S1` can retain timestamp and origin fields, but that does not establish that
the selected external delivery will be represented by a retained row. The
actual delivery record shape and acknowledgment representation remain
**unresolved** for this route.

### Freshness and completeness

**Observed:** Desktop's Code transcript reader can merge disk messages with
its live message buffer. It tracks rewind/clear state and can fall back to
buffered messages. Its disk reader uses caches and byte limits, reports some
truncation, and has a path-selection fallback that can choose among multiple
files for one Code ID. Its full-read path can refresh transcript modification
times unless suppression is enabled. Session metadata writes prefer atomic
replacement but have a direct-write fallback for specified filesystem errors.

**Inferred:** invoking these internal app readers is unsuitable as an assumed
read-only external API. A standalone file reader would need its own handling
for incomplete writes, replacement, compaction, lineage changes, duplicate
candidates, retention, and delayed persistence. Modification time alone cannot
be treated as a message-arrival watermark, including because Desktop can touch
it during reads or retention maintenance.

No observed live flush bound or completeness watermark permits a disk reader
to prove that a message was never accepted. Missing records can mean delay,
filtering, truncation, retention, or an incorrect binding. Bounded inspection
can stop waiting and report unknown; expiration cannot justify an automatic
resend or silently become a refusal.

## Requirement assessment

| Requirement | Current evidence | What must still be established |
| --- | --- | --- |
| Exact consent-bound receiver | Internal Desktop-to-Code ID mapping exists in source | Bind fresh native address, selected Desktop task, running process, and transcript lineage; reject ambiguous or changed identity. |
| Receiver-origin delivery | Transcript and internal peer-state candidates exist | Demonstrate the external sender's durable receiver record and its meaning on the approved fixture. |
| Explicit correlated acknowledgment | SDK can read assistant payloads | Observe an explicit receiver acknowledgment with the same application ID; exclude echoes, quotes, and unrelated output. |
| Bounded wait/inspect | Readable files and SDK calls are candidates | Define read errors, delay, coverage, and timeout behavior; prove the chosen reader sees current fixture evidence. |
| Unknown-send reconciliation | A positive matching receiver record may settle an unknown submission | Establish record provenance and completeness; absent evidence remains unknown without a valid negative-evidence rule. |
| Held/refused/absent/delayed distinctions | Desktop's separate host path has some lifecycle records | Establish which outcomes the selected external path exposes. Do not invent an outcome from silence or reuse host-path flags without proof. |
| Account route, model, permissions, and worktree | Stored metadata covers several requested fields | Observe effective values before/after; any missing field remains a blocker or returns for an explicit change to the claim. |
| Busy-receiver continuity | No live evidence collected | Record predeclared harmless canaries, task resumption, and later turn-in as diagnostics at qualification. No new pass/fail threshold. |

## Decision and maintenance tradeoffs

I recommend a decision on a **bounded standalone internal-reader prototype**,
while retaining the Desktop receiver and accepted evidence contract. This
would accept a dependency worth testing, not establish that the route works.
The prototype should be source and synthetic-fixture work first. It should
read copies or explicitly selected files without importing Desktop modules,
and return unsupported or unknown when build, schema, identity, or coverage
cannot be established. It should not select an arbitrary replacement task or
send again to resolve uncertainty.

The concrete cost is ownership of Desktop metadata mapping, raw transcript
interpretation, and freshness checks across upgrades. There is no demonstrated
stability interval: this investigation inspected one Desktop archive, and
Anthropic explicitly warns that transcript schemas can change each release.
An upgrade would require renewed schema inspection, synthetic fixtures,
independent review, and affected live qualification before support can be
claimed for its new bytes. Runtime uncertainty about account route and
effective permissions remains even if parsing succeeds.

Alternatives are to retain the current hold until a documented external
observer is available, or explicitly reopen the observation method or receiver
choice. Operator-assisted evidence changes the accepted automated-reader
direction; a different receiver changes the destination. Neither is an
implicit fallback.

The adoption decision must block
[Specify the notification interface and qualification evidence](https://github.com/nisavid/provingkit/issues/214).
Before that decision closes, it must wire any required source feasibility work
and preserve unresolved contract requirements as blockers. Live evidence must
follow the existing review, temporary-installation/fixture authorization, and
exact-peer send-consent gates; those gates grant no authority through this
report. The reverse-direction Queue/Steer map remains separate.

## Reproducible inspection and procedure capture

For another read-only source inspection:

1. Record the installed package and ASAR manifest versions, then hash the whole
   archive and the exact extracted chunks. Record running app/executor identity
   separately when a receiver is later selected.
2. Parse the ASAR header and extract only the named source chunks into scratch
   files. Trace the locators above without importing app modules, launching a
   Claude query, or opening user session contents.
3. Follow the session serializer, task-to-Code-ID mapping, transcript reader,
   and delivery-state producers separately. Identify which messaging path each
   producer serves before assigning it evidence meaning.
4. Compare the public SDK contract with the pinned filters and internal fields.
   Record missing or changed fields as a gap, with no inferred runtime pass.
5. Publish only versions, digests, source locators, and findings. Keep private
   account/task identities and transcript content out of the report.

This method is input to
[Capture the Rolecasting peer-notification skill and invocation](https://github.com/nisavid/provingkit/issues/216).
That work must invoke the selected evidence reader and its recovery rules only
after adoption and qualification. It must retain the difference between
notification delivery and explicit acknowledgment. This investigation adds no
unqualified reader to installed skills.
