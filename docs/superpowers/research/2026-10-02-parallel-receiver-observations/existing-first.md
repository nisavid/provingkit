# Existing-interface receiver observations: first-round report

**DONE_WITH_CONCERNS.** A standalone reader using one bound Desktop metadata file and a documented SDK session read is a concrete candidate for positive delivery and acknowledgment evidence. Existing host and renderer getters do not yet provide an externally reachable runtime observer, and their projections do not cover the complete applied-state contract. UI observations can corroborate selected evidence, but their exact-task binding and Linux access path remain unqualified.

I recommend retaining this candidate for comparison without implementing another parser or treating it as a complete notification route.

## Architecture and reachable interfaces

The candidate has three components:

1. **Native submission:** the retained investigation observed `ListAgents` and `SendMessage` through a separate `claude mcp serve` process. Keep that sender candidate; it avoids a second model-driven sender session.
2. **Bound stored-session reader:** acquire one explicitly selected Desktop metadata file, obtain its Code session UUID and lineage, then read that UUID through the SDK with an explicit project directory. Preserve raw-record provenance where the SDK projection cannot support the required interpretation.
3. **Selected UI corroboration:** where an authorized native UI reader exists, observe only the selected task’s identity, visible message/ACK, and displayed settings. Treat each displayed value according to its actual producer.

This architecture changes no Desktop application files and adds no receiver hooks. It still requires later private-read and fixture authority.

The externally callable paths differ substantially:

| Interface | Actual access path | Established limit |
|---|---|---|
| Native MCP tools | A separate Code MCP server exposes callable tools; successful discovery is retained prior evidence. | No send was performed. The formatted listing is not a fresh typed binding to the consented Desktop task. |
| SDK session helpers | External code can call `getSessionInfo(uuid, {dir})` and `getSessionMessages(uuid, {dir, limit, offset})`. | They read stored session information and transcript messages; they do not attach to the existing Desktop query or supply its applied state. |
| Selected files | An external filesystem reader can open an authorized exact metadata/transcript path. | Persistence, buffering, lineage, replacement, and discovery scope need separate handling. |
| Desktop host `get_session` | Registered by `Gd`, enabled for `sessionType === "ccd"`, wrapped by `createProxyServers`, and supplied to Desktop-owned Code queries. | The inspected wrapper creates SDK MCP server objects. It establishes no independently reachable listener or attach address. |
| Renderer `LocalSessions` | `Ob.for(webContents).setImplementation` registers Electron IPC handlers for that renderer. | The registration is tied to `webContents`, with sender-frame validation. Knowing the channel name does not provide an external client connection. |
| Native UI/accessibility | Potential observation through an authorized external assistive-technology reader. | No selected Desktop accessibility tree or usable Linux control surface was observed. This harness’s native computer APIs are disabled. |

The source distinction is concrete: the renderer binding uses `Oo` to install handlers on `webContents.ipc`; `Ab` validates the sender frame. The host wrapper uses `createSdkMcpServer` and returns server objects for the query configuration. Neither inspected chain establishes a standalone read endpoint. This is a bounded finding, not proof that no other transport exists. Sources: `.vite/build/index.chunk-DuaKZOPP.js`, `Oo` at UTF-8 byte 650193, `Ab` at 2192968, binding near 5912800; `.vite/build/index.chunk-CKt-cwRV.js`, `Gd` near 209757 and `createProxyServers` near 397801.

**A correction to the shared seed matters for fixture acquisition.** `LocalSessions.start` returns the Desktop `{sessionId}` on its normal successful path whether or not `typedText` is present. The return expression uses a comma after the conditional `bindChangesNamedInPrompt` side effect; the object is its returned value. The seed’s [native source delta](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/research/2026-10-01-observer-scope-review/native-source-delta.md) incorrectly describes separate return branches. I checked the actual return at UTF-8 byte 28451 in the pinned `index.chunk-COPWZCsC.js`. This corrects the internal creation-result contract; it does not make that result externally observable.

## Requirement-to-producer assessment

“Stored,” “displayed,” and “applied” remain different evidence meanings.

