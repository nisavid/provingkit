# App-side candidate after cross-examination

**DONE_WITH_CONCERNS.** Retain the selected-query observer as a residual observation candidate, alongside the native MCP sender, selected metadata/session readers, and narrowly chosen receiver hooks. The exchange strengthens two cheaper leads: hooks can expose useful event-time evidence, and `LocalSessions.start` internally returns the Desktop task ID. It does not establish a complete observation combination or make app instrumentation necessary.

My first report remains unchanged as history. Its “eight-anchor minimum” needs correction: eight anchors form a candidate subset of the current ten-anchor prototype. They are not a proved minimum across possible designs.

## Critiques and dispositions

The existing-interface lane correctly separates externally callable SDK readers from Desktop-hosted tools and renderer IPC. Its corrected `LocalSessions.start` reading is confirmed: on successful completion, the conditional typed-text binding is a side effect, followed by returned `{sessionId:d}` through a JavaScript comma expression. Exceptions may reject the call. I independently checked the named source span; this correction supplies no external IPC access.

Its warning about identifier-only discovery is also necessary. Enumerating filenames exposes identifiers; opening JSON and then retaining a small projection still acquires the whole selected file. My discovery proposal needs that acquisition scope stated explicitly. A new filename remains a candidate until independently bound to normal fixture creation.

The hooks lane strengthens general Desktop-support evidence and offers `Stop.last_assistant_message` as a simpler ACK candidate than display reconstruction. It also identifies a useful join between hook Code identity and `CLAUDE_CODE_MESSAGING_SOCKET`. Those remain activation and binding hypotheses for the selected executor. An optional event field cannot provide a baseline before it fires, and assistant text cannot replace independent incoming-delivery evidence.

Its worktree row adds lease and pending-move checks beyond the supplied contract. I retain actual worktree association and current cwd; lease preservation is not an acceptance gate. Likewise, receipt-specific registration generations, writer fulfillment, transition epochs, and frozen same-process handoff should not become universal route requirements. They support the stronger acquisition claim that receipt design chose.

All three reports dismiss new prototypes too broadly. Missing runtime producer facts prevent meaningful simulation of their truth, but source-backed projection and endpoint scheduling remain testable design questions.

## Reachable components and coverage

The retained app bridge is reached through launch configuration, then private `bootstrap.json`, `arm.json`, and bounded sample files. Query getters are internal. Desktop host `get_session` and renderer `LocalSessions` remain app-context interfaces without an established standalone connection. The SDK’s selected-session reader is externally callable and reads stored records. Settings-defined commands are the proposed hook access path; their observation log would be a new interface.

