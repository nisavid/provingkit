# Supported native interfaces and the remaining owner binding

The existing Claude MCP sender remains a concrete native candidate. OpenAI's App Server provides a supported protocol, but access to the server actually owning the current GUI task remains unproved. Neither T3's release nor a newly started server supplies that missing association.

This November 3 source refresh supplements the independently frozen [T3 comparison](t3-reuse.md). It combines current public documentation with the retained November 2 source assessment of ChatGPT 26.1027.51404. It includes no connection, environment/configuration acquisition, provider turn, or compatibility test against a running receiver.

## Claude receiver

Claude documents cross-session messaging on Linux: an idle recipient starts a turn; an active recipient receives messages between tool calls. Inbound controls can deliver, hold, or refuse. Delivery and receiver permission remain separate. A local inbox socket supports scripts/hooks, with restrictions and session-specific addressing. These documented behaviors are candidates for qualification, not proof about either current consumer. [Cross-session messaging](https://code.claude.com/docs/en/cross-session-messaging).

`claude mcp serve` exposes Claude Code tools to an external client; the client owns confirmation for individual calls. The public page does not establish the exact external `SendMessage` schema or Desktop target binding. The retained native catalog and C1 exchange supply narrower historical evidence for that actual route. Recheck the advertised tool and selected target at the authorized operation, without assuming the generic server is itself the existing Desktop task. [Claude as an MCP server](https://code.claude.com/docs/en/mcp#use-claude-code-as-an-mcp-server).

A targeted Context7 query for this MCP exposure failed to retrieve snippets; the official page was then read directly. Earlier Context7 cross-session results and the direct page agree on the behaviors above. No fresh MCP process was started.

## Codex receiver

The supported App Server protocol supplies thread and turn controls. Current official source includes `thread/read`, running-thread resume/subscription, and a Unix control-socket transport. Those controls operate within their server's task ownership. Creating a different server or matching a stored thread ID does not establish attachment to the selected GUI owner's active turn. [App Server documentation](https://learn.chatgpt.com/docs/app-server), [control-socket source at ac91c144](https://github.com/openai/codex/blob/ac91c14443c11c4279a9305099354e443c6fa7d4/codex-rs/app-server-transport/src/transport/unix_socket.rs).

The retained, separately reviewed compact-owner assessment already identifies three conditional paths in the inspected application build:

| Application-selected path | Concrete source condition | Missing observation |
| --- | --- | --- |
| Configured WebSocket | A nonempty configured App Server URL, with the application's selected host and any legitimate handshake requirements | Actual selected GUI owner, endpoint, caller access, and namespace association |
| Optional local daemon | Eligible local Linux configuration, daemon selection enabled, no conflicting CLI/config overrides, supported executable | Actual selection, resolved control socket, owning daemon, and legitimate caller association |
| Private stdio | The application constructs its own stdio transport when the other paths do not apply | No external App Server attachment has been established for that instance |

These are retained source findings, not new readings of private configuration. The historical IPC owner-discovery response identifies an IPC handling client; it does not disclose the App Server endpoint/process association. Setup's existing-record check found no supported binding to choose among these paths. That is a missing fact, not demonstrated incompatibility or proof that supported attachment is absent.

Current upstream source confirms that the daemon approach exists; it does not prove that this running application uses it. The public-source refresh must not silently turn a source condition into a runtime observation.

The refreshed CLI source also supplies `codex queue` through `thread/queue/add` on the shared daemon or an explicit remote server. It rejects a separate embedded-server path when the shared daemon is present; optional resume can fail after queue submission. That preserves an important distinction: a queue result is not receiver processing, and queued-but-not-resumed is not proved non-submission. This is current upstream source evidence, not compatibility proof for the installed GUI or permission to execute the command. [Session queue implementation](https://github.com/openai/codex/blob/ac91c14443c11c4279a9305099354e443c6fa7d4/codex-rs/tui/src/session_queue_commands.rs).

## What can proceed

The Claude-receiving source can reuse the native MCP sender and the durable local mailbox at their existing responsibilities. The mailbox records obligations and observations; it neither transports messages nor grants authority. No second queue or general orchestration framework is justified by this comparison.

The next discriminating Codex step is a narrowly scoped actual-owner transport observation. Its concrete acquisition plan must identify what is read, what incidental private data can be acquired, and how the result binds to the selected existing GUI task. It must not start a new server, enable a daemon, change configuration, or infer permission from a discovered endpoint. If no supported attachment exists for that owner, the reviewed private IPC candidate remains the concrete fallback. Choosing that fallback before resolving the owner fact would amend the accepted method order and requires an explicit decision.

Source work, operating adoption, and live qualification remain separate. No supported route is qualified by this report, and no old live grant is renewed.
