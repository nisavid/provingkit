# Receiver hooks: first-round design and source findings

**DONE_WITH_CONCERNS. Hooks are a credible partial observation route without editing Desktop application files. They could supply explicit assistant acknowledgment, event-time cwd and permission mode, model transitions, and a useful native-address binding lead. They do not yet supply the complete accepted observation contract.**

I recommend retaining a composite candidate: the existing native MCP sender; explicitly bound metadata and transcript readers for receiver records; and narrowly configured command hooks for selected observations. The remaining producer gaps are incoming native-message evidence, complete applied permissions, current account route, and fresh endpoint sampling of an already running receiver. This report completes the bounded first investigation. It does not adopt hooks, qualify a route, or complete the later exchange and review.

## Increment and evidence boundary

The authorized outcome is a concrete source/design comparison for hooks against the unchanged notification contract. Supported inputs are the copied charter, the reviewed comparison at `6fbddb3883e08476af9fffe1410863f0e89f0cd6`, named offline source, and independently retrieved public primary sources.

Acceptance evidence here consists of traced source paths, verified source identities, explicit coverage limits, a prototype disposition, and discriminating checks for later authorization. No synthetic experiment, app execution, installation, hook activation, private receiver read, fixture creation, prompt, send, or restart occurred.

The [reviewed comparison](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/research/2026-10-01-observer-scope-review.md) and [method](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/research/2026-10-01-observer-scope-review/method.md) govern the carried evidence. The copied charter supplies the accepted scope; I did not independently read or verify current tracker state.

## Concrete architecture and reachable interfaces

The proposed route has four components:

1. The native MCP sender performs fresh discovery and submits the informational notification.
2. A selected metadata reader binds the Desktop task to its Code session and lineage.
3. Receiver command hooks export approved event projections to a private local observation log.
4. A standalone reader combines positive receiver records, explicit acknowledgment candidates, per-field observations, and unresolved gaps.

The externally configurable hook surface is settings-defined command execution. The command receives event input from the receiver. A standalone reader could consume the resulting local log; that log would be a new observer interface, not an existing Desktop getter.

