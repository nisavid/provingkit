# Endpoint-state observations for qualification

**DONE_WITH_CONCERNS.** This design defines the before/after record, its producer contracts, and a collection sequence for the selected running task. Existing sources can supply named applied model values and several permission, worktree, and cwd facets. They do not supply a complete query-bound account route, all effective permission inputs and pending changes, or cwd/worktree resolution provenance. Those fields need new owning producers; an access adapter alone cannot complete them.

The [approved qualification decision](https://github.com/nisavid/provingkit/issues/411#issuecomment-5972858593) controls this report. Model means configuration actually applied to the selected task at each sample, with observed fallbacks separate. Account means the account, organization, and authentication route in effect for that query at each sample. Per-attempt backend-model proof and server-attributed account proof are outside this claim. The record covers two endpoint samples, with individual observation intervals. It makes no atomicity, continuous-monitoring, or interval-wide claim.

I used `research` and `capturing-agent-procedures`. I read repository context, tracker policy, the collector contract and procedure, reconciled findings, retained reader-hook reports, and runtime-access reports through `git show` at `e971ae6fde6f4f4fa0b603e3a08bd0369b9481c6`. The [published evidence base](https://github.com/nisavid/provingkit/blob/e971ae6fde6f4f4fa0b603e3a08bd0369b9481c6/docs/superpowers/research/2026-10-03-receiver-collector-findings.md) is preparation evidence. The smaller [fixture-binding investigation](https://github.com/nisavid/provingkit/issues/410) remains independent. I read no parallel-lane findings or newer drafts and sent no substantive preliminary findings before this complete report was frozen.

## Source identities and anchor convention

I independently recomputed every retained source identity below. Sources were read as data, never executed or imported. All byte anchors are zero-based UTF-8 intervals into the exact named member, with the end excluded.

| Name | Retained member | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| Manager | `manager-pristine.js`, corresponding to Desktop `.vite/build/index.chunk-B9SZqsi8.js` | 1596495 | `bd2144a3653bb843f4b75fe652124a4e478f273b5f6c2e10a2139fa3a9a3152f` |
| Renderer | `.vite/build/index.chunk-COPWZCsC.js` | 74622 | `b22a9dc34684cef348f9c0e72abe88c433bbfc2d350d9a3e61faf7ae22858950` |
| Common | `.vite/build/index.chunk-DuaKZOPP.js` | 6751779 | `f160a24940ee11cea6a788a9038e95c14fb150889977dcfa331fd9b07aba0c96` |
| Host | `.vite/build/index.chunk-CKt-cwRV.js` | 648655 | `dad88ac66fe13f72d0225c49d48e124d238ff643ff96426c4a2020482621e62d` |
| SDK | Public stable `sdk.mjs` 0.3.284 | 1159746 | `32d062c37b03e10870fbf839f54694545ee01bc0ec719e47078fbed76e30ef71` |
| Engine | Decompressed public Code 2.1.284 RC artifact | 243059896 | `dee301c3e248c62137cc15aafc2781bd5316c66720dd890d72e0054a024ce7d9` |

The [retained runtime report](https://github.com/nisavid/provingkit/blob/e971ae6fde6f4f4fa0b603e3a08bd0369b9481c6/docs/superpowers/research/2026-10-03-receiver-collector-sources/runtime-first.md#claim-authority-and-frozen-inputs) records Desktop 2.9939.4, commit `a166d8a7c640e65ad825ebfb99d74ccbb9c8940d`, and its declared SDK wrapper `0.3.284-rc.20260927.t043816.sha16cbb4d`. The Engine target is commit `16cbb4ddeeb473f57fd8d5b713764903d7928e66`; the [public compressed artifact](https://downloads.claude.ai/claude-code-releases/rc/16cbb4ddeeb473f57fd8d5b713764903d7928e66/2.1.284/linux-x64/claude.zst) has the previously recorded digest `20b1b16df81e34abc68bef87c5a8433106f0cf4e84b2dd507e37bb7978cbd6f2`. I recomputed the decompressed digest, not the compressed digest. Stable SDK bytes are a separate client source identity.

These identities describe the assessed source target. They do not identify the executor actually running a selected task. Runtime admission must independently bind that executor and its compatibility to these producer semantics.

## Record and comparison semantics

Use one record with `schema`, `claim`, `sourceIdentities`, `actualExecutor`, `selection`, and `samples.before` / `samples.after`. Each sample contains `bindingBefore`, `observations`, `bindingAfter`, `coverage`, and `gaps`. This is a proposed interface, not an existing getter.

Every observation has this envelope:

```json
{
  "field": "model.appliedTask",
  "producer": {
    "owner": "engine",
    "operation": "get_settings",
    "sourceIdentity": "Engine",
    "semanticsVersion": "qualification-state-v1"
  },
  "binding": {
    "desktopTaskId": "<independently selected task>",
    "codeSessionId": "<current Code conversation>",
    "queryRef": "<opaque identity of captured query>",
    "streamRef": "<opaque identity of captured stream>",
    "contextRef": null,
    "requestId": "<control request correlation, when applicable>"
  },
  "interval": {
    "collectorStarted": "<time>",
    "collectorCompleted": "<time>",
    "producerObserved": null,
    "clock": "<clock identity and units>"
  },
  "status": "observed",
  "value": {},
  "coverage": {
    "scope": "named applied settings",
    "complete": false,
    "omitted": [],
    "gaps": ["active-context configuration not supplied by this getter"]
  }
}
```

The angle-bracket strings are schema placeholders, not collected values. An existing getter without a producer timestamp gets the request/reply interval and `producerObserved:null`. A newly proposed producer records its local capture interval and clock. Preserve wall-clock and monotonic timings separately when available; do not directly compare monotonic timestamps from different processes. Computer-use expiry needs the evaluator's actual wall-clock argument as well.

`status` is one of `observed`, `missing`, `unsupported`, `failed`, `timeout`, `over_limit`, or `binding_changed`. A missing value is null with a concrete reason. A producer that reports an authoritative empty collection can return `observed` with `[]`; an unavailable collection cannot. A failure may carry bounded error classification and the name of the failed operation, without retaining arbitrary credential, path, or prompt text.

Pending state is data, not an observation failure. Every change record has its owning query/context, category, phase, proposed value when available, currently applied value or its observation reference, and source sequence/epoch when available. Phases distinguish `desired`, `queued`, `written`, `awaiting_reply`, `held`, `awaiting_consent`, `applying`, `rejected`, and `unknown`. Existing sources do not provide all phases for every category. Do not invent them from a promise or boolean.

Retain producer order and exact rule spellings. Compare equal values only where producer meaning, scope, query binding, evaluator context, and coverage agree. An applied-state comparison and a pending-state comparison are separate results. Complete pending observations can show an unstable endpoint; unknown pending coverage prevents a complete result. A change of task/query/stream or an incompatible source version invalidates the combined sample even if field values match. Turn changes are reported and assessed against the selected endpoint claim; a turn ID is not a replacement for query identity.

## Requirement-to-field and access contract

“New” in this table means a producer proposal requiring implementation and review. It does not mean that the parallel lane has an available endpoint.

| Required field | Exact meaning and owning producer | Existing source API or state | Access, freshness, and acquisition |
| --- | --- | --- | --- |
| `selection`, `actualExecutor` | Independent UI/task selection and actual executor witness, followed by unique current-Code association | Fixture procedure; manager selected record/query/stream and lifecycle | Later scoped UI/metadata/executor authority. Source pin, title, PID, historical Code lineage, and request ID alone do not bind the selected task. Keep evidence intervals separate. |
| `account.appliedRoute` | Account UUID/principal, organization ID, provider, authentication mechanism/source, endpoint classification, query credential-binding epoch, and route-resolution state actually applied to this query | Manager `spawnAccountOf(record)`; cached SDK initialization account; Engine `Ie`, `Vc`, `ac`, `Mu`, `tq`, SDK auth/header composition | Existing outputs are supporting observations. New Engine route descriptor must follow actual query credential context and resolved client bindings. No tokens, headers, token fingerprints, credential files, or helper commands are output. Reading/refreshing them merely to form a sample is not passive observation. |
| `account.supporting`, `account.pending` | Spawn account/org, initialization metadata with original date, refresh/push/fence observations, desired versus accepted credential epoch, and unresolved principal mapping | Manager OAuth controller and per-stream token record; SDK `accountInfo()`; Engine local metadata | App and engine projections require selected-query access. Stored profile names/email are labeled as metadata. Host “pushed” state is submission evidence, not engine acceptance. New accepted-epoch producer is needed where no acknowledgment exists. |
| `model.appliedTask` | Engine-resolved task model plus applied effort, advisor, ultracode requested/available/applied, and relevant thinking configuration | Captured query `getSettings().applied`; current Engine state/options | Fresh control request supplies the named existing values. New projection supplies thinking configuration and active task options/overlays that the getter omits. Full `get_settings` acquires merged settings/source/error data before projection. |
| `model.contexts`, `model.selected`, `model.pending` | Applied active main-loop configuration and any applicable contextual overrides; app selection/confirmation and pending model/effort requests separately | Engine model/permission layers; app model sequences, confirmation and `modelInFlight`; query context summary | The context summary is a resolved projection, not an active-attempt inspection. New active-context registry/projection is required where references are not already retained. Report no active context only from its owning registry. |
| `model.observedFallbacks` | Existing fallback events/retained fallback state that were actually available, with event identity, model pair, time, and coverage | `model_fallback`, app refusal/fallback state; internal `query_model_change` | Preserve observed records and gaps. Do not start a listener retrospectively and claim complete history. No fallback event does not mean no fallback occurred. No per-attempt backend proof is required. |
| `permissions.engine` | Raw active mode; active/inactive rules with source/behavior/spelling; raw rule stores/filtered or stripped entries; applied directories, original cwd, runtime flags, and contextual overlays | `listPermissionRules().state`; current `toolPermissionContext`; Engine `pe` composition | Rules getter covers its documented projection only. New Engine permission projection captures base state and applicable active contexts, with modes before/after rewrites. It does not invoke a tool, hook, classifier, or permission request. |
| `permissions.desktop` | Effective browser/computer-use grants and applicable broker policy inputs, grant expiry, contextual restrictions, and consent state | Browser `BE`; `Kqn`/`Jqn`; manager internal-server callbacks; permission broker stores and policy gates | App-only selected-session projections. Capture evaluator arguments/time and applied policy versions. Do not call the broker's permission handler or lock/consent mutators to simulate every decision. Raw grants and effective grants remain separate. |
| `permissions.runtime` | Applied sandbox/filesystem/network/credential policy descriptors, tool availability/narrowing, MCP/connector policy, trust and host-origin restrictions relevant to the selected query | Engine sandbox runtime state and wrapper composition; Engine permission context; manager backend/MCP/policy state | New owner projections are required. Do not export credential values or full server configs. Applicability and coverage of imported policy owners remain explicit. Configuration intent is not runtime application. |
| `permissions.pending` | All applicable unresolved changes and decisions, including out-of-turn entries, per-owner queues, and desired/written/accepted transitions | Manager mode/chip/bypass/flag/MCP/cwd stores; broker maps; Engine pending-request store and apply lanes | New joined projection over independently sampled owners. Bounded entry summaries exclude raw prompts/tool inputs. A single `hasPendingFor` boolean cannot establish an empty aggregate. |
| `location.registeredWorktree` | Registered association returned by worktree ownership, its resolution generation/result/error, and the associated task | Manager `harnessCwd`/`harnessCwdGen`, `worktreePath`/`worktreeLazy`; worktree resolver | Cached host fields are useful facets. New resolution-status projection records existing resolution outcomes. Reading a cache must not silently invoke resolution, filesystem checks, watchers, or adoption. |
| `location.currentCwd` | Current query execution cwd with scope, whether the read succeeded or fell back, original cwd, and bounded failure provenance | Engine `CWt` / `oe`; status rows; Stop event cwd | New Engine projection returns the raw read and explicit fallback classification within the selected engine context. Status/Stop are separate display/event observations; they cannot supply missing fallback provenance. |
| `location.pending` | Requested target/canonical path, trust/applying state, and source generation, distinct from applied cwd/worktree | Manager `pendingCwdMove`; worktree resolution generation | Selected-session projection preserves pending fields and rejects stale generations. A pending target is not current cwd. Absent `harnessCwd` alone cannot distinguish no association, resolution pending, failed read, or cleared association. |

## Account route: follow actual client selection

The approved account claim can use an authoritative local producer; it need not add a server identity lookup. The existing account display is still insufficient. Engine `o_e` builds metadata from local credential/configuration state, and SDK `accountInfo()` reads the retained initialization promise. Manager `spawnAccountOf` uses identity/org retained against the input stream. These three facts can disagree without any one proving the endpoint's actual route. [Engine `[200803900,200805150)`; SDK `[1109700,1109840)`; Manager `[467500,471200)`.]

The route has a concrete consumer chain. Engine `Ie()` selects the provider, while `Vc(model)` can choose Mantle for a model even when the base provider is Bedrock. Engine `tq` consumes the model, query/agent context, prompt identity, permission context, and credentials, resolves the provider branch, and constructs its client. First-party branches distinguish an explicit/API-helper key, profile provider, OAuth, and authorization-header paths. Gateway, AWS, Azure, and Google branches have different provider-resolution inputs. [Engine `[198737300,198740000)`, `[203886700,203896950)`, `[200754600,200755980)`, `[200758000,200759450)`.]

Construction alone is not the final authentication composition. The embedded API SDK's `authHeaders` can use an asynchronously resolved provider/token cache. `buildHeaders` then merges generated auth, default headers, body headers, and request headers; `prepareRequest` adds provider headers where absent. Default/request overrides can therefore matter. An account producer must preserve the effective selected binding and override provenance, not copy `ac().source` into an “actual route” field. [Engine `[200131300,200133850)`, `[200134652,200135240)`, `[200140524,200142150)`.]

**Proposed owning producer:** the Engine maintains a non-secret descriptor when query credential bindings and route/client bindings are ordinarily applied. Its endpoint getter reads those descriptors and current binding/epoch state without calling `tq`, a credential provider, a refresh helper, an API, or a client constructor. Descriptors distinguish query-applied route configuration from active client bindings and last-observed client bindings. Active bindings include context identity, provider branch, effective endpoint class, auth mechanism, override source, principal/org provenance, and resolution/pending state. No active client is a valid registry result; it does not freshen a last-observed route.

A credential epoch is an opaque locally assigned binding version, never a hash of a token. Token rotation preserving account/org advances the credential epoch without being labeled an account change. Host enqueue, delivery eligibility, engine receipt, and accepted application are separate observations. Manager `pushCcdTokenToSession` records a push with a delivery predicate; the inspected source supplies no aggregate engine acceptance witness. [Manager `[469850,471200)`.]

Principal/org must come from the owner of the selected credential binding and remain tied to it. A generic API key, arbitrary Authorization override, or untraced cloud provider cannot obtain an account UUID from its source label. Where the binding has no trustworthy principal/org metadata, return `missing` with that named gap. The later design may add a bounded local principal-binding producer or obtain a separately approved authoritative association; this report does not select a credential lookup, decode secrets, or make a security-property judgment.

Coverage must enumerate the actual route families and override paths assessed for the selected executor. The source shows several families, but I did not close the imported AWS/Azure/Google provider implementations or their principal mapping. Return `unsupported` or incomplete coverage for an applicable unassessed route. This is a concrete producer requirement, not a renewed requirement for server-attributed proof or observation of every inference attempt.

## Applied model configuration and observed fallback

The existing `get_settings` handler returns `applied.model = st()`, effort, advisor, ultracode, requested ultracode, and availability. `st()` resolves current explicit/configured selection and defaults. This supplies useful applied task configuration under the selected claim. It does not inspect an individual inference attempt. `getContextUsage({detail:"summary"})` uses the configured model and permission-aware context resolution; plan mode may change the returned model. Keep that value as `contextResolvedModel`. [Engine `[221225050,221226950)`, `[200476500,200478230)`, `[200484400,200485700)`, `[221137000,221140500)`.]

The active-context gap is concrete. Engine permission layers can override model, effort, thinking budget, mode, and working directory. `C`/`Kf`, `zg`, and `Y$e` resolve model/effort/thinking from a tool-use context, while `wCe` appends layers and can replace context options. Fork construction can add its own avoid-prompts layer and different options. A session-level getter cannot establish that every active context has the same applied configuration. [Engine `[201215600,201218850)`, `[206953000,206955400)`.]

**Proposed owning producer:** an Engine endpoint projection returns the applied session configuration plus bounded active main-task/context descriptors using the same context resolvers and captured inputs. It identifies context role and parent and records applicability to the selected ordinary task. If the Engine has no enumerating registry for active contexts, that registry is a new producer requirement; walking messages or guessing context identities is insufficient. Subagents/served calls remain separate contexts. This does not add a per-attempt proof requirement.

Preserve app `model`, confirmation, change/record sequences, pending target, and query association separately. Busy changes commit the selected app value before `setModel` settles; idle changes retain `modelInFlight`. [Manager `[1433107,1436500)`, `[1521450,1522650)`.]

Existing fallback branches can alter query options and emit `query_model_change` plus `model_fallback`; the headless path drops the former and forwards the latter, as traced in the [Engine report](https://github.com/nisavid/provingkit/blob/e971ae6fde6f4f4fa0b603e3a08bd0369b9481c6/docs/superpowers/research/2026-10-02-reader-hook-sources/state-engine.md#hooks-fallback-differences-and-statusline). I rechecked the options/event branch at Engine `[213024300,213027950)`. Record available fallback facts separately with their coverage. Do not classify the model getter as incomplete merely because it lacks every backend attempt; its actual gap is unreported applicable task/context configuration.

## Complete permission state needs composition, runtime owners, and pending owners

A permission record represents applied policy inputs and their contextual composition. It does not claim to enumerate the allow/deny outcome of every possible future tool/input pair.

The existing rules wire builder preserves exact represented rule strings, source, behavior, editability, inactive managed-only rules, directories, and original cwd. Its allow helper filters by mode, confinement, and tool/source gates. The raw stores and filtered/stripped entries remain additional state. [Engine `[231927050,231928958)`, `[201860380,201862030)`.]

New inspection identifies inputs that the rules getter omits. Startup permission context includes bypass availability, auto/classifier availability, browser classifier flags, restricted/built-in tool state, remote mode, MCP mode overrides, and optional block-reads-outside-directories. Context `pe` composes allowed/disallowed tools, shell clamps, avoid-prompts, sandbox-auto-allow suspension, permission-mode and working-directory layers. It can strip dangerous rules for poll-event delivery, reuse a captured request mode, rewrite prompt-shell auto mode, and rewrite remote-execution modes while removing the local read-block flag. Preserve base context, layers, derived context, and rewrite reason; reporting only base `mode` loses actual applicable semantics. [Engine `[212249900,212252300)`, `[201213000,201218850)`.]

Sandbox state is another owner. The runtime wrapper consumes filesystem, network, credential masks/denies, safe Git directories, PTY and command options; command-level overrides can differ from stored base state. The configuration builder can add protected paths, filter disabled setting sources, and handle block-read policy differently under relaxed filesystem policy. These are observations of source composition, not findings about enforcement strength. [Engine `[202742400,202748000)`, `[202803800,202807900)`.]

**Proposed Engine permission producer:** capture the current base permission context, rule-selection inputs and outputs, applied directory/trust state, applicable active context layers/rewrites, tool availability/narrowing, and applied sandbox descriptors from their current owning state. Include command/context override descriptors for active contexts, or an explicit coverage gap if their registry is absent. Snapshot already-applied sandbox values; do not re-run glob expansion, filesystem discovery, initialization, or command wrapping simply to observe them. Credential policy descriptors contain names/categories and masked/denied paths only within the approved private scope, with no values. Settings-source intent and runtime-applied descriptors remain separate.

Desktop grants add different semantics:

- Browser `BE` depends on surface, sandbox VM status, mode, app-origin choices, stored browser mode, and gates. Return those inputs and the effective mode/domain grant separately. [Host `[522450,523650)`; Manager `[938500,940350)`.]
- Computer-use `Kqn`/`Jqn` apply time-dependent expiry for dispatched sessions. Return raw app/flag grants, grant timestamps, dispatched-session classification, evaluated expiry policy, exact evaluation time, and effective results. App/flag grants can expire between the two samples with no state-change event. Lock ownership and takeover consent are distinct contextual inputs; merely querying effective grants does not capture them. [Common `[3692300,3693500)`; Manager `[940350,942700)`.]
- The permission broker consumes session updates and cached reasons with tool/input/origin conditions. It also uses workflow/trust gates, laptop-MCP/off-host/SSH grants, scheduled-run approvals, remote-dispatch restrictions, and special consent stores. Its constructor holds spawn, sink, archive, title, delete, mode, terminal, connector-switch, and PR-binding consent state. These stores are additional families to project when applicable; they are not all represented in `sessionPermissionUpdates`. [Manager `[131700,133200)`, `[202245,210100)`.]
- Workspace-folder policy can use backend-specific roots, generation/cached results, policy-valid additional directories, and plugin roots. The remote evaluator can resolve and cache roots. Sample applied descriptors/cache provenance without invoking that potentially resolving evaluator. [Manager `[202245,202850)`.]

**Proposed Desktop permission producer:** selected-session projections from broker, browser, computer-use/lock, scheduled-task, connector/MCP, workspace-policy, and special-consent owners. It returns policy applicability, current stored inputs, already-derived state, evaluator outputs only for the declared non-mutating evaluators, and the contexts needed to interpret them. Do not call `handleToolPermission`: it can create prompts, timers, approvals, telemetry, and state changes. Do not execute lock acquisition, collision consumption, consent renewal, sync, warm, or flush methods.

The inspected imported consent/scheduled/connector/lock policies are not all closed by the retained text examined here. Their projection contracts need source follow-up and coverage entries. They cannot be declared irrelevant because the task currently has no visible prompt.

### Pending changes are a separate aggregate

Each owner supplies a selected-query projection, with explicit applicability and truncation. The join records each owner's interval; it does not await or force settlement.

| Pending family | Required facts and source |
| --- | --- |
| Model/configuration | Selected/confirmed/active values; sequence; pending target; query association; effort/thinking requests where present. Manager `[1433107,1436500)`; active Engine contexts above. |
| Mode/chip/bypass | `permissionModeRequestsInFlight`, `permissionModeUserSet`, epoch, chip requests, restoring/deferred bypass state, applicable pending target if retained. Agent setter may return `pending`; bypass rejection can replace the query. Manager `[1290598,1292000)`, `[1409543,1413400)`. |
| Rule/directory application | Desired update, apply-lane occupancy, written/accepted epoch where supplied, flag-sync pending, completed deny/ask/laptop-allow caches. Directory addition saves before asynchronous push; completed caches omit full allow/directories. Manager `[1429203,1430700)`, `[1333100,1336900)`. |
| MCP/connector/trust | Desired versus accepted server keys; dirty/held/spawn-push/unanswered/adoption/rules-lock state; pending MCP verbs; applicability of remote/SSH paths; Engine serialized apply lanes and pending reconnect/exchange state. Manager `[1274000,1281600)`; Engine `[221137000,221140500)`. |
| Broker decisions | Every selected-session pending permission entry, including `outOfTurn`, agent/context/request IDs and request time; separate side-person waits and special-consent operations. `hasPendingFor` excludes out-of-turn entries. Manager `[136100,136950)`, `[204850,210100)`, `[938500,942700)`. |
| Engine decisions/hooks/dialogs | The Engine transport's `pendingRequests` is distinct from the Desktop broker. Existing `getPendingPermissionRequests` and `getPendingUserDialogRequests` filter its request store; generic hook requests and background/published prompt distinctions remain additional categories. Project summaries directly rather than exporting complete request payloads. Engine `[220374464,220375480)`; reinit use `[221253740,221254650)`. |
| Cwd/worktree | Pending target/canonical/trust/applying state and registered-resolution generation/result. Manager `[491800,495600)`, `[508311,511700)`. |

An Engine aggregate needs explicit state for queued/running settings and MCP apply lanes; promise-chain variable `ls` alone does not supply proposed values or successful application. Some transitions require new small status records at the existing owner. Similarly, an absent app counter cannot prove no pending Engine operation. Missing enumeration remains a coverage gap, not zero.

## Registered worktree and current cwd

Manager `applyHarnessWorktreeMove` clears `harnessCwd`, advances `harnessCwdGen`, resolves a registered worktree, and applies the result only for the current generation. It can perform filesystem checks, save/emit, adoption, and watcher synchronization. Errors are logged without a durable error-status field in the inspected path. A getter must not invoke this mutator to “refresh” the sample. [Manager `[508311,511700)`.]

**Proposed worktree producer:** record `resolutionState` (`not_started`, `pending`, `resolved`, `none`, or `failed`), generation, request/result times, input association, returned registered path/identity, and bounded failure classification in the existing resolution owner. Include saved `worktreePath`, lazy-worktree association, base/origin cwd, and pending move as separately named fields. A previous successful resolution remains dated; the source follow-up must decide what endpoint freshness the worktree owner can attest without new filesystem activity.

Engine `CWt()` reads AsyncLocalStorage cwd when present, otherwise global cwd. `oe()` catches failure and returns original cwd. Current status and Stop use the latter value without explaining whether it was a successful read or fallback. [Engine `[198480300,198481700)`; retained [Engine report](https://github.com/nisavid/provingkit/blob/e971ae6fde6f4f4fa0b603e3a08bd0369b9481c6/docs/superpowers/research/2026-10-02-reader-hook-sources/state-engine.md#status-is-a-live-display-projection).]

**Proposed cwd producer:** capture `CWt` in the selected main-query/context scope; on failure retain the original cwd plus `readState:"fallback"` and bounded reason. Return `scope:"async_context"` or `"global"`, original cwd, and the main-query/context binding. A control handler's own async scope may differ from an active nested context: expose active context cwd through its owner or mark coverage missing. Do not treat the control handler's global cwd as every active context's cwd. No `chdir`, trust request, or worktree resolution is performed.

## Collection sequence and bounded integration

1. Load the approved decision, this report, the source identities, and the reviewed fixture procedure. Bind the actual selected executor separately. Admission must assess source/executor compatibility; matching version text is insufficient.
2. Use an independent selected-task witness and current Code association. If the smaller fixture supplies that association later, consume its reviewed evidence and individual intervals. Keep Desktop task, Code conversation, native endpoint, executor, and turn/prompt identities distinct.
3. Through the separately chosen access path, capture the selected in-memory record, query and stream references, current Code ID, backend, lifecycle/start-stop markers, and available prompt/turn epochs. Assign bounded opaque reference identities. A selected-record read is preferable to a lookup that loads other sessions.
4. Acquire Engine endpoint descriptors and existing selected-query control replies, and selected-session Desktop owner projections, without setters, reinitialize, creating/resuming a query, prompting, or native inbox input. Group them under one sample label while preserving every producer interval. Engine pending projection distinguishes these observation requests from preexisting task operations; their induced request accounting is recorded.
5. Recheck the selected record/query/stream/Code identity and relevant lifecycle around each asynchronous result or declared group. Manager's request-accounting wrapper returns the original promise and does not reject a reply merely because its query was replaced. Keep an old reply as an observation of the old query, with `binding_changed` for the intended sample. [Manager `[531000,531700)`; SDK `[1103860,1105550)`.]
6. Collect the two samples at the approved before/after boundaries. Do not wait for pending operations to finish merely to make a sample look stable. A late result belongs to its actual request/reply interval, not an invented instant.
7. Compare bound, covered fields and pending state independently. Report `same`, `changed`, or `unknown` per facet, with source/scope incompatibility explicit. Overall complete qualification evidence requires no uncovered required facet. Equal endpoint samples establish equality only at their stated observation boundaries.
8. Retain only the reviewed bounded output and acquisition metadata; record missing/failed/overflow observations. Do not retry automatically, turn on ongoing monitoring, or perform additional inference to fill gaps.

The proposed output comprises identity/provenance, the account/model/permission/location objects above, bounded pending/fallback summaries, field coverage, and gaps. It excludes conversation text, tool inputs, credential/header values, full MCP configs, and unrestricted environment dumps. These are proposed output choices, not a certification that the whole acquisition protects private data.

For a later implementation proposal, bind limits per producer before use: sample output bytes, field/string bytes, rule/directory/context/grant/pending counts, request duration, and retained event range. Overflow returns `over_limit` with incomplete coverage; truncation never becomes a complete list. Existing getters may acquire full settings/source/error/context replies before projection, so output bounds do not bound those upstream reads. New projections must disclose their actual input reads and allocations. Unsupported requests have no mutating fallback.

The access lane must show which exact existing interfaces reach these owning producers on the selected query. SDK getters are requests on an already owned query. `accountInfo()` and initialization are cached. Reinitialize may change hooks and redeliver requests. Native inbox input is not a demonstrated control transport. The standing [runtime access report](https://github.com/nisavid/provingkit/blob/e971ae6fde6f4f4fa0b603e3a08bd0369b9481c6/docs/superpowers/research/2026-10-03-receiver-collector-sources/runtime-first.md#which-access-an-external-process-actually-has) owns that distinction. This report selects no transport or app intervention.

## Honest completeness result

| Required facet | Existing producer coverage | New producer/access remaining | Result for this source increment |
| --- | --- | --- | --- |
| Actual account/org/auth route | Spawn-bound identity, local metadata, concrete provider/client/auth composition | Query-applied route and accepted credential epoch; principal/org binding; active/last route distinction; imported-provider coverage; selected-query access | Concrete descriptor design; incomplete existing coverage |
| Applied model configuration | Named `get_settings.applied` values; context-resolved model; app pending/confirmation; observed fallback paths | Applicable active-context/option/thinking projection and registry coverage; selected-query access | Existing values support part of the clarified claim; remaining configuration gaps explicit |
| Raw mode and rules/directories | Rules wire projection; event/init/host mode facets | Fresh raw context/mode projection, filtered/stripped state, overlays and rewrite provenance | Incomplete |
| Desktop grants/permissions | Browser/CU evaluators; broker state and traced contextual consumers | Selected-owner projections; imported consent/lock/scheduled/connector policy closure | Incomplete |
| Runtime permission inputs | Concrete Engine context and sandbox composition | Applied base/active-context descriptors; trusted input/source versions; untraced applicable owners | Incomplete |
| All pending changes/decisions | Named app stores; Engine pending-request filters and apply lanes | Full selected-owner enumeration; queued/written/accepted status where absent; out-of-turn/background inclusion | Incomplete |
| Registered worktree/current cwd | Registered association machinery; current-cwd helper; pending move | Resolution outcome/freshness provenance and failure state; raw cwd fallback/context provenance | Incomplete |
| Actual task/query/executor binding | Defined prospective fixture join and in-app references | Independent live witness, actual executor, query/lifecycle checks under later authority | No live evidence supplied |
| Atomicity or interval invariants | Separate getters/projections | Outside selected claim | No claim |
| Every backend model/authenticated server attempt | Some fallback/display metadata | Outside selected claim | No claim |

Completeness is a producer/interface requirement, not the presence of every schema key. A new adapter emitting nulls and gap labels remains incomplete. There is no complete existing aggregate in the inspected routes; the concrete design identifies where new state ownership is necessary.

## Costs, next experiments, and procedure capture

Existing query reads allocate request handlers, write control traffic, and can affect host request counters/scheduling/logging. Settings reads can await policy promises. Context summary reads engine context and computes estimates; its model resolver can emit a once-per-warning message through `Xf`. Account/client constructors and credential resolvers can refresh/read/run helpers, so they are unsuitable observation substitutes. Worktree resolution and broker permission handling have concrete operating effects described above. These costs must appear in the access proposal.

New owner descriptors require source changes, schema/coverage maintenance across Desktop/Engine versions, and review of acquisition and output. Active-context/route/apply-lane registries may retain state that current getters do not retain, introducing memory and lifecycle work. Engine producers are outside the Desktop adapter's ownership: exposing the app's query object does not install them. Implementation, load/restart/interruption/restoration, maintenance, ordinary-runtime transfer, and total duration remain for the access lane and later operator choice.

The smallest next source experiment is to close the producer proposal before choosing an access mechanism: trace actual main-query/active-context holders and their lifetimes, account principal-binding owners and effective header/provider overrides, the sandbox applied-state holder, and the applicable consent/lock/scheduled/connector imports. Produce a source-to-projection coverage manifest for the selected executor family, with each unsupported path named. This requires an explicit increment if additional source artifacts beyond the retained allowlist are needed.

The smallest later live experiment is a separately reviewed, non-prompting sample on an independently bound disposable selected query: existing `get_settings`, `list_permission_rules`, and summary support/shape plus selected-session projections, with identity/lifecycle checks and individual intervals. It can establish support, correlation, and footprint for existing fields. It cannot demonstrate unimplemented account, permission, cwd, or resolution producers. New producer behavior needs a later frozen candidate and reviewed experiment; no tests at those new seams were created here.

Security/control acceptance remains separate. The later reviewer needs the exact acquired private fields, sink/read access, principal-binding authority, error/overflow paths, lifecycle and cancellation effects, retention, intervention bytes/load/removal plan, and the concrete intended observer audience. Questions about authenticated principal trust, hostile processes, containment, private-data protection, and authorization enforcement require appropriately routed security review; this report certifies none of them.

Under `capturing-agent-procedures`, the coordinator captures these exact bytes/digest, exchanges the two frozen first reports, reconciles field coverage and observation effects, and obtains independent review on the final immutable design. Dependent qualification preparation loads that published revision, approved decision, coverage manifest, and collector procedure; records the actual entry bindings and source/executor revisions; verifies the claimed endpoint observations; and returns corrections to the owning report/producers. The immediate discoverability proposal is a repo-carried endpoint-state design under `docs/superpowers/research/` with invocation pointers from the qualification and preparation tickets. Installed skill changes and broader promotion remain unselected.

The next choice is whether to implement the missing owning producers for the selected executor family and then expose them through an existing interface or separately reviewed diagnostic access. If that work is not selected, retain partial endpoint observations and their precise gaps; they do not complete the accepted qualification claim.

I performed source reads and hashing only. I made no edits or Git/tracker mutations, executed no vendor code, read no private receiver/profile/process/environment/credential state, used no UI or live endpoints, and performed no hook, installation, task, prompt, restart, notification, or subdelegation activity.