| Requirement | Producer/interface and binding | Freshness, access, unsupported meaning | Smallest discriminating check |
|---|---|---|---|
| Exact native peer | Fresh native listing plus an independent selected-task identity observation. | Native discovery access; listing freshness does not establish Desktop/Code/process identity or consent. | Compare the fixture’s receiver-side peer identity with a fresh listing and independently obtained Desktop and Code IDs. |
| Desktop-to-Code lineage | Selected metadata serializer `nE`: `sessionId`, `cliSessionId`, prior IDs and lineage. Filename uses Desktop ID. | Exact private-file access; delayed saves and replacement are possible. No live query identity follows from matching IDs alone. | Read the selected mapping before and after an authorized receiver observation; reject changed or ambiguous lineage. |
| Receiver-origin delivery | Bound transcript or SDK row from the exact Code UUID. | SDK returns user/assistant role, UUID, session ID, and raw payload. The external native send’s actual incoming record and origin fields remain unproved. | One authorized idle-fixture send; inspect the corresponding receiver row and attribution without inferring it from sender success. |
| Explicit correlated ACK | A distinct assistant record from the bound receiver, optionally corroborated in the selected UI. | Private content access; quotation, echo, unrelated output, and pair-level reply flags are insufficient. | Qualify the adopted ACK grammar and correlation against the actual fixture output. |
| Unknown-send reconciliation | Positive, provenance-bearing receiver records. | A missing, stale, truncated, or unflushed record leaves unknown; no automatic resend. | Correlate positive receiver evidence after a constructed ambiguous sender result. |
| Held/refused | Explicit admission evidence from the chosen native route’s producer. | Neither transcript silence nor a UI absence distinguishes these states. Held can later be released. | Establish observable native state records; retain synthetic failure coverage until live state changes are separately authorized. |
| Actual account route | Fresh executor-bound authenticated-route producer. | Metadata account/org directory names establish storage placement. Spawn identity and cached initialization account are historical. No qualifying external producer found. | Require a named fresh non-secret route source before a preservation check. |
| Active model | Existing query response or Code report, separately from the selector. | Saved model and renderer `model` describe manager selection; confirmed/last-response values have their own timing. No externally reachable qualifying getter found. | Establish response semantics for the exact query, including freshness when selection and applied state differ. |
| Applied permission mode | Code-confirmed mode plus pending setter outcome. | Renderer/host mode is manager state; a visible selector does not prove application. Host `get_session` also limits mode to self/children. | Observe the actual completion/report producer and any pending or failed transition. |
| Effective rules | Existing query’s `listPermissionRules` control. | Internal query access required; selected metadata and UI omit complete rule state. Errors and inactive rules matter. | Establish exact-query external acquisition and response coverage, or name the residual observer needed. |
| Host grants and pending changes | Host grant stores, permission-update paths, and in-flight operations. | Renderer pending cards cover only selected prompts. Code rules alone omit Desktop grants and failed/pending pushes. | Inventory each applicable store and mutation outcome; demonstrate a bound read for every retained facet. |
| Runtime worktree/cwd | Manager `harnessCwd`, Code init/worktree reports. | Renderer projection includes `harnessCwd`; metadata does not. It is last manager-observed state, not a fresh arbitrary getter. | Establish accessible event provenance/currentness for the selected receiver. |
| Busy continuity | Existing qualification’s harmless canaries and later receiver continuation. | Diagnostic; stored rows cannot alone establish uninterrupted execution. | Collect alongside the separately authorized busy-fixture proof. |

The field limits come from the [observation-path report](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/research/2026-09-29-desktop-observation-paths.md), lines 54–175, and the [observer design](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/specs/2026-09-29-desktop-runtime-observer-design.md), lines 157–208. I also rechecked `formatSessionForEvent` around manager bytes 1325210–1331137: it includes `harnessCwd`, pending cards, manager model/mode, and bridge IDs, but no `cliSessionId` or complete applied-permissions projection.