The current app prototype captures record/query/input-stream identities, Code ID, generation, and getter references. It rejects changes during collection. Its generation hooks are useful for this design, but fewer insertion points might suffice if another source already provides equivalent lifecycle identity. That possibility has not been eliminated. See the [adapter selection](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/prototypes/desktop-observer-probe/desktop-adapter.mjs#L447) and [binding checks](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/prototypes/desktop-observer-probe/observer-probe.mjs#L733).

| Accepted observation | Best retained producer/access candidate | Meaning and remaining gap |
|---|---|---|
| Fresh exact peer and consent | Receiver-bound identity, hook socket-address lead, and fresh native discovery | Every send needs current exact-peer/purpose checks. Address-to-task mapping remains unqualified. |
| Delivery and explicit correlated ACK | Bound SDK/transcript record; `Stop` or selected assistant record for ACK | Actual native inbound attribution and ACK grammar remain unqualified. Stored silence proves no outcome. |
| Held, refused, unknown reconciliation | Chosen native admission producer plus positive receiver evidence | Held may release; refused drops. Neither authorizes resend. No observer invents missing state. |
| Account | Spawn-account record, refresh paths, initialization cache | Intended refresh identity is traceable; fresh authenticated executor route remains unobserved. |
| Model | Existing-query summary report; initialization/model-switch events | Selected model, last-response model, and event-time model have distinct meanings. Endpoint freshness remains unresolved. |
| Applied mode | Code mode events, setter completion, pending request state | Manager selection and event history are partial. No fresh arbitrary mode getter is established. |
| Rules, grants, pending changes | Query rules; selected host stores; newly traced completed-push caches | Coverage improves, but complete combined applied state and pending-operation inventory remain unproved. |
| Worktree/current cwd | Metadata association, manager worktree reports, hook event-time cwd | `harnessCwd` is resolved worktree state, not arbitrary current cwd. No complete endpoint acquisition is established. |

The [observer design’s producer inventory](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/specs/2026-09-29-desktop-runtime-observer-design.md#L157) remains the baseline. This report concerns factual configuration observations, without general security assurance.

## New bounded source findings

**Account refresh narrows intent but leaves applied-route freshness open.** `spawnAccountOf` reads identity retained by input stream. `refreshOAuthTokenForSdk` derives the expected account/org from the spawn identity and checks fences before and after refresh. Token-push paths enqueue an environment update with a delivery predicate. These establish intended account binding and submission conditions, not the receiver’s authenticated account at an arbitrary endpoint. Adding a refresh hook could witness host refresh activity; it would not close that gap by itself.

**Host permission evidence can improve without another hook.** `pushFlagPermissionScope` awaits `query.applyFlagSettings`, then, only while the same query remains selected, records `flagDenyRulesApplied`, `flagAskRulesApplied`, and `flagLaptopAllowRulesApplied`. It clears `flagScopeSyncPending` and releases held host MCP activity. Teardown clears those caches.

`syncFlagDenyRules` compares desired host rule arrays with the retained completed-push arrays. The current observer omits the latter and `hostMcpHeldForRules`. Projecting them could distinguish desired configuration from the manager’s last completed push. This is stronger host-side provenance, without proving the whole executor permission state. The arrays also cover specific host rule categories; they do not replace Code rules or every grant.

**`harnessCwd` has narrower semantics than its name suggests.** `applyHarnessWorktreeMove` increments a generation, clears the value, asynchronously resolves a registered worktree, and stores its resolved path. Code init and parsed enter/exit-worktree messages feed that path. Missing or unresolved `harnessCwd` therefore cannot mean an empty cwd, and even a newly resolved value is not a general cwd getter. Hook `cwd` supplies event-time evidence through a different producer.

**Mode setter completion is useful but insufficient.** The manager tracks query-associated in-flight requests, awaits `setPermissionMode`, and updates manager mode on completion. A rejection path can restart the query for a particular bypass transition. No blanket “manager mode equals current applied mode” inference follows. Identity checks and pending-state interpretation remain necessary.

These findings come from static named source spans, without app execution.

## Qualification sampling and operating lifecycle

The accepted qualification requires actual before/after endpoints. It does not require interval-wide invariants. The supplied evidence does not settle whether every later notification must repeat complete full-state samples or whether qualification plus a defined operating assurance method suffices. That decision belongs in the notification-interface contract. Fresh peer and consent checks remain required for every send.

One-shot app sampling combined with hooks and readers could support an initial qualification experiment if their producers cover every field and their acquisition times bracket the specified operation on the same receiver. The current prototype does not establish that fit: it permits three automatically scheduled samples within 30 seconds. Busy delivery or acknowledgment may fall outside that window, and sampled host fields are still incomplete. A fixed cadence cannot be assumed to identify the intended endpoints.

An ongoing service is conditional on the eventual operating lifecycle. If repeated full-state observations are required, the current one-shot manager guard and arm protocol need a repeated-collection design. If instrumentation is qualification-only, adding a permanent observer service may be unnecessary.

Temporary instrumentation still requires stopped-app archive exchange, candidate launch, stop, pristine restoration, and restored launch. It entails two restarts, potential interruption of active work, and an unmeasured total window. Restoration must respect intervening package changes and separately verify application/task behavior. The receipt’s 15-minute acquisition-admission ceiling applies only if that receipt procedure survives selection; it does not bound restoration.

Transfer to unmodified Desktop requires source analysis of observer effects, relevant matched candidate/restored behavior, and unmodified receiver evidence sufficient for the claimed route. A restored hash proves bytes. An instrumented snapshot cannot supply a later unavailable measurement. See [packaging and operating effects](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/prototypes/desktop-observer-probe/packaging-evidence.md#L95).

## Prototype disposition and proposed combination

Reuse the retained reader and observer demonstrations. I did not rerun their tests. Two narrowly scoped successor experiments could resolve real design uncertainty:

- **Host-push projection:** extend the public projection seam with the named desired/completed-push arrays and hold state. Synthetic cases can check missing caches, stale-query rejection, differing arrays, and partial coverage. The result must say “manager-recorded completed push,” without promoting it to complete applied permissions.
- **Finite endpoint collection:** compare explicit before/after phase requests with the current automatic cadence, reusing binding, deadlines, and envelope mechanics. Synthetic cases can check wrong nonce, duplicate phase, expired request, and query replacement. They test scheduling and identity handling, without simulating unknown account/cwd producers.

Neither requires a full archive rebuild to decide its source-interface shape. Implementation needs a selected contract and test-boundary decision; none was performed here.

The proposed component combination is native MCP submission; bounded Desktop-to-Code binding; selected SDK/transcript reads for positive receiver records; `Stop` and socket-address hook leads where qualified; and app projection only for residual fields inaccessible through those components. No component combination currently satisfies every field.

The smallest next checks are:

1. Resolve the external fixture-ID path and hook/metadata/native-address join.
2. Complete source inventory of applicable permission producers; decide whether the new host-push projection is worth implementing.
3. Set the qualification endpoints and operating sampling lifecycle.
4. Under separate fixture authority, perform no-send activation and residual-producer checks.
5. After complete observation planning and send authority, qualify actual native inbound evidence, ACK, outcomes, and idle/busy endpoints.
6. Obtain required unmodified-runtime evidence if instrumentation is temporary.

Maintenance remains behavior-specific: binding, getter semantics, host stores, event schemas, reader provenance, and export lifecycle receive graduated assessment. Changed build inputs require new candidate verification; unrelated changes need their affected checks.

## Sources and exposure changes

I consumed and digest-verified all three frozen first reports and the coordinator check from exchange r1. Their digests matched the manifest: app `d06e6c…fc8e4`, existing `d57a04…7209`, hooks `f84eae…53d`, and coordinator `e7d698…5091`. The shared repository base remains `6fbddb3883e08476af9fffe1410863f0e89f0cd6`.

New static inspection used the pinned manager, SHA-256 `bd2144a3653bb843f4b75fe652124a4e478f273b5f6c2e10a2139fa3a9a3152f`, with zero-based UTF-8 byte spans:

- Account keeper/refresh: 465700–471200; refresh caller: 886500–887400.
- Worktree resolution: 506700–511400; init input: 1519250–1520210; worktree event: 1542600–1543700.
- Permission teardown: 1040250–1043400; completed push/scope/comparators: 1332000–1336850; mode setter: 1409450–1413400. The inspected 1276550–1278460 branch concerns SSH and is not evidence of the selected local route.
- Corrected `LocalSessions.start`: `index.chunk-COPWZCsC.js`, bytes 27800–28640, SHA-256 `b22a9dc34684cef348f9c0e72abe88c433bbfc2d350d9a3e61faf7ae22858950`.

**Input log:** additional inputs were `coordinator-retained app r2 brief`, `dispatch/exchange-r1.json`, its four named frozen Markdown files, and the named offline manager/COPW members under `offline source extraction/`.

Public documentation findings in sibling reports are attributed to their 2026-10-02 retrievals; I made no new public request. I read no memory, private receiver data, settings, credentials, live process data, or other chats. I wrote no files and performed no tests, delegation, live operations, or external mutations. Under `capturing-agent-procedures`, the join should preserve these corrections and connect any selected method to its reviewed source and consumer invocation.
