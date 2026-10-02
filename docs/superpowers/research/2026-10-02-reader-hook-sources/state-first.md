# Receiver runtime-state producers

**DONE_WITH_CONCERNS.** The approved sources identify useful query, event, and host-state producers, but they do not establish a complete before/after observation of the receiver’s authenticated account, actual model, applied permissions, worktree, and current cwd. Temporary app observation could expose existing query requests and host grant evaluators. It cannot supply missing engine semantics merely by transporting their results.

This report covers initial qualification and affected requalification. Ordinary notifications retain fresh exact-peer and purpose-consent checks; they do not require fresh full-state snapshots. No interval-wide invariant is added.

## Inputs and identity limits

Repository inputs were read through `git show` at `b8760030957fefa1bc9c21bd6052373674d1971d`, including the [reviewed comparison](https://github.com/nisavid/provingkit/blob/b8760030957fefa1bc9c21bd6052373674d1971d/docs/superpowers/research/2026-10-02-receiver-observation-comparison.md), its final lanes, method, controlling source corrections, review record, and earlier observer design.

The following legend makes the byte references below portable. Offsets are zero-based UTF-8 byte intervals, with the end excluded.

| Name | Source member | Verified SHA-256 |
| --- | --- | --- |
| Manager | Retained `manager-pristine.js`, corresponding to Desktop `.vite/build/index.chunk-B9SZqsi8.js` | `bd2144a3653bb843f4b75fe652124a4e478f273b5f6c2e10a2139fa3a9a3152f` |
| Common | `.vite/build/index.chunk-DuaKZOPP.js` | `f160a24940ee11cea6a788a9038e95c14fb150889977dcfa331fd9b07aba0c96` |
| Host | `.vite/build/index.chunk-CKt-cwRV.js` | `dad88ac66fe13f72d0225c49d48e124d238ff643ff96426c4a2020482621e62d` |
| Renderer API | `.vite/build/index.chunk-COPWZCsC.js` | `b22a9dc34684cef348f9c0e72abe88c433bbfc2d350d9a3e61faf7ae22858950` |
| SDK | Public SDK 0.3.284 `sdk.mjs` | `32d062c37b03e10870fbf839f54694545ee01bc0ec719e47078fbed76e30ef71` |

The retained Desktop identity is `@ant/desktop` 2.9939.4, packaged as `claude-desktop-extra` 2.9939.4-1. The [SDK archive](https://registry.npmjs.org/@anthropic-ai/claude-agent-sdk/-/claude-agent-sdk-0.3.284.tgz) identity is `4550e830246026133fc1802a2208dd0f3a785cae1eec83f261d114c33d797771`. Neither identity establishes the executable selected for an actual receiver query. No selected-engine control-handler artifact was among my frozen inputs.

## Access and sample binding

The strongest existing runtime access is the Desktop manager’s selected query. `liveQueryOf(sessionId)` returns its query; `readContextUsage` selects the session record and query, rejects absent/stopping processes, and reports unsupported or failed requests separately (Manager 1440600–1441600). Renderer `getContextUsage` and `getPermissionMode` forward to manager methods (Renderer API 48400–49980). These are app-context interfaces; the inspected source establishes no standalone attach endpoint.

SDK `request` creates a request ID, stores its handler on that query’s transport, and correlates the control response (SDK 1103860–1105440). This binds a reply to the captured query transport. It does not independently bind that query to the consented Desktop/native peer.

The manager’s `$` wrapper counts host requests while the query matches; it returns the original promise and does not reject a reply because identity changed during collection (Manager 531044–531450). A collector therefore needs its own before/after record, query, input-stream, Code-ID, and lifecycle checks. Each asynchronous field also needs its request/response interval. The existing wrappers provide no transactional full-state snapshot.

Host `get_session` projects manager fields including `model`, `cwd`, `worktreePath`, and conditionally `permissionMode` (Host 211620–213230). Its name does not make these fresh engine getters.

## Concrete producer findings

### Account

`spawnAccountOf` reads the identity/org retained against the input stream. `refreshOAuthTokenForSdk` uses that expected identity, checks fences before and after refresh, and reports refresh failures. Token rotation enqueues an environment update with a delivery predicate (Manager 467500–471200).

These paths establish spawn binding, refresh intent, and host submission conditions. They do not report which authenticated account the executor actually uses at an arbitrary endpoint.

SDK `accountInfo()` returns `(await this.initialization).account` (SDK 1109721–1109820). `initializationResult()` likewise returns the retained initialization promise (1105450–1105505). A new collector cannot promote either value into fresh authenticated-route evidence. `reinitialize()` issues another initialize operation, but the approved wrapper does not establish its account producer’s freshness or observer effects.

### Model

`getContextUsage({detail:"summary"})` is a concrete existing-query request. Desktop’s `readRunningModel` consumes its `model` in a version-gated SSH reattachment path, while `readContextUsage` offers the general manager path (Manager 1439364–1441600; SDK 1107265–1107360). Local support and the response’s model meaning remain unqualified.

The source clearly separates selection from confirmation. During a busy turn, `applyModelChange` commits the new selection before the `setModel` request settles. Idle changes retain `modelInFlight`; confirmation and failure paths handle later responses and query replacement (Manager 1433500–1436500). Consequently, saved `model` is insufficient.

Code init updates `modelConfirmed` (Manager 1521450–1522650), and `model_refusal_fallback` reports retry/revert/sticky behavior (1572400–1574300). These are event-derived facts, requiring an adequate baseline and coverage.

### Applied permissions

SDK `getSettings` and `listPermissionRules` send separate live control requests and return the engine response (SDK 1099837–1100130). Manager callers consume `applied` settings for effort/advisor; its permission-rule parser retains only `state.managedOnly` (Manager 1477750–1478700; Host 423590–423850). Full rule/grant interpretation needs the engine handler and qualified response contract.

Mode has several producers: Code init/status reports, manager selection, setter completion, and query-associated pending requests. `setPermissionMode` awaits the query operation before updating manager mode, but includes a bypass-rejection restart path (Manager 1409543–1413400). `setPermissionModeForAgent` can return `pending` while that operation continues (1290598–1292000). Equal manager values therefore do not eliminate pending changes.

`pushFlagPermissionScope` computes permission settings, awaits `applyFlagSettings`, and records completed deny, ask, and laptop-allow arrays only while the same query remains selected (Manager 1333100–1336850). These caches are useful completed-push evidence. They do **not** retain the full pushed allow array or an applied `additionalDirectories` array. Teardown clears them (1040250–1043400).

Host permissions also include:

- `sessionPermissionUpdates` and `alwaysAllowedReasons`, directly consulted by `handleToolPermission` (Manager 202245–204900).
- Browser mode/domains, supplied through `buildInternalServerOptions` and transformed by `BE` according to session mode, gates, and sandbox context (Manager 938500–942450; Host 522780–523400).
- Computer-use app grants and flag grants, exposed through `qC`/`JC` callbacks (Manager 940350–940850).

The last category has a material freshness distinction: Common exports `qC = Kqn` and `JC = Jqn`. These apply time-dependent expiry to dispatched-session grants (Common 3692500–3693350; export anchors 6712391 and 6578102). Raw stored grants can therefore differ from effective grants even without a new event.

`addDirectories` records the session update and starts an asynchronous push before returning (Manager 1429203–1430620). Observing that record is not evidence that the engine applied it.

### Worktree and current cwd

`applyHarnessWorktreeMove` clears `harnessCwd`, advances a generation, resolves a **registered worktree**, and stores its resolved path only for the current generation (Manager 508311–511400). Init cwd and parsed worktree enter/exit messages feed this path (1519250–1520700; 1542900–1543700). It is not a general current-cwd getter.

The manager separately carries `pendingCwdMove` and applies queued moves after busy work settles (491800–495500). Registered association, pending target, and current executor cwd must remain distinct.

## Requirement-to-producer table

| Requirement | Producer and access candidate | Timing, pending semantics, and remaining gap |
| --- | --- | --- |
| Authenticated running account | Spawn stream identity; initialization account; host refresh paths | Spawn/cache/refresh facts only. Fresh executor-bound authenticated identity remains missing. |
| Actual model | Captured query’s context summary; init/fallback reports; confirmed/pending model state | Need session model, in-flight request model, and next-effective model distinguished. Getter freshness and local support remain open. |
| Active permission mode | Code init/status; hook field where present; setter completion and in-flight state | Event time or manager completion. Need endpoint coverage and pending/restart interpretation. |
| Effective Code rules/workspace grants | `listPermissionRules`; applied settings response | Query-correlated request. Complete engine semantics, errors, and active/inactive interpretation remain unqualified. |
| Effective host grants | Broker caches, session updates, browser evaluator, computer-use evaluators | Sample applicable evaluators at collection time; retain expiry and contextual inputs. Inventory remains incomplete for a whole-permission claim. |
| Pending permission changes | Mode requests, flag sync, spawn pushes, MCP holds/dirty state, pending broker decisions | Distinct stores; no demonstrated aggregate pending-state producer. |
| Actual worktree | Registered worktree resolution plus Code events and selected association | Resolved association is partial evidence; asynchronous resolution may be pending. |
| Current cwd | Hook event-time cwd; engine getter still sought | Manager cwd/worktree fields cannot substitute for arbitrary endpoint cwd. |
| Exact receiver binding | Selected Desktop/Code lineage, captured query identity, fresh native discovery | Access and native-address join remain qualification dependencies. |

## Events and a cheaper additional lead

Official hooks supply Code `session_id` and event-time cwd; permission mode is absent on some events. `SessionStart.model` is optional. `PostModelSwitch` covers session-model changes, but explicitly excludes a fallback-chain model serving one turn. `CwdChanged` describes shell-driven main-conversation moves. `ConfigChange` omits server-managed refreshes; `DirectoryAdded` omits Workspace-tab additions. These channels therefore need a baseline and qualified coverage. Silence proves no unchanged-state claim. [Hook reference](https://code.claude.com/docs/en/hooks)

The documented status-line input adds current model, cwd, Code ID/version, and worktree fields. Its updates are event-driven, debounced, and cancellable; optional timed refresh exists. This is a named source lead for model/cwd/worktree, but I found no status-line invocation in Manager, and SDK exposes only its settings schema. Desktop/headless emission is unestablished. Assess that producer before selecting it; adding a logger would not prove its availability. [Status-line reference](https://code.claude.com/docs/en/statusline)

## Blockers, alternatives, and next checks

The first source blocker is the engine handler behind `get_status`, `get_settings`, `list_permission_rules`, and `get_context_usage`. The public client forwards those requests; it does not establish their producers. A public SDK-matched engine artifact would improve source understanding while remaining distinct from the actual selected executor.

The second blocker is permission completeness. Completed host pushes cover particular arrays. Effective browser/computer-use evaluators and pending mode/MCP operations supply additional facets. A complete inventory must follow their applicable consumers, transformations, expiry, and mutation paths; it must expose remaining gaps.

Temporary app observation is useful specifically for the captured query requests, completed-push records, and host evaluators unavailable through current external readers/hooks. Its retained procedure requires stopped-app archive exchange, candidate launch, restoration, and two restarts, with possible interruption and an unmeasured window. Transfer to ordinary Desktop needs an observer-effects argument, relevant source comparison, and sufficient unmodified-runtime evidence. Restored hashes establish restored bytes.

The smallest discriminating checks are:

1. Inspect a frozen engine artifact for getter handlers, model/fallback selection, hook emission, cwd changes, and status-line execution in SDK mode.
2. Establish selected-executor identity separately under later runtime authority.
3. Trace remaining applicable grant evaluators and pending mutation stores; determine whether a read-only aggregate exists.
4. Under a separately authorized disposable-fixture plan, collect explicit before/after requests, per-field intervals, and pending state on the same bound query. Do not manufacture endpoints by invoking setters, waking a query, or prompting.
5. If temporary instrumentation is selected, plan the ordinary-Desktop transfer evidence before installation.

Delivery and explicit correlated ACK remain separate receiver evidence. Unknown outcomes require observation-only reconciliation; held, refused, and unknown outcomes never cause automatic resend.

## Procedural handoff and exposure

Under `capturing-agent-procedures`, freeze this report and its source identities before exchange. Cross-examination should challenge account freshness, actual-model meaning, permission completeness, cwd coverage, and sample binding against concrete producer bytes. Admit new artifacts with explicit identities, revise material contradictions, and bind final review to the reconciled immutable report. The coordinator owns capture, tracker changes, and publication.

I used `research`, read approved static inputs, and retrieved public documentation through three generic Context7 commands and official-page reads. Context7 succeeded. Direct web opens for the TypeScript SDK and context-usage pages returned internal errors; SDK request claims above rely on the retained source instead.

I performed no edits, tests, vendor-module execution, private receiver reads, live actions, prompts, sends, installs, restarts, or delegation. This report supplies source facts and feasibility limits, not runtime qualification or a security-control judgment.