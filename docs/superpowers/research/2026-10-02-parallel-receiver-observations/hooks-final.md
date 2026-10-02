# Hooks lane: cross-informed report

**DONE_WITH_CONCERNS.** Hooks remain a useful partial observation channel. The strongest combination to investigate is the native sender, a reader restricted to the selected stored session, and a minimal `Stop` hook for final acknowledgment text. The app bridge remains a candidate for endpoint fields that those channels cannot supply. None presently covers the complete qualification contract.

This report retains the frozen first-round report unchanged as history. It makes no adoption decision and reports no runtime qualification.

## Cross-examination and dispositions

### The socket projection improves binding evidence but does not complete it

A hook can potentially associate its Code `session_id` with `CLAUDE_CODE_MESSAGING_SOCKET`. Official documentation identifies that variable as the session’s inbox path and shows `/status` presenting a `uds:` peer address. Native discovery may instead address a unique name or a listing-specific identifier. I have not established the transformation from the projected socket to the exact `SendMessage` target, or the independent join from that Code identity to the consented Desktop task. The projection is therefore a binding lead, not a completed admission check. [Messaging documentation](https://code.claude.com/docs/en/cross-session-messaging)

A refusing receiver can still bind its socket and remain visibly unchanged in local listings. Socket presence cannot establish inbound acceptance. Fresh exact-peer and consent checks remain necessary for every send.

### `LocalSessions.start` has one successful return shape

The coordinator correction is confirmed in the named renderer chunk, UTF-8 bytes 27,855–28,570. The comma expression conditionally calls `bindChangesNamedInPrompt` and then returns `{sessionId}`. Both successful paths return that object, regardless of whether `typedText` exists; exceptions can still reject.

This corrects the shared native-source description. It establishes neither an externally callable renderer method nor an external IPC endpoint.

### The stored reader is a delivery candidate, not a complete event stream

The existing-interface lane correctly distinguishes public stored-session readers from attachment to the selected live query. `getSessionInfo` and `getSessionMessages` are externally callable SDK interfaces; supplying the explicit project directory avoids their broader project search.

The remaining delivery question concerns the producer: whether a native incoming notification leaves a retained row with sufficient origin and correlation information. A matching positive record could support delivery. Missing records cannot establish non-delivery without flush, retention, and completeness evidence. Pagination offsets alone supply none of those guarantees.

### Eight app anchors establish access, not complete observation

The app lane’s eight-anchor core is a concrete hypothesis for preserving selected-query access and identity binding. Its conditional mode-event anchors address a separate evidence gap. Removing them requires a qualified substitute.

That bridge cannot make cached account information fresh, turn a requested model into the applied model, or turn rule enumeration into complete applied permissions. Its one-shot arm-and-sample design may be sufficient for an initial experiment; whether an operating interface needs continuous availability or repeated sampling remains open.

I also withdraw the first-round worktree row’s lease-preservation addition. The accepted fields concern the current worktree and cwd.

## Reachable interfaces and producer evidence

Current official Desktop documentation says settings-defined hooks apply to Desktop and CLI sessions. This establishes documented support, not execution by the pinned selected engine. [Desktop documentation](https://code.claude.com/docs/en/desktop)

The offline manager supplies a concrete integration path:

- `buildStartSdkOptions` passes settings sources and host hook callbacks into the selected SDK query.
- The main path includes user, project, and local settings; a distinct backend branch narrows the sources.
- Host callbacks include `Stop` and lifecycle-related behavior.
- `applyFreshBinaryPath` selects the executable and its version identity.
- The manager explicitly removes `PostToolBatch` callbacks when engine support is insufficient.

Those facts separate three versions: Desktop **2.9939.4**, SDK **0.3.284**, and the executable actually selected for the query. The first two do not establish the third.

The immutable public SDK 0.3.284 archive contains modern hook declarations and a wrapper that dispatches `hook_callback` inputs. Its declaration file includes `MessageDisplay`, `CwdChanged`, and `PostModelSwitch`; `Stop.last_assistant_message` and `SessionStart.model` are optional. The archive’s wrapper is not the engine, and declaration presence is not producer qualification. [Versioned SDK archive](https://registry.npmjs.org/@anthropic-ai/claude-agent-sdk/-/claude-agent-sdk-0.3.284.tgz)

For acknowledgment evidence, `Stop` is the smaller capture surface when the contract requires a final response. It does not run on user interruption; API failures have separate semantics. Its final assistant text avoids depending on transcript flush timing. `MessageDisplay` covers assistant text and, under the Agent SDK, fires once after each assistant message. It holds display until the hook returns, adding a different observer effect. Neither is an incoming-message witness. [Hook reference](https://code.claude.com/docs/en/hooks)

Most settings edits, including hooks and permissions, reload during a running session. Model configuration edits do not immediately change the current model. File-change notifications also do not cover every managed-settings arrival. The documentation promises no `SessionStart` replay when installing a hook mid-session. Thus hot reload can enable later observations without supplying a missing initial baseline. [Settings documentation](https://code.claude.com/docs/en/settings)

## Requirement coverage

| Requirement | Candidate evidence | Remaining gap |
|---|---|---|
| Selected Desktop/Code/native-peer binding | Independent selected-task mapping plus hook Code ID/socket projection | Exact native target join and freshness |
| Send attempt and native disposition | Native sender result | Distinguish delivered, held, refused, and unknown |
| Receiver delivery | Selected stored-session record | Native row shape, origin, correlation, flush |
| Correlated acknowledgment | `Stop` final text; conditional `MessageDisplay` | Accepted grammar and actual engine execution |
| Account before/after | Selected app account producer | Cache freshness and applied identity |
| Model before/after | Qualified selected getter; event history as corroboration | Missing baseline and fallback coverage |
| Applied permissions before/after | Mode, rules, applicable grants, pending changes | Complete selected-target producer inventory |
| Worktree/current cwd before/after | Selected app state and qualified cwd observations | Desktop moves and stale observations |

Hook `permission_mode` is an event-time field. It does not expose all rules, grants, or pending changes. Likewise, a cwd event records a transition; it is not an arbitrary-time worktree getter.

Initial qualification needs endpoint evidence before and after the experiment. It does not require proving that every field stayed constant throughout the interval. Whether later notifications require repeated full-state sampling is unresolved; this report does not impose it.

## Costs and observer effects

Hooks avoid modifying the Desktop archive but execute inside the receiver’s hook environment. Their command receives the event input before the logger can reject an unexpected session. Projection reduces retained exposure; it does not erase acquisition exposure.

A minimal logger should retain only approved fields, reject unrelated Code IDs and subagents, avoid transcript dereferencing and environment dumps, and emit no decisions, continuation requests, or display replacements. Its runtime still adds latency. Coexisting hooks, command failures, and reload behavior need observation in the selected engine.

The app bridge has greater preparation cost: candidate archive substitution, restart boundaries, and possible interruption. Its retained synthetic demonstrations support access and race-handling hypotheses, not live preservation claims. Restoring the original archive also changes the candidate on which qualification rests.

The stored reader has lower instrumentation cost but introduces lag and acquisition boundaries. Reading an entire retained session object before projection exposes more than an identifier-only listing. Queries should remain restricted to the independently bound selected session and directory.

Native delivery may start a receiver turn. Held messages may later be released, so an uncertain result must not trigger an automatic resend.

## Prototype disposition

No implementation occurred in this round. The existing observer and stored-reader demonstrations remain reusable source and synthetic evidence; I did not rerun them.

I revise the blanket conclusion that missing producers make every new prototype premature. A pure seam could settle real design questions:

```text
projectHookEvidence(expectedBinding, event, previousCoverage)
    -> projectedEvidence, coverageGaps
```

Injected acquisition and clock inputs could exercise optional fields, wrong-session rejection, subagent exclusion, duplicate or conflicting message events, and a missing baseline after restart. The seam should return field evidence and gaps, never infer overall delivery or successful acknowledgment.

That work could establish deterministic projection and coverage behavior using documented schemas. It would not need invented native-incoming rows. It also would not establish engine support, route identity, or freshness. Its useful decision is whether one projected record format can represent partial evidence without promoting absence into a negative result.

The existing reader remains the appropriate starting point for acquisition mechanics. Its receiver-delivery interpretation must await a real producer record.

## Smallest discriminating later checks

### First settle available source questions

Before touching a receiver, inspect a matched artifact for the actual selected engine. The highest-value questions are:

1. How the exported socket path relates to native discovery and `SendMessage` target resolution.
2. Where the relevant hooks are emitted and which settings sources feed that executor.
3. Which selected Desktop producers own applied account, model, grants, and pending changes.

The public SDK wrapper inspected here cannot answer engine-internal questions. No matching engine source was available in the named inputs.

### Least invasive no-send experiment

The first runtime experiment should use one purpose-made local Desktop Code task in a dedicated project, with an independently established Desktop/Code identity and recorded executor version.

After that Code identity exists, install a project-local **`Stop`-only** command logger. Preserve existing settings and hooks. The logger should project the expected Code ID, cwd, optional permission mode, socket path, and only the agreed fixture response text. It should exit successfully without control output. Record the broader hook-input acquisition exposure explicitly.

Then issue one agreed harmless setup prompt requesting a fixed response such as `observe-ready <nonce>`. If creating the Code session itself requires a setup turn, record that additional turn separately.

This no-send check can discriminate:

- Hook reload into an existing Desktop query.
- Actual `Stop` execution and available fields.
- Code ID/socket association for that event.
- Final-text availability relative to the selected stored transcript.
- Logger latency and interaction with existing hooks.

Remove the task-owned logger configuration and verify restoration. An interrupted turn or absent event is incomplete evidence, not automatically proof that hooks are unsupported.

This experiment cannot establish native delivery, consent, complete endpoint state, or preservation across a notification. It also cannot recover `SessionStart.model`. A fresh-session baseline check is a separate experiment if that producer is needed. Add `MessageDisplay` only if the accepted acknowledgment contract needs text that `Stop` cannot retain.

A later native-message experiment would require fresh peer/consent binding, the settled acknowledgment grammar, and endpoint before/after observations. Its findings should determine the smallest residual app bridge.

## Evidence and exposure record

The source baseline remains commit **`6fbddb3883e08476af9fffe1410863f0e89f0cd6`** in the designated checkout. All four frozen exchange digests matched: the three first-round reports and coordinator check. I inspected no sibling second-round work.

Additional local exposure was the named renderer chunk:

- `offline source extraction/index.chunk-COPWZCsC.js`
- SHA-256: `b22a9dc34684cef348f9c0e72abe88c433bbfc2d350d9a3e61faf7ae22858950`

The named `index.chunk-vRLpacfH.js` was absent; I did not search for a replacement.

Manager evidence remains `offline source extraction/manager-pristine.js`, SHA-256 `bd2144a3653bb843f4b75fe652124a4e478f273b5f6c2e10a2139fa3a9a3152f`. Relevant byte anchors include settings sources at 1,077,013, hook construction at 1,077,269, and executable selection at 1,285,961.

Additional public exposure comprised current official documentation, Context7 queries containing only public subjects, and the public SDK archive read in memory. The archive SHA-256 was `4550e830246026133fc1802a2208dd0f3a785cae1eec83f261d114c33d797771`. Public pages were checked on **2026-10-02** and remain mutable.

There were no file writes, test runs, private receiver reads, application launches, prompts, sends, configuration changes, or delegation. The next comparison decision is which missing producer facts to settle in source and which require the bounded no-send experiment.
