# Granular Wave 1 channel coverage

This report proposes a finite coverage register with 23 endpoint variants, 506 directed associations, and 1,012 lifecycle-profile slots. It preserves the selected six direction families and eight preparation profiles inside that larger register. These are research counts, not a maintained catalog, an implementation choice, or qualified channels. The scoped refresh includes complete current T3 Codex/Claude adapter sources and Claude TypeScript root exports. Release applicability, remaining interfaces, and actual caller bindings remain open.

## Evidence and limits

Observation date: 2026-10-12 UTC. The governing inputs are [the accepted operation contract](https://github.com/nisavid/provingkit/issues/538#issuecomment-6112579765), [the accepted cohort contract](https://github.com/nisavid/provingkit/issues/540#issuecomment-6119910041), [the frozen research question](https://github.com/nisavid/provingkit/issues/560), and [the published comparison at 61b99e73](https://github.com/nisavid/provingkit/blob/61b99e73ebedf8afb33b28a531daea8089504394/docs/superpowers/research/2026-10-11-peer-portfolio-comparison.md). All five supplied files were read completely after their byte counts and SHA-256 digests matched the manifest.

Four evidence classes remain separate:

- **Refreshed public evidence:** release metadata, official OpenAI interface documentation, current Context7 retrievals, and T3's pinned outside-agent document and public source-tree listing.
- **Supplied findings:** the comparison's source declarations and corrections at its recorded revisions. Retaining these findings does not refresh their implementations.
- **Synthetic or supplied operation results:** none were produced in this investigation. The comparison and cohort describe preparation and future checks; they do not supply live operation passes.
- **Observed live task evidence:** none. No account, private task, installed harness, process, authentication, provider turn, or recipient was observed.

The initial refresh stopped after a T3 recursive-tree response acquired 8,828,086 bytes, exceeding the entire 8 MiB acquisition budget before filtering. No further public acquisition was dispatched after the overrun was recognized. Ten official Claude Markdown requests returned HTTP 403; none was retried through another route. Consequently, current Claude Desktop, VS Code, headless, messaging, Channels, Remote Control, cloud, and runner documentation was not refreshed directly. The tree listing identifies files, not their implementation behavior. A separately bounded supplement examined provider drivers, outside-MCP access declarations, and Python SDK ownership. A later four-file packet supplied the complete current T3 adapters and TypeScript root files. Those increments establish the findings below without changing the original overrun, declined bodies, or incomplete acquisition records. They do not establish that every relevant interface was inspected.

The retained comparison covers 48 registry families, including their explicitly named subroutes. This report preserves that inventory, distinguishes newly visible source/version differences, and proposes coverage records. It does not exhaust all conceivable clients or third-party fabrics. Missing evidence establishes neither incompatibility nor unsuitability.

## Source versions and changes

| Source | Refreshed observation and implication |
| --- | --- |
| [Codex stable release](https://github.com/openai/codex/releases/tag/rust-v0.162.1) | The latest-release response named 0.162.1, published 2026-10-09. The supplied implementation pin remains 092d3acd. Release metadata does not identify an installed runtime. |
| [Codex development commit](https://github.com/openai/codex/commit/ddb33e34b278ca1b7d16d1e68f8ad363a2042f2e) | Main observed at ddb33e34 on 2026-10-12, replacing the comparison's cc7ba336 observation. No behavioral delta analysis was completed. |
| [Codex SDK documentation](https://developers.openai.com/codex/sdk/) | Mutable documentation observed 2026-10-12 distinguishes TypeScript local-thread control from Python's local App Server JSON-RPC control and pinned runtime dependency. Keep both ownership profiles. |
| [App Server documentation](https://developers.openai.com/codex/app-server/) | Mutable documentation observed 2026-10-12 declares stdio, WebSocket, Unix socket, and off transports; remote TUI attachment; and a separate outbound Code Mode host connection. Transport, agent execution host, and task owner are separate records. WebSocket and remote Code Mode features carry experimental/support limits. |
| [Codex noninteractive documentation](https://developers.openai.com/codex/noninteractive/) | Persistent exec/resume and ephemeral exec are different preservation profiles. JSON events expose thread/turn progress and results; they do not prove another live owner's attachment. |
| [Codex IDE documentation](https://developers.openai.com/codex/ide/) | The IDE is a separate client surface for local work and cloud delegation. App Server documentation identifies the VS Code extension as a rich client. Its exposure to an outside caller remains unassessed. |
| [Codex Cloud documentation](https://developers.openai.com/codex/cloud/) | Web, mobile, and desktop are documented entry/view surfaces for cloud tasks. That supports a shared product-view record; it does not bind CLI backend IDs, legacy integrations, or Work history to it. |
| [Projects and chats](https://learn.chatgpt.com/codex/projects) | Documentation explicitly separates Work conversation history from Codex history and describes local-computer access with cloud coordination/fallback. Work is retained as an adjacent population; execution mode and remote viewing cannot establish Codex identity. |
| [Claude Code release](https://github.com/anthropics/claude-code/releases/tag/v2.1.296) | Latest-release metadata still named 2.1.296, published 2026-10-09. Its notes distinguish headless sessions, Desktop Code policy, background service, and self-hosted runner behavior. These are surface leads, not a complete callable contract. |
| [TypeScript Agent SDK release](https://github.com/anthropics/claude-agent-sdk-typescript/releases/tag/v0.3.296) | 0.3.296 declares parity with Code 2.1.296 and adds the initialization CLI-version field. This is the supplied browser/bridge package cohort, not the Python cohort. |
| [Python Agent SDK release](https://github.com/anthropics/claude-agent-sdk-python/releases/tag/v0.2.165) | Latest-release metadata named 0.2.165, published 2026-10-08, bundling Code 2.1.294. Python and TypeScript therefore require separate runtime-version bindings even where session operations look alike. |
| [T3 stable release](https://github.com/pingdotgg/t3code/releases/tag/v0.0.45) | Latest-release metadata still named 0.0.45, published 2026-10-02. Its notes include Codex 0.159 protocol regeneration. This does not qualify current-main outside-agent behavior for that release. |
| [T3 development commit](https://github.com/pingdotgg/t3code/commit/5753207d53362608f281738eda3a9faf4e13b6be) | Main observed at 5753207d on 2026-10-12, replacing the supplied 5ce5a8f observation. The current provider drivers, outside-MCP access declarations, and complete Codex/Claude adapters were inspected. Their release applicability and managed-provider/supporting-module behavior remain open. |
| [T3 outside-agent contract at 5753207d](https://github.com/pingdotgg/t3code/blob/5753207d53362608f281738eda3a9faf4e13b6be/docs/user/outside-agents.md) | Outside HTTP MCP/OAuth callers may read projects/threads and, with an appropriate grant, start/message/stop threads. Hosted callers need internet reachability; local callers can use their reachable environment route. Mode ceilings apply to started/steered threads. This is source-declared caller access, not an observed connection. |

Current Context7 resolution selected [/openai/codex](https://context7.com/openai/codex) and [/websites/code_claude_en_agent-sdk](https://context7.com/websites/code_claude_en_agent-sdk). Read-only API retrieval avoided installation and local writes. Codex snippets pointed to exec-backed TypeScript, stdio-backed Python, App Server transports, and version-unbound main sources. Claude snippets included both ordinary query/resume and a V2-preview example. The supplied comparison marks V2 removed at its package cohort. The complete 0.3.296 root declaration/runtime files contain none of the named unstable V2 constructor/resumer/prompt exports. Indexed examples cannot override that package observation. Context7's Claude index was dated 2026-10-03, not the 2026-10-09 release.

## Current owning-source observations

The complete four-source packet acquired 2,476,653 bytes under fixed allocations totaling less than 4 MiB. Each body was retained completely and checked by its digest; no inspected code was installed or executed. Source citations use the artifact keys below and original line numbers. Minified runtime citations also name the class or function.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| [t3-codex.ts](https://github.com/pingdotgg/t3code/blob/5753207d53362608f281738eda3a9faf4e13b6be/apps/server/src/orchestration-v2/Adapters/CodexAdapterV2.ts) | 307,723 | `e207ea59239cfe4b3ac50022e87b2a7e6e16040efa754257b3945f0f6b1caf31` |
| [t3-claude.ts](https://github.com/pingdotgg/t3code/blob/5753207d53362608f281738eda3a9faf4e13b6be/apps/server/src/orchestration-v2/Adapters/ClaudeAdapterV2.ts) | 391,226 | `bac0e24235cfd7a9fa8e04f01880924d44d1dd10e6a4bdf8070e237e5191002d` |
| [claude-sdk.d.ts](https://unpkg.com/@anthropic-ai/claude-agent-sdk@0.3.296/sdk.d.ts) | 538,514 | `fc2866dfe2c01468edb19b1d94f26156bfacecdf1e7f1452b276ed2f8cc0b08f` |
| [claude-sdk.mjs](https://unpkg.com/@anthropic-ai/claude-agent-sdk@0.3.296/sdk.mjs) | 1,239,190 | `5cf6f15237f9c84e6e5b724a10180478732457168921d7aa3e02632037cce299` |

T3 source is commit 5753207d; the TypeScript package is 0.3.296. T3’s installed SDK/executable binding was not observed. The earlier supplement separately established provider-instance construction, outside-MCP thread-scope/mode checks, and Python’s owned CLI subprocess. Its 24 source-attempt records retain two tested release-path 404s, oversized-body refusals, one lost directory-response accounting record, and a conservative aggregate charge of at most 955,256 bytes. Those failures establish limits at the tested paths, not absent release functionality.

### T3 Codex: actual owned runtime and ID chain

The normal App Server factory constructs a child process using the configured binary, launch arguments, provider environment, and effective CODEX_HOME, then builds a client over that child (t3-codex.ts:1507–1556, layerAppServerClientFactory). openSession passes the T3 thread, provider-session ID, provider-instance ID, runtime policy, settings, and environment to that factory (1700–1724). createCodexAdapterV2 separately materializes the shadow home and selects effective settings/environment (1570–1611). This strengthens the supplement's construction claim into a concrete owned-process/client seam. It does not inspect the separate managed-provider implementation or prove attachment to a GUI or terminal owner's connection.

ensureThread calls thread/start. providerThreadFromCodexThread derives the provider-thread ID from driver/native thread ID and stores appThreadId, providerInstanceId, providerSessionId, ownerNodeId, and nativeThreadRef (833–873; 6465–6496). startNativeTurn sends turn/start for that native ID and registers the returned native turn ID against the supplied T3 run/attempt context (6181–6220). These are separate identities; an app-thread ID is not a native-thread ID.

resumeThread requests thread/resume for the recorded native ID, reapplies runtime/MCP/model parameters, handles an explicit archived-session error by unarchiving and retrying, and records the response's thread ID and new provider-session/instance association (6497–6562). This supports a stored native-thread resume candidate. It does not independently prove that requested and resolved IDs match or that prior context survives under the acceptance contract. Keep both IDs in later evidence.

Live steering requires an active provider turn and sends turn/steer with expectedTurnId set to its mapped native turn ID (6648–6690). A successful request is narrower than correlated receiver receipt, completed work, or later reply. The capability table's queued-message and restart claims do not replace the host dispatcher/admission implementation (228–322).

readThreadSnapshot requests thread/read with includeTurns:true, returns the raw thread as providerPayload, and leaves normalized providerTurns, messages, and runtimeRequests empty (7163–7195). This establishes a provider-history read seam, not a complete normalized inspection record or an outside MCP result reader.

forkThread calls thread/fork, optionally uses a native turn boundary or subsequent history revert, and constructs a provider thread for the target app thread using the returned native ID (7272–7345). Record it as fork, not same-task continuation. Rollback can load a stored thread before native revert and retains separate conversation-head metadata (7196–7271).

The adapter emits provider-turn and terminal projections (1969 onward; 5529–5568). Provider completion remains separate from caller validation. Its own source states that a resumed subagent can appear completed between turns, allowing idle release before a delayed resume (6418–6424). Both adapters declare pendingRequestsSurviveRestart:false. These limits prevent a broad restart-preservation claim.

### T3 Claude: allocation, live reuse, cold resume, and replacement

The source binds the query seam concretely: layerQueryRunner allocates UUIDs, feeds an asynchronous prompt queue into SDK query(), exposes its message stream, and implements offer as queue insertion (t3-claude.ts:654–802). MCP configuration is sent through setMcpServers after query creation; unavailable server names are reported, so tool exposure cannot be assumed from configuration alone (715–769).

makeProviderThread stores T3 app/provider/session/instance identities and the allocated native session ID (1264–1298). ensureThread allocates that ID and returns bookkeeping; it does not open the SDK query (8887–8910). resumeThread likewise updates provider-session/status/time without contacting the SDK (8911–8933). Therefore neither method alone establishes native session creation or executed continuation.

Actual creation/resume occurs in openQuery. makeClaudeQueryOptions selects sessionId for creation or resume for an existing native ID, with optional resumeSessionAt (948–1022). The query executable/environment are selected by createClaudeAdapterV2 (9212–9252); this source does not bind T3's installed dependency or binary to the separately inspected SDK 0.3.296 package.

openQuery reuses a live query when native ID, effective policy, and model-selection identity match. It can restore the originally opened permission mode before the next prompt (8192–8240). A selection/policy change on the same native thread can close the old process and open a new one with resume. It refuses that replacement while the live process has retained background work. Moving to another native thread replaces the previous query and clears its process-specific wake state (8242–8270).

Cold resume after idle release is supported by the branch using persisted-turn evidence, openedNativeThreads, or resumeSessionAt to select resume rather than sessionId. The local opened set is updated only after successful queryRunner.open (8272–8334). This is a source path for continuing stored native history through a new process, not an observed restart or active-owner attachment. Failed replacement can leave the old process closed; its cleanup is explicit (8307–8322).

There are three different meanings to retain:

1. A normal subsequent request offers a fresh UUID-bearing user message to the query. startTurn rejects another active provider turn (8413–8450; 8500–8538).
2. A provider-origin continuation drains buffered output without sending its displayed prompt text. It may settle immediately when its buffer is empty (2586–2590; 8500–8573). That host run is not proof that a new requested follow-up executed.
3. Rollback to thread start allocates a new native session ID. Fork closes the live source query, calls SDK forkSession, and records the returned new ID and fork relation (9044–9178). Report these as reset/replacement or fork.

Claude's turn identity is weaker than Codex's: startTurn initially uses turn:<attemptId>; providerTurnPayload uses a message cursor or that synthetic value with strength:weak (8417–8438; 4161–4180). Record attempt, prompt UUID, provider turn, actual session, and message cursor separately.

The adapter does implement prompt-correlation handling: it checks echoed user_message_uuid/user_message_uuids, tracks command lifecycle acknowledgments, holds some output pending an echo, and detects acknowledgment without turn start (2625–2644; 7714–7851). Older or result-only echo paths remain distinct. It also explicitly records uncertainty about positive-turn task-notification results that could resemble stale results (7540–7562). Do not equate queue offer or a host terminal projection with receiver-correlated fulfillment.

readThreadSnapshot always fails with “does not implement snapshots” (9044–9052). This corrects any combined T01/T02 interpretation that imports Codex's provider snapshot capability into Claude. Host projections, stored transcripts, and an independent result reader require their own source and completeness contracts.

### Claude SDK root: complete export inventory and limits

The terminal export statement has 32 runtime names (claude-sdk.mjs:148):

AbortError, CommandMatcher, DirectConnectError, DirectConnectTransport, EXIT_REASONS, FileIndex, HOOK_EVENTS, InMemorySessionStore, ORG_POLICY_LIMIT_PREFIXES, SYSTEM_PROMPT_DYNAMIC_BOUNDARY, USAGE_LIMIT_ERROR_PREFIXES, USAGE_TRANSITION_PREFIXES, USAGE_WARNING_PREFIXES, createSdkMcpServer, deleteSession, filterEscalatingDefaultMode, foldSessionSummary, forkSession, getSessionInfo, getSessionMessages, getSubagentMessages, importSessionToStore, listSessions, listSubagents, parseDirectConnectUrl, prewarm, query, renameSession, resolveSettings, startup, tagSession, and tool.

The root declarations contain none of CommandMatcher, FileIndex, DirectConnectError, DirectConnectTransport, or parseDirectConnectUrl. The first two are search/index helpers in the runtime (117, classes rR/iR), not peer routing. This declaration/runtime mismatch is a concrete source limit.

Neither root export surface exposes unstable_v2_createSession, unstable_v2_resumeSession, or unstable_v2_prompt. Their exact names are absent from both complete files. Strengthen the prior retained V2 finding to current symbol-level absence in SDK 0.3.296; do not revive it from indexed examples or confuse the existing resume options with a V2 API. No claim about other package versions follows.

query constructs a ProcessTransport and selects the native executable or an explicit override/custom process spawner (runtime:136, class rT; 142, yT; 143, lWe). The declarations distinguish continue's most-recent-directory selection, exact resume, supplied sessionId, forkSession, and resumeSessionAt (1594–1599, 1709–1714, 2089–2125), and expose custom process spawning (2440–2463). Custom spawning can place execution elsewhere; it does not establish access to an independently held owner. persistSession:false precludes later stored resume; SessionStore mirrors still require local transcript writes (1816–1845). Readers select filesystem or SessionStore branches (runtime:145, nIt/rIt/oIt/sIt).

getSessionInfo reads transcript metadata, not a fresh active-runtime status observation. getSessionMessages returns conversation-chain user/assistant messages and optionally system messages; SessionMessage has no result variant (declarations:868–944, 6538–6552). These readers are useful inspection leads but do not automatically retrieve a complete terminal SDKResultMessage. Query results carry session/correlation fields and distinguish error/success; success subtype can still have is_error:true (5729–5875).

startup and prewarm are active process/configuration/initialization paths, not passive observation. prewarm can perform authentication, hooks, and MCP initialization before a later claim; its option_not_applied rejection can occur after a prompt was sent (2769–2849; runtime:143, _Z/dWe). A later fixture plan must distinguish these effects and possible submission before fallback.

DirectConnect is a useful additional candidate lead, with a narrower conclusion than an existing-peer route. Its constructor starts initialization. iNe POSTs /sessions with optional cwd, session_key, permission_mode, and bearer token, validates returned session_id/ws_url/work_dir, and then opens the returned WebSocket (runtime:119–121, zB/iNe). A sessionKey is not shown to be an arbitrary native task ID; server selection/reuse behavior is absent from this packet.

The transport supplies newline-JSON input/events and session/work-dir getters; normal close can optionally issue DELETE /sessions/<id> (119–121, zB/FB). No reconnect/replay or independent completed-result retrieval contract is shown. parseDirectConnectUrl accepts cc:// or HTTP(S) server addresses and rejects cc+unix:// (121, sNe). The inspected root query constructor always creates ProcessTransport; it exposes no demonstrated DirectConnect selection path (142, yT). Root exports alone therefore cannot establish a supported typed query integration, Desktop attachment, cloud mapping, credential acceptance, concurrency policy, or passive reader.

Browser and bridge subpath implementations were not in the four-source packet. Retain their earlier evidence and gaps; this root inspection does not refresh them.

### Reconcile the 23 proposed records

| Records | Owning identity and disposition after this increment |
| --- | --- |
| C01, C02, C03 | GUI, terminal, and IDE owners remain separate proposed variants; T3's App Server does not bind any of their live owners. |
| C04, C05, C06 | Persistent exec, TypeScript exec SDK, and Python App Server SDK retain distinct executor provenance; no new native Codex SDK source was inspected. |
| C07 | Independent App Server ownership remains separate from T3's child-process factory and host lifecycle. |
| C08, C09 | Cloud product/UI versus CLI reference mapping stays provisional; this packet supplies no equivalence evidence. |
| C10 | Native leader/child membership remains distinct. T3 projects native Codex subagents into host records; that does not grant outsiders native parent tools. |
| H01, H02, H03 | Desktop local/SSH/WSL query/host bindings remain unproved by SDK or T3 ownership. |
| H04, H05 | Interactive terminal and controlled headless processes remain separate; stored query resume cannot establish access to the terminal's current owner. |
| H06 | Claude IDE caller/input/result exposure remains open. |
| H07 | Root SDK-owned query lifecycle is strengthened; custom-spawn, store, spare-process, and DirectConnect leads require distinct profiles and mappings. |
| H08 | Python findings remain supplied/supplement evidence; TypeScript root inspection does not establish Python parity or its bundled CLI version. |
| H09 | Cloud task identity and exact CLI/browser routes remain separately bound; neither DirectConnect nor T3 proves fresh cloud attachment. |
| H10, H11 | Parent-owned subagent and team-member populations remain separate. SDK task events/readers and T3 projections do not establish arbitrary native child/team routing or later reply. |
| T01, T02 | T3-owned app/provider/native chains are strengthened and their lifecycle/inspection mechanisms differ. Retain host ownership even with a native backend or matching session UUID. |

No row is added, merged, removed, or qualified. The 23/506/1,012/6,072 arithmetic remains proposed enumeration, not maintained coverage. C08/C09 mapping, operational-variant versus native-population counting, and main-versus-child views remain decisions. T3 main 5753207d is neither the earlier 5ce5a8f cohort nor v0.0.45 behavior; the two prior release-path 404s do not establish feature absence.

Outside MCP authentication/access declarations remain supplement evidence. These adapters show provider-side use of a T3-scoped MCP session, not the outside toolkit's complete handlers or OAuth grants. Independently opened T3 tasks are still host-owned; outside callers cannot inherit in-thread caller identity. Every direction needs actual caller exposure/reachability, target and owner binding, origin, permitted access, and an independent evidence reader.


These source findings remain inputs to the comparison/reaction join. That consumer must load the reviewed `updating-cross-harness-catalog` procedure, record its revision, reconcile the affected records and views, and retain every unrelated record. No maintained catalog update, installed method, or live capability is claimed here.

## Proposed endpoint register

An endpoint record below is an **operational variant with its own ownership/access contract**, not a claim that every row has a disjoint transcript backend. A process, transport, model name, or wrapper ID is insufficient to merge rows. Conversely, a remote screen viewing the same identified owner does not create another task population.

C = native Codex family; H = native Claude Code family; T = T3-owned family. All IDs are report-local labels, not native IDs. The R references point to the [retained comparison registry and its source corrections](https://github.com/nisavid/provingkit/blob/61b99e73ebedf8afb33b28a531daea8089504394/docs/superpowers/research/2026-10-11-peer-portfolio-comparison.md#reconciled-registry).

| Record | Population/variant and owning runtime | Required identity/access distinction; fabrics |
| --- | --- | --- |
| C01 | ChatGPT desktop Codex-mode main task, locally owned GUI runtime | Chat/task ID plus actual App Server owner/store; app tools R01, owning controls R05, queue R06. Remote-host bindings are additional profiles, not presumed local-owner equivalence. |
| C02 | Independently running interactive Codex terminal/TUI main task | Native thread plus terminal's actual owner; R03, R05, R06. CLI is the program/command entrance; TUI is its interactive client, not a second native population. |
| C03 | Codex IDE local main task | IDE client's App Server/native thread; R05/R06 only after owner binding. Editor context and IDE approvals remain surface-specific. |
| C04 | Controller-owned persistent Codex exec worker | Native thread/turn plus job/process provenance; R04. Ephemeral exec is an additional nonpersistent profile unsuitable for stored continuation. |
| C05 | TypeScript SDK-owned exec worker | SDK object/job plus resolved native thread/turn; R09/R04. It shares an exec mechanism without proving another executor's active-owner access. |
| C06 | Python SDK-owned App Server worker | SDK connection/server plus native thread/turn; R10/R05. Its default subprocess owner differs from an independently running GUI owner. |
| C07 | Independently provisioned App Server task | Actual server/transport/namespace plus native thread/turn; R05. Existing server attachment and new server creation remain separate inputs. |
| C08 | Current Codex Cloud product task | Cloud task/environment/backend reference; R13 UI views and service-specific creation routes. Web/mobile/desktop views are not three endpoint populations. |
| C09 | Codex cloud-CLI-addressed task cohort, provisionally separate | R12's backend/task reference. Retain a separate unresolved mapping to C08 and legacy tasks; this row does not establish a second backend. |
| C10 | Native Codex leader-owned child task | Root/parent/child identity and caller membership; R02. Arbitrary independent sidebar peers cannot borrow this route. |
| H01 | Claude Desktop local Code main tab | Native session/tab plus selected main query/owner; R19/R20/R21. The stronger Desktop preservation profile remains separate. |
| H02 | Claude Desktop SSH-hosted Code main tab | Desktop tab and remote host/session/query binding; R19. Local sender/socket assumptions do not transfer across SSH. |
| H03 | Claude Desktop WSL-hosted Code main tab | Desktop tab and WSL runtime/session/query binding; R19. Distinct host namespace and acquisition profile. |
| H04 | Independently running interactive Claude terminal main session | Exact native session/current owner; R20/R21 and opted-in R27/R45 routes. Stored resume is not active-owner attachment. |
| H05 | Controller-owned Claude headless CLI session | Native session plus process/result stream; retained R25/R30 mechanisms and current release's headless distinction. Current CLI flag/schema refresh is incomplete. |
| H06 | Claude VS Code local session | IDE/query/session ownership; Desktop tab tools explicitly exclude this population in retained R19. Current outside-input/result contract remains unassessed. |
| H07 | TypeScript Agent SDK-owned query | SDK query/process plus native session, at selected SDK/CLI versions; R25. Browser R23 and worker-bridge R24 profiles need explicit remote-population mappings. |
| H08 | Python Agent SDK-owned query | Python client/query plus native session and bundled CLI; R25 analogue. Fresh metadata binds 0.2.165 to Code 2.1.294, not TS 0.3.296. |
| H09 | Claude Code cloud task | Exact cloud session/URL plus cloud owner; R22, separately R23. Teleport/local resume is a change of execution population, not transparent cloud continuation. |
| H10 | Claude parent-owned subagent | Parent/agent/session identities; R30. Native child routing cannot be assigned to arbitrary Desktop/cloud peers. |
| H11 | Claude team teammate session | Team/member/native identities and eligible native messaging; R20/R30. Team membership and later reply are separate from a one-shot subagent return. |
| T01 | T3-owned Codex thread population | Environment/T3 thread/provider session/run to native Codex thread/turn chain; R35 Codex adapter, outside MCP, R43 connectors. No arbitrary C01/C02 attach follows. |
| T02 | T3-owned Claude thread population | Environment/T3 thread/provider session/run to SDK/native Claude session chain; R35 Claude adapter, outside MCP, R43. No arbitrary H01/H09 attach follows. |

C01–C10 rely on the retained OpenAI inventory plus refreshed [CLI](https://developers.openai.com/codex/cli/), [noninteractive](https://developers.openai.com/codex/noninteractive/), [SDK](https://developers.openai.com/codex/sdk/), [App Server](https://developers.openai.com/codex/app-server/), and [Cloud](https://developers.openai.com/codex/cloud/) source declarations. H01–H11 preserve their supplied interface findings, with current TypeScript root and Python export/subprocess observations recorded below. T01/T02 now include complete adapter inspection at 5753207d, separately from 5ce5a8f and the stable release. No release or live capability follows from a development source finding.

Additional records stay outside the 23-row arithmetic until their ownership/population mapping is resolved: ChatGPT Work cloud/local-computer modes; legacy Codex Cloud and each Slack/Teams/Linear/GitHub workflow binding; Claude self-hosted runner execution; Claude browser/bridge remote sessions; and Projects/Dispatch product conversations. They remain visible follow-ups, not unsuitable populations. Remote TUI, SSH, mobile/web views, Channels, MCP, ACP, and relay transports attach profiles to a known owner; they do not independently add endpoints.

## Six-operation vectors

Positions are **notification / work request / creation / inspection / reply / continuation**. K means a source declares an operation-shaped mechanism for the named eligible population; P means a narrower component, output stream, or conditional capability; ? means unassessed; U means the named route is unsuitable for the asserted population; – means creation of the already existing target is inapplicable. K never means the accepted positive-result contract is met. Inspection K still requires separate status and completed-result records. Reply P often means synchronous return only.

The [accepted operation contract](https://github.com/nisavid/provingkit/issues/538#issuecomment-6112579765) requires correlated receiver receipt for notification, caller validation for fulfilled work, independently observable addressable creation, separately qualified status/result inspection, a later correlated return for reply, and declared native identity/context for continuation. No vector below is a live pass.

| Receiver/route profile | Independently opened/preexisting population | Controller-created population | Source/evidence restriction |
| --- | --- | --- | --- |
| C01, R01 app-exposed chats | KK–KPK | KKKKPK | App caller exposure only; external caller and later return remain open. |
| C02, R03 interactive UI | PP–PPK | PKKKPK | Interactive/native resume declaration; outside structured control partial. |
| C03 IDE owner controls | PP–PP? | PPKPP? | App Server client relationship is known; IDE-specific outside caller and preservation unassessed. |
| C04 persistent exec, R04 | PP–PUP | KKKKPK | Stored eligible session, not another active owner. Ephemeral continuation is U. |
| C05 TS SDK, R09 | PP–PUP | KKKKPK | Owned exec lifecycle; ID resolution still required. |
| C06 Python SDK, R10 | PP–PUP | KKKKPK | Owned App Server; native active-owner attachment unproved. |
| C07 owning App Server, R05 | PP–PPK | KKKKPK | Existing owner/rejoin or eligible cold resume; queue alone is PP–P?P. |
| C08 cloud UI, R13 | KK–KPK | KKKKPK | Human workflow declaration; automated access unknown. |
| C09 cloud CLI, R12 | ??–K?? | ?KKKP? | Creation/status/diff route; general existing follow-up absent in inspected enum. |
| C10 native child, R02 | UU–UUU | KKKKKK | K only inside the native parent/child contract; outside that relationship U. |
| H01/H02/H03 Desktop tabs, R19 | KK–KKK | KKPKKK | Eligible app-run tabs; explicit actual local/SSH/WSL binding needed. |
| H04 native Claude messaging, R20 | KK–PKK | KK?PKK | Eligible peer admission; native state notice is not content acknowledgment. |
| H05 headless CLI | PP–PUP | PKKKPP | Controlled-worker candidate; current complete CLI contract not refreshed. |
| H06 VS Code | ??–??? | ?????? | Population retained; no current operation transfer from Desktop or SDK. |
| H07 TS SDK main query, R25 | PP–PUP | KKKKPK | Eligible stored query/session; not independently held Desktop/cloud query. |
| H08 Python SDK query | PP–PUP | PKKKPP | SDK/resume declarations retrieved; version-specific parity and result/readers not examined. |
| H09 cloud CLI plus independent UI reader, R22 | KK–KPK | KKKKPK | CLI queues and exits; reader is separate; R23 alone remains PP–KPP. |
| H10 subagent | UU–UUU | PKKPPP | Return is not later independent reply; parent-owned creation/request remains a distinct contract. |
| H11 team teammate | PP–PKP | PKKPKP | Team/member routing and native peer admission are required; no arbitrary peer equivalence. |
| T01 outside MCP + Codex adapter | PP–P?P | PKKP?P | Current owned App Server, native turn/start/steer, and raw history snapshot seams. Outside caller exposure, correlated receipt/result, and continuity remain unqualified. |
| T02 outside MCP + Claude adapter | PP–P?P | PKKP?P | Query creation is lazy; allocation/resume bookkeeping is insufficient. Live reuse, cold resume, replacement, weak turn IDs, and buffered-output continuation differ. Provider snapshots are unsupported. |

H10/H11 are conservative proposed classifications, not current exported-tool audits. Independently opened T3 threads remain T3-owned even when this controller did not create them. Controlled provenance and host ownership are different dimensions.

Each direction keeps an operation record for its actual target, source/version, correlation, stage, timestamp, completeness, and limits. Queue acceptance, turn start, SDK processing, CLI exit, broker acknowledgment, returned text, and caller validation are distinct evidence. Idle, busy, held, refused, unloaded, and restart conditions are separate profiles. No channel receives one highest stage that conceals missing operations or conditions.

## Retained candidate/fabric crosswalk

Every R01–R48 family below comes from the [published comparison](https://github.com/nisavid/provingkit/blob/61b99e73ebedf8afb33b28a531daea8089504394/docs/superpowers/research/2026-10-11-peer-portfolio-comparison.md#reconciled-registry). This is a complete crosswalk of that finite registry, including named unsuitable/supporting entries. It is not a fresh implementation audit of every candidate.

| Registry family and distinct subroutes | Endpoint/profile association; limitation |
| --- | --- |
| R01 desktop chat tools; R02 native children | C01 versus C10. App-level peer tools and leader/child membership are different caller contracts. |
| R03 interactive CLI/TUI controls; R04 exec/resume | C02 versus C04. Add explicit persistent/ephemeral profiles; PTY interaction does not establish an outside API. |
| R05 App Server; R06 CLI queue/App Server queue; R07 Python ExternalMessage/tool output | C01–C07 where actual owner binding exists. Preserve distinct caller interfaces, loaded/cold owner conditions, and user/tool-content origin. Queue has no independent result/reply inbox. |
| R08 raw history injection | Codex owner only. Unsuitable for first notification: history insertion does not itself start work. |
| R09 TypeScript SDK; R10 Python SDK | C05 versus C06; exec and stdio App Server owners remain separate. |
| R11 remote TUI socket, managed remote control, SSH | Access/view/execution-host profiles of a bound Codex owner. No native inbox arises from transport alone. |
| R12 cloud CLI; R13 cloud web/mobile/desktop UI | C09 versus C08, with mapping unresolved. Existing follow-up is not supplied by R12's inspected enum. |
| R14 Slack, Teams, Linear, GitHub | Four workflow bindings retained separately. Associated creation/follow-up/review is not arbitrary native-ID control. Backend equivalence unresolved. |
| R15 OpenAI Codex plugin for Claude Code | Plugin-associated Codex jobs; created worker/import profiles. Boolean resume selectors do not accept arbitrary exact IDs; Desktop/cloud plugin availability unproved. |
| R16 removed MCP server; outgoing MCP client | Removed server unsuitable at observed Codex cohort. Client is supporting caller equipment requiring another receiver actuator. |
| R17 execution-service, socket-relay, API-proxy, command/filesystem helpers, hooks, schedules | Supporting execution/transport/trigger entries. None supplies an independently bound native peer/result contract by itself. |
| R18 Work cloud/local-computer mode | Adjacent Work population and execution modes; distinct history, not presumed C01/C08. |
| R19 Desktop tab tools; R20 native ListAgents/SendMessage | H01–H04 and eligible peers; app-run tab restrictions and native admission differ. H06/H09 cannot borrow tab tools. |
| R21 MCP serve; native inbox socket | Two entrances to eligible Claude peers. Current schema and supported external raw-socket contract remain unrefreshed. |
| R22 exact-ID cloud CLI; cloud UI | H09 submission and independent observation routes. Teleport unsuitable for same-cloud continuation. |
| R23 browser SSE; browser WebSocket | Active bound remote-session clients; cursor/delivery semantics differ. Desktop/native mapping and credential acceptance unresolved. |
| R24 SDK worker bridge | Owned remote worker registration/epoch lifecycle. Unsuitable as a passive selected-Desktop observer. |
| R25 main TS SDK; Python SDK; removed V2 | H07/H08 ownership profiles. Current Context7 V2 example does not reopen the package's removed interface. |
| R26 Remote Control | Remote view of opted-in local execution, not new cloud execution or a generally callable peer API. |
| R27 Channels; permission relay | Configured session event ingress and optional reply. Permission delegation is a separate authority; busy drop/group/hold needs its own evidence. |
| R28 Routine API | Experimental new cloud-session trigger; unsuitable for targeting an existing native task. |
| R29 Projects; Dispatch | Distinct product-owned conversations retained outside counted Code endpoints until mapping is established. |
| R30 Agent View, background CLI, --desktop, local resume, teams, subagents | Views, main/worker lifecycles, H10/H11, and local transition profiles. No common arbitrary Desktop/cloud route. |
| R31 hooks, transcript readers, Desktop host/renderer readers, observer prototype | Observation layers; no actuator and no complete applied-state guarantee. |
| R32 ACP v1; ACP v2 draft; CAP draft | Three protocol entries; load/replay, resume, acceptance, and completion differ. No native endpoint identity follows. |
| R33 ACPX; codex-acp; claude-agent-acp | Host queue/watch plus two provider adapters. Adapter-owned tasks, loaded reuse/cold reconnect/replacement, and native ID mapping remain distinct. |
| R34 MCP tasks; A2A v1 | Deferred-task/service protocols needing executors and native mapping. Older A2A service cohorts require version compatibility checks. |
| R35 T3 outside MCP host; Codex; Claude; Cursor adapters | Host access plus T01/T02 Wave 1 populations and Cursor Wave 2. Outside callers cannot inherit in-thread delegation identity. |
| R36 OpenClaw Gateway/external conversations; MCP serve; ACP binding; local Codex branch; paired-node Codex continuation | Five distinct profiles. OpenClaw tasks stay Wave 3; eligible paired-node native continuation may be a Wave 1 fabric. Local branch is unsuitable as source-task continuation. |
| R37 Hermes HTTP sessions/runs; ACP; CLI history; tools MCP | Four routes. Hermes tasks stay Wave 3; tools/history are not native inboxes; unknown-ID ACP resume can replace. |
| R38 Agent Bridge Codex; Claude | Two adapters and distinct source cohorts. Explicit binding required; delivered may mean turn start rather than model result. |
| R39 Intercom Claude broker; Codex daemon | Registered peers and sidecars. Scheduling acknowledgment can precede execution; Codex fallback can replace a task. |
| R40 mcp-agents; R41 Forge | One-shot CLI/review workers versus created PTY control. Unsuitable for arbitrary preserved Desktop/cloud owners; terminal buffer is partial inspection. |
| R42 AI Functions | Coordinator plus separate Codex SDK owner. Idle notify buffers without wake; active notify is user-input steer; runtime/coexistence mapping unresolved. |
| R43 emmsixx t3code-mcp; gfsaaser24 t3-code-agent-mcp | Two connectors to T3-owned threads. Operation-journal versus HTTP/WebSocket orchestration; selected deployment/schema required. |
| R44 cross-agent_mcp | Transcript discovery and resume/panel shims. Recency and resumed process do not prove exact active owner. |
| R45 Claude Relay; cc-dm; cc-tap; tmux-ccm | Four adapters: registered relay, SQLite Channel, Remote Control user-role sender, pane/spool controller. Preserve registration/modal/busy limits; none establishes arbitrary Desktop/cloud attachment. |
| R46 claude-a2a; Hybro adapters; Hybro Hub; A2A Nexus; Superharness | Five service/relay/dispatcher candidates. Host/service IDs need native mapping; creation of managed workers is not independent native-peer attachment. |
| R47 react-agent-harness | Framework-owned provider sessions; unsuitable as native cross-harness proof. |
| R48 AXI; Recensa; Rolecasting; app-observer proposals | Presentation, indexing, route guidance, and evidence layers. They cannot send/wake or infer nondelivery from silence. |

The retained revisions remain authoritative only for their supplied claims: Codex 092d3acd, TS/Python SDK metadata 0.162.1; Claude Code 2.1.296, TS SDK 0.3.296, Claude ACP SDK 0.3.293; T3 5ce5a8f; OpenClaw v2026.10.1; Hermes v0.21.6; ACPX v0.19.4; Agent Bridge Codex v4.10.0; AI Functions 145efc8; and the individual third-party pins in the comparison. Development-head refreshes do not silently replace those cohorts.

## Every directed association

For each ordered pair (caller, receiver) of distinct register records, create two lifecycle slots: **preexisting target** and **controller-created target**. Apply the receiver row below, then the caller-access column. This Cartesian rule accounts for all 506 associations without claiming any is reachable.

| Receiver class | Candidate families | Required caller-side association |
| --- | --- | --- |
| C01/C02/C03 | Actual owner R05/R06; R01 only when genuinely exposed; bound R38/R39 alternatives | Caller must expose the actuator, reach the owner's transport/store, preserve authority and bind the native target. A different local server cannot impersonate that owner. |
| C04/C05/C06/C07 | R04/R09/R10/R05; R33 and managed-worker alternatives as separate ownership profiles | Caller must own or reach the actual executor. Stored resume and active-owner attach are separate contracts. |
| C08/C09 | R13 existing UI route; R12 creation/inspection; service-specific R14 bindings | Actual product/backend ID mapping and automated caller/readback route. No general follow-up transfers from creation/status. |
| C10 | R02 | Actual native leader/child membership. All outsiders retain unassessed direction records rather than borrowing native child tools. |
| H01/H02/H03/H04 | R19 where app-exposed; R20/R21 eligible native peer; opted-in R27/R38/R39/R45 | Current sender schema, exact query/host/namespace, admission, origin, and return path. A local socket does not establish remote ingress. |
| H05/H07/H08 | Owned CLI/query R25/R30; R33/R46 managed alternatives | Exact process/query ownership, resolved native ID, result reader, and preservation conditions. |
| H06 | Unassessed IDE route | A current versioned outside-input/observation contract is a prerequisite. |
| H09 | R22 exact-ID CLI plus separate reader; R23 active browser client | Actual caller authentication/equipment, bound remote session, initialization scope, receiver/result acquisition, and cloud continuation. |
| H10/H11 | Native child/team contracts R20/R30 | Parent/team membership and actual target IDs; later independent reply needs its own route. |
| T01/T02 | R35 outside HTTP MCP/provider adapter; separately R43 | Environment reachability, OAuth scope/mode ceiling, selected deployment tool schema, and T3/provider/native ID chain. In-thread delegation is not an outside-caller capability. |

Caller profiles further specialize every row:

- Local desktop/terminal/IDE callers need actual exposed tools, reachable transport, account grant, and owner binding; a shell declaration is insufficient.
- Headless/SDK/adapter callers need a declared executor/configuration and permitted credentials/network path. Ownership of their own worker supplies no foreign-owner access.
- Cloud callers need actual egress and credential/tool exposure; there is no default cloud-to-local listener association.
- T3 callers need the real T3 thread identity for in-thread operations; outside OAuth callers use the outside contract and its ceiling.
- Remote viewers use the actual executing owner as the caller. The phone/browser is a view or controller interface, not silently another agent task.

For any unresolved binding, the applicable operation remains ? even if its receiver mechanism is K. A reverse direction is another record. Same-family directions remain in scope; equal vendor/model names do not collapse owners. An unsupported actuator may be U for that route while the overall direction remains open for another candidate.

## Counts and selected cohort

The proposed count is 10 Codex variants + 11 Claude variants + 2 T3 provider populations = 23 records. Ordered distinct associations total 23 × 22 = 506; two lifecycle slots give 1,012; six operation slots give 6,072 potential entries. These are enumeration counts, not success counts. Creation is inapplicable to the addressed preexisting target, so its slot records – rather than a pass.

The proposal deliberately retains C09 separately pending cloud-ID reconciliation. Merging only C08/C09 would give 22 records, 462 directions, and 924 lifecycle slots; it requires evidence first. Excluding the three parent/team child variants from a main-task-only view gives 20 records, 380 directions, and 760 slots while preserving the excluded records in another view. Neither change is adopted here. Unresolved peripheral populations could increase counts after their exact inclusion and identity contracts are decided.

The original five-endpoint/20-direction inventory is a dated projection. The [cohort contract](https://github.com/nisavid/provingkit/issues/540#issuecomment-6119910041) selects these six direction families and eight preparation slots:

| Selected direction family | Register location | Selected profile slots |
| --- | --- | --- |
| Claude Desktop Code → ChatGPT Codex | H01 → C01 initially | One independently opened peer notification/receipt slot. H02/H03 need additional caller profiles. |
| ChatGPT Codex → Codex terminal | C01 → C02 peer | One independently opened peer slot; one controlled-worker slot. |
| Claude Desktop Code → Codex terminal | H01 → C02 peer | One independently opened peer slot; one controlled-worker slot. |
| ChatGPT Codex → Claude Cloud | C01 → H09 | One existing-cloud work/result slot. |
| Claude Desktop Code → Claude Cloud | H01 → H09 | One existing-cloud work/result slot. |
| Codex terminal → Claude Cloud | C02 → H09 | One existing-cloud work/result slot. |

The two controlled-worker slots expand into C04/C05/C06/C07 or adapter-owned realizations after candidate selection. They cannot inherit C02's independently running terminal identity. Thus six direction families/eight producer slots are stable planning labels; they are not yet six fully bound atomic edges/eight deployment profiles. Direct CLI, Python/App Server, and ACPX alternatives remain candidates within those slots, with separate actual endpoint and ID bindings. The native Codex controlled-worker check is a same-harness control, not an extra cross-harness direction.

## Proposed follow-up prerequisites

These are research proposals for the coordinator, not new tickets or adopted methods.

1. **Resolve the remaining source mappings.** Compare selected current T3 paths with v0.0.45 and 5ce5a8f; inspect managed-provider/supporting modules and complete outside tool handlers where needed. Current adapters and TypeScript root exports are covered below. CLI/IDE/messaging and SDK browser/bridge refreshes remain incomplete. Bind TS 0.3.296 and Python 0.2.165 separately; the TypeScript root has no named unstable V2 exports.
2. **Settle endpoint granularity before maintained counts.** Decide whether counts denote operational variants or underlying native populations; establish C08/C09/legacy/service mappings, main versus child views, Desktop local/SSH/WSL aggregation, SDK/browser/bridge/runner ownership, and Work/Projects/Dispatch scope. Keep unanswered mappings explicit.
3. **Load the reviewed catalog procedure.** [Issue 552](https://github.com/nisavid/provingkit/issues/552) supplies the producer prerequisite for updating-cross-harness-catalog. Its reviewed revision was not supplied or verified here. The [comparison/reaction join](https://github.com/nisavid/provingkit/issues/569) owns maintained reconciliation and generated counts/views. This research completes only a frozen handback.
4. **Chart the uncovered Wave 1 source/profile work.** Add IDE, remote-host/Desktop SSH/WSL, native child/team, T3 existing/created, reverse/local/cloud directions, and exact caller access investigations as separately bounded work after the governing scope decision. Do not silently expand the eight first-cohort probes. Preserve independent first findings before peer exchange.
5. **Prepare concrete fixtures and probes through the existing gates.** [Preparation](https://github.com/nisavid/provingkit/issues/570), [fixture authorization](https://github.com/nisavid/provingkit/issues/571), [actual binding and probe review](https://github.com/nisavid/provingkit/issues/572), and [operation authorization](https://github.com/nisavid/provingkit/issues/573) must precede private reads or live sends. Each packet needs exact caller/receiver/owner/version/native-wrapper IDs, text, evidence reader, authority, provider footprint, resource admission, stop/restoration, and cost accounting.
6. **Keep six-operation gaps after basic success.** Later correlated reply, creation observability/first execution, separate inspection status/results, strict native continuation, idle/busy, unloaded/restart, unknown-outcome reconciliation, and failure/recovery remain explicit prerequisites. The [Desktop route](https://github.com/nisavid/provingkit/issues/212) retains acknowledgment and its stronger applied-state preservation requirements.

I applied research and capturing-agent-procedures as a consumer of the frozen comparison/accepted contracts. I made no equipment or catalog change and claimed no reviewed catalog-procedure revision. Useful corrections for the existing workflow owner are: bound source acquisition before reading recursive inventories, bind SDK language to its bundled runtime, represent remote views separately from execution owners, and preserve direction-family expansion when controlled candidates create a different population. Their adoption remains an owner decision.

Complete coverage: the five supplied inputs, all 48 retained registry families and named subroutes, the six selected direction families/eight preparation slots, and a finite rule assigning all proposed ordered pairs explicit profiles and gaps. Incomplete coverage: the remaining Claude interfaces, T3 release applicability and supporting modules, backend equivalence, complete public-surface discovery, caller access, independent later reply, and every live qualification. The next comparison must reconcile granularity and remaining source mappings before these research counts become maintained coverage.