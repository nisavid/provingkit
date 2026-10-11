# Shared-fabric cross-examination addendum

The shared inventory remains a set of complementary partial candidates. Two corrections change how its continuation and notification rows should be used: Hermes ACP can create a replacement session during resume, and AI Functions notification does not wake an idle Codex thread. Intercom receipt and resumed-process ownership also need narrower interpretations before any probe.

## Evidence boundary

I verified and read all three frozen FIRST reports. Their SHA-256 identities are:

- Claude: `77756cf1add1b5da1f55cd776164c61a91dbbbaa1bc8f44c0f9ab5b175cf450d`.
- OpenAI: `05833169a237ec7d78cf3d4eeb19d35217148836b8811e6cc5d71f487d67186d`.
- Shared: `ecae97787a6b313a494aabe69036ddd19b85dc05eb1a39a830008cf8732d95c8`.

This addendum preserves those reports and records corrections alongside them. The Provingkit baseline remains [34ab07d80ace058d9c009c79bd810f75d36bc0ac](https://github.com/nisavid/provingkit/tree/34ab07d80ace058d9c009c79bd810f75d36bc0ac). Public sources were examined on 2026-10-11. The named release tags and commits below identify the source actually read; they do not identify an installed executor or establish latest-version compatibility.

I used the installed research and capturing-agent-procedures skills. Firecrawl tools were unavailable. Context7 supplied public ACP documentation leads, which I checked against versioned primary source; unauthenticated public fetches supplied the implementation excerpts. A direct Claude documentation fetch returned 403; the public browser reader supplied the owning page. No researched adapter or backend implementation was executed, and no private task, account, configuration, receiver, or live operation was inspected. These findings are documented or source-examined and remain unqualified.

## Claims checked and corrections

### ACP and ACPX: reconnecting, reusing, and creating are different outcomes

ACP v1 at schema-v1.25.0 gates load and resume on advertised capabilities. Load replays history; resume restores context without replay. Neither operation identifies an arbitrary native application's current executor. [Versioned session contract](https://github.com/agentclientprotocol/agent-client-protocol/blob/schema-v1.25.0/docs/protocol/v1/session-setup.mdx)

ACPX v0.19.4 distinguishes four cases: a missing scoped record makes an ordinary prompt fail; an already loaded session can be reused; reconnecting a dead agent can fall back to a new session; an imported record requires its provider session to load. Busy prompts enter its serial queue, and no-wait returns queue acknowledgment. The FIRST report's fallback warning is supported, but it must not be simplified into either “every prompt creates” or “resume preserves.” [CLI contract](https://github.com/openclaw/acpx/blob/v0.19.4/docs/CLI.md)

The adapter matters. At codex-acp `202e66e63343ec4f5a5e35ab590251d813d129ca`, the inspected resume branch propagates failure separately from new-session creation. Its default connection launches a Codex App Server child. That supports a stored-native-thread continuation candidate, not an established connection to Desktop's existing server. [Session branch](https://github.com/agentclientprotocol/codex-acp/blob/202e66e63343ec4f5a5e35ab590251d813d129ca/src/CodexAcpServer.ts#L831), [process connection](https://github.com/agentclientprotocol/codex-acp/blob/202e66e63343ec4f5a5e35ab590251d813d129ca/src/CodexJsonRpcConnection.ts#L34)

At claude-agent-acp `4e1fc1e8df2b9af3b1b2d6880ba90c5862283ba8`, an existing query is reused only when its session fingerprint matches. Changed session parameters cause teardown and SDK query recreation with resume. Its sign-out recovery also has a specific never-persisted-session fallback that creates fresh context under the same ACP ID. This is narrower than arbitrary load failure, but it shows why ID equality alone cannot prove preserved context or execution. These paths agree with the Claude report's distinction between SDK continuation and reaching a running Desktop/cloud executor. [Reuse and recreation](https://github.com/agentclientprotocol/claude-agent-acp/blob/4e1fc1e8df2b9af3b1b2d6880ba90c5862283ba8/src/acp-agent.ts#L9329), [sign-out recovery](https://github.com/agentclientprotocol/claude-agent-acp/blob/4e1fc1e8df2b9af3b1b2d6880ba90c5862283ba8/src/acp-agent.ts#L3639)

**Impact:** retain ACP/ACPX for controlled workers and compatible stored sessions. Existing-task continuation needs native identity, context, and executor evidence. An outer strict-resume policy cannot establish that an adapter's successful response actually preserved the requested session.

### T3: development-source coverage does not establish release or caller coverage

I reread the outside-agent contract and caller checks at T3 `5ce5a8f658b229c36fc4dc371bb4dc4157500c00`. Outside OAuth clients can address supported T3 operations with explicit project/thread IDs and approved mode ceilings. They have no calling T3 thread. The delegated-task tools explicitly require an agent inside a T3 thread. The same two outside-agent documentation/access-file paths return 404 at v0.0.45; that supports the FIRST report's version warning, not a claim that the release has no MCP surface whatsoever. [Outside callers](https://github.com/pingdotgg/t3code/blob/5ce5a8f658b229c36fc4dc371bb4dc4157500c00/docs/user/outside-agents.md), [caller checks](https://github.com/pingdotgg/t3code/blob/5ce5a8f658b229c36fc4dc371bb4dc4157500c00/apps/server/src/mcp/threadAccess.ts), [delegated tools](https://github.com/pingdotgg/t3code/blob/5ce5a8f658b229c36fc4dc371bb4dc4157500c00/apps/server/src/mcp/toolkits/orchestrator/tools.ts#L64)

The guide requires an internet-reachable environment for hosted callers; a tailnet address only serves callers on that tailnet. That documentary route does not establish connector availability or access from a particular Codex Cloud or Claude cloud task. T3 Codex, Claude, and Cursor remain host-managed endpoint populations. Their native backing IDs do not make independently opened ChatGPT, Desktop Claude, or Cursor tasks into T3 threads.

**Impact:** retain T3 native MCP and both third-party T3 connectors as distinct candidates. Pin a deployment and caller profile before comparing tools. Outside thread creation/message support must not inherit in-thread delegation capabilities.

### OpenClaw: local branching and paired-node continuation remain separate profiles

OpenClaw v2026.10.1 explicitly documents that Gateway-local Continue as branch creates a canonical thread from bounded visible history and never resumes the source. It omits the source's reasoning and tool history. Eligible paired-node continuation instead resumes the exact native thread through that node's Codex CLI and returns final text; it requires the stated node capabilities and operator access. It is not the streaming Gateway-local App Server path. Ordinary attached turns can resend model/policy choices; supervised bindings have different restoration rules. [Thread and supervision contract](https://github.com/openclaw/openclaw/blob/v2026.10.1/docs/plugins/codex-harness-runtime/threads.md)

The release queue contract separately distinguishes steer acceptance, transcript commitment, and later model consumption. A rejected steer can become a queued follow-up, while an unconfirmed send is not automatically replayed. [Queue contract](https://github.com/openclaw/openclaw/blob/v2026.10.1/docs/plugins/codex-harness-runtime/queue-and-feedback.md)

**Impact:** the FIRST distinction is confirmed. Local branching contributes creation and later continuation of the new branch. Paired-node continuation is an exact-ID candidate for eligible stored or idle native tasks. Neither supplies a qualified busy native-peer route or preservation result. OpenClaw Gateway sessions, external conversations, MCP serve, and ACP conversation bindings remain separately bounded candidates.

### Hermes: correct the ACP resume row

At Hermes v0.21.6, ACP `resume_session` creates a fresh session when its manager cannot find the requested ID. The manager generates a new UUID and AIAgent. In contrast, `load_session` returns no session for an unknown ID. Both operations update cwd and attach requested MCP servers, so they are not passive inspection. The response helper can also catch a history-replay exception and return after only partial replay. The FIRST table's generic “implements resume” description is therefore insufficient for exact continuation: **do not count a successful resume response or load response alone as preserved identity and complete history.** [ACP handlers and response helper](https://github.com/NousResearch/hermes-agent/blob/v0.21.6/acp_adapter/server.py#L590), [session manager](https://github.com/NousResearch/hermes-agent/blob/v0.21.6/acp_adapter/session.py#L176)

The HTTP run path selects a Hermes session, can resolve its current continuation tip, creates a distinct run ID, and has explicit idempotency handling. For a selected canonical Bot Chat held by a live Desktop owner, the inspected branch routes through that owner's mailbox and receipt path. This is a useful Hermes-owned existing-session lead. It does not bind a foreign Codex or Claude task. Run steering returns a conflict when the run is not running or cannot accept steering. [Run admission and live-owner branch](https://github.com/NousResearch/hermes-agent/blob/v0.21.6/gateway/platforms/api_server_runs.py#L638), [steer gate](https://github.com/NousResearch/hermes-agent/blob/v0.21.6/gateway/platforms/api_server_runs.py#L1219)

**Impact:** retain Hermes HTTP and ACP as separate later-wave endpoints. Record requested session, resolved session, run, and owner identities separately. Hermes CLI/history and tools MCP remain supporting surfaces; the FIRST report establishes no general foreign-native-task inbox through them.

### Agent Bridge and Intercom: receipt boundaries differ

Agent Bridge v4.10.0 Codex delivery defers a detected foreign active turn. Optional steering is restricted by its code to a bridge-owned turn. An accepted turn start with a returned turn ID finalizes its delivered state; this is earlier than model acknowledgment or completed work. Ambiguous transmission takes a reconciliation path without automatic resend. These are source branches, not independently demonstrated reliability guarantees. [Delivery implementation](https://github.com/EthanSK/agent-bridge/blob/v4.10.0/codex-channel/src/delivery.js#L942)

The Claude FIRST report inspected Agent Bridge head `f45fdfffafd9bbe9b47e16aa8ddd17119d399595`, while the shared Codex findings used v4.10.0. Keep those observations version-specific; neither qualifies the other's adapter or the current deployment.

Intercom's broker at `7de76e5d4f6461b007b19dfc5dbcf11928868adc` emits delivered after recipient acknowledgment. The Codex daemon at `ff1f0e2258ded8c81ae6fcf33048c78a7f8580fe` acknowledges immediately after scheduling routing, before the serial queue waits for idle, starts the turn, and collects completion. Its eventual reply uses the request's message ID. Its resume catch clears the old thread ID and creates a new thread. Therefore broker delivered can precede both model work and replacement-thread creation. [Broker acknowledgment](https://github.com/dataforxyz/agent-intercom-claude/blob/7de76e5d4f6461b007b19dfc5dbcf11928868adc/broker/broker.ts#L1823), [Codex acknowledgment](https://github.com/dataforxyz/agent-intercom-codex/blob/ff1f0e2258ded8c81ae6fcf33048c78a7f8580fe/codex/bridge-daemon.ts#L320), [resume, queue, and reply](https://github.com/dataforxyz/agent-intercom-codex/blob/ff1f0e2258ded8c81ae6fcf33048c78a7f8580fe/codex/bridge-daemon.ts#L473)

Intercom's Claude native bridge acknowledges after its native-send helper returns and requires a native SendMessage reply for the return path; ordinary assistant output stays local. The current owning Claude reference describes busy delivery between tool calls and inbound hold/refuse behavior. Those native controls remain dependencies of this adapter. [Native bridge](https://github.com/dataforxyz/agent-intercom-claude/blob/7de76e5d4f6461b007b19dfc5dbcf11928868adc/claude/native-bridge.ts#L66), [Claude messaging contract](https://code.claude.com/docs/en/cross-session-messaging)

**Impact:** retain explicit Agent Bridge bindings and registered Intercom peers. Correct any reading of “receiver acknowledgment” as model acknowledgment. Report broker receipt, native admission, queueing, receiver reply, and requested-work result separately. Neither registration nor a broker label establishes an arbitrary independent Desktop/cloud target.

### AI Functions: exact resume selector exists; idle notification and ownership remain narrower

At AI Functions `145efc8398dc1a0d91fface870a240e6d813a0b2`, `resume_thread_id` is passed directly to the Python SDK's resume call. The wrapper creates its own AsyncCodex client and runtime-tools server, passes template configuration into resume, and closes on failure; this inspected branch does not substitute a new thread after failed resume. A fork selector takes precedence and creates a different identity. [Connection branch](https://github.com/strands-labs/ai-functions/blob/145efc8398dc1a0d91fface870a240e6d813a0b2/src/ai_functions/codex/codex.py#L672)

**Correction:** Codex `notify()` schedules user-input steering only while this wrapper has an active turn. Otherwise, or after a failed steer, it buffers text for the next execute cycle. It starts no cycle itself, and teardown drops pending buffered input. Its return is therefore neither idle wake nor delivery evidence. [Notification implementation](https://github.com/strands-labs/ai-functions/blob/145efc8398dc1a0d91fface870a240e6d813a0b2/src/ai_functions/codex/codex.py#L492)

The wrapper's docstring asserts a cross-process single-writer refusal. OpenClaw v2026.10.1 explicitly documents the absence of an exclusive cross-process runner/approval-owner lease. AI Functions permits `openai-codex>=0.147.0`, rather than fixing this behavior to the OpenAI FIRST report's 0.162.1 runtime. The inspected connection branch supplies no independent ownership arbitration. I did not resolve that conflicting upstream ownership claim into a runtime guarantee. Actual owner coexistence remains a blocking fact for an existing active-task profile. [Wrapper assertion](https://github.com/strands-labs/ai-functions/blob/145efc8398dc1a0d91fface870a240e6d813a0b2/src/ai_functions/codex/codex.py#L61), [dependency range](https://github.com/strands-labs/ai-functions/blob/145efc8398dc1a0d91fface870a240e6d813a0b2/pyproject.toml#L67), [OpenClaw ownership limitation](https://github.com/openclaw/openclaw/blob/v2026.10.1/docs/plugins/codex-harness-runtime/threads.md#L61)

The OpenAI comparison offers two different mechanisms: its 0.162.1 queue wakes loaded eligible threads, while Python ExternalMessage is documented to start an idle turn or join an active regular turn using tool-output representation. AI Functions user-input steering is not evidence that it uses ExternalMessage. These remain separate adapter proposals, with source names supplying no identity or consent proof. [Queue source at 092d3acd](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/ext/queue/src/service.rs#L472), [ExternalMessage contract](https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/sdk/python/docs/api-reference.md#externalmessage)

### react-agent-harness: immutable source gap narrowed

The supplied direct public commit URL resolves to `6b399e57daeef6475f2dc37c11a1e8fc097ca7e4`; its patch records 2026-09-02 19:09:37 UTC and the manifest change to 0.14.0. This supplies a verified immutable comparison source. It does not prove that commit is current HEAD. Preserve the FIRST report's rate-limited current-commit observation as unresolved at that time. [Commit](https://github.com/ramannanda9/agent-harness/commit/6b399e57daeef6475f2dc37c11a1e8fc097ca7e4), [dated patch](https://github.com/ramannanda9/agent-harness/commit/6b399e57daeef6475f2dc37c11a1e8fc097ca7e4.patch)

The pinned README describes provider access and its own persistent sessions; its Claude adapter explicitly uses direct provider requests rather than a Claude CLI session actuator. Keep it as a framework/host lead, unsuitable as demonstrated native-peer coordination. Its credential and provider-route design remains an unresolved concern for separately classified review, not an accepted account substitution. [Pinned README](https://github.com/ramannanda9/agent-harness/blob/6b399e57daeef6475f2dc37c11a1e8fc097ca7e4/README.md#L367)

## Complementary combinations and retained candidates

The reports support comparison of several compositions, without selecting one:

- A native Claude receiver route plus a callable wrapper and correlated return path could address eligible existing peers. Claude cloud follow-up and the SDK browser event/delivery lead remain distinct candidates from the Claude FIRST report; browser authentication, initialization effects, and current executor binding are unresolved.
- A reachable owning Codex App Server plus queue or ExternalMessage could support existing eligible Codex work. A separately spawned SDK/ACP process needs its own ownership analysis. The OpenAI FIRST report's unresolved existing-cloud-task follow-up interface is not repaired by wrapping local execution.
- ACPX plus pinned adapters can provide common controlled-worker queue/watch operations, provided each adapter's replacement and context behavior is exposed.
- T3, OpenClaw, and Hermes can provide their own host-managed populations. None automatically imports the native tasks already running elsewhere.
- Agent Bridge, Intercom, Relay, or an A2A/MCP service can supply registration, transport, and return correlation. A bounded observer can add positive evidence; it cannot supply the missing actuator or turn silence into nondelivery.

Every FIRST candidate remains visible. ACP v2 and CAP remain draft/supporting leads; MCP and A2A supply protocols rather than native-task identity. OpenAI's Claude plugin remains delegation/import support; mcp-agents and Forge remain created-worker or terminal routes. Both T3 connectors, cross-agent_mcp, Claude Relay, cc-dm, and tmux-ccm remain partial adapters with their recorded population limits. cc-tap remains unsuitable for the claimed peer-origin profile. claude-a2a, Hybro's adapters and Hub, A2A Nexus, and Superharness remain service/dispatcher candidates. AXI, Recensa, Rolecasting guidance, and observer proposals remain supporting layers. react-agent-harness retains the disposition above. Unexamined rows are retained at their FIRST evidence level, not freshly qualified by this addendum.

The shared report's claim that a small wrapper minimizes host state is a design hypothesis, not a measured cost result. Research time and documentation-retrieval costs were not instrumented. No source composition establishes all six operations for both independently opened and controller-created tasks, and no successful direction establishes its reverse.

## Smallest proposed checks

These are proposals for a later authorized increment. No fixture, installation, activation, or provider turn was run here.

| Candidate | Smallest discriminating check | Evidence and unmeasured costs |
| --- | --- | --- |
| ACPX and each selected adapter | First use a fake endpoint for loaded reuse, missing ID, failed reconnect, and replacement success; later bind one disposable stored native session. | Capture wrapper/native IDs and a history marker, not ID equality alone. Adapter/runtime pinning, subprocesses, queue journal, setup time, and provider usage remain unmeasured. |
| T3 | Compare selected-deployment tool schemas for an outside OAuth caller and a live in-thread caller; then one consented exact T3 thread message. | Capture available operations, mode ceiling, host/native/run IDs, and correlated result. OAuth setup, reachable hosting, and model turns are unmeasured. |
| OpenClaw | Treat one local branch and one eligible paired-node continuation as separate fixtures. | Require new-ID evidence for the branch and same-native-ID/result evidence for the node; do not reuse one result for the other. Gateway/plugin/node setup and execution costs are unmeasured. |
| Hermes | Exercise unknown-ID load/resume and interrupted history replay with a fake manager; later one owned HTTP session/run, including the live-owner path if selected. | Capture requested/resolved IDs, complete history evidence, admission, owner receipt, and result. Server/profile setup, storage, and provider costs are unmeasured. |
| Agent Bridge | On a fake App Server, distinguish foreign-busy deferral, bridge-owned steer, and a lost start response; later one opted-in existing task and explicit reply. | Preserve message/turn IDs and unknown outcome. SSH pairing, receiver/lease processes, recovery storage, and receiver turns are unmeasured. |
| Intercom | Make routing fail after daemon acknowledgment and make resume fail before fallback creation; later one registered ask/reply pair. | Show broker delivered independently of turn result and record replacement native ID. Broker, sidecar, registration, and model costs are unmeasured. |
| AI Functions | Fake idle notify, failed steer, teardown, exact resume failure, and fork precedence; resolve the runtime's ownership contract before a separately approved coexistence fixture. | Capture buffer versus wake and native owner/process identity. SDK/runtime, tool server, coordinator, and execution costs are unmeasured. |
| Native actuator plus common wrapper/observer | Carry one inert correlation token through a single direction, first idle and then busy if authorized. | Separate submission, admission, queue/hold/refusal, receiver acknowledgment, and domain result. Additional tool calls, observer scope, and model usage are unmeasured; reverse delivery is a separate check. |

The accepted Codex-to-Claude Desktop preservation contract still requires its complete applied-state and busy-continuity evidence. These basic proposals do not replace it. Restart and replay need separately scoped checks. The portfolio's later basic-probe reassessment limit does not apply to this source review and cannot supply completion.

## Open facts and procedure handback

The remaining consequential facts are the actual caller's route; installed adapter/runtime compatibility; consent-bound target and native-owner identity; busy admission and reply behavior; complete context/model/account/permission/workspace preservation where required; recovery outcomes; and measured setup/operation costs. T3 release applicability, AI Functions owner coexistence, Hermes replay/replacement handling, and current-HEAD identity for react-agent-harness remain explicit limits.

Credential scope, public ingress, sender assertion, permission representation, and cross-process ownership concerns require separately classified review if selected. No security property is established here.

For procedure capture, the proposed consumer rule is to load the frozen inventories and reviewed addendum together, bind wrapper/host/native/turn identities and the actual owner, classify replacement creation separately, and require receiver/result evidence beyond transport receipts. Maintained procedure placement, invocation pointers, independent review, publication, and installation remain with the coordinator. No installed convention was changed. The next decision is the concrete operation and population to authorize for a probe.