Current SDK documentation confirms that a known UUID can be read without general session listing. `getSessionMessages` searches all projects when `dir` is omitted, so this candidate must provide `dir`. Its offset pagination is not a documented transactional cursor or flush guarantee. No retrieved contract promises complete visibility of an active Desktop receiver’s in-memory messages. [Official TypeScript reference](https://code.claude.com/docs/en/agent-sdk/typescript), retrieved through Context7 on 2026-10-02.

## Task binding and bounded identity discovery

Keep four identities distinct: native peer address/reference, Desktop task ID, Code session UUID/lineage, and current executor identity. `bridgeSessionId` is a Remote Control identifier. A title, newest file, PID alone, or SDK UUID alone cannot substitute for the whole binding.

The metadata filename requires the effective user-data root, storage base, account, organization, and **Desktop task ID**. The Code UUID comes from the selected file for subsequent transcript binding. I rechecked `getStorageDir`, `storageDirFor`, and `getSessionFilePath` around manager bytes 919241–920400, plus the writer around 937560–938322. Parked-task storage can use retained account/org values, so the presently displayed account is not automatically the selected file’s storage account.

Two bounded acquisition proposals deserve comparison:

**Selected UI identity first.** If the normal selected-task UI exposes an exact task permalink/ID through a readable control, combine it with separately established storage-root/account/org facts and open only that file. The corrected `LocalSessions.start` result makes an internal ID available, but an existing externally readable UI representation remains to be established. A proposed DOM/debugger bridge would add access outside this lane.

**Nonrecursive identifier discovery.** With an explicit additional grant, capture `.json` entry names in one approved account/org storage directory before normal fixture creation, then capture the bounded difference afterward. Directory entries disclose other task IDs even without content reads. A new entry is only a candidate. Require an independently obtained Desktop ID where available, matching filename and serialized `sessionId`, matching dedicated project identity through `cwd`/`originCwd`, valid Code UUID, approved lineage/origin fields, and an observed creation interval. Multiple qualifying candidates stop selection.

If obtaining those matching fields requires opening candidate files, the grant must cover that acquisition. Projecting a few identifiers after JSON parsing does not turn a whole-file read into identifier-only exposure. The serializer includes unrelated private fields. I would propose the receipt’s bounded selected-metadata projection as a starting inventory: task/Code IDs, cwd/origin/worktree paths, and the named fork/dispatch/lineage discriminators, with any added `createdAt` field justified explicitly.

This proposal establishes endpoint record matching when its independent inputs are available. It cannot reproduce the receipt’s manager/record references, registration generation, account-transition epoch, actual writer fulfillment, or frozen live-query handoff. Stable reads also cannot detect an account transition away and back between reads.

The [receipt design](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/research/2026-09-30-fixture-identity-acquisition-design.md), lines 13–29, 100–137, and 139–157, supplies those stronger internal witnesses through proposed hooks. Its receipt is provisional until admission. Bounded discovery may avoid that machinery where endpoint binding suffices; it supplies neither writer-witness semantics nor full applied-state evidence. This design grants no private discovery read.

## UI meaning, costs, and compatibility

An evidence-only UI reader could confirm a selected task, visible receiver message, assistant ACK, displayed selector, or pending card. It must retain the task/window binding and capture interval. Selecting a task or opening a panel can change focus and render state; that effect should be measured in the later fixture scope.

The public Electron material retrieved here describes automatic accessibility activation in the presence of assistive technology and documents manual accessibility APIs for macOS/Windows. It does not establish the selected Linux package’s accessibility exposure or a usable external reader. Accessibility rendering can affect performance, so even read-oriented activation is an observation effect to assess. [Electron accessibility documentation](https://github.com/electron/electron/blob/main/docs/tutorial/accessibility.md), [application API](https://github.com/electron/electron/blob/main/docs/api/app.md), retrieved through Context7 on 2026-10-02.

The selected-file/SDK component needs no package exchange or planned restart. It adds polling, private-read scope, lineage handling, and compatibility work. UI corroboration adds focus/capture costs and dependence on view semantics. Their runtime overhead is unmeasured.

Maintain compatibility separately for metadata layout/writer, Desktop-to-Code mapping, SDK lookup/projection, external incoming-row attribution, ACK interpretation, and UI fields. A new build is unassessed. Compare consumed producers, reuse justified evidence, then escalate only changed or unresolved assumptions to affected fixture checks. A parser pass cannot restore missing producer provenance.

## Prototype disposition and later checks

**Reuse the retained prototypes; build nothing new in this round.** The [synthetic reader](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/prototypes/claude-receiver-reader.md) already illustrates partial rows, quotes/echoes, ordering, lineage changes, ambiguity, and unknown outcomes. The [runtime-observer experiment](https://github.com/nisavid/provingkit/blob/6fbddb3883e08476af9fffe1410863f0e89f0cd6/docs/superpowers/prototypes/desktop-runtime-observer/README.md) covers synthetic query replacement, deadlines, and per-field gaps. I read their retained descriptions; I did not rerun tests or verify their historical test results independently.

A later public test seam should accept an explicitly supplied binding and observations, with injectable file acquisition, SDK message-page acquisition, and clock. It should return per-record provenance, coverage gaps, and unknown outcomes. Synthetic tests can meaningfully check paging changes, duplicate UUIDs, replacement, incomplete reads, and binding rejection. They cannot prove external native row shape, native-address mapping, live freshness, or applied-state coverage. Implementing that seam now would encode unresolved producer assumptions.

The smallest later checks are ordered by their dependencies:

1. Under separately granted selected-task access, determine whether the normal UI exposes an exact Desktop ID and whether the explicit-UUID SDK lookup resolves that fixture without broader discovery.
2. Compare receiver-side native identity with fresh MCP discovery, retaining Desktop, Code, lineage, and executor evidence.
3. After the full observation plan is ready, perform one authorized idle send and identify the actual inbound row and distinct correlated ACK. Measure visible-versus-persisted timing.
4. Collect qualified before/after producers for every applied field. If a producer remains unnamed, report that gap before claiming preservation.
5. Extend to busy delivery and diagnostic continuity. Preserve synthetic unknown/held/refused cases; disruptive live controls require their own scope.

For the join, the residual questions are fresh authenticated route, applied model/mode, complete Code-and-host permissions, current cwd, query identity, native admission records, and incoming-message provenance. Hook or app-side proposals should name the producer and access path for each claimed substitution. This report supplies no general security assurance or live qualification.

## Sources, exposure, and capture

I verified the checkout HEAD as `6fbddb3883e08476af9fffe1410863f0e89f0cd6`. I consumed the common synthesis, method, linked first reports/follow-ups, history trace, and evidence manifest. Historical first-report errors remain historical; the synthesis controls their corrected interpretation. The accepted parallel decision and copied ticket were dispatch inputs; I did not reopen tracker items.

Input log:

- Frozen brief: `coordinator-retained existing r1 brief`.
- Immutable checkout: `reviewed checkout at 6fbddb3883e08476af9fffe1410863f0e89f0cd6`; read `CONTEXT.md`, the review packet, observation report, observer spec, selected receipt-design sections, and the two prototype descriptions.
- Offline source: `offline source extraction/manager-pristine.js` and the named `COPWZCsC`, `DuaKZOPP`, and `CKt-cwRV` members there. All four SHA-256 values matched the seed’s source-identity table; manager size was 1,596,495 bytes.
- Skills: installed `research`, `context7-mcp`, and `capturing-agent-procedures`.
- Public requests: installed `ctx7` CLI library/docs calls for Claude Agent SDK and Electron, using generic public questions. No proprietary source or task identifiers were sent.
- One attempted local read of the named historical sender-report path found it absent; sender findings here remain attributed to the reviewed seed.

I read no sibling dispatch/new findings, memory, private profiles, receiver records, settings, credentials, or live process data. I wrote no files, ran no tests/app modules, delegated nothing, and performed no UI action, send, installation, or restart.

Under `capturing-agent-procedures`, the coordinator should preserve this frozen report and its source correction for the comparison consumer. A maintained reader procedure and downstream invocation belong after architecture selection and qualified producer contracts; no installed procedure is established by this report.
