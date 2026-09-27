# Claude inbox feasibility: native sender found, receiver evidence unresolved

The inspected Claude binaries expose a native external sender through `claude mcp serve`: both `ListAgents` and `SendMessage` have callable MCP schemas, and a read-only `ListAgents` call succeeded. This establishes a sender and native discovery candidate. The accepted ChatGPT-to-Claude Desktop route still lacks a supported, demonstrated way for the caller to inspect receiver-origin delivery and correlated acknowledgment. Keep implementation behind a route decision on that evidence path; bind the discovered address to the consented receiver during later fixture qualification.

This report records the read-only investigation in [Verify the documented Claude inbox sender and exact-target route](https://github.com/nisavid/provingkit/issues/213). It evaluates the contract chosen in [Choose the first inter-harness route and qualification contract](https://github.com/nisavid/provingkit/issues/192#issuecomment-5845461915). Observations were made on 2026-09-26. No notification or model prompt was sent, existing task resumed, permission changed, or installed component modified.

## What the native surface establishes

Anthropic documents running Claude Code as a stdio MCP server for external applications. The server exposes Claude Code tools; the calling client owns confirmation for individual tool calls. This supplies a documented external entry point worth checking before designing a raw socket adapter. [Claude Code as an MCP server](https://code.claude.com/docs/en/mcp#use-claude-code-as-an-mcp-server)

Two short-lived MCP processes were started solely for `initialize` and `tools/list`, using the locally observed Desktop Code binary and the ambient CLI binary. Both returned the peer tools below. One additional process using the Desktop Code binary executed only `ListAgents` with empty arguments. Every probe process exited afterward.

| Local observation | Result | Limit |
| --- | --- | --- |
| Desktop Code binary | `2.1.280`; MCP server identifies itself as `claude/tengu` at that version | This was a separate MCP process using that binary, not a tool call inside an existing Desktop task. |
| Ambient CLI binary | `2.1.283`; MCP server identifies itself as `claude/tengu` at that version | The shell CLI version does not identify a Desktop receiver's executor. |
| MCP capabilities | `tools` with `listChanged: true` | No acknowledgment stream or transcript resource was advertised. This is an advertisement observation, not proof that no other host interface exists. |
| Peer tool metadata | `ListAgents` and `SendMessage` were identical across the two inspected versions | Exposure is not evidence that a send succeeded. |
| Read-only discovery | `ListAgents({})` returned a JSON object containing a formatted `listing` string, with short references, state words, and local/Desktop labels | The response was not a typed receiver identity record. Private names, references, and paths are excluded from this report. |

The inspected `SendMessage` input schema requires `to` and `message`. It also exposes optional `summary` and `notify_when_idle`. `to` names a currently listed recipient, with a disambiguating reference when the listing or error provides one. `message` is plain text. `summary` describes the sender's transcript row and is not transmitted. The idle notice is a separate observation, not a message acknowledgment. The input schema has no correlation-ID field; carrying and echoing an ID in the message would be an application convention. The `ListAgents` schema has no required inputs; its optional `q` and `channel` inputs are described as unavailable in these builds.

The local metadata record is reproducible without calling `SendMessage`: start `claude mcp serve`, send the MCP `initialize` request, acknowledge initialization, and request `tools/list`. The discovery observation additionally calls only `ListAgents` with `{}`. Capture stdout to a file when inspecting CLI help: piped help output ended prematurely in this environment, while regular-file capture returned the complete command list.

| Pinned local evidence | Value |
| --- | --- |
| Desktop Code executable SHA-256 | `ae4b81c88b10062cf7906075ff19071c0629eccb79eefb38878a3cb0cb1fbc35` |
| Canonical peer-tool metadata SHA-256 | `8a0c417fcf41fd0679dcc6a38f06eb922098dcf01a82362eb54a284249bf906b` |
| Peer metadata digest encoding | SHA-256 of the object keyed by `SendMessage` and `ListAgents`, serialized by Python `json.dumps(..., sort_keys=True)` and UTF-8 encoded |

## What documentation and schemas leave open

The cross-session guide documents native discovery, name disambiguation, text delivery, and receiver admission. A busy receiver reads between tool calls; an idle receiver starts a turn. Admission may deliver, hold, or refuse a message. The socket section explicitly anticipates scripts or hooks posting into a session and describes address discovery plus an optional Linux authentication line. It does not specify a complete external message frame and response protocol. That gap favors the observed native MCP tools over a hand-written socket frame. [Cross-session messaging](https://code.claude.com/docs/en/cross-session-messaging), [inbox socket](https://code.claude.com/docs/en/cross-session-messaging#the-sessions-inbox-socket)

Desktop's separate session tools cover Desktop-run Code tasks, including local, SSH, and WSL sessions. Their busy behavior is different: delivery waits for the current work to finish. Those tools can route replies within Desktop, but the documentation does not expose them as a callable external session-reading endpoint. Preserve the distinction between this host surface and native peer messaging. [Work across sessions](https://code.claude.com/docs/en/desktop#work-across-sessions)

The inspected `SendMessage` description says a successful send does not establish that the receiving Claude read the message. It describes delivery notices for eligible local peers, warns that the sender may have no inbox for a notice, and says the Desktop target case reports nothing back through that notice path. This is a tool-description claim, not an observed send outcome. A tool result, idle notice, or silence cannot replace the receiver's explicit acknowledgment required by the accepted contract.

The Agent SDK documents `listSessions`, `getSessionInfo`, and `getSessionMessages`. The latter reads user and assistant messages from a past session transcript by session UUID. These are useful supported inspection candidates, but the inspected docs do not establish their mapping to an active Desktop-owned task or the live peer message's delivery record. The CLI session guide explicitly says Desktop maintains its own history and warns that raw transcript entry formats are internal and change between releases. Treat a Desktop reader as a remaining feasibility question, not an already supported adapter. [SDK session inspection](https://code.claude.com/docs/en/agent-sdk/typescript#getsessionmessages), [SDK session metadata](https://code.claude.com/docs/en/agent-sdk/typescript#getsessioninfo), [session history scope](https://code.claude.com/docs/en/sessions), [transcript format limits](https://code.claude.com/docs/en/sessions#where-transcripts-are-stored)

## Contract assessment

| Accepted requirement | Evidence now | Remaining obligation |
| --- | --- | --- |
| Sender-callable actuator | Documented MCP server plus observed native `SendMessage` schema | Qualify an actual send on the separately authorized disposable fixture. |
| Exact consent-bound Desktop peer | Native name/reference discovery works in a standalone MCP process | Bind the fresh native address to the chosen Desktop task and its consent before a send. A full session UUID is not an added requirement; do not substitute an unverified name match for the native binding. |
| Receiver-origin delivery and correlated acknowledgment | Native peer messages and replies are documented; the ID can fit the text payload | Establish an inspectable receiver record and acknowledgment path to the caller. No such path was demonstrated here. |
| Bounded wait/inspect and unknown reconciliation | The existing contract defines their required behavior | Choose a supported evidence reader before claiming these operations work for Desktop. |
| Receiver account route, model, permissions, and worktree preservation | No exact disposable receiver was selected or observed | The fixture plan must identify before/after observations for all four fields. CLI/package versions alone do not prove them. |
| Busy-receiver continuity | The map requires diagnostic canaries, task resumption, and later turn-in evidence | Capture during later live qualification; this adds no pass/fail threshold. |

The host had installed ChatGPT package `26.917.71314-1` and Claude Desktop package `2.7032.0-3`, and an observed running Codex app-server executable reported `0.157.1`. Some running desktop executables were marked deleted after replacement, so installed package versions do not establish the exact currently running app build. No claim here binds those package versions, an account route, or a model to the intended receiver. Fresh qualification must pin the actual app, executor, task, and settings together.

## Recommended decision

Retain the selected harness direction and investigate the native MCP sender with a verifiable Desktop evidence reader. The remaining decision is whether to examine a version-pinned Desktop metadata/receipt adapter, accept operator-assisted receiver observation for the first route, or change the receiver surface. Those alternatives change the supported observation method or destination and belong with the operator.

Keep the actuator, maintained procedure, and disposable-fixture design blocked on that decision. The native sender discovery narrows the problem; it does not satisfy the whole qualification contract. The separate Claude-to-ChatGPT Queue/Steer map remains independent.
