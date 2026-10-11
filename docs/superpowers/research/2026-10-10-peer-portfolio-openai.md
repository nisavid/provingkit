# OpenAI coordination surfaces: first inventory

The strongest OpenAI candidates are the desktop app's exposed chat tools for app-reachable tasks, the shared app-server queue for existing local Codex sessions, and app-server or SDK control for a controller's own threads. Codex Cloud has documented creation and follow-up workflows, but the inspected CLI supplies creation and inspection rather than a general existing-task follow-up command. None of these observations qualifies a live directed pair.

This is the independently prepared first report for [Research Wave 1 OpenAI control surfaces](https://github.com/nisavid/provingkit/issues/534), under the [cross-harness portfolio](https://github.com/nisavid/provingkit/issues/533). It covers the ChatGPT desktop app in Codex mode, Codex CLI/TUI, and Codex Web/Cloud, with caller constraints for the other Wave 1 populations. The public-source observation window was 2026-10-11 UTC, corresponding to 2026-10-10 in America/New_York. No findings were exchanged with the other research lanes before this report.

## Evidence and identities

The authorized increment is a source-backed inventory and proposed basic checks. I verified the supplied request and common input digests, read the bound dated report and relevant atlas entries, and used the research and capturing-agent-procedures skills. The repository context was the supplied immutable Provingkit baseline [34ab07d](https://github.com/nisavid/provingkit/tree/34ab07d80ace058d9c009c79bd810f75d36bc0ac). Publication, review, and tracker changes remain with the coordinator.

Evidence labels have narrow meanings:

- **Documented:** freshly fetched first-party documentation describes the behavior.
- **Source-examined:** inspected public source or schema at the revision cited.
- **Exposed schema:** a tool declaration was supplied to this research session; the tool was not called.
- **Historical:** the bound September 25 report or October 10 atlas records an earlier observation.
- **Proposed:** an inference or future check.
- **Synthetic and live:** no synthetic test, server connection, task/account read, task creation, message, or provider execution was performed in this lane.

| Surface identity | Actual observation | Limit |
| --- | --- | --- |
| Codex CLI and app-server | GitHub's latest release endpoint returned [rust-v0.162.1][release], published October 9, 2026 at 19:44:51 UTC. Its annotated tag resolves to commit `092d3acd6bec3e3a14bdc7e7a2810ab628ab759d`. The source claims below use that commit. | No installed binary, running daemon, GUI executor, or cloud executor was identified by this lane. |
| Codex development branch | The public main branch returned [cc7ba336][main], committed October 10 at 22:28:01 UTC. | This identifies observed development drift; it does not turn the release-source findings into claims about every later commit. |
| TypeScript SDK | [npm metadata][npm] returned 0.162.1, published October 9 at 19:51:57.415 UTC, depending on `@openai/codex` 0.162.1. | Package metadata was read; the package was not installed or executed. |
| Python SDK | [PyPI metadata][pypi] returned 0.162.1; the wheel upload was October 9 at 20:00:27.613413 UTC. It depends on `openai-codex-cli-bin==0.162.1`. | The release-tree development manifest still says 0.0.0-dev and names an older runtime dependency. Published metadata and source-tree defaults must not be conflated. |
| OpenAI Codex plugin for Claude Code | Latest release [v1.0.6][plugin-release], published July 8, 2026 at 00:17:32 UTC; tag resolves to `db52e28f4d9ded852ab3942cea316258ae4ef346`. README and protocol map were refreshed. | No Claude Desktop/Web plugin compatibility or installed plugin instance was checked. |
| Desktop app tools | Current no-task-data declarations expose chat creation, listing, reading, waiting, follow-up, fork, handoff, and separate native child controls. | The declarations provide no app release/build identity or portable external endpoint. Their public documentation is less specific than the supplied schema. |
| Hosted products and documentation | Current pages distinguish Codex Cloud, Codex Cloud (Legacy), and ChatGPT Work with local computer access. | The fetched pages expose no immutable hosted executor revision. Access date is not release identity. |

Official documentation was searched and fetched through the OpenAI documentation connector. Context7 resolved `/openai/codex` and returned queue, resume, and SDK leads that were followed to pinned primary source. An initial Context7 invocation encountered the repository's package-manager constraint; the lookup succeeded from a neutral directory. Firecrawl tools were not exposed. A guessed chats documentation URL returned 404; the linked [Projects and chats][projects] page supplied the relevant documentation. No downloaded vendor implementation was executed.

## Capability profiles

An **independent task** was opened separately by a user. A **controller-created task** was created through the coordinating route. Either can still be user-owned; origin does not remove consent requirements.

The six operations are notification, work request, creation, inspection, reply, and continuation. A prompt can carry notification text, but that does not establish peer-origin handling. A result returned to a controller can satisfy a correlated request; it does not establish a receiver's independent ability to send a later reply into another harness.

The following matrix describes available building blocks, not tested operation success. “Full” means the exposed schema covers all six operations within the specified native child relationship. All other verdicts are partial or unsuitable for the stated profile.

| Candidate | Notify | Request work | Create | Inspect status/result | Reply | Continue | Profile and verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Desktop app chat tools | Follow-up prompt | Follow-up prompt | Create/fork | List/read/wait | Separate authorized reverse follow-up | Follow-up | **Partial:** app-reachable independent and created chats; caller access, origin, busy behavior, and external reply path need proof. |
| Native child tools | Message | Follow-up task | Spawn | List/wait and returned result | Native child messaging/result return | Follow-up task | **Full schema coverage for the native leader/child relationship; unsuitable for arbitrary independent user tasks.** |
| CLI `queue` | Queued user input | Queued user input | No | Admission ID only; use other APIs | Needs reverse route | Queued turn | **Partial:** existing eligible threads in the addressed server/store. |
| CLI/TUI `agents`, `resume`, `fork`, interactive composer | User input | User input | New/fork | Interactive overview/transcript | Interactive response | Resume/steer/queue | **Partial:** interactive control; automated caller and exact server binding remain separate. |
| `codex exec` / `exec resume` | Prompt input | Noninteractive job | New execution thread | JSON events/final output | Result to invoking process | Resume stored ID | **Partial:** controlled jobs and stored continuation; arbitrary live GUI attachment unestablished. |
| App-server thread/turn API | Input or tool output | Start/steer turn | Start/fork | Read/list/status/events | Result stream; reverse route needs adapter | Resume/start/steer | **Partial overall:** broad controller lifecycle; independent attachment requires the owning server and eligible thread. |
| App-server queue API | Queued user input | Queued input | No | Queue list plus thread events | Needs reverse route | Start queued item | **Partial:** experimental queue management, with explicit eligibility limits. |
| App-server tool output / Python `ExternalMessage` | Explicit external content | External content within authorized work | Via enclosing SDK/API | Saved items and turn result | Correlation and reverse delivery remain caller work | Starts idle turn or joins active regular turn | **Partial:** useful peer-content representation, not an identity or authority proof. |
| App-server `thread/inject_items` | Raw history mutation | Does not start work | No | Separate read | No return route | Separate turn needed | **Unsuitable as the first notification candidate:** history insertion alone does not deliver an active notification and requires careful role handling. |
| TypeScript SDK | Prompt | Run/stream | Start thread | Run result/events | Result to application | Resume/run | **Partial:** local process wrapper; no demonstrated arbitrary GUI or Cloud attachment. |
| Python SDK | Prompt or ExternalMessage | Run/turn/steer | Start/fork | Read/list/stream/result | Result to application | Resume/run | **Partial:** launches local stdio app-server by default; remote attachment is not supplied by that default. |
| Remote TUI over WebSocket/Unix socket | Uses underlying turn controls | Same | Same | Same | Same limits | Same | **Supporting transport; partial:** a reachable configured server is required. |
| Managed remote control / SSH host connection | Supported client follow-up | Supported client prompt | New remote chat | Client views/results | Conversation response | Existing chat | **Partial:** documented device/client workflow; no general cross-harness agent endpoint established. |
| `codex cloud` | No follow-up subcommand inspected | New-task prompt | `exec` | `list/status/diff` | Result inspection, no later peer send | No follow-up subcommand inspected | **Partial:** creation and inspection; existing-task notification/continuation gap remains. |
| Codex Cloud web/mobile/desktop UI | Follow-up text | Task prompt | New task | Task outputs/diffs | In-task response | Follow-up | **Partial:** documented human workflow; automated sender binding and busy semantics untested. |
| Current Slack / Teams cloud delegation | Related message | Delegate repository work | Separate cloud task | Conversation/task link | Result to originating conversation | Same connected account | **Partial:** integration-created task lifecycle; no arbitrary task-ID attach established. |
| Legacy Linear integration | Thread message | Assign/mention | Cloud chat | Issue activity/chat link | Result to issue thread | Follow up in originating thread | **Partial:** integration-associated tasks; unsuitable as a general independent-peer inbox. |
| Legacy GitHub integration | Comment trigger | Review or requested fix | Fix starts legacy cloud chat | Review/task outputs | PR review/comment | Fix follow-up has its own task semantics | **Partial:** PR workflow, not general task-ID addressing. |
| OpenAI Codex plugin for Claude Code | Rescue prompt | Review/rescue | Job or imported persistent thread | Status/result | Result back through plugin | Latest rescue thread / resume | **Partial:** plugin-associated Codex work; independent GUI task attach and reverse inbox unestablished. |
| Removed `codex mcp-server` | — | — | — | — | — | — | **Unsuitable on the observed current release:** current docs state it was removed. |
| MCP client configuration / plugin MCP tools | Depends on server | Depends on server | Depends on server | Depends on server | Depends on server | Depends on server | **Supporting layer:** not itself a Codex peer-control server. |

Sources for the rows are detailed below; native app and native child rows additionally use the exposed, uninvoked schemas.

## What the native surfaces actually expose

### Desktop chat tools and native children

The supplied desktop declarations distinguish ordinary chats from native children. `create_thread` can create project, projectless, or explicitly requested ChatGPT Work cloud chats; project creation needs a project reference, and asynchronous worktree setup can return a provisional client ID. `send_message_to_thread` addresses an existing chat, keeps model/thinking settings when overrides are omitted, and requires direct human authorization. `read_thread` supports Codex and ChatGPT conversations; `wait_threads` is specifically a Codex wait surface. `fork_thread` and `handoff_thread` have additional backend and locality limits. None was invoked.

Those declarations are evidence for what this caller was offered, not evidence that another CLI or cloud agent can call the same plugin. In particular, the create target named ChatGPT Work cloud does not establish creation of a legacy Codex Cloud task, and the presence of a string-valued thread ID does not establish interchangeable identity across products. Public [desktop][app] and [project][projects] documentation also separates Work and Codex history.

The supplied native collaboration schemas expose spawn, message, follow-up, list, interrupt, and wait inside a leader's agent tree. The [subagent documentation][subagents] describes result collection, model configuration, and client-specific controls. This relationship supplies a useful controller-created profile, but it is not permission to create or steer user-owned sidebar chats.

App busy-delivery behavior was not established by these chat-tool descriptions. A native child message and a user-visible chat follow-up also have different presentation and authority implications. They require distinct instruction and runtime checks before being treated as interchangeable notifications.

### CLI queue and shared-server addressing

Release source makes `codex queue --thread <reference> --message <text>` a client of local or explicit remote app-server. It accepts a UUID or exact session name and rejects image attachments. It generates a client message ID, calls `thread/queue/add`, and prints the queued-submission and target-thread IDs. Its guard rejects `--no-daemon` without an explicit remote route and avoids an embedded-server fallback while a local daemon is running. Name lookup broadens source filters to include Atlas/ChatGPT sessions; this is a discovery implementation detail, not proof that every app task shares this server. [CLI parser][queue-cli], [queue client][queue-client].

The server permits queue storage for an eligible unloaded persisted thread, but rejects archived, ephemeral, and certain spawned-subagent cases. The queue service's wake path only considers loaded, non-interrupted threads. Automatic dispatch starts queued input only when idle; explicit queue start requires a loaded thread and can refuse an active or pending turn. Thus a successful enqueue is useful admission evidence, not proof of wakeup, receiver consumption, or completion. [Queue processor][queue-processor], [queue service][queue-service].

The protocol declares add, list, update, delete, reorder, and start as experimental. Raw API clients need the appropriate capability opt-in; generated default schemas may omit gated methods. Queue add carries `clientUserMessageId`, and returned queue objects retain it. This makes correlation possible, but does not establish duplicate suppression or exactly-once delivery. [Method declarations][protocol], [queue types][thread-types].

The [CLI source][cli] also exposes `agents` for the shared-server overview and resume/fork controls. Current [command documentation][commands] distinguishes Tab queueing from Enter steering while the TUI is busy. Those UI controls do not make PTY injection a supported structured peer API.

### App-server and SDKs

App-server exposes thread creation, read/list, resume/fork, turn start/steer/interrupt, and progress/completion events. The response to starting work and a later terminal result are different evidence. `thread/resume` can rejoin a running thread identified in that server; for a non-running thread it can load stored history. A separately launched server is not thereby attached to an arbitrary desktop process. [App-server documentation][server], [resume schema][resume-schema].

The release schema permits thread/turn overrides including model, working directory, approval policy, sandbox, and service tier. The same ID therefore does not establish preservation. The requested model, available catalog, and executed model are separate observations. This lane neither read an account/model catalog nor observed execution. [Turn schema][turn-schema], [resume schema][resume-schema].

`turn/steer` requires the active turn ID and has no model/workdir/sandbox override fields. It fails without an active turn. Queueing and steering must be qualified as different operations. App-server's transport supports stdio, WebSocket, and Unix-socket clients; the current documentation describes authentication options, experimental support, overload errors, and per-connection initialization. [App-server documentation][server].

The TypeScript SDK starts a local `codex exec --experimental-json` process, adding `resume <id>` for continuation. It forwards selected model and policy options. Its thread class collects streamed events and final results. A resumed stored thread is not evidence of a remote connection to the original active GUI task. [SDK execution source][ts-exec], [SDK thread source][ts-thread].

The Python SDK supplies thread list/read/start/resume/fork and turn handles. Its default client launches `codex app-server --listen stdio://`; a custom launch-argument override is not a documented universal desktop attachment contract. Published SDKs pin a runtime, which must be recorded separately from any ambient CLI. [Python client][py-client], [Python API][py-api], [SDK documentation][sdk].

The Python API's `ExternalMessage` is a particularly useful additional candidate. Its documented representation is tool output, below user/developer instructions, with tool and optional namespace fields. It starts a turn when idle or joins an active regular turn, persists as a function-call-output item, and allows result collection. The documentation explicitly says names do not prove sender identity or permission. This is a documented and source-declared representation, not a security certification or proof that a live receiver enforces the intended interpretation. [ExternalMessage contract][external-message], [input type][py-inputs].

Queue input, ordinary user prompts, standalone tool output, and raw `thread/inject_items` are separate candidate mechanisms. For peer notification, tool output deserves an early comparison with user-input queueing; raw history insertion should remain a deferred alternative until its context and role consequences have a concrete justification.

### Remote control and supporting layers

Managed remote control is distinct from `app-server --listen`. The CLI has foreground operation and start/stop/pair commands; source exposes connecting, connected, disabled, and errored results. A connecting result is not an established path. Pairing and daemon start would be activation, so neither was run. [Remote-control source][remote-source], [command documentation][commands].

The supported remote client workflow requires an online host, compatible clients, pairing, account/workspace alignment, and applicable workspace access. SSH connection starts a Codex app-server on the remote host. Handoff moves chat/Git state and interrupts active work; it is a migration operation rather than notification. The documented cross-host handoff excludes Codex Cloud. Restart, sign-out, sleep, and network loss affect reachability. [Remote connections][remote-docs].

A cloud agent does not gain a host route merely because the host exposes a loopback or Unix socket. It needs an authorized reachable adapter, transport, and credential mechanism. The current documentation warns that non-loopback WebSocket listeners can allow unauthenticated connections by default during rollout. Remote listener exposure, credential scope, and peer-input authority need separately classified security review before any deployment; no security property is certified here. [Transport documentation][server].

MCP in Codex supplies outgoing client access to stdio or Streamable HTTP tools. Hosted ChatGPT Work can use available plugin-backed remote tools, while local config is not automatically read by ChatGPT web. This is a possible caller layer for a separately implemented native adapter. It does not expose every desktop tool remotely. Current [MCP documentation][mcp] and [SDK documentation][sdk] should replace dated instructions that launch `codex mcp-server`.

The inspected CLI also declares execution-service, socket-relay, and API-proxy helpers; app-server exposes command/process/filesystem operations. These are supporting execution or transport leads. Their declarations do not establish independent peer task addressing. Hooks and schedules can provide triggers, but neither a trigger nor a filesystem mailbox supplies the missing receiver contract.

### Codex Cloud and integration-created tasks

Current [Cloud documentation][cloud] describes tasks started from published environments and followed up from web, mobile, or desktop. An existing task keeps its own saved state; changing a published environment affects new tasks. Environment sharing does not grant access to another person's task. The same documentation distinguishes the legacy environments used by Code Review, GitHub, and Linear. The legacy/new population association must be recorded for each real fixture. [Cloud environments][cloud-env].

The release CLI exposes exactly `exec`, `status`, `list`, `apply`, and `diff` in its cloud command enum. Creation selects an environment, branch, and one to four attempts; the inspected creation arguments do not include an explicit model. The public client implementation fetches task details, text, attempts, and diffs and creates a task. It uses a backend client and can carry a ChatGPT account ID. Those internals are source evidence for the CLI, not a supported arbitrary task API or authorization to invoke backend URLs. [Cloud CLI source][cloud-cli], [cloud client][cloud-client].

I did not find an existing-cloud-task follow-up command in that enum or establish a public general follow-up endpoint from the inspected docs. This is a bounded search result, not proof that no such API exists. Equivalence between CLI cloud task identity, current Cloud UI chats, legacy tasks, and ChatGPT Work conversation IDs remains unresolved.

Current Slack and Teams delegation creates a separate Cloud task from a connected conversation. Slack documentation requires eligible shared environments and relevant account access; related follow-ups can continue the task when they use the same connected account. Another account can create separate work. These are usable-looking integration lifecycle candidates, with result return to the conversation, but not evidence for attaching an arbitrary task ID. [Slack][slack], [Teams/cloud delegation][cloud-env].

The [Linear integration][linear] explicitly creates a cloud chat, reports activity/results, and continues the same chat from follow-ups in the originating comment thread. [GitHub integration][github] reviews a PR and can start a legacy cloud chat to fix findings. Neither documented workflow supplies a universal existing-peer inbox. These routes also require separately authorized outward messages; no connector was invoked.

ChatGPT Work with local computer access is an additional adjacent population. Current [project documentation][projects] says enabling sync applies to new tasks, preserves existing tasks' original mode, and keeps Work history separate from Codex history. It cannot be used to silently reclassify an existing Codex desktop task as a cloud-addressable conversation.

### OpenAI's Claude Code plugin and retained adjacent candidates

The refreshed plugin README describes review, adversarial review, rescue, transfer, status, result, and cancel. Rescue can continue the latest associated rescue thread; transfer imports Claude history into a new persistent Codex thread. The wrapper uses local Codex authentication and app-server. Its [protocol map][plugin-protocol] includes start/resume/list, turn start/interrupt, review, and external-session import. That is source-backed delegation support, not attachment to every independent app-owned task. [Plugin README][plugin].

The plugin's applicability inside Claude Desktop-hosted Code and Claude Code on the web was not verified. Local terminal compatibility cannot be substituted for either Wave 1 population. The first useful check is its actual resume selector and host requirements, followed only with an approved fixture and task-creation grant.

Other retained leads are preserved for the portfolio join: ACP/codex-acp/ACPX, Agent Intercom's Codex sidecar, mcp-agents, Forge, T3's Codex adapter, and AI Functions. Their descriptions in the supplied dated inventory remain **historical leads** in this report. They were not installed, probed, or independently refreshed here. The shared-fabric report must establish their current wrapper behavior; this report supplies current OpenAI dependencies against which to check their attach/create and reply claims.

## Sender reachability across Wave 1

This table covers candidate paths into the three OpenAI populations. It does not presume the caller has shell, plugin, credentials, or egress merely because that receiver has an API. Same-population cells are useful baselines, not additional portfolio pairs.

| Sender | Desktop Codex receiver | CLI/TUI receiver | Codex Web/Cloud receiver |
| --- | --- | --- | --- |
| Desktop Codex | Native chat tools where exposed; per-target identity/authorization still required. | Shared-daemon queue or app-server candidate; app/CLI server association unproven. | Cloud CLI creation/inspection, documented UI, or app cloud-chat tool only after backend identity is resolved. |
| Codex CLI/TUI | Queue/app-server only if the app's actual owning server and thread are reachable; matching folder/title is insufficient. | Queue/app-server is the strongest existing-session candidate. | Cloud CLI creates/inspects; general existing-task follow-up remains unresolved. |
| Codex Web/Cloud | No qualified route. Needs an authorized remote adapter or supported connected-host path accessible to that cloud caller. | No qualified route. A cloud-local CLI would control its own runtime unless a remote target is explicitly bound. | UI follow-up documented; autonomous sibling-task send not established. |
| Claude Desktop-hosted Code | Requires a callable native adapter and verified Codex host route. Plugin compatibility with this population is unresolved. | Shell/SDK/plugin/remote adapter is conditional on actual caller equipment and authority. | Cloud CLI or external integration candidate only if caller identity and connectivity are supplied. |
| Claude Code on the web | No established local-host path; requires authorized remote ingress or an applicable connected service. | Remote adapter candidate; cloud container access does not establish local socket reachability. | Public integration or CLI candidate subject to actual cloud equipment, credentials, policy, and backend binding. |

OpenAI senders' paths into Claude populations depend on the Claude receiver contracts and remain for the independent report and later join. A successful OpenAI-target direction does not qualify its reverse. The retained September delivery into Claude Desktop is historical evidence only and was not replayed.

## Smallest meaningful next checks

These are proposals, not live grants or performed tests. Each basic fabric/operation probe has the map's 30 active-minute reassessment limit, including setup/debugging; approval and quota waits pause the clock. Reaching that limit preserves the obstacle and next choice rather than yielding a pass.

| Candidate cohort | Smallest check after concrete authorization | Required evidence and expected cost drivers |
| --- | --- | --- |
| Desktop native tools | One exact disposable independent Codex chat: correlated notification, readback, then bounded request/result; separately test busy input. | Actual app/host/backend identity, admitted prompt and receiver response. Roughly one short receiver turn per operation; sender tool return alone is insufficient. |
| Native children | One authorized child: request, wait/result, follow-up, and reply. | Parent/child IDs and correlated output. Extra model turns; this only qualifies the native relationship. |
| CLI queue + app-server queue | One loaded idle task, then the same task busy; preserve client-message and queue IDs. Add an unloaded stored-task case without treating a stored entry as delivery. | Queue admission, dequeue/start, target history, and receiver acknowledgment. Server availability/setup and two or more short turns dominate; no new server should be silently substituted for the owner. |
| TUI agents/resume/fork | Inspect an exact allowed fixture; rejoin it through its owning server. Test fork separately as new identity. | Session/server binding and expected identity behavior. Interactive control cost; new turn only when explicitly granted. |
| App-server turn API | On one controller-owned fixture, start/read, steer with correct and stale turn IDs, and collect terminal output. Then assess one independently opened fixture through its real owning server. | Request/turn/item correlation; distinct refusal, active, and terminal outcomes. Client/transport setup plus short model turns. |
| ExternalMessage | On an approved app-server fixture, send one external notification while idle and one while busy. Inspect saved item type and correlated output. | Tool-output representation plus receiver behavior; no claim of identity attestation. This comparison needs an authority-focused review before broader reuse. |
| Raw history injection | First establish a concrete need and inspect role/persistence effects in a synthetic contract test. | No immediate live recommendation. Any later fixture must distinguish insertion from receiver notification. |
| Exec / TypeScript SDK | Create one minimal owned thread; capture JSON result and resume by exact ID. | Returned ID, correlated result, continuation output, runtime/package bindings. One or two short turns and subprocess setup. |
| Python SDK | Verify published runtime binding, then run one owned thread and resume/read it. | SDK/runtime identity and final result; independent desktop attach remains a separate test. Python/runtime setup and short turns. |
| Remote TUI / managed remote control | First bind an approved host/client/account route. Inspect one disposable target before one message. Keep listener activation or pairing as a separate authorized setup step. | Reachable target, authenticated route, and receiver output. Highest setup/approval exposure; no speculative listener or pairing activation. |
| Cloud CLI and current Cloud UI | With an explicit published environment and permitted account, create one trivial task; compare CLI ID/status/result with its UI identity, then test UI continuation. | New task identity, result, and continued task association. Environment preparation and cloud startup can consume the whole initial budget. |
| Cloud independent-task follow-up | Obtain the supported caller interface and one permitted exact task reference first. | Missing interface is a valid research outcome. Do not convert “no CLI command” into unofficial backend actuation. |
| Slack / Teams / Linear / GitHub | Use one disposable originating conversation or work item and a connected authorized account; create, inspect result, and follow up where documented. | Service-thread and Codex-task association plus result in the originating service. Requires explicit outward-message authority and may incur service/plan and model costs. |
| Claude Code plugin | Source-check resume selection, then one approved plugin-created minimal job with status/result and continuation. | Plugin/job/Codex-thread bindings and actual host compatibility. Node, plugin, and Codex setup plus model usage; no installation is granted here. |
| MCP wrapper | Only after selecting a backend, expose a narrow synthetic tool contract and prove the actual sender can call it; later repeat the qualified backend operation through it. | MCP tool success and receiver evidence remain distinct. Adds server/auth/config maintenance; removed native MCP-server is not a fallback. |

Restart continuity is a separate follow-up for any selected fabric. Persisted history or queue storage suggests useful recovery inputs, but does not prove reconnection, replay safety, retained credentials, active-turn preservation, or duplicate handling. Measure those on disposable fixtures with separately authorized restart/fault scope.

No latency, reliability, token price, or runtime-preservation result was measured. Documentation/retrieval charges and active research effort were not instrumented. Future probes should retain setup time, tool calls, provider usage, idle process costs, and cleanup work, including failed probes.

## Procedure capture and unresolved facts

This first report supplies a proposed procedure for later capture through [reusable agent-panel workflows](https://github.com/nisavid/provingkit/issues/306): select the receiver population and operation; bind exact task/server/backend and relationship; verify a callable sender route; freeze versions and input; observe operation-specific receiver/result evidence; record idle/busy scope; report restart separately. Consumers should load the reviewed report revision before a dependent probe and record the adapter, runtime, settings, and evidence dependencies they use.

No installed procedure or convention was changed. The coordinator owns placement, independent review, publication, consumer invocation pointers, and the cross-examination join. The report is a research artifact, not a portable authority/model attestation or a qualification receipt.

The material missing facts are:

1. Actual desktop app build, owning daemon, native tool implementation, and cross-client thread association for each proposed fixture.
2. Sender-side exposure of desktop tools from CLI or hosted callers, and the callable remote adapter if native exposure is absent.
3. Current account/workspace/credential route, consent, and model execution evidence for each selected direction.
4. Exact relationship between current Codex Cloud tasks, legacy cloud task IDs, CLI cloud backend identity, and ChatGPT Work cloud conversations.
5. A supported general existing-cloud-task notification/continuation interface, or a concrete restricted workflow that can be accepted instead.
6. Runtime queue admission/consumption, external-message behavior, busy/refusal outcomes, and independently correlated replies.
7. Restart/retry semantics and stronger preservation/attestation evidence where those profiles are selected.
8. Claude Desktop/Web compatibility for the OpenAI plugin and other caller equipment; terminal support alone does not answer this.
9. Current source and behavior of the retained third-party wrappers, to be reconciled at the frozen-report join.
10. Actual setup, operational, and provider costs.

The next decision is which bounded candidate/profile receives a concrete fixture and live grant after the independent reports are frozen, cross-examined, and reviewed.

[release]: https://github.com/openai/codex/releases/tag/rust-v0.162.1
[main]: https://github.com/openai/codex/commit/cc7ba33601286a751477832b01de7b6f8de0dd9c
[npm]: https://registry.npmjs.org/@openai/codex-sdk
[pypi]: https://pypi.org/pypi/openai-codex/0.162.1/json
[app]: https://learn.chatgpt.com/docs/app
[projects]: https://learn.chatgpt.com/docs/projects
[subagents]: https://learn.chatgpt.com/docs/agent-configuration/subagents
[commands]: https://learn.chatgpt.com/docs/developer-commands
[server]: https://learn.chatgpt.com/docs/app-server
[sdk]: https://learn.chatgpt.com/docs/codex-sdk
[mcp]: https://learn.chatgpt.com/docs/extend/mcp
[remote-docs]: https://learn.chatgpt.com/docs/remote-connections
[cloud]: https://learn.chatgpt.com/docs/cloud
[cloud-env]: https://learn.chatgpt.com/docs/environments/cloud-environments
[slack]: https://learn.chatgpt.com/docs/third-party/slack
[linear]: https://learn.chatgpt.com/docs/third-party/linear
[github]: https://learn.chatgpt.com/docs/third-party/github
[cli]: https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/cli/src/main.rs
[queue-cli]: https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/cli/src/queue_cmd.rs
[queue-client]: https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/tui/src/session_queue_commands.rs
[queue-processor]: https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/app-server/src/request_processors/thread_queue_processor.rs
[queue-service]: https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/ext/queue/src/service.rs
[protocol]: https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/app-server-protocol/src/protocol/common.rs
[thread-types]: https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/app-server-protocol/src/protocol/v2/thread.rs
[resume-schema]: https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/app-server-protocol/schema/typescript/v2/ThreadResumeParams.ts
[turn-schema]: https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/app-server-protocol/schema/typescript/v2/TurnStartParams.ts
[ts-exec]: https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/sdk/typescript/src/exec.ts
[ts-thread]: https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/sdk/typescript/src/thread.ts
[py-client]: https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/sdk/python/src/openai_codex/client.py
[py-api]: https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/sdk/python/docs/api-reference.md
[external-message]: https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/sdk/python/docs/api-reference.md#externalmessage
[py-inputs]: https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/sdk/python/src/openai_codex/_inputs.py
[remote-source]: https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/cli/src/remote_control_cmd.rs
[cloud-cli]: https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/cloud-tasks/src/cli.rs
[cloud-client]: https://github.com/openai/codex/blob/092d3acd6bec3e3a14bdc7e7a2810ab628ab759d/codex-rs/cloud-tasks-client/src/http.rs
[plugin-release]: https://github.com/openai/codex-plugin-cc/releases/tag/v1.0.6
[plugin]: https://github.com/openai/codex-plugin-cc/blob/db52e28f4d9ded852ab3942cea316258ae4ef346/README.md
[plugin-protocol]: https://github.com/openai/codex-plugin-cc/blob/db52e28f4d9ded852ab3942cea316258ae4ef346/plugins/codex/scripts/lib/app-server-protocol.d.ts