Current Anthropic documentation expressly says hook events run in Desktop and that settings-defined hooks apply to Desktop sessions. This strengthens the seed’s general support hypothesis. It still does not identify the engine selected by the inspected package or demonstrate an event on the selected receiver. [Hooks reference](https://code.claude.com/docs/en/hooks), [Desktop shared configuration](https://code.claude.com/docs/en/desktop#shared-configuration).

The retained manager makes the source path concrete:

- `.vite/build/index.chunk-B9SZqsi8.js`, `buildStartSdkOptions`, byte **1071531**, constructs the main query options.
- Byte **1077013** supplies `settingSources: ["user", "project", "local"]`.
- Byte **1077269** supplies host SDK hooks through `permissionBroker.createBaseHooks`.
- `createBaseHooks`, byte **180806**, registers host callbacks, including `Stop`; its completion callback appears near byte **199154**.
- `OP`, byte **849947**, merges host hook arrays; calls near bytes **1079907–1080995** add lifecycle, verification, and activity callbacks.
- `applyFreshBinaryPath`, byte **1285961**, selects an executable and version identity. The Desktop package version and SDK version therefore do not establish the actual executor version.

These are internal registration and spawn paths. They are not externally callable selected-query endpoints. The inspected manager contains no literal `MessageDisplay`, `CwdChanged`, `PostModelSwitch`, or `ConfigChange`; that absence does not establish that settings-defined hooks are unsupported, because event production belongs to the selected Code engine.

The matching published SDK **0.3.284** declares those events. I verified its registry integrity and declaration digest. Declarations establish interface shape, not runtime production. [`@anthropic-ai/claude-agent-sdk` 0.3.284](https://registry.npmjs.org/@anthropic-ai/claude-agent-sdk/0.3.284).

Adding callbacks to Desktop’s existing `options.hooks` would require an app-side integration. Starting another SDK query with callbacks would observe another executor. Neither is the proposed settings-defined route.

## Requirement-to-producer assessment

All hook rows below require later authority for receiver configuration, approved event fields, output storage, and selected-fixture access.

| Required observation | Producer/interface | Binding, freshness, and meaning | Unsupported part and smallest discriminating check |
|---|---|---|---|
| Desktop task identity | Selected metadata; `getSessionFilePath`, byte **919665** | Filename uses Desktop task ID; contents can supply Code ID and lineage. Persisted mapping, not live query identity. | Obtain the exact selected path and compare its projected Code ID with a receiver hook event. |
| Code identity | Hook `session_id`; metadata mapping | Event reports its Code identity. Recheck against the consented Desktop task. | No Desktop task ID or manager/query generation in the declared hook input. Check lifecycle replacement on the fixture. |
| Native peer binding | Hook-side `CLAUDE_CODE_MESSAGING_SOCKET`; native discovery | Promising receiver-origin join between event identity and peer address. | Confirm availability in the selected engine and the relation between that address and the discovery target. |
| Incoming delivery | Selected transcript/session reader | Positive evidence only after the external native producer’s record is established. | No inspected hook contract supplies a correlated incoming-peer delivery event. Observe one scoped external delivery later. |
| Explicit acknowledgment | `Stop.last_assistant_message`; alternatively `MessageDisplay` | Receiver assistant text can contain an explicit correlation acknowledgment. | Qualify grammar and origin; reject quotation, echo, unrelated text, and incomplete capture. |
| Initial model | `SessionStart.model` | Optional initialization observation. | Missing model remains unknown; late activation supplies no startup replay. Check actual fixture payload. |
| Model changes | `PostModelSwitch` | Declared resolved before/after model and source. | Event history needs a bound initial value and qualified coverage. Compare a permitted fixture transition. |
| Permission mode | Optional hook `permission_mode` | Event-time Code mode, distinct from saved manager selection. | Not present on every event and not an arbitrary getter. Check which selected events actually include it. |
| Rules, grants, pending changes | Configuration and permission events plus existing readers | Individual events may provide diagnostics. | No complete applied snapshot; host grants and pending pushes remain uncovered. Identify residual producers before implementation. |
| Current account route | Existing query/account producers | Retained source distinguishes spawn/cache facts from later route state. | No hook account-route field established. A fresh executor-bound producer remains necessary. |
| Cwd | Hook `cwd`; `CwdChanged` | Invocation-time directory or declared directory transition. | No arbitrary endpoint sample; shell-change coverage does not establish all Desktop worktree moves. Compare selected executor and host observations. |
| Worktree | Selected metadata plus cwd evidence | Saved worktree association can contextualize a directory observation. | Cwd alone does not establish lease, worktree identity, or pending move. Check those separately. |
| Held/refused/unknown | Explicit route-specific outcome producer | Retain distinct observations and their later transitions. | Hook silence proves none of these states. Qualify the producer; retain unknown when absent. |

Schema references are the pinned SDK’s `BaseHookInput` (**L171**), `ConfigChangeHookInput` (**L364**), `CwdChangedHookInput` (**L640**), `HookEvent` (**L971**), `MessageDisplayHookInput` (**L1346**), `PostModelSwitchHookInput` (**L2559**), `SessionStartHookInput` (**L6398**), and `StopHookInput` (**L9437**). [Versioned declaration archive](https://registry.npmjs.org/@anthropic-ai/claude-agent-sdk/-/claude-agent-sdk-0.3.284.tgz).

The permissions and account conclusions preserve the [retained field-producer inventory](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/specs/2026-09-29-desktop-runtime-observer-design.md#field-producers-and-remaining-gaps). Configuration events do not turn that incomplete inventory into a complete observation.

## Acknowledgment, delivery, and freshness

I would investigate `Stop.last_assistant_message` before adding `MessageDisplay`. It offers one final-text candidate without reconstructing display batches. The retained manager already registers a `Stop` callback, which supports investigating the event path but does not prove every optional input field reaches a settings-defined command.

`MessageDisplay` remains useful when acknowledgment appears before the final response. Current SDK documentation describes one complete-text call per assistant message; the general hook reference distinguishes that from interactive display batches. Desktop’s streamed UI must not be assumed to imply terminal batching. [SDK hook coverage](https://code.claude.com/docs/en/agent-sdk/hooks#available-hooks).

The proposed reader would keep delivery and acknowledgment separate. An assistant assertion naming the correlation ID can support acknowledgment after provenance qualification; it cannot manufacture the independent incoming delivery record. A tool result, notification, idle transition, or pair-level reply flag cannot substitute for explicit acknowledgment.

For a local hook log, I propose recording collector identity, source/version identity, selected binding, event name, acquisition interval, and only approved event fields. Event-specific identifiers would retain their native meaning. A collector sequence would order acquisitions; it would not prove that the receiver emitted every possible event.

Activation on an existing session creates a particular problem: events describe moments at which they fire. Running the logger manually with fabricated JSON would not sample the receiver. If no suitable event occurs before submission, there is no hook-derived baseline. A last observed value remains last observed, even when unchanged in the log.

A missing event, collector restart, delayed write, incompatible field, or changed binding leaves dependent observations unknown. Before/after endpoint evidence remains the accepted claim; this proposal adds no interval-wide invariant requirement.

## Exact-task binding and bounded discovery

The messaging socket is a useful additional lead. Anthropic documents export of `CLAUDE_CODE_MESSAGING_SOCKET` to hooks, including before `SessionStart` when messaging starts enabled. The proposal would project that address only, excluding the messaging token and other environment values. This could help connect Code identity to native addressing, but neither address reuse nor the selected discovery-reference mapping has been qualified. [Inbox socket contract](https://code.claude.com/docs/en/cross-session-messaging#the-sessions-inbox-socket).

For a newly created disposable fixture, bounded identifier discovery could replace parts of the receipt machinery if separately accepted:

- Restrict enumeration to one explicitly authorized metadata directory.
- Retain entry names and necessary file identities; project candidate contents only as approved identifiers.
- Match Desktop `sessionId`, Code `cliSessionId`, and the independently observed creation identity.
- Compare the hook Code ID, dedicated project identity, and native-address evidence.
- Reject multiple matches, changed lineage, or missing provenance.

“Newest file” is insufficient. A Code ID is not required to construct a Desktop metadata filename; it is needed for the later Code/transcript join.

A dedicated project can narrow hook exposure during fixture acquisition. Installing a project hook for an existing task may also cause callbacks in other sessions using that project. A script’s ID filter limits retained output, but the process may receive unselected input before filtering. That exposure must be accounted for in a later scope proposal.

The [receipt design](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/research/2026-09-30-fixture-identity-acquisition-design.md) additionally witnesses registration, writer fulfillment, account-transition bookkeeping, and same-query admission. Identifier discovery does not reproduce those guarantees. It is a scope tradeoff with narrower claims, not a mechanically equivalent replacement.

## Configuration, interruption, and maintenance

Project-local settings are the smallest plausible configuration location for a dedicated fixture. Global hooks broaden exposure. Policy restrictions, disabled hooks, trust admission, and actual settings-source loading must be checked factually before activation; no configuration was inspected here.

Current settings documentation says most hook edits reload without restart. That offers a route avoiding the archive-exchange operation, but reload must be verified for the inspected executor. It supplies no missed startup event. I would not restart or resume an existing receiver merely to create a baseline. [Settings activation](https://code.claude.com/docs/en/settings#when-edits-take-effect).

An observation command should return successfully without context, decisions, display replacement, or environment changes. Its local writes, process creation, scheduling, and event latency would still be observation effects. `MessageDisplay` holds displayed text while its handler returns, making it a less attractive default when final acknowledgment suffices. Configuration changes also change the tested operating route.

Maintenance would cover settings scope, policy interaction, event schemas, Code/SDK compatibility, native-address binding, collector loss and retention, acknowledgment interpretation, and effects on host callbacks. Each dependency should receive graduated compatibility assessment. A changed engine is unassessed; an unchanged schema alone does not establish unchanged semantics.

## Prototype disposition and smallest later checks

**No new prototype is justified in this round.** I ran no tests and created no files.

The [retained reader prototype](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/prototypes/claude-receiver-reader.md) already exercises echoes, quotes, ordering, incomplete records, ambiguity, and unknown outcomes. The [runtime observer prototype](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/prototypes/desktop-runtime-observer/README.md) already exercises stale observations, binding changes, delays, and partial coverage. I read their reports; I did not reproduce their historical results.

A later public test seam could normalize the documented hook input into per-field evidence and correlate qualified assistant text. Synthetic inputs could meaningfully test optional fields, wrong identities, duplicated or incomplete display deltas, collector discontinuity, and unknown propagation. They could not establish Desktop activation, an incoming native-message producer, permission completeness, or current account route. A toy inbound parser would therefore answer the wrong uncertainty.

The smallest later checks are:

1. **No-send activation check:** on an authorized disposable receiver, identify the actual executor and observe selected lifecycle/Stop payloads, settings reload, callback coexistence, and collector latency.
2. **Binding check:** compare exact selected metadata, hook Code ID, native address, and fresh discovery. Stop on ambiguity.
3. **Producer check:** after separate send authority, observe one external native notification’s receiver record and explicit correlated acknowledgment. Establish persistence delay and distinguish submission from receipt.
4. **Residual-state check:** verify field producers before attempting the full preservation proof. Do not change account, model, permissions, or cwd simply to make coverage appear complete.
5. **Qualification:** only after producer gaps and authority are settled, perform the accepted idle/busy proof, unknown-send reconciliation, outcome distinctions, and endpoint observations. Busy continuity remains diagnostic.

## Procedure capture and frozen input log

Under `capturing-agent-procedures`, this report proposes a consumer method: load the reviewed source identities; verify selected binding and activation; acquire event evidence; retain missing producers explicitly; and qualify the composite route before invocation. The comparison join should carry unresolved producer requirements into the eventual maintained Rolecasting procedure. No installed convention or tracker dependency was changed.

**Exposure:** I read only this lane’s frozen brief; applicable supplied instructions; `research`, `context7-mcp`, and `capturing-agent-procedures`; immutable `CONTEXT.md`; the common synthesis, method, first reports, follow-ups, history trace, and native source delta; relevant retained observation/specification, fixture-design, and prototype-report sections; and the named pristine manager extract. Oversized output was reread in bounded portions. I inspected no sibling lane’s new work, memory, other chats, or private receiver data.

**Input locations:** `coordinator-retained hooks r1 brief`; `reviewed checkout at 6fbddb3883e08476af9fffe1410863f0e89f0cd6`; `offline source extraction/manager-pristine.js`; applicable skills beneath `installed skills/`.

**Identities:** manager SHA-256 `bd2144a3653bb843f4b75fe652124a4e478f273b5f6c2e10a2139fa3a9a3152f`, **1,596,495 bytes**. Public SDK tarball SHA-256 `4550e830246026133fc1802a2208dd0f3a785cae1eec83f261d114c33d797771`; `sdk.d.ts` SHA-256 `048ae2e6c796cc2aa3c423afaad59a08972cb48c271ffcc9847d910ff65f61b2`; registry SHA-512 integrity matched.

**Public retrieval:** on **2026-10-02**, Context7 resolved Claude Code and retrieved hook schemas and Desktop/settings support through `/websites/code_claude`. Official hooks, Desktop, messaging, settings, and SDK-hooks pages were then checked; the TypeScript web reference returned an internal error. The pinned npm archive was read in memory as data. External queries contained only public product questions, with no proprietary source or private identifiers.

The candidate remains available for the frozen exchange. The next decision is whether its partial coverage and operating cost improve the composite route enough to justify a separately scoped activation check.
