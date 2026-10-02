# Bounded fixture discovery and executor binding

**DONE_WITH_CONCERNS.** The retained sources support a bounded metadata reader and a proposed Code-ID/socket hook projection. They do not establish an independent external witness identifying the intended Desktop task, the native target-resolution join, or hook execution by the selected receiver engine. I found a publicly reachable artifact matching Desktop’s embedded release target, which makes the next source check concrete.

These are independent first findings. Cross-examination and the final reviewed report remain pending. No private receiver data, working prototype, or other current track output was read.

## Source identities and limits

Repository evidence was read with `git show` at `b8760030957fefa1bc9c21bd6052373674d1971d`, including the reviewed comparison, its lane reports, method, corrections, and cited earlier research.

The source legend below names retained members without their acquisition locations. Offsets are zero-based UTF-8 byte offsets and apply only to these digests.

| Name used here | Retained member | SHA-256 |
|---|---|---|
| Manager | `.vite/build/index.chunk-B9SZqsi8.js`, retained as `manager-pristine.js` | `bd2144a3653bb843f4b75fe652124a4e478f273b5f6c2e10a2139fa3a9a3152f` |
| LocalSessions | `.vite/build/index.chunk-COPWZCsC.js` | `b22a9dc34684cef348f9c0e72abe88c433bbfc2d350d9a3e61faf7ae22858950` |
| Desktop core | `.vite/build/index.chunk-DuaKZOPP.js` | `f160a24940ee11cea6a788a9038e95c14fb150889977dcfa331fd9b07aba0c96` |
| Serializer | `.vite/build/index.chunk-CKt-cwRV.js` | `dad88ac66fe13f72d0225c49d48e124d238ff643ff96426c4a2020482621e62d` |
| Public SDK | `sdk.mjs` from stable SDK 0.3.284 | `32d062c37b03e10870fbf839f54694545ee01bc0ec719e47078fbed76e30ef71` |

