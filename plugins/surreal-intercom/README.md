# Surreal Intercom

Surreal Intercom supplies communication between agents: addressed messages,
retained attempts, exchange correlation, and truthful partial outcomes. It is
usable independently of Rolecasting, which retains delegation and supervision.

Invoke `$surreal-intercom:communicating-with-agents` in Codex, or load
[Communicate With Agents](skills/communicating-with-agents/SKILL.md) through the
client's supported skill mechanism. Resolve helpers from that skill's installed
resources. The Claude projection serves Claude Code; actual Claude Desktop
exposure is established separately during adoption.

The source supports two distinct directions between existing conversations:

- [Codex to Claude](skills/communicating-with-agents/references/claude-mcp-sender.md)
  through a nominated native MCP child and `SendMessage`.
- [Claude to Codex](skills/communicating-with-agents/references/codex-owner-admission.md)
  through exact-recipient owner discovery and inherited-settings admission.

The [Codex Daybreak recipient](skills/communicating-with-agents/references/codex-daybreak-recipient.md)
source procedure adds a fresh local, projectless, unforked child with a harmless
ordinary bootstrap, followed by explicitly selected tasks. The native caller
creates and reads the child; the helper retains those observations, checks saved
Daybreak selection, and submits each task with `gpt-6-sol`, `medium`, and
`daybreakBlue`. Pending observations and explicit continuations retain their
original references without replay. Effective program/backend selection and live
compatibility remain unqualified.

The [older explicit busy and idle operations](skills/communicating-with-agents/references/codex-ipc-sender.md)
retain their separate contracts. Selecting one is an explicit operation choice.

Each caller supplies its actual recipient binding, applicable permission and
holds, and a protected external store/capture location. Existing settings remain
inherited by ordinary sends. Source and synthetic checks do not qualify current
app compatibility, receiver reliability, installation, or ordinary adoption.

A normal send reports observed status and stable references. Submission does not
imply receipt, a reply, or completed work. The
[retained mailbox](skills/communicating-with-agents/references/native-codex-mailbox.md)
preserves original attempts; caller-owned reply observation and reconciliation
continue those references without automatic resend. These sender commands do not
supply a portable reply observer or background waiter.

The plugin includes one skill and contained Python resources. It supplies no MCP
server or daemon. [License](LICENSE).