The retained SDK identity record attributes its archive to [SDK 0.3.284](https://registry.npmjs.org/@anthropic-ai/claude-agent-sdk/-/claude-agent-sdk-0.3.284.tgz), archive SHA-256 `4550e830246026133fc1802a2208dd0f3a785cae1eec83f261d114c33d797771`. I recomputed member digests, but did not reacquire that archive.

Desktop core’s `ig()` identifies Desktop **2.9939.4**, commit `a166d8a7c640e65ad825ebfb99d74ccbb9c8940d`. Its adjacent `ag()` declares:

- Code target **2.1.284**, commit `16cbb4ddeeb473f57fd8d5b713764903d7928e66`;
- mods commit `7779afb12e3635f46f56ec823979d68350ae000b`;
- build date `2026-09-27T04:50:20Z`;
- SDK wrapper **`0.3.284-rc.20260927.t043816.sha16cbb4d`**.

These declarations occur around bytes **1,738,100–1,742,050**. The stable public SDK is therefore a separate interpretation input; it is not a demonstrated byte match to Desktop’s declared release-candidate wrapper.

## What identifies a Desktop task

`LocalSessions.start` awaits Manager `startSession`, conditionally performs text binding, and returns `{sessionId:d}` on either successful path. The comma expression supports the existing integration correction. Exceptions can reject the call. Source: LocalSessions **27,800–28,640**.

That result belongs to an internal interface. Desktop core registers `createLocalSessionsApi` through `Ob.for(webContents).setImplementation`, around **5,913,200–5,915,100**. The inspected registration supplies no standalone external connection address. An internal creation result cannot be treated as an externally available task witness.

Metadata construction is concrete. Manager `getStorageDir`, `storageDirFor`, and `getSessionFilePath`, **918,900–919,920**, derive:

```text
selected user-data root / manager base directory / account ID /
organization ID / Desktop session ID.json
```

Desktop core declares `claude-code-sessions` around **3,869,553**. Parked records can use their recorded account and organization rather than the manager’s current pair. The acquisition contract must consequently receive its directory binding explicitly.

The serializer `nE`, **503,942–509,796**, persists `sessionId`, `cliSessionId`, project/worktree fields, and lineage including `priorCliSessionIds`, `rewindEdges`, `transcriptCuts`, and fork/import/dispatch information. Manager’s initialization handling, **1,520,176–1,521,750**, maps the Code-reported `session_id` to the Desktop record and saves it.

One earlier source claim needs correction: **`nE` does not serialize `unarchivedCliSessionId`.** That symbol occurs elsewhere, and initialization clears its in-memory value. A stored-file reader must not require or claim this field.

These sources establish a persisted Desktop-to-Code relationship. They do not establish current execution, freshness, or native address identity.

## Proposed bounded acquisition contract

The following limits are design proposals for review, not an access grant.

| Stage | Proposed acquisition footprint |
|---|---|
| Directory binding | One explicitly supplied account/organization metadata directory under the selected user-data root. Check its path and filesystem identity. Do not discover account or organization by opening private settings. |
| Listing | One nonrecursive streaming listing: at most **128 entries plus one overflow entry**. Acquire entry names and types; do not recurse, sort an unbounded listing, or open files during enumeration. Overflow stops discovery. |
| Candidate selection | The operator explicitly selects at most **three** regular `.json` basenames from that listing. Names nominate candidates; mtime, novelty, and title do not establish identity. |
| Content acquisition | Read each selected file’s **entire serialized JSON**, including every nested value, if its size is at most **1 MiB**. The grant must cover all three whole files, rather than only retained identity fields. |
| Race and size handling | Check opened file identity and size, cap actual reads at **1 MiB plus one byte**, and reject replacement, growth beyond the limit, incomplete JSON, or filename/serialized-ID disagreement. Any acquired prefix remains part of the exposure record. |
| Interpretation | Retain approved identity, path, lineage, and acquisition-time evidence. Do not dereference transcripts, staging paths, settings, project files, or other values found inside the JSON. |

The complete content footprint is the raw serialized object produced by `nE`, not an identity-only representation. Its fields include titles and previous titles; reminders; settings; MCP and remote configuration; SSH/WSL information; browser/computer-use grants; recaps and summaries; errors; artifact and scratch metadata; peer receipts and inbound records; email and bridge/cloud identifiers; permission updates; spawn seed and binary pin; prompt/tool snapshots; and all other emitted values in the pinned serializer span. Helpers also produce nested values. Output filtering removes none of those acquired bytes.

Manager `writeSessionToDisk`, **937,560–938,322**, serializes the object and attempts an atomic writer, with a direct-write fallback for specified filesystem errors. A successful read must therefore validate the actual acquired object. File existence or mtime is not a writer-fulfillment or freshness guarantee.

### Independent selected-task witness

No existing external exact-task witness was established in these inputs. The proposed metadata selection remains blocked until one is supplied.

Two concrete directions can be assessed:

1. **An operator-readable exact Desktop identifier:** a separately verified selected-task control supplies the Desktop ID, which must equal both filename and serialized `sessionId`. No such control was established by this investigation.
2. **A separately authorized fixture handshake:** the operator acts in the intended dedicated-project Desktop task and requests a unique agreed response. A project-local Stop observation records that response, Code `session_id`, and socket projection. The approved metadata candidates must yield exactly one record whose **current** `cliSessionId` matches the observed Code ID and whose project binding matches the fixture.

The second direction needs normal-UI creation/selection evidence, bounded hook-input exposure, hook activation, and a setup prompt. It is a proposed independent witness, not an observation already available. A historical lineage match alone must not admit a peer: prior Code IDs can explain history but can refer to an earlier executor.

If neither witness is viable, the app-side receipt should be compared specifically against this missing selected-task binding. Its registration, persistence, transition, and same-query witnesses are additional guarantees of that procedure. Its 15-minute admission ceiling applies only if that procedure is selected.

## Hook identity and native target resolution

Current official documentation says settings-defined hooks apply to Desktop and CLI sessions. Command hooks receive event JSON; common fields include Code session identity, transcript path, and event-time cwd. Stop can provide final assistant text, while transcript persistence can lag. This supports designing a projection without opening the transcript. It does not establish emission by the selected engine. [Desktop shared configuration](https://code.claude.com/docs/en/desktop#shared-configuration), [hook inputs](https://code.claude.com/docs/en/hooks#hook-input-and-output).

The messaging documentation associates `CLAUDE_CODE_MESSAGING_SOCKET` with the session inbox and shows that path with a `uds:` prefix in `/status`. It documents export before hooks when messaging starts enabled. A hook can therefore propose a Code-ID/socket association. Socket presence does not prove admission: a refusing session can remain listed. The documentation inspected here does not establish the exact conversion from that projection to the native MCP `SendMessage.to` selector. [Inbox socket](https://code.claude.com/docs/en/cross-session-messaging#the-sessions-inbox-socket).

The earlier sender investigation observed native MCP schemas on Code **2.1.280** and **2.1.283**, with names and disambiguating references as selectors. Those dated observations support the native sender candidate; they do not resolve the **2.1.284 RC** parser or current discovery-address join. [Pinned sender investigation](https://github.com/nisavid/provingkit/blob/ee76e2a85c6cff97bd2111eefdc41fa6dfd433be/docs/superpowers/research/2026-09-26-claude-inbox-feasibility.md).

A future join must demonstrate how the captured socket maps to the fresh native descriptor and accepted selector. A guessed `uds:` prefix, display-name match, or bare UUID is insufficient.

## Matched release artifact lead

Desktop core’s `downloadBinaryForTarget`, beginning at **3,935,555**, constructs the release URL from base URL, version, platform, and binary name. It verifies the compressed manifest checksum before decompression.

For its embedded Linux x64 target, the derived [Code RC artifact](https://downloads.claude.ai/claude-code-releases/rc/16cbb4ddeeb473f57fd8d5b713764903d7928e66/2.1.284/linux-x64/claude.zst) returned **HTTP 200** to a public HEAD request, with content length **85,295,282**, matching the embedded manifest. Expected compressed SHA-256:

```text
20b1b16df81e34abc68bef87c5a8433106f0cf4e84b2dd507e37bb7978cbd6f2
```

The coordinator received this acquisition lead. I did not download or execute the artifact.

It is a **build-target match**, not proof of the selected executor. Desktop core `resolveHostBinary`, approximately **3,945,800–3,946,400**, permits local overrides, preseeds, required versions, and fallback versions. Manager `yT`, **626,221 onward**, handles pins, downloads, and paths with unknown identity. `applyFreshBinaryPath`, **1,285,967 onward**, can transform execution through a launcher.

Manager also conditionally removes `PostToolBatch` when the resolved identity does not establish sufficient support, around **1,289,004**. This demonstrates why declarations and version labels require event-specific qualification.

## Requirement assessment and next checks

| Requirement | Supported source contribution | Remaining evidence |
|---|---|---|
| Intended Desktop task | Metadata filename/object relationship | Independent selected-task witness |
| Desktop-to-Code identity and lineage | Serializer plus initialization mapping | Fresh authorized acquisition and unique current-ID match |
| Code-to-native peer | Documented hook socket association | Matched target parser and fresh native descriptor join |
| Selected-engine hooks | Manager settings/callback path; reachable RC artifact lead | Artifact inspection, actual executor binding, later hook observation |
| Receiver delivery | Public SDK preserves useful origin fields through `gb`/`KD` | Actual native ingress producer and authorized positive record |
| Correlated ACK | Stop final-text candidate | Selected-engine emission, attribution, grammar, and echo rejection |
| Full qualification state | Existing comparison retains required endpoint observations | Actual account, model, applied permissions, worktree, and current-cwd evidence |
| Unknown reconciliation | Positive evidence can be sought through bounded reads | Missing evidence remains unknown; no automatic resend |

The public SDK’s explicit-directory lookup is unsuitable as an exact-file acquisition boundary: `GD` at **530,964** calls `Vo`; `Vo` at **406,889** reaches directory/worktree lookup, and `Aa` around **404,100** can inspect additional transcript candidates. Interpret approved bytes separately from SDK acquisition.

The smallest next source check is coordinator acquisition and static inspection of the named RC artifact, followed by tracing socket export, relevant hook emission, discovery descriptors, and target resolution. Actual selected-executor identity remains a later qualification obligation.

The smallest later live check is one separately authorized no-send fixture handshake with reviewed acquisition limits and a minimal Stop projection. It cannot qualify native delivery or full preservation.

## Cross-examination handoff

Freeze this report and its source identities before exchanging findings. Ask the other tracks to challenge the proposed witness, whole-file footprint, current-versus-historical Code-ID rule, wrapper distinction, and native selector gap. Reconcile contradictions against primary source spans and any explicitly acquired release artifact.

Under `capturing-agent-procedures`, the coordinator should capture the settled method and downstream invocation at the final reviewed revision. This research installs no procedure and grants no security acceptance or live-route qualification.

Public documentation retrieval, bounded source inspection, hashing, and the artifact HEAD request succeeded. Combined report reads occasionally exceeded tool-output limits; relevant spans were subsequently read separately. No files were edited, tests run, modules executed, or live receiver actions performed.